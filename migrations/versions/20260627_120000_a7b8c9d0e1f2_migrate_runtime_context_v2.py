"""migrate completed runs to runtime context schema v2

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-06-27 12:00:00.000000
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from collections.abc import Sequence
from copy import deepcopy
from typing import Any

import sqlalchemy as sa
from alembic import op

revision: str = "a7b8c9d0e1f2"
down_revision: str | None = "f6a7b8c9d0e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CONTEXT_SCHEMA_VERSION = 2
_LEGACY_SCHEMA_VERSION = 1

_DEFAULT_MARKET_STATE: dict[str, Any] = {
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
}
_DEFAULT_PORTFOLIO_STATE: dict[str, Any] = {
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
}
_DEFAULT_RISK_STATE: dict[str, Any] = {
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
}
_DEFAULT_STRATEGY_STATE: dict[str, Any] = {
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
}
_DEFAULT_NAMESPACES = {
    "market": _DEFAULT_MARKET_STATE,
    "portfolio": _DEFAULT_PORTFOLIO_STATE,
    "risk": _DEFAULT_RISK_STATE,
    "strategy": _DEFAULT_STRATEGY_STATE,
}


def upgrade() -> None:
    connection = op.get_bind()
    rows = list(
        connection.execute(
            sa.text(
                """
                SELECT run_id, schema_version, context_json, inputs_json,
                       metadata AS run_metadata
                FROM completed_workflow_runs
                ORDER BY run_id
                """
            )
        ).mappings()
    )
    prepared_updates: list[dict[str, Any]] = []

    for row in rows:
        if row["schema_version"] == _CONTEXT_SCHEMA_VERSION:
            _validate_current_context(row["run_id"], row["context_json"])
            continue
        if row["schema_version"] != _LEGACY_SCHEMA_VERSION:
            _abort(row["run_id"], "unsupported completed-run schema version")

        context = _object(row["run_id"], "context_json", row["context_json"])
        state = _object(row["run_id"], "context_json.state", context.get("state"))
        _validate_legacy_state(row["run_id"], context, state)
        _validate_namespace_updates(row["run_id"], context)

        workflow_inputs = deepcopy(
            _object(
                row["run_id"],
                "context_json.state.shared_state",
                state.get("shared_state", {}),
            )
        )
        existing_inputs = context.get("workflow_inputs")
        if existing_inputs not in (None, {}) and existing_inputs != workflow_inputs:
            _abort(row["run_id"], "conflicting legacy workflow inputs")
        _preserve_backtest_execution_fields(
            run_id=row["run_id"],
            context=context,
            state=state,
            workflow_inputs=workflow_inputs,
        )

        context_version = _integer(
            row["run_id"],
            "context_json.state_version",
            context.get("state_version", 0),
        )
        migrated_context = {
            key: deepcopy(value)
            for key, value in context.items()
            if key
            not in {"state", "state_version", "workflow_inputs", "schema_version"}
        }
        migrated_context.update(
            {
                "schema_version": _CONTEXT_SCHEMA_VERSION,
                "context_version": context_version,
                "workflow_inputs": workflow_inputs,
                "node_outputs": _without_namespace_updates(
                    context.get("node_outputs", {})
                ),
            }
        )
        migrated_metadata = _migrate_run_metadata(
            row["run_id"],
            row["run_metadata"],
            context_version=context_version,
            target_version=_CONTEXT_SCHEMA_VERSION,
        )
        prepared_updates.append(
            {
                "run_id": row["run_id"],
                "schema_version": _CONTEXT_SCHEMA_VERSION,
                "context_json": json.dumps(migrated_context),
                "inputs_json": json.dumps(workflow_inputs),
                "metadata": json.dumps(migrated_metadata),
            }
        )

    _validate_persisted_namespace_updates(connection)

    for parameters in prepared_updates:
        connection.execute(
            sa.text(
                """
                UPDATE completed_workflow_runs
                SET schema_version = :schema_version,
                    context_json = CAST(:context_json AS jsonb),
                    inputs_json = CAST(:inputs_json AS jsonb),
                    metadata = CAST(:metadata AS jsonb)
                WHERE run_id = :run_id
                """
            ),
            parameters,
        )

    connection.execute(
        sa.text(
            """
            UPDATE completed_workflow_node_outputs
            SET metadata = metadata - 'namespace_updates'
            WHERE metadata ? 'namespace_updates'
            """
        )
    )


def downgrade() -> None:
    connection = op.get_bind()
    rows = list(
        connection.execute(
            sa.text(
                """
                SELECT run_id, schema_version, context_json, metadata AS run_metadata
                FROM completed_workflow_runs
                ORDER BY run_id
                """
            )
        ).mappings()
    )
    prepared_updates: list[dict[str, Any]] = []

    for row in rows:
        if row["schema_version"] != _CONTEXT_SCHEMA_VERSION:
            _abort(row["run_id"], "downgrade requires completed-run schema version 2")
        context = _object(row["run_id"], "context_json", row["context_json"])
        _validate_current_context(row["run_id"], context)
        if "state" in context or "state_version" in context:
            _abort(row["run_id"], "v2 context contains legacy state fields")

        workflow_inputs = deepcopy(
            _object(
                row["run_id"],
                "context_json.workflow_inputs",
                context.get("workflow_inputs", {}),
            )
        )
        context_version = _integer(
            row["run_id"],
            "context_json.context_version",
            context.get("context_version", 0),
        )
        step_index = _backtest_step_index(row["run_id"], workflow_inputs)
        legacy_state = {
            **{name: deepcopy(value) for name, value in _DEFAULT_NAMESPACES.items()},
            "timestamp": context.get("simulation_time"),
            "runtime_mode": context.get("mode", "live"),
            "execution_id": context.get("execution_id"),
            "step_index": step_index,
            "shared_state": workflow_inputs,
            "metadata": {},
        }
        legacy_context = {
            key: deepcopy(value)
            for key, value in context.items()
            if key
            not in {"schema_version", "context_version", "workflow_inputs", "state"}
        }
        legacy_context.update(
            {
                "state_version": context_version,
                "state": legacy_state,
                "node_outputs": _with_empty_namespace_updates(
                    context.get("node_outputs", {})
                ),
            }
        )
        legacy_metadata = _migrate_run_metadata(
            row["run_id"],
            row["run_metadata"],
            context_version=context_version,
            target_version=_LEGACY_SCHEMA_VERSION,
        )
        prepared_updates.append(
            {
                "run_id": row["run_id"],
                "schema_version": _LEGACY_SCHEMA_VERSION,
                "context_json": json.dumps(legacy_context),
                "inputs_json": json.dumps(workflow_inputs),
                "metadata": json.dumps(legacy_metadata),
            }
        )

    _validate_persisted_namespace_updates(connection)

    for parameters in prepared_updates:
        connection.execute(
            sa.text(
                """
                UPDATE completed_workflow_runs
                SET schema_version = :schema_version,
                    context_json = CAST(:context_json AS jsonb),
                    inputs_json = CAST(:inputs_json AS jsonb),
                    metadata = CAST(:metadata AS jsonb)
                WHERE run_id = :run_id
                """
            ),
            parameters,
        )

    connection.execute(
        sa.text(
            """
            UPDATE completed_workflow_node_outputs
            SET metadata = metadata || '{"namespace_updates": {}}'::jsonb
            WHERE NOT metadata ? 'namespace_updates'
            """
        )
    )


def _validate_legacy_state(
    run_id: str,
    context: Mapping[str, Any],
    state: Mapping[str, Any],
) -> None:
    for namespace, default_value in _DEFAULT_NAMESPACES.items():
        if state.get(namespace) != default_value:
            _abort(run_id, f"non-default {namespace} namespace contains business data")

    if state.get("runtime_mode", "live") != context.get("mode", "live"):
        _abort(run_id, "state runtime_mode conflicts with context mode")
    state_execution_id = state.get("execution_id")
    if state_execution_id not in (None, context.get("execution_id")):
        _abort(run_id, "state execution_id conflicts with context execution_id")
    if state.get("timestamp") not in (None, context.get("simulation_time")):
        _abort(run_id, "state timestamp conflicts with context simulation_time")

    step_index = _integer(
        run_id, "context_json.state.step_index", state.get("step_index", 0)
    )
    if step_index < 0:
        _abort(run_id, "state step_index cannot be negative")

    metadata = _object(
        run_id,
        "context_json.state.metadata",
        state.get("metadata", {}),
    )
    if metadata:
        _validate_redundant_backtest_metadata(run_id, context, state, metadata)


def _validate_redundant_backtest_metadata(
    run_id: str,
    context: Mapping[str, Any],
    state: Mapping[str, Any],
    metadata: Mapping[str, Any],
) -> None:
    shared_state = _object(
        run_id,
        "context_json.state.shared_state",
        state.get("shared_state", {}),
    )
    backtest = _object(
        run_id,
        "context_json.state.shared_state.backtest",
        shared_state.get("backtest"),
    )
    expected = {
        "backtest_run_id": backtest.get("backtest_run_id"),
        "scenario_id": backtest.get("scenario_id"),
        "simulation_time": context.get("simulation_time"),
    }
    if set(metadata) - set(expected) or any(
        metadata.get(key) != expected.get(key) for key in metadata
    ):
        _abort(run_id, "state metadata contains non-redundant values")


def _validate_namespace_updates(run_id: str, context: Mapping[str, Any]) -> None:
    node_outputs = _object(
        run_id,
        "context_json.node_outputs",
        context.get("node_outputs", {}),
    )
    for node_name, value in node_outputs.items():
        node_output = _object(
            run_id,
            f"context_json.node_outputs.{node_name}",
            value,
        )
        if node_output.get("namespace_updates") not in (None, {}):
            _abort(run_id, f"node {node_name} contains non-empty namespace updates")


def _preserve_backtest_execution_fields(
    *,
    run_id: str,
    context: Mapping[str, Any],
    state: Mapping[str, Any],
    workflow_inputs: dict[str, Any],
) -> None:
    backtest_value = workflow_inputs.get("backtest")
    if backtest_value is None:
        if state.get("step_index", 0) != 0:
            _abort(run_id, "non-zero step_index exists without backtest inputs")
        return
    backtest = _object(run_id, "workflow_inputs.backtest", backtest_value)
    migrated_backtest = deepcopy(backtest)
    step_index = _integer(
        run_id, "context_json.state.step_index", state.get("step_index", 0)
    )
    existing_step_index = migrated_backtest.get("step_index")
    if existing_step_index is not None and existing_step_index != step_index:
        _abort(run_id, "backtest step_index conflicts with legacy runtime state")
    migrated_backtest["step_index"] = step_index

    simulation_time = context.get("simulation_time")
    if simulation_time is not None:
        existing_simulation_time = migrated_backtest.get("simulation_time")
        if (
            existing_simulation_time is not None
            and existing_simulation_time != simulation_time
        ):
            _abort(run_id, "backtest simulation_time conflicts with runtime context")
        migrated_backtest["simulation_time"] = simulation_time
    workflow_inputs["backtest"] = migrated_backtest


def _backtest_step_index(run_id: str, workflow_inputs: Mapping[str, Any]) -> int:
    backtest = workflow_inputs.get("backtest")
    if backtest is None:
        return 0
    backtest_mapping = _object(
        run_id, "context_json.workflow_inputs.backtest", backtest
    )
    return _integer(
        run_id,
        "workflow_inputs.backtest.step_index",
        backtest_mapping.get("step_index", 0),
    )


def _validate_current_context(run_id: str, value: Any) -> None:
    context = _object(run_id, "context_json", value)
    if context.get("schema_version") != _CONTEXT_SCHEMA_VERSION:
        _abort(run_id, "schema_version column and context_json disagree")
    _object(run_id, "context_json.workflow_inputs", context.get("workflow_inputs", {}))
    _integer(run_id, "context_json.context_version", context.get("context_version", 0))
    _validate_namespace_updates(run_id, context)


def _validate_persisted_namespace_updates(connection: Any) -> None:
    row = (
        connection.execute(
            sa.text(
                """
            SELECT run_id, node_name
            FROM completed_workflow_node_outputs
            WHERE metadata ? 'namespace_updates'
              AND metadata -> 'namespace_updates' <> '{}'::jsonb
            ORDER BY run_id, node_name
            LIMIT 1
            """
            )
        )
        .mappings()
        .first()
    )
    if row is not None:
        _abort(
            row["run_id"],
            f"persisted node {row['node_name']} contains non-empty namespace updates",
        )


def _without_namespace_updates(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    migrated: dict[str, Any] = {}
    for node_name, node_value in value.items():
        if isinstance(node_value, Mapping):
            migrated[str(node_name)] = {
                key: deepcopy(item)
                for key, item in node_value.items()
                if key != "namespace_updates"
            }
        else:
            migrated[str(node_name)] = deepcopy(node_value)
    return migrated


def _with_empty_namespace_updates(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    migrated: dict[str, Any] = {}
    for node_name, node_value in value.items():
        if isinstance(node_value, Mapping):
            migrated[str(node_name)] = {
                **deepcopy(dict(node_value)),
                "namespace_updates": {},
            }
        else:
            migrated[str(node_name)] = deepcopy(node_value)
    return migrated


def _migrate_run_metadata(
    run_id: str,
    value: Any,
    *,
    context_version: int,
    target_version: int,
) -> dict[str, Any]:
    metadata = deepcopy(_object(run_id, "completed_workflow_runs.metadata", value))
    if target_version == _CONTEXT_SCHEMA_VERSION:
        metadata.pop("state_version", None)
        metadata["schema_version"] = _CONTEXT_SCHEMA_VERSION
        metadata["context_version"] = context_version
    else:
        metadata.pop("schema_version", None)
        metadata.pop("context_version", None)
        metadata["state_version"] = context_version
    return metadata


def _object(run_id: str, field_name: str, value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        _abort(run_id, f"{field_name} must be a JSON object")
    return dict(value)


def _integer(run_id: str, field_name: str, value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        _abort(run_id, f"{field_name} must be an integer")
    return value


def _abort(run_id: str, reason: str) -> None:
    raise RuntimeError(
        "RuntimeContext v2 migration aborted before mutation for completed run "
        f"{run_id!r}: {reason}. Review and curate this row explicitly."
    )
