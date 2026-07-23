from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from application.observability.ai_observability_contracts import (
    AiEvaluationObservation,
    AiGenerationObservation,
    AiMetadata,
    AiObservabilityCorrelationIds,
    AiObservabilityExportResult,
    AiObservation,
    AiObservationStatus,
    AiObservationType,
    AiPromptVersionReference,
    AiRerankingObservation,
    AiRetrievalObservation,
    AiScoreProjection,
    AiScoreResult,
)
from application.rag.contracts.rag_context import RagRetrievedContext
from application.rag.contracts.rag_quality_models import (
    RagContextEvaluation,
    RagSelfReflection,
)
from application.rag.contracts.rag_request import RagRequest
from application.rag.contracts.rag_result import RagResult
from application.rag.routing.query_routing_models import RagQueryModelExecution

logger = logging.getLogger(__name__)


class RagAiObservabilityProjectorPort(Protocol):
    """Projection boundary for typed AI observations emitted by RAG code."""

    async def project(
        self,
        observation: AiObservation,
    ) -> AiObservabilityExportResult: ...


@dataclass(frozen=True, slots=True)
class RagAiObservabilityRecorder:
    """Non-fatal RAG AI-observability recorder.

    The recorder is intentionally separate from ApplicationRagTelemetry. The
    telemetry stack records Polaris operational health; this boundary projects
    sanitized AI-specific observations to Langfuse or its durable export queue.
    """

    projector: RagAiObservabilityProjectorPort | None = None

    @property
    def enabled(self) -> bool:
        return self.projector is not None

    async def record(
        self,
        observation: AiObservation,
    ) -> None:
        if self.projector is None:
            return
        try:
            await self.projector.project(observation)
        except Exception:
            logger.debug(
                "RAG AI-observability projection failed.",
                extra={
                    "observation_type": observation.observation_type.value,
                    "observation_name": observation.name,
                    "observation_id": observation.correlation_ids.observation_id,
                },
                exc_info=True,
            )


async def record_rag_query_observation(
    recorder: RagAiObservabilityRecorder,
    *,
    request: RagRequest,
    result: RagResult,
    duration_seconds: float,
) -> None:
    await recorder.record(
        AiObservation(
            observation_type=AiObservationType.RAG_QUERY,
            name="rag_query",
            correlation_ids=correlation_ids_from_request(
                request,
                node_name="RagService",
                observation_id=_observation_id(request, "query"),
            ),
            status=_status_from_result(result),
            latency_ms=_latency_ms(duration_seconds),
            input_shape=_request_shape(request),
            output_shape=(
                f"status={result.status};contexts={len(result.contexts)};"
                f"citations={len(result.citations)}"
            ),
            metadata=_metadata(
                {
                    "route": result.route,
                    "top_k": request.top_k,
                    "allow_web": request.allow_web,
                    "context_count": len(result.contexts),
                    "citation_count": len(result.citations),
                    "grounding_score": result.grounding_score,
                    "utility_score": result.utility_score,
                    "injection_detected": result.injection_detected,
                    "error_present": result.error is not None,
                }
            ),
        )
    )


async def record_routing_observation(
    recorder: RagAiObservabilityRecorder,
    *,
    request: RagRequest,
    stage_name: str,
    execution: RagQueryModelExecution | None,
    status: AiObservationStatus = AiObservationStatus.SUCCESS,
    output_shape: str | None = None,
    metadata: Mapping[str, object] | None = None,
) -> None:
    await recorder.record(
        AiGenerationObservation(
            observation_type=AiObservationType.RAG_ROUTING,
            name=stage_name,
            correlation_ids=correlation_ids_from_request(
                request,
                node_name="RagServiceGraph",
                observation_id=_observation_id(request, stage_name),
            ),
            status=status,
            model_name=None if execution is None else execution.configured_model,
            provider_name=None if execution is None else execution.provider_name,
            latency_ms=None if execution is None else execution.duration_ms,
            prompt_reference=_prompt_reference_from_execution(execution),
            input_shape=_request_shape(request),
            output_shape=output_shape,
            metadata=_metadata(
                {
                    **(metadata or {}),
                    "operation": None if execution is None else execution.operation,
                    "model_success": None if execution is None else execution.success,
                }
            ),
        )
    )


