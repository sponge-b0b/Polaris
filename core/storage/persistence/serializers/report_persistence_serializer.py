from __future__ import annotations

from typing import Any, cast

from core.database.models.reports import (
    ReportArtifactModel,
    ReportModel,
    ReportPublicationModel,
    ReportSectionModel,
    ReportVersionModel,
)
from core.storage.persistence.reports.report_persistence_models import (
    JsonObject,
    ReportArtifactRecord,
    ReportPublicationRecord,
    ReportRecord,
    ReportSectionRecord,
    ReportVersionRecord,
)


class ReportPersistenceSerializer:
    """
    Serializer between typed report persistence records and SQLAlchemy models.

    JSON dictionaries are introduced here because this module is the database
    persistence boundary. Application/report layers should continue to use the
    typed records from ``core.storage.persistence.reports``.
    """

    @staticmethod
    def report_values(
        record: ReportRecord,
    ) -> dict[str, Any]:
        return {
            "report_id": record.report_id,
            "report_type": record.report_type,
            "title": record.title,
            "subtitle": record.subtitle,
            "workflow_name": record.workflow_name,
            "execution_id": record.execution_id,
            "runtime_id": record.runtime_id,
            "status": record.status,
            "generated_at": record.generated_at,
            "markdown_body": record.markdown_body,
            "structured_payload": dict(record.structured_payload),
            "metadata_payload": dict(record.metadata),
        }

    @staticmethod
    def section_values(
        record: ReportSectionRecord,
    ) -> dict[str, Any]:
        return {
            "section_id": record.section_id,
            "report_id": record.report_id,
            "section_key": record.section_key,
            "title": record.title,
            "display_order": record.display_order,
            "summary": record.summary,
            "markdown_body": record.markdown_body,
            "content_payload": dict(record.content_payload),
            "metadata_payload": dict(record.metadata),
        }

    @staticmethod
    def artifact_values(
        record: ReportArtifactRecord,
    ) -> dict[str, Any]:
        return {
            "artifact_id": record.artifact_id,
            "report_id": record.report_id,
            "section_id": record.section_id,
            "artifact_type": record.artifact_type,
            "artifact_uri": record.artifact_uri,
            "mime_type": record.mime_type,
            "description": record.description,
            "metadata_payload": dict(record.metadata),
        }

    @staticmethod
    def version_values(
        record: ReportVersionRecord,
    ) -> dict[str, Any]:
        return {
            "version_id": record.version_id,
            "report_id": record.report_id,
            "version_number": record.version_number,
            "created_at": record.created_at,
            "title": record.title,
            "subtitle": record.subtitle,
            "markdown_body": record.markdown_body,
            "change_summary": record.change_summary,
            "created_by": record.created_by,
            "structured_payload": dict(record.structured_payload),
            "metadata_payload": dict(record.metadata),
        }

    @staticmethod
    def publication_values(
        record: ReportPublicationRecord,
    ) -> dict[str, Any]:
        return {
            "publication_id": record.publication_id,
            "report_id": record.report_id,
            "version_id": record.version_id,
            "publication_target": record.publication_target,
            "publication_status": record.publication_status,
            "requested_at": record.requested_at,
            "published_at": record.published_at,
            "artifact_uri": record.artifact_uri,
            "error": record.error,
            "metadata_payload": dict(record.metadata),
        }

    @staticmethod
    def report_from_model(
        model: ReportModel,
    ) -> ReportRecord:
        return ReportRecord(
            report_id=model.report_id,
            report_type=model.report_type,
            title=model.title,
            subtitle=model.subtitle,
            workflow_name=model.workflow_name,
            execution_id=model.execution_id,
            runtime_id=model.runtime_id,
            status=model.status,
            generated_at=model.generated_at,
            markdown_body=model.markdown_body,
            structured_payload=cast(
                JsonObject,
                model.structured_payload,
            ),
            metadata=cast(
                JsonObject,
                model.metadata_payload,
            ),
        )

    @staticmethod
    def section_from_model(
        model: ReportSectionModel,
    ) -> ReportSectionRecord:
        return ReportSectionRecord(
            section_id=model.section_id,
            report_id=model.report_id,
            section_key=model.section_key,
            title=model.title,
            display_order=model.display_order,
            summary=model.summary,
            markdown_body=model.markdown_body,
            content_payload=cast(
                JsonObject,
                model.content_payload,
            ),
            metadata=cast(
                JsonObject,
                model.metadata_payload,
            ),
        )

    @staticmethod
    def artifact_from_model(
        model: ReportArtifactModel,
    ) -> ReportArtifactRecord:
        return ReportArtifactRecord(
            artifact_id=model.artifact_id,
            report_id=model.report_id,
            section_id=model.section_id,
            artifact_type=model.artifact_type,
            artifact_uri=model.artifact_uri,
            mime_type=model.mime_type,
            description=model.description,
            metadata=cast(
                JsonObject,
                model.metadata_payload,
            ),
        )

    @staticmethod
    def version_from_model(
        model: ReportVersionModel,
    ) -> ReportVersionRecord:
        return ReportVersionRecord(
            version_id=model.version_id,
            report_id=model.report_id,
            version_number=model.version_number,
            created_at=model.created_at,
            title=model.title,
            subtitle=model.subtitle,
            markdown_body=model.markdown_body,
            change_summary=model.change_summary,
            created_by=model.created_by,
            structured_payload=cast(
                JsonObject,
                model.structured_payload,
            ),
            metadata=cast(
                JsonObject,
                model.metadata_payload,
            ),
        )

    @staticmethod
    def publication_from_model(
        model: ReportPublicationModel,
    ) -> ReportPublicationRecord:
        return ReportPublicationRecord(
            publication_id=model.publication_id,
            report_id=model.report_id,
            version_id=model.version_id,
            publication_target=model.publication_target,
            publication_status=model.publication_status,
            requested_at=model.requested_at,
            published_at=model.published_at,
            artifact_uri=model.artifact_uri,
            error=model.error,
            metadata=cast(
                JsonObject,
                model.metadata_payload,
            ),
        )
