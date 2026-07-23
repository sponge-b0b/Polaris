from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest

from application.persistence.retention import (
    RetentionPersistenceService,
    RetentionPlanningFilters,
)
from core.storage.persistence.retention import (
    PersistenceRetentionCandidateRecord,
    PersistenceRetentionPeriod,
    PersistenceRetentionPlanAction,
    PersistenceRetentionPolicyRecord,
    new_persistence_retention_policy_id,
)


@pytest.mark.asyncio
async def test_retention_planning_reports_archive_and_delete_candidates_without_execution() -> (  # noqa: E501
    None
):
    service = RetentionPersistenceService()
    as_of = _as_of()

    result = await service.plan_retention(
        policies=(
            _policy(
                domain="reports",
                days=30,
                archive_before_delete=True,
                deletion_eligible=True,
            ),
            _policy(
                domain="telemetry_events",
                days=7,
                archive_before_delete=False,
                deletion_eligible=True,
            ),
        ),
        candidates=(
            _candidate(
                domain="reports",
                record_id="report-1",
                age_days=45,
            ),
            _candidate(
                domain="telemetry_events",
                record_id="event-1",
                age_days=10,
            ),
        ),
        as_of=as_of,
    )

    assert result.dry_run is True
    assert len(result.archive_candidates) == 1
    assert len(result.delete_candidates) == 1
    assert result.archive_candidates[0].candidate.record_id == "report-1"
    assert result.archive_candidates[0].action is PersistenceRetentionPlanAction.ARCHIVE
    assert result.delete_candidates[0].candidate.record_id == "event-1"
    assert result.delete_candidates[0].action is PersistenceRetentionPlanAction.DELETE
    assert all(candidate.dry_run is True for candidate in result.candidates)
    json.dumps(
        result.as_dict(),
        sort_keys=True,
    )


@pytest.mark.asyncio
async def test_retention_planning_retains_recent_and_unconfigured_candidates() -> None:
    service = RetentionPersistenceService()

    result = await service.plan_retention(
        policies=(
            _policy(
                domain="reports",
                days=30,
                archive_before_delete=True,
                deletion_eligible=True,
            ),
        ),
        candidates=(
            _candidate(
                domain="reports",
                record_id="report-new",
                age_days=5,
            ),
            _candidate(
                domain="news_articles",
                record_id="news-1",
                age_days=90,
            ),
        ),
        as_of=_as_of(),
    )

    assert len(result.retained_candidates) == 2
    assert not result.archive_candidates
    assert not result.delete_candidates
    assert result.retained_candidates[0].reason == (
        "Candidate remains within the configured retention period."
    )
    assert result.retained_candidates[1].reason == (
        "No retention policy exists for candidate domain."
    )


@pytest.mark.asyncio
async def test_retention_planning_skips_disabled_policies_and_future_records() -> None:
    service = RetentionPersistenceService()

    result = await service.plan_retention(
        policies=(
            _policy(
                domain="reports",
                days=30,
                archive_before_delete=True,
                deletion_eligible=True,
                enabled=False,
            ),
            _policy(
                domain="macro_observations",
                days=30,
                archive_before_delete=False,
                deletion_eligible=True,
            ),
        ),
        candidates=(
            _candidate(
                domain="reports",
                record_id="report-disabled",
                age_days=90,
            ),
            PersistenceRetentionCandidateRecord(
                domain="macro_observations",
                record_id="macro-future",
                record_timestamp=_as_of()
                + timedelta(
                    days=1,
                ),
            ),
        ),
        as_of=_as_of(),
    )

    assert len(result.skipped_candidates) == 1
    assert result.skipped_candidates[0].reason == "Retention policy is disabled."
    assert len(result.retained_candidates) == 1
    assert result.retained_candidates[0].reason == (
        "Candidate timestamp is after the planning timestamp."
    )


