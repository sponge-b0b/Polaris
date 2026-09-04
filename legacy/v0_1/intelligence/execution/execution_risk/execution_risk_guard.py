from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from core.runtime.contracts.runtime_node import RuntimeNode
from core.runtime.state.runtime_context import RuntimeContext
from core.runtime.state.runtime_node_output import RuntimeNodeOutput
from domain.workflow_outputs import (
    EXECUTION_RISK_DECISION_OUTPUT_CONTRACT,
    WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
)
from integration.adapters.risk import (
    risk_runtime_adapter,
)
from integration.contracts.risk.risk_signal_contract import (
    RiskSignalContract,
)


@dataclass(frozen=True, slots=True)
class _RiskFeatureSnapshot:
    features: dict[str, Any]
    composite_risk: float
    risk_pressure: float
    stability_score: float
    volatility_risk: float
    drawdown_risk: float
    exposure_risk: float
    risk_regime: str
    risk_bias: str
    recommendations: list[str]


@dataclass(frozen=True, slots=True)
class _PortfolioRiskContext:
    margin_utilization_ratio: float
    account_restrictions: dict[str, bool]
    hard_account_restriction: bool


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

    MAX_COMPOSITE_RISK = 0.70
    MAX_RISK_PRESSURE = 0.75
    MIN_STABILITY = 0.30

    MAX_VOLATILITY_RISK = 0.80
    MAX_DRAWDOWN_RISK = 0.75
    MAX_EXPOSURE_RISK = 0.80

    async def _execute(
        self,
        context: RuntimeContext,
    ) -> RuntimeNodeOutput:
        risk_result = _required_node_outputs(
            context,
            "risk_aggregator_agent",
        )
        trade_result = _optional_node_outputs(
            context,
            "trade_packager",
        )
        risk = _risk_feature_snapshot(risk_result)
        portfolio = _portfolio_risk_context(context)
        position_size = _position_size(trade_result)

        flags = _execution_flags(
            risk=risk,
            portfolio=portfolio,
            thresholds=self,
        )
        mode = _execution_mode(
            flags=flags,
            hard_account_restriction=portfolio.hard_account_restriction,
        )
        adjusted_position_size = _adjusted_position_size(
            mode=mode,
            position_size=position_size,
        )
        recommendations = _enriched_recommendations(
            recommendations=risk.recommendations,
            mode=mode,
            hard_account_restriction=portfolio.hard_account_restriction,
        )

        updated_contract = RiskSignalContract(
            volatility_risk=risk.volatility_risk,
            drawdown_risk=risk.drawdown_risk,
            exposure_risk=risk.exposure_risk,
            composite_risk=risk.composite_risk,
            risk_pressure=risk.risk_pressure,
            stability_score=risk.stability_score,
            risk_regime=risk.risk_regime,
            risk_bias=risk.risk_bias,
            recommendations=recommendations,
            features={
                **risk.features,
                "execution_guard": {
                    "flags": flags,
                    "mode": mode,
                    "position_size_original": position_size,
                    "adjusted_position_size": adjusted_position_size,
                    "account_restrictions": portfolio.account_restrictions,
                    "hard_account_restriction": portfolio.hard_account_restriction,
                    "margin_utilization_ratio": portfolio.margin_utilization_ratio,
                },
            },
        )

        return risk_runtime_adapter.to_runtime_output(
            node_name=self.node_name,
            node_type=self.node_type,
            contract=updated_contract,
            output_contract=EXECUTION_RISK_DECISION_OUTPUT_CONTRACT,
            output_schema_version=WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
        )


def _required_node_outputs(
    context: RuntimeContext,
    node_name: str,
) -> Mapping[str, Any]:
    node_output = context.node_outputs[node_name]
    return node_output.get("outputs", {})


def _optional_node_outputs(
    context: RuntimeContext,
    node_name: str,
) -> Mapping[str, Any] | None:
    node_output = context.node_outputs.get(node_name)
    if not node_output:
        return None
    return node_output.get("outputs", {})


def _risk_feature_snapshot(risk_result: Mapping[str, Any]) -> _RiskFeatureSnapshot:
    features = dict(risk_result.get("features", {}) or {})
    return _RiskFeatureSnapshot(
        features=features,
        composite_risk=_float_feature(features, "composite_risk", 0.0),
        risk_pressure=_float_feature(features, "risk_pressure", 0.0),
        stability_score=_float_feature(features, "stability_score", 1.0),
        volatility_risk=_float_feature(features, "volatility_risk", 0.0),
        drawdown_risk=_float_feature(features, "drawdown_risk", 0.0),
        exposure_risk=_float_feature(features, "exposure_risk", 0.0),
        risk_regime=str(
            features.get(
                "risk_regime",
                risk_result.get("regime", "neutral"),
            )
        ),
        risk_bias=str(features.get("risk_bias", "neutral")),
        recommendations=list(risk_result.get("recommendations", []) or []),
    )


