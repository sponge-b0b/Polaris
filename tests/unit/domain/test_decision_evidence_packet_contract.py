from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from domain.authority import RiskTier, classify_risk_authority
from domain.decision_evidence import (
    ClaimEvidenceBinding,
    ClaimMaterialityTier,
    DecisionEvidencePacket,
    DecisionEvidencePacketReadinessFailureMode,
    DecisionEvidencePacketValidationError,
    EvidenceConstraint,
    EvidenceLimitation,
    EvidenceReference,
    EvidenceReferenceKind,
    EvidenceRetentionRequirement,
    EvidenceUncertainty,
    MaterialClaim,
    ReconstructionReference,
    ReconstructionReferenceKind,
    UnsupportedMaterialClaimError,
    assess_decision_evidence_packet_readiness,
)
from tests.helpers.risk_authority_examples import (
    authority_input_for_tier,
    runtime_evidence_authority_input,
)


def test_enhanced_packet_models_claim_relationships_and_reconstruction_refs() -> None:
    packet = DecisionEvidencePacket(
        packet_id="packet-1",
        output_id="rag-answer-1",
        authority=classify_risk_authority(authority_input_for_tier(RiskTier.ENHANCED)),
        claims=(
            MaterialClaim(
                claim_id="claim-1",
                text="SPY momentum improved across the supported lookback window.",
                evidence=ClaimEvidenceBinding(
                    supporting_evidence_ids=("evidence-support",),
                    constraint_ids=("constraint-1",),
                    uncertainty_ids=("uncertainty-1",),
                    limitation_ids=("limitation-1",),
                ),
            ),
        ),
        evidence=(
            EvidenceReference(
                evidence_id="evidence-support",
                kind=EvidenceReferenceKind.RAG_CITATION_CONTEXT,
                reconstruction_reference_ids=("rag-context",),
                summary="Curated retrieval context supporting the answer claim.",
            ),
            EvidenceReference(
                evidence_id="evidence-conflict",
                kind=EvidenceReferenceKind.CANONICAL_RECORD,
                reconstruction_reference_ids=("market-record",),
                summary="Durable market record that conflicts with part of the claim.",
            ),
        ),
        reconstruction_references=(
            ReconstructionReference(
                reference_id="rag-context",
                kind=ReconstructionReferenceKind.RAG_CITATION_CONTEXT,
                record_id="citation:C1",
            ),
            ReconstructionReference(
                reference_id="market-record",
                kind=ReconstructionReferenceKind.CANONICAL_DOMAIN_RECORD,
                record_id="market-snapshot:SPY:2026-07-25",
            ),
        ),
        constraints=(
            EvidenceConstraint(
                constraint_id="constraint-1",
                summary="Claim is constrained to the stated lookback window.",
            ),
        ),
        uncertainties=(
            EvidenceUncertainty(
                uncertainty_id="uncertainty-1",
                summary="Signal may degrade if late market data arrives.",
            ),
        ),
        limitations=(
            EvidenceLimitation(
                limitation_id="limitation-1",
                summary="This packet does not authorize broker execution.",
            ),
        ),
        retention=EvidenceRetentionRequirement(
            retain_until="2031-07-25T00:00:00Z",
            policy_id="enhanced-provenance-5y",
        ),
    )

    assert packet.risk_tier is RiskTier.ENHANCED
    assert packet.material_claims == packet.claims
    assert packet.claims[0].materiality is ClaimMaterialityTier.READINESS_GATING
    assert packet.claims[0].evidence.supporting_evidence_ids == ("evidence-support",)
    assert packet.claims[0].evidence.constraint_ids == ("constraint-1",)
    assert packet.claims[0].evidence.uncertainty_ids == ("uncertainty-1",)
    assert packet.claims[0].evidence.limitation_ids == ("limitation-1",)
    assert packet.reconstruction_reference_ids == ("rag-context", "market-record")
    assert packet.uncertainties[0].summary == (
        "Signal may degrade if late market data arrives."
    )
    assert packet.limitations[0].summary == (
        "This packet does not authorize broker execution."
    )
    with pytest.raises(FrozenInstanceError):
        packet.output_id = "other"  # type: ignore[misc]


