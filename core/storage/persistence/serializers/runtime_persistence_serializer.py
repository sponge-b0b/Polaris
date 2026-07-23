from __future__ import annotations

from typing import Any, cast

from core.database.models.runtime import (
    WorkflowEventModel,
    WorkflowNodeRunModel,
    WorkflowRunModel,
    WorkflowStateSnapshotModel,
)
from core.storage.persistence.lineage import PersistenceLineage
from core.storage.persistence.runtime.runtime_persistence_models import (
    JsonObject,
    WorkflowEventRecord,
    WorkflowNodeRunRecord,
    WorkflowRunRecord,
    WorkflowStateSnapshotRecord,
)


class RuntimePersistenceSerializer:
    """
    Serializer between typed runtime persistence records and SQLAlchemy models.

    JSON dictionaries are introduced here because this module is the database
    persistence boundary. Runtime/application layers should continue to use the
    typed records from ``core.storage.persistence.runtime``.
    """

    @staticmethod
    def workflow_run_values(
        record: WorkflowRunRecord,
    ) -> dict[str, Any]:
        return {
            "workflow_name": record.workflow_name,
            "execution_id": record.execution_id,
            "runtime_id": record.runtime_id,
            "status": record.status,
            "started_at": record.started_at,
            "completed_at": record.completed_at,
            "duration_seconds": record.duration_seconds,
            "mode": record.mode,
            "error": record.error,
            "metadata_payload": dict(record.metadata),
            "state_payload": dict(record.state_payload),
        }

    @staticmethod
    def workflow_run_from_model(
        model: WorkflowRunModel,
    ) -> WorkflowRunRecord:
        return WorkflowRunRecord(
            workflow_name=model.workflow_name,
            execution_id=model.execution_id,
            runtime_id=model.runtime_id,
            status=model.status,
            started_at=model.started_at,
            completed_at=model.completed_at,
            duration_seconds=model.duration_seconds,
            mode=model.mode,
            error=model.error,
            metadata=cast(
                JsonObject,
                model.metadata_payload,
            ),
            state_payload=cast(
                JsonObject,
                model.state_payload,
            ),
        )

    @staticmethod
    def node_run_values(
        record: WorkflowNodeRunRecord,
    ) -> dict[str, Any]:
        return {
            "workflow_name": record.workflow_name,
            "execution_id": record.execution_id,
            "node_name": record.node_name,
            "wave_index": _wave_index_value(record.wave_index),
            "runtime_id": record.runtime_id,
            "status": record.status,
            "started_at": record.started_at,
            "completed_at": record.completed_at,
            "duration_seconds": record.duration_seconds,
            "error": record.error,
            "metadata_payload": dict(record.metadata),
            "output_payload": dict(record.outputs),
        }

    @staticmethod
    def node_run_from_model(
        model: WorkflowNodeRunModel,
    ) -> WorkflowNodeRunRecord:
        return WorkflowNodeRunRecord(
            workflow_name=model.workflow_name,
            execution_id=model.execution_id,
            node_name=model.node_name,
            wave_index=model.wave_index,
            runtime_id=model.runtime_id,
            status=model.status,
            started_at=model.started_at,
            completed_at=model.completed_at,
            duration_seconds=model.duration_seconds,
            error=model.error,
            metadata=cast(
                JsonObject,
                model.metadata_payload,
            ),
            outputs=cast(
                JsonObject,
                model.output_payload,
            ),
        )

    @staticmethod
    def event_values(
        record: WorkflowEventRecord,
    ) -> dict[str, Any]:
        return {
            "event_id": record.event_id,
            "event_type": record.event_type,
            "workflow_name": record.workflow_name,
            "execution_id": record.execution_id,
            "runtime_id": record.runtime_id,
            "node_name": record.node_name,
            "wave_index": record.wave_index,
            "timestamp": record.timestamp,
            "payload": dict(record.payload),
            "metadata_payload": dict(record.metadata),
        }

    @staticmethod
    def event_from_model(
        model: WorkflowEventModel,
    ) -> WorkflowEventRecord:
        return WorkflowEventRecord(
            event_id=model.event_id,
            event_type=model.event_type,
            workflow_name=model.workflow_name,
            execution_id=model.execution_id,
            runtime_id=model.runtime_id,
            node_name=model.node_name,
            wave_index=model.wave_index,
            timestamp=model.timestamp,
            payload=cast(
                JsonObject,
                model.payload,
            ),
            metadata=cast(
                JsonObject,
                model.metadata_payload,
            ),
        )

    @staticmethod
    def workflow_state_snapshot_values(
        record: WorkflowStateSnapshotRecord,
    ) -> dict[str, Any]:
        return {
            "snapshot_id": record.snapshot_id,
            "workflow_name": record.workflow_name,
            "execution_id": record.execution_id,
            "workflow_status": record.workflow_status,
            "timestamp": record.timestamp,
            "runtime_id": record.runtime_id,
            "node_name": record.lineage.node_name,
            "wave_index": record.wave_index,
            "checkpoint_reference": record.checkpoint_reference,
            "state_payload": dict(record.state_payload),
            "metadata_payload": dict(record.metadata),
        }

    @staticmethod
    def workflow_state_snapshot_from_model(
        model: WorkflowStateSnapshotModel,
    ) -> WorkflowStateSnapshotRecord:
        return WorkflowStateSnapshotRecord(
            snapshot_id=model.snapshot_id,
            workflow_name=model.workflow_name,
            execution_id=model.execution_id,
            workflow_status=model.workflow_status,
            timestamp=model.timestamp,
            runtime_id=model.runtime_id,
            wave_index=model.wave_index,
            checkpoint_reference=model.checkpoint_reference,
            state_payload=cast(
                JsonObject,
                model.state_payload,
            ),
            lineage=PersistenceLineage(
                workflow_name=model.workflow_name,
                execution_id=model.execution_id,
                runtime_id=model.runtime_id,
                node_name=model.node_name,
            ),
            metadata=cast(
                JsonObject,
                model.metadata_payload,
            ),
        )


def _wave_index_value(
    wave_index: int | None,
) -> int:
    if wave_index is None:
        return 0

    return wave_index
