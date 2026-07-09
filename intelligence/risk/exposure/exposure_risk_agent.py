from typing import Any

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


class ExposureRiskAgent(RuntimeNode):
    """
    Polaris Exposure Risk Agent

    ============================================================
    PURPOSE
    ============================================================
    - evaluate portfolio exposure structure
    - detect leverage + concentration imbalance
    - normalize exposure pressure into canonical risk signal
    - consume PortfolioStateBuilder context only

    ============================================================
    INPUT SOURCE
    ============================================================
    REQUIRED:
        context.node_outputs["portfolio_state_builder"]

    PROVIDED STRUCTURE:
        RuntimeNodeOutput.outputs["features"] = {
            "portfolio": {...},
            "positions": [...],
            "equity": {...},
        }

    ============================================================
    OUTPUT
    ============================================================
    RuntimeNodeOutput(
        result=RiskSignalContract
    )
    """

    node_name = "exposure_risk_agent"
    node_type = "risk_agent"

    # ============================================================
    # EXECUTE
    # ============================================================

    async def _execute(
        self,
        context: RuntimeContext,
    ) -> RuntimeNodeOutput:

        # ========================================================
        # PORTFOLIO STATE INPUT
        # ========================================================

        portfolio_state_output = context.node_outputs["portfolio_state_builder"]

        if portfolio_state_output is None:
            raise ValueError("Missing portfolio_state_builder in context.")

        portfolio_features = portfolio_state_output.get("outputs", {}).get(
            "features", {}
        )

        portfolio = (
            portfolio_features.get(
                "portfolio_state",
                {},
            )
            or {}
        )

        positions_state = (
            portfolio_features.get(
                "positions_state",
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

        positions = (
            positions_state.get(
                "positions",
                [],
            )
            or []
        )

        # ========================================================
        # NORMALIZED PORTFOLIO METRICS
        # ========================================================

        gross_exposure = float(portfolio.get("gross_exposure", 0.0))

        net_exposure = float(portfolio.get("net_exposure", 0.0))

        leverage = float(portfolio.get("leverage", 1.0))

        cash_pct = float(portfolio.get("cash_pct", 0.0))

        long_exposure = float(portfolio.get("long_exposure", 0.0))

        short_exposure = float(portfolio.get("short_exposure", 0.0))

        position_count = int(
            positions_state.get(
                "position_count",
                len(positions),
            )
        )

        # ========================================================
        # CONCENTRATION RISK
        # ========================================================

        concentration_risk = float(
            portfolio.get(
                "concentration_score",
                positions_state.get(
                    "concentration_risk",
                    self._compute_concentration_risk(positions),
                ),
            )
        )

        # ========================================================
        # LEVERAGE RISK
        # ========================================================

        leverage_risk = self._compute_leverage_risk(leverage)

        # ========================================================
        # EXPOSURE IMBALANCE
        # ========================================================

        exposure_imbalance = self._compute_exposure_imbalance(
            gross_exposure=gross_exposure,
            net_exposure=net_exposure,
            cash_pct=cash_pct,
        )

        # ========================================================
        # DIRECTIONAL CROWDING RISK
        # ========================================================

        directional_crowding = self._compute_directional_crowding(
            long_exposure=long_exposure,
            short_exposure=short_exposure,
        )

        # ========================================================
        # V2 PORTFOLIO PRESSURE
        # ========================================================

        portfolio_heat = float(
            risk_features.get(
                "portfolio_heat",
                portfolio.get(
                    "portfolio_heat",
                    0.0,
                ),
            )
        )

        risk_intensity = float(
            risk_features.get(
                "risk_intensity",
                portfolio.get(
                    "risk_intensity",
                    0.0,
                ),
            )
        )

        margin_utilization_ratio = float(
            risk_features.get(
                "margin_utilization_ratio",
                0.0,
            )
        )

        # ========================================================
        # COMPOSITE EXPOSURE RISK
        # ========================================================

        component_exposure = (
            concentration_risk * 0.35
            + leverage_risk * 0.30
            + exposure_imbalance * 0.20
            + directional_crowding * 0.15
        )

        composite_exposure = self._clamp(
            max(
                component_exposure,
                portfolio_heat,
                risk_intensity,
                margin_utilization_ratio,
            )
        )

        exposure_risk = abs(composite_exposure)

        # ========================================================
        # STABILITY
        # ========================================================

        stability_score = self._compute_stability(exposure_risk)

        risk_pressure = exposure_risk

        # ========================================================
        # CONTRACT
        # ========================================================

        risk_contract = RiskSignalContract(
            volatility_risk=0.0,
            drawdown_risk=0.0,
            exposure_risk=exposure_risk,
            composite_risk=composite_exposure,
            risk_pressure=risk_pressure,
            stability_score=stability_score,
            risk_regime=self._classify_regime(exposure_risk),
            risk_bias=self._bias(composite_exposure),
            recommendations=self._recommend(exposure_risk),
            features={
                "gross_exposure": gross_exposure,
                "net_exposure": net_exposure,
                "long_exposure": long_exposure,
                "short_exposure": short_exposure,
                "cash_pct": cash_pct,
                "leverage": leverage,
                "position_count": position_count,
                "margin_utilization_ratio": margin_utilization_ratio,
                "portfolio_heat": portfolio_heat,
                "risk_intensity": risk_intensity,
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
                "concentration_risk": concentration_risk,
                "leverage_risk": leverage_risk,
                "exposure_imbalance": exposure_imbalance,
                "directional_crowding": directional_crowding,
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

    # ============================================================
    # CONCENTRATION RISK
    # ============================================================

    def _compute_concentration_risk(
        self,
        positions: list[dict[str, Any]],
    ) -> float:

        if not positions:
            return 0.0

        weights = [abs(float(p.get("exposure_weight", 0.0))) for p in positions]

        total_weight = sum(weights)

        if total_weight <= 0:
            return 0.0

        largest_position = max(weights)

        concentration = largest_position / total_weight

        return self._clamp(concentration)

    # ============================================================
    # LEVERAGE RISK
    # ============================================================

    def _compute_leverage_risk(
        self,
        leverage: float,
    ) -> float:

        if leverage <= 1.0:
            return 0.0

        risk = (leverage - 1.0) / 3.0

        return self._clamp(risk)

    # ============================================================
    # EXPOSURE IMBALANCE
    # ============================================================

    def _compute_exposure_imbalance(
        self,
        gross_exposure: float,
        net_exposure: float,
        cash_pct: float,
    ) -> float:

        if gross_exposure <= 0:
            return 0.0

        directional_imbalance = abs(net_exposure) / gross_exposure

        liquidity_penalty = max(
            0.0,
            0.40 - cash_pct,
        )

        imbalance_score = directional_imbalance * 0.70 + liquidity_penalty * 0.30

        return self._clamp(imbalance_score)

    # ============================================================
    # DIRECTIONAL CROWDING
    # ============================================================

    def _compute_directional_crowding(
        self,
        long_exposure: float,
        short_exposure: float,
    ) -> float:

        total = abs(long_exposure) + abs(short_exposure)

        if total <= 0:
            return 0.0

        dominance = (
            max(
                abs(long_exposure),
                abs(short_exposure),
            )
            / total
        )

        return self._clamp(dominance)

    # ============================================================
    # STABILITY
    # ============================================================

    def _compute_stability(
        self,
        exposure_risk: float,
    ) -> float:

        stability = 1.0 - exposure_risk

        return max(
            0.0,
            min(1.0, stability),
        )

    # ============================================================
    # REGIME
    # ============================================================

    def _classify_regime(
        self,
        risk: float,
    ) -> str:

        if risk >= 0.75:
            return "critical"

        if risk >= 0.50:
            return "stressed"

        if risk >= 0.30:
            return "elevated"

        return "controlled"

    # ============================================================
    # RISK BIAS
    # ============================================================

    def _bias(
        self,
        risk: float,
    ) -> str:

        if risk >= 0.50:
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

        if risk >= 0.75:
            return [
                "delever_immediately",
                "reduce_concentration",
                "raise_cash_levels",
            ]

        if risk >= 0.50:
            return [
                "reduce_position_sizing",
                "rebalance_exposure",
                "limit_new_positions",
            ]

        if risk >= 0.30:
            return [
                "monitor_exposure_levels",
                "review_concentration",
            ]

        return ["exposure_within_limits"]

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
