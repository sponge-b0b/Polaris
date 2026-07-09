from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC
from datetime import datetime
from typing import cast

import pytest

from application.rag.projections.graph_projection import GraphProjectionJobProcessor
from application.rag.projections.graph_projection import Neo4jGraphRetriever
from application.rag.projections.graph_projection import RagGraphEntityExtractor
from application.rag.contracts.rag_context import RagRetrievalFilters
from application.rag.contracts.rag_request import RagRequest
from core.storage.persistence.rag import JsonObject
from core.storage.persistence.rag import RagDocumentRecord
from core.storage.persistence.rag import RagGraphJobRecord
from core.storage.persistence.rag import RagPersistenceRepository
from core.storage.persistence.rag import RagRecordPersistenceResult
from core.telemetry.emitters.application_rag_telemetry import ApplicationRagTelemetry
from core.telemetry.observability.observability_manager import ObservabilityManager
from core.telemetry.sinks.telemetry_sink import InMemoryTelemetrySink
from integration.providers.rag.graph_projection_models import GraphNodeType
from integration.providers.rag.graph_projection_models import GraphProjection
from integration.providers.rag.graph_projection_models import GraphRelationshipType
from integration.providers.rag.graph_projection_models import GraphSearchQuery
from integration.providers.rag.graph_projection_models import GraphSearchResult
from integration.providers.rag.graph_projection_models import GraphStoreStatus
from integration.providers.rag.graph_projection_provider import GraphProjectionProvider


class FakeRepository:
    def __init__(
        self,
        *,
        documents: tuple[RagDocumentRecord, ...] = (),
        jobs: tuple[RagGraphJobRecord, ...] = (),
    ) -> None:
        self.documents = {document.document_id: document for document in documents}
        self.jobs = {job.job_id: job for job in jobs}

    async def get_document(self, document_id: str) -> RagDocumentRecord | None:
        return self.documents.get(document_id)

    async def list_graph_jobs(
        self,
        *,
        status: str | None = None,
    ) -> Sequence[RagGraphJobRecord]:
        jobs = tuple(self.jobs.values())
        if status is None:
            return jobs
        return tuple(job for job in jobs if job.status == status)

    async def persist_graph_job(
        self,
        job: RagGraphJobRecord,
    ) -> RagRecordPersistenceResult:
        self.jobs[job.job_id] = job
        return RagRecordPersistenceResult.succeeded(record_id=job.job_id)


class FakeGraphProvider:
    def __init__(
        self,
        *,
        search_results: tuple[GraphSearchResult, ...] = (),
        cleared_count: int = 0,
    ) -> None:
        self.search_results = search_results
        self.cleared_count = cleared_count
        self.projections: list[GraphProjection] = []
        self.searches: list[GraphSearchQuery] = []

    async def upsert_projection(self, projection: GraphProjection) -> None:
        self.projections.append(projection)

    async def search(
        self,
        query: GraphSearchQuery,
    ) -> tuple[GraphSearchResult, ...]:
        self.searches.append(query)
        return self.search_results

    async def clear_projection(self) -> int:
        self.projections.clear()
        return self.cleared_count

    async def status(self) -> GraphStoreStatus:
        return GraphStoreStatus(healthy=True, entity_count=len(self.projections))


def test_entity_extractor_builds_master_graph_entities_deterministically() -> None:
    document = _document(
        source_table="agent_signals",
        source_id="signal-1",
        source_type="technical_signal",
        metadata={
            "symbol": "spy",
            "technical_regime": "risk_on",
            "recommendation_id": "recommendation-1",
        },
    )

    projection = RagGraphEntityExtractor().extract(document)

    assert {node.node_type for node in projection.nodes} == {
        GraphNodeType.AGENT_SIGNAL,
        GraphNodeType.WORKFLOW_RUN,
        GraphNodeType.SYMBOL,
        GraphNodeType.TECHNICAL_REGIME,
        GraphNodeType.RECOMMENDATION,
    }
    assert {
        relationship.relationship_type for relationship in projection.relationships
    } == {
        GraphRelationshipType.PRODUCED,
        GraphRelationshipType.MENTIONS,
        GraphRelationshipType.HAS_REGIME,
        GraphRelationshipType.SUPPORTS,
    }
    assert projection == RagGraphEntityExtractor().extract(document)


