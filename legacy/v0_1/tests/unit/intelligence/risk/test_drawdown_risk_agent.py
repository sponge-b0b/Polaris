from __future__ import annotations

import pytest

from core.runtime.state.runtime_context import RuntimeContext
from domain.workflow_outputs import (
    RISK_DRAWDOWN_SIGNAL_OUTPUT_CONTRACT,
    WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
)
from intelligence.risk.drawdown.drawdown_risk_agent import DrawdownRiskAgent


@pytest.mark.asyncio
async def test_drawdown_risk_agent_consumes_canonical_v2_drawdown_percent() -> None:
    output = await DrawdownRiskAgent()._execute(
        RuntimeContext(
            runtime_id="runtime-1",
            workflow_id="morning_report",
            execution_id="exec-1",
            node_outputs={
                "portfolio_state_builder": {
                    "outputs": {
                        "features": {
                            "portfolio_state": {},
                            "equity_state": {
                                "equity": 100_000.0,
                                "peak_equity": 100_000.0,
                                "drawdown_percent": 0.42,
                            },
                            "risk_features": {
                                "margin_utilization_ratio": 0.30,
                                "account_health": "watch",
                                "trading_blocked": False,
                                "account_blocked": False,
                            },
                        }
                    }
                }
            },
        )
    )

    features = output.outputs["features"]
    assert features["drawdown_percent"] == 0.42
    assert features["drawdown_risk"] == 0.42
    assert features["margin_utilization_ratio"] == 0.30
    assert features["account_health"] == "watch"
    assert output.outputs["regime"] == "elevated"
    assert output.output_contract == RISK_DRAWDOWN_SIGNAL_OUTPUT_CONTRACT
    assert output.output_schema_version == WORKFLOW_OUTPUT_SCHEMA_VERSION_V1
