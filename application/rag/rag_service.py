from __future__ import annotations

import hashlib
from collections.abc import Mapping
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from datetime import timezone
from time import perf_counter
from typing import Protocol
from typing import Any
from typing import cast

from application.rag.contracts.rag_request import RagRequest
from application.rag.contracts.rag_result import RagResult
from application.rag.observability import RagAiObservabilityProjectorPort
from application.rag.observability import RagAiObservabilityRecorder
from application.rag.observability import record_rag_query_observation
from core.storage.persistence.rag import JsonObject
from core.storage.persistence.rag import RagAnswerLogRecord
from core.storage.persistence.rag import RagPersistenceRepository
from core.storage.persistence.rag import RagQueryLogRecord
from core.storage.persistence.rag import RagQueryModelExecutionRecord
from core.storage.persistence.rag import RagQueryReflectionScores
from core.storage.persistence.rag import new_rag_answer_log_id
from core.telemetry.emitters.application_rag_telemetry import ApplicationRagTelemetry


class RagPipelinePort(Protocol):
    async def run(
        self,
        request: RagRequest,
    ) -> RagResult: ...


@dataclass(
    frozen=True,
    slots=True,
)
class RagServiceConfig:
    """
    Runtime controls for platform-native RAG orchestration.
    """

    operation_name: str = "rag.service.run"

    def __post_init__(
        self,
    ) -> None:
        if not self.operation_name.strip():
            raise ValueError("operation_name cannot be empty.")


