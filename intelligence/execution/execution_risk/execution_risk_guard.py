from __future__ import annotations

from typing import Any, List

from core.runtime.contracts.runtime_node import RuntimeNode
from core.runtime.state.runtime_context import RuntimeContext
from core.runtime.state.runtime_node_output import RuntimeNodeOutput

from integration.contracts.risk.risk_signal_contract import (
    RiskSignalContract,
)

from integration.adapters.risk import (
    risk_runtime_adapter,
)


class ExecutionRiskGuard(RuntimeNode):
    """
    Polaris Execution Risk Guard

    PURPOSE:
    --------
    Final deterministic execution safety layer.

    RESPONSIBILITIES:
    -----------------
    - enforce execution safety constraints
    - apply deterministic execution throttling
    - convert risk posture into execution posture
    - NEVER generate directional signals
    - NEVER mutate upstream intelligence

    IMPORTANT:
    ----------
    INPUT SOURCE OF TRUTH:
        risk_aggregator_agent

    OUTPUT CONTRACT:
        RiskSignalContract
            -> RiskRuntimeAdapter
            -> RuntimeNodeOutput
    """

    node_name = "risk_guard"
    node_type = "execution_risk_guard"

    # ============================================================
    # SAFETY THRESHOLDS
    # ============================================================

    MAX_COMPOSITE_RISK = 0.70
    MAX_RISK_PRESSURE = 0.75
    MIN_STABILITY = 0.30

    MAX_VOLATILITY_RISK = 0.80
    MAX_DRAWDOWN_RISK = 0.75
    MAX_EXPOSURE_RISK = 0.80

    # ============================================================
    # EXECUTE
    # ============================================================

    async def _execute(
        self,
        context: RuntimeContext,
    ) -> RuntimeNodeOutput:

        # ========================================================
        # RISK AGGREGATOR OUTPUT (SOURCE OF TRUTH)
        # ========================================================

        risk_output = context.node_outputs["risk_aggregator_agent"]

        risk_result: dict[str, Any] = risk_output.get("outputs", {})

        # ========================================================
        # TRADE PACKAGER OUTPUT
        # ========================================================

        trade_output = context.node_outputs.get("trade_packager")

        trade_result = trade_output.get("outputs", {}) if trade_output else None

        # ========================================================
        # EXTRACT RISK FEATURES
        # ========================================================

        features = risk_result.get("features", {}) or {}

        composite_risk = float(
            features.get(
                "composite_risk",
                0.0,
            )
        )

        risk_pressure = float(
            features.get(
                "risk_pressure",
                0.0,
            )
        )

        stability_score = float(
            features.get(
                "stability_score",
                1.0,
            )
        )

        volatility_risk = float(
            features.get(
                "volatility_risk",
                0.0,
            )
        )

        drawdown_risk = float(
            features.get(
                "drawdown_risk",
                0.0,
            )
        )

        exposure_risk = float(
            features.get(
                "exposure_risk",
                0.0,
            )
        )

        risk_regime = str(
            features.get(
                "risk_regime",
                risk_result.get("regime", "neutral"),
            )
        )

        risk_bias = str(
            features.get(
                "risk_bias",
                "neutral",
            )
        )

        recommendations = list(risk_result.get("recommendations", []) or [])

        # ========================================================
        # PORTFOLIO V2 SAFETY CONTEXT
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

        margin_utilization_ratio = float(
            portfolio_risk_features.get(
                "margin_utilization_ratio",
                0.0,
            )
        )

        account_restrictions = {
            "trading_blocked": bool(
                portfolio_risk_features.get(
                    "trading_blocked",
                    False,
                )
            ),
            "account_blocked": bool(
                portfolio_risk_features.get(
                    "account_blocked",
                    False,
                )
            ),
            "trade_suspended_by_user": bool(
                portfolio_risk_features.get(
                    "trade_suspended_by_user",
                    False,
                )
            ),
            "transfers_blocked": bool(
                portfolio_risk_features.get(
                    "transfers_blocked",
                    False,
                )
            ),
            "pattern_day_trader": bool(
                portfolio_risk_features.get(
                    "pattern_day_trader",
                    False,
                )
            ),
        }

        hard_account_restriction = any(
            account_restrictions[flag]
            for flag in (
                "trading_blocked",
                "account_blocked",
                "trade_suspended_by_user",
            )
        )

        # ========================================================
        # TRADE FEATURES
        # ========================================================

        position_size = 0.0

        if trade_result:
            position_size = float(
                trade_result.get("features", {}).get(
                    "position_sizing_hint",
                    0.0,
                )
            )

        # ========================================================
        # FLAG ENGINE
        # ========================================================

        flags: List[str] = []

        if abs(composite_risk) > self.MAX_COMPOSITE_RISK:
            flags.append("composite_risk_breach")

        if risk_pressure > self.MAX_RISK_PRESSURE:
            flags.append("risk_pressure_breach")

        if volatility_risk > self.MAX_VOLATILITY_RISK:
            flags.append("volatility_risk_high")

        if drawdown_risk > self.MAX_DRAWDOWN_RISK:
            flags.append("drawdown_risk_high")

        if exposure_risk > self.MAX_EXPOSURE_RISK:
            flags.append("exposure_risk_high")

        if stability_score < self.MIN_STABILITY:
            flags.append("system_instability")

        if margin_utilization_ratio > 0.75:
            flags.append("margin_utilization_high")

        for restriction_name, is_active in account_restrictions.items():
            if is_active:
                flags.append(restriction_name)

        # ========================================================
        # EXECUTION MODE
        # ========================================================

        if hard_account_restriction:
            mode = "blocked"

        elif len(flags) >= 3:
            mode = "blocked"

        elif len(flags) == 2:
            mode = "reduced"

        elif len(flags) == 1:
            mode = "scaled"

        else:
            mode = "normal"

        # ========================================================
        # POSITION SIZE ADJUSTMENT
        # ========================================================

        adjusted_position_size = position_size

        if mode == "blocked":
            adjusted_position_size = 0.0

        elif mode == "reduced":
            adjusted_position_size *= 0.50

        elif mode == "scaled":
            adjusted_position_size *= 0.75

        adjusted_position_size = max(
            0.0,
            min(
                1.0,
                adjusted_position_size,
            ),
        )

        # ========================================================
        # RECOMMENDATION ENRICHMENT
        # ========================================================

        if hard_account_restriction:
            recommendations.append("respect_account_restrictions")

        if mode == "blocked":
            recommendations.append("block_new_execution")

        elif mode == "reduced":
            recommendations.append("reduce_position_size")

        elif mode == "scaled":
            recommendations.append("scale_position_size")

        else:
            recommendations.append("execution_conditions_normal")

        # ========================================================
        # BUILD UPDATED CONTRACT
        # ========================================================

        updated_contract = RiskSignalContract(
            volatility_risk=(volatility_risk),
            drawdown_risk=(drawdown_risk),
            exposure_risk=(exposure_risk),
            composite_risk=(composite_risk),
            risk_pressure=(risk_pressure),
            stability_score=(stability_score),
            risk_regime=risk_regime,
            risk_bias=risk_bias,
            recommendations=(recommendations),
            features={
                **features,
                "execution_guard": {
                    "flags": flags,
                    "mode": mode,
                    "position_size_original": (position_size),
                    "adjusted_position_size": (adjusted_position_size),
                    "account_restrictions": account_restrictions,
                    "hard_account_restriction": (hard_account_restriction),
                    "margin_utilization_ratio": (margin_utilization_ratio),
                },
            },
        )

        # ========================================================
        # CANONICAL OUTPUT PATH
        # ========================================================

        return risk_runtime_adapter.to_runtime_output(
            node_name=self.node_name,
            node_type=self.node_type,
            contract=updated_contract,
        )
