from __future__ import annotations

from collections.abc import Sequence
from contextlib import AbstractAsyncContextManager
from datetime import UTC, datetime
from enum import StrEnum
from types import TracebackType
from typing import cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core.runtime.events import RuntimeEvent, RuntimeEventType
from core.storage.persistence.runtime import (
    RuntimePersistenceEventSubscriber,
    RuntimePersistenceEventSubscriberConfig,
    RuntimePersistenceResult,
    WorkflowEventRecord,
    WorkflowNodeRunRecord,
    WorkflowRunRecord,
    WorkflowStateSnapshotRecord,
)
from core.storage.persistence.runtime.runtime_persistence_repository import (
    RuntimePersistenceRepository,
)
from core.workflow.bootstrap.workflow_bootstrap import (
    WorkflowBootstrapConfig,
    build_workflow_runtime,
)


class ExampleEnum(StrEnum):
    VALUE = "value"


class FakeSessionContext(AbstractAsyncContextManager[AsyncSession]):
    def __init__(
        self,
        session: object,
    ) -> None:
        self._session = session
        self.entered = 0
        self.exited = 0

    async def __aenter__(
        self,
    ) -> AsyncSession:
        self.entered += 1
        return cast(
            AsyncSession,
            self._session,
        )

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        self.exited += 1
        return None


