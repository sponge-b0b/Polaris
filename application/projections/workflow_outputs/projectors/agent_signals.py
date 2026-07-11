from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC
from datetime import datetime
from typing import Final
from application.persistence.agent_signals import AgentSignalPersistenceService
from application.projections.workflow_outputs.projection_models import (
    WorkflowOutputProjectionOutcome,
)
from application.projections.workflow_outputs.projection_models import (
    WorkflowOutputProjectionStatus,
)
from application.projections.workflow_outputs.projection_models import (
    WorkflowOutputProjectorRequest,
)
from application.projections.workflow_outputs.projection_registry import (
    WorkflowOutputProjectorRegistration,
)
from core.storage.persistence.agent_signals import AgentSignalRecord
from core.storage.persistence.agent_signals import JsonObject
from core.storage.persistence.agent_signals import JsonValue
from core.storage.persistence.agent_signals import new_agent_signal_id
from domain.workflow_outputs import EXECUTION_RISK_DECISION_OUTPUT_CONTRACT
from domain.workflow_outputs import RISK_AGGREGATE_INPUT_SIGNAL_OUTPUT_CONTRACT
from domain.workflow_outputs import RISK_AGGREGATE_SIGNAL_OUTPUT_CONTRACT
from domain.workflow_outputs import RISK_DRAWDOWN_SIGNAL_OUTPUT_CONTRACT
from domain.workflow_outputs import RISK_EXPOSURE_SIGNAL_OUTPUT_CONTRACT
from domain.workflow_outputs import RISK_VOLATILITY_SIGNAL_OUTPUT_CONTRACT
from domain.workflow_outputs import WORKFLOW_OUTPUT_SCHEMA_VERSION_V1

RISK_DRAWDOWN_SIGNAL_PROJECTOR_NAME: Final = "risk_drawdown_signal_projector"
RISK_VOLATILITY_SIGNAL_PROJECTOR_NAME: Final = "risk_volatility_signal_projector"
RISK_EXPOSURE_SIGNAL_PROJECTOR_NAME: Final = "risk_exposure_signal_projector"
RISK_AGGREGATE_INPUT_SIGNAL_PROJECTOR_NAME: Final = (
    "risk_aggregate_input_signal_projector"
)
RISK_AGGREGATE_SIGNAL_PROJECTOR_NAME: Final = "risk_aggregate_signal_projector"
EXECUTION_RISK_DECISION_PROJECTOR_NAME: Final = "execution_risk_decision_projector"


class AgentSignalWorkflowOutputProjector:
    """Project eligible agent workflow evidence into curated signal records."""

    def __init__(
        self,
        *,
        agent_signal_persistence_service: AgentSignalPersistenceService,
        projector_name: str,
        agent_name: str,
        agent_type: str,
        signal_key: str,
    ) -> None:
        self._agent_signal_persistence_service = agent_signal_persistence_service
        self._projector_name = projector_name
        self._agent_name = agent_name
        self._agent_type = agent_type
        self._signal_key = signal_key

    @property
    def projector_name(self) -> str:
        return self._projector_name

    async def project(
        self,
        request: WorkflowOutputProjectorRequest,
    ) -> WorkflowOutputProjectionOutcome:
        outputs = _mapping(request.node_output.outputs)
        timestamp = _timestamp(request)
        signal = AgentSignalRecord(
            signal_id=new_agent_signal_id(
                self._agent_name,
                execution_id=request.run.execution_id,
                node_name=request.node_output.node_name,
                signal_key=self._signal_key,
            ),
            agent_name=self._agent_name,
            agent_type=self._agent_type,
            timestamp=timestamp,
            workflow_name=request.run.workflow_name,
            execution_id=request.run.execution_id,
            runtime_id=request.run.runtime_id,
            node_name=request.node_output.node_name,
            symbol=_symbol(request, outputs),
            universe=_string_tuple(outputs.get("universe")),
            directional_score=_score(outputs.get("directional_score"), signed=True),
            confidence=_score(outputs.get("confidence"), signed=False),
            regime=_optional_text(outputs.get("regime")),
            signals=_json_object_from_sequence(outputs.get("signals")),
            risks=_json_object_from_sequence(outputs.get("risks")),
            recommendations=_json_object_from_sequence(outputs.get("recommendations")),
            features=_json_mapping(outputs.get("features")),
            reasoning_text=_reasoning_text(outputs),
            llm_response=_llm_response(outputs),
            metadata={
                "source_fingerprint": request.source_fingerprint,
                "output_contract": request.node_output.output_contract,
                "output_schema_version": request.node_output.output_schema_version,
                "node_output_id": request.node_output.node_output_id,
            },
        )
        result = await self._agent_signal_persistence_service.persist_signal(signal)
        if not result.success:
            return _failed(request, result.error or "Agent signal persistence failed.")
        return _outcome(
            request=request,
            status=WorkflowOutputProjectionStatus.SUCCEEDED,
            records_written=result.records_persisted,
            message="Agent workflow output projected into curated signal record.",
        )


