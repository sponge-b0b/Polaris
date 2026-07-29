from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final, cast

from application.decision_evidence import (
    DecisionEvidencePacketPersistenceService,
    calculate_completed_workflow_node_evidence_digest,
)
from application.persistence.lineage import LineagePersistenceService
from application.persistence.recommendations import RecommendationPersistenceService
from application.persistence.strategy import StrategyPersistenceService
from application.projections.workflow_outputs.projection_models import (
    WorkflowOutputProjectionOutcome,
    WorkflowOutputProjectionStatus,
    WorkflowOutputProjectorRequest,
)
from application.projections.workflow_outputs.projection_registry import (
    WorkflowOutputProjectorRegistration,
)
from core.security.sensitive_data import sanitize_sensitive_value
from core.storage.persistence.completed_run_archive import CompletedNodeOutputRecord
from core.storage.persistence.lineage import (
    JsonObject,
    PersistenceLineage,
    PersistenceLineageLinkRecord,
    PersistenceRecordIdentity,
    new_persistence_lineage_link_id,
)
from core.storage.persistence.recommendations import (
    RecommendationPersistenceBundle,
    RecommendationRationaleRecord,
    RecommendationRecord,
    new_recommendation_child_id,
    new_recommendation_id,
)
from core.storage.persistence.strategy import (
    StrategyHypothesisEvaluationRecord,
    StrategyHypothesisRecord,
    StrategyPersistenceBundle,
    StrategySynthesisDecisionRecord,
    new_strategy_decision_id,
    new_strategy_evaluation_id,
    new_strategy_hypothesis_id,
)
from domain.authority import (
    RiskAuthorityContract,
    SourceOfTruthCategory,
    authority_contract_metadata,
    model_authority_claims_from_payloads,
    strategy_recommendation_rationale_authority,
    strategy_recommendation_record_authority,
    strategy_synthesis_decision_authority,
)
from domain.decision_evidence import (
    EvidenceRetentionRequirement,
    ReconstructionReference,
    ReconstructionReferenceKind,
    SupportingEvidenceSnapshot,
)
from domain.workflow_outputs import (
    STRATEGY_BEAR_HYPOTHESIS_OUTPUT_CONTRACT,
    STRATEGY_BULL_HYPOTHESIS_OUTPUT_CONTRACT,
    STRATEGY_SIDEWAYS_HYPOTHESIS_OUTPUT_CONTRACT,
    STRATEGY_SYNTHESIS_OUTPUT_CONTRACT,
    WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
)
from intelligence.strategy.hypothesis.evidence import StrategyEvidenceItem
from intelligence.strategy.hypothesis.hypothesis import StrategyHypothesis
from intelligence.strategy.synthesis.contracts import StrategySynthesisDecision
from intelligence.strategy.synthesis.evidence_packets import (
    StrategySynthesisEvidencePacketAssemblyError,
    assemble_strategy_synthesis_decision_evidence_packet,
)

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
_DECISION_EVIDENCE_PACKET_RECORD_TYPE: Final = "decision_evidence_packet"
_STRATEGY_DECISION_RECORD_TYPE: Final = "strategy_synthesis_decision"
_STRATEGY_RECOMMENDATION_RECORD_TYPE: Final = "recommendation"
_STRATEGY_RECOMMENDATION_RATIONALE_RECORD_TYPE: Final = "recommendation_rationale"
_EVIDENCE_PACKET_RELATIONSHIP_TYPE: Final = "supported_by_decision_evidence_packet"


@dataclass(frozen=True, slots=True)
class _EvidencePacketSourceRecord:
    record: PersistenceRecordIdentity
    created_at: datetime
    lineage: PersistenceLineage


