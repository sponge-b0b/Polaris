from __future__ import annotations

from dataclasses import fields
from typing import Any

from domain.portfolio.models.portfolio_state import (
    PortfolioState,
)

from core.database.models.portfolio_state import (
    PortfolioStateHistoryModel,
    PortfolioStateLatestModel,
)


def _state_values(
    state: PortfolioState,
) -> dict[str, Any]:
    return {field.name: getattr(state, field.name) for field in fields(PortfolioState)}


def _model_values(
    model: PortfolioStateHistoryModel | PortfolioStateLatestModel,
) -> dict[str, Any]:
    values = {
        field.name: getattr(model, field.name) for field in fields(PortfolioState)
    }
    values["account_health"] = values["account_health"] or "unknown"
    values["portfolio_regime"] = values["portfolio_regime"] or "unknown"
    values["directional_bias"] = values["directional_bias"] or "neutral"
    values["risk_signals"] = values["risk_signals"] or {}
    values["sector_exposure"] = values["sector_exposure"] or {}
    values["asset_class_exposure"] = values["asset_class_exposure"] or {}
    return values


class PortfolioStateSerializer:
    @staticmethod
    def to_history_model(
        state: PortfolioState,
    ) -> PortfolioStateHistoryModel:

        return PortfolioStateHistoryModel(
            **_state_values(state),
        )

    @staticmethod
    def to_latest_model(
        state: PortfolioState,
    ) -> PortfolioStateLatestModel:

        return PortfolioStateLatestModel(
            **_state_values(state),
        )

    @staticmethod
    def from_latest_model(
        model: PortfolioStateLatestModel,
    ) -> PortfolioState:

        return PortfolioState(
            **_model_values(model),
        )

    @staticmethod
    def from_history_model(
        model: PortfolioStateHistoryModel,
    ) -> PortfolioState:

        return PortfolioState(
            **_model_values(model),
        )
