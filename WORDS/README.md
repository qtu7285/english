# English Tutor Runtime Router

This file is the small canonical router for the English tutoring workflow under `WORDS`.
It is platform-neutral and is intentionally kept short so canonical hydration is cheap.

## 0. Canonical files

Runtime router:

- Path: `WORDS/README.md`

Lazy WORDS workflow modules:

- Test/history workflow: `WORDS/TEST-WORKFLOW.md`
- Checkpoint/save workflow: `WORDS/SAVE-WORKFLOW.md`
- Technical/data specification: `WORDS/AGENTS.md`
- Canonical headword index: `WORDS/WORDS-INDEX.csv`

Planning entrypoint:

- `English/PLANS/README.md`

Do not preload all of these files. This README exists to decide the minimum next read.

## 1. FAST_CORE stays outside local data

runtime/client instructions own the small stateless tutoring core.

For a visible English word, phrase, sentence, or `.headword`, ordinary first-impression learning should happen without reading local files when it does not depend on stored state.

This includes, as supported by the current client:

- Vietnamese meaning;
- part of speech;
- common usage/collocations;
- short natural examples;
- sentence meaning/grammar/correction;
- pronunciation capability.

For `.headword`, the leading `.` marks learner intent but the visible lexical target may be explained immediately before canonical local resolution.

Do not load this README merely because a new chat started or merely to explain a word.

## 2. Session state before hydration

The tutor may keep lightweight temporary session state without local-file reads, including:

- current visible `.headword` target;
- current valid `#username` override;
- `DEFAULT_USERNAME` supplied by the client;
- unsaved useful lexical material grouped by visible target;
- pending requested test count;
- whether a test answer is currently pending.

This temporary state is not canonical local state and must not be presented as saved history/mastery.

Switching from one stateless `.headword` to another does not by itself force local-data hydration or a checkpoint. Keep useful unsaved material grouped by target until an explicit save/checkpoint or a genuinely risky tested-state transition requires it.

If a test is active or meaningful completed learner-test progress exists, follow `TEST-WORKFLOW.md` / `SAVE-WORKFLOW.md` before a risky switch.

## 3. Canonical-state boundary

Load this entire current README only when an action first needs canonical or learner-specific state, including:

- starting or continuing a test;
- a positive integer requesting test questions;
- learner history/progress;
- canonical headword resolution from local data;
- PLAN/STRATEGY evaluation or selection;
- deciding plan completion or what to study next;
- checkpoint/save;
- Git reconciliation, migration, schema, template, or file operations.

Do not rely on a remembered README from another session.

After this README is loaded, route the requested action below and read only the required branch.

## 4. Routing rules

### 4.1 Ordinary learning

If the request is still only meaning, usage, collocation, example, grammar, correction, pronunciation, comparison between words, or another stateless learning question:

- use FAST_CORE;
- do not read TEST-WORKFLOW, SAVE-WORKFLOW, AGENTS, PLANS, STRATEGIES, learner files, or WORDS content merely for enrichment;
- do not auto-save.

### 4.2 Test or learner history

Read the entire current:

`WORDS/TEST-WORKFLOW.md`

Then follow its lazy read order.

Normal test startup must not read `AGENTS.md` merely to run questions. Test/history is read-only with respect to local files; new evidence stays temporary until a save boundary.

### 4.3 Plan / strategy / next-study decision

Read the entire current:

`English/PLANS/README.md`

Then load only the PLAN, STRATEGY, SCOPE, or VIEW that PLANS actually references for the requested decision.

Do not read unrelated strategies.

If the request also starts/runs a test, additionally load `TEST-WORKFLOW.md`.

### 4.4 Checkpoint or save

Read the entire current:

`WORDS/SAVE-WORKFLOW.md`

Checkpoint preview should use temporary session state and must not read AGENTS merely to ask whether the learner wants to save.

Only after explicit save approval does SAVE-WORKFLOW load the entire current `WORDS/AGENTS.md` and the concrete target files required for persistence.

### 4.5 Direct technical operation

For schema, template, storage, IDs/FKs, migration, WORDS-INDEX.csv repair/reconciliation, file creation/moves, or another technical local-file operation, read the entire current:

`WORDS/AGENTS.md`

Do not load TEST-WORKFLOW or PLANS unless the requested technical operation actually depends on them.

### 4.6 Canonical headword lookup only

If the user explicitly needs canonical local headword resolution without a test/save:

- use `WORDS-INDEX.csv` exact lookup first;
- on miss, resolve the likely lexical lemma/canonical form linguistically and look up again;
- ordinary inflections remain under the base lexical headword unless an exact entry or clear context establishes an independent lexical item;
- ask only on genuine lexical ambiguity.

This read-only lookup does not require AGENTS unless integrity repair/migration becomes necessary.

## 5. Learner resolution

Resolve learner identity in this order:

1. valid explicit `#username` in the current session;
2. otherwise valid `DEFAULT_USERNAME=<username>` supplied by runtime/client configuration;
3. otherwise unknown.

A learner may remain unknown during stateless learning.

A known learner is required before learner-specific testing/history/save. If a positive test count was already supplied, preserve that count while asking for `#username`; do not make the learner repeat the request.

Do not guess identity from account name, display name, email, device, or prior assumptions.

## 6. Preserve intent across lazy hydration

Hydration must not consume or reset the learner's visible intent.

Never ask them to resend a `.headword`, word, phrase, sentence, username, requested test count, or save command merely because a required file was loaded.

Do not repeat a lexical explanation that FAST_CORE already showed before hydration. Continue only with the newly required canonical/plan/test/save portion.

## 7. Minimal-read principle

At every step ask: **what is the smallest authoritative source needed for the next user-visible action?**

Rules:

- no speculative preload;
- no whole-tree local-file scan for a normal tutoring turn;
- no AGENTS read for ordinary learning or normal test delivery;
- no PLANS/STRATEGY read until a plan/strategy decision is actually required;
- no learner history read unless it affects the requested action;
- no learner file creation until confirmed persistence requires it;
- reuse files already successfully loaded in the current session unless the user explicitly requests refresh or a write requires a fresh technical read.

## 8. Single-writer rule

One tutoring session has one authoritative state and one writer.

Other agents/tasks may perform read-only analysis/audit when useful, but they must not independently save learner/shared progress in parallel.

All writes are serialized through the confirmed SAVE/AGENTS workflow.

## 9. Failure behavior

If a required canonical file cannot be accessed or fully read:

- say clearly which required layer is unavailable;
- do not claim it was loaded;
- do not continue that local-data action from memory.

A stateless FAST_CORE explanation may still continue when it does not depend on the unavailable canonical data.

## 10. Responsibility boundary

- runtime/client FAST_CORE = immediate stateless tutoring.
- `WORDS/README.md` = lightweight runtime router.
- `WORDS/TEST-WORKFLOW.md` = test delivery, grading, learner-history read behavior, temporary test evidence.
- `WORDS/SAVE-WORKFLOW.md` = checkpoint preview and persistence orchestration.
- `WORDS/AGENTS.md` = technical/data/schema/storage/write specification.
- `PLANS` = plan composition and execution policy.
- `STRATEGIES` = reusable learning/review methods and gates.
- `SCOPES` = explicit reusable headword sets.
- `VIEWS` = dynamic selectors/projections.
- `WORDS` shared/learner CSV files = vocabulary content and truthful learner evidence.

Do not duplicate large rule sets across these layers. When behavior changes, update the smallest owning layer.
