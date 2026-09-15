# Learning Views Operating Manual

`VIEW` answers **which items match a dynamic lens right now**.

Examples:
- weak words in `business-core`;
- words with recent mistakes;
- unfinished acquisition targets;
- words not practiced for 30 days.

A view is not a factual history and not a reusable static vocabulary set. A VIEW is strategy-independent: it may filter canonical facts/evidence/time (and optionally a SCOPE), but it must not ask “due under the currently selected strategy”. Strategy-specific due/review policy belongs to STRATEGY/PLAN execution.

A PLAN may use a VIEW as its subject selector. Resolve it once at SESSION start and keep that result as the stable runtime subject snapshot for the session. Recompute the VIEW for the next session; do not persist the snapshot as learner history or silently turn it into a SCOPE.
