---
name: database-migrations
description: Manage, generate, apply, and validate PostgreSQL schema migrations using SQLAlchemy and Alembic. Owns the repository migration lifecycle policy, pre-1.0 branch-baseline strategy, migration selection and squashing, local database application and stale-revision recovery, upgrade/downgrade validation, targeted database-backed verification, and applicable Living Entity Wiki synchronization.
compatibility: product=codex product=claude-code system=python system=git network=none
---

# Database Migrations

## Objective

Manage, generate, apply, and validate database schema migrations while ensuring:

* alignment between authoritative SQLAlchemy models and PostgreSQL schema;
* data integrity;
* a validated upgrade/downgrade/re-upgrade migration path;
* explicit treatment of destructive or data-loss operations;
* compliance with the repository's release-version migration policy;
* synchronization with the Living Entity Wiki when database changes affect durable architectural knowledge.

A successful `downgrade()` proves that the **schema transition** can be reversed as designed.

It does not imply that data destroyed by an irreversible operation can be reconstructed.

Never describe destructive data loss as "fully reversible" unless an explicit restoration mechanism actually exists and is verified.
---

## Initial Pre-Flight Check

Before writing or executing any database schema modification:

1. Identify the authoritative SQLAlchemy models and durable persistence contracts being altered.

2. Determine the intended schema effect:

   * table creation/removal;
   * column changes;
   * constraints;
   * indexes;
   * relationships;
   * persistence serialization;
   * canonical-record behavior.

3. Confirm that PostgreSQL schema evolution is represented through Alembic migrations.

   Do not perform application-owned schema changes through ad hoc runtime DDL.

4. If the Living Entity Wiki exists, invoke `$wiki-sync` **before editing source code or migration files**.

   Do not guess which entity owns the affected persistence concern.

   `$wiki-sync` owns:

   * routing through `wiki/index.md`;
   * resolving the relevant entity or entities;
   * evaluating `[source-conflict]`;
   * checking applicable Strict Invariants;
   * checking relevant Rejected Approaches;
   * identifying accepted decisions whose implementation may be pending.

5. If `$wiki-sync` surfaces a blocking condition, stop before modifying files.

   Blocking conditions may include:

   * `[source-conflict]`;
   * the proposed schema approach violating a Strict Invariant;
   * retrying a Rejected Approach whose reasoning still applies;
   * unresolved entity ownership or architectural ambiguity requiring owner judgment.

Do not restate persistence architecture rules here merely to avoid consulting the wiki.

For example, whether a projection store may delete canonical PostgreSQL records belongs to the authoritative architecture sources and derived entity knowledge, not duplicated prose inside this skill.

If the Living Entity Wiki has not yet been bootstrapped, proceed without the wiki audit.

---

# Execution Workflow

## Step 1: Check Project Release Version and Select Strategy

Before modifying or generating migration files, inspect:

```text
pyproject.toml
```

The `[project].version` value is authoritative for repository migration lifecycle.

An active Git release tag may provide corroborating context, but if it disagrees with `pyproject.toml`, use `pyproject.toml`.

Apply this policy.

### Before 1.0

Migrations created for an **active feature branch** remain mutable until that feature is merged or released.

Use the **branch-baseline policy**:

* if the current feature already has an unreleased migration representing its schema work, edit that migration;
* do not create sequential corrective migrations merely because the active branch migration needs adjustment;
* do not rewrite migration baselines belonging to previously merged features merely to absorb current feature work;
* keep the current feature migration tracked and committed so its schema state propagates across environments.

The goal is:

```text
one coherent migration for the active feature
```

not:

```text
initial feature migration
→ correction
→ correction of correction
→ cleanup
```

### 1.0 Release Preparation

Repository-wide squashing into the canonical initial schema is a deliberate release operation.

Perform it only after the intended 1.0 feature branches have landed.

Validate:

* clean database creation;
* Alembic metadata parity;
* targeted PostgreSQL-backed integration behavior.

Reset disposable development/test databases where necessary.

Do not casually apply repository-wide squashing during ordinary feature work.

### After 1.0

