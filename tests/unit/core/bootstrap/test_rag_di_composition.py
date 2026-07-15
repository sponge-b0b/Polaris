from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest

from application.rag.operations.rag_embedding_operations import (
    RagEmbeddingJobOperationsService,
)
from application.rag.operations.rag_ingestion_operations import (
    RagIngestionOperationsService,
)
from application.rag.operations.rag_projection_operations import (
    RagProjectionOperationsService,
)
from application.rag.operations.rag_status_operations import RagStatusOperationsService
from application.rag.rag_service import RagService
from config.settings import Settings
from core.bootstrap.di_providers import get_async_di_container
import core.storage.rag_di as rag_di
from core.storage.persistence.rag import RagPersistenceRepository
from core.telemetry.emitters.application_rag_telemetry import ApplicationRagTelemetry
from core.telemetry.emitters.integration_telemetry import IntegrationTelemetry
from core.telemetry.observability.observability_manager import ObservabilityManager
from integration.clients.rag import bge_m3_embedding_client
from integration.clients.rag import neo4j_rag_client
from integration.clients.rag import qdrant_rag_client
from integration.clients.rag.neo4j_rag_client import Neo4jRagClient
from integration.clients.rag.qdrant_rag_client import QdrantRagClient


class _FakeBgeM3Encoder:
    def encode(
        self,
        sentences: list[str],
        *,
        return_dense: bool,
        return_sparse: bool,
        return_colbert_vecs: bool,
    ) -> Mapping[str, object]:
        raise AssertionError("The composition test must not execute embedding work.")


class _FakeAsyncSession:
    def __init__(self) -> None:
        self.exit_calls = 0

    async def __aenter__(self) -> _FakeAsyncSession:
        return self

    async def __aexit__(self, *args: object) -> None:
        self.exit_calls += 1


class _FakeQdrantClient:
    def __init__(self) -> None:
        self.close_calls = 0

    async def close(self) -> None:
        self.close_calls += 1


class _FakeNeo4jDriver:
    def __init__(self) -> None:
        self.close_calls = 0

    async def execute_query(self, *args: Any, **kwargs: Any) -> object:
        raise AssertionError("The composition test must not execute Neo4j queries.")

    async def verify_connectivity(self, **config: Any) -> None:
        raise AssertionError("The composition test must not contact Neo4j.")

    async def close(self) -> None:
        self.close_calls += 1


@pytest.mark.asyncio
async def test_async_application_container_composes_shared_rag_resources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    encoder = _FakeBgeM3Encoder()
    driver = _FakeNeo4jDriver()
    raw_qdrant_client = _FakeQdrantClient()
    sessions: list[_FakeAsyncSession] = []
    monkeypatch.setattr(
        bge_m3_embedding_client,
        "BGEM3FlagModel",
        lambda *args, **kwargs: encoder,
    )
    monkeypatch.setattr(
        neo4j_rag_client.AsyncGraphDatabase,
        "driver",
        lambda *args, **kwargs: driver,
    )
    monkeypatch.setattr(
        qdrant_rag_client,
        "AsyncQdrantClient",
        lambda *args, **kwargs: raw_qdrant_client,
    )
    monkeypatch.setattr(
        rag_di,
        "AsyncSessionLocal",
        lambda: _new_fake_session(sessions),
    )

    settings = Settings(RAG_WEB_FALLBACK_ENABLED=False)
    container = get_async_di_container(settings)
    try:
        async with container() as request_container:
            rag_service = await request_container.get(RagService)
            ingestion_operations = await request_container.get(
                RagIngestionOperationsService
            )
            embedding_operations = await request_container.get(
                RagEmbeddingJobOperationsService
            )
            projection_operations = await request_container.get(
                RagProjectionOperationsService
            )
            status_operations = await request_container.get(RagStatusOperationsService)
            observability = await request_container.get(ObservabilityManager)
            application_telemetry = await request_container.get(ApplicationRagTelemetry)
            integration_telemetry = await request_container.get(IntegrationTelemetry)
            repository = await request_container.get(RagPersistenceRepository)
            neo4j_client = await request_container.get(Neo4jRagClient)
            qdrant_client = await request_container.get(QdrantRagClient)

            assert await request_container.get(RagService) is rag_service
            assert (
                await request_container.get(RagIngestionOperationsService)
                is ingestion_operations
            )
            assert (
                await request_container.get(RagEmbeddingJobOperationsService)
                is embedding_operations
            )
            assert (
                await request_container.get(RagProjectionOperationsService)
                is projection_operations
            )
            assert (
                await request_container.get(RagStatusOperationsService)
                is status_operations
            )
            assert await request_container.get(RagPersistenceRepository) is repository
            assert await request_container.get(Neo4jRagClient) is neo4j_client
            assert await request_container.get(QdrantRagClient) is qdrant_client
            assert application_telemetry.observability_manager is observability
            assert integration_telemetry.observability_manager is observability
            assert rag_service._repository is repository
            assert ingestion_operations._rag_repository is repository
            assert embedding_operations._rag_repository is repository
            assert projection_operations._rag_repository is repository
            assert status_operations._rag_repository is repository

        async with container() as second_request_container:
            second_rag_service = await second_request_container.get(RagService)
            second_repository = await second_request_container.get(
                RagPersistenceRepository
            )

            assert second_rag_service is not rag_service
            assert second_repository is not repository
            assert (
                await second_request_container.get(ObservabilityManager)
                is observability
            )
            assert await second_request_container.get(Neo4jRagClient) is neo4j_client
            assert await second_request_container.get(QdrantRagClient) is qdrant_client
    finally:
        await container.close()

    assert driver.close_calls == 1
    assert raw_qdrant_client.close_calls == 1
    assert len(sessions) == 2
    assert [session.exit_calls for session in sessions] == [1, 1]


def _new_fake_session(
    sessions: list[_FakeAsyncSession],
) -> _FakeAsyncSession:
    session = _FakeAsyncSession()
    sessions.append(session)
    return session
