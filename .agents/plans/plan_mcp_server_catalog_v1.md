  # Polaris MCP Server V1 Catalog Implementation Plan

  ## Summary

  Implement a thin, read-only MCP transport boundary over existing Polaris application services. The server will expose exactly six tools:

  1. polaris_rag_ask
  2. polaris_rag_status
  3. polaris_workflows_list
  4. polaris_workflow_describe
  5. polaris_completed_runs_list
  6. polaris_completed_run_get

  Support both:

  - stdio for trusted local agent hosts.
  - Stateless Streamable HTTP with JSON responses and static bearer-token authentication for remote agent hosts.

  The implementation will use the official Python MCP SDK. Because the repository currently resolves MCP SDK 1.27.2 transitively while SDK v2 is not yet stable, declare mcp>=1.27,<2 as a direct dependency to prevent an
  unplanned major-version upgrade. Streamable HTTP is the official recommendation for production deployments.

  The server must not implement its own RAG pipeline, workflow runtime, persistence repository, SQL, Cypher, vector search, provider calls, or business logic.

  ———

  ## Public Interfaces and Contracts

  ### Server entrypoint

  Add:

  polaris-mcp --transport stdio
  polaris-mcp --transport streamable-http

  Defaults:

  transport: stdio
  host: 127.0.0.1
  port: 8000
  path: /mcp
  stateless HTTP: true
  JSON responses: true

  Streamable HTTP startup must fail securely if POLARIS_MCP_BEARER_TOKEN is missing.

  ### Configuration

  Introduce typed McpServerSettings with:

  POLARIS_MCP_TRANSPORT
  POLARIS_MCP_HOST
  POLARIS_MCP_PORT
  POLARIS_MCP_PATH
  POLARIS_MCP_BEARER_TOKEN
  POLARIS_MCP_ALLOW_WEB
  POLARIS_MCP_MAX_QUERY_CHARACTERS
  POLARIS_MCP_MAX_TOP_K
  POLARIS_MCP_MAX_PAGE_SIZE

  Defaults:

  ALLOW_WEB=false
  MAX_QUERY_CHARACTERS=8000
  MAX_TOP_K=50
  MAX_PAGE_SIZE=100

  Secrets must use secret-aware settings fields, must not appear in representations, and must never be logged or returned.

  ### Tool contracts

  #### polaris_rag_ask

  Delegates exclusively to:

  RagService.run(RagRequest)

  Inputs:

  query: required non-empty string
  symbols: optional list
  source_types: optional list
  source_tables: optional list
  agent_names: optional list
  agent_types: optional list
  report_types: optional list
  regimes: optional list
  workflow_name: optional
  execution_id: optional
  runtime_id: optional
  as_of_start: optional ISO-8601 datetime
  as_of_end: optional ISO-8601 datetime
  top_k: default 8, range 1..configured maximum
  allow_web: default false
  include_contexts: default false

  Rules:

  - Hardcode the canonical initial route to hybrid; do not let MCP consumers bypass adaptive routing.
  - Reject allow_web=true unless POLARIS_MCP_ALLOW_WEB=true.
  - Set requester="polaris_mcp".
  - Use the MCP invocation correlation ID as the RAG request ID.
  - Return the complete answer, citations, quality scores, security indicators, corrective actions, status, and error.
  - Return full retrieved contexts only when include_contexts=true.
  - Never silently truncate requested answer or context text.

  #### polaris_rag_status

  Delegates exclusively to:

  RagStatusOperationsService.status(RagStatusOperationRequest)

  Input:

  include_details: default true

  Return typed readiness for:

  PostgreSQL canonical records
  Qdrant vector projection
  Neo4j graph projection
  embedding model
  reranker
  overall status

  Sanitize all error details before serialization.

  #### polaris_workflows_list

  Delegates exclusively to:

  WorkflowFacade.list_workflow_summaries()

  Inputs:

  tag: optional
  offset: default 0
  limit: default 50, maximum configured page size

  Return:

  workflow name
  description
  tags
  sanitized metadata
  total count
  offset
  limit
  has_more
  next_offset

  #### polaris_workflow_describe

  Delegates exclusively to:

  WorkflowFacade.describe_workflow()

  Input:

  workflow_name: required

  Return the registered workflow metadata and complete graph definition after boundary sanitization.

  An unregistered workflow should produce a structured not-found result rather than expose a raw KeyError.

  #### polaris_completed_runs_list

  Delegates exclusively to:

  WorkflowFacade.list_completed_runs()

  Inputs:

  workflow_name: required
  offset: default 0
  limit: default 20, maximum configured page size

  Return:

  workflow_name
  execution_ids
  total count
  offset
  limit
  has_more
  next_offset

  Preserve the canonical archive ordering before applying boundary pagination.

  #### polaris_completed_run_get

  Delegates exclusively to:

  WorkflowFacade.load_completed_run()

  Inputs:

  workflow_name: required
  execution_id: required
  include: optional set of sections
  node_names: optional node-output selector

  Supported explicit sections:

  workflow_inputs
  node_outputs
  errors
  artifact_refs
  trace_context

  Default response contains only:

  found
  workflow_id
  execution_id
  runtime_id
  mode
  created_at
  simulation_time
  context_version
  node_output_count
  error_count
  artifact_count

  Rules:

  - node_names is valid only when node_outputs is included.
  - Requested unknown node names produce a validation error rather than silent omission.
  - Included sections are returned completely without hidden truncation.
  - Artifact references may be returned, but artifact file contents are out of scope.
  - Apply the canonical sensitive-data sanitizer to every selected section.
  - Missing runs return found=false; persistence failures remain tool errors.

  ———

  ## Implementation Steps

  ### Step 1 — Establish the MCP dependency boundary

  - Add direct dependency mcp>=1.27,<2 using uv add.
  - Add the polaris-mcp project script.
  - Confirm the dependency lock does not upgrade to an incompatible major version.
  - Verify import of FastMCP and structured-output support.

  ### Step 2 — Create the canonical built-in workflow catalog

  - Move the built-in workflow list out of the CLI-specific package into a shared module under workflows/.
  - Update the CLI bootstrap to use the shared catalog.
  - Delete the obsolete CLI-only catalog module after all imports are migrated.
  - Add a focused test proving the CLI still registers morning_report.

  ### Step 3 — Add typed MCP settings

  - Implement McpServerSettings.
  - Validate transport, host, port, path, limits, and HTTP token requirements.
  - Store the bearer token as a non-renderable secret value.
  - Test defaults, environment overrides, invalid limits, and missing HTTP credentials.

  ### Step 4 — Define MCP boundary request and response models

  - Add explicit Pydantic models for all six tools.
  - Use typed datetime, pagination, section-selection, citation, readiness, and error structures.
  - Restrict internal dictionaries to the final MCP serialization boundary.
  - Generate and snapshot each tool’s input JSON schema.

  ### Step 5 — Build the server-owned Dishka application lifespan

  - Construct one long-lived application container using get_async_di_container().
  - Bind one WorkflowInfrastructureProvider to that container.
  - Resolve WorkflowBootstrapResult once during startup.
  - Register canonical built-in workflows once through WorkflowFacade.
  - Close the container and flush/shut down telemetry during server shutdown.

  ### Step 6 — Add a per-invocation request-scope helper

  - Open a Dishka request scope for every tool invocation.
  - Resolve RagService, RagStatusOperationsService, or WorkflowFacade from that scope.
  - Never cache request-scoped application services.
  - Ensure request scopes close on success, validation failure, cancellation, and exceptions.

  ### Step 7 — Implement the MCP authentication boundary

  - Protect Streamable HTTP /mcp requests with bearer-token middleware.
  - Compare tokens using secrets.compare_digest.
  - Return 401 for missing or invalid credentials without revealing why validation failed.
  - Keep stdio trusted by the parent process and do not require a bearer token.
  - Leave /healthz unauthenticated but return only process readiness and no dependency details.

  ### Step 8 — Implement MCP boundary telemetry

  Add a boundary-specific McpTelemetry adapter that records exactly one lifecycle per tool call:

  mcp.tool.started
  mcp.tool.completed
  mcp.tool.failed

  Record:

  tool name
  transport
  request/correlation ID
  duration
  success
  failure category
  result status
  top_k or page size where relevant

  Do not record:

  bearer tokens
  raw authorization headers
  full queries
  RAG answers
  node-output contents
  workflow inputs
  database URLs

  Create a canonical trace context per stdio invocation and accept a valid incoming HTTP trace context when available. Correlate polaris_rag_ask with downstream RAG telemetry through its request ID.

  ### Step 9 — Implement polaris_rag_ask

  - Translate the MCP request into RagRetrievalFilters and RagRequest.
  - Enforce query, date-range, top_k, and web-access policies at the boundary.
  - Call RagService.run().
  - Serialize the canonical RagResult.
  - Add unit tests for filters, web denial, failed RAG results, citations, security flags, and optional full contexts.

  ### Step 10 — Implement polaris_rag_status

  - Resolve RagStatusOperationsService.
  - Call the typed status operation.
  - Serialize every readiness component.
  - Preserve degraded status as a successful tool response rather than a transport exception.
  - Add ready, degraded, sanitized-error, and dependency-exception tests.

  ### Step 11 — Implement polaris_workflows_list

  - Resolve WorkflowFacade.
  - Call list_workflow_summaries().
  - Apply deterministic boundary pagination.
  - Sanitize metadata.
  - Test tag filtering, empty results, pagination, and built-in workflow registration.

  ### Step 12 — Implement polaris_workflow_describe

  - Resolve WorkflowFacade.
  - Call describe_workflow().
  - Return the complete registered graph definition.
  - Convert missing workflow errors to a typed not-found response.
  - Test known, unknown, and metadata-sanitization cases.

  ### Step 13 — Implement polaris_completed_runs_list

  - Resolve WorkflowFacade.
  - Call list_completed_runs().
  - Apply pagination without changing canonical ordering.
  - Test empty archives, multiple pages, invalid limits, and persistence exceptions.

  ### Step 14 — Implement polaris_completed_run_get

  - Resolve WorkflowFacade.
  - Load the canonical RuntimeContext.
  - Build the default summary and add only explicitly requested sections.
  - Support exact node-name selection without truncating selected outputs.
  - Sanitize every returned section.
  - Test not-found runs, full selected sections, unknown node names, artifacts, errors, trace context, and secret redaction.

  ### Step 15 — Register the exact V1 tool allowlist

  Register only the six approved tools and apply MCP annotations:

  - Read-only and non-destructive for all six tools.
  - Idempotent for catalog, status, and completed-run reads.
  - Non-idempotent hint for RAG ask because model output and persisted query logs may vary.
  - Open-world hint only for RAG ask because explicitly authorized web fallback can contact external sources.

  Add a contract test that fails if an unapproved tool appears.

  Explicitly prohibit:

  workflow run/pause/resume/cancel
  RAG ingestion
  embedding processing
  graph processing
  projection rebuild
  completed-run deletion/cleanup
  direct SQL
  direct Cypher
  direct Qdrant operations
  provider or vendor SDK access
  Firecrawl as a standalone tool
  shell or filesystem access
  plugin management

  ### Step 16 — Implement the stdio transport

  - Run the same FastMCP server over stdio.
  - Keep protocol output isolated from normal logs; logs must go to stderr or configured telemetry sinks.
  - Add an MCP client-session test that initializes, lists tools, and invokes representative fake-backed tools.

  ### Step 17 — Implement Streamable HTTP

  - Create a stateless JSON Streamable HTTP ASGI application.
  - Mount it at the configured MCP path.
  - Add bearer authentication and /healthz.
  - Add startup and shutdown lifespan management for the MCP session manager and Polaris DI container.
  - Test initialization, tool listing, authorized calls, unauthorized calls, invalid tokens, and shutdown cleanup.

  ### Step 18 — Add transport and catalog documentation

  Document:

  architecture and thin-boundary rule
  six-tool catalog
  stdio startup and agent-host configuration
  Streamable HTTP startup
  required environment variables
  authentication behavior
  web-access policy
  tool schemas and examples
  service prerequisites
  deferred admin/action tools

  Include no real tokens, passwords, URLs containing credentials, or service secrets.

  ### Step 19 — Run isolated integration tests

  Use fake or in-memory canonical service implementations to verify:

  - Both transports expose identical tool schemas.
  - Tool handlers open and close request scopes.
  - Cancellation releases scopes.
  - Errors become safe MCP errors.
  - Tool results contain valid structured content.
  - The exact six-tool allowlist is enforced.
  - No handler imports a PostgreSQL repository, Qdrant client, Neo4j driver, Firecrawl client, provider SDK, or workflow runtime engine.

  ### Step 20 — Run notified live-service smoke tests

  Notify the user before starting these tests.

  Required for completed-run tools:

  PostgreSQL

  Required for full RAG ask/status:

  PostgreSQL
  Qdrant
  Neo4j
  Ollama and configured RAG models
  BGE reranker

  Firecrawl is required only for a separate smoke test with both:

  POLARIS_MCP_ALLOW_WEB=true
  allow_web=true

  Run one live stdio and one live Streamable HTTP client session, then verify:

  - tool discovery
  - workflow discovery
  - completed-run retrieval
  - authentication rejection
  - telemetry correlation
  - secret redaction

  ### Step 21 — Final regression and architecture gate

  Run in project order:

  ruff check --fix
  ruff format
  mypy . --explicit-package-bases
  pytest
  graphify update .

  Then verify:

  - No direct datastore or provider imports under mcp_server/.
  - No duplicate workflow registration catalog.
  - No second RAG or workflow execution path.
  - No admin or destructive MCP tools.
  - No secrets in source, tests, logs, snapshots, or documentation.
  - Every non-health tool resolves canonical services through a Dishka request scope.
  - Repowise risk and health checks show no unplanned changes to churn-heavy core files.

  ———

  ## Acceptance Criteria

  The V1 catalog is complete when:

  - Both stdio and authenticated Streamable HTTP transports work.
  - The server advertises exactly the six approved tools.
  - Every tool delegates to a canonical Polaris service or WorkflowFacade.
  - Tool requests and results have discoverable structured schemas.
  - Large answers and explicitly selected node outputs are never silently truncated.
  - Streamable HTTP rejects missing and invalid bearer tokens.
  - Sensitive values are redacted from results, telemetry, errors, and logs.
  - Telemetry records one correlated lifecycle per tool invocation.
  - Unit, integration, type, lint, format, and architecture checks pass.
  - No external service is contacted during ordinary unit tests.
  - Live-service tests are run only after notifying the user of their prerequisites.

  ## Assumptions and Deferred Work

  - V1 serves one remote agent-host identity represented by one static bearer token; multi-user OAuth and per-user authorization are deferred.
  - CORS is disabled by default. Browser access should be added only with an explicit origin allowlist.
  - Workflow execution and workflow control tools are deferred to a separately approved action-tool phase.
  - Administrative RAG and completed-run mutation tools are excluded.
  - Artifact metadata or references may be returned, but artifact file download is excluded.
  - Resources, prompts, sampling, elicitation, and custom MCP clients are excluded from V1.
  - No compatibility wrappers or parallel MCP-owned service implementations will be introduced.