Migration history is immutable.

Never edit an applied or released migration.

Every schema change receives a new migration.

---

## Step 2: Identify the Target Migration File

Inspect migration history and branch state before editing schema files:

```bash
uv run alembic heads
uv run alembic history
git status --short migrations/versions
git log --oneline -- migrations/versions
```

For pre-1.0 feature work, determine whether the current feature already owns an active branch migration.

### Existing active branch migration

Modify that migration.

Do not create a second migration solely because the original branch migration needs correction.

### No active branch migration

Create one through Alembic.

Example:

```bash
uv run alembic revision --autogenerate -m "<feature description>"
```

Autogenerate is a **diff aid**, not architectural authority.

Audit generated operations before keeping them.

Do not blindly overwrite hand-maintained migration content.

Preserve intentional:

* constraints;
* indexes;
* operation ordering;
* comments;
* downgrade logic;
* PostgreSQL-specific semantics.

If intentionally regenerating a mutable pre-1.0 branch revision using the same revision ID is genuinely safer:

```bash
uv run alembic revision \
  --autogenerate \
  -m "<feature description>" \
  --rev-id=<EXISTING_REVISION_ID>
```

review the complete diff before accepting it.

Do not use this technique for immutable released migrations.

---

## Step 3: Audit SQLAlchemy and Migration Structure

Compare the authoritative model state with the target migration.

Verify:

### Columns

* SQLAlchemy/Alembic types match the typed model.
* Nullability is intentional.
* defaults and server defaults are intentional and distinguished correctly.
* canonical fields are represented explicitly rather than buried in arbitrary metadata.

### Relationships and Foreign Keys

Verify:

* target tables/columns;
* uniqueness where required;
* intended cascade semantics;
* safe dependency ordering.

### Constraints

Verify relevant:

* check constraints;
* unique constraints;
* enum/domain restrictions;
* JSON object/array requirements;
* canonical-record constraints.

### Indexes

Ensure indexes exist for intended high-value lookup patterns.

Do not add speculative indexes merely because a column is queried somewhere.

### `upgrade()`

Confirm operations are ordered according to dependency requirements.

### `downgrade()`

Confirm schema objects are removed or restored in safe reverse dependency order.

For destructive data operations, explicitly document what cannot be reconstructed.

Do not claim a downgrade restores lost data unless it actually does.

---

## Step 4: Inspect and Apply the Target Database

Use repository-standard environment variables and `uv`.

Never print secrets.

If `POLARIS_DATABASE_URL` is not exported but `.env` contains the canonical local PostgreSQL configuration, load it without echoing values:

```bash
set -a; source .env; set +a; uv run alembic heads
set -a; source .env; set +a; uv run alembic current
set -a; source .env; set +a; uv run alembic upgrade head
set -a; source .env; set +a; uv run alembic check
set -a; source .env; set +a; uv run polaris inspect persistence
```

### `alembic current`

Confirms the database's recorded revision state.

It does **not** prove physical schema parity.

### `alembic check`

Run after applying migrations.

It compares database/model migration expectations and must not be replaced by checking the revision stamp alone.

### Polaris persistence inspection

When a local PostgreSQL database is available, also run:

```bash
uv run polaris inspect persistence
```

Its persistence diagnostics provide the canonical application-level view of schema drift and datastore health.

---

## Test Database Configuration

If a targeted DB-backed test requires:

```text
POLARIS_TEST_DATABASE_URL
```

and it is not already exported, derive safe local test configuration from repository-owned sources such as:

* `.env`;
* `.env.example`;
* `docker-compose.yml`;
* test fixtures;
* `PostgresSettings`;
* other established configuration contracts.

Prefer:

* an isolated test database; or
* an isolated test schema

for destructive migration-contract validation.

Never echo full connection strings or credentials.

Do not count a DB-backed test as passed merely because it skipped for missing environment configuration.

---

## Local Docker Services

If the required local PostgreSQL service is not running and repository policy authorizes service management, start only the required service.

Example:

```bash
docker compose up -d postgres
```

Do not start unrelated services merely because they exist in the compose file.

