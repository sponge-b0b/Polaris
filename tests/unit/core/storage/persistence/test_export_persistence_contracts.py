from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from core.storage.persistence.export import (
    PersistenceExportDestination,
    PersistenceExportDestinationType,
    PersistenceExportFormat,
    PersistenceExportRequest,
    PersistenceExportResult,
)
from core.storage.persistence.query import PersistenceTimeRange


def test_export_destination_normalizes_type_uri_and_metadata() -> None:
    destination = PersistenceExportDestination(
        destination_type=" LOCAL_FILE ",
        uri=" /tmp/reports.json ",
        metadata={"compression": "gzip"},
    )

    assert destination.destination_type is PersistenceExportDestinationType.LOCAL_FILE
    assert destination.uri == "/tmp/reports.json"
    assert destination.as_dict() == {
        "destination_type": "local_file",
        "uri": "/tmp/reports.json",
        "metadata": {"compression": "gzip"},
    }

    with pytest.raises(ValueError, match="destination_type"):
        PersistenceExportDestination(
            destination_type="warehouse",
        )

    with pytest.raises(FrozenInstanceError):
        destination.uri = "/tmp/other.json"  # type: ignore[misc]


def test_export_request_supports_domain_time_range_format_and_destination_metadata() -> (  # noqa: E501 - descriptive pytest node id
    None
):
    start = datetime(2026, 6, 1, 9, tzinfo=UTC)
    end = datetime(2026, 6, 1, 10, tzinfo=UTC)
    request = PersistenceExportRequest(
        export_id=" export-1 ",
        domains=(
            " Reports ",
            "recommendations",
            "reports",
        ),
        time_range=PersistenceTimeRange(
            start=start,
            end=end,
        ),
        export_format="JSON",
        destination=PersistenceExportDestination(
            destination_type=PersistenceExportDestinationType.OBJECT_STORE,
            uri=" s3://bucket/reports/export-1.json ",
            metadata={"bucket": "bucket"},
        ),
        metadata={"requested_by": "unit-test"},
    )

    assert request.export_id == "export-1"
    assert request.domains == (
        "reports",
        "recommendations",
    )
    assert request.domain is None
    assert request.export_format is PersistenceExportFormat.JSON
    assert request.as_dict() == {
        "export_id": "export-1",
        "domains": (
            "reports",
            "recommendations",
        ),
        "time_range": {
            "start": start.isoformat(),
            "end": end.isoformat(),
        },
        "format": "json",
        "destination": {
            "destination_type": "object_store",
            "uri": "s3://bucket/reports/export-1.json",
            "metadata": {"bucket": "bucket"},
        },
        "metadata": {"requested_by": "unit-test"},
    }


def test_export_request_validates_domains_time_range_and_format() -> None:
    with pytest.raises(ValueError, match="domains"):
        PersistenceExportRequest(
            domains=(),
        )

    with pytest.raises(ValueError, match=r"domains\[0\]"):
        PersistenceExportRequest(
            domains=(" ",),
        )

    with pytest.raises(ValueError, match="export_format"):
        PersistenceExportRequest(
            domains=("reports",),
            export_format="parquet",
        )

    with pytest.raises(ValueError, match="end"):
        PersistenceExportRequest(
            domains=("reports",),
            time_range=PersistenceTimeRange(
                start=datetime(2026, 6, 1, 10, tzinfo=UTC),
                end=datetime(2026, 6, 1, 9, tzinfo=UTC),
            ),
        )


def test_export_request_exposes_single_domain_convenience_property() -> None:
    request = PersistenceExportRequest(
        domains=(" reports ",),
    )

    assert request.domain == "reports"
    assert (
        request.destination.destination_type is PersistenceExportDestinationType.MEMORY
    )
    assert request.export_format is PersistenceExportFormat.JSON
    assert request.as_dict()["destination"] == {
        "destination_type": "memory",
        "metadata": {},
    }


def test_export_result_success_and_failure_contracts() -> None:
    request = PersistenceExportRequest(
        domains=("reports", "signals"),
    )
    success = PersistenceExportResult.succeeded(
        request=request,
        records_exported=3,
        domain_record_counts={
            " Reports ": 2,
            "signals": 1,
        },
        artifact_uri=" /tmp/export.json ",
        metadata={"serializer": "json"},
    )
    failure = PersistenceExportResult.failed(
        request=request,
        error="No serializer configured.",
    )

    assert success.success is True
    assert success.records_exported == 3
    assert success.domain_record_counts == {
        "reports": 2,
        "signals": 1,
    }
    assert success.as_dict()["artifact_uri"] == "/tmp/export.json"
    assert success.as_dict()["metadata"] == {"serializer": "json"}
    assert failure.success is False
    assert failure.records_exported == 0
    assert failure.as_dict()["error"] == "No serializer configured."


def test_export_result_validates_state() -> None:
    request = PersistenceExportRequest(
        domains=("reports",),
    )

    with pytest.raises(ValueError, match="records_exported"):
        PersistenceExportResult(
            request=request,
            success=True,
            records_exported=-1,
        )

    with pytest.raises(ValueError, match="error"):
        PersistenceExportResult(
            request=request,
            success=False,
        )

    with pytest.raises(ValueError, match="error"):
        PersistenceExportResult(
            request=request,
            success=True,
            error="unexpected",
        )

    with pytest.raises(ValueError, match="domain record counts"):
        PersistenceExportResult.succeeded(
            request=request,
            records_exported=0,
            domain_record_counts={"reports": -1},
        )
