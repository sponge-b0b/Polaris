# Observability Coverage Ledger

## Purpose and status

This ledger defines Polaris's canonical ownership rules for operational events and records the completed observability-boundary audit.

**Audit finalized:** July 2, 2026
**Status:** Complete for the production roots `application/`, `core/`, `integration/`, `intelligence/`, and `interfaces/`.

The governing invariant is:

> One operational fact has one canonical owner and one canonical event. Logging, metrics, tracing, and PostgreSQL are sink projections of that event, not independent recreations of it.

A provider-call failure and a higher-level degraded service result are different facts and may both be recorded. The same exception must not be independently logged or emitted at every layer through which it propagates.

## Canonical contracts

`core.telemetry.events.telemetry_event.TelemetryEvent` is the only platform telemetry-event contract.

- `core.telemetry.contracts.TelemetryEvent` and `core.telemetry.events.TelemetryEvent` are public re-exports of that same class, not competing models.
- `RuntimeTelemetryEvent` is a typed runtime notification that is converted to the canonical telemetry event at the runtime telemetry boundary.
- `TelemetryEventRecord` and `TelemetryEventModel` are persistence-boundary representations, not internal event alternatives.
- Dictionaries are used only when serializing the canonical event into a sink or external boundary.

The architecture contract in `tests/unit/telemetry/test_observability_architecture.py` rejects a second production `TelemetryEvent` class or a production import from a noncanonical module.

## Event taxonomy

| Event category | Meaning | Typical terminal state | Default severity |
|---|---|---|---|
| Lifecycle started | A bounded operation instance began. | Nonterminal | INFO |
| Lifecycle completed | The operation completed normally. | Terminal | INFO |
| Lifecycle failed | The operation cannot produce its requested result. | Terminal | ERROR |
| Lifecycle cancelled | Cooperative cancellation stopped the operation. | Terminal | WARNING unless the owning contract requires ERROR |
| Retry scheduled | A failed attempt will be followed by another bounded attempt. | Nonterminal | WARNING |
| Degraded success | The operation completed, but completeness, source availability, or capability was materially reduced. | Terminal success | WARNING |
| Policy/governance decision | A typed allow, warn, deny, skip, or approval decision. | Decision | INFO, WARNING, or ERROR according to outcome |
| Callback/subscriber failure | A plugin, runtime hook, or EventBus callback failed. | Failure of that callback | ERROR |
| Configuration failure | Required or optional infrastructure configuration was invalid. | Failed or degraded startup | ERROR or WARNING; CRITICAL before telemetry exists |
| Telemetry sink failure | A sink could not accept an event. | Delivery failure | ERROR through the nonrecursive emergency path |
| Intelligence signal/degradation | An intelligence component produced a signal or selected a deterministic fallback. | Domain fact | INFO or WARNING |
| Workflow control/progress | Pause, resume, cancel, and progress state changed. | Runtime notification | INFO or WARNING according to state |

## Ownership matrix

| Operational fact | Canonical owner | Canonical event family | Notes |
|---|---|---|---|
| Workflow, wave, and node lifecycle | Runtime event publishers and runtime telemetry mapping | `runtime.*`, `workflow_progress.*`, `workflow_control.*` | Module logs must not recreate lifecycle events. |
| Runtime node retry | Runtime node executor/event publisher | `runtime.node.retrying` | Each independently timed attempt receives its own operation span. |
| Application-service lifecycle | `ServiceRunner` through `ApplicationServiceTelemetry` | `application.service.*` | Includes configuration failure, retry, degradation, completion, failure, and cancellation. |
| Successful partial service result | `ServiceRunner` from typed `ServiceDegradation` records | `application.service.degraded` | Provider exceptions remain owned by provider telemetry. |
| Provider operation | `record_provider_call()` through `IntegrationTelemetry` | `integration.provider.call` | One terminal provider result with typed exception details on failure. |
| Client retry | The integration client through `IntegrationTelemetry` | `integration.client.retry_scheduled` | Emitted only when another request attempt will occur. |
| Policy evaluation | Policy engine and `PolicyTelemetry` | `runtime.policy.*` | Typed denial is not an unexpected exception. |
| Governance evaluation | Governance engine and `GovernanceTelemetry` | `runtime.governance.*` | Preserves fail-closed semantics. |
| EventBus subscriber failure | `EventBus` | Runtime system-warning mapping | Includes original event and failed handler identity. |
| Plugin lifecycle failure | Plugin lifecycle manager | `plugin.lifecycle.hook_failed` | One event per failed hook. |
| Runtime lifecycle hook failure | Runtime lifecycle manager | `runtime.lifecycle.hook_failed` | One event per failed hook. |
| Intelligence fallback | `IntelligenceTelemetry` | `intelligence.agent.degraded` | Emitted before a deterministic LLM fallback is returned. |
| RAG operation | Focused RAG service through `ApplicationRagTelemetry` | `application.rag.operation.*` | Readiness, security, retrieval, projection, and generation degradation use the same owner. |
| Persistence result | Calling application/runtime boundary | Owner-specific service/runtime event | Repositories roll back and re-raise; they do not duplicate the owning event. |
| Completed-run archival degradation | `WorkflowEngine` safe archival boundary | Direct fallback record until a dedicated post-terminal runtime event exists | The archive and repository no longer log the same exception. |
| Bootstrap/configuration failure | Bootstrap configuration telemetry; emergency logger before observability exists | `platform.bootstrap.configuration_failed` | Sensitive configuration values are sanitized. |
| Telemetry sink delivery failure | `TelemetryCollector` emergency path | Direct emergency log plus `telemetry.sink.failures` metric | Must not recursively emit through the failed collector. |
| PostgreSQL telemetry persistence | Telemetry persistence sink and mapper | Canonical event/trace records | Event evidence is immutable; operation spans are assembled by canonical span identity. |
| OpenTelemetry representation | `OpenTelemetrySink` | Canonical operation spans and span events | Jaeger receives the same parent map represented in PostgreSQL. |
| CLI presentation failure | CLI boundary | Rendered failure envelope; direct log only when telemetry cannot be reached | Must not duplicate an already emitted workflow or RAG failure. |

