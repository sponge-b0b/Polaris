"""Stable complete-owner reads during an Intelligence dependent write."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from polaris.application.evidence.revalidation import (
    AtomicCurrentBasisRead,
    AtomicCurrentBasisUnavailable,
    CurrentBasisValidationReader,
)
from polaris.domain.evidence.context_versions import BasisScopeKey

from .schema import POLARIS_TABLE_NAMES


class PostgresCurrentBasisReader:
    """An injected inward current-basis reader bound to the same PostgreSQL engine."""

    def __init__(
        self, engine: AsyncEngine, query: CurrentBasisValidationReader
    ) -> None:
        if query is None:
            raise TypeError("complete current-basis query is required")
        self.engine = engine
        self.query = query


class PostgresIntelligenceBasisParticipation:
    """Block every canonical owner write until dependent validation and commit.

    The owner query may open its normal read connections after this transaction
    holds SHARE locks over the complete current PostgreSQL fact-table registry.
    All those reads then observe a stable committed universe; the dependent
    transaction retains the locks through its write and commit. Model/provider
    work happens before this boundary opens.
    """

    def __init__(
        self,
        connection: AsyncConnection,
        reader: PostgresCurrentBasisReader,
    ) -> None:
        if not connection.in_transaction() or connection.engine is not reader.engine:
            raise AtomicCurrentBasisUnavailable(
                "owner query and dependent write do not share one PostgreSQL engine"
            )
        self._connection = connection
        self._reader = reader
        self._established = False
        self._at: datetime | None = None

    async def establish(self, key: BasisScopeKey) -> AtomicCurrentBasisRead:
        if type(key) is not BasisScopeKey:
            raise TypeError("atomic basis key must be typed")
        if not self._established:
            names = ", ".join(f'"{name}"' for name in sorted(POLARIS_TABLE_NAMES))
            await self._connection.exec_driver_sql(f"LOCK TABLE {names} IN SHARE MODE")
            self._established = True
            at = await self._connection.scalar(text("SELECT clock_timestamp()"))
            if not isinstance(at, datetime) or at.utcoffset() is None:
                raise AtomicCurrentBasisUnavailable(
                    "trusted PostgreSQL validation instant is unavailable"
                )
            self._at = at
        assert self._at is not None
        return AtomicCurrentBasisRead(key, self._at, self._reader.query)
