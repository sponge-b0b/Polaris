---
name: database-migrations
description: Manage, generate, apply, and validate PostgreSQL schema migrations using SQLAlchemy and Alembic, including the pre-1.0 branch-baseline policy and targeted database verification.
compatibility: product=codex product=claude-code system=python system=git network=none
---

# Database Migrations

## Objective

Keep PostgreSQL schema, SQLAlchemy models, and Alembic history correct for the repository's current release lifecycle.

Before 1.0, **schema and migration correctness outrank existing data**. After 1.0, migration history and persisted data must be preserved.

A valid `downgrade()` proves schema reversibility. It does not imply destroyed data can be recovered.

## Pre-flight

Before modifying database-affecting code:

1. identify the authoritative SQLAlchemy models and persistence contracts;
2. confirm schema evolution uses Alembic rather than ad hoc runtime DDL;
3. read `[project].version` from `pyproject.toml`;
4. if the Living Entity Wiki exists, invoke `$wiki-sync`;
5. halt on blocking architecture findings such as `[source-conflict]`.

`[project].version` is authoritative for migration lifecycle. Git tags are corroborating only.

Before any pytest invocation, follow the mandatory test-service preflight in
`AGENTS.md` and `docs/process/testing-guide.md`. Determine the selected scope's
complete external prerequisites and verify them before pytest starts. Missing
prerequisites leave required verification unresolved.

For local PostgreSQL-backed work, `.env` is the canonical local environment
input. Run database preflights, migrations, database-backed pytest, and Python
database probes through `uv run --env-file .env ...`. Do not manually source
`.env` merely to populate the current shell, and never use bare `python` for a
database preflight; use `uv run --env-file .env python ...` so project
dependencies and database configuration are established by the same command.

CI must provide its database environment explicitly at the job level. CI does
not depend on a developer `.env` file.

## PostgreSQL URL Roles

`POLARIS_DATABASE_URL` is the canonical application/runtime and ordinary Alembic
migration target.

`POLARIS_TEST_DATABASE_URL` is an explicit PostgreSQL test target and live-test
opt-in. It does **not** imply that a second physical database must exist. Tests
must never implicitly fall back from `POLARIS_TEST_DATABASE_URL` to
`POLARIS_DATABASE_URL` when the test target is absent.

Before 1.0, when the repository-local development database is clearly disposable,
`.env` may intentionally set `POLARIS_TEST_DATABASE_URL` equal to
`POLARIS_DATABASE_URL`. Ephemeral CI should normally set both variables
explicitly to the same job-local PostgreSQL database. The explicit second
variable remains valuable because it records authorization to use that target for
PostgreSQL-backed tests even when both values happen to be identical.

Do not synthesize `POLARIS_TEST_DATABASE_URL` at runtime by rewriting or copying
`POLARIS_DATABASE_URL`. Load the explicit configured value. If a required test
target is absent, the required live verification remains unresolved.

## 1. Select the Migration Strategy

### Before 1.0

Use the **branch-baseline policy**:

* the current feature's migration remains mutable until that feature is merged/released;
* if the feature already has an unreleased branch migration, edit it instead of adding sequential corrective migrations;
* do not rewrite migration baselines belonging to previously merged features;
* keep the active migration tracked and committed.

### Pre-1.0 Data Disposability

**All pre-1.0 development and test data is disposable.**

Do not:

* preserve existing rows at the expense of the correct schema;
* add corrective/compatibility migrations merely because existing pre-1.0 data would be lost;
* retain obsolete mutable migration history because a database has already applied it;
* skip or defer a required migration because reset would destroy data;
* stamp around incompatible mutable migration history merely to preserve data;
* request user confirmation solely because resetting a pre-1.0 local development/test database is destructive.

When current mutable migration history and an existing local development/test database disagree, **reset and rebuild from current migrations**.

Destructive reset of a clearly identified repository-local development/test database is pre-authorized before 1.0.

