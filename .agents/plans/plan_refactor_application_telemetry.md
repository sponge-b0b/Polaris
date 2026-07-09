  # Refactor Application Telemetry into ServiceRunner and RAG-Specific Emitters

  ## Summary / Design Findings

  I agree with your assessment.

  The current implementation overloads ApplicationTelemetry with two different meanings:

  1. Canonical application service lifecycle telemetry
      - Owned by ServiceRunner.
      - Built around ServiceRequest, ServiceResult, request_name, request_id, policy context, retries, and validation.
      - Correct event family: application.service.started|completed|failed.

  2. RAG pipeline/component telemetry
      - Used by CuratedRagIngestionService, RagService, RagRetriever, RagAnswerGenerator, and EmbeddingJobProcessor.
      - These are RAG orchestration/pipeline components, not ServiceRunner-managed services.
      - They need operation/stage telemetry such as rag.ingestion.persist_source, rag.retrieval.vector_search, rag.embedding.job, etc.

  The current operation field was added to make RAG stage telemetry fit into ApplicationTelemetry, but that polluted the ServiceRunner telemetry contract. The two code smells you identified are real:

  - core/telemetry/emitters/application_telemetry.py::_resolve_operation
  - application/services/base/service_runner.py::_request_operation

  Both exist only because one emitter is trying to support incompatible semantics.

  Repowise also flags the impacted files as active hotspots, especially:

  - core/telemetry/emitters/application_telemetry.py
  - application/services/base/service_runner.py
  - application/rag/curated_rag_document_builder.py

  So the implementation should be surgical and test-driven.

  ## Proposed Architecture

  Introduce two explicit telemetry emitters:

  ### ApplicationServiceTelemetry

  Purpose: canonical ServiceRunner lifecycle telemetry only.

  Event types:

  application.service.started
  application.service.completed
  application.service.failed

  Required concepts:

  service_name
  request_name
  request_id
  correlation_id
  TelemetryContext
  duration_seconds
  success/failure
  validation_errors
  attempts

  Important rule:

  No operation field.

  ServiceRunner should depend on ApplicationServiceTelemetry, not generic ApplicationTelemetry.

  ### ApplicationRagTelemetry

  Purpose: RAG pipeline/component/stage telemetry.

  Event types:

  application.rag.operation.started
  application.rag.operation.completed
  application.rag.operation.failed

  Required concepts:

  component_name
  operation
  correlation_id
  duration_seconds
  attributes
  payload
  error metadata

  Examples:

  component_name = CuratedRagIngestionService
  operation = rag.ingestion.persist_source

  component_name = RagRetriever
  operation = rag.retrieval.vector_search

  component_name = EmbeddingJobProcessor
  operation = rag.embedding.job

  Important rule:

  No request_name.

  This keeps operation where it belongs: RAG operational telemetry, not ServiceRunner lifecycle telemetry.

  ## Implementation Plan

  ### Step 1 — Split the telemetry emitters

  Create two dedicated emitter modules:

  core/telemetry/emitters/application_service_telemetry.py
  core/telemetry/emitters/application_rag_telemetry.py

  Implement:

  - ApplicationServiceTelemetry
      - Based on the current service lifecycle behavior.
      - Remove operation from public methods.
      - Remove _resolve_operation.
      - Preserve trace/context propagation behavior.

  - ApplicationRagTelemetry
      - Emits application.rag.operation.started|completed|failed.
      - Requires explicit operation.
      - Includes component_name and operation in attributes and payload.
      - Uses TelemetryContext support consistently with other emitters.

  Do not keep a long-term ApplicationTelemetry compatibility wrapper unless an implementation blocker is discovered.

  ### Step 2 — Refactor ServiceRunner

  Update application/services/base/service_runner.py:

  - Replace ApplicationTelemetry with ApplicationServiceTelemetry.
  - Remove _request_operation.
  - Stop reading request.metadata["operation"].
  - Emit service lifecycle events with:
      - service_name
      - request_name
      - request_id
      - attempts
      - validation errors
      - duration
      - telemetry context

  Do not change ServiceRequest.metadata; it remains valid for policy/request metadata, just not for telemetry operation routing.

  ### Step 3 — Refactor RAG components to use RAG telemetry

  Update RAG components that currently use ApplicationTelemetry:

  application/rag/curated_rag_document_builder.py
  application/rag/rag_service.py
  application/rag/rag_retriever.py
  application/rag/generation/answer_generator.py
  application/rag/embedding_job_processor.py

  For each component:

  - Inject ApplicationRagTelemetry | None.
  - Replace emit_service_started/completed/failed calls with RAG operation telemetry calls.
  - Preserve existing operation names.
  - Preserve existing attributes and duration fields.
  - Remove fake service/request pairs such as:
      - "CuratedRagIngestionService", "persist_source"
      - "RagRetriever", "retrieve_stage"
      - "EmbeddingJobProcessor", "process_job"

  The component name becomes component_name; the operation remains the RAG stage name.

  ### Step 4 — Update DI wiring

  Update application/services/di.py:

  - Provide ApplicationServiceTelemetry for ServiceRunner.
  - Provide ApplicationRagTelemetry as a separate app-scoped dependency.
  - Do not inject service telemetry into RAG components.
  - Do not make RAG components use ServiceRunner just to fit telemetry.

  ### Step 5 — Update domain metrics mapping

  Update core/telemetry/observability/domain_metrics.py:

  Keep existing service metrics:

  application.service.calls.total
  application.service.calls.failed
  application.service.duration_seconds

  Add RAG-specific metrics:

  application.rag.operations.total
  application.rag.operations.failed
  application.rag.operation.duration_seconds

  For RAG metric attributes, include:

  component_name
  operation
  workflow_id
  runtime_id
  node_name

  Service metrics should no longer rely on or expect operation.

  ### Step 6 — Update tests

  Update or split telemetry tests:

  tests/unit/telemetry/test_application_service_telemetry.py
  tests/unit/telemetry/test_application_rag_telemetry.py

  Update existing tests that import ApplicationTelemetry:

  - ServiceRunner tests should use ApplicationServiceTelemetry.
  - RAG tests should use ApplicationRagTelemetry.
  - Assertions for ServiceRunner events should no longer expect operation.
  - Assertions for RAG events should expect:
      - event_type == application.rag.operation.*
      - attributes["component_name"]
      - attributes["operation"]

  Update domain metrics tests so:
  - RAG operation events produce RAG metrics.
  - RAG tests no longer assert against application.service.calls.total.

  After all imports are migrated:

  - Remove ApplicationTelemetry if unused.
  - Remove _resolve_operation.
  - Remove _request_operation.

  ### Step 8 — Verification

  Run targeted tests first:

  uv run pytest -q \
    tests/unit/telemetry/test_application_service_telemetry.py \
    tests/unit/telemetry/test_application_rag_telemetry.py \
    tests/unit/application/services/base/test_service_runner.py \
    tests/unit/application/rag/test_curated_rag_document_builder.py \
    tests/unit/application/rag/test_rag_service.py \
    tests/unit/application/rag/test_rag_retriever.py \
    tests/unit/application/rag/test_embedding_job_processor.py

  Then run broader telemetry coverage tests:

  uv run pytest -q tests/integration/telemetry/test_telemetry_coverage_audit.py

  Then run static checks:

  uv run ruff check .
  uv run mypy .

  ## Acceptance Criteria

  - ServiceRunner no longer emits or derives operation.
  - ApplicationServiceTelemetry has no operation parameter.
  - ApplicationRagTelemetry owns RAG operation/stage telemetry.
  - RAG pipeline telemetry no longer uses application.service.* event types.
  - RAG metrics no longer pollute application.service.* counters.
  - _resolve_operation and _request_operation are removed.
  - Tests clearly distinguish service telemetry from RAG telemetry.
  - No compatibility shim remains unless explicitly approved later.

  ## Assumptions

  - ApplicationTelemetry is internal platform code, so we can migrate imports directly instead of preserving a compatibility alias.
  - RAG components should remain application-layer orchestration components, but they should not pretend to be ServiceRunner services.
  - The existing RAG operation names are useful and should be preserved under the new RAG telemetry emitter.
  - We should not refactor RAG into ServiceRequest / ServiceResult as part of this fix.