## Step Results

### Step 1 — Establish the MCP dependency boundary

- Added the official Python MCP SDK as a direct project dependency constrained to `mcp>=1.27,<2`.
- Added the `polaris-mcp` project script and a minimal canonical FastMCP server entrypoint using stdio as the initial default transport.
- Confirmed the resolved lock remains on MCP SDK `1.27.2`; no incompatible major-version upgrade occurred.
- Confirmed `FastMCP`, `CallToolResult`, and the SDK's `structured_output` tool-registration option are available.
- Verification completed without contacting any live Polaris infrastructure service.

### Step 2 — Create the canonical built-in workflow catalog

- Moved `get_builtin_workflows()` from the CLI-specific bootstrap package to the shared `workflows.catalog` module without changing its catalog behavior.
- Updated CLI bootstrap registration to consume the shared catalog and identify `workflows.catalog` as the registration source.
- Removed the obsolete `interfaces/cli/bootstrap/workflows.py` module after migrating all references.
- Added focused coverage confirming the shared built-in catalog contains `morning_report`; existing CLI bootstrap coverage continues to verify that the workflow is registered through `WorkflowFacade`.
- No runtime, facade, workflow-definition, or external-service contract was changed.
- Verification: focused Ruff and MyPy checks passed; all four CLI provider-profile/catalog tests passed without contacting a live service.

