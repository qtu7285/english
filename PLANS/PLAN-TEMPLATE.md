# <Plan Name>

## Identity
- `plan_name`: `<Plan Name>`
- `plan_slug`: `<plan_slug>`
- `status`: `draft`
- Purpose: <short purpose>

## Subject
- `subject_mode`: `<active_headword | headword | scope | view>`
- `subject_ref`: `<none | canonical-headword | scope_slug | view_slug>`

## Strategy
- `strategy_ref`: `<strategy_slug>`

## Schedule / Cadence
- `mode`: `<on-demand | daily | weekly | other>`
- rule: <explicit rule>

## Plan Priority / Ordering
1. <optional plan-level ordering rule>

## Strategy Overrides
<none by default; explicit only>

## Stop / Completion
<plan-level behavior if different from the referenced strategy>


## Session Resolution
- Resolve the effective subject once at SESSION start.
- If `subject_mode = view`, hold the VIEW result stable for the current `session_id`.
- Use persisted HISTORY plus finalized-unsaved events from the current session when applying the strategy.

## Lifecycle Note
After `status = active`, keep `plan_slug` stable. Breaking semantic changes require a new plan slug/version.
