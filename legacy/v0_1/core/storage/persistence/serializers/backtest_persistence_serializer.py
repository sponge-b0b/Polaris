from __future__ import annotations

from typing import Any, cast

from core.database.models.backtesting import (
    BacktestArtifactModel,
    BacktestFillModel,
    BacktestMetricModel,
    BacktestPortfolioSnapshotModel,
    BacktestRunModel,
    BacktestScenarioModel,
    BacktestStepModel,
)
from core.storage.persistence.backtesting import (
    BacktestArtifactRecord,
    BacktestFillRecord,
    BacktestMetricRecord,
    BacktestPortfolioSnapshotRecord,
    BacktestRunRecord,
    BacktestScenarioRecord,
    BacktestStepRecord,
    JsonArray,
    JsonObject,
)


class BacktestPersistenceSerializer:
    """
    Serializer between typed backtest persistence records and SQLAlchemy models.

    JSON payloads are introduced here because this module is the PostgreSQL
    boundary. Backtesting services continue to exchange typed records.
    """

    @staticmethod
    def scenario_values(
        record: BacktestScenarioRecord,
    ) -> dict[str, Any]:
        return {
            "scenario_id": record.scenario_id,
            "name": record.name,
            "workflow_name": record.workflow_name,
            "start_date": record.start_date,
            "end_date": record.end_date,
            "symbols": list(record.symbols),
            "benchmark_symbol": record.benchmark_symbol,
            "initial_cash": record.initial_cash,
            "provider_profile": record.provider_profile,
            "initial_positions": list(record.initial_positions),
            "parameters": dict(record.parameters),
            "expected_outcomes": list(record.expected_outcomes),
            "metadata_payload": dict(record.metadata),
        }

    @staticmethod
    def run_values(
        record: BacktestRunRecord,
    ) -> dict[str, Any]:
        return {
            "backtest_run_id": record.backtest_run_id,
            "scenario_id": record.scenario_id,
            "workflow_name": record.workflow_name,
            "status": record.status,
            "success": record.success,
            "started_at": record.started_at,
            "completed_at": record.completed_at,
            "metrics_payload": dict(record.metrics),
            "metadata_payload": dict(record.metadata),
        }

    @staticmethod
    def step_values(
        record: BacktestStepRecord,
    ) -> dict[str, Any]:
        return {
            "step_id": record.step_id,
            "backtest_run_id": record.backtest_run_id,
            "step_index": record.step_index,
            "timestamp": record.timestamp,
            "workflow_run_id": record.workflow_run_id,
            "success": record.success,
            "node_output_keys": list(record.node_output_keys),
            "summary_payload": dict(record.summary),
        }

    @staticmethod
    def portfolio_snapshot_values(
        record: BacktestPortfolioSnapshotRecord,
    ) -> dict[str, Any]:
        return {
            "snapshot_id": record.snapshot_id,
            "backtest_run_id": record.backtest_run_id,
            "step_id": record.step_id,
            "timestamp": record.timestamp,
            "cash": record.cash,
            "equity": record.equity,
            "market_value": record.market_value,
            "positions": dict(record.positions),
            "metadata_payload": dict(record.metadata),
        }

    @staticmethod
    def fill_values(
        record: BacktestFillRecord,
    ) -> dict[str, Any]:
        return {
            "fill_id": record.fill_id,
            "backtest_run_id": record.backtest_run_id,
            "step_id": record.step_id,
            "timestamp": record.timestamp,
            "symbol": record.symbol,
            "side": record.side,
            "quantity": record.quantity,
            "price": record.price,
            "status": record.status,
            "reason": record.reason,
            "realized_pnl": record.realized_pnl,
            "metadata_payload": dict(record.metadata),
        }

    @staticmethod
    def metric_values(
        record: BacktestMetricRecord,
    ) -> dict[str, Any]:
        return {
            "metric_id": record.metric_id,
            "backtest_run_id": record.backtest_run_id,
            "metric_name": record.metric_name,
            "metric_value": record.metric_value,
            "recorded_at": record.recorded_at,
            "metadata_payload": dict(record.metadata),
        }

    @staticmethod
    def artifact_values(
        record: BacktestArtifactRecord,
    ) -> dict[str, Any]:
        return {
            "artifact_id": record.artifact_id,
            "backtest_run_id": record.backtest_run_id,
            "artifact_format": record.artifact_format,
            "content": record.content,
            "mime_type": record.mime_type,
            "generated_at": record.generated_at,
            "metadata_payload": dict(record.metadata),
        }

    @staticmethod
    def scenario_from_model(
        model: BacktestScenarioModel,
    ) -> BacktestScenarioRecord:
        return BacktestScenarioRecord(
            scenario_id=model.scenario_id,
            name=model.name,
            workflow_name=model.workflow_name,
            start_date=model.start_date,
            end_date=model.end_date,
            symbols=tuple(cast(list[str], model.symbols)),
            benchmark_symbol=model.benchmark_symbol,
            initial_cash=model.initial_cash,
            provider_profile=model.provider_profile,
            initial_positions=tuple(cast(JsonArray, model.initial_positions)),
            parameters=cast(JsonObject, model.parameters),
            expected_outcomes=tuple(cast(JsonArray, model.expected_outcomes)),
            metadata=cast(JsonObject, model.metadata_payload),
        )

    @staticmethod
    def run_from_model(
        model: BacktestRunModel,
    ) -> BacktestRunRecord:
        return BacktestRunRecord(
            backtest_run_id=model.backtest_run_id,
            scenario_id=model.scenario_id,
            workflow_name=model.workflow_name,
            status=model.status,
            success=model.success,
            started_at=model.started_at,
            completed_at=model.completed_at,
            metrics=cast(JsonObject, model.metrics_payload),
            metadata=cast(JsonObject, model.metadata_payload),
        )

    @staticmethod
    def step_from_model(
        model: BacktestStepModel,
    ) -> BacktestStepRecord:
        return BacktestStepRecord(
            step_id=model.step_id,
            backtest_run_id=model.backtest_run_id,
            step_index=model.step_index,
            timestamp=model.timestamp,
            workflow_run_id=model.workflow_run_id,
            success=model.success,
            node_output_keys=tuple(cast(list[str], model.node_output_keys)),
            summary=cast(JsonObject, model.summary_payload),
        )

    @staticmethod
    def portfolio_snapshot_from_model(
        model: BacktestPortfolioSnapshotModel,
    ) -> BacktestPortfolioSnapshotRecord:
        return BacktestPortfolioSnapshotRecord(
            snapshot_id=model.snapshot_id,
            backtest_run_id=model.backtest_run_id,
            step_id=model.step_id,
            timestamp=model.timestamp,
            cash=model.cash,
            equity=model.equity,
            market_value=model.market_value,
            positions=cast(JsonObject, model.positions),
            metadata=cast(JsonObject, model.metadata_payload),
        )

    @staticmethod
    def fill_from_model(
        model: BacktestFillModel,
    ) -> BacktestFillRecord:
        return BacktestFillRecord(
            fill_id=model.fill_id,
            backtest_run_id=model.backtest_run_id,
            step_id=model.step_id,
            timestamp=model.timestamp,
            symbol=model.symbol,
            side=model.side,
            quantity=model.quantity,
            price=model.price,
            status=model.status,
            reason=model.reason,
            realized_pnl=model.realized_pnl,
            metadata=cast(JsonObject, model.metadata_payload),
        )

    @staticmethod
    def metric_from_model(
        model: BacktestMetricModel,
    ) -> BacktestMetricRecord:
        return BacktestMetricRecord(
            metric_id=model.metric_id,
            backtest_run_id=model.backtest_run_id,
            metric_name=model.metric_name,
            metric_value=model.metric_value,
            recorded_at=model.recorded_at,
            metadata=cast(JsonObject, model.metadata_payload),
        )

    @staticmethod
    def artifact_from_model(
        model: BacktestArtifactModel,
    ) -> BacktestArtifactRecord:
        return BacktestArtifactRecord(
            artifact_id=model.artifact_id,
            backtest_run_id=model.backtest_run_id,
            artifact_format=model.artifact_format,
            content=model.content,
            mime_type=model.mime_type,
            generated_at=model.generated_at,
            metadata=cast(JsonObject, model.metadata_payload),
        )
