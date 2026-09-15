# <Strategy Name>

## Identity
- `strategy_type`: `<TYPE>`
- `strategy_name`: `<Strategy Name>`
- `strategy_slug`: `<strategy_slug>`
- `status`: `draft`
- `base_strategy`: `<none-or-strategy_slug>`
- Purpose: <short purpose>

## Applicability
Define what kinds of learning objects this method can operate on. Do not list a reusable vocabulary set here.

## Target Model
Define the unit evaluated by the strategy, e.g. headword, meaning, phrase, example, test, or another explicit unit.

For WORD-family strategies, declare machine-readable selection explicitly when applicable, for example:
- `meaning_tiers`: `<core | core,common | ...>`
- `phrase_tiers`: `<core | core,common | ...>`
- `phrase_status`: `active`

## Stages
Define stages and transitions when relevant.

## Content Readiness Gates
Define explicit content requirements.

## Learner Achievement Gates
Define actual evidence required from WORDS HISTORY/STATISTICS.

## Review / Maintenance Method
- `method`: <acquisition-only | fixed-spacing | adaptive | mistake-first | mixed | other>
- `spacing_rule`: <explicit rule>
- `review_trigger`: <explicit rule>

## Priority Rules
1. <priority>
2. <priority>
3. <priority>

## Stop / Completion Rules
Define when a target/headword/stage is complete under this strategy.

## Overrides / Parameters
Document only reusable strategy parameters. Vocabulary membership belongs to SCOPES; composition belongs to PLANS.


## Lifecycle Note
After `status = active`, keep `strategy_slug` stable. Breaking semantic changes require a new strategy slug/version rather than silently changing the meaning of the active slug.
