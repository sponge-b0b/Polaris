from __future__ import annotations

import pytest

from core.runtime.state.runtime_context import RuntimeContext
from intelligence.execution.execution_risk.execution_risk_guard import (
    ExecutionRiskGuard,
)


@pytest.mark.asyncio
async def test_execution_risk_guard_blocks_hard_account_restrictions() -> None:
    output = await ExecutionRiskGuard()._execute(
        RuntimeContext(
            runtime_id="runtime-1",
            workflow_id="morning_report",
            execution_id="exec-1",
            node_outputs={
                "risk_aggregator_agent": {
                    "outputs": {
                        "recommendations": [
                            "monitor_risk",
                        ],
                        "features": {
                            "composite_risk": 0.10,
                            "risk_pressure": 0.10,
                            "stability_score": 0.95,
                            "volatility_risk": 0.05,
                            "drawdown_risk": 0.05,
                            "exposure_risk": 0.05,
                            "risk_regime": "stable",
                            "risk_bias": "neutral",
                        },
                    }
                },
                "trade_packager": {
                    "outputs": {
                        "features": {
                            "position_sizing_hint": 0.80,
                        }
                    }
                },
                "portfolio_state_builder": {
                    "outputs": {
                        "features": {
                            "risk_features": {
                                "margin_utilization_ratio": 0.20,
                                "trading_blocked": False,
                                "account_blocked": True,
                                "trade_suspended_by_user": False,
                                "transfers_blocked": False,
                                "pattern_day_trader": False,
                            }
                        }
                    }
                },
            },
        )
    )

    guard = output.outputs["features"]["execution_guard"]
    assert guard["mode"] == "blocked"
    assert guard["adjusted_position_size"] == 0.0
    assert guard["hard_account_restriction"] is True
    assert guard["account_restrictions"]["account_blocked"] is True
    assert "account_blocked" in guard["flags"]
    assert "respect_account_restrictions" in output.outputs["recommendations"]
    assert "block_new_execution" in output.outputs["recommendations"]


@pytest.mark.asyncio
async def test_execution_risk_guard_scales_position_for_single_risk_breach() -> None:
    output = await ExecutionRiskGuard()._execute(
        RuntimeContext(
            runtime_id="runtime-1",
            workflow_id="morning_report",
            execution_id="exec-2",
            node_outputs={
                "risk_aggregator_agent": {
                    "outputs": {
                        "recommendations": ["monitor_risk"],
                        "features": {
                            "composite_risk": 0.71,
                            "risk_pressure": 0.50,
                            "stability_score": 0.80,
                            "volatility_risk": 0.60,
                            "drawdown_risk": 0.50,
                            "exposure_risk": 0.50,
                            "risk_regime": "elevated",
                            "risk_bias": "neutral",
                        },
                    }
                },
                "trade_packager": {
                    "outputs": {
                        "features": {
                            "position_sizing_hint": 0.80,
                        }
                    }
                },
            },
        )
    )

    guard = output.outputs["features"]["execution_guard"]
    assert guard["mode"] == "scaled"
    assert guard["flags"] == ["composite_risk_breach"]
    assert guard["position_size_original"] == 0.80
    assert guard["adjusted_position_size"] == pytest.approx(0.60)
    assert guard["hard_account_restriction"] is False
    assert "scale_position_size" in output.outputs["recommendations"]
