from __future__ import annotations

import pytest

from domain.authority import SourceOfTruthCategory, classify_risk_authority
from domain.decision_evidence import (
    EvidenceRetentionRequirement,
    ReconstructionReference,
    ReconstructionReferenceKind,
    SupportingEvidenceSnapshot,
)
from intelligence.strategy.hypothesis import StrategyPerspective
from intelligence.strategy.hypothesis.evidence import (
    StrategyAssumption,
    StrategyEvidenceItem,
    StrategyInvalidationCondition,
    StrategyInvalidationOperator,
)
from intelligence.strategy.hypothesis.hypothesis import StrategyHypothesis
from intelligence.strategy.synthesis import (
    StrategyHypothesisEvaluation,
    StrategySynthesisDecision,
    StrategySynthesisEvidencePacketAssemblyError,
    StrategySynthesisSelectionStatus,
    assemble_strategy_synthesis_decision_evidence_packet,
)
from tests.helpers.risk_authority_examples import strategy_synthesis_authority_input


def test_strategy_synthesis_packet_exposes_hypotheses_and_evidence() -> None:
    decision = _decision(evidence_packet_ids=("strategy-packet-1",))

    packet = assemble_strategy_synthesis_decision_evidence_packet(
        decision=decision,
        hypotheses=_hypotheses(),
        packet_id="strategy-packet-1",
        output_id="strategy-synthesis-output-1",
        authority=classify_risk_authority(strategy_synthesis_authority_input()),
        reconstruction_references=(_workflow_reference(),),
        retention=_retention_requirement(),
        support_snapshots=_support_snapshots(_hypotheses()),
    )

    assert packet.packet_id == "strategy-packet-1"
    assert packet.output_id == "strategy-synthesis-output-1"
    assert packet.risk_tier.value == "vigilant"
    assert decision.to_dict()["evidence_packet_ids"] == ["strategy-packet-1"]
    assert StrategySynthesisDecision.from_dict(decision.to_dict()) == decision

    claim_ids = {claim.claim_id for claim in packet.claims}
    assert "strategy_synthesis_decision" in claim_ids
    assert "strategy_hypothesis_evaluation:bull" in claim_ids
    assert "strategy_hypothesis_evaluation:bear" in claim_ids
    assert "strategy_hypothesis_evaluation:sideways" in claim_ids

    evidence_ids = {evidence.evidence_id for evidence in packet.evidence}
    assert {
        "bull-momentum",
        "bull-spread-risk",
        "bear-credit-stress",
        "sideways-range",
    }.issubset(evidence_ids)
    assert all(evidence.support_snapshot is not None for evidence in packet.evidence)
    assert {
        evidence.support_snapshot.snapshot_id
        for evidence in packet.evidence
        if evidence.support_snapshot is not None
    } == {f"{evidence_id}:support-snapshot" for evidence_id in evidence_ids}

    constraint_ids = {constraint.constraint_id for constraint in packet.constraints}
    assert "bull:assumption:bull-liquidity" in constraint_ids
    assert "bear:assumption:bear-credit" in constraint_ids
    assert "sideways:assumption:sideways-range" in constraint_ids

    limitation_ids = {limitation.limitation_id for limitation in packet.limitations}
    assert "bear:invalidation:bear-stress-invalidated" in limitation_ids

    uncertainty = packet.uncertainties[0]
    assert uncertainty.uncertainty_id == "strategy_synthesis_uncertainty"
    assert "0.1875" in uncertainty.summary
    assert set(uncertainty.evidence_ids) == evidence_ids

    selected_claim = next(
        claim
        for claim in packet.claims
        if claim.claim_id == "strategy_hypothesis_evaluation:bull"
    )
    assert selected_claim.evidence.supporting_evidence_ids == ("bull-momentum",)
    assert selected_claim.evidence.conflicting_evidence_ids == ("bull-spread-risk",)
    assert selected_claim.evidence.constraint_ids == ("bull:assumption:bull-liquidity",)
    assert selected_claim.evidence.uncertainty_ids == (
        "strategy_synthesis_uncertainty",
    )


