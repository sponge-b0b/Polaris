from __future__ import annotations

from datetime import UTC, datetime

from core.database.models.runtime import (
    WorkflowEventModel,
    WorkflowNodeRunModel,
    WorkflowRunModel,
    WorkflowStateSnapshotModel,
)
from core.storage.persistence.lineage import PersistenceLineage
from core.storage.persistence.runtime import (
    WorkflowEventRecord,
    WorkflowNodeRunRecord,
    WorkflowRunRecord,
    WorkflowStateSnapshotRecord,
)
from core.storage.persistence.serializers.runtime_persistence_serializer import (
    RuntimePersistenceSerializer,
)


def test_workflow_run_serializer_round_trips_model_boundary_values() -> None:
    started_at = datetime(2026, 5, 30, 14, tzinfo=UTC)
    completed_at = datetime(2026, 5, 30, 14, 2, tzinfo=UTC)
    record = WorkflowRunRecord(
        workflow_name="morning_report",
        execution_id="exec-serializer-1",
        runtime_id="runtime-1",
        status="succeeded",
        started_at=started_at,
        completed_at=completed_at,
        duration_seconds=120.0,
        mode="simulation",
        metadata={"source": "serializer-test"},
        state_payload={"node_count": 3, "success": True},
    )

    model = WorkflowRunModel(
        **RuntimePersistenceSerializer.workflow_run_values(record),
    )

    round_tripped = RuntimePersistenceSerializer.workflow_run_from_model(model)

    assert round_tripped == record


def test_node_run_serializer_round_trips_and_defaults_missing_wave_index() -> None:
    completed_at = datetime(2026, 5, 30, 14, 3, tzinfo=UTC)
    record = WorkflowNodeRunRecord(
        workflow_name="morning_report",
        execution_id="exec-serializer-1",
        node_name="macro_node",
        status="succeeded",
        runtime_id="runtime-1",
        wave_index=None,
        completed_at=completed_at,
        duration_seconds=3.25,
        metadata={"provider": "test"},
        outputs={"macro_signal": {"confidence": 0.82}},
    )

    values = RuntimePersistenceSerializer.node_run_values(record)
    model = WorkflowNodeRunModel(
        **values,
    )

    round_tripped = RuntimePersistenceSerializer.node_run_from_model(model)

    assert values["wave_index"] == 0
    assert round_tripped.workflow_name == record.workflow_name
    assert round_tripped.execution_id == record.execution_id
    assert round_tripped.node_name == record.node_name
    assert round_tripped.wave_index == 0
    assert round_tripped.outputs == {"macro_signal": {"confidence": 0.82}}


def test_event_serializer_round_trips_model_boundary_values() -> None:
    timestamp = datetime(2026, 5, 30, 14, 4, tzinfo=UTC)
    record = WorkflowEventRecord(
        event_id="event-serializer-1",
        event_type="runtime.node.completed",
        workflow_name="morning_report",
        execution_id="exec-serializer-1",
        runtime_id="runtime-1",
        node_name="macro_node",
        wave_index=1,
        timestamp=timestamp,
        payload={"success": True, "duration_seconds": 3.25},
        metadata={"workflow_name": "morning_report"},
    )

    model = WorkflowEventModel(
        **RuntimePersistenceSerializer.event_values(record),
    )

    round_tripped = RuntimePersistenceSerializer.event_from_model(model)

    assert round_tripped == record


def test_workflow_state_snapshot_serializer_round_trips_model_boundary_values() -> None:
    timestamp = datetime(2026, 5, 30, 14, 5, tzinfo=UTC)
    record = WorkflowStateSnapshotRecord(
        snapshot_id="snapshot-serializer-1",
        workflow_name="morning_report",
        execution_id="exec-serializer-1",
        workflow_status="paused",
        timestamp=timestamp,
        runtime_id="runtime-1",
        wave_index=2,
        checkpoint_reference="checkpoint-1",
        state_payload={"completed_nodes": ["macro_node"]},
        lineage=PersistenceLineage(
            workflow_name="morning_report",
            execution_id="exec-serializer-1",
            runtime_id="runtime-1",
            node_name="macro_node",
        ),
        metadata={"capture_reason": "checkpoint"},
    )

    model = WorkflowStateSnapshotModel(
        **RuntimePersistenceSerializer.workflow_state_snapshot_values(record),
    )

    round_tripped = RuntimePersistenceSerializer.workflow_state_snapshot_from_model(
        model,
    )

    assert round_tripped == record