def build_risk_signal_projector_registrations(
    agent_signal_persistence_service: AgentSignalPersistenceService,
) -> tuple[WorkflowOutputProjectorRegistration, ...]:
    """Build canonical risk signal projector registrations."""
    specs = (
        (
            RISK_DRAWDOWN_SIGNAL_PROJECTOR_NAME,
            RISK_DRAWDOWN_SIGNAL_OUTPUT_CONTRACT,
            ("drawdown_risk_agent",),
            "drawdown_risk_agent",
            "risk_drawdown",
            "drawdown",
        ),
        (
            RISK_VOLATILITY_SIGNAL_PROJECTOR_NAME,
            RISK_VOLATILITY_SIGNAL_OUTPUT_CONTRACT,
            ("volatility_risk_agent",),
            "volatility_risk_agent",
            "risk_volatility",
            "volatility",
        ),
        (
            RISK_EXPOSURE_SIGNAL_PROJECTOR_NAME,
            RISK_EXPOSURE_SIGNAL_OUTPUT_CONTRACT,
            ("exposure_risk_agent",),
            "exposure_risk_agent",
            "risk_exposure",
            "exposure",
        ),
        (
            RISK_AGGREGATE_INPUT_SIGNAL_PROJECTOR_NAME,
            RISK_AGGREGATE_INPUT_SIGNAL_OUTPUT_CONTRACT,
            ("risk_signal_builder",),
            "risk_signal_builder",
            "risk_aggregate_input",
            "aggregate_input",
        ),
        (
            RISK_AGGREGATE_SIGNAL_PROJECTOR_NAME,
            RISK_AGGREGATE_SIGNAL_OUTPUT_CONTRACT,
            ("risk_aggregator_agent",),
            "risk_aggregator_agent",
            "risk_aggregate",
            "aggregate",
        ),
        (
            EXECUTION_RISK_DECISION_PROJECTOR_NAME,
            EXECUTION_RISK_DECISION_OUTPUT_CONTRACT,
            ("execution_risk_guard",),
            "execution_risk_guard",
            "execution_risk_decision",
            "execution_decision",
        ),
    )
    return tuple(
        WorkflowOutputProjectorRegistration(
            projector_name=projector_name,
            output_contract=output_contract,
            output_schema_version=WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
            projector=AgentSignalWorkflowOutputProjector(
                agent_signal_persistence_service=agent_signal_persistence_service,
                projector_name=projector_name,
                agent_name=agent_name,
                agent_type=agent_type,
                signal_key=signal_key,
            ),
            supported_node_names=supported_node_names,
        )
        for (
            projector_name,
            output_contract,
            supported_node_names,
            agent_name,
            agent_type,
            signal_key,
        ) in specs
    )


def _timestamp(request: WorkflowOutputProjectorRequest) -> datetime:
    return (
        request.node_output.completed_at
        or request.node_output.started_at
        or request.run.completed_at
        or request.run.started_at
        or request.requested_at
        or datetime.now(UTC)
    )


def _symbol(
    request: WorkflowOutputProjectorRequest,
    outputs: Mapping[str, object],
) -> str | None:
    features = _mapping(outputs.get("features"))
    for value in (
        outputs.get("symbol"),
        features.get("symbol"),
        request.run.inputs_json.get("symbol"),
        request.node_output.metadata.get("symbol"),
    ):
        text = _optional_text(value)
        if text is not None:
            return text.upper()
    return None


