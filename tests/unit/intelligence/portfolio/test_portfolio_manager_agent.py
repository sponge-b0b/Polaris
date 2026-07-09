from __future__ import annotations

import pytest

from core.runtime.state.runtime_context import RuntimeContext
from intelligence.portfolio.management.portfolio_manager_agent import (
    PortfolioManagerAgent,
)


@pytest.mark.asyncio
async def test_portfolio_manager_rejects_restricted_account_state() -> None:
    output = await PortfolioManagerAgent()._execute(
        RuntimeContext(
            runtime_id="runtime-1",
            workflow_id="morning_report",
            execution_id="exec-1",
            node_outputs={
                "strategy_synthesis_agent": {
                    "outputs": {
                        "directional_score": 0.25,
                        "confidence": 0.80,
                        "regime": "risk_on",
                        "features": {
                            "bull_weight": 0.50,
                            "bear_weight": 0.20,
                            "sideways_weight": 0.30,
                        },
                    }
                },
                "risk_aggregator_agent": {
                    "outputs": {
                        "features": {
                            "composite_risk": 0.20,
                            "risk_pressure": 0.20,
                            "stability_score": 0.90,
                            "risk_regime": "stable",
                        }
                    }
                },
                "portfolio_state_builder": {
                    "outputs": {
                        "features": {
                            "risk_features": {
                                "portfolio_heat": 0.20,
                                "risk_intensity": 0.25,
                                "margin_utilization_ratio": 0.15,
                                "trading_blocked": True,
                                "account_blocked": False,
                                "trade_suspended_by_user": False,
                            }
                        }
                    }
                },
            },
        )
    )

    features = output.outputs["features"]
    assert features["execution_status"] == "rejected"
    assert features["scale_factor"] == 0.0
    assert features["account_restricted"] is True
    assert features["composite_risk"] == 1.0
    assert "account_restricted" in output.outputs["risks"]
    assert "respect_account_restrictions" in output.outputs["recommendations"]
