from __future__ import annotations

from dataclasses import dataclass
from typing import cast

import pytest

from application.observability import AiObservabilityOperationalStatusService
from config.settings import Settings
from core.storage.persistence.ai_observability import (
    AiObservabilityExportJobRepository,
    AiObservabilityExportQueueStatus,
)
from core.telemetry.observability.observability_manager import ObservabilityManager


@dataclass(frozen=True, slots=True)
class FakeAiObservabilityExportJobRepository:
    queue_status: AiObservabilityExportQueueStatus

    async def get_queue_status(self) -> AiObservabilityExportQueueStatus:
        return self.queue_status


def _metric_names(observability_manager: ObservabilityManager) -> set[str]:
    return {point.name for point in observability_manager.metrics_store.points()}


@pytest.mark.asyncio
async def test_operational_status_reports_required_langfuse_configuration() -> None:
    service = AiObservabilityOperationalStatusService(
        repository=cast(
            AiObservabilityExportJobRepository,
            FakeAiObservabilityExportJobRepository(AiObservabilityExportQueueStatus()),
        ),
        settings=Settings(
            ENVIRONMENT="production",
            LANGFUSE_HOST=None,
            LANGFUSE_PUBLIC_KEY=None,
            LANGFUSE_SECRET_KEY=None,
        ),
    )

    status = await service.status()

    assert status.status == "not_configured"
    assert status.langfuse_configured is False
    assert status.reasons


@pytest.mark.asyncio
async def test_operational_status_reports_retry_pressure_and_records_gauges() -> None:
    observability_manager = ObservabilityManager()
    service = AiObservabilityOperationalStatusService(
        repository=cast(
            AiObservabilityExportJobRepository,
            FakeAiObservabilityExportJobRepository(
                AiObservabilityExportQueueStatus(
                    failed_count=2,
                    retryable_failed_count=1,
                    exhausted_failed_count=1,
                )
            ),
        ),
        settings=Settings(
            LANGFUSE_HOST="http://localhost:3000",
            LANGFUSE_PUBLIC_KEY="public-key",
            LANGFUSE_SECRET_KEY="secret-key",
        ),
        observability_manager=observability_manager,
    )

    status = await service.status()

    assert status.status == "degraded"
    assert status.langfuse_configured is True
    assert status.queue.has_retry_pressure is True
    metric_names = _metric_names(observability_manager)
    assert "application.ai_observability.langfuse.configured" in metric_names
    assert "application.ai_observability.export_queue.jobs" in metric_names
    assert "application.ai_observability.export_queue.backlog" in metric_names
