from __future__ import annotations

from collections.abc import Sequence
from time import perf_counter
from typing import Protocol

from application.rag.ingestion.curated_rag_models import CuratedRagBuildOptions
from application.rag.ingestion.curated_rag_models import CuratedRagSource
from application.rag.contracts.rag_operation_models import RagIngestOperationRequest
from application.rag.contracts.rag_operation_models import RagOperationDetail
from application.rag.contracts.rag_operation_models import RagOperationResult
from application.rag.contracts.rag_operation_models import RagProjectionConfig
from application.rag.operations.rag_operation_telemetry import RagOperationTelemetry
from application.rag.ingestion.rag_source_loaders import CuratedRagSourceLoaderRegistry
from core.storage.persistence.rag import RagPersistenceResult
from core.storage.persistence.rag import RagSourceEligibilityRecord
from core.storage.persistence.rag import RagPersistenceRepository
from core.telemetry.emitters.application_rag_telemetry import ApplicationRagTelemetry


RAG_INGEST_SOURCE_REPORTS = "reports"
RAG_INGEST_SOURCE_AGENT_SIGNALS = "agent-signals"
RAG_INGEST_SOURCE_RECOMMENDATIONS = "recommendations"
RAG_INGEST_SOURCE_MARKET = "market"
RAG_INGEST_SOURCE_MACRO = "macro"
RAG_INGEST_SOURCE_NEWS = "news"
RAG_INGEST_SOURCE_SENTIMENT = "sentiment"
RAG_INGEST_SOURCE_PORTFOLIO = "portfolio"
RAG_INGEST_SOURCE_BACKTESTS = "backtests"

SUPPORTED_RAG_INGEST_SOURCES = (
    RAG_INGEST_SOURCE_REPORTS,
    RAG_INGEST_SOURCE_AGENT_SIGNALS,
    RAG_INGEST_SOURCE_RECOMMENDATIONS,
    RAG_INGEST_SOURCE_MARKET,
    RAG_INGEST_SOURCE_MACRO,
    RAG_INGEST_SOURCE_NEWS,
    RAG_INGEST_SOURCE_SENTIMENT,
    RAG_INGEST_SOURCE_PORTFOLIO,
    RAG_INGEST_SOURCE_BACKTESTS,
)
IMPLEMENTED_RAG_INGEST_SOURCES = SUPPORTED_RAG_INGEST_SOURCES


class CuratedRagIngestionPort(Protocol):
    async def persist_source(
        self,
        source: CuratedRagSource,
        *,
        options: CuratedRagBuildOptions | None = None,
    ) -> RagPersistenceResult: ...


class GraphDocumentQueuePort(Protocol):
    async def queue_document(self, document_id: str) -> bool: ...


class RagIngestionOperationsService:
    """Ingests eligible canonical PostgreSQL records into the RAG corpus."""

    def __init__(
        self,
        *,
        rag_repository: RagPersistenceRepository,
        source_loader_registry: CuratedRagSourceLoaderRegistry,
        ingestion_service: CuratedRagIngestionPort | None = None,
        graph_document_queue: GraphDocumentQueuePort | None = None,
        projection_config: RagProjectionConfig | None = None,
        telemetry: ApplicationRagTelemetry | None = None,
    ) -> None:
        self._rag_repository = rag_repository
        self._source_loader_registry = source_loader_registry
        self._ingestion_service = ingestion_service
        self._graph_document_queue = graph_document_queue
        self._projection_config = projection_config
        self._telemetry = RagOperationTelemetry(self.__class__.__name__, telemetry)

    async def ingest(
        self,
        request: RagIngestOperationRequest,
    ) -> RagOperationResult:
        operation = "rag.ingest"
        source = normalize_source(request.source)
        await self._telemetry.emit_event(
            "rag.ingestion.source_selection",
            attributes={
                "source": source,
                "supported": source in SUPPORTED_RAG_INGEST_SOURCES,
                "dry_run": request.dry_run,
            },
        )
        if source not in SUPPORTED_RAG_INGEST_SOURCES:
            return unsupported_source_result(
                operation,
                source,
                dry_run=request.dry_run,
            )

        started_at = perf_counter()
        await self._telemetry.emit_started(
            operation,
            details=(RagOperationDetail("source", source),),
        )
        try:
            result = await self._ingest_supported_source(
                source=source,
                request=request,
            )
        except Exception as exc:
            await self._telemetry.emit_failed(
                operation,
                error=exc,
                duration_seconds=perf_counter() - started_at,
            )
            return RagOperationResult.failed(
                operation=operation,
                error=str(exc),
                dry_run=request.dry_run,
            )

        await self._telemetry.emit_completed(
            operation,
            result=result,
            duration_seconds=perf_counter() - started_at,
        )
        return result

    async def _ingest_supported_source(
        self,
        *,
        source: str,
        request: RagIngestOperationRequest,
    ) -> RagOperationResult:
        source_tables = source_tables_for_ingest_source(source)
        eligible_records = await self._list_eligible_source_records(source_tables)
        selected_records = apply_limit(eligible_records, request.limit)
        if request.dry_run:
            return _ingestion_dry_run_result(
                source,
                source_tables,
                eligible_records,
                selected_records,
            )
        if self._ingestion_service is None:
            return RagOperationResult.failed(
                operation="rag.ingest",
                error="Curated RAG ingestion service is not configured.",
            )

        ingested, skipped, failed = await self._persist_selected_sources(
            selected_records,
            request=request,
        )
        details = _ingestion_details(
            source=source,
            source_tables=source_tables,
            eligible_count=len(eligible_records),
            selected_count=len(selected_records),
            ingested=ingested,
            skipped=skipped,
            failed=failed,
            request=request,
        )
        if failed == 0:
            return RagOperationResult.succeeded(
                operation="rag.ingest",
                message=f"RAG ingestion completed for source '{source}'.",
                records_processed=ingested,
                details=details,
            )
        return RagOperationResult.failed(
            operation="rag.ingest",
            error=f"RAG ingestion completed with {failed} failed source(s).",
            details=details,
        )

    async def _persist_selected_sources(
        self,
        records: Sequence[RagSourceEligibilityRecord],
        *,
        request: RagIngestOperationRequest,
    ) -> tuple[int, int, int]:
        ingested = 0
        skipped = 0
        failed = 0
        for eligibility in records:
            source_record = await self._source_loader_registry.load(eligibility)
            if source_record is None:
                skipped += 1
                continue
            persist_result = await self._ingestion_service.persist_source(
                source_record,
                options=CuratedRagBuildOptions(
                    queue_embedding_jobs=request.queue_embedding_jobs,
                    embedding_model=self._embedding_model(),
                    require_source_eligibility=True,
                ),
            )
            if not persist_result.success:
                failed += 1
                continue
            ingested += 1
            if request.queue_graph_jobs and self._graph_document_queue is not None:
                await self._graph_document_queue.queue_document(
                    persist_result.document_id
                )
        return ingested, skipped, failed

    def _embedding_model(self) -> str:
        if self._projection_config is not None:
            return self._projection_config.embedding_model
        return CuratedRagBuildOptions().embedding_model

    async def _list_eligible_source_records(
        self,
        source_tables: tuple[str, ...],
    ) -> tuple[RagSourceEligibilityRecord, ...]:
        records: list[RagSourceEligibilityRecord] = []
        for source_table in source_tables:
            records.extend(
                await self._rag_repository.list_source_eligibility(
                    source_table=source_table,
                    eligible=True,
                )
            )
        return tuple(records)


