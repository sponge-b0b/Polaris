# Database Migration Testing Plan (Alembic)

# Goal
write robust database migration tests that do not rely on specific migration files or brittle naming conventions. Checking filenames or counting files is an anti-pattern because it breaks during a **squash** or **history cleanup**.
for database migration contract testing, focus on state, behavior, and API compatibility, treating Alembic's history as a black box.

## Intent
Ensure database schema integrity, zero-downtime compatibility, and seamless migration execution without creating brittle tests. Agents must treat the migration timeline as a dynamic black box instead of hardcoding file names or counting migration files.

## Core Principles
1. **Never check files:** Do not use `os.listdir`, count files, or assert on specific migration filenames/prefixes in tests. Squashing migrations must not break the test suite.
2. **State over Structure:** Test the *result* of the schema application and its compatibility with SQLAlchemy metadata, not the migration files themselves.
3. **Use `pytest-alembic`:** Utilize the `pytest-alembic` library to abstract migration context and session management.

---

## Implementation Guidelines

Agents should implement the following three core contract tests in the test suite (typically under `tests/database/test_migrations.py`).

### 1. The Single Head & Upgrade Test
Ensures that the migration history has not branched due to merge conflicts and that a blank database can successfully upgrade to the latest state.

```python
def test_migrations_up and_down(alembic_runner):
    """
    Validates that there is only a single head and that 
    the upgrade timeline executes from base to head cleanly.
    """
    # Verifies no accidental branching in git history
    alembic_runner.migrate_up_to("heads")
```

### 2. ORM Metadata Divergence Test (The Most Important Contract)
Ensures developers did not modify SQLAlchemy models without running `alembic revision --autogenerate`. This prevents production code from expecting columns that do not exist in the database.

```python
def test_model_definitions_match_ddl(alembic_runner):
    """
    Dynamically compares live DB schema after running migrations 
    against the current SQLAlchemy ORM metadata definition.
    Fails if any model changes are missing a migration file.
    """
    alembic_runner.migrate_up_to("heads")
    alembic_runner.assert_model_definitions_match()
```

