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

## Verification gates

- Every operation span has one unique ID and at most one terminal outcome.
- Concurrent branches share a trace ID but never a span ID.
- Retry attempts have distinct span IDs.
- Events do not become spans merely because they are exported.
- Persisted and exported parent-child relationships match.
- No bounded anchor mapping remains.
