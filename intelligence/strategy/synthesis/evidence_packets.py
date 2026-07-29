from __future__ import annotations

from collections.abc import Iterable, Mapping

from domain.authority import RiskAuthorityContract, SourceOfTruthCategory
from domain.decision_evidence import (
    ClaimEvidenceBinding,
    DecisionEvidencePacket,
    EvidenceConstraint,
    EvidenceLimitation,
    EvidenceReference,
    EvidenceReferenceKind,
    EvidenceRetentionRequirement,
    EvidenceUncertainty,
    MaterialClaim,
    ReconstructionReference,
    SupportingEvidenceSnapshot,
)
from intelligence.strategy.hypothesis.contracts import StrategyPerspective
from intelligence.strategy.hypothesis.evidence import (
    StrategyAssumption,
    StrategyEvidenceItem,
    StrategyInvalidationCondition,
)
from intelligence.strategy.hypothesis.hypothesis import StrategyHypothesis
from intelligence.strategy.synthesis.contracts import StrategySynthesisDecision


class StrategySynthesisEvidencePacketAssemblyError(ValueError):
    """Raised when strategy synthesis cannot assemble a canonical packet."""


def assemble_strategy_synthesis_decision_evidence_packet(
    *,
    decision: StrategySynthesisDecision,
    hypotheses: tuple[StrategyHypothesis, ...],
    packet_id: str,
    output_id: str,
    authority: RiskAuthorityContract,
    reconstruction_references: tuple[ReconstructionReference, ...],
    retention: EvidenceRetentionRequirement,
    support_snapshots: Mapping[str, SupportingEvidenceSnapshot],
) -> DecisionEvidencePacket:
    """Build the canonical evidence packet for a strategy synthesis decision.

    Strategy synthesis remains on the shared decision-evidence packet contract:
    hypotheses become material claims, assumptions become constraints,
    invalidated conditions become limitations, and scalar synthesis uncertainty is
    recorded as canonical uncertainty. Source observations are represented only by
    packet evidence references; reconstruction stays delegated to canonical runtime
    or domain records.
    """

    if not reconstruction_references:
        raise StrategySynthesisEvidencePacketAssemblyError(
            "strategy synthesis packet requires reconstruction references."
        )
    _validate_decision_evidence_packet_binding(
        decision=decision,
        packet_id=packet_id,
    )

    hypotheses_by_perspective = _hypotheses_by_perspective(hypotheses)
    evidence_by_id = _evidence_by_id(hypotheses)
    reconstruction_reference_ids = tuple(
        reference.reference_id for reference in reconstruction_references
    )

    constraints = _constraints_for_hypotheses(
        hypotheses=hypotheses,
        evidence_by_id=evidence_by_id,
    )
    limitations = _limitations_for_hypotheses(
        hypotheses=hypotheses,
        evidence_by_id=evidence_by_id,
    )
    uncertainty = EvidenceUncertainty(
        uncertainty_id="strategy_synthesis_uncertainty",
        summary=(
            "Strategy synthesis uncertainty "
            f"{decision.uncertainty} with confidence {decision.confidence}."
        ),
        evidence_ids=tuple(evidence_by_id),
    )
    evidence = tuple(
        EvidenceReference(
            evidence_id=item.evidence_id,
            kind=EvidenceReferenceKind.WORKFLOW_NODE_OUTPUT,
            reconstruction_reference_ids=reconstruction_reference_ids,
            summary=_evidence_summary(item),
            source_of_truth=SourceOfTruthCategory.RUNTIME_EVIDENCE,
            support_snapshot=_support_snapshot_for_evidence(
                item,
                support_snapshots,
            ),
        )
        for item in evidence_by_id.values()
    )
    if not evidence:
        raise StrategySynthesisEvidencePacketAssemblyError(
            "strategy synthesis packet requires at least one evidence reference."
        )

    claims = (
        _decision_claim(
            decision=decision,
            hypotheses_by_perspective=hypotheses_by_perspective,
            uncertainty_id=uncertainty.uncertainty_id,
        ),
        *tuple(
            _evaluation_claim(
                evaluation_perspective=evaluation.perspective,
                decision=decision,
                hypotheses_by_perspective=hypotheses_by_perspective,
                uncertainty_id=uncertainty.uncertainty_id,
            )
            for evaluation in decision.evaluations
        ),
    )

    return DecisionEvidencePacket(
        packet_id=packet_id,
        output_id=output_id,
        authority=authority,
        claims=claims,
        evidence=evidence,
        reconstruction_references=reconstruction_references,
        constraints=constraints,
        uncertainties=(uncertainty,),
        limitations=limitations,
        retention=retention,
    )


