from __future__ import annotations

from typing import cast

from sqlalchemy import CheckConstraint
from sqlalchemy import Table
from sqlalchemy.dialects.postgresql import JSONB

from core.database.base import Base
from core.database.models.runtime import WorkflowEventModel
from core.database.models.runtime import WorkflowNodeRunModel
from core.database.models.runtime import WorkflowRunModel
from core.database.models.runtime import WorkflowStateSnapshotModel


def test_runtime_models_are_imported_into_base_metadata() -> None:
    assert "workflow_runs" in Base.metadata.tables
    assert "workflow_node_runs" in Base.metadata.tables
    assert "workflow_events" in Base.metadata.tables
    assert "workflow_state_snapshots" in Base.metadata.tables


def test_workflow_run_model_uses_composite_execution_identity() -> None:
    columns = WorkflowRunModel.__table__.c
    primary_keys = {column.name for column in WorkflowRunModel.__table__.primary_key}

    assert primary_keys == {
        "workflow_name",
        "execution_id",
    }
    assert columns.workflow_name.nullable is False
    assert columns.execution_id.nullable is False
    assert columns.runtime_id.nullable is True
    assert columns.status.nullable is False
    assert columns.created_at.server_default is not None
    assert columns.updated_at.server_default is not None


def test_workflow_node_run_model_uses_node_execution_identity() -> None:
    columns = WorkflowNodeRunModel.__table__.c
    primary_keys = {
        column.name for column in WorkflowNodeRunModel.__table__.primary_key
    }

    assert primary_keys == {
        "workflow_name",
        "execution_id",
        "node_name",
        "wave_index",
    }
    assert columns.node_name.nullable is False
    assert columns.wave_index.nullable is False
    assert columns.status.nullable is False
    assert columns.runtime_id.nullable is True
    assert columns.created_at.server_default is not None
    assert columns.updated_at.server_default is not None


def test_workflow_event_model_uses_append_only_event_identity() -> None:
    columns = WorkflowEventModel.__table__.c
    primary_keys = {column.name for column in WorkflowEventModel.__table__.primary_key}

    assert primary_keys == {"event_id"}
    assert columns.event_type.nullable is False
    assert columns.workflow_name.nullable is False
    assert columns.execution_id.nullable is False
    assert columns.timestamp.nullable is False
    assert columns.created_at.server_default is not None


def test_workflow_state_snapshot_model_persists_audit_snapshots() -> None:
    columns = WorkflowStateSnapshotModel.__table__.c
    primary_keys = {
        column.name for column in WorkflowStateSnapshotModel.__table__.primary_key
    }

    assert primary_keys == {"snapshot_id"}
    assert columns.workflow_name.nullable is False
    assert columns.execution_id.nullable is False
    assert columns.workflow_status.nullable is False
    assert columns.timestamp.nullable is False
    assert columns.runtime_id.nullable is True
    assert columns.node_name.nullable is True
    assert columns.wave_index.nullable is True
    assert columns.checkpoint_reference.nullable is True
    assert columns.row_created_at.server_default is not None
    assert columns.row_updated_at.server_default is not None


def test_workflow_state_snapshot_model_indexes_audit_query_paths() -> None:
    indexes = _index_names(WorkflowStateSnapshotModel.__table__)

    assert indexes >= {
        "idx_workflow_state_snapshots_workflow_timestamp",
        "idx_workflow_state_snapshots_execution_timestamp",
        "idx_workflow_state_snapshots_runtime_timestamp",
        "idx_workflow_state_snapshots_wave_timestamp",
        "ix_workflow_state_snapshots_workflow_name",
        "ix_workflow_state_snapshots_execution_id",
        "ix_workflow_state_snapshots_runtime_id",
        "ix_workflow_state_snapshots_timestamp",
        "ix_workflow_state_snapshots_wave_index",
    }


def test_workflow_state_snapshot_model_enforces_non_negative_wave_index() -> None:
    assert _check_constraint_names(WorkflowStateSnapshotModel.__table__) >= {
        "ck_workflow_state_snapshots_wave_index_non_negative",
    }


def test_runtime_models_use_jsonb_for_serialized_boundaries() -> None:
    assert isinstance(
        WorkflowRunModel.__table__.c.metadata.type,
        JSONB,
    )
    assert isinstance(
        WorkflowRunModel.__table__.c.state_payload.type,
        JSONB,
    )
    assert isinstance(
        WorkflowNodeRunModel.__table__.c.metadata.type,
        JSONB,
    )
    assert isinstance(
        WorkflowNodeRunModel.__table__.c.outputs.type,
        JSONB,
    )
    assert isinstance(
        WorkflowEventModel.__table__.c.payload.type,
        JSONB,
    )
    assert isinstance(
        WorkflowEventModel.__table__.c.metadata.type,
        JSONB,
    )
    assert isinstance(
        WorkflowStateSnapshotModel.__table__.c.state_payload.type,
        JSONB,
    )
    assert isinstance(
        WorkflowStateSnapshotModel.__table__.c.metadata.type,
        JSONB,
    )


def _check_constraint_names(table: object) -> set[str]:
    sqlalchemy_table = cast(Table, table)
    names: set[str] = set()
    for constraint in sqlalchemy_table.constraints:
        if not isinstance(constraint, CheckConstraint):
            continue
        if isinstance(constraint.name, str):
            names.add(constraint.name)
    return names


def _index_names(table: object) -> set[str]:
    sqlalchemy_table = cast(Table, table)
    return {index.name for index in sqlalchemy_table.indexes if index.name is not None}
