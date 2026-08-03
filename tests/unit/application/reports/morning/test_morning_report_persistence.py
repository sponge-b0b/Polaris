from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

import pytest

from application.decision_evidence import (
    DecisionEvidenceClaimBindingService,
    ReportClaimEvidenceBindingTarget,
)
from application.governance import (
    GovernanceReviewApprovalState,
    GovernedOutputReleaseDecision,
    GovernedOutputReleaseRequest,
)
from application.reports import MorningReportMarkdownRenderer
from application.reports.authority import ReportAuthorityViolationError
from application.reports.morning_report_models import (
    MorningReportDocument,
    ReportBullet,
    ReportMetric,
    ReportPublicationReview,
    ReportSection,
)
from application.reports.morning_report_persistence import (
    MorningReportPersistenceMapper,
    MorningReportPersistenceService,
    ReportArtifactReference,
)
from core.storage.persistence.governance_audit import (
    AutomatedDecisionEvidenceReference,
    AutomatedDecisionSubject,
)
from core.storage.persistence.reports import (
    ReportArtifactRecord,
    ReportClaimEvidenceLinkRecord,
    ReportPersistenceBundle,
    ReportPersistenceResult,
    ReportPublicationRecord,
    ReportRecord,
    ReportSectionRecord,
    ReportVersionRecord,
)
from domain.authority import RiskTier
from domain.decision_evidence import (
    DECISION_EVIDENCE_CLAIM_REFERENCES_METADATA_KEY,
    ClaimMaterialityTier,
    DecisionEvidencePacketValidationError,
    EvidenceClaimReference,
)
from domain.llm import ReasoningTraceViolationError


class _FakeGovernedOutputReleaseService:
    def __init__(self, decision: GovernedOutputReleaseDecision) -> None:
        self.decision = decision
        self.requests: list[GovernedOutputReleaseRequest] = []

    async def evaluate_governed_output_release(
        self,
        request: GovernedOutputReleaseRequest,
    ) -> GovernedOutputReleaseDecision:
        self.requests.append(request)
        return self.decision


