from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC
from datetime import datetime
from typing import Final
from typing import cast

from application.persistence.recommendations import RecommendationPersistenceService
from application.persistence.strategy import StrategyPersistenceService
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
from core.storage.persistence.completed_run_archive import CompletedNodeOutputRecord
from core.storage.persistence.lineage import JsonObject
from core.storage.persistence.recommendations import RecommendationPersistenceBundle
from core.storage.persistence.recommendations import RecommendationRationaleRecord
from core.storage.persistence.recommendations import RecommendationRecord
from core.storage.persistence.recommendations import new_recommendation_child_id
from core.storage.persistence.recommendations import new_recommendation_id
from core.storage.persistence.strategy import StrategyHypothesisEvaluationRecord
from core.storage.persistence.strategy import StrategyHypothesisRecord
from core.storage.persistence.strategy import StrategyPersistenceBundle
from core.storage.persistence.strategy import StrategySynthesisDecisionRecord
from core.storage.persistence.strategy import new_strategy_decision_id
from core.storage.persistence.strategy import new_strategy_evaluation_id
from core.storage.persistence.strategy import new_strategy_hypothesis_id
from domain.workflow_outputs import STRATEGY_BEAR_HYPOTHESIS_OUTPUT_CONTRACT
from domain.workflow_outputs import STRATEGY_BULL_HYPOTHESIS_OUTPUT_CONTRACT
from domain.workflow_outputs import STRATEGY_SIDEWAYS_HYPOTHESIS_OUTPUT_CONTRACT
from domain.workflow_outputs import STRATEGY_SYNTHESIS_OUTPUT_CONTRACT
from domain.workflow_outputs import WORKFLOW_OUTPUT_SCHEMA_VERSION_V1
from intelligence.strategy.hypothesis.hypothesis import StrategyHypothesis
from intelligence.strategy.synthesis.contracts import StrategySynthesisDecision

STRATEGY_BULL_HYPOTHESIS_PROJECTOR_NAME: Final = "strategy_bull_hypothesis_projector"
STRATEGY_BEAR_HYPOTHESIS_PROJECTOR_NAME: Final = "strategy_bear_hypothesis_projector"
STRATEGY_SIDEWAYS_HYPOTHESIS_PROJECTOR_NAME: Final = (
    "strategy_sideways_hypothesis_projector"
)
STRATEGY_SYNTHESIS_PROJECTOR_NAME: Final = "strategy_synthesis_projector"

_HYPOTHESIS_CONTRACTS: Final = {
    STRATEGY_BULL_HYPOTHESIS_OUTPUT_CONTRACT,
    STRATEGY_BEAR_HYPOTHESIS_OUTPUT_CONTRACT,
    STRATEGY_SIDEWAYS_HYPOTHESIS_OUTPUT_CONTRACT,
}


class StrategyHypothesisWorkflowOutputProjector:
    """Project one strategy perspective hypothesis into a first-class record."""

    def __init__(
        self,
        *,
        strategy_persistence_service: StrategyPersistenceService,
        projector_name: str,
    ) -> None:
        self._strategy_persistence_service = strategy_persistence_service
        self._projector_name = projector_name

    @property
    def projector_name(self) -> str:
        return self._projector_name

    async def project(
        self,
        request: WorkflowOutputProjectorRequest,
    ) -> WorkflowOutputProjectionOutcome:
        hypothesis = _hypothesis_from_node_output(request.node_output)
        if hypothesis is None:
            return _skipped(
                request, self.projector_name, "Strategy hypothesis missing."
            )
        symbol = _symbol_from_request(request)
        if symbol is None:
            return _skipped(request, self.projector_name, "Strategy symbol missing.")
        record = _hypothesis_record(
            request=request,
            node_output=request.node_output,
            hypothesis=hypothesis,
            symbol=symbol,
        )
        result = await self._strategy_persistence_service.persist_hypotheses((record,))
        if not result.success:
            return _failed(
                request,
                self.projector_name,
                result.error or "Strategy hypothesis persistence failed.",
            )
        return _outcome(
            request=request,
            projector_name=self.projector_name,
            status=WorkflowOutputProjectionStatus.SUCCEEDED,
            records_written=result.records_persisted,
            message="Strategy hypothesis projected into curated strategy record.",
        )


