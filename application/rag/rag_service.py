from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from time import perf_counter
from typing import Any, Protocol, cast

from application.decision_evidence import DecisionEvidencePacketPersistenceService
from application.presentation.evidence import (
    presentation_gate_evidence,
    presentation_sink_decision_metadata,
)
from application.presentation.sink_decision import PresentationSinkDecisionService
from application.rag.authority import (
    RAG_AUTHORITY_FAILURE_MODE_METADATA_KEY,
    RagAuthorityFailureMode,
    classify_rag_result_authority,
)
from application.rag.contracts.rag_context import RagRetrievedContext
from application.rag.contracts.rag_request import RagRequest
from application.rag.contracts.rag_result import RagResult
from application.rag.evidence_packets import (
    DECISION_EVIDENCE_PACKET_FAILURE_METADATA_KEY,
    attach_rag_answer_evidence_packet,
)
from application.rag.observability import (
    RagAiObservabilityProjectorPort,
    RagAiObservabilityRecorder,
    record_rag_query_observation,
)
from application.rag.security.rag_security import safe_grounding_failure_answer
from core.storage.persistence.rag import (
    JsonObject,
    RagAnswerLogRecord,
    RagPersistenceRepository,
    RagQueryLogRecord,
    RagQueryModelExecutionRecord,
    RagQueryReflectionScores,
    new_rag_answer_log_id,
)
from core.telemetry.emitters.application_rag_telemetry import ApplicationRagTelemetry
from core.workflow.registry.workflow_registry import (
    WorkflowAuthorityFacts,
    WorkflowRegistry,
)
from domain.authority import (
    RiskAuthorityContract,
    RiskTier,
)


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
        decision_evidence_packet_persistence_service: (
            DecisionEvidencePacketPersistenceService
        ),
        workflow_registry: WorkflowRegistry | None = None,
        telemetry: ApplicationRagTelemetry | None = None,
        config: RagServiceConfig | None = None,
        ai_observability_projector: RagAiObservabilityProjectorPort | None = None,
        presentation_sink_decision_service: (
            PresentationSinkDecisionService | None
        ) = None,
    ) -> None:
        self._pipeline = pipeline
        self._repository = repository
        self._decision_evidence_packet_persistence_service = (
            decision_evidence_packet_persistence_service
        )
        self._workflow_registry = workflow_registry
        self._telemetry = telemetry
        self._config = config or RagServiceConfig()
        self._ai_observability = RagAiObservabilityRecorder(ai_observability_projector)
        self._presentation_sink_decision_service = (
            presentation_sink_decision_service or PresentationSinkDecisionService()
        )

    async def run(
        self,
        request: RagRequest,
    ) -> RagResult:
        started_at = datetime.now(UTC)
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
        result = classify_rag_result_authority(
            request=request,
            result=result,
        )

        completed_at = datetime.now(UTC)
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
        result = await self._reacquire_claim_evidence_packet(
            request=request,
            result=result,
        )
        result = await self._apply_presentation_decision(result)
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

    async def _reacquire_claim_evidence_packet(
        self,
        *,
        request: RagRequest,
        result: RagResult,
    ) -> RagResult:
        """Persist and verify a claim packet before releasing a RAG answer."""

        if result.status != "answered":
            return result
        try:
            authority = result.authority
            if authority is None:
                raise ValueError("RAG answer lacks typed platform-owned authority.")
            if authority.risk_tier not in {RiskTier.ENHANCED, RiskTier.VIGILANT}:
                return result
            facts, execution_id = self._workflow_facts(result=result)
            result = attach_rag_answer_evidence_packet(
                request=request,
                result=result,
                workflow_name=facts.identity.workflow_name,
                workflow_definition_fingerprint=facts.identity.definition_fingerprint,
                execution_id=execution_id,
            )
            packet = result.evidence_packet
            if packet is None:
                return result
            persistence_service = self._decision_evidence_packet_persistence_service
            persistence = await persistence_service.persist_packet(packet)
            if (
                not persistence.success
                or persistence.records_persisted < 1
                or persistence.packet_id != packet.packet_id
            ):
                raise ValueError("RAG claim evidence packet was not durably persisted.")
            reconstructed = await persistence_service.reconstruct_packet(
                packet.packet_id
            )
            if reconstructed != packet:
                raise ValueError(
                    "RAG claim evidence packet changed during reconstruction."
                )
        except Exception as exc:
            return classify_rag_result_authority(
                request=request,
                result=replace(
                    result,
                    evidence_packet=None,
                    metadata={
                        **result.metadata,
                        RAG_AUTHORITY_FAILURE_MODE_METADATA_KEY: (
                            RagAuthorityFailureMode.UNSUPPORTED_EVIDENCE.value
                        ),
                        DECISION_EVIDENCE_PACKET_FAILURE_METADATA_KEY: str(exc),
                    },
                ),
            )
        return replace(result, evidence_packet=reconstructed)

    async def _apply_presentation_decision(self, result: RagResult) -> RagResult:
        authority = result.authority
        packets = () if result.evidence_packet is None else (result.evidence_packet,)
        evidence = presentation_gate_evidence(packets=packets)
        blocking_reasons, withholding_reasons = _rag_presentation_boundary_reasons(
            result
        )
        decision = await self._presentation_sink_decision_service.evaluate(
            authority,
            evidence=evidence,
            expected_authority_metadata=authority,
            blocking_reasons=blocking_reasons,
            withholding_reasons=withholding_reasons,
        )
        metadata = cast(
            JsonObject,
            {
                **result.metadata,
                **presentation_sink_decision_metadata(decision),
            },
        )
        if decision.may_present or result.status != "answered":
            return replace(result, metadata=metadata)
        return replace(
            result,
            answer_text=safe_grounding_failure_answer(),
            status="no_results",
            citations=(),
            confidence_score=None,
            error=None,
            metadata=metadata,
        )

    def _workflow_facts(
        self,
        *,
        result: RagResult,
    ) -> tuple[WorkflowAuthorityFacts, str]:
        """Bind a claim packet to durable context provenance before release."""

        registry = self._workflow_registry
        workflow_names = {
            _clean_required(context.source.workflow_name, "workflow_name")
            for context in result.contexts
        }
        execution_ids = {
            _clean_required(context.source.execution_id, "execution_id")
            for context in result.contexts
        }
        if registry is None or len(workflow_names) != 1 or len(execution_ids) != 1:
            raise ValueError("RAG claim evidence lacks governed workflow provenance.")
        workflow_name = next(iter(workflow_names))
        execution_id = next(iter(execution_ids))
        facts = registry.get_authority_facts(workflow_name)
        if not isinstance(facts.authority, RiskAuthorityContract):
            raise ValueError(
                "RAG claim evidence lacks typed workflow registry authority facts."
            )
        return facts, execution_id

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
        if error is not None or result.status == "failed":
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


