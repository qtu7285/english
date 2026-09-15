# Learning Views Technical Specification

## 0. Purpose
`VIEWS` owns reusable dynamic filters/projections over canonical data.

## 1. Canonical folder
```text
English/VIEWS/
├── README.md
├── AGENTS.md
├── VIEW-TEMPLATE.md
└── <view_slug>/
    └── VIEW.md
```

## 2. Naming
`view_slug` is lowercase ASCII and matches `^[a-z0-9][a-z0-9_-]*$`.

## 3. VIEW.md contract
Define:
- identity;
- source domain(s), optionally a source scope;
- filter predicates;
- ordering/priority;
- optional limit;
- output entity type, normally canonical headwords for vocabulary plans.

## 4. Semantics
A VIEW is dynamic and normally recomputed. It must not fabricate learner facts or silently freeze a result set as if it were a scope.

Canonical dependency rule:
- a VIEW may depend on WORDS facts, learner evidence, current time, and optionally a SCOPE;
- a VIEW must not depend on the PLAN-selected STRATEGY, strategy thresholds, or plan-local overrides. Policy-specific “due under this strategy” selection belongs to STRATEGY/PLAN execution, not to the VIEW filter;
- this keeps dependency direction acyclic: VIEW resolves WHAT is currently eligible, STRATEGY decides HOW/WHEN to act on that subject.

When a PLAN starts a runtime SESSION with a VIEW subject, evaluate the VIEW once and hold that effective headword snapshot stable for that `session_id`. Do not add/remove members mid-session merely because answers in the same session changed the underlying evidence. Recompute on the next session unless the user explicitly restarts/re-resolves the subject. The snapshot is runtime state only and is not persisted as a SCOPE or learner fact.

If a stable reusable membership list is desired, materialize/author it as a SCOPE through an explicit workflow rather than changing VIEW semantics.

A future cache may exist only if rebuildable and documented here.

## 5. Lifecycle/versioning
Canonical VIEW status values are `draft`, `active`, and `retired`. `view_slug` is immutable after activation. Breaking predicate/source/ordering semantics require a new slug/version; non-semantic editorial clarification may be updated in place.
