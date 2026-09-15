# WORDS Test and Learner-State Workflow

This file is loaded only when a tutoring action needs canonical test, learner-history, or plan-backed state. It is not required for ordinary `.headword`, word, phrase, sentence, meaning, collocation, example, grammar, or pronunciation help.

## 0. Boundary

Before reading this file, the small canonical `WORDS/README.md` router must already be loaded for the current session.

Do not read `WORDS/AGENTS.md` merely to start or run a test. Testing is read-only with respect to local files. Keep new learner events and newly generated lexical/test material in temporary session state until a save boundary.

Only load the additional sources that the requested test/history action actually needs.

## 1. Resolve learner and visible target

Use the current session state in this order:

1. explicit valid `#username` from the current session;
2. otherwise valid `DEFAULT_USERNAME` from runtime/client configuration;
3. otherwise learner is unknown.

A positive integer requesting test questions requires a known learner. If unknown, ask for `#username` and preserve the requested count and visible target so the learner does not need to repeat them.

For `.headword`, preserve the surface form that the learner typed during FAST_CORE. Do not ask them to resend it when canonical hydration begins.

## 2. Canonical headword lookup for test/history

Use the canonical WORDS index:

- File: `WORDS/WORDS-INDEX.csv`
- CSV rows: `HEADWORDS`
- Runtime columns needed here: `headword | file_path | updated_at | test_count`

Read-only lookup order:

```text
visible surface form
→ exact HEADWORDS.headword lookup
→ if miss, linguistic lemma/canonical-headword resolution
→ HEADWORDS lookup again
→ if found, open shared headword CSV bundle directly by file_path
```

Canonicalize aggressively, split conservatively, and ask only when genuine lexical ambiguity remains and choosing would create a different canonical headword.

Ordinary inflections such as `learned`, `learning`, `urged`, or `urging` normally remain under their base lexical headword unless an exact canonical entry or clear context establishes an independent lexical item.

After the exact + canonical-candidate lookups, classify the result:

1. **Indexed canonical headword** — a valid HEADWORDS row exists. Open the shared CSV bundle by `file_path` and continue with canonical data.
2. **Clean index miss / cold headword** — no exact row and no canonical-candidate row exists, and there is no separate evidence that the index is corrupt. Do **not** block the test. Treat the target as a provisional cold headword for this session and continue with generated temporary test content.
3. **Known/suspected index-integrity problem** — there is evidence of a stale, duplicate, orphaned, mismatched, or otherwise unreliable index entry. Do not repair it during test startup. For ordinary practice, the tutor may still continue in provisional mode without claiming canonical/history coverage; repair belongs to a save/technical boundary after `AGENTS.md` is loaded.

A missing index row by itself must not trigger a full WORDS tree scan and must not prevent a learner from practicing. It only means that canonical shared content/history cannot be assumed available through the normal fast lookup path.

For a cold/provisional test, keep the linguistically resolved target as a temporary session headword label. Do not create a folder, shared CSV bundle, learner CSV, WORDS-INDEX.csv row, or canonical IDs during test startup. Re-resolve and reconcile at confirmed save time through `SAVE-WORKFLOW.md` + `AGENTS.md`.

## 3. Plan and strategy hydration

A `.headword` first-impression does not load PLANS. The first plan-dependent action does.

For the normal `.headword` test flow:

1. read the entire current `English/PLANS/README.md`;
2. follow its read order;
3. load only the selected PLAN;
4. load only the STRATEGY referenced by that PLAN;
5. load SCOPES/VIEWS only when the selected PLAN/STRATEGY actually requires them.

The ordinary `.headword` intent uses the canonical `default-headword` plan unless the learner explicitly selected another plan/strategy.

Do not preload unrelated plans, strategies, scopes, or views.

If the user explicitly chooses or asks about a strategy without starting a test, route through PLANS and load only the relevant strategy; do not load this TEST workflow unless test/history behavior is also needed.

## 4. Read only the learning data needed

For an indexed canonical headword:

- use the indexed shared headword `file_path` to read the required shared content;
- read only required CSV rows needed for selection, typically the relevant `PHRASES`, `EXAMPLES`, and `TESTS` rows plus form/meaning context when necessary;
- load learner HISTORY only when it materially affects selection, progress, mistake targeting, or the user's explicit history/progress request;
- do not read every learner file or every headword file;
- do not run a full WORDS tree scan during normal test startup.

