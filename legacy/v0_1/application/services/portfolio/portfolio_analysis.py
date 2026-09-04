from __future__ import annotations

from typing import Any

from core.utils.utils import (
    _get_value,
    _last_or_none,
    _safe_float,
    _safe_list,
)


def execute_portfolio_analysis(
    positions_state: dict[str, Any],
    equity_state: dict[str, Any],
    portfolio_history: dict[str, Any] | None = None,
) -> dict[str, Any]:
    positions = list(positions_state.get("positions", []))

    equity = max(
        _safe_float(equity_state.get("equity")),
        1e-6,
    )

    cash = _safe_float(equity_state.get("cash"))
    portfolio_value = _safe_float(
        equity_state.get("portfolio_value"),
        default=equity,
    )

    if portfolio_value <= 0:
        portfolio_value = equity

    history_state = _extract_portfolio_history_state(
        portfolio_history,
    )

    unrealized_pnl = _compute_unrealized_pnl(
        positions,
    )

    unrealized_pnl_pct = _compute_unrealized_pnl_pct(
        positions,
    )

    unrealized_intraday_pnl = _compute_unrealized_intraday_pnl(
        positions,
    )

    unrealized_intraday_pnl_pct = _compute_unrealized_intraday_pnl_pct(
        positions,
    )

    pnl_total = history_state["profit_loss"]
    pnl_total_pct = history_state["profit_loss_pct"]

    realized_pnl = pnl_total - unrealized_pnl if history_state["has_history"] else 0.0

    base_value = history_state["base_value"]
    realized_pnl_pct = realized_pnl / base_value if base_value > 0 else 0.0

    if not positions:
        return _empty_portfolio_state(
            equity=equity,
            cash=cash,
            portfolio_value=portfolio_value,
            unrealized_pnl=unrealized_pnl,
            unrealized_pnl_pct=unrealized_pnl_pct,
            unrealized_intraday_pnl=unrealized_intraday_pnl,
            unrealized_intraday_pnl_pct=unrealized_intraday_pnl_pct,
            realized_pnl=realized_pnl,
            realized_pnl_pct=realized_pnl_pct,
            pnl_total=pnl_total,
            pnl_total_pct=pnl_total_pct,
            history_state=history_state,
        )

    gross_exposure = 0.0
    net_exposure = 0.0
    long_exposure = 0.0
    short_exposure = 0.0
    weighted_beta = 0.0
    largest_position_pct = 0.0

    sector_exposure: dict[str, float] = {}
    asset_class_exposure: dict[str, float] = {}
    absolute_weights: list[float] = []

    for position in positions:
        normalized = _normalize_position(
            position=position,
            equity=equity,
        )

        exposure_pct = normalized["exposure_pct"]
        signed_exposure = normalized["signed_exposure"]

        gross_exposure += abs(exposure_pct)
        net_exposure += signed_exposure

        if normalized["side"] == "long":
            long_exposure += exposure_pct
        else:
            short_exposure += exposure_pct

        weighted_beta += signed_exposure * normalized["beta"]

        sector = normalized["sector"]
        asset_class = normalized["asset_class"]

        sector_exposure[sector] = sector_exposure.get(sector, 0.0) + abs(exposure_pct)

        asset_class_exposure[asset_class] = asset_class_exposure.get(
            asset_class, 0.0
        ) + abs(exposure_pct)

        largest_position_pct = max(
            largest_position_pct,
            abs(exposure_pct),
        )

        absolute_weights.append(
            abs(exposure_pct),
        )

    leverage = gross_exposure

    concentration_score = _compute_concentration(
        absolute_weights,
    )

    diversification_score = _compute_diversification(
        concentration_score,
    )

    portfolio_heat = gross_exposure

    cash_pct = cash / equity if equity > 0 else 0.0

    beta_risk = min(
        1.0,
        abs(weighted_beta) / 2.0,
    )

    portfolio_regime = _classify_portfolio_regime(
        net_exposure=net_exposure,
        leverage=leverage,
    )

    directional_bias = _classify_directional_bias(
        net_exposure,
    )

    risk_intensity = _compute_risk_intensity(
        leverage=leverage,
        concentration=concentration_score,
        net_exposure=net_exposure,
        beta_exposure=weighted_beta,
    )

    return {
        "portfolio_value": portfolio_value,
        "equity": equity,
        "cash": cash,
        "cash_pct": cash_pct,
        "position_count": len(positions),
        "gross_exposure": gross_exposure,
        "net_exposure": net_exposure,
        "long_exposure": long_exposure,
        "short_exposure": short_exposure,
        "leverage": leverage,
        "largest_position_pct": largest_position_pct,
        "concentration_score": concentration_score,
        "diversification_score": diversification_score,
        "sector_exposure": sector_exposure,
        "asset_class_exposure": asset_class_exposure,
        "beta_exposure": weighted_beta,
        "beta_risk": beta_risk,
        "portfolio_heat": portfolio_heat,
        "risk_intensity": risk_intensity,
        "portfolio_regime": portfolio_regime,
        "directional_bias": directional_bias,
        "unrealized_pnl": unrealized_pnl,
        "unrealized_pnl_pct": unrealized_pnl_pct,
        "unrealized_intraday_pnl": unrealized_intraday_pnl,
        "unrealized_intraday_pnl_pct": unrealized_intraday_pnl_pct,
        "realized_pnl": realized_pnl,
        "realized_pnl_pct": realized_pnl_pct,
        "pnl_total": pnl_total,
        "pnl_total_pct": pnl_total_pct,
        "portfolio_history": history_state,
        "risk_signals": {
            "high_leverage": leverage >= 1.50,
            "overconcentrated": concentration_score >= 0.45,
            "directionally_aggressive": abs(net_exposure) >= 0.80,
            "high_beta": abs(weighted_beta) >= 1.50,
            "low_cash_buffer": cash_pct <= 0.10,
            "portfolio_loss": pnl_total < 0.0,
            "unrealized_intraday_loss": unrealized_intraday_pnl < 0.0,
        },
    }


