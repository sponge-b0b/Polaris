from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from application.observability import AiGenerationObservation
from application.observability.ai_observability_contracts import AiMetadata
from application.observability import AiObservation
from application.observability import AiObservationStatus
from application.observability import AiObservationType
from application.observability import AiObservabilityCorrelationIds
from application.observability import AiObservabilityExportResult
from application.observability import AiPromptVersionReference
from core.runtime.state.runtime_context import RuntimeContext

logger = logging.getLogger(__name__)


class IntelligenceAiObservabilityProjectorPort(Protocol):
    """Projection boundary for typed AI observations emitted by intelligence code."""

    async def project(
        self,
        observation: AiObservation,
    ) -> AiObservabilityExportResult: ...


@dataclass(frozen=True, slots=True)
class IntelligenceAiObservabilityRecorder:
    """Non-fatal intelligence AI-observability recorder.

    Runtime node outputs remain the canonical workflow evidence. This recorder
    only projects sanitized, typed AI-observability observations for Langfuse.
    """

    projector: IntelligenceAiObservabilityProjectorPort | None = None

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
            logger.exception(
                "Intelligence AI-observability projection failed.",
                extra={
                    "observation_type": observation.observation_type.value,
                    "observation_name": observation.name,
                    "observation_id": observation.correlation_ids.observation_id,
                },
            )


async def record_intelligence_generation_observation(
    recorder: IntelligenceAiObservabilityRecorder,
    *,
    context: RuntimeContext,
    node_name: str,
    component_name: str,
    status: AiObservationStatus,
    latency_seconds: float,
    model_name: str | None = None,
    provider_name: str | None = None,
    prompt_name: str | None = None,
    prompt_version: str | None = None,
    prompt_hash: str | None = None,
    prompt_source: str | None = "polaris.intelligence",
    input_shape: str | None = None,
    output_shape: str | None = None,
    metadata: Mapping[str, object] | None = None,
) -> None:
    """Record an LLM-backed intelligence generation observation."""

    await recorder.record(
        AiGenerationObservation(
            observation_type=AiObservationType.INTELLIGENCE_AGENT_REASONING,
            name=component_name,
            correlation_ids=correlation_ids_from_runtime(
                context,
                node_name=node_name,
                observation_id=_observation_id(context, node_name, component_name),
            ),
            status=status,
            model_name=model_name,
            provider_name=provider_name,
            latency_ms=_latency_ms(latency_seconds),
            input_shape=input_shape,
            output_shape=output_shape,
            prompt_reference=_prompt_reference(
                prompt_name,
                prompt_version,
                prompt_hash,
                prompt_source,
            ),
            metadata=_metadata(metadata or {}),
        )
    )


async def record_strategy_synthesis_observation(
    recorder: IntelligenceAiObservabilityRecorder,
    *,
    context: RuntimeContext,
    node_name: str,
    status: AiObservationStatus,
    latency_seconds: float,
    input_shape: str,
    output_shape: str,
    metadata: Mapping[str, object],
) -> None:
    """Record the structured-hypothesis strategy synthesis decision projection."""

    await recorder.record(
        AiGenerationObservation(
            observation_type=AiObservationType.INTELLIGENCE_STRATEGY_SYNTHESIS,
            name="strategy_synthesis",
            correlation_ids=correlation_ids_from_runtime(
                context,
                node_name=node_name,
                observation_id=_observation_id(
                    context, node_name, "strategy_synthesis"
                ),
            ),
            status=status,
            provider_name="StrategySynthesisAgent",
            latency_ms=_latency_ms(latency_seconds),
            input_shape=input_shape,
            output_shape=output_shape,
            metadata=_metadata(metadata),
        )
    )


def correlation_ids_from_runtime(
    context: RuntimeContext,
    *,
    node_name: str,
    observation_id: str,
    parent_observation_id: str | None = None,
) -> AiObservabilityCorrelationIds:
    trace_context = context.trace_context
    return AiObservabilityCorrelationIds(
        trace_id=trace_context.trace_id if trace_context is not None else None,
        span_id=trace_context.span_id if trace_context is not None else None,
        parent_span_id=(
            trace_context.parent_span_id if trace_context is not None else None
        ),
        workflow_name=context.workflow_id,
        execution_id=context.execution_id,
        runtime_id=context.runtime_id,
        node_name=node_name,
        observation_id=observation_id,
        parent_observation_id=parent_observation_id,
    )


def llm_model_name(llm_service: object) -> str | None:
    service_model = getattr(llm_service, "model", None)
    if isinstance(service_model, str) and service_model.strip():
        return service_model
    llm_client = getattr(llm_service, "llm_client", None)
    client_model = getattr(llm_client, "llm_model", None)
    if isinstance(client_model, str) and client_model.strip():
        return client_model
    return None


def _prompt_reference(
    prompt_name: str | None,
    prompt_version: str | None,
    prompt_hash: str | None,
    prompt_source: str | None,
) -> AiPromptVersionReference | None:
    if prompt_name is None or prompt_version is None:
        return None
    return AiPromptVersionReference(
        prompt_name=prompt_name,
        prompt_version=prompt_version,
        prompt_hash=prompt_hash,
        source=prompt_source,
    )


def _metadata(values: Mapping[str, object]) -> AiMetadata:
    clean: dict[str, str | int | float | bool | None] = {}
    for key, value in values.items():
        if value is None or isinstance(value, str | int | float | bool):
            clean[key] = value
        else:
            clean[key] = str(value)
    return clean


def _observation_id(
    context: RuntimeContext,
    node_name: str,
    component_name: str,
) -> str:
    return f"{context.execution_id}:{node_name}:{component_name}"


def _latency_ms(duration_seconds: float) -> float:
    return duration_seconds * 1000.0
