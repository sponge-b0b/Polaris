from __future__ import annotations

from collections import OrderedDict

from intelligence.strategy.hypothesis import (
    StrategyEvidenceInputStatus,
    StrategyPerspective,
    normalize_strategy_evidence_context,
)

STRONG_BREADTH: dict[str, object] = {
    "has_breadth_data": True,
    "breadth_regime": "strong_breadth",
    "risk_regime": "stable",
    "breadth_score": 0.64,
    "breadth_risk_score": 0.24,
    "participation_score": 0.36,
    "leadership_score": 0.22,
    "mcclellan_score": 0.18,
    "price_ad_divergence": False,
}


def test_normalization_builds_expected_typed_evidence_context() -> None:
    context = normalize_strategy_evidence_context(
        _node_outputs(sentiment_score=0.123456789, technical_score=0.456789123),
        symbol="SPY",
        as_of="2026-07-10T13:30:00Z",
    )

    evidence = context.evidence_by_id()

    assert context.symbol == "SPY"
    assert context.as_of == "2026-07-10T13:30:00Z"
    assert context.has_missing_required_inputs is False
    assert context.has_degraded_required_inputs is False
    assert evidence["sentiment.directional_score"].observed_value == 0.123456789
    assert evidence["technical.directional_score"].observed_value == 0.456789123
    assert evidence["technical.breadth.confirmation_score"].observed_value == 0.417
    assert evidence["fundamental.directional_score"].source == "fundamental_agent"
    assert evidence["macro.directional_score"].source == "macro_analysis"
    assert evidence["portfolio.scale_factor"].observed_value == 0.88
    assert evidence["market_events.bias"].observed_value == -0.15
    assert evidence["technical.directional_score"].supports == (
        StrategyPerspective.BULL,
    )
    assert evidence["market_events.bias"].supports == (StrategyPerspective.BEAR,)
    assert {
        quality.input_name: quality.status for quality in context.input_quality
    } == {
        "sentiment_agent": StrategyEvidenceInputStatus.AVAILABLE,
        "technical_agent": StrategyEvidenceInputStatus.AVAILABLE,
        "macro_analysis": StrategyEvidenceInputStatus.AVAILABLE,
        "fundamental_agent": StrategyEvidenceInputStatus.AVAILABLE,
        "news_agent": StrategyEvidenceInputStatus.AVAILABLE,
        "risk_aggregator_agent": StrategyEvidenceInputStatus.AVAILABLE,
        "portfolio_state_builder": StrategyEvidenceInputStatus.AVAILABLE,
        "market_events": StrategyEvidenceInputStatus.AVAILABLE,
    }


def test_normalization_preserves_bull_bear_and_sideways_fixture_directionality() -> (
    None
):
    bullish = normalize_strategy_evidence_context(
        _node_outputs(sentiment_score=0.70, technical_score=0.60)
    )
    bearish = normalize_strategy_evidence_context(
        _node_outputs(sentiment_score=-0.70, technical_score=-0.60)
    )
    sideways = normalize_strategy_evidence_context(
        _node_outputs(sentiment_score=0.0, technical_score=0.0)
    )

    bullish_score = bullish.evidence_by_id()["sentiment.directional_score"]
    bearish_score = bearish.evidence_by_id()["sentiment.directional_score"]
    sideways_score = sideways.evidence_by_id()["sentiment.directional_score"]

    assert bullish_score.supports == (StrategyPerspective.BULL,)
    assert bearish_score.supports == (StrategyPerspective.BEAR,)
    assert sideways_score.supports == (StrategyPerspective.SIDEWAYS,)
    assert [item.evidence_id for item in bullish.required_evidence] == [
        item.evidence_id for item in bearish.required_evidence
    ]
    assert [item.evidence_id for item in bullish.required_evidence] == [
        item.evidence_id for item in sideways.required_evidence
    ]


def test_normalization_flags_missing_required_and_optional_inputs_explicitly() -> None:
    context = normalize_strategy_evidence_context(
        {
            "sentiment_agent": {
                "outputs": {
                    "directional_score": 0.25,
                    "confidence": 0.8,
                }
            }
        }
    )

    quality = {item.input_name: item for item in context.input_quality}

    assert context.has_missing_required_inputs is True
    assert quality["sentiment_agent"].status is StrategyEvidenceInputStatus.AVAILABLE
    assert quality["technical_agent"].status is StrategyEvidenceInputStatus.MISSING
    assert quality["technical_agent"].required is True
    assert quality["news_agent"].status is StrategyEvidenceInputStatus.MISSING
    assert quality["news_agent"].required is False
    assert quality["technical_agent"].reason == (
        "technical_agent did not produce runtime output."
    )


def test_normalization_fingerprint_is_stable_across_node_output_ordering() -> None:
    first = _node_outputs(sentiment_score=0.42, technical_score=0.33)
    second = OrderedDict(reversed(list(first.items())))

    first_context = normalize_strategy_evidence_context(first)
    second_context = normalize_strategy_evidence_context(second)

    assert first_context.to_canonical_json() == second_context.to_canonical_json()
    assert first_context.evidence_fingerprint() == second_context.evidence_fingerprint()


def _node_outputs(
    *,
    sentiment_score: float,
    technical_score: float,
) -> dict[str, object]:
    return {
        "sentiment_agent": {
            "outputs": {
                "directional_score": sentiment_score,
                "confidence": 0.73,
                "features": {
                    "momentum": 0.31,
                    "stability": 0.62,
                    "divergence": {"avg_divergence": 0.08},
                },
            }
        },
        "technical_agent": {
            "outputs": {
                "directional_score": technical_score,
                "confidence": 0.81,
                "features": {
                    "regime": {"regime": "bullish"},
                    "trend": {"trend_strength": 0.55},
                    "volatility": {
                        "volatility_score": 0.22,
                        "volatility_regime": "normal",
                    },
                    "breadth_state": STRONG_BREADTH,
                },
            }
        },
        "macro_analysis": {
            "outputs": {
                "directional_score": 0.11,
                "confidence": 0.56,
                "regime": "stable_growth",
            }
        },
        "fundamental_agent": {
            "outputs": {"directional_score": 0.15, "confidence": 0.67}
        },
        "news_agent": {"outputs": {"directional_score": -0.05, "confidence": 0.58}},
        "risk_aggregator_agent": {
            "outputs": {
                "confidence": 0.72,
                "features": {"risk_pressure": 0.24, "composite_risk": 0.30},
            }
        },
        "portfolio_state_builder": {
            "outputs": {
                "confidence": 0.90,
                "features": {
                    "scale_factor": 0.88,
                    "status": "approved",
                    "risk_features": {"portfolio_heat": 0.33},
                },
            }
        },
        "market_events": {
            "outputs": {
                "confidence": 0.60,
                "features": {
                    "event_pressure": 0.20,
                    "event_bias": -0.15,
                    "event_volatility": 0.30,
                },
            }
        },
    }