async def record_hyde_observation(
    recorder: RagAiObservabilityRecorder,
    *,
    request: RagRequest,
    execution: RagQueryModelExecution,
    hypothetical_document_length: int,
) -> None:
    await recorder.record(
        AiGenerationObservation(
            observation_type=AiObservationType.RAG_ROUTING,
            name="hyde",
            correlation_ids=correlation_ids_from_request(
                request,
                node_name="RagServiceGraph",
                observation_id=_observation_id(request, "hyde"),
            ),
            status=AiObservationStatus.SUCCESS,
            model_name=execution.configured_model,
            provider_name=execution.provider_name,
            latency_ms=execution.duration_ms,
            prompt_reference=_prompt_reference_from_execution(execution),
            input_shape=_request_shape(request),
            output_shape=f"hypothetical_document_characters={hypothetical_document_length}",
            metadata=_metadata(
                {
                    "operation": execution.operation,
                    "model_success": execution.success,
                    "hypothetical_document_characters": hypothetical_document_length,
                }
            ),
        )
    )


async def record_retrieval_observation(
    recorder: RagAiObservabilityRecorder,
    *,
    request: RagRequest,
    observation_type: AiObservationType,
    stage_name: str,
    duration_seconds: float,
    retrieved_count: int,
    selected_context_ids: tuple[str, ...] = (),
    retrieval_scores: tuple[float, ...] = (),
    status: AiObservationStatus = AiObservationStatus.SUCCESS,
    metadata: Mapping[str, object] | None = None,
) -> None:
    await recorder.record(
        AiRetrievalObservation(
            observation_type=observation_type,
            name=stage_name,
            correlation_ids=correlation_ids_from_request(
                request,
                node_name="RagRetriever",
                observation_id=_observation_id(request, stage_name),
            ),
            status=status,
            latency_ms=_latency_ms(duration_seconds),
            input_shape=_request_shape(request),
            output_shape=f"retrieved_count={retrieved_count}",
            metadata=_metadata(metadata or {}),
            retrieved_count=retrieved_count,
            selected_context_ids=selected_context_ids,
            retrieval_scores=retrieval_scores,
        )
    )


async def record_reranking_observation(
    recorder: RagAiObservabilityRecorder,
    *,
    request: RagRequest,
    duration_seconds: float,
    candidate_count: int,
    selected_contexts: tuple[RagRetrievedContext, ...],
    reranker_enabled: bool,
) -> None:
    await recorder.record(
        AiRerankingObservation(
            observation_type=AiObservationType.RAG_RERANKING,
            name="reranking",
            correlation_ids=correlation_ids_from_request(
                request,
                node_name="RagRetriever",
                observation_id=_observation_id(request, "reranking"),
            ),
            status=AiObservationStatus.SUCCESS,
            latency_ms=_latency_ms(duration_seconds),
            input_shape=f"candidate_contexts={candidate_count};top_k={request.top_k}",
            output_shape=f"selected_contexts={len(selected_contexts)}",
            metadata=_metadata(
                {
                    "reranker_enabled": reranker_enabled,
                    "route": request.route,
                }
            ),
            candidate_count=candidate_count,
            selected_count=len(selected_contexts),
            reranking_scores=tuple(context.score for context in selected_contexts),
        )
    )


async def record_crag_observation(
    recorder: RagAiObservabilityRecorder,
    *,
    request: RagRequest,
    evaluation: RagContextEvaluation,
    input_context_count: int,
    retained_context_count: int,
) -> None:
    await recorder.record(
        AiEvaluationObservation(
            observation_type=AiObservationType.RAG_CRAG,
            name="crag_evaluator",
            correlation_ids=correlation_ids_from_request(
                request,
                node_name="RagServiceGraph",
                observation_id=_observation_id(request, "crag_evaluator"),
            ),
            status=AiObservationStatus.SUCCESS,
            input_shape=f"contexts={input_context_count}",
            output_shape=(
                f"quality={evaluation.quality.value};action={evaluation.action.value};"
                f"retained={retained_context_count}"
            ),
            metadata=_metadata(
                {
                    "context_quality": evaluation.quality.value,
                    "corrective_action": evaluation.action.value,
                    "input_context_count": input_context_count,
                    "retained_context_count": retained_context_count,
                }
            ),
        )
    )