If the target database is not clearly development/test or repository-owned, halt rather than assuming it is disposable.

### 1.0 Release Preparation

After intended 1.0 feature branches land, deliberately squash repository migration history into the canonical initial schema.

Reset disposable development/test databases as necessary and validate a clean install.

### After 1.0

Migration history is immutable.

Never edit an applied/released migration. Every schema change receives a new migration.

Preserve persisted data unless an explicitly authorized migration says otherwise.

## 2. Select the Target Migration

Inspect current history:

```bash id="8ymxg6"
uv run --env-file .env alembic heads
uv run --env-file .env alembic history
git status --short migrations/versions
git log --oneline -- migrations/versions
```

Before 1.0:

* modify the current feature's existing branch migration when one exists;
* otherwise create a new migration.

Autogenerate may assist with the diff, but audit the result. Preserve intentional constraints, indexes, operation ordering, comments, and downgrade behavior.

If intentionally regenerating a mutable revision with its existing ID:

```bash id="bb3jra"
uv run --env-file .env alembic revision --autogenerate -m "<description>" --rev-id=<EXISTING_REVISION_ID>
```

Audit the complete generated revision before keeping it.

## 3. Audit the Migration

Compare the migration with authoritative SQLAlchemy state.

Verify:

* column types, nullability, and defaults;
* foreign keys and cascades;
* check and unique constraints;
* required JSON/enum constraints;
* established high-value indexes;
* dependency-safe `upgrade()` ordering;
* reverse dependency-safe `downgrade()` ordering.

Do not add speculative indexes or abstractions.

Before 1.0, destructive data loss is not itself a migration blocker.

After 1.0, identify data that destructive operations cannot reconstruct.

## 4. Apply and Inspect the Database

Use repository-standard environment variables and `uv`.

For local work, load canonical local PostgreSQL configuration from `.env` through
`uv` without exporting secrets into the current shell:

```bash id="tg0jp5"
uv run --env-file .env alembic current
uv run --env-file .env alembic upgrade head
uv run --env-file .env alembic check
uv run --env-file .env polaris inspect persistence
```

`alembic current` verifies the revision stamp only.

Always run `alembic check` after migration application.

When local PostgreSQL is available, also run:

```bash id="g4f58m"
uv run --env-file .env polaris inspect persistence
```

### PostgreSQL Test Target

If targeted tests require `POLARIS_TEST_DATABASE_URL`, require that explicit test
target from the active environment source. For local development, load `.env`
with `uv run --env-file .env ...`. Do not derive a replacement from
`POLARIS_DATABASE_URL`, `POLARIS_POSTGRES_*`, `docker-compose.yml`, or other
repository defaults.

A separate physical test database is optional. Before 1.0, the explicit test URL
may equal `POLARIS_DATABASE_URL` when both identify the clearly disposable
repository-local database. Migration contract tests still isolate their work in
temporary PostgreSQL schemas. Ephemeral CI should normally set both URLs to the
same ephemeral job database.

Never print connection strings or secrets.

If the required repository-local PostgreSQL service is not running and repository rules authorize service management, start only that service:

```bash id="sw9k7m"
docker compose up -d postgres
```

For a bounded Python connectivity or metadata probe, always use the project
environment and local env file:

```bash id="database-python-preflight"
uv run --env-file .env python <probe-script-or--c-expression>
```

Never run a database preflight with bare `python`.

A required DB-backed test skipped solely because local setup is missing is unresolved verification, not a pass.

## 5. Handle Stale or Mutable Revision State

If `alembic current` references a revision removed or rewritten on the current branch, inspect migration/Git history enough to confirm the cause.

Do not blindly use:

```bash id="h4mzt1"
uv run --env-file .env alembic stamp head
```

because stamping can hide unapplied schema operations.

### Before 1.0

For a stale or incompatible local development/test schema, reset and rebuild:

