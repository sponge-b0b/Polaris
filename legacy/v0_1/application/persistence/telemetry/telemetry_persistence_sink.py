from __future__ import annotations

from dataclasses import dataclass

from application.persistence.telemetry.telemetry_event_mapper import (
    TelemetryPersistenceMapper,
)
from application.persistence.telemetry.telemetry_persistence_service import (
    TelemetryPersistenceService,
)
from core.telemetry.events.telemetry_event import TelemetryEvent


@dataclass(
    frozen=True,
    slots=True,
)
class TelemetryPersistenceSinkConfig:
    """
    Configuration for optional durable telemetry persistence.

    Disabled by default so runtime JSONL telemetry remains the lightweight local
    path until an explicit PostgreSQL retention/volume policy is enabled.
    """

    enabled: bool = False
    fail_fast: bool = False


class TelemetryPersistenceSink:
    """
    Optional telemetry sink that persists mapped telemetry bundles.
    """

    def __init__(
        self,
        service: TelemetryPersistenceService,
        *,
        mapper: TelemetryPersistenceMapper | None = None,
        config: TelemetryPersistenceSinkConfig | None = None,
    ) -> None:
        self._service = service
        self._mapper = mapper or TelemetryPersistenceMapper()
        self._config = config or TelemetryPersistenceSinkConfig()

    async def emit(
        self,
        event: TelemetryEvent,
    ) -> None:
        if not self._config.enabled:
            return

        try:
            bundle = self._mapper.map_event(
                event,
            )
            result = await self._service.persist_telemetry_bundle(
                bundle,
            )
        except Exception:
            if self._config.fail_fast:
                raise
            return

        if not result.success and self._config.fail_fast:
            raise RuntimeError(result.error or "Telemetry persistence failed.")
