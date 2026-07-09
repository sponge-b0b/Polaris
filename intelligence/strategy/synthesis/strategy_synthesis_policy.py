from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from application.services.market_events.market_events_result import MarketEventsResult
from core.utils.utils import _clamp
from intelligence.analysts.technical.technical_breadth_context import (
    TechnicalBreadthContext,
    extract_technical_breadth_context,
)

DEFAULT_EVENT_SYMBOLS = frozenset(
    {
        "AAPL",
        "AMZN",
        "GOOG",
        "GOOGL",
        "META",
        "MSFT",
        "NVDA",
        "TSLA",
        "AVGO",
        "JPM",
        "V",
        "MA",
        "BRK-B",
        "LLY",
        "XOM",
        "UNH",
        "COST",
        "WMT",
        "AMD",
        "NFLX",
        "CRM",
        "ORCL",
        "ADBE",
        "BAC",
        "GS",
        "MS",
        "JNJ",
        "ABBV",
        "MRK",
        "HD",
        "LOW",
        "TGT",
        "CAT",
        "GE",
        "LIN",
    }
)


class MissingStrategySynthesisInput(ValueError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(
    frozen=True,
    slots=True,
)
class StrategyMarketEvents:
    symbol: str
    market_pressure_score: float
    volatility_pressure: float
    volatility_forecast: str
    regime_bias: str
    service_result: MarketEventsResult | None = None
    event_error: str | None = None

    @classmethod
    def from_service_result(
        cls,
        result: MarketEventsResult,
    ) -> StrategyMarketEvents:
        return cls(
            symbol=result.symbol,
            market_pressure_score=result.market_pressure_score,
            volatility_pressure=result.volatility_pressure,
            volatility_forecast=result.volatility_forecast,
            regime_bias=result.regime_bias,
            service_result=result,
        )

    @classmethod
    def neutral(
        cls,
        *,
        symbol: str,
        error: str,
    ) -> StrategyMarketEvents:
        return cls(
            symbol=symbol,
            market_pressure_score=0.0,
            volatility_pressure=0.0,
            volatility_forecast="unknown",
            regime_bias="neutral",
            event_error=error,
        )

    def to_dict(self) -> dict[str, Any]:
        if self.service_result is not None:
            return self.service_result.to_dict()
        return {
            "symbol": self.symbol,
            "market_pressure_score": self.market_pressure_score,
            "volatility_pressure": self.volatility_pressure,
            "volatility_forecast": self.volatility_forecast,
            "regime_bias": self.regime_bias,
            "event_error": self.event_error,
        }


@dataclass(
    frozen=True,
    slots=True,
)
class StrategySynthesisInputs:
    symbol: str
    event_lookahead_days: int
    horizon: str
    bull_weight: float
    bear_weight: float
    sideways_weight: float
    adjusted_risk_pressure: float
    composite_risk: float
    portfolio_scale_factor: float
    portfolio_status: str
    technical_regime: str
    breadth_context: TechnicalBreadthContext
    symbol_constituents: frozenset[str]

    @classmethod
    def from_runtime_payloads(
        cls,
        *,
        workflow_inputs: Mapping[str, Any],
        node_outputs: Mapping[str, Any],
    ) -> StrategySynthesisInputs:
        weighting_output = _required_output(
            node_outputs,
            "adaptive_weighting_engine",
        )
        risk_output = _required_output(node_outputs, "risk_aggregator_agent")
        portfolio_output = _required_output(node_outputs, "portfolio_state_builder")
        technical_output = _required_output(node_outputs, "technical_agent")

        weighting_features = _features(weighting_output)
        risk_features = _features(risk_output)
        portfolio_features = _features(portfolio_output)
        technical_features = _features(technical_output)
        technical_regime = _mapping(technical_features.get("regime"))

        risk_pressure = float(risk_features.get("risk_pressure", 0.0))
        return cls(
            symbol=str(workflow_inputs.get("symbol", "SPY")),
            event_lookahead_days=int(workflow_inputs.get("event_lookahead_days", 10)),
            horizon=str(workflow_inputs.get("horizon", "3month")),
            bull_weight=float(weighting_features.get("bull_weight", 0.33)),
            bear_weight=float(weighting_features.get("bear_weight", 0.33)),
            sideways_weight=float(weighting_features.get("sideways_weight", 0.34)),
            adjusted_risk_pressure=float(
                risk_features.get("adjusted_risk_pressure", risk_pressure)
            ),
            composite_risk=float(risk_features.get("composite_risk", 0.0)),
            portfolio_scale_factor=float(portfolio_features.get("scale_factor", 1.0)),
            portfolio_status=str(portfolio_features.get("status", "unknown")),
            technical_regime=str(technical_regime.get("regime", "neutral")),
            breadth_context=extract_technical_breadth_context(technical_output),
            symbol_constituents=extract_symbol_constituents(
                technical_features.get("market_context")
            ),
        )


@dataclass(
    frozen=True,
    slots=True,
)
class StrategySynthesisDecision:
    directional_score: float
    confidence: float
    regime: str
    uncertainty: float
    signals: tuple[str, ...]
    risks: tuple[str, ...]
    recommendations: tuple[str, ...]
    features: dict[str, Any]

    def to_runtime_outputs(self) -> dict[str, Any]:
        return {
            "directional_score": self.directional_score,
            "confidence": self.confidence,
            "regime": self.regime,
            "signals": list(self.signals),
            "risks": list(self.risks),
            "recommendations": list(self.recommendations),
            "features": self.features,
        }


def synthesize_strategy(
    inputs: StrategySynthesisInputs,
    market_events: StrategyMarketEvents,
) -> StrategySynthesisDecision:
    bull_weight, bear_weight, sideways_weight = normalize_weights(
        inputs.bull_weight,
        inputs.bear_weight,
        inputs.sideways_weight,
    )
    event_pressure = _clamp(
        market_events.market_pressure_score,
        lower=0.0,
        upper=1.0,
    )
    event_bias = market_events.regime_bias
    event_volatility = _clamp(
        market_events.volatility_pressure,
        lower=0.0,
        upper=1.0,
    )
    bull_weight, bear_weight, sideways_weight = apply_event_weighting(
        bull_weight=bull_weight,
        bear_weight=bear_weight,
        sideways_weight=sideways_weight,
        event_pressure=event_pressure,
        event_bias=event_bias,
        event_volatility=event_volatility,
    )
    bull_weight, bear_weight, sideways_weight = normalize_weights(
        bull_weight,
        bear_weight,
        sideways_weight,
    )

    risk_multiplier = _clamp(
        1.0 - (inputs.adjusted_risk_pressure * 0.50),
        lower=0.0,
        upper=1.0,
    )
    bull_weight *= risk_multiplier
    bear_weight *= 1.0 - (inputs.adjusted_risk_pressure * 0.15)
    sideways_weight *= 1.0 + inputs.adjusted_risk_pressure
    bull_weight, bear_weight, sideways_weight = normalize_weights(
        bull_weight,
        bear_weight,
        sideways_weight,
    )

    net_bias = _clamp(bull_weight - bear_weight, lower=-1.0, upper=1.0)
    posture = classify_posture(
        net_bias=net_bias,
        sideways_weight=sideways_weight,
        event_pressure=event_pressure,
    )
    event_uncertainty_modifier = event_uncertainty(
        event_pressure=event_pressure,
        event_volatility=event_volatility,
    )
    breadth_uncertainty_modifier = breadth_uncertainty(inputs.breadth_context)
    uncertainty = _clamp(
        calculate_uncertainty(
            net_bias=net_bias,
            sideways_weight=sideways_weight,
            risk_pressure=inputs.adjusted_risk_pressure,
            event_pressure=event_pressure,
            event_volatility=event_volatility,
        )
        + breadth_uncertainty_modifier
        + event_uncertainty_modifier,
        lower=0.0,
        upper=1.0,
    )
    confidence = _clamp(
        (1.0 - uncertainty) * inputs.portfolio_scale_factor,
        lower=0.0,
        upper=1.0,
    )

    breadth_readiness_modifier = breadth_execution_readiness(inputs.breadth_context)
    event_readiness_modifier = event_execution_readiness(
        event_pressure=event_pressure,
        event_bias=event_bias,
    )
    execution_readiness = _clamp(
        abs(net_bias) * confidence * inputs.portfolio_scale_factor
        + breadth_readiness_modifier
        + event_readiness_modifier,
        lower=0.0,
        upper=1.0,
    )

    breadth_quality_modifier = breadth_signal_quality(inputs.breadth_context)
    event_quality_modifier = event_signal_quality(
        event_pressure=event_pressure,
        event_volatility=event_volatility,
    )
    signal_quality = _clamp(
        (abs(net_bias) * 0.45)
        + (confidence * 0.25)
        + ((1.0 - inputs.composite_risk) * 0.20)
        + ((1.0 - event_pressure) * 0.10)
        + breadth_quality_modifier
        + event_quality_modifier,
        lower=0.0,
        upper=1.0,
    )

    signals = deduplicate(
        [
            posture,
            f"bull_weight:{bull_weight:.3f}",
            f"bear_weight:{bear_weight:.3f}",
            f"sideways_weight:{sideways_weight:.3f}",
            f"net_bias:{net_bias:.3f}",
            f"risk_pressure:{inputs.adjusted_risk_pressure:.3f}",
            f"event_pressure:{event_pressure:.3f}",
            f"event_bias:{event_bias}",
            f"event_volatility:{event_volatility:.3f}",
            f"technical_regime:{inputs.technical_regime}",
            f"portfolio_status:{inputs.portfolio_status}",
            *event_context_signals(market_events),
            *event_signals(
                event_pressure=event_pressure,
                event_bias=event_bias,
                event_volatility=event_volatility,
            ),
            *breadth_signals(inputs.breadth_context),
        ]
    )
    risks = base_risks(
        adjusted_risk_pressure=inputs.adjusted_risk_pressure,
        sideways_weight=sideways_weight,
        confidence=confidence,
        net_bias=net_bias,
        portfolio_status=inputs.portfolio_status,
    )
    risks = deduplicate(
        [
            *risks,
            *event_context_risks(market_events),
            *event_risks(
                event_pressure=event_pressure,
                event_bias=event_bias,
                event_volatility=event_volatility,
            ),
            *breadth_risks(inputs.breadth_context),
        ]
    )
    recommendations = deduplicate(
        [
            *posture_recommendations(posture, confidence),
            *event_recommendations(
                event_pressure=event_pressure,
                event_bias=event_bias,
                event_volatility=event_volatility,
            ),
            *breadth_recommendations(inputs.breadth_context),
        ]
    )

    return StrategySynthesisDecision(
        directional_score=net_bias,
        confidence=confidence,
        regime=posture,
        uncertainty=uncertainty,
        signals=tuple(signals),
        risks=tuple(risks),
        recommendations=tuple(recommendations),
        features={
            "symbol": inputs.symbol,
            "bull_weight": bull_weight,
            "bear_weight": bear_weight,
            "sideways_weight": sideways_weight,
            "allocation_vector": {
                "bull": bull_weight * inputs.portfolio_scale_factor,
                "bear": bear_weight * inputs.portfolio_scale_factor,
                "sideways": sideways_weight * inputs.portfolio_scale_factor,
            },
            "net_bias": net_bias,
            "uncertainty": uncertainty,
            "execution_readiness": execution_readiness,
            "signal_quality": signal_quality,
            "posture": posture,
            "composite_risk": inputs.composite_risk,
            "risk_pressure": inputs.adjusted_risk_pressure,
            "portfolio_scale_factor": inputs.portfolio_scale_factor,
            "portfolio_status": inputs.portfolio_status,
            "technical_regime": inputs.technical_regime,
            "market_events": market_events.to_dict(),
            "market_event_constituents": sorted(inputs.symbol_constituents),
            "event_lookahead_days": inputs.event_lookahead_days,
            "event_pressure": event_pressure,
            "event_bias": event_bias,
            "event_volatility": event_volatility,
            "event_uncertainty_modifier": event_uncertainty_modifier,
            "event_execution_readiness_modifier": event_readiness_modifier,
            "event_signal_quality_modifier": event_quality_modifier,
            "breadth_context": inputs.breadth_context.to_dict(),
            "breadth_confirmation_score": inputs.breadth_context.confirmation_score,
            "breadth_risk_pressure": inputs.breadth_context.risk_pressure,
            "breadth_uncertainty_modifier": breadth_uncertainty_modifier,
            "breadth_execution_readiness_modifier": breadth_readiness_modifier,
            "breadth_signal_quality_modifier": breadth_quality_modifier,
            "breadth_risk_flags": list(inputs.breadth_context.risk_flags()),
        },
    )


def extract_symbol_constituents(market_context: Any) -> frozenset[str]:
    source = _mapping(market_context)
    raw_symbols = source.get("top_50_constituents")
    if not isinstance(raw_symbols, (list, tuple, set, frozenset)):
        return DEFAULT_EVENT_SYMBOLS
    symbols = frozenset(
        symbol.strip().upper()
        for symbol in raw_symbols
        if isinstance(symbol, str) and symbol.strip()
    )
    return symbols or DEFAULT_EVENT_SYMBOLS


def normalize_weights(
    bull: float,
    bear: float,
    sideways: float,
) -> tuple[float, float, float]:
    bull = max(0.0, bull)
    bear = max(0.0, bear)
    sideways = max(0.0, sideways)
    total = bull + bear + sideways
    if total <= 0:
        return 0.33, 0.33, 0.34
    return bull / total, bear / total, sideways / total


def apply_event_weighting(
    *,
    bull_weight: float,
    bear_weight: float,
    sideways_weight: float,
    event_pressure: float,
    event_bias: str,
    event_volatility: float,
) -> tuple[float, float, float]:
    if event_pressure >= 0.70:
        bull_weight *= 0.85
        bear_weight *= 0.85
        # Preserve the established two-stage high-pressure uncertainty penalty.
        sideways_weight *= 1.20
        sideways_weight *= 1.20
    elif event_pressure <= 0.30:
        bull_weight *= 1.05
        bear_weight *= 1.05
        sideways_weight *= 0.95

    if event_volatility >= 0.70:
        bull_weight *= 0.90
        bear_weight *= 0.95
        sideways_weight *= 1.15
    if event_bias == "risk_off":
        bull_weight *= 0.80
        bear_weight *= 1.15
        sideways_weight *= 1.05
    elif event_bias == "risk_on":
        bull_weight *= 1.10
        bear_weight *= 0.90
    return bull_weight, bear_weight, sideways_weight


def classify_posture(
    *,
    net_bias: float,
    sideways_weight: float,
    event_pressure: float,
) -> str:
    if event_pressure >= 0.85 or sideways_weight >= 0.55:
        return "neutral"
    if net_bias >= 0.45:
        return "strong_risk_on"
    if net_bias >= 0.20:
        return "risk_on"
    if net_bias <= -0.45:
        return "strong_risk_off"
    if net_bias <= -0.20:
        return "risk_off"
    return "neutral"


def calculate_uncertainty(
    *,
    net_bias: float,
    sideways_weight: float,
    risk_pressure: float,
    event_pressure: float,
    event_volatility: float,
) -> float:
    return _clamp(
        (sideways_weight * 0.40)
        + ((1.0 - abs(net_bias)) * 0.30)
        + (risk_pressure * 0.20)
        + (event_pressure * 0.07)
        + (event_volatility * 0.03),
        lower=0.0,
        upper=1.0,
    )


def event_uncertainty(*, event_pressure: float, event_volatility: float) -> float:
    return _clamp(
        (event_pressure * 0.08) + (event_volatility * 0.05),
        lower=0.0,
        upper=0.15,
    )


def event_execution_readiness(*, event_pressure: float, event_bias: str) -> float:
    modifier = 0.0
    if event_pressure >= 0.70:
        modifier -= 0.08
    if event_bias == "risk_off":
        modifier -= 0.04
    elif event_bias == "risk_on" and event_pressure <= 0.50:
        modifier += 0.03
    return _clamp(modifier, lower=-0.12, upper=0.04)


def event_signal_quality(
    *,
    event_pressure: float,
    event_volatility: float,
) -> float:
    modifier = 0.0
    if event_pressure >= 0.70:
        modifier -= 0.05
    if event_volatility >= 0.70:
        modifier -= 0.04
    if event_pressure <= 0.25 and event_volatility <= 0.35:
        modifier += 0.03
    return _clamp(modifier, lower=-0.10, upper=0.03)


def breadth_uncertainty(context: TechnicalBreadthContext) -> float:
    if not context.has_breadth_data:
        return 0.0
    modifier = 0.0
    if context.is_weak:
        modifier += 0.08
    if context.price_ad_divergence:
        modifier += 0.05
    if context.participation_score <= -0.25:
        modifier += 0.03
    if context.leadership_score <= -0.25:
        modifier += 0.02
    if context.is_strong:
        modifier -= min(0.06, context.confirmation_score * 0.08)
    return _clamp(modifier, lower=-0.06, upper=0.16)


def breadth_execution_readiness(context: TechnicalBreadthContext) -> float:
    if not context.has_breadth_data:
        return 0.0
    modifier = 0.0
    if context.is_weak:
        modifier -= 0.08
    if context.price_ad_divergence:
        modifier -= 0.05
    if context.risk_pressure >= 0.65:
        modifier -= 0.03
    if context.is_strong:
        modifier += min(0.06, context.confirmation_score * 0.08)
    return _clamp(modifier, lower=-0.16, upper=0.06)


def breadth_signal_quality(context: TechnicalBreadthContext) -> float:
    if not context.has_breadth_data:
        return 0.0
    modifier = 0.0
    if context.is_weak:
        modifier -= 0.05
    if context.price_ad_divergence:
        modifier -= 0.03
    if context.is_strong:
        modifier += min(0.05, context.confirmation_score * 0.07)
    return _clamp(modifier, lower=-0.08, upper=0.05)


def event_context_signals(events: StrategyMarketEvents) -> list[str]:
    return ["market_event_context_unavailable"] if events.event_error else []


def event_context_risks(events: StrategyMarketEvents) -> list[str]:
    return ["market_event_context_unavailable"] if events.event_error else []


def event_signals(
    *,
    event_pressure: float,
    event_bias: str,
    event_volatility: float,
) -> list[str]:
    signals: list[str] = []
    if event_pressure >= 0.70:
        signals.append("high_event_pressure_conditions")
    if event_pressure <= 0.30:
        signals.append("low_event_pressure_conditions")
    if event_bias in {"risk_on", "risk_off"}:
        signals.append(f"event_bias:{event_bias}")
    if event_volatility >= 0.70:
        signals.append("event_volatility_pressure_elevated")
    return signals


def event_risks(
    *,
    event_pressure: float,
    event_bias: str,
    event_volatility: float,
) -> list[str]:
    risks: list[str] = []
    if event_pressure >= 0.70:
        risks.append("high_event_pressure")
    if event_bias == "risk_off":
        risks.append("event_regime_risk_off")
    if event_volatility >= 0.70:
        risks.append("event_volatility_risk")
    return risks


def event_recommendations(
    *,
    event_pressure: float,
    event_bias: str,
    event_volatility: float,
) -> list[str]:
    recommendations: list[str] = []
    if event_pressure >= 0.70:
        recommendations.extend(
            [
                "reduce_conviction_until_event_risk_clears",
                "avoid_oversized_positions_into_event_window",
            ]
        )
    if event_bias == "risk_off":
        recommendations.append("respect_event_driven_risk_off_bias")
    if event_volatility >= 0.70:
        recommendations.append("expect_volatility_around_event_window")
    return recommendations


def breadth_signals(context: TechnicalBreadthContext) -> list[str]:
    if not context.has_breadth_data:
        return []
    signals = [f"breadth:{context.breadth_regime}"]
    if context.is_strong:
        signals.append("breadth_confirms_strategy_synthesis")
    if context.is_weak:
        signals.append("weak_breadth_lowers_execution_readiness")
    if context.price_ad_divergence:
        signals.append("breadth_divergence_increases_synthesis_uncertainty")
    return signals


def breadth_risks(context: TechnicalBreadthContext) -> list[str]:
    if not context.has_breadth_data:
        return []
    risks = list(context.risk_flags())
    if context.is_weak:
        risks.append("breadth_confirmation_risk")
    if context.price_ad_divergence:
        risks.append("breadth_divergence_risk")
    return risks


def breadth_recommendations(context: TechnicalBreadthContext) -> list[str]:
    if not context.has_breadth_data:
        return []
    if context.is_strong:
        return ["breadth_supports_strategy_conviction"]
    if context.is_weak or context.price_ad_divergence:
        return [
            "require_breadth_confirmation_before_aggressive_allocation",
            "reduce_execution_urgency_until_breadth_improves",
        ]
    return []


def base_risks(
    *,
    adjusted_risk_pressure: float,
    sideways_weight: float,
    confidence: float,
    net_bias: float,
    portfolio_status: str,
) -> list[str]:
    risks: list[str] = []
    if adjusted_risk_pressure >= 0.70:
        risks.append("high_risk_environment")
    if sideways_weight >= 0.50:
        risks.append("high_regime_uncertainty")
    if confidence <= 0.35:
        risks.append("low_synthesis_confidence")
    if abs(net_bias) <= 0.15:
        risks.append("weak_directional_edge")
    if portfolio_status == "rejected":
        risks.append("portfolio_execution_restricted")
    return risks


def posture_recommendations(posture: str, confidence: float) -> list[str]:
    if posture.startswith("strong_risk_on"):
        recommendations = [
            "allow_aggressive_trend_exposure",
            "favor_breakout_continuation",
        ]
    elif posture == "risk_on":
        recommendations = ["favor_long_exposure", "allow_trend_following"]
    elif posture.startswith("strong_risk_off"):
        recommendations = ["preserve_capital", "reduce_beta_exposure"]
    elif posture == "risk_off":
        recommendations = ["reduce_net_exposure", "favor_defensive_positioning"]
    else:
        recommendations = [
            "reduce_aggressive_positioning",
            "favor_market_neutrality",
        ]
    if confidence <= 0.40:
        recommendations.append("decrease_position_size")
    return recommendations


def deduplicate(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _required_output(
    node_outputs: Mapping[str, Any],
    node_name: str,
) -> Mapping[str, Any]:
    output = node_outputs.get(node_name)
    if not isinstance(output, Mapping) or output.get("outputs", {}) is None:
        raise MissingStrategySynthesisInput(f"missing_{node_name}")
    return output


def _features(output: Mapping[str, Any]) -> Mapping[str, Any]:
    return _mapping(_mapping(output.get("outputs")).get("features"))


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}
