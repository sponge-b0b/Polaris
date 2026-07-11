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


def test_entity_extractor_projects_strategy_decision_hypothesis_graph() -> None:
    document = _document(
        source_table="strategy_synthesis_decisions",
        source_id="decision-1",
        source_type="strategy_synthesis_decision",
        metadata={
            "symbol": "SPY",
            "selected_perspective": "bull",
            "selected_hypothesis_id": "hypothesis-bull",
            "selection_status": "selected",
            "related_hypothesis_ids": ["hypothesis-bull", "hypothesis-bear"],
            "related_hypotheses": [
                {
                    "hypothesis_id": "hypothesis-bull",
                    "symbol": "SPY",
                    "perspective": "bull",
                    "confidence": 0.82,
                    "hypothesis_strength": 0.76,
                    "directional_bias": 0.65,
                    "invalidated": False,
                    "supporting_evidence": [
                        {
                            "source": "technical",
                            "name": "breadth expansion",
                            "description": "breadth expanded across sectors",
                        }
                    ],
                    "contradicting_evidence": [
                        {
                            "source": "macro",
                            "name": "macro risk",
                            "description": "macro risk remains elevated",
                        }
                    ],
                    "invalidation_conditions": [
                        {
                            "name": "50dma break",
                            "condition": "SPY closes below 50dma",
                            "operator": "less_than",
                            "threshold": 500.0,
                        }
                    ],
                },
                {
                    "hypothesis_id": "hypothesis-bear",
                    "symbol": "SPY",
                    "perspective": "bear",
                    "confidence": 0.35,
                    "hypothesis_strength": 0.32,
                    "directional_bias": -0.4,
                    "invalidated": False,
                },
            ],
            "related_evaluations": [
                {
                    "evaluation_id": "evaluation-bull",
                    "hypothesis_id": "hypothesis-bull",
                    "perspective": "bull",
                    "perspective_weight": 0.5,
                    "synthesis_weight": 0.7,
                    "candidate_score": 0.75,
                    "contradiction_burden": 0.1,
                    "assumption_support": 0.8,
                    "rank": 1,
                    "selection_status": "selected",
                    "invalidated": False,
                }
            ],
        },
    )

    projection = RagGraphEntityExtractor().extract(document)

    relationship_types = {
        relationship.relationship_type for relationship in projection.relationships
    }
    assert GraphRelationshipType.DECISION_EVALUATED_HYPOTHESIS in relationship_types
    assert GraphRelationshipType.DECISION_SELECTED_HYPOTHESIS in relationship_types
    assert GraphRelationshipType.HYPOTHESIS_SUPPORTED_BY in relationship_types
    assert GraphRelationshipType.HYPOTHESIS_CONTRADICTED_BY in relationship_types
    assert GraphRelationshipType.HYPOTHESIS_INVALIDATED_BY in relationship_types
    assert {node.node_id for node in projection.nodes} >= {
        "strategy_hypothesis:hypothesis-bull",
        "strategy_hypothesis:hypothesis-bear",
        "strategy_evidence:hypothesis-bull:supporting:1",
        "strategy_evidence:hypothesis-bull:contradicting:1",
        "strategy_evidence:hypothesis-bull:invalidation:1",
    }
    selected_relationship = next(
        relationship
        for relationship in projection.relationships
        if relationship.relationship_type
        is GraphRelationshipType.DECISION_SELECTED_HYPOTHESIS
    )
    assert selected_relationship.end_node_id == "strategy_hypothesis:hypothesis-bull"
    assert selected_relationship.properties["synthesis_weight"] == 0.7


def test_entity_extractor_projects_standalone_strategy_hypothesis_evidence() -> None:
    document = _document(
        source_table="strategy_hypotheses",
        source_id="hypothesis-bull",
        source_type="strategy_hypothesis",
        metadata={
            "symbol": "SPY",
            "perspective": "bull",
            "supporting_evidence": [
                {"name": "breadth expansion", "description": "breadth expanded"}
            ],
            "contradicting_evidence": [
                {"name": "macro risk", "description": "macro risk remains elevated"}
            ],
            "invalidation_conditions": [
                {"name": "50dma break", "condition": "SPY closes below 50dma"}
            ],
        },
    )

    projection = RagGraphEntityExtractor().extract(document)

    assert {
        relationship.relationship_type for relationship in projection.relationships
    } >= {
        GraphRelationshipType.HYPOTHESIS_SUPPORTED_BY,
        GraphRelationshipType.HYPOTHESIS_CONTRADICTED_BY,
        GraphRelationshipType.HYPOTHESIS_INVALIDATED_BY,
    }


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