def _reasoning_text(outputs: Mapping[str, object]) -> str | None:
    for key in ("reasoning", "reasoning_text", "thesis"):
        text = _optional_text(outputs.get(key))
        if text is not None:
            return text
    features = _mapping(outputs.get("features"))
    return _optional_text(features.get("thesis"))


def _llm_response(outputs: Mapping[str, object]) -> str | None:
    value = outputs.get("llm_response")
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return json.dumps(_json_value(value), sort_keys=True, separators=(",", ":"))


def _mapping(value: object) -> Mapping[str, object]:
    if isinstance(value, Mapping):
        return {str(key): item for key, item in value.items()}
    return {}


def _json_mapping(value: object) -> JsonObject:
    if not isinstance(value, Mapping):
        return {}
    return {str(key): _json_value(item) for key, item in value.items()}


def _json_value(value: object) -> JsonValue:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return _json_mapping(value)
    if isinstance(value, (list, tuple)):
        return tuple(_json_value(item) for item in value)
    return str(value)


def _json_object_from_sequence(value: object) -> JsonObject:
    if not isinstance(value, list):
        return {}
    return {"items": tuple(_json_value(item) for item in value)}


def _string_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(item) for item in value if item is not None and str(item).strip())


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _score(value: object, *, signed: bool) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    numeric = float(value)
    if signed and -1.0 <= numeric <= 1.0:
        return numeric
    if not signed and 0.0 <= numeric <= 1.0:
        return numeric
    return None


def _outcome(
    *,
    request: WorkflowOutputProjectorRequest,
    status: WorkflowOutputProjectionStatus,
    records_written: int,
    message: str,
) -> WorkflowOutputProjectionOutcome:
    return WorkflowOutputProjectionOutcome(
        status=status,
        projector_name=request.node_output.output_contract
        and _projector_name_for_contract(request.node_output.output_contract)
        or "agent_signal_projector",
        node_name=request.node_output.node_name,
        output_contract=request.node_output.output_contract or "unknown",
        output_schema_version=request.node_output.output_schema_version or 1,
        source_fingerprint=request.source_fingerprint,
        records_written=records_written,
        message=message,
    )


def _failed(
    request: WorkflowOutputProjectorRequest,
    error: str,
) -> WorkflowOutputProjectionOutcome:
    return WorkflowOutputProjectionOutcome(
        status=WorkflowOutputProjectionStatus.FAILED,
        projector_name=_projector_name_for_contract(
            request.node_output.output_contract
        ),
        node_name=request.node_output.node_name,
        output_contract=request.node_output.output_contract or "unknown",
        output_schema_version=request.node_output.output_schema_version or 1,
        source_fingerprint=request.source_fingerprint,
        error_type="PersistenceError",
        error_message=error,
        message="Agent signal projection failed.",
    )


def _projector_name_for_contract(output_contract: str | None) -> str:
    return {
        RISK_DRAWDOWN_SIGNAL_OUTPUT_CONTRACT: RISK_DRAWDOWN_SIGNAL_PROJECTOR_NAME,
        RISK_VOLATILITY_SIGNAL_OUTPUT_CONTRACT: RISK_VOLATILITY_SIGNAL_PROJECTOR_NAME,
        RISK_EXPOSURE_SIGNAL_OUTPUT_CONTRACT: RISK_EXPOSURE_SIGNAL_PROJECTOR_NAME,
        RISK_AGGREGATE_INPUT_SIGNAL_OUTPUT_CONTRACT: RISK_AGGREGATE_INPUT_SIGNAL_PROJECTOR_NAME,
        RISK_AGGREGATE_SIGNAL_OUTPUT_CONTRACT: RISK_AGGREGATE_SIGNAL_PROJECTOR_NAME,
        EXECUTION_RISK_DECISION_OUTPUT_CONTRACT: EXECUTION_RISK_DECISION_PROJECTOR_NAME,
    }.get(output_contract or "", "agent_signal_projector")
