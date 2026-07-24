from application.services.macro.economic_regime import classify_economic_regime
from application.services.macro.fed_analysis import analyze_fed_environment
from application.services.macro.inflation_analysis import analyze_inflation_environment
from application.services.macro.liquidity_analysis import analyze_liquidity_environment
from domain.macro.models import MacroDataSnapshot


def test_macro_analysis_classifies_constructive_inputs() -> None:
    snapshot = MacroDataSnapshot(
        cpi=2.8,
        core_cpi=2.5,
        pce=2.2,
        fed_funds_rate=1.5,
        treasury_2y=4.0,
        treasury_10y=4.5,
        unemployment_rate=4.4,
        m2_money_supply=21_500_000.0,
        vix=14.0,
    )

    inflation = analyze_inflation_environment(snapshot)
    fed = analyze_fed_environment(snapshot)
    liquidity = analyze_liquidity_environment(snapshot)
    regime = classify_economic_regime(
        inflation,
        fed,
        liquidity,
        {"curve_regime": "steep_curve"},
    )

    assert inflation == {
        "inflation_regime": "moderate_inflation",
        "inflation_pressure": "balanced",
        "trend": "sticky_inflation",
        "summary": (
            "Inflation regime is moderate_inflation with balanced and "
            "sticky_inflation trend behavior."
        ),
    }
    assert fed == {
        "fed_stance": "neutral",
        "policy_pressure": "balanced",
        "rate_environment": "low_rate",
        "summary": (
            "Fed stance is neutral with low_rate environment and balanced "
            "policy pressure."
        ),
    }
    assert liquidity == {
        "liquidity_regime": "high_liquidity",
        "liquidity_pressure": "risk_on",
        "risk_environment": "bullish_liquidity_tailwind",
        "summary": (
            "Liquidity regime is high_liquidity with risk_on conditions and "
            "bullish_liquidity_tailwind market behavior."
        ),
    }
    assert regime == {
        "economic_regime": "constructive_growth",
        "market_bias": "bullish_bias",
        "macro_score": 3,
        "components": {
            "inflation": "moderate_inflation",
            "fed": "neutral",
            "liquidity": "high_liquidity",
            "curve": "steep_curve",
        },
        "summary": (
            "Macro regime is constructive_growth with bullish_bias and score 3."
        ),
    }


def test_macro_analysis_preserves_insufficient_data_defaults() -> None:
    snapshot = MacroDataSnapshot(
        cpi=None,
        core_cpi=None,
        pce=1.8,
        fed_funds_rate=None,
        treasury_2y=None,
        treasury_10y=None,
        unemployment_rate=None,
        m2_money_supply=None,
        vix=18.0,
    )

    assert analyze_inflation_environment(snapshot) == {
        "inflation_regime": "unknown",
        "inflation_pressure": "neutral",
        "trend": "flat",
        "summary": "Insufficient inflation data",
    }
    assert analyze_fed_environment(snapshot) == {
        "fed_stance": "neutral",
        "policy_pressure": "balanced",
        "rate_environment": "uncertain",
        "summary": "Insufficient data for Fed analysis",
    }
    assert analyze_liquidity_environment(snapshot) == {
        "liquidity_regime": "unknown",
        "liquidity_pressure": "neutral",
        "risk_environment": "neutral",
        "summary": "Insufficient liquidity data",
    }
