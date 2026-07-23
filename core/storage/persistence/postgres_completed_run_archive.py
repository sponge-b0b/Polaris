from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager

from sqlalchemy.ext.asyncio import AsyncSession

from core.storage.persistence.completed_run_archive import (
    CompletedRunArchive,
    CompletedRunBundle,
)
from core.storage.persistence.repositories.postgres_completed_run_repository import (
    PostgresCompletedRunRepository,
)

type CompletedRunArchiveSessionFactory = Callable[
    [],
    AbstractAsyncContextManager[AsyncSession],
]
type CompletedRunRepositoryFactory = Callable[
    [AsyncSession],
    PostgresCompletedRunRepository,
]


class PostgresCompletedRunArchive(CompletedRunArchive):
    """PostgreSQL-backed archive for completed workflow runs."""

    def __init__(
        self,
        session_factory: CompletedRunArchiveSessionFactory | None = None,
        repository_factory: CompletedRunRepositoryFactory | None = None,
    ) -> None:
        self._session_factory = session_factory or _default_session_factory
        self._repository_factory = repository_factory or _default_repository_factory

    async def archive_run(
        self,
        bundle: CompletedRunBundle,
    ) -> None:
        async with self._session_factory() as session:
            repository = self._repository_factory(
                session,
            )
            await repository.persist_completed_run_bundle(
                bundle,
            )

    async def load_archived_run(
        self,
        workflow_name: str,
        execution_id: str,
    ) -> CompletedRunBundle | None:
        async with self._session_factory() as session:
            repository = self._repository_factory(
                session,
            )
            return await repository.load_completed_run_bundle(
                workflow_name=workflow_name,
                execution_id=execution_id,
            )

    async def list_archived_runs(
        self,
        workflow_name: str,
    ) -> list[str]:
        async with self._session_factory() as session:
            repository = self._repository_factory(
                session,
            )
            return await repository.list_completed_run_ids(
                workflow_name,
            )

    async def delete_archived_run(
        self,
        workflow_name: str,
        execution_id: str,
    ) -> None:
        async with self._session_factory() as session:
            repository = self._repository_factory(
                session,
            )
            await repository.delete_completed_run(
                workflow_name=workflow_name,
                execution_id=execution_id,
            )

    async def cleanup_archived_runs(
        self,
        max_age_days: int | None = None,
        max_count: int | None = None,
    ) -> int:
        async with self._session_factory() as session:
            repository = self._repository_factory(
                session,
            )
            return await repository.cleanup_completed_runs(
                max_age_days=max_age_days,
                max_count=max_count,
            )


def _default_session_factory() -> AbstractAsyncContextManager[AsyncSession]:
    from core.database.postgres import AsyncSessionLocal

    return AsyncSessionLocal()


def _default_repository_factory(
    session: AsyncSession,
) -> PostgresCompletedRunRepository:
    return PostgresCompletedRunRepository(
        session,
    )