async def record_generation_observation(
    recorder: RagAiObservabilityRecorder,
    *,
    request: RagRequest,
    result: RagResult,
    input_context_count: int,
    duration_seconds: float | None = None,
) -> None:
    await recorder.record(
        AiGenerationObservation(
            observation_type=AiObservationType.RAG_GENERATION,
            name="secure_generation",
            correlation_ids=correlation_ids_from_request(
                request,
                node_name="RagServiceGraph",
                observation_id=_observation_id(request, "secure_generation"),
            ),
            status=_status_from_result(result),
            model_name=_metadata_str(result.metadata, "generation_model"),
            provider_name=_metadata_str(result.metadata, "generation_provider"),
            prompt_reference=_prompt_reference_from_metadata(result.metadata),
            latency_ms=None
            if duration_seconds is None
            else _latency_ms(duration_seconds),
            input_shape=f"contexts={input_context_count}",
            output_shape=f"status={result.status};answer_characters={len(result.answer_text)}",
            metadata=_metadata(
                {
                    "context_count": input_context_count,
                    "citation_count": len(result.citations),
                    "confidence_score": result.confidence_score,
                    "injection_detected": result.injection_detected,
                    "prompt_name": _metadata_str(result.metadata, "prompt_name"),
                    "prompt_version": _metadata_str(
                        result.metadata,
                        "prompt_version",
                    ),
                    "prompt_source": _metadata_str(result.metadata, "prompt_source"),
                    "ai_artifact_id": _metadata_str(
                        result.metadata,
                        "ai_artifact_id",
                    ),
                    "ai_artifact_type": _metadata_str(
                        result.metadata,
                        "ai_artifact_type",
                    ),
                    "ai_artifact_prompt_reference": _metadata_str(
                        result.metadata,
                        "ai_artifact_prompt_reference",
                    ),
                    "ai_artifact_evaluation_dataset_id": _metadata_str(
                        result.metadata,
                        "ai_artifact_evaluation_dataset_id",
                    ),
                    "ai_artifact_evaluation_run_id": _metadata_str(
                        result.metadata,
                        "ai_artifact_evaluation_run_id",
                    ),
                }
            ),
        )
    )


async def record_self_rag_observation(
    recorder: RagAiObservabilityRecorder,
    *,
    request: RagRequest,
    reflection: RagSelfReflection | None,
    skipped: bool,
) -> None:
    if reflection is None:
        status = AiObservationStatus.SKIPPED if skipped else AiObservationStatus.SUCCESS
        metadata: Mapping[str, object] = {"reflection_available": False}
        scores: tuple[AiScoreProjection, ...] = ()
        output_shape = "reflection_available=False"
    else:
        status = (
            AiObservationStatus.SUCCESS
            if reflection.answer_supported and not reflection.injection_detected
            else AiObservationStatus.DEGRADED
        )
        metadata = {
            "reflection_available": True,
            "answer_supported": reflection.answer_supported,
            "injection_detected": reflection.injection_detected,
        }
        scores = _reflection_scores(reflection)
        output_shape = (
            f"answer_supported={reflection.answer_supported};"
            f"injection_detected={reflection.injection_detected}"
        )
    await recorder.record(
        AiEvaluationObservation(
            observation_type=AiObservationType.RAG_SELF_RAG,
            name="self_rag_reflection",
            correlation_ids=correlation_ids_from_request(
                request,
                node_name="RagServiceGraph",
                observation_id=_observation_id(request, "self_rag_reflection"),
            ),
            status=status,
            input_shape=_request_shape(request),
            output_shape=output_shape,
            metadata=_metadata(metadata),
            scores=scores,
        )
    )


async def record_security_observation(
    recorder: RagAiObservabilityRecorder,
    *,
    request: RagRequest,
    stage_name: str,
    detected: bool,
    signal_count: int,
) -> None:
    await recorder.record(
        AiEvaluationObservation(
            observation_type=AiObservationType.RAG_SECURITY,
            name=stage_name,
            correlation_ids=correlation_ids_from_request(
                request,
                node_name="RagServiceGraph",
                observation_id=_observation_id(request, stage_name),
            ),
            status=(
                AiObservationStatus.DEGRADED
                if detected
                else AiObservationStatus.SUCCESS
            ),
            input_shape=_request_shape(request),
            output_shape=f"detected={detected};signals={signal_count}",
            metadata=_metadata(
                {
                    "detected": detected,
                    "signal_count": signal_count,
                }
            ),
        )
    )


async def record_answer_quality_observation(
    recorder: RagAiObservabilityRecorder,
    *,
    request: RagRequest,
    result: RagResult,
) -> None:
    scores: list[AiScoreProjection] = []
    if result.grounding_score is not None:
        scores.append(
            AiScoreProjection(
                metric_name="grounding",
                score=result.grounding_score,
                result=_score_result(result.grounding_score),
                threshold=0.5,
            )
        )
    if result.utility_score is not None:
        scores.append(
            AiScoreProjection(
                metric_name="utility",
                score=result.utility_score,
                result=_score_result(result.utility_score),
                threshold=0.5,
            )
        )
    await recorder.record(
        AiEvaluationObservation(
            observation_type=AiObservationType.RAG_ANSWER_QUALITY,
            name="answer_quality",
            correlation_ids=correlation_ids_from_request(
                request,
                node_name="RagServiceGraph",
                observation_id=_observation_id(request, "answer_quality"),
            ),
            status=_status_from_result(result),
            input_shape=f"contexts={len(result.contexts)};citations={len(result.citations)}",
            output_shape=f"status={result.status};scores={len(scores)}",
            metadata=_metadata(
                {
                    "status": result.status,
                    "context_count": len(result.contexts),
                    "citation_count": len(result.citations),
                    "injection_detected": result.injection_detected,
                }
            ),
            scores=tuple(scores),
        )
    )


