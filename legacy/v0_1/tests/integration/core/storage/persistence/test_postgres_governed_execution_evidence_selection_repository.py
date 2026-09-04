from __future__ import annotations

import os
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.database.models.governed_execution_evidence_selection import (
    GovernedExecutionEvidenceSelectionModel,
)
from core.storage.persistence.governed_execution_evidence import (
    GovernedExecutionEvidenceSelection,
    GovernedExecutionEvidenceSelectionConflictError,
)
from core.storage.persistence.repositories import (
    PostgresGovernedExecutionEvidenceSelectionRepository,
)
from core.workflow.registry.workflow_registry import WorkflowIdentity
from domain.authority import RiskTier

TEST_DATABASE_URL = os.environ.get("POLARIS_TEST_DATABASE_URL")
_EXECUTION_ID = "ticket-159-selection-repository"
_IDENTITY = WorkflowIdentity(
    workflow_name="ticket-159-workflow",
    definition_fingerprint="ticket-159-definition",
)

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="POLARIS_TEST_DATABASE_URL is required for Postgres persistence tests.",
)


@pytest_asyncio.fixture
async def postgres_session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    assert TEST_DATABASE_URL is not None
    engine = create_async_engine(TEST_DATABASE_URL, future=True, pool_pre_ping=True)
    yield async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    await engine.dispose()


@pytest.mark.asyncio
async def test_selection_repository_enforces_one_record_per_execution_identity(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _delete_selection(postgres_session_factory)
    selection = GovernedExecutionEvidenceSelection(
        execution_id=_EXECUTION_ID,
        identity=_IDENTITY,
        risk_tier=RiskTier.BASELINE,
        evidence_id="baseline:ticket-159-selection-repository",
    )
    try:
        async with postgres_session_factory() as session:
            repository = PostgresGovernedExecutionEvidenceSelectionRepository(session)
            await repository.create(selection)

        async with postgres_session_factory() as session:
            repository = PostgresGovernedExecutionEvidenceSelectionRepository(session)
            assert await repository.get(
                execution_id=_EXECUTION_ID,
                identity=_IDENTITY,
            ) == (selection,)
            with pytest.raises(GovernedExecutionEvidenceSelectionConflictError):
                await repository.create(selection)
    finally:
        await _delete_selection(postgres_session_factory)


async def _delete_selection(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with postgres_session_factory() as session:
        await session.execute(
            delete(GovernedExecutionEvidenceSelectionModel).where(
                GovernedExecutionEvidenceSelectionModel.execution_id == _EXECUTION_ID
            )
        )
        await session.commit()
