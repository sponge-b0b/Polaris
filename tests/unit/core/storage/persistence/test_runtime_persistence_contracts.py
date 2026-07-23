from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from core.storage.persistence.lineage import PersistenceLineage
from core.storage.persistence.runtime import (
    RuntimePersistenceResult,
    WorkflowEventRecord,
    WorkflowNodeRunRecord,
    WorkflowRunRecord,
    WorkflowStateSnapshotRecord,
    new_random_workflow_state_snapshot_id,
    new_workflow_state_snapshot_id,
)


def test_workflow_run_record_is_typed_and_immutable() -> None:
    record = WorkflowRunRecord(
        workflow_name="morning_report",
        execution_id="exec-1",
        runtime_id="runtime-1",
        status="succeeded",
        duration_seconds=1.25,
        metadata={"mode": "paper"},
        state_payload={"node_count": 3},
    )

    assert record.workflow_name == "morning_report"
    assert record.execution_id == "exec-1"
    assert record.state_payload["node_count"] == 3

    with pytest.raises(FrozenInstanceError):
        record.status = "failed"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("field_name", "kwargs"),
    [
        (
            "workflow_name",
            {"workflow_name": " "},
        ),
        (
            "execution_id",
            {"execution_id": ""},
        ),
        (
            "status",
            {"status": " "},
        ),
        (
            "duration_seconds",
            {"duration_seconds": -0.1},
        ),
    ],
)
def test_workflow_run_record_validates_required_fields(
    field_name: str,
    kwargs: dict[str, object],
) -> None:
    values: dict[str, object] = {
        "workflow_name": "morning_report",
        "execution_id": "exec-1",
        "status": "running",
    }
    values.update(kwargs)

    with pytest.raises(ValueError, match=field_name):
        WorkflowRunRecord(**values)  # type: ignore[arg-type]


def test_workflow_node_run_record_validates_node_fields() -> None:
    record = WorkflowNodeRunRecord(
        workflow_name="morning_report",
        execution_id="exec-1",
        node_name="macro_analysis",
        status="succeeded",
        wave_index=0,
        outputs={"signal": {"confidence": 0.82}},
    )

    assert record.node_name == "macro_analysis"
    assert record.outputs["signal"] == {"confidence": 0.82}

    with pytest.raises(ValueError, match="node_name"):
        WorkflowNodeRunRecord(
            workflow_name="morning_report",
            execution_id="exec-1",
            node_name=" ",
            status="succeeded",
        )

    with pytest.raises(ValueError, match="wave_index"):
        WorkflowNodeRunRecord(
            workflow_name="morning_report",
            execution_id="exec-1",
            node_name="macro_analysis",
            status="succeeded",
            wave_index=-1,
        )


def test_workflow_state_snapshot_record_is_typed_immutable_and_preserves_state() -> (
    None
):
    timestamp = datetime(2026, 5, 31, 14, 0, tzinfo=UTC)
    record = WorkflowStateSnapshotRecord(
        snapshot_id=" workflow-state-snapshot-1 ",
        workflow_name=" morning_report ",
        execution_id=" exec-1 ",
        workflow_status=" paused ",
        timestamp=timestamp,
        runtime_id=" runtime-1 ",
        wave_index=2,
        checkpoint_reference=" checkpoint-1 ",
        state_payload={
            "active_nodes": ["macro_analysis", "technical_analysis"],
            "control_state": {"paused": True},
        },
        lineage=PersistenceLineage(
            workflow_name=" morning_report ",
            execution_id=" exec-1 ",
            runtime_id=" runtime-1 ",
        ),
        metadata={"source": "unit-test"},
    )

    assert record.snapshot_id == "workflow-state-snapshot-1"
    assert record.workflow_name == "morning_report"
    assert record.execution_id == "exec-1"
    assert record.workflow_status == "paused"
    assert record.runtime_id == "runtime-1"
    assert record.wave_index == 2
    assert record.checkpoint_reference == "checkpoint-1"
    assert record.state_payload["control_state"] == {"paused": True}
    assert record.lineage.workflow_name == "morning_report"

    with pytest.raises(FrozenInstanceError):
        record.workflow_status = "running"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("kwargs", "field_name"),
    [
        ({"snapshot_id": " "}, "snapshot_id"),
        ({"workflow_name": ""}, "workflow_name"),
        ({"execution_id": " "}, "execution_id"),
        ({"workflow_status": " "}, "workflow_status"),
        ({"wave_index": -1}, "wave_index"),
    ],
)
def test_workflow_state_snapshot_record_validates_required_fields(
    kwargs: dict[str, object],
    field_name: str,
) -> None:
    values: dict[str, object] = {
        "snapshot_id": "workflow-state-snapshot-1",
        "workflow_name": "morning_report",
        "execution_id": "exec-1",
        "workflow_status": "running",
        "timestamp": datetime(2026, 5, 31, 14, 0, tzinfo=UTC),
    }
    values.update(kwargs)

    with pytest.raises(ValueError, match=field_name):
        WorkflowStateSnapshotRecord(**values)  # type: ignore[arg-type]


