from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from core.storage.persistence.lineage import JsonObject, PersistenceLineage
from core.storage.persistence.portfolio import (
    PortfolioEquityHistoryPointRecord,
    new_portfolio_equity_history_point_id,
)

_REQUIRED_SERIES = (
    "timestamp",
    "equity",
    "profit_loss",
    "profit_loss_pct",
)


def normalize_portfolio_equity_history(
    *,
    account_id: str,
    source: str,
    history: Mapping[str, Any],
    lineage: PersistenceLineage | None = None,
) -> tuple[PortfolioEquityHistoryPointRecord, ...]:
    """Normalize one provider history payload into append-only equity points."""

    if not history:
        return ()

    if lineage is None:
        lineage = PersistenceLineage()

    series = {name: _require_series(history, name) for name in _REQUIRED_SERIES}
    lengths = {len(values) for values in series.values()}
    if len(lengths) != 1:
        raise ValueError("Portfolio history series must have equal lengths.")

    timeframe = _require_text(history.get("timeframe"), "timeframe")
    base_value = _optional_float(history.get("base_value"), "base_value")
    cashflow = _cashflow_series(
        history.get("cashflow"), point_count=next(iter(lengths))
    )

    points: list[PortfolioEquityHistoryPointRecord] = []
    for index, timestamp in enumerate(series["timestamp"]):
        observed_at = _observed_at(timestamp)
        points.append(
            PortfolioEquityHistoryPointRecord(
                portfolio_equity_history_point_id=(
                    new_portfolio_equity_history_point_id(
                        account_id=account_id,
                        source=source,
                        timeframe=timeframe,
                        observed_at=observed_at,
                    )
                ),
                account_id=account_id,
                source=source,
                timeframe=timeframe,
                observed_at=observed_at,
                equity=_require_float(series["equity"][index], "equity"),
                profit_loss=_require_float(
                    series["profit_loss"][index],
                    "profit_loss",
                ),
                profit_loss_pct=_optional_float(
                    series["profit_loss_pct"][index],
                    "profit_loss_pct",
                ),
                base_value=base_value,
                cashflow_payload=_cashflow_payload_at(cashflow, index=index),
                lineage=lineage,
            )
        )

    return tuple(points)


def _require_series(
    history: Mapping[str, Any],
    name: str,
) -> list[Any]:
    value = history.get(name)
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a list.")
    return value


def _observed_at(value: Any) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp datetimes must be timezone-aware.")
        return value.astimezone(UTC)

    if isinstance(value, bool):
        raise ValueError(
            "timestamp must be an epoch number or timezone-aware datetime."
        )

    try:
        return datetime.fromtimestamp(float(value), UTC)
    except (TypeError, ValueError, OSError) as exc:
        raise ValueError(
            "timestamp must be an epoch number or timezone-aware datetime."
        ) from exc


def _require_text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string.")
    return value.strip()


def _require_float(value: Any, name: str) -> float:
    result = _optional_float(value, name)
    if result is None:
        raise ValueError(f"{name} is required.")
    return result


def _optional_float(value: Any, name: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError(f"{name} must be numeric.")
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric.") from exc


def _cashflow_series(
    value: Any,
    *,
    point_count: int,
) -> dict[str, list[Any]]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ValueError("cashflow must be a mapping.")

    cashflow: dict[str, list[Any]] = {}
    for activity_type, activity_values in value.items():
        if not isinstance(activity_values, list):
            raise ValueError("cashflow activity values must be lists.")
        if len(activity_values) != point_count:
            raise ValueError("cashflow activity series must match history length.")
        cashflow[str(activity_type)] = activity_values
    return cashflow


def _cashflow_payload_at(
    cashflow: Mapping[str, list[Any]],
    *,
    index: int,
) -> JsonObject:
    return {
        activity_type: activity_values[index]
        for activity_type, activity_values in cashflow.items()
        if activity_values[index] is not None
    }
