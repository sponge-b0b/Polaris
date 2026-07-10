from __future__ import annotations

import inspect
from dataclasses import dataclass
from datetime import datetime
from datetime import timezone
from typing import Any

from application.persistence import AgentIntelligencePersistenceService
from application.persistence import AttributionPersistenceService
from application.persistence import MacroPersistenceService
from application.persistence import MarketPersistenceService
from application.persistence import NewsPersistenceService
from application.persistence import PortfolioPersistenceService
from application.persistence import RecommendationPersistenceService
from application.persistence import ReportPersistenceService
from application.persistence import SentimentPersistenceService
from core.database.models.agent_intelligence import AgentReasoningModel
from core.database.models.agent_intelligence import AgentRecommendationModel
from core.database.models.agent_intelligence import AgentRiskAssessmentModel
from core.database.models.agent_signals import AgentSignalModel
from core.database.models.attribution import AttributionRecordModel
from core.database.models.attribution import RecommendationAttributionModel
from core.database.models.attribution import SignalAttributionModel
from core.database.models.macro import MacroRegimeSnapshotModel
from core.database.models.market import TechnicalAnalysisSnapshotModel
from core.database.models.news import NewsAnalysisSnapshotModel
from core.database.models.portfolio import PortfolioAllocationSnapshotModel
from core.database.models.portfolio import PortfolioExposureSnapshotModel
from core.database.models.portfolio import PortfolioPositionHistoryModel
from core.database.models.portfolio import PortfolioPositionLatestModel
from core.database.models.portfolio import PortfolioRiskSnapshotModel
from core.database.models.portfolio_state import PortfolioStateHistoryModel
from core.database.models.recommendations import RecommendationModel
from core.database.models.recommendations import TradeSetupModel
from core.database.models.recommendations import WatchlistItemModel
from core.database.models.reports import ReportModel
from core.database.models.reports import ReportSectionModel
from core.database.models.sentiment import SentimentSnapshotModel
from core.storage.persistence.rag import RagDocumentRecord
from core.storage.persistence.rag import RagPersistenceRepository
from core.storage.persistence.repositories import PostgresRagPersistenceRepository


@dataclass(
    frozen=True,
    slots=True,
)
class RagCanonicalSource:
    name: str
    source_type: str
    models: tuple[type[Any], ...]
    service_type: type[Any] | None

    @property
    def table_names(
        self,
    ) -> tuple[str, ...]:
        return tuple(model.__tablename__ for model in self.models)


_CANONICAL_RAG_SOURCES: tuple[RagCanonicalSource, ...] = (
    RagCanonicalSource(
        name="reports",
        source_type="report",
        models=(
            ReportModel,
            ReportSectionModel,
        ),
        service_type=ReportPersistenceService,
    ),
    RagCanonicalSource(
        name="agent_signals_and_intelligence",
        source_type="agent_intelligence",
        models=(
            AgentSignalModel,
            AgentReasoningModel,
            AgentRecommendationModel,
            AgentRiskAssessmentModel,
        ),
        service_type=AgentIntelligencePersistenceService,
    ),
    RagCanonicalSource(
        name="recommendations",
        source_type="recommendation",
        models=(
            RecommendationModel,
            TradeSetupModel,
            WatchlistItemModel,
        ),
        service_type=RecommendationPersistenceService,
    ),
    RagCanonicalSource(
        name="portfolio_snapshots",
        source_type="portfolio_snapshot",
        models=(
            PortfolioStateHistoryModel,
            PortfolioPositionHistoryModel,
            PortfolioPositionLatestModel,
            PortfolioExposureSnapshotModel,
            PortfolioRiskSnapshotModel,
            PortfolioAllocationSnapshotModel,
        ),
        service_type=PortfolioPersistenceService,
    ),
    RagCanonicalSource(
        name="technical_snapshots",
        source_type="technical_snapshot",
        models=(TechnicalAnalysisSnapshotModel,),
        service_type=MarketPersistenceService,
    ),
    RagCanonicalSource(
        name="macro_snapshots",
        source_type="macro_snapshot",
        models=(MacroRegimeSnapshotModel,),
        service_type=MacroPersistenceService,
    ),
    RagCanonicalSource(
        name="news_summaries",
        source_type="news_summary",
        models=(NewsAnalysisSnapshotModel,),
        service_type=NewsPersistenceService,
    ),
    RagCanonicalSource(
        name="sentiment_snapshots",
        source_type="sentiment_snapshot",
        models=(SentimentSnapshotModel,),
        service_type=SentimentPersistenceService,
    ),
    RagCanonicalSource(
        name="attribution_references",
        source_type="attribution_reference",
        models=(
            AttributionRecordModel,
            SignalAttributionModel,
            RecommendationAttributionModel,
        ),
        service_type=AttributionPersistenceService,
    ),
)

