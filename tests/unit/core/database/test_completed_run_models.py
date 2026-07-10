from __future__ import annotations

from typing import cast

from sqlalchemy import CheckConstraint
from sqlalchemy import Table

from core.database.models.completed_runs import CompletedWorkflowRunModel


def test_completed_run_model_has_first_class_execution_mode() -> None:
    column = CompletedWorkflowRunModel.__table__.c.execution_mode

    assert column.nullable is False
    assert column.default is not None
    assert column.server_default is not None


def test_completed_run_model_constrains_execution_mode_values() -> None:
    table = cast(Table, CompletedWorkflowRunModel.__table__)
    constraints = {
        constraint.name: constraint
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }

    constraint = constraints["ck_completed_workflow_runs_execution_mode"]
    constraint_sql = str(constraint.sqltext)

    assert "normal" in constraint_sql
    assert "replay" in constraint_sql
    assert "backtest" in constraint_sql
    assert "simulated" in constraint_sql
