#!/usr/bin/env python3
"""Prepare and apply an authorized single-headword CSV save. Python 3.14+."""
import argparse
import csv
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import re
import tempfile
from datetime import datetime, timezone
import uuid

AUDIT = "created_at created_by updated_at updated_by".split()
SCHEMAS = {
    "forms": "id form role tag note".split() + AUDIT,
    "meanings": "id form_id pos meaning usage tier note".split() + AUDIT,
    "phrases": "id form_id meaning_id phrase meaning type tier words note status".split() + AUDIT,
    "examples": "id form_id phrase_id sentence vi_meaning source".split() + AUDIT,
    "tests": "id form_id question vi_context correct_answer phrase_id example_id test_type status".split() + AUDIT,
    "history": "id created_at test_id answer result attempts first_try mistake_note session_id".split(),
    "stats": ["metric", "value"],
    "index": "headword file_path updated_at test_count".split(),
}
PREFIX = dict(forms="f", meanings="m", phrases="p", examples="e", tests="t")
LINKS = dict(form_id="forms", meaning_id="meanings", phrase_id="phrases", example_id="examples")
OPTIONAL = {"tag", "note"}
ID_PATTERN = re.compile(r"^[fmpeths]-[0-9a-z]{25}$")

def require(condition, message):
    if not condition:
        raise ValueError(message)

def new_id(prefix):
    require(hasattr(uuid, "uuid7"), "Python 3.14+ with uuid.uuid7 is required")
    number, body = uuid.uuid7().int, ""
    while number:
        number, digit = divmod(number, 36)
        body = "0123456789abcdefghijklmnopqrstuvwxyz"[digit] + body
    return prefix + "-" + body.zfill(25)

def valid_id(value, prefix):
    require(isinstance(value, str) and bool(ID_PATTERN.fullmatch(value)) and value[0] == prefix,
            "Invalid " + prefix + " ID")
    require(uuid.UUID(int=int(value[2:], 36)).version == 7, "ID must encode a UUIDv7")

def timestamp(value):
    parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    require(parsed.strftime("%Y-%m-%dT%H:%M:%SZ") == value, "Invalid UTC timestamp")
    return value

def paths(headword, username):
    require(bool(re.fullmatch(r"[a-z][a-z0-9-]*", headword)), "Unsupported canonical headword")
    require(bool(re.fullmatch(r"[a-z0-9][a-z0-9_-]*", username)), "Invalid username")
    stem = f"WORDS/{headword[:3]}/{headword}/{headword}"
    return dict(forms=stem + ".csv", meanings=stem + "-MEANINGS.csv",
                phrases=stem + "-PHRASES.csv", examples=stem + "-EXAMPLES.csv",
                tests=stem + "-TESTS.csv", history=stem + "-" + username + ".csv",
                stats=stem + "-" + username + "-STATISTICS.csv", index="WORDS/WORDS-INDEX.csv")

def safe_path(root, relative):
    target = root / relative
    require(target.resolve() == target, "Symlink or noncanonical path: " + relative)
    require(target.is_relative_to(root), "Path outside repository")
    return target

def digest(raw):
    return None if raw is None else hashlib.sha256(raw).hexdigest()

def parse(raw, kind):
    if raw is None:
        return []
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8"), newline=""))
    require(reader.fieldnames == SCHEMAS[kind], "Unsupported schema: " + kind)
    rows = list(reader)
    require(all(None not in r and all(v is not None for v in r.values()) for r in rows),
            "Malformed CSV: " + kind)
    return rows

def render(rows, kind):
    out = io.StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=SCHEMAS[kind], lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue().encode("utf-8")

def statistics(history):
    total = len(history)
    first = sum(r["first_try"] == "TRUE" for r in history)
    values = dict(tests_attempted=total, correct_first_try=first, mistakes=total-first,
                  first_try_rate=first / total if total else 0,
                  total_attempts=sum(int(r["attempts"]) for r in history),
                  last_practiced=max((r["created_at"] for r in history), default=""))
    return [{"metric": k, "value": str(v)} for k, v in values.items()]

