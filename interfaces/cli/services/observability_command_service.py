from __future__ import annotations

from collections.abc import AsyncIterator
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from contextlib import asynccontextmanager
from typing import Protocol

from application.observability import AiObservabilityOperationalStatus
from application.observability import AiObservabilityOperationalStatusService
from core.bootstrap.di_providers import application_request_scope


class AiObservabilityOperationalStatusPort(Protocol):
    async def status(self) -> AiObservabilityOperationalStatus: ...


AiObservabilityStatusContextFactory = Callable[
    [], AbstractAsyncContextManager[AiObservabilityOperationalStatusPort]
]


class ObservabilityCommandService:
    """Thin CLI service for Polaris observability operational views."""

    def __init__(
        self,
        ai_status_service: AiObservabilityOperationalStatusPort | None = None,
        ai_status_context_factory: AiObservabilityStatusContextFactory | None = None,
    ) -> None:
        self._ai_status_service = ai_status_service
        self._ai_status_context_factory = (
            ai_status_context_factory or default_ai_observability_status_context
        )

    async def ai_status(self) -> AiObservabilityOperationalStatus:
        if self._ai_status_service is not None:
            return await self._ai_status_service.status()
        async with self._ai_status_context_factory() as service:
            return await service.status()


@asynccontextmanager
async def default_ai_observability_status_context() -> AsyncIterator[
    AiObservabilityOperationalStatusPort
]:
    async with application_request_scope() as request_container:
        yield await request_container.get(AiObservabilityOperationalStatusService)


def render_ai_observability_status(
    status: AiObservabilityOperationalStatus,
) -> str:
    """Render Langfuse AI-observability operational status for humans."""

    queue = status.queue
    lines = [
        "AI Observability Status",
        f"Status: {status.status}",
        f"Healthy: {str(status.healthy)}",
        f"Langfuse configured: {_yes_no(status.langfuse_configured)}",
        f"Environment: {status.environment}",
        f"Release: {status.release or 'unset'}",
        f"Reachability: {status.reachability}",
        "Queue:",
        f"  pending: {queue.pending_count}",
        f"  running: {queue.running_count}",
        f"  retryable failed: {queue.retryable_failed_count}",
        f"  exhausted failed: {queue.exhausted_failed_count}",
        f"  backlog: {queue.backlog_count}",
        f"  exported: {queue.exported_count}",
        f"  skipped: {queue.skipped_count}",
        f"  total: {queue.total_count}",
    ]
    if queue.oldest_retryable_available_at is not None:
        lines.append(
            "  oldest retryable available at: "
            f"{queue.oldest_retryable_available_at.isoformat()}"
        )
    if queue.latest_failure_at is not None:
        lines.append(f"  latest failure at: {queue.latest_failure_at.isoformat()}")
    if queue.latest_exported_at is not None:
        lines.append(f"  latest exported at: {queue.latest_exported_at.isoformat()}")
    if status.reasons:
        lines.append("Reasons:")
        lines.extend(f"  - {reason}" for reason in status.reasons)
    return "\n".join(lines)


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"
