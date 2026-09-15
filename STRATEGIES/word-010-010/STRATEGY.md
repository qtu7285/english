# WORD-010-010

## Identity
- `strategy_type`: `WORD`
- `strategy_name`: `WORD-010-010`
- `strategy_slug`: `word-010-010`
- `status`: `active`
- `base_strategy`: `none`
- Purpose: lighter WORD acquisition strategy requiring broad exposure across 10 distinct contexts.

## Applicability
Apply independently to each canonical headword resolved by the active PLAN subject. The strategy itself contains no vocabulary membership.

## Target Model
For each headword, select learning targets deterministically:

```text
meaning_tiers = core
phrase_tiers = core
phrase_status = active
```

Each matching active/core PHRASES row linked to a core MEANINGS row is one learning target. Cover relevant forms naturally and avoid unnatural coverage inflation.

## Stages
`impression → acquisition`; maintenance is not scheduled here.

## Content Readiness Gates
For every target:

```text
examples_per_learning_target = 10
```

Require at least 10 distinct natural useful examples, with tests that collectively cover those contexts and relevant forms naturally.

## Learner Achievement Gates
For every target:

```text
correct_completions_per_learning_target = 10
minimum_correct_completions_per_example = 1
first_try_required = false
```

Require 10 distinct example contexts to each receive at least one finalized completion whose HISTORY `result` is `correct`, `partial_corrected`, or `incorrect_corrected`. Derive the set from HISTORY/TESTS; do not persist it separately.

## Review / Maintenance Method
- `method`: `acquisition-only`
- `spacing_rule`: `none`
- `review_trigger`: `none`

## Priority Rules
1. recent mistakes;
2. missing content/test coverage;
3. uncredited example contexts;
4. under-covered forms;
5. varied contexts before repetition.

## Stop / Completion Rules
A target completes when it has at least 10 suitable examples and 10 distinct credited contexts with at least one correct completion each. A headword completes when every in-scope target completes.

## Overrides / Parameters
No default headword-specific overrides.
