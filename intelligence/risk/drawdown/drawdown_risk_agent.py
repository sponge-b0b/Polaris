from core.runtime.contracts.runtime_node import RuntimeNode
from core.runtime.state.runtime_context import RuntimeContext
from core.runtime.state.runtime_node_output import (
    RuntimeNodeOutput,
)

from integration.contracts.risk.risk_signal_contract import (
    RiskSignalContract,
)

from integration.adapters.risk import (
    risk_runtime_adapter,
)


class DrawdownRiskAgent(RuntimeNode):
    """
    Polaris Drawdown Risk Agent

    ============================================================
    PURPOSE
    ============================================================
    - evaluate portfolio drawdown pressure
    - measure equity curve deterioration
    - detect capital instability
    - produce normalized drawdown risk contract

    ============================================================
    ARCHITECTURE
    ============================================================
    INPUT:
        PortfolioStateBuilder output

    REQUIRED CONTEXT:
        context.node_outputs["portfolio_state_builder"]

    OUTPUT:
        RuntimeNodeOutput
            -> RiskSignalContract
            -> RuntimeNodeOutput.outputs

    ============================================================
    IMPORTANT
    ============================================================
    This node ONLY computes drawdown risk.

    It does NOT:
    - aggregate all risk agents
    - perform execution logic
    - modify portfolio state
    """

    node_name: str = "drawdown_risk_agent"
    node_type: str = "risk_agent"

    # ============================================================
    # MAIN EXECUTION
    # ============================================================

    async def _execute(
        self,
        context: RuntimeContext,
    ) -> RuntimeNodeOutput:

        # ========================================================
        # PORTFOLIO STATE
        # ========================================================

        portfolio_state_output = context.node_outputs["portfolio_state_builder"]

        if portfolio_state_output is None:
            raise ValueError("Missing portfolio_state_builder in context.")

        portfolio_features = portfolio_state_output.get("outputs", {}).get(
            "features", {}
        )

        # ========================================================
        # EQUITY DATA
        # ========================================================

        equity = portfolio_features.get("equity_state", {}) or {}

        current_equity = float(equity.get("equity", 0.0))

        peak_equity = float(
            equity.get(
                "peak_equity",
                current_equity,
            )
        )

        # ========================================================
        # PORTFOLIO DATA
        # ========================================================

        portfolio = (
            portfolio_features.get(
                "portfolio_state",
                {},
            )
            or {}
        )

        risk_features = (
            portfolio_features.get(
                "risk_features",
                {},
            )
            or {}
        )

        canonical_drawdown = abs(
            float(
                equity.get(
                    "drawdown_percent",
                    portfolio.get(
                        "drawdown_percent",
                        0.0,
                    ),
                )
            )
        )

        realized_drawdown = abs(
            float(
                portfolio.get(
                    "realized_drawdown",
                    canonical_drawdown,
                )
            )
        )

        unrealized_drawdown = abs(
            float(
                portfolio.get(
                    "unrealized_drawdown",
                    canonical_drawdown,
                )
            )
        )

        # ========================================================
        # PEAK-TO-TROUGH DRAWDOWN
        # ========================================================

        peak_to_trough = self._compute_peak_drawdown(
            current_equity=current_equity,
            peak_equity=peak_equity,
        )

        # ========================================================
        # COMPOSITE DRAWDOWN MODEL
        # ========================================================

        component_drawdown = (
            peak_to_trough * 0.50
            + realized_drawdown * 0.30
            + unrealized_drawdown * 0.20
        )

        composite_drawdown = self._clamp(
            max(
                canonical_drawdown,
                component_drawdown,
            )
        )

        # ========================================================
        # RISK MODEL
        # ========================================================

        drawdown_risk = abs(composite_drawdown)

        stability_score = self._compute_stability(drawdown_risk)

        risk_pressure = drawdown_risk

        # ========================================================
        # DOMAIN CONTRACT
        # ========================================================

        contract = RiskSignalContract(
            volatility_risk=0.0,
            drawdown_risk=drawdown_risk,
            exposure_risk=0.0,
            composite_risk=composite_drawdown,
            risk_pressure=risk_pressure,
            stability_score=stability_score,
            risk_regime=self._classify_regime(drawdown_risk),
            risk_bias=self._bias(drawdown_risk),
            recommendations=self._recommend(drawdown_risk),
            features={
                # ====================================================
                # EQUITY
                # ====================================================
                "current_equity": current_equity,
                "peak_equity": peak_equity,
                # ====================================================
                # DRAWDOWN COMPONENTS
                # ====================================================
                "drawdown_percent": canonical_drawdown,
                "peak_to_trough": peak_to_trough,
                "realized_drawdown": realized_drawdown,
                "unrealized_drawdown": unrealized_drawdown,
                "margin_utilization_ratio": risk_features.get(
                    "margin_utilization_ratio",
                    0.0,
                ),
                "account_health": risk_features.get(
                    "account_health",
                    "unknown",
                ),
                "trading_blocked": risk_features.get(
                    "trading_blocked",
                    False,
                ),
                "account_blocked": risk_features.get(
                    "account_blocked",
                    False,
                ),
                # ====================================================
                # FINAL METRICS
                # ====================================================
                "drawdown_risk": drawdown_risk,
                "composite_drawdown": composite_drawdown,
                "stability_score": stability_score,
            },
        )

        # ========================================================
        # CANONICAL OUTPUT
        # ========================================================

        return risk_runtime_adapter.to_runtime_output(
            node_name=self.node_name,
            node_type=self.node_type,
            contract=contract,
        )

    # ============================================================
    # PEAK DRAWDOWN
    # ============================================================

    def _compute_peak_drawdown(
        self,
        current_equity: float,
        peak_equity: float,
    ) -> float:

        if peak_equity <= 0:
            return 0.0

        drawdown = (peak_equity - current_equity) / peak_equity

        return max(0.0, drawdown)

    # ============================================================
    # STABILITY MODEL
    # ============================================================

    def _compute_stability(
        self,
        drawdown_risk: float,
    ) -> float:

        stability = 1.0 - drawdown_risk

        return max(
            0.0,
            min(1.0, stability),
        )

    # ============================================================
    # REGIME CLASSIFICATION
    # ============================================================

    def _classify_regime(
        self,
        risk: float,
    ) -> str:

        if risk >= 0.70:
            return "critical"

        if risk >= 0.50:
            return "stressed"

        if risk >= 0.30:
            return "elevated"

        return "stable"

    # ============================================================
    # RISK BIAS
    # ============================================================

    def _bias(
        self,
        risk: float,
    ) -> str:

        if risk >= 0.60:
            return "risk_off"

        if risk <= 0.20:
            return "risk_on"

        return "neutral"

    # ============================================================
    # RECOMMENDATIONS
    # ============================================================

    def _recommend(
        self,
        risk: float,
    ) -> list[str]:

        if risk >= 0.70:
            return [
                "halt_new_exposure",
                "reduce_portfolio_risk",
                "tighten_global_limits",
            ]

        if risk >= 0.50:
            return [
                "reduce_position_sizing",
                "decrease_gross_exposure",
            ]

        if risk >= 0.30:
            return [
                "monitor_equity_curve",
                "review_risk_budget",
            ]

        return [
            "normal_operation",
        ]

    # ============================================================
    # CLAMP
    # ============================================================

    def _clamp(
        self,
        value: float,
    ) -> float:

        return max(
            -1.0,
            min(1.0, float(value)),
        )