def normalize_source(source: str) -> str:
    return source.strip().lower().replace("_", "-")


def source_tables_for_ingest_source(source: str) -> tuple[str, ...]:
    source_tables = {
        RAG_INGEST_SOURCE_REPORTS: ("reports",),
        RAG_INGEST_SOURCE_AGENT_SIGNALS: ("agent_signals",),
        RAG_INGEST_SOURCE_RECOMMENDATIONS: (
            "recommendations",
            "recommendation_rationales",
        ),
        RAG_INGEST_SOURCE_MARKET: (
            "technical_analysis_snapshots",
            "market_context_snapshots",
            "market_breadth_snapshots",
        ),
        RAG_INGEST_SOURCE_MACRO: ("macro_regime_snapshots",),
        RAG_INGEST_SOURCE_NEWS: ("news_analysis_snapshots",),
        RAG_INGEST_SOURCE_SENTIMENT: ("sentiment_snapshots",),
        RAG_INGEST_SOURCE_PORTFOLIO: (
            "portfolio_risk_snapshots",
            "portfolio_allocation_snapshots",
        ),
        RAG_INGEST_SOURCE_BACKTESTS: (
            "backtest_runs",
            "backtest_steps",
            "backtest_portfolio_snapshots",
            "backtest_metrics",
            "backtest_artifacts",
        ),
    }
    return source_tables.get(source, ())


def apply_limit[T](records: Sequence[T], limit: int | None) -> tuple[T, ...]:
    selected = tuple(records)
    if limit is None:
        return selected
    return selected[:limit]


def unsupported_source_result(
    operation: str,
    source: str,
    *,
    dry_run: bool,
) -> RagOperationResult:
    return RagOperationResult.failed(
        operation=operation,
        error=(
            f"Unsupported RAG ingestion source '{source}'. Supported sources: "
            f"{', '.join(SUPPORTED_RAG_INGEST_SOURCES)}."
        ),
        dry_run=dry_run,
    )


def _ingestion_dry_run_result(
    source: str,
    source_tables: tuple[str, ...],
    eligible_records: Sequence[RagSourceEligibilityRecord],
    selected_records: Sequence[RagSourceEligibilityRecord],
) -> RagOperationResult:
    return RagOperationResult.succeeded(
        operation="rag.ingest",
        message=f"Dry run complete; eligible '{source}' sources were not ingested.",
        records_processed=len(selected_records),
        dry_run=True,
        details=(
            RagOperationDetail("source", source),
            RagOperationDetail("source_tables", ",".join(source_tables)),
            RagOperationDetail("eligible_sources", str(len(eligible_records))),
            RagOperationDetail("selected_sources", str(len(selected_records))),
        ),
    )


def _ingestion_details(
    *,
    source: str,
    source_tables: tuple[str, ...],
    eligible_count: int,
    selected_count: int,
    ingested: int,
    skipped: int,
    failed: int,
    request: RagIngestOperationRequest,
) -> tuple[RagOperationDetail, ...]:
    return (
        RagOperationDetail("source", source),
        RagOperationDetail("source_tables", ",".join(source_tables)),
        RagOperationDetail("eligible_sources", str(eligible_count)),
        RagOperationDetail("selected_sources", str(selected_count)),
        RagOperationDetail("ingested_sources", str(ingested)),
        RagOperationDetail("skipped_sources", str(skipped)),
        RagOperationDetail("failed_sources", str(failed)),
        RagOperationDetail("queue_embedding_jobs", str(request.queue_embedding_jobs)),
        RagOperationDetail("queue_graph_jobs", str(request.queue_graph_jobs)),
    )
