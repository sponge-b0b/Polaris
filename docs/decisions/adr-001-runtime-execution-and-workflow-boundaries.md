# ADR-001: Runtime Execution and Workflow Boundaries

## Status

Accepted

## Context

Workflow execution spans interface, application, workflow, and runtime layers. Without explicit ownership, callers can bypass policy, governance, replay, control, telemetry, or lifecycle behavior by invoking the runtime directly or assembling alternate execution paths.

## Decision

`RuntimeEngine` owns graph execution and runtime lifecycle semantics. `WorkflowFacade` is the canonical application boundary for workflow registration, execution, replay, inspection, and control. `WorkflowBootstrap` is the composition root that assembles the facade and its runtime dependencies. Interface and application callers must use the facade rather than construct or mutate runtime components directly.

The stable contracts are `WorkflowFacade`, `WorkflowBootstrap`, `RuntimeNode`, `RuntimeNodeOutput`, `RuntimeContext`, and `WorkflowGraphDefinition`. Internal decomposition may reduce complexity, but it must not create a parallel runtime or move execution ownership into an interface, workflow definition, agent, or provider.

## Rationale

A single execution owner preserves policy and governance enforcement, deterministic replay, control-state handling, event publication, telemetry, and persistence behavior. A single facade and composition root also prevent split-brain runtime instances and hidden dependency construction.

## Consequences

- Callers depend on `WorkflowFacade`, not `RuntimeEngine`.
- `WorkflowBootstrap` owns runtime assembly but not business behavior.
- Refactors may decompose implementation details while preserving the canonical boundaries.
- New execution features must extend the existing runtime path rather than introduce a second executor.

## Affected Modules

- `core/runtime/execution/runtime_engine.py`
- `core/workflow/execution/workflow_facade.py`
- `core/workflow/bootstrap/workflow_bootstrap.py`
- `core/workflow/execution/workflow_engine.py`
- `core/workflow/execution/workflow_runner.py`
- `core/workflow/execution/workflow_service.py`
