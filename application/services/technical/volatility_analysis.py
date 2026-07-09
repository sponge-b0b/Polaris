from __future__ import annotations

from typing import Any, Dict
from core.utils.utils import _clamp, _safe_float


STABLE_RISK_THRESHOLD = 0.25
NORMAL_RISK_THRESHOLD = 0.50
ELEVATED_RISK_THRESHOLD = 0.75


def stability_to_risk(stability_score: float) -> float:
    return _clamp((1.0 - stability_score) / 2.0, 0.0, 1.0)


def analyze(technical_result: Dict[str, Any]) -> Dict[str, Any]:
    snapshot = dict(technical_result.get("snapshot", {}))
    market_context = dict(technical_result.get("market_context", {}))

    asset_score, asset_components = _compute_asset_volatility_score(snapshot)
    market_score, market_components = _compute_market_volatility_score(market_context)
    vol_of_vol_score, vol_of_vol_components = _compute_vol_of_vol_score(market_context)
    breadth_score, breadth_components = _compute_breadth_confirmation_score(
        market_context
    )

    volatility_score = _clamp(
        asset_score * 0.45
        + market_score * 0.25
        + vol_of_vol_score * 0.20
        + breadth_score * 0.10,
        -1.0,
        1.0,
    )

    volatility_risk_score = stability_to_risk(volatility_score)
    volatility_regime = _determine_volatility_regime(volatility_risk_score)
    stability_state = _determine_stability_state(volatility_risk_score)

    return {
        "close": _safe_float(snapshot.get("close")),
        "atr_14": _safe_float(snapshot.get("atr_14")),
        "atr_50": _safe_float(snapshot.get("atr_50")),
        "atr_percent_of_price": _safe_float(snapshot.get("atr_14_percent_of_price")),
        "atr_percentile": _safe_float(snapshot.get("atr_14_percentile_252")),
        "hv_20": _safe_float(snapshot.get("hv_20")),
        "hv_50": _safe_float(snapshot.get("hv_50")),
        "hv_100": _safe_float(snapshot.get("hv_100")),
        "vix": _safe_float(market_context.get("vix")),
        "vvix": _safe_float(market_context.get("vvix")),
        "ad_line": _safe_float(market_context.get("ad_line")),
        "asset_volatility_score": asset_score,
        "market_volatility_score": market_score,
        "vol_of_vol_score": vol_of_vol_score,
        "breadth_confirmation_score": breadth_score,
        "volatility_score": volatility_score,
        "volatility_risk_score": volatility_risk_score,
        "volatility_regime": volatility_regime,
        "risk_regime": volatility_regime,
        "stability_state": stability_state,
        "strategy_environment": _determine_strategy_environment(
            volatility_regime=volatility_regime,
            stability_state=stability_state,
        ),
        "components": {
            "asset": asset_components,
            "market": market_components,
            "vol_of_vol": vol_of_vol_components,
            "breadth": breadth_components,
        },
    }


def _compute_asset_volatility_score(
    snapshot: Dict[str, Any],
) -> tuple[float, Dict[str, float]]:
    atr_percentile = _safe_float(snapshot.get("atr_14_percentile_252"))
    atr_trend_ratio = _safe_float(snapshot.get("atr_trend_ratio"))
    atr_change_5d = _safe_float(snapshot.get("atr_14_change_5d"))
    atr_change_20d = _safe_float(snapshot.get("atr_14_change_20d"))
    hv_20 = _safe_float(snapshot.get("hv_20"))
    hv_50 = _safe_float(snapshot.get("hv_50"))

    percentile_pressure = _clamp((atr_percentile - 50.0) / 50.0)
    trend_pressure = _clamp(atr_trend_ratio - 1.0)
    momentum_pressure = _clamp((atr_change_5d + atr_change_20d) / 2.0)

    hv_pressure = 0.0
    if hv_50 > 0:
        hv_pressure = _clamp((hv_20 / hv_50) - 1.0)

    danger_score = _clamp(
        percentile_pressure * 0.35
        + trend_pressure * 0.25
        + momentum_pressure * 0.20
        + hv_pressure * 0.20,
    )

    return _clamp(-danger_score), {
        "percentile_pressure": percentile_pressure,
        "trend_pressure": trend_pressure,
        "momentum_pressure": momentum_pressure,
        "hv_pressure": hv_pressure,
    }


