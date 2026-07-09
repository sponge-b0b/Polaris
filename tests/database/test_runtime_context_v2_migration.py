from __future__ import annotations

import json
from datetime import datetime
from datetime import timezone
from typing import Any

import pytest
from pytest_alembic.runner import MigrationContext
from sqlalchemy import Engine
from sqlalchemy import text

_PREVIOUS_REVISION = "f6a7b8c9d0e1"
_RUNTIME_CONTEXT_V2_REVISION = "a7b8c9d0e1f2"
_SIMULATION_TIME = "2026-06-27T14:30:00+00:00"


def _default_namespaces() -> dict[str, dict[str, Any]]:
    return {
        "market": {
            "session": "regular",
            "market_open": True,
            "timestamp": None,
            "index_levels": {},
            "index_returns": {},
            "trend_regime": "neutral",
            "volatility_regime": "normal",
            "risk_regime": "neutral",
            "realized_volatility": 0.0,
            "implied_volatility": 0.0,
            "volatility_compression": 0.0,
            "volatility_expansion": 0.0,
            "macro_regime": "neutral",
            "yield_curve_signal": "flat",
            "liquidity_signal": "stable",
            "earnings_pressure": 0.0,
            "macro_event_risk": 0.0,
            "fed_event_risk": 0.0,
            "market_breadth_score": 0.0,
            "sector_strength": {},
            "symbols_universe": [],
            "metadata": {},
        },
        "portfolio": {
            "equity": 0.0,
            "portfolio_value": 0.0,
            "cash": 0.0,
            "buying_power": 0.0,
            "realized_pnl": 0.0,
            "unrealized_pnl": 0.0,
            "total_pnl": 0.0,
            "peak_equity": 0.0,
            "drawdown_absolute": 0.0,
            "drawdown_percent": 0.0,
            "capital_base": 0.0,
            "capital_utilization": 0.0,
            "cash_ratio": 0.0,
            "positions": {},
            "gross_exposure": 0.0,
            "net_exposure": 0.0,
            "long_exposure": 0.0,
            "short_exposure": 0.0,
            "leverage_ratio": 0.0,
            "open_orders": [],
            "risk_flags": [],
            "account_health": "healthy",
            "metadata": {},
        },
        "risk": {
            "total_exposure": 0.0,
            "gross_exposure": 0.0,
            "net_exposure": 0.0,
            "leverage_ratio": 0.0,
            "concentration_risk": 0.0,
            "sector_exposure": {},
            "current_drawdown": 0.0,
            "max_drawdown": 0.0,
            "drawdown_velocity": 0.0,
            "recovery_pressure": 0.0,
            "realized_volatility_risk": 0.0,
            "implied_volatility_risk": 0.0,
            "volatility_regime": "normal",
            "volatility_expansion_signal": 0.0,
            "volatility_compression_signal": 0.0,
            "cash_buffer_ratio": 0.0,
            "liquidity_stress": 0.0,
            "execution_fragility": 0.0,
            "spread_widening_risk": 0.0,
            "earnings_event_risk": 0.0,
            "macro_event_risk": 0.0,
            "fed_event_risk": 0.0,
            "event_cluster_density": 0.0,
            "regime_stability_score": 0.0,
            "risk_regime": "neutral",
            "regime_conflict_score": 0.0,
            "slippage_risk": 0.0,
            "latency_sensitivity": 0.0,
            "fill_quality_risk": 0.0,
            "execution_risk_flags": [],
            "overall_risk_score": 0.0,
            "risk_band": "normal",
            "metadata": {},
        },
        "strategy": {
            "strategy_votes": {},
            "strategy_weights": {},
            "adaptive_weight_multiplier": 1.0,
            "regime_weight_adjustment": {},
            "consensus_directional_score": 0.0,
            "consensus_confidence": 0.0,
            "agreement_score": 0.0,
            "disagreement_score": 0.0,
            "vote_distribution": {},
            "regime_alignment_scores": {},
            "regime_compatibility_score": 0.0,
            "dominant_regime_alignment": "neutral",
            "conflicting_strategies": [],
            "suppressed_strategies": [],
            "override_signals": [],
            "conflict_score": 0.0,
            "final_directional_bias": 0.0,
            "final_confidence": 0.0,
            "portfolio_tilt": "neutral",
            "execution_signal": "hold",
            "position_bias_adjustment": 0.0,
            "metadata": {},
        },
    }