### Step 3 — Add typed MCP settings

- Added the isolated `McpServerSettings` boundary contract and `McpTransport` enum under `mcp_server/settings.py`; the churn-heavy global settings module was intentionally left unchanged.
- Added explicit defaults for local stdio, loopback host, port, MCP path, web-access policy, query length, retrieval depth, and pagination size.
- Added environment parsing for every approved `POLARIS_MCP_*` setting with validation for supported transports, nonblank hosts, valid TCP ports, absolute MCP paths, booleans, integers, and positive request limits.
- Enforced fail-closed Streamable HTTP configuration: `POLARIS_MCP_BEARER_TOKEN` is required whenever the selected transport is `streamable-http`.
- Stored the bearer token as `pydantic.SecretStr` in a dataclass field excluded from representations; focused tests confirm the raw token is absent from both `repr()` and `str()` output.
- Added 12 focused unit tests covering defaults, all environment overrides, invalid endpoint values, invalid limits, missing HTTP credentials, and secret redaction.
- Verification: focused Ruff check/format and MyPy passed; all 12 MCP settings tests passed without contacting an external service.

### Step 4 — Define MCP boundary request and response models

- Added strict, immutable Pydantic boundary contracts for the exact six approved MCP tools in `mcp_server/models.py`.
- Added typed ISO-8601 datetime ranges, pagination fields, completed-run section selection, citations, retrieved contexts, RAG quality scores, readiness components, workflow graph descriptions, trace context, and sanitized structured errors.
- Kept the consumer-controlled RAG surface constrained: adaptive routing remains hidden, unknown fields are rejected, and invalid date windows or completed-run node selectors fail validation before reaching application services.
- Limited open-ended dictionaries to transport-facing serialized metadata, runtime-output, artifact, event, and error payloads where the canonical source is already a serialized boundary.
- Added explicit input/output model registries for only `polaris_rag_ask`, `polaris_rag_status`, `polaris_workflows_list`, `polaris_workflow_describe`, `polaris_completed_runs_list`, and `polaris_completed_run_get`.
- Added a stable JSON-schema snapshot for every tool input plus focused tests for catalog exactness, schema drift, datetime parsing, time-window validation, section/node selection, structured not-found responses, and rejection of unapproved fields.
- Verification: focused Ruff check/fix and format passed; focused MyPy passed with explicit package bases; all 7 MCP model tests passed without contacting an external service.

### Step 5 — Build the server-owned Dishka application lifespan

