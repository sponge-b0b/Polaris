from typing import Any

from core.runtime.contracts.runtime_node import RuntimeNode
from core.runtime.state.runtime_context import RuntimeContext
from core.runtime.state.runtime_node_output import RuntimeNodeOutput

from integration.contracts.risk.risk_signal_contract import RiskSignalContract
from integration.adapters.risk import risk_runtime_adapter


class RiskSignalBuilder(RuntimeNode):
    """
    Polaris Risk Signal Builder (V2 FIXED)

    FIXES:
    ------
    - removes invalid `risk_score` dependency
    - uses RuntimeNodeOutput.outputs features consistently
    - normalizes primitive risk agent outputs correctly
    - supports missing agents safely

    PURPOSE:
    --------
    Aggregates primitive risk signals into a canonical RiskSignalContract
    BEFORE regime coupling layer.
    """

    node_name = "risk_signal_builder"
    node_type = "risk_builder"

    # ============================================================
    # EXECUTE
    # ============================================================

    async def _execute(self, context: RuntimeContext) -> RuntimeNodeOutput:

        # ========================================================
        # PRIMITIVE RISK AGENTS
        # ========================================================

        drawdown_output = context.node_outputs.get("drawdown_risk_agent")
        exposure_output = context.node_outputs.get("exposure_risk_agent")
        volatility_output = context.node_outputs.get("volatility_risk_agent")

        # ========================================================
        # SAFE RESULT EXTRACTION
        # ========================================================

        volatility_result = (
            volatility_output.get("outputs", {}) if volatility_output else None
        )
        drawdown_result = (
            drawdown_output.get("outputs", {}) if drawdown_output else None
        )
        exposure_result = (
            exposure_output.get("outputs", {}) if exposure_output else None
        )

        # ========================================================
        # SAFE FEATURE EXTRACTION (FIXED)
        # ========================================================

        volatility_features = (volatility_result or {}).get("features", {})
        drawdown_features = (drawdown_result or {}).get("features", {})
        exposure_features = (exposure_result or {}).get("features", {})

        # ========================================================
        # CORRECT SCORE SOURCES
        # ========================================================
        # PRIMARY: features["composite_risk"]
        # FALLBACK: directional_score * -1

        volatility_risk_val = max(
            0.0,
            min(1.0, self.extract_risk(volatility_result, volatility_features)),
        )

        drawdown_risk_val = max(
            0.0,
            min(1.0, self.extract_risk(drawdown_result, drawdown_features)),
        )

        exposure_risk_val = max(
            0.0,
            min(1.0, self.extract_risk(exposure_result, exposure_features)),
        )

        # ========================================================
        # COMPOSITE RISK (FIXED FUSION)
        # ========================================================

        composite_risk = (
            volatility_risk_val * 0.40
            + drawdown_risk_val * 0.35
            + exposure_risk_val * 0.25
        )

        composite_risk = max(0.0, min(1.0, composite_risk))

        # ========================================================
        # RISK PRESSURE
        # ========================================================

        risk_pressure = volatility_risk_val * 0.5 + exposure_risk_val * 0.5

        risk_pressure = max(0.0, min(1.0, risk_pressure))

        # ========================================================
        # STABILITY SCORE
        # ========================================================

        stability_score = max(0.0, min(1.0, 1.0 - composite_risk))

        # ========================================================
        # CONTRACT BUILD
        # ========================================================

        risk_contract = RiskSignalContract(
            volatility_risk=round(volatility_risk_val, 4),
            drawdown_risk=round(drawdown_risk_val, 4),
            exposure_risk=round(exposure_risk_val, 4),
            composite_risk=round(composite_risk, 4),
            risk_pressure=round(risk_pressure, 4),
            stability_score=round(stability_score, 4),
            risk_regime="unclassified",
            risk_bias="neutral",
            recommendations=[],
            features={
                "primitive_sources": {
                    "volatility": volatility_risk_val,
                    "drawdown": drawdown_risk_val,
                    "exposure": exposure_risk_val,
                }
            },
        )

        # ========================================================
        # RUNTIME OUTPUT
        # ========================================================

        return risk_runtime_adapter.to_runtime_output(
            node_name=self.node_name,
            node_type=self.node_type,
            contract=risk_contract,
        )

    def extract_risk(
        self,
        result: dict[str, Any] | None,
        features: dict[str, Any],
    ) -> float:
        if features and "composite_risk" in features:
            return float(features["composite_risk"])

        if result is not None:
            return float(result.get("directional_score", 0.0)) * -1.0

        return 0.0
