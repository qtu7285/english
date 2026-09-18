# Vocabulary System Technical Specification

This file is the canonical technical/data specification for the vocabulary system under `WORDS`.
Tutor behavior and learning workflow live in `README.md`.

## 0. Rule boundary and read order

- `WORDS/README.md` is the small runtime router and is loaded only when a canonical-state boundary is reached. Stateless FAST_CORE learning may happen before any local-file read.
- `WORDS/TEST-WORKFLOW.md` owns test delivery, grading, learner-history read behavior, and temporary test evidence.
- `WORDS/SAVE-WORKFLOW.md` owns checkpoint preview and persistence orchestration.
- Read this `AGENTS.md` before any actual local schema/template/storage write, migration, file architecture change, or whenever deep technical conventions are needed.
- Normal stateless learning and normal read-only test delivery must not load AGENTS merely as a precaution.
- Do not duplicate tutoring/test/save workflow rules here unless they directly affect data storage.
- `README.md` = runtime router.
- `TEST-WORKFLOW.md` / `SAVE-WORKFLOW.md` = lazy operation runbooks.
- `AGENTS.md` = technical/data specification.
- When routing or tutoring behavior changes, update the owning README/workflow module.
- When schema, naming, storage, IDs/FKs, templates, or sync rules change, update `AGENTS.md`.

## 1. Root structure

```text
WORDS/
├── README.md
├── TEST-WORKFLOW.md
├── SAVE-WORKFLOW.md
├── AGENTS.md
├── WORDS-INDEX.csv
├── WORD-TEMPLATE.csv
├── USER-TEMPLATE.csv
├── urg/
│   └── urge/
│       ├── urge.csv
│       ├── urge-qtu.csv
│       └── urge-lan.csv
└── ...
```

- `WORDS` is the system root.
- `WORDS-INDEX.csv` = master headword registry for fast lookup.
- `WORD-TEMPLATE.csv` = Word Template.
- `USER-TEMPLATE.csv` = User Template.
- System-level assets use uppercase names.
- Headword folders/files use the exact lowercase headword.
- Columns use lowercase `snake_case`.
- Avoid spaces, slashes, accents, emoji, and unnecessary special characters in machine-facing names. Hyphens are allowed in system-level file names such as `WORDS-INDEX.csv`, `WORD-TEMPLATE.csv`, and `USER-TEMPLATE.csv`.

Sibling system boundary:

```text
English/
├── WORDS/       # vocabulary content + factual learner evidence
├── SCOPES/      # explicit reusable canonical-headword sets
├── VIEWS/       # dynamic filters/projections
├── STRATEGIES/  # reusable learning/review methods
└── PLANS/       # subject + strategy composition/execution policy
```

`SCOPES`, `VIEWS`, `STRATEGIES`, and `PLANS` are sibling systems, not subfolders of WORDS. SCOPES owns stable explicit membership; VIEWS owns dynamic selection; STRATEGIES owns learning/review methods and gates; PLANS binds a subject selector to a strategy plus optional execution policy. WORDS remains the source of truth for vocabulary content and actual learner events.

## 2. Headword storage

### CSV conventions

All persisted vocabulary data is local, UTF-8, comma-delimited CSV with a header row. CSV has no tabs, formulas, validation, or visual formatting. A shared headword bundle uses `<headword>.csv` for `FORMS` and companion files named `<headword>-MEANINGS.csv`, `<headword>-PHRASES.csv`, `<headword>-EXAMPLES.csv`, and `<headword>-TESTS.csv`. A learner bundle uses `<headword>-<username>.csv` for `HISTORY` and `<headword>-<username>-STATISTICS.csv` for `STATISTICS`. A workflow must read and write only the rows and columns required for its operation.


CSV text round-trip rules:

- Use a real CSV reader/writer (for example Python `csv.DictReader` / `csv.DictWriter` with UTF-8 and `newline=""`). Never parse records with `split(",")` or `splitlines()`, or construct rows by joining raw values with commas.
- The CSV delimiter is `,` and the quote character is `"`. The writer quotes fields containing commas, double quotes, or line breaks, and doubles embedded quotes. The reader restores the original field text. Do not manually pre-escape values before passing them to the writer, or unescape them again after reading.
- Preserve original punctuation, quotations, Unicode, and embedded line breaks. CSV wrapper quotes and doubled escape quotes are storage syntax, not learner-facing text. Literal repeated quotes in the decoded text must not be removed by a global replacement.
- Decode CSV first; only then interpret `|` alternatives and `;` blank separators inside `TESTS.correct_answer`. Never apply those splits to sentence, question, translation, or other free-text fields. CSV quoting does not escape the separate answer-list syntax.
- At an authorized content write, verify that reading the affected fields back yields the exact intended text, including commas and quotes. Tutoring display, clipboard, and speech use that decoded text as specified in TEST-WORKFLOW section 7.

Each headword is a folder, not a standalone file.

Path:

```text
WORDS/<first_3_chars>/<headword>/
```

Example:

```text
WORDS/urg/urge/
```

Inside each headword folder:

```text
<headword>.csv              # shared CSV export copied from WORD-TEMPLATE.csv
<headword>-<username>.csv # learner CSV export copied from USER-TEMPLATE.csv
<headword>-<username_2>.csv # another learner CSV export when needed
```

Example:

```text
WORDS/urg/urge/
├── urge.csv
├── urge-qtu.csv
└── urge-lan.csv
```

Do not create a `HISTORY/` subfolder for learner CSVs. Learner files are stored directly beside the shared headword CSV bundle.
Do not create separate headword files for inflections such as `urged`, `urging`, or `urges`.
Do not create separate files for collocations or phrases; store them in the shared headword CSV bundle.