class StrategySynthesisWorkflowOutputProjector:
    """Project strategy synthesis and recommendation records from workflow evidence."""

    def __init__(
        self,
        *,
        strategy_persistence_service: StrategyPersistenceService,
        recommendation_persistence_service: RecommendationPersistenceService,
    ) -> None:
        self._strategy_persistence_service = strategy_persistence_service
        self._recommendation_persistence_service = recommendation_persistence_service

    @property
    def projector_name(self) -> str:
        return STRATEGY_SYNTHESIS_PROJECTOR_NAME

    async def project(
        self,
        request: WorkflowOutputProjectorRequest,
    ) -> WorkflowOutputProjectionOutcome:
        outputs = _mapping(request.node_output.outputs)
        features = _mapping(outputs.get("features"))
        decision_payload = _mapping(features.get("strategy_synthesis_decision"))
        if not decision_payload:
            return _skipped(
                request, self.projector_name, "Strategy synthesis decision missing."
            )
        decision = StrategySynthesisDecision.from_dict(dict(decision_payload))
        symbol = _symbol_from_request(request, outputs=outputs, features=features)
        if symbol is None:
            return _skipped(request, self.projector_name, "Strategy symbol missing.")

        hypotheses = _hypothesis_records_from_bundle(request, symbol=symbol)
        evidence_fingerprint = _decision_evidence_fingerprint(
            decision=decision,
            hypotheses=hypotheses,
            request=request,
        )
        decision_record = _decision_record(
            request=request,
            decision=decision,
            symbol=symbol,
            evidence_fingerprint=evidence_fingerprint,
        )
        evaluations = _evaluation_records(
            request=request,
            decision=decision,
            decision_record=decision_record,
            hypotheses=hypotheses,
        )
        strategy_result = await self._strategy_persistence_service.persist_bundle(
            StrategyPersistenceBundle(
                decision=decision_record,
                hypotheses=hypotheses,
                evaluations=evaluations,
            )
        )
        if not strategy_result.success:
            return _failed(
                request,
                self.projector_name,
                strategy_result.error or "Strategy synthesis persistence failed.",
            )

        records_written = strategy_result.records_persisted
        recommendation_bundle = _strategy_recommendation_bundle(
            request=request,
            decision=decision,
            decision_record=decision_record,
        )
        if recommendation_bundle is not None:
            recommendation_result = (
                await self._recommendation_persistence_service.persist_bundle(
                    recommendation_bundle
                )
            )
            if not recommendation_result.success:
                return _failed(
                    request,
                    self.projector_name,
                    recommendation_result.error
                    or "Strategy recommendation persistence failed.",
                )
            records_written += recommendation_result.records_persisted

        return _outcome(
            request=request,
            projector_name=self.projector_name,
            status=WorkflowOutputProjectionStatus.SUCCEEDED,
            records_written=records_written,
            message=(
                "Strategy synthesis projected into strategy decision/evaluation "
                "records and downstream recommendation mapping."
            ),
        )


def build_strategy_projector_registrations(
    *,
    strategy_persistence_service: StrategyPersistenceService,
    recommendation_persistence_service: RecommendationPersistenceService,
) -> tuple[WorkflowOutputProjectorRegistration, ...]:
    """Build canonical strategy projector registrations."""
    hypothesis_specs = (
        (
            STRATEGY_BULL_HYPOTHESIS_PROJECTOR_NAME,
            STRATEGY_BULL_HYPOTHESIS_OUTPUT_CONTRACT,
            ("bull_agent",),
        ),
        (
            STRATEGY_BEAR_HYPOTHESIS_PROJECTOR_NAME,
            STRATEGY_BEAR_HYPOTHESIS_OUTPUT_CONTRACT,
            ("bear_agent",),
        ),
        (
            STRATEGY_SIDEWAYS_HYPOTHESIS_PROJECTOR_NAME,
            STRATEGY_SIDEWAYS_HYPOTHESIS_OUTPUT_CONTRACT,
            ("sideways_agent",),
        ),
    )
    registrations = [
        WorkflowOutputProjectorRegistration(
            projector_name=projector_name,
            output_contract=output_contract,
            output_schema_version=WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
            projector=StrategyHypothesisWorkflowOutputProjector(
                strategy_persistence_service=strategy_persistence_service,
                projector_name=projector_name,
            ),
            supported_node_names=supported_node_names,
        )
        for projector_name, output_contract, supported_node_names in hypothesis_specs
    ]
    synthesis_projector = StrategySynthesisWorkflowOutputProjector(
        strategy_persistence_service=strategy_persistence_service,
        recommendation_persistence_service=recommendation_persistence_service,
    )
    registrations.append(
        WorkflowOutputProjectorRegistration(
            projector_name=STRATEGY_SYNTHESIS_PROJECTOR_NAME,
            output_contract=STRATEGY_SYNTHESIS_OUTPUT_CONTRACT,
            output_schema_version=WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
            projector=synthesis_projector,
            supported_node_names=("strategy_synthesis_agent",),
            persists_quality_status=True,
        )
    )
    return tuple(registrations)