def _validate_decision_evidence_packet_binding(
    *,
    decision: StrategySynthesisDecision,
    packet_id: str,
) -> None:
    packet_ids = decision.evidence_packet_ids
    if not packet_ids:
        raise StrategySynthesisEvidencePacketAssemblyError(
            "strategy synthesis decision requires canonical evidence packet "
            f"binding for packet {packet_id!r}."
        )
    if packet_ids == (packet_id,):
        return
    if packet_id not in packet_ids:
        raise StrategySynthesisEvidencePacketAssemblyError(
            "strategy synthesis decision evidence_packet_ids "
            f"{packet_ids!r} does not match canonical packet {packet_id!r}."
        )
    substituted_packet_ids = tuple(
        existing_packet_id
        for existing_packet_id in packet_ids
        if existing_packet_id != packet_id
    )
    raise StrategySynthesisEvidencePacketAssemblyError(
        "strategy synthesis decision contains substituted evidence packet ids "
        f"{substituted_packet_ids!r} for canonical packet {packet_id!r}."
    )


def _support_snapshot_for_evidence(
    item: StrategyEvidenceItem,
    support_snapshots: Mapping[str, SupportingEvidenceSnapshot],
) -> SupportingEvidenceSnapshot:
    snapshot = support_snapshots.get(item.evidence_id)
    if snapshot is None:
        raise StrategySynthesisEvidencePacketAssemblyError(
            f"strategy synthesis evidence '{item.evidence_id}' lacks retained "
            "support snapshot."
        )
    return snapshot


def _hypotheses_by_perspective(
    hypotheses: tuple[StrategyHypothesis, ...],
) -> dict[StrategyPerspective, StrategyHypothesis]:
    by_perspective: dict[StrategyPerspective, StrategyHypothesis] = {}
    for hypothesis in hypotheses:
        if hypothesis.perspective in by_perspective:
            raise StrategySynthesisEvidencePacketAssemblyError(
                "duplicate strategy hypothesis for perspective "
                f"'{hypothesis.perspective.value}'."
            )
        by_perspective[hypothesis.perspective] = hypothesis
    return by_perspective


def _evidence_by_id(
    hypotheses: tuple[StrategyHypothesis, ...],
) -> dict[str, StrategyEvidenceItem]:
    evidence: dict[str, StrategyEvidenceItem] = {}
    for hypothesis in hypotheses:
        for item in (
            *hypothesis.supporting_evidence,
            *hypothesis.contradicting_evidence,
        ):
            if item.evidence_id not in evidence:
                evidence[item.evidence_id] = item
    return evidence


def _constraints_for_hypotheses(
    *,
    hypotheses: tuple[StrategyHypothesis, ...],
    evidence_by_id: dict[str, StrategyEvidenceItem],
) -> tuple[EvidenceConstraint, ...]:
    constraints: list[EvidenceConstraint] = []
    for hypothesis in hypotheses:
        if not hypothesis.key_assumptions:
            raise StrategySynthesisEvidencePacketAssemblyError(
                "strategy synthesis constraint for perspective "
                f"'{hypothesis.perspective.value}' requires at least one assumption."
            )
        for assumption in hypothesis.key_assumptions:
            _validate_assumption_evidence(assumption, evidence_by_id)
            constraints.append(
                EvidenceConstraint(
                    constraint_id=_constraint_id(assumption),
                    summary=(
                        f"{assumption.perspective.value} assumption "
                        f"'{assumption.assumption_id}' with confidence "
                        f"{assumption.confidence}: {assumption.description}"
                    ),
                    evidence_ids=assumption.evidence_ids,
                )
            )
    return tuple(constraints)