### 2.1 WORDS-INDEX.csv master registry

Canonical file:

```text
WORDS/WORDS-INDEX.csv
```

Canonical local path:

```text
WORDS/WORDS-INDEX.csv
```

`WORDS-INDEX.csv` is a local UTF-8 CSV file used as the fast lookup registry for canonical headwords. It is a derived registry/cache, not the source of truth for vocabulary content. The shared per-headword CSV file remains the source of truth.

Index data rows:

```text
HEADWORDS
```

Canonical columns:

```text
headword | file_path | updated_at | test_count
```

Rules:

- one row represents one canonical headword;
- `headword` is the exact canonical lowercase headword;
- `file_path` is the relative CSV path of the shared `<headword>` CSV file, not the headword folder path and not a learner CSV path;
- use `file_path` for direct shared-file access after lookup; do not search the local tree by filename when a valid index row is available;
- `updated_at` is the UTC ISO 8601 timestamp with second precision (`YYYY-MM-DDTHH:MM:SSZ`) of the most recent successful write that changed the shared headword content; learner-only HISTORY/STATISTICS writes do not update it;
- `test_count` is the total number of non-empty canonical `TESTS.id` rows currently stored in that headword's shared CSV bundle;
- if active-only counts are needed later, add a separately named metric rather than silently changing the meaning of `test_count`;
- do not store `prefix` because it is derivable from the canonical headword;
- do not store learner CSV paths in `WORDS-INDEX.csv`; learner CSV files are resolved from the headword folder and canonical `<headword>-<username>.csv` naming convention;
- `WORDS-INDEX.csv` must be rebuildable from the actual local headword structure and shared CSV bundles; index corruption or a missing row must never be treated as deletion of the underlying vocabulary data.

Lookup and write order:

```text
input surface form
→ exact HEADWORDS lookup
→ if miss, canonical-headword resolution
→ HEADWORDS lookup again
→ direct open by file_path when found
```

When creating a new canonical headword:

```text
resolve canonical headword
→ confirm no canonical HEADWORDS row exists
→ create/verify headword folder and shared CSV bundle
→ only then add the WORDS-INDEX.csv row
```

Never add an index row before the shared headword CSV bundle exists and has been verified.

After a successful shared-content save, update that headword's `updated_at` and `test_count`. If the shared save succeeds but the index update fails, the shared CSV bundle remains authoritative; report the index as out of sync and repair/rebuild the index rather than rolling back or duplicating content.


#### 2.1.1 WORDS-INDEX.csv integrity and reconciliation

`WORDS-INDEX.csv` is a synchronized derived registry. The canonical shared headword CSV files and their local paths remain the source of truth. The system must be able to detect and repair registry drift without rewriting valid shared WORDS content merely to match the index.

Global integrity invariants:

- every materialized canonical headword under `WORDS/<prefix>/<headword>/` has exactly one `HEADWORDS` row;
- every non-empty `HEADWORDS` row resolves to exactly one materialized canonical shared `<headword>` CSV file;
- `HEADWORDS.headword` equals the canonical lowercase headword represented by that shared CSV bundle/folder;
- `HEADWORDS.file_path` equals that shared CSV bundle's current local path;
- `HEADWORDS.test_count` equals the current total of non-empty canonical `TESTS.id` rows in that shared CSV bundle;
- `HEADWORDS.updated_at` equals the timestamp of the most recent successful semantic shared-content write performed through the canonical workflow; it is not derived from learner writes or metadata-only file changes;
- duplicate rows for one canonical headword, duplicate ownership of one `file_path`, missing rows, stale `file_path`, orphan rows, and incorrect `test_count` are integrity errors and must not be silently tolerated.

Per-write verification:

```text
successful shared-content write
→ synchronize/create the HEADWORDS row
→ read back the affected INDEX row
→ verify headword + file_path + updated_at + test_count
→ only then treat INDEX synchronization as successful
```

If readback verification fails, the shared headword content remains authoritative and saved. Mark/report the index as out of sync and repair the registry; do not roll back or duplicate the shared content.

Global reconciliation:

```text
enumerate materialized canonical headword shared CSV bundles
+ read all non-empty HEADWORDS rows
→ compare both directions
→ classify missing / orphan / duplicate / stale / count-mismatch rows
→ repair WORDS-INDEX.csv from shared WORDS source truth
→ read back repaired rows and verify invariants
```

Reconciliation rules:

- repair the derived INDEX from shared WORDS; never mutate valid shared lexical content merely to make it agree with a stale INDEX row;
- when an INDEX row is missing for a verified materialized headword, add it using the actual shared CSV bundle `file_path`, actual `test_count`, and the best trustworthy canonical `updated_at` available from the shared-content workflow/audit evidence; do not fabricate a semantic-write timestamp from a learner-only or metadata-only modification;
- when an INDEX row points to a missing/wrong shared file, locate the canonical shared headword CSV file from the verified WORDS folder structure before repairing `file_path`;
- when duplicate INDEX rows exist for one headword, reconcile to exactly one canonical row after verifying which shared file is authoritative; do not delete/merge ambiguous duplicates by guesswork;
- an orphan INDEX row with no verified canonical shared CSV bundle must be treated as registry corruption/staleness and investigated before removal; absence from INDEX is never proof that WORDS content should be deleted;
- full reconciliation is required when integrity drift is detected, after a known partial INDEX-sync failure, after manual/bulk migrations that may bypass normal per-write sync, and before relying on INDEX for a large batch operation if there is evidence it may be stale;
- routine single-headword reads do not require a full-tree scan when the INDEX row passes normal lookup/readback checks; reconciliation is a consistency repair mechanism, not a mandatory expensive step on every tutoring turn.

