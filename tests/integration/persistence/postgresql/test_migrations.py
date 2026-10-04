from __future__ import annotations

import asyncio
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import text

from polaris.infrastructure.persistence.postgresql import (
    DECISION_TABLE_NAMES,
    POLARIS_TABLE_NAMES,
    create_postgres_engine,
)

from .conftest import PostgresTestTarget

FORBIDDEN_TABLE_FRAGMENTS = {
    "action_intent",
    "agent",
    "event",
    "governance",
    "job",
    "lesson",
    "outcome",
    "rag",
    "recommendation",
    "report",
    "workflow",
}
# duplicate-code: this independently asserted migration expectation must not
# consume the runtime schema registry it is intended to falsify.
# arid: disable
SUFFICIENCY_TABLE_NAMES = {
    "evidence_support_versions",
    "evidence_sufficiency_assessments",
    "evidence_sufficiency_contributors",
    "evidence_sufficiency_command_receipts",
}
# arid: enable


async def _string_values(
    target: PostgresTestTarget,
    statement: str,
    parameters: dict[str, str],
) -> frozenset[str]:
    engine = create_postgres_engine(target.database_url, schema=target.schema)
    try:
        async with engine.connect() as connection:
            rows = await connection.execute(text(statement), parameters)
            return frozenset(rows.scalars())
    finally:
        await engine.dispose()


async def _table_names(target: PostgresTestTarget) -> frozenset[str]:
    return await _string_values(
        target,
        "SELECT table_name FROM information_schema.tables WHERE table_schema = :schema",
        {"schema": target.schema},
    )


async def _identity_column_types(
    target: PostgresTestTarget,
) -> dict[tuple[str, str], str]:
    engine = create_postgres_engine(target.database_url, schema=target.schema)
    try:
        async with engine.connect() as connection:
            rows = await connection.execute(
                text(
                    "SELECT table_name, column_name, udt_name "
                    "FROM information_schema.columns "
                    "WHERE table_schema = :schema "
                    "AND (column_name = 'row_id' "
                    "OR column_name LIKE '%\\_id' ESCAPE '\\')"
                ),
                {"schema": target.schema},
            )
            return {(row.table_name, row.column_name): row.udt_name for row in rows}
    # duplicate-code: migration falsifiers require local proof shape.
    # arid: disable
    finally:
        await engine.dispose()


async def _column_default(
    target: PostgresTestTarget,
    table_name: str,
    column_name: str,
) -> str | None:
    engine = create_postgres_engine(target.database_url, schema=target.schema)
    try:
        async with engine.connect() as connection:
            return await connection.scalar(
                text(
                    "SELECT column_default FROM information_schema.columns "
                    "WHERE table_schema = :schema AND table_name = :table_name "
                    "AND column_name = :column_name"
                ),
                {
                    "schema": target.schema,
                    "table_name": table_name,
                    "column_name": column_name,
                },
            )
    finally:
        await engine.dispose()


async def _column_names(
    target: PostgresTestTarget,
    table_name: str,
) -> frozenset[str]:
    return await _string_values(
        target,
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema = :schema AND table_name = :table_name",
        {"schema": target.schema, "table_name": table_name},
    )


async def _constraint_names(
    target: PostgresTestTarget,
    table_name: str,
) -> frozenset[str]:
    return await _string_values(
        target,
        "SELECT c.conname "
        "FROM pg_constraint AS c "
        "JOIN pg_class AS t ON t.oid = c.conrelid "
        "JOIN pg_namespace AS n ON n.oid = t.relnamespace "
        "WHERE n.nspname = :schema AND t.relname = :table_name",
        {"schema": target.schema, "table_name": table_name},
    )


def _assert_revision_round_trip(
    target: PostgresTestTarget,
    revision: str,
    expected_tables: frozenset[str],
) -> None:
    alembic = Config("alembic.ini")
    command.downgrade(alembic, revision)
    assert asyncio.run(_table_names(target)) == expected_tables

    command.upgrade(alembic, "head")
    assert asyncio.run(_table_names(target)) == (
        POLARIS_TABLE_NAMES | {"alembic_version"}
    )


