# <View Name>

## Identity
- `view_name`: `<View Name>`
- `view_slug`: `<view_slug>`
- `status`: `draft`
- Purpose: <short purpose>

## Source
- `source_scope`: `<none-or-scope_slug>`
- `output_entity`: `headword`

## Filters
- <explicit predicate>

## Ordering
1. <sort/priority rule>

## Limit
- `max_items`: <none-or-number>

## Recompute Rule
Recompute from canonical WORDS/SCOPE/time sources at SESSION start; do not depend on the selected STRATEGY and do not persist the result as factual learner history.

## Session Snapshot Rule
Hold the resolved result stable for the current `session_id`; recompute on the next session.