- Added `McpApplicationContext` and `mcp_application_lifespan()` as the MCP server's application-scope ownership boundary.
- The lifespan constructs exactly one canonical async Dishka container through `get_async_di_container()` and passes exactly one `WorkflowInfrastructureProvider` instance into that composition.
- Bound the completed application container to the workflow provider before lazily resolving `WorkflowBootstrapResult`, preserving the canonical runtime/facade composition path.
- Resolved the workflow runtime once during server startup and registered every workflow from `workflows.catalog` exactly once through `WorkflowFacade.register_workflow_async()` with canonical built-in metadata.
- Attached the lifespan directly to the shared `FastMCP` server instance so stdio and future Streamable HTTP transports will use the same application resources.
- Made application composition and workflow catalog imports startup-lazy so importing the MCP server or running isolated unit tests does not eagerly parse database settings or initialize infrastructure.
- Server shutdown closes the application container in a `finally` block, including startup failures. Closing the APP scope finalizes `WorkflowInfrastructureProvider`, which force-flushes and shuts down runtime telemetry without a duplicate MCP-owned shutdown path.
- Added focused tests for single container/provider/runtime ownership, registration ordering and metadata, server lifespan wiring, telemetry-finalizing container closure, and cleanup after startup failure.
- Verification: focused Ruff check/fix and format passed; focused MyPy passed with explicit package bases; all 22 MCP unit tests passed without contacting an external service.

### Step 6 — Add a per-invocation request-scope helper

- Added `mcp_dependency_scope()` as the single typed MCP helper for opening one Dishka request scope and resolving one canonical dependency per tool invocation.
- The helper reuses the server-owned application container from `McpApplicationContext`; it does not construct a second application container or bypass canonical composition.
- Dependency resolution remains generic and typed, allowing tool handlers to resolve `RagService`, `RagStatusOperationsService`, or `WorkflowFacade` directly from the invocation scope without MCP-owned service adapters.
- The helper holds no resolved-service cache. Each invocation opens a fresh request scope, while normal request-local lifetime ownership remains Dishka's responsibility.
- Added focused tests proving fresh-scope resolution for all three canonical dependency types and deterministic scope closure after success, input-validation failure, tool exceptions, and task cancellation.
- Verification: focused Ruff check/fix and format passed; focused MyPy passed with explicit package bases; all 26 MCP unit tests passed without contacting an external service.

### Step 7 — Implement the MCP authentication boundary

- Added `McpHttpAuthenticationBoundary` as a transport-only ASGI boundary that protects the configured Streamable HTTP MCP path and all nested paths without changing the trusted stdio execution path.
- Added `protect_streamable_http_app()` to require validated `streamable-http` settings and apply the configured `SecretStr` bearer token to a future FastMCP HTTP application without introducing an MCP-owned identity system.
- Bearer credentials are parsed from the `Authorization` header and token values are compared with `secrets.compare_digest`; authentication failures never include the supplied token or distinguish missing, malformed, wrong-scheme, and invalid-token cases.
- Missing and invalid credentials return the same `401 {"error": "unauthorized"}` response with a generic `WWW-Authenticate: Bearer` header, and requests are not forwarded downstream.
- Added an unauthenticated `/healthz` interception that returns only `{"status": "ready"}` and does not resolve, query, or reveal the status of PostgreSQL, Qdrant, Neo4j, models, workflows, or application services.
- Confirmed the stdio entrypoint remains parent-process trusted and continues to start without reading or requiring bearer-token configuration.
- Added focused tests for constant-time comparison, valid forwarding, equivalent safe failures, nested MCP-path protection, process-only health readiness, stdio behavior, and rejection of non-HTTP settings.
- Verification: MCP-scoped Ruff check/fix and format passed; MCP-scoped MyPy passed with explicit package bases; all 35 MCP unit tests passed without contacting an external service.

### Step 8 — Implement MCP boundary telemetry

- Added `McpTelemetry` as a boundary-specific adapter over the canonical `ObservabilityManager`; the MCP layer does not create a second collector, metrics store, trace system, or persistence path.
- Added typed `McpToolInvocation` and `McpToolFailureCategory` contracts so each tool call carries one request/correlation ID, one canonical operation trace context, its transport, start time, and only the approved retrieval or pagination dimensions.
- Added the exact `mcp.tool.started`, `mcp.tool.completed`, and `mcp.tool.failed` lifecycle events. Terminal events include duration, success, result status, and a stable failure category; the existing observability manager records event counters, error counters, and duration histograms once from those events.
- Restricted telemetry fields to an explicit allowlist: tool name, transport, request ID, `top_k`, page size, result status, failure category, error type, and trace identifiers. The adapter accepts no arbitrary payload or attribute dictionary and does not record queries, answers, workflow inputs, node outputs, authorization values, database URLs, exception messages, or exception tracebacks.
- Added strict W3C `traceparent` handling for Streamable HTTP. A valid remote trace ID is retained, its span ID becomes the parent, and Polaris creates a new local operation span. Invalid headers fall back to a new canonical trace; stdio always creates a new local trace and ignores HTTP trace input.
- Made the MCP application lifespan construct one `McpTelemetry` adapter from the already-bootstrapped runtime `ObservabilityManager`. MCP startup now fails clearly if canonical workflow observability is disabled instead of silently creating an unobserved boundary.
- Preserved the MCP invocation request ID as the canonical correlation ID. `polaris_rag_ask` can pass that same request ID into `RagRequest` in Step 9, directly correlating MCP lifecycle events with existing downstream `ApplicationRagTelemetry` events without duplicating RAG telemetry.
- Added focused tests for successful and failed lifecycles, deterministic duration, exact correlation, generated request IDs, safe field capture, sensitive error-content exclusion, valid remote-parent propagation, invalid-header fallback, stdio trace isolation, and invalid telemetry dimensions.
- Verification: all 45 MCP unit tests passed; repository-wide Ruff check and format check passed; repository-wide MyPy passed across 1,108 source files; no external service was contacted.

### Step 9 — Implement `polaris_rag_ask`

