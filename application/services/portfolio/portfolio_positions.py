from __future__ import annotations

from typing import Any
from core.utils.utils import (
    _get_value,
    _safe_bool,
    _safe_float,
    _safe_str,
)


def execute_positions_analysis(
    raw_positions: list[Any],
    symbol: str | None = None,
) -> dict[str, Any]:
    if raw_positions is None:
        raw_positions = []

    if not isinstance(raw_positions, list):
        raise ValueError("raw_positions must be a list.")

    if symbol:
        target_symbol = symbol.upper()
        raw_positions = [
            position
            for position in raw_positions
            if _safe_str(_get_value(position, "symbol")).upper() == target_symbol
        ]

    enriched_positions = [_enrich_position(position) for position in raw_positions]

    gross_exposure = sum(
        abs(position["market_value"]) for position in enriched_positions
    )

    net_exposure = sum(
        position["signed_market_value"] for position in enriched_positions
    )

    long_exposure = sum(
        abs(position["market_value"])
        for position in enriched_positions
        if position["side"] == "long"
    )

    short_exposure = sum(
        abs(position["market_value"])
        for position in enriched_positions
        if position["side"] == "short"
    )

    for position in enriched_positions:
        position["exposure_weight"] = (
            abs(position["market_value"]) / gross_exposure
            if gross_exposure > 0
            else 0.0
        )

    concentration_risk = _compute_concentration_risk(
        enriched_positions,
    )

    leverage_risk = _compute_leverage_risk(
        gross_exposure=gross_exposure,
        long_exposure=long_exposure,
        short_exposure=short_exposure,
    )

    directional_bias = _classify_directional_bias(
        net_exposure=net_exposure,
    )

    return {
        "positions": enriched_positions,
        "gross_exposure": gross_exposure,
        "net_exposure": net_exposure,
        "long_exposure": long_exposure,
        "short_exposure": short_exposure,
        "concentration_risk": concentration_risk,
        "leverage_risk": leverage_risk,
        "position_count": len(enriched_positions),
        "long_position_count": sum(
            1 for p in enriched_positions if p["side"] == "long"
        ),
        "short_position_count": sum(
            1 for p in enriched_positions if p["side"] == "short"
        ),
        "risk_signals": {
            "overconcentrated": concentration_risk > 0.70,
            "high_leverage": leverage_risk > 0.70,
            "directional_bias": directional_bias,
        },
    }