class FakeReportRepository:
    def __init__(
        self,
    ) -> None:
        self.report: ReportRecord | None = None
        self.sections: tuple[ReportSectionRecord, ...] = ()
        self.artifacts: tuple[ReportArtifactRecord, ...] = ()
        self.versions: tuple[ReportVersionRecord, ...] = ()
        self.publications: tuple[ReportPublicationRecord, ...] = ()
        self.claim_evidence_links: tuple[ReportClaimEvidenceLinkRecord, ...] = ()

    async def persist_report_bundle(
        self,
        bundle: ReportPersistenceBundle,
    ) -> ReportPersistenceResult:
        return await self.persist_report(
            bundle.report,
            sections=bundle.sections,
            artifacts=bundle.artifacts,
            versions=bundle.versions,
            publications=bundle.publications,
            claim_evidence_links=bundle.claim_evidence_links,
        )

    async def persist_report(
        self,
        report: ReportRecord,
        *,
        sections: Sequence[ReportSectionRecord] = (),
        artifacts: Sequence[ReportArtifactRecord] = (),
        versions: Sequence[ReportVersionRecord] = (),
        publications: Sequence[ReportPublicationRecord] = (),
        claim_evidence_links: Sequence[ReportClaimEvidenceLinkRecord] = (),
    ) -> ReportPersistenceResult:
        self.report = report
        self.sections = tuple(
            sections,
        )
        self.artifacts = tuple(
            artifacts,
        )
        self.versions = tuple(
            versions,
        )
        self.publications = tuple(
            publications,
        )
        self.claim_evidence_links = tuple(
            claim_evidence_links,
        )
        return ReportPersistenceResult.succeeded(
            report_id=report.report_id,
            records_persisted=1
            + len(
                self.sections,
            )
            + len(
                self.artifacts,
            )
            + len(
                self.claim_evidence_links,
            ),
        )

    async def get_report(
        self,
        report_id: str,
    ) -> ReportRecord | None:
        if self.report is not None and self.report.report_id == report_id:
            return self.report

        return None

    async def get_report_bundle(
        self,
        report_id: str,
    ) -> ReportPersistenceBundle | None:
        if self.report is None or self.report.report_id != report_id:
            return None

        return ReportPersistenceBundle(
            report=self.report,
            sections=self.sections,
            artifacts=self.artifacts,
            versions=self.versions,
            publications=self.publications,
            claim_evidence_links=self.claim_evidence_links,
        )

    async def get_version(
        self,
        version_id: str,
    ) -> ReportVersionRecord | None:
        for version in self.versions:
            if version.version_id == version_id:
                return version

        return None

    async def list_sections(
        self,
        report_id: str,
    ) -> Sequence[ReportSectionRecord]:
        if self.report is not None and self.report.report_id == report_id:
            return self.sections

        return ()

    async def list_artifacts(
        self,
        *,
        report_id: str | None = None,
        section_id: str | None = None,
    ) -> Sequence[ReportArtifactRecord]:
        return tuple(
            artifact
            for artifact in self.artifacts
            if (report_id is None or artifact.report_id == report_id)
            and (section_id is None or artifact.section_id == section_id)
        )

    async def list_versions(
        self,
        report_id: str,
    ) -> Sequence[ReportVersionRecord]:
        return tuple(
            version for version in self.versions if version.report_id == report_id
        )

    async def list_publications(
        self,
        *,
        report_id: str | None = None,
        version_id: str | None = None,
        publication_target: str | None = None,
        publication_status: str | None = None,
    ) -> Sequence[ReportPublicationRecord]:
        return tuple(
            publication
            for publication in self.publications
            if (report_id is None or publication.report_id == report_id)
            and (version_id is None or publication.version_id == version_id)
            and (
                publication_target is None
                or publication.publication_target == publication_target
            )
            and (
                publication_status is None
                or publication.publication_status == publication_status
            )
        )

    async def list_claim_evidence_links(
        self,
        *,
        report_id: str | None = None,
        section_id: str | None = None,
        packet_id: str | None = None,
        claim_target_id: str | None = None,
    ) -> Sequence[ReportClaimEvidenceLinkRecord]:
        return tuple(
            link
            for link in self.claim_evidence_links
            if (report_id is None or link.report_id == report_id)
            and (section_id is None or link.section_id == section_id)
            and (packet_id is None or link.packet_id == packet_id)
            and (claim_target_id is None or link.claim_target_id == claim_target_id)
        )


def test_morning_report_mapper_preserves_full_markdown_and_llm_text() -> None:
    document = _document()
    markdown = MorningReportMarkdownRenderer().render(
        document,
    )

    bundle = MorningReportPersistenceMapper().build_bundle(
        document,
        markdown_body=markdown,
        artifact_references=(
            ReportArtifactReference.from_path(
                Path("/tmp/morning_report.md"),
            ),
        ),
    )

    assert bundle.report.report_id == "morning_report:exec-full"
    assert bundle.report.markdown_body == markdown
    assert _long_response() in bundle.report.markdown_body
    executive_summary = cast(
        dict[str, Any],
        bundle.report.structured_payload["executive_summary"],
    )
    assert executive_summary["summary"] == _long_response()
    assert len(bundle.sections) == 7
    section_payload = cast(
        dict[str, Any],
        bundle.sections[0].content_payload,
    )
    assert section_payload["summary"] == _long_response()
    assert bundle.artifacts[0].artifact_uri == "/tmp/morning_report.md"
    assert bundle.artifacts[0].artifact_type == "markdown"
    assert bundle.artifacts[0].mime_type == "text/markdown"


@pytest.mark.asyncio
async def test_morning_report_persistence_service_persists_full_bundle() -> None:
    repository = FakeReportRepository()
    service = MorningReportPersistenceService(
        repository,
    )
    document = _document_with_contextual_claim_reference()
    markdown = MorningReportMarkdownRenderer().render(
        document,
    )

    result = await service.persist(
        document,
        markdown_body=markdown,
        artifact_references=(
            ReportArtifactReference(
                uri="/tmp/morning_report.json",
                artifact_type="json",
                mime_type="application/json",
            ),
        ),
    )

    assert result.success is True
    assert repository.report is not None
    assert repository.report.markdown_body == markdown
    assert repository.sections[0].summary == _long_response()
    assert repository.artifacts[0].artifact_type == "json"