def test_entity_extractor_maps_news_themes_and_risk_constraints() -> None:
    news = _document(
        document_id="document-news",
        source_table="news_analysis_snapshots",
        source_id="news-1",
        source_type="news_analysis",
        metadata={
            "themes": ["AI spending", "Liquidity"],
            "recommendation_id": "recommendation-1",
        },
    )
    risk = _document(
        document_id="document-risk",
        source_table="portfolio_risk_snapshots",
        source_id="risk-1",
        source_type="portfolio_risk",
        metadata={"recommendation_id": "recommendation-1"},
    )

    news_projection = RagGraphEntityExtractor().extract(news)
    risk_projection = RagGraphEntityExtractor().extract(risk)

    assert GraphRelationshipType.INFLUENCES in {
        relationship.relationship_type for relationship in news_projection.relationships
    }
    assert GraphRelationshipType.CONSTRAINS in {
        relationship.relationship_type for relationship in risk_projection.relationships
    }
    assert (
        len(
            [
                node
                for node in news_projection.nodes
                if node.node_type is GraphNodeType.NEWS_THEME
            ]
        )
        == 3
    )


@pytest.mark.asyncio
async def test_graph_processor_queues_processes_and_rebuilds_from_postgres_jobs() -> (
    None
):
    document = _document()
    repository = FakeRepository(documents=(document,))
    provider = FakeGraphProvider(cleared_count=4)
    processor = GraphProjectionJobProcessor(
        repository=cast(RagPersistenceRepository, repository),
        provider=cast(GraphProjectionProvider, provider),
    )

    assert await processor.queue_document(document.document_id) is True
    assert await processor.queue_document(document.document_id) is False

    processed = await processor.process_queued_jobs()

    assert processed.processed_count == 1
    assert processed.completed_count == 1
    assert tuple(repository.jobs.values())[0].status == "completed"
    assert len(provider.projections) == 1

    rebuilt = await processor.rebuild()

    assert rebuilt.cleared_entity_count == 4
    assert rebuilt.completed_count == 1
    assert tuple(repository.jobs.values())[0].status == "completed"
    assert len(provider.projections) == 1


@pytest.mark.asyncio
async def test_graph_processor_emits_job_failure_and_batch_completion_telemetry() -> (
    None
):
    sink = InMemoryTelemetrySink()
    observability = ObservabilityManager()
    observability.add_sink(sink)
    repository = FakeRepository()
    processor = GraphProjectionJobProcessor(
        repository=cast(RagPersistenceRepository, repository),
        provider=cast(GraphProjectionProvider, FakeGraphProvider()),
        telemetry=ApplicationRagTelemetry(observability),
    )
    await processor.queue_document("missing-document")

    result = await processor.process_queued_jobs()

    assert result.failed_count == 1
    assert [event.attributes["operation"] for event in sink.events] == [
        "rag.graph.process",
        "rag.graph.job",
        "rag.graph.job",
        "rag.graph.process",
    ]
    assert sink.events[2].event_type == "application.rag.operation.failed"
    assert sink.events[2].payload["error_type"] == "LookupError"
    assert sink.events[-1].attributes["failed_count"] == 1


@pytest.mark.asyncio
async def test_graph_retriever_rehydrates_canonical_postgres_document() -> None:
    document = _document()
    repository = FakeRepository(documents=(document,))
    provider = FakeGraphProvider(
        search_results=(
            GraphSearchResult(
                document_id=document.document_id,
                source_id=document.source_id,
                source_type=document.source_type,
                title=document.title,
                score=2.01,
                related_entities=("SPY", "risk_on"),
            ),
        )
    )
    retriever = Neo4jGraphRetriever(
        repository=cast(RagPersistenceRepository, repository),
        provider=cast(GraphProjectionProvider, provider),
    )

    contexts = await retriever.retrieve(
        RagRequest(
            query="SPY breadth",
            filters=RagRetrievalFilters(symbols=("SPY",)),
            top_k=3,
        )
    )

    assert len(contexts) == 1
    assert contexts[0].text == document.content_text
    assert contexts[0].retrieval_route == "graph"
    assert contexts[0].source.document_id == document.document_id
    assert contexts[0].metadata["related_entities"] == ["SPY", "risk_on"]
    assert provider.searches[0].symbols == ("SPY",)


def _document(
    *,
    document_id: str = "document-1",
    source_table: str = "reports",
    source_id: str = "report-1",
    source_type: str = "morning_report",
    metadata: JsonObject | None = None,
) -> RagDocumentRecord:
    return RagDocumentRecord(
        document_id=document_id,
        source_table=source_table,
        source_id=source_id,
        source_type=source_type,
        title="Market Breadth Report",
        content_text="SPY breadth is strong in the risk-on regime.",
        generated_at=datetime(2026, 6, 24, tzinfo=UTC),
        workflow_name="morning_report",
        execution_id="execution-1",
        metadata=metadata or {"symbols": ["SPY"], "regime": "risk_on"},
    )