def _normalize_position(
    position: dict[str, Any],
    equity: float,
) -> dict[str, Any]:
    quantity = abs(
        _safe_float(position.get("quantity")),
    )

    current_price = _safe_float(
        position.get("current_price"),
    )

    market_value = abs(
        _safe_float(
            position.get("market_value"),
            default=quantity * current_price,
        )
    )

    side = str(
        position.get("side", "long"),
    ).lower()

    beta = _safe_float(
        position.get("beta"),
        default=1.0,
    )

    sector = str(
        position.get("sector", "unknown"),
    )

    asset_class = str(
        position.get("asset_class", "equity"),
    )

    exposure_pct = market_value / equity

    signed_exposure = exposure_pct if side == "long" else -exposure_pct

    return {
        "quantity": quantity,
        "current_price": current_price,
        "market_value": market_value,
        "side": side,
        "beta": beta,
        "sector": sector,
        "asset_class": asset_class,
        "exposure_pct": exposure_pct,
        "signed_exposure": signed_exposure,
    }


def _extract_portfolio_history_state(
    portfolio_history: dict[str, Any] | None,
) -> dict[str, Any]:
    if not portfolio_history:
        return _empty_history_state()

    timestamps = _safe_list(
        _get_value(portfolio_history, "timestamp"),
    )

    equity_values = _safe_list(
        _get_value(portfolio_history, "equity"),
    )

    profit_loss_values = _safe_list(
        _get_value(portfolio_history, "profit_loss"),
    )

    profit_loss_pct_values = _safe_list(
        _get_value(portfolio_history, "profit_loss_pct"),
    )

    has_history = bool(
        timestamps or equity_values or profit_loss_values or profit_loss_pct_values
    )

    if not has_history:
        return _empty_history_state()

    return {
        "has_history": True,
        "timestamp": _last_or_none(timestamps),
        "equity": _safe_float(_last_or_none(equity_values)),
        "profit_loss": _safe_float(_last_or_none(profit_loss_values)),
        "profit_loss_pct": _safe_float(_last_or_none(profit_loss_pct_values)),
        "base_value": _safe_float(
            _get_value(portfolio_history, "base_value"),
        ),
        "timeframe": str(
            _get_value(portfolio_history, "timeframe", ""),
        ),
        "cashflow": _get_value(portfolio_history, "cashflow", {}) or {},
    }


def _compute_unrealized_pnl(
    positions: list[dict[str, Any]],
) -> float:
    return sum(_safe_float(position.get("unrealized_pnl")) for position in positions)


def _compute_unrealized_pnl_pct(
    positions: list[dict[str, Any]],
) -> float:
    cost_basis = _compute_cost_basis(
        positions,
    )

    if cost_basis <= 0.0:
        return 0.0

    return (
        _compute_unrealized_pnl(
            positions,
        )
        / cost_basis
    )


