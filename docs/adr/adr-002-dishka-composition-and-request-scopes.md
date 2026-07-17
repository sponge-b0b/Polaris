# ADR-002: Dishka Composition and Request Scopes

## Status

Accepted

## Context

The platform requires shared runtime infrastructure and request-local application dependencies across CLI, MCP, and future interfaces. Manual construction, globals, and service locators can create duplicate `EventBus`, control, telemetry, persistence, or facade instances and make resource cleanup unreliable.

## Decision

Dishka is the canonical dependency-injection framework. Application-scope providers own long-lived infrastructure and shared runtime components. Every command, request, or tool invocation opens a Dishka request scope and resolves request-scoped services from that scope. Interfaces may own transport parsing, but they must not manually recreate the application object graph.

`get_async_di_container()` and the registered providers are the supported composition entry points. A request scope must be closed by its owning boundary. Shared components such as `EventBus`, `WorkflowControlManager`, telemetry, and `WorkflowFacade` must resolve consistently from the configured container.

## Rationale

Explicit scopes make ownership, lifecycle, test substitution, and cleanup deterministic. They also prevent split-brain runtime state and ensure all interfaces use the same canonical providers and application services.

## Consequences

- No global mutable service registry or hidden service locator is introduced.
- Interface code remains thin and resolves services inside a request scope.
- Provider changes are made in the canonical Dishka provider modules.
- Tests may override providers, but production code does not bypass the container.

## Affected Modules

- `core/bootstrap/app_container.py`
- `core/bootstrap/di_providers.py`
- `core/bootstrap/workflow_providers.py`
- `interfaces/cli/bootstrap/container.py`
- `integration/providers/di.py`
- `integration/providers/backtesting/di.py`
