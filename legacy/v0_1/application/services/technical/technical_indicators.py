from __future__ import annotations

from typing import Any, cast

import numpy as np
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD, EMAIndicator
from ta.volatility import AverageTrueRange

from core.utils.utils import _clamp, _safe_bool, _safe_float

TRADING_DAYS_PER_YEAR = 252


def _percentile_rank(series: pd.Series) -> float:
    current = series.iloc[-1]
    if pd.isna(current):
        return 0.0
    return float((series <= current).mean() * 100.0)


def _replace_invalid_numbers(
    series: pd.Series,
    default: float = 0.0,
) -> pd.Series:
    return series.replace([np.inf, -np.inf], np.nan).fillna(default)


def _find_value_column(df: pd.DataFrame) -> str:
    preferred_columns = (
        "close",
        "value",
        "adj_close",
        "price",
        "market_cap_index",
        "ad_line",
    )

    for column in preferred_columns:
        if column in df.columns:
            return column

    numeric_columns = list(df.select_dtypes(include="number").columns)

    if not numeric_columns:
        raise ValueError("Market context DataFrame has no numeric value column.")

    return numeric_columns[0]


def validate_ohlcv(df: pd.DataFrame) -> None:
    required_columns = {"open", "high", "low", "close", "volume"}
    missing_columns = required_columns.difference(set(df.columns))

    if missing_columns:
        raise ValueError(f"Missing required OHLCV columns: {sorted(missing_columns)}")

    if df.empty:
        raise ValueError("Cannot compute technical indicators for empty DataFrame.")


def _validate_optional_context_df(
    df: pd.DataFrame | None,
    name: str,
) -> None:
    if df is None:
        return

    if df.empty:
        raise ValueError(f"{name} DataFrame cannot be empty when provided.")

    _find_value_column(df)


def _validate_sp500_context_df(df: pd.DataFrame | None) -> None:
    if df is None:
        return

    if df.empty:
        raise ValueError("S&P 500 DataFrame cannot be empty when provided.")

    required_columns = {
        "market_cap_index",
        "advances_count",
        "declines_count",
        "net_breadth",
        "ad_line",
        "ad_ratio",
    }

    missing_columns = required_columns.difference(set(df.columns))

    if missing_columns:
        raise ValueError(
            f"Missing required S&P 500 breadth columns: {sorted(missing_columns)}"
        )


def add_ema(df: pd.DataFrame, period: int) -> pd.DataFrame:
    df[f"ema_{period}"] = EMAIndicator(
        close=cast(pd.Series, df["close"]),
        window=period,
    ).ema_indicator()
    return df


def add_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    df[f"rsi_{period}"] = RSIIndicator(
        close=cast(pd.Series, df["close"]),
        window=period,
    ).rsi()
    return df


def add_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    df[f"atr_{period}"] = AverageTrueRange(
        high=cast(pd.Series, df["high"]),
        low=cast(pd.Series, df["low"]),
        close=cast(pd.Series, df["close"]),
        window=period,
    ).average_true_range()
    return df


def add_macd(df: pd.DataFrame) -> pd.DataFrame:
    macd = MACD(
        close=cast(pd.Series, df["close"]),
        window_fast=12,
        window_slow=26,
        window_sign=9,
    )
    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()
    df["macd_histogram"] = macd.macd_diff()
    return df


def add_atr_percent_of_price(
    df: pd.DataFrame,
    period: int = 14,
) -> pd.DataFrame:
    atr_column = f"atr_{period}"
    output_column = f"atr_{period}_percent_of_price"
    df[output_column] = _replace_invalid_numbers(df[atr_column] / df["close"])
    return df


def add_historical_volatility(df: pd.DataFrame, period: int) -> pd.DataFrame:
    returns = df["close"].pct_change()
    df[f"hv_{period}"] = returns.rolling(window=period, min_periods=period).std() * (
        TRADING_DAYS_PER_YEAR**0.5
    )
    return df


