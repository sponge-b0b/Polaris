from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from core.storage.persistence.reports import (
    ReportArtifactRecord,
    ReportPersistenceBundle,
    ReportPersistenceResult,
    ReportPublicationRecord,
    ReportRecord,
    ReportSectionRecord,
    ReportVersionRecord,
    new_report_publication_id,
    new_report_version_id,
)


def test_report_record_is_typed_and_immutable() -> None:
    record = ReportRecord(
        report_id="morning_report:exec-1",
        report_type="morning_report",
        title="Morning Report",
        generated_at=datetime(2026, 5, 30, tzinfo=UTC),
        markdown_body="# Full report\n",
        structured_payload={"symbol": "SPY"},
    )

    assert record.report_id == "morning_report:exec-1"
    assert record.structured_payload["symbol"] == "SPY"

    with pytest.raises(FrozenInstanceError):
        record.title = "Changed"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("field_name", "kwargs"),
    [
        ("report_id", {"report_id": " "}),
        ("report_type", {"report_type": ""}),
        ("title", {"title": " "}),
        ("markdown_body", {"markdown_body": ""}),
    ],
)
def test_report_record_validates_required_fields(
    field_name: str,
    kwargs: dict[str, object],
) -> None:
    values: dict[str, object] = {
        "report_id": "morning_report:exec-1",
        "report_type": "morning_report",
        "title": "Morning Report",
        "generated_at": datetime(2026, 5, 30, tzinfo=UTC),
        "markdown_body": "# Full report\n",
    }
    values.update(kwargs)

    with pytest.raises(ValueError, match=field_name):
        ReportRecord(**values)  # type: ignore[arg-type]


def test_report_section_and_artifact_records_validate_required_fields() -> None:
    section = ReportSectionRecord(
        section_id="report-1:section:summary",
        report_id="report-1",
        section_key="summary",
        title="Summary",
        display_order=1,
        content_payload={"summary": "full text"},
    )
    artifact = ReportArtifactRecord(
        artifact_id="report-1:artifact:1",
        report_id="report-1",
        artifact_type="markdown",
        artifact_uri="/tmp/report.md",
    )

    assert section.section_key == "summary"
    assert artifact.artifact_type == "markdown"

    with pytest.raises(ValueError, match="display_order"):
        ReportSectionRecord(
            section_id="report-1:section:summary",
            report_id="report-1",
            section_key="summary",
            title="Summary",
            display_order=-1,
        )

    with pytest.raises(ValueError, match="artifact_uri"):
        ReportArtifactRecord(
            artifact_id="report-1:artifact:1",
            report_id="report-1",
            artifact_type="markdown",
            artifact_uri=" ",
        )


def test_report_persistence_bundle_and_result_validate_state() -> None:
    report = ReportRecord(
        report_id="morning_report:exec-1",
        report_type="morning_report",
        title="Morning Report",
        generated_at=datetime(2026, 5, 30, tzinfo=UTC),
        markdown_body="# Full report\n",
    )
    bundle = ReportPersistenceBundle(
        report=report,
    )
    success = ReportPersistenceResult.succeeded(
        report_id=report.report_id,
        records_persisted=1,
    )
    failure = ReportPersistenceResult.failed(
        "database unavailable",
    )

    assert bundle.report is report
    assert success.success is True
    assert success.report_id == report.report_id
    assert failure.success is False

    with pytest.raises(ValueError, match="error"):
        ReportPersistenceResult.failed(
            " ",
        )

    with pytest.raises(ValueError, match="successful"):
        ReportPersistenceResult(
            success=True,
            report_id=report.report_id,
            error="unexpected",
        )

    with pytest.raises(ValueError, match="report_id"):
        ReportPersistenceResult(
            success=True,
        )


def test_report_version_record_links_to_report_and_preserves_full_content() -> None:
    markdown_body = "# Full Report\n" + ("Untruncated report text. " * 20)
    version = ReportVersionRecord(
        version_id="morning_report:exec-1:version:1",
        report_id="morning_report:exec-1",
        version_number=1,
        created_at=datetime(2026, 5, 30, 14, tzinfo=UTC),
        title="Morning Report",
        markdown_body=markdown_body,
        structured_payload={"full_payload": "x" * 2000},
        metadata={"source": "contract-test"},
    )

    assert version.report_id == "morning_report:exec-1"
    assert version.version_number == 1
    assert version.markdown_body == markdown_body
    assert version.structured_payload == {"full_payload": "x" * 2000}