If safe local configuration or services cannot be resolved:

```text
database verification: unresolved
```

or:

```text
database verification: owner-deferred
```

Do not report the skipped verification as passing.

---

## Step 5: Handle Stale or Squashed Local Revisions

A pre-1.0 branch migration may be rewritten while a disposable local database remains stamped with the old revision.

If:

```bash
uv run alembic current
```

references a revision that no longer exists, first inspect Git history and branch migration history.

Determine whether the missing revision was intentionally squashed into the current feature baseline.

Do **not** blindly run:

```bash
uv run alembic stamp head
```

Stamping changes revision metadata without proving the database actually contains:

* tables;
* columns;
* constraints;
* indexes;
* migration-side transformations

required by the current migration graph.

---

### Disposable Local Development/Test Database

Prefer recreating the schema/database from the current migration history.

When Polaris provides its guarded reset helper, use:

```bash
uv run python scripts/reset_local_postgres_schema.py --confirm-destroy-local-db
```

Then run:

```bash
uv run alembic upgrade head
uv run alembic check
uv run polaris inspect persistence
```

Use destructive reset operations only for environments confirmed to be disposable.

---

### Data-Preserving Environment

Stop.

Do not reset, stamp, or issue corrective manual DDL casually.

Produce an explicit remediation plan that compares:

```text
actual database state
vs.
current migration history
vs.
authoritative SQLAlchemy metadata
```

before performing any mutation.

---

## Step 6: Run the Upgrade / Downgrade / Re-Upgrade Validation

For a migration changed by the current work, validate the complete relevant lifecycle.

### 1. Upgrade

```bash
uv run alembic upgrade head
```

### 2. Metadata parity

```bash
uv run alembic check
```

### 3. Canonical persistence diagnostics

When PostgreSQL is available:

```bash
uv run polaris inspect persistence
```

### 4. Inspect affected schema state

Verify the relevant:

* tables;
* columns;
* foreign keys;
* constraints;
* indexes;
* defaults;
* PostgreSQL-specific behavior.

### 5. Downgrade

Against a disposable or isolated migration-test database/schema:

```bash
uv run alembic downgrade -1
```

Use the downgrade target that actually exercises the migration under test.

Do not destructively downgrade a data-preserving environment merely to satisfy this workflow.

### 6. Verify downgraded state

Check that the schema reflects the intended prior state.

If the migration destroys data that cannot be restored, state that explicitly.

### 7. Re-upgrade

```bash
uv run alembic upgrade head
```

### 8. Re-check parity

```bash
uv run alembic check
```

### 9. Re-run persistence diagnostics

When available:

```bash
uv run polaris inspect persistence
```

### 10. Targeted migration and integration tests

Run targeted migration-contract and PostgreSQL-backed integration tests.

Use a real, safely derived database URL.

A skipped DB-backed test caused solely by missing local configuration is **unresolved verification**, not a pass.

---

## Step 7: Post-Change `$wiki-sync`

If the Living Entity Wiki exists, invoke `$wiki-sync` after the database implementation and migration work is complete.

Do this for every substantive database source-code change.

Do not first decide whether the change was "architectural enough."

`$wiki-sync` owns that determination.

It must evaluate whether the completed work:

* changed or established a Strict Invariant;
* realized an accepted decision previously marked `accepted, implementation pending`;
* established a qualifying Rejected Approach;
* surfaced or resolved an Open Question;
* changed entity topology or Boundary Rationale;
* produced no durable entity knowledge.

Examples of changes that may produce durable wiki knowledge include:

* changing the canonical writer for a durable concept;
* introducing or removing a cross-store authority boundary;
* changing projection rebuild semantics;
* establishing a durable persistence ownership constraint;
* realizing an accepted persistence ADR;
* moving responsibility between persistence entities.

Ordinary schema implementation details do not automatically deserve wiki entries.

Examples that normally remain implementation-only:

* adding a routine index;
* adding a straightforward column;
* adjusting an internal constraint with no architectural meaning;
* modifying a branch migration to match an already-established invariant.