- Added `polaris_rag_ask` to the shared FastMCP server as a read-only, non-destructive structured tool and kept the transport wrapper thin.
- Added `execute_rag_ask()` as the MCP boundary handler. Each invocation uses the server-owned `McpApplicationContext`, opens one Dishka request scope through `mcp_dependency_scope()`, resolves canonical `RagService`, and calls `RagService.run()` without introducing an MCP-owned retrieval or generation path.
- Translated every approved MCP filter into canonical `RagRetrievalFilters`, including source, symbol, workflow, execution, runtime, agent, report, regime, and date-range selectors. The MCP request ID is passed directly into `RagRequest.request_id` so MCP and downstream RAG telemetry share one correlation ID.
- Kept adaptive routing internal by fixing the canonical request route to `hybrid`; identified the requester and source as `polaris_mcp` without adding untyped domain data.
- Enforced configured query-length, `top_k`, and web-access limits before resolving `RagService`. ISO date ordering remains enforced by the strict `RagAskRequest` boundary model. Policy failures produce safe `ToolError` messages and validation-class telemetry.
- Serialized the complete canonical answer, citations, optional full retrieved contexts, confidence/grounding/utility scores, injection flag, reflection scores, corrective actions, route, status, and generation timestamp into the typed MCP response. Successful answer and context text are not truncated or summarized.
- Sanitized canonical failed results at the external boundary so internal exception messages, connection strings, and credentials cannot be exposed through either `answer_text` or `error`. Failed domain results remain successful MCP protocol responses with `status="failed"`; boundary/application exceptions become sanitized tool errors.
- Added cancellation-aware terminal telemetry and safe exception logging that records only the request ID and exception type, not raw exception contents.
- Moved typed MCP settings into the server lifespan context so every tool uses one validated startup configuration rather than rereading environment variables per invocation.
- Added focused tests for complete filter translation, request/telemetry correlation, query and retrieval-depth limits, denied web access, failed-result sanitization, citations, security flags, reflection scores, corrective actions, optional full contexts, and deterministic request-scope closure.
- Verification: all 52 MCP unit tests passed; repository-wide Ruff check/fix and formatting passed; repository-wide MyPy passed across 1,110 source files; Graphify was updated; no external service was contacted.

### Step 10 — Implement `polaris_rag_status`

- Added `polaris_rag_status` to the shared FastMCP server as a read-only, non-destructive, idempotent structured tool. The transport wrapper delegates directly to the focused MCP boundary handler and does not contain readiness logic.
- Added `execute_rag_status()` as a thin boundary over canonical `RagStatusOperationsService`. Every invocation opens one Dishka request scope through `mcp_dependency_scope()`, resolves the canonical service, and calls `status(RagStatusOperationRequest(...))` without introducing direct PostgreSQL, Qdrant, Neo4j, embedding, or reranker access under `mcp_server/`.
- Serialized every canonical readiness component into the existing strict MCP response models: PostgreSQL canonical-record counts and job states, Qdrant collection/vector compatibility, Neo4j connectivity/entity count, embedding model readiness/dimensions, and reranker readiness.
- Preserved `include_details` as a typed presentation control. The canonical service still performs the readiness operation, while the MCP response omits dependency component payloads when details are not requested.
- Preserved degraded readiness as a normal successful MCP tool response with `status="degraded"` and `ready=false`; degraded dependencies therefore do not become transport exceptions. MCP lifecycle telemetry records the canonical degraded status as a completed invocation.
- Sanitized all dependency-provided error strings at the external boundary. PostgreSQL URLs, credentials, provider endpoints, API keys, and raw exception messages are replaced with stable component-specific messages while non-sensitive readiness facts remain available.
- Added cancellation-aware failure telemetry and safe exception logging that records only request ID and exception type. Unexpected service or scope failures become the generic `ToolError("Polaris RAG status request failed.")`, and request scopes close deterministically.
- Added focused tests for complete ready serialization, optional detail omission, degraded readiness, redaction of all dependency errors, dependency exceptions, task cancellation, telemetry correlation, scope closure, and FastMCP registration annotations/output schema.
- Verification: all 58 MCP unit tests passed; repository-wide Ruff check/fix and formatting passed; repository-wide MyPy passed across 1,112 source files; Repowise found no churn or co-change warning for the surgical MCP-only change; no external service was contacted.

### Step 11 — Implement `polaris_workflows_list`

- Added `polaris_workflows_list` to the shared FastMCP server as a read-only, non-destructive, idempotent structured tool. The server wrapper delegates directly to the focused MCP boundary handler.
- Added `execute_workflows_list()` as a thin boundary over canonical `WorkflowFacade.list_workflow_summaries()`. Every invocation opens one Dishka request scope through `mcp_dependency_scope()` and resolves `WorkflowFacade`; no registry, workflow service, runtime engine, or persistence component is accessed directly by the MCP layer.
- Delegated tag filtering and canonical workflow ordering to `WorkflowFacade`. The MCP boundary applies deterministic offset/limit pagination only after receiving the facade's ordered typed summaries and reports `total_count`, `has_more`, and `next_offset` without introducing a second workflow catalog.
- Enforced `McpServerSettings.max_page_size` before resolving the facade. Empty results, final pages, and offsets beyond the available summaries return stable empty/final-page responses rather than errors.
- Serialized the complete workflow name, description, tags, and transport-safe metadata into the strict MCP response model. Metadata is copied and sanitized through the canonical sensitive-data sanitizer so credential-shaped keys, bearer values, and URL credentials are redacted without mutating the canonical workflow summary.
- Preserved the built-in `morning_report` catalog contract and verified that a facade-provided built-in summary tagged `builtin` is discoverable with its `workflows.catalog` source metadata. Existing lifespan coverage continues to verify that built-ins are registered through `WorkflowFacade` at MCP startup.
- Added cancellation-aware telemetry and safe boundary failures. Validation failures are recorded before dependency resolution; application failures expose only the generic workflow-discovery tool error and scopes close deterministically.
- Added focused tests for tag forwarding and built-in discovery, empty results, first/final/past-end pagination, metadata redaction and source immutability, page-size policy, sanitized application failures, cancellation, scope closure, telemetry correlation, and FastMCP registration annotations/output schema.
- Verification: all 68 MCP unit tests passed; repository-wide Ruff check/fix and formatting passed; repository-wide MyPy passed across 1,114 source files; Repowise found no health biomarker findings or co-change warning for the surgical MCP-only change. No external service was contacted.

### Step 12 — Implement `polaris_workflow_describe`

- Added `polaris_workflow_describe` to the shared FastMCP server as a read-only, non-destructive, idempotent structured tool. The server wrapper delegates directly to the focused MCP boundary handler.
- Added `execute_workflow_describe()` as a thin boundary over canonical `WorkflowFacade.describe_workflow()`. Every invocation opens one Dishka request scope through `mcp_dependency_scope()` and resolves `WorkflowFacade`; the MCP layer does not query the workflow registry, workflow service, runtime engine, compiler, datastore, or provider layer directly.
- Returned the complete registered workflow graph definition through the existing strict MCP response models, including workflow name, description, tags, workflow metadata, graph description, node names, node types, dependencies, enabled state, retry policy, retry backoff, fail-fast setting, timeout, tags, and node metadata.
- Converted missing workflow `KeyError` responses from the canonical facade into a typed non-exception MCP response with `found=false`, `error.code="workflow_not_found"`, `retryable=false`, and terminal telemetry status `not_found`.
- Sanitized workflow-level and node-level metadata through the canonical sensitive-data sanitizer. Credential-shaped keys, bearer values, and URL credentials are redacted without mutating the canonical description payload returned by the facade.
- Added cancellation-aware telemetry and safe application failures. Unexpected facade/scope/serialization failures expose only `ToolError("Polaris workflow description request failed.")`, log only request ID and exception type, and close request scopes deterministically.
- Added focused tests for known workflow graph serialization, unknown workflow typed not-found responses, workflow and node metadata redaction/source immutability, sanitized application failures, cancellation handling, telemetry correlation, scope closure, and FastMCP registration annotations/output schema.
- Verification: all 74 MCP unit tests passed; repository-wide Ruff check/fix and formatting passed; repository-wide MyPy passed across 1,116 source files; Repowise found no co-change warning for the surgical MCP-only change. No external service was contacted.