@pytest.mark.parametrize("tier", [RiskTier.ENHANCED, RiskTier.VIGILANT])
def test_enhanced_and_vigilant_packets_require_risk_authority_contract(
    tier: RiskTier,
) -> None:
    with pytest.raises(
        DecisionEvidencePacketValidationError,
        match="authority must be a RiskAuthorityContract",
    ):
        DecisionEvidencePacket(
            packet_id="packet-1",
            output_id="output-1",
            authority=None,  # type: ignore[arg-type]
            claims=(supported_claim(),),
            evidence=(supporting_evidence(),),
            reconstruction_references=(workflow_reference(),),
            retention=retention_requirement(),
        )

    baseline_authority = classify_risk_authority(runtime_evidence_authority_input())
    with pytest.raises(
        DecisionEvidencePacketValidationError,
        match="decision evidence packets are only valid for enhanced or vigilant",
    ):
        DecisionEvidencePacket(
            packet_id="packet-1",
            output_id="output-1",
            authority=baseline_authority,
            claims=(supported_claim(),),
            evidence=(supporting_evidence(),),
            reconstruction_references=(workflow_reference(),),
            retention=retention_requirement(),
        )

    authority = classify_risk_authority(authority_input_for_tier(tier))
    packet = DecisionEvidencePacket(
        packet_id=f"packet-{tier.value}",
        output_id="output-1",
        authority=authority,
        claims=(supported_claim(),),
        evidence=(supporting_evidence(),),
        reconstruction_references=(workflow_reference(),),
        retention=retention_requirement(),
    )

    assert packet.authority is authority
    assert packet.risk_tier is tier


def test_material_claim_without_support_fails_closed() -> None:
    authority = classify_risk_authority(authority_input_for_tier(RiskTier.ENHANCED))

    with pytest.raises(UnsupportedMaterialClaimError, match="claim-unsupported"):
        DecisionEvidencePacket(
            packet_id="packet-1",
            output_id="output-1",
            authority=authority,
            claims=(
                MaterialClaim(
                    claim_id="claim-unsupported",
                    text="This material claim has no backing evidence.",
                ),
            ),
            evidence=(supporting_evidence(),),
            reconstruction_references=(workflow_reference(),),
            retention=retention_requirement(),
        )


def test_supported_uncontradicted_material_claim_is_readiness_gating() -> None:
    packet = DecisionEvidencePacket(
        packet_id="packet-1",
        output_id="output-1",
        authority=classify_risk_authority(authority_input_for_tier(RiskTier.ENHANCED)),
        claims=(supported_claim(),),
        evidence=(supporting_evidence(),),
        reconstruction_references=(workflow_reference(),),
        retention=retention_requirement(),
    )

    assert packet.material_claims == packet.claims
    assert packet.claims[0].materiality is ClaimMaterialityTier.READINESS_GATING
    assert packet.claims[0].material is True


def test_supported_material_claim_with_conflict_fails_readiness_closed() -> None:
    authority = classify_risk_authority(authority_input_for_tier(RiskTier.ENHANCED))

    packet = DecisionEvidencePacket(
        packet_id="packet-1",
        output_id="output-1",
        authority=authority,
        claims=(
            MaterialClaim(
                claim_id="claim-conflicted",
                text="This material claim has both support and contradiction.",
                evidence=ClaimEvidenceBinding(
                    supporting_evidence_ids=("evidence-1",),
                    conflicting_evidence_ids=("evidence-conflict",),
                ),
            ),
        ),
        evidence=(supporting_evidence(), conflicting_evidence()),
        reconstruction_references=(workflow_reference(), conflict_reference()),
        retention=retention_requirement(),
    )

    readiness = assess_decision_evidence_packet_readiness(packets=(packet,))

    assert readiness.passed is False
    assert (
        readiness.failure_mode
        is DecisionEvidencePacketReadinessFailureMode.MATERIAL_CONFLICT_UNRESOLVED
    )
    assert readiness.conflicting_evidence_ids == ("evidence-conflict",)


