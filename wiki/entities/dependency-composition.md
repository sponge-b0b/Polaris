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