### Step 13 — Implement `polaris_completed_runs_list`

- Added `polaris_completed_runs_list` to the shared FastMCP server as a read-only, non-destructive, idempotent structured tool. The server wrapper delegates directly to the focused MCP boundary handler.
- Added `execute_completed_runs_list()` as a thin boundary over canonical `WorkflowFacade.list_completed_runs()`. Every invocation opens one Dishka request scope through `mcp_dependency_scope()` and resolves `WorkflowFacade`; the MCP layer does not access completed-run repositories, state managers, workflow services, runtime engines, PostgreSQL, or archive storage directly.
- Preserved canonical completed-run ordering returned by `WorkflowFacade` and applied deterministic offset/limit pagination only at the MCP boundary. The response reports `workflow_name`, `execution_ids`, `total_count`, `offset`, `limit`, `has_more`, and `next_offset` without sorting or reinterpreting execution IDs.
- Enforced `McpServerSettings.max_page_size` before dependency resolution. Empty archives, final pages, and offsets beyond available execution IDs return stable empty/final-page responses rather than errors.
- Added cancellation-aware telemetry and safe boundary failures. Validation failures are recorded before dependency resolution; persistence or facade exceptions expose only `ToolError("Polaris completed-run discovery request failed.")`, log only request ID and exception type, and close request scopes deterministically.
- Added focused tests for canonical-order preservation, empty archives, first/final/past-end pagination, page-size policy, sanitized persistence/application failures, cancellation, telemetry correlation, scope closure, and FastMCP registration annotations/output schema.
- Verification: all 83 MCP unit tests passed; repository-wide Ruff check and format check passed; repository-wide MyPy passed across 1,118 source files; direct MCP import audit found no direct database, Qdrant, Neo4j, Firecrawl, runtime-engine, workflow-service, state-manager, or completed-run-repository access under `mcp_server/`. No external service was contacted.

### Step 14 — Implement `polaris_completed_run_get`

- Added `polaris_completed_run_get` to the shared FastMCP server as a read-only, non-destructive, idempotent structured tool. The server wrapper delegates directly to the focused MCP boundary handler.
- Added `execute_completed_run_get()` as a thin boundary over canonical `WorkflowFacade.load_completed_run()`. Every invocation opens one Dishka request scope through `mcp_dependency_scope()` and resolves `WorkflowFacade`; the MCP layer does not access completed-run repositories, state managers, workflow services, runtime engines, PostgreSQL, archive storage, or runtime internals directly.
- Returned a default completed-run summary from the canonical `RuntimeContext`: workflow ID, execution ID, runtime ID, mode, timestamps, context version, node-output count, error count, and artifact count.
- Added only explicitly requested sections: workflow inputs, selected node outputs, errors, artifact references, and trace context. Node-name filtering is exact and does not truncate selected node outputs or long LLM-style response fields.
- Sanitized every returned selected section with the canonical sensitive-data sanitizer and JSON-safe boundary conversion, including workflow inputs, node output payloads, emitted events, node errors, execution metadata, artifact references, top-level errors, and trace attributes.
- Converted missing runs into typed non-exception MCP responses with `found=false`, `error.code="completed_run_not_found"`, `retryable=false`, and terminal telemetry status `not_found`.
- Added cancellation-aware telemetry and safe application failures. Unexpected facade/scope/serialization failures expose only `ToolError("Polaris completed-run retrieval request failed.")`, log only request ID and exception type, and close request scopes deterministically.
- Added focused tests for default summaries, not-found runs, all selected sections, exact node-name selection with unknown nodes, artifacts, errors, trace context, secret redaction, sanitized persistence/application failures, cancellation, scope closure, telemetry correlation, and FastMCP registration annotations/output schema.
- Verification: all 90 MCP unit tests passed; repository-wide Ruff check and format check passed across 925 files; repository-wide MyPy passed across 1,120 source files; direct MCP import audit found no direct database, Qdrant, Neo4j, Firecrawl, runtime-engine, workflow-service, state-manager, or completed-run-repository access under `mcp_server/`; `git diff --check` passed. No external service was contacted.
- Postflight: Repowise reported the new focused tool and test as no-git-metadata files, `mcp_server/server.py` remains high-health at 9.65/10, and the only noted biomarker was existing declarative FastMCP registration boilerplate duplication. No additional core or datastore changes were made.

### Step 15 — Register the exact V1 tool allowlist

- Added `mcp_server/tool_allowlist.py` as the canonical V1 MCP catalog guard with the exact six approved tool names: `polaris_rag_ask`, `polaris_rag_status`, `polaris_workflows_list`, `polaris_workflow_describe`, `polaris_completed_runs_list`, and `polaris_completed_run_get`.
- Added explicit annotation requirements for every approved tool. All six tools must be read-only and non-destructive; catalog, status, and completed-run reads must be idempotent; `polaris_rag_ask` is intentionally marked non-idempotent and is the only open-world tool because authorized web fallback can contact external sources.
- Added explicit prohibited-tool name and prefix guards for workflow actions, RAG ingestion/admin operations, projection rebuilds, completed-run mutation, direct SQL/Cypher/Qdrant/Neo4j access, provider/vendor access, Firecrawl as a standalone tool, shell/filesystem access, and plugin management.
- Wired `validate_registered_tool_allowlist()` into `mcp_server/server.py` after FastMCP tool registration so import/startup fails closed if the registered server catalog drifts from the approved V1 allowlist or annotation contract.
- Added focused contract tests that verify the server advertises exactly the approved six tools, all tool annotations match the V1 contract, the server output models match the strict boundary-model catalog, no prohibited operations are registered or modeled, and the validator rejects both unapproved tools and annotation drift.
- Verification: all 96 MCP unit tests passed; repository-wide Ruff check and format check passed across 927 files; repository-wide MyPy passed across 1,122 source files; `git diff --check` passed; direct MCP import audit found no direct database, Qdrant, Neo4j, Firecrawl, runtime-engine, workflow-service, state-manager, or completed-run-repository imports under `mcp_server/`. No external service was contacted.
- Postflight: Repowise reported `mcp_server/server.py` remains high-health at 9.65/10. The new allowlist module and test are not yet represented in git history, so Repowise reports no historical metadata for them; focused unit coverage now exists for the allowlist contract.

