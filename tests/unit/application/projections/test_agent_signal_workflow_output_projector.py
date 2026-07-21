from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

import pytest

from application.persistence.agent_signals import AgentSignalPersistenceService
from application.projections.workflow_outputs.projection_identity import (
    build_workflow_output_projection_lineage,
)
from application.projections.workflow_outputs.projection_models import (
    WorkflowOutputProjectionStatus,
    WorkflowOutputProjectorRequest,
)
from application.projections.workflow_outputs.projectors import (
    build_risk_signal_projector_registrations,
)
from core.storage.persistence.agent_signals import (
    AgentSignalPersistenceRepository,
    AgentSignalPersistenceResult,
    AgentSignalRecord,
)
from core.storage.persistence.completed_run_archive import (
    CompletedNodeOutputRecord,
    CompletedRunExecutionMode,
    CompletedRunRecord,
    JsonObject,
)
from domain.workflow_outputs import (
    RISK_AGGREGATE_SIGNAL_OUTPUT_CONTRACT,
    WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
)


@pytest.mark.asyncio
async def test_risk_agent_signal_projector_persists_curated_signal_record() -> None:
    repository = _FakeAgentSignalRepository()
    registration = next(
        item
        for item in build_risk_signal_projector_registrations(
            AgentSignalPersistenceService(
                cast(AgentSignalPersistenceRepository, repository),
            )
        )
        if item.output_contract == RISK_AGGREGATE_SIGNAL_OUTPUT_CONTRACT
    )

    outcome = await registration.projector.project(_projector_request())

    assert outcome.status is WorkflowOutputProjectionStatus.SUCCEEDED
    assert outcome.records_written == 1
    assert len(repository.signals) == 1
    signal = repository.signals[0]
    assert signal.agent_name == "risk_aggregator_agent"
    assert signal.agent_type == "risk_aggregate"
    assert signal.symbol == "SPY"
    assert signal.directional_score == -0.2
    assert signal.confidence == 0.81
    assert signal.reasoning_text == "Composite risk remains elevated."
    assert signal.metadata["source_fingerprint"] == "fingerprint-1"


@pytest.mark.asyncio
async def test_risk_agent_signal_projector_fails_closed_on_reasoning_trace() -> None:
    repository = _FakeAgentSignalRepository()
    registration = next(
        item
        for item in build_risk_signal_projector_registrations(
            AgentSignalPersistenceService(
                cast(AgentSignalPersistenceRepository, repository),
            )
        )
        if item.output_contract == RISK_AGGREGATE_SIGNAL_OUTPUT_CONTRACT
    )

    outcome = await registration.projector.project(
        _projector_request(
            outputs={
                "symbol": "SPY",
                "directional_score": -0.2,
                "confidence": 0.81,
                "reasoning": "<think>hidden runtime reasoning without a close tag",
            },
        )
    )

    assert outcome.status is WorkflowOutputProjectionStatus.FAILED
    assert outcome.records_written == 0
    assert outcome.error_type == "ReasoningTraceViolationError"
    assert outcome.error_message is not None
    assert "hidden runtime reasoning" not in outcome.error_message
    assert repository.signals == []


class _FakeAgentSignalRepository:
    def __init__(self) -> None:
        self.signals: list[AgentSignalRecord] = []

    async def persist_signal(
        self,
        signal: AgentSignalRecord,
    ) -> AgentSignalPersistenceResult:
        self.signals.append(signal)
        return AgentSignalPersistenceResult.succeeded(
            signal_id=signal.signal_id,
            records_persisted=1,
        )


def _projector_request(
    *,
    outputs: JsonObject | None = None,
) -> WorkflowOutputProjectorRequest:
    run = _run()
    node_output = _node(outputs=outputs)
    return WorkflowOutputProjectorRequest(
        run=run,
        node_output=node_output,
        source_fingerprint="fingerprint-1",
        lineage=build_workflow_output_projection_lineage(
            run=run,
            node_output=node_output,
        ),
        requested_at=datetime(2026, 7, 10, 13, 31, tzinfo=UTC),
    )


def _run() -> CompletedRunRecord:
    return CompletedRunRecord(
        run_id="run-1",
        workflow_name="morning_report",
        workflow_id="workflow-1",
        execution_id="exec-1",
        runtime_id="runtime-1",
        status="succeeded",
        success=True,
        context_json={},
        inputs_json={"symbol": "SPY"},
        outputs_json={},
        metadata={},
        errors_json=(),
        started_at=datetime(2026, 7, 10, 13, tzinfo=UTC),
        completed_at=datetime(2026, 7, 10, 13, 35, tzinfo=UTC),
        duration_seconds=300.0,
        node_count=1,
        completed_node_count=1,
        failed_node_count=0,
        execution_mode=CompletedRunExecutionMode.NORMAL,
    )


def _node(
    *,
    outputs: JsonObject | None = None,
) -> CompletedNodeOutputRecord:
    return CompletedNodeOutputRecord(
        node_output_id="node-output-risk",
        run_id="run-1",
        workflow_name="morning_report",
        execution_id="exec-1",
        node_name="risk_aggregator_agent",
        node_type="risk",
        output_contract=RISK_AGGREGATE_SIGNAL_OUTPUT_CONTRACT,
        output_schema_version=WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
        status="succeeded",
        success=True,
        outputs=outputs
        or cast(
            JsonObject,
            {
                "symbol": "SPY",
                "directional_score": -0.2,
                "confidence": 0.81,
                "regime": "elevated_risk",
                "risks": ["drawdown pressure"],
                "features": {"composite_risk": 0.66},
                "reasoning": "Composite risk remains elevated.",
            },
        ),
        metadata={"quality_status": "normal"},
        errors_json=(),
        started_at=datetime(2026, 7, 10, 13, 29, tzinfo=UTC),
        completed_at=datetime(2026, 7, 10, 13, 31, tzinfo=UTC),
        duration_seconds=120.0,
    )
