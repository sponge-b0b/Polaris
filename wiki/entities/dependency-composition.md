# Dependency Composition (Entity ID: dependency-composition)

**Boundary Rationale:** Composition deserves preservation because dependency scopes, request lifetimes, and the ban on hidden service locators are architectural invariants affecting every runtime entry path.
(source: owner-approved entity promotion)

### Strict Invariants

* Dishka is the canonical dependency-injection framework for runtime and service assembly, because dependency lifetimes must be configured once rather than recreated by entrypoints. (source: docs/adr/0002-dependency-composition-dishka-request-scopes.md)
* Long-lived infrastructure lives in application scope, while every command, request, or tool execution opens a request scope that the owning boundary closes, because request-scoped state must not leak across invocations. (source: docs/adr/0002-dependency-composition-dishka-request-scopes.md)
* `get_async_di_container()` and registered providers are the supported composition entry points; interfaces must not recreate the object graph by hand, because manual wiring creates divergent runtime behavior. (source: docs/adr/0002-dependency-composition-dishka-request-scopes.md)
* Production code must not introduce a hidden global mutable service locator, because service location would bypass explicit scopes and make dependencies invisible to tests and governance. (source: docs/adr/0002-dependency-composition-dishka-request-scopes.md)
* The request-scoped governed execution service reconstructs Baseline runtime provenance or Enhanced/Vigilant decision evidence before deriving audit context and issuing the facade capability, because caller-supplied evidence cannot authorize governed execution. (source: docs/adr/0012-dependency-composition-governed-execution-evidence-contract.md)
### Planned

* **Canonical Baseline runtime-evidence production lifecycle** — accepted, implementation pending. The canonical runtime/workflow orchestration boundary must use one application lifecycle service to create and persist Baseline authority and provenance; persistence adapters reconstruct/store and transports only identify/consume the durable record. (source: docs/adr/0013-dependency-composition-baseline-runtime-evidence-production-lifecycle.md)
* **Request-scoped governed-execution evidence acquisition** — accepted, implementation pending. The governed execution service must resolve workflow identity, platform-owned authority tier, and the durable evidence variant through one application resolver before enforcement; transports only submit execution requests and render typed failures. (source: docs/adr/0015-dependency-composition-governed-execution-evidence-acquisition.md)
* **Execution-scoped governed-evidence resolution lifecycle** — accepted, implementation pending. Canonical orchestration must persist one tier-specific evidence selection for its platform-created execution correlation and registry-resolved workflow identity; the request-scoped resolver must re-acquire and validate it before enforcement, rather than accepting a transport-carried evidence reference. (source: docs/adr/0016-dependency-composition-governed-execution-evidence-resolution-lifecycle.md)
