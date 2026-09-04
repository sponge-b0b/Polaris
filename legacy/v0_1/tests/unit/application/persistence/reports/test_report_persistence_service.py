from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

import pytest

from application.persistence.reports import (
    ReportArtifactPersistenceFilters,
    ReportClaimEvidenceLinkPersistenceFilters,
    ReportPersistenceService,
    ReportPublicationPersistenceFilters,
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


class FakeReportRepository:
    def __init__(
        self,
        *,
        bundle: ReportPersistenceBundle | None = None,
    ) -> None:
        self.bundle = bundle
        self.persisted_bundle: ReportPersistenceBundle | None = None
        self.artifact_filters: dict[str, str | None] | None = None
        self.publication_filters: dict[str, str | None] | None = None
        self.claim_evidence_link_filters: dict[str, str | None] | None = None

    async def persist_report_bundle(
        self,
        bundle: ReportPersistenceBundle,
    ) -> ReportPersistenceResult:
        self.persisted_bundle = bundle
        return ReportPersistenceResult.succeeded(
            report_id=bundle.report.report_id,
            records_persisted=(
                1
                + len(bundle.sections)
                + len(bundle.artifacts)
                + len(bundle.versions)
                + len(bundle.publications)
                + len(bundle.claim_evidence_links)
            ),
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
        return await self.persist_report_bundle(
            ReportPersistenceBundle(
                report=report,
                sections=tuple(sections),
                artifacts=tuple(artifacts),
                versions=tuple(versions),
                publications=tuple(publications),
                claim_evidence_links=tuple(claim_evidence_links),
            )
        )

    async def get_report(
        self,
        report_id: str,
    ) -> ReportRecord | None:
        if self.bundle is None or self.bundle.report.report_id != report_id:
            return None
        return self.bundle.report

    async def get_report_bundle(
        self,
        report_id: str,
    ) -> ReportPersistenceBundle | None:
        if self.bundle is None or self.bundle.report.report_id != report_id:
            return None
        return self.bundle

    async def get_version(
        self,
        version_id: str,
    ) -> ReportVersionRecord | None:
        if self.bundle is None:
            return None
        for version in self.bundle.versions:
            if version.version_id == version_id:
                return version
        return None

    async def list_sections(
        self,
        report_id: str,
    ) -> Sequence[ReportSectionRecord]:
        if self.bundle is None or self.bundle.report.report_id != report_id:
            return ()
        return self.bundle.sections

    async def list_artifacts(
        self,
        *,
        report_id: str | None = None,
        section_id: str | None = None,
    ) -> Sequence[ReportArtifactRecord]:
        self.artifact_filters = {
            "report_id": report_id,
            "section_id": section_id,
        }
        if self.bundle is None:
            return ()
        return self.bundle.artifacts

    async def list_versions(
        self,
        report_id: str,
    ) -> Sequence[ReportVersionRecord]:
        if self.bundle is None or self.bundle.report.report_id != report_id:
            return ()
        return self.bundle.versions

    async def list_claim_evidence_links(
        self,
        *,
        report_id: str | None = None,
        section_id: str | None = None,
        packet_id: str | None = None,
        claim_target_id: str | None = None,
    ) -> Sequence[ReportClaimEvidenceLinkRecord]:
        self.claim_evidence_link_filters = {
            "report_id": report_id,
            "section_id": section_id,
            "packet_id": packet_id,
            "claim_target_id": claim_target_id,
        }
        if self.bundle is None:
            return ()
        return self.bundle.claim_evidence_links

    async def list_publications(
        self,
        *,
        report_id: str | None = None,
        version_id: str | None = None,
        publication_target: str | None = None,
        publication_status: str | None = None,
    ) -> Sequence[ReportPublicationRecord]:
        self.publication_filters = {
            "report_id": report_id,
            "version_id": version_id,
            "publication_target": publication_target,
            "publication_status": publication_status,
        }
        if self.bundle is None:
            return ()
        return self.bundle.publications


@pytest.mark.asyncio
async def test_report_persistence_service_persists_typed_report_bundle() -> None:
    repository = FakeReportRepository()
    service = ReportPersistenceService(repository)

    result = await service.persist_report(
        _report(),
        sections=(_section(),),
        artifacts=(_artifact(),),
        versions=(_version(),),
        publications=(_publication(),),
    )

    assert result.success is True
    assert result.records_persisted == 5
    assert repository.persisted_bundle is not None
    assert repository.persisted_bundle.report.report_id == "morning_report:exec-1"
    assert repository.persisted_bundle.versions[0].markdown_body == "# Full version\n"
    assert repository.persisted_bundle.publications[0].publication_target == (
        "markdown_archive"
    )


@pytest.mark.asyncio
async def test_report_persistence_service_rehydrates_existing_bundle() -> None:
    bundle = ReportPersistenceBundle(
        report=_report(),
        sections=(_section(),),
        artifacts=(_artifact(),),
        versions=(_version(),),
        publications=(_publication(),),
    )
    service = ReportPersistenceService(
        FakeReportRepository(
            bundle=bundle,
        )
    )

    retrieved = await service.get_bundle(
        "morning_report:exec-1",
    )

    assert retrieved == bundle


@pytest.mark.asyncio
async def test_report_persistence_service_uses_typed_filters() -> None:
    repository = FakeReportRepository(
        bundle=ReportPersistenceBundle(
            report=_report(),
            artifacts=(_artifact(),),
            versions=(_version(),),
            publications=(_publication(),),
        )
    )
    service = ReportPersistenceService(repository)

    artifacts = await service.list_artifacts(
        ReportArtifactPersistenceFilters(
            report_id=" morning_report:exec-1 ",
            section_id=" morning_report:exec-1:section:macro ",
        )
    )
    publications = await service.list_publications(
        ReportPublicationPersistenceFilters(
            report_id=" morning_report:exec-1 ",
            version_id=" morning_report:exec-1:version:1 ",
            publication_target=" markdown_archive ",
            publication_status=" published ",
        )
    )

    assert len(artifacts) == 1
    assert len(publications) == 1
    assert repository.artifact_filters == {
        "report_id": "morning_report:exec-1",
        "section_id": "morning_report:exec-1:section:macro",
    }
    assert repository.publication_filters == {
        "report_id": "morning_report:exec-1",
        "version_id": "morning_report:exec-1:version:1",
        "publication_target": "markdown_archive",
        "publication_status": "published",
    }


@pytest.mark.asyncio
async def test_report_persistence_service_returns_none_for_missing_records() -> None:
    service = ReportPersistenceService(
        FakeReportRepository(),
    )

    assert await service.get_report("missing") is None
    assert await service.get_bundle("missing") is None
    assert await service.get_version("missing") is None


@pytest.mark.asyncio
async def test_service_persists_and_lists_report_claim_links() -> None:
    repository = FakeReportRepository(
        bundle=ReportPersistenceBundle(
            report=_report(),
            claim_evidence_links=(_claim_evidence_link(),),
        )
    )
    service = ReportPersistenceService(repository)

    result = await service.persist_report(
        _report(),
        claim_evidence_links=(_claim_evidence_link(),),
    )
    links = await service.list_claim_evidence_links(
        ReportClaimEvidenceLinkPersistenceFilters(
            report_id=" morning_report:exec-1 ",
            section_id=" morning_report:exec-1:section:macro ",
            packet_id=" packet-1 ",
            claim_target_id=" claim-1 ",
        )
    )

    assert result.records_persisted == 2
    assert repository.persisted_bundle is not None
    assert repository.persisted_bundle.claim_evidence_links[0].packet_id == "packet-1"
    assert links == (_claim_evidence_link(),)
    assert repository.claim_evidence_link_filters == {
        "report_id": "morning_report:exec-1",
        "section_id": "morning_report:exec-1:section:macro",
        "packet_id": "packet-1",
        "claim_target_id": "claim-1",
    }


def _timestamp() -> datetime:
    return datetime(2026, 5, 30, 14, tzinfo=UTC)


def _report() -> ReportRecord:
    return ReportRecord(
        report_id="morning_report:exec-1",
        report_type="morning_report",
        title="Morning Report",
        generated_at=_timestamp(),
        markdown_body="# Full report\n",
        structured_payload={"symbol": "SPY"},
    )


def _section() -> ReportSectionRecord:
    return ReportSectionRecord(
        section_id="morning_report:exec-1:section:macro",
        report_id="morning_report:exec-1",
        section_key="macro",
        title="Macro",
        display_order=1,
    )


def _artifact() -> ReportArtifactRecord:
    return ReportArtifactRecord(
        artifact_id="morning_report:exec-1:artifact:markdown",
        report_id="morning_report:exec-1",
        section_id="morning_report:exec-1:section:macro",
        artifact_type="markdown",
        artifact_uri="/reports/morning_report.md",
    )


def _version() -> ReportVersionRecord:
    return ReportVersionRecord(
        version_id="morning_report:exec-1:version:1",
        report_id="morning_report:exec-1",
        version_number=1,
        created_at=_timestamp(),
        markdown_body="# Full version\n",
        structured_payload={"symbol": "SPY"},
    )


def _publication() -> ReportPublicationRecord:
    return ReportPublicationRecord(
        publication_id="morning_report:exec-1:publication:markdown",
        report_id="morning_report:exec-1",
        version_id="morning_report:exec-1:version:1",
        publication_target="markdown_archive",
        publication_status="published",
        requested_at=_timestamp(),
        published_at=datetime(2026, 5, 30, 14, 5, tzinfo=UTC),
        artifact_uri="/reports/morning_report.md",
    )


def _claim_evidence_link() -> ReportClaimEvidenceLinkRecord:
    return ReportClaimEvidenceLinkRecord(
        link_id="morning_report:exec-1:claim_evidence:claim-1:packet-1:claim-a",
        report_id="morning_report:exec-1",
        section_id="morning_report:exec-1:section:macro",
        claim_target_id="claim-1",
        packet_id="packet-1",
        packet_claim_id="claim-a",
        risk_tier=RiskTier.ENHANCED,
        material=True,
        supporting_evidence_ids=("evidence-1",),
        reconstruction_reference_ids=("reconstruction-1",),
    )