def test_fresh_root_migrates_only_greenfield_polaris_schema(
    postgres_target: PostgresTestTarget,
) -> None:
    decision_migration = Path(
        "migrations/versions/0001_decision_persistence_foundation.py"
    ).read_text(encoding="utf-8")
    evidence_migration = Path(
        "migrations/versions/0002_evidence_observation_foundation.py"
    ).read_text(encoding="utf-8")
    requirement_migration = Path(
        "migrations/versions/0003_evidence_requirement_authority.py"
    ).read_text(encoding="utf-8")
    binding_migration = Path("migrations/versions/0004_evidence_bindings.py").read_text(
        encoding="utf-8"
    )
    sufficiency_requirement_migration = Path(
        "migrations/versions/0005_evidence_sufficiency_requirements.py"
    ).read_text(encoding="utf-8")
    sufficiency_assessment_migration = Path(
        "migrations/versions/0006_evidence_sufficiency_assessments.py"
    ).read_text(encoding="utf-8")
    assert "down_revision: str | None = None" in decision_migration
    assert (
        'down_revision: str | None = "0001_decision_persistence"' in evidence_migration
    )
    assert (
        'down_revision: str | None = "0002_evidence_observations"'
        in requirement_migration
    )
    assert (
        'down_revision: str | None = "0003_evidence_requirements"' in binding_migration
    )
    assert (
        'down_revision: str | None = "0004_evidence_bindings"'
        in sufficiency_requirement_migration
    )
    assert (
        'down_revision: str | None = "0005_sufficiency_requirements"'
        in sufficiency_assessment_migration
    )
    assert "legacy" not in decision_migration.lower()
    assert "legacy" not in evidence_migration.lower()
    assert "legacy" not in requirement_migration.lower()
    assert "legacy" not in binding_migration.lower()
    assert "legacy" not in sufficiency_requirement_migration.lower()
    assert "legacy" not in sufficiency_assessment_migration.lower()

    tables = asyncio.run(_table_names(postgres_target))
    assert tables == POLARIS_TABLE_NAMES | {"alembic_version"}
    assert not {
        table
        for table in tables
        if any(fragment in table for fragment in FORBIDDEN_TABLE_FRAGMENTS)
    }

    column_types = asyncio.run(_identity_column_types(postgres_target))
    assert column_types
    for (_, column_name), data_type in column_types.items():
        assert data_type == ("int8" if column_name == "row_id" else "uuid")

    for table_name, column_name in (
        ("evidence_observations", "observation_id"),
        ("evidence_bindings", "binding_id"),
        ("evidence_sufficiency_assessments", "assessment_id"),
    ):
        assert (
            asyncio.run(
                _column_default(
                    postgres_target,
                    table_name,
                    column_name,
                )
            )
            is None
        )

    relationship_columns = asyncio.run(
        _column_names(postgres_target, "investment_decision_relationships")
    )
    assert (
        not {
            "prior_decision_context",
            "target_known_at",
            "target_decision_version",
        }
        & relationship_columns
    )
    binding_columns = asyncio.run(_column_names(postgres_target, "evidence_bindings"))
    assert {
        "claim_id",
        "freshness_state",
        "freshness_basis_at",
        "freshness_applicability",
        "freshness_result",
        "freshness_failure_reason",
        "freshness_contested_version_ids",
    } <= binding_columns


def test_binding_migration_preserves_canonical_constraint_names(
    postgres_target: PostgresTestTarget,
) -> None:
    binding_constraints = asyncio.run(
        _constraint_names(postgres_target, "evidence_bindings")
    )
    assert {
        "ck_evidence_bindings_target_family",
        "ck_evidence_bindings_scope_kind",
        "ck_evidence_bindings_evidence_use",
        "ck_evidence_bindings_role",
        "ck_evidence_bindings_availability",
        "ck_evidence_bindings_material_use_requires_available",
        "ck_evidence_bindings_material_qualification_nonempty",
        "ck_evidence_bindings_freshness_state",
        "ck_evidence_bindings_freshness_result",
        "ck_evidence_bindings_freshness_basis_reference_nonempty",
        "ck_evidence_bindings_freshness_failure_reason_nonempty",
        "ck_evidence_bindings_freshness_shape",
        "fk_evidence_binding_observation",
        "fk_evidence_binding_freshness_version",
        "fk_evidence_binding_freshness_requirement",
        "pk_evidence_bindings",
        "uq_evidence_bindings_binding_id",
    } <= binding_constraints
    assert not {
        name
        for name in binding_constraints
        if name.startswith("ck_evidence_bindings_ck_evidence_bindings_")
    }

    receipt_constraints = asyncio.run(
        _constraint_names(postgres_target, "evidence_binding_command_receipts")
    )
    assert "ck_evidence_binding_command_receipts_fingerprint_sha256" in (
        receipt_constraints
    )
    assert not {
        name
        for name in receipt_constraints
        if name.startswith(
            "ck_evidence_binding_command_receipts_ck_evidence_binding_command_receipts_"
        )
    }


