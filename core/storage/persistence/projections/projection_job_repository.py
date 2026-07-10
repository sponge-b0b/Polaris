from __future__ import annotations

from datetime import datetime
from typing import Protocol
from typing import Sequence

from core.storage.persistence.projections.projection_job_models import (
    MissingProjectionRunRecord,
)
from core.storage.persistence.projections.projection_job_models import (
    ProjectionJobClaim,
)
from core.storage.persistence.projections.projection_job_models import (
    WorkflowOutputProjectionJobRecord,
)
from core.storage.persistence.projections.projection_job_models import (
    WorkflowOutputProjectionJobStatus,
)


class WorkflowOutputProjectionJobRepository(Protocol):
    """Async repository contract for durable workflow-output projection jobs."""

    async def create_job(
        self,
        record: WorkflowOutputProjectionJobRecord,
    ) -> WorkflowOutputProjectionJobRecord: ...

    async def claim_next_job(
        self,
        claim: ProjectionJobClaim | None = None,
    ) -> WorkflowOutputProjectionJobRecord | None: ...

    async def claim_job(
        self,
        projection_job_id: str,
        *,
        statuses: Sequence[WorkflowOutputProjectionJobStatus | str] | None = None,
    ) -> WorkflowOutputProjectionJobRecord | None: ...

    async def mark_succeeded(
        self,
        projection_job_id: str,
        *,
        completed_at: datetime | None = None,
    ) -> WorkflowOutputProjectionJobRecord | None: ...

    async def mark_failed(
        self,
        projection_job_id: str,
        *,
        error: str,
        completed_at: datetime | None = None,
    ) -> WorkflowOutputProjectionJobRecord | None: ...

    async def mark_skipped(
        self,
        projection_job_id: str,
        *,
        reason: str | None = None,
        completed_at: datetime | None = None,
    ) -> WorkflowOutputProjectionJobRecord | None: ...

    async def list_jobs(
        self,
        *,
        run_id: str | None = None,
        workflow_name: str | None = None,
        execution_id: str | None = None,
        projector_name: str | None = None,
        statuses: Sequence[WorkflowOutputProjectionJobStatus | str] | None = None,
        limit: int | None = None,
    ) -> Sequence[WorkflowOutputProjectionJobRecord]: ...

    async def recover_stale_running_jobs(
        self,
        *,
        started_before: datetime,
        error: str,
    ) -> int: ...

    async def list_runs_missing_projection_jobs(
        self,
        *,
        workflow_name: str | None = None,
        execution_id: str | None = None,
        limit: int | None = None,
    ) -> Sequence[MissingProjectionRunRecord]: ...