```bash id="lis3ya"
uv run --env-file .env python scripts/reset_local_postgres_schema.py --confirm-destroy-local-db
uv run --env-file .env alembic upgrade head
uv run --env-file .env alembic check
uv run --env-file .env polaris inspect persistence
```

Do this without additional user confirmation when the target is clearly the repository's local development/test database.

Existing pre-1.0 data must not block this reset.

### After 1.0 or Unknown Environment

Do not destructively reset an environment that is production, shared, data-preserving, or cannot be confidently identified as disposable.

Stop and report the migration/schema mismatch and required remediation.

## 6. Validate the Migration Lifecycle

For migrations changed by the current work, run the applicable round trip against a disposable/isolated database:

1. `uv run --env-file .env alembic upgrade head`
2. `uv run --env-file .env alembic check`
3. `uv run --env-file .env polaris inspect persistence` when available
4. inspect affected tables, columns, constraints, and indexes
5. `uv run --env-file .env alembic downgrade -1`
6. verify the intended prior schema
7. `uv run --env-file .env alembic upgrade head`
8. `uv run --env-file .env alembic check`
9. run targeted migration-contract and PostgreSQL integration tests through `uv run --env-file .env pytest ...`

Before 1.0, reset/rebuild the disposable database whenever mutable migration history makes an in-place round trip invalid or misleading.

After 1.0, do not destructively downgrade a data-preserving environment merely to satisfy this workflow.

## 7. Post-change Wiki Sync

After substantive database work, invoke `$wiki-sync` when the Living Entity Wiki exists.

`$wiki-sync` owns whether the change affects durable architectural knowledge, including realization of an accepted decision that was previously pending.

Ordinary schema details do not automatically require wiki changes.

When called by `$implement-ticket`, wiki mutations and their semantic `wiki/log.md` entry belong to the parent ticket commit.

## Completion

Database migration work is incomplete while any required condition remains unresolved, including:

* migration upgrade failure;
* `alembic check` drift;
* invalid required downgrade/re-upgrade behavior;
* missing required constraints/indexes;
* failed targeted database tests;
* required DB tests skipped for missing local setup;
* stale revision state not reset/reconciled according to the release policy;
* blocking `$wiki-sync` findings.

Before 1.0, **existing disposable data is never a valid reason to leave one of these conditions unresolved**.

Report unresolved database verification explicitly.

## Transition-Bound Migration Safety and Completion

Two judgment-bearing transitions in this skill require explicit working state: destructive pre-1.0 reset authorization and completion of a changed migration contract.

### Environment Disposition Before Destructive Reset

Before any destructive reset, record:

```text
Target identity: <database/environment identifier without secrets>
Project version: <pyproject version>
Repository-local evidence: <evidence>
Development/test evidence: <evidence>
Shared/production/data-preserving contrary evidence: <None | evidence>
Disposable: <yes | no | unknown>
```

Only `Disposable: yes` authorizes the pre-1.0 destructive reset. `unknown` and `no` halt. The pre-1.0 policy removes the need for an extra human confirmation **after** disposability is proven; it does not permit the agent to assume disposability because reset would be convenient. Never print connection strings while establishing this state.

### Migration Contract Completion Record

For every migration changed by the current work, maintain:

```text
Migration: <revision/path>
Authoritative model/schema delta: <exact affected objects>
Model/migration correspondence: <pass | unresolved>
Upgrade proof: <pass | unresolved>
Required schema inspection: <pass | unresolved>
Downgrade/prior-schema proof: <pass | not-applicable-with-authority | unresolved>
Final re-upgrade/head/check: <pass | unresolved>
Required migration/PostgreSQL tests: <pass | not-applicable-with-reason | unresolved>
External prerequisites: <satisfied | unresolved>
```

Completion requires every applicable field `pass`, every `not-applicable` disposition to carry the exact policy/environment reason, and zero unresolved fields. A successful `alembic upgrade`, revision stamp, or test subset cannot stand in for the other required lifecycle predicates.

These records are working safety state; concise reporting remains sufficient.
