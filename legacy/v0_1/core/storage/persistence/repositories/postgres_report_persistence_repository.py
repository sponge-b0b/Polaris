from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.models.reports import (
    ReportArtifactModel,
    ReportClaimEvidenceLinkModel,
    ReportModel,
    ReportPublicationModel,
    ReportSectionModel,
    ReportVersionModel,
)
from core.storage.persistence.claim_evidence_links import (
    PostgresClaimEvidenceLinkObservability,
    claim_evidence_link_started_at,
    claim_evidence_link_upsert_set_values,
    execute_claim_evidence_link_upserts,
)
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
from core.storage.persistence.reports.report_persistence_repository import (
    ReportPersistenceRepository,
)
from core.storage.persistence.serializers.report_persistence_serializer import (
    ReportPersistenceSerializer,
)
from core.telemetry.observability import ObservabilityManager

_COMPONENT_NAME = "PostgresReportPersistenceRepository"
_REPORT_CLAIM_EVIDENCE_LINK_TABLE = "report_claim_evidence_links"
_REPORT_CLAIM_EVIDENCE_LINK_METRIC_PREFIX = (
    "storage.postgres.report_claim_evidence_link"
)
_REPORT_CLAIM_EVIDENCE_LINK_WRITE_OPERATION = "report_claim_evidence_link_write"
_REPORT_CLAIM_EVIDENCE_LINK_READ_OPERATION = "report_claim_evidence_link_read"