### Step 16 — Implement the stdio transport

- Added an explicit trusted-local stdio runner boundary through `run_stdio_server()` and updated the `polaris-mcp` entrypoint to parse the approved `--transport` option.
- Kept Step 16 fail-closed to stdio only: `--transport stdio` runs the shared FastMCP server, while `streamable-http` is rejected until the dedicated HTTP transport phase.
- Preserved the single shared FastMCP server and exact V1 allowlist; no second server instance, transport-specific tool catalog, or parallel workflow/RAG implementation was introduced.
- Added stdio logging isolation so root logging handlers that would write to stdout are redirected to stderr before the MCP stdio server starts. This keeps stdout reserved for MCP protocol frames.
- Added a fake-backed MCP stdio client-session test that launches the actual Polaris MCP server module in a subprocess with a patched fake lifespan, initializes an MCP client session, lists the exact six approved tools, and invokes `polaris_workflows_list` through stdio without contacting any external service.
- Added focused tests for explicit `--transport stdio`, rejection of premature Streamable HTTP execution, and stdout/stderr log isolation.
- Verification: all 100 MCP unit tests passed; repository-wide Ruff check passed; repository-wide Ruff format check passed across 928 files; repository-wide MyPy passed across 1,123 source files; `git diff --check` passed; direct MCP import audit found no direct database, Qdrant, Neo4j, Firecrawl, runtime-engine, workflow-service, state-manager, or completed-run-repository imports under `mcp_server/`; Graphify was updated. No external service was contacted.
- Postflight: Repowise reported `mcp_server/server.py` remains high-health at 9.65/10. The only noted biomarker is existing declarative FastMCP registration boilerplate duplication shared with other MCP tool registration modules; this was not expanded into a broader refactor during the surgical stdio step. The new stdio test has no git-history metadata yet, as expected for a new file.

### Step 17 — Implement Streamable HTTP

- Added `create_streamable_http_app()` as the canonical ASGI construction boundary for authenticated Streamable HTTP. It configures the shared FastMCP server for the Polaris settings path, JSON responses, and stateless HTTP before wrapping the app with the existing bearer-token authentication boundary.
- Added `run_streamable_http_server()` and updated the `polaris-mcp` entrypoint so `--transport stdio` starts the trusted stdio runner and `--transport streamable-http` starts the authenticated HTTP server through Uvicorn.
- Kept Streamable HTTP fail-closed: `McpServerSettings` still requires `POLARIS_MCP_BEARER_TOKEN` for HTTP transport, `run_stdio_server()` rejects HTTP settings, and `create_streamable_http_app()` rejects stdio settings.
- Mounted the MCP HTTP endpoint at the configured MCP path through FastMCP's Streamable HTTP route and preserved `/healthz` as process-only readiness outside authentication and outside dependency resolution.
- Preserved the single shared FastMCP server, exact six-tool V1 allowlist, and server-owned lifespan. No second server instance, duplicate tool catalog, direct datastore/provider access, or parallel workflow/RAG implementation was introduced.
- Added fake-backed in-process HTTP client-session coverage using the official MCP Streamable HTTP client transport over `httpx.ASGITransport`. The test initializes a client session, lists the exact six approved tools, and invokes `polaris_workflows_list` without contacting external services.
- Added focused tests for missing bearer token rejection, invalid bearer token rejection, unauthenticated `/healthz`, configured stateless JSON/path behavior, stdio-settings rejection, CLI routing for `--transport streamable-http`, Uvicorn host/port configuration, and balanced startup/shutdown cleanup under stateless request lifecycles.
- Verification: all 107 MCP unit tests passed; repository-wide Ruff check passed; repository-wide Ruff format check passed across 929 files; repository-wide MyPy passed across 1,124 source files; `git diff --check` passed; direct MCP import audit found no direct database, Qdrant, Neo4j, Firecrawl, runtime-engine, workflow-service, state-manager, or completed-run-repository imports under `mcp_server/`; Graphify was updated. No external service was contacted.
- Postflight: Repowise reported `mcp_server/server.py` remains high-health at 9.65/10 and `mcp_server/auth.py` remains 10.0/10. The only noted biomarker is existing declarative FastMCP registration boilerplate duplication in `mcp_server/server.py`; this was not expanded into a broader refactor during the surgical HTTP transport step. The new HTTP transport test has no git-history metadata yet, as expected for a new file.

### Step 18 — Add transport and catalog documentation

- Added `docs/platform_mcp_server.md` as the maintained V1 MCP server operations and architecture document.
- Documented the thin-boundary architecture pattern and justification: MCP is a transport/serialization boundary over canonical Polaris services and `WorkflowFacade`, not a second workflow engine, RAG implementation, datastore gateway, provider gateway, or administration API.
- Documented both supported transports: trusted local stdio and authenticated stateless JSON Streamable HTTP, including startup commands, agent-host expectations, logging/protocol separation, configured MCP path behavior, and `/healthz` process-only readiness.
- Documented every `POLARIS_MCP_*` configuration option, including required HTTP bearer-token behavior, web-access controls, query/retrieval/page-size limits, and placeholder-only credential examples.
- Documented the exact six-tool V1 catalog, MCP annotation intent, tool input fields, response highlights, safe example requests, and the rule that successful answers, explicitly requested retrieved contexts, and selected completed-run node outputs are not silently summarized or truncated by the MCP layer.
- Documented service prerequisites for live use while clarifying that `/healthz` does not validate PostgreSQL, Qdrant, Neo4j, model, workflow, or application-service readiness.
- Documented security/sanitization expectations and the explicitly deferred/prohibited V1 tools, including workflow actions, RAG admin operations, direct datastore access, provider/vendor access, Firecrawl/search as standalone tools, shell/filesystem tools, and plugin management.
- Verification: documentation coverage script confirmed required Step 18 topics are present; secret audit found no literal service secrets, credentialed PostgreSQL URLs, known local test passwords, or literal bearer-token values in the MCP documentation/plan; repository-wide Ruff check passed; repository-wide Ruff format check passed across 929 files; repository-wide MyPy passed across 1,124 source files; `git diff --check` passed; Graphify update completed with no code-topology changes. No external service was contacted.