class RagService:
    """
    Application service boundary for platform-native RAG execution.

    Pipeline execution remains delegated to the unified RAG graph. This service
    owns request/answer persistence logging and service-level telemetry for the
    complete RAG use case.
    """

    def __init__(
        self,
        *,
        pipeline: RagPipelinePort,
        repository: RagPersistenceRepository,
        telemetry: ApplicationRagTelemetry | None = None,
        config: RagServiceConfig | None = None,
        ai_observability_projector: RagAiObservabilityProjectorPort | None = None,
    ) -> None:
        self._pipeline = pipeline
        self._repository = repository
        self._telemetry = telemetry
        self._config = config or RagServiceConfig()
        self._ai_observability = RagAiObservabilityRecorder(ai_observability_projector)

    async def run(
        self,
        request: RagRequest,
    ) -> RagResult:
        started_at = datetime.now(timezone.utc)
        timer_started_at = perf_counter()
        await self._emit_started(
            request,
        )
        await self._persist_query_log(
            _query_log_from_request(
                request=request,
                status="started",
                started_at=started_at,
            )
        )

        pipeline_error: BaseException | None = None
        try:
            result = await self._pipeline.run(
                request,
            )
        except Exception as exc:
            pipeline_error = exc
            result = RagResult.failed(
                request=request,
                error=str(exc),
            )

        completed_at = datetime.now(timezone.utc)
        duration_seconds = perf_counter() - timer_started_at
        await self._persist_query_log(
            _query_log_from_result(
                request=request,
                result=result,
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=duration_seconds,
            )
        )
        await self._persist_answer_log(
            _answer_log_from_result(
                result=result,
                completed_at=completed_at,
            )
        )
        await self._emit_finished(
            request=request,
            result=result,
            duration_seconds=duration_seconds,
            error=pipeline_error,
        )
        await record_rag_query_observation(
            self._ai_observability,
            request=request,
            result=result,
            duration_seconds=duration_seconds,
        )
        return result

    async def _persist_query_log(
        self,
        query_log: RagQueryLogRecord,
    ) -> None:
        started_at = perf_counter()
        try:
            persistence_result = await self._repository.persist_query_log(
                query_log,
            )
        except Exception as exc:
            await self._emit_persistence_failed(
                operation="rag.persistence.query_log",
                record_id=query_log.query_id,
                status=query_log.status,
                error=exc,
                duration_seconds=perf_counter() - started_at,
            )
            raise
        if not persistence_result.success:
            await self._emit_persistence_failed(
                operation="rag.persistence.query_log",
                record_id=query_log.query_id,
                status=query_log.status,
                error=persistence_result.error or "Failed to persist RAG query log.",
                duration_seconds=perf_counter() - started_at,
            )
            return
        await self._emit_persistence_completed(
            operation="rag.persistence.query_log",
            record_id=query_log.query_id,
            status=query_log.status,
            duration_seconds=perf_counter() - started_at,
            attributes={
                "records_persisted": persistence_result.records_persisted,
            },
        )

    async def _persist_answer_log(
        self,
        answer_log: RagAnswerLogRecord,
    ) -> None:
        started_at = perf_counter()
        try:
            persistence_result = await self._repository.persist_answer_log(
                answer_log,
            )
        except Exception as exc:
            await self._emit_persistence_failed(
                operation="rag.persistence.answer_log",
                record_id=answer_log.answer_id,
                status=answer_log.status,
                error=exc,
                duration_seconds=perf_counter() - started_at,
            )
            raise
        if not persistence_result.success:
            await self._emit_persistence_failed(
                operation="rag.persistence.answer_log",
                record_id=answer_log.answer_id,
                status=answer_log.status,
                error=(persistence_result.error or "Failed to persist RAG answer log."),
                duration_seconds=perf_counter() - started_at,
            )
            return
        await self._emit_persistence_completed(
            operation="rag.persistence.answer_log",
            record_id=answer_log.answer_id,
            status=answer_log.status,
            duration_seconds=perf_counter() - started_at,
            attributes={
                "records_persisted": persistence_result.records_persisted,
            },
        )

    async def _emit_started(
        self,
        request: RagRequest,
    ) -> None:
        if self._telemetry is None:
            return
        await self._telemetry.emit_operation_started(
            "RagService",
            self._config.operation_name,
            correlation_id=request.request_id,
            attributes={
                "route": request.route,
                "top_k": request.top_k,
            },
        )

    async def _emit_finished(
        self,
        *,
        request: RagRequest,
        result: RagResult,
        duration_seconds: float,
        error: BaseException | None = None,
    ) -> None:
        if self._telemetry is None:
            return
        attributes = {
            "route": request.route,
            "status": result.status,
            "context_count": len(result.contexts),
            "citation_count": len(result.citations),
        }
        if result.status == "failed":
            await self._telemetry.emit_operation_failed(
                "RagService",
                self._config.operation_name,
                error=error or result.error or "RAG request failed.",
                duration_seconds=duration_seconds,
                correlation_id=request.request_id,
                attributes=attributes,
            )
            return

        await self._telemetry.emit_operation_completed(
            "RagService",
            self._config.operation_name,
            duration_seconds=duration_seconds,
            correlation_id=request.request_id,
            attributes=attributes,
        )

    async def _emit_persistence_completed(
        self,
        *,
        operation: str,
        record_id: str,
        status: str,
        duration_seconds: float,
        attributes: dict[str, Any],
    ) -> None:
        if self._telemetry is None:
            return
        await self._telemetry.emit_operation_completed(
            "RagService",
            operation,
            duration_seconds=duration_seconds,
            correlation_id=record_id,
            attributes={
                **attributes,
                "record_id": record_id,
                "status": status,
                "persistence_success": True,
            },
        )

    async def _emit_persistence_failed(
        self,
        *,
        operation: str,
        record_id: str,
        status: str,
        error: BaseException | str,
        duration_seconds: float,
    ) -> None:
        if self._telemetry is None:
            return
        await self._telemetry.emit_operation_failed(
            "RagService",
            operation,
            error=error,
            duration_seconds=duration_seconds,
            correlation_id=record_id,
            attributes={
                "record_id": record_id,
                "status": status,
                "persistence_success": False,
            },
        )


def _query_log_from_request(
    *,
    request: RagRequest,
    status: str,
    started_at: datetime,
) -> RagQueryLogRecord:
    return RagQueryLogRecord(
        query_id=request.request_id,
        query_text=request.query,
        normalized_query=request.normalized_query,
        requester=request.requester,
        workflow_name=request.workflow_name,
        execution_id=request.execution_id,
        retrieval_route=request.route,
        top_k=request.top_k,
        filters=_json_object(
            request.filters.to_dict(),
        ),
        status=status,
        started_at=started_at,
        model_executions=_query_model_executions(request.metadata),
        metadata=_request_debug_metadata(request.metadata),
    )