## Severity policy

| Severity | Required use |
|---|---|
| DEBUG | High-volume diagnostic detail that is disabled during normal operation. |
| INFO | Successful lifecycle transitions, ordinary domain signals, and successful external outcomes. |
| WARNING | Retry scheduled, cancellation, partial success, optional dependency unavailable, fallback selected, or materially degraded output. |
| ERROR | Terminal operation failure, required callback failure, telemetry delivery failure, or invalid required configuration after telemetry is available. |
| CRITICAL | Required startup infrastructure cannot be constructed and no canonical telemetry path is available. |

Expected parsing, coercion, and normalization failures remain quiet when they are part of the documented input contract and do not reduce correctness or completeness. Typed validation, policy, and governance outcomes do not receive exception tracebacks unless an unexpected exception caused the outcome.

## Exception-capture policy

1. The canonical owner receives the original `BaseException`, not only `str(error)`.
2. The owner creates one immutable `TelemetryExceptionDetails` snapshot.
3. Exception type, message, stack trace, and truncation state are sanitized and bounded before reaching any sink.
4. The default maximums are 256 characters for exception type, 4 KiB for message, and 32 KiB for stack trace.
5. The same snapshot feeds structured logging, PostgreSQL, and OpenTelemetry.
6. Intermediate layers that only roll back, clean up, or re-raise do not log or emit the same exception.
7. Cancellation is re-raised after its owning cancellation event and is never normalized into an ordinary failure.
8. Validation and expected typed denials remain traceback-free.

## Retry and degradation policy

### Retry

A retry event is emitted only when a next attempt will actually occur. It includes bounded operational fields such as:

- provider, client, service, and operation name;
- current, next, and maximum attempt;
- scheduled backoff;
- retryable status or exception type;
- active trace context.

The retry event is nonterminal. The final successful or failed attempt owns the terminal event and terminal exception details.

### Degradation

A degradation event is required when the requested operation succeeds but materially changes because of a missing source, fallback implementation, optional dependency failure, sanitization action, or reduced retrieval coverage.

- Degraded completion uses WARNING severity with `success=True`.
- Terminal failure uses ERROR with `success=False`; it is not labeled as degradation.
- Application services return typed `ServiceDegradation` records and let `ServiceRunner` emit one aggregate degradation event.
- Intelligence and RAG use their focused telemetry owners.
- Expected coercion defaults remain quiet unless they alter the requested result.

## Direct-logging exceptions

The absence of `logging.getLogger(__name__)` is correct when a module's lifecycle facts are already owned by canonical telemetry. A logger is not a required service dependency and must not be added merely for consistency.

Direct WARNING/ERROR/CRITICAL logging is restricted to these cases:

| Boundary | Current files | Justification |
|---|---|---|
| Telemetry infrastructure emergency | `core/telemetry/collectors/telemetry_collector.py` | The collector cannot report its own sink failure through itself without recursion. |
| Bootstrap before/while telemetry is unavailable | `core/telemetry/emitters/bootstrap_configuration_telemetry.py` | Required configuration failures need a sanitized visible record before canonical delivery is reliable. |
| Post-terminal workflow archival fallback | `core/workflow/execution/workflow_engine.py` | Archival is best effort and must not replace a completed workflow result; lower persistence layers re-raise without duplicate logs. |
| Partial child-source integration degradation | Yahoo Finance, Federal Reserve, FRED, Finnhub clients and the live macro provider | A bounded child source failed while the parent provider may still return a partial result. These logs must not report the parent provider's terminal outcome. |
| CLI request-scope/presentation escape | `interfaces/cli/services/rag_command_service.py` | Composition or presentation can fail before canonical RAG telemetry is reachable. |