@pytest.mark.parametrize(
    ("evidence_packet_ids", "expected_message"),
    [
        ((), "requires canonical evidence packet binding"),
        (("packet-substituted",), "does not match canonical packet"),
        (
            ("strategy-packet-1", "packet-substituted"),
            "contains substituted evidence packet ids",
        ),
    ],
)
def test_strategy_synthesis_packet_fails_for_missing_or_substituted_binding(
    evidence_packet_ids: tuple[str, ...],
    expected_message: str,
) -> None:
    with pytest.raises(
        StrategySynthesisEvidencePacketAssemblyError,
        match=expected_message,
    ):
        assemble_strategy_synthesis_decision_evidence_packet(
            decision=_decision(evidence_packet_ids=evidence_packet_ids),
            hypotheses=_hypotheses(),
            packet_id="strategy-packet-1",
            output_id="strategy-synthesis-output-1",
            authority=classify_risk_authority(strategy_synthesis_authority_input()),
            reconstruction_references=(_workflow_reference(),),
            retention=_retention_requirement(),
            support_snapshots=_support_snapshots(_hypotheses()),
        )


@pytest.mark.parametrize(
    ("hypotheses", "expected_message"),
    [
        (
            lambda: _hypotheses()[:2],
            "missing hypothesis for perspective 'sideways'",
        ),
        (
            lambda: (
                _hypothesis(
                    StrategyPerspective.BULL,
                    supporting_evidence=(
                        _evidence(
                            "bull-momentum",
                            supports=(StrategyPerspective.BULL,),
                        ),
                    ),
                    assumptions=(),
                ),
                *_hypotheses()[1:],
            ),
            (
                "strategy synthesis constraint for perspective 'bull' requires "
                "at least one assumption"
            ),
        ),
        (
            lambda: (
                _hypothesis(
                    StrategyPerspective.BULL,
                    supporting_evidence=(
                        _evidence(
                            "bull-momentum",
                            supports=(StrategyPerspective.BULL,),
                        ),
                    ),
                    assumptions=(
                        StrategyAssumption(
                            assumption_id="bull-missing-evidence",
                            perspective=StrategyPerspective.BULL,
                            description="Liquidity remains durable.",
                            confidence=0.70,
                            evidence_ids=("missing-evidence",),
                        ),
                    ),
                ),
                *_hypotheses()[1:],
            ),
            (
                "assumption 'bull-missing-evidence' references unknown "
                "evidence 'missing-evidence'"
            ),
        ),
        (
            lambda: (
                _hypothesis(
                    StrategyPerspective.BULL,
                    supporting_evidence=(
                        _evidence(
                            "bull-momentum",
                            supports=(StrategyPerspective.BULL,),
                        ),
                    ),
                    assumptions=(
                        StrategyAssumption(
                            assumption_id="bull-liquidity",
                            perspective=StrategyPerspective.BULL,
                            description="Liquidity remains durable.",
                            confidence=0.70,
                            evidence_ids=("bull-momentum",),
                        ),
                    ),
                    invalidations=(
                        StrategyInvalidationCondition(
                            condition_id="bull-invalidated-without-evidence",
                            perspective=StrategyPerspective.BULL,
                            description="Credit spread stress invalidates bull case.",
                            observed_value=0.90,
                            operator=StrategyInvalidationOperator.GREATER_THAN_OR_EQUAL,
                            threshold=0.80,
                        ),
                    ),
                ),
                *_hypotheses()[1:],
            ),
            (
                "invalidation condition 'bull-invalidated-without-evidence' "
                "lacks evidence_id"
            ),
        ),
    ],
)
def test_strategy_synthesis_packet_assembly_fails_when_references_are_missing(
    hypotheses: object,
    expected_message: str,
) -> None:
    active_hypotheses = hypotheses()  # type: ignore[operator]
    with pytest.raises(
        StrategySynthesisEvidencePacketAssemblyError,
        match=expected_message,
    ):
        assemble_strategy_synthesis_decision_evidence_packet(
            decision=_decision(evidence_packet_ids=("strategy-packet-1",)),
            hypotheses=active_hypotheses,
            packet_id="strategy-packet-1",
            output_id="strategy-synthesis-output-1",
            authority=classify_risk_authority(strategy_synthesis_authority_input()),
            reconstruction_references=(_workflow_reference(),),
            retention=_retention_requirement(),
            support_snapshots=_support_snapshots(active_hypotheses),
        )