@dataclass(frozen=True, slots=True)
class _StrategyHypothesisProjectionEvidence:
    hypothesis: StrategyHypothesis
    node_output: CompletedNodeOutputRecord
    content_digest: str


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
        decision_evidence_packet_persistence_service: (
            DecisionEvidencePacketPersistenceService
        ),
        lineage_persistence_service: LineagePersistenceService,
    ) -> None:
        self._strategy_persistence_service = strategy_persistence_service
        self._recommendation_persistence_service = recommendation_persistence_service
        self._decision_evidence_packet_persistence_service = (
            decision_evidence_packet_persistence_service
        )
        self._lineage_persistence_service = lineage_persistence_service

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

        hypothesis_evidence = _strategy_hypothesis_projection_evidence(request)
        hypotheses = _hypothesis_records_from_projection_evidence(
            request,
            symbol=symbol,
            hypothesis_evidence=hypothesis_evidence,
        )
        evidence_fingerprint = _decision_evidence_fingerprint(
            decision=decision,
            hypotheses=hypotheses,
            request=request,
        )
        try:
            evidence_packet = assemble_strategy_synthesis_decision_evidence_packet(
                decision=decision,
                hypotheses=tuple(item.hypothesis for item in hypothesis_evidence),
                packet_id=_canonical_strategy_packet_id(decision),
                output_id=request.node_output.node_output_id,
                authority=_strategy_synthesis_authority(
                    request=request,
                    outputs=outputs,
                    features=features,
                ),
                reconstruction_references=_strategy_reconstruction_references(
                    request=request,
                    hypothesis_evidence=hypothesis_evidence,
                ),
                retention=_strategy_evidence_retention_requirement(request),
                support_snapshots=_strategy_support_snapshots(hypothesis_evidence),
            )
        except StrategySynthesisEvidencePacketAssemblyError as exc:
            return _failed(
                request,
                self.projector_name,
                f"Strategy decision evidence packet assembly failed: {exc}",
            )

        packet_result = (
            await self._decision_evidence_packet_persistence_service.persist_packet(
                evidence_packet
            )
        )
        if not packet_result.success:
            error = "; ".join(packet_result.errors) or (
                "Strategy decision evidence packet persistence failed."
            )
            return _failed(request, self.projector_name, error)
        evidence_packet_ids = (evidence_packet.packet_id,)

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

        records_written = (
            packet_result.records_persisted + strategy_result.records_persisted
        )
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

        lineage_links = _evidence_packet_lineage_links(
            request=request,
            evidence_packet_ids=evidence_packet_ids,
            decision_record=decision_record,
            recommendation_bundle=recommendation_bundle,
        )
        lineage_records_written, lineage_error = await _persist_lineage_links(
            self._lineage_persistence_service,
            links=lineage_links,
        )
        if lineage_error is not None:
            return _failed(
                request,
                self.projector_name,
                f"Evidence packet lineage persistence failed: {lineage_error}",
            )
        records_written += lineage_records_written

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
    decision_evidence_packet_persistence_service: (
        DecisionEvidencePacketPersistenceService
    ),
    lineage_persistence_service: LineagePersistenceService,
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
        decision_evidence_packet_persistence_service=(
            decision_evidence_packet_persistence_service
        ),
        lineage_persistence_service=lineage_persistence_service,
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
    return _hypothesis_records_from_projection_evidence(
        request,
        symbol=symbol,
        hypothesis_evidence=_strategy_hypothesis_projection_evidence(request),
    )


def _strategy_hypothesis_projection_evidence(
    request: WorkflowOutputProjectorRequest,
) -> tuple[_StrategyHypothesisProjectionEvidence, ...]:
    if request.bundle is None:
        return ()
    evidence: list[_StrategyHypothesisProjectionEvidence] = []
    for node_output in request.bundle.node_outputs:
        if node_output.output_contract not in _HYPOTHESIS_CONTRACTS:
            continue
        if node_output.success is False:
            continue
        hypothesis = _hypothesis_from_node_output(node_output)
        if hypothesis is None:
            continue
        evidence.append(
            _StrategyHypothesisProjectionEvidence(
                hypothesis=hypothesis,
                node_output=node_output,
                content_digest=calculate_completed_workflow_node_evidence_digest(
                    run=request.run,
                    node_output=node_output,
                ),
            )
        )
    return tuple(evidence)


