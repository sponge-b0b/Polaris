from __future__ import annotations

from datetime import UTC, datetime

from core.storage.persistence.reports import (
    ReportArtifactRecord,
    ReportPublicationRecord,
    ReportRecord,
    ReportSectionRecord,
    ReportVersionRecord,
)
from core.storage.persistence.serializers.report_persistence_serializer import (
    ReportPersistenceSerializer,
)


def test_report_serializer_preserves_full_markdown_and_structured_payload() -> None:
    full_markdown = "# Morning Report\n" + ("Full LLM response. " * 50)
    record = ReportRecord(
        report_id="morning_report:exec-1",
        report_type="morning_report",
        title="Morning Report",
        generated_at=datetime(2026, 5, 30, tzinfo=UTC),
        markdown_body=full_markdown,
        structured_payload={"full_response": "x" * 4000},
        metadata={"symbol": "SPY"},
    )

    values = ReportPersistenceSerializer.report_values(
        record,
    )

    assert values["markdown_body"] == full_markdown
    assert values["structured_payload"] == {"full_response": "x" * 4000}
    assert values["metadata_payload"] == {"symbol": "SPY"}


def test_report_serializer_converts_section_and_artifact_records() -> None:
    section = ReportSectionRecord(
        section_id="morning_report:exec-1:section:macro",
        report_id="morning_report:exec-1",
        section_key="macro",
        title="Macro",
        display_order=3,
        summary="Full section response",
        content_payload={"summary": "Full section response"},
    )
    artifact = ReportArtifactRecord(
        artifact_id="morning_report:exec-1:artifact:1",
        report_id="morning_report:exec-1",
        artifact_type="markdown",
        artifact_uri="/tmp/morning_report.md",
        mime_type="text/markdown",
    )

    section_values = ReportPersistenceSerializer.section_values(
        section,
    )
    artifact_values = ReportPersistenceSerializer.artifact_values(
        artifact,
    )

    assert section_values["content_payload"] == {"summary": "Full section response"}
    assert artifact_values["artifact_uri"] == "/tmp/morning_report.md"
    assert artifact_values["mime_type"] == "text/markdown"


def test_report_serializer_converts_version_and_publication_records() -> None:
    full_markdown = "# Versioned Report\n" + ("Full content. " * 50)
    created_at = datetime(2026, 5, 30, 14, tzinfo=UTC)
    published_at = datetime(2026, 5, 30, 14, 5, tzinfo=UTC)
    version = ReportVersionRecord(
        version_id="morning_report:exec-1:version:1",
        report_id="morning_report:exec-1",
        version_number=1,
        created_at=created_at,
        title="Morning Report",
        markdown_body=full_markdown,
        structured_payload={"full_response": "x" * 4000},
        metadata={"source": "serializer-test"},
    )
    publication = ReportPublicationRecord(
        publication_id="morning_report:exec-1:publication:markdown",
        report_id="morning_report:exec-1",
        version_id=version.version_id,
        publication_target="markdown_archive",
        publication_status="published",
        requested_at=created_at,
        published_at=published_at,
        artifact_uri="/reports/morning_report.md",
        metadata={"source": "serializer-test"},
    )

    version_values = ReportPersistenceSerializer.version_values(
        version,
    )
    publication_values = ReportPersistenceSerializer.publication_values(
        publication,
    )

    assert version_values["markdown_body"] == full_markdown
    assert version_values["structured_payload"] == {"full_response": "x" * 4000}
    assert version_values["metadata_payload"] == {"source": "serializer-test"}
    assert publication_values["version_id"] == version.version_id
    assert publication_values["publication_target"] == "markdown_archive"
    assert publication_values["published_at"] == published_at
