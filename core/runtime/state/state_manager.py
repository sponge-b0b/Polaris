from __future__ import annotations

from datetime import datetime
from datetime import timezone
from typing import Any
from typing import Mapping
from uuid import uuid4

from core.runtime.state.runtime_context import RuntimeContext
from core.storage.persistence.completed_run_archive import CompletedRunArchive
from core.storage.persistence.serializers.completed_run_serializer import (
    CompletedRunPersistenceSerializer,
)


class StateManager:
    """Creates, archives, and restores canonical ``RuntimeContext`` snapshots."""

    def __init__(
        self,
        archive: CompletedRunArchive | None = None,
    ) -> None:
        self.archive = archive

    def create_context(
        self,
        workflow_id: str,
        mode: str = "live",
        workflow_inputs: Mapping[str, Any] | None = None,
        simulation_time: datetime | None = None,
        execution_id: str | None = None,
    ) -> RuntimeContext:
        if not workflow_id.strip():
            raise ValueError("workflow_id cannot be empty.")

        return RuntimeContext(
            runtime_id=self._generate_runtime_id(),
            workflow_id=workflow_id,
            execution_id=execution_id or self._generate_execution_id(),
            mode=mode,
            simulation_time=simulation_time,
            workflow_inputs=dict(workflow_inputs or {}),
        )

    async def archive_completed_run(
        self,
        context: RuntimeContext,
    ) -> None:
        if self.archive is None:
            return

        bundle = CompletedRunPersistenceSerializer.bundle_from_context_payload(
            context.to_dict(),
            workflow_name=context.workflow_id,
        )
        await self.archive.archive_run(bundle)

    async def list_completed_runs(
        self,
        workflow_name: str,
    ) -> list[str]:
        if self.archive is None:
            return []
        return await self.archive.list_archived_runs(workflow_name)

    async def load_completed_run(
        self,
        workflow_name: str,
        execution_id: str,
    ) -> RuntimeContext | None:
        if self.archive is None:
            return None

        bundle = await self.archive.load_archived_run(workflow_name, execution_id)
        if bundle is None:
            return None

        return RuntimeContext.from_dict(
            CompletedRunPersistenceSerializer.context_payload_from_bundle(bundle)
        )

    async def delete_completed_run(
        self,
        workflow_name: str,
        execution_id: str,
    ) -> None:
        if self.archive is None:
            return
        await self.archive.delete_archived_run(workflow_name, execution_id)

    async def cleanup_completed_runs(
        self,
        max_age_days: int | None = None,
        max_count: int | None = None,
    ) -> int:
        if self.archive is None:
            return 0
        return await self.archive.cleanup_archived_runs(
            max_age_days=max_age_days,
            max_count=max_count,
        )

    def restore_context(
        self,
        snapshot_data: Mapping[str, Any],
    ) -> RuntimeContext:
        return RuntimeContext.from_dict(snapshot_data)

    def _generate_runtime_id(
        self,
    ) -> str:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        return f"runtime_{timestamp}_{uuid4().hex[:8]}"

    def _generate_execution_id(
        self,
    ) -> str:
        return uuid4().hex