A reconciliation implementation may optimize discovery/indexing later, but these invariants and source-of-truth direction are canonical.

### 2.2 Canonical headword resolution

The system uses a canonical-headword model: ordinary grammatical/inflectional forms normally belong to one base lexical headword rather than separate folders.

Default examples:

```text
learns   → learn
learned  → learn
learning → learn

urges   → urge
urged    → urge
urging   → urge
```

Resolution order:

1. Normalize the user's surface form for lookup without changing its linguistic meaning.
2. Check `WORDS-INDEX.csv/HEADWORDS` for an exact canonical-headword match first. Exact match wins.
3. If there is no exact match, use linguistic analysis/lemmatization to resolve the most likely canonical headword.
4. Check `WORDS-INDEX.csv/HEADWORDS` again using the resolved candidate.
5. If one clear canonical headword is supported, route to it automatically; do not ask the user merely because the supplied form was inflected.
6. If the surface form can reasonably be an independent lexical item as well as an inflection/derivation, use the user's sentence and learning context to decide.
7. If genuine lexical ambiguity remains and the decision would create a separate canonical headword/folder, ask the user before creating it.

Design principle:

```text
canonicalize aggressively
split conservatively
ask only on genuine lexical ambiguity
```

Examples such as `building`, `meeting`, `learning`, `left`, or `saw` can have independent lexical uses depending on context. Do not force them to a base lemma when an exact canonical headword already exists or when the context clearly targets the independent lexical item. Conversely, do not create a separate headword merely because an ordinary inflected form was supplied.

The shared headword CSV file's `FORMS` record group remains the authoritative place for morphological/grammatical forms encountered while learning that headword. `WORDS-INDEX.csv` does not duplicate a full alias/inflection table by default. Add a separate alias/override registry only if future observed routing errors justify that additional maintenance burden.

## 3. WORD-TEMPLATE.csv: shared word content

`WORD-TEMPLATE.csv` contains shared learning content and should be treated as the template for each headword content file.

Logical record groups:

```text
FORMS
MEANINGS
PHRASES
EXAMPLES
TESTS
```

User-specific progress must not be stored in WORD-TEMPLATE.csv-derived content files.

### 3.1 FORMS

Purpose: morphological/grammatical forms encountered while learning the headword.

Current columns:

```text
id | form | role | tag | note | created_at | created_by | updated_at | updated_by
```

Rules:

- `id` is the primary key.
- `form + role` may be treated as a logical uniqueness pair, but it is not the primary key.
- `FORMS.id` is the canonical form key referenced by `MEANINGS.form_id`, `PHRASES.form_id`, `EXAMPLES.form_id`, and `TESTS.form_id`.
- `form` is the surface form; `role` describes its grammatical/morphological role within the canonical headword.
- Keep separate FORMS rows when the same spelling has materially different grammatical roles that must be distinguished by downstream data.

### 3.2 MEANINGS

Current columns:

```text
id | form_id | pos | meaning | usage | tier | note | created_at | created_by | updated_at | updated_by
```

Rules:

- `id` is the primary key.
- `form_id` is a foreign key to `FORMS.id`.
- One row represents one distinct sense/use associated with a specific form of the canonical headword.
- Use the canonical/base form ID for meanings that are generic across the headword and not specific to another surface form.
- If a form carries a distinct nuance, grammaticalized meaning, or part-of-speech behavior, give that meaning its own row tied to the relevant `form_id`.
- `tier` is the machine-readable learning-priority classification defined in section 3.3.1.

### 3.3 PHRASES

Current columns:

```text
id | form_id | meaning_id | phrase | meaning | type | tier | words | note | status | created_at | created_by | updated_at | updated_by
```

Rules:

- `id` is the primary key.
- `form_id` is a foreign key to `FORMS.id` and identifies the form around which the phrase/collocation/structure is expressed.
- `meaning_id` is a foreign key to `MEANINGS.id`.
- `PHRASES.form_id` may differ from `MEANINGS.form_id` when the phrase uses a specific inflected/surface form while the linked meaning is generic/base-form meaning; this is valid when semantically consistent.
- `tier` is the machine-readable learning-priority classification defined below.
- `words` is the visible derived word-count helper for the phrase; repair/recompute it rather than treating it as semantic source data.
- `status` is content lifecycle state, not learner mastery. Canonical values are `active` and `archived`; only `active` rows are eligible for new normal learning/test selection unless a strategy explicitly says otherwise.

### 3.3.1 Learning tier classification

`MEANINGS.tier` and `PHRASES.tier` use the same canonical enum:

```text
core
common
extended
```

Semantics:

- `core` = practical high-value content required by the default WORD acquisition family;
- `common` = broadly useful content beyond the default minimum;
- `extended` = secondary, specialized, rare, or otherwise non-default expansion content.

Rules:

- use the enum values exactly; do not store free-text synonyms such as `basic`, `important`, `high-value`, or emoji in `tier`;
- a strategy must declare which tiers it selects instead of re-interpreting “basic/high-value” independently;
- the canonical default WORD target set is `PHRASES.status = active`, `PHRASES.tier = core`, with the linked `MEANINGS.tier = core`, unless the selected strategy explicitly defines another tier set;
- classification is shared lexical/content metadata, not learner mastery and not a plan/SRS state.

### 3.4 EXAMPLES

Current columns:

```text
id | form_id | phrase_id | sentence | vi_meaning | source | created_at | created_by | updated_at | updated_by
```

Rules:

- `id` is the primary key.
- `form_id` is a foreign key to `FORMS.id` and identifies the actual surface form of the target headword used in this sentence.
- `phrase_id` is a foreign key to `PHRASES.id`.
- `EXAMPLES.form_id` may differ from `PHRASES.form_id` when the sentence realizes the phrase with a different inflected form.
- Do not duplicate `meaning_id`; it is reachable through `phrase_id`.
- `source` uses canonical values `learning` or `test`; it describes why the example exists, not learner outcome.

Relationship:

```text
EXAMPLES.form_id → FORMS.id
EXAMPLES.phrase_id
→ PHRASES.id
→ PHRASES.meaning_id
→ MEANINGS.id
```

### 3.5 TESTS

Current columns:

```text
id | form_id | question | vi_context | correct_answer | phrase_id | example_id | test_type | status | created_at | created_by | updated_at | updated_by
```

Rules:

- `id` is the primary key for each distinct test item.
- `form_id` is a foreign key to `FORMS.id` and identifies the form of the canonical headword that this test intentionally targets.
- `phrase_id` identifies the phrase/structure being tested.
- `example_id` identifies the source example sentence.
- `example_id` is a foreign key to `EXAMPLES.id`.
- `phrase_id` is a foreign key to `PHRASES.id`.
- `TESTS.form_id` should reflect the intended tested form, not be copied mechanically from `EXAMPLES.form_id`; they are usually equal for direct fill-blank tests but may differ for rewrite/transformation tasks.
- One example may generate multiple tests by blanking different positions or using different test formats.
- The pair `phrase_id + example_id` identifies the learning content context, but does not replace `TESTS.id`.
- `status` uses canonical values `active` or `archived`; archived tests remain addressable for historical foreign keys but are not selected for new normal practice unless a strategy explicitly permits it.

`correct_answer` encoding:

- Store ordered complete answer alternatives separated by `|`; the first is the original target answer, and later entries are verified acceptable alternatives. A single answer needs no `|`.
- For `fb`, use `;` between the fills within each alternative, in blank order: `chief; concern | chief; priority`. Never use `|` to separate individual blanks or generate cross-products of unrelated alternatives. Each alternative must supply the same number of non-empty fills as the question has blanks.
- Trim surrounding delimiter whitespace and deduplicate equivalent alternatives while preserving the original first. Do not store empty alternatives. For other test types, each `|` entry is one complete answer in that type's normal format.
- The first alternative reconstructs the linked EXAMPLES sentence; later alternatives need not equal that sentence, but the tutor must verify their language/context before persistence. They do not repoint `phrase_id` or `example_id`. Original-target recall and alternative feedback follow TEST-WORKFLOW section 8.3.
- Adding alternatives is a semantic TESTS change, subject to section 3.8: retain historically referenced rows unchanged and create a replacement with a new ID when needed. Preserve old HISTORY references. The append-only save helper may create a replacement; archive the old test through the authorized workflow before future selection.

Example:

```text
p-03gvf4diacd3ax3fwv3knscat = phrase context
e-03gvf4diai4fko8mynvk237p2 = She resisted the urge to reply immediately.

t-03gvf4dian9re6bdxgqpll1fp → p-03gvf4diacd3ax3fwv3knscat + e-03gvf4diai4fko8mynvk237p2 → She ___ the ___ to reply immediately.
t-03gvf4diasvzxoeo3d1vt941e → p-03gvf4diacd3ax3fwv3knscat + e-03gvf4diai4fko8mynvk237p2 → She resisted the ___ to ___ immediately.
```

Form-aware example:

```text
f-03gvf3zfy9kmw6zhkgmi5h7xh = learn   / base
f-03gvf46h4b1vzwatg84cvafff = learned / past

m-03gvf3zfy9j4eopdvv8t70ms2.form_id = f-03gvf3zfy9kmw6zhkgmi5h7xh
p-03gvf3zfy9ou36ogn8o77xofj.form_id  = f-03gvf3zfy9kmw6zhkgmi5h7xh
e-03gvf3zfy9ogoau4z4b01hpws.form_id  = f-03gvf46h4b1vzwatg84cvafff   # She learned from her mistakes.
t-03gvf3zfy9klxa85gvnc65x76.form_id  = f-03gvf46h4b1vzwatg84cvafff   # She ___ from her mistakes.
```

This difference is valid: the meaning and canonical phrase can be base-form concepts while the example/test uses an inflected surface form.

### 3.6 Form-aware shared-schema migration

The canonical WORD-TEMPLATE.csv schema requires `form_id` in `MEANINGS`, `PHRASES`, `EXAMPLES`, and `TESTS`. Every non-empty data row in those logical record groups must have a valid `form_id` that references `FORMS.id`.

For an older shared headword CSV file encountered without these columns:

1. preserve all existing IDs, rows, headers, row order, UTF-8 encoding, and local path;
2. insert `form_id` immediately after `id` in each affected record group;
3. map each existing row to the most appropriate existing `FORMS.id`;
4. create a missing FORMS row only when required to represent the actual lexical/grammatical form;
5. do not invent a new canonical headword merely to satisfy the migration;
6. verify all foreign keys and row references after insertion before writing new learning data.

If an old row cannot be mapped to a form confidently, leave the migration unresolved for that row and ask for review rather than guessing.