`tests/unit/telemetry/test_observability_architecture.py` maintains the allowlist. Removal of an allowed direct log does not fail the test; adding a new operational direct-log site requires an explicit ownership decision and ledger update.

INFO logs used only for human-facing startup or command narration are outside this operational-failure allowlist, but must not duplicate canonical lifecycle events.

## Metrics and cardinality policy

Canonical telemetry is projected into metrics by `DomainMetricsRecorder`; application, runtime, client, and callback code must not create parallel metric paths.

Required operational metric families include:

- application-service configuration failures, retries, and degradations;
- integration-client retries and provider outcomes;
- telemetry-sink failures;
- plugin/runtime callback and EventBus subscriber failures;
- bootstrap configuration failures;
- runtime workflow/node lifecycle and duration;
- RAG lifecycle and quality outcomes.

Allowed labels are stable bounded names such as:

- `service_name`;
- `component_name`;
- `provider_name`;
- `operation`;
- `event_type`;
- `outcome`.

Forbidden labels include:

- request, execution, event, trace, or span IDs;
- exception messages or stack traces;
- URLs;
- symbols or document identifiers;
- arbitrary user input;
- any other unbounded value.

Detailed correlation and exception data belongs in structured logs, PostgreSQL, and traces—not Prometheus labels.

## Trace and persistence policy

- One `trace_id` identifies one end-to-end trace.
- One `span_id` identifies one bounded operation instance.
- One `parent_span_id` identifies the immediate parent operation.
- One `event_id` identifies one immutable telemetry event.
- Workflow, node attempt, service attempt, provider call, and independently timed client/datastore work are operation spans.
- Retry, progress, warning, and degradation facts are events on the owning operation unless the retry itself is independently timed work.
- PostgreSQL stores every event by `event_id` and exactly one assembled trace row per `(trace_id, span_id)`.
- OpenTelemetry exports one span per canonical operation and attaches applicable event and exception data.

See `.docs/canonical_trace_lifecycle.md` for the complete lifecycle contract.

## Regression coverage

| Boundary | Focused contract coverage |
|---|---|
| Canonical event identity, serialization, and exception bounds | `tests/unit/telemetry/test_telemetry_event.py` |
| Canonical imports and direct-log allowlist | `tests/unit/telemetry/test_observability_architecture.py` |
| Structured logging and exactly-once traceback | `tests/unit/telemetry/test_telemetry_logger.py` |
| Collector failure isolation and emergency reporting | `tests/unit/telemetry/test_telemetry_collector.py` |
| Service lifecycle, retry, degradation, cancellation | ServiceRunner and application telemetry unit tests |
| Provider and client telemetry | Integration telemetry/provider/client unit tests |
| Runtime/EventBus/plugin/policy/governance | Focused runtime and plugin telemetry tests |
| RAG and intelligence degradation | RAG and intelligence telemetry tests |
| Metrics and bounded labels | Domain metrics, Prometheus exporter, and deployment configuration tests |
| PostgreSQL event/trace persistence | Mapper, serializer, repository, migration, and gated PostgreSQL integration tests |
| OpenTelemetry topology | OpenTelemetry sink tests and gated live PostgreSQL/Jaeger topology test |
| End-to-end canonical paths | `tests/integration/telemetry/test_telemetry_coverage_audit.py` |

The architecture does **not** require every Python file to define a logger. Regression coverage protects canonical owners and delivery boundaries rather than counting logger declarations.

## Final audit disposition

- [x] One canonical telemetry event and typed exception contract.
- [x] Nonrecursive collector/runtime/persistence sink failure visibility.
- [x] Structured logging with exactly-once traceback rendering.
- [x] Service configuration, retry, degradation, failure, and cancellation coverage.
- [x] Typed service degradation and removal of duplicate service warnings.
- [x] Provider exception snapshots and client retry visibility.
- [x] Runtime, EventBus, plugin, policy, and governance fan-out coverage.
- [x] Bootstrap and configuration-failure observability.
- [x] Canonical trace propagation, OpenTelemetry topology, and PostgreSQL span assembly.
- [x] Stable Prometheus metrics, alert rules, dashboard mappings, and bounded labels.
- [x] Canonical event and exception persistence in PostgreSQL.
- [x] RAG and intelligence degradation/failure ownership.
- [x] Duplicate completed-run repository/archive logging removed; workflow archival fallback remains the single visible owner.
- [x] Focused architecture and boundary regression tests.