def test_sufficiency_requirement_migration_constrains_definition_shape(
    postgres_target: PostgresTestTarget,
) -> None:
    constraint = "ck_evidence_requirement_definitions_definition_shape"
    assert constraint in asyncio.run(
        _constraint_names(postgres_target, "evidence_requirement_definitions")
    )
    alembic = Config("alembic.ini")
    command.downgrade(alembic, "0004_evidence_bindings")
    assert constraint not in asyncio.run(
        _constraint_names(postgres_target, "evidence_requirement_definitions")
    )
    command.upgrade(alembic, "head")
    assert constraint in asyncio.run(
        _constraint_names(postgres_target, "evidence_requirement_definitions")
    )


def test_sufficiency_assessment_migration_preserves_constraints(
    postgres_target: PostgresTestTarget,
) -> None:
    support_version_constraints = asyncio.run(
        _constraint_names(postgres_target, "evidence_support_versions")
    )
    assert {
        "ck_evidence_support_versions_evidence_use",
        "ck_evidence_support_versions_scope_kind",
        "ck_evidence_support_versions_support_version_positive",
        "ck_evidence_support_versions_target_family",
        "fk_evidence_support_version_binding",
        "uq_evidence_support_versions_binding_id",
    } <= support_version_constraints
    assessment_constraints = asyncio.run(
        _constraint_names(postgres_target, "evidence_sufficiency_assessments")
    )
    assert {
        "ck_evidence_sufficiency_assessments_actor_attribution_kind",
        "ck_evidence_sufficiency_assessments_actor_attribution_shape",
        "ck_evidence_sufficiency_assessments_evidence_use",
        "ck_evidence_sufficiency_assessments_known_before_recorded",
        "ck_evidence_sufficiency_assessments_reassessment_distinct",
        "ck_evidence_sufficiency_assessments_result",
        "ck_evidence_sufficiency_assessments_scope_kind",
        "ck_evidence_sufficiency_assessments_support_version_nonnegative",
        "ck_evidence_sufficiency_assessments_target_family",
        "fk_evidence_sufficiency_reassessment",
        "fk_evidence_sufficiency_requirement_version",
        "uq_evidence_sufficiency_assessment_requirement_version",
    } <= assessment_constraints
    contributor_constraints = asyncio.run(
        _constraint_names(postgres_target, "evidence_sufficiency_contributors")
    )
    assert {
        "fk_evidence_sufficiency_contributor_assessment",
        "fk_evidence_sufficiency_contributor_binding",
        "uq_evidence_sufficiency_contributor",
    } <= contributor_constraints


def test_root_downgrades_to_empty_and_reupgrades(
    postgres_target: PostgresTestTarget,
) -> None:
    _assert_revision_round_trip(
        postgres_target,
        "base",
        frozenset({"alembic_version"}),
    )


def test_evidence_revision_downgrades_to_decision_foundation_and_reupgrades(
    postgres_target: PostgresTestTarget,
) -> None:
    _assert_revision_round_trip(
        postgres_target,
        "0001_decision_persistence",
        DECISION_TABLE_NAMES | {"alembic_version"},
    )


def test_requirement_revision_downgrades_to_evidence_foundation_and_reupgrades(
    postgres_target: PostgresTestTarget,
) -> None:
    _assert_revision_round_trip(
        postgres_target,
        "0002_evidence_observations",
        (
            POLARIS_TABLE_NAMES
            - {
                "evidence_requirement_set_versions",
                "evidence_requirement_definitions",
                "evidence_bindings",
                "evidence_binding_command_receipts",
                *SUFFICIENCY_TABLE_NAMES,
            }
        )
        | {"alembic_version"},
    )


def test_binding_revision_downgrades_to_requirement_foundation_and_reupgrades(
    postgres_target: PostgresTestTarget,
) -> None:
    _assert_revision_round_trip(
        postgres_target,
        "0003_evidence_requirements",
        (
            POLARIS_TABLE_NAMES
            - {
                "evidence_bindings",
                "evidence_binding_command_receipts",
                *SUFFICIENCY_TABLE_NAMES,
            }
        )
        | {"alembic_version"},
    )


def test_sufficiency_revision_downgrades_to_executable_requirements_and_reupgrades(
    postgres_target: PostgresTestTarget,
) -> None:
    _assert_revision_round_trip(
        postgres_target,
        "0005_sufficiency_requirements",
        (POLARIS_TABLE_NAMES - SUFFICIENCY_TABLE_NAMES) | {"alembic_version"},
    )
