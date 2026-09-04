from __future__ import annotations

import json
from decimal import Decimal
from typing import Any, cast

from application.services.backtesting import BacktestResult
from core.storage.persistence.backtesting import (
    BacktestArtifactRecord,
    BacktestFillRecord,
    BacktestMetricRecord,
    BacktestPersistenceBundle,
    BacktestPortfolioSnapshotRecord,
    BacktestRunRecord,
    BacktestScenarioRecord,
    BacktestStepRecord,
    JsonArray,
    JsonObject,
)

MIME_TYPES = {
    "console": "text/plain",
    "json": "application/json",
    "markdown": "text/markdown",
}


def backtest_result_to_persistence_bundle(
    result: BacktestResult,
) -> BacktestPersistenceBundle:
    """
    Map an application backtest result into curated persistence records.

    Raw node outputs are intentionally not copied into PostgreSQL backtest
    tables. Step records persist only node-output keys and a compact summary so
    callers can join back to runtime persistence by workflow_run_id when raw
    execution details are needed.
    """

    scenario_payload = _json_safe(result.scenario.to_dict())
    metrics_payload = _json_safe(result.metrics.to_dict())
    metadata_payload = _json_safe(result.metadata)

    steps: list[BacktestStepRecord] = []
    snapshots: list[BacktestPortfolioSnapshotRecord] = []
    fills: list[BacktestFillRecord] = []

    for step_index, step in enumerate(result.steps):
        step_id = _step_id(result.backtest_run_id, step_index)
        node_output_keys = tuple(sorted(str(key) for key in step.node_outputs))
        step_record = BacktestStepRecord(
            step_id=step_id,
            backtest_run_id=result.backtest_run_id,
            step_index=step_index,
            timestamp=step.timestamp,
            workflow_run_id=step.workflow_run_id,
            success=step.success,
            node_output_keys=node_output_keys,
            summary={
                "node_output_count": len(node_output_keys),
                "simulated_fill_count": len(step.simulated_fills),
            },
        )
        steps.append(step_record)
        snapshots.append(
            BacktestPortfolioSnapshotRecord(
                snapshot_id=f"{step_id}:snapshot",
                backtest_run_id=result.backtest_run_id,
                step_id=step_id,
                timestamp=step.portfolio_snapshot.timestamp,
                cash=step.portfolio_snapshot.cash,
                equity=step.portfolio_snapshot.equity,
                market_value=step.portfolio_snapshot.market_value,
                positions=cast(
                    JsonObject,
                    _json_safe(step.portfolio_snapshot.positions),
                ),
            )
        )
        for fill_index, fill in enumerate(step.simulated_fills):
            fills.append(
                BacktestFillRecord(
                    fill_id=f"{step_id}:fill:{fill_index}",
                    backtest_run_id=result.backtest_run_id,
                    step_id=step_id,
                    timestamp=fill.timestamp,
                    symbol=fill.symbol,
                    side=fill.side,
                    quantity=fill.quantity,
                    price=fill.price,
                    status=fill.status,
                    reason=fill.reason,
                    realized_pnl=fill.realized_pnl,
                )
            )

    return BacktestPersistenceBundle(
        scenario=BacktestScenarioRecord(
            scenario_id=result.scenario.scenario_id,
            name=result.scenario.name,
            workflow_name=result.scenario.workflow_name,
            start_date=result.scenario.start_date,
            end_date=result.scenario.end_date,
            symbols=result.scenario.symbols,
            benchmark_symbol=result.scenario.benchmark_symbol,
            initial_cash=result.scenario.initial_cash,
            provider_profile=result.scenario.provider_profile,
            initial_positions=cast(JsonArray, scenario_payload["initial_positions"]),
            parameters=cast(JsonObject, scenario_payload["parameters"]),
            expected_outcomes=cast(JsonArray, scenario_payload["expected_outcomes"]),
        ),
        run=BacktestRunRecord(
            backtest_run_id=result.backtest_run_id,
            scenario_id=result.scenario.scenario_id,
            workflow_name=result.scenario.workflow_name,
            status=result.status,
            success=result.success,
            started_at=result.started_at,
            completed_at=result.completed_at,
            metrics=cast(JsonObject, metrics_payload),
            metadata=cast(JsonObject, metadata_payload),
        ),
        steps=tuple(steps),
        portfolio_snapshots=tuple(snapshots),
        fills=tuple(fills),
        metrics=_metric_records(result),
        artifacts=_artifact_records(result),
    )


def _metric_records(
    result: BacktestResult,
) -> tuple[BacktestMetricRecord, ...]:
    records: list[BacktestMetricRecord] = []
    for metric_name, metric_value in result.metrics.to_dict().items():
        records.append(
            BacktestMetricRecord(
                metric_id=f"{result.backtest_run_id}:metric:{metric_name}",
                backtest_run_id=result.backtest_run_id,
                metric_name=metric_name,
                metric_value=Decimal(str(metric_value)),
                recorded_at=result.completed_at,
            )
        )
    return tuple(records)


def _artifact_records(
    result: BacktestResult,
) -> tuple[BacktestArtifactRecord, ...]:
    records: list[BacktestArtifactRecord] = []
    for artifact_format, content in sorted(result.artifacts.items()):
        records.append(
            BacktestArtifactRecord(
                artifact_id=f"{result.backtest_run_id}:artifact:{artifact_format}",
                backtest_run_id=result.backtest_run_id,
                artifact_format=artifact_format,
                content=content,
                mime_type=MIME_TYPES.get(artifact_format, "text/plain"),
                generated_at=result.completed_at,
            )
        )
    return tuple(records)


def _step_id(
    backtest_run_id: str,
    step_index: int,
) -> str:
    return f"{backtest_run_id}:step:{step_index}"


def _json_safe(
    value: object,
) -> Any:
    return json.loads(
        json.dumps(
            value,
            default=str,
        )
    )
