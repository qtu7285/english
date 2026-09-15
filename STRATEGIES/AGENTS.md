# Learning Strategies Technical Specification

This file is the canonical technical/data specification for `English/STRATEGIES`.

## 0. Boundary

- `STRATEGIES` owns reusable learning/review methods.
- `SCOPES` owns explicit reusable headword membership.
- `VIEWS` owns dynamic filtering/projection definitions.
- `PLANS` owns composition/binding.
- `WORDS` owns vocabulary content and factual learner evidence.

A strategy must not duplicate a scope member list or learner HISTORY.

## 1. Canonical folder

```text
English/STRATEGIES/
├── README.md
├── AGENTS.md
├── STRATEGY-TEMPLATE.md
├── word-010-010/
│   └── STRATEGY.md
├── word-010-050/
│   └── STRATEGY.md
└── <strategy_slug>/
    └── STRATEGY.md
```

## 2. Naming

`strategy_slug` is lowercase ASCII and matches `^[a-z0-9][a-z0-9_-]*$`.

WORD-family display names use:

```text
WORD-EEE-CCC
```

- `EEE` = zero-padded examples per learning target.
- `CCC` = zero-padded correct completions per learning target.
- display name regex: `^WORD-[0-9]{3}-[0-9]{3}$`.
- corresponding slug is lowercase, e.g. `word-010-050`.

The name encodes EEE and CCC only. Distribution requirements such as a per-example minimum must be explicit in the file.

## 3. Canonical STRATEGY.md contract

Every strategy defines:

```text
Identity
Applicability
Target Model
Stages
Content Readiness Gates
Learner Achievement Gates
Review / Maintenance Method
Priority Rules
Stop / Completion Rules
Overrides / Parameters
```

Required identity fields:
- `strategy_type`
- `strategy_name`
- `strategy_slug`
- `status`
- optional `base_strategy`
- purpose

A strategy must not contain `scope_mode`, fixed vocabulary membership, or a plan schedule.

## 4. WORD-family semantics

A WORD strategy is evaluated per canonical headword in the effective plan subject.

The default WORD-family learning target is deterministic: one WORDS `PHRASES` row with `status = active` and `tier = core`, linked to a `MEANINGS` row with `tier = core`. `common` and `extended` content are excluded unless the selected strategy explicitly includes those tiers.

For `WORD-010-050`:

```text
examples_per_learning_target = 10
correct_completions_per_learning_target = 50
minimum_correct_completions_per_example = 5
first_try_required = false
```

Counting:
- target credit: `HISTORY.test_id → TESTS.phrase_id`;
- only finalized canonical HISTORY result values `correct`, `partial_corrected`, and `incorrect_corrected` count as completed questions; all count once after final correction, while `first_try`/`attempts` remain available for stricter strategies;
- example credit: `HISTORY.test_id → TESTS.example_id`;
- a finalized fully-correct question counts once;
- wrong/partial then corrected counts once unless a strategy explicitly requires first-try;
- at least 10 distinct example contexts must each reach 5 correct completions;
- the credited example set is derived from HISTORY/TESTS and is not persisted separately;
- if more than 10 examples exist, only 10 need satisfy this acquisition strategy unless explicitly stated otherwise;
- never multiply thresholds by every TESTS.id;
- relevant forms must be represented naturally, not by a Cartesian product of form × target × example.

Consistency rule: if a strategy requires EEE examples each to have minimum M correct completions, `EEE × M` must not exceed CCC unless the strategy explicitly states that CCC is only a label and defines a higher actual minimum. For canonical WORD strategies, keep them consistent.

## 5. Strategy inheritance

```text
base strategy
→ named strategy overrides
→ explicit plan-level parameter overrides
```

The most specific explicit rule wins. If a plan repeatedly overrides core thresholds, prefer defining a new reusable strategy instead.

## 6. Lifecycle and semantic versioning

Canonical strategy `status` values are `draft`, `active`, and `retired`.

- `strategy_slug` becomes immutable when the strategy first becomes `active`;
- editorial clarification that does not change machine meaning may be updated in place;
- any breaking change to target selection, thresholds, counting, spacing, priority, completion, or other execution semantics must create a new strategy slug rather than silently redefining an active slug;
- when the numeric `WORD-EEE-CCC` contract stays the same but other semantics break, an explicit versioned slug such as `word-010-050-v2` may be used while the display name/purpose makes the revision clear;
- retired strategies remain readable so plans/reviews that reference them can still resolve their historical definition; do not delete them merely because a newer strategy exists.

## 7. Persistence

Persist strategy definitions only. Do not persist:
- learner attempts;
- synthetic mastery;
- future due decisions as WORDS facts;
- resolved scope memberships from a view.

If future strategy execution requires cache/state, document it here first and keep it rebuildable from canonical strategy + WORDS evidence where practical.