def test_workflow_state_snapshot_id_helpers_are_stable_and_validated() -> None:
    timestamp = datetime(2026, 5, 31, 14, 0, tzinfo=UTC)

    snapshot_id = new_workflow_state_snapshot_id(
        workflow_name=" morning_report ",
        execution_id=" exec-1 ",
        timestamp=timestamp,
        wave_index=3,
        checkpoint_reference=" checkpoint-1 ",
    )
    duplicate_snapshot_id = new_workflow_state_snapshot_id(
        workflow_name="morning_report",
        execution_id="exec-1",
        timestamp=timestamp,
        wave_index=3,
        checkpoint_reference="checkpoint-1",
    )
    random_snapshot_id = new_random_workflow_state_snapshot_id()

    assert snapshot_id == duplicate_snapshot_id
    assert snapshot_id == (
        "workflow_state_snapshot:morning_report:exec-1:"
        "wave-3:2026-05-31T14:00:00+00:00:checkpoint-1"
    )
    assert random_snapshot_id.startswith("workflow_state_snapshot:")

    with pytest.raises(ValueError, match="wave_index"):
        new_workflow_state_snapshot_id(
            workflow_name="morning_report",
            execution_id="exec-1",
            timestamp=timestamp,
            wave_index=-1,
        )


def test_workflow_event_record_validates_event_fields() -> None:
    record = WorkflowEventRecord(
        event_type="runtime.node.completed",
        workflow_name="morning_report",
        execution_id="exec-1",
        timestamp=datetime.now(UTC),
        node_name="macro_analysis",
        payload={"progress": 1.0},
    )

    assert record.event_id
    assert record.event_type == "runtime.node.completed"

    with pytest.raises(ValueError, match="event_type"):
        WorkflowEventRecord(
            event_type=" ",
            workflow_name="morning_report",
            execution_id="exec-1",
            timestamp=datetime.now(UTC),
        )

    with pytest.raises(ValueError, match="wave_index"):
        WorkflowEventRecord(
            event_type="runtime.node.completed",
            workflow_name="morning_report",
            execution_id="exec-1",
            timestamp=datetime.now(UTC),
            wave_index=-1,
        )


def test_runtime_persistence_result_factories_validate_state() -> None:
    success = RuntimePersistenceResult.succeeded(
        records_persisted=2,
    )
    failure = RuntimePersistenceResult.failed(
        "database unavailable",
    )

    assert success.success is True
    assert success.records_persisted == 2
    assert success.error is None
    assert failure.success is False
    assert failure.records_persisted == 0
    assert failure.error == "database unavailable"

    with pytest.raises(ValueError, match="error"):
        RuntimePersistenceResult.failed(
            " ",
        )

    with pytest.raises(ValueError, match="successful"):
        RuntimePersistenceResult(
            success=True,
            error="unexpected",
        )

    with pytest.raises(ValueError, match="records_persisted"):
        RuntimePersistenceResult(
            success=True,
            records_persisted=-1,
        )