def _legacy_context(*, run_id: str) -> dict[str, Any]:
    workflow_inputs = {
        "symbol": "SPY",
        "backtest": {
            "backtest_run_id": f"backtest-{run_id}",
            "scenario_id": "scenario-1",
            "provider_profile": "backtest_synthetic",
        },
    }
    return {
        "runtime_id": f"runtime-{run_id}",
        "workflow_id": "workflow-1",
        "execution_id": f"execution-{run_id}",
        "mode": "backtest",
        "created_at": "2026-06-27T14:00:00+00:00",
        "simulation_time": _SIMULATION_TIME,
        "state_version": 7,
        "state": {
            **_default_namespaces(),
            "timestamp": _SIMULATION_TIME,
            "runtime_mode": "backtest",
            "execution_id": f"execution-{run_id}",
            "step_index": 4,
            "shared_state": workflow_inputs,
            "metadata": {
                "backtest_run_id": f"backtest-{run_id}",
                "scenario_id": "scenario-1",
                "simulation_time": _SIMULATION_TIME,
            },
        },
        "artifact_refs": {"report": {"artifact_id": "artifact-1", "path": "report.md"}},
        "node_outputs": {
            "technical": {
                "node_name": "technical",
                "status": "succeeded",
                "success": True,
                "outputs": {"technical_score": 0.75},
                "metadata": {},
                "errors": [],
                "namespace_updates": {},
            }
        },
        "errors": [],
        "trace_context": {"trace_id": "trace-1"},
    }


