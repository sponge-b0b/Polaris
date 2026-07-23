from __future__ import annotations

import json
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from typing import cast

import pytest

from core.storage.persistence.retention import (
    PersistenceArchiveMarkerRecord,
    PersistenceRetentionPeriod,
    PersistenceRetentionPolicyRecord,
    new_persistence_archive_marker_id,
    new_persistence_retention_policy_id,
)


def test_retention_period_exposes_typed_duration_and_boundary_dict() -> None:
    period = PersistenceRetentionPeriod(
        days=30,
    )

    assert period.duration.days == 30
    assert period.as_dict() == {
        "days": 30,
        "seconds": 2_592_000,
    }


@pytest.mark.parametrize(
    "days",
    [
        0,
        -1,
        True,
    ],
)
def test_retention_period_requires_positive_day_count(days: int) -> None:
    with pytest.raises(
        ValueError,
        match="retention period days must be positive",
    ):
        PersistenceRetentionPeriod(
            days=days,
        )


def test_retention_policy_normalizes_domain_and_exposes_lifecycle_flags() -> None:
    policy = PersistenceRetentionPolicyRecord(
        policy_id="policy-1",
        domain=" Reports ",
        retention_period=PersistenceRetentionPeriod(
            days=365,
        ),
        archive_before_delete=True,
        deletion_eligible=False,
        description=" Archive reports before manual review ",
        metadata={
            "owner": "persistence",
        },
    )

    assert policy.domain == "reports"
    assert policy.description == "Archive reports before manual review"
    assert policy.can_archive is True
    assert policy.can_delete is False
    assert policy.as_dict() == {
        "policy_id": "policy-1",
        "domain": "reports",
        "retention_period": {
            "days": 365,
            "seconds": 31_536_000,
        },
        "archive_before_delete": True,
        "deletion_eligible": False,
        "enabled": True,
        "metadata": {
            "owner": "persistence",
        },
        "description": "Archive reports before manual review",
    }
    json.dumps(
        policy.as_dict(),
        sort_keys=True,
    )


def test_disabled_retention_policy_cannot_archive_or_delete() -> None:
    policy = PersistenceRetentionPolicyRecord(
        policy_id="policy-1",
        domain="news_articles",
        retention_period=PersistenceRetentionPeriod(
            days=90,
        ),
        archive_before_delete=True,
        deletion_eligible=True,
        enabled=False,
    )

    assert policy.can_archive is False
    assert policy.can_delete is False


def test_retention_policy_requires_typed_period() -> None:
    with pytest.raises(
        TypeError,
        match="retention_period must be a PersistenceRetentionPeriod",
    ):
        PersistenceRetentionPolicyRecord(
            policy_id="policy-1",
            domain="reports",
            retention_period=cast(
                PersistenceRetentionPeriod,
                365,
            ),
            archive_before_delete=True,
            deletion_eligible=True,
        )


def test_retention_policy_is_immutable() -> None:
    policy = PersistenceRetentionPolicyRecord(
        policy_id="policy-1",
        domain="reports",
        retention_period=PersistenceRetentionPeriod(
            days=365,
        ),
        archive_before_delete=True,
        deletion_eligible=True,
    )

    with pytest.raises(
        FrozenInstanceError,
    ):
        policy.domain = "other"  # type: ignore[misc]


def test_retention_policy_id_is_stable_by_domain() -> None:
    assert (
        new_persistence_retention_policy_id(
            domain=" Reports ",
        )
        == "persistence_retention_policy:reports"
    )

    with pytest.raises(
        ValueError,
        match="domain cannot be empty",
    ):
        new_persistence_retention_policy_id(
            domain=" ",
        )


def test_archive_marker_is_typed_dry_run_and_audit_metadata_ready() -> None:
    marker = PersistenceArchiveMarkerRecord(
        marker_id=new_persistence_archive_marker_id(
            domain=" Reports ",
            record_id=" report-1 ",
        ),
        domain=" Reports ",
        record_id=" report-1 ",
        record_type=" Report ",
        policy_id=" policy-1 ",
        marked_timestamp=_marked_timestamp(),
        reason=" Candidate exceeds retention period. ",
        metadata={
            "source_action": "archive",
        },
    )

    assert marker.marker_id == "persistence_archive_marker:reports:report-1"
    assert marker.domain == "reports"
    assert marker.record_id == "report-1"
    assert marker.record_type == "Report"
    assert marker.policy_id == "policy-1"
    assert marker.dry_run is True
    assert marker.audit_metadata == {
        "archive_marker_id": "persistence_archive_marker:reports:report-1",
        "domain": "reports",
        "record_id": "report-1",
        "marked_timestamp": "2026-06-01T14:00:00+00:00",
        "reason": "Candidate exceeds retention period.",
        "dry_run": True,
        "marker_type": "persistence_archive_marker",
        "metadata": {
            "source_action": "archive",
        },
        "record_type": "Report",
        "policy_id": "policy-1",
    }
    assert marker.as_dict()["marker_id"] == marker.marker_id
    json.dumps(
        marker.as_dict(),
        sort_keys=True,
    )


def test_archive_marker_rejects_non_dry_run() -> None:
    with pytest.raises(
        ValueError,
        match="archive marker records must be dry-run only",
    ):
        PersistenceArchiveMarkerRecord(
            marker_id="marker-1",
            domain="reports",
            record_id="report-1",
            marked_timestamp=_marked_timestamp(),
            reason="archive candidate",
            dry_run=False,
        )


def test_archive_marker_id_is_stable_by_domain_and_record() -> None:
    assert (
        new_persistence_archive_marker_id(
            domain=" Reports ",
            record_id=" report-1 ",
        )
        == "persistence_archive_marker:reports:report-1"
    )

    with pytest.raises(
        ValueError,
        match="record_id cannot be empty",
    ):
        new_persistence_archive_marker_id(
            domain="reports",
            record_id=" ",
        )


def test_archive_marker_is_immutable() -> None:
    marker = PersistenceArchiveMarkerRecord(
        marker_id="marker-1",
        domain="reports",
        record_id="report-1",
        marked_timestamp=_marked_timestamp(),
        reason="archive candidate",
    )

    with pytest.raises(
        FrozenInstanceError,
    ):
        marker.record_id = "other"  # type: ignore[misc]


def _marked_timestamp() -> datetime:
    return datetime(
        2026,
        6,
        1,
        14,
        0,
        tzinfo=UTC,
    )
