# Plan: Workflow Control + External Progress Notifications

## Goal

Extend the workflow runtime with:

1. Workflow control:
   - pause
   - resume
   - cancel / stop

2. External progress notifications:
   - workflow state changes
   - wave lifecycle events
   - node lifecycle events
   - current workflow execution state

Primary use case:

```text
CLI displays progress and lets the user control running workflows.
```

---

# Architecture Principles

- Preserve stable core contracts.
- Extend runtime cleanly; do not create a parallel execution system.
- Use cooperative pause/cancel at safe boundaries.
- Use `EventBus` for workflow/node progress events.
- Keep runtime nodes focused on business execution.
- Do not force individual nodes to know about pause/resume yet.
- Do not forcibly kill active async tasks in this phase.
- Prefer metadata over broad result-model changes.
- Existing runtime tests must continue passing.

---

# Safe Control Boundaries

Pause and cancel should be checked at these points:

```text
before workflow starts
before each wave
after each wave
before each node
after each node
```

Running nodes should be allowed to finish unless a future hard-cancel feature is explicitly designed.

---

# Step 1: Build Workflow Control State

Create:

```text
core/runtime/control/workflow_control_state.py
```

Add:

```python
from enum import Enum


class WorkflowControlState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSING = "pausing"
    PAUSED = "paused"
    RESUMING = "resuming"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    FAILED = "failed"
```

State rules:

```text
PAUSING    = pause requested; waiting for safe boundary
PAUSED     = execution parked at safe boundary
RESUMING   = resume requested
CANCELLING = cancel requested; waiting for safe boundary
CANCELLED  = workflow stopped before completion
COMPLETED  = workflow finished normally
FAILED     = workflow failed
```

---

# Step 2: Build Workflow Control Commands

Create:

```text
core/runtime/control/workflow_control_command.py
```

Add:

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from datetime import timezone
from enum import Enum
from typing import Any


class WorkflowControlCommand(str, Enum):
    PAUSE = "pause"
    RESUME = "resume"
    CANCEL = "cancel"


@dataclass(frozen=True, slots=True)
class WorkflowControlRequest:
    execution_id: str
    command: WorkflowControlCommand
    reason: str | None = None
    requested_by: str | None = None
    metadata: dict[str, Any] | None = None
    requested_at: datetime = datetime.now(timezone.utc)
```

---

# Step 3: Build WorkflowControlManager

Create:

```text
core/runtime/control/workflow_control_manager.py
```

Responsibilities:

- Track workflow state by `execution_id`.
- Accept pause/resume/cancel requests.
- Let runtime check pause/cancel state.
- Provide current state snapshots.
- Emit state-change events through `EventBus`.

Suggested API:

```python
class WorkflowControlManager:
    def __init__(self, event_bus: EventBus | None = None) -> None:
        ...

    def initialize_execution(self, execution_id: str) -> None:
        ...

    def mark_running(self, execution_id: str) -> None:
        ...

    def request_pause(self, execution_id: str, reason: str | None = None) -> None:
        ...

    async def wait_if_paused(self, execution_id: str) -> None:
        ...

    def request_resume(self, execution_id: str, reason: str | None = None) -> None:
        ...

    def request_cancel(self, execution_id: str, reason: str | None = None) -> None:
        ...

    def mark_cancelled(self, execution_id: str) -> None:
        ...

    def mark_completed(self, execution_id: str) -> None:
        ...

    def mark_failed(self, execution_id: str) -> None:
        ...

    def get_state(self, execution_id: str) -> WorkflowControlState:
        ...

    def should_pause(self, execution_id: str) -> bool:
        ...

    def should_cancel(self, execution_id: str) -> bool:
        ...
```

Implementation notes:

```text
_states: dict[str, WorkflowControlState]
_resume_events: dict[str, asyncio.Event]
```

Rules:

- `request_pause()` sets `PAUSING`.
- `wait_if_paused()` converts `PAUSING` to `PAUSED` and waits for resume.
- `request_resume()` sets `RESUMING` and releases the resume event.
- Runtime marks state back to `RUNNING`.
- `request_cancel()` sets `CANCELLING`.
- Runtime marks `CANCELLED` at safe boundary.

---

# Step 4: Export Runtime Control Package

Create:

```text
core/runtime/control/__init__.py
```

Export:

```python
from core.runtime.control.workflow_control_command import (
    WorkflowControlCommand,
    WorkflowControlRequest,
)
from core.runtime.control.workflow_control_manager import (
    WorkflowControlManager,
)
from core.runtime.control.workflow_control_state import (
    WorkflowControlState,
)

__all__ = [
    "WorkflowControlCommand",
    "WorkflowControlManager",
    "WorkflowControlRequest",
    "WorkflowControlState",
]
```

---

# Step 5: Add Workflow and Node Progress Events

Use existing `EventBus`.

Emit these event types:

```text
runtime.workflow.state_changed
runtime.workflow.started
runtime.workflow.running
runtime.workflow.pausing
runtime.workflow.paused
runtime.workflow.resuming
runtime.workflow.resumed
runtime.workflow.cancelling
runtime.workflow.cancelled
runtime.workflow.completed
runtime.workflow.failed

runtime.workflow.wave.started
runtime.workflow.wave.completed

runtime.node.started
runtime.node.running
runtime.node.completed
runtime.node.failed
```

Standard payload:

```python
{
    "workflow_id": workflow_id,
    "workflow_name": workflow_name,
    "execution_id": execution_id,
    "runtime_id": runtime_id,
    "state": state,
    "node_name": node_name,
    "wave_index": wave_index,
    "timestamp": timestamp,
    "metadata": metadata,
}
```

CLI should subscribe to progress events instead of scraping logs.

---

# Step 6: Wire Control Manager Into WorkflowBootstrap

Update:

```text
core/workflow/bootstrap/workflow_bootstrap.py
```

Add optional dependency:

```python
workflow_control_manager: WorkflowControlManager | None = None
```

Bootstrap should create a default manager:

```python
if workflow_control_manager is None:
    workflow_control_manager = WorkflowControlManager(
        event_bus=event_bus,
    )
```

Add to `WorkflowBootstrapResult`:

```python
workflow_control_manager: WorkflowControlManager
```

Pass it into `WorkflowFacade.create(...)`.

Also update helper functions:

```text
build_workflow_runtime(...)
build_workflow_runtime_async(...)
```

to accept and pass:

```python
workflow_control_manager: WorkflowControlManager | None = None
```

---

# Step 7: Wire Control Manager Into WorkflowFacade

Update:

```text
core/workflow/execution/workflow_facade.py
```

Add:

```python
workflow_control_manager: WorkflowControlManager | None = None
```

Store:

```python
self.workflow_control_manager = workflow_control_manager
```

Add facade control methods:

```python
def pause_workflow(
    self,
    execution_id: str,
    reason: str | None = None,
) -> None:
    ...

def resume_workflow(
    self,
    execution_id: str,
    reason: str | None = None,
) -> None:
    ...

def cancel_workflow(
    self,
    execution_id: str,
    reason: str | None = None,
) -> None:
    ...

def get_workflow_state(
    self,
    execution_id: str,
) -> WorkflowControlState:
    ...
```

These delegate to `WorkflowControlManager`.

If manager is missing, raise clear `RuntimeError`.

---

# Step 8: Wire Control Manager Into Dishka Providers

Update:

```text
core/bootstrap/workflow_providers.py
```

Provide:

```python
@provide
def provide_workflow_control_manager(
    self,
    event_bus: EventBus,
) -> WorkflowControlManager:
    return WorkflowControlManager(
        event_bus=event_bus,
    )
```

Pass into `WorkflowFacade.create(...)`.

Add provider test or update existing provider wiring tests.

---

# Step 9: Integrate Control Checks Into Runtime Execution Loop

Find the workflow execution loop / runtime engine where waves and nodes execute.

Add before workflow execution:

```python
control_manager.initialize_execution(execution_id)
control_manager.mark_running(execution_id)
```

Before each wave:

```python
if control_manager.should_cancel(execution_id):
    control_manager.mark_cancelled(execution_id)
    return cancelled_result

await control_manager.wait_if_paused(execution_id)
```

Before each node:

```python
if control_manager.should_cancel(execution_id):
    control_manager.mark_cancelled(execution_id)
    return cancelled_result

await control_manager.wait_if_paused(execution_id)
```

After workflow success:

```python
control_manager.mark_completed(execution_id)
```

On workflow exception:

```python
control_manager.mark_failed(execution_id)
```

Important:

```text
Pause/cancel is cooperative.
Do not kill currently running node tasks.
```

---

# Step 10: Emit Progress Events During Execution

In runtime execution loop, emit:

Before workflow:

```text
runtime.workflow.started
runtime.workflow.running
```

Before wave:

```text
runtime.workflow.wave.started
```

After wave:

```text
runtime.workflow.wave.completed
```

Before node:

```text
runtime.node.started
runtime.node.running
```

After node success:

```text
runtime.node.completed
```

After node failure:

```text
runtime.node.failed
```

After workflow success:

```text
runtime.workflow.completed
```

After workflow failure:

```text
runtime.workflow.failed
```

After cancellation:

```text
runtime.workflow.cancelled
```

Payloads must include:

```text
execution_id
workflow_id
workflow_name
runtime_id
node_name when relevant
wave_index when relevant
state
timestamp
```

---

# Step 11: Define Cancelled Workflow Result Behavior

Prefer metadata if workflow result model is stable.

Cancelled result should clearly include:

```python
metadata={
    "cancelled": True,
    "status": "cancelled",
    "reason": reason,
}
```

Expected semantics:

```text
success = False
status = cancelled
remaining nodes are not executed
completed nodes remain available in context/checkpoint state
```

Do not add broad model changes unless required.

---

# Step 12: Add Tests

Add unit tests:

```text
tests/unit/runtime/control/test_workflow_control_manager.py
```

Test:

- initialize execution state
- mark running
- request pause transitions to `PAUSING`
- `wait_if_paused()` transitions to `PAUSED`
- request resume returns to running flow
- request cancel transitions to `CANCELLING`
- mark cancelled transitions to `CANCELLED`
- mark completed transitions to `COMPLETED`
- mark failed transitions to `FAILED`

Add integration tests:

```text
tests/integration/runtime/test_workflow_pause_resume.py
tests/integration/runtime/test_workflow_cancel.py
tests/integration/runtime/test_workflow_progress_events.py
```

Test:

- workflow emits started/running/completed
- node emits started/completed
- pause pauses before next node or wave
- resume continues execution
- cancel prevents remaining nodes from running
- cancelled result includes metadata status
- event payloads include execution_id, workflow_id, node_name, wave_index
- CLI-like subscriber can observe events

---

# External Notification Strategy

## Preferred

Use existing `EventBus`.

CLI subscribes to:

```text
runtime.workflow.*
runtime.node.*
```

## Fallback

Only if `EventBus` cannot support external subscriptions cleanly, add:

```text
core/runtime/progress/
├── progress_event.py
├── progress_sink.py
├── in_memory_progress_sink.py
└── progress_manager.py
```

Do not build this unless needed.

---

# Telemetry Strategy

Emit telemetry for:

```text
workflow_control.pause_requested
workflow_control.paused
workflow_control.resume_requested
workflow_control.resumed
workflow_control.cancel_requested
workflow_control.cancelled

