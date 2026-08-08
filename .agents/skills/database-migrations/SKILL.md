---
name: database-migrations
description: Manage the entire database schema lifecycle, including script generation, version tracking, file squashing, and lifecycle testing using SQLAlchemy and Alembic. Use whenever the database schema is modified, tables are created, migrations are required, or a user asks to update the database.
license: MIT
compatibility: product=codex product=claude-code system=alembic system=postgresql network=none
metadata:
  version: 1.2.0
---

# Database Migrations

## Objective
Manage, generate, and validate database schema migrations seamlessly while ensuring data integrity, absolute backward reversibility, and alignment with the repository's lifecycle release version.

## Initial Pre-flight Check
Before writing or executing any database schema modification:
1. Identify the authoritative SQLAlchemy models being altered.
2. Confirm that changes are driven purely via `alembic` migration scripts.
3. If `wiki/entities/` exists, invoke `/wiki-sync`'s pre-edit audit,
   scoped to the SQLAlchemy models and tables being altered — do not
   assume which entity this maps to; let `/wiki-sync` step 1 resolve
   it against `wiki/index.md`. This check is what enforces cross-store
   constraints — for example, whether a projection store may delete
   canonical source records — rather than restating them here as
   fixed prose that could silently drift from the entity page's
   actual, current invariant. If `wiki/entities/` does not exist,
   proceed without this check.

## Execution Workflow

### Step 1: Check Project Release Version & Select Strategy

Check the current project release version before modifying or generating
migration files. `pyproject.toml` under `[project].version` is authoritative;
if an active Git release tag ever disagrees with it, `pyproject.toml` wins —
active Git release tags are secondary, corroborating context only.

Apply this lifecycle policy:

* **Before 1.0:** migrations created for an active feature are mutable until
  that feature is merged or released. If the current feature already has an
  unapplied/unreleased branch migration representing its schema work, modify
  that migration instead of adding sequential corrective migrations. Do not
  rewrite migration baselines belonging to previously merged features merely to
  incorporate the current ticket. The squashed branch migration file must remain
  tracked and committed so schema state syncs across environments.
* **1.0 release preparation:** repository-wide squashing into the canonical
  initial schema is a deliberate release operation after intended 1.0 feature
  branches have landed. Validate a clean install and reset development/test
  databases as necessary.
* **After 1.0:** migration history is immutable. Never edit an applied or
  released migration; every schema change gets a new migration.

### Step 2: Identify the Target Migration File

Inspect the migration history and the active branch before editing schema
files:

```bash
uv run alembic heads
uv run alembic history
git status --short migrations/versions
git log --oneline -- migrations/versions
```

For pre-1.0 feature work, choose the current feature's existing branch
migration when one exists. If no active feature migration exists, create one
with Alembic. Do not create a second corrective branch migration only because
the first branch migration needs adjustment.

Autogenerate may be used as a scratch/diff aid, but do not blindly overwrite a
hand-maintained baseline: preserve explicit constraints, indexes, operation
ordering, comments, and downgrade logic. If force-overwriting is truly safer,
pass the existing revision ID intentionally and audit the result before keeping
it:

```bash
uv run alembic revision --autogenerate -m "initial_setup" --rev-id=<EXISTING_REVISION_ID>
```

### Step 3: Audit the Structural Code Blocks

Open the target migration file and verify that the syntax maps exactly to the
expected SQLAlchemy model state:

* Explicit column types match typed model structures.
* Foreign keys specify intended cascade behavior.
* Check constraints enforce canonical enums and JSON object/array shapes.
* Indexes cover expected high-churn lookups.
* `downgrade()` removes objects in safe reverse dependency order.

### Step 4: Inspect and Apply the Target Database

Use the standard runtime environment variables and `uv` tooling. If
`POLARIS_DATABASE_URL` is not exported but `.env` contains the canonical
PostgreSQL parts, load `.env` for local execution without printing secrets:

```bash
set -a; source .env; set +a; uv run alembic heads
set -a; source .env; set +a; uv run alembic current
set -a; source .env; set +a; uv run alembic upgrade head
set -a; source .env; set +a; uv run alembic check
set -a; source .env; set +a; uv run polaris inspect persistence
```

`alembic current` verifies only the stored revision stamp. Always run
`alembic check` after applying migrations so the physical database schema is
compared against SQLAlchemy metadata. In Polaris, also run
`polaris inspect persistence` when a local PostgreSQL database is available; its
`alembic_schema_drift` check exposes the same drift through the canonical
application diagnostics boundary.

If a DB-backed integration test needs `POLARIS_TEST_DATABASE_URL` and it is not
pre-exported, derive it from the same `.env` PostgreSQL settings,
`.env.example`, `docker-compose.yml`, test fixtures, or the project's
`PostgresSettings` environment contract instead of skipping solely because the
variable was absent. Prefer an isolated test database or schema for
migration-contract tests. Never echo full connection strings or secrets.

If the derived local database depends on a Docker service and repository rules
authorize service management, start only the required service, for example
`docker compose up -d postgres`, before rerunning the exact targeted migration
or DB-backed integration test. If local env or services cannot be safely
resolved, report database verification as unresolved or owner-deferred; do not
count the skip as a pass.

### Step 5: Handle Stale or Squashed Local Revisions

If `alembic current` fails because the database is stamped with a revision that
no longer exists in the branch, inspect Git history to determine whether that
revision was squashed into an active feature migration. Do not blindly run
`alembic stamp head`; stamping can hide missing tables, constraints, indexes, or
other operations from the edited squashed migration.

* For disposable local development/test databases, reset or recreate the local
  database/schema, then run `uv run alembic upgrade head` from the current repo
  state. When the repository provides a guarded local reset helper, prefer it
  over hand-written destructive SQL; for Polaris, use
  `uv run python scripts/reset_local_postgres_schema.py --confirm-destroy-local-db`.
  Confirm afterward with `uv run alembic check` and
  `uv run polaris inspect persistence`.
* For data-preserving environments, stop and create an explicit remediation plan
  that compares actual schema state with the current migration head before any
  stamping or manual DDL.

### Step 6: Run the UP / DOWN Lifecycle Validation

Execute a full round-trip validation matrix for migration changes:

1. Apply upgrade: `uv run alembic upgrade head`.
2. Verify metadata parity: `uv run alembic check`.
3. Verify canonical diagnostics, when a local PostgreSQL database is available:
   `uv run polaris inspect persistence`.
4. Verify state: inspect tables, columns, constraints, and indexes relevant to
   the change.
5. Apply downgrade by exactly one relevant step or against an isolated migration
   test schema: `uv run alembic downgrade -1`.
6. Re-upgrade to the final intended state: `uv run alembic upgrade head`.
7. Re-run `uv run alembic check` after the final upgrade.
8. Run targeted migration-contract and PostgreSQL integration tests with a real
   env-derived database URL; do not count a skipped DB test as passing database
   verification.

### Step 7: Entity Wiki Sync

If `wiki/entities/` exists and this migration altered a structural
boundary or invariant — a new cross-store constraint, a changed
contract, a boundary moving — apply `/wiki-sync` step 6 to update
whichever entity page the Initial Pre-flight Check's `/wiki-sync`
audit (item 3) identified as covering the altered models or tables.
If invoked from within `/implement-ticket`, stage this alongside that
skill's own entity wiki guard rather than committing separately, per
`/wiki-sync`'s guidance for calling skills.

## Examples

### Example 1: Creating a Table Modification Plan (Pre-1.0.0)
**User:** "Add an active flag to the user accounts table."
**Agent Action:**
1. Checks `pyproject.toml` and detects version `0.4.2`.
2. Inspects git status and logs to find the current unmerged branch baseline file.
3. Appends `sa.Column('active', sa.Boolean(), default=True)` straight into the existing local migration block instead of spawning a new sequential version file.
4. Executes `uv run alembic upgrade head` followed by `uv run alembic downgrade -1` to validate the round-trip code integrity.