def _limitations_for_hypotheses(
    *,
    hypotheses: tuple[StrategyHypothesis, ...],
    evidence_by_id: dict[str, StrategyEvidenceItem],
) -> tuple[EvidenceLimitation, ...]:
    limitations: list[EvidenceLimitation] = []
    for hypothesis in hypotheses:
        for condition in hypothesis.invalidation_conditions:
            if not condition.is_invalidated():
                continue
            evidence_id = _validated_invalidation_evidence(condition, evidence_by_id)
            limitations.append(
                EvidenceLimitation(
                    limitation_id=_limitation_id(condition),
                    summary=(
                        f"{condition.perspective.value} invalidation "
                        f"'{condition.condition_id}' triggered: "
                        f"{condition.description} observed "
                        f"{condition.observed_value} "
                        f"{condition.operator.value} "
                        f"threshold {condition.threshold}."
                    ),
                    evidence_ids=(evidence_id,),
                )
            )
    return tuple(limitations)


def _decision_claim(
    *,
    decision: StrategySynthesisDecision,
    hypotheses_by_perspective: dict[StrategyPerspective, StrategyHypothesis],
    uncertainty_id: str,
) -> MaterialClaim:
    for evaluation in decision.evaluations:
        _require_hypothesis(evaluation.perspective, hypotheses_by_perspective)

    supporting_ids = _decision_supporting_evidence_ids(
        decision,
        hypotheses_by_perspective,
    )
    conflicting_ids = _unique_string_tuple(
        evidence.evidence_id
        for hypothesis in hypotheses_by_perspective.values()
        for evidence in hypothesis.contradicting_evidence
    )
    return MaterialClaim(
        claim_id="strategy_synthesis_decision",
        text=(
            "Strategy synthesis selected "
            f"{_selected_perspective_text(decision)} with status "
            f"{decision.selection_status.value}, regime {decision.regime}, "
            f"confidence {decision.confidence}, uncertainty {decision.uncertainty}, "
            f"and directional score {decision.directional_score}."
        ),
        evidence=ClaimEvidenceBinding(
            supporting_evidence_ids=supporting_ids,
            conflicting_evidence_ids=conflicting_ids,
            constraint_ids=tuple(
                _constraint_id(assumption)
                for hypothesis in hypotheses_by_perspective.values()
                for assumption in hypothesis.key_assumptions
            ),
            uncertainty_ids=(uncertainty_id,),
            limitation_ids=tuple(
                _limitation_id(condition)
                for hypothesis in hypotheses_by_perspective.values()
                for condition in hypothesis.invalidation_conditions
                if condition.is_invalidated()
            ),
        ),
    )


def _evaluation_claim(
    *,
    evaluation_perspective: StrategyPerspective,
    decision: StrategySynthesisDecision,
    hypotheses_by_perspective: dict[StrategyPerspective, StrategyHypothesis],
    uncertainty_id: str,
) -> MaterialClaim:
    hypothesis = _require_hypothesis(evaluation_perspective, hypotheses_by_perspective)
    evaluation = next(
        item
        for item in decision.evaluations
        if item.perspective is evaluation_perspective
    )
    supporting_ids = _supporting_evidence_ids(hypothesis)
    return MaterialClaim(
        claim_id=f"strategy_hypothesis_evaluation:{evaluation_perspective.value}",
        text=(
            f"{evaluation_perspective.value} hypothesis evaluated with candidate score "
            f"{evaluation.candidate_score}, synthesis weight "
            f"{evaluation.synthesis_weight}, "
            f"rank {evaluation.rank}, status {evaluation.selection_status.value}, "
            f"invalidated {evaluation.invalidated}, perspective weight "
            f"{evaluation.perspective_weight}, contradiction burden "
            f"{evaluation.contradiction_burden}, and assumption support "
            f"{evaluation.assumption_support}."
        ),
        evidence=ClaimEvidenceBinding(
            supporting_evidence_ids=supporting_ids,
            conflicting_evidence_ids=tuple(
                item.evidence_id for item in hypothesis.contradicting_evidence
            ),
            constraint_ids=tuple(
                _constraint_id(assumption) for assumption in hypothesis.key_assumptions
            ),
            uncertainty_ids=(uncertainty_id,),
            limitation_ids=tuple(
                _limitation_id(condition)
                for condition in hypothesis.invalidation_conditions
                if condition.is_invalidated()
            ),
        ),
    )


