from __future__ import annotations

from typing import Any, cast

import pytest

from domain.authority import RiskTier, classify_risk_authority
from domain.decision_evidence import (
    DECISION_EVIDENCE_CLAIM_REFERENCES_METADATA_KEY,
    ClaimEvidenceBinding,
    ClaimMaterialityTier,
    DecisionEvidencePacket,
    EvidenceClaimReference,
    EvidenceLimitation,
    EvidenceReference,
    EvidenceReferenceKind,
    EvidenceRetentionRequirement,
    EvidenceUncertainty,
    MaterialClaim,
    ReconstructionReference,
    ReconstructionReferenceKind,
    UnsupportedMaterialClaimError,
    evidence_claim_references_from_metadata,
    evidence_claim_references_from_packet,
)
from tests.helpers.risk_authority_examples import authority_input_for_tier


def test_claim_references_preserve_reconstruction_uncertainty_limits() -> None:
    packet = _packet()

    references = evidence_claim_references_from_packet(packet)
    metadata = references.as_metadata()

    assert metadata["packet_ids"] == ["packet-1"]
    assert metadata["reconstruction_reference_ids"] == ["workflow-node"]
    claim_references = cast(list[dict[str, Any]], metadata["claim_references"])
    claim_reference = claim_references[0]
    assert claim_reference == {
        "schema_version": 1,
        "packet_id": "packet-1",
        "output_id": "recommendation-output-1",
        "claim_id": "claim-1",
        "risk_tier": RiskTier.ENHANCED.value,
        "material": True,
        "materiality": ClaimMaterialityTier.READINESS_GATING.value,
        "supporting_evidence_ids": ["evidence-1"],
        "conflicting_evidence_ids": [],
        "unresolved_conflicting_evidence_ids": [],
        "reconstruction_reference_ids": ["workflow-node"],
        "uncertainty_ids": ["uncertainty-1"],
        "limitation_ids": ["limitation-1"],
    }
    serialized = str(metadata)
    assert "Runtime node output supporting the material claim." not in serialized
    assert "raw_payload" not in serialized


def test_claim_reference_metadata_round_trips_for_presentation_boundaries() -> None:
    references = evidence_claim_references_from_packet(_packet())
    envelope = {
        DECISION_EVIDENCE_CLAIM_REFERENCES_METADATA_KEY: references.as_metadata()
    }

    parsed = evidence_claim_references_from_metadata(
        envelope[DECISION_EVIDENCE_CLAIM_REFERENCES_METADATA_KEY]
    )

    assert parsed == references
    assert parsed.claim_references[0].uncertainty_ids == ("uncertainty-1",)
    assert parsed.claim_references[0].limitation_ids == ("limitation-1",)


def test_claim_reference_metadata_exposes_resolved_contrary_evidence() -> None:
    packet = DecisionEvidencePacket(
        packet_id="packet-with-contrary-evidence",
        output_id="recommendation-output-1",
        authority=classify_risk_authority(authority_input_for_tier(RiskTier.ENHANCED)),
        claims=(
            MaterialClaim(
                claim_id="claim-1",
                text="SPY momentum remains supported after contrary evidence review.",
                evidence=ClaimEvidenceBinding(
                    supporting_evidence_ids=("evidence-1",),
                    conflicting_evidence_ids=("evidence-conflict",),
                ),
            ),
        ),
        evidence=(
            EvidenceReference(
                evidence_id="evidence-1",
                kind=EvidenceReferenceKind.WORKFLOW_NODE_OUTPUT,
                reconstruction_reference_ids=("workflow-node",),
                summary="Runtime node output supporting the material claim.",
            ),
            EvidenceReference(
                evidence_id="evidence-conflict",
                kind=EvidenceReferenceKind.CANONICAL_RECORD,
                reconstruction_reference_ids=("conflict-record",),
                summary="Contrary evidence disclosed for governance review.",
            ),
        ),
        reconstruction_references=(
            ReconstructionReference(
                reference_id="workflow-node",
                kind=ReconstructionReferenceKind.WORKFLOW_NODE_OUTPUT,
                record_id="run-1:node:market-analysis",
            ),
            ReconstructionReference(
                reference_id="conflict-record",
                kind=ReconstructionReferenceKind.CANONICAL_DOMAIN_RECORD,
                record_id="market-snapshot:SPY:2026-07-25",
            ),
        ),
        retention=EvidenceRetentionRequirement(
            retain_until="2031-07-25T00:00:00Z",
            policy_id="enhanced-provenance-5y",
        ),
    )

    references = evidence_claim_references_from_packet(packet)
    parsed = evidence_claim_references_from_metadata(references.as_metadata())
    claim_reference = parsed.claim_references[0]

    assert claim_reference.conflicting_evidence_ids == ("evidence-conflict",)
    assert claim_reference.unresolved_conflicting_evidence_ids == ()
    assert claim_reference.reconstruction_reference_ids == (
        "workflow-node",
        "conflict-record",
    )


@pytest.mark.parametrize("tier", [RiskTier.ENHANCED, RiskTier.VIGILANT])
def test_material_claim_reference_without_support_fails_closed(tier: RiskTier) -> None:
    with pytest.raises(
        UnsupportedMaterialClaimError,
        match="lacks supporting evidence",
    ):
        EvidenceClaimReference(
            packet_id="packet-1",
            output_id="recommendation-output-1",
            claim_id="claim-unsupported",
            risk_tier=tier,
            supporting_evidence_ids=(),
            reconstruction_reference_ids=("workflow-node",),
        )


@pytest.mark.parametrize("tier", [RiskTier.ENHANCED, RiskTier.VIGILANT])
def test_material_claim_reference_without_reconstruction_fails_closed(
    tier: RiskTier,
) -> None:
    with pytest.raises(
        UnsupportedMaterialClaimError,
        match="lacks reconstruction references",
    ):
        EvidenceClaimReference(
            packet_id="packet-1",
            output_id="recommendation-output-1",
            claim_id="claim-unsupported",
            risk_tier=tier,
            supporting_evidence_ids=("evidence-1",),
            reconstruction_reference_ids=(),
        )


def _packet() -> DecisionEvidencePacket:
    return DecisionEvidencePacket(
        packet_id="packet-1",
        output_id="recommendation-output-1",
        authority=classify_risk_authority(authority_input_for_tier(RiskTier.ENHANCED)),
        claims=(
            MaterialClaim(
                claim_id="claim-1",
                text="SPY momentum improved across the supported lookback window.",
                evidence=ClaimEvidenceBinding(
                    supporting_evidence_ids=("evidence-1",),
                    uncertainty_ids=("uncertainty-1",),
                    limitation_ids=("limitation-1",),
                ),
            ),
        ),
        evidence=(
            EvidenceReference(
                evidence_id="evidence-1",
                kind=EvidenceReferenceKind.WORKFLOW_NODE_OUTPUT,
                reconstruction_reference_ids=("workflow-node",),
                summary="Runtime node output supporting the material claim.",
            ),
        ),
        reconstruction_references=(
            ReconstructionReference(
                reference_id="workflow-node",
                kind=ReconstructionReferenceKind.WORKFLOW_NODE_OUTPUT,
                record_id="run-1:node:market-analysis",
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
