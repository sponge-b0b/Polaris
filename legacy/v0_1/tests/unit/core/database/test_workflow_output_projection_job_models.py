from __future__ import annotations

from typing import cast

from sqlalchemy import CheckConstraint, Table

from core.database.base import Base
from core.database.models.projections import WorkflowOutputProjectionJobModel


def test_workflow_output_projection_job_model_is_imported_into_base_metadata() -> None:
    assert "workflow_output_projection_jobs" in Base.metadata.tables


def test_workflow_output_projection_job_model_uses_deterministic_identity() -> None:
    columns = WorkflowOutputProjectionJobModel.__table__.c
    primary_keys = {
        column.name for column in WorkflowOutputProjectionJobModel.__table__.primary_key
    }

    assert primary_keys == {"projection_job_id"}
    assert columns.run_id.nullable is False
    assert columns.workflow_name.nullable is False
    assert columns.execution_id.nullable is False
    assert columns.node_name.nullable is False
    assert columns.projector_name.nullable is False
    assert columns.output_contract.nullable is False
    assert columns.output_schema_version.nullable is False
    assert columns.source_fingerprint.nullable is False
    assert columns.status.nullable is False
    assert columns.attempt_count.nullable is False
    assert columns.last_error.nullable is True
    assert columns.created_at.server_default is not None
    assert columns.updated_at.server_default is not None


def test_workflow_output_projection_job_model_enforces_projection_constraints() -> None:
    assert _check_constraint_names(WorkflowOutputProjectionJobModel.__table__) >= {
        "ck_workflow_output_projection_jobs_status",
        "ck_workflow_output_projection_jobs_attempt_count_non_negative",
        "ck_workflow_output_projection_jobs_schema_version_positive",
    }


def test_workflow_output_projection_job_model_indexes_operational_queries() -> None:
    indexes = _index_names(WorkflowOutputProjectionJobModel.__table__)

    assert indexes >= {
        "ix_workflow_output_projection_jobs_run_id",
        "ix_workflow_output_projection_jobs_workflow_name",
        "ix_workflow_output_projection_jobs_execution_id",
        "ix_workflow_output_projection_jobs_node_name",
        "ix_workflow_output_projection_jobs_projector_name",
        "ix_workflow_output_projection_jobs_output_contract",
        "ix_workflow_output_projection_jobs_output_schema_version",
        "ix_workflow_output_projection_jobs_status",
        "idx_workflow_projection_jobs_status_created_at",
        "idx_workflow_projection_jobs_workflow_execution",
        "idx_workflow_projection_jobs_projector_node",
        "idx_workflow_projection_jobs_pending_failed",
        "idx_workflow_projection_jobs_contract_version",
    }


def test_workflow_output_projection_job_model_enforces_idempotency_constraint() -> None:
    table = cast(Table, WorkflowOutputProjectionJobModel.__table__)
    unique_constraint_names = {
        constraint.name
        for constraint in table.constraints
        if constraint.name is not None
    }

    assert "uq_workflow_output_projection_jobs_source" in unique_constraint_names


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