def add_atr_percentile(
    df: pd.DataFrame,
    atr_period: int = 14,
    lookback: int = 252,
) -> pd.DataFrame:
    atr_column = f"atr_{atr_period}"
    output_column = f"atr_{atr_period}_percentile_{lookback}"

    df[output_column] = (
        df[atr_column]
        .rolling(window=lookback, min_periods=min(30, lookback))
        .apply(_percentile_rank, raw=False)
    )
    return df


def add_volatility_momentum(
    df: pd.DataFrame,
    atr_period: int = 14,
) -> pd.DataFrame:
    atr_column = f"atr_{atr_period}"
    df[f"atr_{atr_period}_change_5d"] = df[atr_column].pct_change(periods=5)
    df[f"atr_{atr_period}_change_20d"] = df[atr_column].pct_change(periods=20)
    return df


def add_volatility_trend(
    df: pd.DataFrame,
    short_period: int = 14,
    long_period: int = 50,
) -> pd.DataFrame:
    short_column = f"atr_{short_period}"
    long_column = f"atr_{long_period}"

    df["volatility_expanding"] = df[short_column] > df[long_column]
    df["atr_trend_ratio"] = _replace_invalid_numbers(df[short_column] / df[long_column])
    return df


def apply_standard_indicators(df: pd.DataFrame) -> pd.DataFrame:
    validate_ohlcv(df)

    indicator_df = df.copy()

    for period in (8, 21, 50, 200):
        indicator_df = add_ema(indicator_df, period)

    indicator_df = add_rsi(indicator_df, 14)

    indicator_df = add_atr(indicator_df, 14)
    indicator_df = add_atr(indicator_df, 50)
    indicator_df = add_atr_percent_of_price(indicator_df, 14)
    indicator_df = add_atr_percentile(indicator_df, 14, 252)
    indicator_df = add_volatility_momentum(indicator_df, 14)
    indicator_df = add_volatility_trend(indicator_df, 14, 50)

    for period in (20, 50, 100):
        indicator_df = add_historical_volatility(indicator_df, period)

    indicator_df = add_macd(indicator_df)

    return indicator_df


def _prepare_context_series(df: pd.DataFrame, name: str) -> pd.DataFrame:
    value_column = _find_value_column(df)
    context_df = df.copy()
    context_df[name] = context_df[value_column].astype(float)

    context_df[f"{name}_20"] = (
        context_df[name]
        .rolling(
            window=20,
            min_periods=5,
        )
        .mean()
    )

    context_df[f"{name}_50"] = (
        context_df[name]
        .rolling(
            window=50,
            min_periods=10,
        )
        .mean()
    )

    context_df[f"{name}_percentile_252"] = (
        context_df[name]
        .rolling(window=252, min_periods=30)
        .apply(_percentile_rank, raw=False)
    )

    context_df[f"{name}_trend_ratio"] = _replace_invalid_numbers(
        context_df[f"{name}_20"] / context_df[f"{name}_50"]
    )

    context_df[f"{name}_change_5d"] = context_df[name].pct_change(periods=5)
    context_df[f"{name}_change_20d"] = context_df[name].pct_change(periods=20)

    return context_df


def _latest_context_snapshot(
    df: pd.DataFrame | None,
    name: str,
) -> dict[str, float]:
    if df is None:
        return {
            name: 0.0,
            f"{name}_20": 0.0,
            f"{name}_50": 0.0,
            f"{name}_percentile_252": 0.0,
            f"{name}_trend_ratio": 0.0,
            f"{name}_change_5d": 0.0,
            f"{name}_change_20d": 0.0,
        }

    context_df = _prepare_context_series(df, name)
    latest = context_df.iloc[-1]

    return {
        name: _safe_float(latest.get(name)),
        f"{name}_20": _safe_float(latest.get(f"{name}_20")),
        f"{name}_50": _safe_float(latest.get(f"{name}_50")),
        f"{name}_percentile_252": _safe_float(latest.get(f"{name}_percentile_252")),
        f"{name}_trend_ratio": _safe_float(latest.get(f"{name}_trend_ratio")),
        f"{name}_change_5d": _safe_float(latest.get(f"{name}_change_5d")),
        f"{name}_change_20d": _safe_float(latest.get(f"{name}_change_20d")),
    }