@pytest.mark.asyncio
async def test_morning_report_persistence_blocks_missing_publication_review_state() -> (
    None
):
    repository = FakeReportRepository()
    gate = _FakeGovernedOutputReleaseService(
        GovernedOutputReleaseDecision(
            allowed=True,
            reason="should not be called without publication review metadata",
        )
    )
    service = MorningReportPersistenceService(
        repository,
        governed_output_release_service=gate,
    )
    document = _document_with_contextual_claim_reference()

    result = await service.persist(
        document,
        markdown_body=MorningReportMarkdownRenderer().render(document),
    )

    assert result.success is False
    assert "requires authoritative governance review metadata" in str(result.error)
    assert repository.report is None
    assert gate.requests == []


@pytest.mark.asyncio
async def test_morning_report_persistence_blocks_denied_publication() -> None:
    repository = FakeReportRepository()
    gate = _FakeGovernedOutputReleaseService(
        GovernedOutputReleaseDecision(
            allowed=False,
            reason=(
                "morning_report.persistence is blocked by governance review state "
                "review_denied."
            ),
            approval_state=GovernanceReviewApprovalState.REVIEW_DENIED,
            review_task_id="review-task-1",
        )
    )
    service = MorningReportPersistenceService(
        repository,
        governed_output_release_service=gate,
    )
    document = replace(
        _document_with_contextual_claim_reference(),
        publication_review=_publication_review(),
    )

    result = await service.persist(
        document,
        markdown_body=MorningReportMarkdownRenderer().render(document),
    )

    assert result.success is False
    assert "review_denied" in str(result.error)
    assert repository.report is None
    assert gate.requests == [
        GovernedOutputReleaseRequest(
            authority=gate.requests[0].authority,
            subject=AutomatedDecisionSubject("report", "morning_report:exec-full"),
            evidence=AutomatedDecisionEvidenceReference("packet-1", 1),
            review_scope="morning_report",
            requested_action="report_publication",
            boundary_name="morning_report.persistence",
            residual_risk_acceptance_required=True,
        )
    ]


@pytest.mark.asyncio
async def test_morning_report_persistence_persists_after_review_approval() -> None:
    repository = FakeReportRepository()
    gate = _FakeGovernedOutputReleaseService(
        GovernedOutputReleaseDecision(
            allowed=True,
            reason="governance review permits release",
            approval_state=GovernanceReviewApprovalState.REVIEW_APPROVED,
            review_task_id="review-task-1",
            residual_risk_acceptance_id="acceptance-1",
        )
    )
    service = MorningReportPersistenceService(
        repository,
        governed_output_release_service=gate,
    )
    document = replace(
        _document_with_contextual_claim_reference(),
        publication_review=_publication_review(),
    )

    result = await service.persist(
        document,
        markdown_body=MorningReportMarkdownRenderer().render(document),
    )

    assert result.success is True
    assert repository.report is not None
    assert gate.requests[0].residual_risk_acceptance_required is True


