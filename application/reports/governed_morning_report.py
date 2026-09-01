from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from application.decision_evidence.claim_binding import (
    ClaimEvidenceBindingError,
    DecisionEvidenceClaimBindingService,
)
from application.decision_evidence.persistence import (
    DecisionEvidencePacketReconstructionError,
)
from application.evaluations.risk_authority_gate import OutputGovernanceGateEvidence
from application.governance import (
    GovernedOutputReleaseDecision,
    requires_governed_output_release_review,
)
from application.presentation.evidence import presentation_gate_evidence
from application.presentation.governed_result import GovernedPresentationResult
from application.presentation.sink_decision import PresentationSinkDecisionService
from application.reports.authority import (
    ReportAuthorityViolationError,
    ensure_report_publication_authority,
)
from application.reports.morning_report_models import MorningReportDocument
from application.reports.morning_report_persistence import (
    GovernedOutputReleaseService,
    MorningReportPersistenceMapper,
    ReportArtifactReference,
    _bind_report_claim_evidence,
    _document_text_values,
    _missing_publication_release_service_decision,
    _presentation_failure_reason,
    _publication_text,
    _report_publication_release_request,
)
from core.storage.persistence.reports import (
    ReportClaimEvidenceLinkRecord,
    ReportPersistenceRepository,
    ReportPersistenceResult,
    new_report_id,
)
from domain.decision_evidence import (
    DecisionEvidencePacketValidationError,
    EvidenceClaimReference,
)
from domain.llm import ReasoningTraceViolationError


@dataclass(frozen=True, slots=True)
class MorningReportPresentationPreparation:
    """Pre-render report result plus application-validated persistence links."""

    result: GovernedPresentationResult[MorningReportDocument]
    claim_evidence_links: tuple[ReportClaimEvidenceLinkRecord, ...] = ()


class MorningReportPersistenceService:
    """Govern report presentation before rendering, then persist the same result."""

    def __init__(
        self,
        repository: ReportPersistenceRepository,
        *,
        mapper: MorningReportPersistenceMapper | None = None,
        claim_binding_service: DecisionEvidenceClaimBindingService | None = None,
        governed_output_release_service: GovernedOutputReleaseService | None = None,
        presentation_sink_decision_service: (
            PresentationSinkDecisionService | None
        ) = None,
    ) -> None:
        self._repository = repository
        self._mapper = mapper or MorningReportPersistenceMapper()
        self._claim_binding_service = claim_binding_service
        self._governed_output_release_service = governed_output_release_service
        self._presentation_sink_decision_service = (
            presentation_sink_decision_service or PresentationSinkDecisionService()
        )

    async def prepare_presentation(
        self,
        document: MorningReportDocument,
    ) -> MorningReportPresentationPreparation:
        """Bind authority/evidence/governance before any renderer receives claims."""

        try:
            _validate_pre_render_document(document)
        except (ReportAuthorityViolationError, ReasoningTraceViolationError) as exc:
            decision = await self._presentation_sink_decision_service.evaluate(
                document.authority,
                expected_authority_metadata=document.authority,
                limitations=document.authority_limitations,
                blocking_reasons=(str(exc),),
            )
            return MorningReportPresentationPreparation(
                result=GovernedPresentationResult(payload=None, decision=decision)
            )

        report_id = new_report_id("morning_report", document.execution_id)
        try:
            claim_binding = await _bind_report_claim_evidence(
                self._claim_binding_service,
                report_id=report_id,
                document=document,
            )
        except (
            ClaimEvidenceBindingError,
            DecisionEvidencePacketReconstructionError,
            DecisionEvidencePacketValidationError,
        ) as exc:
            decision = await self._presentation_sink_decision_service.evaluate(
                document.authority,
                expected_authority_metadata=document.authority,
                limitations=document.authority_limitations,
                withholding_reasons=(str(exc),),
            )
            return MorningReportPresentationPreparation(
                result=GovernedPresentationResult(payload=None, decision=decision)
            )

        (
            output_governance_evidence,
            withholding_reasons,
        ) = await self._presentation_governance_evidence(
            document,
            claim_references=claim_binding.validated_claim_references,
        )
        evidence = presentation_gate_evidence(
            packets=claim_binding.decision_evidence_packets,
            claim_references=claim_binding.validated_claim_references,
            output_governance_evidence=output_governance_evidence,
        )
        decision = await self._presentation_sink_decision_service.evaluate(
            document.authority,
            evidence=evidence,
            expected_authority_metadata=document.authority,
            limitations=document.authority_limitations,
            withholding_reasons=withholding_reasons,
        )
        return MorningReportPresentationPreparation(
            result=GovernedPresentationResult(
                payload=document if decision.may_present else None,
                decision=decision,
            ),
            claim_evidence_links=claim_binding.links,
        )

    async def persist(
        self,
        preparation: MorningReportPresentationPreparation,
        *,
        markdown_body: str,
        workflow_name: str = "morning_report",
        runtime_id: str | None = None,
        artifact_references: Iterable[ReportArtifactReference] = (),
    ) -> ReportPersistenceResult:
        """Persist the exact governed report without another presentation decision."""

        if not preparation.result.decision.may_present:
            return ReportPersistenceResult.failed(
                _presentation_failure_reason(preparation.result.decision)
            )
        document = preparation.result.require_presentable_payload()
        try:
            bundle = self._mapper.build_bundle(
                document,
                markdown_body=markdown_body,
                workflow_name=workflow_name,
                runtime_id=runtime_id,
                artifact_references=artifact_references,
            )
        except (ReportAuthorityViolationError, ReasoningTraceViolationError):
            return ReportPersistenceResult.failed(
                "governed report failed persistence boundary validation."
            )
        return await self._repository.persist_report(
            bundle.report,
            sections=bundle.sections,
            artifacts=bundle.artifacts,
            claim_evidence_links=preparation.claim_evidence_links,
        )

    async def _presentation_governance_evidence(
        self,
        document: MorningReportDocument,
        *,
        claim_references: tuple[EvidenceClaimReference, ...],
    ) -> tuple[tuple[OutputGovernanceGateEvidence, ...], tuple[str, ...]]:
        if not requires_governed_output_release_review(document.authority):
            return (), ()

        release_request = _report_publication_release_request(
            document=document,
            claim_references=claim_references,
            boundary_name="morning_report.presentation",
        )
        if isinstance(release_request, GovernedOutputReleaseDecision):
            return (), (release_request.reason,)

        service = self._governed_output_release_service
        if service is None:
            release_decision = _missing_publication_release_service_decision(
                document.authority,
                boundary_name="morning_report.presentation",
            )
        else:
            release_decision = await service.evaluate_governed_output_release(
                release_request
            )

        governance_evidence = OutputGovernanceGateEvidence.from_release_decision(
            request=release_request,
            decision=release_decision,
        )
        withholding_reasons = (
            () if release_decision.allowed else (release_decision.reason,)
        )
        return (governance_evidence,), withholding_reasons


def _validate_pre_render_document(document: MorningReportDocument) -> None:
    content_texts = _document_text_values(document)
    ensure_report_publication_authority(
        contract=document.authority,
        content_texts=content_texts,
        boundary_name="morning_report.presentation",
    )
    for value in content_texts:
        _publication_text(
            value,
            boundary_name="morning_report.presentation",
        )


__all__ = [
    "MorningReportPersistenceService",
    "MorningReportPresentationPreparation",
]