class FakeRuntimePersistenceRepository(RuntimePersistenceRepository):
    def __init__(
        self,
        session: AsyncSession,
        result: RuntimePersistenceResult | None = None,
    ) -> None:
        self.session = session
        self.result = result or RuntimePersistenceResult.succeeded()
        self.workflow_runs: list[WorkflowRunRecord] = []
        self.node_runs: list[WorkflowNodeRunRecord] = []
        self.events: list[WorkflowEventRecord] = []

    async def persist_workflow_run(
        self,
        record: WorkflowRunRecord,
    ) -> RuntimePersistenceResult:
        self.workflow_runs.append(record)
        return self.result

    async def persist_node_run(
        self,
        record: WorkflowNodeRunRecord,
    ) -> RuntimePersistenceResult:
        self.node_runs.append(record)
        return self.result

    async def persist_event(
        self,
        record: WorkflowEventRecord,
    ) -> RuntimePersistenceResult:
        self.events.append(record)
        return self.result

    async def persist_workflow_state_snapshot(
        self,
        record: WorkflowStateSnapshotRecord,
    ) -> RuntimePersistenceResult:
        return self.result

    async def get_workflow_run(
        self,
        workflow_name: str,
        execution_id: str,
    ) -> WorkflowRunRecord | None:
        return None

    async def list_node_runs(
        self,
        workflow_name: str,
        execution_id: str,
    ) -> list[WorkflowNodeRunRecord]:
        return []

    async def list_events(
        self,
        workflow_name: str,
        execution_id: str,
    ) -> Sequence[WorkflowEventRecord]:
        return ()

    async def get_workflow_state_snapshot(
        self,
        snapshot_id: str,
    ) -> WorkflowStateSnapshotRecord | None:
        return None

    async def list_workflow_state_snapshots(
        self,
        *,
        workflow_name: str | None = None,
        execution_id: str | None = None,
        runtime_id: str | None = None,
        workflow_status: str | None = None,
        checkpoint_reference: str | None = None,
        wave_index: int | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[WorkflowStateSnapshotRecord]:
        return ()


def _workflow_event(
    event_type: RuntimeEventType = RuntimeEventType.WORKFLOW_PROGRESS_COMPLETED,
) -> RuntimeEvent:
    return RuntimeEvent(
        event_type=event_type,
        workflow_id="workflow-id-1",
        execution_id="exec-1",
        runtime_id="runtime-1",
        timestamp=datetime(2026, 5, 30, 12, tzinfo=UTC),
        payload={
            "workflow_name": "morning_report",
            "state": "completed",
            "duration_seconds": 42.5,
            "generated_at": datetime(2026, 5, 30, 12, tzinfo=UTC),
            "enum_value": ExampleEnum.VALUE,
        },
        metadata={
            "workflow_name": "morning_report",
            "mode": "paper",
        },
    )


def _node_event() -> RuntimeEvent:
    return RuntimeEvent(
        event_type=RuntimeEventType.NODE_PROGRESS_COMPLETED,
        workflow_id="workflow-id-1",
        execution_id="exec-1",
        runtime_id="runtime-1",
        node_name="macro_node",
        wave_index=2,
        timestamp=datetime(2026, 5, 30, 12, tzinfo=UTC),
        payload={
            "workflow_name": "morning_report",
            "node_type": "macro",
            "success": True,
        },
        metadata={
            "workflow_name": "morning_report",
        },
    )


@pytest.mark.asyncio
async def test_subscriber_persists_runtime_event_and_workflow_summary() -> None:
    repository = FakeRuntimePersistenceRepository(
        cast(
            AsyncSession,
            object(),
        )
    )
    session_context = FakeSessionContext(
        object(),
    )
    subscriber = RuntimePersistenceEventSubscriber(
        session_factory=lambda: session_context,
        repository_factory=lambda session: repository,
    )

    await subscriber.handle_event(
        _workflow_event(),
    )

    assert session_context.entered == 1
    assert session_context.exited == 1
    assert len(repository.events) == 1
    assert len(repository.workflow_runs) == 1
    assert repository.workflow_runs[0].workflow_name == "morning_report"
    assert repository.workflow_runs[0].status == "completed"
    assert repository.workflow_runs[0].completed_at is not None
    assert repository.workflow_runs[0].duration_seconds == 42.5
    assert repository.events[0].payload["generated_at"] == "2026-05-30T12:00:00+00:00"
    assert repository.events[0].payload["enum_value"] == "value"


@pytest.mark.asyncio
async def test_subscriber_persists_node_summary_from_node_event() -> None:
    repository = FakeRuntimePersistenceRepository(
        cast(
            AsyncSession,
            object(),
        )
    )
    subscriber = RuntimePersistenceEventSubscriber(
        session_factory=lambda: FakeSessionContext(object()),
        repository_factory=lambda session: repository,
    )

    await subscriber.handle_event(
        _node_event(),
    )

    assert len(repository.events) == 1
    assert len(repository.node_runs) == 1
    assert repository.node_runs[0].node_name == "macro_node"
    assert repository.node_runs[0].wave_index == 2
    assert repository.node_runs[0].status == "succeeded"
    assert repository.node_runs[0].completed_at is not None


@pytest.mark.asyncio
async def test_subscriber_skips_events_without_workflow_identity() -> None:
    repository = FakeRuntimePersistenceRepository(
        cast(
            AsyncSession,
            object(),
        )
    )
    subscriber = RuntimePersistenceEventSubscriber(
        session_factory=lambda: FakeSessionContext(object()),
        repository_factory=lambda session: repository,
    )

    await subscriber.handle_event(
        RuntimeEvent(
            event_type=RuntimeEventType.WORKFLOW_STATE_CHANGED,
            workflow_id="",
            execution_id="exec-1",
        )
    )

    assert repository.events == []
    assert repository.workflow_runs == []
    assert repository.node_runs == []


@pytest.mark.asyncio
async def test_subscriber_can_fail_fast_on_persistence_failure() -> None:
    repository = FakeRuntimePersistenceRepository(
        cast(
            AsyncSession,
            object(),
        ),
        result=RuntimePersistenceResult.failed("database unavailable"),
    )
    subscriber = RuntimePersistenceEventSubscriber(
        session_factory=lambda: FakeSessionContext(object()),
        repository_factory=lambda session: repository,
        config=RuntimePersistenceEventSubscriberConfig(
            fail_fast=True,
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="database unavailable",
    ):
        await subscriber.handle_event(
            _workflow_event(),
        )


def test_bootstrap_wires_injected_runtime_persistence_subscriber() -> None:
    subscriber = RuntimePersistenceEventSubscriber(
        session_factory=lambda: FakeSessionContext(object()),
        repository_factory=lambda session: FakeRuntimePersistenceRepository(session),
    )

    runtime = build_workflow_runtime(
        config=WorkflowBootstrapConfig(
            enable_checkpoints=False,
            enable_artifacts=False,
            enable_telemetry=False,
            enable_jsonl_telemetry=False,
            enable_observability=False,
            enable_policies=False,
            enable_governance=False,
        ),
        runtime_persistence_subscriber=subscriber,
    )

    assert runtime.runtime_persistence_subscriber is subscriber
    assert runtime.event_bus.global_subscriber_count() >= 2


def test_bootstrap_leaves_postgres_persistence_disabled_by_default() -> None:
    runtime = build_workflow_runtime(
        config=WorkflowBootstrapConfig(
            enable_checkpoints=False,
            enable_artifacts=False,
            enable_telemetry=False,
            enable_jsonl_telemetry=False,
            enable_observability=False,
            enable_policies=False,
            enable_governance=False,
        ),
    )

    assert runtime.runtime_persistence_subscriber is None


@pytest.mark.asyncio
async def test_subscriber_respects_disabled_projection_categories() -> None:
    repository = FakeRuntimePersistenceRepository(
        cast(
            AsyncSession,
            object(),
        )
    )
    subscriber = RuntimePersistenceEventSubscriber(
        session_factory=lambda: FakeSessionContext(object()),
        repository_factory=lambda session: repository,
        config=RuntimePersistenceEventSubscriberConfig(
            persist_events=False,
            persist_workflow_summaries=False,
            persist_node_summaries=True,
        ),
    )

    await subscriber.handle_event(
        _node_event(),
    )

    assert repository.events == []
    assert repository.workflow_runs == []
    assert len(repository.node_runs) == 1


@pytest.mark.asyncio
async def test_subscriber_suppresses_persistence_failure_by_default() -> None:
    repository = FakeRuntimePersistenceRepository(
        cast(
            AsyncSession,
            object(),
        ),
        result=RuntimePersistenceResult.failed("database unavailable"),
    )
    subscriber = RuntimePersistenceEventSubscriber(
        session_factory=lambda: FakeSessionContext(object()),
        repository_factory=lambda session: repository,
    )

    await subscriber.handle_event(
        _workflow_event(),
    )

    assert len(repository.events) == 1
    assert len(repository.workflow_runs) == 1