def _rag_presentation_boundary_reasons(
    result: RagResult,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    blocking_reasons: list[str] = []
    withholding_reasons: list[str] = []
    if result.injection_detected:
        blocking_reasons.append(
            "RAG presentation is blocked because prompt-injection evidence "
            "was detected."
        )

    failure_mode = _rag_authority_failure_mode(result.metadata)
    if failure_mode in {
        RagAuthorityFailureMode.CITATION_SPOOFING,
        RagAuthorityFailureMode.MODEL_AUTHORITY_CLAIM,
        RagAuthorityFailureMode.OUTSIDE_AUTHORITY,
    }:
        blocking_reasons.append(
            f"RAG authority boundary rejected {failure_mode.value}."
        )
    elif failure_mode is not RagAuthorityFailureMode.NONE:
        withholding_reasons.append(
            f"RAG presentation lacks releasable evidence: {failure_mode.value}."
        )
    return tuple(blocking_reasons), tuple(withholding_reasons)


def _rag_authority_failure_mode(metadata: JsonObject) -> RagAuthorityFailureMode:
    raw_failure_mode = metadata.get(RAG_AUTHORITY_FAILURE_MODE_METADATA_KEY)
    if not isinstance(raw_failure_mode, str):
        return RagAuthorityFailureMode.UNSUPPORTED_EVIDENCE
    try:
        return RagAuthorityFailureMode(raw_failure_mode)
    except ValueError:
        return RagAuthorityFailureMode.OUTSIDE_AUTHORITY


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
        metadata=_query_result_metadata(
            request_metadata=request.metadata,
            result=result,
        ),
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


def _query_result_metadata(
    *,
    request_metadata: JsonObject,
    result: RagResult,
) -> JsonObject:
    metadata: dict[str, object] = dict(_request_debug_metadata(request_metadata))
    if result.status != "answered":
        return _json_object(metadata)

    retrieved_contexts = _retained_retrieval_context_payloads(result.contexts)
    if retrieved_contexts:
        metadata["retrieved_contexts"] = retrieved_contexts
    return _json_object(metadata)


def _retained_retrieval_context_payloads(
    contexts: Sequence[RagRetrievedContext],
) -> tuple[JsonObject, ...]:
    return tuple(
        _json_object(context.to_dict())
        for context in contexts
        if _is_durable_retrieval_context(context)
    )


def _is_durable_retrieval_context(context: RagRetrievedContext) -> bool:
    source = context.source
    if (
        context.metadata.get("transient") is True
        or source.metadata.get("transient") is True
    ):
        return False
    if context.retrieval_route in {"web", "web_fallback"}:
        return False
    if source.source_table in {"web", "web_fallback"}:
        return False
    if source.source_type in {"web", "web_fallback"}:
        return False
    return True


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


def _clean_required(value: str | None, field_name: str) -> str:
    if value is None:
        raise ValueError(f"{field_name} cannot be empty.")
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} cannot be empty.")
    return cleaned