def _float_feature(
    features: Mapping[str, Any],
    key: str,
    default: float,
) -> float:
    return float(features.get(key, default))


def _portfolio_risk_context(context: RuntimeContext) -> _PortfolioRiskContext:
    portfolio_output = context.node_outputs.get("portfolio_state_builder", {})
    portfolio_features = (
        portfolio_output.get("outputs", {}).get("features", {})
        if portfolio_output
        else {}
    )
    portfolio_risk_features = portfolio_features.get("risk_features", {}) or {}
    account_restrictions = _account_restrictions(portfolio_risk_features)
    hard_account_restriction = any(
        account_restrictions[flag]
        for flag in (
            "trading_blocked",
            "account_blocked",
            "trade_suspended_by_user",
        )
    )
    return _PortfolioRiskContext(
        margin_utilization_ratio=float(
            portfolio_risk_features.get("margin_utilization_ratio", 0.0),
        ),
        account_restrictions=account_restrictions,
        hard_account_restriction=hard_account_restriction,
    )


def _account_restrictions(
    portfolio_risk_features: Mapping[str, Any],
) -> dict[str, bool]:
    return {
        "trading_blocked": bool(
            portfolio_risk_features.get("trading_blocked", False),
        ),
        "account_blocked": bool(
            portfolio_risk_features.get("account_blocked", False),
        ),
        "trade_suspended_by_user": bool(
            portfolio_risk_features.get("trade_suspended_by_user", False),
        ),
        "transfers_blocked": bool(
            portfolio_risk_features.get("transfers_blocked", False),
        ),
        "pattern_day_trader": bool(
            portfolio_risk_features.get("pattern_day_trader", False),
        ),
    }


def _position_size(trade_result: Mapping[str, Any] | None) -> float:
    if not trade_result:
        return 0.0
    return float(
        trade_result.get("features", {}).get(
            "position_sizing_hint",
            0.0,
        )
    )


def _execution_flags(
    *,
    risk: _RiskFeatureSnapshot,
    portfolio: _PortfolioRiskContext,
    thresholds: ExecutionRiskGuard,
) -> list[str]:
    flags = _risk_threshold_flags(
        risk=risk,
        thresholds=thresholds,
    )
    if portfolio.margin_utilization_ratio > 0.75:
        flags.append("margin_utilization_high")
    flags.extend(_active_account_restrictions(portfolio.account_restrictions))
    return flags


def _risk_threshold_flags(
    *,
    risk: _RiskFeatureSnapshot,
    thresholds: ExecutionRiskGuard,
) -> list[str]:
    checks = (
        (
            abs(risk.composite_risk) > thresholds.MAX_COMPOSITE_RISK,
            "composite_risk_breach",
        ),
        (risk.risk_pressure > thresholds.MAX_RISK_PRESSURE, "risk_pressure_breach"),
        (risk.volatility_risk > thresholds.MAX_VOLATILITY_RISK, "volatility_risk_high"),
        (risk.drawdown_risk > thresholds.MAX_DRAWDOWN_RISK, "drawdown_risk_high"),
        (risk.exposure_risk > thresholds.MAX_EXPOSURE_RISK, "exposure_risk_high"),
        (risk.stability_score < thresholds.MIN_STABILITY, "system_instability"),
    )
    return [flag for breached, flag in checks if breached]


def _active_account_restrictions(
    account_restrictions: Mapping[str, bool],
) -> list[str]:
    return [
        restriction_name
        for restriction_name, is_active in account_restrictions.items()
        if is_active
    ]


def _execution_mode(
    *,
    flags: list[str],
    hard_account_restriction: bool,
) -> str:
    if hard_account_restriction or len(flags) >= 3:
        return "blocked"
    if len(flags) == 2:
        return "reduced"
    if len(flags) == 1:
        return "scaled"
    return "normal"


def _adjusted_position_size(
    *,
    mode: str,
    position_size: float,
) -> float:
    scale_by_mode = {
        "blocked": 0.0,
        "reduced": 0.50,
        "scaled": 0.75,
        "normal": 1.0,
    }
    return max(
        0.0,
        min(
            1.0,
            position_size * scale_by_mode[mode],
        ),
    )


def _enriched_recommendations(
    *,
    recommendations: list[str],
    mode: str,
    hard_account_restriction: bool,
) -> list[str]:
    if hard_account_restriction:
        recommendations.append("respect_account_restrictions")
    recommendations.append(_mode_recommendation(mode))
    return recommendations


def _mode_recommendation(mode: str) -> str:
    return {
        "blocked": "block_new_execution",
        "reduced": "reduce_position_size",
        "scaled": "scale_position_size",
        "normal": "execution_conditions_normal",
    }[mode]
