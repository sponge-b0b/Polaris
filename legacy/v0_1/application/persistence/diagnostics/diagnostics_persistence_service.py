from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from application.persistence.health import (
    HealthPersistenceFilters,
    HealthPersistenceService,
)
from core.storage.persistence.health import PersistenceHealthReport


@dataclass(
    frozen=True,
    slots=True,
)
class DiagnosticsPersistenceFilters:
    """
    Typed options for persistence diagnostics.

    Diagnostics currently delegate to the canonical persistence health-check
    service. CLI or API presentation remains outside this application boundary.
    """

    health_filters: HealthPersistenceFilters = field(
        default_factory=HealthPersistenceFilters,
    )

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.health_filters,
            HealthPersistenceFilters,
        ):
            raise TypeError(
                "health_filters must be a HealthPersistenceFilters instance."
            )


class DiagnosticsPersistenceService:
    """
    Thin application boundary for persistence diagnostics.

    This service centralizes diagnostics entry points while delegating concrete
    health checks to `HealthPersistenceService`. It does not render CLI output,
    mutate database state, execute migrations, or bypass persistence services.
    """

    def __init__(
        self,
        *,
        health_service: HealthPersistenceService | None = None,
    ) -> None:
        self._health_service = health_service or HealthPersistenceService()

    async def run_diagnostics(
        self,
        *,
        checked_at: datetime | None = None,
        filters: DiagnosticsPersistenceFilters | None = None,
    ) -> PersistenceHealthReport:
        active_filters = filters or DiagnosticsPersistenceFilters()
        return await self._health_service.check_health(
            checked_at=checked_at,
            filters=active_filters.health_filters,
        )
