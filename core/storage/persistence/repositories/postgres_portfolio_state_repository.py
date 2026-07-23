from __future__ import annotations

from dataclasses import fields
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.models.portfolio_state import (
    PortfolioStateHistoryModel,
    PortfolioStateLatestModel,
)
from core.storage.persistence.portfolio.portfolio_state_repository import (
    PortfolioStateRepository,
)
from core.storage.persistence.serializers.portfolio_state_serializer import (
    PortfolioStateSerializer,
)
from domain.portfolio.models.portfolio_state import (
    PortfolioState,
)

_PORTFOLIO_STATE_FIELD_NAMES = tuple(field.name for field in fields(PortfolioState))
_LATEST_INSERT_FIELD_NAMES = (
    *_PORTFOLIO_STATE_FIELD_NAMES,
    "workflow_name",
    "execution_id",
)
_LATEST_UPDATE_FIELD_NAMES = tuple(
    field_name
    for field_name in _LATEST_INSERT_FIELD_NAMES
    if field_name != "account_id"
)
_LATEST_COLUMN_KEYS_BY_FIELD_NAME = {
    attribute.key: attribute.columns[0].key
    for attribute in PortfolioStateLatestModel.__mapper__.column_attrs
}


def _latest_column_key(
    field_name: str,
) -> str:
    return _LATEST_COLUMN_KEYS_BY_FIELD_NAME[field_name]


def _latest_values(
    model: PortfolioStateLatestModel,
) -> dict[str, Any]:
    return {
        _latest_column_key(field_name): getattr(model, field_name)
        for field_name in _LATEST_INSERT_FIELD_NAMES
    }


class PostgresPortfolioStateRepository(PortfolioStateRepository):
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self._session = session

    async def persist_snapshot(
        self,
        state: PortfolioState,
    ) -> None:

        history_model = PortfolioStateSerializer.to_history_model(
            state,
        )

        self._session.add(history_model)

        latest_model = PortfolioStateSerializer.to_latest_model(
            state,
        )

        latest_values = _latest_values(
            latest_model,
        )

        stmt = insert(PortfolioStateLatestModel).values(
            **latest_values,
        )

        stmt = stmt.on_conflict_do_update(
            index_elements=["account_id"],
            set_={
                **{
                    _latest_column_key(field_name): latest_values[
                        _latest_column_key(field_name)
                    ]
                    for field_name in _LATEST_UPDATE_FIELD_NAMES
                },
                "updated_at": func.now(),
            },
        )

        await self._session.execute(stmt)

        await self._session.commit()

    async def get_latest(
        self,
        account_id: str,
    ) -> PortfolioState | None:

        stmt = select(PortfolioStateLatestModel).where(
            PortfolioStateLatestModel.account_id == account_id
        )

        result = await self._session.execute(stmt)

        model = result.scalar_one_or_none()

        if model is None:
            return None

        return PortfolioStateSerializer.from_latest_model(
            model,
        )

    async def get_history(
        self,
        account_id: str,
        start: datetime,
        end: datetime,
    ) -> list[PortfolioState]:

        stmt = (
            select(PortfolioStateHistoryModel)
            .where(PortfolioStateHistoryModel.account_id == account_id)
            .where(PortfolioStateHistoryModel.timestamp >= start)
            .where(PortfolioStateHistoryModel.timestamp <= end)
            .order_by(PortfolioStateHistoryModel.timestamp.asc())
        )

        result = await self._session.execute(stmt)

        rows = result.scalars().all()

        return [PortfolioStateSerializer.from_history_model(row) for row in rows]
