  # Core Telemetry Integration Plan

  ## Summary

  Current telemetry is partially implemented but fragmented.

  The platform already has strong foundations:

  - EventBus and typed RuntimeEvent exist for runtime coordination.
  - Runtime/workflow/control/checkpoint/replay events are partially emitted.
  - RuntimeTelemetryHook bridges runtime lifecycle events into RuntimeTelemetry.
  - CoreTelemetryRuntimeSink can forward runtime telemetry into ObservabilityManager.
  - ObservabilityManager supports telemetry events, in-memory metrics, sinks, and trace context creation.
  - TelemetryLogger and OpenTelemetrySink already exist.
  - ServiceRunner, provider wrappers, and several intelligence agents emit some telemetry.

  Important gaps remain:

  - EventBus usage is concentrated in runtime/control/progress, not consistently connected to observability/logging/metrics/tracing.
  - Logging sink exists but is not wired by default.
  - OpenTelemetry support exists but is disabled and lightly integrated.
  - Runtime node emitted_events are preserved but not actually published by RuntimeEngine.
  - Skipped/unregistered node paths can update context without emitting canonical node events.
  - Runtime telemetry can double-record semantically similar workflow lifecycle milestones through both lifecycle hooks and EventBus-derived events.
  - Application/provider/intelligence telemetry is not consistently correlated back to workflow_id, execution_id, runtime_id, and node name.
  - Metrics are mostly generic telemetry counters rather than useful operational metrics.
  - EventBus silently swallows subscriber failures in non-fail-fast mode, which can hide telemetry sink failures.
  - Repowise risk analysis flags RuntimeEngine, WorkflowFacade, WorkflowBootstrap, and ObservabilityManager as high-risk/hotspot areas, so implementation should avoid adding large logic directly to those classes.

  ## Public API / Contract Changes

  - Add optional telemetry correlation to ServiceRequest:
      - telemetry_context: TelemetryContext | None = None
      - Preserve backwards compatibility with default None.

  - Add optional context propagation to provider telemetry:
      - record_provider_call(..., context: TelemetryContext | None = None)
      - If no explicit context is passed, use the active telemetry context set by ServiceRunner.

  - Extend WorkflowBootstrapConfig with observability wiring flags:
      - enable_telemetry_logging: bool = True
      - telemetry_logger_name: str = "polaris.telemetry"
      - enable_domain_metrics: bool = True
      - Keep enable_opentelemetry: bool = False as the default; OpenTelemetry remains opt-in.

  - Keep EventBus runtime-owned. Do not force every application/provider/intelligence event through EventBus; instead, bridge runtime events into observability and use telemetry emitters for higher-layer operational telemetry.

  ## Implementation Plan

  ### 1. Establish telemetry baseline tests

  - Add or extend tests that capture the current telemetry paths:
      - Runtime workflow emits workflow lifecycle events.
      - Runtime progress emits workflow/wave/node progress events.
      - Control manager emits pause/resume/cancel state events.
      - RuntimeTelemetryHook forwards lifecycle/runtime events into RuntimeTelemetry.
      - CoreTelemetryRuntimeSink forwards runtime telemetry into ObservabilityManager.

  - This gives a safety net before refactoring hotspot files.

  Verification:

  - uv run pytest -q tests/integration/runtime tests/unit/runtime/telemetry tests/integration/telemetry

  ———

  ### 2. Deduplicate runtime telemetry flow

  - Keep the existing canonical path:

  RuntimeEngine / WorkflowEngine / Control / Checkpoint / Replay
      → EventBus / RuntimeLifecycleManager
      → RuntimeTelemetryHook
      → RuntimeTelemetry
      → CoreTelemetryRuntimeSink
      → ObservabilityManager

  - Update RuntimeTelemetryHook.on_runtime_event so lifecycle-derived events are not double-counted when equivalent lifecycle hook events already emit duration-aware telemetry.
  - Preserve progress/control/checkpoint/replay/system events from EventBus because those are not fully represented by lifecycle hooks.

  Verification:

  - Add assertions that a simple workflow produces one canonical workflow started/completed telemetry record plus separate progress records.
  - Confirm existing progress/control tests still pass.

  ———

  ### 3. Publish runtime node output events

  - Update RuntimeEngine so RuntimeNodeOutput.emitted_events are actually emitted to the canonical EventBus after node execution.
  - Ensure emitted events receive missing runtime location metadata where safe:
      - workflow_id
      - execution_id
      - runtime_id
      - node_name
      - wave_index

  - Do not mutate event objects; create enriched copies if metadata must be added.

  Verification:

  - Add a unit test with a fake node returning RuntimeNodeOutput(emitted_events=[...]).
  - Assert the subscribed handler receives the event.

  ———

  ### 4. Emit missing skipped/failure node events

  - Add canonical node events for currently silent paths:
      - disabled node → NODE_SKIPPED / progress skipped equivalent if taxonomy is extended
      - dependency failure skip → NODE_SKIPPED
      - missing registered runtime node → NODE_FAILED
      - retry attempt → NODE_RETRYING

  - Keep progress notifications user-facing and lifecycle events infrastructure-facing.
  - If needed, add a NODE_PROGRESS_SKIPPED event type to avoid forcing skipped nodes into failed progress semantics.

  Verification:

  - Add tests for disabled node, dependency skip, missing node registration, and retry path.
  - Assert both final context and EventBus events are correct.

  ———

  ### 5. Improve EventBus failure observability

  - Preserve current non-fail-fast behavior, but stop silently discarding subscriber exceptions.
  - Add internal failure reporting:
      - collect subscriber exception metadata
      - emit a SYSTEM_WARNING or SYSTEM_ERROR event when a subscriber fails
      - avoid infinite recursion if the failing subscriber is the telemetry subscriber itself

  - Keep fail_fast=True behavior unchanged.

  Verification:

  - Add tests where one subscriber fails and another succeeds.
  - Assert the good subscriber still runs and a system warning/error is observable.

  ———

  ### 6. Wire structured logging by default

  - Register TelemetryLogger with ObservabilityManager during bootstrap when enable_telemetry_logging=True.
  - Wire this in both bootstrap paths:
      - direct WorkflowBootstrap
      - Dishka WorkflowInfrastructureProvider

  - Use logger name polaris.telemetry.
  - Do not configure global logging handlers in core; CLI/API entrypoints may configure handlers separately.

  Verification:

  - Add bootstrap tests proving the logger sink is present when enabled and absent when disabled.
  - Add a unit test with caplog proving telemetry events become Python log records with structured extra["telemetry"].

  ———

  ### 7. Add domain metrics mapping

  - Keep existing generic metrics:
      - telemetry.events.total
      - telemetry.events.errors
      - telemetry.event.duration_seconds

  - Add stable operational metrics with bounded names:
      - workflow.executions.total
      - workflow.executions.failed
      - workflow.duration_seconds
      - runtime.nodes.total
      - runtime.nodes.failed
      - runtime.nodes.skipped
      - runtime.node.duration_seconds
      - application.service.calls.total
      - application.service.calls.failed
      - application.service.duration_seconds
      - integration.provider.calls.total
      - integration.provider.calls.failed
      - integration.provider.duration_seconds
      - intelligence.agent.signals.total

  - Implement this as a small mapper/helper, not as large conditional logic inside ObservabilityManager.

  Verification:

  - Unit tests emit representative telemetry events and assert metric points are recorded.

  ———

  ### 8. Propagate telemetry context through services

  - Extend ServiceRequest with optional TelemetryContext.
  - Update ServiceRunner so application telemetry includes:
      - workflow_id
      - execution_id
      - runtime_id
      - node_name
      - correlation_id

  - Add a lightweight active telemetry context scope used only for telemetry/tracing propagation during service.run(...).

  Verification:

  - Unit test ServiceRunner with a request containing telemetry context.
  - Assert started/completed/failed service events include the runtime correlation fields.

  ———

  ### 9. Correlate provider telemetry with active service context

  - Update record_provider_call to include the active telemetry context when one exists.
  - Update IntegrationTelemetry.emit_provider_call payload/attributes so provider events include:
      - provider name
      - operation
      - duration
      - success/failure
      - error type/message on failure
      - runtime/service correlation fields when available

  - Preserve existing provider method signatures unless an explicit context is already available.

  Verification:

  - Unit test provider telemetry with and without active context.
  - Assert provider failures produce error-level telemetry and metrics.

  ———

  ### 10. Propagate runtime context from intelligence nodes

  - Update runtime intelligence nodes that call ServiceRunner to pass a TelemetryContext into ServiceRequest.
  - Start with existing service-calling agents:
      - technical
      - fundamental
      - news
      - sentiment
      - portfolio state builder
      - strategy synthesis

  - Do not add vendor or transport dependencies to agents.
  - Keep business outputs unchanged.

  Verification:

  - Unit tests for at least one representative agent confirming service telemetry includes node/runtime identifiers.
  - Existing intelligence tests must continue to pass.

  ———

  ### 11. Fill intelligence fallback/error telemetry gaps

  - Add telemetry for meaningful non-exception intelligence outcomes:
      - fallback output generated
      - missing upstream dependency
      - low confidence signal
      - degraded data quality

  - Use IntelligenceTelemetry, not direct logging.
  - Avoid noisy per-field telemetry; only emit decision-relevant events.

  Verification:

  - Add tests for representative fallback paths, especially strategy synthesis fallback outputs.

  ———

  ### 12. Validate OpenTelemetry integration

  - Keep OpenTelemetry disabled by default.
  - Ensure enable_opentelemetry=True attaches OpenTelemetrySink to ObservabilityManager.
  - Confirm emitted telemetry events produce spans with workflow/execution/node/provider attributes.
  - Do not require an external collector in local tests; use console/in-memory-compatible configuration where possible.

  Verification:

  - Existing test_opentelemetry_sink plus one bootstrap-level test for opt-in wiring.

  ———

  ### 13. Connect telemetry persistence intentionally

  - Keep runtime JSONL telemetry as the lightweight local default.
  - Do not persist every telemetry event to PostgreSQL by default until retention/volume policy is defined.
  - Add an optional PostgreSQL telemetry sink or bridge only behind a config flag.
  - Map generic telemetry into existing persistence records:
      - telemetry event records
      - workflow metrics
      - provider metrics
      - agent metrics
      - trace records

  Verification:

  - Unit test mapper from TelemetryEvent to persistence records.
  - Integration test can remain optional/marked if PostgreSQL is not available.

  ———

  ### 14. Add telemetry coverage audit tests

  - Add a small audit-style test that verifies the platform has at least one registered telemetry path for:
      - runtime lifecycle
      - workflow progress
      - workflow control
      - integration provider calls
      - intelligence agent signals
      - logging sink
      - metrics recording

  - This prevents future regressions where a refactor accidentally disconnects telemetry.

  Verification:

  - uv run pytest -q tests/unit/telemetry tests/unit/runtime/telemetry tests/integration/telemetry


  ## Canonical Trace Context Propagation Addendum

  The first telemetry integration pass wired logging, metrics, EventBus forwarding, provider/service/intelligence telemetry, optional OpenTelemetry export, and optional telemetry persistence. It did not complete canonical trace context propagation. The follow-on steps below close that gap while keeping OpenTelemetry vendor-specific behavior at the sink boundary.

  ### 15. Define canonical trace context contract

  - Extend the internal telemetry context contract so trace identity can be carried alongside workflow, execution, runtime, node, correlation, tags, and attributes.
  - Bridge `TelemetryContext` and `TraceContext` without making OpenTelemetry a core dependency.
  - Ensure emitted telemetry attributes include canonical `trace_id`, `span_id`, and `parent_span_id` when a trace context exists.
  - Add focused contract tests before changing runtime/service propagation.

  Verification:

  - `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/telemetry/test_telemetry_context.py tests/unit/telemetry/test_application_telemetry.py tests/unit/telemetry/test_integration_intelligence_telemetry.py`

  ———

  ### 16. Activate root trace context at workflow execution start

  - Create one root `TraceContext` per workflow execution through `ObservabilityManager.create_trace_context(...)`.
  - Store/propagate it through the runtime execution path without changing workflow business outputs.
  - Ensure workflow-level runtime telemetry carries the root trace identifiers.

  Verification:

  - Add/extend runtime telemetry tests proving workflow start/completion events include the same root `trace_id`.

  ———

  ### 17. Create child trace contexts for runtime node execution

  - Derive child trace contexts for each node from the workflow root trace.
  - Preserve parent/child span identity across node started/running/completed/failed/skipped events.
  - Avoid large logic additions in `RuntimeEngine`; prefer small helpers.

  Verification:

  - Add runtime node telemetry tests proving node events have a child `span_id`, the workflow `trace_id`, and parent span linkage.

  ———

  ### 18. Propagate trace identity through application services

  - Ensure `ServiceRequest.telemetry_context` can carry trace identity from runtime nodes into `ServiceRunner`.
  - Ensure application service started/completed/failed telemetry includes trace identifiers.
  - Preserve active telemetry context behavior for downstream provider calls.

  Verification:

  - Extend ServiceRunner tests to assert service telemetry and active context include trace identity.

  ———

  ### 19. Propagate trace identity through provider calls

  - Ensure `record_provider_call(...)` and `IntegrationTelemetry` preserve active trace identity on success and failure.
  - Do not change provider business method signatures unless a provider already accepts explicit telemetry context.

  Verification:

  - Extend provider telemetry tests for successful and failed provider calls with inherited trace identifiers.

  ———

  ### 20. Propagate trace identity through intelligence telemetry

  - Update runtime-to-intelligence telemetry helpers so agents inherit node trace identity when creating service requests or emitting intelligence telemetry.
  - Keep vendor and transport logic out of intelligence components.

  Verification:

  - Extend representative intelligence telemetry tests for runtime-derived trace identity.

  ———

  ### 21. Make OpenTelemetry and persistence consume canonical trace fields

  - Update `OpenTelemetrySink` to map canonical trace identifiers from telemetry events into span attributes.
  - Keep OpenTelemetry export opt-in and boundary-only.
  - Ensure telemetry persistence mapper creates trace records from real emitted telemetry events carrying canonical trace fields.

  Verification:

  - Extend OpenTelemetry sink and telemetry persistence mapper tests for trace identifiers and parent span linkage.

  ———

  ### 22. Add trace propagation audit coverage

  - Add audit coverage proving `create_trace_context()` is used in a real workflow path.
  - Verify workflow, node, application service, provider, intelligence, OpenTelemetry, and persistence mapping paths can all observe canonical trace identity.
  - Keep tests local and collector-free.

  Verification:

  - `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/telemetry tests/unit/runtime/telemetry tests/unit/application/services/base tests/unit/integration/providers tests/integration/telemetry`

  ## Architectural Guardrails

  - Do not bloat RuntimeEngine, WorkflowFacade, or WorkflowBootstrap; add small helpers, mappers, hooks, and subscribers.
  - Keep EventBus as the runtime coordination bus, not a catch-all application event bus.
  - Keep telemetry emitters at layer boundaries:
      - runtime → RuntimeTelemetry
      - application → ApplicationTelemetry
      - integration → IntegrationTelemetry
      - intelligence → IntelligenceTelemetry

  - Use typed telemetry/context objects internally.
  - Serialize only at sinks, logs, persistence, JSONL, and OpenTelemetry boundaries.
  - Keep OpenTelemetry/vendor exporters optional and boundary-only.

  ## Test Plan

  Run after implementation:

  UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .
  UV_CACHE_DIR=/tmp/uv-cache uv run ruff format . --check
  UV_CACHE_DIR=/tmp/uv-cache uv run mypy . --explicit-package-bases
  UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/telemetry tests/unit/runtime/telemetry tests/unit/integration/providers tests/unit/application/services/base tests/integration/telemetry tests/integration/runtime

  Also run a smoke workflow:

  UV_CACHE_DIR=/tmp/uv-cache uv run polaris morning-report --format console --progress

  Acceptance criteria:

  - Workflow execution emits runtime, progress, control, node, checkpoint/replay where applicable.
  - Telemetry events reach ObservabilityManager.
  - Logging sink receives structured telemetry records.
  - Metrics store records workflow/node/service/provider/agent metrics.
  - OpenTelemetry remains opt-in and still works when enabled.
  - Provider and service telemetry can be correlated to workflow execution when invoked from runtime nodes.
  - No mypy, ruff, or targeted pytest failures.

  ## Assumptions

  - We should complete internal telemetry/logging/metrics/tracing integration before requiring external infrastructure such as Prometheus, Jaeger, Grafana, or an OTLP collector.
  - The next phase of the integration will be to integrate with external infrastructure such as Prometheus, Jaeger, and Grafana.
  - EventBus should remain runtime-owned; application/provider/intelligence telemetry should not be forced through EventBus unless the event is truly a runtime coordination event.
  - PostgreSQL telemetry persistence should be optional until retention and volume policy are explicitly chosen.