@pytest.mark.asyncio
async def test_morning_report_persistence_service_persists_claim_evidence_links() -> (
    None
):
    reference = EvidenceClaimReference(
        packet_id="packet-1",
        output_id="report-output-1",
        claim_id="claim-1",
        risk_tier=RiskTier.VIGILANT,
        supporting_evidence_ids=("evidence-1",),
        reconstruction_reference_ids=("workflow-node",),
        uncertainty_ids=("uncertainty-1",),
        limitation_ids=("limitation-1",),
    )
    document = _document_with_claim_reference(reference)
    repository = FakeReportRepository()
    binding_service = _FakeReportClaimBindingService(
        (
            ReportClaimEvidenceLinkRecord(
                link_id=(
                    "morning_report:exec-evidence:claim_evidence:"
                    "morning_report:exec-evidence:section:executive_summary:"
                    "morning_report:exec-evidence:section:executive_summary:"
                    "bullet:0:packet-1:claim-1"
                ),
                report_id="morning_report:exec-evidence",
                section_id="morning_report:exec-evidence:section:executive_summary",
                claim_target_id=(
                    "morning_report:exec-evidence:section:executive_summary:bullet:0"
                ),
                packet_id="packet-1",
                packet_claim_id="claim-1",
                risk_tier=RiskTier.VIGILANT,
                material=True,
                supporting_evidence_ids=("evidence-1",),
                reconstruction_reference_ids=("workflow-node",),
                uncertainty_ids=("uncertainty-1",),
                limitation_ids=("limitation-1",),
            ),
        )
    )
    service = MorningReportPersistenceService(
        repository,
        claim_binding_service=binding_service,
    )

    result = await service.persist(
        document,
        markdown_body=MorningReportMarkdownRenderer().render(document),
    )

    assert result.success is True
    assert len(repository.claim_evidence_links) == 1
    assert repository.claim_evidence_links[0].packet_id == "packet-1"
    assert repository.claim_evidence_links[0].uncertainty_ids == ("uncertainty-1",)
    assert repository.claim_evidence_links[0].limitation_ids == ("limitation-1",)
    assert binding_service.targets == (
        ReportClaimEvidenceBindingTarget(
            section_id="morning_report:exec-evidence:section:executive_summary",
            claim_target_id=(
                "morning_report:exec-evidence:section:executive_summary:bullet:0"
            ),
            claim_references=(reference,),
        ),
    )
    assert all(
        DECISION_EVIDENCE_CLAIM_REFERENCES_METADATA_KEY not in section.metadata
        for section in repository.sections
    )


@pytest.mark.asyncio
async def test_morning_report_fails_closed_without_claim_audit_treatment(
    caplog: pytest.LogCaptureFixture,
) -> None:
    document = _document()
    repository = FakeReportRepository()
    service = MorningReportPersistenceService(repository)

    with caplog.at_level(
        logging.WARNING,
        logger="application.reports.morning_report_persistence",
    ):
        result = await service.persist(
            document,
            markdown_body=MorningReportMarkdownRenderer().render(document),
        )

    assert result.success is False
    assert "no explicit decision-evidence claim audit treatment" in str(result.error)
    assert "canonical decision-evidence packet provenance" in str(result.error)
    assert repository.report is None
    assert any(
        "Morning report claim-evidence binding failed closed." in record.message
        for record in caplog.records
    )


@pytest.mark.asyncio
async def test_morning_report_fails_closed_for_packet_validation_error() -> None:
    reference = _material_claim_reference()
    document = _document_with_claim_reference(reference)
    repository = FakeReportRepository()
    service = MorningReportPersistenceService(
        repository,
        claim_binding_service=_FailingReportClaimBindingService(
            DecisionEvidencePacketValidationError("stale packet provenance"),
        ),
    )

    result = await service.persist(
        document,
        markdown_body=MorningReportMarkdownRenderer().render(document),
    )

    assert result.success is False
    assert "stale packet provenance" in str(result.error)
    assert repository.report is None


@pytest.mark.asyncio
async def test_morning_report_fails_closed_for_missing_material_binding() -> None:
    reference = _material_claim_reference()
    document = _document_with_claim_reference(reference)
    repository = FakeReportRepository()
    service = MorningReportPersistenceService(
        repository,
        claim_binding_service=_FakeReportClaimBindingService(()),
    )

    result = await service.persist(
        document,
        markdown_body=MorningReportMarkdownRenderer().render(document),
    )

    assert result.success is False
    assert "material claim 'claim-1'" in str(result.error)
    assert "lacks required decision-evidence packet binding" in str(result.error)
    assert repository.report is None