def _require_hypothesis(
    perspective: StrategyPerspective,
    hypotheses_by_perspective: dict[StrategyPerspective, StrategyHypothesis],
) -> StrategyHypothesis:
    hypothesis = hypotheses_by_perspective.get(perspective)
    if hypothesis is None:
        raise StrategySynthesisEvidencePacketAssemblyError(
            f"missing hypothesis for perspective '{perspective.value}'."
        )
    return hypothesis


def _supporting_evidence_ids(hypothesis: StrategyHypothesis) -> tuple[str, ...]:
    evidence_ids = tuple(item.evidence_id for item in hypothesis.supporting_evidence)
    if not evidence_ids:
        raise StrategySynthesisEvidencePacketAssemblyError(
            f"hypothesis '{hypothesis.perspective.value}' lacks supporting "
            "evidence references."
        )
    return evidence_ids


def _decision_supporting_evidence_ids(
    decision: StrategySynthesisDecision,
    hypotheses_by_perspective: dict[StrategyPerspective, StrategyHypothesis],
) -> tuple[str, ...]:
    if decision.selected_perspective is not None:
        return _supporting_evidence_ids(
            _require_hypothesis(
                decision.selected_perspective,
                hypotheses_by_perspective,
            )
        )
    return _unique_string_tuple(
        evidence_id
        for hypothesis in hypotheses_by_perspective.values()
        for evidence_id in _supporting_evidence_ids(hypothesis)
    )


def _validate_assumption_evidence(
    assumption: StrategyAssumption,
    evidence_by_id: dict[str, StrategyEvidenceItem],
) -> None:
    if not assumption.evidence_ids:
        raise StrategySynthesisEvidencePacketAssemblyError(
            f"constraint '{assumption.assumption_id}' lacks evidence references."
        )
    for evidence_id in assumption.evidence_ids:
        if evidence_id not in evidence_by_id:
            raise StrategySynthesisEvidencePacketAssemblyError(
                f"assumption '{assumption.assumption_id}' references unknown "
                f"evidence '{evidence_id}'."
            )


def _validated_invalidation_evidence(
    condition: StrategyInvalidationCondition,
    evidence_by_id: dict[str, StrategyEvidenceItem],
) -> str:
    if condition.evidence_id is None:
        raise StrategySynthesisEvidencePacketAssemblyError(
            f"invalidation condition '{condition.condition_id}' lacks evidence_id."
        )
    if condition.evidence_id not in evidence_by_id:
        raise StrategySynthesisEvidencePacketAssemblyError(
            f"invalidation condition '{condition.condition_id}' references unknown "
            f"evidence '{condition.evidence_id}'."
        )
    return condition.evidence_id


def _constraint_id(assumption: StrategyAssumption) -> str:
    return f"{assumption.perspective.value}:assumption:{assumption.assumption_id}"


def _limitation_id(condition: StrategyInvalidationCondition) -> str:
    return f"{condition.perspective.value}:invalidation:{condition.condition_id}"


def _evidence_summary(item: StrategyEvidenceItem) -> str:
    explanation = "" if item.explanation is None else f" {item.explanation}"
    supports = ",".join(perspective.value for perspective in item.supports) or "none"
    contradicts = (
        ",".join(perspective.value for perspective in item.contradicts) or "none"
    )
    return (
        f"{item.source} {item.name} observed {item.observed_value}; "
        f"strength {item.strength}; reliability {item.reliability}; "
        f"supports {supports}; contradicts {contradicts}.{explanation}"
    )


def _selected_perspective_text(decision: StrategySynthesisDecision) -> str:
    if decision.selected_perspective is None:
        return "no single perspective"
    return decision.selected_perspective.value


def _unique_string_tuple(values: Iterable[str]) -> tuple[str, ...]:
    unique: dict[str, None] = {}
    for value in values:
        unique[value] = None
    return tuple(unique)
