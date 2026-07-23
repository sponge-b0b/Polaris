from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from time import perf_counter
from typing import Protocol

from core.storage.persistence.health import (
    PersistenceHealthCheckCategory,
    PersistenceHealthReport,
    PersistenceHealthStatus,
)

ReadinessProbe = Callable[[], Awaitable[None]]


class PersistenceHealthChecker(Protocol):
    async def check_health(self) -> PersistenceHealthReport: ...


class PlatformReadinessCategory(StrEnum):
    POSTGRESQL = "postgresql"
    TELEMETRY_EXPORTER = "telemetry_exporter"
    PROVIDER = "provider"
    RUNTIME_PERSISTENCE = "runtime_persistence"


class PlatformReadinessStatus(StrEnum):
    READY = "ready"
    NOT_READY = "not_ready"


@dataclass(frozen=True, slots=True)
class PlatformReadinessProbe:
    category: PlatformReadinessCategory
    component: str
    check: ReadinessProbe

    def __post_init__(self) -> None:
        if not self.component.strip():
            raise ValueError("Readiness probe component cannot be empty.")


@dataclass(frozen=True, slots=True)
class PlatformReadinessCheck:
    category: PlatformReadinessCategory
    component: str
    status: PlatformReadinessStatus
    duration_seconds: float
    detail: str
    error_type: str | None = None

    @property
    def ready(self) -> bool:
        return self.status is PlatformReadinessStatus.READY


@dataclass(frozen=True, slots=True)
class PlatformReadinessReport:
    checked_at: datetime
    checks: tuple[PlatformReadinessCheck, ...]

    @property
    def ready(self) -> bool:
        return bool(self.checks) and all(check.ready for check in self.checks)


class PlatformReadinessService:
    """Typed non-RAG readiness diagnostics for platform infrastructure."""

    def __init__(
        self,
        *,
        persistence_health: PersistenceHealthChecker,
        probes: tuple[PlatformReadinessProbe, ...] = (),
    ) -> None:
        self._persistence_health = persistence_health
        self._probes = probes

    async def check(self) -> PlatformReadinessReport:
        checked_at = datetime.now(UTC)
        postgres_check, probe_checks = await asyncio.gather(
            self._check_postgresql(),
            self._check_probes(),
        )
        return PlatformReadinessReport(
            checked_at=checked_at,
            checks=(postgres_check, *probe_checks),
        )

    async def _check_postgresql(self) -> PlatformReadinessCheck:
        started_at = perf_counter()
        try:
            report = await self._persistence_health.check_health()
        except Exception as exc:  # pragma: no cover - integration guard
            return PlatformReadinessCheck(
                category=PlatformReadinessCategory.POSTGRESQL,
                component="postgresql",
                status=PlatformReadinessStatus.NOT_READY,
                duration_seconds=perf_counter() - started_at,
                detail="PostgreSQL readiness check failed.",
                error_type=type(exc).__name__,
            )

        required_categories = {
            PersistenceHealthCheckCategory.DATABASE_CONNECTIVITY,
            PersistenceHealthCheckCategory.MIGRATION_STATE,
            PersistenceHealthCheckCategory.METADATA_TABLE_AVAILABILITY,
        }
        required_checks = tuple(
            check for check in report.checks if check.category in required_categories
        )
        observed_categories = {check.category for check in required_checks}
        ready = observed_categories == required_categories and all(
            check.status is PersistenceHealthStatus.HEALTHY for check in required_checks
        )
        return PlatformReadinessCheck(
            category=PlatformReadinessCategory.POSTGRESQL,
            component="postgresql",
            status=(
                PlatformReadinessStatus.READY
                if ready
                else PlatformReadinessStatus.NOT_READY
            ),
            duration_seconds=perf_counter() - started_at,
            detail=(
                "PostgreSQL persistence is ready."
                if ready
                else "PostgreSQL persistence is not ready."
            ),
        )

    async def _check_probes(self) -> tuple[PlatformReadinessCheck, ...]:
        if not self._probes:
            return ()
        return tuple(
            await asyncio.gather(
                *(self._run_probe(probe) for probe in self._probes),
            )
        )

    async def _run_probe(
        self,
        probe: PlatformReadinessProbe,
    ) -> PlatformReadinessCheck:
        started_at = perf_counter()
        try:
            await probe.check()
        except Exception as exc:  # pragma: no cover - exercised by unit test
            return PlatformReadinessCheck(
                category=probe.category,
                component=probe.component,
                status=PlatformReadinessStatus.NOT_READY,
                duration_seconds=perf_counter() - started_at,
                detail=f"{probe.component} readiness check failed.",
                error_type=type(exc).__name__,
            )

        return PlatformReadinessCheck(
            category=probe.category,
            component=probe.component,
            status=PlatformReadinessStatus.READY,
            duration_seconds=perf_counter() - started_at,
            detail=f"{probe.component} is ready.",
        )