def validate(data, headword, username):
    all_ids, tables = set(), {}
    for kind in (*PREFIX, "history"):
        tables[kind] = {}
        for row in data[kind]:
            valid_id(row["id"], PREFIX.get(kind, "h"))
            require(row["id"] not in all_ids, "Duplicate ID")
            all_ids.add(row["id"])
            tables[kind][row["id"]] = row
            timestamp(row["created_at"])
            if kind != "history":
                timestamp(row["updated_at"])
                require(all(re.fullmatch(r"[a-z0-9][a-z0-9_-]*", row[k])
                            for k in ("created_by", "updated_by")), "Invalid audit username")
    for kind in PREFIX:
        for row in data[kind]:
            for field, target in LINKS.items():
                if field in row:
                    require(row[field] in tables[target], "Broken " + field + " in " + kind)
            if "tier" in row:
                require(row["tier"] in {"core", "common", "extended"}, "Invalid tier")
            if "status" in row:
                require(row["status"] in {"active", "archived"}, "Invalid status")
            if kind == "phrases":
                require(row["words"] == str(len(row["phrase"].split())), "Phrase word count mismatch")
            if kind == "examples":
                require(row["source"] in {"learning", "test"}, "Invalid example source")
            if kind == "tests":
                example = tables["examples"][row["example_id"]]
                require(example["phrase_id"] == row["phrase_id"], "Test/example phrase mismatch")
                require(row["test_type"] in {"fb", "mc", "tf", "rw"}, "Invalid test type")
                alternatives = [value.strip() for value in row["correct_answer"].split("|")]
                require(all(alternatives), "Empty answer alternative")
                seen = set()
                for position, alternative in enumerate(alternatives):
                    answers = ([answer.strip() for answer in alternative.split(";")]
                               if row["test_type"] == "fb" else [alternative])
                    require(all(answers), "Empty blank answer")
                    key = tuple(" ".join(answer.casefold().split()) for answer in answers)
                    require(key not in seen, "Duplicate answer alternative")
                    seen.add(key)
                    if row["test_type"] == "fb":
                        require(row["question"].count("___") == len(answers), "Blank count mismatch")
                        filled = row["question"]
                        for answer in answers:
                            filled = filled.replace("___", answer, 1)
                        if position == 0:
                            require(filled.strip() == example["sentence"], "Filled test differs from example")
    for row in data["history"]:
        valid_id(row["session_id"], "s")
        require(row["test_id"] in tables["tests"], "History references missing test")
        result = row["result"]
        require(result in {"correct", "partial_corrected", "incorrect_corrected"}, "Invalid result")
        require(row["attempts"].isdigit() and int(row["attempts"]) >= 1, "Invalid attempts")
        first = result == "correct"
        require(row["first_try"] == ("TRUE" if first else "FALSE"), "Inconsistent first_try")
        require((int(row["attempts"]) == 1) == first, "Inconsistent result/attempts")
    require(data["stats"] == statistics(data["history"]), "Statistics mismatch")
    index = data["index"]
    require(len({r["headword"] for r in index}) == len(index), "Duplicate indexed headword")
    require(len({r["file_path"] for r in index}) == len(index), "Duplicate indexed path")
    matches = [r for r in index if r["headword"] == headword]
    require(len(matches) == 1, "Missing target index row")
    require(matches[0]["file_path"] == paths(headword, username)["forms"], "Index path mismatch")
    require(matches[0]["test_count"] == str(len(data["tests"])), "Index count mismatch")
    timestamp(matches[0]["updated_at"])