def _compute_unrealized_intraday_pnl(
    positions: list[dict[str, Any]],
) -> float:
    return sum(
        _safe_float(position.get("unrealized_intraday_pnl")) for position in positions
    )


def _compute_unrealized_intraday_pnl_pct(
    positions: list[dict[str, Any]],
) -> float:
    cost_basis = _compute_cost_basis(
        positions,
    )

    if cost_basis <= 0.0:
        return 0.0

    return (
        _compute_unrealized_intraday_pnl(
            positions,
        )
        / cost_basis
    )


def _compute_cost_basis(
    positions: list[dict[str, Any]],
) -> float:
    return sum(abs(_safe_float(position.get("cost_basis"))) for position in positions)


def _compute_concentration(
    weights: list[float],
) -> float:
    if not weights:
        return 0.0

    return min(
        1.0,
        sum(weight * weight for weight in weights),
    )


def _compute_diversification(
    concentration_score: float,
) -> float:
    return max(
        0.0,
        min(
            1.0,
            1.0 - concentration_score,
        ),
    )


def _compute_risk_intensity(
    leverage: float,
    concentration: float,
    net_exposure: float,
    beta_exposure: float,
) -> float:
    score = (
        leverage * 0.35
        + concentration * 0.30
        + abs(net_exposure) * 0.20
        + min(
            1.0,
            abs(beta_exposure) / 2.0,
        )
        * 0.15
    )

    return max(
        0.0,
        min(1.0, score),
    )


def _classify_portfolio_regime(
    net_exposure: float,
    leverage: float,
) -> str:
    if leverage < 0.10:
        return "flat"

    if leverage >= 1.50:
        return "stressed"

    if net_exposure >= 0.50:
        return "risk_on"

    if net_exposure <= -0.50:
        return "risk_off"

    return "balanced"


def _classify_directional_bias(
    net_exposure: float,
) -> str:
    if net_exposure >= 0.20:
        return "long"

    if net_exposure <= -0.20:
        return "short"

    return "neutral"


def _empty_portfolio_state(
    *,
    equity: float,
    cash: float,
    portfolio_value: float,
    unrealized_pnl: float,
    unrealized_pnl_pct: float,
    unrealized_intraday_pnl: float,
    unrealized_intraday_pnl_pct: float,
    realized_pnl: float,
    realized_pnl_pct: float,
    pnl_total: float,
    pnl_total_pct: float,
    history_state: dict[str, Any],
) -> dict[str, Any]:
    cash_pct = cash / equity if equity > 0 else 0.0

    return {
        "portfolio_value": portfolio_value,
        "equity": equity,
        "cash": cash,
        "cash_pct": cash_pct,
        "gross_exposure": 0.0,
        "net_exposure": 0.0,
        "long_exposure": 0.0,
        "short_exposure": 0.0,
        "leverage": 0.0,
        "position_count": 0,
        "largest_position_pct": 0.0,
        "concentration_score": 0.0,
        "diversification_score": 1.0,
        "sector_exposure": {},
        "asset_class_exposure": {},
        "beta_exposure": 0.0,
        "beta_risk": 0.0,
        "portfolio_heat": 0.0,
        "portfolio_regime": "flat",
        "directional_bias": "neutral",
        "risk_intensity": 0.0,
        "unrealized_pnl": unrealized_pnl,
        "unrealized_pnl_pct": unrealized_pnl_pct,
        "unrealized_intraday_pnl": unrealized_intraday_pnl,
        "unrealized_intraday_pnl_pct": unrealized_intraday_pnl_pct,
        "realized_pnl": realized_pnl,
        "realized_pnl_pct": realized_pnl_pct,
        "pnl_total": pnl_total,
        "pnl_total_pct": pnl_total_pct,
        "portfolio_history": history_state,
        "risk_signals": {
            "high_leverage": False,
            "overconcentrated": False,
            "directionally_aggressive": False,
            "high_beta": False,
            "low_cash_buffer": cash_pct <= 0.10,
            "portfolio_loss": pnl_total < 0.0,
            "unrealized_intraday_loss": unrealized_intraday_pnl < 0.0,
        },
    }


def _empty_history_state() -> dict[str, Any]:
    return {
        "has_history": False,
        "timestamp": None,
        "equity": 0.0,
        "profit_loss": 0.0,
        "profit_loss_pct": 0.0,
        "base_value": 0.0,
        "timeframe": "",
        "cashflow": {},
    }