def _empty_sp500_context() -> dict[str, float]:
    return {
        "market_cap_index": 0.0,
        "market_cap_index_20": 0.0,
        "market_cap_index_50": 0.0,
        "market_cap_index_change_5d": 0.0,
        "market_cap_index_change_20d": 0.0,
        "advances_count": 0.0,
        "declines_count": 0.0,
        "unchanged_count": 0.0,
        "active_count": 0.0,
        "net_breadth": 0.0,
        "breadth_percent": 0.0,
        "ad_ratio": 0.0,
        "ad_line": 0.0,
        "ad_line_ema_10": 0.0,
        "ad_line_ema_20": 0.0,
        "ad_line_ema_50": 0.0,
        "ad_line_slope_5": 0.0,
        "ad_line_slope_20": 0.0,
        "ad_line_trend_ratio": 0.0,
        "ad_line_trend_score": 0.0,
        "price_ad_divergence": 0.0,
        "pct_above_50dma": 0.0,
        "pct_above_200dma": 0.0,
        "new_highs": 0.0,
        "new_lows": 0.0,
        "new_high_low_diff": 0.0,
        "new_high_low_ratio": 0.0,
    }


def _apply_sp500_indicators(df: pd.DataFrame) -> pd.DataFrame:
    context_df = df.copy()

    context_df["new_high_low_diff"] = context_df["new_highs"] - context_df["new_lows"]

    context_df["new_high_low_ratio"] = np.where(
        context_df["new_lows"] > 0,
        (context_df["new_highs"] / context_df["new_lows"]),
        0.0,
    )

    context_df["price_ad_divergence"] = (
        context_df["market_cap_index"] > context_df["market_cap_index"].shift(5)
    ) & (context_df["ad_line"] < context_df["ad_line"].shift(5))

    context_df["ad_line_ema_10"] = (
        context_df["ad_line"]
        .ewm(
            span=10,
            adjust=False,
        )
        .mean()
    )

    context_df["ad_line_ema_20"] = (
        context_df["ad_line"]
        .ewm(
            span=20,
            adjust=False,
        )
        .mean()
    )

    context_df["ad_line_ema_50"] = (
        context_df["ad_line"]
        .ewm(
            span=50,
            adjust=False,
        )
        .mean()
    )

    context_df["ad_line_slope_5"] = context_df["ad_line"] - context_df["ad_line"].shift(
        5
    )

    context_df["ad_line_slope_20"] = context_df["ad_line"] - context_df[
        "ad_line"
    ].shift(20)

    context_df["ad_line_trend_ratio"] = np.where(
        context_df["ad_line_ema_50"] > 0,
        (context_df["ad_line_ema_20"] / context_df["ad_line_ema_50"]),
        0.0,
    )

    context_df["market_cap_index_20"] = (
        context_df["market_cap_index"]
        .rolling(
            window=20,
            min_periods=5,
        )
        .mean()
    )

    context_df["market_cap_index_50"] = (
        context_df["market_cap_index"]
        .rolling(
            window=50,
            min_periods=10,
        )
        .mean()
    )

    context_df["market_cap_index_change_5d"] = context_df[
        "market_cap_index"
    ].pct_change(periods=5)

    context_df["market_cap_index_change_20d"] = context_df[
        "market_cap_index"
    ].pct_change(periods=20)

    context_df["net_breadth_ema_19"] = (
        context_df["net_breadth"]
        .ewm(
            span=19,
            adjust=False,
        )
        .mean()
    )

    context_df["net_breadth_ema_39"] = (
        context_df["net_breadth"]
        .ewm(
            span=39,
            adjust=False,
        )
        .mean()
    )

    context_df["mcclellan_oscillator"] = (
        context_df["net_breadth_ema_19"] - context_df["net_breadth_ema_39"]
    )

    context_df["mcclellan_summation_index"] = context_df[
        "mcclellan_oscillator"
    ].cumsum()

    return context_df