The canonical schema also requires `tier` in `MEANINGS` (after `usage`) and `PHRASES` (after `type`). When an older shared CSV bundle lacks these columns, insert them in canonical position, preserve all IDs/FKs/content/formatting, and classify rows intentionally as `core`, `common`, or `extended`. Do not bulk-default every legacy row to `core` merely to satisfy the column requirement; unresolved classification may remain pending review until it can be assigned confidently.

### 3.7 Shared row audit metadata

Every non-empty mutable content row in `FORMS`, `MEANINGS`, `PHRASES`, `EXAMPLES`, and `TESTS` must end with the canonical audit block:

```text
created_at | created_by | updated_at | updated_by
```

Canonical rules:

- timestamps are UTC ISO 8601 text values with second precision, exactly `YYYY-MM-DDTHH:MM:SSZ`, for example `2026-09-15T09:30:41Z`;
- do not store date-only values in audit timestamp fields; hours, minutes, and seconds are required;
- `created_by` and `updated_by` store the canonical lowercase username without the runtime `#` prefix;
- a valid active username is therefore required before creating or modifying shared-content rows; do not substitute account display names, email addresses, AI product names, or guessed identities;
- when a row is first created, set `created_at = updated_at` and `created_by = updated_by`;
- after creation, `created_at` and `created_by` are immutable;
- when the row's stored content or lifecycle state changes, preserve creation metadata and replace only `updated_at` and `updated_by`;
- no-op normalizations or metadata-only changes, reads, and no-op saves do not by themselves count as a semantic row update and must not rewrite audit metadata;
- one successful save batch may use the same timestamp and username for every row created/updated by that batch;
- `WORDS-INDEX.csv.updated_at` remains a headword-level cache/sync timestamp and is separate from these row-level audit fields.

If an older shared headword CSV file lacks the audit block, migrate it in place: preserve existing content/IDs/FKs/headers/row order/UTF-8 encoding, append the four audit columns in canonical order, and populate trustworthy metadata when it can be established. Do not fabricate a historical creator or historical timestamp. If original provenance is unknown, leave the unknown historical field blank and set future `updated_at`/`updated_by` normally on the first verified edit.

### 3.8 Historical-reference immutability

Saved learner HISTORY must keep a stable interpretation over time. Once any finalized saved `HISTORY.test_id` references a TESTS row, the semantic relationship chain behind that event is protected.

Rules:

- do not rewrite in place the historically referenced TESTS semantic fields (`form_id`, `question`, `vi_context`, `correct_answer`, `phrase_id`, `example_id`, `test_type`);
- do not repoint or materially rewrite the linked EXAMPLES/PHRASES/MEANINGS/FORMS semantic identity in a way that would change what that past test meant; this includes changing a historically relevant `tier` classification that would change target membership;
- lifecycle-only changes such as `active → archived`, audit metadata, and genuinely non-semantic notes may still be updated;
- when a material correction or reclassification is required after historical use, archive/retain the old row and create a replacement row with a new canonical ID, then use the replacement for future tests;
- never repoint old HISTORY to the replacement merely to make history look current. Past facts must continue to resolve to the content identity that produced them.

This rule prioritizes historical lineage over in-place convenience.

## 4. Test type codes

`test_type` uses short 2-character codes for machine-friendly storage.

Canonical codes:

```text
fb = fill blank / fill blanks
mc = multiple choice
tf = true / false
rw = rewrite
```

Rules:

- Use `fb` for both one-blank and multi-blank exercises.
- Do not create separate codes for `fill_blank` and `fill_blanks`.
- The number of blanks is determined by the test content, not by `test_type`.
- New codes must be documented here before becoming canonical.

## 5. USER-TEMPLATE.csv: per-user learning data

`USER-TEMPLATE.csv` is the template for one learner's data for one headword.

Logical record groups:

```text
HISTORY
STATISTICS
```

A learner CSV is copied from USER-TEMPLATE.csv and stored directly inside the headword folder using the canonical filename:

```text
WORDS/<prefix>/<headword>/<headword>-<username>.csv
```

Example:

```text
WORDS/urg/urge/urge-qtu.csv
```

Each username gets a separate learner CSV for each headword. Do not mix multiple learners in the same learner CSV.

### 5.1 Username identity and filename

The current storage model uses `username` as the learner identifier.

Runtime command:

```text
#username
```

Storage path and filename:

```text
WORDS/<prefix>/<headword>/<headword>-<username>.csv
```

Rules:

- The leading `#` is a runtime command prefix only; never store it in the username or filename.
- Normalize the username to lowercase before storage.
- Canonical stored usernames must match `^[a-z0-9][a-z0-9_-]*$`.
- Do not silently transliterate, guess, or derive a username from display names, email addresses, or account metadata. If the supplied username does not satisfy the canonical format, ask the user for another username.
- A username is assumed to be unique within this `WORDS` dataset.
- The canonical learner CSVname is exactly `<headword>-<username>`, for example `urge-qtu`.
- The headword portion is the exact canonical lowercase headword used by the parent folder/shared file.
- The username portion is the canonical lowercase username without `#`.
- Do not parse learner identity by naively splitting the filename on `-`; canonical usernames may themselves contain hyphens. Resolve the known headword from the parent folder and the known active username from runtime state, then construct the filename.
- The `<headword>-<username>` convention is intentionally self-describing and search-friendly across local files. Searching `qtu` can find that learner's files across headwords; searching `urge` can find the shared file and learner CSVs for that headword.
- Do not add a `username` or `learner` column to HISTORY while one file belongs to exactly one username.
- If a future authenticated app provides an immutable `user_id`, the storage model may be migrated to separate `user_id` from mutable/display `username`; until then, username is the canonical learner identifier.

### 5.2 Runtime default learner configuration

