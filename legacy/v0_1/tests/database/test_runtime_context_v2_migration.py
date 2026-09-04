from __future__ import annotations

import json
from datetime import UTC, datetime

from pytest_alembic.runner import MigrationContext
from sqlalchemy import Engine, text

from core.runtime.state.runtime_context import (
    RUNTIME_CONTEXT_SCHEMA_VERSION,
    RuntimeContext,
)

_SIMULATION_TIME = datetime(2026, 6, 27, 14, 30, tzinfo=UTC)


def _canonical_runtime_context(*, run_id: str) -> RuntimeContext:
    return RuntimeContext(
        runtime_id=f"runtime-{run_id}",
        workflow_id="workflow-1",
        execution_id=f"execution-{run_id}",
        mode="backtest",
        created_at=datetime(2026, 6, 27, 14, tzinfo=UTC),
        simulation_time=_SIMULATION_TIME,
        context_version=7,
        workflow_inputs={
            "symbol": "SPY",
            "backtest": {
                "backtest_run_id": f"backtest-{run_id}",
                "scenario_id": "scenario-1",
                "provider_profile": "backtest_synthetic",
            },
        },
        artifact_refs={"report": {"artifact_id": "artifact-1", "path": "report.md"}},
        node_outputs={
            "technical": {
                "node_name": "technical",
                "status": "succeeded",
                "success": True,
                "outputs": {"technical_score": 0.75},
                "metadata": {},
                "errors": [],
            }
        },
        errors=[],
        trace_context=None,
    )


def _insert_completed_run(
    engine: Engine,
    *,
    run_id: str,
    context: RuntimeContext,
) -> None:
    now = datetime(2026, 6, 27, 14, tzinfo=UTC)
    context_payload = context.to_dict()
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                DELETE FROM completed_workflow_runs
                WHERE run_id = :run_id OR execution_id = :execution_id
                """
            ),
            {
                "run_id": run_id,
                "execution_id": context.execution_id,
            },
        )
        connection.execute(
            text(
                """
                INSERT INTO completed_workflow_runs (
                    run_id, workflow_name, workflow_id, execution_id, runtime_id,
                    status, success, execution_mode, started_at, completed_at,
                    duration_seconds, schema_version, context_json, inputs_json,
                    outputs_json, metadata, errors_json, node_count,
                    completed_node_count, failed_node_count
                ) VALUES (
                    :run_id, 'morning_report', :workflow_id, :execution_id,
                    :runtime_id, 'succeeded', true, :execution_mode, :now, :now,
                    1.0, :schema_version, CAST(:context_json AS jsonb),
                    CAST(:inputs_json AS jsonb), '{"report": "complete"}'::jsonb,
                    CAST(:metadata AS jsonb), '[]'::jsonb, 1, 1, 0
                )
                """
            ),
            {
                "run_id": run_id,
                "workflow_id": context.workflow_id,
                "execution_id": context.execution_id,
                "runtime_id": context.runtime_id,
                "execution_mode": context.mode,
                "now": now,
                "schema_version": RUNTIME_CONTEXT_SCHEMA_VERSION,
                "context_json": json.dumps(context_payload),
                "inputs_json": json.dumps(context.workflow_inputs),
                "metadata": json.dumps(
                    {
                        "schema_version": RUNTIME_CONTEXT_SCHEMA_VERSION,
                        "context_version": context.context_version,
                    }
                ),
            },
        )


def test_current_runtime_context_schema_persists_canonical_v2_payload(
    alembic_runner: MigrationContext,
    alembic_engine: Engine,
) -> None:
    """Validate the current migrated schema without pinning squashed revision IDs."""

    alembic_runner.migrate_up_to("heads")
    run_id = "runtime-context-schema-v2"
    context = _canonical_runtime_context(run_id=run_id)

    _insert_completed_run(alembic_engine, run_id=run_id, context=context)

    with alembic_engine.connect() as connection:
        row = connection.execute(
            text(
                """
                SELECT schema_version, context_json, inputs_json, metadata
                FROM completed_workflow_runs
                WHERE run_id = :run_id
                """
            ),
            {"run_id": run_id},
        ).one()

    context_payload = row.context_json
    restored_context = RuntimeContext.from_dict(context_payload)

    assert row.schema_version == RUNTIME_CONTEXT_SCHEMA_VERSION
    assert context_payload["schema_version"] == RUNTIME_CONTEXT_SCHEMA_VERSION
    assert "state" not in context_payload
    assert "state_version" not in context_payload
    assert context_payload["workflow_inputs"] == row.inputs_json
    assert restored_context.workflow_inputs == context.workflow_inputs
    assert restored_context.context_version == context.context_version
    assert restored_context.node_outputs["technical"]["outputs"] == {
        "technical_score": 0.75,
    }
    assert row.metadata["schema_version"] == RUNTIME_CONTEXT_SCHEMA_VERSION
    assert row.metadata["context_version"] == context.context_version