def _derive_ad_line_trend_score(latest: pd.Series) -> float:
    trend_score = 0.0

    ad_line = _safe_float(latest.get("ad_line"))
    ad_line_ema_20 = _safe_float(latest.get("ad_line_ema_20"))
    ad_line_ema_50 = _safe_float(latest.get("ad_line_ema_50"))
    ad_line_slope_5 = _safe_float(latest.get("ad_line_slope_5"))
    ad_line_slope_20 = _safe_float(latest.get("ad_line_slope_20"))

    if ad_line > ad_line_ema_20:
        trend_score += 0.25
    elif ad_line < ad_line_ema_20:
        trend_score -= 0.25

    if ad_line_ema_20 > ad_line_ema_50:
        trend_score += 0.35
    elif ad_line_ema_20 < ad_line_ema_50:
        trend_score -= 0.35

    if ad_line_slope_5 > 0:
        trend_score += 0.20
    elif ad_line_slope_5 < 0:
        trend_score -= 0.20

    if ad_line_slope_20 > 0:
        trend_score += 0.20
    elif ad_line_slope_20 < 0:
        trend_score -= 0.20

    return _clamp(trend_score, -1.0, 1.0)


def _derive_sp500_context(sp500_df: pd.DataFrame | None) -> dict[str, float]:

    if sp500_df is None:
        return _empty_sp500_context()

    context_df = _apply_sp500_indicators(sp500_df)
    latest = context_df.iloc[-1]

    return {
        "market_cap_index": _safe_float(latest.get("market_cap_index")),
        "market_cap_index_20": _safe_float(latest.get("market_cap_index_20")),
        "market_cap_index_50": _safe_float(latest.get("market_cap_index_50")),
        "market_cap_index_change_5d": _safe_float(
            latest.get("market_cap_index_change_5d")
        ),
        "market_cap_index_change_20d": _safe_float(
            latest.get("market_cap_index_change_20d")
        ),
        "advances_count": _safe_float(latest.get("advances_count")),
        "declines_count": _safe_float(latest.get("declines_count")),
        "unchanged_count": _safe_float(latest.get("unchanged_count")),
        "active_count": _safe_float(latest.get("active_count")),
        "net_breadth": _safe_float(latest.get("net_breadth")),
        "breadth_percent": _safe_float(latest.get("breadth_percent")),
        "ad_ratio": _safe_float(latest.get("ad_ratio")),
        "ad_line": _safe_float(latest.get("ad_line")),
        "ad_line_ema_10": _safe_float(latest.get("ad_line_ema_10")),
        "ad_line_ema_20": _safe_float(latest.get("ad_line_ema_20")),
        "ad_line_ema_50": _safe_float(latest.get("ad_line_ema_50")),
        "ad_line_slope_5": _safe_float(latest.get("ad_line_slope_5")),
        "ad_line_slope_20": _safe_float(latest.get("ad_line_slope_20")),
        "ad_line_trend_ratio": _safe_float(latest.get("ad_line_trend_ratio")),
        "ad_line_trend_score": _derive_ad_line_trend_score(latest),
        "price_ad_divergence": 1.0
        if _safe_bool(latest.get("price_ad_divergence"))
        else 0.0,
        "pct_above_50dma": _safe_float(latest.get("pct_above_50dma")),
        "pct_above_200dma": _safe_float(latest.get("pct_above_200dma")),
        "new_highs": _safe_float(latest.get("new_highs")),
        "new_lows": _safe_float(latest.get("new_lows")),
        "new_high_low_diff": _safe_float(latest.get("new_high_low_diff")),
        "new_high_low_ratio": _safe_float(latest.get("new_high_low_ratio")),
        "net_breadth_ema_19": _safe_float(latest.get("net_breadth_ema_19")),
        "net_breadth_ema_39": _safe_float(latest.get("net_breadth_ema_39")),
        "mcclellan_oscillator": _safe_float(latest.get("mcclellan_oscillator")),
        "mcclellan_summation_index": _safe_float(
            latest.get("mcclellan_summation_index")
        ),
    }


