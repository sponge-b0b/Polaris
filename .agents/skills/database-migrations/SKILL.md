---

name: database-migrations
description: Manage, generate, apply, and validate PostgreSQL schema migrations using SQLAlchemy and Alembic, including the pre-1.0 branch-baseline policy and targeted database verification.
compatibility: product=codex product=claude-code system=python system=git network=none
--------------------------------------------------------------------------------------

# Database Migrations

## Objective

Manage and validate database schema migrations while preserving data integrity, verifying upgrade/downgrade behavior, and following the repository's release-version migration policy.

A valid `downgrade()` proves the intended **schema transition** is reversible. Do not claim destroyed data is recoverable unless an explicit restoration mechanism exists and is verified.

## Pre-flight

Before modifying database-affecting code:

1. Identify the authoritative SQLAlchemy models and persistence contracts being changed.
2. Confirm schema evolution is represented through Alembic migrations rather than ad hoc runtime DDL.
3. If the Living Entity Wiki exists, invoke `$wiki-sync` before editing. Let it resolve the affected entity and applicable architectural constraints from `wiki/index.md`; do not duplicate those invariants here.
4. Halt on any blocking `$wiki-sync` finding such as `[source-conflict]` or violation of an active invariant.

## 1. Select the Migration Strategy

Read `[project].version` from `pyproject.toml`. It is authoritative for migration lifecycle; Git tags are corroborating context only.

### Before 1.0

Use the **branch-baseline policy**:

* migrations for the current active feature remain mutable until that feature is merged or released;
* if the feature already has an unreleased branch migration, edit it instead of adding sequential corrective migrations;
* do not rewrite migration baselines belonging to previously merged features;
* keep the active migration tracked and committed.

### 1.0 release preparation

Repository-wide squashing into the canonical initial schema is a deliberate release operation after intended 1.0 feature branches have landed.

Validate a clean install and reset disposable development/test databases as necessary.

### After 1.0

Migration history is immutable.

Never edit an applied or released migration. Every schema change receives a new migration.

## 2. Select the Target Migration

Inspect current history before editing:

```bash
uv run alembic heads
uv run alembic history
git status --short migrations/versions
git log --oneline -- migrations/versions
```

Before 1.0:

* modify the current feature's existing branch migration when one exists;
* otherwise create a new migration with Alembic.

Autogenerate may be used as a diff aid, but do not blindly replace hand-maintained migration logic. Preserve intentional constraints, indexes, operation ordering, comments, and downgrade behavior.

If intentionally regenerating a mutable revision with its existing revision ID:

```bash
uv run alembic revision --autogenerate -m "<description>" --rev-id=<EXISTING_REVISION_ID>
```

audit the complete result before keeping it.

## 3. Audit the Migration

Compare the migration against the authoritative SQLAlchemy model state.

Verify:

* column types, nullability, and defaults;
* foreign keys and cascade behavior;
* check and unique constraints;
* required JSON/enum constraints;
* indexes for established high-value lookup paths;
* safe dependency ordering in `upgrade()`;
* safe reverse dependency ordering in `downgrade()`.

Do not add speculative indexes or abstractions.

For destructive operations, identify any data that cannot be reconstructed by downgrade.

## 4. Apply and Inspect the Database

Use repository-standard environment variables and `uv`.

If `POLARIS_DATABASE_URL` is not exported but `.env` contains the canonical local PostgreSQL configuration, load it without printing secrets:

```bash
set -a; source .env; set +a; uv run alembic heads
set -a; source .env; set +a; uv run alembic current
set -a; source .env; set +a; uv run alembic upgrade head
set -a; source .env; set +a; uv run alembic check
set -a; source .env; set +a; uv run polaris inspect persistence
```

`alembic current` verifies the revision stamp only.

Always run `alembic check` after applying migrations to compare the physical schema with SQLAlchemy metadata.

When local PostgreSQL is available, also run:

```bash
uv run polaris inspect persistence
```

for the application's canonical persistence diagnostics.

### Test database

If a targeted test requires `POLARIS_TEST_DATABASE_URL` and it is not exported, derive safe local configuration from repository-owned sources such as:

* `.env`;
* `.env.example`;
* `docker-compose.yml`;
* test fixtures;
* `PostgresSettings`.

Prefer an isolated test database or schema.

Never print connection strings or secrets.

If the required local PostgreSQL service is not running and repository rules authorize service management, start only that service, for example:

```bash
docker compose up -d postgres
```

A DB-backed test skipped solely because local environment/service setup was absent is **unresolved verification**, not a pass.

## 5. Handle Stale Squashed Revisions

If `alembic current` references a revision no longer present on the branch, inspect Git history before changing the database stamp.

Do not blindly use:

```bash
uv run alembic stamp head
```

because stamping can hide unapplied schema operations.

For a disposable local development/test database, prefer resetting and rebuilding from current migrations. In Polaris:

```bash
uv run python scripts/reset_local_postgres_schema.py --confirm-destroy-local-db
uv run alembic upgrade head
uv run alembic check
uv run polaris inspect persistence
```

For a data-preserving environment, stop and produce an explicit remediation plan comparing actual schema state with current migration history before stamping, resetting, or issuing manual DDL.

## 6. Validate the Migration Lifecycle

For migrations changed by the current work, run the relevant round trip against a disposable or isolated database/schema:

1. `uv run alembic upgrade head`
2. `uv run alembic check`
3. `uv run polaris inspect persistence` when local PostgreSQL is available
4. inspect affected tables, columns, constraints, and indexes
5. `uv run alembic downgrade -1`
6. verify the intended prior schema state
7. `uv run alembic upgrade head`
8. `uv run alembic check`
9. run targeted migration-contract and PostgreSQL integration tests

Do not destructively downgrade a data-preserving environment merely to satisfy this workflow.

## 7. Post-change Wiki Sync

If the Living Entity Wiki exists, invoke `$wiki-sync` after substantive database work.

Do not decide locally whether the change is "architectural enough." `$wiki-sync` owns whether the completed change affects durable entity knowledge, including realization of an accepted decision that was previously implementation-pending.

Ordinary schema details do not automatically require wiki changes.

If invoked from `$implement-ticket`, stage any resulting wiki mutation and semantic `wiki/log.md` entry for the parent ticket commit rather than creating a separate wiki commit.

## Completion

Database migration work is not complete when any required condition remains unresolved, including:

* migration upgrade failure;
* `alembic check` drift;
* invalid downgrade/re-upgrade behavior;
* missing required constraints or indexes;
* failed targeted database tests;
* required DB tests skipped solely for missing local setup;
* stale removed revision state;
* unresolved blocking `$wiki-sync` finding.

Report unresolved or owner-deferred database verification explicitly.
