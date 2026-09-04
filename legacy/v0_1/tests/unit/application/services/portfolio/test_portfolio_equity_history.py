from __future__ import annotations

from datetime import UTC, datetime

import pytest

from application.services.portfolio.portfolio_equity_history import (
    normalize_portfolio_equity_history,
)
from core.storage.persistence.lineage import PersistenceLineage


def test_normalize_portfolio_equity_history_builds_full_precision_points() -> None:
    points = normalize_portfolio_equity_history(
        account_id=" acct-1 ",
        source=" alpaca ",
        history={
            "timestamp": [1780689600, 1780776000],
            "equity": [100_000.123456789, 100_125.987654321],
            "profit_loss": [0.0, 125.864197532],
            "profit_loss_pct": [0.0, 0.00125864012345],
            "base_value": 100_000.123456789,
            "timeframe": " 1D ",
            "cashflow": {
                "deposit": [None, 250.125],
                "withdrawal": [10.5, None],
            },
        },
        lineage=PersistenceLineage(
            workflow_name="morning_report",
            execution_id="exec-1",
            runtime_id="runtime-1",
            node_name="portfolio_state",
        ),
    )

    assert len(points) == 2
    assert points[0].observed_at == datetime(
        2026,
        6,
        5,
        20,
        tzinfo=UTC,
    )
    assert points[0].equity == 100_000.123456789
    assert points[0].cashflow_payload == {"withdrawal": 10.5}
    assert points[1].profit_loss == 125.864197532
    assert points[1].cashflow_payload == {"deposit": 250.125}
    assert points[1].lineage.execution_id == "exec-1"
    assert points[1].portfolio_equity_history_point_id.endswith(
        "2026-06-06T20:00:00+00:00"
    )


def test_normalize_portfolio_equity_history_accepts_aware_datetimes() -> None:
    observed_at = datetime(2026, 6, 5, 14, tzinfo=UTC)

    points = normalize_portfolio_equity_history(
        account_id="acct-1",
        source="simulated",
        history={
            "timestamp": [observed_at],
            "equity": [100_000.0],
            "profit_loss": [-125.0],
            "profit_loss_pct": [-0.00125],
            "base_value": 100_125.0,
            "timeframe": "1D",
        },
    )

    assert points[0].observed_at == observed_at
    assert points[0].cashflow_payload == {}


def test_normalize_portfolio_equity_history_preserves_empty_provider_payload() -> None:
    assert (
        normalize_portfolio_equity_history(
            account_id="acct-1",
            source="backtest",
            history={},
        )
        == ()
    )


@pytest.mark.parametrize(
    ("history", "message"),
    [
        (
            {
                "timestamp": [1780689600],
                "equity": [100_000.0, 100_100.0],
                "profit_loss": [0.0],
                "profit_loss_pct": [0.0],
                "timeframe": "1D",
            },
            "equal lengths",
        ),
        (
            {
                "timestamp": [datetime(2026, 6, 5, 14)],
                "equity": [100_000.0],
                "profit_loss": [0.0],
                "profit_loss_pct": [0.0],
                "timeframe": "1D",
            },
            "timezone-aware",
        ),
        (
            {
                "timestamp": [1780689600],
                "equity": [100_000.0],
                "profit_loss": [0.0],
                "profit_loss_pct": [0.0],
                "timeframe": "1D",
                "cashflow": {"deposit": [1.0, 2.0]},
            },
            "match history length",
        ),
        (
            {
                "timestamp": [1780689600],
                "equity": [True],
                "profit_loss": [0.0],
                "profit_loss_pct": [0.0],
                "timeframe": "1D",
            },
            "equity must be numeric",
        ),
    ],
)
def test_normalize_portfolio_equity_history_rejects_invalid_payloads(
    history: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        normalize_portfolio_equity_history(
            account_id="acct-1",
            source="alpaca",
            history=history,
        )
