from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import replace
from typing import Any

import pytest

from application.decision_evidence import (
    ClaimEvidenceBindingError,
    DecisionEvidenceClaimBindingService,
    ReportClaimEvidenceBindingTarget,
    StaleDecisionEvidenceSourceError,
)
from application.decision_evidence.claim_binding import (
    RecommendationClaimEvidenceBindingTarget,
)
from core.storage.persistence.recommendations import (
    RecommendationClaimEvidenceLinkRecord,
)
from core.storage.persistence.reports import ReportClaimEvidenceLinkRecord
from domain.authority import RiskTier, SourceOfTruthCategory, classify_risk_authority
from domain.decision_evidence import (
    ClaimEvidenceBinding,
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
    evidence_claim_references_from_packet,
)
from tests.helpers.risk_authority_examples import authority_input_for_tier


@pytest.mark.asyncio
async def test_binds_supported_report_claims_to_durable_links() -> None:
    packet = _packet()
    references = evidence_claim_references_from_packet(packet).claim_references
    service = DecisionEvidenceClaimBindingService(_FakePacketService(packet))

    links = await service.bind_report_claims(
        report_id="report-1",
        targets=(
            ReportClaimEvidenceBindingTarget(
                section_id="section-1",
                claim_target_id="section-1:bullet:0",
                claim_references=references,
            ),
        ),
    )

    assert len(links) == 1
    link = links[0]
    assert isinstance(link, ReportClaimEvidenceLinkRecord)
    assert link.report_id == "report-1"
    assert link.section_id == "section-1"
    assert link.claim_target_id == "section-1:bullet:0"
    assert link.packet_id == "packet-1"
    assert link.packet_claim_id == "claim-1"
    assert link.risk_tier is RiskTier.ENHANCED
    assert link.supporting_evidence_ids == ("evidence-1",)
    assert link.reconstruction_reference_ids == ("workflow-node",)
    assert link.uncertainty_ids == ("uncertainty-1",)
    assert link.limitation_ids == ("limitation-1",)


@pytest.mark.asyncio
async def test_binds_supported_recommendation_claims_to_durable_links() -> None:
    packet = _packet()
    references = evidence_claim_references_from_packet(packet).claim_references
    service = DecisionEvidenceClaimBindingService(_FakePacketService(packet))

    links = await service.bind_recommendation_claims(
        recommendation_id="recommendation-1",
        targets=(
            RecommendationClaimEvidenceBindingTarget(
                rationale_id="rationale-1",
                claim_target_id="rationale-1:claim:claim-1",
                claim_references=references,
            ),
        ),
    )

    assert len(links) == 1
    link = links[0]
    assert isinstance(link, RecommendationClaimEvidenceLinkRecord)
    assert link.recommendation_id == "recommendation-1"
    assert link.rationale_id == "rationale-1"
    assert link.claim_target_id == "rationale-1:claim:claim-1"
    assert link.packet_id == "packet-1"
    assert link.packet_claim_id == "claim-1"
    assert link.risk_tier is RiskTier.ENHANCED
    assert link.supporting_evidence_ids == ("evidence-1",)
    assert link.reconstruction_reference_ids == ("workflow-node",)
    assert link.uncertainty_ids == ("uncertainty-1",)
    assert link.limitation_ids == ("limitation-1",)


@pytest.mark.asyncio
async def test_report_and_recommendation_claims_use_shared_binding_path() -> None:
    packet = _packet()
    references = evidence_claim_references_from_packet(packet).claim_references
    packet_service = _FakePacketService(packet)
    service = _SharedBindingPathSpy(packet_service)
    report_targets = (
        ReportClaimEvidenceBindingTarget(
            section_id="section-1",
            claim_target_id="section-1:bullet:0",
            claim_references=references,
        ),
    )
    recommendation_targets = (
        RecommendationClaimEvidenceBindingTarget(
            rationale_id="rationale-1",
            claim_target_id="rationale-1:claim:claim-1",
            claim_references=references,
        ),
    )

    report_links = await service.bind_report_claims(
        report_id="report-1",
        targets=report_targets,
    )
    recommendation_links = await service.bind_recommendation_claims(
        recommendation_id="recommendation-1",
        targets=recommendation_targets,
    )

    assert isinstance(report_links[0], ReportClaimEvidenceLinkRecord)
    assert isinstance(recommendation_links[0], RecommendationClaimEvidenceLinkRecord)
    assert service.shared_binding_target_ids == [
        ("section-1:bullet:0",),
        ("rationale-1:claim:claim-1",),
    ]
    assert packet_service.calls == ["packet-1", "packet-1"]


