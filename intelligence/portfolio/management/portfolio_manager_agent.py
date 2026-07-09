from __future__ import annotations


from core.runtime.contracts.runtime_node import RuntimeNode
from core.runtime.state.runtime_context import RuntimeContext
from core.runtime.state.runtime_node_output import RuntimeNodeOutput


class PortfolioManagerAgent(RuntimeNode):
    """
    Polaris Portfolio Manager Agent

    ============================================================
    PURPOSE
    ============================================================
    - enforce portfolio-level execution governance
    - apply risk-aware capital scaling
    - validate synthesized regime posture
    - determine deployable portfolio posture

    ============================================================
    THIS NODE DOES NOT
    ============================================================
    - generate alpha
    - create signals
    - modify strategy synthesis
    - override risk layer

    ============================================================
    INPUTS
    ============================================================
    StrategySynthesisAgent
    RiskAggregatorAgent

    ============================================================
    OUTPUT
    ============================================================
    RuntimeNodeOutput.outputs portfolio intent payload
    """

    node_name = "portfolio_manager_agent"
    node_type = "portfolio_manager"

    # ============================================================
    # EXECUTE
    # ============================================================

    async def _execute(
        self,
        context: RuntimeContext,
    ) -> RuntimeNodeOutput:

        # ========================================================
        # UPSTREAM RESULTS
        # ========================================================

        synthesis_result = context.node_outputs["strategy_synthesis_agent"].get(
            "outputs", {}
        )

        risk_result = context.node_outputs["risk_aggregator_agent"].get("outputs", {})

        # ========================================================
        # SYNTHESIS OUTPUTS
        # ========================================================

        bull_weight = float(
            synthesis_result.get("features", {}).get(
                "bull_weight",
                0.33,
            )
        )

        bear_weight = float(
            synthesis_result.get("features", {}).get(
                "bear_weight",
                0.33,
            )
        )

        sideways_weight = float(
            synthesis_result.get("features", {}).get(
                "sideways_weight",
                0.34,
            )
        )

        posture = synthesis_result.get("regime", "neutral")

        synthesis_confidence = float(synthesis_result.get("confidence", 0.0))

        directional_score = float(synthesis_result.get("directional_score", 0.0))

        # ========================================================
        # TARGET ALLOCATION VECTOR
        # ========================================================

        target_allocation = {
            "bull": bull_weight,
            "bear": bear_weight,
            "sideways": sideways_weight,
        }

        # ========================================================
        # RISK STATE
        # ========================================================

        composite_risk = float(
            risk_result.get("features", {}).get("composite_risk", 0.0)
        )

        risk_pressure = float(risk_result.get("features", {}).get("risk_pressure", 0.0))

        stability_score = float(
            risk_result.get("features", {}).get("stability_score", 0.0)
        )

        risk_regime = risk_result.get("features", {}).get("risk_regime")

        # ========================================================
        # PORTFOLIO V2 RISK CONTEXT
        # ========================================================

        portfolio_output = context.node_outputs.get(
            "portfolio_state_builder",
            {},
        )

        portfolio_features = (
            portfolio_output.get("outputs", {}).get("features", {})
            if portfolio_output
            else {}
        )

        portfolio_risk_features = portfolio_features.get("risk_features", {}) or {}

        portfolio_heat = float(
            portfolio_risk_features.get(
                "portfolio_heat",
                0.0,
            )
        )

        risk_intensity = float(
            portfolio_risk_features.get(
                "risk_intensity",
                0.0,
            )
        )

        margin_utilization_ratio = float(
            portfolio_risk_features.get(
                "margin_utilization_ratio",
                0.0,
            )
        )

        account_restricted = any(
            bool(
                portfolio_risk_features.get(
                    flag,
                    False,
                )
            )
            for flag in (
                "trading_blocked",
                "account_blocked",
                "trade_suspended_by_user",
            )
        )

        composite_risk = max(
            composite_risk,
            portfolio_heat,
            risk_intensity,
            margin_utilization_ratio,
        )

        risk_pressure = max(
            risk_pressure,
            portfolio_heat,
            risk_intensity,
            margin_utilization_ratio,
        )

        if account_restricted:
            composite_risk = 1.0
            risk_pressure = 1.0
            stability_score = 0.0

        # ========================================================
        # DRIFT ANALYSIS
        # ========================================================

        baseline = 1.0 / 3.0

        drift = {k: abs(v - baseline) for k, v in target_allocation.items()}

        total_drift = sum(drift.values())

        # ========================================================
        # EXECUTION STATUS
        # ========================================================

        execution_status = self._execution_status(
            total_drift=total_drift,
            composite_risk=composite_risk,
            risk_pressure=risk_pressure,
            stability_score=stability_score,
        )

        # ========================================================
        # CAPITAL SCALE FACTOR
        # ========================================================

        scale_factor = self._scale_factor(
            risk_pressure=risk_pressure,
            stability_score=stability_score,
            execution_status=execution_status,
        )

        # ========================================================
        # PORTFOLIO REGIME
        # ========================================================

        portfolio_regime = self._portfolio_regime(
            posture=posture,
            composite_risk=composite_risk,
        )

        # ========================================================
        # CONFIDENCE
        # ========================================================

        confidence = (
            synthesis_confidence * 0.60
            + stability_score * 0.25
            + (1.0 - risk_pressure) * 0.15
        )

        confidence = max(
            0.0,
            min(1.0, confidence),
        )

        # ========================================================
        # RESULT
        # ========================================================

        result = dict(
            directional_score=directional_score,
            confidence=round(
                confidence,
                4,
            ),
            regime=portfolio_regime,
            signals=[
                execution_status,
                posture,
                risk_regime,
                f"drift_{round(total_drift, 4)}",
                f"scale_{round(scale_factor, 4)}",
            ],
            risks=[
                (
                    "elevated_risk_pressure"
                    if risk_pressure > 0.5
                    else "risk_pressure_normal"
                ),
                ("allocation_drift" if total_drift > 0.25 else "allocation_stable"),
                ("low_stability" if stability_score < 0.4 else "stability_normal"),
                (
                    "account_restricted"
                    if account_restricted
                    else "account_unrestricted"
                ),
                (
                    "high_portfolio_heat"
                    if portfolio_heat > 0.60
                    else "portfolio_heat_normal"
                ),
                (
                    "high_margin_utilization"
                    if margin_utilization_ratio > 0.60
                    else "margin_utilization_normal"
                ),
            ],
            recommendations=[
                (
                    "reduce_capital_deployment"
                    if scale_factor < 0.5
                    else "normal_capital_deployment"
                ),
                (
                    "preserve_capital"
                    if execution_status == "rejected"
                    else "allow_execution_pipeline"
                ),
                (
                    "respect_account_restrictions"
                    if account_restricted
                    else "account_restrictions_clear"
                ),
            ],
            features={
                # =================================================
                # ALLOCATION
                # =================================================
                "target_allocation": target_allocation,
                "drift": drift,
                "total_drift": total_drift,
                # =================================================
                # EXECUTION CONTROL
                # =================================================
                "execution_status": execution_status,
                "scale_factor": scale_factor,
                "portfolio_regime": portfolio_regime,
                # =================================================
                # RISK
                # =================================================
                "composite_risk": composite_risk,
                "risk_pressure": risk_pressure,
                "stability_score": stability_score,
                "risk_regime": risk_regime,
                "portfolio_heat": portfolio_heat,
                "risk_intensity": risk_intensity,
                "margin_utilization_ratio": margin_utilization_ratio,
                "account_restricted": account_restricted,
            },
        )

        # ========================================================
        # OUTPUT
        # ========================================================

        return RuntimeNodeOutput.success_output(
            outputs=result,
            execution_metadata={
                "node_name": self.node_name,
                "node_type": self.node_type,
                "confidence": (confidence),
                **(
                    {
                        "execution_status": execution_status,
                        "portfolio_regime": portfolio_regime,
                    }
                ),
            },
        )

    # ============================================================
    # EXECUTION STATUS
    # ============================================================

    def _execution_status(
        self,
        total_drift: float,
        composite_risk: float,
        risk_pressure: float,
        stability_score: float,
    ) -> str:

        if composite_risk > 0.80 or risk_pressure > 0.80 or stability_score < 0.20:
            return "rejected"

        if composite_risk > 0.60 or risk_pressure > 0.60 or total_drift > 0.35:
            return "restricted"

        if composite_risk > 0.40 or risk_pressure > 0.40 or total_drift > 0.20:
            return "approved_with_caution"

        return "approved"

    # ============================================================
    # SCALE FACTOR
    # ============================================================

    def _scale_factor(
        self,
        risk_pressure: float,
        stability_score: float,
        execution_status: str,
    ) -> float:

        scale = (1.0 - risk_pressure) * stability_score

        if execution_status == "rejected":
            scale *= 0.0

        elif execution_status == "restricted":
            scale *= 0.50

        elif execution_status == "approved_with_caution":
            scale *= 0.75

        return max(
            0.0,
            min(1.0, scale),
        )

    # ============================================================
    # PORTFOLIO REGIME
    # ============================================================

    def _portfolio_regime(
        self,
        posture: str,
        composite_risk: float,
    ) -> str:

        if composite_risk >= 0.75:
            return "capital_preservation"

        if posture == "risk_on":
            return "offensive"

        if posture == "risk_off":
            return "defensive"

        return "balanced"
