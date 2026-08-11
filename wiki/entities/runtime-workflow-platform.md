# Runtime & Workflow Platform (Entity ID: runtime-workflow-platform)

**Boundary Rationale:** This is the execution trunk: workflow facade/bootstrap, runtime graph execution, runtime context, events, replay/control/checkpointing, and policy/governance hooks. It is a boundary because execution ownership, lifecycle, context semantics, and callback/event rules are centralized here.
(source: owner-approved entity boundary determination)

### Strict Invariants

* `WorkflowFacade` is the canonical application-facing workflow boundary, `RuntimeEngine` owns graph execution, and `WorkflowBootstrap` owns assembly, because runtime execution must have one stable trunk rather than scattered entry paths. (source: docs/adr/0001-runtime-workflow-platform-execution-boundaries.md)
* Runtime callers must use the facade instead of constructing or invoking the runtime engine directly, because direct engine access would bypass lifecycle, policy, composition, and telemetry constraints. (source: docs/adr/0001-runtime-workflow-platform-execution-boundaries.md)
* New execution features extend the existing runtime path rather than creating parallel runtimes or moving runtime ownership into interfaces, workflow definitions, agents, or providers, because live, backtest, replay, and service flows must remain comparable. (source: docs/adr/0001-runtime-workflow-platform-execution-boundaries.md)
* `RuntimeContext` is the canonical workflow execution snapshot and not a business aggregate, because runtime state must support execution/replay without becoming the durable domain record owner. (source: docs/current/platform-architecture-ownership-ledger.md)
* `EventBus` and typed `RuntimeEvent` notifications are the canonical runtime notification path, because telemetry and observers should project runtime facts without taking over execution ownership. (source: docs/adr/0003-platform-runtime-events-telemetry-trace-propagation.md)
* Workflow facade governance and policy preflight evaluations must stay on the canonical runtime/application seam, including handoff to application-owned automated decision audit when evidence-scoped audit context is supplied, because runtime execution cannot bypass approval-lifecycle evidence. (source: docs/adr/0001-runtime-workflow-platform-execution-boundaries.md; docs/adr/0010-governance-approval-lifecycle-contestability-residual-risk.md)
* Enforced facade execution consumes a one-use capability derived from reconstructed canonical evidence—Baseline runtime provenance or an Enhanced/Vigilant decision-evidence packet—and receives it through an explicit typed seam rather than context metadata, because the same verified authority must govern and audit the invocation. (source: docs/adr/0012-dependency-composition-governed-execution-evidence-contract.md)
### Planned

* **Registry-owned governed Workflow Identity** — accepted, implementation pending. The registry must resolve the workflow name and deterministic definition fingerprint used to bind every governed evidence variant before evaluation and audit-capability issuance. (source: docs/adr/0014-runtime-workflow-platform-governed-workflow-identity.md)

* **Runtime approvals and scheduling expansion** — proposed, not yet accepted. (source: docs/proposed/platform-future-architecture.md)