_EXCLUDED_RAW_OPERATIONAL_TABLES = frozenset(
    {
        "workflow_events",
        "workflow_node_runs",
        "workflow_runs",
        "telemetry_events",
        "telemetry_metrics",
        "telemetry_traces",
        "workflow_metrics",
        "agent_metrics",
        "provider_metrics",
    }
)


def test_v2_canonical_rag_sources_have_postgres_tables_and_services() -> None:
    source_names = {source.name for source in _CANONICAL_RAG_SOURCES}

    assert source_names == {
        "reports",
        "agent_signals_and_intelligence",
        "recommendations",
        "portfolio_snapshots",
        "technical_snapshots",
        "macro_snapshots",
        "news_summaries",
        "sentiment_snapshots",
        "attribution_references",
    }
    for source in _CANONICAL_RAG_SOURCES:
        assert source.table_names
        assert all(table_name for table_name in source.table_names)
        assert source.service_type is not None
        assert source.service_type.__name__.endswith("PersistenceService")


def test_rag_documents_reference_curated_postgres_sources_before_projection() -> None:
    documents = tuple(_document_for_source(source) for source in _CANONICAL_RAG_SOURCES)

    assert {document.source_table for document in documents} == {
        source.table_names[0] for source in _CANONICAL_RAG_SOURCES
    }
    assert all(document.source_id.endswith(":source-1") for document in documents)
    assert all(
        document.content_text.startswith("Curated source text")
        for document in documents
    )
    assert all(
        document.metadata["projection_status"] == "not_projected"
        for document in documents
    )


def test_raw_runtime_and_telemetry_tables_are_not_rag_canonical_sources() -> None:
    canonical_tables = {
        table_name
        for source in _CANONICAL_RAG_SOURCES
        for table_name in source.table_names
    }

    assert canonical_tables.isdisjoint(_EXCLUDED_RAW_OPERATIONAL_TABLES)


def test_rag_repository_scope_stops_before_vector_store_writes() -> None:
    expected_methods = {
        "get_canonical_record_counts",
        "get_document",
        "get_query_log",
        "get_source_eligibility",
        "list_answer_logs",
        "list_chunks",
        "get_chunk",
        "list_chunks_by_metadata",
        "list_embedding_jobs",
        "list_graph_jobs",
        "list_source_eligibility",
        "mark_source_eligibility",
        "persist_answer_log",
        "persist_document",
        "persist_embedding_job",
        "persist_graph_job",
        "persist_query_log",
        "unmark_source_eligibility",
    }

    assert _public_async_method_names(RagPersistenceRepository) == expected_methods
    assert (
        _public_async_method_names(PostgresRagPersistenceRepository) == expected_methods
    )
    assert not any(
        method_name
        for method_name in expected_methods
        if "vector" in method_name or method_name.startswith("write_embedding")
    )


def _document_for_source(
    source: RagCanonicalSource,
) -> RagDocumentRecord:
    table_name = source.table_names[0]
    return RagDocumentRecord(
        document_id=f"rag_document:{table_name}:{source.source_type}:{source.name}:source-1",
        source_table=table_name,
        source_id=f"{source.name}:source-1",
        source_type=source.source_type,
        title=f"RAG readiness source: {source.name}",
        content_text=f"Curated source text for {source.name}.",
        generated_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
        metadata={
            "canonical_source": source.name,
            "projection_status": "not_projected",
        },
    )


def _public_async_method_names(
    target: type[Any],
) -> frozenset[str]:
    return frozenset(
        name
        for name, member in inspect.getmembers(
            target,
            predicate=inspect.isfunction,
        )
        if not name.startswith("_") and _is_async_function(member)
    )


def _is_async_function(
    member: Any,
) -> bool:
    return inspect.iscoroutinefunction(member)
