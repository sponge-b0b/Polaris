from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from datetime import UTC, datetime
from typing import cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core.storage.persistence.completed_run_archive import (
    CompletedRunBundle,
    CompletedRunRecord,
)
from core.storage.persistence.postgres_completed_run_archive import (
    PostgresCompletedRunArchive,
)
from core.storage.persistence.repositories.postgres_completed_run_repository import (
    PostgresCompletedRunRepository,
)


class FakeSessionContext(AbstractAsyncContextManager[AsyncSession]):
    def __init__(
        self,
        session: object,
    ) -> None:
        self.session = session
        self.entered = 0
        self.exited = 0

    async def __aenter__(
        self,
    ) -> AsyncSession:
        self.entered += 1
        return cast(
            AsyncSession,
            self.session,
        )

    async def __aexit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        self.exited += 1


class FakeRepository:
    def __init__(
        self,
        bundle: CompletedRunBundle | None = None,
    ) -> None:
        self.bundle = bundle
        self.archived: list[CompletedRunBundle] = []
        self.loaded: list[tuple[str, str]] = []
        self.listed: list[str] = []
        self.deleted: list[tuple[str, str]] = []
        self.cleaned: list[tuple[int | None, int | None]] = []

    async def persist_completed_run_bundle(
        self,
        bundle: CompletedRunBundle,
    ) -> None:
        self.archived.append(
            bundle,
        )

    async def load_completed_run_bundle(
        self,
        *,
        workflow_name: str,
        execution_id: str,
    ) -> CompletedRunBundle | None:
        self.loaded.append(
            (
                workflow_name,
                execution_id,
            )
        )
        return self.bundle

    async def list_completed_run_ids(
        self,
        workflow_name: str,
    ) -> list[str]:
        self.listed.append(
            workflow_name,
        )
        return ["exec-2", "exec-1"]

    async def delete_completed_run(
        self,
        *,
        workflow_name: str,
        execution_id: str,
    ) -> None:
        self.deleted.append(
            (
                workflow_name,
                execution_id,
            )
        )

    async def cleanup_completed_runs(
        self,
        *,
        max_age_days: int | None = None,
        max_count: int | None = None,
    ) -> int:
        self.cleaned.append(
            (
                max_age_days,
                max_count,
            )
        )
        return 3


@pytest.mark.asyncio
async def test_archive_run_delegates_to_repository_with_session_context() -> None:
    context = FakeSessionContext(object())
    repository = FakeRepository()
    archive = PostgresCompletedRunArchive(
        session_factory=lambda: context,
        repository_factory=lambda session: cast(
            PostgresCompletedRunRepository,
            repository,
        ),
    )
    bundle = _bundle()

    await archive.archive_run(
        bundle,
    )

    assert context.entered == 1
    assert context.exited == 1
    assert repository.archived == [bundle]


@pytest.mark.asyncio
async def test_load_list_delete_and_cleanup_delegate_to_repository() -> None:
    context = FakeSessionContext(object())
    repository = FakeRepository(
        bundle=_bundle(),
    )
    archive = PostgresCompletedRunArchive(
        session_factory=lambda: context,
        repository_factory=lambda session: cast(
            PostgresCompletedRunRepository,
            repository,
        ),
    )

    loaded = await archive.load_archived_run(
        workflow_name="morning_report",
        execution_id="exec-1",
    )
    execution_ids = await archive.list_archived_runs(
        "morning_report",
    )
    await archive.delete_archived_run(
        workflow_name="morning_report",
        execution_id="exec-1",
    )
    cleaned = await archive.cleanup_archived_runs(
        max_age_days=30,
        max_count=10,
    )

    assert loaded == repository.bundle
    assert execution_ids == ["exec-2", "exec-1"]
    assert cleaned == 3
    assert repository.loaded == [("morning_report", "exec-1")]
    assert repository.listed == ["morning_report"]
    assert repository.deleted == [("morning_report", "exec-1")]
    assert repository.cleaned == [(30, 10)]
    assert context.entered == 4
    assert context.exited == 4


@pytest.mark.asyncio
async def test_archive_run_propagates_repository_errors() -> None:
    context = FakeSessionContext(object())

    class ErrorRepository(FakeRepository):
        async def persist_completed_run_bundle(
            self,
            bundle: CompletedRunBundle,
        ) -> None:
            raise RuntimeError("archive failed")

    archive = PostgresCompletedRunArchive(
        session_factory=lambda: context,
        repository_factory=lambda session: cast(
            PostgresCompletedRunRepository,
            ErrorRepository(),
        ),
    )

    with pytest.raises(RuntimeError, match="archive failed"):
        await archive.archive_run(
            _bundle(),
        )

    assert context.entered == 1
    assert context.exited == 1


def _bundle() -> CompletedRunBundle:
    completed_at = datetime(2026, 6, 21, 12, tzinfo=UTC)
    return CompletedRunBundle(
        run=CompletedRunRecord(
            run_id="run-1",
            workflow_name="morning_report",
            workflow_id="morning_report",
            execution_id="exec-1",
            runtime_id="runtime-1",
            status="succeeded",
            success=True,
            context_json={"state": "complete"},
            inputs_json={},
            outputs_json={},
            metadata={},
            errors_json=[],
            started_at=completed_at,
            completed_at=completed_at,
            duration_seconds=1.0,
            node_count=0,
            completed_node_count=0,
            failed_node_count=0,
        )
    )
