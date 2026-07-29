# 0003. Runtime Events, Telemetry, and Trace Propagation

Status: accepted
Date: 2026-07-17

## Context and Problem Statement

Workflow execution, progress, control, persistence, and observability require consistent event identity and trace correlation across asynchronous boundaries. Direct callbacks or independent event systems would fragment notifications, metrics, logs, traces, and audit records.

## Decision Outcome

Chosen option: "RuntimeEvent notifications through EventBus with boundary telemetry mapping", because it keeps workflow notifications, persistence reactions, metrics, logs, and traces correlated without creating parallel event systems.

`EventBus` and typed `RuntimeEvent` objects are the canonical runtime coordination and notification mechanism. Runtime components publish domain events; subscribers handle persistence or other reactions without taking execution ownership. Telemetry maps runtime events at the observability boundary into structured logs, metrics, and traces.

Trace context is created at canonical operation entry points and propagated through runtime context, events, provider calls, and asynchronous tasks. `asyncio` concurrency must preserve the active context. Telemetry failure must not replace the domain result, but caught failures must be logged defensively.

## Rationale

One event path keeps workflow progress, control notifications, persistence, metrics, and distributed traces correlated and replay-inspectable. Boundary mapping avoids coupling runtime domain contracts to a specific telemetry backend.

## Consequences

- New runtime notifications use existing `RuntimeEvent` contracts and `EventBus`.
- Components do not introduce parallel callback buses for workflow coordination.
- External datastore and provider operations retain latency and failure telemetry.
- OpenTelemetry, Prometheus, Jaeger, logging, and persistence remain sinks or boundary concerns rather than runtime execution owners.

## Affected Modules

- `core/runtime/events/event_bus.py`
- `core/runtime/events/runtime_events.py`
- `core/runtime/telemetry/runtime_telemetry.py`
- `core/runtime/telemetry/runtime_telemetry_hook.py`
- `core/telemetry/observability/observability_manager.py`
- `core/telemetry/context.py`
- `core/telemetry/tracing/trace_context.py`
