from __future__ import annotations

from time import perf_counter
from typing import Any

from application.rag.ingestion.curated_rag_bundle_persistence import (
    CuratedRagBundlePersister,
)
from application.rag.ingestion.curated_rag_chunking import (
    build_agent_signal_chunks,
    build_report_chunks,
)
from application.rag.ingestion.curated_rag_document_factory import (
    CuratedRagDocumentFactory,
)
from application.rag.ingestion.curated_rag_jobs import build_embedding_jobs
from application.rag.ingestion.curated_rag_metadata import (
    eligibility_error_message,
    evaluate_source_eligibility,
    raise_if_ineligible,
    resolve_persisted_or_default_eligibility,
)
from application.rag.ingestion.curated_rag_models import (
    CuratedRagBuildOptions,
    CuratedRagSource,
)
from application.rag.ingestion.curated_rag_structured_sources import (
    build_structured_source_bundle,
    is_structured_curated_rag_source,
    require_structured_source_spec,
    structured_source_id,
)
from core.storage.persistence.agent_signals import AgentSignalRecord
from core.storage.persistence.rag import (
    RagPersistenceBundle,
    RagPersistenceRepository,
    RagPersistenceResult,
    RagSourceEligibilityRecord,
)
from core.storage.persistence.reports import ReportRecord
from core.telemetry.emitters.application_rag_telemetry import ApplicationRagTelemetry


class CuratedRagDocumentBuilder:
    """
    Builds canonical RAG bundles from curated PostgreSQL source records only.

    Supported sources are intentionally curated: persisted reports, persisted
    agent signals, and typed analytical PostgreSQL records such as recommendations,
    regime snapshots, market summaries, portfolio snapshots, and backtest summaries.
    Raw runtime dumps are not accepted because vector/RAG stores must be derived
    from curated Postgres records.
    """

    def __init__(
        self,
        document_factory: CuratedRagDocumentFactory | None = None,
    ) -> None:
        self._document_factory = document_factory or CuratedRagDocumentFactory()

    def build_from_source(
        self,
        source: CuratedRagSource,
        *,
        options: CuratedRagBuildOptions | None = None,
        source_eligibility: RagSourceEligibilityRecord | None = None,
    ) -> RagPersistenceBundle:
        resolved_options = options or CuratedRagBuildOptions()

        if isinstance(
            source,
            ReportRecord,
        ):
            return self.build_from_report(
                source,
                options=resolved_options,
                source_eligibility=source_eligibility,
            )

        if isinstance(
            source,
            AgentSignalRecord,
        ):
            return self.build_from_agent_signal(
                source,
                options=resolved_options,
                source_eligibility=source_eligibility,
            )

        if is_structured_curated_rag_source(
            source,
        ):
            return self.build_from_structured_source(
                source,
                options=resolved_options,
                source_eligibility=source_eligibility,
            )

        raise TypeError(
            "RAG documents must be built from curated PostgreSQL source records; "
            "raw runtime dumps, telemetry, provider payloads, and arbitrary JSON "
            "payloads are not supported."
        )

    def build_from_report(
        self,
        report: ReportRecord,
        *,
        options: CuratedRagBuildOptions | None = None,
        source_eligibility: RagSourceEligibilityRecord | None = None,
    ) -> RagPersistenceBundle:
        resolved_options = options or CuratedRagBuildOptions()
        eligibility = source_eligibility or evaluate_source_eligibility(
            report,
        )
        raise_if_ineligible(
            eligibility,
            options=resolved_options,
        )
        document = self._document_factory.build_report_document(
            report,
            eligibility=eligibility,
            options=resolved_options,
        )
        chunks = build_report_chunks(
            document=document,
            report=report,
            options=resolved_options,
        )
        jobs = build_embedding_jobs(
            document=document,
            chunks=chunks,
            options=resolved_options,
        )

        return RagPersistenceBundle(
            document=document,
            chunks=chunks,
            embedding_jobs=jobs,
        )

    def build_from_agent_signal(
        self,
        signal: AgentSignalRecord,
        *,
        options: CuratedRagBuildOptions | None = None,
        source_eligibility: RagSourceEligibilityRecord | None = None,
    ) -> RagPersistenceBundle:
        resolved_options = options or CuratedRagBuildOptions()
        eligibility = source_eligibility or evaluate_source_eligibility(
            signal,
        )
        raise_if_ineligible(
            eligibility,
            options=resolved_options,
        )
        document = self._document_factory.build_agent_signal_document(
            signal,
            eligibility=eligibility,
            options=resolved_options,
        )
        chunks = build_agent_signal_chunks(
            document=document,
            signal=signal,
            text=document.content_text,
            options=resolved_options,
        )
        jobs = build_embedding_jobs(
            document=document,
            chunks=chunks,
            options=resolved_options,
        )

        return RagPersistenceBundle(
            document=document,
            chunks=chunks,
            embedding_jobs=jobs,
        )

    def build_from_structured_source(
        self,
        source: CuratedRagSource,
        *,
        options: CuratedRagBuildOptions | None = None,
        source_eligibility: RagSourceEligibilityRecord | None = None,
    ) -> RagPersistenceBundle:
        if not is_structured_curated_rag_source(
            source,
        ):
            raise TypeError(
                "Structured RAG ingestion requires a supported curated PostgreSQL "
                "source record."
            )
        resolved_options = options or CuratedRagBuildOptions()
        eligibility = source_eligibility or evaluate_source_eligibility(
            source,
        )
        raise_if_ineligible(
            eligibility,
            options=resolved_options,
        )
        return build_structured_source_bundle(
            source,
            options=resolved_options,
            eligibility=eligibility,
        )