The runtime/client may provide one default learner using:

```text
DEFAULT_USERNAME=minh
```

Technical rules:

- `DEFAULT_USERNAME` is runtime/client configuration, not learner-history data.
- Store only the canonical username value; do not include the runtime `#` prefix.
- The value must satisfy the same canonical username regex: `^[a-z0-9][a-z0-9_-]*$`.
- Do not write `DEFAULT_USERNAME` into shared headword CSV files, HISTORY rows, STATISTICS, or filenames as a separate field.
- At runtime, resolve learner identity in this order: explicit current-session `#username`, then `DEFAULT_USERNAME`, then unknown.
- A valid `#username` is a session override and must not silently mutate `DEFAULT_USERNAME`.
- The runtime configuration may be device-specific; it is not persisted in learner data or synchronized by this repository.
- A future custom app may implement a device-local default in local secure/app configuration, but it should still feed the same runtime `DEFAULT_USERNAME` concept and canonical username validation.
- If `DEFAULT_USERNAME` is missing or invalid, treat it as unavailable and require a valid runtime `#username` before learner-specific operations.

### 5.3 HISTORY

Current columns:

```text
id | created_at | test_id | answer | result | attempts | first_try | mistake_note | session_id
```

Rules:

- `id` is the primary key for each history event.
- `created_at` is the event creation time stored as UTC ISO 8601 text with second precision: `YYYY-MM-DDTHH:MM:SSZ`.
- `test_id` references the shared headword CSV bundle's `TESTS.id`.
- No `learner`, `username`, or `created_by` column is needed because the entire file belongs to one canonical username.
- HISTORY is append-only after a saved event is finalized; do not add `updated_at`/`updated_by` to normal history rows.
- `result` is machine-facing and uses exactly one of `correct`, `partial_corrected`, or `incorrect_corrected`; tutoring status symbols such as `[OK]`, `[~]`, `[X]`, or `[RETRY]` are presentation only and must not be stored in new canonical HISTORY rows.
- `correct` = the question was fully correct on the first evaluated attempt; `partial_corrected` = it was initially partial and later finalized fully correct without a fully incorrect attempt; `incorrect_corrected` = at least one fully incorrect attempt occurred before final correction. If both partial and incorrect attempts occurred, use `incorrect_corrected`.
- All three canonical `result` values represent one finalized fully-correct question completion for strategy counting; `first_try` and `attempts` preserve the quality/effort distinction. Normally `correct` has `first_try = TRUE`, while the two corrected values have `first_try = FALSE`.
- A linguistically valid alternative requiring original-answer re-entry is partial target recall under TEST-WORKFLOW 8.3. Store `partial_corrected` after the original is supplied (unless an incorrect attempt occurred), and explain the valid alternative plus recall requirement in `mistake_note`; do not invent a language error. Existing finalized HISTORY remains unchanged when this policy is introduced.
- Store attempts, mistakes, and session grouping here.
- `HISTORY.id` is also the idempotency key for saves: retrying a partial/multi-file checkpoint must not append another row with the same `id`.
- One runtime multi-headword session may reuse the same canonical `session_id` across different `<headword>-<username>` learner CSVs; `session_id` is a grouping key, not a per-file unique key.
- `last_practiced` in STATISTICS is derived from the greatest canonical UTC ISO `HISTORY.created_at`; because all timestamps use the same fixed UTC format, lexical descending order is chronological order.
- Do not add a vague `last_try` field unless a concrete storage requirement emerges. If individual attempts need to be stored, prefer a separate attempt-level model.

### 5.3.1 HISTORY result migration

When a legacy finalized HISTORY row uses display-oriented result text, migrate without changing the event ID, answer, attempts, `first_try`, mistake note, timestamp, test reference, or session grouping:

```text
[OK]    → correct
[~]→[OK] → partial_corrected
[X]→[OK] → incorrect_corrected
```

If a legacy row represents a non-final attempt or its path cannot be inferred safely, preserve it for review rather than guessing.

### 5.3.2 HISTORY timestamp migration

The canonical USER-TEMPLATE.csv uses `created_at`, not the legacy `date` field. When an older learner CSV is encountered:

1. preserve the HISTORY row IDs and all learner/test data;
2. rename `date` to `created_at`;
3. convert trustworthy legacy date/time values to canonical UTC ISO timestamps when the source precision is known;
4. do not invent missing historical time-of-day precision for date-only legacy rows; if only a date exists, preserve that legacy value until reviewed rather than fabricating hours/minutes/seconds;
5. update dependent derived STATISTICS fields such as `last_practiced` so they work with canonical ISO timestamp text.

### 5.4 STATISTICS

Current columns:

```text
metric | value
```

Typical metrics:

```text
tests_attempted
correct_first_try
mistakes
first_try_rate
total_attempts
last_practiced
```

Rules:

- STATISTICS is derived from that username's HISTORY.
- Learners are not represented as columns because each USER-TEMPLATE.csv-derived file belongs to exactly one username.
- STATISTICS does not use per-row `created_at`/`updated_at` audit fields because it is derived state and may be recomputed from HISTORY.

## 6. Core relationships

Shared content:

```text
FORMS.id
   ├──→ MEANINGS.form_id
   ├──→ PHRASES.form_id
   ├──→ EXAMPLES.form_id
   └──→ TESTS.form_id

MEANINGS.id
   ↓ meaning_id
PHRASES.id
   ↓ phrase_id
EXAMPLES.id
   ↓ example_id + phrase_id context
TESTS
```

Form semantics:

- `MEANINGS.form_id` = lexical/grammatical form whose sense/use is being described.
- `PHRASES.form_id` = form around which the phrase/collocation/structure is expressed.
- `EXAMPLES.form_id` = actual surface form of the target headword in the sentence.
- `TESTS.form_id` = form the test is intentionally assessing.
- These form IDs are related but are not required to be identical across a chain; differences are valid when caused by inflection or test transformation and must remain semantically coherent.

Per learner:

```text
TESTS.id
   ↓ test_id
HISTORY
   ↓ derived metrics
STATISTICS
```

## 7. Content vs user data

- Headword content is shared across learners.
- Learner history is private to that learner's file.
- Content files should be mostly read-only for the learning app.
- User history files are the normal write target during learning.
- Learner mastery/progress belongs in HISTORY/STATISTICS, not in content `status` columns.
- WORDS stores factual evidence about what actually happened; it does not own future curriculum/scheduling decisions.
- Do not add plan-specific fields such as `next_review_date`, `due_at`, `box_level`, `ease_factor`, `stability`, or `difficulty` to WORDS learner CSVs solely to support a current planning/SRS method. Such decisions belong to the sibling planning stack and should be recomputed from PLAN + referenced STRATEGY + resolved SCOPE/VIEW + WORDS evidence unless a sibling system later defines its own documented rebuildable cache/state.
- Plan completion is not a WORDS schema concept. Different plans may evaluate the same truthful HISTORY differently without rewriting past events.
- Because strategies may re-evaluate truthful HISTORY later, historically referenced shared content follows section 3.8 immutability; do not silently mutate the meaning of old evidence.

## 8. IDs and foreign keys

Naming convention:

- Primary key of its own entity: `id`
- Foreign/reference key: `<entity>_id`

Examples:

```text
FORMS.id
MEANINGS.form_id
PHRASES.form_id
PHRASES.meaning_id
EXAMPLES.form_id
EXAMPLES.phrase_id
TESTS.form_id
TESTS.phrase_id
TESTS.example_id
HISTORY.test_id
HISTORY.session_id
```

### 8.1 Canonical generated ID format

All new internal entity/session IDs generated by this system use:

```text
<entity_prefix>-<uuidv7_base36>
```

The UUID body is a complete RFC 9562 UUIDv7 value represented as a lowercase unsigned base36 integer and left-padded with `0` to exactly 25 characters. Base36 here is an encoding, not a hash: do not hash, truncate, or otherwise discard UUID bits.

Canonical shape:

```text
^[fmpeths]-[0-9a-z]{25}$
```

Examples:

```text
f-03gvf3zfy9kmw6zhkgmi5h7xh
m-03gvf3zfy9j4eopdvv8t70ms2
p-03gvf3zfy9ou36ogn8o77xofj
e-03gvf3zfy9ogoau4z4b01hpws
t-03gvf3zfy9klxa85gvnc65x76
h-03gvf42yja9hjs5az7xwe1nit
s-03gvf3yuurphp640pdldsp5me
```

Entity prefixes:

```text
f = FORMS row
m = MEANINGS row
p = PHRASES row
e = EXAMPLES row
t = TESTS row
h = HISTORY row/event
s = session grouping ID used by HISTORY.session_id
```

Rules:

- the hyphen is the single separator between the entity prefix and the 25-character body;
- generated IDs are lowercase strings and are globally unique identifiers for this `WORDS` dataset, not counters local to one CSV file or headword;
- foreign keys store the complete referenced ID including prefix and hyphen;
- `session_id` uses the `s-` format and may be reused across multiple HISTORY rows belonging to the same session grouping;
- `WORDS-INDEX.csv.file_path` is a validated local relative CSV path. It must not be replaced with an internal UUIDv7 value;
- usernames, headwords, timestamps, and semantic content must not be embedded into generated IDs;
- IDs are immutable after creation, stable across moves, Git history, and database migration, and must never be reused for another entity.

### 8.2 UUIDv7 → fixed-width base36 generation

Canonical generation procedure:

1. Generate a standards-compliant 128-bit UUIDv7 using a trusted UUIDv7 implementation with millisecond Unix time and appropriate random/monotonic bits.
2. Interpret the complete 128-bit UUID value as one unsigned integer.
3. Encode that integer in lowercase base36 using only `0-9a-z`.
4. Left-pad the result with `0` until the body is exactly 25 characters.
5. Prepend the entity prefix and one hyphen.

Do not:

- generate IDs from timestamp milliseconds alone;
- scan a CSV file for the previous/highest ID;
- use a shared sequential counter as the primary uniqueness mechanism;
- artificially increment the embedded timestamp by 1 ms merely to avoid a possible collision;
- truncate the UUIDv7 value to make the ID shorter;
- treat base36 encoding as cryptographic hashing.

UUIDv7 already combines time ordering with sufficient non-time bits for decentralized generation. If a library offers a standards-compliant monotonic UUIDv7 mode for multiple IDs generated within the same millisecond, it may be used. Do not assume exact creation order among independently generated IDs within the same millisecond unless the generator explicitly provides monotonic ordering.

Fixed-width base36 preserves the unsigned UUID numeric ordering inside the same entity prefix, so ordinary lexical sorting of IDs from one entity type follows UUIDv7's time-ordered structure. Audit/business time remains the explicit `created_at` field; do not require consumers to decode the ID to determine creation time.

A future database must still enforce a `PRIMARY KEY` or `UNIQUE` constraint on the stored ID. If an actual uniqueness conflict is ever detected, reject that candidate and generate a fresh UUIDv7; never mutate or reuse an existing row ID.

### 8.3 Legacy ID migration

