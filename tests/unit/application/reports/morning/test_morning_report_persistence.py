from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any, cast

import pytest

from application.reports import MorningReportMarkdownRenderer
from application.reports.authority import ReportAuthorityViolationError
from application.reports.morning_report_models import (
    MorningReportDocument,
    ReportBullet,
    ReportMetric,
    ReportSection,
)
from application.reports.morning_report_persistence import (
    MorningReportPersistenceMapper,
    MorningReportPersistenceService,
    ReportArtifactReference,
)
from core.storage.persistence.reports import (
    ReportArtifactRecord,
    ReportPersistenceBundle,
    ReportPersistenceResult,
    ReportPublicationRecord,
    ReportRecord,
    ReportSectionRecord,
    ReportVersionRecord,
)
from domain.llm import ReasoningTraceViolationError


class FakeReportRepository:
    def __init__(
        self,
    ) -> None:
        self.report: ReportRecord | None = None
        self.sections: tuple[ReportSectionRecord, ...] = ()
        self.artifacts: tuple[ReportArtifactRecord, ...] = ()
        self.versions: tuple[ReportVersionRecord, ...] = ()
        self.publications: tuple[ReportPublicationRecord, ...] = ()

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
        )

    async def persist_report(
        self,
        report: ReportRecord,
        *,
        sections: Sequence[ReportSectionRecord] = (),
        artifacts: Sequence[ReportArtifactRecord] = (),
        versions: Sequence[ReportVersionRecord] = (),
        publications: Sequence[ReportPublicationRecord] = (),
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
        return ReportPersistenceResult.succeeded(
            report_id=report.report_id,
            records_persisted=1
            + len(
                self.sections,
            )
            + len(
                self.artifacts,
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
    document = _document()
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
