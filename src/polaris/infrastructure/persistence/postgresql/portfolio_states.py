"""PostgreSQL storage for Portfolio-owned actual State facts."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, insert, select
from sqlalchemy.engine import RowMapping
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine

from polaris.application.portfolio import (
    PortfolioStateConflict,
    PortfolioStateStoreFailure,
)
from polaris.domain.portfolio import (
    FinancialInstrumentId,
    PortfolioId,
    PortfolioSource,
    PortfolioState,
    PortfolioStateId,
    RecordedPortfolioState,
)

from .codec_support import uuid_value
from .runtime_qualification import require_qualified_postgres_runtime
from .schema import portfolio_states


def _from_row(row: RowMapping) -> RecordedPortfolioState:
    state = PortfolioState(
        state_id=PortfolioStateId(uuid_value(row["state_id"], "state_id")),
        portfolio_id=PortfolioId(uuid_value(row["portfolio_id"], "portfolio_id")),
        as_of=row["as_of"],
        source=PortfolioSource(
            system=row["source_system"],
            record_reference=row["source_record_reference"],
            observed_at=row["source_observed_at"],
        ),
        currency=row["currency"],
        capital_basis=Decimal(row["capital_basis"]),
        cash=Decimal(row["cash"]),
        instrument_id=FinancialInstrumentId(
            uuid_value(row["instrument_id"], "instrument_id")
        ),
        position_quantity=Decimal(row["position_quantity"]),
        position_value=Decimal(row["position_value"]),
        exposure_value=Decimal(row["exposure_value"]),
        allocation_fraction=Decimal(row["allocation_fraction"]),
        interpretation_basis=row["interpretation_basis"],
        uncertainty=row["uncertainty"],
    )
    return RecordedPortfolioState(state=state, known_at=row["known_at"])


class PostgresPortfolioStateStore:
    """Append and reconstruct actual State without replacing source authority."""

    def __init__(self, engine: AsyncEngine) -> None:
        require_qualified_postgres_runtime()
        self._engine = engine

    async def append(self, state: PortfolioState) -> RecordedPortfolioState:
        values = {
            "state_id": state.state_id.value,
            "portfolio_id": state.portfolio_id.value,
            "as_of": state.as_of,
            "known_at": func.clock_timestamp(),
            "source_system": state.source.system,
            "source_record_reference": state.source.record_reference,
            "source_observed_at": state.source.observed_at,
            "currency": state.currency,
            "capital_basis": state.capital_basis,
            "cash": state.cash,
            "instrument_id": state.instrument_id.value,
            "position_quantity": state.position_quantity,
            "position_value": state.position_value,
            "exposure_value": state.exposure_value,
            "allocation_fraction": state.allocation_fraction,
            "interpretation_basis": state.interpretation_basis,
            "uncertainty": state.uncertainty,
        }
        try:
            async with self._engine.begin() as connection:
                result = await connection.execute(
                    insert(portfolio_states)
                    .values(**values)
                    .returning(portfolio_states)
                )
                row = result.mappings().one()
        except IntegrityError as exc:
            if getattr(exc.orig, "sqlstate", None) == "23505":
                raise PortfolioStateConflict("State identity already exists") from exc
            raise PortfolioStateStoreFailure("Portfolio State append failed") from exc
        except SQLAlchemyError as exc:
            raise PortfolioStateStoreFailure("Portfolio State append failed") from exc
        return _from_row(row)

    async def get(self, state_id: PortfolioStateId) -> RecordedPortfolioState | None:
        try:
            async with self._engine.connect() as connection:
                result = await connection.execute(
                    select(portfolio_states).where(
                        portfolio_states.c.state_id == state_id.value
                    )
                )
                row = result.mappings().one_or_none()
        except SQLAlchemyError as exc:
            raise PortfolioStateStoreFailure("Portfolio State read failed") from exc
        return None if row is None else _from_row(row)

    async def history(
        self,
        portfolio_id: PortfolioId,
        *,
        effective_at: datetime,
        known_at: datetime,
    ) -> tuple[RecordedPortfolioState, ...]:
        for field, boundary in (("effective_at", effective_at), ("known_at", known_at)):
            if not isinstance(boundary, datetime) or boundary.utcoffset() is None:
                raise ValueError(f"{field} must be timezone-aware")
        try:
            async with self._engine.connect() as connection:
                result = await connection.execute(
                    select(portfolio_states)
                    .where(
                        portfolio_states.c.portfolio_id == portfolio_id.value,
                        portfolio_states.c.as_of <= effective_at,
                        portfolio_states.c.known_at <= known_at,
                    )
                    .order_by(
                        portfolio_states.c.as_of,
                        portfolio_states.c.known_at,
                        portfolio_states.c.state_id,
                    )
                )
                rows = result.mappings().all()
        except SQLAlchemyError as exc:
            raise PortfolioStateStoreFailure("Portfolio State history failed") from exc
        return tuple(_from_row(row) for row in rows)
