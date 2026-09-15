#!/usr/bin/env python3
"""Fast read-only integrity check for the local WORDS index.

Run from the repository root:
    python3 tools/words_check.py
"""

import csv
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "WORDS" / "WORDS-INDEX.csv"
REQUIRED = {"headword", "file_path", "updated_at", "test_count"}


def main() -> int:
    if not INDEX.is_file():
        print(f"[X] Missing {INDEX}")
        return 1

    errors = []
    seen_headwords = set()
    seen_paths = set()
    with INDEX.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        if set(reader.fieldnames or ()) != REQUIRED:
            errors.append("WORDS-INDEX.csv has an unexpected header")
        for row_number, row in enumerate(reader, start=2):
            headword = (row.get("headword") or "").strip()
            file_path = (row.get("file_path") or "").strip()
            if not headword or not file_path:
                errors.append(f"row {row_number}: headword/file_path is empty")
                continue
            if headword in seen_headwords:
                errors.append(f"row {row_number}: duplicate headword {headword}")
            if file_path in seen_paths:
                errors.append(f"row {row_number}: duplicate file_path {file_path}")
            seen_headwords.add(headword)
            seen_paths.add(file_path)

            shared = ROOT / file_path
            if not shared.is_file():
                errors.append(f"row {row_number}: missing shared file {file_path}")
                continue
            tests = shared.with_name(f"{shared.stem}-TESTS.csv")
            if not tests.is_file():
                errors.append(f"row {row_number}: missing TESTS bundle {tests}")
                continue
            with tests.open(newline="", encoding="utf-8") as test_stream:
                test_rows = [r for r in csv.DictReader(test_stream) if (r.get("id") or "").strip()]
            try:
                expected = int(row.get("test_count") or "")
            except ValueError:
                errors.append(f"row {row_number}: test_count is not an integer")
                continue
            if expected != len(test_rows):
                errors.append(
                    f"row {row_number}: test_count={expected}, actual={len(test_rows)}"
                )

    if errors:
        print("[X] WORDS integrity check failed")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"[OK] WORDS index check passed ({len(seen_headwords)} headwords)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
