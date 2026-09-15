# Vocabulary Scopes Technical Specification

## 0. Purpose
`SCOPES` owns explicit reusable vocabulary-set membership.

## 1. Canonical folder
```text
English/SCOPES/
├── README.md
├── AGENTS.md
├── SCOPE-TEMPLATE.md
└── <scope_slug>/
    └── SCOPE.md
```

## 2. Naming
`scope_slug` is lowercase ASCII and matches `^[a-z0-9][a-z0-9_-]*$`.

## 3. SCOPE.md contract
Required concepts:
- identity (`scope_name`, `scope_slug`, `status`, purpose);
- membership rule;
- canonical headword members;
- optional notes/tags.

Default scope type is explicit/static membership. Members are canonical lexical headword strings, not inflected surface forms or WORDS row IDs. A scope member may be declared before its shared WORDS CSV file has been materialized; membership does not require pre-creating thousands of WORDS files. When execution reaches an unmaterialized member, resolve/validate the canonical headword and materialize WORDS content only when needed under normal WORDS write rules.

Do not duplicate FORMS/MEANINGS/PHRASES content inside a scope.

## 4. Membership
A scope must answer deterministically which canonical headwords belong to it. If a collection is defined by a changing filter such as “weak words today” or “due items”, that is a VIEW, not a SCOPE.

For large future sets, a separate indexed/CSV representation may be introduced only after documenting it here. Until then, Markdown membership is canonical.

## 5. Interaction
Scopes do not read/write learner HISTORY. PLANS may reference a scope and STRATEGIES may then operate over the resolved members.

## 6. Lifecycle/versioning
Canonical SCOPE status values are `draft`, `active`, and `retired`. `scope_slug` is immutable after activation. Routine membership curation that preserves the scope's declared meaning may update an active scope in place; a breaking redefinition of what the set means should create a new slug/version rather than silently repurpose the old one.