def _compute_market_volatility_score(
    market_context: Dict[str, Any],
) -> tuple[float, Dict[str, float]]:
    if not market_context.get("has_vix"):
        return 0.0, {
            "vix_percentile_pressure": 0.0,
            "vix_trend_pressure": 0.0,
            "vix_momentum_pressure": 0.0,
        }

    vix_percentile = _safe_float(market_context.get("vix_percentile_252"))
    vix_trend_ratio = _safe_float(market_context.get("vix_trend_ratio"))
    vix_change_5d = _safe_float(market_context.get("vix_change_5d"))
    vix_change_20d = _safe_float(market_context.get("vix_change_20d"))

    percentile_pressure = _clamp((vix_percentile - 50.0) / 50.0)
    trend_pressure = _clamp(vix_trend_ratio - 1.0)
    momentum_pressure = _clamp((vix_change_5d + vix_change_20d) / 2.0)

    danger_score = _clamp(
        percentile_pressure * 0.45 + trend_pressure * 0.30 + momentum_pressure * 0.25,
    )

    return _clamp(-danger_score), {
        "vix_percentile_pressure": percentile_pressure,
        "vix_trend_pressure": trend_pressure,
        "vix_momentum_pressure": momentum_pressure,
    }


def _compute_vol_of_vol_score(
    market_context: Dict[str, Any],
) -> tuple[float, Dict[str, float]]:
    if not market_context.get("has_vvix"):
        return 0.0, {
            "vvix_percentile_pressure": 0.0,
            "vvix_trend_pressure": 0.0,
            "vvix_momentum_pressure": 0.0,
        }

    vvix_percentile = _safe_float(market_context.get("vvix_percentile_252"))
    vvix_trend_ratio = _safe_float(market_context.get("vvix_trend_ratio"))
    vvix_change_5d = _safe_float(market_context.get("vvix_change_5d"))
    vvix_change_20d = _safe_float(market_context.get("vvix_change_20d"))

    percentile_pressure = _clamp((vvix_percentile - 50.0) / 50.0)
    trend_pressure = _clamp(vvix_trend_ratio - 1.0)
    momentum_pressure = _clamp((vvix_change_5d + vvix_change_20d) / 2.0)

    danger_score = _clamp(
        percentile_pressure * 0.40 + trend_pressure * 0.30 + momentum_pressure * 0.30,
    )

    return _clamp(-danger_score), {
        "vvix_percentile_pressure": percentile_pressure,
        "vvix_trend_pressure": trend_pressure,
        "vvix_momentum_pressure": momentum_pressure,
    }


def _compute_breadth_confirmation_score(
    market_context: Dict[str, Any],
) -> tuple[float, Dict[str, float]]:
    if not market_context.get("has_breadth"):
        return 0.0, {
            "raw_participation_score": 0.0,
            "raw_leadership_score": 0.0,
            "raw_mcclellan_score": 0.0,
            "price_ad_divergence_pressure": 0.0,
            "ad_line_trend_score": 0.0,
        }

    breadth_percent = _safe_float(market_context.get("breadth_percent"))
    pct_above_50dma = _safe_float(market_context.get("pct_above_50dma"))
    pct_above_200dma = _safe_float(market_context.get("pct_above_200dma"))
    ad_ratio = _safe_float(market_context.get("ad_ratio"))
    new_high_low_diff = _safe_float(market_context.get("new_high_low_diff"))
    new_high_low_ratio = _safe_float(market_context.get("new_high_low_ratio"))
    mcclellan_oscillator = _safe_float(market_context.get("mcclellan_oscillator"))
    mcclellan_summation_index = _safe_float(
        market_context.get("mcclellan_summation_index")
    )
    price_ad_divergence = bool(market_context.get("price_ad_divergence"))
    ad_line_trend_score = _safe_float(market_context.get("ad_line_trend_score"))

    participation_score = _compute_raw_participation_score(
        breadth_percent=breadth_percent,
        ad_ratio=ad_ratio,
        pct_above_50dma=pct_above_50dma,
        pct_above_200dma=pct_above_200dma,
    )
    leadership_score = _compute_raw_leadership_score(
        new_high_low_diff=new_high_low_diff,
        new_high_low_ratio=new_high_low_ratio,
    )
    mcclellan_score = _compute_raw_mcclellan_score(
        mcclellan_oscillator=mcclellan_oscillator,
        mcclellan_summation_index=mcclellan_summation_index,
    )
    divergence_pressure = -1.0 if price_ad_divergence else 0.0

    composite_score = _clamp(
        participation_score * 0.40
        + leadership_score * 0.25
        + mcclellan_score * 0.20
        + ad_line_trend_score * 0.10
        + divergence_pressure * 0.05,
    )

    return composite_score, {
        "raw_participation_score": participation_score,
        "raw_leadership_score": leadership_score,
        "raw_mcclellan_score": mcclellan_score,
        "price_ad_divergence_pressure": divergence_pressure,
        "ad_line_trend_score": ad_line_trend_score,
    }


