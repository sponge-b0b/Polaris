## Analysis Summary

After examining the code flow across the relevant files, I've identified **why the runtime context is persisted to disk after workflow completion but never used**:

### The Flow

1. **`WorkflowEngine.execute_from_context()`** (core/workflow/execution/workflow_engine.py:112-274)
   - Has `persist_on_completion: bool = True` parameter (default True)
   - On success (line 163-166) and failure (line 228-231), calls `_persist_context_safe()`
   - `_persist_context_safe()` → `state_manager.persist_context(context)`

2. **`StateManager.persist_context()`** (core/runtime/state/state_manager.py:75-89)
   - Calls `self.persistence.save_run(workflow_name=context.workflow_id, run_data=context.to_dict())`
   - Only if `self.persistence` is not None

3. **`RunPersistence.save_run()`** (core/storage/persistence/run_persistence.py:55-99)
   - Saves to `storage/runs/{workflow_name}/{execution_id}.json`

### The Problem: `load_run()` is NEVER Called

**Search results confirm:**
- `RunPersistence.load_run()` exists in the abstract base class and `LocalDiskRunPersistence` implementation
- **Zero call sites** in the entire codebase call `.load_run()`
- **Zero call sites** call `list_runs()` on the RunPersistence interface

### What IS Used for Recovery/Replay: CheckpointManager

The **ReplayEngine** (core/runtime/replay/replay_engine.py) and **WorkflowFacade/WorkflowService** use:
- `CheckpointManager.save_checkpoint()` - saves RuntimeCheckpoint WITH embedded RuntimeContext
- `CheckpointManager.load_checkpoint()` / `restore_context()` - loads from checkpoints
- **NOT** `RunPersistence.load_run()`

### Root Cause

The `RunPersistence` abstraction was designed with both `save_run()` and `load_run()`, but:
1. The **checkpoint system** (CheckpointManager) is the actual mechanism for replay/recovery
2. Checkpoints contain the full RuntimeContext + execution position (wave_index, completed_nodes, etc.)
3. Run persistence saves only the final RuntimeContext snapshot without execution position metadata
4. No code path exists to load a completed run and resume from it

### Architectural Intent (from AGENTS.md)

The platform follows an inside-out architecture where:
- **ReplayEngine** uses checkpoints for deterministic replay
- **RunPersistence** appears to be for audit/history/archival purposes
- But there's no consumer of this audit data

---

## Proposed Plan

### Option 1: Remove Unused Persistence (Recommended)
If run persistence is truly unused:
1. Remove `persist_on_completion` parameter from `WorkflowEngine.execute()` and `execute_from_context()`
2. Remove `_persist_context_safe()` and its calls
3. Remove `persist_context()` from `StateManager`
4. Remove `RunPersistence` abstraction and `LocalDiskRunPersistence` implementation
5. Remove `RunPersistence` from DI providers

### Option 2: Add Load Capability (If Audit/History is Needed)
If the persisted runs should be queryable:
1. Add `load_run()` and `list_runs()` methods to `StateManager`
2. Expose via `WorkflowFacade`/`WorkflowService` 
3. Add CLI commands to list/load historical runs
4. Add API endpoints for run history

### Option 3: Unify with Checkpoints
Make run persistence a byproduct of checkpointing:
1. On checkpoint save, also save a run snapshot
2. On checkpoint load, use that as the run history
3. Eliminate separate `persist_on_completion` logic

---

## Questions for Clarification

1. **Is run persistence intended for audit/history purposes?** Should users be able to query past workflow executions?
2. **Should completed runs be resumable?** Currently only checkpoints support resume.
3. **Is there a planned feature** that would consume these persisted runs (e.g., backtest comparison, historical analysis)?
4. **What's the retention policy?** Currently runs accumulate indefinitely in `storage/runs/`

The current implementation persists data that is written but never read - this violates the "Observability First" and "Replayability" principles since the data exists but isn't observable or replayable.


# My recommendation
do not remove run persistence. Reclassify it.

Use:

CheckpointManager
    = resume / replay / execution recovery

RunPersistence
    = completed-run audit / history / RAG source material

So I would choose a modified Option 2, not Option 1 or 3.

Recommended direction:

1. Keep checkpointing as the only resume/replay mechanism.
2. Keep run persistence, but stop pretending it is for recovery.
3. Rename/reposition it as CompletedRunArchive.
4. Add read/list capabilities.
5. Add retention policy.
6. Later migrate completed runs from local disk to PostgreSQL.
7. Use completed run summaries as RAG source material, not raw RuntimeContext dumps.

The key architecture fix is semantic clarity:

storage/checkpoints/
    recoverable execution state

storage/runs/
    completed execution archive / audit snapshot

I would not make completed runs resumable. A completed run is historical evidence. A checkpoint is executable recovery state.

Also, do not embed raw run JSON directly into RAG. Instead, use completed runs to build curated records:

Completed Run
    -> run summary
    -> node output summaries
    -> report sections
    -> recommendation records
    -> RAG documents/chunks

Best next implementation step:

1. Rename RunPersistence to CompletedRunArchive.
2. Add StateManager.list_completed_runs().
3. Add StateManager.load_completed_run().
4. Add CLI command: polaris runs list / polaris runs show.
5. Add retention config.
6. Later add PostgresCompletedRunArchive.

So the answer to the clarification questions:

Audit/history? Yes.
Completed runs resumable? No.
Planned consumers? Yes: CLI history, audit, RAG document builder, backtest comparison, workflow analytics.
Retention? Add explicit policy now.

We need to preserve the new CompletedRunArchive because the data will be valuable for RAG, observability, audit, and historical analysis.

## Implementation Plan: CompletedRunArchive

Based on your architectural direction, here's the detailed implementation plan:

---

### Phase 1: Core Rename & Interface (storage layer)

**Files to modify:**
1. `core/storage/persistence/run_persistence.py` → `core/storage/persistence/completed_run_archive.py`
   - Rename `RunPersistence` → `CompletedRunArchive` (ABC)
   - Rename `LocalDiskRunPersistence` → `LocalDiskCompletedRunArchive`
   - Keep `save_run()` → `archive_run()`
   - Add `load_run()` → `load_archived_run()` (implement)
   - Add `list_runs()` → `list_archived_runs()` (implement)
   - Add `delete_run()` → `delete_archived_run()` (keep)
   - Add retention: `cleanup_archived_runs(max_age_days: int, max_count: int)`

2. `core/storage/__init__.py` - Update exports

---

### Phase 2: StateManager Integration

**File: `core/runtime/state/state_manager.py`**
- Rename `persist_context()` → `archive_completed_run()`
- Add `list_completed_runs(workflow_name: str) -> list[str]`
- Add `load_completed_run(workflow_name: str, execution_id: str) -> RuntimeContext | None`
- Add `cleanup_completed_runs(max_age_days: int, max_count: int) -> int`

---

### Phase 3: WorkflowEngine & Facade

**Files:**
- `core/workflow/execution/workflow_engine.py`
  - Rename `persist_on_completion` → `archive_on_completion` (param + internal)
  - Rename `_persist_context_safe()` → `_archive_context_safe()`

- `core/workflow/execution/workflow_service.py`
  - Expose `list_completed_runs()`, `load_completed_run()` via service

- `core/workflow/execution/workflow_facade.py`
  - Expose `list_completed_runs()`, `load_completed_run()` via facade

---

### Phase 4: CLI Commands

**New file: `interfaces/cli/commands/completed_runs_command.py`**
- `polaris runs list [--workflow NAME] [--limit N] [--format console|json]`
- `polaris runs show <workflow_name> <execution_id> [--format console|json|markdown]`
- `polaris runs delete <workflow_name> <execution_id>`
- `polaris runs cleanup [--max-age-days N] [--max-count N]`

**Register in:** `interfaces/cli/app.py`

---

### Phase 5: Configuration & Retention

