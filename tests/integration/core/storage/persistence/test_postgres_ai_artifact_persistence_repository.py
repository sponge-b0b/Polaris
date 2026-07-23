from __future__ import annotations

import hashlib
import os
from collections.abc import AsyncIterator
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any, cast
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import Table, delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.database.models.ai_artifacts import AiPromptProgramArtifactModel
from core.database.models.evaluation import EvaluationDatasetModel, EvaluationRunModel
from core.storage.persistence.ai_artifacts import (
    AiArtifactApprovalStatus,
    AiArtifactType,
    AiPromptProgramArtifactRecord,
)
from core.storage.persistence.repositories import (
    PostgresAiArtifactPersistenceRepository,
)

TEST_DATABASE_URL = os.environ.get("POLARIS_TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="POLARIS_TEST_DATABASE_URL is required for AI artifact repository integration tests.",  # noqa: E501
)


@pytest_asyncio.fixture
async def postgres_session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    assert TEST_DATABASE_URL is not None
    engine = create_async_engine(
        TEST_DATABASE_URL,
        future=True,
        pool_pre_ping=True,
    )
    session_factory = async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )

    async with engine.begin() as connection:
        await connection.run_sync(_create_required_tables)

    yield session_factory

    await engine.dispose()


def _create_required_tables(sync_connection: Any) -> None:
    for model in (
        EvaluationDatasetModel,
        EvaluationRunModel,
        AiPromptProgramArtifactModel,
    ):
        cast(Table, model.__table__).create(sync_connection, checkfirst=True)


async def _delete_test_records(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    target_component: str,
) -> None:
    async with session_factory() as session:
        await session.execute(
            delete(AiPromptProgramArtifactModel).where(
                AiPromptProgramArtifactModel.target_component == target_component,
            )
        )
        await session.commit()


@pytest.mark.asyncio
async def test_postgres_ai_artifact_repository_create_read_list_approve_deactivate(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    target_component = f"integration.rag.answer_generation.{uuid4().hex}"
    record = _record(target_component=target_component)

    await _delete_test_records(
        postgres_session_factory,
        target_component=target_component,
    )

    try:
        async with postgres_session_factory() as session:
            repository = PostgresAiArtifactPersistenceRepository(session)
            created = await repository.upsert_artifact(record)

        assert created.artifact_id == record.artifact_id
        assert created.active is False
        assert created.approval_status is AiArtifactApprovalStatus.DRAFT

        async with postgres_session_factory() as session:
            repository = PostgresAiArtifactPersistenceRepository(session)
            loaded = await repository.get_artifact(record.artifact_id)
            listed = await repository.list_artifacts(
                target_component=target_component,
                artifact_type=AiArtifactType.SOURCE_CONTROLLED_PROMPT,
            )
            approved = await repository.approve_artifact(
                record.artifact_id,
                approved_by="integration-test-reviewer",
                approved_at=datetime(2026, 7, 15, tzinfo=UTC),
            )

        assert loaded == created
        assert tuple(item.artifact_id for item in listed) == (record.artifact_id,)
        assert approved is not None
        assert approved.active is False
        assert approved.approval_status is AiArtifactApprovalStatus.APPROVED

        async with postgres_session_factory() as session:
            repository = PostgresAiArtifactPersistenceRepository(session)
            activated = await repository.upsert_artifact(replace(approved, active=True))
            active = await repository.get_active_artifact(target_component)
            deactivated = await repository.deactivate_artifact(record.artifact_id)

        assert activated.active is True
        assert active is not None
        assert active.artifact_id == record.artifact_id
        assert deactivated is not None
        assert deactivated.active is False
        assert deactivated.approval_status is AiArtifactApprovalStatus.INACTIVE
    finally:
        await _delete_test_records(
            postgres_session_factory,
            target_component=target_component,
        )


def _record(*, target_component: str) -> AiPromptProgramArtifactRecord:
    return AiPromptProgramArtifactRecord(
        artifact_id=f"artifact-{uuid4().hex}",
        artifact_type=AiArtifactType.SOURCE_CONTROLLED_PROMPT,
        artifact_name=f"rag-answer-prompt-{uuid4().hex}",
        artifact_version="2026.07.15",
        target_component=target_component,
        model_name="qwen3.5:4b",
        provider_name="ollama",
        prompt_reference="prompts/rag/answer_generation.md",
        prompt_hash=hashlib.sha256(b"canonical prompt fixture").hexdigest(),
        source="source_control",
        deepeval_score_summary={"answer_relevancy": 0.95, "faithfulness": 0.93},
        langfuse_trace_id="trace-ai-artifact-integration",
    )