The learner file is conceptually `<headword>-<username>.csv` inside the canonical headword folder. For a normal read, prefer an already-known/cached file reference or a narrowly scoped lookup. If the learner file does not yet exist, treat history as empty for this materialized headword; do not create the file during test startup.

For a cold headword with no indexed canonical source:

- do not search the entire WORDS tree merely to prove absence;
- do not create/read a learner file;
- do not claim that the learner has no historical data — say only that no indexed canonical source was available for history-backed selection;
- generate the requested practice provisionally from the visible target, the loaded PLAN/STRATEGY method, and reliable linguistic knowledge;
- keep all generated forms/meanings/phrases/examples/tests and learner results in temporary session state until save.

For an indexed headword whose canonical `TESTS` supply is insufficient for the requested round or selected strategy coverage, use **hybrid mode**: reuse suitable canonical items first, then generate only the additional provisional items needed. Do not write those generated items during test startup.

## 5. Starting a test

When no test answer is pending:

- a positive integer starts exactly that many questions;
- the integer is the current round size, not a change to plan completion thresholds;
- show only one question at a time;
- do not reveal the answer or pronunciation before the learner answers.

Choose one source mode for the round/target:

1. **Canonical mode** — indexed shared data provides enough suitable active tests. Select from canonical content according to the active PLAN/STRATEGY and relevant learner evidence.
2. **Hybrid mode** — indexed canonical data exists but does not provide enough suitable questions/coverage. Reuse suitable canonical tests and generate temporary provisional tests for the remainder.
3. **Cold provisional mode** — no indexed canonical source exists for the resolved target. Generate the requested questions temporarily and start the test normally.

Do **not** block a requested test merely because:

- the headword is absent from `WORDS-INDEX.csv`;
- the indexed `test_count` is `0`;
- the shared CSV bundle has too few suitable tests;
- the learner file does not yet exist.

In provisional/hybrid generation:

- follow the active PLAN/STRATEGY method as far as the available evidence allows;
- prioritize common, high-value, natural uses that are supportable from reliable linguistic knowledge and the learner's visible study context;
- do not invent obscure senses, fake prior mastery, fake tier membership, or nonexistent stored history;
- use temporary references only; no canonical persistent IDs are required before save;
- if a strategy gate depends on canonical shared tier coverage or saved learner history that is unavailable, the questions may still run, but do not claim that the plan/strategy completion gate has been satisfied from provisional evidence alone.

For fill-blank (`fb`) questions, use at least two meaningful blanks when natural: one for the target and one for an important collocation/partner word. The Vietnamese context must not directly reveal the missing answers.

Prefer common collocations, natural structures, practical communication/work contexts, varied subjects/tenses/situations, and new sentences rather than mechanical repetition.

When learner history is actually available, reuse learned knowledge intelligently, pay extra attention to prior mistakes, and avoid repeating old sentences verbatim when possible.

## 6. Pending-answer rule

While a test question is pending, treat every learner message as the answer except `.headword` and `#username` control commands.

A literal `.` while a question is pending is an answer, not a checkpoint command.

If `.headword` or `#username` arrives while a question is pending, stop the active question. If meaningful completed unsaved learner progress exists, route to `SAVE-WORKFLOW.md` before finalizing the switch. If nothing meaningful was completed, switch without forcing a save.

## 7. Question display

Default compact format:

```text
Câu 2/5

🇬🇧 She ___ the ___ to reply immediately.
🇻🇳 Cô ấy kiềm chế ý muốn trả lời ngay lập tức.
```

For multiple choice or another test type, add only the minimal controls needed for that question.

Do not add filler or preview future questions.

## 8. Grading

For every answer:

1. grade as fully correct, partial, or incorrect;
2. show the complete correct answer;
3. for partial/incorrect, explain only the error that needs fixing;
4. show the complete correct English sentence and natural Vietnamese meaning;
5. provide pronunciation only for correct target text, never for the learner's incorrect response;
6. after a fully correct completion, provide copy output when supported.

Multiple blanks:

- all correct → `✅`;
- partially correct → `🟡`;
- main target wrong → `❌`.

For `🟡` or `❌`, end with:

`👉 Mời bạn nhập lại đáp án đúng.`

Do not advance until the learner re-enters the answer fully correctly.

A question counts as completed only after it is fully correct. Multiple attempts still count as one completed question.

### 8.1 Fully correct

