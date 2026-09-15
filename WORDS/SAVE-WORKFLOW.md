# WORDS Checkpoint and Save Workflow

This file is loaded only when the session reaches a checkpoint/save boundary or a risky state transition with meaningful unsaved learner progress. It separates a cheap in-memory checkpoint preview from the expensive technical local-file write.

## 0. Core rule

A checkpoint preview does not require `WORDS/AGENTS.md` and should not trigger broad local-file reads.

Only after the learner explicitly agrees to save may the tutor load the entire current `WORDS/AGENTS.md` and perform technical persistence work.

There is one authoritative writer for the tutoring session. Do not let a second agent/task write learner/shared progress concurrently.

## 1. Checkpoint triggers

A checkpoint may be triggered by:

- the user entering `.` when no test answer is pending;
- the end of a completed test round;
- switching `.headword` or `#username` after meaningful completed unsaved learner/test progress;
- another state transition that could otherwise lose meaningful unsaved progress.

Pure stateless `.headword` learning does not force a local-file checkpoint on every headword switch. Keep unsaved lexical material grouped by visible target in session memory until the learner explicitly checkpoints/saves or until a later risky transition actually requires it.

If there is no meaningful unsaved data, do not ask to save again.

## 2. Cheap checkpoint preview — no AGENTS, no write

Build the preview entirely from current temporary session state.

Default compact shape:

```text
💾 Checkpoint — <target or session>

Shared:
- +<n> phrases
- +<n> examples
- +<n> tests

#<username>:
- +<n> completed history events
- <n> câu từng sai

Một số nội dung:
- <representative item>
- <representative item>

👉 Bạn có muốn lưu tiến trình này không?
```

Show only meaningful counts and a few representative items. Omit empty blocks. Do not dump internal temporary objects, IDs, foreign keys, or implementation details.

Do not access AGENTS or write local files before the learner agrees.

## 3. If the learner declines

- do not write local files;
- keep pending session data unsaved;
- do not reset the unsaved completed-question counter;
- continue the requested workflow;
- do not immediately ask the same save question again.

## 4. If the learner agrees — technical boundary

Before any local schema/template/storage/CSV write:

1. load the entire current `WORDS/AGENTS.md`;
2. apply its current schema, naming, ID/FK, migration, audit, index-sync, and storage rules;
3. load only the concrete local files/rows required for this save;
4. do not load PLANS/STRATEGIES merely to persist truthful WORDS facts unless the user separately requested a planning operation.

If AGENTS cannot be accessed/read fully, do not perform the write and do not imply success.

## 5. Resolve pending visible targets at save time

Stateless FAST_CORE learning may have accumulated unsaved material before any canonical local lookup. For each pending visible target that will actually be saved:

1. resolve its canonical headword using current AGENTS/WORDS-INDEX.csv rules;
2. reuse an existing canonical shared headword file when present;
3. create a new headword folder/shared file only when the canonical workflow permits it;
4. preserve ordinary inflections under the canonical lexical headword;
5. ask only on genuine lexical ambiguity where choosing would create a different canonical item.

Do not canonicalize every stateless target preemptively just because it was mentioned during learning. Canonicalize only targets included in the confirmed save.

## 6. Shared lexical-content write

For confirmed useful new shared material such as forms, meanings, phrases, examples, or generated tests:

- write only new/non-duplicate data;
- preserve the current shared schema and relationships from AGENTS;
- generate canonical persistent IDs only now, under the AGENTS ID rules;
- map temporary session references to the new canonical IDs before dependent rows are written;
- set required row audit metadata using the active canonical username;
- preserve historically referenced semantic identity;
- never rewrite old factual content merely to satisfy a current strategy.

A valid active username is required for shared-content changes because shared row audit metadata records the responsible user.

If a generated test used during the session was not previously in canonical TESTS, create/resolve its shared content chain before writing a learner HISTORY event that references it.

## 7. Learner HISTORY write

Write finalized learner events only after their canonical `test_id` references are valid.

Follow current AGENTS rules for:

- learner filename/location;
- HISTORY schema;
- canonical generated HISTORY IDs;
- UTC `created_at` precision;
- canonical machine-readable result enum;
- attempts and first-try facts;
- append-only behavior;
- idempotent retry;
- multi-headword `session_id` grouping.

Do not persist plan-specific future decisions such as next review date, box level, ease factor, stability, difficulty, or other strategy state into WORDS learner history merely because a plan uses those concepts.

If a learner file does not yet exist, create it from the current canonical USER-TEMPLATE.csv according to AGENTS at this save boundary, not during ordinary learning/test startup.

## 8. WORDS-INDEX.csv synchronization

After a successful shared-content write:

1. synchronize the affected canonical `WORDS-INDEX.csv` row;
2. update `file_path`, `updated_at`, and `test_count` as required by AGENTS;
3. read the affected index row back;
4. verify the required invariants before declaring index synchronization successful.

If shared content saved successfully but index synchronization fails, do not roll back or duplicate the shared content. Report that the content is saved but the index is out of sync, then repair/reconcile according to AGENTS.

Learner-only writes do not change shared-content `updated_at`/`test_count` in WORDS-INDEX.csv.

## 9. Partial multi-file saves

Local writes are not assumed atomic across multiple files; create a Git commit only after all intended files have been saved and verified.

If a checkpoint partially succeeds:

- keep successful writes;
- preserve only the still-unsaved temporary items for retry;
- never duplicate already-saved HISTORY events or shared rows;
- use canonical IDs/idempotency rules from AGENTS to reconcile retry state;
- do not reset the global unsaved counter until the relevant learner progress is confirmed saved.

## 10. Save completion

After successful persistence:

- mark only successfully persisted temporary items as saved;
- reset the unsaved completed-question counter only when the learner progress represented by that counter is successfully saved;
- confirm briefly, for example:

`✅ Đã lưu tiến trình của urge: 3 collocations + 4 câu test + 4 history events.`

If any part failed, state precisely what was and was not saved. Never imply success for a failed write.

## 11. Direct technical operations

If the user explicitly requests schema/template/migration/index repair/file architecture work rather than a normal tutoring save, the small README router should route directly to `AGENTS.md`. This SAVE workflow may be skipped unless checkpoint/session persistence is also involved.