def _hypothesis_from_node_output(
    node_output: CompletedNodeOutputRecord,
) -> StrategyHypothesis | None:
    payload = _mapping(_mapping(node_output.outputs).get("strategy_hypothesis"))
    if not payload:
        return None
    return StrategyHypothesis.from_dict(dict(payload))


def _hypothesis_records_from_bundle(
    request: WorkflowOutputProjectorRequest,
    *,
    symbol: str,
) -> tuple[StrategyHypothesisRecord, ...]:
    if request.bundle is None:
        return ()
    records: list[StrategyHypothesisRecord] = []
    for node_output in request.bundle.node_outputs:
        if node_output.output_contract not in _HYPOTHESIS_CONTRACTS:
            continue
        if node_output.success is False:
            continue
        hypothesis = _hypothesis_from_node_output(node_output)
        if hypothesis is None:
            continue
        records.append(
            _hypothesis_record(
                request=request,
                node_output=node_output,
                hypothesis=hypothesis,
                symbol=symbol,
            )
        )
    return tuple(records)


def _hypothesis_record(
    *,
    request: WorkflowOutputProjectorRequest,
    node_output: CompletedNodeOutputRecord,
    hypothesis: StrategyHypothesis,
    symbol: str,
) -> StrategyHypothesisRecord:
    lineage = _lineage_for_node(request, node_output)
    perspective = hypothesis.perspective.value
    created_at = _timestamp(request, node_output)
    return StrategyHypothesisRecord(
        hypothesis_id=new_strategy_hypothesis_id(
            symbol=symbol,
            perspective=perspective,
            evidence_fingerprint=hypothesis.evidence_fingerprint,
            execution_id=request.run.execution_id,
        ),
        symbol=symbol,
        perspective=perspective,
        thesis=hypothesis.thesis,
        directional_bias=hypothesis.directional_bias,
        hypothesis_strength=hypothesis.hypothesis_strength,
        confidence=hypothesis.confidence,
        evidence_fingerprint=hypothesis.evidence_fingerprint,
        created_at=created_at,
        lineage=lineage,
        horizon=_optional_text(request.run.inputs_json.get("horizon")),
        as_of=request.run.completed_at,
        invalidated=hypothesis.invalidated,
        supporting_evidence=tuple(
            cast(JsonObject, item.to_dict()) for item in hypothesis.supporting_evidence
        ),
        contradicting_evidence=tuple(
            cast(JsonObject, item.to_dict())
            for item in hypothesis.contradicting_evidence
        ),
        key_assumptions=tuple(
            cast(JsonObject, item.to_dict()) for item in hypothesis.key_assumptions
        ),
        invalidation_conditions=tuple(
            cast(JsonObject, item.to_dict())
            for item in hypothesis.invalidation_conditions
        ),
        risks=hypothesis.risks,
        recommendations=hypothesis.recommendations,
        data_quality_flags=hypothesis.data_quality_flags,
        metadata={
            "source_fingerprint": request.source_fingerprint,
            "node_output_id": node_output.node_output_id,
            "output_contract": node_output.output_contract,
            "output_schema_version": node_output.output_schema_version,
        },
    )


