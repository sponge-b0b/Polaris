from __future__ import annotations

from dataclasses import replace

import pytest

from application.governance import (
    GovernanceReviewApprovalState,
    GovernedOutputReleaseDecision,
)
from application.reports import (
    MorningReportMarkdownRenderer,
    MorningReportPersistenceService,
)
from application.reports.morning_report_models import ReportSection
from tests.unit.application.reports.morning.test_morning_report_persistence import (
    FakeReportRepository,
    _approved_release_gate,
    _document,
    _document_with_contextual_claim_reference,
    _FakeGovernedOutputReleaseService,
    _FakeReportClaimBindingService,
    _with_publication_review,
)


@pytest.mark.asyncio
async def test_morning_report_is_governed_before_render_and_persisted_once() -> None:
    repository = FakeReportRepository()
    gate = _approved_release_gate()
    service = MorningReportPersistenceService(
        repository,
        claim_binding_service=_FakeReportClaimBindingService(()),
        governed_output_release_service=gate,
    )
    document = _with_publication_review(_document_with_contextual_claim_reference())

    preparation = await service.prepare_presentation(document)

    assert preparation.result.decision.may_present is True
    assert preparation.result.payload == document
    assert len(gate.requests) == 1
    assert gate.requests[0].boundary_name == "morning_report.presentation"

    markdown = MorningReportMarkdownRenderer().render(preparation.result)
    persisted = await service.persist(
        preparation,
        markdown_body=markdown,
    )

    assert persisted.success is True
    assert repository.report is not None
    assert repository.report.markdown_body == markdown
    assert len(gate.requests) == 1


@pytest.mark.asyncio
async def test_withheld_morning_report_has_no_payload_before_renderer() -> None:
    repository = FakeReportRepository()
    gate = _FakeGovernedOutputReleaseService(
        GovernedOutputReleaseDecision(
            allowed=False,
            reason="governance review denied report publication",
            approval_state=GovernanceReviewApprovalState.REVIEW_DENIED,
        )
    )
    service = MorningReportPersistenceService(
        repository,
        claim_binding_service=_FakeReportClaimBindingService(()),
        governed_output_release_service=gate,
    )
    document = _with_publication_review(_document_with_contextual_claim_reference())

    preparation = await service.prepare_presentation(document)

    assert preparation.result.decision.may_present is False
    assert preparation.result.payload is None
    assert preparation.result.projection.disposition == "withheld"
    with pytest.raises(ValueError, match="not eligible for presentation"):
        MorningReportMarkdownRenderer().render(preparation.result)

    persisted = await service.persist(
        preparation,
        markdown_body="# should never be externally rendered",
    )

    assert persisted.success is False
    assert repository.report is None
    assert len(gate.requests) == 1


@pytest.mark.asyncio
async def test_unsafe_report_is_blocked_before_claim_binding_or_render() -> None:
    repository = FakeReportRepository()
    binding = _FakeReportClaimBindingService(())
    gate = _approved_release_gate()
    service = MorningReportPersistenceService(
        repository,
        claim_binding_service=binding,
        governed_output_release_service=gate,
    )
    document = replace(
        _document(),
        executive_summary=ReportSection(
            title="Executive Summary",
            summary="Buy 100 shares of SPY at the open.",
        ),
    )

    preparation = await service.prepare_presentation(document)

    assert preparation.result.decision.may_present is False
    assert preparation.result.payload is None
    assert preparation.result.projection.disposition == "blocked"
    assert binding.targets == ()
    assert gate.requests == []
    assert repository.report is None


@pytest.mark.asyncio
async def test_missing_claim_evidence_is_withheld_before_render() -> None:
    repository = FakeReportRepository()
    service = MorningReportPersistenceService(
        repository,
        governed_output_release_service=_approved_release_gate(),
    )

    preparation = await service.prepare_presentation(_document())

    assert preparation.result.decision.may_present is False
    assert preparation.result.payload is None
    assert preparation.result.projection.disposition == "withheld"
    assert repository.report is None


def test_markdown_renderer_rejects_raw_report_document() -> None:
    with pytest.raises(TypeError, match="requires a governed presentation result"):
        MorningReportMarkdownRenderer().render(_document())  # type: ignore[arg-type]
