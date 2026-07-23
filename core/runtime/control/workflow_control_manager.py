from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from core.runtime.control.workflow_control_snapshot import WorkflowControlSnapshot
from core.runtime.control.workflow_control_state import WorkflowControlState
from core.runtime.events import EventBus, RuntimeEvent, RuntimeEventType


class WorkflowControlManager:
    """
    In-memory cooperative workflow control state manager.

    Tracks workflow lifecycle state, coordinates cooperative pause/resume/cancel
    behavior at runtime-safe boundaries, and emits runtime control/progress
    events through the canonical EventBus when one is provided.
    """

    def __init__(
        self,
        event_bus: EventBus | None = None,
    ) -> None:
        self._event_bus = event_bus
        self._snapshots: dict[str, WorkflowControlSnapshot] = {}
        self._resume_events: dict[str, asyncio.Event] = {}
        self._state_change_lock = asyncio.Lock()

    @property
    def event_bus(
        self,
    ) -> EventBus | None:
        return self._event_bus

    async def initialize_execution(
        self,
        execution_id: str,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowControlSnapshot:
        return await self._set_state_and_emit(
            execution_id=execution_id,
            state=WorkflowControlState.PENDING,
            metadata=metadata,
        )

    async def mark_running(
        self,
        execution_id: str,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowControlSnapshot:
        return await self._set_state_and_emit(
            execution_id=execution_id,
            state=WorkflowControlState.RUNNING,
            metadata=metadata,
        )

    async def request_pause(
        self,
        execution_id: str,
        *,
        reason: str | None = None,
        requested_by: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowControlSnapshot:
        resume_event = self._get_resume_event(
            execution_id,
        )
        resume_event.clear()
        return await self._set_state_and_emit(
            execution_id=execution_id,
            state=WorkflowControlState.PAUSING,
            reason=reason,
            requested_by=requested_by,
            metadata=metadata,
        )

    async def wait_if_paused(
        self,
        execution_id: str,
    ) -> None:
        state = self.get_state(
            execution_id,
        )
        if state is WorkflowControlState.PAUSING:
            resume_event = self._get_resume_event(
                execution_id,
            )
            await self._set_state_and_emit(
                execution_id=execution_id,
                state=WorkflowControlState.PAUSED,
            )
            await resume_event.wait()

        if (
            self.get_state(
                execution_id,
            )
            is WorkflowControlState.RESUMING
        ):
            await self._set_state_and_emit(
                execution_id=execution_id,
                state=WorkflowControlState.RUNNING,
            )

    async def request_resume(
        self,
        execution_id: str,
        *,
        reason: str | None = None,
        requested_by: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowControlSnapshot:
        resume_event = self._get_resume_event(
            execution_id,
        )
        snapshot = await self._set_state_and_emit(
            execution_id=execution_id,
            state=WorkflowControlState.RESUMING,
            reason=reason,
            requested_by=requested_by,
            metadata=metadata,
        )
        resume_event.set()
        return snapshot

    def should_pause(
        self,
        execution_id: str,
    ) -> bool:
        return self.get_state(
            execution_id,
        ) in {
            WorkflowControlState.PAUSING,
            WorkflowControlState.PAUSED,
        }

    async def request_cancel(
        self,
        execution_id: str,
        *,
        reason: str | None = None,
        requested_by: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowControlSnapshot:
        resume_event = self._get_resume_event(
            execution_id,
        )
        snapshot = await self._set_state_and_emit(
            execution_id=execution_id,
            state=WorkflowControlState.CANCELLING,
            reason=reason,
            requested_by=requested_by,
            metadata=metadata,
        )
        resume_event.set()
        return snapshot

    async def mark_cancelled(
        self,
        execution_id: str,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowControlSnapshot:
        return await self._set_state_and_emit(
            execution_id=execution_id,
            state=WorkflowControlState.CANCELLED,
            metadata=metadata,
        )

    def should_cancel(
        self,
        execution_id: str,
    ) -> bool:
        return self.get_state(
            execution_id,
        ) in {
            WorkflowControlState.CANCELLING,
            WorkflowControlState.CANCELLED,
        }

    async def mark_completed(
        self,
        execution_id: str,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowControlSnapshot:
        return await self._set_state_and_emit(
            execution_id=execution_id,
            state=WorkflowControlState.COMPLETED,
            metadata=metadata,
        )

    async def mark_failed(
        self,
        execution_id: str,
        *,
        reason: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowControlSnapshot:
        return await self._set_state_and_emit(
            execution_id=execution_id,
            state=WorkflowControlState.FAILED,
            reason=reason,
            metadata=metadata,
        )

    def get_state(
        self,
        execution_id: str,
    ) -> WorkflowControlState:
        return self.get_snapshot(
            execution_id,
        ).state

    def get_snapshot(
        self,
        execution_id: str,
    ) -> WorkflowControlSnapshot:
        self._validate_execution_id(
            execution_id,
        )

        snapshot = self._snapshots.get(
            execution_id,
        )
        if snapshot is None:
            return WorkflowControlSnapshot(
                execution_id=execution_id,
                state=WorkflowControlState.PENDING,
            )

        return WorkflowControlSnapshot(
            execution_id=snapshot.execution_id,
            state=snapshot.state,
            reason=snapshot.reason,
            requested_by=snapshot.requested_by,
            metadata=deepcopy(
                snapshot.metadata,
            ),
            updated_at=snapshot.updated_at,
        )

    def _get_resume_event(
        self,
        execution_id: str,
    ) -> asyncio.Event:
        self._validate_execution_id(
            execution_id,
        )
        resume_event = self._resume_events.get(
            execution_id,
        )
        if resume_event is None:
            resume_event = asyncio.Event()
            self._resume_events[execution_id] = resume_event
        return resume_event

    async def _set_state_and_emit(
        self,
        *,
        execution_id: str,
        state: WorkflowControlState,
        reason: str | None = None,
        requested_by: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowControlSnapshot:
        async with self._state_change_lock:
            snapshot, previous_state = self._set_state(
                execution_id=execution_id,
                state=state,
                reason=reason,
                requested_by=requested_by,
                metadata=metadata,
            )
            await self._emit_state_events(
                snapshot=snapshot,
                previous_state=previous_state,
            )
            return snapshot

    def _set_state(
        self,
        *,
        execution_id: str,
        state: WorkflowControlState,
        reason: str | None = None,
        requested_by: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[WorkflowControlSnapshot, WorkflowControlState | None]:
        self._validate_execution_id(
            execution_id,
        )

        previous = self._snapshots.get(
            execution_id,
        )
        previous_metadata = previous.metadata if previous else {}
        previous_reason = previous.reason if previous else None
        previous_requested_by = previous.requested_by if previous else None
        previous_state = previous.state if previous else None

        merged_metadata = deepcopy(
            previous_metadata,
        )
        if metadata:
            merged_metadata.update(
                deepcopy(
                    metadata,
                ),
            )

        snapshot = WorkflowControlSnapshot(
            execution_id=execution_id,
            state=state,
            reason=reason if reason is not None else previous_reason,
            requested_by=(
                requested_by if requested_by is not None else previous_requested_by
            ),
            metadata=merged_metadata,
            updated_at=datetime.now(
                UTC,
            ),
        )
        self._snapshots[execution_id] = snapshot
        return snapshot, previous_state

    async def _emit_state_events(
        self,
        *,
        snapshot: WorkflowControlSnapshot,
        previous_state: WorkflowControlState | None,
    ) -> None:
        if self._event_bus is None:
            return

        await self._event_bus.emit(
            self._build_runtime_event(
                event_type=RuntimeEventType.WORKFLOW_STATE_CHANGED,
                snapshot=snapshot,
                previous_state=previous_state,
            )
        )

        progress_event_type = self._progress_event_type(
            snapshot.state,
            previous_state=previous_state,
        )
        if progress_event_type is None:
            return

        await self._event_bus.emit(
            self._build_runtime_event(
                event_type=progress_event_type,
                snapshot=snapshot,
                previous_state=previous_state,
            )
        )

    def _build_runtime_event(
        self,
        *,
        event_type: RuntimeEventType,
        snapshot: WorkflowControlSnapshot,
        previous_state: WorkflowControlState | None,
    ) -> RuntimeEvent:
        workflow_id = self._metadata_string(
            snapshot.metadata,
            "workflow_id",
        ) or self._metadata_string(
            snapshot.metadata,
            "workflow_name",
        )
        workflow_name = (
            self._metadata_string(
                snapshot.metadata,
                "workflow_name",
            )
            or workflow_id
        )
        runtime_id = self._metadata_string(
            snapshot.metadata,
            "runtime_id",
        )
        payload = snapshot.to_dict()
        payload.update(
            {
                "workflow_id": workflow_id,
                "workflow_name": workflow_name,
                "execution_id": snapshot.execution_id,
                "runtime_id": runtime_id,
                "state": snapshot.state.value,
                "node_name": None,
                "wave_index": None,
                "timestamp": snapshot.updated_at.isoformat(),
                "context_version": snapshot.metadata.get(
                    "context_version",
                ),
                "metadata": deepcopy(
                    snapshot.metadata,
                ),
                "previous_state": previous_state.value if previous_state else None,
            }
        )

        return RuntimeEvent(
            event_type=event_type,
            execution_id=snapshot.execution_id,
            workflow_id=workflow_id,
            runtime_id=runtime_id,
            payload=payload,
            metadata=deepcopy(
                snapshot.metadata,
            ),
        )

    def _progress_event_type(
        self,
        state: WorkflowControlState,
        *,
        previous_state: WorkflowControlState | None,
    ) -> RuntimeEventType | None:
        if state is WorkflowControlState.RUNNING:
            if previous_state is WorkflowControlState.RESUMING:
                return RuntimeEventType.WORKFLOW_PROGRESS_RESUMED
            return RuntimeEventType.WORKFLOW_PROGRESS_RUNNING

        return {
            WorkflowControlState.PAUSING: RuntimeEventType.WORKFLOW_PROGRESS_PAUSING,
            WorkflowControlState.PAUSED: RuntimeEventType.WORKFLOW_PROGRESS_PAUSED,
            WorkflowControlState.RESUMING: RuntimeEventType.WORKFLOW_PROGRESS_RESUMING,
            WorkflowControlState.CANCELLING: (
                RuntimeEventType.WORKFLOW_PROGRESS_CANCELLING
            ),
            WorkflowControlState.CANCELLED: RuntimeEventType.WORKFLOW_PROGRESS_CANCELLED,  # noqa: E501
            WorkflowControlState.COMPLETED: RuntimeEventType.WORKFLOW_PROGRESS_COMPLETED,  # noqa: E501
            WorkflowControlState.FAILED: RuntimeEventType.WORKFLOW_PROGRESS_FAILED,
        }.get(
            state,
        )

    def _metadata_string(
        self,
        metadata: dict[str, Any],
        key: str,
    ) -> str:
        value = metadata.get(
            key,
        )
        if value is None:
            return ""
        return str(
            value,
        )

    def _validate_execution_id(
        self,
        execution_id: str,
    ) -> None:
        if not execution_id.strip():
            raise ValueError("execution_id cannot be empty.")
