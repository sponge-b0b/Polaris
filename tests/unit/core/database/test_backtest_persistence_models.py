from __future__ import annotations

from typing import cast

from sqlalchemy import DateTime

from core.database.models.backtesting import BacktestArtifactModel
from core.database.models.backtesting import BacktestMetricModel


def test_backtest_metric_has_required_domain_timestamp() -> None:
    columns = BacktestMetricModel.__table__.columns

    assert columns.recorded_at.nullable is False
    assert cast(DateTime, columns.recorded_at.type).timezone is True
    assert columns.recorded_at.server_default is None


def test_backtest_artifact_has_required_domain_timestamp() -> None:
    columns = BacktestArtifactModel.__table__.columns

    assert columns.generated_at.nullable is False
    assert cast(DateTime, columns.generated_at.type).timezone is True
    assert columns.generated_at.server_default is None