def test_strategy_synthesis_packet_assembly_fails_when_snapshot_missing() -> None:
    with pytest.raises(
        StrategySynthesisEvidencePacketAssemblyError,
        match="lacks retained support snapshot",
    ):
        assemble_strategy_synthesis_decision_evidence_packet(
            decision=_decision(evidence_packet_ids=("strategy-packet-1",)),
            hypotheses=_hypotheses(),
            packet_id="strategy-packet-1",
            output_id="strategy-synthesis-output-1",
            authority=classify_risk_authority(strategy_synthesis_authority_input()),
            reconstruction_references=(_workflow_reference(),),
            retention=_retention_requirement(),
            support_snapshots={},
        )


def _decision(
    *,
    evidence_packet_ids: tuple[str, ...] = (),
) -> StrategySynthesisDecision:
    return StrategySynthesisDecision.from_evaluations(
        evaluations=(
            _evaluation(StrategyPerspective.BULL, score=0.72),
            _evaluation(StrategyPerspective.BEAR, score=0.18, invalidated=True),
            _evaluation(StrategyPerspective.SIDEWAYS, score=0.10),
        ),
        directional_score=0.43,
        confidence=0.8125,
        regime="risk_on",
        uncertainty=0.1875,
        thesis="Bull case has the strongest adjusted candidate score.",
        signals=("bull_selected",),
        risks=("credit_spreads_can_invalidate",),
        recommendations=("favor_quality_long_exposure",),
        evidence_packet_ids=evidence_packet_ids,
    )


def _evaluation(
    perspective: StrategyPerspective,
    *,
    score: float,
    invalidated: bool = False,
) -> StrategyHypothesisEvaluation:
    return StrategyHypothesisEvaluation(
        perspective=perspective,
        perspective_weight=score,
        contradiction_burden=0.10,
        assumption_support=0.85,
        invalidated=invalidated,
        candidate_score=score,
        synthesis_weight=0.0,
        rank=0,
        selection_status=StrategySynthesisSelectionStatus.CANDIDATE,
    )


def _hypotheses() -> tuple[StrategyHypothesis, ...]:
    return (
        _hypothesis(
            StrategyPerspective.BULL,
            supporting_evidence=(
                _evidence("bull-momentum", supports=(StrategyPerspective.BULL,)),
            ),
            contradicting_evidence=(
                _evidence(
                    "bull-spread-risk",
                    contradicts=(StrategyPerspective.BULL,),
                ),
            ),
            assumptions=(
                StrategyAssumption(
                    assumption_id="bull-liquidity",
                    perspective=StrategyPerspective.BULL,
                    description="Liquidity remains durable.",
                    confidence=0.70,
                    evidence_ids=("bull-momentum",),
                ),
            ),
        ),
        _hypothesis(
            StrategyPerspective.BEAR,
            supporting_evidence=(
                _evidence(
                    "bear-credit-stress",
                    supports=(StrategyPerspective.BEAR,),
                ),
            ),
            assumptions=(
                StrategyAssumption(
                    assumption_id="bear-credit",
                    perspective=StrategyPerspective.BEAR,
                    description="Credit stress remains elevated.",
                    confidence=0.65,
                    evidence_ids=("bear-credit-stress",),
                ),
            ),
            invalidations=(
                StrategyInvalidationCondition(
                    condition_id="bear-stress-invalidated",
                    perspective=StrategyPerspective.BEAR,
                    description="Credit stress eased enough to invalidate bear case.",
                    observed_value=0.10,
                    operator=StrategyInvalidationOperator.LESS_THAN_OR_EQUAL,
                    threshold=0.20,
                    evidence_id="bear-credit-stress",
                ),
            ),
        ),
        _hypothesis(
            StrategyPerspective.SIDEWAYS,
            supporting_evidence=(
                _evidence(
                    "sideways-range",
                    supports=(StrategyPerspective.SIDEWAYS,),
                ),
            ),
            assumptions=(
                StrategyAssumption(
                    assumption_id="sideways-range",
                    perspective=StrategyPerspective.SIDEWAYS,
                    description="Realized volatility remains range-bound.",
                    confidence=0.60,
                    evidence_ids=("sideways-range",),
                ),
            ),
        ),
    )