def prepare(root, payload):
    require(set(payload) <= {"headword", "username", "content", "events"}, "Unknown payload field")
    headword, username = payload["headword"], payload["username"]
    files = paths(headword, username)
    require((root / "WORDS").is_dir(), "Repository WORDS directory is missing")
    originals = {}
    for kind, relative in files.items():
        path = safe_path(root, relative)
        originals[kind] = path.read_bytes() if path.exists() else None
    require(originals["index"] is not None, "Missing canonical index; reconcile first")
    data = {k: parse(raw, k) for k, raw in originals.items()}
    present = [originals[k] is not None for k in PREFIX]
    require(not any(present) or all(present), "Incomplete existing bundle; reconcile rather than invent content")
    require(any(present) or originals["history"] is None, "Orphan learner history")
    indexed = [r for r in data["index"] if r["headword"] == headword]
    if indexed:
        require(any(present), "Index points to missing content; reconcile first")
        require(indexed[0]["file_path"] == files["forms"], "Unexpected indexed path; reconcile first")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    audit = dict(created_at=now, created_by=username, updated_at=now, updated_by=username)
    content = payload.get("content", {})
    require(set(content) <= set(PREFIX), "Unknown content group")
    refs = {}
    for kind in PREFIX:
        for item in content.get(kind, []):
            item = dict(item)
            ref = item.pop("ref")
            require(isinstance(ref, str) and ref and ref not in refs and not ref.startswith("@"),
                    "Duplicate or invalid temporary reference")
            if set(item) == {"id"}:
                require(any(r["id"] == item["id"] for r in data[kind]), "Unknown existing ID")
                refs[ref] = item["id"]
                continue
            allowed = set(SCHEMAS[kind]) - set(AUDIT) - {"id"}
            require(set(item) <= allowed and allowed - OPTIONAL <= set(item), "Missing/unknown fields: " + kind)
            require(all(isinstance(v, str) for v in item.values()), "Content values must be strings")
            for field in LINKS:
                if item.get(field, "").startswith("@"):
                    require(item[field][1:] in refs, "Unresolved reference: " + item[field])
                    item[field] = refs[item[field][1:]]
            values = {key: item.get(key, "") for key in allowed}
            identity = allowed - {"note"}
            matches = [r for r in data[kind] if all(r[key] == values[key] for key in identity)]
            require(len(matches) <= 1, "Ambiguous duplicate content: " + kind)
            row = matches[0] if matches else dict(id=new_id(PREFIX[kind]), **values, **audit)
            if not matches:
                data[kind].append(row)
            refs[ref] = row["id"]
    events = payload.get("events", [])
    session_id = new_id("s") if events else None
    for event in events:
        require(set(event) <= {"test_id", "attempts", "mistake_note"}, "Unknown event field")
        test = event["test_id"]
        if test.startswith("@"):
            require(test[1:] in refs, "Unknown event test reference")
            test = refs[test[1:]]
        attempts = event["attempts"]
        require(isinstance(attempts, list) and attempts, "Completed attempts are required")
        for attempt in attempts:
            require(set(attempt) == {"answer", "grade"} and isinstance(attempt["answer"], str),
                    "Invalid attempt")
            require(attempt["grade"] in {"correct", "partial", "incorrect"}, "Invalid attempt grade")
        require(attempts[-1]["grade"] == "correct", "Unfinished question must remain temporary")
        require(all(a["grade"] != "correct" for a in attempts[:-1]), "Question already completed earlier")
        result = ("correct" if len(attempts) == 1 else
                  "incorrect_corrected" if any(a["grade"] == "incorrect" for a in attempts) else
                  "partial_corrected")
        note = event.get("mistake_note", "")
        require(isinstance(note, str), "mistake_note must be text")
        data["history"].append(dict(id=new_id("h"), created_at=now, test_id=test,
                                    answer=attempts[-1]["answer"], result=result,
                                    attempts=str(len(attempts)), first_try="TRUE" if len(attempts) == 1 else "FALSE",
                                    mistake_note=note, session_id=session_id))
    require(any(r['form'] == headword and r['role'] == 'base' for r in data['forms']),
            'Canonical base form is required')
    shared_changed = any(data[k] != parse(originals[k], k) for k in PREFIX)
    if indexed:
        indexed[0]["test_count"] = str(len(data["tests"]))
        if shared_changed:
            indexed[0]["updated_at"] = now
    else:
        latest = max((r["updated_at"] for k in PREFIX for r in data[k]), default=now)
        data["index"].append(dict(headword=headword, file_path=files["forms"],
                                  updated_at=latest, test_count=str(len(data["tests"]))))
    data["stats"] = statistics(data["history"])
    validate(data, headword, username)
    # Preserve untouched byte formatting; append-only semantics are checked independently.
    outputs = {}
    for kind in files:
        original_rows = parse(originals[kind], kind)
        if kind in (*PREFIX, "history"):
            require(data[kind][:len(original_rows)] == original_rows, "Existing rows changed")
        raw = originals[kind] if original_rows == data[kind] and originals[kind] is not None else render(data[kind], kind)
        outputs[kind] = dict(path=files[kind], before=digest(originals[kind]), after=raw.decode("utf-8"))
    return dict(version=1, root=str(root), headword=headword, username=username, files=outputs,
                session_id=session_id, completed_events=len(events))

