from __future__ import annotations

import json
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from typing import cast

import pytest

from core.storage.persistence.health import (
    PersistenceHealthCheckCategory,
    PersistenceHealthCheckResult,
    PersistenceHealthReport,
    PersistenceHealthStatus,
)


def test_health_check_result_normalizes_boundary_fields() -> None:
    check = PersistenceHealthCheckResult.healthy(
        category=" DATABASE_CONNECTIVITY ",
        check_name=" postgres ping ",
        component=" primary database ",
        checked_at=_checked_at(),
        message=" Connectivity verified. ",
        metadata={
            "timeout_seconds": 5,
        },
    )

    assert check.category is PersistenceHealthCheckCategory.DATABASE_CONNECTIVITY
    assert check.status is PersistenceHealthStatus.HEALTHY
    assert check.check_name == "postgres ping"
    assert check.component == "primary database"
    assert check.message == "Connectivity verified."
    assert check.is_healthy is True
    assert check.as_dict() == {
        "category": "database_connectivity",
        "check_name": "postgres ping",
        "status": "healthy",
        "message": "Connectivity verified.",
        "checked_at": "2026-06-01T14:00:00+00:00",
        "metadata": {
            "timeout_seconds": 5,
        },
        "component": "primary database",
    }
    json.dumps(
        check.as_dict(),
        sort_keys=True,
    )


def test_health_check_result_supports_required_persistence_categories() -> None:
    checked_at = _checked_at()
    checks = (
        PersistenceHealthCheckResult.healthy(
            category=PersistenceHealthCheckCategory.DATABASE_CONNECTIVITY,
            check_name="postgres_connectivity",
            message="PostgreSQL connectivity is healthy.",
            checked_at=checked_at,
        ),
        PersistenceHealthCheckResult.healthy(
            category=PersistenceHealthCheckCategory.MIGRATION_STATE,
            check_name="alembic_heads",
            message="Alembic head is current.",
            checked_at=checked_at,
            metadata={"head": "20260606_0001"},
        ),
        PersistenceHealthCheckResult.healthy(
            category=PersistenceHealthCheckCategory.METADATA_TABLE_AVAILABILITY,
            check_name="required_tables",
            message="Required metadata tables are available.",
            checked_at=checked_at,
            metadata={"tables": ("persistence_audit_events",)},
        ),
        PersistenceHealthCheckResult.healthy(
            category=PersistenceHealthCheckCategory.REPOSITORY_READINESS,
            check_name="repository_contracts",
            message="Repository contracts are ready.",
            checked_at=checked_at,
            component="PostgresReportPersistenceRepository",
        ),
        PersistenceHealthCheckResult.healthy(
            category=PersistenceHealthCheckCategory.SERVICE_READINESS,
            check_name="service_contracts",
            message="Application services are ready.",
            checked_at=checked_at,
            component="JsonPersistenceExportService",
        ),
    )

    report = PersistenceHealthReport(
        report_id=" health-report-1 ",
        checked_at=checked_at,
        checks=checks,
        metadata={"scope": "persistence_v3"},
    )

    assert report.report_id == "health-report-1"
    assert report.status is PersistenceHealthStatus.HEALTHY
    assert len(report.database_connectivity_checks) == 1
    assert len(report.migration_state_checks) == 1
    assert len(report.metadata_table_availability_checks) == 1
    assert len(report.repository_readiness_checks) == 1
    assert len(report.service_readiness_checks) == 1
    assert report.as_dict()["healthy_check_count"] == 5
    json.dumps(
        report.as_dict(),
        sort_keys=True,
    )


def test_health_report_aggregates_degraded_unknown_and_unhealthy_status() -> None:
    checked_at = _checked_at()
    degraded = PersistenceHealthReport(
        checked_at=checked_at,
        checks=(
            PersistenceHealthCheckResult.healthy(
                category="database_connectivity",
                check_name="postgres_connectivity",
                message="Connectivity verified.",
                checked_at=checked_at,
            ),
            PersistenceHealthCheckResult.degraded(
                category="migration_state",
                check_name="migration_drift",
                message="Migration state should be reviewed.",
                checked_at=checked_at,
            ),
        ),
    )
    unknown = PersistenceHealthReport(
        checked_at=checked_at,
        checks=(
            PersistenceHealthCheckResult.unknown(
                category="service_readiness",
                check_name="service_probe",
                message="Service has not been checked yet.",
                checked_at=checked_at,
            ),
        ),
    )
    unhealthy = PersistenceHealthReport(
        checked_at=checked_at,
        checks=(
            PersistenceHealthCheckResult.unhealthy(
                category="metadata_table_availability",
                check_name="missing_table",
                message="Required table is missing.",
                checked_at=checked_at,
            ),
            PersistenceHealthCheckResult.degraded(
                category="repository_readiness",
                check_name="repository_probe",
                message="Repository is partially ready.",
                checked_at=checked_at,
            ),
        ),
    )
    empty = PersistenceHealthReport(
        checked_at=checked_at,
        checks=(),
    )

    assert degraded.status is PersistenceHealthStatus.DEGRADED
    assert unknown.status is PersistenceHealthStatus.DEGRADED
    assert unhealthy.status is PersistenceHealthStatus.UNHEALTHY
    assert empty.status is PersistenceHealthStatus.UNKNOWN
    assert len(unhealthy.unhealthy_checks) == 1
    assert len(unhealthy.degraded_checks) == 1


def test_health_contracts_validate_required_fields_and_enums() -> None:
    with pytest.raises(ValueError, match="health check category"):
        PersistenceHealthCheckResult(
            category="cache",
            check_name="redis",
            status="healthy",
            message="ok",
            checked_at=_checked_at(),
        )

    with pytest.raises(ValueError, match="health status"):
        PersistenceHealthCheckResult(
            category="database_connectivity",
            check_name="postgres",
            status="ok",
            message="ok",
            checked_at=_checked_at(),
        )

    with pytest.raises(ValueError, match="check_name cannot be empty"):
        PersistenceHealthCheckResult.healthy(
            category="database_connectivity",
            check_name=" ",
            message="ok",
            checked_at=_checked_at(),
        )

    with pytest.raises(TypeError, match="checks must contain"):
        PersistenceHealthReport(
            checked_at=_checked_at(),
            checks=cast(
                tuple[PersistenceHealthCheckResult, ...],
                ("not-a-check",),
            ),
        )


def test_health_contracts_are_immutable() -> None:
    check = PersistenceHealthCheckResult.healthy(
        category="database_connectivity",
        check_name="postgres",
        message="Connectivity verified.",
        checked_at=_checked_at(),
    )

    with pytest.raises(FrozenInstanceError):
        check.message = "changed"  # type: ignore[misc]


def _checked_at() -> datetime:
    return datetime(
        2026,
        6,
        1,
        14,
        0,
        tzinfo=UTC,
    )
