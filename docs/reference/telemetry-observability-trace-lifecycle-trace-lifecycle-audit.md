# Trace Lifecycle Audit

> **Reference-only historical audit.** This document preserves trace-lifecycle audit findings and migration notes extracted from the current lifecycle contract. It is structured lookup material, not current architectural authority, and must not be used to establish new Strict Invariants. Current trace lifecycle authority is owned by [`../current/telemetry-observability-trace-lifecycle-canonical-trace.md`](../current/telemetry-observability-trace-lifecycle-canonical-trace.md).

## Historical lifecycle audit material

The section titles below are preserved from the historical audit material. They describe the audit baseline and migration disposition rather than current document authority.

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

## Historical migration note

Migration `b8c9d0e1f2a3` corrected the former event-time-plus-duration terminal timestamps, removed duplicate historical trace/span rows, and then enforced the unique canonical span constraint. It also removed the obsolete non-unique composite index; no compatibility trace identity remains.
