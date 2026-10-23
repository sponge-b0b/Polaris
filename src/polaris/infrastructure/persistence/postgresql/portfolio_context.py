"""Durable append-only Portfolio context owner history."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, insert, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from polaris.application.portfolio_context import (
    InvalidPortfolioContextHistory,
    PortfolioContextCommit,
    PortfolioContextConflict,
    PortfolioContextHistory,
    PortfolioContextStoreUnavailable,
)

from .portfolio_context_codec import commit_from_payload, commit_payload
from .runtime_qualification import require_qualified_postgres_runtime
from .schema import portfolio_context_commits


async def _load(connection: AsyncConnection) -> PortfolioContextHistory:
    result = await connection.execute(
        select(portfolio_context_commits).order_by(
            portfolio_context_commits.c.known_at,
            portfolio_context_commits.c.commit_id,
        )
    )
    commits = []
    for row in result.mappings():
        commit = commit_from_payload(row["payload"])
        if commit.commit_id != row["commit_id"] or commit.known_at != row["known_at"]:
            raise InvalidPortfolioContextHistory("stored owner commit metadata differs")
        commits.append(commit)
    return PortfolioContextHistory(tuple(commits))


class PostgresPortfolioContextHistoryStore:
    """Serialize owner commits and validate complete history before append."""

    def __init__(self, engine: AsyncEngine) -> None:
        # duplicate-code: each adapter qualifies its own connection boundary.
        # arid: disable
        require_qualified_postgres_runtime()
        self._engine = engine
        # arid: enable

    async def load(self) -> PortfolioContextHistory:
        try:
            async with self._engine.connect() as connection:
                return await _load(connection)
        except SQLAlchemyError as error:
            raise PortfolioContextStoreUnavailable(
                "Portfolio context history read failed"
            ) from error
        except (TypeError, ValueError) as error:
            raise InvalidPortfolioContextHistory(
                "Portfolio context history cannot be reconstructed"
            ) from error

    async def append(
        self, commit: PortfolioContextCommit, *, expected_last_commit: UUID | None
    ) -> PortfolioContextHistory:
        if type(commit) is not PortfolioContextCommit:
            raise TypeError("commit must be PortfolioContextCommit")
        try:
            async with self._engine.begin() as connection:
                await connection.execute(select(func.pg_advisory_xact_lock(408359)))
                history = await _load(connection)
                last = history.commits[-1].commit_id if history.commits else None
                if last != expected_last_commit:
                    raise PortfolioContextConflict("Portfolio context history advanced")
                updated = history.append(commit)
                await connection.execute(
                    insert(portfolio_context_commits).values(
                        commit_id=commit.commit_id,
                        known_at=commit.known_at,
                        payload=commit_payload(commit),
                    )
                )
                return updated
        except IntegrityError as error:
            raise PortfolioContextConflict(
                "Portfolio context commit identity already exists"
            ) from error
        except SQLAlchemyError as error:
            raise PortfolioContextStoreUnavailable(
                "Portfolio context history append failed"
            ) from error
