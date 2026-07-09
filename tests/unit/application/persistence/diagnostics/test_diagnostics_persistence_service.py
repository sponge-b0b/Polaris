from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC
from datetime import datetime
from typing import cast

import pytest

from application.persistence.diagnostics import DiagnosticsPersistenceFilters
from application.persistence.diagnostics import DiagnosticsPersistenceService
from application.persistence.health import HealthPersistenceFilters
from application.persistence.health import HealthPersistenceService
from core.storage.persistence.health import PersistenceHealthStatus


@pytest.mark.asyncio
async def test_diagnostics_service_delegates_to_health_service_boundary() -> None:
    health_service = HealthPersistenceService(
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
    )
    diagnostics = DiagnosticsPersistenceService(
        health_service=health_service,
    )

    report = await diagnostics.run_diagnostics(
        checked_at=_checked_at(),
        filters=DiagnosticsPersistenceFilters(
            health_filters=HealthPersistenceFilters(
                required_tables=("reports",),
                repository_components=("ReportPersistenceRepository",),
                service_components=("JsonPersistenceExportService",),
            ),
        ),
    )

    assert report.status is PersistenceHealthStatus.HEALTHY
    assert len(report.database_connectivity_checks) == 1
    assert len(report.repository_readiness_checks) == 1
    assert len(report.service_readiness_checks) == 1
    assert report.metadata == {
        "service": "application.persistence.health",
        "required_table_count": 1,
    }


@pytest.mark.asyncio
async def test_diagnostics_service_uses_default_diagnostics_filters() -> None:
    health_service = HealthPersistenceService(
        connectivity_checker=_successful_connectivity,
        database_table_loader=_tables(
            "reports",
        ),
        current_revision_loader=_revision(
            "20260606_0001",
        ),
        head_revision_loader=lambda: "20260606_0001",
        metadata_table_loader=lambda: ("reports",),
    )
    diagnostics = DiagnosticsPersistenceService(
        health_service=health_service,
    )

    report = await diagnostics.run_diagnostics(
        checked_at=_checked_at(),
    )

    assert report.status is PersistenceHealthStatus.DEGRADED
    assert report.repository_readiness_checks[0].is_unknown
    assert report.service_readiness_checks[0].is_unknown
    assert report.metadata["required_table_count"] == 1


def test_diagnostics_filters_require_typed_health_filters() -> None:
    filters = DiagnosticsPersistenceFilters(
        health_filters=HealthPersistenceFilters(
            required_tables=("reports",),
        ),
    )

    assert filters.health_filters.required_tables == ("reports",)

    with pytest.raises(
        TypeError,
        match="health_filters must be a HealthPersistenceFilters",
    ):
        DiagnosticsPersistenceFilters(
            health_filters=cast(
                HealthPersistenceFilters,
                "not-health-filters",
            ),
        )


def test_diagnostics_filters_are_immutable() -> None:
    filters = DiagnosticsPersistenceFilters()

    with pytest.raises(FrozenInstanceError):
        filters.health_filters = HealthPersistenceFilters()  # type: ignore[misc]


async def _successful_connectivity() -> None:
    return None


def _tables(
    *table_names: str,
):
    async def load_tables() -> tuple[str, ...]:
        return tuple(
            table_names,
        )

    return load_tables


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
