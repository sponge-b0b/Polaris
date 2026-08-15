from __future__ import annotations

from dataclasses import FrozenInstanceError
from typing import Final

import pytest

from domain.authority import RiskTier, SourceOfTruthCategory, classify_risk_authority
from domain.decision_evidence import (
    ClaimEvidenceBinding,
    ClaimMaterialityTier,
    DecisionEvidencePacketReadinessFailureMode,
    DecisionEvidencePacketValidationError,
    EvidenceClaimReference,
    EvidenceConstraint,
    EvidenceLimitation,
    EvidenceReference,
    EvidenceReferenceKind,
    EvidenceRetentionRequirement,
    EvidenceUncertainty,
    MaterialClaim,
    ReconstructionReference,
    ReconstructionReferenceKind,
    SupportingEvidenceSnapshot,
    UnsupportedMaterialClaimError,
    assess_decision_evidence_packet_readiness,
    evidence_claim_references_from_packet,
)
from domain.decision_evidence import (
    DecisionEvidencePacket as DomainDecisionEvidencePacket,
)
from tests.helpers.risk_authority_examples import (
    authority_input_for_tier,
    runtime_evidence_authority_input,
)


def DecisionEvidencePacket(**kwargs: object) -> DomainDecisionEvidencePacket:
    return DomainDecisionEvidencePacket(
        workflow_name="test-workflow",
        workflow_definition_fingerprint="test-definition-fingerprint",
        execution_id="test-execution",
        **kwargs,  # type: ignore[arg-type]
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
                support_snapshot=material_support_snapshot(
                    snapshot_id="evidence-support:support-snapshot",
                    source_label="rag-context",
                ),
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

    readiness = assess_decision_evidence_packet_readiness(packets=(packet,))

    assert packet.material_claims == packet.claims
    assert packet.claims[0].materiality is ClaimMaterialityTier.READINESS_GATING
    assert packet.claims[0].material is True
    assert readiness.passed is True
    assert readiness.conflicting_evidence_ids == ()
    assert readiness.unresolved_conflicting_evidence_ids == ()


def test_readiness_requires_retained_material_support_snapshot() -> None:
    packet = DecisionEvidencePacket(
        packet_id="packet-1",
        output_id="output-1",
        authority=classify_risk_authority(authority_input_for_tier(RiskTier.ENHANCED)),
        claims=(supported_claim(),),
        evidence=(supporting_evidence(retain_snapshot=False),),
        reconstruction_references=(workflow_reference(),),
        retention=retention_requirement(),
    )

    readiness = assess_decision_evidence_packet_readiness(packets=(packet,))

    assert readiness.passed is False
    assert (
        readiness.failure_mode
        is DecisionEvidencePacketReadinessFailureMode.MATERIAL_SUPPORT_SNAPSHOT_MISSING
    )
    assert "retained support snapshot" in readiness.message
    assert readiness.provenance_reconstruction_complete is True
    assert readiness.claim_support_complete is False
    assert readiness.correctness_support_complete is False
    assert readiness.packet_ids == ("packet-1",)
    assert readiness.supporting_evidence_ids == ("evidence-1",)
    assert readiness.reconstruction_reference_ids == ("workflow-node",)


@pytest.mark.parametrize(
    ("tampered_field", "tampered_value"),
    [
        ("redacted_content", "Tampered material support content."),
        ("content_digest", None),
    ],
)
def test_readiness_detects_tampered_or_incomplete_material_support_snapshot(
    tampered_field: str,
    tampered_value: str | None,
) -> None:
    snapshot = material_support_snapshot()
    object.__setattr__(snapshot, tampered_field, tampered_value)
    packet = DecisionEvidencePacket(
        packet_id="packet-1",
        output_id="output-1",
        authority=classify_risk_authority(authority_input_for_tier(RiskTier.ENHANCED)),
        claims=(supported_claim(),),
        evidence=(supporting_evidence(support_snapshot=snapshot),),
        reconstruction_references=(workflow_reference(),),
        retention=retention_requirement(),
    )

    readiness = assess_decision_evidence_packet_readiness(packets=(packet,))

    assert readiness.passed is False
    assert (
        readiness.failure_mode
        is DecisionEvidencePacketReadinessFailureMode.MATERIAL_SUPPORT_SNAPSHOT_MISSING
    )
    assert "content digest" in readiness.message
    assert readiness.supporting_evidence_ids == ("evidence-1",)
    assert readiness.reconstruction_reference_ids == ("workflow-node",)


def test_verified_claim_reference_matches_canonical_packet_binding() -> None:
    packet = DecisionEvidencePacket(
        packet_id="packet-1",
        output_id="output-1",
        authority=classify_risk_authority(authority_input_for_tier(RiskTier.ENHANCED)),
        claims=(supported_claim(),),
        evidence=(supporting_evidence(),),
        reconstruction_references=(workflow_reference(),),
        retention=retention_requirement(),
    )
    reference = evidence_claim_references_from_packet(packet).claim_references[0]

    readiness = assess_decision_evidence_packet_readiness(
        packets=(packet,),
        claim_references=(reference,),
        required_risk_tier=RiskTier.ENHANCED,
    )

    assert readiness.passed is True
    assert readiness.packet_ids == ("packet-1",)
    assert readiness.supporting_evidence_ids == ("evidence-1",)
    assert readiness.reconstruction_reference_ids == ("workflow-node",)


def test_reference_only_claim_metadata_cannot_satisfy_material_readiness() -> None:
    reference = EvidenceClaimReference(
        packet_id="packet-1",
        output_id="output-1",
        claim_id="claim-1",
        risk_tier=RiskTier.ENHANCED,
        supporting_evidence_ids=("evidence-1",),
        reconstruction_reference_ids=("workflow-node",),
    )

    readiness = assess_decision_evidence_packet_readiness(
        claim_references=(reference,),
        required_risk_tier=RiskTier.ENHANCED,
    )

    assert readiness.passed is False
    assert (
        readiness.failure_mode
        is DecisionEvidencePacketReadinessFailureMode.PACKET_SUPPORT_MISSING
    )
    assert "reference-only" in readiness.message.lower()
    assert "canonical" in readiness.message.lower()
    assert readiness.packet_ids == ("packet-1",)
    assert readiness.supporting_evidence_ids == ("evidence-1",)
    assert readiness.reconstruction_reference_ids == ("workflow-node",)
    assert readiness.claim_support_complete is False


def test_fabricated_claim_reference_must_match_verified_packet_binding() -> None:
    packet = DecisionEvidencePacket(
        packet_id="packet-1",
        output_id="output-1",
        authority=classify_risk_authority(authority_input_for_tier(RiskTier.ENHANCED)),
        claims=(supported_claim(),),
        evidence=(supporting_evidence(),),
        reconstruction_references=(workflow_reference(),),
        retention=retention_requirement(),
    )
    fabricated_reference = EvidenceClaimReference(
        packet_id="packet-1",
        output_id="output-1",
        claim_id="claim-1",
        risk_tier=RiskTier.ENHANCED,
        supporting_evidence_ids=("stale-evidence",),
        reconstruction_reference_ids=("workflow-node",),
    )

    readiness = assess_decision_evidence_packet_readiness(
        packets=(packet,),
        claim_references=(fabricated_reference,),
        required_risk_tier=RiskTier.ENHANCED,
    )

    assert readiness.passed is False
    assert (
        readiness.failure_mode
        is DecisionEvidencePacketReadinessFailureMode.AUTHORITY_METADATA_INCONSISTENT
    )
    assert "canonical" in readiness.message.lower()
    assert readiness.packet_ids == ("packet-1",)
    assert readiness.supporting_evidence_ids == ("stale-evidence",)
    assert readiness.reconstruction_reference_ids == ("workflow-node",)


def test_reference_only_contextual_metadata_is_audit_not_readiness_proof() -> None:
    reference = EvidenceClaimReference(
        packet_id="packet-1",
        output_id="output-1",
        claim_id="claim-context",
        risk_tier=RiskTier.ENHANCED,
        supporting_evidence_ids=(),
        conflicting_evidence_ids=("evidence-conflict",),
        unresolved_conflicting_evidence_ids=("evidence-conflict",),
        reconstruction_reference_ids=("conflict-record",),
        material=False,
        materiality=ClaimMaterialityTier.CONTEXTUAL,
    )

    readiness = assess_decision_evidence_packet_readiness(
        claim_references=(reference,),
        required_risk_tier=RiskTier.ENHANCED,
    )

    assert readiness.passed is False
    assert (
        readiness.failure_mode
        is DecisionEvidencePacketReadinessFailureMode.PACKET_SUPPORT_MISSING
    )
    assert readiness.claim_support_complete is False
    assert readiness.correctness_support_complete is False
    assert readiness.conflicting_evidence_ids == ("evidence-conflict",)
    assert readiness.unresolved_conflicting_evidence_ids == ("evidence-conflict",)


def test_unresolved_material_conflict_fails_readiness_closed() -> None:
    authority = classify_risk_authority(authority_input_for_tier(RiskTier.ENHANCED))

    packet = DecisionEvidencePacket(
        packet_id="packet-1",
        output_id="output-1",
        authority=authority,
        claims=(
            MaterialClaim(
                claim_id="claim-conflicted",
                text=(
                    "This material claim has both support and unresolved contradiction."
                ),
                evidence=ClaimEvidenceBinding(
                    supporting_evidence_ids=("evidence-1",),
                    conflicting_evidence_ids=("evidence-conflict",),
                    unresolved_conflicting_evidence_ids=("evidence-conflict",),
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
    assert readiness.claim_support_complete is True
    assert readiness.correctness_support_complete is False
    assert readiness.conflicting_evidence_ids == ("evidence-conflict",)
    assert readiness.unresolved_conflicting_evidence_ids == ("evidence-conflict",)


def test_resolved_contrary_evidence_stays_reviewable_without_blocking() -> None:
    authority = classify_risk_authority(authority_input_for_tier(RiskTier.ENHANCED))

    packet = DecisionEvidencePacket(
        packet_id="packet-1",
        output_id="output-1",
        authority=authority,
        claims=(
            MaterialClaim(
                claim_id="claim-reviewed",
                text=(
                    "This material claim discloses contrary evidence resolved "
                    "in review."
                ),
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

    assert readiness.passed is True
    assert readiness.failure_mode is DecisionEvidencePacketReadinessFailureMode.NONE
    assert readiness.claim_support_complete is True
    assert readiness.correctness_support_complete is True
    assert readiness.conflicting_evidence_ids == ("evidence-conflict",)
    assert readiness.unresolved_conflicting_evidence_ids == ()


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
                    supporting_evidence_ids=("evidence-1",),
                    conflicting_evidence_ids=("evidence-conflict",),
                ),
            ),
        ),
        evidence=(supporting_evidence(retain_snapshot=False), conflicting_evidence()),
        reconstruction_references=(workflow_reference(), conflict_reference()),
        retention=retention_requirement(),
    )

    assert packet.material_claims == ()
    assert packet.claims[0].materiality is ClaimMaterialityTier.CONTEXTUAL
    assert packet.claims[0].material is False
    assert packet.claims[0].evidence.supporting_evidence_ids == ("evidence-1",)
    assert packet.evidence[0].support_snapshot is None
    assert packet.claims[0].evidence.conflicting_evidence_ids == ("evidence-conflict",)
    assert assess_decision_evidence_packet_readiness(packets=(packet,)).passed is True


def test_readiness_separates_reconstructable_provenance_from_rejected_support() -> None:
    packet = DecisionEvidencePacket(
        packet_id="packet-1",
        output_id="output-1",
        authority=classify_risk_authority(authority_input_for_tier(RiskTier.ENHANCED)),
        claims=(supported_claim(),),
        evidence=(supporting_evidence(),),
        reconstruction_references=(workflow_reference(),),
        retention=retention_requirement(),
    )

    readiness = assess_decision_evidence_packet_readiness(
        packets=(packet,),
        rejected_evidence_ids=("evidence-1",),
    )

    assert readiness.passed is False
    assert readiness.provenance_reconstruction_complete is True
    assert readiness.claim_support_complete is False
    assert readiness.correctness_support_complete is False
    assert readiness.provenance_reconstruction_failure_mode is (
        DecisionEvidencePacketReadinessFailureMode.NONE
    )
    assert (
        readiness.claim_support_failure_mode
        is DecisionEvidencePacketReadinessFailureMode.REJECTED_EVIDENCE_CITED
    )


def test_readiness_validates_every_canonical_reconstruction_reference_kind() -> None:
    reconstruction_references = tuple(
        ReconstructionReference(
            reference_id=f"reference-{kind.value}",
            kind=kind,
            record_id=f"record-{kind.value}",
            source_of_truth=_source_of_truth_for_reference_kind(kind),
            snapshot_id=f"snapshot-{kind.value}",
            content_digest=f"digest-{kind.value}",
        )
        for kind in ReconstructionReferenceKind
    )
    packet = DecisionEvidencePacket(
        packet_id="packet-all-reference-kinds",
        output_id="output-1",
        authority=classify_risk_authority(authority_input_for_tier(RiskTier.ENHANCED)),
        claims=(supported_claim(),),
        evidence=(
            EvidenceReference(
                evidence_id="evidence-1",
                kind=EvidenceReferenceKind.CANONICAL_RECORD,
                reconstruction_reference_ids=tuple(
                    reference.reference_id for reference in reconstruction_references
                ),
                summary="Evidence backed by every canonical reconstruction kind.",
                support_snapshot=material_support_snapshot(),
            ),
        ),
        reconstruction_references=reconstruction_references,
        retention=retention_requirement(),
    )

    readiness = assess_decision_evidence_packet_readiness(packets=(packet,))

    assert readiness.passed is True
    assert readiness.provenance_reconstruction_complete is True
    assert readiness.reconstruction_reference_ids == tuple(
        reference.reference_id for reference in reconstruction_references
    )
    assert readiness.reconstruction_reference_kinds == tuple(
        kind.value for kind in ReconstructionReferenceKind
    )


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


_DEFAULT_SUPPORT_SNAPSHOT_ID: Final[str] = "evidence-1:support-snapshot"


def material_support_snapshot(
    *,
    snapshot_id: str = _DEFAULT_SUPPORT_SNAPSHOT_ID,
    source_label: str = "workflow_node_output:workflow-node",
) -> SupportingEvidenceSnapshot:
    return SupportingEvidenceSnapshot(
        snapshot_id=snapshot_id,
        summary="Runtime node output supporting the material claim.",
        redacted_content="Supported material claim evidence retained for readiness.",
        source_label=source_label,
    )


def supported_claim() -> MaterialClaim:
    return MaterialClaim(
        claim_id="claim-1",
        text="Supported material claim.",
        evidence=ClaimEvidenceBinding(supporting_evidence_ids=("evidence-1",)),
    )


def supporting_evidence(
    *,
    retain_snapshot: bool = True,
    support_snapshot: SupportingEvidenceSnapshot | None = None,
) -> EvidenceReference:
    snapshot = support_snapshot
    if retain_snapshot and snapshot is None:
        snapshot = material_support_snapshot()
    return EvidenceReference(
        evidence_id="evidence-1",
        kind=EvidenceReferenceKind.WORKFLOW_NODE_OUTPUT,
        reconstruction_reference_ids=("workflow-node",),
        summary="Runtime node output supporting the material claim.",
        support_snapshot=snapshot,
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


def _source_of_truth_for_reference_kind(
    kind: ReconstructionReferenceKind,
) -> SourceOfTruthCategory:
    if kind in {
        ReconstructionReferenceKind.COMPLETED_WORKFLOW_RUN,
        ReconstructionReferenceKind.WORKFLOW_NODE_OUTPUT,
    }:
        return SourceOfTruthCategory.RUNTIME_EVIDENCE
    if kind is ReconstructionReferenceKind.TRACE_CONTEXT:
        return SourceOfTruthCategory.TELEMETRY
    return SourceOfTruthCategory.CANONICAL_DOMAIN_RECORD
