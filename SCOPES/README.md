# Vocabulary Scopes Operating Manual

`SCOPE` answers **what reusable set of canonical headwords belongs together**.

A scope contains membership, not a learning method. It must not define example counts, correct-completion thresholds, spacing, grading, or learner history.

Examples:
- `business-core`
- `academic-core`
- `travel-basic`

A scope may contain one headword or many headwords, and it may declare canonical headword members before their WORDS CSV files are materialized; membership is not a command to pre-create content files. Ordinary `.headword` learning does not require creating a persistent one-word scope; the plan may use `active_headword` as a runtime singleton subject.

When a plan references a scope, resolve its canonical headwords, then apply the selected strategy.