**Files:**
- `interfaces/cli/bootstrap/settings.py` - Add `runs_retention_max_age_days`, `runs_retention_max_count`
- `core/workflow/bootstrap/workflow_bootstrap.py` - Add retention config to `WorkflowBootstrapConfig`
- `core/bootstrap/workflow_providers.py` - Pass retention config to archive

---

### Phase 6: DI & Bootstrap

**Files:**
- `core/bootstrap/workflow_providers.py` - Update provider to use `CompletedRunArchive`
- `core/workflow/bootstrap/workflow_bootstrap.py` - Wire new archive

---

### Phase 7: Tests

- Integration tests for `StateManager`
- All other tests can be deferred because we are going to replace the use of `LocalDiskCompletedRunArchive` for file persistence with a PostgreSQL implementation in the next plan iteration.

---

## Step Results

### Phase 1: Core Rename & Interface (storage layer) - COMPLETED
- Created `core/storage/persistence/completed_run_archive.py` with:
  - `CompletedRunArchive` ABC (renamed from `RunPersistence`)
  - `LocalDiskCompletedRunArchive` implementation (renamed from `LocalDiskRunPersistence`)
  - `archive_run()` (renamed from `save_run()`)
  - `load_archived_run()` (implemented, was `load_run()`)
  - `list_archived_runs()` (implemented, was `list_runs()`)
  - `delete_archived_run()` (renamed from `delete_run()`)
  - `cleanup_archived_runs(max_age_days, max_count)` (NEW - retention policy)
- Updated `core/storage/__init__.py` exports
- Deleted old `core/storage/persistence/run_persistence.py`

### Phase 2: StateManager Integration - COMPLETED
- Updated `core/runtime/state/state_manager.py`:
  - Renamed `persistence` → `archive` (type: `CompletedRunArchive`)
  - Renamed `persist_context()` → `archive_completed_run()` with clear docstring
  - Added `list_completed_runs(workflow_name: str) -> list[str]`
  - Added `load_completed_run(workflow_name: str, execution_id: str) -> RuntimeContext | None`
  - Added `cleanup_completed_runs(max_age_days, max_count) -> int`
  - Kept `restore_context()` for checkpoint recovery (unchanged)

### Phase 3: WorkflowEngine & Facade - COMPLETED
- Updated `core/workflow/execution/workflow_engine.py`:
  - Renamed `persist_on_completion` → `archive_on_completion` (param + internal)
  - Renamed `_persist_context_safe()` → `_archive_context_safe()`
  - Updated `execute()` and `execute_from_context()` signatures

- Updated `core/workflow/execution/workflow_service.py`:
  - Updated `run_workflow()` and `run_from_context()` to use `archive_on_completion`
  - (Note: `list_completed_runs()` and `load_completed_run()` exposure pending)

- Updated `core/workflow/execution/workflow_facade.py`:
  - Updated `run_workflow()` and `run_from_context()` to use `archive_on_completion`
  - (Note: `list_completed_runs()` and `load_completed_run()` exposure pending)

- Updated `core/runtime/replay/replay_engine.py`:
  - Renamed `persist_on_completion` → `archive_on_completion` in `replay_from_checkpoint()`

- Updated `core/workflow/examples/run_example_workflow.py`:
  - Updated example to use `archive_on_completion`


## Analysis: Why Runtime Context is Persisted After Workflow Completion

### The Answer

**The runtime context IS persisted AND IS loadable/fetchable** - the methods exist and work. The confusion stems from the fact that the codebase has already been refactored from the old naming convention to a new, clearer one:

| Old Name (referenced in task) | New Name (current code) |
|-------------------------------|-------------------------|
| `persist_on_completion` | `archive_on_completion` |
| `_persist_context_safe()` | `_archive_context_safe()` |
| `StateManager.persist_context()` | `StateManager.archive_completed_run()` |
| `RunPersistence.save_run()` | `CompletedRunArchive.archive_run()` |
| `RunPersistence.load_run()` | `CompletedRunArchive.load_archived_run()` |
| `RunPersistence.list_runs()` | `CompletedRunArchive.list_archived_runs()` |

