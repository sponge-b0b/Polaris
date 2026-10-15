from __future__ import annotations

import asyncio
import inspect
from dataclasses import replace
from datetime import timedelta
from uuid import UUID

import pytest
from sqlalchemy import insert, update
from sqlalchemy.exc import SQLAlchemyError

from polaris.application.evidence import (
    EvidenceRequirementHistoryRejected,
    EvidenceRequirementStore,
    EvidenceRequirementStoreUnavailable,
    EvidenceRequirementVersionAppended,
    ResolvedEvidenceRequirementVersion,
    resolve_requirement_version,
)
from polaris.domain.configuration import SufficiencyRequirementApplicabilityState
from polaris.infrastructure.persistence.postgresql import (
    PostgresEvidenceRequirementStore,
)
from polaris.infrastructure.persistence.postgresql.schema import (
    evidence_requirement_definitions,
    evidence_requirement_set_versions,
)
from tests.configuration_support import (
    RECORDED_AT,
    ROOT_VERSION_ID,
    SECOND_VERSION_ID,
    requirement_key,
    requirement_version,
)

from .conftest import PostgresTestTarget, postgres_row_counts, postgres_store

REQUIREMENT_TABLES = (
    evidence_requirement_set_versions,
    evidence_requirement_definitions,
)


def test_complete_requirement_versions_round_trip_and_resolve_after_restart(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        root = requirement_version(
            sufficiency_applicability=(
                SufficiencyRequirementApplicabilityState.NOT_APPLICABLE
            )
        )
        corrected_with_sufficiency = requirement_version(
            SECOND_VERSION_ID,
            recorded_at=RECORDED_AT + timedelta(minutes=1),
            predecessor_id=ROOT_VERSION_ID,
        )
        corrected = replace(
            corrected_with_sufficiency,
            requirements=(corrected_with_sufficiency.requirements[0],),
        )
        async with postgres_store(
            postgres_target, PostgresEvidenceRequirementStore
        ) as (_, store):
            assert await store.append_requirement_version(root) == (
                EvidenceRequirementVersionAppended(root)
            )
            assert await store.append_requirement_version(corrected) == (
                EvidenceRequirementVersionAppended(corrected)
            )

        async with postgres_store(
            postgres_target, PostgresEvidenceRequirementStore
        ) as (_, restarted):
            history = await restarted.load_requirement_versions()
            assert history == (root, corrected)
            key = requirement_key()
            requirement_id = root.requirements[1].requirement_id
            not_applicable_witness = root.not_applicable_witness(
                requirement_id,
                key,
            )
            assert not_applicable_witness is not None
            assert not_applicable_witness.version_id == root.version_id
            no_requirements_witness = corrected.no_sufficiency_requirements_witness(key)
            assert no_requirements_witness is not None
            assert no_requirements_witness.version_id == corrected.version_id
            result = resolve_requirement_version(
                history,
                key,
                effective_at=RECORDED_AT + timedelta(hours=1),
                known_at=RECORDED_AT + timedelta(hours=1),
            )
            assert result == ResolvedEvidenceRequirementVersion(corrected)

    asyncio.run(scenario())


def test_missing_predecessor_is_rejected_without_partial_write(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        orphan = requirement_version(
            SECOND_VERSION_ID,
            predecessor_id=ROOT_VERSION_ID,
        )
        async with postgres_store(
            postgres_target, PostgresEvidenceRequirementStore
        ) as (engine, store):
            result = await store.append_requirement_version(orphan)
            assert isinstance(result, EvidenceRequirementHistoryRejected)
            assert await postgres_row_counts(engine, *REQUIREMENT_TABLES) == (0, 0)

    asyncio.run(scenario())


class _FailAfterVersionStore(PostgresEvidenceRequirementStore):
    def _write_completed(self, step: str) -> None:
        if step == "version":
            raise RuntimeError("injected transaction failure")


def test_failure_after_version_insert_rolls_back_complete_version(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        async with postgres_store(
            postgres_target,
            _FailAfterVersionStore,
        ) as (engine, store):
            result = await store.append_requirement_version(requirement_version())
            assert isinstance(result, EvidenceRequirementStoreUnavailable)
            assert await postgres_row_counts(engine, *REQUIREMENT_TABLES) == (0, 0)

    asyncio.run(scenario())


def test_requirement_versions_and_definitions_are_database_immutable(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        async with postgres_store(
            postgres_target, PostgresEvidenceRequirementStore
        ) as (engine, store):
            await store.append_requirement_version(requirement_version())
            async with engine.begin() as connection:
                with pytest.raises(SQLAlchemyError):
                    await connection.execute(
                        update(evidence_requirement_set_versions).values(
                            authority_identity="rewritten authority"
                        )
                    )

    asyncio.run(scenario())


def test_database_rejects_non_readiness_sufficiency_role(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        version = requirement_version()
        async with postgres_store(
            postgres_target, PostgresEvidenceRequirementStore
        ) as (engine, store):
            await store.append_requirement_version(version)
            with pytest.raises(SQLAlchemyError):
                async with engine.begin() as connection:
                    await connection.execute(
                        insert(evidence_requirement_definitions).values(
                            set_id=version.set_id.value,
                            version_id=version.version_id.value,
                            requirement_id=UUID("00000000-0000-4000-8000-00000000020c"),
                            position=2,
                            requirement_kind="sufficiency",
                            definition={
                                "minimum_distinct_observations": 1,
                                "qualifying_roles": ["contextual"],
                                "applicability_state": "required",
                                "description": "invalid readiness role",
                            },
                        )
                    )
            assert await postgres_row_counts(engine, *REQUIREMENT_TABLES) == (1, 2)

    asyncio.run(scenario())


def test_inward_requirement_port_exposes_no_database_types() -> None:
    for method_name in (
        "load_requirement_versions",
        "append_requirement_version",
    ):
        signature = str(
            inspect.signature(getattr(EvidenceRequirementStore, method_name))
        )
        assert "sqlalchemy" not in signature.lower()
        assert "asyncpg" not in signature.lower()
        assert "postgres" not in signature.lower()
