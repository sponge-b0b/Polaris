from __future__ import annotations

from dataclasses import dataclass

import pytest

from application.observability import AiObservation
from application.observability import AiObservationStatus
from application.observability import AiObservabilityExportResult
from application.observability import AiObservationType
from core.runtime.state.runtime_context import RuntimeContext
from core.telemetry.tracing.trace_context import TraceContext
from intelligence.observability import IntelligenceAiObservabilityRecorder
from intelligence.observability import record_intelligence_generation_observation


@dataclass(slots=True)
class _RecordingProjector:
    observations: list[AiObservation]

    async def project(
        self,
        observation: AiObservation,
    ) -> AiObservabilityExportResult:
        self.observations.append(observation)
        return AiObservabilityExportResult.exported(
            idempotency_key=observation.idempotency_key(),
            observation_id=observation.correlation_ids.observation_id,
        )


class _FailingProjector:
    async def project(
        self,
        observation: AiObservation,
    ) -> AiObservabilityExportResult:
        raise RuntimeError("projection failed")


@pytest.mark.asyncio
async def test_intelligence_generation_observation_uses_runtime_correlation_ids() -> (
    None
):
    projector = _RecordingProjector(observations=[])
    context = RuntimeContext(
        runtime_id="runtime-1",
        workflow_id="morning_report",
        execution_id="exec-1",
        trace_context=TraceContext(
            trace_id="trace-1",
            span_id="span-1",
            parent_span_id="parent-1",
            correlation_id="correlation-1",
            workflow_id="morning_report",
            execution_id="exec-1",
            runtime_id="runtime-1",
            node_name="technical_agent",
        ),
    )

    await record_intelligence_generation_observation(
        IntelligenceAiObservabilityRecorder(projector),
        context=context,
        node_name="technical_agent",
        component_name="technical_llm_reasoning",
        status=AiObservationStatus.SUCCESS,
        latency_seconds=0.125,
        model_name="qwen2.5:7b",
        provider_name="LLMService",
        prompt_name="technical_agent_system_prompt",
        prompt_version="static-v1",
        prompt_hash="hash-technical-v1",
        input_shape="context_characters=100",
        output_shape="response_keys=4",
        metadata={"symbol": "SPY", "confidence": 0.72},
    )

    assert len(projector.observations) == 1
    observation = projector.observations[0]
    assert (
        observation.observation_type is AiObservationType.INTELLIGENCE_AGENT_REASONING
    )
    assert observation.name == "technical_llm_reasoning"
    assert observation.correlation_ids.trace_id == "trace-1"
    assert observation.correlation_ids.span_id == "span-1"
    assert observation.correlation_ids.parent_span_id == "parent-1"
    assert observation.correlation_ids.workflow_name == "morning_report"
    assert observation.correlation_ids.execution_id == "exec-1"
    assert observation.correlation_ids.runtime_id == "runtime-1"
    assert observation.correlation_ids.node_name == "technical_agent"
    assert observation.correlation_ids.observation_id == (
        "exec-1:technical_agent:technical_llm_reasoning"
    )
    assert observation.prompt is None
    assert observation.response is None
    assert observation.prompt_reference is not None
    assert observation.prompt_reference.prompt_name == "technical_agent_system_prompt"
    assert observation.prompt_reference.prompt_hash == "hash-technical-v1"
    assert observation.prompt_reference.source == "polaris.intelligence"
    assert observation.metadata["symbol"] == "SPY"


@pytest.mark.asyncio
async def test_intelligence_recorder_keeps_projection_failures_non_fatal() -> None:
    context = RuntimeContext(
        runtime_id="runtime-1",
        workflow_id="morning_report",
        execution_id="exec-1",
    )

    await record_intelligence_generation_observation(
        IntelligenceAiObservabilityRecorder(_FailingProjector()),
        context=context,
        node_name="technical_agent",
        component_name="technical_llm_reasoning",
        status=AiObservationStatus.SUCCESS,
        latency_seconds=0.001,
    )
