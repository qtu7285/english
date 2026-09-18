# WORDS Checkpoint and Save Workflow

This file is loaded only when the session reaches a checkpoint/save boundary or a risky state transition with meaningful unsaved learner progress. It separates a cheap in-memory checkpoint preview from the expensive technical local-file write.

## 0. Core rule

A checkpoint preview does not require `WORDS/AGENTS.md` and should not trigger broad local-file reads.

Only after the learner explicitly agrees to save may the tutor load the entire current `WORDS/AGENTS.md` and perform technical persistence work. A standalone `.s` is itself explicit save approval under section 1.1; do not ask for approval a second time.

There is one authoritative writer for the tutoring session. Do not let a second agent/task write learner/shared progress concurrently.

## 1. Checkpoint triggers

A checkpoint may be triggered by:

- the user entering standalone `.s` at any time (already-authorized direct save; use section 1.1);
- the end of a completed test round;
- switching `.headword` or `#username` after meaningful completed unsaved learner/test progress;
- another state transition that could otherwise lose meaningful unsaved progress.

Pure stateless `.headword` learning does not force a local-file checkpoint on every headword switch. Keep unsaved lexical material grouped by visible target in session memory until the learner explicitly checkpoints/saves or until a later risky transition actually requires it.

If there is no meaningful unsaved data, do not ask to save again.

### 1.1 `.s` save command — save now and resume

The learner has chosen standalone `.s` as the save command. Recognize it when the entire message, after trimming whitespace, is exactly `.s`; keep `.headword` as the separate target-switch command. A standalone `.` has no save meaning.

1. Treat `.s` as explicit authorization to save eligible unsaved session material, whether a question is pending, a round has ended, or a checkpoint preview is waiting for approval. Do not ask the section 2 confirmation question again.
2. If a question is pending, preserve its exact content/reference, number, learner/target, round size and remaining count, prior attempts/mistakes, and initial-answer or correction/re-entry state in session memory. `.s` itself is never an answer or an attempt.
3. Save only finalized completed learner events and useful eligible shared learning material through sections 4–10, including the content dependencies of completed events. Keep an unfinished question and its unfinished answer path temporary; do not fabricate a HISTORY event, result, or completion for it.
4. If nothing eligible is unsaved, say `Chưa có dữ liệu mới cần lưu.` and resume the same pending question without writing files or creating an empty commit.
5. For an actual save, load the required technical rules, write and verify the affected CSV data, and create the verified Git snapshot as required by AGENTS. Preserve partial-save retry state and deduplicate repeated `.s` commands through section 9.
6. Report the actual save outcome, then re-display the same pending question and wait for its answer (or corrected re-entry), without advancing, restarting, or replaying completed-question audio. If saving fails, preserve both unsaved material and the pending question; do not claim success.

The existing preview/confirmation flow below still applies to automatic round-end and risky-transition checkpoints when no explicit save authorization has been given.

## 2. Cheap checkpoint preview — no AGENTS, no write

Build the preview entirely from current temporary session state.

Default compact shape:

```text
[SAVE] Checkpoint — <target or session>

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

[CONFIRM] Bạn có muốn lưu tiến trình này không?
```

Show only meaningful counts and a few representative items. Omit empty blocks. Do not dump internal temporary objects, IDs, foreign keys, or implementation details.

Do not access AGENTS or write local files before the learner agrees.

## 3. If the learner declines

- do not write local files;
- keep pending session data unsaved;
- do not reset the unsaved completed-question counter;
- continue the requested workflow;
- do not immediately ask the same save question again.

## 4. Authorized save — technical boundary

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

### 6.1 Missing content is part of an authorized save

An explicit save (`.s` or equivalent approval) also authorizes adding the useful missing FORMS → MEANINGS → PHRASES → EXAMPLES → TESTS dependencies of completed questions. Do this automatically, then save HISTORY; do not stop or request another confirmation merely because a provisional question has no canonical ID. Reuse equivalent existing rows and preserve the exact question, answer, and attempt path that actually occurred. Never invent completed attempts or rewrite historical content to fit the current rules.

Only a real blocker (unreadable required rules, ambiguous identity, invalid/conflicting data, or a failed write) can prevent this step. Identify the specific blocker and keep unsaved evidence for retry. Missing generated IDs alone are not a blocker.

### 6.2 Reusable save helper

Prefer `TOOLS/words_save.py` for a supported single-headword save; read `TOOLS/README.md` for its JSON contract. The tutor supplies reviewed lexical content and actual completed attempts. The helper resolves temporary references, reuses matching rows, creates UUIDv7 IDs, derives result/attempt statistics, verifies relationships, and prepares all file changes before applying them.

After save authorization, prepare one plan in a private temporary directory and keep that exact plan for retries. Apply it, verify the result, review the affected diff, then create the Git snapshot. The helper does not commit or push. Do not regenerate a plan to retry a partial save, because the plan carries stable HISTORY IDs. Keep it until verification and the Git snapshot succeed. A repeated `.s` after success must use session saved-state and must not create another plan for the same completed events.

The helper's preparation belongs to the authorized save boundary; it does not replace the cheap checkpoint preview. For unsupported migrations or lexical ambiguity, follow AGENTS directly rather than inventing data to make the helper pass. An unrelated whole-repository check failure must be reported separately from the verified target's save result.

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

`[OK] Đã lưu tiến trình của urge: 3 collocations + 4 câu test + 4 history events.`

If any part failed, state precisely what was and was not saved. Never imply success for a failed write.

## 11. Direct technical operations

If the user explicitly requests schema/template/migration/index repair/file architecture work rather than a normal tutoring save, the small README router should route directly to `AGENTS.md`. This SAVE workflow may be skipped unless checkpoint/session persistence is also involved.