class CuratedRagIngestionService:
    """
    Persists curated RAG source records through the RAG repository boundary.
    """

    def __init__(
        self,
        repository: RagPersistenceRepository,
        builder: CuratedRagDocumentBuilder | None = None,
        bundle_persister: CuratedRagBundlePersister | None = None,
        telemetry: ApplicationRagTelemetry | None = None,
    ) -> None:
        self._repository = repository
        self._builder = builder or CuratedRagDocumentBuilder()
        self._bundle_persister = bundle_persister or CuratedRagBundlePersister(
            repository
        )
        self._telemetry = telemetry

    async def persist_source(
        self,
        source: CuratedRagSource,
        *,
        options: CuratedRagBuildOptions | None = None,
    ) -> RagPersistenceResult:
        started_at = perf_counter()
        resolved_options = options or CuratedRagBuildOptions()
        source_attributes = _source_telemetry_attributes(
            source,
        )
        await self._emit_started(
            operation="rag.ingestion.persist_source",
            attributes={
                **source_attributes,
                "require_source_eligibility": (
                    resolved_options.require_source_eligibility
                ),
                "queue_embedding_jobs": resolved_options.queue_embedding_jobs,
            },
        )
        try:
            eligibility, failure = await self._resolve_eligibility(
                source,
                options=resolved_options,
                source_attributes=source_attributes,
                started_at=started_at,
            )
            if failure is not None:
                return failure

            bundle = await self._build_bundle(
                source,
                options=resolved_options,
                source_eligibility=eligibility,
                source_attributes=source_attributes,
            )
            return await self._persist_bundle(
                bundle,
                source_attributes=source_attributes,
                started_at=started_at,
            )
        except Exception as exc:
            await self._emit_failed(
                operation="rag.ingestion.persist_source",
                error=exc,
                duration_seconds=perf_counter() - started_at,
                attributes=source_attributes,
            )
            raise

    async def _resolve_eligibility(
        self,
        source: CuratedRagSource,
        *,
        options: CuratedRagBuildOptions,
        source_attributes: dict[str, Any],
        started_at: float,
    ) -> tuple[RagSourceEligibilityRecord | None, RagPersistenceResult | None]:
        if not options.require_source_eligibility:
            return None, None

        eligibility_started_at = perf_counter()
        eligibility = await resolve_persisted_or_default_eligibility(
            self._repository,
            source,
        )
        await self._emit_completed(
            operation="rag.ingestion.eligibility",
            duration_seconds=perf_counter() - eligibility_started_at,
            attributes={
                **source_attributes,
                "eligible": eligibility.eligible,
                "eligibility_rule_name": eligibility.metadata.get(
                    "rule_name",
                ),
            },
        )
        if eligibility.eligible:
            return eligibility, None

        result = RagPersistenceResult.failed(
            eligibility_error_message(
                eligibility,
            )
        )
        await self._emit_failed(
            operation="rag.ingestion.persist_source",
            error=result.error or "RAG source is not eligible.",
            duration_seconds=perf_counter() - started_at,
            attributes={
                **source_attributes,
                "eligible": False,
            },
        )
        return eligibility, result

    async def _build_bundle(
        self,
        source: CuratedRagSource,
        *,
        options: CuratedRagBuildOptions,
        source_eligibility: RagSourceEligibilityRecord | None,
        source_attributes: dict[str, Any],
    ) -> RagPersistenceBundle:
        build_started_at = perf_counter()
        bundle = self._builder.build_from_source(
            source,
            options=options,
            source_eligibility=source_eligibility,
        )
        await self._emit_completed(
            operation="rag.ingestion.build_bundle",
            duration_seconds=perf_counter() - build_started_at,
            attributes=_bundle_telemetry_attributes(
                bundle,
                source_attributes=source_attributes,
            ),
        )
        return bundle

    async def _persist_bundle(
        self,
        bundle: RagPersistenceBundle,
        *,
        source_attributes: dict[str, Any],
        started_at: float,
    ) -> RagPersistenceResult:
        persist_started_at = perf_counter()
        result = await self._bundle_persister.persist(
            bundle,
        )
        result_attributes = {
            **_bundle_telemetry_attributes(
                bundle,
                source_attributes=source_attributes,
            ),
            "persistence_success": result.success,
            "records_persisted": result.records_persisted,
        }
        if not result.success:
            await self._emit_failed(
                operation="rag.ingestion.persist_bundle",
                error=result.error or "Failed to persist RAG bundle.",
                duration_seconds=perf_counter() - persist_started_at,
                attributes=result_attributes,
            )
            await self._emit_failed(
                operation="rag.ingestion.persist_source",
                error=result.error or "Failed to persist RAG source.",
                duration_seconds=perf_counter() - started_at,
                attributes=result_attributes,
            )
            return result

        await self._emit_completed(
            operation="rag.ingestion.persist_bundle",
            duration_seconds=perf_counter() - persist_started_at,
            attributes=result_attributes,
        )
        await self._emit_completed(
            operation="rag.ingestion.persist_source",
            duration_seconds=perf_counter() - started_at,
            attributes=result_attributes,
        )
        return result

    async def _emit_started(
        self,
        *,
        operation: str,
        attributes: dict[str, Any],
    ) -> None:
        if self._telemetry is None:
            return
        await self._telemetry.emit_operation_started(
            "CuratedRagIngestionService",
            operation,
            attributes=attributes,
        )

    async def _emit_completed(
        self,
        *,
        operation: str,
        duration_seconds: float,
        attributes: dict[str, Any],
    ) -> None:
        if self._telemetry is None:
            return
        await self._telemetry.emit_operation_completed(
            "CuratedRagIngestionService",
            operation,
            duration_seconds=duration_seconds,
            attributes=attributes,
        )

    async def _emit_failed(
        self,
        *,
        operation: str,
        error: BaseException | str,
        duration_seconds: float,
        attributes: dict[str, Any],
    ) -> None:
        if self._telemetry is None:
            return
        await self._telemetry.emit_operation_failed(
            "CuratedRagIngestionService",
            operation,
            error=error,
            duration_seconds=duration_seconds,
            attributes=attributes,
        )


