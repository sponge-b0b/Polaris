from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from integration.contracts.risk.risk_signal_contract import RiskSignalContract
from intelligence.analysts.technical.technical_breadth_context import (
    TechnicalBreadthContext,
    extract_technical_breadth_context,
)
from intelligence.risk.breadth_annotations import deduplicate_strings


@dataclass(
    frozen=True,
    slots=True,
)
class VolatilityRiskInputs:
    atr: float
    atr_percent: float
    historical_volatility: float
    volatility_score: float
    volatility_regime: str
    stability_state: str
    gross_exposure: float
    leverage: float
    portfolio_concentration: float
    largest_position_pct: float
    cash_pct: float
    breadth_context: TechnicalBreadthContext

    @classmethod
    def from_runtime_outputs(
        cls,
        node_outputs: Mapping[str, Any],
    ) -> VolatilityRiskInputs:
        portfolio_output = node_outputs.get("portfolio_state_builder")
        if portfolio_output is None:
            raise ValueError(
                "VolatilityRiskAgent requires "
                "'portfolio_state_builder' in node_outputs."
            )

        technical_output = node_outputs.get("technical_agent")
        if technical_output is None:
            raise ValueError(
                "VolatilityRiskAgent requires 'technical_agent' in node_outputs."
            )

        portfolio_features = _features(portfolio_output)
        technical_features = _features(technical_output)
        portfolio = _mapping(portfolio_features.get("portfolio_state"))
        snapshot = _mapping(technical_features.get("snapshot"))
        volatility = _mapping(technical_features.get("volatility"))

        return cls(
            atr=float(snapshot.get("atr_14", volatility.get("atr_14", 0.0))),
            atr_percent=float(volatility.get("atr_percent", 0.0)),
            historical_volatility=float(volatility.get("historical_volatility", 0.0)),
            volatility_score=float(volatility.get("volatility_score", 0.0)),
            volatility_regime=str(volatility.get("volatility_regime", "unknown")),
            stability_state=str(volatility.get("stability_state", "unknown")),
            gross_exposure=float(portfolio.get("gross_exposure", 0.0)),
            leverage=float(portfolio.get("leverage", 0.0)),
            portfolio_concentration=float(portfolio.get("concentration_score", 0.0)),
            largest_position_pct=float(portfolio.get("largest_position_pct", 0.0)),
            cash_pct=float(portfolio.get("cash_pct", 0.0)),
            breadth_context=extract_technical_breadth_context(technical_output),
        )


@dataclass(
    frozen=True,
    slots=True,
)
class VolatilityRiskDecision:
    volatility_risk: float
    stability_score: float
    risk_regime: str
    risk_bias: str
    recommendations: tuple[str, ...]
    features: dict[str, Any]

    def to_contract(self) -> RiskSignalContract:
        return RiskSignalContract(
            volatility_risk=self.volatility_risk,
            drawdown_risk=0.0,
            exposure_risk=0.0,
            composite_risk=self.volatility_risk,
            risk_pressure=self.volatility_risk,
            stability_score=self.stability_score,
            risk_regime=self.risk_regime,
            risk_bias=self.risk_bias,
            recommendations=list(self.recommendations),
            features=self.features,
        )