@pytest.mark.asyncio
async def test_morning_report_fails_closed_for_invalid_material_binding() -> None:
    reference = _material_claim_reference()
    document = _document_with_claim_reference(reference)
    repository = FakeReportRepository()
    service = MorningReportPersistenceService(
        repository,
        claim_binding_service=_FakeReportClaimBindingService(
            (
                _report_claim_link(
                    packet_id="packet-substituted",
                    packet_claim_id="claim-substituted",
                ),
            )
        ),
    )

    result = await service.persist(
        document,
        markdown_body=MorningReportMarkdownRenderer().render(document),
    )

    assert result.success is False
    assert "unexpected material decision-evidence packet binding" in str(result.error)
    assert repository.report is None


@pytest.mark.asyncio
async def test_morning_report_fails_closed_for_substituted_material_link() -> None:
    reference = _material_claim_reference()
    document = _document_with_claim_reference(reference)
    repository = FakeReportRepository()
    service = MorningReportPersistenceService(
        repository,
        claim_binding_service=_FakeReportClaimBindingService(
            (
                replace(
                    _report_claim_link(),
                    supporting_evidence_ids=("evidence-substituted",),
                ),
            )
        ),
    )

    result = await service.persist(
        document,
        markdown_body=MorningReportMarkdownRenderer().render(document),
    )

    assert result.success is False
    assert (
        "supporting evidence does not match required canonical claim reference"
        in str(result.error)
    )
    assert repository.report is None


@pytest.mark.asyncio
async def test_morning_report_allows_contextual_claim_without_binding() -> None:
    reference = EvidenceClaimReference(
        packet_id="packet-context",
        output_id="report-output-context",
        claim_id="claim-context",
        risk_tier=RiskTier.VIGILANT,
        materiality=ClaimMaterialityTier.CONTEXTUAL,
        supporting_evidence_ids=(),
        reconstruction_reference_ids=(),
    )
    document = _document_with_claim_reference(reference)
    repository = FakeReportRepository()
    service = MorningReportPersistenceService(repository)

    result = await service.persist(
        document,
        markdown_body=MorningReportMarkdownRenderer().render(document),
    )

    assert result.success is True
    assert repository.report is not None
    assert repository.claim_evidence_links == ()
    assert DECISION_EVIDENCE_CLAIM_REFERENCES_METADATA_KEY not in (
        repository.sections[0].metadata
    )
    assert "packet-context" not in str(repository.sections[0].metadata)
    assert "claim-context" not in str(repository.sections[0].metadata)


def test_mapper_attaches_authority_metadata_to_presentation_records() -> None:
    document = _document()
    markdown = MorningReportMarkdownRenderer().render(
        document,
    )

    bundle = MorningReportPersistenceMapper().build_bundle(
        document,
        markdown_body=markdown,
        artifact_references=(
            ReportArtifactReference.from_path(
                Path("/tmp/morning_report.md"),
            ),
        ),
    )

    risk_authority = cast(
        dict[str, Any],
        bundle.report.metadata["risk_authority"],
    )
    assert risk_authority["risk_tier"] == "vigilant"
    assert risk_authority["content_type"] == "report"
    assert risk_authority["authority_effect"] == "advisory_context"
    assert risk_authority["canonical_owner"] == "report_service"
    assert risk_authority["source_of_truth"] == "presentation_output"
    assert risk_authority["intended_sink"] == "report"
    assert risk_authority["gate_profile"] == "vigilant_decision_evidence"
    assert risk_authority["capital_relevant"] is True
    assert risk_authority["externally_visible"] is True
    assert bundle.report.metadata["report_authority_failure_mode"] == "none"
    assert bundle.report.metadata["report_authority_fail_closed"] is False
    assert bundle.report.metadata["report_authority_boundary"] == (
        "presentation_report_is_decision_support_not_portfolio_strategy_governance_"
        "readiness_or_execution_authority"
    )
    payload_boundary = cast(
        dict[str, Any],
        bundle.report.structured_payload["authority_boundary"],
    )
    assert payload_boundary["risk_authority"] == risk_authority
    assert bundle.sections[0].metadata["risk_authority"] == risk_authority
    assert bundle.artifacts[0].metadata["risk_authority"] == risk_authority


