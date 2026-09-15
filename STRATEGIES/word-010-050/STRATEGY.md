# WORD-010-050

## Identity
- `strategy_type`: `WORD`
- `strategy_name`: `WORD-010-050`
- `strategy_slug`: `word-010-050`
- `status`: `active`
- `base_strategy`: `none`
- Purpose: canonical default WORD acquisition strategy for practical breadth plus repeated successful recall.

## Applicability
Apply independently to each canonical headword resolved by the active PLAN subject. The strategy itself contains no vocabulary membership.

## Target Model
For each headword, select learning targets deterministically:

```text
meaning_tiers = core
phrase_tiers = core
phrase_status = active
```

Use each matching active/core PHRASES row linked to a core MEANINGS row as one `learning_target`. Cover relevant/common FORMS naturally through those targets and examples. Do not add rare, archaic, highly specialized, `common`, or `extended` targets solely to inflate coverage unless this strategy is explicitly overridden.

## Stages
`impression → acquisition`; no hard maintenance schedule is imposed here.

The normal WORDS explanation supplies the impression stage. Acquisition completes only when all in-scope learning targets pass both gates below.

## Content Readiness Gates
For every learning target:

```text
examples_per_learning_target = 10
```

Require at least 10 distinct natural useful EXAMPLES. Once enough suitable examples exist, do not create more solely for this strategy. Tests should collectively assess those contexts and relevant forms naturally; prefer at least one active test per credited example context where suitable. Form coverage is a constraint, not a multiplier.

## Learner Achievement Gates
For every learning target:

```text
correct_completions_per_learning_target = 50
minimum_correct_completions_per_example = 5
first_try_required = false
```

Counting rules:
- target: `HISTORY.test_id → TESTS.phrase_id`;
- example: `HISTORY.test_id → TESTS.example_id`;
- one finalized HISTORY row with `result` in `{correct, partial_corrected, incorrect_corrected}` = one completion;
- initially wrong/partial then correctly re-entered still counts once;
- require at least 50 total correct completions;
- require at least 10 distinct example contexts each with at least 5 correct completions;
- derive the 10 credited contexts from factual HISTORY/TESTS; do not persist a separate acquisition set;
- multiple TESTS rows for the same example may contribute, but vary test form where useful;
- never require every TESTS.id to be completed 50 times.

## Review / Maintenance Method
- `method`: `acquisition-only`
- `spacing_rule`: `distributed-preferred`
- `review_trigger`: `none`

Do not immediately repeat an already-correct example while eligible contexts have lower credited counts. Across later sessions, prefer lower-count and older successful contexts. This strategy does not impose a hard minimum number of sessions or calendar spacing.

## Priority Rules
1. recover recent mistakes;
2. fill missing content/test coverage;
3. practice examples with the lowest credited count;
4. cover relevant forms/contexts not yet represented naturally;
5. after all 10 contexts reach 5, add varied completions only if needed to reach 50;
6. vary test type/context before identical repetition.

## Stop / Completion Rules
A learning target completes when it has at least 10 suitable examples, at least 50 total credited correct completions, and at least 10 distinct contexts with at least 5 credited correct completions each. A headword completes this strategy when every in-scope learning target completes.

Completion means acquisition under this strategy, not permanent mastery.

## Overrides / Parameters
No default headword-specific overrides. Vocabulary selection belongs to the PLAN subject; reusable threshold variants should normally be separate STRATEGIES.
