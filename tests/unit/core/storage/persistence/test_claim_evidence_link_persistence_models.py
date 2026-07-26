from __future__ import annotations

import pytest

from core.storage.persistence.recommendations import (
    RecommendationClaimEvidenceLinkRecord,
)
from core.storage.persistence.reports import ReportClaimEvidenceLinkRecord
from domain.authority import RiskTier


def test_report_claim_evidence_link_preserves_packet_identifiers() -> None:
    link = ReportClaimEvidenceLinkRecord(
        link_id="report-link-1",
        report_id="morning_report:exec-1",
        section_id="morning_report:exec-1:section:strategy",
        claim_target_id="report-claim:strategy-posture",
        packet_id="packet-1",
        packet_claim_id="claim-1",
        risk_tier=RiskTier.ENHANCED,
        material=True,
        supporting_evidence_ids=("evidence-synthesis",),
        reconstruction_reference_ids=(
            "evidence-synthesis:completed-run",
            "evidence-synthesis:node-output",
        ),
        uncertainty_ids=("uncertainty-1",),
        limitation_ids=("limitation-1",),
    )

    assert link.report_id == "morning_report:exec-1"
    assert link.section_id == "morning_report:exec-1:section:strategy"
    assert link.claim_target_id == "report-claim:strategy-posture"
    assert link.packet_id == "packet-1"
    assert link.packet_claim_id == "claim-1"
    assert link.risk_tier is RiskTier.ENHANCED
    assert link.supporting_evidence_ids == ("evidence-synthesis",)
    assert link.reconstruction_reference_ids == (
        "evidence-synthesis:completed-run",
        "evidence-synthesis:node-output",
    )
    assert not hasattr(link, "metadata")


def test_recommendation_claim_link_preserves_rationale_target() -> None:
    link = RecommendationClaimEvidenceLinkRecord(
        link_id="recommendation-link-1",
        recommendation_id="rec-1",
        rationale_id="rec-1:rationale:primary",
        claim_target_id="rationale-claim:momentum",
        packet_id="packet-1",
        packet_claim_id="claim-1",
        risk_tier="vigilant",
        material=True,
        supporting_evidence_ids=("evidence-synthesis",),
        reconstruction_reference_ids=("evidence-synthesis:node-output",),
    )

    assert link.recommendation_id == "rec-1"
    assert link.rationale_id == "rec-1:rationale:primary"
    assert link.claim_target_id == "rationale-claim:momentum"
    assert link.packet_id == "packet-1"
    assert link.packet_claim_id == "claim-1"
    assert link.risk_tier is RiskTier.VIGILANT


@pytest.mark.parametrize(
    "record_factory",
    [
        lambda: ReportClaimEvidenceLinkRecord(
            link_id="report-link-1",
            report_id="morning_report:exec-1",
            section_id="morning_report:exec-1:section:strategy",
            claim_target_id="report-claim:strategy-posture",
            packet_id="packet-1",
            packet_claim_id="claim-1",
            risk_tier=RiskTier.ENHANCED,
            material=True,
            supporting_evidence_ids=(),
            reconstruction_reference_ids=("evidence-synthesis:node-output",),
        ),
        lambda: RecommendationClaimEvidenceLinkRecord(
            link_id="recommendation-link-1",
            recommendation_id="rec-1",
            rationale_id="rec-1:rationale:primary",
            claim_target_id="rationale-claim:momentum",
            packet_id="packet-1",
            packet_claim_id="claim-1",
            risk_tier=RiskTier.VIGILANT,
            material=True,
            supporting_evidence_ids=("evidence-synthesis",),
            reconstruction_reference_ids=(),
        ),
    ],
)
def test_material_enhanced_and_vigilant_links_require_support_and_reconstruction(
    record_factory: object,
) -> None:
    with pytest.raises(ValueError):
        record_factory()