```text
✅ Đúng!

<correct answer>

🇬🇧 <complete correct sentence>
🇻🇳 <Vietnamese meaning>

<copy outputs when supported>
<pronunciation output(s)>
```

### 8.2 Partial / incorrect

```text
🟡 Gần đúng
# or
❌ Chưa đúng

Đáp án đúng: <correct answer>
Lỗi: <brief correction>

🇬🇧 <complete correct sentence>
🇻🇳 <Vietnamese meaning>

<pronunciation output(s)>

👉 Mời bạn nhập lại đáp án đúng.
```

Do not provide dedicated copy controls for the correction until re-entry is fully correct.

## 9. Pronunciation and copy capability

Use platform capability rather than platform brand.

Pronunciation fallback:

1. native pronunciation/audio capability when available;
2. otherwise a real Google Translate URL for the exact correct English target using `https://translate.google.com/?sl=en&tl=vi&text=<URL_ENCODED_TEXT>&op=translate`;
3. otherwise state that playback is unavailable; never invent audio or fake controls.

When both the target answer and complete sentence require pronunciation, provide separate outputs when the platform supports them.

Copy fallback after a fully correct answer:

1. real native copy control if available;
2. otherwise separate fenced `text` blocks for the exact reusable English answer and complete sentence;
3. otherwise clean selectable text.

Never copy or pronounce the learner's incorrect response as if it were correct.

## 10. Temporary session evidence — no local write

During testing, keep new evidence in temporary session state. Do not write local files after every question.

Track at least the factual information required to save later:

- canonical headword when resolved from indexed data, or a provisional linguistic target label for a cold headword;
- source mode (`canonical`, `hybrid`, or `cold_provisional`);
- selected existing `test_id`, or a temporary reference for a newly generated unsaved test;
- learner answer path;
- final result class;
- attempts;
- first-try status;
- concise mistake note when useful;
- round/session grouping;
- any newly generated shared forms/meanings/phrases/examples/tests that would be useful to persist.

Do not generate or depend on canonical persistent IDs for newly unsaved rows until the save workflow loads `AGENTS.md`. Existing local row IDs may of course be retained as references.

For a provisional semantic chain, keep enough temporary structure to reconstruct/deduplicate it at save time, for example:

```text
temporary form/meaning context
→ temporary phrase/collocation
→ temporary example sentence
→ temporary test
→ learner result evidence
```

At confirmed save time, `SAVE-WORKFLOW.md` + `AGENTS.md` must re-check canonical identity and current local state before creating anything. If an equivalent canonical row/file already exists — including a materialized headword that was missing from a stale index — reuse/reconcile it instead of creating a duplicate. Only after a valid canonical `TESTS.id` exists may the corresponding learner HISTORY event be persisted.

Canonical HISTORY result values will be assigned at save time according to AGENTS, based on the factual attempt path retained here.

## 11. Unsaved-progress reminder

Track fully completed questions since the last successful save.

After 5 unsaved completed questions, remind between questions only:

`💾 Bạn đã có 5 câu test chưa lưu. Nhập . nếu muốn tạo checkpoint cho an toàn.`

If the learner continues, continue normally. Remind again at reasonable 5-question milestones (10, 15, ...). Reset only after a confirmed successful save.

## 12. Round end and checkpoint routing

When the requested round is fully completed:

1. end the round;
2. if there is meaningful unsaved progress, load `WORDS/SAVE-WORKFLOW.md` and run its checkpoint preview;
3. do not load `AGENTS.md` merely to show that preview;
4. `AGENTS.md` is loaded only if the learner confirms a write;
5. after the save decision, ask whether to learn another target or start another round.

Do not automatically open a new round.

## 13. History/progress requests

For a factual history request that does not require plan evaluation, resolve only the requested headword/learner and read the minimum learner HISTORY/STATISTICS needed.

If the headword has no indexed canonical source, do not reinterpret the clean miss as proof that no prior history exists. State that no indexed canonical source was available for history lookup. A practice round may still proceed provisionally, but a factual claim such as “you have never studied this word” is not supported by an index miss alone.

For questions such as plan completion, next study target, mastery gate, or strategy evaluation, additionally load PLANS and only the selected PLAN/STRATEGY and needed scope/view inputs. Provisional unsaved evidence may inform the current session, but do not declare a persisted plan-completion gate satisfied when that gate requires canonical saved evidence.

Do not interpret learner HISTORY as future scheduling policy; WORDS stores factual evidence, while PLANS/STRATEGIES decide how that evidence is evaluated.
