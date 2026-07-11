from __future__ import annotations

import pytest

from domain.workflow_outputs import RISK_EXPOSURE_SIGNAL_OUTPUT_CONTRACT
from domain.workflow_outputs import WORKFLOW_OUTPUT_SCHEMA_VERSION_V1
from core.runtime.state.runtime_context import RuntimeContext
from intelligence.risk.exposure.exposure_risk_agent import ExposureRiskAgent


@pytest.mark.asyncio
async def test_exposure_risk_agent_prefers_v2_portfolio_risk_fields() -> None:
    output = await ExposureRiskAgent()._execute(
        RuntimeContext(
            runtime_id="runtime-1",
            workflow_id="morning_report",
            execution_id="exec-1",
            node_outputs={
                "portfolio_state_builder": {
                    "outputs": {
                        "features": {
                            "portfolio_state": {
                                "gross_exposure": 0.90,
                                "net_exposure": 0.80,
                                "long_exposure": 0.85,
                                "short_exposure": 0.05,
                                "cash_pct": 0.10,
                                "leverage": 1.20,
                                "concentration_score": 0.72,
                                "portfolio_heat": 0.25,
                                "risk_intensity": 0.65,
                            },
                            "positions_state": {
                                "position_count": 2,
                                "positions": [
                                    {
                                        "symbol": "SPY",
                                        "exposure_weight": 0.90,
                                    }
                                ],
                            },
                            "risk_features": {
                                "portfolio_heat": 0.25,
                                "risk_intensity": 0.65,
                                "margin_utilization_ratio": 0.81,
                                "account_health": "restricted",
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
    assert features["position_count"] == 2
    assert features["concentration_risk"] == 0.72
    assert features["risk_intensity"] == 0.65
    assert features["margin_utilization_ratio"] == 0.81
    assert features["exposure_risk"] == 0.81
    assert output.outputs["regime"] == "critical"
    assert "overexposure" in output.outputs["risks"]
    assert output.output_contract == RISK_EXPOSURE_SIGNAL_OUTPUT_CONTRACT
    assert output.output_schema_version == WORKFLOW_OUTPUT_SCHEMA_VERSION_V1