def _decision_record(
    *,
    request: WorkflowOutputProjectorRequest,
    decision: StrategySynthesisDecision,
    symbol: str,
    evidence_fingerprint: str,
) -> StrategySynthesisDecisionRecord:
    selected = (
        None
        if decision.selected_perspective is None
        else decision.selected_perspective.value
    )
    decision_key = selected or decision.selection_status.value
    return StrategySynthesisDecisionRecord(
        decision_id=new_strategy_decision_id(
            symbol=symbol,
            evidence_fingerprint=evidence_fingerprint,
            execution_id=request.run.execution_id,
            decision_key=decision_key,
        ),
        symbol=symbol,
        selected_perspective=selected,
        selection_status=decision.selection_status.value,
        directional_score=decision.directional_score,
        confidence=decision.confidence,
        regime=decision.regime,
        uncertainty=decision.uncertainty,
        thesis=decision.thesis,
        evidence_fingerprint=evidence_fingerprint,
        created_at=_timestamp(request, request.node_output),
        lineage=request.lineage,
        horizon=_optional_text(request.run.inputs_json.get("horizon")),
        as_of=request.run.completed_at,
        signals=decision.signals,
        risks=decision.risks,
        recommendations=decision.recommendations,
        degraded_reasons=tuple(reason.value for reason in decision.degraded_reasons),
        metadata={
            "source_fingerprint": request.source_fingerprint,
            "node_output_id": request.node_output.node_output_id,
            "output_contract": request.node_output.output_contract,
            "output_schema_version": request.node_output.output_schema_version,
        },
    )


def _evaluation_records(
    *,
    request: WorkflowOutputProjectorRequest,
    decision: StrategySynthesisDecision,
    decision_record: StrategySynthesisDecisionRecord,
    hypotheses: tuple[StrategyHypothesisRecord, ...],
) -> tuple[StrategyHypothesisEvaluationRecord, ...]:
    hypotheses_by_perspective = {record.perspective: record for record in hypotheses}
    records: list[StrategyHypothesisEvaluationRecord] = []
    for evaluation in decision.evaluations:
        perspective = evaluation.perspective.value
        hypothesis = hypotheses_by_perspective.get(perspective)
        records.append(
            StrategyHypothesisEvaluationRecord(
                evaluation_id=new_strategy_evaluation_id(
                    decision_id=decision_record.decision_id,
                    perspective=perspective,
                ),
                decision_id=decision_record.decision_id,
                hypothesis_id=None if hypothesis is None else hypothesis.hypothesis_id,
                symbol=decision_record.symbol,
                perspective=perspective,
                perspective_weight=evaluation.perspective_weight,
                contradiction_burden=evaluation.contradiction_burden,
                assumption_support=evaluation.assumption_support,
                invalidated=evaluation.invalidated,
                candidate_score=evaluation.candidate_score,
                posterior_weight=evaluation.posterior_weight,
                rank=evaluation.rank,
                selection_status=evaluation.selection_status.value,
                evidence_fingerprint=(
                    decision_record.evidence_fingerprint
                    if hypothesis is None
                    else hypothesis.evidence_fingerprint
                ),
                created_at=decision_record.created_at,
                lineage=decision_record.lineage,
                horizon=decision_record.horizon,
                as_of=decision_record.as_of,
                degraded_reasons=tuple(
                    reason.value for reason in evaluation.degraded_reasons
                ),
                metadata={
                    "strategy_decision_id": decision_record.decision_id,
                    "source_fingerprint": request.source_fingerprint,
                },
            )
        )
    return tuple(records)


def _decision_evidence_fingerprint(
    *,
    decision: StrategySynthesisDecision,
    hypotheses: tuple[StrategyHypothesisRecord, ...],
    request: WorkflowOutputProjectorRequest,
) -> str:
    if decision.selected_perspective is not None:
        selected = decision.selected_perspective.value
        for hypothesis in hypotheses:
            if hypothesis.perspective == selected:
                return hypothesis.evidence_fingerprint
    if hypotheses:
        return hypotheses[0].evidence_fingerprint
    return request.source_fingerprint