@pytest.mark.asyncio
async def test_binding_fails_closed_for_stale_canonical_evidence() -> None:
    packet = _packet()
    references = evidence_claim_references_from_packet(packet).claim_references
    service = DecisionEvidenceClaimBindingService(
        _FailingPacketService(StaleDecisionEvidenceSourceError("stale source"))
    )

    with pytest.raises(StaleDecisionEvidenceSourceError, match="stale source"):
        await service.bind_report_claims(
            report_id="report-1",
            targets=(
                ReportClaimEvidenceBindingTarget(
                    section_id="section-1",
                    claim_target_id="section-1:claim:claim-1",
                    claim_references=references,
                ),
            ),
        )


@pytest.mark.asyncio
async def test_binding_fails_closed_for_substituted_support_reference() -> None:
    packet = _packet()
    reference = replace(
        evidence_claim_references_from_packet(packet).claim_references[0],
        supporting_evidence_ids=("evidence-substituted",),
    )
    service = DecisionEvidenceClaimBindingService(_FakePacketService(packet))

    with pytest.raises(ClaimEvidenceBindingError, match="supporting evidence"):
        await service.bind_report_claims(
            report_id="report-1",
            targets=(
                ReportClaimEvidenceBindingTarget(
                    section_id="section-1",
                    claim_target_id="section-1:claim:claim-1",
                    claim_references=(reference,),
                ),
            ),
        )


@pytest.mark.asyncio
async def test_binding_fails_closed_for_substituted_reconstruction_reference() -> None:
    packet = _packet()
    reference = replace(
        evidence_claim_references_from_packet(packet).claim_references[0],
        reconstruction_reference_ids=("workflow-node-substituted",),
    )
    service = DecisionEvidenceClaimBindingService(_FakePacketService(packet))

    with pytest.raises(ClaimEvidenceBindingError, match="reconstruction"):
        await service.bind_recommendation_claims(
            recommendation_id="recommendation-1",
            targets=(
                RecommendationClaimEvidenceBindingTarget(
                    rationale_id="rationale-1",
                    claim_target_id="rationale-1:claim:claim-1",
                    claim_references=(reference,),
                ),
            ),
        )


def _packet() -> DecisionEvidencePacket:
    return DecisionEvidencePacket(
        packet_id="packet-1",
        output_id="node-output-trade",
        authority=classify_risk_authority(authority_input_for_tier(RiskTier.ENHANCED)),
        claims=(
            MaterialClaim(
                claim_id="claim-1",
                text="Constructive setup with contained risk.",
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
                summary="Persisted trade recommendation node output.",
                source_of_truth=SourceOfTruthCategory.RUNTIME_EVIDENCE,
            ),
        ),
        reconstruction_references=(
            ReconstructionReference(
                reference_id="workflow-node",
                kind=ReconstructionReferenceKind.WORKFLOW_NODE_OUTPUT,
                record_id="node-output-trade",
                source_of_truth=SourceOfTruthCategory.RUNTIME_EVIDENCE,
            ),
        ),
        uncertainties=(
            EvidenceUncertainty(
                uncertainty_id="uncertainty-1",
                summary="Volatility can change intraday.",
                evidence_ids=("evidence-1",),
            ),
        ),
        limitations=(
            EvidenceLimitation(
                limitation_id="limitation-1",
                summary="Report is decision support only.",
                evidence_ids=("evidence-1",),
            ),
        ),
        retention=EvidenceRetentionRequirement(
            retain_until="2031-07-25T00:00:00Z",
            policy_id="enhanced-provenance-5y",
        ),
        workflow_name="morning_report",
        workflow_definition_fingerprint="test-definition-fingerprint",
        execution_id="exec-1",
    )


class _FakePacketService:
    def __init__(self, packet: DecisionEvidencePacket) -> None:
        self.packet = packet
        self.calls: list[str] = []

    async def reconstruct_packet(self, packet_id: str) -> DecisionEvidencePacket:
        self.calls.append(packet_id)
        return self.packet


class _SharedBindingPathSpy(DecisionEvidenceClaimBindingService):
    def __init__(self, packet_service: _FakePacketService) -> None:
        super().__init__(packet_service)
        self.shared_binding_target_ids: list[tuple[str, ...]] = []

    async def _bind_claim_links(
        self,
        *,
        targets: Sequence[Any],
        make_link: Callable[[Any, EvidenceClaimReference], Any],
    ) -> tuple[Any, ...]:
        self.shared_binding_target_ids.append(
            tuple(target.claim_target_id for target in targets)
        )
        return await super()._bind_claim_links(
            targets=targets,
            make_link=make_link,
        )


class _FailingPacketService:
    def __init__(self, exc: Exception) -> None:
        self.exc = exc

    async def reconstruct_packet(self, packet_id: str) -> DecisionEvidencePacket:
        raise self.exc
