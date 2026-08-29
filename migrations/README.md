# Alembic Migrations

PostgreSQL schema changes are managed with Alembic.

The migration environment loads `core.database.base.Base.metadata` after importing
all SQLAlchemy models from `core.database.models`.

`POLARIS_DATABASE_URL` is the canonical application/runtime and ordinary Alembic
migration target. `POLARIS_TEST_DATABASE_URL` is a separate semantic role: it is
an explicit PostgreSQL test target and live-test opt-in, not a requirement for a
second physical database. Tests must never implicitly fall back to
`POLARIS_DATABASE_URL` when `POLARIS_TEST_DATABASE_URL` is unset.

Before 1.0, the repository-local development database is disposable, so local
`.env` configuration may intentionally set both URLs to the same `polaris`
database. Ephemeral CI should normally set both URLs explicitly to the same
job-local PostgreSQL database. After 1.0, keep the explicit test-target boundary
even if deployment policy chooses stronger physical isolation.

For local database commands, load the ignored `.env` through `uv` rather than
manually sourcing it into the shell:

```bash
uv run --env-file .env alembic current
uv run --env-file .env alembic upgrade head
uv run --env-file .env alembic check
```

PostgreSQL passwords have no source-controlled default. See
`../docs/current/persistence-curated-records-postgresql-persistence.md` for local
PostgreSQL startup, environment variables, migration policy, and developer
validation commands.
