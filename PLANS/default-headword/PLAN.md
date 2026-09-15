# DEFAULT-HEADWORD

## Identity
- `plan_name`: `DEFAULT-HEADWORD`
- `plan_slug`: `default-headword`
- `status`: `active`
- Purpose: canonical composition used for ordinary `.headword` study.

## Subject
- `subject_mode`: `active_headword`
- `subject_ref`: `none`

At runtime, bind the canonical headword resolved from the current `.headword` command. This is an implicit singleton subject; do not create a persistent SCOPE file for every ordinary word command.

## Strategy
- `strategy_ref`: `word-010-050`

Read `STRATEGIES/word-010-050/STRATEGY.md` for all method/gate semantics.

## Schedule / Cadence
- `mode`: `on-demand`
- rule: run/continue when the learner invokes `.headword` or explicitly resumes this plan.

## Plan Priority / Ordering
For a singleton subject, ordering across headwords is not applicable. Within the headword, defer to the strategy.

## Strategy Overrides
None.

## Stop / Completion
The plan completes for the active headword when the referenced strategy reports that headword complete. Later maintenance may be handled by another plan/strategy without rewriting WORDS HISTORY.
