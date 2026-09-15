# Learning Plans Technical Specification

## 0. Boundary
`PLANS` owns composition/binding only.

```text
WORDS      factual content/evidence
SCOPES     explicit reusable membership
VIEWS      dynamic filtering/projection
STRATEGIES reusable methods
PLANS      subject + strategy + execution policy
```

## 1. Canonical folder
```text
English/PLANS/
├── README.md
├── AGENTS.md
├── PLAN-TEMPLATE.md
├── default-headword/
│   └── PLAN.md
└── <plan_slug>/
    └── PLAN.md
```

Strategy definitions must not live under PLANS after migration.

## 2. Naming
`plan_slug` is lowercase ASCII and matches `^[a-z0-9][a-z0-9_-]*$`.

## 3. PLAN.md contract
Every plan defines:
- identity (`plan_name`, `plan_slug`, `status`, purpose);
- exactly one `subject_mode`;
- corresponding subject reference when required;
- exactly one `strategy_ref`;
- optional schedule/cadence;
- optional ordering/priority rules;
- optional strategy overrides;
- plan-level completion/stop behavior when it differs from the strategy default.

Supported subject modes:

```text
active_headword
headword
scope
view
```

Reference rules:
- `active_headword` → no persisted subject ref; bind current canonical `.headword`;
- `headword` → canonical WORDS headword;
- `scope` → canonical `scope_slug` under SCOPES;
- `view` → canonical `view_slug` under VIEWS.

## 4. Strategy references
`strategy_ref` is the canonical STRATEGIES slug, e.g. `word-010-050`.

A plan must read the referenced `STRATEGY.md`; do not infer strategy semantics from the slug alone.

Do not copy large strategy definitions into PLAN.md. Small explicit overrides are allowed. Reusable variants belong in STRATEGIES.

## 5. Default plan
Canonical ordinary `.headword` plan:

```text
plan_name: DEFAULT-HEADWORD
plan_slug: default-headword
subject_mode: active_headword
strategy_ref: word-010-050
```

Path: `PLANS/default-headword/PLAN.md`.

## 6. Scope/view resolution
A plan's effective runtime headword set is resolved before strategy execution.

```text
active_headword/headword → canonical WORDS headword(s)
scope                   → SCOPES membership
view                    → VIEWS runtime result
```

A plan must not persist or duplicate an entire referenced scope member list or VIEW result. For execution, however, the resolved effective subject is snapshotted in runtime at SESSION start; that snapshot is stable for the `session_id` and is discarded as runtime state after the session.

## 7. Session
A session is runtime state, not a PLANS artifact by default.

```text
PLAN + learner + resolved-headword snapshot + persisted WORDS evidence + current finalized-unsaved events + current time → SESSION decisions
```

Canonical session rules:
- create one canonical `s-...` `session_id` for the runtime SESSION and reuse it across HISTORY rows in every headword learner file touched by that session;
- resolve the subject once at session start. A VIEW result is therefore a runtime snapshot and does not churn membership after every answer;
- strategy decisions must count both persisted HISTORY and finalized-but-unsaved events already completed in the current session; checkpoint timing must not make the planner repeat already completed work;
- automatic progression from one headword to the next inside the same PLAN/SESSION is not an explicit user `.headword` switch and does not itself require a checkpoint; normal round-end, unsaved-count, user command, and risky-transition checkpoint rules still apply;
- multi-file saves are not atomic across local files. Use `HISTORY.id` as the idempotency key: keep successful file writes, retry only missing events after partial failure, and never append the same event twice; create a Git commit only after the intended files are verified;
- unless the PLAN defines another stop rule, a fixed headword/scope subject completes when every headword in the session snapshot meets the selected STRATEGY. A VIEW-driven session completes relative to that session's snapshot; a later session may recompute the VIEW and yield new members.

Actual attempts/results are persisted only through WORDS HISTORY. `HISTORY.session_id` groups events. Do not create a SESSIONS folder merely to mirror existing HISTORY facts.

## 8. Persistence
Persist in PLANS:
- plan definitions;
- references to scope/view and strategy;
- plan-specific schedule/priority/overrides.

Do not persist in PLAN.md:
- learner attempts/results;
- duplicated HISTORY;
- resolved dynamic view output by default;
- copied STRATEGY bodies;
- copied SCOPE membership by default.

## 9. Lifecycle/versioning
Canonical PLAN status values are `draft`, `active`, and `retired`. `plan_slug` is immutable after activation. Editorial clarification may update in place, but breaking changes to subject binding, `strategy_ref`, schedule semantics, overrides, ordering, or completion behavior require a new plan slug/version rather than silently redefining an active plan. Retired plans remain readable while referenced.

## 10. Technical change rule
- runtime plan behavior → update `PLANS/README.md`;
- composition/storage conventions → update `PLANS/AGENTS.md`;
- plan contract → update `PLAN-TEMPLATE.md`;
- method rules → STRATEGIES;
- static set membership → SCOPES;
- dynamic filter semantics → VIEWS;
- WORDS content/history schema → WORDS only.
