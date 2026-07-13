from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from typing import Protocol

from application.observability.ai_observability_contracts import AiEvaluationObservation
from application.observability.ai_observability_contracts import AiGenerationObservation
from application.observability.ai_observability_contracts import AiObservation
from application.observability.ai_observability_contracts import (
    AiObservabilityCapturePolicy,
)
from application.observability.ai_observability_contracts import (
    AiObservabilityCorrelationIds,
)
from application.observability.ai_observability_contracts import (
    AiObservabilityExportResult,
)
from application.observability.ai_observability_contracts import AiRedactionMode
from application.observability.ai_prompt_management import AiPromptGovernancePolicy
from application.observability.ai_observability_security import (
    AiObservabilityRedactionReport,
)
from application.observability.ai_observability_security import sanitize_metadata
from application.observability.ai_observability_security import sanitize_text
from application.observability.ai_observability_contracts import AiRerankingObservation
from application.observability.ai_observability_contracts import AiRetrievalObservation
from application.observability.ai_observability_contracts import AiScoreProjection

logger = logging.getLogger(__name__)

LangfusePayload = dict[str, object]


class LangfuseExportClient(Protocol):
    """Transport boundary for Langfuse export clients."""

    async def export(self, payload: LangfusePayload) -> object:
        """Export an already-sanitized Langfuse payload."""


class AiObservabilitySink(Protocol):
    """Projection sink for typed Polaris AI observations."""

    async def export(self, observation: AiObservation) -> AiObservabilityExportResult:
        """Export one typed AI observation."""


@dataclass(frozen=True, slots=True)
class LangfuseObservationMapper:
    """Map Polaris AI observations to Langfuse-boundary payloads."""

    capture_policy: AiObservabilityCapturePolicy
    environment: str
    release: str | None = None
    prompt_governance_policy: AiPromptGovernancePolicy | None = None

    def to_payload(self, observation: AiObservation) -> LangfusePayload:
        self._validate_prompt_reference(observation)
        redaction_report = AiObservabilityRedactionReport.empty()
        payload: LangfusePayload = {
            "idempotency_key": observation.idempotency_key(),
            "timestamp": _serialize_datetime(observation.created_at),
            "name": observation.name,
            "type": observation.observation_type.value,
            "family": observation.family.value,
            "status": observation.status.value,
            "environment": self.environment,
            "release": self.release,
            "model": observation.model_name,
            "provider": observation.provider_name,
            "latency_ms": observation.latency_ms,
            "input_shape": observation.input_shape,
            "output_shape": observation.output_shape,
            "metadata": sanitize_metadata(
                observation.metadata,
                policy=self.capture_policy,
                report=redaction_report,
            ),
            "correlation": _correlation_payload(observation.correlation_ids),
            "otel": _otel_payload(observation.correlation_ids),
            "capture_policy": _capture_policy_payload(self.capture_policy),
        }
        if observation.prompt_reference is not None:
            payload["prompt"] = _prompt_reference_payload(observation)
        self._add_text_payload(payload, observation, redaction_report)
        self._add_stage_payload(payload, observation, redaction_report)
        payload["redaction"] = {
            **redaction_report.to_payload(),
            "mode": self.capture_policy.redaction_mode.value,
            "retention_days": self.capture_policy.retention_days,
            "max_payload_characters": self.capture_policy.max_payload_characters,
            "max_metadata_value_characters": (
                self.capture_policy.max_metadata_value_characters
            ),
        }
        return payload

    def _validate_prompt_reference(self, observation: AiObservation) -> None:
        policy = self.prompt_governance_policy or AiPromptGovernancePolicy(
            environment=self.environment
        )
        policy.validate_observation(observation)

    def _add_text_payload(
        self,
        payload: LangfusePayload,
        observation: AiObservation,
        redaction_report: AiObservabilityRedactionReport,
    ) -> None:
        prompt_text = _capture_text(
            observation.prompt,
            field_path="prompt_text",
            enabled=self.capture_policy.capture_prompts,
            policy=self.capture_policy,
            report=redaction_report,
        )
        response_text = _capture_text(
            observation.response,
            field_path="response_text",
            enabled=self.capture_policy.capture_responses,
            policy=self.capture_policy,
            report=redaction_report,
        )
        payload["prompt_captured"] = prompt_text is not None
        payload["response_captured"] = response_text is not None
        if prompt_text is not None:
            payload["prompt_text"] = prompt_text
            payload["prompt_truncated"] = _is_truncated(
                observation.prompt,
                self.capture_policy.max_payload_characters,
            )
        if response_text is not None:
            payload["response_text"] = response_text
            payload["response_truncated"] = _is_truncated(
                observation.response,
                self.capture_policy.max_payload_characters,
            )

    def _add_stage_payload(
        self,
        payload: LangfusePayload,
        observation: AiObservation,
        redaction_report: AiObservabilityRedactionReport,
    ) -> None:
        if isinstance(observation, AiGenerationObservation):
            payload["generation"] = {
                "input_tokens": observation.token_count_input,
                "output_tokens": observation.token_count_output,
                "cost_usd": observation.cost_usd,
            }
        if isinstance(observation, AiRetrievalObservation):
            payload["retrieval"] = {
                "retrieved_count": observation.retrieved_count,
                "selected_context_ids": list(observation.selected_context_ids),
                "scores": list(observation.retrieval_scores),
            }
        if isinstance(observation, AiRerankingObservation):
            payload["reranking"] = {
                "candidate_count": observation.candidate_count,
                "selected_count": observation.selected_count,
                "scores": list(observation.reranking_scores),
            }
        if isinstance(observation, AiEvaluationObservation):
            payload["evaluation"] = {
                "evaluated_observation_id": observation.evaluated_observation_id,
                "dataset_id": observation.correlation_ids.dataset_id,
                "case_id": observation.correlation_ids.case_id,
                "run_id": observation.correlation_ids.run_id,
                "scores": [
                    _score_payload(score, self.capture_policy, redaction_report)
                    for score in observation.scores
                ],
            }