## Step Results

- Step 0: Added the Step Results section to track one-step-at-a-time implementation progress.
- Step 1: Added `tests/integration/telemetry/test_core_telemetry_baseline.py` to lock in the current runtime lifecycle/progress/control telemetry path from EventBus/RuntimeLifecycleManager through RuntimeTelemetryHook, CoreTelemetryRuntimeSink, ObservabilityManager, and in-memory telemetry sink. Verification passed: `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/integration/runtime tests/unit/runtime/telemetry tests/integration/telemetry` (13 passed); `ruff check` and `ruff format --check` passed for the new test file.
- Step 2: Deduplicated runtime telemetry by having `RuntimeTelemetryHook.on_runtime_event` ignore EventBus events that are equivalent to duration-aware lifecycle hook telemetry (`WORKFLOW_*`, `WAVE_*`, and `NODE_*` lifecycle events), while preserving progress/control/checkpoint/replay/system runtime events. Added unit coverage for the skip behavior and strengthened bootstrap observability coverage to assert one canonical lifecycle telemetry record plus separate progress records. Verification passed: `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/integration/runtime tests/unit/runtime/telemetry tests/integration/telemetry` (14 passed); targeted `ruff check`, `ruff format --check`, and `mypy --explicit-package-bases` passed for changed telemetry files.
- Step 3: Published `RuntimeNodeOutput.emitted_events` through the canonical `EventBus` after node output is applied to runtime context and before terminal node progress is emitted. Added non-mutating runtime-location enrichment for emitted events so missing `workflow_id`, `execution_id`, `runtime_id`, `node_name`, and `wave_index` are filled from the active context/plan while explicit event values are preserved. Added `tests/unit/runtime/execution/test_runtime_engine_output_events.py` to verify subscribers receive emitted node-output events, that enrichment occurs on copied events, and that explicit event location metadata is not overwritten. Verification passed: `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/runtime/execution/test_runtime_engine_output_events.py tests/unit/runtime/execution/test_runtime_engine_control_manager.py tests/integration/runtime tests/integration/telemetry/test_core_telemetry_baseline.py tests/integration/telemetry/test_bootstrap_observability.py` (19 passed); targeted `ruff check`, `ruff format --check`, and `mypy --explicit-package-bases` passed for `core/runtime/execution/runtime_engine.py` and the new unit test; `UV_CACHE_DIR=/tmp/uv-cache uv run graphify update .` completed successfully.
- Step 4: Added canonical EventBus coverage for previously silent node paths. Disabled nodes and dependency skips now emit `NODE_SKIPPED` plus the new user-facing `NODE_PROGRESS_SKIPPED` event (`runtime.node.skipped`); missing runtime node registration now emits `NODE_FAILED` plus `NODE_PROGRESS_FAILED`; retryable failed attempts now emit `NODE_RETRYING` before the next attempt. Added telemetry taxonomy/mapping for skipped node progress (`RuntimeTelemetryEventType.NODE_PROGRESS_SKIPPED`) and expanded telemetry hook coverage so skipped progress maps cleanly without treating skips as failed progress. Added `tests/unit/runtime/execution/test_runtime_engine_node_events.py` for disabled node, dependency skip, missing registration, and retry events, and extended runtime telemetry hook tests for skipped progress mapping. Verification passed: `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/runtime/execution/test_runtime_engine_node_events.py tests/unit/runtime/execution/test_runtime_engine_output_events.py tests/unit/runtime/execution/test_runtime_engine_control_manager.py tests/unit/runtime/telemetry/test_runtime_telemetry_hook.py tests/unit/interfaces/cli/test_workflow_progress_service.py tests/integration/runtime tests/integration/telemetry/test_core_telemetry_baseline.py tests/integration/telemetry/test_bootstrap_observability.py` (30 passed, 1 external deprecation warning); targeted `ruff check`, `ruff format --check`, and `mypy --explicit-package-bases` passed for changed runtime/telemetry/test files; `UV_CACHE_DIR=/tmp/uv-cache uv run graphify update .` completed successfully.
- Step 5: Improved `EventBus` subscriber failure observability while preserving current non-fail-fast semantics. Non-fail-fast subscriber exceptions are now collected and reported as a canonical `SYSTEM_WARNING` runtime event with the original workflow/execution/runtime/node/wave context, failed event type, handler name, exception type, and message. Added recursion protection so failures while emitting the warning do not produce an infinite warning loop, and preserved `fail_fast=True` behavior unchanged. Added `tests/unit/runtime/events/test_event_bus_failure_observability.py` covering successful handler continuation, warning emission, recursive warning suppression, and unchanged fail-fast behavior. Verification passed: `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/runtime/events/test_event_bus_failure_observability.py tests/unit/runtime/control/test_workflow_control_events.py tests/unit/runtime/execution/test_runtime_engine_node_events.py tests/unit/runtime/execution/test_runtime_engine_output_events.py tests/unit/runtime/execution/test_runtime_engine_control_manager.py tests/unit/runtime/telemetry/test_runtime_telemetry_hook.py tests/integration/runtime tests/integration/telemetry/test_core_telemetry_baseline.py tests/integration/telemetry/test_bootstrap_observability.py` (33 passed); targeted `ruff check`, `ruff format --check`, and `mypy --explicit-package-bases` passed for changed EventBus/test files after formatting; `UV_CACHE_DIR=/tmp/uv-cache uv run graphify update .` completed successfully.
- Step 6: Wired structured telemetry logging by default through both runtime composition paths. Added `WorkflowBootstrapConfig.enable_telemetry_logging` with default `True` and `telemetry_logger_name` defaulting to `polaris.telemetry`; direct `WorkflowBootstrap` now registers `TelemetryLogger` with `ObservabilityManager` when logging is enabled, without configuring global logging handlers. Updated `WorkflowInfrastructureProvider` to accept an optional `WorkflowBootstrapConfig` and register the same `TelemetryLogger` in the Dishka path when observability and telemetry logging are enabled. Added bootstrap coverage for default, disabled, and custom logger-name behavior in the direct bootstrap path plus default/disabled Dishka provider behavior. Added `tests/unit/telemetry/test_telemetry_logger.py` with `caplog` coverage proving telemetry events become Python log records with structured `extra["telemetry"]`, and that payload/attribute omission options still work. Verification passed: `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/telemetry/test_telemetry_logger.py tests/integration/telemetry/test_bootstrap_observability.py tests/integration/workflow/test_workflow_provider_control.py tests/integration/governance/test_bootstrap_governance_provider.py tests/integration/runtime tests/unit/runtime/telemetry/test_runtime_telemetry_hook.py tests/integration/telemetry/test_core_telemetry_baseline.py` (24 passed); targeted `ruff check`, `ruff format --check`, and `mypy --explicit-package-bases` passed for changed bootstrap/provider/logging test files after formatting; `UV_CACHE_DIR=/tmp/uv-cache uv run graphify update .` completed successfully.
- Step 7: Added domain operational metrics mapping while preserving the existing generic telemetry metrics. Introduced `DomainMetricsRecorder` in `core/telemetry/observability/domain_metrics.py` so domain-specific metric routing stays out of `ObservabilityManager` conditional logic. `ObservabilityManager` now records the existing `telemetry.events.total`, `telemetry.events.errors`, and `telemetry.event.duration_seconds` metrics first, then delegates optional domain metrics recording when `enable_domain_metrics=True`. Added `WorkflowBootstrapConfig.enable_domain_metrics` with default `True`; direct `WorkflowBootstrap` and Dishka `WorkflowInfrastructureProvider` pass the flag into constructed `ObservabilityManager` instances. Domain metrics now cover workflow executions/failures/duration, runtime node totals/failures/skips/duration, application service calls/failures/duration, integration provider calls/failures/duration, and intelligence agent signal totals. Added `tests/unit/telemetry/test_domain_metrics_mapper.py` covering runtime workflow/node metrics, application/provider/intelligence metrics, metric attributes, duration observations, and disabling domain metrics. Verification passed: `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/telemetry/test_domain_metrics_mapper.py tests/unit/telemetry/test_application_telemetry.py tests/unit/telemetry/test_integration_intelligence_telemetry.py tests/unit/telemetry/test_telemetry_logger.py tests/integration/telemetry/test_observability_pipeline.py tests/integration/telemetry/test_bootstrap_observability.py tests/integration/telemetry/test_core_telemetry_baseline.py tests/unit/runtime/telemetry/test_runtime_telemetry_hook.py tests/integration/runtime` (31 passed); targeted `ruff check`, `ruff format --check`, and `mypy --explicit-package-bases` passed for changed observability/bootstrap/provider/test files after formatting; `UV_CACHE_DIR=/tmp/uv-cache uv run graphify update .` completed successfully.
- Step 8: Propagated telemetry context through canonical application service execution. Added optional `telemetry_context: TelemetryContext | None` to `ServiceRequest` and included a serialized telemetry context in `policy_context()` and `to_dict()` for boundary visibility. Added `core/telemetry/context.py` with an async-safe contextvar-backed active telemetry context scope, and updated `ServiceRunner.run(...)` to activate the request telemetry context around validation, policy evaluation, service execution, retries, and service telemetry emission. Updated `ApplicationTelemetry` service/analysis/data-quality emitters to accept optional `TelemetryContext` and copy workflow, execution, runtime, node, correlation, tags, and context attributes onto emitted `TelemetryEvent` records while preserving existing call behavior when no context is provided. Added ServiceRunner tests proving success events, failed validation events, and the active context scope carry runtime correlation fields. Verification passed: `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/application/services/base/test_service_runner.py tests/unit/telemetry/test_application_telemetry.py tests/unit/telemetry/test_domain_metrics_mapper.py tests/integration/telemetry/test_core_telemetry_baseline.py tests/integration/telemetry/test_bootstrap_observability.py` (23 passed); targeted `ruff check`, `ruff format --check`, and `mypy --explicit-package-bases` passed for changed service/telemetry/test files after formatting; `UV_CACHE_DIR=/tmp/uv-cache uv run graphify update .` completed successfully.
- Step 9: Correlated integration provider telemetry with active application service telemetry context. Updated `record_provider_call(...)` to accept an optional explicit `TelemetryContext`; when one is not provided, it reads the active async telemetry context established by `ServiceRunner`, so provider calls made inside service execution inherit workflow, execution, runtime, node, correlation, tags, and context attributes without changing existing provider method signatures. Updated `IntegrationTelemetry.emit_provider_call(...)` to keep provider name and operation in attributes while also placing provider name, operation, success, and duration in payload; failure payloads continue to include error type/message and now remain correlated to runtime/service context. Added provider telemetry tests covering active context inheritance, explicit context override, failure/error-level telemetry, and domain metrics for provider total/failed/duration. Verification passed: `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/integration/providers/test_provider_telemetry.py tests/unit/telemetry/test_integration_intelligence_telemetry.py tests/unit/application/services/base/test_service_runner.py tests/unit/telemetry/test_domain_metrics_mapper.py` (16 passed); targeted `ruff check`, `ruff format --check`, and `mypy --explicit-package-bases` passed for changed provider/integration telemetry test files after formatting; `UV_CACHE_DIR=/tmp/uv-cache uv run graphify update .` completed successfully.
- Step 10: Propagated runtime-derived telemetry context from service-calling intelligence nodes into canonical `ServiceRequest` envelopes. Added `intelligence.telemetry.telemetry_context_from_runtime(...)` to build `TelemetryContext` from `RuntimeContext` with workflow, execution, runtime, node, correlation, runtime/intelligence tags, and runtime mode attributes. Updated TechnicalAgent, FundamentalAgent, NewsAgent, SentimentAgent, PortfolioStateBuilder, and StrategySynthesisAgent service calls to pass this context without adding vendor/transport dependencies or changing business outputs. Added representative coverage in `tests/unit/intelligence/analysts/technical/test_technical_agent.py` plus helper coverage in `tests/unit/intelligence/telemetry/test_runtime_context.py`. Verification passed: `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/intelligence/telemetry/test_runtime_context.py tests/unit/intelligence/analysts/technical/test_technical_agent.py tests/unit/intelligence/portfolio/test_portfolio_state_builder.py tests/unit/intelligence/strategy/test_strategy_synthesis_breadth_gating.py tests/unit/application/services/base/test_service_runner.py tests/unit/integration/providers/test_provider_telemetry.py` (20 passed); targeted `ruff check` passed for changed intelligence files/tests; targeted `mypy --explicit-package-bases` passed for changed intelligence files/tests; `UV_CACHE_DIR=/tmp/uv-cache uv run graphify update .` completed successfully. Note: full `ruff format --check` on legacy intelligence agent files still reports they would be reformatted, so broad formatting was intentionally not applied to avoid unrelated churn in hotspot files.
- Step 11: Filled representative intelligence fallback/error telemetry gaps in `StrategySynthesisAgent`. Missing upstream dependencies now emit `strategy_synthesis.fallback_output` before returning fallback outputs; low synthesis confidence emits `strategy_synthesis.low_confidence`; degraded market-events data/service failures emit `strategy_synthesis.degraded_data_quality` before using neutral market-event fallback data. All new emissions use `IntelligenceTelemetry.emit_agent_signal(...)` with runtime-derived `TelemetryContext` from `telemetry_context_from_runtime(...)`; business outputs remain unchanged. Added strategy synthesis coverage for missing-upstream fallback telemetry, degraded data-quality telemetry, and low-confidence telemetry, and updated the local test telemetry fake to assert runtime correlation fields. Verification passed: `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check intelligence/strategy/synthesis/strategy_synthesis_agent.py tests/unit/intelligence/strategy/test_strategy_synthesis_breadth_gating.py`; `UV_CACHE_DIR=/tmp/uv-cache uv run mypy intelligence/strategy/synthesis/strategy_synthesis_agent.py tests/unit/intelligence/strategy/test_strategy_synthesis_breadth_gating.py --explicit-package-bases`; `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/intelligence/strategy/test_strategy_synthesis_breadth_gating.py tests/unit/intelligence/telemetry/test_runtime_context.py tests/unit/intelligence/analysts/technical/test_technical_agent.py tests/unit/intelligence/portfolio/test_portfolio_state_builder.py tests/unit/application/services/base/test_service_runner.py tests/unit/integration/providers/test_provider_telemetry.py tests/unit/telemetry/test_integration_intelligence_telemetry.py` (24 passed); `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format tests/unit/intelligence/strategy/test_strategy_synthesis_breadth_gating.py --check`; `UV_CACHE_DIR=/tmp/uv-cache uv run graphify update .`. Note: broad formatting of the legacy hotspot `strategy_synthesis_agent.py` was intentionally not applied to avoid unrelated churn.
- Step 12: Validated and tightened the OpenTelemetry integration while keeping it opt-in. `WorkflowBootstrapConfig.enable_opentelemetry` remains `False` by default; direct `WorkflowBootstrap` already wired `OpenTelemetrySink` when enabled, and the Dishka `WorkflowInfrastructureProvider` now wires the same sink when `enable_opentelemetry=True`. Updated `OpenTelemetrySink` to use its own `TracerProvider` directly instead of mutating the global OpenTelemetry tracer provider, and added optional injected `SpanExporter` support so tests can use an in-memory exporter without requiring a local OTLP collector. OpenTelemetry span mapping now includes `correlation.id`, `provider.name`, and `provider.operation` in addition to existing workflow/execution/runtime/node attributes. Expanded `tests/integration/telemetry/test_opentelemetry_sink.py` to assert emitted span attributes using `InMemorySpanExporter`, and expanded bootstrap observability tests to prove OpenTelemetry is not wired by default and is wired in both direct and Dishka composition paths when enabled. Verification passed: `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check core/telemetry/integrations/opentelemetry/opentelemetry_sink.py core/bootstrap/workflow_providers.py tests/integration/telemetry/test_opentelemetry_sink.py tests/integration/telemetry/test_bootstrap_observability.py`; `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format core/telemetry/integrations/opentelemetry/opentelemetry_sink.py core/bootstrap/workflow_providers.py tests/integration/telemetry/test_opentelemetry_sink.py tests/integration/telemetry/test_bootstrap_observability.py --check`; `UV_CACHE_DIR=/tmp/uv-cache uv run mypy core/telemetry/integrations/opentelemetry/opentelemetry_sink.py core/bootstrap/workflow_providers.py tests/integration/telemetry/test_opentelemetry_sink.py tests/integration/telemetry/test_bootstrap_observability.py --explicit-package-bases`; `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/integration/telemetry/test_opentelemetry_sink.py tests/integration/telemetry/test_bootstrap_observability.py tests/unit/telemetry/test_telemetry_logger.py tests/unit/telemetry/test_domain_metrics_mapper.py tests/integration/telemetry/test_core_telemetry_baseline.py` (17 passed); `UV_CACHE_DIR=/tmp/uv-cache uv run graphify update .`.
- Step 13: Connected telemetry persistence intentionally without changing default runtime behavior. Added `TelemetryPersistenceMapper` to convert core `TelemetryEvent` objects into typed optional persistence bundles: telemetry event records, workflow metrics for runtime workflow lifecycle events, provider metrics for `integration.provider.call`, agent metrics for `intelligence.agent.signal`, and trace records when `trace_id`/`span_id` are present in telemetry attributes or payload. Added `TelemetryPersistenceSink` plus disabled-by-default `TelemetryPersistenceSinkConfig`, so PostgreSQL telemetry persistence remains opt-in and does not replace lightweight JSONL runtime telemetry until an explicit retention/volume policy enables it. Exported the new mapper/sink from `application.persistence.telemetry` and added targeted mapper/sink tests covering workflow, provider, agent, trace, disabled sink, enabled sink, non-fail-fast failure swallowing, and fail-fast errors. Verification passed: `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check application/persistence/telemetry/telemetry_event_mapper.py application/persistence/telemetry/telemetry_persistence_sink.py application/persistence/telemetry/__init__.py tests/unit/application/persistence/telemetry/test_telemetry_event_mapper.py tests/unit/application/persistence/telemetry/test_telemetry_persistence_sink.py`; `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format application/persistence/telemetry/telemetry_event_mapper.py application/persistence/telemetry/telemetry_persistence_sink.py application/persistence/telemetry/__init__.py tests/unit/application/persistence/telemetry/test_telemetry_event_mapper.py tests/unit/application/persistence/telemetry/test_telemetry_persistence_sink.py --check`; `UV_CACHE_DIR=/tmp/uv-cache uv run mypy application/persistence/telemetry tests/unit/application/persistence/telemetry/test_telemetry_event_mapper.py tests/unit/application/persistence/telemetry/test_telemetry_persistence_sink.py --explicit-package-bases`; `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/application/persistence/telemetry/test_telemetry_event_mapper.py tests/unit/application/persistence/telemetry/test_telemetry_persistence_sink.py tests/unit/application/persistence/telemetry/test_telemetry_persistence_service.py tests/unit/core/storage/persistence/test_telemetry_persistence_contracts.py` (31 passed); `UV_CACHE_DIR=/tmp/uv-cache GRAPHIFY_VIZ_NODE_LIMIT=10000 uv run graphify update .` completed successfully. Important architectural note: - PostgreSQL telemetry persistence remains opt-in. - Runtime JSONL telemetry remains the lightweight default. - No core bootstrap wiring was added for PostgreSQL persistence in this step, which avoids forcing durable storage before retention/volume policy is defined.
- Step 14: Added an integration audit test that prevents future telemetry wiring regressions across the current core telemetry surface. New `tests/integration/telemetry/test_telemetry_coverage_audit.py` builds the runtime/EventBus/lifecycle telemetry path into `ObservabilityManager`, attaches both an in-memory sink and `TelemetryLogger`, executes a minimal runtime workflow, emits workflow control events, emits integration provider telemetry, and emits intelligence agent telemetry. The audit asserts representative events reach observability for runtime lifecycle, workflow progress, workflow control, provider calls, and intelligence agent signals; asserts the logging sink receives structured telemetry records; and asserts metrics are recorded for generic telemetry, workflow duration/executions, provider calls/duration, and intelligence agent signals. Verification passed: `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check tests/integration/telemetry/test_telemetry_coverage_audit.py`; `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format tests/integration/telemetry/test_telemetry_coverage_audit.py --check`; `UV_CACHE_DIR=/tmp/uv-cache uv run mypy tests/integration/telemetry/test_telemetry_coverage_audit.py --explicit-package-bases`; `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/integration/telemetry/test_telemetry_coverage_audit.py tests/integration/telemetry/test_core_telemetry_baseline.py tests/unit/telemetry/test_domain_metrics_mapper.py tests/unit/telemetry/test_telemetry_logger.py tests/unit/telemetry/test_integration_intelligence_telemetry.py tests/unit/integration/providers/test_provider_telemetry.py` (15 passed); broader telemetry suite `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/telemetry tests/unit/runtime/telemetry tests/integration/telemetry` passed (31 passed); `UV_CACHE_DIR=/tmp/uv-cache GRAPHIFY_VIZ_NODE_LIMIT=10000 uv run graphify update .` completed successfully.
- Step 15: Defined the canonical trace context contract for internal telemetry propagation. Extended `TelemetryContext` with optional `trace_id`, `span_id`, and `parent_span_id` fields plus `from_trace_context(...)`, `with_trace_context(...)`, `to_trace_context()`, and canonical `trace_attributes()` helpers. Updated `TelemetryContext.merged_attributes(...)` so trace identifiers are always emitted as canonical attributes when present. Added `TraceContext.telemetry_attributes()` and updated `ObservabilityManager` / `TelemetryLifecycle` trace-context paths so events emitted with a `TraceContext` now include `trace_id`, `span_id`, and `parent_span_id` attributes in addition to workflow/execution/runtime/node/correlation fields. Added `tests/unit/telemetry/test_telemetry_context.py` covering TraceContext ↔ TelemetryContext bridging, canonical attribute precedence, ObservabilityManager trace-context emission, and generic TelemetryEmitter trace attributes. Verification passed: `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check core/telemetry/contracts/telemetry_context.py core/telemetry/tracing/trace_context.py core/telemetry/observability/observability_manager.py core/telemetry/lifecycle/telemetry_lifecycle.py tests/unit/telemetry/test_telemetry_context.py tests/unit/telemetry/test_application_telemetry.py tests/unit/telemetry/test_integration_intelligence_telemetry.py`; `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format core/telemetry/contracts/telemetry_context.py core/telemetry/tracing/trace_context.py core/telemetry/observability/observability_manager.py core/telemetry/lifecycle/telemetry_lifecycle.py tests/unit/telemetry/test_telemetry_context.py tests/unit/telemetry/test_application_telemetry.py tests/unit/telemetry/test_integration_intelligence_telemetry.py --check`; `UV_CACHE_DIR=/tmp/uv-cache uv run mypy core/telemetry/contracts/telemetry_context.py core/telemetry/tracing/trace_context.py core/telemetry/observability/observability_manager.py core/telemetry/lifecycle/telemetry_lifecycle.py tests/unit/telemetry/test_telemetry_context.py tests/unit/telemetry/test_application_telemetry.py tests/unit/telemetry/test_integration_intelligence_telemetry.py --explicit-package-bases`; `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/telemetry/test_telemetry_context.py tests/unit/telemetry/test_application_telemetry.py tests/unit/telemetry/test_integration_intelligence_telemetry.py` (14 passed); `UV_CACHE_DIR=/tmp/uv-cache GRAPHIFY_VIZ_NODE_LIMIT=10000 uv run graphify update .` completed successfully. Repowise pre-flight noted `ObservabilityManager` and `OpenTelemetrySink` are hotspots, so this step kept changes surgical and added focused tests before broader runtime propagation.
- Step 16: Activated one canonical root `TraceContext` at workflow execution start. `RuntimeContext` now carries an optional typed `TraceContext`, serializes it through `to_dict()`, restores it from dictionaries via validation, and exposes `with_trace_context(...)` for immutable propagation. `RuntimeEngine` now creates a root trace context through `ObservabilityManager.create_trace_context(...)` when execution starts and preserves any pre-existing context; direct `WorkflowFacade` construction now passes the shared `ObservabilityManager` into the runtime engine. Workflow lifecycle telemetry (`runtime.workflow.started` / completed / failed) now includes the root `trace_id` and `span_id`, and workflow progress events include the same trace identity in runtime event payload/metadata for downstream observability. Added unit coverage for lifecycle telemetry trace payloads and integration coverage proving a real runtime execution creates a root trace and emits matching workflow start/completion/progress trace IDs. Verification passed: `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check core/runtime/state/runtime_context.py core/runtime/execution/runtime_engine.py core/runtime/telemetry/runtime_telemetry_hook.py core/workflow/execution/workflow_facade.py tests/unit/runtime/telemetry/test_runtime_telemetry_hook.py tests/integration/telemetry/test_core_telemetry_baseline.py`; `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format core/runtime/state/runtime_context.py core/runtime/execution/runtime_engine.py core/runtime/telemetry/runtime_telemetry_hook.py core/workflow/execution/workflow_facade.py tests/unit/runtime/telemetry/test_runtime_telemetry_hook.py tests/integration/telemetry/test_core_telemetry_baseline.py --check`; `UV_CACHE_DIR=/tmp/uv-cache uv run mypy core/runtime/state/runtime_context.py core/runtime/execution/runtime_engine.py core/runtime/telemetry/runtime_telemetry_hook.py core/workflow/execution/workflow_facade.py tests/unit/runtime/telemetry/test_runtime_telemetry_hook.py tests/integration/telemetry/test_core_telemetry_baseline.py`; `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/runtime/telemetry/test_runtime_telemetry_hook.py tests/integration/telemetry/test_core_telemetry_baseline.py tests/unit/telemetry/test_telemetry_context.py` (13 passed); `UV_CACHE_DIR=/tmp/uv-cache GRAPHIFY_VIZ_NODE_LIMIT=10000 uv run graphify update .` completed successfully. Repowise pre-flight identified `RuntimeEngine` and `RuntimeContext` as high-churn/high-impact files, so this step intentionally kept the change limited to root trace creation/propagation and workflow-level telemetry only; child node spans remain for Step 17.
- Step 17: Created canonical child trace contexts for runtime node execution without changing workflow business outputs or allowing the aggregate workflow context to drift away from the root trace. `RuntimeEngine` now derives a per-node child `TraceContext` from the workflow root, passes that child context into node execution, node lifecycle telemetry, node progress events, retry events, skipped-node events, missing-node failure events, and node output event enrichment while restoring the root trace on the returned workflow context. `RuntimeTelemetryHook` now includes canonical trace identifiers on node started/completed/failed/skipped lifecycle telemetry payloads. Added/expanded tests proving runtime nodes execute with a child span, node lifecycle telemetry and progress telemetry carry the workflow `trace_id`, node child `span_id`, and `parent_span_id` linking back to the workflow root, and skipped/failed/retry runtime node events include the same child trace linkage in payload and metadata. Verification passed: `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check core/runtime/execution/runtime_engine.py core/runtime/telemetry/runtime_telemetry_hook.py tests/unit/runtime/telemetry/test_runtime_telemetry_hook.py tests/integration/telemetry/test_core_telemetry_baseline.py tests/unit/runtime/execution/test_runtime_engine_node_events.py --fix`; `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format core/runtime/execution/runtime_engine.py core/runtime/telemetry/runtime_telemetry_hook.py tests/unit/runtime/telemetry/test_runtime_telemetry_hook.py tests/integration/telemetry/test_core_telemetry_baseline.py tests/unit/runtime/execution/test_runtime_engine_node_events.py --check`; `UV_CACHE_DIR=/tmp/uv-cache uv run mypy core/runtime/execution/runtime_engine.py core/runtime/telemetry/runtime_telemetry_hook.py tests/unit/runtime/telemetry/test_runtime_telemetry_hook.py tests/integration/telemetry/test_core_telemetry_baseline.py tests/unit/runtime/execution/test_runtime_engine_node_events.py`; `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/runtime/telemetry/test_runtime_telemetry_hook.py tests/integration/telemetry/test_core_telemetry_baseline.py tests/unit/runtime/execution/test_runtime_engine_node_events.py tests/unit/runtime/execution/test_runtime_engine_control_manager.py` (21 passed); `UV_CACHE_DIR=/tmp/uv-cache GRAPHIFY_VIZ_NODE_LIMIT=10000 uv run graphify update .` completed successfully. Repowise pre-flight again identified `RuntimeEngine` as a high-churn hotspot/god class, so the implementation was intentionally limited to small trace-context helpers plus surgical call-site changes.
- Step 18: Completed application-service trace propagation coverage and filled the remaining serialization gap in the canonical `ServiceRequest` envelope. `ServiceRequest.policy_context()` / `to_dict()` now include `trace_id`, `span_id`, and `parent_span_id` when a telemetry context is present, preserving trace identity at policy and serialization boundaries. Existing `ServiceRunner` active-context propagation and `ApplicationTelemetry` context mapping were verified with stronger tests: service success/failure telemetry now asserts workflow/execution/runtime/node/correlation plus canonical trace attributes, the active async telemetry context inside service execution carries the same trace identifiers, and direct application telemetry emits trace attributes on service events. Verification passed: `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check application/services/base/service_request.py tests/unit/application/services/base/test_service_runner.py tests/unit/telemetry/test_application_telemetry.py --fix`; `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format application/services/base/service_request.py tests/unit/application/services/base/test_service_runner.py tests/unit/telemetry/test_application_telemetry.py --check`; `UV_CACHE_DIR=/tmp/uv-cache uv run mypy application/services/base/service_request.py application/services/base/service_runner.py core/telemetry/emitters/application_telemetry.py core/telemetry/contracts/telemetry_context.py tests/unit/application/services/base/test_service_runner.py tests/unit/telemetry/test_application_telemetry.py --explicit-package-bases`; `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/application/services/base/test_service_runner.py tests/unit/telemetry/test_application_telemetry.py tests/unit/telemetry/test_telemetry_context.py tests/unit/integration/providers/test_provider_telemetry.py` (24 passed); `UV_CACHE_DIR=/tmp/uv-cache GRAPHIFY_VIZ_NODE_LIMIT=10000 uv run graphify update .` completed successfully. Repowise pre-flight flagged `ServiceRunner` as churn-heavy and `TelemetryContext` as high-coupling, so this step avoided broad refactors and limited code changes to the missing request-envelope trace fields plus focused regression tests.
- Step 19: Verified provider-call trace propagation without changing provider business signatures. `record_provider_call(...)` already captures the explicit or active `TelemetryContext` once at the provider boundary and passes it to `IntegrationTelemetry`; `IntegrationTelemetry` routes through the base `TelemetryEmitter`, whose canonical `TelemetryContext.merged_attributes(...)` emits `trace_id`, `span_id`, and `parent_span_id` attributes. Strengthened provider telemetry tests so successful active-context calls, explicit-context override calls, and failed active-context calls all assert inherited trace identifiers, and strengthened the direct integration telemetry emitter test to assert workflow/execution/runtime/node/correlation plus canonical trace attributes. Verification passed: `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check integration/providers/provider_telemetry.py core/telemetry/emitters/integration_telemetry.py tests/unit/integration/providers/test_provider_telemetry.py tests/unit/telemetry/test_integration_intelligence_telemetry.py --fix`; `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format integration/providers/provider_telemetry.py core/telemetry/emitters/integration_telemetry.py tests/unit/integration/providers/test_provider_telemetry.py tests/unit/telemetry/test_integration_intelligence_telemetry.py --check`; `UV_CACHE_DIR=/tmp/uv-cache uv run mypy integration/providers/provider_telemetry.py core/telemetry/emitters/integration_telemetry.py core/telemetry/contracts/telemetry_context.py core/telemetry/context.py tests/unit/integration/providers/test_provider_telemetry.py tests/unit/telemetry/test_integration_intelligence_telemetry.py --explicit-package-bases`; `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/integration/providers/test_provider_telemetry.py tests/unit/telemetry/test_integration_intelligence_telemetry.py tests/unit/application/services/base/test_service_runner.py tests/unit/telemetry/test_application_telemetry.py` (20 passed); `UV_CACHE_DIR=/tmp/uv-cache GRAPHIFY_VIZ_NODE_LIMIT=10000 uv run graphify update .` completed successfully. Repowise pre-flight flagged provider telemetry as high-coupling/feature-active, so this step intentionally avoided production refactors and limited changes to focused trace regression coverage.
- Step 20: Completed runtime-derived trace propagation through intelligence telemetry. Updated `telemetry_context_from_runtime(...)` to preserve the active runtime node `TraceContext` as canonical `TelemetryContext` fields (`trace_id`, `span_id`, `parent_span_id`) while keeping runtime/intelligence tags and runtime mode attributes. Updated TechnicalAgent, FundamentalAgent, NewsAgent, SentimentAgent, PortfolioStateBuilder, and existing StrategySynthesisAgent paths so intelligence agent signal emissions include runtime-derived telemetry context without adding vendor or transport dependencies. Strengthened tests for the helper, direct `IntelligenceTelemetry.emit_agent_signal(...)`, and representative TechnicalAgent service-request plus intelligence-signal propagation. Verification passed: `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check intelligence/telemetry/runtime_context.py intelligence/analysts/technical/technical_agent.py intelligence/analysts/fundamental/fundamental_agent.py intelligence/research/news/news_agent.py intelligence/research/sentiment/sentiment_agent.py intelligence/portfolio/management/portfolio_state_builder.py core/telemetry/emitters/intelligence_telemetry.py tests/unit/intelligence/telemetry/test_runtime_context.py tests/unit/intelligence/analysts/technical/test_technical_agent.py tests/unit/intelligence/portfolio/test_portfolio_state_builder.py tests/unit/telemetry/test_integration_intelligence_telemetry.py --fix`; `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format intelligence/telemetry/runtime_context.py tests/unit/intelligence/telemetry/test_runtime_context.py tests/unit/intelligence/analysts/technical/test_technical_agent.py tests/unit/intelligence/portfolio/test_portfolio_state_builder.py tests/unit/telemetry/test_integration_intelligence_telemetry.py --check`; `UV_CACHE_DIR=/tmp/uv-cache uv run mypy intelligence/telemetry/runtime_context.py intelligence/analysts/technical/technical_agent.py intelligence/analysts/fundamental/fundamental_agent.py intelligence/research/news/news_agent.py intelligence/research/sentiment/sentiment_agent.py intelligence/portfolio/management/portfolio_state_builder.py core/telemetry/emitters/intelligence_telemetry.py tests/unit/intelligence/telemetry/test_runtime_context.py tests/unit/intelligence/analysts/technical/test_technical_agent.py tests/unit/intelligence/portfolio/test_portfolio_state_builder.py tests/unit/telemetry/test_integration_intelligence_telemetry.py --explicit-package-bases`; `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/intelligence/telemetry/test_runtime_context.py tests/unit/intelligence/analysts/technical/test_technical_agent.py tests/unit/intelligence/portfolio/test_portfolio_state_builder.py tests/unit/intelligence/strategy/test_strategy_synthesis_breadth_gating.py tests/unit/telemetry/test_integration_intelligence_telemetry.py tests/unit/application/services/base/test_service_runner.py tests/unit/integration/providers/test_provider_telemetry.py` (25 passed); `UV_CACHE_DIR=/tmp/uv-cache GRAPHIFY_VIZ_NODE_LIMIT=10000 uv run graphify update .` completed successfully. Repowise pre-flight flagged TechnicalAgent and StrategySynthesisAgent as high-churn hotspots/god-class risk, so this step kept agent changes surgical and avoided broad formatting/refactoring of legacy hotspot files.
- Step 21: Updated boundary consumers for canonical trace fields. `OpenTelemetrySink` now promotes canonical `trace_id`, `span_id`, and `parent_span_id` from telemetry event attributes/payload into first-class OpenTelemetry span attributes (`trace.id`, `span.id`, `parent_span.id`) while preserving existing `attr.*` serialized attributes and keeping OpenTelemetry optional/boundary-only. The telemetry persistence mapper already produced trace records from canonical event fields; its coverage was strengthened to assert parent-span linkage and trace attributes on persisted `TelemetryTraceRecord` objects. Verification passed: `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check core/telemetry/integrations/opentelemetry/opentelemetry_sink.py application/persistence/telemetry/telemetry_event_mapper.py tests/integration/telemetry/test_opentelemetry_sink.py tests/unit/application/persistence/telemetry/test_telemetry_event_mapper.py --fix`; `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format core/telemetry/integrations/opentelemetry/opentelemetry_sink.py application/persistence/telemetry/telemetry_event_mapper.py tests/integration/telemetry/test_opentelemetry_sink.py tests/unit/application/persistence/telemetry/test_telemetry_event_mapper.py --check`; `UV_CACHE_DIR=/tmp/uv-cache uv run mypy core/telemetry/integrations/opentelemetry/opentelemetry_sink.py application/persistence/telemetry/telemetry_event_mapper.py tests/integration/telemetry/test_opentelemetry_sink.py tests/unit/application/persistence/telemetry/test_telemetry_event_mapper.py --explicit-package-bases`; `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/integration/telemetry/test_opentelemetry_sink.py tests/unit/application/persistence/telemetry/test_telemetry_event_mapper.py tests/unit/application/persistence/telemetry/test_telemetry_persistence_sink.py tests/unit/application/persistence/telemetry/test_telemetry_persistence_service.py tests/unit/core/storage/persistence/test_telemetry_persistence_contracts.py tests/unit/telemetry/test_telemetry_context.py` (38 passed); `UV_CACHE_DIR=/tmp/uv-cache GRAPHIFY_VIZ_NODE_LIMIT=10000 uv run graphify update .` completed successfully. Repowise pre-flight flagged both OpenTelemetry sink and persistence mapper as churn-heavy, so changes were limited to a small trace attribute mapper plus focused regression assertions.
- Step 22: Added end-to-end trace propagation audit coverage in `tests/integration/telemetry/test_telemetry_coverage_audit.py`. The new audit uses a real `RuntimeEngine` execution with a tracking `ObservabilityManager` to prove `create_trace_context()` is invoked on the workflow path, derives a runtime-node child span, propagates that canonical trace identity through a `ServiceRunner` application service, inherited provider telemetry via `record_provider_call(...)`, intelligence telemetry via `IntelligenceTelemetry`, collector-free OpenTelemetry export through `InMemorySpanExporter`, and PostgreSQL persistence mapping through `TelemetryPersistenceMapper`. The audit asserts workflow root trace identity, node child `span_id` / `parent_span_id` linkage, OpenTelemetry `trace.id` / `span.id` / `parent_span.id` attributes, and persisted `TelemetryTraceRecord` lineage. Verification passed: `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check tests/integration/telemetry/test_telemetry_coverage_audit.py --fix`; `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format tests/integration/telemetry/test_telemetry_coverage_audit.py --check`; `UV_CACHE_DIR=/tmp/uv-cache uv run mypy tests/integration/telemetry/test_telemetry_coverage_audit.py --explicit-package-bases`; `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/telemetry tests/unit/runtime/telemetry tests/unit/application/services/base tests/unit/integration/providers tests/integration/telemetry` (53 passed); `UV_CACHE_DIR=/tmp/uv-cache GRAPHIFY_VIZ_NODE_LIMIT=10000 uv run graphify update .` completed successfully. Repowise pre-flight flagged `RuntimeEngine` and `ObservabilityManager` as high-churn/high-impact, so this step intentionally added audit coverage only and made no production runtime or observability code changes.
