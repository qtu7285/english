# WORDS save helper

`words_save.py` handles the mechanical part of an **authorized** save for one canonical headword and one learner. It needs Python 3.14+ (standard-library UUIDv7); it has no third-party dependencies.

The tutor still resolves the canonical headword, reviews the English and Vietnamese content, grades actual answers, and reads the required WORDS manuals. This helper does not generate lessons, grade English, decide mastery, or authorize saving. Do not call it during test startup or an unapproved checkpoint preview.

## Run after save approval

Create a private temporary directory with `mktemp -d`. Put the reviewed session payload there and keep the prepared plan there until the save and Git snapshot succeed:

```sh
python TOOLS/words_save.py prepare /absolute/temp/session.json --plan /absolute/temp/save-plan.json
python TOOLS/words_save.py apply /absolute/temp/save-plan.json
```

Preparation reads the target bundle and writes only the plan. Application checks for intervening changes, writes shared dependencies before history and the index, recalculates statistics, and reads every target file back. Both commands print a result and return a nonzero exit code on failure. Inspect the exit code before claiming success.

Retry a failed application with **the same plan file**. It contains stable UUIDv7 IDs, expected prior file hashes, and exact intended contents. If some files were already written, the retry accepts those files and writes the rest. Reapplying a completed plan makes no changes. Do not create another plan for those same learner events, even if a previous process failed to report success. Keep the session's saved-event state after success so repeated `.s` commands do not produce duplicate HISTORY.

Plans contain learner data; keep them private. The plan is a temporary retry artifact, not a new canonical session store. If it is lost, reconcile actual CSV events against session evidence before making another plan.

The helper does not run Git. After successful application, review the affected diff and create the focused snapshot through SAVE-WORKFLOW. Push only when authorized by the Git workflow.

## JSON contract

Top-level fields:

- `headword`: already resolved canonical headword; supported filename syntax is lowercase letters/digits/hyphens, beginning with a letter.
- `username`: canonical learner username without `#`.
- `content`: optional object containing `forms`, `meanings`, `phrases`, `examples`, and `tests` arrays in dependency order.
- `events`: optional array of completed questions, with actual evaluated attempts in chronological order.

Each content record has a unique temporary `ref` plus the semantic columns from its CSV schema. Omit `id` and audit columns for new content. `tag` and `note` may be omitted; all other semantic fields must be supplied as strings. References such as `"form_id": "@base"` resolve an earlier temporary reference. Canonical IDs can also be used directly.

To reference an existing row, supply only `{"ref": "old_test", "id": "<existing TESTS.id>"}` in the appropriate group. Full supplied rows are reused when all semantic fields except `note` match; ambiguous duplicates cause an explicit reconciliation error. Shared rows are appended, never rewritten.

Example payload (illustrative; only save events that actually happened):

```json
{
  "headword": "measure",
  "username": "qtu",
  "content": {
    "forms": [
      {"ref": "base", "form": "measure", "role": "base"},
      {"ref": "plural", "form": "measures", "role": "plural"}
    ],
    "meanings": [
      {"ref": "meaning", "form_id": "@base", "pos": "noun",
       "meaning": "biện pháp", "usage": "take measures", "tier": "core"}
    ],
    "phrases": [
      {"ref": "phrase", "form_id": "@base", "meaning_id": "@meaning",
       "phrase": "take measures", "meaning": "thực hiện các biện pháp",
       "type": "collocation", "tier": "core", "words": "2", "status": "active"}
    ],
    "examples": [
      {"ref": "example", "form_id": "@plural", "phrase_id": "@phrase",
       "sentence": "We must take measures to protect customer data.",
       "vi_meaning": "Chúng ta phải thực hiện các biện pháp để bảo vệ dữ liệu khách hàng.",
       "source": "test"}
    ],
    "tests": [
      {"ref": "test", "form_id": "@plural", "phrase_id": "@phrase",
       "example_id": "@example",
       "question": "We must ___ ___ to protect customer data.",
       "vi_context": "Chúng ta phải thực hiện các biện pháp để bảo vệ dữ liệu khách hàng.",
       "correct_answer": "take; measures", "test_type": "fb", "status": "active"}
    ]
  },
  "events": [
    {"test_id": "@test",
     "attempts": [
       {"answer": "measure", "grade": "incorrect"},
       {"answer": "take measures", "grade": "correct"}
     ],
     "mistake_note": "Missing take and plural -s."}
  ]
}
```

Valid attempt grades are `correct`, `partial`, and `incorrect`. The final attempt must be correct, and no earlier attempt may be correct. Exclude control commands, clarification questions, and ungraded messages. The helper derives `result`, `attempts`, and `first_try`; it trusts the tutor's supplied grades. Explain useful mistakes in `mistake_note`. HISTORY timestamps are the time these records are created during preparation, not invented historical completion times.

For `correct_answer`, separate complete accepted alternatives with `|`, keeping the original first. For fill blanks, use `;` within each alternative, for example `take; measures | adopt; measures`. Every alternative must fill every blank; only the first must reconstruct the source example exactly. The tutor verifies naturalness and contextual meaning; the helper only validates structure. It rejects empty alternatives, empty fills, duplicate alternatives, and mismatched blank counts.

A valid alternative that still requires original-answer recall is a `partial` attempt, with `mistake_note` explaining that the wording was valid. Save its event only after a `correct` re-entry of the original, as required by TEST-WORKFLOW 8.3. Do not retroactively change events completed before that rule applied. Extending an existing historically referenced answer list requires a new test ID; this helper appends a new semantic row and preserves the old one. Archive the superseded test separately through the authorized workflow before future selection.

For existing content, reuse known IDs whenever available. Exact text matching cannot recognize paraphrases as the same sense: the tutor must resolve that semantic equivalence before preparing a payload.

## Verification and limits

The helper validates schemas, canonical UUIDv7 IDs, foreign keys, fill-blank reconstruction, result/attempt consistency, target index count/path, and statistics. It preserves old content and history. It can create a cold headword bundle or append to an intact bundle, and can restore the target's missing/stale index entry from its actual content. It refuses an incomplete existing bundle rather than fabricating missing historical content.

Saves use a process lock and per-file atomic replacement. A multi-file save is recoverable through its prepared plan, not a single filesystem transaction. Other writers that ignore this lock must not run concurrently. Any unexpected file change blocks application before writing or at the affected file; retain the plan and reconcile.

Only the target learner and headword are checked in full. Whole-repository failures (for example, another headword's missing file) must be reported separately; this helper is not a global migration or repair tool. Follow WORDS/AGENTS.md for legacy schemas, global reconciliation, unsupported headword syntax, or ambiguous lexical identity.

Run regression tests in isolated temporary repositories:

```sh
python -B -m unittest discover -s TOOLS -p test_words_save.py -v
```

To operate on an isolated repository, put `--root /absolute/test/repo` before the `prepare` or `apply` command.