### 3. Data Migration & State Verification (When needed)
When testing complex data migrations (e.g., refactoring a column's data format), use a targeted structural hook instead of hardcoding revision IDs.

```python
def test_custom_data_migration(alembic_runner):
    """Example pattern for testing data transformations safely."""
    # 1. Move to the state right BEFORE the complex migration
    # (Agent Note: Only use specific IDs if validating a highly complex data migration)
    alembic_runner.migrate_up_to("previous_revision_id")
    
    # 2. Insert mock data using raw SQL connection
    # 3. Step forward
    alembic_runner.migrate_up_to("target_revision_id")
    
    # 4. Assert data was transformed correctly
```

---

## Agent Guardrails & Anti-Patterns
* ❌ **DO NOT** write tests checking `len(os.listdir('migrations/versions'))`.
* ❌ **DO NOT** assert against naming conventions like `assert "add_users_table" in file.name`.
* ⚠️ **Alembic Config:** Ensure `alembic.ini` is accessible by the test environment, or use `pytest-alembic` config hooks in `conftest.py` to route the path programmatically.

  # Recommended Database Migration Test Replacement Plan

  ## Summary

  Replace the old brittle migration-file tests with state-based Alembic contract tests that treat migration history as a black box.

  Current finding: the existing migration tests under tests/unit/core/database/ assert specific historical migration filenames/revision IDs that no longer exist after the migration squash/cleanup. Example failure confirmed:
  test_runtime_persistence_migration.py expects migrations/versions/20260530_0001_add_runtime_persistence_tables.py, but the current migration timeline only contains the squashed/current migration files.

  The new migration tests will validate:

  - Alembic has exactly one head.
  - A blank PostgreSQL schema can upgrade to head.
  - Downgrades are structurally valid where supported.
  - Migrated DDL matches SQLAlchemy Base.metadata.
  - Tests do not count migration files, assert filenames, or hardcode revision chains.

  ## Implementation Changes

  ### 1. Remove brittle old migration tests

  Delete the old tests that directly inspect migration files, migration names, or historical revision IDs:

  - tests/unit/core/database/test_*_migration.py
  - tests/unit/core/database/test_schema_migration_contract.py
  - tests/unit/core/database/test_postgres_persistence_v3_migration_coverage.py

  Keep the non-brittle database/model tests:

  - tests/unit/core/database/test_*_models.py
  - tests/unit/core/database/test_model_output_coverage.py
  - tests/unit/core/database/test_postgres_settings.py
  - tests/unit/core/database/test_alembic_foundation.py, unless it becomes redundant after the new tests are added.

  ### 2. Add pytest-alembic migration contract tests

  Create a new migration test module, preferably:

  tests/database/test_migrations.py

  Implement explicit pytest-alembic-backed tests:

  - test_migration_history_has_single_head
      - delegates to pytest_alembic.tests.test_single_head_revision

  - test_migrations_upgrade_from_blank_database
      - delegates to pytest_alembic.tests.test_upgrade

  - test_migration_downgrades_are_consistent
      - delegates to pytest_alembic.tests.test_up_down_consistency

  - test_model_definitions_match_migrated_ddl
      - delegates to pytest_alembic.tests.test_model_definitions_match_ddl

  Do not use pytest-alembic’s automatic --test-alembic collection as the only interface; explicit tests are clearer and easier to run directly.

  ### 3. Add isolated PostgreSQL fixtures

  Create migration-test fixtures, likely in:

  tests/database/conftest.py

  Fixture behavior:

  - Require POLARIS_TEST_DATABASE_URL.
  - Skip migration tests when the env var is unset.
  - Never use POLARIS_DATABASE_URL as an implicit fallback.
  - Create a temporary PostgreSQL schema per test.
  - Run Alembic against that isolated schema.
  - Drop the schema with CASCADE after each test.

  Recommended fixture names:

  - test_database_url
  - migration_test_schema
  - alembic_engine
  - alembic_config

  The alembic_config fixture should point to:
  migrations/
  core.database.base.Base.metadata

  ### 4. Make Alembic env.py pytest-alembic compatible if needed

  If current migrations/env.py does not correctly honor pytest-alembic’s injected connection/engine, update it minimally so tests can run against the fixture-provided isolated schema.

  The change should preserve current production behavior:

  - If config.attributes["connection"] is provided, use it.
  - If no injected connection exists, continue using PostgresSettings.from_env().async_database_url.
  - Keep compare_type=True.
  - Keep compare_server_default=True.
  - Do not introduce Base.metadata.create_all().

  This is a testability improvement to Alembic wiring, not a schema behavior change.

  ### 5. Do not add generic data-migration tests yet

  The plan file allows targeted data-migration tests only for complex data migrations.

  For this rewrite, do not invent revision-specific data migration tests. Add those later only when validating a known data transformation, and only then may a specific revision ID be used.

  ## Test Plan

  Run these checks after implementation:

  uv run pytest -q tests/database/test_migrations.py

  Expected without env var:

  skipped because POLARIS_TEST_DATABASE_URL is unset

  Run live PostgreSQL migration tests with:

  POLARIS_TEST_DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/db \
  UV_CACHE_DIR=/tmp/uv-cache \
  uv run pytest -q tests/database/test_migrations.py

  Also run:

  uv run pytest -q tests/unit/core/database
  uv run ruff check tests/database tests/unit/core/database
  uv run mypy tests/database tests/unit/core/database --explicit-package-bases

  If repo-wide mypy has unrelated pre-existing failures, report them separately and do not block this migration-test replacement on unrelated files.

  ## Assumptions

  - PostgreSQL migration contract tests are integration-style tests and should be skipped unless POLARIS_TEST_DATABASE_URL is explicitly set.
  - The old file-inspection tests are intentionally removed, not repaired, because they violate the new migration testing policy.
  - SQLAlchemy model-level tests remain valuable and should not be deleted unless they also inspect migration filenames or revision IDs.
  - The canonical migration contract is final database state and ORM metadata compatibility, not the shape or count of migration files.

## Step Results

### Step 1 — Remove brittle old migration tests (2026-06-15 11:09:26 UTC)

- Removed migration-file inspection tests that asserted historical Alembic filenames, revision IDs, or direct migration source text.
- Preserved non-migration database/model tests such as model coverage, settings, and model persistence tests.
- Added this `## Step Results` section for ongoing per-step implementation notes.
- Verification passed: `uv run pytest -q tests/unit/core/database --maxfail=1` returned `132 passed`.
- Verification passed: no remaining `migrations/versions/`, `MIGRATION_PATH`, revision-ID, or migration-spec references remain in `tests/unit/core/database/*.py`.

Removed files:
- `tests/unit/core/database/test_agent_intelligence_payload_migration.py`
- `tests/unit/core/database/test_agent_intelligence_persistence_migration.py`
- `tests/unit/core/database/test_agent_signal_persistence_migration.py`
- `tests/unit/core/database/test_attribution_persistence_migration.py`
- `tests/unit/core/database/test_audit_persistence_migration.py`
- `tests/unit/core/database/test_lineage_persistence_migration.py`
- `tests/unit/core/database/test_macro_persistence_migration.py`
- `tests/unit/core/database/test_macro_regime_payload_migration.py`
- `tests/unit/core/database/test_market_event_volatility_forecast_migration.py`
- `tests/unit/core/database/test_market_persistence_migration.py`
- `tests/unit/core/database/test_market_technical_payload_migration.py`
- `tests/unit/core/database/test_news_payload_migration.py`
- `tests/unit/core/database/test_news_persistence_migration.py`
- `tests/unit/core/database/test_portfolio_expansion_persistence_migration.py`
- `tests/unit/core/database/test_portfolio_position_output_migration.py`
- `tests/unit/core/database/test_portfolio_state_account_payload_migration.py`
- `tests/unit/core/database/test_portfolio_state_v2_migration.py`
- `tests/unit/core/database/test_rag_persistence_migration.py`
- `tests/unit/core/database/test_rag_source_eligibility_migration.py`
- `tests/unit/core/database/test_recommendation_persistence_migration.py`
- `tests/unit/core/database/test_report_persistence_migration.py`
- `tests/unit/core/database/test_report_version_publication_persistence_migration.py`
- `tests/unit/core/database/test_retention_persistence_migration.py`
- `tests/unit/core/database/test_runtime_persistence_migration.py`
- `tests/unit/core/database/test_sentiment_persistence_migration.py`
- `tests/unit/core/database/test_sentiment_snapshot_payload_migration.py`
- `tests/unit/core/database/test_telemetry_persistence_migration.py`
- `tests/unit/core/database/test_workflow_state_snapshot_persistence_migration.py`
- `tests/unit/core/database/test_schema_migration_contract.py`
- `tests/unit/core/database/test_postgres_persistence_v3_migration_coverage.py`

### Step 2 — Add pytest-alembic migration contract test module (2026-06-15 11:12:00 UTC)

- Created `tests/database/test_migrations.py` with four explicit pytest-alembic contract tests.
- The tests delegate to pytest-alembic's canonical contract checks for single-head history, blank-database upgrade, up/down consistency, and ORM metadata-vs-DDL drift.
- Avoided pytest-alembic automatic `--test-alembic` collection as the only interface; the migration contract is now directly runnable by path.
- Verification passed: `uv run pytest --collect-only -q tests/database/test_migrations.py` collected 4 tests.
- Ran `uv run graphify update .` after the code change to refresh the repository graph.

### Step 3 — Add isolated PostgreSQL fixtures (2026-06-15 11:17:37 UTC)

- Created `tests/database/conftest.py` with explicit pytest-alembic fixtures for migration contract tests.
- Added `test_database_url` fixture that requires `POLARIS_TEST_DATABASE_URL` and skips migration tests when unset; it does not fall back to `POLARIS_DATABASE_URL`.
- Added a per-test `migration_test_schema` fixture and `alembic_engine` fixture that creates a temporary PostgreSQL schema, runs test connections with that schema in `search_path`, and drops the schema with `CASCADE` during teardown.
- Added `alembic_config` fixture pointing pytest-alembic at `alembic.ini`, `migrations`, and `core.database.base.Base.metadata`.
- Verification passed: `uv run pytest -q tests/database/test_migrations.py` without `POLARIS_TEST_DATABASE_URL` returned `4 skipped`.
- Verification passed: `uv run ruff check tests/database --fix`.
- Verification passed: `uv run ruff format tests/database`.
- Verification passed: `uv run mypy tests/database --explicit-package-bases`.
- Ran `uv run graphify update .` after the code change to refresh the repository graph.
- Note: live execution of the migration tests still depends on Step 4 because `migrations/env.py` must honor pytest-alembic's injected connection/engine before the temporary schema is used by Alembic.

### Step 4 — Make Alembic env.py pytest-alembic compatible (2026-06-15 11:27:47 UTC)

- Updated `migrations/env.py` so online migrations honor pytest-alembic's injected `config.attributes["connection"]`.
- Added support for injected `AsyncEngine`, `AsyncConnection`, synchronous `Engine`, and synchronous `Connection` while preserving the existing production path that builds an async engine from Alembic/Postgres settings when no injected connection exists.
- Preserved `compare_type=True` and `compare_server_default=True`.
- Added support for pytest-alembic-provided `target_metadata`, `include_schemas`, and `process_revision_directives`; this is required for metadata-vs-DDL autogenerate checks.
- Did not add `Base.metadata.create_all()` or any schema creation shortcut.
- Verification passed: `uv run ruff check migrations/env.py tests/database --fix`.
- Verification passed: `uv run ruff format migrations/env.py tests/database`.
- Verification passed: `uv run mypy migrations/env.py tests/database --explicit-package-bases`.
- Verification passed without live database env: `uv run pytest -q tests/database/test_migrations.py tests/unit/core/database/test_alembic_foundation.py` returned `2 passed, 4 skipped`.
- Ran `uv run graphify update .` after the code change to refresh the repository graph.
- Live PostgreSQL execution was attempted with `POLARIS_TEST_DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/db`, but the command timed out before producing pytest output. This appears to be a local database connectivity/runtime issue rather than a collection or static contract issue; Step 5 should perform final live verification once PostgreSQL connectivity is confirmed.

### Step 5 — Final migration-test verification and no generic data-migration tests (2026-06-15 11:33:35 UTC)

- Confirmed local PostgreSQL TCP connectivity on `localhost:5432`; sandbox escalation was required because local socket access is restricted by default.
- Ran the live PostgreSQL migration contract tests with `POLARIS_TEST_DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/db`.
- First live run exposed an asyncpg event-loop ownership issue in the pytest fixture teardown because a fixture-scoped `AsyncEngine` was reused across multiple `asyncio.run(...)` calls and pytest-alembic migration invocations.
- Refactored `tests/database/conftest.py` to provide pytest-alembic a synchronous SQLAlchemy `Engine` using the existing `psycopg2` dependency while preserving the externally supplied async test URL as the required environment contract.
  - The fixture converts `postgresql+asyncpg://...` to `postgresql+psycopg2://...` only inside the migration test fixture.
  - Alembic production behavior remains async-first when no injected test engine is provided.
  - Schema isolation is preserved through PostgreSQL `search_path` and one temporary schema per test.
- Cleaned up four temporary `polaris_migration_test_%` schemas left by the failed pre-fix live run.
- Verification passed: live PostgreSQL test run returned `4 passed`:
  - `POLARIS_TEST_DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/db UV_CACHE_DIR=/tmp/uv-cache timeout 300s uv run pytest -q tests/database/test_migrations.py`
- Verification passed without live database env: `uv run pytest -q tests/database/test_migrations.py tests/unit/core/database --maxfail=1` returned `132 passed, 4 skipped`.
- Verification passed: no migration tests under `tests/database` or `tests/unit/core/database` contain migration-file path checks, `os.listdir`, or hardcoded revision IDs.
- Ran `uv run graphify update .` after the fixture change to refresh the repository graph.
- No generic data-migration tests were added. Future data-migration tests should remain targeted to a specific known data transformation and should not be introduced speculatively.
