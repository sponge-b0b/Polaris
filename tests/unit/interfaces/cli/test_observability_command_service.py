from __future__ import annotations

from dataclasses import dataclass

import pytest

from application.observability import AiObservabilityOperationalStatus
from core.storage.persistence.ai_observability import AiObservabilityExportQueueStatus
from interfaces.cli.services.observability_command_service import (
    ObservabilityCommandService,
    render_ai_observability_status,
)


@dataclass(frozen=True, slots=True)
class FakeAiStatusService:
    result: AiObservabilityOperationalStatus

    async def status(self) -> AiObservabilityOperationalStatus:
        return self.result


def _status() -> AiObservabilityOperationalStatus:
    return AiObservabilityOperationalStatus(
        status="backlogged",
        langfuse_configured=True,
        environment="test",
        release="abc123",
        queue=AiObservabilityExportQueueStatus(pending_count=2, exported_count=3),
        reasons=("Langfuse export jobs are pending or currently running.",),
    )


@pytest.mark.asyncio
async def test_observability_command_service_returns_ai_status() -> None:
    expected = _status()
    service = ObservabilityCommandService(
        ai_status_service=FakeAiStatusService(expected)
    )

    result = await service.ai_status()

    assert result is expected


def test_render_ai_observability_status_includes_queue_summary() -> None:
    rendered = render_ai_observability_status(_status())

    assert "AI Observability Status" in rendered
    assert "Status: backlogged" in rendered
    assert "Langfuse configured: yes" in rendered
    assert "pending: 2" in rendered
    assert "exported: 3" in rendered