def _strategy_recommendation_bundle(
    *,
    request: WorkflowOutputProjectorRequest,
    decision: StrategySynthesisDecision,
    decision_record: StrategySynthesisDecisionRecord,
) -> RecommendationPersistenceBundle | None:
    if not decision.recommendations:
        return None
    recommendation_id = new_recommendation_id(
        symbol=decision_record.symbol,
        execution_id=request.run.execution_id,
        recommendation_key="strategy_synthesis",
    )
    recommendation = RecommendationRecord(
        recommendation_id=recommendation_id,
        symbol=decision_record.symbol,
        bias=decision.regime,
        confidence=decision.confidence,
        created_at=decision_record.created_at,
        lineage=decision_record.lineage,
        setup_quality=1.0 - decision.uncertainty,
        risk_score=decision.uncertainty,
        risk_level=_risk_level(decision.uncertainty),
        time_horizon=decision_record.horizon,
        status="strategy_recommendation",
        metadata={
            "strategy_decision_id": decision_record.decision_id,
            "selected_perspective": decision_record.selected_perspective,
            "selection_status": decision_record.selection_status,
            "evidence_fingerprint": decision_record.evidence_fingerprint,
        },
    )
    rationale = RecommendationRationaleRecord(
        rationale_id=new_recommendation_child_id(
            recommendation_id=recommendation_id,
            child_type="rationale",
            child_key="strategy_synthesis",
        ),
        recommendation_id=recommendation_id,
        rationale_type="strategy_synthesis",
        rationale_text=decision.thesis,
        created_at=decision_record.created_at,
        lineage=decision_record.lineage,
        confidence=decision.confidence,
        metadata={"recommendations": list(decision.recommendations)},
    )
    return RecommendationPersistenceBundle(
        recommendation=recommendation, rationales=(rationale,)
    )


def _risk_level(uncertainty: float) -> str:
    if uncertainty >= 0.7:
        return "high"
    if uncertainty >= 0.4:
        return "medium"
    return "low"


def _symbol_from_request(
    request: WorkflowOutputProjectorRequest,
    *,
    outputs: Mapping[str, object] | None = None,
    features: Mapping[str, object] | None = None,
) -> str | None:
    active_outputs = outputs or _mapping(request.node_output.outputs)
    active_features = features or _mapping(active_outputs.get("features"))
    for value in (
        active_outputs.get("symbol"),
        active_features.get("symbol"),
        request.run.inputs_json.get("symbol"),
        request.node_output.metadata.get("symbol"),
    ):
        text = _optional_text(value)
        if text is not None:
            return text.upper()
    return None


def _lineage_for_node(
    request: WorkflowOutputProjectorRequest,
    node_output: CompletedNodeOutputRecord,
):
    if node_output.node_name == request.node_output.node_name:
        return request.lineage
    return type(request.lineage)(
        workflow_name=request.run.workflow_name,
        execution_id=request.run.execution_id,
        runtime_id=request.run.runtime_id,
        node_name=node_output.node_name,
    )


def _timestamp(
    request: WorkflowOutputProjectorRequest,
    node_output: CompletedNodeOutputRecord,
) -> datetime:
    return (
        node_output.completed_at
        or node_output.started_at
        or request.run.completed_at
        or request.run.started_at
        or request.requested_at
        or datetime.now(UTC)
    )


def _mapping(value: object) -> Mapping[str, object]:
    if isinstance(value, Mapping):
        return {str(key): item for key, item in value.items()}
    return {}


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _outcome(
    *,
    request: WorkflowOutputProjectorRequest,
    projector_name: str,
    status: WorkflowOutputProjectionStatus,
    records_written: int,
    message: str,
) -> WorkflowOutputProjectionOutcome:
    return WorkflowOutputProjectionOutcome(
        status=status,
        projector_name=projector_name,
        node_name=request.node_output.node_name,
        output_contract=request.node_output.output_contract or "unknown",
        output_schema_version=request.node_output.output_schema_version or 1,
        source_fingerprint=request.source_fingerprint,
        records_written=records_written,
        message=message,
    )


def _skipped(
    request: WorkflowOutputProjectorRequest,
    projector_name: str,
    message: str,
) -> WorkflowOutputProjectionOutcome:
    return _outcome(
        request=request,
        projector_name=projector_name,
        status=WorkflowOutputProjectionStatus.SKIPPED,
        records_written=0,
        message=message,
    )


def _failed(
    request: WorkflowOutputProjectorRequest,
    projector_name: str,
    error: str,
) -> WorkflowOutputProjectionOutcome:
    return WorkflowOutputProjectionOutcome(
        status=WorkflowOutputProjectionStatus.FAILED,
        projector_name=projector_name,
        node_name=request.node_output.node_name,
        output_contract=request.node_output.output_contract or "unknown",
        output_schema_version=request.node_output.output_schema_version or 1,
        source_fingerprint=request.source_fingerprint,
        error_type="PersistenceError",
        error_message=error,
        message="Strategy projection failed.",
    )