def _insert_completed_run(
    engine: Engine,
    *,
    run_id: str,
    context: dict[str, Any],
    child_namespace_updates: dict[str, Any] | None = None,
) -> None:
    now = datetime(2026, 6, 27, 14, tzinfo=timezone.utc)
    workflow_inputs = context["state"]["shared_state"]
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO completed_workflow_runs (
                    run_id, workflow_name, workflow_id, execution_id, runtime_id,
                    status, success, started_at, completed_at, duration_seconds,
                    schema_version, context_json, inputs_json, outputs_json,
                    metadata, errors_json, node_count, completed_node_count,
                    failed_node_count
                ) VALUES (
                    :run_id, 'morning_report', 'workflow-1', :execution_id,
                    :runtime_id, 'succeeded', true, :now, :now, 1.0, 1,
                    CAST(:context_json AS jsonb), CAST(:inputs_json AS jsonb),
                    '{"report": "complete"}'::jsonb, CAST(:metadata AS jsonb),
                    '[]'::jsonb, 1, 1, 0
                )
                """
            ),
            {
                "run_id": run_id,
                "execution_id": context["execution_id"],
                "runtime_id": context["runtime_id"],
                "now": now,
                "context_json": json.dumps(context),
                "inputs_json": json.dumps(workflow_inputs),
                "metadata": json.dumps({"state_version": 7, "preserve": "value"}),
            },
        )
        connection.execute(
            text(
                """
                INSERT INTO completed_workflow_node_outputs (
                    node_output_id, run_id, workflow_name, execution_id,
                    node_name, node_type, status, success, started_at,
                    completed_at, duration_seconds, outputs, metadata, errors_json
                ) VALUES (
                    :node_output_id, :run_id, 'morning_report', :execution_id,
                    'technical', 'technical', 'succeeded', true, :now, :now,
                    0.5, '{"technical_score": 0.75}'::jsonb,
                    CAST(:metadata AS jsonb), '[]'::jsonb
                )
                """
            ),
            {
                "node_output_id": f"node-output-{run_id}",
                "run_id": run_id,
                "execution_id": context["execution_id"],
                "now": now,
                "metadata": json.dumps(
                    {"namespace_updates": child_namespace_updates or {}}
                ),
            },
        )


def test_runtime_context_v2_migration_preserves_canonical_data_and_round_trips(
    alembic_runner: MigrationContext,
    alembic_engine: object,
) -> None:
    engine = alembic_engine
    assert isinstance(engine, Engine)
    alembic_runner.migrate_up_before(_RUNTIME_CONTEXT_V2_REVISION)
    legacy_context = _legacy_context(run_id="round-trip")
    _insert_completed_run(engine, run_id="round-trip", context=legacy_context)

    alembic_runner.migrate_up_to(_RUNTIME_CONTEXT_V2_REVISION)

    with engine.connect() as connection:
        run = connection.execute(
            text(
                """
                SELECT schema_version, context_json, inputs_json, metadata
                FROM completed_workflow_runs
                WHERE run_id = 'round-trip'
                """
            )
        ).one()
        child_metadata = connection.execute(
            text(
                """
                SELECT metadata
                FROM completed_workflow_node_outputs
                WHERE run_id = 'round-trip'
                """
            )
        ).scalar_one()

    context = run.context_json
    assert run.schema_version == 2
    assert context["schema_version"] == 2
    assert context["context_version"] == 7
    assert "state" not in context
    assert "state_version" not in context
    assert context["workflow_inputs"]["symbol"] == "SPY"
    assert context["workflow_inputs"]["backtest"]["step_index"] == 4
    assert context["workflow_inputs"]["backtest"]["simulation_time"] == _SIMULATION_TIME
    assert run.inputs_json == context["workflow_inputs"]
    assert context["artifact_refs"] == {
        "report": {"artifact_id": "artifact-1", "path": "report.md"}
    }
    assert context["trace_context"] == {"trace_id": "trace-1"}
    assert "namespace_updates" not in context["node_outputs"]["technical"]
    assert child_metadata == {}
    assert run.metadata == {
        "schema_version": 2,
        "context_version": 7,
        "preserve": "value",
    }

    alembic_runner.migrate_down_to(_PREVIOUS_REVISION)

    with engine.connect() as connection:
        downgraded = connection.execute(
            text(
                """
                SELECT schema_version, context_json, inputs_json, metadata
                FROM completed_workflow_runs
                WHERE run_id = 'round-trip'
                """
            )
        ).one()
        downgraded_child_metadata = connection.execute(
            text(
                """
                SELECT metadata
                FROM completed_workflow_node_outputs
                WHERE run_id = 'round-trip'
                """
            )
        ).scalar_one()

    restored = downgraded.context_json
    assert downgraded.schema_version == 1
    assert restored["state_version"] == 7
    assert restored["state"]["shared_state"] == downgraded.inputs_json
    assert restored["state"]["step_index"] == 4
    assert restored["state"]["timestamp"] == _SIMULATION_TIME
    assert restored["state"]["market"] == _default_namespaces()["market"]
    assert restored["node_outputs"]["technical"]["namespace_updates"] == {}
    assert downgraded_child_metadata == {"namespace_updates": {}}
    assert downgraded.metadata == {"state_version": 7, "preserve": "value"}


def test_runtime_context_v2_migration_rejects_business_namespace_before_mutation(
    alembic_runner: MigrationContext,
    alembic_engine: object,
) -> None:
    engine = alembic_engine
    assert isinstance(engine, Engine)
    alembic_runner.migrate_up_before(_RUNTIME_CONTEXT_V2_REVISION)
    valid_context = _legacy_context(run_id="a-valid")
    unsafe_context = _legacy_context(run_id="z-unsafe")
    unsafe_context["state"]["market"]["trend_regime"] = "bullish"
    _insert_completed_run(engine, run_id="a-valid", context=valid_context)
    _insert_completed_run(engine, run_id="z-unsafe", context=unsafe_context)

    with pytest.raises(RuntimeError, match="non-default market namespace"):
        alembic_runner.migrate_up_to(_RUNTIME_CONTEXT_V2_REVISION)

    with engine.connect() as connection:
        rows = connection.execute(
            text(
                """
                SELECT run_id, schema_version, context_json
                FROM completed_workflow_runs
                ORDER BY run_id
                """
            )
        ).all()

    assert [row.schema_version for row in rows] == [1, 1]
    assert all("state" in row.context_json for row in rows)


def test_runtime_context_v2_migration_rejects_persisted_namespace_updates(
    alembic_runner: MigrationContext,
    alembic_engine: object,
) -> None:
    engine = alembic_engine
    assert isinstance(engine, Engine)
    alembic_runner.migrate_up_before(_RUNTIME_CONTEXT_V2_REVISION)
    context = _legacy_context(run_id="persisted-namespace")
    _insert_completed_run(
        engine,
        run_id="persisted-namespace",
        context=context,
        child_namespace_updates={"market": {"trend_regime": "bullish"}},
    )

    with pytest.raises(RuntimeError, match="persisted node technical"):
        alembic_runner.migrate_up_to(_RUNTIME_CONTEXT_V2_REVISION)

    with engine.connect() as connection:
        run = connection.execute(
            text(
                """
                SELECT schema_version, context_json
                FROM completed_workflow_runs
                WHERE run_id = 'persisted-namespace'
                """
            )
        ).one()

    assert run.schema_version == 1
    assert "state" in run.context_json
