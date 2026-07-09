# Alembic Migrations

PostgreSQL schema changes are managed with Alembic.

The migration environment loads `core.database.base.Base.metadata` after importing
all SQLAlchemy models from `core.database.models`.

Configure `POLARIS_DATABASE_URL` or the `POLARIS_POSTGRES_*` settings before running migrations. PostgreSQL passwords have no source-controlled default.

See `../docs/postgres_persistence.md` for local Postgres startup, environment variables, and developer validation commands.
