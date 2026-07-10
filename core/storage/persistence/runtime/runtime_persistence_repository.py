from __future__ import annotations

from datetime import datetime
from typing import Protocol
from typing import Sequence

from core.storage.persistence.runtime.runtime_persistence_models import (
    RuntimePersistenceResult,
)
from core.storage.persistence.runtime.runtime_persistence_models import (
    WorkflowEventRecord,
)
from core.storage.persistence.runtime.runtime_persistence_models import (
    WorkflowNodeRunRecord,
)
from core.storage.persistence.runtime.runtime_persistence_models import (
    WorkflowStateSnapshotRecord,
)
from core.storage.persistence.runtime.runtime_persistence_models import (
    WorkflowRunRecord,
)


class RuntimePersistenceRepository(Protocol):
    """
    Async repository contract for durable runtime persistence.

    Implementations are persistence adapters. Runtime execution should publish
    typed records to this boundary instead of exchanging raw dictionaries
    inside runtime/application layers.
    """

    async def persist_workflow_run(
        self,
        record: WorkflowRunRecord,
    ) -> RuntimePersistenceResult: ...

    async def persist_node_run(
        self,
        record: WorkflowNodeRunRecord,
    ) -> RuntimePersistenceResult: ...

    async def persist_event(
        self,
        record: WorkflowEventRecord,
    ) -> RuntimePersistenceResult: ...

    async def persist_workflow_state_snapshot(
        self,
        record: WorkflowStateSnapshotRecord,
    ) -> RuntimePersistenceResult: ...

    async def get_workflow_run(
        self,
        workflow_name: str,
        execution_id: str,
    ) -> WorkflowRunRecord | None: ...

    async def list_node_runs(
        self,
        workflow_name: str,
        execution_id: str,
    ) -> Sequence[WorkflowNodeRunRecord]: ...

    async def list_events(
        self,
        workflow_name: str,
        execution_id: str,
    ) -> Sequence[WorkflowEventRecord]: ...

    async def get_workflow_state_snapshot(
        self,
        snapshot_id: str,
    ) -> WorkflowStateSnapshotRecord | None: ...

    async def list_workflow_state_snapshots(
        self,
        *,
        workflow_name: str | None = None,
        execution_id: str | None = None,
        runtime_id: str | None = None,
        workflow_status: str | None = None,
        checkpoint_reference: str | None = None,
        wave_index: int | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[WorkflowStateSnapshotRecord]: ...