def test_contextual_claim_can_be_unsupported_or_conflicted_without_blocking() -> None:
    authority = classify_risk_authority(authority_input_for_tier(RiskTier.ENHANCED))

    packet = DecisionEvidencePacket(
        packet_id="packet-1",
        output_id="output-1",
        authority=authority,
        claims=(
            MaterialClaim(
                claim_id="claim-context",
                text="This contextual claim is retained for audit only.",
                materiality=ClaimMaterialityTier.CONTEXTUAL,
                evidence=ClaimEvidenceBinding(
                    conflicting_evidence_ids=("evidence-conflict",),
                ),
            ),
        ),
        evidence=(conflicting_evidence(),),
        reconstruction_references=(conflict_reference(),),
        retention=retention_requirement(),
    )

    assert packet.material_claims == ()
    assert packet.claims[0].materiality is ClaimMaterialityTier.CONTEXTUAL
    assert packet.claims[0].material is False
    assert packet.claims[0].evidence.supporting_evidence_ids == ()
    assert packet.claims[0].evidence.conflicting_evidence_ids == ("evidence-conflict",)
    assert assess_decision_evidence_packet_readiness(packets=(packet,)).passed is True


def test_packet_references_canonical_evidence_ids_not_source_payloads() -> None:
    authority = classify_risk_authority(authority_input_for_tier(RiskTier.VIGILANT))

    with pytest.raises(
        DecisionEvidencePacketValidationError,
        match="raw_payload is not part of the canonical evidence packet contract",
    ):
        EvidenceReference(
            evidence_id="evidence-1",
            kind=EvidenceReferenceKind.CANONICAL_RECORD,
            reconstruction_reference_ids=("workflow-node",),
            raw_payload={"arbitrary": "source copy"},  # type: ignore[call-arg]
        )

    packet = DecisionEvidencePacket(
        packet_id="packet-1",
        output_id="output-1",
        authority=authority,
        claims=(supported_claim(),),
        evidence=(supporting_evidence(),),
        reconstruction_references=(workflow_reference(),),
        retention=retention_requirement(),
    )

    assert packet.evidence[0].reconstruction_reference_ids == ("workflow-node",)


def test_unknown_relationship_targets_are_rejected() -> None:
    authority = classify_risk_authority(authority_input_for_tier(RiskTier.ENHANCED))

    with pytest.raises(
        DecisionEvidencePacketValidationError,
        match="claim-1 references unknown supporting evidence 'missing-evidence'",
    ):
        DecisionEvidencePacket(
            packet_id="packet-1",
            output_id="output-1",
            authority=authority,
            claims=(
                MaterialClaim(
                    claim_id="claim-1",
                    text="Claim references evidence outside the packet index.",
                    evidence=ClaimEvidenceBinding(
                        supporting_evidence_ids=("missing-evidence",),
                    ),
                ),
            ),
            evidence=(supporting_evidence(),),
            reconstruction_references=(workflow_reference(),),
            retention=retention_requirement(),
        )


def supported_claim() -> MaterialClaim:
    return MaterialClaim(
        claim_id="claim-1",
        text="Supported material claim.",
        evidence=ClaimEvidenceBinding(supporting_evidence_ids=("evidence-1",)),
    )


def supporting_evidence() -> EvidenceReference:
    return EvidenceReference(
        evidence_id="evidence-1",
        kind=EvidenceReferenceKind.WORKFLOW_NODE_OUTPUT,
        reconstruction_reference_ids=("workflow-node",),
        summary="Runtime node output supporting the material claim.",
    )


def conflicting_evidence() -> EvidenceReference:
    return EvidenceReference(
        evidence_id="evidence-conflict",
        kind=EvidenceReferenceKind.CANONICAL_RECORD,
        reconstruction_reference_ids=("conflict-record",),
        summary="Canonical record contradicting a readiness-gating claim.",
    )


def workflow_reference() -> ReconstructionReference:
    return ReconstructionReference(
        reference_id="workflow-node",
        kind=ReconstructionReferenceKind.WORKFLOW_NODE_OUTPUT,
        record_id="run-1:node:market-analysis",
    )


def conflict_reference() -> ReconstructionReference:
    return ReconstructionReference(
        reference_id="conflict-record",
        kind=ReconstructionReferenceKind.CANONICAL_DOMAIN_RECORD,
        record_id="market-snapshot:SPY:2026-07-25",
    )


def retention_requirement() -> EvidenceRetentionRequirement:
    return EvidenceRetentionRequirement(
        retain_until="2031-07-25T00:00:00Z",
        policy_id="enhanced-provenance-5y",
    )