def apply(root, plan):
    require(plan["version"] == 1 and plan["root"] == str(root), "Plan repository/version mismatch")
    expected = paths(plan["headword"], plan["username"])
    require(set(plan["files"]) == set(expected), "Invalid plan file set")
    for kind, relative in expected.items():
        require(plan["files"][kind]["path"] == relative, "Invalid plan path")
        safe_path(root, relative)
    validate({k: parse(v["after"].encode("utf-8"), k) for k, v in plan["files"].items()},
             plan["headword"], plan["username"])
    lock_name = "words-save-" + hashlib.sha256(str(root).encode()).hexdigest() + ".lock"
    changed = 0
    with (Path(tempfile.gettempdir()) / lock_name).open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        # Check every dependency before the first write; partial retries accept exact after-state.
        for entry in plan["files"].values():
            target = safe_path(root, entry["path"])
            raw = target.read_bytes() if target.exists() else None
            require(digest(raw) in {entry["before"], digest(entry["after"].encode("utf-8"))},
                    "Concurrent change; preserve this plan and reconcile: " + entry["path"])
        for entry in plan["files"].values():
            target = safe_path(root, entry["path"])
            after = entry["after"].encode("utf-8")
            raw = target.read_bytes() if target.exists() else None
            if raw == after:
                continue
            require(digest(raw) == entry["before"], "Concurrent change during write")
            target.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(prefix=".words-save-", dir=target.parent)
            try:
                with os.fdopen(fd, "wb") as stream:
                    stream.write(after)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(tmp, target)
            finally:
                if os.path.exists(tmp):
                    os.unlink(tmp)
            changed += 1
        for entry in plan["files"].values():
            require(safe_path(root, entry["path"]).read_bytes() == entry["after"].encode("utf-8"),
                    "Readback verification failed")
    return changed

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("payload", type=Path)
    prep.add_argument("--plan", required=True, type=Path)
    run = sub.add_parser("apply")
    run.add_argument("plan", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        if args.command == "prepare":
            require(not args.plan.exists(), "Plan already exists; reuse it for retries")
            plan = prepare(root, json.loads(args.payload.read_text(encoding="utf-8")))
            # Exclusive creation keeps the stable IDs from an earlier plan.
            with args.plan.open("x", encoding="utf-8") as stream:
                json.dump(plan, stream, ensure_ascii=False, indent=2)
            print(f"[OK] Prepared {plan['completed_events']} completed events; CSV files unchanged.")
        else:
            plan = json.loads(args.plan.read_text(encoding="utf-8"))
            count = apply(root, plan)
            print(f"[OK] Verified save; {count} files changed, {plan['completed_events']} events in this plan.")
        return 0
    except (ValueError, KeyError, TypeError, OSError, csv.Error) as error:
        print(f"[X] {error}")
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