class PostgresReportPersistenceRepository(ReportPersistenceRepository):
    """
    PostgreSQL adapter for durable curated report persistence.

    Reports, sections, artifact references, versions, and publication records
    are idempotent upserts so CLI retries can preserve one canonical report row
    per workflow execution while retaining explicit version/publication audit
    records.
    """

    def __init__(
        self,
        session: AsyncSession,
        *,
        observability_manager: ObservabilityManager | None = None,
    ) -> None:
        self._session = session
        self._claim_evidence_observability = PostgresClaimEvidenceLinkObservability(
            observability_manager=observability_manager,
            component_name=_COMPONENT_NAME,
            table_name=_REPORT_CLAIM_EVIDENCE_LINK_TABLE,
            metric_prefix=_REPORT_CLAIM_EVIDENCE_LINK_METRIC_PREFIX,
            owner_id_attribute="report_id",
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
                claim_evidence_links=tuple(
                    claim_evidence_links,
                ),
            )
        )

    async def persist_report_bundle(
        self,
        bundle: ReportPersistenceBundle,
    ) -> ReportPersistenceResult:
        claim_evidence_links = tuple(bundle.claim_evidence_links)
        claim_evidence_started_at: float | None = None
        try:
            await self._session.execute(
                _upsert_report_statement(
                    bundle.report,
                )
            )
            for section in bundle.sections:
                await self._session.execute(
                    _upsert_section_statement(
                        section,
                    )
                )
            for artifact in bundle.artifacts:
                await self._session.execute(
                    _upsert_artifact_statement(
                        artifact,
                    )
                )
            for version in bundle.versions:
                await self._session.execute(
                    _upsert_version_statement(
                        version,
                    )
                )
            for publication in bundle.publications:
                await self._session.execute(
                    _upsert_publication_statement(
                        publication,
                    )
                )
            if claim_evidence_links:
                claim_evidence_started_at = claim_evidence_link_started_at()
                await execute_claim_evidence_link_upserts(
                    self._session,
                    claim_evidence_links,
                    _upsert_claim_evidence_link_statement,
                )
            await self._session.commit()
        except SQLAlchemyError as exc:
            await self._session.rollback()
            if claim_evidence_started_at is not None:
                await self._claim_evidence_observability.record_operation(
                    operation=_REPORT_CLAIM_EVIDENCE_LINK_WRITE_OPERATION,
                    owner_id=bundle.report.report_id,
                    started_at=claim_evidence_started_at,
                    success=False,
                    error=exc,
                )

            return ReportPersistenceResult.failed(
                str(exc),
            )

        if claim_evidence_started_at is not None:
            await self._claim_evidence_observability.record_operation(
                operation=_REPORT_CLAIM_EVIDENCE_LINK_WRITE_OPERATION,
                owner_id=bundle.report.report_id,
                started_at=claim_evidence_started_at,
                success=True,
                records_persisted=len(claim_evidence_links),
            )

        return ReportPersistenceResult.succeeded(
            report_id=bundle.report.report_id,
            records_persisted=1
            + len(
                bundle.sections,
            )
            + len(
                bundle.artifacts,
            )
            + len(
                bundle.versions,
            )
            + len(
                bundle.publications,
            )
            + len(
                bundle.claim_evidence_links,
            ),
        )

    async def get_report(
        self,
        report_id: str,
    ) -> ReportRecord | None:
        stmt = select(ReportModel).where(
            ReportModel.report_id == report_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None

        return ReportPersistenceSerializer.report_from_model(
            model,
        )

    async def get_report_bundle(
        self,
        report_id: str,
    ) -> ReportPersistenceBundle | None:
        report = await self.get_report(
            report_id,
        )
        if report is None:
            return None

        sections = await self.list_sections(
            report_id,
        )
        artifacts = await self.list_artifacts(
            report_id=report_id,
        )
        versions = await self.list_versions(
            report_id,
        )
        publications = await self.list_publications(
            report_id=report_id,
        )
        claim_evidence_links = await self.list_claim_evidence_links(
            report_id=report_id,
        )

        return ReportPersistenceBundle(
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
            claim_evidence_links=tuple(
                claim_evidence_links,
            ),
        )

    async def get_version(
        self,
        version_id: str,
    ) -> ReportVersionRecord | None:
        stmt = select(ReportVersionModel).where(
            ReportVersionModel.version_id == version_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None

        return ReportPersistenceSerializer.version_from_model(
            model,
        )

    async def list_sections(
        self,
        report_id: str,
    ) -> Sequence[ReportSectionRecord]:
        stmt = (
            select(ReportSectionModel)
            .where(
                ReportSectionModel.report_id == report_id,
            )
            .order_by(
                ReportSectionModel.display_order,
                ReportSectionModel.section_key,
                ReportSectionModel.section_id,
            )
        )
        result = await self._session.execute(stmt)

        return tuple(
            ReportPersistenceSerializer.section_from_model(
                model,
            )
            for model in result.scalars().all()
        )

    async def list_artifacts(
        self,
        *,
        report_id: str | None = None,
        section_id: str | None = None,
    ) -> Sequence[ReportArtifactRecord]:
        stmt = select(ReportArtifactModel)
        if report_id is not None:
            stmt = stmt.where(
                ReportArtifactModel.report_id == report_id,
            )
        if section_id is not None:
            stmt = stmt.where(
                ReportArtifactModel.section_id == section_id,
            )
        stmt = stmt.order_by(
            ReportArtifactModel.report_id,
            ReportArtifactModel.artifact_type,
            ReportArtifactModel.artifact_id,
        )
        result = await self._session.execute(stmt)

        return tuple(
            ReportPersistenceSerializer.artifact_from_model(
                model,
            )
            for model in result.scalars().all()
        )

    async def list_versions(
        self,
        report_id: str,
    ) -> Sequence[ReportVersionRecord]:
        stmt = (
            select(ReportVersionModel)
            .where(
                ReportVersionModel.report_id == report_id,
            )
            .order_by(
                ReportVersionModel.version_number,
                ReportVersionModel.created_at,
                ReportVersionModel.version_id,
            )
        )
        result = await self._session.execute(stmt)

        return tuple(
            ReportPersistenceSerializer.version_from_model(
                model,
            )
            for model in result.scalars().all()
        )

    async def list_publications(
        self,
        *,
        report_id: str | None = None,
        version_id: str | None = None,
        publication_target: str | None = None,
        publication_status: str | None = None,
    ) -> Sequence[ReportPublicationRecord]:
        stmt = select(ReportPublicationModel)
        if report_id is not None:
            stmt = stmt.where(
                ReportPublicationModel.report_id == report_id,
            )
        if version_id is not None:
            stmt = stmt.where(
                ReportPublicationModel.version_id == version_id,
            )
        if publication_target is not None:
            stmt = stmt.where(
                ReportPublicationModel.publication_target == publication_target,
            )
        if publication_status is not None:
            stmt = stmt.where(
                ReportPublicationModel.publication_status == publication_status,
            )
        stmt = stmt.order_by(
            ReportPublicationModel.requested_at,
            ReportPublicationModel.publication_target,
            ReportPublicationModel.publication_id,
        )
        result = await self._session.execute(stmt)

        return tuple(
            ReportPersistenceSerializer.publication_from_model(
                model,
            )
            for model in result.scalars().all()
        )

    async def list_claim_evidence_links(
        self,
        *,
        report_id: str | None = None,
        section_id: str | None = None,
        packet_id: str | None = None,
        claim_target_id: str | None = None,
    ) -> Sequence[ReportClaimEvidenceLinkRecord]:
        started_at = claim_evidence_link_started_at()
        filters = {
            "section_id": section_id,
            "packet_id": packet_id,
            "claim_target_id": claim_target_id,
        }
        stmt = select(ReportClaimEvidenceLinkModel)
        if report_id is not None:
            stmt = stmt.where(
                ReportClaimEvidenceLinkModel.report_id == report_id,
            )
        if section_id is not None:
            stmt = stmt.where(
                ReportClaimEvidenceLinkModel.section_id == section_id,
            )
        if packet_id is not None:
            stmt = stmt.where(
                ReportClaimEvidenceLinkModel.packet_id == packet_id,
            )
        if claim_target_id is not None:
            stmt = stmt.where(
                ReportClaimEvidenceLinkModel.claim_target_id == claim_target_id,
            )
        stmt = stmt.order_by(
            ReportClaimEvidenceLinkModel.report_id,
            ReportClaimEvidenceLinkModel.claim_target_id,
            ReportClaimEvidenceLinkModel.packet_id,
            ReportClaimEvidenceLinkModel.packet_claim_id,
            ReportClaimEvidenceLinkModel.link_id,
        )
        try:
            result = await self._session.execute(stmt)
            records = tuple(
                ReportPersistenceSerializer.claim_evidence_link_from_model(
                    model,
                )
                for model in result.scalars().all()
            )
        except SQLAlchemyError as exc:
            await self._claim_evidence_observability.record_operation(
                operation=_REPORT_CLAIM_EVIDENCE_LINK_READ_OPERATION,
                owner_id=report_id,
                started_at=started_at,
                success=False,
                filters=filters,
                error=exc,
            )
            raise

        await self._claim_evidence_observability.record_operation(
            operation=_REPORT_CLAIM_EVIDENCE_LINK_READ_OPERATION,
            owner_id=report_id,
            started_at=started_at,
            success=True,
            filters=filters,
            records_returned=len(records),
        )
        return records


def _report_claim_evidence_link_log_context(
    *,
    operation: str,
    report_id: str | None,
    filters: dict[str, str | None] | None = None,
) -> dict[str, Any]:
    context: dict[str, Any] = {
        "component_name": _COMPONENT_NAME,
        "database_system": "postgresql",
        "operation": operation,
        "table": _REPORT_CLAIM_EVIDENCE_LINK_TABLE,
    }
    if report_id is not None:
        context["report_id"] = report_id
    if filters is not None:
        context.update(
            {key: value for key, value in filters.items() if value is not None}
        )
    return context


def _upsert_report_statement(
    report: ReportRecord,
) -> Any:
    values = ReportPersistenceSerializer.report_values(report)
    stmt = insert(ReportModel).values(**values)
    excluded = stmt.excluded

    return stmt.on_conflict_do_update(
        index_elements=[
            "report_id",
        ],
        set_={
            "report_type": excluded.report_type,
            "title": excluded.title,
            "subtitle": excluded.subtitle,
            "workflow_name": excluded.workflow_name,
            "execution_id": excluded.execution_id,
            "runtime_id": excluded.runtime_id,
            "status": excluded.status,
            "generated_at": excluded.generated_at,
            "markdown_body": excluded.markdown_body,
            "structured_payload": excluded.structured_payload,
            "metadata": excluded.metadata,
            "updated_at": func.now(),
        },
    )


def _upsert_section_statement(
    section: ReportSectionRecord,
) -> Any:
    values = ReportPersistenceSerializer.section_values(section)
    stmt = insert(ReportSectionModel).values(**values)
    excluded = stmt.excluded

    return stmt.on_conflict_do_update(
        index_elements=[
            "section_id",
        ],
        set_={
            "section_key": excluded.section_key,
            "title": excluded.title,
            "display_order": excluded.display_order,
            "summary": excluded.summary,
            "markdown_body": excluded.markdown_body,
            "content_payload": excluded.content_payload,
            "metadata": excluded.metadata,
            "updated_at": func.now(),
        },
    )


def _upsert_artifact_statement(
    artifact: ReportArtifactRecord,
) -> Any:
    values = ReportPersistenceSerializer.artifact_values(artifact)
    stmt = insert(ReportArtifactModel).values(**values)
    excluded = stmt.excluded

    return stmt.on_conflict_do_update(
        index_elements=[
            "artifact_id",
        ],
        set_={
            "section_id": excluded.section_id,
            "artifact_type": excluded.artifact_type,
            "artifact_uri": excluded.artifact_uri,
            "mime_type": excluded.mime_type,
            "description": excluded.description,
            "metadata": excluded.metadata,
            "updated_at": func.now(),
        },
    )


def _upsert_version_statement(
    version: ReportVersionRecord,
) -> Any:
    values = ReportPersistenceSerializer.version_values(version)
    stmt = insert(ReportVersionModel).values(**values)
    excluded = stmt.excluded

    return stmt.on_conflict_do_update(
        index_elements=[
            "version_id",
        ],
        set_={
            "report_id": excluded.report_id,
            "version_number": excluded.version_number,
            "created_at": excluded.created_at,
            "title": excluded.title,
            "subtitle": excluded.subtitle,
            "markdown_body": excluded.markdown_body,
            "change_summary": excluded.change_summary,
            "created_by": excluded.created_by,
            "structured_payload": excluded.structured_payload,
            "metadata": excluded.metadata,
            "row_updated_at": func.now(),
        },
    )


def _upsert_publication_statement(
    publication: ReportPublicationRecord,
) -> Any:
    values = ReportPersistenceSerializer.publication_values(publication)
    stmt = insert(ReportPublicationModel).values(**values)
    excluded = stmt.excluded

    return stmt.on_conflict_do_update(
        index_elements=[
            "publication_id",
        ],
        set_={
            "report_id": excluded.report_id,
            "version_id": excluded.version_id,
            "publication_target": excluded.publication_target,
            "publication_status": excluded.publication_status,
            "requested_at": excluded.requested_at,
            "published_at": excluded.published_at,
            "artifact_uri": excluded.artifact_uri,
            "error": excluded.error,
            "metadata": excluded.metadata,
            "row_updated_at": func.now(),
        },
    )


def _upsert_claim_evidence_link_statement(
    link: ReportClaimEvidenceLinkRecord,
) -> Any:
    values = ReportPersistenceSerializer.claim_evidence_link_values(link)
    stmt = insert(ReportClaimEvidenceLinkModel).values(**values)
    excluded = stmt.excluded

    return stmt.on_conflict_do_update(
        index_elements=[
            "link_id",
        ],
        set_=claim_evidence_link_upsert_set_values(
            excluded,
            owner_columns=("report_id", "section_id"),
        ),
    )