def _hypothesis_records_from_projection_evidence(
    request: WorkflowOutputProjectorRequest,
    *,
    symbol: str,
    hypothesis_evidence: tuple[_StrategyHypothesisProjectionEvidence, ...],
) -> tuple[StrategyHypothesisRecord, ...]:
    records: list[StrategyHypothesisRecord] = []
    for item in hypothesis_evidence:
        records.append(
            _hypothesis_record(
                request=request,
                node_output=item.node_output,
                hypothesis=item.hypothesis,
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
            **authority_contract_metadata(
                strategy_synthesis_decision_authority(
                    model_authority_claims_from_payloads(
                        _mapping(request.node_output.outputs),
                        _mapping(_mapping(request.node_output.outputs).get("features")),
                    )
                )
            ),
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
                synthesis_weight=evaluation.synthesis_weight,
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


def _canonical_strategy_packet_id(decision: StrategySynthesisDecision) -> str:
    if not decision.evidence_packet_ids:
        raise StrategySynthesisEvidencePacketAssemblyError(
            "strategy synthesis decision requires canonical evidence packet binding."
        )
    return decision.evidence_packet_ids[0]


def _strategy_synthesis_authority(
    *,
    request: WorkflowOutputProjectorRequest,
    outputs: Mapping[str, object],
    features: Mapping[str, object],
) -> RiskAuthorityContract:
    return request.authority_contract or strategy_synthesis_decision_authority(
        model_authority_claims_from_payloads(outputs, features)
    )


def _strategy_reconstruction_references(
    *,
    request: WorkflowOutputProjectorRequest,
    hypothesis_evidence: tuple[_StrategyHypothesisProjectionEvidence, ...],
) -> tuple[ReconstructionReference, ...]:
    if request.bundle is None:
        raise StrategySynthesisEvidencePacketAssemblyError(
            "strategy synthesis packet assembly requires completed run bundle for "
            "retained support snapshots."
        )

    references: dict[str, ReconstructionReference] = {}
    run_reference = ReconstructionReference(
        reference_id="strategy_synthesis:completed-run",
        kind=ReconstructionReferenceKind.COMPLETED_WORKFLOW_RUN,
        record_id=f"{request.run.workflow_name}:{request.run.execution_id}",
        source_of_truth=SourceOfTruthCategory.RUNTIME_EVIDENCE,
        snapshot_id=request.run.run_id,
    )
    references[run_reference.reference_id] = run_reference

    node_outputs = (
        request.node_output,
        *(item.node_output for item in hypothesis_evidence),
    )
    for node_output in node_outputs:
        reference = _workflow_node_reconstruction_reference(
            request=request,
            node_output=node_output,
        )
        references[reference.reference_id] = reference
    return tuple(references.values())


def _workflow_node_reconstruction_reference(
    *,
    request: WorkflowOutputProjectorRequest,
    node_output: CompletedNodeOutputRecord,
) -> ReconstructionReference:
    return ReconstructionReference(
        reference_id=f"strategy_synthesis:node-output:{node_output.node_output_id}",
        kind=ReconstructionReferenceKind.WORKFLOW_NODE_OUTPUT,
        record_id=node_output.node_output_id,
        source_of_truth=SourceOfTruthCategory.RUNTIME_EVIDENCE,
        snapshot_id=(
            f"{node_output.workflow_name}:{node_output.execution_id}:"
            f"{node_output.node_name}"
        ),
        content_digest=calculate_completed_workflow_node_evidence_digest(
            run=request.run,
            node_output=node_output,
        ),
    )


def _strategy_support_snapshots(
    hypothesis_evidence: tuple[_StrategyHypothesisProjectionEvidence, ...],
) -> Mapping[str, SupportingEvidenceSnapshot]:
    snapshots: dict[str, SupportingEvidenceSnapshot] = {}
    for item in hypothesis_evidence:
        for evidence in (
            *item.hypothesis.supporting_evidence,
            *item.hypothesis.contradicting_evidence,
        ):
            snapshots.setdefault(
                evidence.evidence_id,
                _strategy_support_snapshot(
                    evidence=evidence,
                    projection_evidence=item,
                ),
            )
    return snapshots


def _strategy_support_snapshot(
    *,
    evidence: StrategyEvidenceItem,
    projection_evidence: _StrategyHypothesisProjectionEvidence,
) -> SupportingEvidenceSnapshot:
    content = {
        "hypothesis_perspective": projection_evidence.hypothesis.perspective.value,
        "hypothesis_evidence_fingerprint": (
            projection_evidence.hypothesis.evidence_fingerprint
        ),
        "node_name": projection_evidence.node_output.node_name,
        "node_output_id": projection_evidence.node_output.node_output_id,
        "output_contract": projection_evidence.node_output.output_contract,
        "output_schema_version": projection_evidence.node_output.output_schema_version,
        "content_digest": projection_evidence.content_digest,
        "strategy_evidence": sanitize_sensitive_value(evidence.to_dict()),
    }
    return SupportingEvidenceSnapshot(
        snapshot_id=f"{evidence.evidence_id}:support-snapshot",
        summary=_strategy_support_snapshot_summary(evidence),
        redacted_content=json.dumps(content, sort_keys=True, separators=(",", ":")),
        source_label=f"workflow_node_output:{projection_evidence.node_output.node_output_id}",
    )


def _strategy_support_snapshot_summary(evidence: StrategyEvidenceItem) -> str:
    return f"Strategy support evidence {evidence.evidence_id}: {evidence.name}."


def _strategy_evidence_retention_requirement(
    request: WorkflowOutputProjectorRequest,
) -> EvidenceRetentionRequirement:
    retain_until = _add_years(_timestamp(request, request.node_output), years=5)
    return EvidenceRetentionRequirement(
        retain_until=retain_until.isoformat(),
        policy_id="vigilant-strategy-synthesis-5y",
    )


def _add_years(value: datetime, *, years: int) -> datetime:
    active_value = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    try:
        return active_value.replace(year=active_value.year + years)
    except ValueError:
        return active_value.replace(year=active_value.year + years, day=28)


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
            **authority_contract_metadata(
                strategy_recommendation_record_authority(
                    model_authority_claims_from_payloads(
                        _mapping(request.node_output.outputs),
                        _mapping(_mapping(request.node_output.outputs).get("features")),
                    )
                )
            ),
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
        metadata={
            "recommendations": list(decision.recommendations),
            **authority_contract_metadata(
                strategy_recommendation_rationale_authority(
                    model_authority_claims_from_payloads(
                        _mapping(request.node_output.outputs),
                        _mapping(_mapping(request.node_output.outputs).get("features")),
                    )
                )
            ),
        },
    )
    return RecommendationPersistenceBundle(
        recommendation=recommendation, rationales=(rationale,)
    )


def _evidence_packet_lineage_links(
    *,
    request: WorkflowOutputProjectorRequest,
    evidence_packet_ids: tuple[str, ...],
    decision_record: StrategySynthesisDecisionRecord,
    recommendation_bundle: RecommendationPersistenceBundle | None,
) -> tuple[PersistenceLineageLinkRecord, ...]:
    links: list[PersistenceLineageLinkRecord] = []
    source_records = [
        _evidence_packet_source_record(
            record_type=_STRATEGY_DECISION_RECORD_TYPE,
            record_id=decision_record.decision_id,
            created_at=decision_record.created_at,
            lineage=decision_record.lineage,
        )
    ]
    if recommendation_bundle is not None:
        source_records.append(
            _evidence_packet_source_record(
                record_type=_STRATEGY_RECOMMENDATION_RECORD_TYPE,
                record_id=recommendation_bundle.recommendation.recommendation_id,
                created_at=recommendation_bundle.recommendation.created_at,
                lineage=recommendation_bundle.recommendation.lineage,
            )
        )
        source_records.extend(
            _evidence_packet_source_record(
                record_type=_STRATEGY_RECOMMENDATION_RATIONALE_RECORD_TYPE,
                record_id=rationale.rationale_id,
                created_at=rationale.created_at,
                lineage=rationale.lineage,
            )
            for rationale in recommendation_bundle.rationales
        )

    for packet_id in evidence_packet_ids:
        for source in source_records:
            source_record = source.record
            target_record = PersistenceRecordIdentity(
                record_type=_DECISION_EVIDENCE_PACKET_RECORD_TYPE,
                record_id=packet_id,
            )
            links.append(
                PersistenceLineageLinkRecord(
                    link_id=new_persistence_lineage_link_id(
                        source_record=source_record,
                        target_record=target_record,
                        relationship_type=_EVIDENCE_PACKET_RELATIONSHIP_TYPE,
                    ),
                    source_record=source_record,
                    target_record=target_record,
                    relationship_type=_EVIDENCE_PACKET_RELATIONSHIP_TYPE,
                    created_at=source.created_at,
                    lineage=source.lineage,
                    metadata={
                        "projection_source": "strategy_synthesis",
                        "source_fingerprint": request.source_fingerprint,
                        "node_output_id": request.node_output.node_output_id,
                    },
                )
            )
    return tuple(links)


def _evidence_packet_source_record(
    *,
    record_type: str,
    record_id: str,
    created_at: datetime,
    lineage: PersistenceLineage,
) -> _EvidencePacketSourceRecord:
    return _EvidencePacketSourceRecord(
        record=PersistenceRecordIdentity(
            record_type=record_type,
            record_id=record_id,
        ),
        created_at=created_at,
        lineage=lineage,
    )


async def _persist_lineage_links(
    lineage_persistence_service: LineagePersistenceService,
    *,
    links: tuple[PersistenceLineageLinkRecord, ...],
) -> tuple[int, str | None]:
    records_persisted = 0
    for link in links:
        result = await lineage_persistence_service.persist_lineage_link(link)
        if not result.success:
            return records_persisted, result.error or "unknown lineage error"
        records_persisted += result.records_persisted
    return records_persisted, None


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