def correlation_ids_from_request(
    request: RagRequest,
    *,
    node_name: str,
    observation_id: str,
    parent_observation_id: str | None = None,
) -> AiObservabilityCorrelationIds:
    return AiObservabilityCorrelationIds(
        trace_id=_metadata_str(request.metadata, "trace_id"),
        span_id=_metadata_str(request.metadata, "span_id"),
        parent_span_id=_metadata_str(request.metadata, "parent_span_id"),
        workflow_name=request.workflow_name,
        execution_id=request.execution_id,
        runtime_id=(
            _metadata_str(request.metadata, "runtime_id") or request.filters.runtime_id
        ),
        node_name=node_name,
        observation_id=observation_id,
        parent_observation_id=parent_observation_id,
        dataset_id=_metadata_str(request.metadata, "dataset_id"),
        case_id=_metadata_str(request.metadata, "case_id"),
        run_id=_metadata_str(request.metadata, "run_id"),
    )


def context_ids(contexts: tuple[RagRetrievedContext, ...]) -> tuple[str, ...]:
    return tuple(context.context_id for context in contexts)


def context_scores(contexts: tuple[RagRetrievedContext, ...]) -> tuple[float, ...]:
    return tuple(context.score for context in contexts)


def _prompt_reference_from_execution(
    execution: RagQueryModelExecution | None,
) -> AiPromptVersionReference | None:
    if execution is None:
        return None
    if execution.prompt_name is None or execution.prompt_version is None:
        return None
    return AiPromptVersionReference(
        prompt_name=execution.prompt_name,
        prompt_version=execution.prompt_version,
        prompt_hash=execution.prompt_hash,
        source=execution.prompt_source,
    )


def _prompt_reference_from_metadata(
    metadata: Mapping[str, object],
) -> AiPromptVersionReference | None:
    prompt_name = _metadata_str(metadata, "prompt_name")
    prompt_version = _metadata_str(metadata, "prompt_version")
    if prompt_name is None or prompt_version is None:
        return None
    return AiPromptVersionReference(
        prompt_name=prompt_name,
        prompt_version=prompt_version,
        prompt_hash=_metadata_str(metadata, "prompt_hash"),
        source=_metadata_str(metadata, "prompt_source"),
    )


def _status_from_result(result: RagResult) -> AiObservationStatus:
    if result.status == "failed":
        return AiObservationStatus.FAILED
    if result.injection_detected or result.status == "no_results":
        return AiObservationStatus.DEGRADED
    return AiObservationStatus.SUCCESS


def _reflection_scores(reflection: RagSelfReflection) -> tuple[AiScoreProjection, ...]:
    values = reflection.scores
    return (
        AiScoreProjection(
            metric_name="retrieval_necessity",
            score=values.retrieval_necessity,
            result=_score_result(values.retrieval_necessity),
            threshold=0.5,
        ),
        AiScoreProjection(
            metric_name="source_relevance",
            score=values.source_relevance,
            result=_score_result(values.source_relevance),
            threshold=0.5,
        ),
        AiScoreProjection(
            metric_name="answer_support",
            score=values.answer_support,
            result=_score_result(values.answer_support),
            threshold=0.5,
        ),
        AiScoreProjection(
            metric_name="usefulness",
            score=values.usefulness,
            result=_score_result(values.usefulness),
            threshold=0.5,
        ),
    )


def _score_result(score: float) -> AiScoreResult:
    return AiScoreResult.PASS if score >= 0.5 else AiScoreResult.WARN


def _metadata(values: Mapping[str, object]) -> AiMetadata:
    clean: dict[str, str | int | float | bool | None] = {}
    for key, value in values.items():
        if value is None or isinstance(value, str | int | float | bool):
            clean[key] = value
        else:
            clean[key] = str(value)
    return clean


def _metadata_str(metadata: Mapping[str, object], key: str) -> str | None:
    value = metadata.get(key)
    if isinstance(value, str) and value.strip():
        return value
    return None


def _request_shape(request: RagRequest) -> str:
    return (
        f"route={request.route};top_k={request.top_k};"
        f"filters={len(request.filters.to_dict())}"
    )


def _observation_id(request: RagRequest, stage_name: str) -> str:
    return f"{request.request_id}:{stage_name}"


def _latency_ms(duration_seconds: float) -> float:
    return duration_seconds * 1000.0