def _enrich_position(
    position: Any,
) -> dict[str, Any]:
    symbol = _safe_str(
        _get_value(position, "symbol"),
    ).upper()

    side = _normalize_side(
        _get_value(position, "side", "long"),
    )

    quantity = abs(
        _safe_float(
            _first_available(
                position,
                "qty",
                "quantity",
            ),
        )
    )

    qty_available = abs(
        _safe_float(
            _get_value(
                position,
                "qty_available",
                quantity,
            ),
        )
    )

    entry_price = _safe_float(
        _first_available(
            position,
            "avg_entry_price",
            "entry_price",
        ),
    )

    current_price = _safe_float(
        _get_value(
            position,
            "current_price",
        ),
    )

    market_value = abs(
        _safe_float(
            _first_available(
                position,
                "market_value",
                ("usd", "market_value"),
            ),
            default=quantity * current_price,
        )
    )

    if market_value == 0.0 and quantity > 0 and current_price > 0:
        market_value = quantity * current_price

    cost_basis = abs(
        _safe_float(
            _first_available(
                position,
                "cost_basis",
                ("usd", "cost_basis"),
            ),
            default=quantity * entry_price,
        )
    )

    if cost_basis == 0.0 and quantity > 0 and entry_price > 0:
        cost_basis = quantity * entry_price

    unrealized_pnl_default = (
        cost_basis - market_value if side == "short" else market_value - cost_basis
    )

    unrealized_pnl = _safe_float(
        _first_available(
            position,
            "unrealized_pl",
            "pnl",
            ("usd", "unrealized_pl"),
        ),
        default=unrealized_pnl_default,
    )

    unrealized_pnl_pct = _safe_float(
        _first_available(
            position,
            "unrealized_plpc",
            "pnl_pct",
            ("usd", "unrealized_plpc"),
        ),
        default=(unrealized_pnl / cost_basis if cost_basis > 0 else 0.0),
    )

    unrealized_intraday_pnl = _safe_float(
        _first_available(
            position,
            "unrealized_intraday_pl",
            ("usd", "unrealized_intraday_pl"),
        ),
    )

    unrealized_intraday_pnl_pct = _safe_float(
        _first_available(
            position,
            "unrealized_intraday_plpc",
            ("usd", "unrealized_intraday_plpc"),
        ),
    )

    change_today = _safe_float(
        _get_value(
            position,
            "change_today",
        ),
    )

    signed_market_value = market_value if side == "long" else -market_value

    return {
        "symbol": symbol,
        "side": side,
        "quantity": quantity,
        "qty_available": qty_available,
        "entry_price": entry_price,
        "current_price": current_price,
        "lastday_price": _safe_float(
            _get_value(position, "lastday_price"),
        ),
        "change_today": change_today,
        "market_value": market_value,
        "signed_market_value": signed_market_value,
        "cost_basis": cost_basis,
        "unrealized_pnl": unrealized_pnl,
        "unrealized_pnl_pct": unrealized_pnl_pct,
        "unrealized_intraday_pnl": unrealized_intraday_pnl,
        "unrealized_intraday_pnl_pct": unrealized_intraday_pnl_pct,
        "asset_id": _safe_str(
            _get_value(position, "asset_id"),
        ),
        "exchange": _safe_str(
            _get_value(position, "exchange"),
        ),
        "asset_class": _safe_str(
            _get_value(position, "asset_class", "equity"),
            default="equity",
        ),
        "asset_marginable": _safe_bool(
            _get_value(position, "asset_marginable"),
        ),
        "sector": _safe_str(
            _get_value(position, "sector", "unknown"),
            default="unknown",
        ),
        "beta": _safe_float(
            _get_value(position, "beta", 1.0),
            default=1.0,
        ),
        "swap_rate": _safe_float(
            _get_value(position, "swap_rate"),
        ),
        "avg_entry_swap_rate": _safe_float(
            _get_value(position, "avg_entry_swap_rate"),
        ),
        "exposure_weight": 0.0,
    }


def _compute_concentration_risk(
    positions: list[dict[str, Any]],
) -> float:
    if not positions:
        return 0.0

    total = sum(abs(position["market_value"]) for position in positions)

    if total <= 0:
        return 0.0

    weights = [abs(position["market_value"]) / total for position in positions]

    hhi = sum(weight * weight for weight in weights)
    largest_weight = max(weights)

    return min(
        1.0,
        (largest_weight * 0.50) + (hhi * 0.50),
    )


def _compute_leverage_risk(
    gross_exposure: float,
    long_exposure: float,
    short_exposure: float,
) -> float:
    if gross_exposure <= 0:
        return 0.0

    directional_imbalance = abs(long_exposure - short_exposure) / gross_exposure

    leverage_factor = min(
        1.0,
        gross_exposure / 100000.0,
    )

    return min(
        1.0,
        directional_imbalance * 0.50 + leverage_factor * 0.50,
    )


def _classify_directional_bias(
    net_exposure: float,
) -> str:
    if net_exposure > 0:
        return "long"

    if net_exposure < 0:
        return "short"

    return "neutral"


def _normalize_side(value: Any) -> str:
    side = _safe_str(value, default="long").lower()

    if side.endswith(".long"):
        return "long"

    if side.endswith(".short"):
        return "short"

    if side in {"short", "sell"}:
        return "short"

    return "long"


def _first_available(
    source: Any,
    *paths: str | tuple[str, ...],
) -> Any:
    for path in paths:
        value = _get_nested_value(source, path)

        if value is not None:
            return value

    return None


def _get_nested_value(
    source: Any,
    path: str | tuple[str, ...],
) -> Any:
    if isinstance(path, str):
        return _get_value(source, path)

    current = source

    for part in path:
        current = _get_value(current, part)

        if current is None:
            return None

    return current