@pytest.mark.parametrize(
    ("field_name", "kwargs"),
    [
        ("version_id", {"version_id": " "}),
        ("report_id", {"report_id": ""}),
        ("version_number", {"version_number": 0}),
        ("markdown_body", {"markdown_body": " "}),
    ],
)
def test_report_version_record_validates_required_fields(
    field_name: str,
    kwargs: dict[str, object],
) -> None:
    values: dict[str, object] = {
        "version_id": "morning_report:exec-1:version:1",
        "report_id": "morning_report:exec-1",
        "version_number": 1,
        "created_at": datetime(2026, 5, 30, 14, tzinfo=UTC),
        "markdown_body": "# Full report\n",
    }
    values.update(kwargs)

    with pytest.raises(ValueError, match=field_name):
        ReportVersionRecord(**values)  # type: ignore[arg-type]


def test_report_publication_record_links_to_report_and_optional_version() -> None:
    requested_at = datetime(2026, 5, 30, 14, tzinfo=UTC)
    published_at = datetime(2026, 5, 30, 14, 1, tzinfo=UTC)
    publication = ReportPublicationRecord(
        publication_id="morning_report:exec-1:publication:markdown",
        report_id="morning_report:exec-1",
        version_id="morning_report:exec-1:version:1",
        publication_target="markdown_archive",
        publication_status="published",
        requested_at=requested_at,
        published_at=published_at,
        artifact_uri="/reports/morning_report.md",
        metadata={"source": "contract-test"},
    )

    assert publication.report_id == "morning_report:exec-1"
    assert publication.version_id == "morning_report:exec-1:version:1"
    assert publication.publication_target == "markdown_archive"
    assert publication.published_at == published_at


@pytest.mark.parametrize(
    ("field_name", "kwargs"),
    [
        ("publication_id", {"publication_id": " "}),
        ("report_id", {"report_id": ""}),
        ("publication_target", {"publication_target": " "}),
        ("publication_status", {"publication_status": ""}),
        ("version_id", {"version_id": " "}),
        (
            "published_at",
            {
                "published_at": datetime(2026, 5, 30, 13, tzinfo=UTC),
            },
        ),
    ],
)
def test_report_publication_record_validates_required_fields(
    field_name: str,
    kwargs: dict[str, object],
) -> None:
    values: dict[str, object] = {
        "publication_id": "morning_report:exec-1:publication:markdown",
        "report_id": "morning_report:exec-1",
        "version_id": "morning_report:exec-1:version:1",
        "publication_target": "markdown_archive",
        "publication_status": "published",
        "requested_at": datetime(2026, 5, 30, 14, tzinfo=UTC),
    }
    values.update(kwargs)

    with pytest.raises(ValueError, match=field_name):
        ReportPublicationRecord(**values)  # type: ignore[arg-type]


def test_report_version_and_publication_id_helpers_are_stable() -> None:
    requested_at = datetime(2026, 5, 30, 14, tzinfo=UTC)
    version_id = new_report_version_id(
        "morning_report:exec-1",
        2,
    )
    publication_id = new_report_publication_id(
        report_id="morning_report:exec-1",
        version_id=version_id,
        publication_target="markdown_archive",
        requested_at=requested_at,
    )

    assert version_id == "morning_report:exec-1:version:2"
    assert publication_id == (
        "morning_report:exec-1:publication:markdown_archive:"
        "2026-05-30T14:00:00+00:00:morning_report:exec-1:version:2"
    )


def test_report_persistence_bundle_can_include_versions_and_publications() -> None:
    report = ReportRecord(
        report_id="morning_report:exec-1",
        report_type="morning_report",
        title="Morning Report",
        generated_at=datetime(2026, 5, 30, tzinfo=UTC),
        markdown_body="# Full report\n",
    )
    version = ReportVersionRecord(
        version_id="morning_report:exec-1:version:1",
        report_id=report.report_id,
        version_number=1,
        created_at=datetime(2026, 5, 30, 14, tzinfo=UTC),
        markdown_body="# Full report\n",
    )
    publication = ReportPublicationRecord(
        publication_id="morning_report:exec-1:publication:markdown",
        report_id=report.report_id,
        version_id=version.version_id,
        publication_target="markdown_archive",
        publication_status="pending",
        requested_at=datetime(2026, 5, 30, 14, tzinfo=UTC),
    )

    bundle = ReportPersistenceBundle(
        report=report,
        versions=(version,),
        publications=(publication,),
    )

    assert bundle.versions == (version,)
    assert bundle.publications == (publication,)
