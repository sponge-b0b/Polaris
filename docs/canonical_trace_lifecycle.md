# Canonical Trace Lifecycle

## Decision

Polaris owns a vendor-neutral trace context so workflow execution, telemetry,
PostgreSQL persistence, replay evidence, logs, metrics, and external tracing can
share one identity without making the runtime depend on OpenTelemetry.

The identifiers are tracing contracts, not generic logical keys:

```text
trace_id        one end-to-end distributed trace
span_id         one bounded operation instance
parent_span_id  the immediate parent operation
event_id        one immutable telemetry event
```

A span ID may appear on multiple lifecycle events only when those events describe
the same operation. It must not identify an arbitrary execution scope containing
several independently timed operations.

## Canonical ownership

| Concept | Canonical owner | Durable representation | External representation |
| --- | --- | --- | --- |
| Workflow execution | Workflow/runtime execution boundary | One trace/span record plus events | Root OpenTelemetry span |
| Runtime node attempt | Runtime node executor | One child span per attempt | Child OpenTelemetry span |
| Application service attempt | `ServiceRunner` | One child span per attempt | Child OpenTelemetry span |
| Provider call | `record_provider_call()` | One child span per call | Child OpenTelemetry span |
| HTTP, datastore, or model operation | Owning client/repository/model boundary | One child span when independently timed | Child OpenTelemetry span |
| Retry, progress, warning, or degradation | Boundary that owns the operational fact | Telemetry event associated with an operation span | OpenTelemetry span event |
| Exception | Terminal operation owner | Terminal span state plus one exception-bearing event | Error status and exception event |

## Required lifecycle

```text
operation starts
    -> allocate one span_id
    -> retain its start time and parent relationship

operation emits notifications
    -> create distinct event_id values
    -> associate each event with the operation span_id

operation completes, fails, or is cancelled
    -> close the same span_id exactly once
    -> persist end time, duration, status, and bounded exception details
    -> export one completed OpenTelemetry span
```

Retries that represent new attempts are new operation instances and therefore
receive new span IDs under the same parent operation.

## Current data lifecycle audit

```text
TraceContext producer
    -> RuntimeContext / TelemetryContext
    -> RuntimeEvent or TelemetryEvent
    -> TelemetryCollector
    -> logging / metrics / PostgreSQL / OpenTelemetry
    -> PostgreSQL queries, Jaeger, Grafana, and operational diagnostics
```

### Current classifications and gaps

| Boundary | Current behavior | Classification | Required correction |
| --- | --- | --- | --- |
| Workflow | Root `TraceContext` is created for the run | Real operation span | Retain with strict lifecycle semantics |
| Runtime node | One child context is created before the node retry loop | Over-broad scope | Create one node-attempt span per attempt |
| ServiceRunner | Service lifecycle usually reuses the incoming node context | Distinct operation sharing parent ID | Create one child span per service attempt |
| Provider telemetry | Provider lifecycle reuses the active service/node context | Distinct operation sharing parent ID | Create one child span per provider call |
| Client retry | Retry event uses the surrounding provider context | Span event | Attach to the provider or attempt span; do not export a new span |
| Datastore/HTTP/model calls | Coverage varies and often inherits the caller context | Missing or over-broad span | Create child spans for independently timed external operations |
| Runtime progress/control | Multiple notifications share a runtime context | Span events | Keep distinct event IDs and attach to the owning span |
| OpenTelemetry sink | One external span is retained per canonical operation; lifecycle notifications are attached as span events | Canonical external projection | Retain this one-operation/one-span contract |
| PostgreSQL mapper | Canonical events retain their own `event_id`; lifecycle observations map to one stable `trace_id + span_id` record identity | Canonical event/span separation | Retain this contract |
| PostgreSQL repository | Trace lifecycle observations upsert one canonical span row and choose terminal state deterministically | Canonical durable assembly | Retain this contract |

## Step 10 anchor-map removal

The former anchor map created separate external spans with random identifiers
for events that shared one Polaris operation span. Step 10C removed that workaround.
The OpenTelemetry boundary now uses Polaris's canonical trace and span identifiers
as the actual exported identities, retains one span for the operation lifecycle,
and attaches notifications and exception details as span events.

Open lifecycles are bounded. Limit eviction and sink shutdown explicitly mark
and end incomplete spans; `force_flush()` never closes operations that are still
running. No compatibility alias or logical-span mapping remains.

## Persistence invariants

- `telemetry_events` stores one row per canonical `event_id`.
- `telemetry_traces` stores one row per canonical `(trace_id, span_id)` operation.
- Starting and terminal lifecycle information must merge into the same span row.
- Completion, failure, cancellation, duration, and exception information must
  never be discarded by conflict handling.
- PostgreSQL remains authoritative; Jaeger is an external projection of the same
  canonical trace topology.

## PostgreSQL lifecycle assembly

PostgreSQL stores the two observability concepts independently:

- `telemetry_events` is immutable event evidence keyed by the canonical
  `TelemetryEvent.event_id`; persistence does not generate a replacement ID.
- `telemetry_traces` is assembled operation state with a unique
  `(trace_id, span_id)` contract. Start, progress, and terminal observations
  therefore update one row rather than creating competing span records.

Every exception-bearing event also retains its canonical sanitized exception
snapshot under `telemetry_events.payload.exception_details`. The event `message`
uses an explicit canonical event message when present and otherwise falls back
to the exception message. Exception type, message, and stack trace are bounded to
`256`, `4096`, and `32768` characters respectively before any sink receives them.

Terminal observations set first-class `ended_at`, `duration_seconds`, `status`,
`terminal_event_id`, and bounded exception fields. Conflict resolution is
deterministic: failure outranks cancellation, cancellation outranks success, and
equivalent outcomes use the latest terminal timestamp. Non-terminal observations
may enrich lineage, attributes, and metadata, but cannot reopen or erase a
terminal outcome. The earliest observed start time is retained.

Migration `b8c9d0e1f2a3` corrects the former event-time-plus-duration terminal
timestamps, removes duplicate historical trace/span rows, and then enforces the
unique canonical span constraint. It also removes the obsolete non-unique
composite index; no compatibility trace identity remains.

## Verification gates

- Every operation span has one unique ID and at most one terminal outcome.
- Concurrent branches share a trace ID but never a span ID.
- Retry attempts have distinct span IDs.
- Events do not become spans merely because they are exported.
- Persisted and exported parent-child relationships match.
- No bounded anchor mapping remains after the correction is complete.