@dataclass(frozen=True, slots=True)
class LangfuseAiObservabilitySink:
    """Langfuse projection sink for typed Polaris AI observations."""

    client: LangfuseExportClient
    mapper: LangfuseObservationMapper

    async def export(self, observation: AiObservation) -> AiObservabilityExportResult:
        idempotency_key = observation.idempotency_key()
        try:
            response = await self.client.export(self.mapper.to_payload(observation))
        except Exception as exc:
            logger.exception(
                "Langfuse AI-observability export failed.",
                extra={
                    "idempotency_key": idempotency_key,
                    "observation_type": observation.observation_type.value,
                    "observation_name": observation.name,
                },
            )
            return AiObservabilityExportResult.failed(
                idempotency_key=idempotency_key,
                error_message=str(exc),
            )
        return _export_result_from_response(
            idempotency_key=idempotency_key,
            observation=observation,
            response=response,
        )


@dataclass(frozen=True, slots=True)
class AiObservabilityProjector:
    """Application boundary for projecting typed AI observations."""

    sink: AiObservabilitySink

    async def project(
        self,
        observation: AiObservation,
    ) -> AiObservabilityExportResult:
        return await self.sink.export(observation)


def _export_result_from_response(
    *,
    idempotency_key: str,
    observation: AiObservation,
    response: object,
) -> AiObservabilityExportResult:
    response_map = response if isinstance(response, dict) else {}
    return AiObservabilityExportResult.exported(
        idempotency_key=idempotency_key,
        observation_id=observation.correlation_ids.observation_id,
        external_trace_id=_optional_string(
            response_map.get("external_trace_id") or response_map.get("trace_id")
        ),
        external_observation_id=_optional_string(
            response_map.get("external_observation_id")
            or response_map.get("observation_id")
        ),
        dataset_id=_optional_string(
            response_map.get("dataset_id") or observation.correlation_ids.dataset_id
        ),
        case_id=_optional_string(
            response_map.get("case_id") or observation.correlation_ids.case_id
        ),
        run_id=_optional_string(
            response_map.get("run_id") or observation.correlation_ids.run_id
        ),
    )


def _correlation_payload(
    correlation_ids: AiObservabilityCorrelationIds,
) -> dict[str, str | None]:
    return {
        "trace_id": correlation_ids.trace_id,
        "span_id": correlation_ids.span_id,
        "parent_span_id": correlation_ids.parent_span_id,
        "workflow_name": correlation_ids.workflow_name,
        "execution_id": correlation_ids.execution_id,
        "runtime_id": correlation_ids.runtime_id,
        "node_name": correlation_ids.node_name,
        "observation_id": correlation_ids.observation_id,
        "parent_observation_id": correlation_ids.parent_observation_id,
        "dataset_id": correlation_ids.dataset_id,
        "case_id": correlation_ids.case_id,
        "run_id": correlation_ids.run_id,
    }


def _otel_payload(
    correlation_ids: AiObservabilityCorrelationIds,
) -> dict[str, str | None]:
    return {
        "trace_id": correlation_ids.trace_id,
        "span_id": correlation_ids.span_id,
        "parent_span_id": correlation_ids.parent_span_id,
    }


def _capture_policy_payload(
    policy: AiObservabilityCapturePolicy,
) -> dict[str, str | int | bool]:
    return {
        "capture_prompts": policy.capture_prompts,
        "capture_responses": policy.capture_responses,
        "capture_contexts": policy.capture_contexts,
        "capture_user_input": policy.capture_user_input,
        "redaction_mode": policy.redaction_mode.value,
        "max_payload_characters": policy.max_payload_characters,
        "max_metadata_value_characters": policy.max_metadata_value_characters,
        "retention_days": policy.retention_days,
    }


def _prompt_reference_payload(observation: AiObservation) -> dict[str, str | None]:
    prompt_reference = observation.prompt_reference
    if prompt_reference is None:
        return {}
    return {
        "name": prompt_reference.prompt_name,
        "version": prompt_reference.prompt_version,
        "hash": prompt_reference.prompt_hash,
        "source": prompt_reference.source,
    }


def _score_payload(
    score: AiScoreProjection,
    policy: AiObservabilityCapturePolicy,
    redaction_report: AiObservabilityRedactionReport,
) -> dict[str, str | float | None]:
    return {
        "metric_name": score.metric_name,
        "score": score.score,
        "threshold": score.threshold,
        "result": score.result.value,
        "reason": _capture_text(
            score.reason,
            field_path=f"evaluation.scores.{score.metric_name}.reason",
            enabled=policy.capture_responses,
            policy=policy,
            report=redaction_report,
        ),
        "evaluator_model": score.evaluator_model,
        "evaluator_provider": score.evaluator_provider,
    }


def _capture_text(
    value: str | None,
    *,
    field_path: str,
    enabled: bool,
    policy: AiObservabilityCapturePolicy,
    report: AiObservabilityRedactionReport,
) -> str | None:
    if value is None:
        return None
    if not enabled or policy.redaction_mode is not AiRedactionMode.PERMISSIVE:
        report.record_dropped(field_path)
        return None
    return sanitize_text(
        value,
        field_path=field_path,
        policy=policy,
        report=report,
    )


def _is_truncated(value: str | None, max_characters: int) -> bool:
    return value is not None and len(value) > max_characters


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value or None
    return str(value)


def _serialize_datetime(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.isoformat()