workflow_progress.node_started
workflow_progress.node_completed
workflow_progress.node_failed
```

Use existing `ObservabilityManager` if available.

Telemetry failure must not block execution.

---

# Expected Final API

```python
runtime = build_workflow_runtime(...)

run_task = asyncio.create_task(
    runtime.facade.run_workflow(
        workflow_name="example",
        execution_id="run-1",
    )
)

runtime.facade.pause_workflow(
    execution_id="run-1",
    reason="User requested pause.",
)

runtime.facade.resume_workflow(
    execution_id="run-1",
    reason="User resumed.",
)

runtime.facade.cancel_workflow(
    execution_id="run-1",
    reason="User cancelled.",
)

state = runtime.facade.get_workflow_state(
    execution_id="run-1",
)
```

CLI should be able to display:

```text
Workflow started
Wave 0 started
Node technical_agent started
Node technical_agent completed
Workflow paused
Workflow resumed
Workflow cancelled
Workflow completed
```

---

# Compatibility Rules

- Do not introduce legacy adapters.
- Do not create a second runtime system.
- Do not move workflow state into runtime nodes.
- Do not require nodes to manage pause/resume.
- Do not forcibly cancel active node execution.
- Do not change sacred core contracts unless required.
- Prefer extension points and metadata.
- Keep existing tests passing.

---

# Implementation Order

```text
1. core/runtime/control/workflow_control_state.py
2. core/runtime/control/workflow_control_command.py
3. core/runtime/control/workflow_control_manager.py
4. core/runtime/control/__init__.py
5. tests/unit/runtime/control/test_workflow_control_manager.py
6. Wire WorkflowBootstrapResult
7. Wire WorkflowBootstrap
8. Wire WorkflowFacade
9. Add facade pause/resume/cancel/state methods
10. Wire WorkflowInfrastructureProvider
11. Add runtime execution-loop control checks
12. Add workflow/node progress events
13. Add pause/resume integration test
14. Add cancel integration test
15. Add progress event integration test
16. Run full runtime test suite
```

---

# Success Criteria

- Existing runtime tests pass.
- New control manager unit tests pass.
- Pause/resume integration test passes.
- Cancel integration test passes.
- Progress event test passes.
- CLI can observe workflow and node progress.
- CLI can control workflow by `execution_id`.
- Cancellation prevents remaining nodes from running.
- Pause/resume occurs at safe boundaries.
- Core runtime remains canonical and clean.

---

# Agent Refinement Plan: Incremental Workflow Control + Notifications

This section is intentionally separate from the original plan above. It is the implementation checkpoint log for the incremental, review-after-each-step workflow.

## Implementation Protocol

- Implement one step at a time.
- After each step, update only this section's checkbox state.
- Run the step-specific validation.
- Stop and wait for user review before beginning the next step.
- Keep Typer as the CLI argument/process boundary while moving workflow CLI behavior into async command services in the CLI phase.

## Incremental Steps

- [x] Step 1 — Add `WorkflowControlState` and export it from `core.runtime.control`.
- [x] Step 2 — Add `WorkflowControlCommand` and `WorkflowControlRequest` models.
- [x] Step 3 — Add `WorkflowControlSnapshot` model.
- [x] Step 4 — Add basic `WorkflowControlManager` state/snapshot skeleton.
- [x] Step 5 — Unit test basic control state transitions.
- [x] Step 6 — Add pause/resume manager behavior.
- [x] Step 7 — Unit test pause/resume behavior.
- [x] Step 8 — Add cancel manager behavior.
- [x] Step 9 — Unit test cancel behavior.
- [x] Step 10 — Add runtime event types for control/progress.
- [x] Step 11 — Emit control state events from the manager.
- [x] Step 12 — Unit test control events.
- [x] Step 13 — Wire control manager into `RuntimeEngine` constructor.
- [x] Step 14 — Add runtime control initialization and terminal marking.
- [x] Step 15 — Add pause checks before waves.
- [x] Step 16 — Add pause/resume integration test.
- [x] Step 17 — Add cancel checks before waves.
- [x] Step 18 — Add cancel integration test.
- [x] Step 19 — Add node-boundary pause/cancel checks.
- [x] Step 20 — Add runtime progress event emission.
- [x] Step 21 — Add progress event integration test.
- [x] Step 22 — Add cancelled workflow result semantics.
- [x] Step 23 — Wire control manager into `WorkflowFacade`.
- [x] Step 24 — Wire control manager into `WorkflowBootstrap`.
- [x] Step 25 — Wire control manager into Dishka provider.
- [x] Step 26 — Add CLI async command-service foundation.
- [x] Step 27 — Add CLI progress subscription service.
- [x] Step 28 — Update telemetry mappings for new control/progress events.
- [x] Step 29 — Run targeted runtime/CLI regression checks.
- [x] Step 30 — Run graph update and final review.

## Step 1 Validation

- Import check: `from core.runtime.control import WorkflowControlState`
- Ruff check: `python -m ruff check core/runtime/control`

## CLI Async Recommendation

Use an async workflow command-service layer behind the existing Typer boundary. Do not replace Typer in this feature. The CLI should subscribe to `EventBus` progress notifications and call async facade control APIs through a single small async runner boundary.

## Step 2 Validation

- Import check: `from core.runtime.control import WorkflowControlCommand, WorkflowControlRequest`
- Default timestamp check confirms `requested_at` uses a per-instance default factory.
- Ruff check: `python -m ruff check core/runtime/control`

## Step 3 Validation

- Import check: `from core.runtime.control import WorkflowControlSnapshot`
- Serialization check confirms `WorkflowControlSnapshot.to_dict()` emits boundary-safe values.
- Ruff check: `python -m ruff check core/runtime/control`

## Step 4 Validation

- Import check: `from core.runtime.control import WorkflowControlManager`
- Behavior check confirms initialize/running/completed/failed state transitions and snapshot metadata.
- Ruff check: `python -m ruff check core/runtime/control`


## Step 4 Completion Notes

- Added `WorkflowControlManager` as the in-memory control state/snapshot skeleton.
- Exported `WorkflowControlManager` from `core.runtime.control`.
- Manager now defensively copies snapshot metadata at read/write boundaries.
- Pause/resume/cancel behavior remains intentionally deferred to later steps.

## Step 5 Validation

- Pytest check: `python -m pytest tests/unit/runtime/control/test_workflow_control_manager.py`
- Ruff check: `python -m ruff check core/runtime/control tests/unit/runtime/control/test_workflow_control_manager.py`
- Test coverage confirms default pending snapshots, basic lifecycle transitions, failed state reason handling, metadata defensive copying, and empty execution ID validation.

## Step 6 Validation

- Behavior check confirms `request_pause()` moves executions to `PAUSING`.
- Behavior check confirms `wait_if_paused()` parks executions in `PAUSED` until `request_resume()` is called.
- Behavior check confirms `request_resume()` moves executions through `RESUMING` and releases the pause wait.
- Behavior check confirms resumed executions return to `RUNNING` at the cooperative wait boundary.
- Ruff check: `python -m ruff check core/runtime/control`
- Existing unit regression check: `python -m pytest tests/unit/runtime/control/test_workflow_control_manager.py`

## Step 7 Validation

- Added pause/resume unit coverage to `tests/unit/runtime/control/test_workflow_control_manager.py`.
- Tests confirm pause request context, cooperative parking at `PAUSED`, resume release through `RESUMING`, return to `RUNNING`, and immediate return when not paused.
- Pytest check: `python -m pytest tests/unit/runtime/control/test_workflow_control_manager.py`
- Ruff check: `python -m ruff check core/runtime/control tests/unit/runtime/control/test_workflow_control_manager.py`

## Step 8 Validation

- Behavior check confirms `request_cancel()` moves executions to `CANCELLING`.
- Behavior check confirms `should_cancel()` returns true for `CANCELLING` and `CANCELLED`.
- Behavior check confirms `mark_cancelled()` moves executions to `CANCELLED`.
- Behavior check confirms cancellation releases a paused wait so runtime can observe cancellation at a safe boundary.
- Ruff check: `python -m ruff check core/runtime/control`
- Existing unit regression check: `python -m pytest tests/unit/runtime/control/test_workflow_control_manager.py`

## Step 9 Validation

- Added cancel unit coverage to `tests/unit/runtime/control/test_workflow_control_manager.py`.
- Tests confirm cancel request context, terminal cancelled state, paused wait release on cancellation, and non-cancel states returning `should_cancel() == False`.
- Pytest check: `python -m pytest tests/unit/runtime/control/test_workflow_control_manager.py`
- Ruff check: `python -m ruff check core/runtime/control tests/unit/runtime/control/test_workflow_control_manager.py`

## Step 10 Validation

- Added namespaced workflow control/progress event types to `RuntimeEventType`.
- Added namespaced wave progress event types to `RuntimeEventType`.
- Added namespaced node progress event types to `RuntimeEventType`.
- Updated `RuntimeEvent.is_error` and `RuntimeEvent.is_terminal` classification for new failed/completed/cancelled progress events.
- Import/serialization check confirms new event values emit boundary-safe namespaced strings.
- Ruff check: `python -m ruff check core/runtime/events`
- Existing legacy runtime event values were preserved. I added namespaced progress/control event types instead of changing existing values, to avoid breaking current runtime/replay contracts.

## Step 11 Results — Control State Event Emission

Step 11 was completed as a core runtime refinement.

### Files updated

- `core/runtime/control/workflow_control_manager.py`
- `tests/unit/runtime/control/test_workflow_control_manager.py`
- `.agent/plans/plan_workflow_control_plus_notifications.md`

### Implementation results

- Added optional `EventBus` dependency to `WorkflowControlManager`:
  - `WorkflowControlManager(event_bus: EventBus | None = None)`
- Refactored state-changing manager methods to async so EventBus emission is awaited and deterministic:
  - `initialize_execution(...)`
  - `mark_running(...)`
  - `request_pause(...)`
  - `request_resume(...)`
  - `request_cancel(...)`
  - `mark_cancelled(...)`
  - `mark_completed(...)`
  - `mark_failed(...)`
- Kept read/query methods synchronous:
  - `get_state(...)`
  - `get_snapshot(...)`
  - `should_pause(...)`
  - `should_cancel(...)`
- Added manager-level state-change locking with `asyncio.Lock()` so each state mutation and paired event emission remains ordered.
- Added state event emission for every state transition when an EventBus is provided.
- Kept no-op behavior when no EventBus is provided, preserving simple in-memory use.

### Events emitted

Every state transition emits:

- `runtime.workflow.state_changed`

State-specific progress events emitted by the manager:

- `runtime.workflow.running`
- `runtime.workflow.pausing`
- `runtime.workflow.paused`
- `runtime.workflow.resuming`
- `runtime.workflow.resumed`
- `runtime.workflow.cancelling`
- `runtime.workflow.cancelled`
- `runtime.workflow.completed`
- `runtime.workflow.failed`

### Event payload contract

Manager-emitted events use the canonical `RuntimeEvent` envelope.

Payload contains serialized `WorkflowControlSnapshot` data plus:

- `previous_state`

Metadata is copied from the snapshot metadata.

`workflow_id` and `runtime_id` are derived from snapshot metadata when present:

- `workflow_id`
- `workflow_name` fallback for workflow ID
- `runtime_id`

### Validation completed

- Event behavior check confirmed ordered state/progress events through `EventBus.subscribe_all()`.
- Existing control manager unit tests were updated to await async state-changing APIs.
- Regression tests passed:
  - `python -m pytest tests/unit/runtime/control/test_workflow_control_manager.py`
  - Result: `13 passed`
- Ruff checks passed:
  - `python -m ruff check core/runtime/control core/runtime/events tests/unit/runtime/control/test_workflow_control_manager.py`
  - Result: `All checks passed!`

### Architectural note

This step intentionally made state-changing control manager APIs async. That keeps EventBus publication deterministic, avoids fire-and-forget runtime events, and aligns this control surface with the runtime/workflow async architecture.

## Step 12 Results — Control Event Unit Tests

Step 12 was completed as event-specific unit coverage for the workflow control manager.

### Files updated

- `tests/unit/runtime/control/test_workflow_control_events.py`
- `.agent/plans/plan_workflow_control_plus_notifications.md`

### Implementation results

- Added isolated unit tests for manager-emitted control/progress events through `EventBus.subscribe_all()`.
- Verified `mark_running()` emits ordered state-change and running progress events.
- Verified pause/resume emits deterministic ordered control events:
  - `runtime.workflow.state_changed`
  - `runtime.workflow.running`
  - `runtime.workflow.pausing`
  - `runtime.workflow.paused`
  - `runtime.workflow.resuming`
  - `runtime.workflow.resumed`
- Verified cancel while paused emits cancelling/cancelled events without a resumed progress event.
- Verified completed and failed progress events are classified correctly by `RuntimeEvent.is_terminal` and `RuntimeEvent.is_error`.
- Verified event envelopes preserve execution ID, workflow ID/runtime ID metadata, serialized state, previous state, reason, and requested-by attribution.

### Validation completed

- Unit tests passed:
  - `python -m pytest tests/unit/runtime/control/test_workflow_control_manager.py tests/unit/runtime/control/test_workflow_control_events.py`
  - Result: `17 passed`
- Ruff checks passed:
  - `python -m ruff check core/runtime/control core/runtime/events tests/unit/runtime/control`
  - Result: `All checks passed!`

### Architectural note

This step keeps event verification at the runtime-control unit boundary. Runtime-engine integration of the control manager remains intentionally deferred to Step 13.

## Step 13 Results — RuntimeEngine Control Manager Constructor Wiring

Step 13 was completed as a narrow RuntimeEngine constructor integration.

### Files updated

- `core/runtime/execution/runtime_engine.py`
- `tests/unit/runtime/execution/test_runtime_engine_control_manager.py`
- `.agent/plans/plan_workflow_control_plus_notifications.md`

### Implementation results

- Added `WorkflowControlManager` as an optional constructor dependency on `RuntimeEngine`:
  - `control_manager: WorkflowControlManager | None = None`
- Added `self.control_manager` to `RuntimeEngine`.
- RuntimeEngine now creates a default `WorkflowControlManager()` when no manager is injected.
- RuntimeEngine preserves injected manager identity when a manager is supplied.
- No execution-loop behavior was changed in this step; runtime initialization and terminal marking remain deferred to Step 14.

### Validation completed

- Unit tests passed:
  - `python -m pytest tests/unit/runtime/execution/test_runtime_engine_control_manager.py tests/unit/runtime/control/test_workflow_control_manager.py tests/unit/runtime/control/test_workflow_control_events.py`
  - Result: `19 passed`
- Ruff checks passed:
  - `python -m ruff check core/runtime/execution/runtime_engine.py core/runtime/control tests/unit/runtime/execution/test_runtime_engine_control_manager.py tests/unit/runtime/control`
  - Result: `All checks passed!`

### Architectural note

This step keeps the control manager as a core runtime dependency without yet changing workflow execution semantics. The next step can safely initialize and mark control state during execution using the manager already attached to RuntimeEngine.

## Step 14 Results — Runtime Control Initialization and Terminal Marking

Step 14 was completed as RuntimeEngine execution lifecycle wiring.

### Files updated

- `core/runtime/execution/runtime_engine.py`
- `tests/unit/runtime/execution/test_runtime_engine_control_manager.py`
- `.agent/plans/plan_workflow_control_plus_notifications.md`

### Implementation results

- RuntimeEngine now initializes control state at workflow execution start:
  - `initialize_execution(...)`
  - `mark_running(...)`
- RuntimeEngine now marks terminal control state after workflow execution completes:
  - `mark_completed(...)` when execution finishes without runtime failures
  - `mark_failed(...)` when node/runtime outputs leave failed errors in the final context
- RuntimeEngine now marks control state failed and re-raises if execution raises an exception after control initialization.
- Added `_control_metadata(...)` so control events include workflow/runtime execution metadata.
- Added `_has_execution_failure(...)` to classify terminal failed executions from final runtime context.
- No pause/resume/cancel safe-boundary checks were added in this step; those remain deferred to later steps.

### Validation completed

- Unit tests passed:
  - `python -m pytest tests/unit/runtime/execution/test_runtime_engine_control_manager.py tests/unit/runtime/control/test_workflow_control_manager.py tests/unit/runtime/control/test_workflow_control_events.py`
  - Result: `21 passed`
- Ruff checks passed:
  - `python -m ruff check core/runtime/execution/runtime_engine.py core/runtime/control tests/unit/runtime/execution/test_runtime_engine_control_manager.py tests/unit/runtime/control`
  - Result: `All checks passed!`

### Architectural note

This step wires workflow lifecycle state into the core RuntimeEngine without changing control behavior at wave or node boundaries. It keeps control state authoritative in the runtime trunk while preserving existing execution semantics until explicit pause/cancel boundary steps are implemented.

## Step 15 Results — Pause Checks Before Waves

Step 15 was completed as a cooperative safe-boundary pause check in the RuntimeEngine wave loop.

### Files updated

- `core/runtime/execution/runtime_engine.py`
- `tests/unit/runtime/execution/test_runtime_engine_control_manager.py`
- `.agent/plans/plan_workflow_control_plus_notifications.md`

### Implementation results

- Added a control-manager pause wait before each execution wave:
  - `await self.control_manager.wait_if_paused(execution_plan.execution_id)`
- Pause remains cooperative and safe-boundary based. Active nodes are not interrupted.
- A pause requested during one wave is observed before the next wave starts.
- Added runtime-engine unit coverage proving a pause request after wave 0 prevents wave 1 from starting until resume is requested.
- No cancel checks or node-boundary checks were added in this step; those remain deferred to later steps.

### Validation completed

- Unit tests passed:
  - `python -m pytest tests/unit/runtime/execution/test_runtime_engine_control_manager.py tests/unit/runtime/control/test_workflow_control_manager.py tests/unit/runtime/control/test_workflow_control_events.py`
  - Result: `22 passed`
- Ruff checks passed:
  - `python -m ruff check core/runtime/execution/runtime_engine.py core/runtime/control tests/unit/runtime/execution/test_runtime_engine_control_manager.py tests/unit/runtime/control`
  - Result: `All checks passed!`

### Architectural note

This step adds the first runtime safe-boundary control behavior without changing node execution semantics. Workflow pause remains owned by the runtime trunk rather than individual nodes.

## Step 16 Results — Pause/Resume Integration Test

Step 16 was completed as a runtime integration test for cooperative pause/resume behavior across workflow waves.

### Files updated

- `tests/integration/runtime/test_workflow_pause_resume.py`
- `.agent/plans/plan_workflow_control_plus_notifications.md`

### Implementation results

- Added an integration test using real `RuntimeEngine`, `WorkflowControlManager`, and `EventBus`.
- The test runs a two-wave workflow where the first wave is externally paused while its node is still active.
- Verified the runtime observes the pause before the second wave starts.
- Verified the second wave does not execute while the workflow is paused.
- Verified external resume releases the workflow and allows the second wave to complete.
- Verified final control state becomes `COMPLETED`.
- Verified emitted control/progress events include pause, paused, resume, resumed, and completed progress events.

### Validation completed

- Integration/unit regression tests passed:
  - `python -m pytest tests/integration/runtime/test_workflow_pause_resume.py tests/unit/runtime/execution/test_runtime_engine_control_manager.py tests/unit/runtime/control/test_workflow_control_manager.py tests/unit/runtime/control/test_workflow_control_events.py`
  - Result: `23 passed`
- Ruff checks passed:
  - `python -m ruff check core/runtime/execution/runtime_engine.py core/runtime/control tests/integration/runtime/test_workflow_pause_resume.py tests/unit/runtime/execution/test_runtime_engine_control_manager.py tests/unit/runtime/control`
  - Result: `All checks passed!`

### Architectural note

This integration test validates the intended external-control path at the runtime boundary without introducing facade or CLI control APIs ahead of their planned steps.

## Step 17 Results — Cancel Checks Before Waves

Step 17 was completed as a cooperative safe-boundary cancel check in the RuntimeEngine wave loop.

### Files updated

- `core/runtime/execution/runtime_engine.py`
- `tests/unit/runtime/execution/test_runtime_engine_control_manager.py`
- `.agent/plans/plan_workflow_control_plus_notifications.md`

### Implementation results

- Added a cancel check after the pause wait and before each wave starts.
- When cancellation is requested at a wave boundary, RuntimeEngine now marks the workflow `CANCELLED` and stops before starting the next wave.
- Added terminal guard logic so cancelled executions are not overwritten as completed or failed by the existing terminal marker.
- Added runtime-engine unit coverage proving a cancel request after wave 0 prevents wave 1 from starting and leaves control state as `CANCELLED`.
- Cancel result-model metadata semantics are still deferred to Step 22.

### Validation completed

- Integration/unit regression tests passed:
  - `python -m pytest tests/integration/runtime/test_workflow_pause_resume.py tests/unit/runtime/execution/test_runtime_engine_control_manager.py tests/unit/runtime/control/test_workflow_control_manager.py tests/unit/runtime/control/test_workflow_control_events.py`
  - Result: `24 passed`
- Ruff checks passed:
  - `python -m ruff check core/runtime/execution/runtime_engine.py core/runtime/control tests/integration/runtime/test_workflow_pause_resume.py tests/unit/runtime/execution/test_runtime_engine_control_manager.py tests/unit/runtime/control`
  - Result: `All checks passed!`

### Architectural note

This step keeps cancellation cooperative and runtime-owned. Active nodes are allowed to finish, and cancellation is applied at the safe wave boundary before additional work begins.

## Step 18 Results — Cancel Integration Test

Step 18 was completed as a runtime integration test for cooperative cancellation before the next workflow wave.

### Files updated

- `tests/integration/runtime/test_workflow_cancel.py`
- `.agent/plans/plan_workflow_control_plus_notifications.md`

### Implementation results

- Added an integration test using real `RuntimeEngine`, `WorkflowControlManager`, and `EventBus`.
- The test runs a two-wave workflow where cancellation is requested externally while the first wave node is still active.
- Verified the first active node is allowed to finish.
- Verified the runtime observes cancellation before the second wave starts.
- Verified the second wave does not execute after cancellation.
- Verified final control state becomes `CANCELLED`.
- Verified cancel metadata includes the safe boundary and wave index.
- Verified emitted events include cancelling/cancelled progress events and do not include completed/failed progress events.

### Validation completed

- Integration/unit regression tests passed:
  - `python -m pytest tests/integration/runtime/test_workflow_cancel.py tests/integration/runtime/test_workflow_pause_resume.py tests/unit/runtime/execution/test_runtime_engine_control_manager.py tests/unit/runtime/control/test_workflow_control_manager.py tests/unit/runtime/control/test_workflow_control_events.py`
  - Result: `25 passed`
- Ruff checks passed:
  - `python -m ruff check core/runtime/execution/runtime_engine.py core/runtime/control tests/integration/runtime/test_workflow_cancel.py tests/integration/runtime/test_workflow_pause_resume.py tests/unit/runtime/execution/test_runtime_engine_control_manager.py tests/unit/runtime/control`
  - Result: `All checks passed!`

### Architectural note

This integration test confirms cancellation is cooperative, safe-boundary based, and externally observable through the runtime event bus. Result-model cancellation semantics remain deferred to Step 22.



## Step 19 Results — Node-Boundary Pause/Cancel Checks

Step 19 was completed as cooperative node-boundary pause/cancel enforcement inside `RuntimeEngine`.

### Files updated

- `core/runtime/execution/runtime_engine.py`
- `tests/unit/runtime/execution/test_runtime_engine_control_manager.py`
- `tests/integration/runtime/test_workflow_cancel.py`
- `.agent/plans/plan_workflow_control_plus_notifications.md`

### Implementation results

- Added pause waits before each node is scheduled.
- Added pause waits after each node output is applied.
- Added cancel checks before each node is scheduled.
- Added cancel checks after each node output is applied.
- Extracted `_mark_cancelled_if_requested(...)` so wave and node boundaries share one cancellation path.
- Added cancellation metadata for node boundaries:
  - `cancel_boundary`
  - `wave_index`
  - `node_name` when available
- Updated active-node cancellation expectations to reflect the more precise `after_node` boundary instead of deferring all cancellation to the next wave.
- Added unit coverage proving a pause requested at a node boundary prevents the next same-wave node from starting until resume.
- Added unit coverage proving a cancel requested at a node boundary prevents the next same-wave node from starting.
- No explicit runtime wave/node progress event emission was added in this step; that remains Step 20.

### Validation completed

- Unit tests passed:
  - `python -m pytest tests/unit/runtime/execution/test_runtime_engine_control_manager.py tests/unit/runtime/control/test_workflow_control_manager.py tests/unit/runtime/control/test_workflow_control_events.py`
  - Result: `25 passed`
- Integration/unit regression tests passed:
  - `python -m pytest tests/integration/runtime/test_workflow_cancel.py tests/integration/runtime/test_workflow_pause_resume.py tests/unit/runtime/execution/test_runtime_engine_control_manager.py tests/unit/runtime/control/test_workflow_control_manager.py tests/unit/runtime/control/test_workflow_control_events.py`
  - Result: `27 passed`
- Ruff checks passed:
  - `python -m ruff check core/runtime/execution/runtime_engine.py core/runtime/control tests/integration/runtime/test_workflow_cancel.py tests/integration/runtime/test_workflow_pause_resume.py tests/unit/runtime/execution/test_runtime_engine_control_manager.py tests/unit/runtime/control`
  - Result: `All checks passed!`

### Architectural note

This step preserves cooperative safe-boundary semantics: active nodes are allowed to finish, while pause/cancel requests are honored before additional same-wave or next-wave work begins. Runtime control remains centralized in the runtime trunk rather than leaking into individual business nodes.


## Step 20 Results — Runtime Progress Event Emission

Step 20 was completed as direct runtime emission of workflow, wave, and node progress events through the canonical `EventBus`.

### Files updated

- `core/runtime/control/workflow_control_manager.py`
- `core/runtime/execution/runtime_engine.py`
- `tests/unit/runtime/execution/test_runtime_engine_control_manager.py`
- `.agent/plans/plan_workflow_control_plus_notifications.md`

### Implementation results

- Added a read-only `WorkflowControlManager.event_bus` property so runtime components can share the manager's canonical bus without reaching into private state.
- Added optional `event_bus` injection to `RuntimeEngine`.
- When `RuntimeEngine` is created without an explicit control manager, it now creates a default `WorkflowControlManager(event_bus=event_bus)` so control-state events and runtime progress events use the same bus.
- When `RuntimeEngine` is created with an injected control manager, it uses the injected `event_bus` or falls back to `control_manager.event_bus`.
- Added runtime progress emission helper `_emit_progress_event(...)` with the canonical `RuntimeEvent` envelope.
- Added workflow start progress emission:
  - `runtime.workflow.started`
- Added wave progress emission:
  - `runtime.workflow.wave.started`
  - `runtime.workflow.wave.completed`
  - `runtime.workflow.wave.failed`
- Added node progress emission:
  - `runtime.node.started`
  - `runtime.node.running`
  - `runtime.node.completed`
  - `runtime.node.failed`
- Progress payloads include workflow IDs, execution ID, runtime ID, current control state, node/wave location, timestamp, state version, and metadata.
- Added unit coverage for successful runtime progress events.
- Added unit coverage for failed node/wave runtime progress events.
- Full integration progress sequencing remains deferred to Step 21.

### Validation completed

- Unit tests passed:
  - `python -m pytest tests/unit/runtime/execution/test_runtime_engine_control_manager.py tests/unit/runtime/control/test_workflow_control_manager.py tests/unit/runtime/control/test_workflow_control_events.py`
  - Result: `27 passed`
- Integration/unit regression tests passed:
  - `python -m pytest tests/integration/runtime/test_workflow_cancel.py tests/integration/runtime/test_workflow_pause_resume.py tests/unit/runtime/execution/test_runtime_engine_control_manager.py tests/unit/runtime/control/test_workflow_control_manager.py tests/unit/runtime/control/test_workflow_control_events.py`
  - Result: `29 passed`
- Ruff checks passed:
  - `python -m ruff check core/runtime/execution/runtime_engine.py core/runtime/control tests/integration/runtime/test_workflow_cancel.py tests/integration/runtime/test_workflow_pause_resume.py tests/unit/runtime/execution/test_runtime_engine_control_manager.py tests/unit/runtime/control`
  - Result: `All checks passed!`

### Architectural note

Runtime progress notifications now flow through the same EventBus path as workflow control state changes. This keeps external observers, including the future CLI progress subscriber, decoupled from runtime internals and prevents log-scraping or parallel progress channels.


## Step 21 Results — Progress Event Integration Test

Step 21 was completed as an integration test for externally observable workflow, wave, and node progress events.

### Files updated

- `core/runtime/control/workflow_control_manager.py`
- `tests/integration/runtime/test_workflow_progress_events.py`
- `.agent/plans/plan_workflow_control_plus_notifications.md`

### Implementation results

- Added `tests/integration/runtime/test_workflow_progress_events.py`.
- The new integration test runs a real two-wave workflow through `RuntimeEngine` with a real `EventBus` subscriber.
- Verified `RuntimeEngine(event_bus=event_bus)` wires its default `WorkflowControlManager` to the same bus.
- Verified ordered external progress events across the full successful workflow path:
  - `runtime.workflow.started`
  - `runtime.workflow.running`
  - `runtime.workflow.wave.started`
  - `runtime.node.started`
  - `runtime.node.running`
  - `runtime.node.completed`
  - `runtime.workflow.wave.completed`
  - repeated wave/node progress for the second wave
  - `runtime.workflow.completed`
- Verified progress event envelopes include execution ID, workflow ID, runtime ID, node name, wave index, and payload metadata needed by future CLI subscribers.
- Verified wave progress payloads include `wave_nodes`.
- Verified node progress payloads include `node_type`.
- Enhanced manager-emitted workflow control progress payloads with the same standard top-level progress fields:
  - `workflow_id`
  - `workflow_name`
  - `execution_id`
  - `runtime_id`
  - `state`
  - `node_name`
  - `wave_index`
  - `timestamp`
  - `state_version`
  - `metadata`
- Preserved the existing serialized `WorkflowControlSnapshot` payload fields and `previous_state` attribution.

### Validation completed

- New integration test passed:
  - `python -m pytest tests/integration/runtime/test_workflow_progress_events.py`
  - Result: `1 passed`
- Integration/unit regression tests passed:
  - `python -m pytest tests/integration/runtime/test_workflow_progress_events.py tests/integration/runtime/test_workflow_cancel.py tests/integration/runtime/test_workflow_pause_resume.py tests/unit/runtime/execution/test_runtime_engine_control_manager.py tests/unit/runtime/control/test_workflow_control_manager.py tests/unit/runtime/control/test_workflow_control_events.py`
  - Result: `30 passed`
- Ruff checks passed:
  - `python -m ruff check core/runtime/execution/runtime_engine.py core/runtime/control tests/integration/runtime/test_workflow_progress_events.py tests/integration/runtime/test_workflow_cancel.py tests/integration/runtime/test_workflow_pause_resume.py tests/unit/runtime/execution/test_runtime_engine_control_manager.py tests/unit/runtime/control`
  - Result: `All checks passed!`

### Architectural note

This step validates the event-driven external progress contract through the real runtime boundary. CLI and other observers can now subscribe to the canonical EventBus instead of scraping logs or inspecting private runtime state.

## Step 22 Results — Cancelled Workflow Result Semantics

Step 22 was completed as an explicit runtime cancellation result contract that keeps cooperative cancellation distinct from workflow failure.

### Files updated

- `core/runtime/execution/runtime_engine.py`
- `tests/unit/runtime/execution/test_runtime_engine_control_manager.py`
- `tests/integration/runtime/test_workflow_cancel.py`
- `.agent/plans/plan_workflow_control_plus_notifications.md`

### Implementation results

- Added a canonical synthetic runtime output key:
  - `workflow_control.cancelled`
- Cancellation now writes an explicit serialized runtime output when the runtime observes cancellation at a safe boundary.
- The cancellation output includes:
  - `success: false`
  - `stop_propagation: true`
  - `cancelled: true`
  - `status: cancelled`
  - `reason`
  - `requested_by`
  - `cancel_boundary`
  - `wave_index` when available
  - `node_name` when available
- Cancellation remains non-error semantics:
  - `errors` remains empty for intentional cancellation.
  - Completed node outputs remain available in `RuntimeContext.node_outputs`.
  - Remaining nodes are not executed after cancellation is observed.
  - The synthetic cancellation output is excluded from failed-node classification.
- Refactored the previous boolean-only cancellation marker into a context-returning helper so the runtime can atomically add the cancellation result before marking the control state `CANCELLED`.
- Cancellation control snapshot metadata now also includes:
  - `cancelled: true`
  - `status: cancelled`
  - final cancellation boundary attribution

### Validation completed

- Targeted cancellation tests passed:
  - `python -m pytest tests/unit/runtime/execution/test_runtime_engine_control_manager.py tests/integration/runtime/test_workflow_cancel.py`
  - Result: `11 passed`
- Runtime control/progress regression tests passed:
  - `python -m pytest tests/integration/runtime/test_workflow_progress_events.py tests/integration/runtime/test_workflow_cancel.py tests/integration/runtime/test_workflow_pause_resume.py tests/unit/runtime/execution/test_runtime_engine_control_manager.py tests/unit/runtime/control/test_workflow_control_manager.py tests/unit/runtime/control/test_workflow_control_events.py`
  - Result: `30 passed`
- Ruff checks passed:
  - `python -m ruff check core/runtime/execution/runtime_engine.py core/runtime/control tests/integration/runtime/test_workflow_progress_events.py tests/integration/runtime/test_workflow_cancel.py tests/integration/runtime/test_workflow_pause_resume.py tests/unit/runtime/execution/test_runtime_engine_control_manager.py tests/unit/runtime/control`
  - Result: `All checks passed!`
- Mypy was attempted on the changed runtime/test files, but the local environment does not currently have `mypy` installed:
  - `python -m mypy core/runtime/execution/runtime_engine.py tests/unit/runtime/execution/test_runtime_engine_control_manager.py tests/integration/runtime/test_workflow_cancel.py`
  - Result: `No module named mypy`
- Code graph updated:
  - `GRAPHIFY_VIZ_NODE_LIMIT=6000 graphify update .`
  - Result: graph updated successfully.

### Architectural note

Cancellation is now represented as an explicit runtime boundary result instead of an implicit early return. This preserves replayability and inspectability while keeping intentional cancellation separate from execution failure.

## Step 23 Results — WorkflowFacade Control Manager Wiring

Step 23 was completed by making `WorkflowFacade` own the runtime control surface and share the same `WorkflowControlManager` instance with `RuntimeEngine`. Mypy was also installed into the project environment and added to project dependency manifests.

### Files updated

- `core/workflow/execution/workflow_facade.py`
- `tests/unit/workflow/test_workflow_facade_control.py`
- `pyproject.toml`
- `requirements.txt`
- `.agent/plans/plan_workflow_control_plus_notifications.md`

### Implementation results

- Added `WorkflowControlManager`, `WorkflowControlSnapshot`, and `WorkflowControlState` to the facade layer contract.
- Added optional `workflow_control_manager` injection to `WorkflowFacade.__init__(...)` and `WorkflowFacade.create(...)`.
- `WorkflowFacade.create(...)` now creates a default `WorkflowControlManager(event_bus=final_event_bus)` when one is not injected.
- `WorkflowFacade.create(...)` now passes the shared control manager and event bus into `RuntimeEngine`, preventing a split-brain control state between facade and runtime.
- Stored the manager on `facade.workflow_control_manager`.
- Added async facade control APIs aligned with the async runtime/control architecture:
  - `pause_workflow(...)`
  - `resume_workflow(...)`
  - `cancel_workflow(...)`
- Added read APIs:
  - `get_workflow_state(...)`
  - `get_workflow_control_snapshot(...)`
- Added a clear runtime guard if a facade instance is constructed without a workflow control manager.
- Installed `mypy` into the local project environment.
- Added `mypy` to both dependency manifests:
  - `pyproject.toml`
  - `requirements.txt`

### Validation completed

- New facade control tests passed:
  - `python -m pytest tests/unit/workflow/test_workflow_facade_control.py`
  - Result: `3 passed`
- Runtime/facade regression tests passed:
  - `python -m pytest tests/unit/workflow/test_workflow_facade_control.py tests/integration/runtime/test_workflow_progress_events.py tests/integration/runtime/test_workflow_cancel.py tests/integration/runtime/test_workflow_pause_resume.py tests/unit/runtime/execution/test_runtime_engine_control_manager.py tests/unit/runtime/control/test_workflow_control_manager.py tests/unit/runtime/control/test_workflow_control_events.py`
  - Result: `33 passed`
- Ruff checks passed:
  - `python -m ruff check core/workflow/execution/workflow_facade.py core/runtime/execution/runtime_engine.py core/runtime/control tests/unit/workflow/test_workflow_facade_control.py tests/integration/runtime/test_workflow_progress_events.py tests/integration/runtime/test_workflow_cancel.py tests/integration/runtime/test_workflow_pause_resume.py tests/unit/runtime/execution/test_runtime_engine_control_manager.py tests/unit/runtime/control`
  - Result: `All checks passed!`
- Mypy installed successfully:
  - `python -m pip install mypy`
  - Installed version: `2.1.0`
- Direct mypy invocation required `--explicit-package-bases` because the repository root has an `__init__.py` while the project name contains hyphens.
- Targeted mypy on changed files passed with imported dependencies skipped:
  - `python -m mypy --explicit-package-bases --follow-imports=skip core/workflow/execution/workflow_facade.py core/runtime/execution/runtime_engine.py tests/unit/workflow/test_workflow_facade_control.py tests/unit/runtime/execution/test_runtime_engine_control_manager.py tests/integration/runtime/test_workflow_cancel.py`
  - Result: `Success: no issues found in 5 source files`
- Full import-following targeted mypy surfaced pre-existing unrelated errors outside this step's files:
  - `core/runtime/policies/policy_engine.py`
  - `core/runtime/governance/governance_engine.py`
  - `core/runtime/artifacts/artifact_serializers.py`
- Code graph updated:
  - `GRAPHIFY_VIZ_NODE_LIMIT=6000 graphify update .`
  - Result: graph updated successfully.

### Architectural note

`WorkflowFacade` is now the application boundary for workflow control requests, while `RuntimeEngine` remains the execution authority that cooperatively observes pause/cancel state. Both layers share one canonical control manager instance, preserving runtime-first ownership without forcing callers to bypass the facade.

## Step 24 Results — WorkflowBootstrap Control Manager Wiring

Step 24 was completed by promoting `WorkflowControlManager` to a first-class `WorkflowBootstrap` dependency and exposing the composed manager through the bootstrap result.

### Files updated

- `core/workflow/bootstrap/workflow_bootstrap.py`
- `tests/integration/workflow/test_workflow_bootstrap.py`
- `.agent/plans/plan_workflow_control_plus_notifications.md`

### Implementation results

- Added `WorkflowControlManager` wiring to `WorkflowBootstrap`.
- Added optional `workflow_control_manager` injection to `WorkflowBootstrap.__init__(...)`.
- `WorkflowBootstrap` now creates a default `WorkflowControlManager(event_bus=self.event_bus)` when one is not injected.
- Added `workflow_control_manager` to `WorkflowBootstrapResult` so composed applications can access the canonical workflow control surface.
- `WorkflowBootstrap` now passes the shared manager into `WorkflowFacade.create(...)`.
- Updated both bootstrap helper boundaries to accept and forward the manager:
  - `build_workflow_runtime(...)`
  - `build_workflow_runtime_async(...)`
- Added bootstrap integration tests for default and injected manager wiring.
- Verified the async bootstrap helper preserves facade delegation by pausing a workflow through the facade and reading the state from the bootstrap-owned manager.

### Validation completed

- Bootstrap/facade control tests passed:
  - `python -m pytest tests/integration/workflow/test_workflow_bootstrap.py tests/unit/workflow/test_workflow_facade_control.py`
  - Result: `6 passed`
- Runtime/control/facade regression tests passed:
  - `python -m pytest tests/integration/workflow/test_workflow_bootstrap.py tests/unit/workflow/test_workflow_facade_control.py tests/integration/runtime/test_workflow_progress_events.py tests/integration/runtime/test_workflow_cancel.py tests/integration/runtime/test_workflow_pause_resume.py tests/unit/runtime/execution/test_runtime_engine_control_manager.py tests/unit/runtime/control/test_workflow_control_manager.py tests/unit/runtime/control/test_workflow_control_events.py`
  - Result: `36 passed`
- Ruff checks passed:
  - `python -m ruff check core/workflow/bootstrap/workflow_bootstrap.py core/workflow/execution/workflow_facade.py core/runtime/execution/runtime_engine.py core/runtime/control tests/integration/workflow/test_workflow_bootstrap.py tests/unit/workflow/test_workflow_facade_control.py tests/integration/runtime/test_workflow_progress_events.py tests/integration/runtime/test_workflow_cancel.py tests/integration/runtime/test_workflow_pause_resume.py tests/unit/runtime/execution/test_runtime_engine_control_manager.py tests/unit/runtime/control`
  - Result: `All checks passed!`
- Targeted mypy passed with imported dependencies skipped:
  - `python -m mypy --explicit-package-bases --follow-imports=skip core/workflow/bootstrap/workflow_bootstrap.py core/workflow/execution/workflow_facade.py core/runtime/execution/runtime_engine.py tests/integration/workflow/test_workflow_bootstrap.py tests/unit/workflow/test_workflow_facade_control.py`
  - Result: `Success: no issues found in 5 source files`
- Code graph updated:
  - `GRAPHIFY_VIZ_NODE_LIMIT=6000 graphify update .`
  - Result: graph updated successfully.

### Architectural note

`WorkflowBootstrap` is now the composition root for workflow control. Facade callers, runtime execution, and external progress subscribers can share one control manager and one EventBus without bypassing the bootstrap/facade boundary or creating split-brain workflow state.

## Step 25 Results — Dishka Provider Control Manager Wiring

Step 25 was completed by making `WorkflowControlManager` a first-class Dishka-provided workflow infrastructure dependency and sharing it with `WorkflowFacade`.

### Files updated

- `core/bootstrap/workflow_providers.py`
- `tests/integration/workflow/test_workflow_provider_control.py`
- `.agent/plans/plan_workflow_control_plus_notifications.md`

### Implementation results

- Added `WorkflowControlManager` to `WorkflowInfrastructureProvider`.
- Added a provider method:
  - `provide_workflow_control_manager(event_bus: EventBus) -> WorkflowControlManager`
- The Dishka-provided control manager is constructed with the same APP-scoped `EventBus` as the rest of workflow infrastructure.
- Updated `provide_workflow_facade(...)` to require the Dishka-provided `WorkflowControlManager`.
- `WorkflowInfrastructureProvider` now passes the shared manager into `WorkflowFacade.create(...)`.
- Added provider integration coverage proving:
  - `WorkflowControlManager` resolves from the Dishka container.
  - The resolved manager uses the container's canonical `EventBus`.
  - `WorkflowFacade` and `RuntimeEngine` receive the same manager instance.
  - Facade control APIs mutate the provider-owned manager state.

### Validation completed

- Provider/bootstrap/facade wiring tests passed:
  - `python -m pytest tests/integration/workflow/test_workflow_provider_control.py tests/integration/workflow/test_workflow_bootstrap.py tests/unit/workflow/test_workflow_facade_control.py tests/integration/governance/test_bootstrap_governance_provider.py`
  - Result: `11 passed`
- Runtime/control/Dishka regression tests passed:
  - `python -m pytest tests/integration/workflow/test_workflow_provider_control.py tests/integration/workflow/test_workflow_bootstrap.py tests/unit/workflow/test_workflow_facade_control.py tests/integration/workflow/test_dishka_workflow.py tests/integration/runtime/test_workflow_progress_events.py tests/integration/runtime/test_workflow_cancel.py tests/integration/runtime/test_workflow_pause_resume.py tests/unit/runtime/execution/test_runtime_engine_control_manager.py tests/unit/runtime/control/test_workflow_control_manager.py tests/unit/runtime/control/test_workflow_control_events.py tests/integration/governance/test_bootstrap_governance_provider.py`
  - Result: `42 passed`
- Ruff checks passed:
  - `python -m ruff check core/bootstrap/workflow_providers.py core/workflow/bootstrap/workflow_bootstrap.py core/workflow/execution/workflow_facade.py core/runtime/execution/runtime_engine.py core/runtime/control tests/integration/workflow/test_workflow_provider_control.py tests/integration/workflow/test_workflow_bootstrap.py tests/unit/workflow/test_workflow_facade_control.py tests/integration/workflow/test_dishka_workflow.py tests/integration/runtime/test_workflow_progress_events.py tests/integration/runtime/test_workflow_cancel.py tests/integration/runtime/test_workflow_pause_resume.py tests/unit/runtime/execution/test_runtime_engine_control_manager.py tests/unit/runtime/control tests/integration/governance/test_bootstrap_governance_provider.py`
  - Result: `All checks passed!`
- Targeted mypy passed with imported dependencies skipped:
  - `python -m mypy --explicit-package-bases --follow-imports=skip core/bootstrap/workflow_providers.py core/workflow/bootstrap/workflow_bootstrap.py core/workflow/execution/workflow_facade.py core/runtime/execution/runtime_engine.py tests/integration/workflow/test_workflow_provider_control.py tests/integration/workflow/test_workflow_bootstrap.py tests/unit/workflow/test_workflow_facade_control.py`
  - Result: `Success: no issues found in 7 source files`
- Code graph updated:
  - `GRAPHIFY_VIZ_NODE_LIMIT=6000 graphify update .`
  - Result: graph updated successfully.

### Architectural note

The Dishka composition path now matches the direct bootstrap path: workflow control is composed once at the infrastructure boundary, then shared by facade and runtime. This prevents split-brain control state for DI-created CLI/application runtimes and keeps external progress/control observers on the canonical EventBus.



## Step 26 Results — CLI Async Command-Service Foundation

Step 26 was completed by moving workflow execution behavior behind a typed async CLI command-service layer while keeping Typer as the process/argument boundary.

### Files updated

- `interfaces/cli/services/__init__.py`
- `interfaces/cli/services/async_runner.py`
- `interfaces/cli/services/workflow_command_service.py`
- `interfaces/cli/commands/workflow_command.py`
- `interfaces/cli/commands/morning_report_command.py`
- `tests/unit/interfaces/cli/test_workflow_command_service.py`
- `tests/unit/interfaces/cli/test_workflow_rendering.py`
- `.agent/plans/plan_workflow_control_plus_notifications.md`

### Implementation results

- Added a CLI service package for workflow command execution.
- Added `run_cli_async(...)` as the single small synchronous Typer-to-async runner boundary.
- Added typed frozen/slotted command-service request models:
  - `WorkflowRunCommandRequest`
  - `MorningReportCommandRequest`
- Added `WorkflowCommandService` with async methods:
  - `run_workflow(...)`
  - `run_morning_report(...)`
- Moved async runtime construction, workflow registration checks, facade execution, and render-envelope conversion behind the command service.
- Kept Typer command functions responsible for CLI-only concerns:
  - argument parsing
  - output-format validation
  - output file writing
  - process exit code selection
- Preserved always-render behavior by returning `WorkflowRenderEnvelope` for both successful workflow results and command/runtime exceptions.
- Updated `polaris workflow run ...` to use `WorkflowCommandService.run_workflow(...)`.
- Updated `polaris morning-report ...` to use `WorkflowCommandService.run_morning_report(...)`.
- Did not implement progress subscription in this step; that remains isolated for Step 27.

### Validation completed

- CLI/service/rendering tests passed:
  - `python -m pytest tests/unit/interfaces/cli/test_workflow_command_service.py tests/unit/interfaces/cli/test_workflow_rendering.py tests/unit/interfaces/cli/test_cli.py`
  - Result: `19 passed`
- Morning-report real-node integration test passed:
  - `python -m pytest tests/integration/workflow/test_morning_report_real_nodes.py`
  - Result: `1 passed`
- Combined targeted regression passed:
  - `python -m pytest tests/unit/interfaces/cli/test_workflow_command_service.py tests/unit/interfaces/cli/test_workflow_rendering.py tests/unit/interfaces/cli/test_cli.py tests/integration/workflow/test_morning_report_real_nodes.py`
  - Result: `20 passed`
- Ruff checks passed:
  - `python -m ruff check interfaces/cli/commands/workflow_command.py interfaces/cli/commands/morning_report_command.py interfaces/cli/services tests/unit/interfaces/cli/test_workflow_command_service.py tests/unit/interfaces/cli/test_workflow_rendering.py tests/unit/interfaces/cli/test_cli.py`
  - Result: `All checks passed!`
- Targeted mypy passed with imported dependencies skipped:
  - `python -m mypy --explicit-package-bases --follow-imports=skip interfaces/cli/commands/workflow_command.py interfaces/cli/commands/morning_report_command.py interfaces/cli/services tests/unit/interfaces/cli/test_workflow_command_service.py`
  - Result: `Success: no issues found in 6 source files`
- Code graph updated:
  - `GRAPHIFY_VIZ_NODE_LIMIT=6000 graphify update .`
  - Result: graph updated successfully.

### Architectural note

The CLI now follows the runtime architecture more closely without replacing Typer: command functions remain thin boundary adapters, while workflow execution lives in async command services that call the canonical `WorkflowFacade` through the bootstrapped runtime. This creates the extension seam needed for Step 27 progress notifications without adding a parallel execution path.


## Step 27 Results — CLI Progress Subscription Service

Step 27 was completed by adding a typed CLI progress subscription service that observes the canonical runtime `EventBus` and forwards workflow/node progress notifications to optional CLI handlers.

### Files updated

- `interfaces/cli/services/workflow_progress_service.py`
- `interfaces/cli/services/workflow_command_service.py`
- `interfaces/cli/services/__init__.py`
- `interfaces/cli/commands/workflow_command.py`
- `interfaces/cli/commands/morning_report_command.py`
- `tests/unit/interfaces/cli/test_workflow_progress_service.py`
- `tests/unit/interfaces/cli/test_workflow_command_service.py`
- `.agent/plans/plan_workflow_control_plus_notifications.md`

### Implementation results

- Added typed progress notification models and subscription service:
  - `WorkflowProgressNotification`
  - `WorkflowProgressSubscriptionRequest`
  - `WorkflowProgressSubscription`
  - `ProgressNotificationHandler`
- Added conversion from runtime events to CLI progress notifications:
  - `progress_notification_from_event(...)`
- Added console-safe progress rendering:
  - `format_workflow_progress_notification(...)`
- Progress subscriptions use the existing runtime `EventBus.subscribe_all(...)` / `unsubscribe_all(...)` APIs.
- Progress filtering is scoped to external progress/control events:
  - `runtime.workflow.*`
  - `runtime.node.*`
- Updated `WorkflowCommandService` so optional progress handlers subscribe after runtime bootstrap and before facade execution.
- Ensured subscriptions are removed in `finally`, preventing stale CLI subscribers after success, failure, or registration errors.
- Added optional CLI flags:
  - `polaris workflow run ... --progress`
  - `polaris morning-report ... --progress`
- Progress output is written to stderr so existing stdout rendering remains stable for console/json/markdown and file-output workflows.
- Default command output behavior remains unchanged when `--progress` is not supplied.

### Validation completed

- Progress/service tests passed:
  - `python -m pytest tests/unit/interfaces/cli/test_workflow_progress_service.py tests/unit/interfaces/cli/test_workflow_command_service.py`
  - Result: `7 passed`
- CLI/service/rendering regression tests passed:
  - `python -m pytest tests/unit/interfaces/cli/test_workflow_progress_service.py tests/unit/interfaces/cli/test_workflow_command_service.py tests/unit/interfaces/cli/test_workflow_rendering.py tests/unit/interfaces/cli/test_cli.py tests/integration/workflow/test_morning_report_real_nodes.py`
  - Result: `24 passed`
- Ruff checks passed:
  - `python -m ruff check interfaces/cli/commands/workflow_command.py interfaces/cli/commands/morning_report_command.py interfaces/cli/services tests/unit/interfaces/cli/test_workflow_progress_service.py tests/unit/interfaces/cli/test_workflow_command_service.py tests/unit/interfaces/cli/test_workflow_rendering.py tests/unit/interfaces/cli/test_cli.py`
  - Result: `All checks passed!`
- Targeted mypy passed with imported dependencies skipped:
  - `python -m mypy --explicit-package-bases --follow-imports=skip interfaces/cli/commands/workflow_command.py interfaces/cli/commands/morning_report_command.py interfaces/cli/services tests/unit/interfaces/cli/test_workflow_progress_service.py tests/unit/interfaces/cli/test_workflow_command_service.py`
  - Result: `Success: no issues found in 8 source files`
- Code graph updated:
  - `GRAPHIFY_VIZ_NODE_LIMIT=6000 graphify update .`
  - Result: graph updated successfully.

### Architectural note

The CLI now observes runtime progress through the canonical `EventBus` instead of scraping logs or inspecting runtime internals. The command service owns subscription lifecycle around facade execution, while Typer remains a thin process boundary that optionally renders progress notifications to stderr.

## Step 28 Results — Telemetry Mappings for Workflow Control and Progress Events

Step 28 was completed by adding canonical runtime telemetry mappings for the workflow control and external progress events introduced by the workflow control feature.

### Files updated

- `core/runtime/telemetry/runtime_telemetry.py`
- `core/runtime/telemetry/runtime_telemetry_hook.py`
- `tests/unit/runtime/telemetry/test_runtime_telemetry_hook.py`
- `tests/integration/telemetry/test_bootstrap_observability.py`
- `.agent/plans/plan_workflow_control_plus_notifications.md`

### Implementation results

- Extended `RuntimeTelemetryEventType` with explicit workflow-control telemetry event names:
  - `workflow_control.state_changed`
  - `workflow_control.pause_requested`
  - `workflow_control.paused`
  - `workflow_control.resume_requested`
  - `workflow_control.resumed`
  - `workflow_control.cancel_requested`
  - `workflow_control.cancelled`
- Extended `RuntimeTelemetryEventType` with external workflow-progress telemetry event names:
  - `workflow_progress.workflow_started`
  - `workflow_progress.workflow_running`
  - `workflow_progress.workflow_completed`
  - `workflow_progress.workflow_failed`
  - `workflow_progress.workflow_cancelled`
  - `workflow_progress.wave_started`
  - `workflow_progress.wave_completed`
  - `workflow_progress.wave_failed`
  - `workflow_progress.node_started`
  - `workflow_progress.node_running`
  - `workflow_progress.node_completed`
  - `workflow_progress.node_failed`
- Added missing runtime telemetry event types for:
  - `runtime.wave.failed`
  - `runtime.checkpoint.failed`
  - `runtime.event` fallback
- Replaced the previous incomplete runtime-event mapping that defaulted unknown runtime events to `runtime.workflow.completed`. Unknown runtime events now map to the neutral `runtime.event` telemetry type.
- Corrected checkpoint/replay runtime-event mappings to use the canonical `RuntimeEventType` values while preserving legacy dotted aliases.
- Updated `RuntimeTelemetryHook.on_runtime_event(...)` to preserve runtime-event boundary metadata on telemetry events:
  - `timestamp`
  - `node_name`
  - `wave_index`
  - `success`
  - `error_count`
- Added focused unit coverage for control mappings, progress mappings, and failed-progress error propagation.
- Updated bootstrap observability integration coverage to assert that new `workflow_progress.*` telemetry events reach the core observability pipeline.

### Validation completed

- Focused telemetry tests passed:
  - `python -m pytest tests/unit/runtime/telemetry/test_runtime_telemetry_hook.py tests/integration/telemetry/test_bootstrap_observability.py`
  - Result: `4 passed`
- Runtime/control/progress telemetry regression tests passed:
  - `python -m pytest tests/unit/runtime/telemetry/test_runtime_telemetry_hook.py tests/integration/telemetry/test_bootstrap_observability.py tests/integration/telemetry/test_observability_pipeline.py tests/unit/runtime/control/test_workflow_control_events.py tests/integration/runtime/test_workflow_progress_events.py tests/integration/runtime/test_workflow_cancel.py tests/integration/runtime/test_workflow_pause_resume.py`
  - Result: `12 passed`
- Ruff checks passed:
  - `python -m ruff check core/runtime/telemetry core/telemetry/sinks/runtime_telemetry_sink.py tests/unit/runtime/telemetry/test_runtime_telemetry_hook.py tests/integration/telemetry/test_bootstrap_observability.py`
  - Result: `All checks passed!`
- Targeted mypy passed with imported dependencies skipped:
  - `python -m mypy --explicit-package-bases --follow-imports=skip core/runtime/telemetry tests/unit/runtime/telemetry/test_runtime_telemetry_hook.py tests/integration/telemetry/test_bootstrap_observability.py`
  - Result: `Success: no issues found in 6 source files`
- Code graph updated:
  - `GRAPHIFY_VIZ_NODE_LIMIT=6000 graphify update .`
  - Result: graph updated successfully.

### Architectural note

Telemetry now distinguishes lifecycle telemetry (`runtime.*`) from external progress telemetry (`workflow_progress.*`) and workflow-control telemetry (`workflow_control.*`). Runtime nodes and control managers continue to emit canonical `RuntimeEvent` objects; serialization into telemetry event names happens only at the telemetry boundary through `RuntimeTelemetryHook`.

## Step 29 Results — Targeted Runtime and CLI Regression Checks

Step 29 was completed as a targeted regression pass across the workflow control, progress notification, telemetry, bootstrap, Dishka provider, and CLI command-service surfaces.

### Files updated

- `tests/unit/runtime/control/test_workflow_control_manager.py`
- `.agent/plans/plan_workflow_control_plus_notifications.md`

### Implementation results

- Ran the full targeted regression suite for the workflow control + notifications feature.
- Verified runtime control manager state/event behavior remained stable.
- Verified runtime engine pause/resume/cancel/progress behavior remained stable.
- Verified telemetry mappings and observability flow remained stable.
- Verified facade, bootstrap, and Dishka provider wiring remained stable.
- Verified CLI command services, progress subscriptions, rendering behavior, and morning-report workflow integration tests remained stable.
- Ran the real `polaris morning-report --format console` command. The command reached the runtime and rendered the workflow output/errors to console as expected; it exited non-zero because the sandboxed environment could not resolve the external Alpaca paper API host. This confirms the always-render CLI behavior works even when the workflow fails due an external network dependency.
- Added a small test-only type annotation in `tests/unit/runtime/control/test_workflow_control_manager.py` so targeted mypy can validate the runtime control test suite without inference ambiguity.

### Validation completed

- Targeted runtime/workflow/telemetry/CLI regression tests passed:
  - `python -m pytest tests/unit/runtime/control tests/unit/runtime/execution/test_runtime_engine_control_manager.py tests/unit/runtime/telemetry/test_runtime_telemetry_hook.py tests/unit/workflow/test_workflow_facade_control.py tests/unit/interfaces/cli/test_workflow_progress_service.py tests/unit/interfaces/cli/test_workflow_command_service.py tests/unit/interfaces/cli/test_workflow_rendering.py tests/unit/interfaces/cli/test_cli.py tests/integration/runtime/test_workflow_progress_events.py tests/integration/runtime/test_workflow_cancel.py tests/integration/runtime/test_workflow_pause_resume.py tests/integration/telemetry/test_bootstrap_observability.py tests/integration/telemetry/test_observability_pipeline.py tests/integration/workflow/test_workflow_bootstrap.py tests/integration/workflow/test_workflow_provider_control.py tests/integration/workflow/test_morning_report_real_nodes.py`
  - Result: `67 passed, 1 warning`
- CLI smoke check executed:
  - `polaris morning-report --format console`
  - Result: rendered workflow output and runtime node errors; exited `1` due sandbox DNS failure resolving `paper-api.alpaca.markets`.
- Ruff checks passed:
  - `python -m ruff check core/runtime/control core/runtime/execution/runtime_engine.py core/runtime/telemetry core/workflow/bootstrap/workflow_bootstrap.py core/workflow/execution/workflow_facade.py core/bootstrap/workflow_providers.py interfaces/cli/commands/workflow_command.py interfaces/cli/commands/morning_report_command.py interfaces/cli/services tests/unit/runtime/control tests/unit/runtime/execution/test_runtime_engine_control_manager.py tests/unit/runtime/telemetry/test_runtime_telemetry_hook.py tests/unit/workflow/test_workflow_facade_control.py tests/unit/interfaces/cli/test_workflow_progress_service.py tests/unit/interfaces/cli/test_workflow_command_service.py tests/unit/interfaces/cli/test_workflow_rendering.py tests/unit/interfaces/cli/test_cli.py tests/integration/runtime/test_workflow_progress_events.py tests/integration/runtime/test_workflow_cancel.py tests/integration/runtime/test_workflow_pause_resume.py tests/integration/telemetry/test_bootstrap_observability.py tests/integration/telemetry/test_observability_pipeline.py tests/integration/workflow/test_workflow_bootstrap.py tests/integration/workflow/test_workflow_provider_control.py tests/integration/workflow/test_morning_report_real_nodes.py`
  - Result: `All checks passed!`
- Targeted mypy passed with imported dependencies skipped:
  - `python -m mypy --explicit-package-bases --follow-imports=skip core/runtime/control core/runtime/execution/runtime_engine.py core/runtime/telemetry core/workflow/bootstrap/workflow_bootstrap.py core/workflow/execution/workflow_facade.py core/bootstrap/workflow_providers.py interfaces/cli/commands/workflow_command.py interfaces/cli/commands/morning_report_command.py interfaces/cli/services tests/unit/runtime/control tests/unit/runtime/execution/test_runtime_engine_control_manager.py tests/unit/runtime/telemetry/test_runtime_telemetry_hook.py tests/unit/workflow/test_workflow_facade_control.py tests/unit/interfaces/cli/test_workflow_progress_service.py tests/unit/interfaces/cli/test_workflow_command_service.py tests/unit/interfaces/cli/test_workflow_rendering.py tests/unit/interfaces/cli/test_cli.py tests/integration/runtime/test_workflow_progress_events.py tests/integration/runtime/test_workflow_cancel.py tests/integration/runtime/test_workflow_pause_resume.py tests/integration/telemetry/test_bootstrap_observability.py tests/integration/telemetry/test_observability_pipeline.py tests/integration/workflow/test_workflow_bootstrap.py tests/integration/workflow/test_workflow_provider_control.py tests/integration/workflow/test_morning_report_real_nodes.py`
  - Result: `Success: no issues found in 36 source files`
- Code graph updated after the test type-annotation change:
  - `GRAPHIFY_VIZ_NODE_LIMIT=6000 graphify update .`
  - Result: graph updated successfully.

### Architectural note

The regression pass confirms the feature remains wired through the intended inside-out architecture: the runtime owns cooperative control/progress semantics, the facade/bootstrap/provider layers expose the shared control surface, telemetry observes canonical runtime events at the telemetry boundary, and the CLI remains a thin async command-service adapter around the bootstrapped workflow runtime.

## Step 30 Results — Graph Update and Final Review

Step 30 was completed as the final graph refresh and review pass for the workflow control plus external progress notifications feature.

### Files updated

- `.agent/plans/plan_workflow_control_plus_notifications.md`
- `graphify-out/GRAPH_REPORT.md`
- `graphify-out/graph.html`

### Final review results

- Re-ran the repository code graph update after the final regression and type-annotation changes.
- Reviewed the working tree status and confirmed the workflow control/notification changes are isolated to the intended runtime, workflow, CLI, tests, dependency manifests, plan file, and graph outputs.
- Confirmed generated runtime telemetry persistence output was restored and is not part of the feature diff.
- Ran a final focused smoke test across the new telemetry mapping, CLI command-service/progress subscription, bootstrap wiring, and observability surfaces.
- Ran a final focused Ruff check over the changed runtime/workflow/CLI/test surfaces.

### Validation completed

- Code graph updated:
  - `GRAPHIFY_VIZ_NODE_LIMIT=6000 graphify update .`
  - Result: graph updated successfully.
- Final focused smoke tests passed:
  - `python -m pytest tests/unit/runtime/telemetry/test_runtime_telemetry_hook.py tests/unit/interfaces/cli/test_workflow_command_service.py tests/unit/interfaces/cli/test_workflow_progress_service.py tests/integration/workflow/test_workflow_bootstrap.py tests/integration/telemetry/test_bootstrap_observability.py`
  - Result: `14 passed, 1 warning`
- Final focused Ruff checks passed:
  - `python -m ruff check core/runtime/control core/runtime/execution/runtime_engine.py core/runtime/telemetry core/workflow/bootstrap/workflow_bootstrap.py core/workflow/execution/workflow_facade.py core/bootstrap/workflow_providers.py interfaces/cli/commands/workflow_command.py interfaces/cli/commands/morning_report_command.py interfaces/cli/services tests/unit/runtime/telemetry/test_runtime_telemetry_hook.py tests/unit/interfaces/cli/test_workflow_command_service.py tests/unit/interfaces/cli/test_workflow_progress_service.py tests/integration/workflow/test_workflow_bootstrap.py tests/integration/telemetry/test_bootstrap_observability.py`
  - Result: `All checks passed!`

### Final architectural summary

The feature now provides cooperative workflow control and external progress notifications through the runtime-first architecture:

- `WorkflowControlManager` owns workflow control state and emits canonical runtime events.
- `RuntimeEngine` cooperatively observes pause/resume/cancel state at safe boundaries and emits progress events through the canonical `EventBus`.
- `WorkflowFacade` exposes workflow control APIs as the application boundary.
- `WorkflowBootstrap` and the Dishka provider compose one shared control manager and event bus to avoid split-brain workflow state.
- Runtime telemetry maps canonical runtime control/progress events into explicit `workflow_control.*` and `workflow_progress.*` telemetry event names at the telemetry boundary.
- CLI commands remain Typer process-boundary adapters and delegate async workflow execution/progress subscription behavior to typed command services.
- Console workflow output renders runtime node outputs and errors even when workflow execution fails.