def test_mapper_keeps_report_claim_refs_out_of_metadata_blobs() -> None:
    reference = EvidenceClaimReference(
        packet_id="packet-1",
        output_id="report-output-1",
        claim_id="claim-1",
        risk_tier=RiskTier.VIGILANT,
        supporting_evidence_ids=("evidence-1",),
        reconstruction_reference_ids=("workflow-node",),
        uncertainty_ids=("uncertainty-1",),
        limitation_ids=("limitation-1",),
    )
    section = ReportSection(
        title="Executive Summary",
        summary="Market risk remains elevated based on canonical evidence.",
        bullets=(
            ReportBullet(
                text="Maintain discipline while monitoring catalysts.",
                label="Posture",
                claim_references=(reference,),
            ),
        ),
    )
    document = MorningReportDocument(
        title="Polaris Morning Financial Report",
        subtitle="Decision-support report for SPY",
        symbol="SPY",
        execution_id="exec-evidence",
        generated_at="2026-05-30T13:30:00Z",
        status="Succeeded",
        executive_summary=section,
        portfolio_snapshot=ReportSection.unavailable("Portfolio Snapshot"),
        macro_backdrop=ReportSection.unavailable("Macro / Fundamental Backdrop"),
        technical_setup=ReportSection.unavailable("Technical Setup"),
        news_sentiment=ReportSection.unavailable("News & Sentiment"),
        risk_assessment=ReportSection.unavailable("Risk Assessment"),
        recommended_action_plan=ReportSection.unavailable("Recommended Action Plan"),
    )

    bundle = MorningReportPersistenceMapper().build_bundle(
        document,
        markdown_body=MorningReportMarkdownRenderer().render(document),
    )

    metadata = bundle.sections[0].metadata
    assert metadata["section_key"] == "executive_summary"
    assert DECISION_EVIDENCE_CLAIM_REFERENCES_METADATA_KEY not in metadata
    serialized_metadata = str(metadata)
    assert "packet-1" not in serialized_metadata
    assert "claim-1" not in serialized_metadata
    assert "canonical evidence summary" not in serialized_metadata
    assert "raw_payload" not in serialized_metadata


def test_morning_report_mapper_fails_closed_on_unsupported_capital_advice() -> None:
    section = ReportSection(
        title="Executive Summary",
        summary="Buy 100 shares of SPY at the open.",
    )
    document = MorningReportDocument(
        title="Polaris Morning Financial Report",
        subtitle="Decision-support report for SPY",
        symbol="SPY",
        execution_id="exec-capital-advice",
        generated_at="2026-05-30T13:30:00Z",
        status="Succeeded",
        executive_summary=section,
        portfolio_snapshot=ReportSection.unavailable("Portfolio Snapshot"),
        macro_backdrop=ReportSection.unavailable("Macro / Fundamental Backdrop"),
        technical_setup=ReportSection.unavailable("Technical Setup"),
        news_sentiment=ReportSection.unavailable("News & Sentiment"),
        risk_assessment=ReportSection.unavailable("Risk Assessment"),
        recommended_action_plan=ReportSection.unavailable("Recommended Action Plan"),
    )

    with pytest.raises(
        ReportAuthorityViolationError,
        match="unsupported_capital_advice",
    ):
        MorningReportPersistenceMapper().build_bundle(
            document,
            markdown_body="# Published report\n\nBuy 100 shares of SPY.",
        )


class _FailingReportClaimBindingService(DecisionEvidenceClaimBindingService):
    def __init__(self, error: Exception) -> None:
        self.error = error

    async def bind_report_claims(
        self,
        report_id: str,
        targets: Sequence[ReportClaimEvidenceBindingTarget],
    ) -> tuple[ReportClaimEvidenceLinkRecord, ...]:
        raise self.error


