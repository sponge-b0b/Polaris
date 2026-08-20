# Runtime & Workflow Platform (Entity ID: runtime-workflow-platform)

**Boundary Rationale:** This is the execution trunk: workflow facade/bootstrap, runtime graph execution, runtime context, events, replay/control/checkpointing, and policy/governance hooks. It is a boundary because execution ownership, lifecycle, context semantics, and callback/event rules are centralized here.
(source: owner-approved entity boundary determination)

### Strict Invariants

* `WorkflowFacade` is the canonical application-facing workflow boundary, `RuntimeEngine` owns graph execution, and `WorkflowBootstrap` owns assembly, because runtime execution must have one stable trunk rather than scattered entry paths. (source: docs/adr/0001-runtime-workflow-platform-execution-boundaries.md)
* Runtime callers must use the facade instead of constructing or invoking the runtime engine directly, because direct engine access would bypass lifecycle, policy, composition, and telemetry constraints. (source: docs/adr/0001-runtime-workflow-platform-execution-boundaries.md)
* New execution features extend the existing runtime path rather than creating parallel runtimes or moving runtime ownership into interfaces, workflow definitions, agents, or providers, because live, backtest, replay, and service flows must remain comparable. (source: docs/adr/0001-runtime-workflow-platform-execution-boundaries.md)
* `RuntimeContext` is the canonical workflow execution snapshot and not a business aggregate, because runtime state must support execution/replay without becoming the durable domain record owner. (source: docs/current/platform-architecture-ownership-ledger.md)
* `EventBus` and typed `RuntimeEvent` notifications are the canonical runtime notification path, because telemetry and observers should project runtime facts without taking over execution ownership. (source: docs/adr/0003-platform-runtime-events-telemetry-trace-propagation.md)

### Planned

* **Explicit actor attribution across runtime boundaries** — accepted, implementation pending: request-scoped identity becomes typed actor attribution when work crosses into runtime, asynchronous, durable, governance, or independently protected execution; workflow executions preserve their initiating principal, while internal nodes do not redundantly re-authorize unless they start a new protected action. (source: docs/adr/0023-identity-access-propagation-audit-attribution.md)
* **Runtime approvals and scheduling expansion** — proposed, not yet accepted. (source: docs/proposed/platform-future-architecture.md)
