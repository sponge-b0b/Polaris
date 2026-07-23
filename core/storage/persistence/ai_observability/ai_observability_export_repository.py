from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol

from core.storage.persistence.ai_observability.ai_observability_export_models import (
    AiObservabilityExportJobClaim,
    AiObservabilityExportJobRecord,
    AiObservabilityExportJobStatus,
    AiObservabilityExportQueueStatus,
)


class AiObservabilityExportJobRepository(Protocol):
    """Async repository contract for durable AI-observability export jobs."""

    async def create_job(
        self,
        record: AiObservabilityExportJobRecord,
    ) -> AiObservabilityExportJobRecord: ...

    async def get_job(
        self,
        export_job_id: str,
    ) -> AiObservabilityExportJobRecord | None: ...

    async def claim_next_job(
        self,
        claim: AiObservabilityExportJobClaim | None = None,
    ) -> AiObservabilityExportJobRecord | None: ...

    async def mark_exported(
        self,
        export_job_id: str,
        *,
        external_trace_id: str | None = None,
        external_observation_id: str | None = None,
        exported_at: datetime | None = None,
    ) -> AiObservabilityExportJobRecord | None: ...

    async def mark_failed(
        self,
        export_job_id: str,
        *,
        error: str,
        retry_after_seconds: float | None = None,
        available_at: datetime | None = None,
    ) -> AiObservabilityExportJobRecord | None: ...

    async def mark_skipped(
        self,
        export_job_id: str,
        *,
        reason: str | None = None,
    ) -> AiObservabilityExportJobRecord | None: ...

    async def list_jobs(
        self,
        *,
        statuses: Sequence[AiObservabilityExportJobStatus | str] | None = None,
        workflow_name: str | None = None,
        execution_id: str | None = None,
        observation_type: str | None = None,
        limit: int | None = None,
    ) -> Sequence[AiObservabilityExportJobRecord]: ...

    async def get_queue_status(self) -> AiObservabilityExportQueueStatus: ...

    async def delete_terminal_jobs_before(
        self,
        *,
        cutoff: datetime,
        statuses: Sequence[AiObservabilityExportJobStatus | str] | None = None,
    ) -> int: ...

    async def recover_stale_running_jobs(
        self,
        *,
        started_before: datetime,
        error: str,
    ) -> int: ...