## Step Results

### Implementation Complete — Application Telemetry Refactor

- Created `ApplicationServiceTelemetry` for `ServiceRunner`-managed application service lifecycle events.
- Created `ApplicationRagTelemetry` for RAG component operation/stage events.
- Removed the overloaded `ApplicationTelemetry` emitter and its operation-resolution behavior.
- Refactored `ServiceRunner` to stop deriving or emitting `operation` from `ServiceRequest.metadata`.
- Refactored RAG components to emit `application.rag.operation.*` events with explicit `component_name` and `operation`.
- Updated domain metrics mapping so service metrics and RAG operation metrics are separate.
- Updated unit and integration tests to distinguish service telemetry from RAG telemetry.
- Verified there are no remaining references to `ApplicationTelemetry`, `application_telemetry`, `_resolve_operation`, or `_request_operation` in `application/`, `core/`, `interfaces/`, `integration/`, or `tests/`.

### Verification

- Targeted telemetry/service/RAG tests: `46 passed in 1.96s`.
- Telemetry coverage audit: `2 passed in 0.93s`.
- Ruff check and formatting: passed after safe fixes/formatting.
- Modified-file mypy check: passed with no issues across the touched telemetry, service, RAG, and test files.
- Whole-project mypy was also run and failed on pre-existing unrelated runtime/CLI test errors outside this refactor.
- Graphify was updated after code changes.