def _query_log_from_result(
    *,
    request: RagRequest,
    result: RagResult,
    started_at: datetime,
    completed_at: datetime,
    duration_seconds: float,
) -> RagQueryLogRecord:
    return RagQueryLogRecord(
        query_id=request.request_id,
        query_text=request.query,
        normalized_query=request.normalized_query,
        requester=request.requester,
        workflow_name=request.workflow_name,
        execution_id=request.execution_id,
        retrieval_route=request.route,
        top_k=request.top_k,
        filters=_json_object(
            request.filters.to_dict(),
        ),
        status=result.status,
        started_at=started_at,
        model_executions=_query_model_executions(
            result.metadata,
            request.metadata,
        ),
        context_count=len(result.contexts),
        citation_count=len(result.citations),
        grounding_score=result.grounding_score,
        utility_score=result.utility_score,
        injection_detected=result.injection_detected,
        reflection_scores=(
            None
            if result.reflection_scores is None
            else RagQueryReflectionScores(
                retrieval_necessity=result.reflection_scores.retrieval_necessity,
                source_relevance=result.reflection_scores.source_relevance,
                answer_support=result.reflection_scores.answer_support,
                usefulness=result.reflection_scores.usefulness,
            )
        ),
        corrective_actions=tuple(action.value for action in result.corrective_actions),
        completed_at=completed_at,
        duration_ms=duration_seconds * 1000.0,
        error=result.error,
        metadata=_request_debug_metadata(request.metadata),
    )


def _answer_log_from_result(
    *,
    result: RagResult,
    completed_at: datetime,
) -> RagAnswerLogRecord:
    return RagAnswerLogRecord(
        answer_id=new_rag_answer_log_id(
            query_id=result.query_id,
        ),
        query_id=result.query_id,
        answer_text=result.answer_text,
        answer_hash=_sha256_text(
            result.answer_text,
        ),
        generation_model=_optional_metadata_string(
            result.metadata,
            "generation_model",
        ),
        status=result.status,
        confidence_score=result.confidence_score,
        source_count=len(
            result.citations,
        ),
        citations=_json_object(
            {
                "items": [citation.to_dict() for citation in result.citations],
            }
        ),
        sources=_json_object(
            {
                "items": [context.source.to_dict() for context in result.contexts],
            }
        ),
        completed_at=completed_at,
        metadata=_json_object(
            {
                "route": result.route,
                "error": result.error,
                "result_metadata": _debug_metadata(result.metadata),
            }
        ),
    )


def _query_model_executions(
    *metadata_sources: JsonObject,
) -> tuple[RagQueryModelExecutionRecord, ...]:
    for metadata in metadata_sources:
        payload = metadata.get("model_executions")
        if payload is None:
            continue
        if isinstance(payload, str) or not isinstance(payload, Sequence):
            raise TypeError("model_executions must be a sequence of objects.")
        records: list[RagQueryModelExecutionRecord] = []
        for item in payload:
            if not isinstance(item, Mapping):
                raise TypeError("model_executions must contain objects.")
            records.append(RagQueryModelExecutionRecord.from_mapping(item))
        return tuple(records)
    return ()


def _request_debug_metadata(
    metadata: JsonObject,
) -> JsonObject:
    request_metadata = _debug_metadata(metadata)
    if not request_metadata:
        return {}
    return _json_object(
        {
            "request_metadata": request_metadata,
        }
    )


def _debug_metadata(
    metadata: JsonObject,
) -> JsonObject:
    return _json_object(
        {key: value for key, value in metadata.items() if key != "model_executions"}
    )


def _sha256_text(
    value: str,
) -> str:
    return hashlib.sha256(
        value.encode("utf-8"),
    ).hexdigest()


def _optional_metadata_string(
    metadata: JsonObject,
    key: str,
) -> str | None:
    value = metadata.get(
        key,
    )
    if isinstance(value, str) and value.strip():
        return value
    return None


def _json_object(
    value: object,
) -> JsonObject:
    return cast(
        JsonObject,
        value,
    )
