from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from config.settings import Settings
from core.storage.persistence.ai_observability import (
    AiObservabilityExportJobRepository,
    AiObservabilityExportQueueStatus,
)
from core.telemetry.observability.observability_manager import ObservabilityManager

AiObservabilityHealthStatus = Literal[
    "healthy",
    "backlogged",
    "retrying",
    "degraded",
    "not_configured",
]


@dataclass(frozen=True, slots=True)
class AiObservabilityOperationalStatus:
    """Operational status for the required Langfuse AI-observability projection."""

    status: AiObservabilityHealthStatus
    langfuse_configured: bool
    environment: str
    release: str | None
    queue: AiObservabilityExportQueueStatus
    reasons: tuple[str, ...] = ()
    reachability: str = "not_checked"

    @property
    def healthy(self) -> bool:
        return self.status == "healthy"

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "healthy": self.healthy,
            "langfuse_configured": self.langfuse_configured,
            "environment": self.environment,
            "release": self.release,
            "reachability": self.reachability,
            "reasons": list(self.reasons),
            "queue": self.queue.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class AiObservabilityOperationalStatusService:
    """Expose Langfuse projection health without reading Langfuse as a source of truth."""  # noqa: E501

    repository: AiObservabilityExportJobRepository
    settings: Settings
    observability_manager: ObservabilityManager | None = None

    async def status(self) -> AiObservabilityOperationalStatus:
        queue_status = await self.repository.get_queue_status()
        configured, config_reason = _langfuse_configured(self.settings)
        status = _resolve_health_status(
            queue_status=queue_status,
            langfuse_configured=configured,
        )
        reasons = _status_reasons(
            queue_status=queue_status,
            langfuse_configured=configured,
            config_reason=config_reason,
        )
        operational_status = AiObservabilityOperationalStatus(
            status=status,
            langfuse_configured=configured,
            environment=self.settings.LANGFUSE_ENVIRONMENT,
            release=self.settings.LANGFUSE_RELEASE,
            queue=queue_status,
            reasons=reasons,
        )
        self._record_metrics(operational_status)
        return operational_status

    def _record_metrics(
        self,
        status: AiObservabilityOperationalStatus,
    ) -> None:
        if self.observability_manager is None:
            return
        attributes = {
            "component_name": "LangfuseAiObservability",
            "operation": "ai_observability_status",
        }
        self.observability_manager.gauge(
            "application.ai_observability.langfuse.configured",
            1.0 if status.langfuse_configured else 0.0,
            attributes={**attributes, "outcome": status.status},
        )
        for outcome, value in status.queue.status_counts().items():
            self.observability_manager.gauge(
                "application.ai_observability.export_queue.jobs",
                float(value),
                attributes={**attributes, "outcome": outcome},
            )
        self.observability_manager.gauge(
            "application.ai_observability.export_queue.backlog",
            float(status.queue.backlog_count),
            attributes={**attributes, "outcome": status.status},
        )
        self.observability_manager.gauge(
            "application.ai_observability.export_queue.exhausted_failed",
            float(status.queue.exhausted_failed_count),
            attributes={**attributes, "outcome": status.status},
        )


def _langfuse_configured(settings: Settings) -> tuple[bool, str | None]:
    try:
        settings.validate_langfuse_observability(require_configured=True)
    except ValueError as exc:
        return False, str(exc)
    return True, None


def _resolve_health_status(
    *,
    queue_status: AiObservabilityExportQueueStatus,
    langfuse_configured: bool,
) -> AiObservabilityHealthStatus:
    if not langfuse_configured:
        return "not_configured"
    if queue_status.exhausted_failed_count > 0:
        return "degraded"
    if queue_status.retryable_failed_count > 0:
        return "retrying"
    if queue_status.pending_count > 0 or queue_status.running_count > 0:
        return "backlogged"
    return "healthy"


def _status_reasons(
    *,
    queue_status: AiObservabilityExportQueueStatus,
    langfuse_configured: bool,
    config_reason: str | None,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if not langfuse_configured:
        reasons.append(config_reason or "Langfuse configuration is incomplete.")
    if queue_status.exhausted_failed_count > 0:
        reasons.append("One or more Langfuse export jobs exhausted retry attempts.")
    if queue_status.retryable_failed_count > 0:
        reasons.append("One or more Langfuse export jobs are waiting for retry.")
    if queue_status.pending_count > 0 or queue_status.running_count > 0:
        reasons.append("Langfuse export jobs are pending or currently running.")
    return tuple(reasons)
