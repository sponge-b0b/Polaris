# Dependency Composition (Entity ID: dependency-composition)

**Boundary Rationale:** Composition deserves preservation because dependency scopes, request lifetimes, and the ban on hidden service locators are architectural invariants affecting every runtime entry path.
(source: owner-approved entity promotion)

### Strict Invariants

* Dishka is the canonical dependency-injection framework for runtime and service assembly, because dependency lifetimes must be configured once rather than recreated by entrypoints. (source: docs/adr/0002-dependency-composition-dishka-request-scopes.md)
* Long-lived infrastructure lives in application scope, while every command, request, or tool execution opens a request scope that the owning boundary closes, because request-scoped state must not leak across invocations. (source: docs/adr/0002-dependency-composition-dishka-request-scopes.md)
* `get_async_di_container()` and registered providers are the supported composition entry points; interfaces must not recreate the object graph by hand, because manual wiring creates divergent runtime behavior. (source: docs/adr/0002-dependency-composition-dishka-request-scopes.md)
* Production code must not introduce a hidden global mutable service locator, because service location would bypass explicit scopes and make dependencies invisible to tests and governance. (source: docs/adr/0002-dependency-composition-dishka-request-scopes.md)
* Built-in workflow catalog registrations supply risk authority to CLI and MCP composition, while request-scoped services provide governed invocation and output-evidence lifecycles, because transports cannot select authority or bypass durable evidence acquisition. (source: docs/adr/0018-platform-governed-invocation-and-output-evidence-boundaries.md)
