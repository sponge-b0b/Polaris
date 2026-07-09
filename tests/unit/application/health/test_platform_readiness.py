from __future__ import annotations

from datetime import UTC
from datetime import datetime

import pytest

from application.health import PlatformReadinessCategory
from application.health import PlatformReadinessProbe
from application.health import PlatformReadinessService
from application.health import PlatformReadinessStatus
from core.storage.persistence.health import PersistenceHealthCheckCategory
from core.storage.persistence.health import PersistenceHealthCheckResult
from core.storage.persistence.health import PersistenceHealthReport


class StubPersistenceHealthService:
    def __init__(self, report: PersistenceHealthReport) -> None:
        self.report = report

    async def check_health(self) -> PersistenceHealthReport:
        return self.report


async def _ready() -> None:
    return None


async def _not_ready() -> None:
    raise ConnectionError("sensitive endpoint detail")


@pytest.mark.asyncio
async def test_platform_readiness_reports_typed_non_rag_dependencies() -> None:
    checked_at = datetime.now(UTC)
    persistence_report = PersistenceHealthReport(
        checked_at=checked_at,
        checks=tuple(
            PersistenceHealthCheckResult.healthy(
                category=category,
                check_name=category.value,
                component="postgresql",
                checked_at=checked_at,
                message="ready",
            )
            for category in (
                PersistenceHealthCheckCategory.DATABASE_CONNECTIVITY,
                PersistenceHealthCheckCategory.MIGRATION_STATE,
                PersistenceHealthCheckCategory.METADATA_TABLE_AVAILABILITY,
            )
        ),
    )
    service = PlatformReadinessService(
        persistence_health=StubPersistenceHealthService(persistence_report),
        probes=(
            PlatformReadinessProbe(
                category=PlatformReadinessCategory.TELEMETRY_EXPORTER,
                component="prometheus",
                check=_ready,
            ),
            PlatformReadinessProbe(
                category=PlatformReadinessCategory.TELEMETRY_EXPORTER,
                component="jaeger",
                check=_ready,
            ),
            PlatformReadinessProbe(
                category=PlatformReadinessCategory.PROVIDER,
                component="market_data_provider",
                check=_ready,
            ),
            PlatformReadinessProbe(
                category=PlatformReadinessCategory.RUNTIME_PERSISTENCE,
                component="completed_run_archive",
                check=_ready,
            ),
        ),
    )

    report = await service.check()

    assert report.ready is True
    assert {check.component for check in report.checks} == {
        "postgresql",
        "prometheus",
        "jaeger",
        "market_data_provider",
        "completed_run_archive",
    }
    assert all(check.duration_seconds >= 0 for check in report.checks)


@pytest.mark.asyncio
async def test_platform_readiness_contains_failure_without_leaking_error_text() -> None:
    checked_at = datetime.now(UTC)
    persistence_report = PersistenceHealthReport(
        checked_at=checked_at,
        checks=(
            PersistenceHealthCheckResult.healthy(
                category=PersistenceHealthCheckCategory.DATABASE_CONNECTIVITY,
                check_name="connectivity",
                component="postgresql",
                checked_at=checked_at,
                message="ready",
            ),
        ),
    )
    service = PlatformReadinessService(
        persistence_health=StubPersistenceHealthService(persistence_report),
        probes=(
            PlatformReadinessProbe(
                category=PlatformReadinessCategory.PROVIDER,
                component="market_data_provider",
                check=_not_ready,
            ),
        ),
    )

    report = await service.check()

    assert report.ready is False
    assert report.checks[0].status is PlatformReadinessStatus.NOT_READY
    failed = report.checks[-1]
    assert failed.status is PlatformReadinessStatus.NOT_READY
    assert failed.error_type == "ConnectionError"
    assert "sensitive endpoint detail" not in failed.detail