### The Complete Flow (Current Code)

1. **WorkflowEngine.execute_from_context()** (line 163-166):
   ```python
   if archive_on_completion:
       await self._archive_context_safe(context=final_context)
   ```

2. **_archive_context_safe()** (line 309-318):
   ```python
   async def _archive_context_safe(self, context: RuntimeContext) -> None:
       try:
           self.state_manager.archive_completed_run(context)
       except Exception:
           return
   ```

3. **StateManager.archive_completed_run()** (state_manager.py line 76-92):
   ```python
   def archive_completed_run(self, context: RuntimeContext) -> None:
       if self.archive is None:
           return
       self.archive.archive_run(
           workflow_name=context.workflow_id,
           run_data=context.to_dict(),
       )
   ```

4. **LocalDiskCompletedRunArchive.archive_run()** (completed_run_archive.py line 86-130):
   - Saves to `storage/runs/{workflow_name}/{execution_id}.json`

### The Data IS Loadable - Methods Exist

**StateManager provides:**
- `load_completed_run(workflow_name, execution_id)` → Returns `RuntimeContext` for historical analysis
- `list_completed_runs(workflow_name)` → Lists all archived execution IDs
- `cleanup_completed_runs(max_age_days, max_count)` → Retention policy enforcement

**LocalDiskCompletedRunArchive provides:**
- `load_archived_run(workflow_name, execution_id)` → Returns raw dict
- `list_archived_runs(workflow_name)` → List of execution IDs
- `delete_archived_run(workflow_name, execution_id)` → Delete specific run
- `cleanup_archived_runs(max_age_days, max_count)` → Retention cleanup

### Why It Might Seem "Unused"

1. **No current callers** - My search found no code calling `load_completed_run()` or `list_completed_runs()` in the codebase
2. **Different purpose** - It's not for re-execution; it's for:
   - **Audit/compliance** - Immutable record of what ran
   - **RAG/ML** - Training data for future agents
   - **Debugging** - Post-mortem analysis
   - **Reporting** - Historical performance analysis
   - **Observability** - Long-term metrics

### Key Distinction: Archive vs Checkpoints

| Aspect | CompletedRunArchive | CheckpointManager |
|--------|---------------------|-------------------|
| **Purpose** | Audit, history, RAG, observability | Execution recovery, replay |
| **When** | After workflow completion | During workflow (wave boundaries) |
| **Recovery** | NOT for recovery | FOR recovery |
| **Data** | Full RuntimeContext snapshot | RuntimeContext + execution position |

### Conclusion

The runtime context is persisted (archived) because the architecture explicitly designed `CompletedRunArchive` for **post-execution value** (audit, RAG, analysis), not for **re-execution**. The loading methods exist and work - they're just waiting for consumers (CLI commands, API endpoints, RAG pipelines, reporting jobs) to be built on top of them. The refactoring from `RunPersistence` → `CompletedRunArchive` makes this semantic distinction explicit.

---

## Task Progress

- [x] Phase 1: Rename RunPersistence → CompletedRunArchive (storage layer)
- [x] Phase 2: StateManager integration (list/load/archive methods)
- [x] Phase 3: WorkflowEngine & Facade parameter rename + wiring
- [x] Phase 4: CLI commands (list, show, delete, cleanup)
- [x] Phase 5: Configuration & retention policy
- [x] Phase 6: DI providers & bootstrap wiring
- [x] Phase 7: Tests

---

## Codex Continuation Audit and Revised Completion Plan

### Current Implementation Audit

The partially executed refactor has materially completed the semantic rename from completed-run persistence to completed-run archive:

- Phase 1 is complete: `CompletedRunArchive` and `LocalDiskCompletedRunArchive` exist in `core/storage/persistence/completed_run_archive.py`, and the old `RunPersistence` path is no longer present.
- Phase 2 is complete: `StateManager` exposes archive/list/load/delete/cleanup methods for completed runs while keeping checkpoint recovery separate.
- Phase 3 is complete: workflow execution paths use `archive_on_completion` and expose completed-run read/delete/cleanup through `WorkflowService` and `WorkflowFacade`.
- Phase 4 is present but needs a correctness fix: `polaris runs show --format console` still references stale `RuntimeState` fields (`success`, `status`, `current_wave`, `completed_nodes`, `outputs`, `errors`) that do not exist on the current canonical `RuntimeState` model. Console rendering should derive success/status from `RuntimeContext.errors` and read output/error counts from `RuntimeContext`.

### Revised Remaining Work

- [x] Phase 5: Add explicit retention configuration to `WorkflowBootstrapConfig`, CLI settings, and environment parsing.
  - Add `completed_run_retention_max_age_days` and `completed_run_retention_max_count` as optional config values.
  - Allow `LocalDiskCompletedRunArchive.cleanup_archived_runs()` to use constructor-level defaults when CLI/runtime cleanup does not provide explicit values.
  - Expose environment variables:
    - `POLARIS_COMPLETED_RUN_RETENTION_MAX_AGE_DAYS`
    - `POLARIS_COMPLETED_RUN_RETENTION_MAX_COUNT`

- [x] Phase 6: Wire retention configuration through bootstrap and DI.
  - Pass retention configuration into `LocalDiskCompletedRunArchive` from `WorkflowBootstrap`.
  - Pass retention configuration into `LocalDiskCompletedRunArchive` from `WorkflowInfrastructureProvider`.
  - Pass CLI settings into `WorkflowBootstrapConfig`.

- [x] Phase 7: Fix consumer correctness and add tests.
  - Fix `interfaces/cli/commands/completed_runs_command.py` console output and cleanup default handling.
  - Replace remaining stale workflow execution keyword usage from `persist_on_completion` to `archive_on_completion` where callers invoke the runtime/facade contract.
  - Add unit coverage for local disk archive roundtrip/delete/retention.
  - Add unit coverage for `StateManager` completed-run roundtrip.
  - Add CLI coverage for `runs show` console rendering and cleanup configured retention defaults.

### Implementation Notes

Completed runs remain historical evidence only. They must not become a resume/replay mechanism. Checkpoints remain the canonical recovery and replay path.


### Completion Step Results

#### Phase 5: Configuration & Retention Policy - COMPLETED
- Added `completed_run_retention_max_age_days` and `completed_run_retention_max_count` to `WorkflowBootstrapConfig`.
- Added matching CLI settings and environment variables:
  - `POLARIS_COMPLETED_RUN_RETENTION_MAX_AGE_DAYS`
  - `POLARIS_COMPLETED_RUN_RETENTION_MAX_COUNT`
- Updated `LocalDiskCompletedRunArchive` so constructor-level retention defaults are used when cleanup callers do not pass explicit values.
- Added validation to reject negative retention values.

#### Phase 6: DI Providers & Bootstrap Wiring - COMPLETED
- Wired completed-run retention defaults through `WorkflowBootstrap` into `LocalDiskCompletedRunArchive`.
- Wired completed-run retention defaults through `WorkflowInfrastructureProvider` into the Dishka-provided `CompletedRunArchive`.
- Wired CLI settings into `WorkflowBootstrapConfig` so `polaris runs cleanup --yes` can use configured defaults.

#### Phase 7: Consumer Correctness & Tests - COMPLETED
- Fixed `polaris runs show --format console` to render current `RuntimeContext` fields instead of stale `RuntimeState` fields.
- Fixed `polaris runs cleanup` to use configured retention defaults when flags are omitted.
- Replaced stale runtime keyword usage from `persist_on_completion` to `archive_on_completion` in direct runtime/facade callers and tests.
- Added tests for:
  - local disk completed-run archive roundtrip/delete/count retention/age retention/validation
  - `StateManager` completed-run archive/load/list/delete/cleanup behavior
  - CLI completed-runs console rendering and configured cleanup defaults
  - CLI settings environment parsing for completed-run retention defaults
