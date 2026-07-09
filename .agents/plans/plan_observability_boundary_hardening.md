  # Structured Observability Coverage Audit and Canonical Boundary Hardening

  ## Summary

  Perform a production-wide observability audit across application/, core/, integration/, intelligence/, and interfaces/, including RAG. The implementation will ensure that:

  - Each operational fact has one canonical owner and is emitted once.
  - The same canonical event is fanned out to logging, metrics, tracing, and PostgreSQL rather than recreated independently.
  - Unexpected exceptions retain sanitized tracebacks.
  - Recoverable retries and degraded outcomes are visible and trace-correlated.
  - Invalid configuration and telemetry sink failures are observable.
  - Expected parsing, validation, and normalization failures do not create noisy logs.
  - Telemetry failures remain non-fatal unless fail-fast behavior is explicitly configured.

  The initial audit has already identified concrete gaps in ServiceRunner, TelemetryCollector, TelemetryLogger, the OpenTelemetry sink, client retry loops, partial-success services, and several asynchronous fan-out boundaries.

  ## Canonical Event Ownership Rules

   Operational fact                            Canonical owner                                          Severity
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━
   Workflow or runtime-node lifecycle          Runtime event publisher/EventBus                         INFO, WARNING, or ERROR
  ──────────────────────────────────────────  ───────────────────────────────────────────────────────  ─────────────────────────
   Application-service lifecycle               ServiceRunner                                            INFO, WARNING, or ERROR
  ──────────────────────────────────────────  ───────────────────────────────────────────────────────  ─────────────────────────
   Successful but incomplete service result    ServiceRunner, from typed service degradation records    WARNING
  ──────────────────────────────────────────  ───────────────────────────────────────────────────────  ─────────────────────────
   Provider call outcome                       record_provider_call()                                   INFO, WARNING, or ERROR
  ──────────────────────────────────────────  ───────────────────────────────────────────────────────  ─────────────────────────
   Internal HTTP/client retry                  Client integration telemetry                             WARNING
  ──────────────────────────────────────────  ───────────────────────────────────────────────────────  ─────────────────────────
   Policy or governance evaluation             Policy/Governance engine                                 INFO or ERROR
  ──────────────────────────────────────────  ───────────────────────────────────────────────────────  ─────────────────────────
   Intelligence fallback or degraded signal    Intelligence telemetry                                   WARNING
  ──────────────────────────────────────────  ───────────────────────────────────────────────────────  ─────────────────────────
   RAG operation lifecycle                     ApplicationRagTelemetry                                  INFO, WARNING, or ERROR
  ──────────────────────────────────────────  ───────────────────────────────────────────────────────  ─────────────────────────
   Bootstrap/configuration failure             Composition root                                         ERROR or CRITICAL
  ──────────────────────────────────────────  ───────────────────────────────────────────────────────  ─────────────────────────
   Telemetry sink failure                      Collector emergency logging and internal metric          ERROR
  ──────────────────────────────────────────  ───────────────────────────────────────────────────────  ─────────────────────────
   Expected parsing/coercion fallback          No event unless it degrades the operation                None

  A lower-level provider failure and an upper-level degraded service result are different operational facts and may both be recorded. The same exception must not be independently logged again at every layer.

  ## Implementation Steps

  ### 1. Produce the observability coverage ledger — Completed

  - Inventory production exception handlers, retries, asyncio.gather(return_exceptions=True) calls, fallback branches, configuration validation, external calls, and direct logging.
  - Trace each site through producer → boundary owner → telemetry emitter → collector → logging/metrics/tracing/PostgreSQL sinks.
  - Classify every catch site as:
      - expected conversion or input normalization;
      - re-raised for an owning boundary;
      - terminal failure;
      - recoverable retry;
      - degraded/fallback operation;
      - telemetry-infrastructure failure.

  - Record ownership, required severity, trace-context source, metrics, and current gap in .docs/observability_coverage_ledger.md.
  - Use this ledger as the remediation checklist and document intentional no-log cases to prevent later blanket logging.

  ### 2. Consolidate the canonical telemetry event contract — Completed

  - Extend the active TelemetryEvent with first-class:
      - event_id;
      - trace_id;
      - span_id;
      - parent_span_id;
      - optional typed TelemetryExceptionDetails.

  - Define TelemetryExceptionDetails as an immutable, serializable contract containing exception type, message, and a sanitized, bounded stack trace.
  - Default traceback retention to 32 KiB per event, with an explicit truncation marker.
  - Populate trace fields directly from TelemetryContext instead of hiding them only inside attributes.
  - Preserve boundary deserialization of historical events that lack the new fields.
  - Remove the unused competing core.telemetry.contracts.telemetry_event.TelemetryEvent definition and export only the canonical event contract.
  - Update attribution and runtime-event conversion paths so they preserve all new fields.

  ### 3. Make sink fan-out failures visible without recursion — Completed

  - Change TelemetryCollector to inspect every asyncio.gather() result instead of silently discarding sink exceptions.
  - For each failed sink:
      - produce one standard Python emergency log with traceback;
      - include sink name, canonical event ID/type, trace ID, span ID, and correlation ID;
      - increment telemetry.sink.failures;
      - continue delivering to unaffected sinks when fail-fast is disabled.

  - Do not emit another TelemetryEvent for a sink failure because doing so could recursively invoke the failing sink.
  - Preserve fail-fast behavior by logging the failure and then re-raising it.
  - Apply equivalent defensive handling to collector flush and shutdown operations.

  ### 4. Strengthen structured logging output — Completed

  - Update TelemetryLogger so every record exposes event, trace, span, correlation, workflow, execution, runtime, node, and severity fields at the top level of structured log data.
  - Include concise event and trace identifiers in the human-readable message so context remains visible even with a basic Python formatter.
  - Render the sanitized traceback exactly once when TelemetryExceptionDetails is present.
  - Continue sanitizing attributes, payloads, and exception data before they cross the logging boundary.
  - Reserve direct module logging for:
      - telemetry-infrastructure failures that cannot safely emit telemetry;
      - bootstrap failures occurring before observability is available;
      - interface presentation failures where no canonical telemetry context exists.

  ### 5. Complete ServiceRunner lifecycle coverage — Completed

  Add canonical application-service events:

  - application.service.configuration_failed — ERROR.
  - application.service.retry_scheduled — WARNING for each non-terminal failed attempt.
  - application.service.degraded — WARNING for successful but incomplete execution.
  - Preserve existing started, completed, failed, cancelled, validation, and policy-denial outcomes.

  Implementation behavior:

  - Emit configuration failure before returning an invalid-runner result when telemetry is enabled.
  - Carry the original exception into terminal failure telemetry so its traceback is not lost by conversion to a string.
  - Emit a retry event only when another attempt will actually occur.
  - Include attempt, next attempt, maximum attempts, backoff, reason, and error type.
  - Do not emit a separate attempt-failed event for the terminal attempt; the terminal application.service.failed event owns that fact.
  - Preserve cancellation semantics and never retry CancelledError.
  - Keep validation and policy failures traceback-free because they are typed operational outcomes, not unexpected exceptions.

  ### 6. Add typed degraded-service outcomes — Completed

  - Add a first-class immutable ServiceDegradation contract and a degradations tuple on ServiceResult.
  - Include stable fields such as code, component/source, summary, and error type; do not place these fields in generic result metadata.
  - Update partial-success services such as News and Sentiment to:
      - collect degradation records while processing concurrent provider results;
      - return them with the successful result;
      - stop issuing parallel local warning logs.

  - Have ServiceRunner emit one aggregate application.service.degraded event before application.service.completed.
  - Keep provider exception tracebacks owned by provider-call telemetry; the service degradation event records the higher-level partial-success outcome without duplicating those exceptions.

  ### 7. Add provider and client retry visibility — Completed

  - Enhance record_provider_call() to attach the original exception snapshot to terminal provider failure events.
  - Add integration.client.retry_scheduled to IntegrationTelemetry.
  - Instrument bounded HTTP retry loops, beginning with Yahoo Finance, with:
      - provider/client and operation names;
      - current and next attempts;
      - maximum attempts and backoff;
      - status code or exception type;
      - active trace context.

  - Emit retry telemetry only when another attempt will occur.
  - Continue emitting exactly one final provider outcome around the complete provider operation.
  - Audit all integration clients using return_exceptions=True and ensure each result is explicitly handled rather than silently discarded.

  ### 8. Audit runtime, workflow, plugin, policy, and governance fan-out — Completed

  - Verify runtime retries continue through the existing typed NODE_RETRYING event rather than adding a parallel telemetry path.
  - Confirm EventBus subscriber failures are emitted once with handler identity, original event identity, trace context, and exception details.
  - Add missing visibility to plugin lifecycle fan-out, where hook exceptions are currently gathered and discarded.
  - Preserve fail-closed policy and governance results while attaching exception diagnostics to their existing canonical telemetry events.
  - Verify runtime wave exceptions and timeout conversions retain the original trace relationship and produce one terminal node event.
  - Do not add local logging where an existing runtime event already owns the failure.

  ### 9. Add bootstrap and configuration-failure observability — Completed

  - Validate telemetry, OpenTelemetry, Prometheus, persistence, provider, and workflow configuration at their composition roots.
  - When observability is available, emit a canonical configuration-failure event with component, invalid setting names, and trace/correlation context.
  - When observability cannot be constructed, use one CRITICAL emergency log with traceback and sanitized configuration details.
  - Never log credentials, API keys, database passwords, headers, tokens, or complete connection URLs.
  - Distinguish optional-integration degradation from required-platform initialization failure:
      - optional component unavailable: WARNING and continue;
      - required component invalid/unavailable: ERROR or CRITICAL and fail startup.

  ### 10. Correct OpenTelemetry trace and exception mapping — Completed

  - Map canonical event IDs and trace fields directly rather than looking them up from arbitrary payload or attribute dictionaries.
  - Use canonical trace, span, and parent-span identities to create real OpenTelemetry parent-child relationships, not merely span attributes with matching text.
  - Add an OpenTelemetry exception event containing sanitized semantic fields:
      - exception.type;
      - exception.message;
      - exception.stacktrace.

  - Set span status to ERROR for terminal failures and exception-bearing error events.
  - Keep WARNING degraded and retry spans non-error unless the underlying event represents a failed operation.
  - Preserve trace context across asyncio.create_task() and concurrent gather operations.

  ### 10A — Define and verify canonical span semantics

  - [x] Define the canonical invariant: one `trace_id` per end-to-end trace, one `span_id` per bounded operation instance, one `parent_span_id` per immediate parent operation, and one `event_id` per telemetry event.
  - [x] Audit workflow, runtime-node, service, provider, client, datastore, and model-call boundaries through producer → context → event → collector → PostgreSQL/OpenTelemetry → consumer.
  - [x] Classify current uses as real operation spans, span events, or correlation-only fields.
  - [x] Mark the Step 10 anchor mapping as an interim workaround superseded by Steps 10A–10E.
  - [x] Add executable expected-failure contracts that expose event-to-span duplication and PostgreSQL trace conflict-discard behavior until the corrective implementation lands.

  ### 10B — Establish real operation-span boundaries

  - [x] Keep `TraceContext` vendor-neutral while removing the ambiguous logical-scope interpretation.
  - [x] Create a distinct child trace context for each workflow execution, runtime node attempt, application service attempt, provider call, and separately timed external operation.
  - [x] Give retry attempts distinct span identities when they are independently timed operations.
  - [x] Associate warnings, progress, retry, and degradation notifications with their owning operation instead of exporting them as independent spans.
  - [x] Preserve cancellation and concurrent-task context propagation.

  ### 10C — Separate span lifecycle from event export

  - [x] Stop converting every `TelemetryEvent` into a new OpenTelemetry span.
  - [x] Export one completed span for each canonical operation and attach applicable operational events and exception details to it.
  - [x] Use canonical trace/span identities as actual exported identities.
  - [x] Remove the bounded canonical-span anchor map and remote-anchor workaround.
  - [x] Handle incomplete lifecycles without leaking unbounded in-memory state.

  ### 10D — Correct PostgreSQL trace persistence

  - [x] Persist every telemetry event independently by canonical `event_id`.
  - [x] Persist exactly one `telemetry_traces` record per canonical span.
  - [x] Update terminal status, end time, duration, and failure details deterministically instead of discarding trace-record conflicts.
  - [x] Add destructive schema cleanup or migration changes required by the corrected contract; retain no obsolete trace compatibility behavior.

  ### 10E — Verify complete trace topology

  - [x] Verify workflow → node attempt → service attempt → provider/client/datastore parentage.
  - [x] Verify retries and concurrent branches receive distinct child span identities under one trace.
  - [x] Verify lifecycle events assemble into one complete PostgreSQL span record.
  - [x] Verify in-memory OpenTelemetry export and live Jaeger show the same canonical hierarchy.
  - [x] Remove the Step 10 expected-failure markers after all corrected contracts pass.

  ### 11. Complete metrics and external observability coverage

  Add stable, low-cardinality metrics for:

  - application.service.configuration_failures;
  - application.service.retries;
  - application.service.degraded;
  - integration.client.retries;
  - telemetry.sink.failures;
  - plugin/subscriber callback failures;
  - bootstrap configuration failures.

  Rules:

  - Labels may include stable service, component, provider, operation, event type, and outcome names.
  - Never use request IDs, event IDs, trace IDs, exception messages, URLs, symbols, or user input as Prometheus labels.
  - Update existing Prometheus mappings and Grafana dashboards/alerts for retry spikes, degraded service rates, sink failures, and configuration failures.
  - Keep detailed exception data in logs, traces, and PostgreSQL—not metric labels.

  ### 12. Preserve exception and trace data in PostgreSQL

  - Update telemetry persistence mapping to use the canonical event ID rather than generating a separate sink-specific identity.
  - Persist trace IDs in the existing first-class columns.
  - Serialize the typed exception snapshot into the telemetry event JSONB payload.
  - Populate the existing message field from the canonical event or exception message where appropriate.
  - Sanitize and bound exception data before persistence.
  - No schema migration is expected because the database already provides event identity, trace columns, message, and JSONB payload storage.

  ### 13. Remediate remaining production exception and fallback gaps

  Apply the audit rules across the remaining production packages:

  - Convert meaningful RAG, intelligence, persistence, and CLI fallback logs to their existing canonical telemetry owners where one exists.
  - Retain direct interface logging only for rendering or startup failures that cannot reach telemetry.
  - Leave expected parsing and coercion fallbacks quiet unless they materially alter the requested result.
  - Avoid unrelated refactoring in churn-heavy files; observability edits must remain surgical.

  ### 14. Documentation and regression guardrails

  - Finalize .docs/observability_coverage_ledger.md with:
      - event taxonomy;
      - ownership matrix;
      - severity policy;
      - exception-capture policy;
      - retry and degradation policy;
      - direct-logging exceptions;
      - metrics cardinality rules.

  - Add an architecture test ensuring only the canonical TelemetryEvent is imported.
  - Add focused tests around every canonical boundary instead of a brittle test that requires every Python file to contain a logger.
  - Document that absence of logging.getLogger(__name__) is correct when lifecycle events are already owned by telemetry.

  ## Public Contract Changes

  - TelemetryEvent gains canonical event identity, direct trace fields, and optional typed exception details.
  - New TelemetryExceptionDetails immutable serialization contract.
  - ServiceResult gains a first-class tuple of ServiceDegradation records.
  - ApplicationServiceTelemetry gains configuration-failure, retry, and degraded event methods.
  - IntegrationTelemetry gains client-retry telemetry.
  - TelemetryCollector.emit() internally reports sink-delivery failures to ObservabilityManager; external emitter behavior remains asynchronous and non-fatal by default.
  - Historical serialized telemetry remains readable at the serialization boundary, but no parallel internal telemetry event model will be retained.

  ## Test Plan

  - Telemetry event round-trip tests for event ID, trace hierarchy, exception details, sanitization, and historical payload compatibility.
  - Logger tests confirming severity, structured context, and exactly one visible traceback.
  - Collector tests with one healthy and one failing sink, including fail-fast and non-fail-fast behavior.
  - ServiceRunner tests for invalid configuration, validation failure, policy denial, retry-then-success, retry exhaustion, unexpected exception, cancellation, and degraded success.
  - News and Sentiment tests verifying one aggregate degradation event and no duplicate warning logs.
  - Provider/client tests for retry visibility, successful recovery, terminal failure, cancellation, and trace propagation.
  - Runtime/EventBus/plugin tests for concurrent callback failures and exactly-once failure reporting.
  - OpenTelemetry exporter tests for canonical trace IDs, actual parent-child relationships, exception events, and error status.
  - PostgreSQL mapper and live integration tests confirming exception and trace persistence.
  - Prometheus tests confirming counters and bounded labels.
  - End-to-end workflow test injecting a provider retry, partial degradation, and terminal failure and asserting the exact event counts across the in-memory sink.
  - Final verification in project order: Ruff fixes, Ruff formatting, MyPy, focused tests, full test suite, and Graphify update.

  ## Assumptions

  - The audit covers all production code, including RAG, while excluding tests, generated files, caches, and third-party code.
  - Sanitized tracebacks are retained in logging, PostgreSQL telemetry, and OpenTelemetry.
  - Tracebacks default to a 32 KiB maximum per event.
  - PostgreSQL remains the system of record; logs and OpenTelemetry are external representations of the same canonical event.
  - No blanket requirement will be introduced for every module or service to declare a logger.
  - Core telemetry changes are architecturally necessary because event identity, trace propagation, sink behavior, and exception representation are core cross-platform contracts.

  ## Step Results

  ### Step 1 — Produce the observability coverage ledger

  **Status:** Completed on July 1, 2026.

  **Changes:**

  - Created `.docs/observability_coverage_ledger.md` as the canonical remediation ledger.
  - Audited production code under `application/`, `core/`, `integration/`, `intelligence/`, and `interfaces/`, including RAG.
  - Classified all 163 production exception handlers into the six plan categories.
  - Recorded all 15 `asyncio.gather(..., return_exceptions=True)` fan-out sites and their required ownership disposition.
  - Documented canonical producer → owner/emitter → collector → logging/metrics/tracing/PostgreSQL paths.
  - Documented external HTTP/datastore boundaries, severity rules, exception/traceback policy, metric-cardinality rules, direct-logging exceptions, intentional no-log cases, and the remediation checklist.
  - Added Repowise health/risk guardrails for the churn-heavy `ServiceRunner`, high-coupling provider telemetry helper, telemetry collector, logger, and OpenTelemetry sink.

  **Key findings:**

  - Sink failures are silently discarded by `TelemetryCollector`, runtime telemetry fan-out, and the optional PostgreSQL telemetry sink when fail-fast is disabled.
  - `ServiceRunner` lacks canonical configuration-failure, retry-scheduled, and degraded-success events, and terminal exceptions currently lose traceback data.
  - News and sentiment partial-success warnings, several RAG exception logs, and some integration client warnings duplicate or bypass canonical ownership.
  - Plugin/runtime lifecycle non-fail-fast fan-out discards callback exceptions.
  - Intelligence LLM fallbacks can return successful node outputs without warning-level degradation telemetry.
  - OpenTelemetry and PostgreSQL mappings derive trace/event identity from generic dictionaries rather than first-class canonical fields.

  **Verification:**

  - AST census total verified: `23 + 46 + 53 + 1 + 38 + 2 = 163` classified catch sites.
  - Documentation-only step; no production code or tests were changed.

  ### Step 2 — Consolidate the canonical telemetry event contract

  **Status:** Completed on July 1, 2026.

  **Changes:**

  - Extended the canonical `core.telemetry.events.TelemetryEvent` with generated `event_id`, direct `trace_id`, `span_id`, and `parent_span_id` fields, plus optional typed `TelemetryExceptionDetails`.
  - Added immutable exception serialization with sanitized exception type/message/stack trace, a 32 KiB default stack-trace budget, and an explicit truncation marker.
  - Preserved historical event deserialization by generating missing event IDs, accepting the former `severity` key, and promoting legacy trace identities from `attributes` into first-class fields.
  - Updated `TelemetryEmitter`, `ApplicationServiceTelemetry`, `ApplicationRagTelemetry`, `ObservabilityManager`, and `TelemetryLifecycleEvent` to populate direct trace fields while retaining current attribute mirrors for downstream compatibility.
  - Updated telemetry attribution to preserve event identity, trace hierarchy, and exception details.
  - Updated runtime-to-core telemetry conversion to promote trace and correlation identity from runtime payloads.
  - Removed the unused competing `core/telemetry/contracts/telemetry_event.py` model; `core.telemetry.contracts.TelemetryEvent` now re-exports the canonical event class.
  - Added focused tests for canonical export identity, complete round trips, historical compatibility, secret sanitization, 32 KiB truncation, attribution preservation, runtime conversion, and emitter trace propagation.

  **Architectural guardrail:**

  - Repowise identified the canonical event and trace context as high-coupling core contracts. The implementation therefore remained limited to the event envelope and required conversion paths; sink-failure handling, logger rendering, OpenTelemetry mapping, and PostgreSQL persistence remain assigned to later plan steps.

  **Verification:**

  - Focused telemetry suite: `73 passed`.
  - MyPy: `Success: no issues found in 1079 source files`.
  - Ruff check/fix and formatting passed for all changed Python files.
  - Graphify refreshed successfully: `18,065 nodes`, `79,006 edges`, `634 communities`.
  - No external services were required for this step.

  ### Step 3 — Make sink fan-out failures visible without recursion

  **Status:** Completed on July 1, 2026.

  **Changes:**

  - Updated `TelemetryCollector` to inspect every non-fail-fast `asyncio.gather()` result and report each failed sink exactly once.
  - Added one direct Python `ERROR` emergency log per sink failure with the original traceback, sink/operation identity, canonical event ID/type, trace ID, span ID, and correlation ID.
  - Added the low-cardinality `telemetry.sink.failures` counter with only sink class and lifecycle operation attributes; no recursive `TelemetryEvent` is emitted.
  - Preserved fail-fast behavior by logging and counting the failure before re-raising, while non-fail-fast fan-out continues delivering to healthy sinks.
  - Preserved cancellation semantics by re-raising sink `CancelledError` results rather than converting them into ordinary telemetry failures.
  - Applied the same defensive logging, metric, continuation, and fail-fast rules to `force_flush()` and `shutdown()`.
  - Made `ObservabilityManager` and its collector share one `MetricsStore`, ensuring collector-internal failure counters are visible through the canonical observability metrics boundary.
  - Added focused tests for healthy-sink continuation, traceback/context logging, metric recording, emit fail-fast behavior, lifecycle continuation, lifecycle fail-fast behavior, and manager-level metric visibility.

  **Architectural guardrail:**

  - Repowise identified `ObservabilityManager` as a churn-heavy central hotspot with 44 dependents. The implementation therefore kept failure handling inside the collector and limited the manager change to shared metrics-store composition. Sink failures use direct emergency logging because emitting another telemetry event could recursively invoke the failing sink.

  **Verification:**

  - Telemetry unit suite: `49 passed`.
  - Observability/bootstrap integration tests: `15 passed`.
  - MyPy: `Success: no issues found in 1080 source files`.
  - Ruff check/fix and formatting passed for all Step 3 Python files.
  - Graphify refreshed successfully: `18,091 nodes`, `79,127 edges`, `644 communities`.
  - No external services were required for this step.

  ### Step 4 — Strengthen structured logging output

  **Status:** Completed on July 1, 2026.

  **Changes:**

  - Updated `TelemetryLogger` so canonical event identity, severity, workflow/execution/runtime/node context, correlation identity, and trace/span hierarchy are exposed both in the existing nested `telemetry` mapping and as top-level Python `LogRecord` fields.
  - Preserved the existing `level` field for compatibility and added the explicit canonical `severity` field.
  - Added concise `event_id`, `trace_id`, `span_id`, and `correlation_id` context to the human-readable log message so basic Python formatters retain operational correlation.
  - Added sanitized `exception_details` metadata containing exception type, message, and truncation status.
  - Rendered the sanitized stack trace exactly once in the human-readable message and intentionally omitted it from structured metadata; `exc_info` remains unset so Python formatters cannot append a duplicate traceback.
  - Preserved payload and attribute redaction and the existing options that omit those fields from logging output.
  - Extended focused tests to verify flattened and nested structured fields, severity mapping, message correlation identifiers, secret redaction, original-event immutability, and exactly-once traceback rendering.

  **Architectural guardrail:**

  - Repowise reports `TelemetryLogger` as stable and healthy (`9.85`) with no test gap. The change therefore preserved its public sink contract and existing nested `telemetry` representation while strengthening only the logging boundary representation. No emitter, event, bootstrap, or downstream domain behavior was changed.

  **Verification:**

  - Telemetry unit suite: `50 passed`.
  - Bootstrap and telemetry-coverage integration tests: `16 passed`.
  - MyPy: `Success: no issues found in 1080 source files`.
  - Ruff check/fix and formatting passed for all Step 4 Python files.
  - Graphify refreshed successfully: `18,092 nodes`, `79,132 edges`, `645 communities`.
  - No external services were required for this step.



  ### Step 5 — Complete ServiceRunner lifecycle coverage

  **Status:** Completed on July 1, 2026.

  **Changes:**

  - Added canonical `application.service.configuration_failed`, `application.service.retry_scheduled`, and `application.service.degraded` event methods to `ApplicationServiceTelemetry` with the planned ERROR/WARNING severities.
  - Updated `ServiceRunner` to emit one configuration-failure event before returning an invalid-runner result, including the typed validation errors and safe runner settings.
  - Updated the retry loop to emit `application.service.retry_scheduled` only for non-terminal failed attempts, immediately before the configured backoff and actual next attempt.
  - Included current attempt, next attempt, maximum attempts, backoff duration, failure reason, error type, request identity, and propagated trace context in retry telemetry.
  - Preserved the original terminal exception object through `ServiceRunner` and attached a sanitized bounded `TelemetryExceptionDetails` snapshot to the single terminal `application.service.failed` event.
  - Kept validation failures, policy denials, configuration failures, retries, and cancellations traceback-free; `CancelledError` is still re-raised immediately and is never retried.
  - Established the `application.service.degraded` emitter contract without prematurely changing `ServiceResult`; Step 6 remains responsible for typed `ServiceDegradation` results and aggregate degraded-event triggering.
  - Added focused tests for invalid configuration, retry-then-success ordering and payloads, retry exhaustion, exactly one terminal exception snapshot, cancellation with retries enabled, traceback-free typed outcomes, and all three new emitter contracts.

  **Architectural guardrail:**

  - Repowise identified `ServiceRunner` as a churn-heavy hotspot (`7.69` health, top 11% repository churn) and `ApplicationServiceTelemetry` as high-coupling. The implementation therefore preserved public service execution contracts and changed only canonical lifecycle emission and the minimum retry-state handling required by this step. Metrics mapping remains assigned to Step 11, and typed partial-success behavior remains assigned to Step 6.

  **Verification:**

  - Focused ServiceRunner and telemetry unit tests: `28 passed`.
  - Telemetry coverage integration tests: `2 passed`.
  - MyPy: `Success: no issues found in 1080 source files`.
  - Ruff check/fix and formatting passed for all Step 5 Python files.
  - Graphify refreshed successfully: `18,104 nodes`, `79,209 edges`, `631 communities`.
  - No external services were required for this step.

  ### Step 6 — Add typed degraded-service outcomes

  **Status:** Completed on July 1, 2026.

  **Changes:**

  - Added the immutable `ServiceDegradation` contract with first-class `code`, `component`, `summary`, and optional `error_type` fields.
  - Added a `degradations` tuple to `ServiceResult`, preserved it through `ServiceRunner` runtime metadata enrichment, and included it in boundary serialization.
  - Updated `NewsService` and `SentimentService` to collect typed degradation records for failed provider calls and invalid provider payloads while preserving successful partial results.
  - Removed the services' parallel local warning logs so provider-call telemetry remains the owner of provider exception tracebacks.
  - Updated `ServiceRunner` to emit exactly one aggregate `application.service.degraded` event before `application.service.completed` whenever a successful result contains degradations.
  - Kept degraded events traceback-free and included only typed degradation details, request identity, attempt count, duration, and degradation count.
  - Added focused tests for result serialization, degradation preservation, event ordering, one aggregate event for News and Sentiment partial success, and absence of duplicate service warning logs.

  **Architectural guardrail:**

  - Repowise identified `ServiceRunner`, `NewsService`, and `SentimentService` as churn-heavy hotspots. The implementation therefore preserved the existing service and `_execute()` contracts, introduced no persistence changes, and limited changes to typed partial-success propagation and canonical telemetry ownership.

  **Verification:**

  - Focused service and telemetry unit tests: `46 passed`.
  - Telemetry integration tests: `3 passed`.
  - MyPy: `Success: no issues found in 1080 source files`.
  - Ruff check/fix and formatting passed for all Step 6 Python files.
  - Graphify refreshed successfully: `18,121 nodes`, `79,381 edges`, `654 communities`.
  - No external services were required for this step.

  ### Step 7 — Add provider and client retry visibility

  **Status:** Completed on July 1, 2026.

  **Changes:**

  - Enhanced `record_provider_call()` so the single terminal `integration.provider.call` failure event retains the original exception as a sanitized, bounded `TelemetryExceptionDetails` snapshot.
  - Extended the canonical `TelemetryEmitter` boundary to carry typed exception details without requiring integration emitters to construct a competing event path.
  - Added `IntegrationTelemetry.emit_client_retry_scheduled()` for the canonical `integration.client.retry_scheduled` WARNING event.
  - Included stable provider, client, operation, current/next/maximum attempt, and backoff fields, plus either retryable HTTP status or transport exception type.
  - Injected the shared `IntegrationTelemetry` instance into `YFinanceDataClient` through Dishka and instrumented its existing bounded HTTP retry loop.
  - Added explicit Yahoo operation names for cookie, crumb, constituent, symbol-history, and summary requests.
  - Preserved exactly-once ownership: client telemetry reports only non-terminal retries, while `record_provider_call()` reports one final provider success, failure, or cancellation.
  - Preserved cancellation semantics: `CancelledError` is never retried and produces only the canonical provider-cancelled event.
  - Audited all six integration client `asyncio.gather(..., return_exceptions=True)` sites. Every result is explicitly inspected; cancellation is re-raised, and failures are converted to typed degradation data, logged at the client boundary, or normalized intentionally. No silent-discard remediation was required.

  **Architectural guardrail:**

  - Repowise identified `YFinanceDataClient` as a critical churn hotspot with a `4.56` health score and the retry method as a nested-complexity hotspot. The change therefore avoided a broad transport refactor and introduced only the telemetry dependency, explicit operation identity, and one retry-scheduling helper. Metrics mapping for `integration.client.retries` remains assigned to Step 11.

  **Verification:**

  - Focused provider/client tests: `13 passed`.
  - Broader integration-client, bootstrap, and telemetry-coverage regression tests: `22 passed`.
  - Telemetry unit and integration regression suite: `80 passed`.
  - MyPy: `Success: no issues found in 1080 source files`.
  - Ruff check/fix and formatting passed for all Step 7 Python files.
  - Graphify refreshed successfully: `18,146 nodes`, `79,612 edges`, `644 communities`.
  - No external services were required for this step.

  ### Step 8 — Audit runtime, workflow, plugin, policy, and governance fan-out

  **Status:** Completed on July 1, 2026.

  **Changes:**

  - Verified runtime retry visibility remains owned by the existing typed `NODE_RETRYING` event; no parallel retry telemetry path was introduced.
  - Strengthened `EventBus` subscriber-failure reporting so one `SYSTEM_WARNING` retains the failed event identity, timestamp, execution location, trace hierarchy, handler identity, and sanitized bounded exception details.
  - Preserved `CancelledError` across EventBus, plugin lifecycle, runtime lifecycle, policy, governance, and runtime-wave fan-out instead of normalizing cancellation into an ordinary failure.
  - Added one canonical `plugin.lifecycle.hook_failed` event for each failed plugin lifecycle callback in both fail-fast and non-fail-fast modes, while successful hooks continue in non-fail-fast mode.
  - Added typed runtime lifecycle failure context and one canonical `runtime.lifecycle.hook_failed` event carrying workflow, execution, runtime, node, trace, lifecycle-event, hook, and exception identity.
  - Wired runtime lifecycle failure telemetry through `WorkflowRuntimeAssembler` only for assembler-owned managers when observability is enabled; explicitly supplied lifecycle managers remain caller-owned and unmodified.
  - Preserved fail-closed policy and governance behavior while attaching typed exception snapshots to their existing terminal denied/blocked telemetry events. Summary evaluated events contain only failure counts, preventing duplicate tracebacks.
  - Corrected runtime-wave cancellation handling so node-task cancellation propagates rather than becoming a failed node output.
  - Verified timeout conversion retains the child-node trace relationship and emits exactly one terminal lifecycle-owned `NODE_FAILED` event.
  - Added no local Python logging where an existing canonical runtime or telemetry event owns the failure.

  **Architectural guardrail:**

  - Repowise identified the runtime lifecycle manager and workflow runtime assembler as churn-heavy, under-tested core hotspots. The implementation therefore added narrow injected failure-owner contracts and focused composition wiring without changing runtime execution, public facade, event taxonomy, or caller-supplied manager behavior.

  **Verification:**

  - Focused runtime, plugin, policy, governance, EventBus, and wave-execution suite: `50 passed`.
  - Broader runtime and related integration regression suite: `144 passed`.
  - Ruff check/fix and formatting passed across the project.
  - MyPy: `Success: no issues found in 1082 source files`.
  - Graphify refreshed successfully: `18,238 nodes`, `80,256 edges`, `650 communities`.
  - No external services were required for this step.

  ### Step 9 — Add bootstrap and configuration-failure observability

  **Status:** Completed on July 2, 2026.

  **Changes:**

  - Added `BootstrapConfigurationTelemetry` as the single canonical owner of `platform.bootstrap.configuration_failed` events, including component identity, invalid setting names, required/optional classification, startup action, active correlation identity, and canonical trace/span context.
  - Added recursive configuration-detail sanitization that redacts secret-shaped fields and complete connection or endpoint URLs before telemetry or emergency logging crosses a boundary.
  - Added one CRITICAL emergency logging path for failures that occur before observability can be constructed; it preserves the original traceback while replacing the exception message and configuration values with sanitized diagnostics.
  - Added explicit required workflow configuration validation for retention limits, checkpoint/artifact directories, and plugin directories. Invalid required settings emit one ERROR event and fail startup.
  - Made OpenTelemetry, Prometheus, telemetry logging, and JSONL telemetry optional integrations: invalid configuration or startup failures emit one WARNING event and allow the platform to continue without the failed integration.
  - Corrected `WorkflowInfrastructureProvider` so disabled OpenTelemetry no longer parses irrelevant OpenTelemetry environment variables during provider construction.
  - Added required PostgreSQL runtime-persistence failure reporting at the workflow composition root; construction failures emit one ERROR event and remain fail-fast.
  - Added sanitized pre-observability CRITICAL reporting for invalid CLI environment configuration, provider profiles, and integration-provider selection. Invalid provider values are never included in log output.
  - Added focused tests for active trace propagation, severity and startup-action classification, metrics recording, URL/credential sanitization, exactly-one emergency records, disabled-integration lazy parsing, optional OpenTelemetry/Prometheus/JSONL degradation, required workflow and persistence failures, CLI configuration failures, and provider-selection failures.

  **Architectural guardrail:**

  - Repowise continues to classify the workflow assembler, workflow provider, DI provider selection, and CLI container as churn-heavy hotspots. The implementation therefore introduced one narrow telemetry emitter and one focused validator instead of refactoring bootstrap composition. Required platform components remain fail-fast; only explicitly optional observability integrations degrade. The existing bootstrap/facade/runtime contracts were not changed.

  **Verification:**

  - Focused Step 9 suite: `33 passed`.
  - Broader telemetry, bootstrap, CLI, and workflow-provider regression suite: `95 passed`.
  - Ruff check/fix and formatting passed across all `1,089` Python files.
  - MyPy: `Success: no issues found in 1086 source files` with `--explicit-package-bases`.
  - `git diff --check` passed.
  - Graphify refreshed successfully: `18,303 nodes`, `80,602 edges`, `656 communities`.
  - Repowise post-change review found no new security signals or missing historical co-change partners; the known churn/complexity risks remain contained by focused regression coverage.
  - No external services were required for this step.

  ### Step 10 — Correct OpenTelemetry trace and exception mapping

  **Status:** Interim implementation completed on July 2, 2026; superseded by corrective Steps 10A–10E.

  **Changes:**

  - Updated `OpenTelemetrySink` to read canonical `TelemetryEvent.event_id`, `trace_id`, `span_id`, and `parent_span_id` fields directly instead of resolving trace identity from arbitrary attributes or payload dictionaries.
  - Added `telemetry.event_id` to exported spans while preserving canonical Polaris trace fields as explicit span attributes.
  - Added a bounded canonical-span anchor map that translates Polaris's logical span identities into valid, unique OpenTelemetry event spans. This avoids duplicate OpenTelemetry span IDs when multiple lifecycle events share one Polaris span while still producing real exported parent-child relationships.
  - Added a remote-parent fallback for valid canonical parent identities that arrive before their parent event, preserving the canonical trace and parent identity rather than flattening the span to a root.
  - Added one sanitized OpenTelemetry `exception` event containing `exception.type`, `exception.message`, and `exception.stacktrace`.
  - Set OpenTelemetry status to `ERROR` for ERROR/CRITICAL events, exception-bearing events, and non-cancellation failed operations. Retry, degraded-success, and cancellation WARNING events remain non-error.
  - Added focused concurrent-task coverage proving `TelemetryContext` survives `asyncio.create_task()` and `asyncio.gather()` and that concurrently emitted child events attach to the exported parent anchor.
  - Updated the end-to-end telemetry coverage audit to require a real exported parent for application-service spans instead of the former flattened root-span behavior.

  **Architectural guardrail:**

  - Polaris's canonical `span_id` identifies a logical operation and is intentionally reused by multiple lifecycle events. The sink therefore does not force that value into every OpenTelemetry event span, which would create invalid duplicate span identities. Canonical IDs remain explicit attributes and bounded lookup keys, while OpenTelemetry owns unique external span IDs.
  - Repowise classifies the sink as a churn-heavy hotspot. The change remained isolated to the OpenTelemetry boundary and focused integration tests; the canonical telemetry event and trace-context contracts were not modified.

  **Verification:**

  - Focused OpenTelemetry and trace-audit integration tests: `7 passed`.
  - Broader telemetry and runtime observability regression suite: `96 passed`.
  - Ruff check/fix and formatting passed across all `1,089` Python files.
  - MyPy: `Success: no issues found in 1086 source files` with `--explicit-package-bases`.
  - `git diff --check` passed.
  - Graphify refreshed successfully: `18,321 nodes`, `80,702 edges`, `654 communities`.
  - Repowise post-change blast-radius review found no missing historical co-change partners or security signals; bootstrap/configuration dependents were covered by the broader telemetry regression suite.
  - No external services were required; exporter behavior was verified with the in-memory OpenTelemetry exporter.


  ### Step 10A — Define and verify canonical span semantics

  **Status:** Completed on July 2, 2026.

  **Changes:**

  - Added `.docs/canonical_trace_lifecycle.md` as the canonical trace ownership and lifecycle decision.
  - Defined strict meanings for `trace_id`, `span_id`, `parent_span_id`, and `event_id`; no identifier is retained as a generic logical key.
  - Traced the complete lifecycle from `TraceContext` creation through runtime and telemetry contexts, canonical events, collector fan-out, PostgreSQL mapping, OpenTelemetry export, and operational consumers.
  - Classified workflow execution as a real root operation while identifying over-broad span reuse at runtime-node retries, `ServiceRunner`, provider calls, client retries, and external-operation boundaries.
  - Documented that progress, retry, warning, and degradation notifications are span events associated with an owning operation rather than independent spans.
  - Documented the PostgreSQL collision risk: event-derived trace records use `trace_id + span_id`, while repository conflict handling currently discards later lifecycle state with `ON CONFLICT DO NOTHING`.
  - Marked Step 10's canonical-span anchor map as an interim workaround superseded by Steps 10B–10E.
  - Added two strict expected-failure contracts that make the remaining architecture gaps executable:
    - lifecycle start/completion events must export one canonical operation span using the canonical span ID;
    - terminal PostgreSQL trace state must update the canonical span record rather than be discarded.

  **Architectural guardrail:**

  - Repowise reports an overall blast-radius risk of `10.0` for the eventual cross-boundary correction. `TraceContext` is high-coupling, the OpenTelemetry sink and PostgreSQL repository are churn-heavy, and the persistence mapper is a high-churn boundary. Step 10A therefore changed no production behavior; it established the decision, lifecycle audit, and executable acceptance contracts before modifying those core paths.
  - The expected-failure markers are temporary implementation gates, not compatibility behavior. Step 10E must remove them after the corrected contracts pass.

  **Verification:**

  - Focused lifecycle, OpenTelemetry, mapper, and PostgreSQL repository suite: `12 passed, 2 xfailed`.
  - The two xfails are strict and correspond exactly to Steps 10C and 10D; an unexpected pass will fail the suite and force removal of the obsolete marker.
  - MyPy: `Success: no issues found in 1087 source files` with `--explicit-package-bases`.
  - Ruff check/fix and formatting passed for the new contract test.
  - `git diff --check` passed.
  - Graphify refreshed successfully: `18,327 nodes`, `80,726 edges`, `653 communities`.
  - No external services were required for Step 10A.

  ### Step 10B — Establish real operation-span boundaries

  **Status:** Completed on July 2, 2026.

  **Changes:**

  - Clarified `TraceContext` as the vendor-neutral identity of exactly one bounded operation span; `span_id` is no longer documented or treated as a reusable logical-scope identifier.
  - Added `TelemetryContext.child_operation()` as the canonical boundary helper. It creates a child of an active trace or a new root operation when no trace exists, while retaining workflow, execution, runtime, node, correlation, tag, and attribute context.
  - Kept workflow execution as the root operation and assigned a distinct child operation to every runtime-node attempt. Independently timed retry attempts are sibling spans under the workflow operation rather than repeated events on one node identity.
  - Moved runtime attempt lifecycle ownership into `RuntimeNodeExecutor` while preserving the wave scheduler's pause/cancel safe boundary before each first attempt. Failed attempts now close through lifecycle telemetry before retry notifications are emitted on that same attempt.
  - Added a typed `RuntimeNodeExecutionResult` so finalization receives both the node output and the exact attempt context that produced it.
  - Assigned every `ServiceRunner` attempt a distinct operation context. Started, failed, retry-scheduled, degraded, cancelled, and completed events now reference the attempt that owns them; subsequent retries receive fresh sibling span identities.
  - Assigned every `record_provider_call()` invocation a distinct provider-operation context and scoped the awaited provider/client work beneath it. Provider-level completion/failure and nested client retry notifications therefore share the provider operation identity without turning the retry notification into a new operation.
  - Preserved `contextvars` propagation through awaited calls, `asyncio.create_task()`, and `asyncio.gather()`, and preserved `CancelledError` propagation at runtime, service, and provider boundaries.
  - Updated trace-audit tests to assert the canonical hierarchy `workflow → node attempt → service attempt` and `workflow → node attempt → provider call`; intelligence notifications remain associated with the owning node attempt.

  **Architectural guardrail:**

  - Step 10B corrects canonical operation ownership only. `OpenTelemetrySink` still exports lifecycle events as separate event spans through the interim anchor map; collapsing those events into one exported operation span is intentionally deferred to Step 10C. PostgreSQL terminal-state assembly remains Step 10D.
  - Repowise still assigns the cross-boundary change an overall risk score of `10.0`: `RuntimeEngine` and `ServiceRunner` are churn-heavy, while `TraceContext`, `TelemetryContext`, and provider telemetry are highly coupled. The implementation therefore changed only the canonical workflow, attempt, service, and provider owners and added direct regression coverage. No historical co-change partner or security signal was left unaddressed.

  **Verification:**

  - Focused operation-boundary suite: `31 passed`.
  - Broader application-service, provider/client, runtime, control, and telemetry regression suite: `186 passed`.
  - Full telemetry unit/integration suite: `89 passed, 2 xfailed`; the strict expected failures remain the Step 10C OpenTelemetry lifecycle gate and Step 10D PostgreSQL terminal-state gate.
  - Ruff check/fix and formatting passed across all `1,090` Python files.
  - MyPy: `Success: no issues found in 1087 source files` with `--explicit-package-bases`.
  - `git diff --check` passed.
  - Graphify refreshed successfully: `18,346 nodes`, `80,876 edges`, `662 communities`.
  - A full repository test run was also attempted. It reached `80 passed, 18 skipped, 2 xfailed` before the live Neo4j projection test failed because `localhost:7687` was unavailable; execution was then stopped rather than waiting through repeated external-service retries. This failure is unrelated to Step 10B, whose affected suites pass without external services.

  ### Step 10C — Separate span lifecycle from event export

  **Status:** Completed on July 2, 2026.

  **Changes:**

  - Replaced the event-per-span OpenTelemetry projection with one retained OpenTelemetry span per canonical `(trace_id, span_id)` operation lifecycle.
  - Made Polaris's canonical trace and span identifiers the actual exported OpenTelemetry identities through a boundary-specific ID generator; they are no longer aliases for randomly generated external span IDs.
  - Attached started, progress, retry, degradation, signal, terminal, and exception facts as timestamped OpenTelemetry span events on their owning operation span.
  - Exported workflow, runtime-node attempt, application-service attempt, and provider-call spans with their real canonical parent relationships.
  - Removed the canonical-span anchor map and its same-span/remote-parent workaround.
  - Added bounded open-lifecycle state. If the open-span limit is exceeded, the oldest incomplete span is explicitly marked and ended; shutdown also marks and ends every remaining incomplete span so state cannot leak indefinitely.
  - Kept `force_flush()` non-destructive: it flushes completed spans without prematurely closing operations that are still running.
  - Ignored telemetry without valid canonical trace/span identity at the tracing projection boundary instead of manufacturing unrelated spans. Those events remain available to canonical telemetry, logging, metrics, and persistence paths.
  - Removed only the strict Step 10C expected-failure marker. The Step 10D PostgreSQL terminal-state marker remains in place.

  **Verification:**

  - Focused OpenTelemetry lifecycle and trace-audit suite: `37 passed, 1 xfailed`.
  - Full service-free telemetry unit/integration suite: `91 passed, 1 xfailed`; the remaining strict xfail is Step 10D only.
  - Ruff check/fix and formatting passed across all `1,090` Python files.
  - MyPy: `Success: no issues found in 1087 source files` with `--explicit-package-bases`.
  - `git diff --check` passed.
  - Graphify refreshed successfully: `18,371 nodes`, `80,976 edges`, `653 communities`.
  - No external services were required or invoked. In particular, no Neo4j, PostgreSQL, Qdrant, Jaeger, Prometheus, or other live-service tests were run for Step 10C.

  ### Step 10D — Correct PostgreSQL trace persistence

  **Status:** Completed on July 2, 2026.

  **Changes:**

  - Corrected the persistence contract so every canonical `TelemetryEvent` is stored independently by its original `event_id`; persistence no longer generates replacement event identities.
  - Established `(trace_id, span_id)` as the unique PostgreSQL identity of one canonical operation span and added a database uniqueness constraint that enforces that ownership.
  - Replaced trace-row `ON CONFLICT DO NOTHING` behavior with deterministic lifecycle assembly. Start observations retain the earliest start time, terminal observations update end time and duration, and nonterminal observations cannot erase an existing terminal state.
  - Added deterministic terminal precedence (`failed` → `cancelled` → `succeeded` → `running` → `unknown`), with the latest terminal timestamp resolving observations of equal precedence.
  - Promoted terminal-event and exception data to first-class trace columns: `terminal_event_id`, exception type, message, stack trace, and truncation state.
  - Added shared operation-lifecycle classification used by both PostgreSQL persistence and the OpenTelemetry sink, removing duplicated lifecycle-name logic at the projection boundaries.
  - Added migration `b8c9d0e1f2a3` to correct legacy terminal timestamps, normalize legacy operation names, remove duplicate trace/span rows deterministically, remove the obsolete nonunique index, add the unique trace/span constraint, and add the first-class terminal/exception columns and indexes.
  - Removed the Step 10D strict expected-failure marker and expanded mapper, model, serializer, repository, lifecycle-contract, migration, and live PostgreSQL integration coverage.
  - Updated `.docs/canonical_trace_lifecycle.md` to define immutable event persistence separately from canonical span lifecycle assembly.

  **Architectural guardrail:**

  - Telemetry events remain immutable evidence, while `telemetry_traces` is the assembled operation-span projection. PostgreSQL now has one explicit writer contract for each: event identity is `event_id`, and span identity is `(trace_id, span_id)`. No generated identity, metadata-only failure field, duplicate span row, or legacy conflict-discard behavior is retained.
  - The PostgreSQL repository and telemetry mapper are churn-heavy boundaries, so the implementation remained limited to lifecycle mapping, persistence, schema migration, and direct contract coverage. No unrelated telemetry or runtime architecture was refactored.

  **Verification:**

  - PostgreSQL connectivity confirmed directly with `SELECT 1`.
  - Applied migration `d9649abf672c -> b8c9d0e1f2a3` successfully with `alembic upgrade head`.
  - `alembic check`: no new upgrade operations detected.
  - Live migration contract suite: `6 passed` (`tests/database/test_migrations.py`).
  - Live PostgreSQL telemetry lifecycle integration: `1 passed`; two event rows assembled into exactly one terminal failed trace row with canonical timing and first-class exception details.
  - Focused lifecycle, persistence, and OpenTelemetry suite: `48 passed`.
  - Full service-free telemetry unit/integration suite: `141 passed`.
  - Bootstrap, retention, health, and export regression suite: `43 passed`.
  - Ruff check/fix and formatting passed.
  - MyPy: `Success: no issues found in 1089 source files`.
  - `git diff --check` passed.
  - Graphify refreshed successfully: `18,398 nodes`, `81,043 edges`, `655 communities`.
  - PostgreSQL was the only external service used. No Neo4j, Qdrant, Jaeger, Prometheus, or other live-service tests were invoked.

  ### Step 10E — Verify complete trace topology

  **Status:** Completed on July 2, 2026.

  **Changes:**

  - Corrected the integration trace-audit fixture so the provider call executes within the active application-service attempt rather than after service completion. The exercised hierarchy now matches production ownership: `workflow → node attempt → service attempt → provider call`.
  - Verified client retry telemetry as an event on the owning provider span, not as an artificial operation span. Independently timed client or datastore operations remain eligible for their own child spans; notification-only retry facts do not create duplicate span identities.
  - Added an explicitly gated live topology contract that emits the same four-span hierarchy to PostgreSQL and the OTLP exporter, reads it back from PostgreSQL and Jaeger, and requires exact parent-map equality with no extra exported spans.
  - Kept live-service access opt-in through `POLARIS_TEST_DATABASE_URL`, `POLARIS_TEST_JAEGER_URL`, and `POLARIS_TEST_OTEL_ENDPOINT`, so ordinary telemetry suites do not contact external services.
  - Confirmed runtime retries and concurrent branches receive distinct child span identities under one trace, while all lifecycle observations for one operation assemble into one canonical PostgreSQL span record.
  - Confirmed no Step 10 expected-failure markers remain in the affected runtime, service, provider/client, OpenTelemetry, or PostgreSQL telemetry contracts.

  **Architectural guardrail:**

  - Workflow, node attempt, service attempt, provider call, and independently timed client/datastore operations are operation spans. Retry, progress, warning, and degradation notifications are events on their owning operation span. PostgreSQL persistence is the authoritative projection of that hierarchy and does not recursively create a telemetry datastore child span for its own write.
  - Step 10E added verification and corrected only the test orchestration needed to exercise the real nesting contract. It did not broaden production tracing behavior or introduce a parallel trace identity.

  **Verification:**

  - Focused topology, retry, concurrency, and lifecycle suite: `8 passed, 1 skipped`; the skip is the deliberately gated live-service test.
  - Broader service-free telemetry/runtime/service/provider regression suite: `164 passed, 1 skipped`.
  - Live PostgreSQL lifecycle assembly test: `1 passed`.
  - Live PostgreSQL/Jaeger exact topology parity test: `1 passed in 1.14s`.
  - Ruff check/fix and formatting passed across all project Python files.
  - MyPy: `Success: no issues found in 1090 source files` with `--explicit-package-bases`.
  - `git diff --check` passed.
  - Graphify refreshed successfully: `18,410 nodes`, `81,119 edges`, `647 communities`.
  - PostgreSQL and Jaeger were the only external services used. No Neo4j, Qdrant, Prometheus, or other live-service tests were invoked.


  ### Step 11 — Complete metrics and external observability coverage

  **Status:** Completed on July 2, 2026.

  **Changes:**

  - Added canonical low-cardinality metric mappings for application-service configuration failures, retries, and degraded outcomes; integration-client retries; telemetry-sink failures; plugin/runtime callback failures; EventBus subscriber failures; and bootstrap configuration failures.
  - Refactored `DomainMetricsRecorder` into bounded event-domain handlers before extending it, keeping metric ownership at the existing canonical telemetry-to-metrics projection boundary rather than adding direct metric calls to services, clients, hooks, or bootstrap code.
  - Normalized operational dimensions to stable `service_name`, `component_name`, `provider_name`, `operation`, `event_type`, and `outcome` attributes where applicable.
  - Expanded the Prometheus label allowlist only for stable service/component/outcome dimensions. Request IDs, event IDs, trace/span IDs, exception details, URLs, symbols, and user input remain excluded from Prometheus labels.
  - Corrected telemetry-sink failure dimensions to use canonical component, operation, and outcome attributes instead of the unsupported legacy `sink` metric attribute.
  - Added repository-owned Prometheus alert rules for application retry spikes, degraded-service rates, integration-client retry spikes, telemetry-sink failures, configuration failures, and callback/subscriber failures.
  - Wired the alert rules into Prometheus and Docker Compose, and corrected stale Grafana queries to use the metric families actually exported by Polaris.
  - Added Grafana panels for application-service resilience, configuration failures, integration-client retries, and telemetry/callback failures.
  - Updated the telemetry observability documentation and coverage ledger with the canonical metric families, alert ownership, validation commands, and label-cardinality rules.
  - Added focused contract tests for operational metric mapping, forbidden-label exclusion, Prometheus rule loading, alert coverage, Docker Compose wiring, and canonical Grafana queries.

  **Architectural guardrail:**

  - Detailed exception and correlation data remains in structured logs, traces, and PostgreSQL. Prometheus receives only bounded operational dimensions. The implementation reuses the existing `DomainMetricsRecorder → MetricsStore → PrometheusMetricsExporter` boundary and does not introduce direct instrumentation paths or duplicate event ownership.
  - Repowise identifies `domain_metrics.py` as a churn-heavy boundary and its current index still reports the pre-refactor monolithic `record()` shape. The source implementation was therefore kept surgical, decomposed into event-domain handlers, and protected by the complete service-free telemetry suite; no unrelated observability-manager or exporter refactor was introduced.

  **Verification:**

  - Full service-free telemetry unit/integration suite: `97 passed`.
  - Deployment configuration contracts: Prometheus YAML, alert rules, Docker Compose, and Grafana JSON all parsed and validated successfully.
  - `docker compose config --quiet` passed.
  - Ruff check/fix and formatting passed across all project Python files.
  - MyPy: `Success: no issues found in 1091 source files` with `--explicit-package-bases`.
  - `git diff --check` passed.
  - Graphify refreshed successfully: `18,431 nodes`, `81,198 edges`, `631 communities`.
  - No external services were required or invoked for Step 11.

  ### Step 12 — Preserve exception and trace data in PostgreSQL

  **Status:** Completed on July 2, 2026.

  **Changes:**

  - Reconciled Step 12 with the completed Step 10D lifecycle correction. Canonical `TelemetryEvent.event_id`, first-class `trace_id`/`span_id`, and first-class terminal trace exception columns were already implemented, so no competing identity or duplicate persistence path was introduced.
  - Added the canonical typed `TelemetryExceptionDetails` snapshot to `telemetry_events.payload.exception_details`, preserving exception type, message, stack trace, and truncation state in the existing PostgreSQL JSONB event payload.
  - Defined event-message precedence at the mapper boundary: an explicit canonical event message is retained; otherwise an exception-bearing event uses the sanitized exception message.
  - Made sanitization and bounds invariant for every `TelemetryExceptionDetails` instance, including direct dataclass construction. Exception type, message, and stack trace are bounded to `256`, `4096`, and `32768` characters respectively before reaching persistence or any other sink.
  - Added focused mapper tests for canonical identity, first-class trace fields, exception-payload serialization, sanitization, and message precedence.
  - Expanded serializer round-trip coverage so nested typed exception data is proven to survive the PostgreSQL model boundary unchanged.
  - Updated the canonical trace lifecycle, telemetry observability guide, and observability coverage ledger with the completed PostgreSQL event/exception contract.
  - Added no schema migration. The existing event identity, trace columns, message, and JSONB payload columns satisfy Step 12; Step 10D's existing migration continues to own the first-class trace exception columns.

  **Architectural guardrail:**

  - `TelemetryEvent` remains the single canonical event owner. The mapper performs boundary serialization only; it does not create a second exception model, replacement event identity, or sink-specific message.
  - PostgreSQL retains immutable event evidence in `telemetry_events` and assembled operation state in `telemetry_traces`. The event JSONB snapshot and trace query columns are two representations of the same canonical typed exception, not independent writers.
  - Repowise continues to identify the mapper as churn-heavy but healthy (`9.65`). The change was limited to the exception payload/message boundary and direct contracts; the broader service-free telemetry suite covers the reported sink and audit impact surface.

  **Verification:**

  - Focused telemetry persistence and exception contract suite: `47 passed`.
  - Full service-free telemetry unit/integration suite: `149 passed`.
  - Ruff check/fix and formatting passed across all project Python files.
  - MyPy: `Success: no issues found in 1091 source files` with `--explicit-package-bases`.
  - `git diff --check` passed.
  - Graphify refreshed successfully: `18,438 nodes`, `81,222 edges`, `652 communities`.
  - No external services were required or invoked for Step 12.

  ### Step 13 — Remediate remaining production exception and fallback gaps

  **Status:** Completed on July 2, 2026.

  **Changes:**

  - Added canonical degraded-operation emission to `ApplicationRagTelemetry` and degraded-agent emission to `IntelligenceTelemetry`, both at WARNING severity with typed exception details when a caught exception caused the degradation.
  - Added typed exception details to canonical RAG operation-failure events so PostgreSQL, logs, and trace sinks receive the original exception type, message, and traceback through one telemetry owner.
  - Instrumented Fundamental, Technical, News, and Sentiment agent LLM failures as canonical degraded intelligence events before their deterministic fallback paths execute.
  - Removed duplicate direct exception/warning logs from RAG lifecycle, retrieval, projection, ingestion, embedding, generation, security, and web-fallback paths where `ApplicationRagTelemetry` already owns the same operational outcome.
  - Converted RAG dependency-readiness failures, security sanitization/rejection outcomes, missing Qdrant rehydration records, and missing Neo4j canonical documents into aggregate canonical degraded events instead of per-record warning logs.
  - Preserved one direct CLI exception log in `RagCommandService.ask` because request-scope, composition, or rendering failures can escape before canonical RAG telemetry is available. No meaningful persistence fallback log gap was found.
  - Kept successful handled fallbacks as `success=True` WARNING degradation events, distinguishing a safely completed degraded operation from a failed operation without hiding the underlying exception.
  - Added focused contracts for degraded RAG/intelligence events, exception preservation, readiness degradation, security degradation, web-fallback failure ownership, and terminal RAG pipeline failures.

  **Architectural guardrail:**

  - Each operational failure or degradation now has one canonical owner. Intelligence fallbacks are owned by `IntelligenceTelemetry`; RAG lifecycle and dependency outcomes are owned by `ApplicationRagTelemetry`; repositories do not duplicate boundary telemetry; and direct interface logging is retained only when the canonical application boundary may not be reachable.
  - Repowise identified several affected RAG orchestration and retrieval files as churn-heavy. Changes were therefore limited to telemetry emission, duplicate-log removal, aggregate degradation reporting, exception propagation, and direct regression coverage. No unrelated RAG, persistence, intelligence, or CLI refactor was introduced.

  **Verification:**

  - Final direct-log audit found only the intentionally retained `RagCommandService.ask` exception log across RAG, persistence, intelligence, and CLI targets.
  - Focused service-free RAG, intelligence, telemetry unit, and telemetry integration suite: `306 passed, 1 skipped`. The skipped test is deliberately gated behind live-service configuration.
  - Ruff check/fix and formatting passed across all project Python files.
  - MyPy: `Success: no issues found in 1091 source files` with `--explicit-package-bases`.
  - `git diff --check` passed.
  - Graphify refreshed successfully: `18,486 nodes`, `81,499 edges`, `644 communities`.
  - No external services were required or invoked for Step 13.

  ### Step 14 — Documentation and regression guardrails

  **Status:** Completed on July 2, 2026.

  **Changes:**

  - Finalized `.docs/observability_coverage_ledger.md` as the canonical record of the event taxonomy, ownership matrix, severity rules, exception-capture rules, retry/degradation policy, direct-logging exceptions, metrics/cardinality limits, trace/persistence contract, and regression coverage.
  - Documented that `core.telemetry.events.telemetry_event.TelemetryEvent` is the sole production telemetry-event definition. Public contract/event package exports remain aliases of that same class, while runtime notifications and PostgreSQL records are explicitly documented as boundary representations rather than competing event contracts.
  - Added an AST-based architecture contract that rejects a second production `TelemetryEvent` definition and rejects production imports of `TelemetryEvent` from noncanonical modules.
  - Added an AST-based direct-operational-logging guardrail. WARNING, ERROR, EXCEPTION, and CRITICAL calls are restricted to explicitly documented emergency, partial-child-source, post-terminal archival, and CLI escape boundaries; removing an allowed log remains safe, while adding a new site requires an ownership decision.
  - Documented that the absence of `logging.getLogger(__name__)` is correct when canonical telemetry already owns a module's lifecycle facts. The architecture intentionally tests event ownership rather than imposing a brittle logger-per-file rule.
  - Removed duplicate completed-run persistence exception logs from `PostgresCompletedRunArchive` and `PostgresCompletedRunRepository`. These layers retain rollback/cleanup behavior and re-raise; `WorkflowEngine` remains the single visible owner of best-effort post-terminal archival failure.
  - Preserved the narrow, documented direct-log exceptions for telemetry infrastructure failure, bootstrap failure before telemetry is reliable, bounded integration child-source degradation, workflow archival fallback, and CLI composition/presentation escape.

  **Architectural guardrail:**

  - One operational fact has one canonical owner and one canonical event. Logs, metrics, traces, and PostgreSQL are projections of that event, not independent lifecycle writers.
  - The regression contracts focus on canonical boundaries and semantic ownership. They do not require every Python module to contain a logger and do not hardcode line numbers or require every allowlisted direct-log site to remain forever.
  - Step 14 changed no canonical telemetry event, runtime, trace, metrics, or database schema contracts. The only production behavior change removes duplicate lower-level archival logging while preserving exception propagation to the established workflow boundary.

  **Verification:**

  - Focused architecture and completed-run persistence/runtime suite: `15 passed`.
  - Full service-free telemetry, telemetry integration, completed-run workflow, and storage persistence regression suite: `721 passed`.
  - One pre-existing SQLAlchemy test warning remains in `test_postgres_portfolio_state_repository.py` for additional compiled column names; it is unrelated to Step 14.
  - Ruff check/fix and formatting passed across all project Python files.
  - MyPy: `Success: no issues found in 1092 source files` with `--explicit-package-bases`.
  - Direct operational-log audit matched the documented allowlist, and `git diff --check` passed.
  - Graphify refreshed successfully: `18,495 nodes`, `81,511 edges`, `665 communities`.
  - No external services were required or invoked for Step 14.