class _FakeReportClaimBindingService(DecisionEvidenceClaimBindingService):
    def __init__(
        self,
        links: tuple[ReportClaimEvidenceLinkRecord, ...],
    ) -> None:
        self.links = links
        self.targets: tuple[ReportClaimEvidenceBindingTarget, ...] = ()

    async def bind_report_claims(
        self,
        report_id: str,
        targets: Sequence[ReportClaimEvidenceBindingTarget],
    ) -> tuple[ReportClaimEvidenceLinkRecord, ...]:
        self.targets = tuple(targets)
        return self.links


def _publication_review() -> ReportPublicationReview:
    return ReportPublicationReview(
        subject=AutomatedDecisionSubject("report", "morning_report:exec-full"),
        evidence=AutomatedDecisionEvidenceReference("packet-1", 1),
        review_scope="morning_report",
        requested_action="report_publication",
        residual_risk_acceptance_required=True,
    )


def _contextual_claim_reference() -> EvidenceClaimReference:
    return EvidenceClaimReference(
        packet_id="packet-context",
        output_id="report-output-context",
        claim_id="claim-context",
        risk_tier=RiskTier.VIGILANT,
        materiality=ClaimMaterialityTier.CONTEXTUAL,
        supporting_evidence_ids=(),
        reconstruction_reference_ids=(),
    )


def _document_with_contextual_claim_reference() -> MorningReportDocument:
    document = _document()
    return replace(
        document,
        executive_summary=replace(
            document.executive_summary,
            bullets=(
                ReportBullet(
                    text="Maintain discipline while monitoring catalysts.",
                    label="Posture",
                    claim_references=(_contextual_claim_reference(),),
                ),
            ),
        ),
    )


def _material_claim_reference() -> EvidenceClaimReference:
    return EvidenceClaimReference(
        packet_id="packet-1",
        output_id="report-output-1",
        claim_id="claim-1",
        risk_tier=RiskTier.VIGILANT,
        supporting_evidence_ids=("evidence-1",),
        reconstruction_reference_ids=("workflow-node",),
        uncertainty_ids=("uncertainty-1",),
        limitation_ids=("limitation-1",),
    )


def _report_claim_link(
    *,
    packet_id: str = "packet-1",
    packet_claim_id: str = "claim-1",
) -> ReportClaimEvidenceLinkRecord:
    return ReportClaimEvidenceLinkRecord(
        link_id=(
            "morning_report:exec-evidence:claim_evidence:"
            "morning_report:exec-evidence:section:executive_summary:"
            "morning_report:exec-evidence:section:executive_summary:"
            f"bullet:0:{packet_id}:{packet_claim_id}"
        ),
        report_id="morning_report:exec-evidence",
        section_id="morning_report:exec-evidence:section:executive_summary",
        claim_target_id=(
            "morning_report:exec-evidence:section:executive_summary:bullet:0"
        ),
        packet_id=packet_id,
        packet_claim_id=packet_claim_id,
        risk_tier=RiskTier.VIGILANT,
        material=True,
        supporting_evidence_ids=("evidence-1",),
        reconstruction_reference_ids=("workflow-node",),
        uncertainty_ids=("uncertainty-1",),
        limitation_ids=("limitation-1",),
    )


def _document_with_claim_reference(
    reference: EvidenceClaimReference,
) -> MorningReportDocument:
    section = ReportSection(
        title="Executive Summary",
        summary="Market risk remains elevated based on canonical evidence.",
        bullets=(
            ReportBullet(
                text="Maintain discipline while monitoring catalysts.",
                label="Posture",
                claim_references=(reference,),
            ),
        ),
    )
    return MorningReportDocument(
        title="Polaris Morning Financial Report",
        subtitle="Decision-support report for SPY",
        symbol="SPY",
        execution_id="exec-evidence",
        generated_at="2026-05-30T13:30:00Z",
        status="Succeeded",
        executive_summary=section,
        portfolio_snapshot=ReportSection.unavailable("Portfolio Snapshot"),
        macro_backdrop=ReportSection.unavailable("Macro / Fundamental Backdrop"),
        technical_setup=ReportSection.unavailable("Technical Setup"),
        news_sentiment=ReportSection.unavailable("News & Sentiment"),
        risk_assessment=ReportSection.unavailable("Risk Assessment"),
        recommended_action_plan=ReportSection.unavailable("Recommended Action Plan"),
    )