def derive_market_context(
    *,
    vix_df: pd.DataFrame | None = None,
    vvix_df: pd.DataFrame | None = None,
    sp500_df: pd.DataFrame | None = None,
) -> dict[str, Any]:

    _validate_optional_context_df(vix_df, "VIX")
    _validate_optional_context_df(vvix_df, "VVIX")
    _validate_sp500_context_df(sp500_df)

    return {
        **_latest_context_snapshot(vix_df, "vix"),
        **_latest_context_snapshot(vvix_df, "vvix"),
        **_derive_sp500_context(sp500_df),
        "has_vix": vix_df is not None,
        "has_vvix": vvix_df is not None,
        "has_sp500": sp500_df is not None,
        "has_ad_line": sp500_df is not None,
        "has_breadth": sp500_df is not None,
    }


def latest_snapshot(df: pd.DataFrame) -> dict[str, float]:
    latest = df.iloc[-1]

    return {
        "close": _safe_float(latest.get("close")),
        "volume": _safe_float(latest.get("volume")),
        "ema_8": _safe_float(latest.get("ema_8")),
        "ema_21": _safe_float(latest.get("ema_21")),
        "ema_50": _safe_float(latest.get("ema_50")),
        "ema_200": _safe_float(latest.get("ema_200")),
        "rsi_14": _safe_float(latest.get("rsi_14")),
        "atr_14": _safe_float(latest.get("atr_14")),
        "atr_50": _safe_float(latest.get("atr_50")),
        "atr_14_percent_of_price": _safe_float(latest.get("atr_14_percent_of_price")),
        "atr_14_percentile_252": _safe_float(latest.get("atr_14_percentile_252")),
        "atr_14_change_5d": _safe_float(latest.get("atr_14_change_5d")),
        "atr_14_change_20d": _safe_float(latest.get("atr_14_change_20d")),
        "atr_trend_ratio": _safe_float(latest.get("atr_trend_ratio")),
        "volatility_expanding": 1.0
        if _safe_bool(latest.get("volatility_expanding"))
        else 0.0,
        "hv_20": _safe_float(latest.get("hv_20")),
        "hv_50": _safe_float(latest.get("hv_50")),
        "hv_100": _safe_float(latest.get("hv_100")),
        "macd": _safe_float(latest.get("macd")),
        "macd_signal": _safe_float(latest.get("macd_signal")),
        "macd_histogram": _safe_float(latest.get("macd_histogram")),
    }


def derive_micro_regime(snapshot: dict[str, float]) -> dict[str, Any]:
    trend_score = 0.0

    if snapshot["ema_21"] > snapshot["ema_50"]:
        trend_score = 1.0
    elif snapshot["ema_21"] < snapshot["ema_50"]:
        trend_score = -1.0

    rsi = snapshot["rsi_14"]
    rsi_score = 0.0

    if rsi >= 70:
        rsi_score = -1.0
    elif rsi <= 30:
        rsi_score = 1.0
    elif rsi > 0:
        rsi_score = _clamp((50.0 - rsi) / 20.0, -1.0, 1.0)

    macd_score = 0.0

    if snapshot["macd_histogram"] > 0:
        macd_score = 1.0
    elif snapshot["macd_histogram"] < 0:
        macd_score = -1.0

    composite_score = _clamp(
        trend_score * 0.5 + rsi_score * 0.3 + macd_score * 0.2,
        -1.0,
        1.0,
    )

    return {
        "trend_score": trend_score,
        "rsi_score": rsi_score,
        "macd_score": macd_score,
        "composite_score": composite_score,
    }


def compute(
    symbol_df: pd.DataFrame,
    *,
    vix_df: pd.DataFrame | None = None,
    vvix_df: pd.DataFrame | None = None,
    sp500_df: pd.DataFrame | None = None,
) -> dict[str, Any]:

    indicator_df = apply_standard_indicators(symbol_df)
    snapshot = latest_snapshot(indicator_df)
    micro_regime = derive_micro_regime(snapshot)

    market_context = derive_market_context(
        vix_df=vix_df,
        vvix_df=vvix_df,
        sp500_df=sp500_df,
    )

    return {
        "snapshot": snapshot,
        "micro_regime": micro_regime,
        "market_context": market_context,
    }