Legacy identifiers such as `F001`, `M001`, `P001`, `E001`, `T001`, `H001`, or `S001` are not valid for newly generated rows after this convention becomes canonical.

Migration rules:

- new rows always use the canonical prefix + fixed-width UUIDv7-base36 format;
- do not automatically rewrite an already-saved legacy primary key merely for cosmetic conformity, because IDs are stable references;
- when an explicit legacy re-key migration is required, create a complete old-ID → new-ID mapping first, update every referencing foreign key atomically/consistently, verify referential integrity across shared and learner CSVs, and retain the migration mapping until verification is complete;
- `TESTS.id` migration must update every corresponding learner `HISTORY.test_id`;
- HISTORY `session_id` migration must preserve grouping: all rows that shared one legacy session ID must receive the same new `s-...` ID;
- never partially migrate a relationship chain and never generate a new ID for an existing row without updating all references;
- mixed legacy/new IDs may be temporarily accepted only when preserving pre-existing data that has not yet undergone an explicit safe re-key migration.


## 9. Naming convention

- System-level file/folder names may use uppercase hyphenated names, for example `WORDS-INDEX.csv`, `WORD-TEMPLATE.csv`, `USER-TEMPLATE.csv`, `TEST-WORKFLOW.md`, and `SAVE-WORKFLOW.md`.
- Headword folders/files use exact lowercase English headwords.
- Column/field names use lowercase `snake_case`.
- Learner files live directly inside each headword folder and use the canonical filename `<headword>-<username>`.
- Do not use hyphens in column/field names; hyphens remain allowed inside canonical usernames.

## 10. Legacy learner-file migration

The legacy layout used:

```text
WORDS/<prefix>/<headword>/HISTORY/<username>
```

When a legacy learner CSV is encountered, migrate it to the flat canonical layout:

```text
WORDS/<prefix>/<headword>/<headword>-<username>.csv
```

Migration rules:

- preserve the existing learner CSV local path when possible; move and rename the same file rather than copying data into a new file;
- preserve all CSV contents, IDs/FKs, headers, row order, and UTF-8 encoding, and metadata;
- verify the moved file before removing the old `HISTORY/` folder;
- remove an empty legacy `HISTORY/` folder only after confirming no learner CSVs remain inside;
- never overwrite an existing canonical `<headword>-<username>` file without first reconciling the two files;
- the legacy folder-layout migration itself does not alter learner CSV columns; apply any separately documented USER-TEMPLATE.csv schema migration (such as `HISTORY.date` → `HISTORY.created_at`) independently and preserve learner data while doing so.

## 11. Git and local-file guidance

The local repository is the only canonical store. Git records verified snapshots; it is not a second runtime data source.

Suggested persistence flow:

```text
write the required local CSV files
→ read back and verify the affected rows and index invariants
→ review `git diff`
→ stage only the verified files
→ create one focused Git commit
```

Rules:

- do not use cloud synchronization or remote file IDs as part of normal runtime lookup or persistence;
- do not create a commit before all files in a multi-file checkpoint have been written and verified;
- if a multi-file save partially fails, keep the successful local writes, preserve only unsaved events for retry, and use `HISTORY.id` to avoid duplicates before committing the repaired checkpoint;
- use `WORDS-INDEX.csv` as the normal canonical-headword lookup registry before traversing the local WORDS tree;
- shared-content writes must synchronize that headword's `WORDS-INDEX.csv.updated_at` and `test_count` after the shared CSV bundle write succeeds;
- after synchronizing a shared-write INDEX row, read the row back and verify `headword`, `file_path`, `updated_at`, and `test_count`; a write without successful readback verification is not a confirmed INDEX sync;
- apply the global WORDS-INDEX.csv reconciliation contract in section 2.1.1 whenever drift, a partial save, or manual/bulk migration makes registry completeness or correctness uncertain;
- shared mutable content rows carry canonical row-level audit metadata (`created_at`, `created_by`, `updated_at`, `updated_by`) as defined in section 3.7.

## 12. Runtime rule

`README.md` is the lightweight canonical runtime router, not a monolithic tutoring manual.
`TEST-WORKFLOW.md` and `SAVE-WORKFLOW.md` are lazy operation-specific runbooks.
`AGENTS.md` is the canonical technical/data specification and should be loaded only at an actual technical/write boundary, not on every tutoring/test turn.
Sibling `English/SCOPES`, `English/VIEWS`, `English/STRATEGIES`, and `English/PLANS` govern reusable sets, dynamic selection, learning methods, and plan composition respectively; none may override WORDS-owned data truth.
Application runtime logic should use matching constants/config in code rather than parsing every Markdown file on every run. The runtime router must choose the smallest authoritative next source. Runtime headword lookup should use the canonical `WORDS-INDEX.csv` `file_path` column and schema documented above. The runtime/client may supply `DEFAULT_USERNAME` as runtime configuration; this is separate from local learner data.

Normal optimization boundaries:

- stateless `.headword` learning: no local-file read;
- test/history: README router → TEST-WORKFLOW → only required PLAN/STRATEGY/shared/learner reads;
- checkpoint preview: SAVE-WORKFLOW from temporary state, no AGENTS yet;
- confirmed save or schema/storage change: load AGENTS, then only concrete target files/ranges.

When a convention changes:

1. update `README.md` if routing/boundary behavior changes;
2. update `TEST-WORKFLOW.md` or `SAVE-WORKFLOW.md` when that operation's behavior changes;
3. update `AGENTS.md` if technical/data conventions change;
4. update templates if the schema changes;
5. update app/script constants if runtime behavior changes.
