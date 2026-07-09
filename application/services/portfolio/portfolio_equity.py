from __future__ import annotations

from typing import Any
from core.utils.utils import (
    _get_value,
    _safe_bool,
    _safe_float,
    _safe_int,
    _safe_str,
)


def execute_equity_analysis(
    raw_peak_equity: float,
    raw_account: Any,
) -> dict[str, Any]:
    if raw_account is None:
        raw_account = {}

    equity = _safe_float(
        _get_value(raw_account, "equity"),
    )

    portfolio_value = _safe_float(
        _get_value(raw_account, "portfolio_value"),
        default=equity,
    )

    if portfolio_value == 0.0 and equity > 0.0:
        portfolio_value = equity

    cash = _safe_float(
        _get_value(raw_account, "cash"),
    )

    buying_power = _safe_float(
        _get_value(raw_account, "buying_power"),
    )

    long_market_value = _safe_float(
        _get_value(raw_account, "long_market_value"),
    )

    short_market_value = _safe_float(
        _get_value(raw_account, "short_market_value"),
    )

    initial_margin = _safe_float(
        _get_value(raw_account, "initial_margin"),
    )

    maintenance_margin = _safe_float(
        _get_value(raw_account, "maintenance_margin"),
    )

    last_maintenance_margin = _safe_float(
        _get_value(raw_account, "last_maintenance_margin"),
    )

    last_equity = _safe_float(
        _get_value(raw_account, "last_equity"),
    )

    accrued_fees = _safe_float(
        _get_value(raw_account, "accrued_fees"),
    )

    pending_transfer_in = _safe_float(
        _get_value(raw_account, "pending_transfer_in"),
    )

    pending_transfer_out = _safe_float(
        _get_value(raw_account, "pending_transfer_out"),
    )

    multiplier = _safe_float(
        _get_value(raw_account, "multiplier"),
        default=1.0,
    )

    daytrade_count = _safe_int(
        _get_value(raw_account, "daytrade_count"),
    )

    peak_equity = max(
        _safe_float(raw_peak_equity),
        equity,
    )

    drawdown_absolute = max(
        0.0,
        peak_equity - equity,
    )

    drawdown_percent = drawdown_absolute / peak_equity if peak_equity > 0 else 0.0

    capital_base = max(
        peak_equity,
        equity,
        1.0,
    )

    equity_retention_ratio = equity / capital_base

    cash_ratio = cash / equity if equity > 0 else 0.0

    buying_power_ratio = buying_power / equity if equity > 0 else 0.0

    long_exposure_ratio = abs(long_market_value) / equity if equity > 0 else 0.0

    short_exposure_ratio = abs(short_market_value) / equity if equity > 0 else 0.0

    gross_market_value = abs(long_market_value) + abs(short_market_value)

    gross_exposure_ratio = gross_market_value / equity if equity > 0 else 0.0

    net_market_value = long_market_value + short_market_value

    net_exposure_ratio = net_market_value / equity if equity > 0 else 0.0

    margin_utilization_ratio = maintenance_margin / equity if equity > 0 else 0.0

    initial_margin_ratio = initial_margin / equity if equity > 0 else 0.0

    account_blocked = _safe_bool(
        _get_value(raw_account, "account_blocked"),
    )

    trading_blocked = _safe_bool(
        _get_value(raw_account, "trading_blocked"),
    )

    transfers_blocked = _safe_bool(
        _get_value(raw_account, "transfers_blocked"),
    )

    trade_suspended_by_user = _safe_bool(
        _get_value(raw_account, "trade_suspended_by_user"),
    )

    pattern_day_trader = _safe_bool(
        _get_value(raw_account, "pattern_day_trader"),
    )

    shorting_enabled = _safe_bool(
        _get_value(raw_account, "shorting_enabled"),
    )

    account_health = _classify_account_health(
        drawdown_percent=drawdown_percent,
        cash_ratio=cash_ratio,
        margin_utilization_ratio=margin_utilization_ratio,
        trading_blocked=trading_blocked,
        account_blocked=account_blocked,
        trade_suspended_by_user=trade_suspended_by_user,
    )

    return {
        "account_id": _safe_str(
            _get_value(raw_account, "id"),
        ),
        "account_number": _safe_str(
            _get_value(raw_account, "account_number"),
        ),
        "status": _safe_str(
            _get_value(raw_account, "status"),
        ),
        "currency": _safe_str(
            _get_value(raw_account, "currency", "USD"),
            default="USD",
        ),
        "equity": equity,
        "last_equity": last_equity,
        "portfolio_value": portfolio_value,
        "cash": cash,
        "buying_power": buying_power,
        "regt_buying_power": _safe_float(
            _get_value(raw_account, "regt_buying_power"),
        ),
        "daytrading_buying_power": _safe_float(
            _get_value(raw_account, "daytrading_buying_power"),
        ),
        "non_marginable_buying_power": _safe_float(
            _get_value(raw_account, "non_marginable_buying_power"),
        ),
        "options_buying_power": _safe_float(
            _get_value(raw_account, "options_buying_power"),
        ),
        "peak_equity": peak_equity,
        "drawdown_absolute": drawdown_absolute,
        "drawdown_percent": drawdown_percent,
        "capital_base": capital_base,
        "equity_retention_ratio": equity_retention_ratio,
        "cash_ratio": cash_ratio,
        "buying_power_ratio": buying_power_ratio,
        "long_market_value": long_market_value,
        "short_market_value": short_market_value,
        "gross_market_value": gross_market_value,
        "net_market_value": net_market_value,
        "long_exposure_ratio": long_exposure_ratio,
        "short_exposure_ratio": short_exposure_ratio,
        "gross_exposure_ratio": gross_exposure_ratio,
        "net_exposure_ratio": net_exposure_ratio,
        "initial_margin": initial_margin,
        "maintenance_margin": maintenance_margin,
        "last_maintenance_margin": last_maintenance_margin,
        "margin_utilization_ratio": margin_utilization_ratio,
        "initial_margin_ratio": initial_margin_ratio,
        "multiplier": multiplier,
        "accrued_fees": accrued_fees,
        "pending_transfer_in": pending_transfer_in,
        "pending_transfer_out": pending_transfer_out,
        "daytrade_count": daytrade_count,
        "pattern_day_trader": pattern_day_trader,
        "trading_blocked": trading_blocked,
        "transfers_blocked": transfers_blocked,
        "account_blocked": account_blocked,
        "trade_suspended_by_user": trade_suspended_by_user,
        "shorting_enabled": shorting_enabled,
        "options_approved_level": _safe_int(
            _get_value(raw_account, "options_approved_level"),
        ),
        "options_trading_level": _safe_int(
            _get_value(raw_account, "options_trading_level"),
        ),
        "account_health": account_health,
        "risk_signals": {
            "in_drawdown": drawdown_percent > 0.02,
            "deep_drawdown": drawdown_percent > 0.05,
            "critical_drawdown": drawdown_percent > 0.10,
            "capital_expanding": equity >= peak_equity,
            "capital_contracting": equity < peak_equity,
            "low_cash_buffer": cash_ratio < 0.10,
            "healthy_cash_buffer": cash_ratio >= 0.25,
            "low_buying_power": buying_power_ratio < 0.10,
            "high_margin_utilization": margin_utilization_ratio > 0.50,
            "critical_margin_utilization": margin_utilization_ratio > 0.75,
            "high_gross_exposure": gross_exposure_ratio > 1.0,
            "net_short_exposure": net_exposure_ratio < 0.0,
            "pattern_day_trader": pattern_day_trader,
            "daytrade_warning": daytrade_count >= 3,
            "trading_blocked": trading_blocked,
            "transfers_blocked": transfers_blocked,
            "account_blocked": account_blocked,
            "trade_suspended_by_user": trade_suspended_by_user,
            "shorting_disabled": not shorting_enabled,
        },
    }


def _classify_account_health(
    drawdown_percent: float,
    cash_ratio: float,
    margin_utilization_ratio: float,
    trading_blocked: bool,
    account_blocked: bool,
    trade_suspended_by_user: bool,
) -> str:
    if account_blocked or trading_blocked or trade_suspended_by_user:
        return "restricted"

    if drawdown_percent >= 0.10:
        return "critical"

    if margin_utilization_ratio >= 0.75:
        return "margin_stress"

    if drawdown_percent >= 0.05:
        return "stressed"

    if cash_ratio <= 0.05:
        return "illiquid"

    if drawdown_percent <= 0.02 and margin_utilization_ratio < 0.50:
        return "healthy"

    return "stable"