@pytest.mark.asyncio
async def test_retention_planning_filters_domains() -> None:
    service = RetentionPersistenceService()

    result = await service.plan_retention(
        policies=(
            _policy(
                domain="reports",
                days=30,
                archive_before_delete=True,
                deletion_eligible=True,
            ),
            _policy(
                domain="telemetry_events",
                days=7,
                archive_before_delete=False,
                deletion_eligible=True,
            ),
        ),
        candidates=(
            _candidate(
                domain="reports",
                record_id="report-1",
                age_days=45,
            ),
            _candidate(
                domain="telemetry_events",
                record_id="event-1",
                age_days=10,
            ),
        ),
        as_of=_as_of(),
        filters=RetentionPlanningFilters(
            domains=(" Reports ",),
        ),
    )

    assert len(result.candidates) == 1
    assert result.candidates[0].candidate.domain == "reports"
    assert result.metadata["domains"] == ("reports",)


@pytest.mark.asyncio
async def test_retention_planning_rejects_duplicate_policy_domains() -> None:
    service = RetentionPersistenceService()

    with pytest.raises(
        ValueError,
        match="duplicate retention policy for domain: reports",
    ):
        await service.plan_retention(
            policies=(
                _policy(
                    domain="reports",
                    days=30,
                    archive_before_delete=True,
                    deletion_eligible=True,
                ),
                _policy(
                    domain=" Reports ",
                    days=60,
                    archive_before_delete=False,
                    deletion_eligible=True,
                ),
            ),
            candidates=(),
            as_of=_as_of(),
        )


@pytest.mark.asyncio
async def test_build_archive_markers_from_archive_candidates_only() -> None:
    service = RetentionPersistenceService()
    result = await service.plan_retention(
        policies=(
            _policy(
                domain="reports",
                days=30,
                archive_before_delete=True,
                deletion_eligible=True,
            ),
            _policy(
                domain="telemetry_events",
                days=7,
                archive_before_delete=False,
                deletion_eligible=True,
            ),
        ),
        candidates=(
            _candidate(
                domain="reports",
                record_id="report-1",
                age_days=45,
            ),
            _candidate(
                domain="telemetry_events",
                record_id="event-1",
                age_days=10,
            ),
        ),
        as_of=_as_of(),
    )

    markers = service.build_archive_markers(
        plan=result,
        marked_timestamp=_as_of(),
    )

    assert len(markers) == 1
    marker = markers[0]
    assert marker.marker_id == "persistence_archive_marker:reports:report-1"
    assert marker.domain == "reports"
    assert marker.record_id == "report-1"
    assert marker.record_type == "report"
    assert marker.policy_id == "persistence_retention_policy:reports"
    assert marker.dry_run is True
    assert marker.metadata == {
        "source_action": "archive",
        "source_plan_dry_run": True,
        "retention_period_days": 30,
    }
    assert marker.audit_metadata["marker_type"] == "persistence_archive_marker"
    assert marker.audit_metadata["dry_run"] is True
    assert "event-1" not in json.dumps(
        tuple(archive_marker.as_dict() for archive_marker in markers),
        sort_keys=True,
    )


def test_retention_planning_filters_normalize_domains() -> None:
    filters = RetentionPlanningFilters(
        domains=(
            " Reports ",
            "reports",
            "NEWS_ARTICLES",
        ),
    )

    assert filters.domains == (
        "reports",
        "news_articles",
    )
    assert filters.allows_domain(
        "reports",
    )
    assert not filters.allows_domain(
        "telemetry_events",
    )


def _policy(
    *,
    domain: str,
    days: int,
    archive_before_delete: bool,
    deletion_eligible: bool,
    enabled: bool = True,
) -> PersistenceRetentionPolicyRecord:
    return PersistenceRetentionPolicyRecord(
        policy_id=new_persistence_retention_policy_id(
            domain=domain,
        ),
        domain=domain,
        retention_period=PersistenceRetentionPeriod(
            days=days,
        ),
        archive_before_delete=archive_before_delete,
        deletion_eligible=deletion_eligible,
        enabled=enabled,
    )


def _candidate(
    *,
    domain: str,
    record_id: str,
    age_days: int,
) -> PersistenceRetentionCandidateRecord:
    return PersistenceRetentionCandidateRecord(
        domain=domain,
        record_id=record_id,
        record_timestamp=_as_of()
        - timedelta(
            days=age_days,
        ),
        record_type=domain.rstrip("s"),
    )


def _as_of() -> datetime:
    return datetime(
        2026,
        6,
        1,
        14,
        0,
        tzinfo=UTC,
    )
