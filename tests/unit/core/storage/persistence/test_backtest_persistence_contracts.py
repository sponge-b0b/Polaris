from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from core.storage.persistence.backtesting import (
    BacktestArtifactRecord,
    BacktestMetricRecord,
)


def test_backtest_metric_requires_timezone_aware_recorded_at() -> None:
    with pytest.raises(ValueError, match="recorded_at must be timezone-aware"):
        BacktestMetricRecord(
            metric_id="metric-1",
            backtest_run_id="run-1",
            metric_name="total_return",
            metric_value=Decimal("0.10"),
            recorded_at=datetime(2026, 6, 25, 12),
        )


def test_backtest_artifact_requires_timezone_aware_generated_at() -> None:
    with pytest.raises(ValueError, match="generated_at must be timezone-aware"):
        BacktestArtifactRecord(
            artifact_id="artifact-1",
            backtest_run_id="run-1",
            artifact_format="markdown",
            content="# Report",
            mime_type="text/markdown",
            generated_at=datetime(2026, 6, 25, 12),
        )


def test_backtest_metric_and_artifact_accept_timezone_aware_timestamps() -> None:
    timestamp = datetime(2026, 6, 25, 12, tzinfo=UTC)

    metric = BacktestMetricRecord(
        metric_id="metric-1",
        backtest_run_id="run-1",
        metric_name="total_return",
        metric_value=Decimal("0.10"),
        recorded_at=timestamp,
    )
    artifact = BacktestArtifactRecord(
        artifact_id="artifact-1",
        backtest_run_id="run-1",
        artifact_format="markdown",
        content="# Report",
        mime_type="text/markdown",
        generated_at=timestamp,
    )

    assert metric.recorded_at == timestamp
    assert artifact.generated_at == timestamp