### Step 19 — Run isolated integration tests

- Added `tests/integration/mcp_server/test_transport_contracts.py` as the isolated fake-backed integration contract suite for the V1 MCP transport/catalog boundary.
- Verified trusted stdio and authenticated Streamable HTTP expose identical tool schemas, annotations, and output schema metadata for the exact six approved V1 tools.
- Verified every V1 tool handler opens exactly one canonical request scope, returns valid structured content, emits start/completed telemetry, and closes its scope after success.
- Verified cancellation preserves `asyncio.CancelledError`, emits sanitized cancelled telemetry, and still releases the request scope.
- Verified application failures become safe MCP `ToolError` responses without leaking credentialed URLs or secret values, while still closing the request scope and emitting sanitized failure telemetry.
- Verified the exact six-tool allowlist remains enforced through the canonical allowlist validator.
- Added an AST import audit covering `mcp_server/*_tool.py` and `mcp_server/server.py` to prevent direct handler/server imports of PostgreSQL repository modules, Qdrant, Neo4j, Firecrawl, provider/client SDKs, or the workflow runtime engine.
- Verification: isolated MCP integration contract suite passed with 11 tests; combined MCP unit plus isolated integration suite passed with 118 tests; repository-wide Ruff check passed; repository-wide Ruff format check passed across 930 files; repository-wide MyPy passed across 1,125 source files; `git diff --check` passed; Graphify update rebuilt the graph successfully. No external service was contacted.
- Postflight: Repowise reports no git metadata for the new integration test file yet, which is expected for a new file; no downstream blast radius or co-change risks were identified.

### Step 20 — Run notified live-service smoke tests

- Notified before running live-service tests and identified the required dependencies for this step: PostgreSQL for completed-run tools, plus PostgreSQL, Qdrant, Neo4j, Ollama, configured RAG models, and the BGE reranker for full RAG status/ask smoke coverage. Firecrawl/web smoke was intentionally not run because the step requires the explicit web gate to be enabled separately.
- Confirmed the Compose service catalog and started the required local services for the smoke run: PostgreSQL, Qdrant, Neo4j, and BGE reranker. Verified the required containers reached running/healthy state before invoking MCP tools.
- Confirmed Ollama readiness and verified the configured RAG models were available locally: the triage/router/synthesis models and `bge-m3:567m` embedding model were present.
- Applied Alembic migrations to the live PostgreSQL database before the smoke test, then verified `polaris rag status` reported a ready canonical/vector/graph/model projection state.
- Found no existing archived `morning_report` runs, so seeded one through the canonical Polaris CLI workflow path rather than writing directly to storage. The completed run archived successfully with execution ID `371b893f5b734a9cb42b76d42567ae75`.
- Ran one live MCP stdio client session against the actual Polaris MCP server boundary. The session initialized, discovered exactly the six approved V1 tools, listed registered workflows, described `morning_report`, checked RAG readiness, executed a no-web RAG ask, listed completed runs, and retrieved the completed morning-report context.
- Ran one live MCP Streamable HTTP client session against the authenticated ASGI app. The session verified missing and invalid bearer tokens return `401`, then authenticated successfully and exercised the same live tool path as stdio.
- Verified completed-run retrieval returned node evidence and trace context through the MCP boundary for both transports. This confirms completed-run access is delegated through the canonical workflow facade/archive path, not a direct MCP datastore implementation.
- Verified MCP lifecycle telemetry was emitted with correlated `mcp.tool.started` and `mcp.tool.completed` events during live tool calls. The smoke run also showed downstream RAG/provider telemetry during status and ask operations.
- Verified secret redaction at the live boundary by checking all returned MCP tool payloads for configured secret values and connection-string patterns. No MCP response payload leaked service credentials, bearer values, or database URLs.
- Result: live smoke passed for both stdio and Streamable HTTP. RAG ask returned the valid canonical `no_results` status because the live curated RAG store currently contains zero documents/chunks; readiness remained `ready`, and no web fallback was requested.

### Step 21 — Final regression and architecture gate

- Ran the required final verification workflow in order after the MCP V1 catalog implementation: `ruff check --fix`, `ruff format`, `mypy . --explicit-package-bases`, full `pytest`, and `graphify update .`.
- Fixed final-gate issues exposed by the repository-wide regression suite:
  - Renamed the new MCP request-scope test file to avoid a pytest module-name collision with an existing integration test.
  - Replaced literal credential-shaped database URLs in MCP tests with dynamically constructed test values so security-hygiene checks continue to validate redaction behavior without embedding secrets in tracked files.
  - Removed the remaining direct persistence-model import from the RAG MCP boundary; `mcp_server/` now avoids direct datastore/persistence/provider/client imports and stays a transport boundary over canonical services.
  - Scrubbed stale retired-brand references from generated/reporting artifacts touched during the step so the current Polaris branding gate passes.
- Verified final static checks: Ruff check/fix passed, Ruff format left 930 files unchanged, and MyPy passed with no issues across 1,125 source files.
- Verified final repository-wide tests: `pytest -q` passed with 1,824 passed, 17 skipped, and 6 warnings. The full run required the local environment configuration to be loaded, but no secret values were printed or written.
- Updated Graphify successfully. The graph rebuilt with 19,246 nodes, 85,352 edges, and 639 communities; HTML visualization was skipped because the graph exceeds the configured visualization node limit.
- Re-ran the security/branding tests after Graphify because the generated report can reintroduce historical text. The focused security gate passed with 5 tests.
- Ran MCP architecture gates:
  - no direct database, storage, provider, vendor-client, Qdrant, Neo4j, SQLAlchemy, or Firecrawl imports under `mcp_server/`;
  - exact six-tool V1 allowlist enforced;
  - every non-health tool module resolves canonical services through `mcp_dependency_scope()`;
  - the only workflow catalog definition remains `workflows/catalog.py`;
  - no admin/destructive MCP tools are registered.
- Repowise postflight: target MCP files remain high-health at 9.65/10 where indexed; no churn-heavy core files were changed. Repowise still flags expected medium DRY findings caused by similar thin-tool boundary boilerplate across MCP wrappers, but no core blast-radius or co-change warning requires additional Step 21 changes.
- Result: Step 21 final regression and architecture gate passed. MCP V1 remains a thin external transport over canonical Polaris services and the workflow facade, with no parallel RAG, workflow, datastore, provider, or administration implementation.

