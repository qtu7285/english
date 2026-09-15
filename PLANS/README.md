# Learning Plans Operating Manual

This file is the canonical operating manual for `English/PLANS`.

## 0. Core model

A PLAN is a composition, not a learning algorithm by itself.

```text
subject selector + strategy + optional schedule/priority/overrides = PLAN
PLAN + learner + current WORDS evidence + current time = SESSION
```

System responsibilities:

```text
WORDS      = knowledge + factual learner evidence
SCOPES     = explicit reusable headword sets
VIEWS      = dynamic projections/filters
STRATEGIES = reusable learning/review methods
PLANS      = compositions that bind WHAT to HOW
SESSION    = one runtime execution; not a persistent root system by default
```

## 1. Subject selectors
A plan must resolve exactly one effective subject through one of:
- `active_headword`: runtime singleton from `.headword`;
- `headword`: one explicit canonical headword;
- `scope`: reusable explicit set from SCOPES;
- `view`: dynamic result from VIEWS.

The result is the effective runtime headword set for the session.

## 2. Strategy binding
A plan references one canonical STRATEGY by `strategy_ref`. The strategy defines method/gates; the plan must not copy the whole strategy body.

Plan-level overrides are allowed when exceptional and explicit. If the same method variant will be reused, create a separate STRATEGY instead.

## 3. Default `.headword` plan
Ordinary `.headword`, e.g. `.urge`, activates the canonical plan:

```text
PLANS/default-headword/PLAN.md
```

It resolves:

```text
subject_mode = active_headword
strategy_ref = word-010-050
```

So `.urge` means: singleton subject `[urge]` + strategy `WORD-010-050` → runtime session.

## 4. Read order
For plan-based study:
1. ensure `WORDS/README.md` is loaded;
2. read this `PLANS/README.md`;
3. read the selected `PLAN.md`;
4. resolve its subject:
   - active/headword directly through WORDS canonical resolution;
   - scope through `SCOPES/README.md` + selected `SCOPE.md`;
   - view through `VIEWS/README.md` + selected `VIEW.md` and any referenced scope;
5. read `STRATEGIES/README.md` + selected `STRATEGY.md`;
6. read relevant WORDS content and learner evidence;
7. compute the runtime SESSION decision;
8. execute tutoring/testing with WORDS rules;
9. save only actual finalized WORDS facts.

For technical changes, read the relevant sibling AGENTS files before writing.

## 5. Session semantics
A SESSION is the runtime realization of a plan for one learner at one time. At session start, resolve the effective headword set once; a VIEW subject therefore becomes a stable runtime snapshot for that `session_id`.

Use one `session_id` across all headword learner files touched by that session. Runtime strategy decisions read persisted HISTORY plus finalized-but-unsaved events already completed in the current session. Automatic plan progression between headwords is not an explicit `.headword` command and does not by itself force a checkpoint.

If a checkpoint spans multiple learner files and only some writes succeed, keep those successful writes and retry only missing `HISTORY.id` events; never duplicate already-saved rows.

By default there is no `English/SESSIONS` persistence layer. Actual learner events are already grouped by WORDS `HISTORY.session_id`. If future requirements need session metadata beyond HISTORY, define a dedicated system only after documenting its schema and source-of-truth boundary.

## 6. Views vs scopes
- SCOPE = stable explicit membership.
- VIEW = dynamic strategy-independent lens whose result may change between sessions with evidence/time; its result is snapshotted for one active session.
- PLAN may use either.
- VIEW results are not automatically persisted as SCOPE membership.

## 7. Evidence boundary
Past facts stay in WORDS. Future decisions are computed from PLAN + STRATEGY + subject resolution + current WORDS evidence.


## 8. Stable plan identity

Once a PLAN is active, do not silently change the meaning of its slug. Breaking subject/strategy/schedule/override/completion changes require a new plan slug/version; retire the old plan when appropriate rather than repurposing it.