def _bundle_telemetry_attributes(
    bundle: RagPersistenceBundle,
    *,
    source_attributes: dict[str, Any],
) -> dict[str, Any]:
    return {
        **source_attributes,
        "document_id": bundle.document.document_id,
        "chunk_count": len(bundle.chunks),
        "embedding_job_count": len(bundle.embedding_jobs),
    }


def _source_telemetry_attributes(
    source: CuratedRagSource,
) -> dict[str, Any]:
    if isinstance(
        source,
        ReportRecord,
    ):
        return {
            "source_table": "reports",
            "source_id": source.report_id,
            "source_type": source.report_type,
            "workflow_name": source.workflow_name,
            "execution_id": source.execution_id,
        }
    if isinstance(
        source,
        AgentSignalRecord,
    ):
        return {
            "source_table": "agent_signals",
            "source_id": source.signal_id,
            "source_type": source.agent_type,
            "workflow_name": source.workflow_name,
            "execution_id": source.execution_id,
        }
    if is_structured_curated_rag_source(
        source,
    ):
        spec = require_structured_source_spec(
            source,
        )
        return {
            "source_table": spec.source_table,
            "source_id": structured_source_id(
                source,
            ),
            "source_type": spec.source_type,
        }
    return {
        "source_type": type(source).__name__,
    }
