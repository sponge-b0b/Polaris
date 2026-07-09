from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from core.storage.persistence.lineage import clean_optional_identifier
from core.storage.persistence.reports import ReportArtifactRecord
from core.storage.persistence.reports import ReportPersistenceBundle
from core.storage.persistence.reports import ReportPersistenceRepository
from core.storage.persistence.reports import ReportPersistenceResult
from core.storage.persistence.reports import ReportPublicationRecord
from core.storage.persistence.reports import ReportRecord
from core.storage.persistence.reports import ReportSectionRecord
from core.storage.persistence.reports import ReportVersionRecord
from core.storage.persistence.query import PersistenceListResult

from application.persistence.query_result_helpers import build_common_query
from application.persistence.query_result_helpers import build_list_result


@dataclass(
    frozen=True,
    slots=True,
)
class ReportArtifactPersistenceFilters:
    """
    Typed application-layer filters for curated report artifact retrieval.
    """

    report_id: str | None = None
    section_id: str | None = None

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "report_id",
            clean_optional_identifier(
                self.report_id,
                "report_id",
            ),
        )
        object.__setattr__(
            self,
            "section_id",
            clean_optional_identifier(
                self.section_id,
                "section_id",
            ),
        )


@dataclass(
    frozen=True,
    slots=True,
)
class ReportPublicationPersistenceFilters:
    """
    Typed application-layer filters for report publication retrieval.
    """

    report_id: str | None = None
    version_id: str | None = None
    publication_target: str | None = None
    publication_status: str | None = None

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "report_id",
            clean_optional_identifier(
                self.report_id,
                "report_id",
            ),
        )
        object.__setattr__(
            self,
            "version_id",
            clean_optional_identifier(
                self.version_id,
                "version_id",
            ),
        )
        object.__setattr__(
            self,
            "publication_target",
            clean_optional_identifier(
                self.publication_target,
                "publication_target",
            ),
        )
        object.__setattr__(
            self,
            "publication_status",
            clean_optional_identifier(
                self.publication_status,
                "publication_status",
            ),
        )


class ReportPersistenceService:
    """
    Application service for curated report persistence.

    This service coordinates typed report persistence through the repository
    protocol only. It intentionally accepts curated report/version/publication
    records and does not auto-capture raw workflow output or runtime state.
    """

    def __init__(
        self,
        repository: ReportPersistenceRepository,
    ) -> None:
        self._repository = repository

    async def persist_bundle(
        self,
        bundle: ReportPersistenceBundle,
    ) -> ReportPersistenceResult:
        return await self._repository.persist_report_bundle(
            bundle,
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
        return await self.persist_bundle(
            ReportPersistenceBundle(
                report=report,
                sections=tuple(
                    sections,
                ),
                artifacts=tuple(
                    artifacts,
                ),
                versions=tuple(
                    versions,
                ),
                publications=tuple(
                    publications,
                ),
            )
        )

    async def get_report(
        self,
        report_id: str,
    ) -> ReportRecord | None:
        return await self._repository.get_report(
            report_id,
        )

    async def get_bundle(
        self,
        report_id: str,
    ) -> ReportPersistenceBundle | None:
        return await self._repository.get_report_bundle(
            report_id,
        )

    async def get_version(
        self,
        version_id: str,
    ) -> ReportVersionRecord | None:
        return await self._repository.get_version(
            version_id,
        )

    async def list_sections(
        self,
        report_id: str,
    ) -> Sequence[ReportSectionRecord]:
        result = await self.list_sections_result(
            report_id,
        )
        return result.records

    async def list_sections_result(
        self,
        report_id: str,
    ) -> PersistenceListResult[ReportSectionRecord]:
        clean_report_id = clean_optional_identifier(
            report_id,
            "report_id",
        )
        records = await self._repository.list_sections(
            report_id,
        )
        query = build_common_query(
            record_type="report_section",
            metadata={
                "report_id": clean_report_id,
            },
        )
        return build_list_result(
            records,
            query=query,
        )

    async def list_artifacts(
        self,
        filters: ReportArtifactPersistenceFilters | None = None,
    ) -> Sequence[ReportArtifactRecord]:
        result = await self.list_artifacts_result(
            filters,
        )
        return result.records

    async def list_artifacts_result(
        self,
        filters: ReportArtifactPersistenceFilters | None = None,
    ) -> PersistenceListResult[ReportArtifactRecord]:
        active_filters = filters or ReportArtifactPersistenceFilters()
        records = await self._repository.list_artifacts(
            report_id=active_filters.report_id,
            section_id=active_filters.section_id,
        )
        query = build_common_query(
            record_type="report_artifact",
            metadata={
                "report_id": active_filters.report_id,
                "section_id": active_filters.section_id,
            },
        )
        return build_list_result(
            records,
            query=query,
        )

    async def list_versions(
        self,
        report_id: str,
    ) -> Sequence[ReportVersionRecord]:
        result = await self.list_versions_result(
            report_id,
        )
        return result.records

    async def list_versions_result(
        self,
        report_id: str,
    ) -> PersistenceListResult[ReportVersionRecord]:
        clean_report_id = clean_optional_identifier(
            report_id,
            "report_id",
        )
        records = await self._repository.list_versions(
            report_id,
        )
        query = build_common_query(
            record_type="report_version",
            metadata={
                "report_id": clean_report_id,
            },
        )
        return build_list_result(
            records,
            query=query,
        )

    async def list_publications(
        self,
        filters: ReportPublicationPersistenceFilters | None = None,
    ) -> Sequence[ReportPublicationRecord]:
        result = await self.list_publications_result(
            filters,
        )
        return result.records

    async def list_publications_result(
        self,
        filters: ReportPublicationPersistenceFilters | None = None,
    ) -> PersistenceListResult[ReportPublicationRecord]:
        active_filters = filters or ReportPublicationPersistenceFilters()
        records = await self._repository.list_publications(
            report_id=active_filters.report_id,
            version_id=active_filters.version_id,
            publication_target=active_filters.publication_target,
            publication_status=active_filters.publication_status,
        )
        query = build_common_query(
            record_type="report_publication",
            metadata={
                "report_id": active_filters.report_id,
                "version_id": active_filters.version_id,
                "publication_target": active_filters.publication_target,
                "publication_status": active_filters.publication_status,
            },
        )
        return build_list_result(
            records,
            query=query,
        )