Let `$wiki-sync` decide based on the actual sources and entity knowledge.

---

## Wiki Mutation Commit Ownership

If this skill is invoked by `$implement-ticket`:

* do not create a standalone wiki commit;
* stage any substantive entity/index change;
* stage its matching `wiki/log.md` semantic entry;
* allow `$implement-ticket` to include them in the ticket commit.

If `$wiki-sync` determines no durable wiki knowledge changed:

* do not modify `wiki/log.md`;
* do not create a wiki-only commit.

If `$database-migrations` is invoked independently, follow `$wiki-sync`'s normal commit-ownership guidance for the surrounding workflow.

---

# Verification Failure Rules

The migration work is not complete when:

* `alembic upgrade` fails;
* `alembic check` reports drift;
* the migration cannot cleanly re-upgrade after a valid downgrade test;
* required constraints/indexes are absent;
* targeted migration-contract tests fail;
* required PostgreSQL-backed tests skip only because local configuration was not prepared;
* the database remains on a stale removed revision;
* `[source-conflict]` remains unresolved;
* required `$wiki-sync` post-change evaluation has not completed.

Do not commit/push/close a calling ticket as successfully verified while one of these required checks remains unresolved.

---

# Examples

## Example 1: Add a Column Before 1.0

**User:** "Add an active flag to user accounts."

### Action

1. Read `pyproject.toml`; version is `0.4.2`.
2. Invoke pre-change `$wiki-sync`.
3. Inspect Git/Alembic history and find the current feature's mutable branch migration.
4. Update the authoritative SQLAlchemy model.
5. Modify the existing feature migration rather than adding a sequential corrective migration.
6. Verify:

   * upgrade;
   * schema state;
   * `alembic check`;
   * downgrade in a disposable test environment;
   * re-upgrade;
   * targeted DB-backed tests.
7. Invoke post-change `$wiki-sync`.
8. If the column has no durable architectural consequence, no entity mutation is required.

---

## Example 2: Implement an Accepted Persistence Decision

An accepted ADR establishes a new durable persistence ownership boundary but implementation has remained pending.

### Action

1. Pre-change `$wiki-sync` identifies the relevant entity and the Planned entry:
   `accepted, implementation pending`.
2. Implement the SQLAlchemy/repository/schema changes.
3. Update the current feature's pre-1.0 branch migration.
4. Run full targeted migration lifecycle verification.
5. Post-change `$wiki-sync` verifies realization.
6. The accepted-pending Planned entry is removed.
7. The resulting active constraint becomes a Strict Invariant citing the accepted ADR.
8. If invoked through `$implement-ticket`, the entity change and semantic `wiki/log.md` entry land in the ticket commit.

---

## Example 3: Stale Squashed Local Revision

The current branch rewrote an unreleased feature migration, but the local disposable database is stamped with the removed revision.

### Action

1. Confirm through Git history that the old revision belonged to the current unreleased feature.
2. Do not `stamp head`.
3. Reset the disposable local database through:

```bash
uv run python scripts/reset_local_postgres_schema.py --confirm-destroy-local-db
```

4. Run:

```bash
uv run alembic upgrade head
uv run alembic check
uv run polaris inspect persistence
```

5. Run the targeted PostgreSQL-backed migration/integration tests.
6. Report the rebuilt local state and verification result.

---

# Out of Scope

`$database-migrations` does not:

* define persistence architecture independently of accepted ADRs/current docs;
* duplicate entity invariants as fixed migration-policy prose;
* resolve `[source-conflict]`;
* create or change ADR lifecycle — use `$to-adr-doc`;
* classify non-ADR documentation — use `$to-doc` or `$classify-doc`;
* manually update entity pages outside `$wiki-sync`;
* treat Alembic autogeneration as architectural authority;
* guarantee restoration of data that a destructive migration permanently removed;
* broaden targeted verification beyond the calling workflow's authorization.

Its responsibility is to keep the authoritative SQLAlchemy model, Alembic migration history, physical PostgreSQL schema, targeted database verification, and applicable Living Entity Wiki lifecycle in a coherent state.