def _document() -> MorningReportDocument:
    section = ReportSection(
        title="Executive Summary",
        summary=_long_response(),
        metrics=(
            ReportMetric(
                label="Confidence",
                value="82.0%",
                raw_value=0.82,
            ),
        ),
        bullets=(
            ReportBullet(
                text="Maintain discipline while monitoring catalysts.",
                label="Posture",
            ),
        ),
    )
    return MorningReportDocument(
        title="Polaris Morning Financial Report",
        subtitle="Decision-support report for SPY",
        symbol="SPY",
        execution_id="exec-full",
        generated_at="2026-05-30T13:30:00Z",
        status="Succeeded",
        executive_summary=section,
        portfolio_snapshot=ReportSection.unavailable(
            "Portfolio Snapshot",
        ),
        macro_backdrop=ReportSection.unavailable(
            "Macro / Fundamental Backdrop",
        ),
        technical_setup=ReportSection.unavailable(
            "Technical Setup",
        ),
        news_sentiment=ReportSection.unavailable(
            "News & Sentiment",
        ),
        risk_assessment=ReportSection.unavailable(
            "Risk Assessment",
        ),
        recommended_action_plan=ReportSection.unavailable(
            "Recommended Action Plan",
        ),
    )


def _long_response() -> str:
    return "FULL_LLM_RESPONSE_START " + ("complete response segment " * 200) + "END"


def test_morning_report_mapper_sanitizes_report_publication_payloads() -> None:
    document = _document_with_reasoning_trace()

    bundle = MorningReportPersistenceMapper().build_bundle(
        document,
        markdown_body="<think>private report reasoning</think>\n# Published report",
    )

    assert bundle.report.markdown_body == "# Published report"
    executive_summary = cast(
        dict[str, Any],
        bundle.report.structured_payload["executive_summary"],
    )
    assert executive_summary["summary"] == "Visible executive summary."
    assert "chain_of_thought" not in executive_summary
    section_payload = cast(dict[str, Any], bundle.sections[0].content_payload)
    assert section_payload["summary"] == "Visible executive summary."
    assert bundle.sections[0].summary == "Visible executive summary."
    serialized = str(bundle.report.structured_payload) + str(
        bundle.sections[0].content_payload
    )
    assert "private report reasoning" not in bundle.report.markdown_body
    assert "private section reasoning" not in serialized
    assert "private bullet reasoning" not in serialized


def test_morning_report_mapper_rejects_unsafe_report_publication_payloads() -> None:
    with pytest.raises(
        ReasoningTraceViolationError,
        match="morning_report.persistence",
    ):
        MorningReportPersistenceMapper().build_bundle(
            _document(),
            markdown_body="<think>private report reasoning without a closing tag",
        )


def _document_with_reasoning_trace() -> MorningReportDocument:
    section = ReportSection(
        title="Executive Summary",
        summary="<think>private section reasoning</think>\nVisible executive summary.",
        bullets=(
            ReportBullet(
                text="```reasoning\nprivate bullet reasoning\n```\nVisible bullet.",
                label="Posture",
            ),
        ),
    )
    return MorningReportDocument(
        title="Polaris Morning Financial Report",
        subtitle="Decision-support report for SPY",
        symbol="SPY",
        execution_id="exec-safe",
        generated_at="2026-05-30T13:30:00Z",
        status="Succeeded",
        executive_summary=section,
        portfolio_snapshot=ReportSection.unavailable("Portfolio Snapshot"),
        macro_backdrop=ReportSection.unavailable("Macro / Fundamental Backdrop"),
        technical_setup=ReportSection.unavailable("Technical Setup"),
        news_sentiment=ReportSection.unavailable("News & Sentiment"),
        risk_assessment=ReportSection.unavailable("Risk Assessment"),
        recommended_action_plan=ReportSection.unavailable("Recommended Action Plan"),
    )