def _compute_raw_participation_score(
    *,
    breadth_percent: float,
    ad_ratio: float,
    pct_above_50dma: float,
    pct_above_200dma: float,
) -> float:
    breadth_percent_score = _clamp(
        (breadth_percent - 0.50) / 0.50,
    )
    above_50_score = _clamp(
        (pct_above_50dma - 0.50) / 0.50,
    )
    above_200_score = _clamp(
        (pct_above_200dma - 0.50) / 0.50,
    )
    ad_ratio_score = _score_raw_ad_ratio(
        ad_ratio,
    )

    return _clamp(
        breadth_percent_score * 0.30
        + above_50_score * 0.30
        + above_200_score * 0.25
        + ad_ratio_score * 0.15,
    )


def _score_raw_ad_ratio(
    ad_ratio: float,
) -> float:
    if ad_ratio <= 0:
        return 0.0

    if ad_ratio >= 2.0:
        return 1.0

    if ad_ratio >= 1.2:
        return 0.5

    if ad_ratio >= 0.8:
        return 0.0

    if ad_ratio >= 0.5:
        return -0.5

    return -1.0


def _compute_raw_leadership_score(
    *,
    new_high_low_diff: float,
    new_high_low_ratio: float,
) -> float:
    diff_score = _clamp(
        new_high_low_diff / 100.0,
    )

    ratio_score = 0.0
    if new_high_low_ratio >= 3.0:
        ratio_score = 1.0
    elif new_high_low_ratio >= 1.5:
        ratio_score = 0.5
    elif 0.0 < new_high_low_ratio < 0.33:
        ratio_score = -1.0
    elif 0.0 < new_high_low_ratio < 0.75:
        ratio_score = -0.5

    return _clamp(
        diff_score * 0.60 + ratio_score * 0.40,
    )


def _compute_raw_mcclellan_score(
    *,
    mcclellan_oscillator: float,
    mcclellan_summation_index: float,
) -> float:
    oscillator_score = _clamp(
        mcclellan_oscillator / 250.0,
    )
    summation_score = _clamp(
        mcclellan_summation_index / 1000.0,
    )

    return _clamp(
        oscillator_score * 0.65 + summation_score * 0.35,
    )


def _determine_volatility_regime(volatility_risk_score: float) -> str:
    if volatility_risk_score >= ELEVATED_RISK_THRESHOLD:
        return "high"

    if volatility_risk_score >= NORMAL_RISK_THRESHOLD:
        return "elevated"

    if volatility_risk_score >= STABLE_RISK_THRESHOLD:
        return "normal"

    return "stable"


def _determine_stability_state(volatility_risk_score: float) -> str:
    if volatility_risk_score >= ELEVATED_RISK_THRESHOLD:
        return "unstable"

    if volatility_risk_score >= NORMAL_RISK_THRESHOLD:
        return "elevated_risk"

    if volatility_risk_score < STABLE_RISK_THRESHOLD:
        return "stable"

    return "normal"


def _determine_strategy_environment(
    volatility_regime: str,
    stability_state: str,
) -> Dict[str, float]:
    bull = 1.0
    bear = 1.0
    sideways = 1.0

    if volatility_regime == "high":
        bull *= 0.70
        bear *= 0.85
        sideways *= 1.30
    elif volatility_regime == "elevated":
        bull *= 0.85
        bear *= 0.90
        sideways *= 1.10
    elif volatility_regime == "stable":
        bull *= 1.10
        bear *= 0.95
        sideways *= 0.90

    if stability_state == "unstable":
        bull *= 0.70
        bear *= 0.85
        sideways *= 1.25
    elif stability_state == "elevated_risk":
        bull *= 0.85
        bear *= 0.90
        sideways *= 1.10

    return {
        "bull": bull,
        "bear": bear,
        "sideways": sideways,
    }
