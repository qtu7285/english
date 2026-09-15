# Learning Strategies Operating Manual

This file is the canonical operating manual for reusable learning methods under `English/STRATEGIES`.

## 0. Purpose

`STRATEGY` answers **how to learn**. It must not decide which reusable vocabulary set is being studied.

Canonical separation:

```text
WORDS      = knowledge + factual learner evidence
SCOPES     = reusable explicit sets of canonical headwords
VIEWS      = reusable dynamic projections/filters
STRATEGIES = reusable learning/review methods
PLANS      = bind a subject selector to a strategy plus optional execution policy
SESSION    = one runtime execution of a plan for one learner
```

A strategy may define acquisition thresholds, test distribution, mistake priority, review spacing, stage gates, and completion rules. It must remain reusable across one headword or many headwords.

## 1. Read order

When a plan selects a strategy:
1. load the selected `STRATEGY.md` completely;
2. resolve the plan subject through `active_headword`, `headword`, `scope`, or `view`;
3. read the required WORDS content/evidence;
4. apply the strategy independently to the resolved headwords unless the strategy explicitly defines cross-headword behavior;
5. return runtime decisions to the active session.

For technical changes under STRATEGIES, read `STRATEGIES/AGENTS.md` first.

## 2. Strategy vs plan

A strategy is not a plan.

```text
strategy = reusable method
plan     = selected subject + selected strategy + optional schedule/priority/overrides
```

Therefore `WORD-010-050` is a strategy name. It does not mean “study urge” or “study business-core”.

## 3. Canonical default strategy

The canonical default strategy for ordinary `.headword` learning is `WORD-010-050`, stored at:

```text
STRATEGIES/word-010-050/STRATEGY.md
```

Its key semantics are:
- 10 useful example contexts per learning target;
- 50 fully-correct completions per learning target;
- at least 5 correct completions on each of 10 distinct example contexts;
- target phrases are deterministic `active + core` rows linked to `core` meanings; relevant forms are covered naturally;
- first-try correctness observed but not required;
- repetition distributed when practical rather than immediate identical drilling.

`WORD-010-010` remains a lighter named strategy.

## 4. Session interaction

A strategy never creates learner facts by itself. Only actual completed learning events are written to WORDS HISTORY. Runtime decisions must read persisted HISTORY plus finalized-but-unsaved events already completed in the current session so the planner does not repeat work merely because the next checkpoint has not happened yet.

A runtime session may use strategy decisions such as:
- choose the lowest-credited example;
- prioritize a recent mistake;
- move to another headword in the plan;
- stop when the plan/strategy gate is met.

Do not persist future decisions into WORDS as facts.


## 5. Stable strategy identity

Once a strategy is active, its slug identifies a stable execution contract. Do not silently redefine an active slug with breaking target/counting/spacing/completion semantics; create a new strategy slug/version and retire the old one when appropriate.