def _hypothesis(
    perspective: StrategyPerspective,
    *,
    supporting_evidence: tuple[StrategyEvidenceItem, ...],
    contradicting_evidence: tuple[StrategyEvidenceItem, ...] = (),
    assumptions: tuple[StrategyAssumption, ...] = (),
    invalidations: tuple[StrategyInvalidationCondition, ...] = (),
) -> StrategyHypothesis:
    return StrategyHypothesis(
        perspective=perspective,
        thesis=f"{perspective.value} thesis.",
        directional_bias=0.50 if perspective is StrategyPerspective.BULL else -0.25,
        hypothesis_strength=0.70,
        confidence=0.75,
        supporting_evidence=supporting_evidence,
        contradicting_evidence=contradicting_evidence,
        key_assumptions=assumptions,
        invalidation_conditions=invalidations,
        risks=("risk",),
        recommendations=("recommendation",),
        data_quality_flags=(),
        evidence_fingerprint=f"fingerprint-{perspective.value}",
    )


def _evidence(
    evidence_id: str,
    *,
    supports: tuple[StrategyPerspective, ...] = (),
    contradicts: tuple[StrategyPerspective, ...] = (),
) -> StrategyEvidenceItem:
    return StrategyEvidenceItem(
        evidence_id=evidence_id,
        source="strategy-runtime",
        name=evidence_id.replace("-", " "),
        observed_value=0.5,
        strength=0.80,
        reliability=0.90,
        supports=supports,
        contradicts=contradicts,
        explanation=f"{evidence_id} explanation.",
    )


def _workflow_reference() -> ReconstructionReference:
    return ReconstructionReference(
        reference_id="strategy-synthesis-node",
        kind=ReconstructionReferenceKind.WORKFLOW_NODE_OUTPUT,
        record_id="run-1:node:strategy_synthesis",
        source_of_truth=SourceOfTruthCategory.RUNTIME_EVIDENCE,
    )


def _support_snapshots(
    hypotheses: tuple[StrategyHypothesis, ...],
) -> dict[str, SupportingEvidenceSnapshot]:
    snapshots: dict[str, SupportingEvidenceSnapshot] = {}
    for hypothesis in hypotheses:
        for evidence in (
            *hypothesis.supporting_evidence,
            *hypothesis.contradicting_evidence,
        ):
            snapshots[evidence.evidence_id] = SupportingEvidenceSnapshot(
                snapshot_id=f"{evidence.evidence_id}:support-snapshot",
                summary=f"Retained {evidence.evidence_id} support.",
                redacted_content=f"redacted strategy support {evidence.evidence_id}",
                source_label="workflow_node_output:test-node",
            )
    return snapshots


def _retention_requirement() -> EvidenceRetentionRequirement:
    return EvidenceRetentionRequirement(
        retain_until="2031-07-25T00:00:00Z",
        policy_id="vigilant-strategy-synthesis-5y",
    )
