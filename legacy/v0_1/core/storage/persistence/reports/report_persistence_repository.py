from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from core.storage.persistence.reports.report_persistence_models import (
    ReportArtifactRecord,
    ReportClaimEvidenceLinkRecord,
    ReportPersistenceBundle,
    ReportPersistenceResult,
    ReportPublicationRecord,
    ReportRecord,
    ReportSectionRecord,
    ReportVersionRecord,
)


class ReportPersistenceRepository(Protocol):
    """
    Async repository contract for durable curated report persistence.
    """

    async def persist_report_bundle(
        self,
        bundle: ReportPersistenceBundle,
    ) -> ReportPersistenceResult: ...

    async def persist_report(
        self,
        report: ReportRecord,
        *,
        sections: Sequence[ReportSectionRecord] = (),
        artifacts: Sequence[ReportArtifactRecord] = (),
        versions: Sequence[ReportVersionRecord] = (),
        publications: Sequence[ReportPublicationRecord] = (),
        claim_evidence_links: Sequence[ReportClaimEvidenceLinkRecord] = (),
    ) -> ReportPersistenceResult: ...

    async def get_report(
        self,
        report_id: str,
    ) -> ReportRecord | None: ...

    async def get_report_bundle(
        self,
        report_id: str,
    ) -> ReportPersistenceBundle | None: ...

    async def get_version(
        self,
        version_id: str,
    ) -> ReportVersionRecord | None: ...

    async def list_sections(
        self,
        report_id: str,
    ) -> Sequence[ReportSectionRecord]: ...

    async def list_artifacts(
        self,
        *,
        report_id: str | None = None,
        section_id: str | None = None,
    ) -> Sequence[ReportArtifactRecord]: ...

    async def list_versions(
        self,
        report_id: str,
    ) -> Sequence[ReportVersionRecord]: ...

    async def list_publications(
        self,
        *,
        report_id: str | None = None,
        version_id: str | None = None,
        publication_target: str | None = None,
        publication_status: str | None = None,
    ) -> Sequence[ReportPublicationRecord]: ...

    async def list_claim_evidence_links(
        self,
        *,
        report_id: str | None = None,
        section_id: str | None = None,
        packet_id: str | None = None,
        claim_target_id: str | None = None,
    ) -> Sequence[ReportClaimEvidenceLinkRecord]: ...
