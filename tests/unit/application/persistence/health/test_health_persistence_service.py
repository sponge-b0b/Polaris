from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import SQLAlchemyError

from application.persistence.health import (
    HealthPersistenceFilters,
    HealthPersistenceService,
)
from core.storage.persistence.health import PersistenceHealthStatus


@pytest.mark.asyncio
async def test_health_service_reports_successful_persistence_readiness() -> None:
    service = HealthPersistenceService(
        connectivity_checker=_successful_connectivity,
        database_table_loader=_tables(
            "reports",
            "recommendations",
        ),
        current_revision_loader=_revision(
            "20260606_0001",
        ),
        head_revision_loader=lambda: "20260606_0001",
        metadata_table_loader=lambda: (
            "reports",
            "recommendations",
        ),
        schema_drift_loader=_schema_drift(),
    )

    report = await service.check_health(
        checked_at=_checked_at(),
        filters=HealthPersistenceFilters(
            required_tables=(
                " reports ",
                "recommendations",
                "reports",
            ),
            repository_components=("ReportPersistenceRepository",),
            service_components=("JsonPersistenceExportService",),
        ),
    )

    assert report.status is PersistenceHealthStatus.HEALTHY
    assert len(report.database_connectivity_checks) == 1
    assert len(report.migration_state_checks) == 2
    assert len(report.metadata_table_availability_checks) == 2
    assert len(report.repository_readiness_checks) == 1
    assert len(report.service_readiness_checks) == 1
    assert report.as_dict()["healthy_check_count"] == 7
    assert report.metadata == {
        "service": "application.persistence.health",
        "required_table_count": 2,
    }
    json.dumps(
        report.as_dict(),
        sort_keys=True,
    )


@pytest.mark.asyncio
async def test_health_service_reports_connectivity_migration_and_table_failures() -> (
    None
):
    service = HealthPersistenceService(
        connectivity_checker=_failed_connectivity,
        database_table_loader=_tables(
            "reports",
        ),
        current_revision_loader=_revision(
            "20260530_0018",
        ),
        head_revision_loader=lambda: "20260606_0001",
        metadata_table_loader=lambda: ("reports",),
        schema_drift_loader=_schema_drift(),
    )

    report = await service.check_health(
        checked_at=_checked_at(),
        filters=HealthPersistenceFilters(
            required_tables=(
                "reports",
                "recommendations",
            ),
        ),
    )

    assert report.status is PersistenceHealthStatus.UNHEALTHY
    assert report.database_connectivity_checks[0].is_unhealthy
    assert report.migration_state_checks[0].is_unhealthy
    assert all(
        check.is_unhealthy for check in report.metadata_table_availability_checks
    )
    assert report.metadata_table_availability_checks[0].metadata["missing_tables"] == (
        "recommendations",
    )
    assert report.metadata_table_availability_checks[1].metadata["missing_tables"] == (
        "recommendations",
    )
    assert report.repository_readiness_checks[0].is_unknown
    assert report.service_readiness_checks[0].is_unknown


@pytest.mark.asyncio
async def test_health_service_reports_unknown_migration_state() -> None:
    service = HealthPersistenceService(
        connectivity_checker=_successful_connectivity,
        database_table_loader=_tables(
            "reports",
        ),
        current_revision_loader=_revision(
            None,
        ),
        head_revision_loader=lambda: "20260606_0001",
        metadata_table_loader=lambda: ("reports",),
        schema_drift_loader=_schema_drift(),
    )

    report = await service.check_health(
        checked_at=_checked_at(),
        filters=HealthPersistenceFilters(
            required_tables=("reports",),
        ),
    )

    assert report.status is PersistenceHealthStatus.DEGRADED
    assert report.migration_state_checks[0].is_unknown
    assert report.migration_state_checks[0].metadata == {
        "current_revision": None,
        "head_revision": "20260606_0001",
    }


@pytest.mark.asyncio
async def test_health_service_reports_schema_drift_when_alembic_head_matches() -> None:
    service = HealthPersistenceService(
        connectivity_checker=_successful_connectivity,
        database_table_loader=_tables(
            "reports",
        ),
        current_revision_loader=_revision(
            "20260606_0001",
        ),
        head_revision_loader=lambda: "20260606_0001",
        metadata_table_loader=lambda: ("reports",),
        schema_drift_loader=_schema_drift(
            "add_column governance_review_decisions.resulting_task_status",
        ),
    )

    report = await service.check_health(
        checked_at=_checked_at(),
        filters=HealthPersistenceFilters(
            required_tables=("reports",),
        ),
    )

    schema_drift = report.migration_state_checks[1]
    assert report.status is PersistenceHealthStatus.UNHEALTHY
    assert schema_drift.is_unhealthy
    assert schema_drift.check_name == "alembic_schema_drift"
    assert schema_drift.metadata["operation_count"] == 1
    assert schema_drift.metadata["operations"] == (
        "add_column governance_review_decisions.resulting_task_status",
    )


@pytest.mark.asyncio
async def test_health_service_reports_schema_drift_checker_failure() -> None:
    service = HealthPersistenceService(
        connectivity_checker=_successful_connectivity,
        database_table_loader=_tables(
            "reports",
        ),
        current_revision_loader=_revision(
            "20260606_0001",
        ),
        head_revision_loader=lambda: "20260606_0001",
        metadata_table_loader=lambda: ("reports",),
        schema_drift_loader=_failed_schema_drift,
    )

    report = await service.check_health(
        checked_at=_checked_at(),
        filters=HealthPersistenceFilters(
            required_tables=("reports",),
        ),
    )

    schema_drift = report.migration_state_checks[1]
    assert report.status is PersistenceHealthStatus.UNHEALTHY
    assert schema_drift.is_unhealthy
    assert schema_drift.check_name == "alembic_schema_drift"
    assert schema_drift.metadata == {"error": "autogenerate unavailable"}


def test_health_filters_normalize_and_validate_names() -> None:
    filters = HealthPersistenceFilters(
        required_tables=(
            " reports ",
            "reports",
        ),
        repository_components=(" Repo ",),
        service_components=(" Service ",),
    )

    assert filters.required_tables == ("reports",)
    assert filters.repository_components == ("Repo",)
    assert filters.service_components == ("Service",)

    with pytest.raises(
        ValueError,
        match=r"required_tables\[0\]",
    ):
        HealthPersistenceFilters(
            required_tables=(" ",),
        )


async def _successful_connectivity() -> None:
    return None


async def _failed_connectivity() -> None:
    raise RuntimeError("connection refused")


def _tables(
    *table_names: str,
):
    async def load_tables() -> tuple[str, ...]:
        return tuple(
            table_names,
        )

    return load_tables


def _schema_drift(
    *operations: str,
):
    async def load_schema_drift() -> tuple[str, ...]:
        return tuple(
            operations,
        )

    return load_schema_drift


async def _failed_schema_drift() -> tuple[str, ...]:
    raise SQLAlchemyError("autogenerate unavailable")


def _revision(
    revision: str | None,
):
    async def load_revision() -> str | None:
        return revision

    return load_revision


def _checked_at() -> datetime:
    return datetime(
        2026,
        6,
        1,
        14,
        0,
        tzinfo=UTC,
    )