def evaluate_volatility_risk(
    inputs: VolatilityRiskInputs,
) -> VolatilityRiskDecision:
    market_volatility_risk = compute_market_volatility_risk(
        volatility_score=inputs.volatility_score,
        historical_volatility=inputs.historical_volatility,
        atr_percent=inputs.atr_percent,
    )
    exposure_amplification = compute_exposure_amplification(
        gross_exposure=inputs.gross_exposure,
        leverage=inputs.leverage,
    )
    concentration_amplification = compute_concentration_amplification(
        concentration=inputs.portfolio_concentration,
        largest_position_pct=inputs.largest_position_pct,
    )
    liquidity_buffer_modifier = compute_cash_buffer_modifier(inputs.cash_pct)
    base_composite_risk = (
        (market_volatility_risk * 0.60)
        + (exposure_amplification * 0.20)
        + (concentration_amplification * 0.15)
        + (liquidity_buffer_modifier * 0.05)
    )
    breadth_risk_modifier = compute_breadth_risk_modifier(inputs.breadth_context)
    volatility_risk = clamp_01(base_composite_risk + breadth_risk_modifier)
    stability_score = clamp_01(1.0 - volatility_risk)
    recommendations = deduplicate_strings(
        recommend(volatility_risk) + breadth_recommendations(inputs.breadth_context)
    )

    return VolatilityRiskDecision(
        volatility_risk=volatility_risk,
        stability_score=stability_score,
        risk_regime=classify_regime(volatility_risk),
        risk_bias=classify_bias(volatility_risk),
        recommendations=tuple(recommendations),
        features={
            "atr": inputs.atr,
            "atr_percent": inputs.atr_percent,
            "historical_volatility": inputs.historical_volatility,
            "volatility_score": inputs.volatility_score,
            "volatility_regime": inputs.volatility_regime,
            "stability_state": inputs.stability_state,
            "gross_exposure": inputs.gross_exposure,
            "leverage": inputs.leverage,
            "cash_pct": inputs.cash_pct,
            "portfolio_concentration": inputs.portfolio_concentration,
            "largest_position_pct": inputs.largest_position_pct,
            "market_volatility_risk": market_volatility_risk,
            "exposure_amplification": exposure_amplification,
            "concentration_amplification": concentration_amplification,
            "liquidity_buffer_modifier": liquidity_buffer_modifier,
            "base_composite_risk": base_composite_risk,
            "breadth_context": inputs.breadth_context.to_dict(),
            "breadth_confirmation_score": inputs.breadth_context.confirmation_score,
            "breadth_risk_pressure": inputs.breadth_context.risk_pressure,
            "breadth_risk_modifier": breadth_risk_modifier,
            "breadth_risk_flags": list(inputs.breadth_context.risk_flags()),
        },
    )


def compute_market_volatility_risk(
    *,
    volatility_score: float,
    historical_volatility: float,
    atr_percent: float,
) -> float:
    score = (
        (convert_volatility_score_to_risk(volatility_score) * 0.60)
        + (historical_volatility * 0.25)
        + (atr_percent * 0.15)
    )
    return clamp_01(score)


def convert_volatility_score_to_risk(volatility_score: float) -> float:
    return clamp_01((1.0 - volatility_score) / 2.0)


def compute_breadth_risk_modifier(
    breadth_context: TechnicalBreadthContext,
) -> float:
    if not breadth_context.has_breadth_data:
        return 0.0
    return max(-0.08, min(0.12, (breadth_context.risk_pressure - 0.50) * 0.20))


def breadth_recommendations(
    breadth_context: TechnicalBreadthContext,
) -> list[str]:
    if not breadth_context.has_breadth_data:
        return []

    recommendations: list[str] = []
    if breadth_context.price_ad_divergence:
        recommendations.append("validate_volatility_signal_with_breadth_confirmation")
    if breadth_context.risk_pressure >= 0.65:
        recommendations.append("deteriorating_breadth_increases_volatility_risk")
    if breadth_context.participation_score <= -0.25:
        recommendations.append("reduce_sizing_until_market_participation_improves")
    if breadth_context.is_strong:
        recommendations.append("breadth_confirms_lower_volatility_pressure")
    return recommendations


def compute_exposure_amplification(
    *,
    gross_exposure: float,
    leverage: float,
) -> float:
    return clamp_01(
        (min(gross_exposure / 2.0, 1.0) * 0.60) + (min(leverage / 3.0, 1.0) * 0.40)
    )


def compute_concentration_amplification(
    *,
    concentration: float,
    largest_position_pct: float,
) -> float:
    return clamp_01((concentration * 0.70) + (largest_position_pct * 0.30))


def compute_cash_buffer_modifier(cash_pct: float) -> float:
    if cash_pct >= 0.30:
        return 0.0
    return clamp_01((0.30 - cash_pct) / 0.30)


def classify_regime(risk: float) -> str:
    if risk >= 0.75:
        return "crisis"
    if risk >= 0.50:
        return "stressed"
    if risk >= 0.30:
        return "elevated"
    return "calm"


def classify_bias(risk: float) -> str:
    if risk >= 0.50:
        return "risk_off"
    if risk <= 0.20:
        return "risk_on"
    return "neutral"


def recommend(risk: float) -> list[str]:
    if risk >= 0.75:
        return [
            "reduce_risk_immediately",
            "raise_cash_levels",
            "tighten_all_stops",
        ]
    if risk >= 0.50:
        return [
            "reduce_position_size",
            "tighten_risk_limits",
            "avoid_aggressive_entries",
        ]
    if risk >= 0.30:
        return [
            "moderate_position_sizing",
            "monitor_volatility_expansion",
        ]
    return ["normal_risk_allocation"]


def clamp_01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _features(output: Mapping[str, Any]) -> Mapping[str, Any]:
    return _mapping(_mapping(output.get("outputs")).get("features"))


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}
