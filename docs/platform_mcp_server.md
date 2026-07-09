# Polaris MCP Server

## Purpose

The Polaris MCP server is an external transport boundary for approved LLM agent
hosts. It exposes a small read-only catalog over the Model Context Protocol
(MCP) so an outside assistant can ask grounded RAG questions, inspect workflow
metadata, and retrieve completed-run evidence without learning Polaris internals.

The server is intentionally thin. It must not become a second workflow engine,
RAG implementation, datastore gateway, provider gateway, or administration API.
Every non-health tool delegates to canonical Polaris application services or the
canonical `WorkflowFacade` through the server-owned Dishka application container
and one per-invocation request scope.

## Architecture pattern and justification

```text
MCP client / agent host
    -> MCP transport boundary
    -> strict MCP request model
    -> FastMCP tool handler
    -> Dishka request scope
    -> canonical application service or WorkflowFacade
    -> strict MCP response model
```

This pattern exists to preserve one source of truth for platform behavior:

- Workflow discovery and completed-run retrieval remain owned by
  `WorkflowFacade`.
- RAG answering and readiness remain owned by canonical RAG application services.
- Dependency composition remains owned by the existing Polaris Dishka container.
- PostgreSQL, Qdrant, Neo4j, Firecrawl, providers, and runtime internals are not
  directly imported or queried by `mcp_server/`.
- Transport serialization is the only place MCP-specific dictionaries and JSON
  shapes should appear.

If a future MCP consumer needs a capability that is not already available
through a canonical Polaris service, implement that service capability first and
then expose it through MCP. Do not implement the missing behavior inside the MCP
server.

## Supported transports

### Trusted local stdio

Use stdio when the agent host starts Polaris as a trusted child process.

```bash
uv run polaris-mcp --transport stdio
```

Stdio behavior:

- Uses the same FastMCP server and same six-tool catalog as HTTP.
- Requires no bearer token because the parent process owns the child process.
- Keeps MCP protocol frames on stdout.
- Redirects normal process logging away from stdout so logs do not corrupt the
  MCP protocol stream.

Agent-host configuration should treat `polaris-mcp --transport stdio` as a local
command transport. The agent host should not wrap stdout or inject human-readable
logging into that stream.

### Streamable HTTP

Use Streamable HTTP when a remote or separately hosted agent host needs to call
Polaris over HTTP.

Example startup with placeholder values:

```bash
export POLARIS_MCP_TRANSPORT=streamable-http
export POLARIS_MCP_HOST=127.0.0.1
export POLARIS_MCP_PORT=8000
export POLARIS_MCP_PATH=/mcp
export POLARIS_MCP_BEARER_TOKEN='<replace-with-generated-token>'
uv run polaris-mcp --transport streamable-http
```

Streamable HTTP behavior:

- Runs the same FastMCP server as stdio.
- Uses stateless JSON Streamable HTTP.
- Mounts MCP at `POLARIS_MCP_PATH`.
- Requires a bearer token for the MCP path and nested MCP paths.
- Exposes unauthenticated process-only readiness at `/healthz`.
- Starts and stops the FastMCP session manager and Polaris DI container through
  the server lifespan.

The `/healthz` endpoint intentionally reports only process readiness:

```json
{"status": "ready"}
```

It does not reveal PostgreSQL, Qdrant, Neo4j, model, workflow, or application
service status. Use the `polaris_rag_status` tool for authorized RAG readiness.

## Configuration

| Environment variable | Default | Required | Description |
| --- | --- | --- | --- |
| `POLARIS_MCP_TRANSPORT` | `stdio` | No | `stdio` or `streamable-http`. |
| `POLARIS_MCP_HOST` | `127.0.0.1` | No | Host used by the HTTP server. |
| `POLARIS_MCP_PORT` | `8000` | No | HTTP server TCP port. |
| `POLARIS_MCP_PATH` | `/mcp` | No | Streamable HTTP MCP route. Must start with `/`. |
| `POLARIS_MCP_BEARER_TOKEN` | unset | HTTP only | Bearer token required for `streamable-http`. |
| `POLARIS_MCP_ALLOW_WEB` | `false` | No | Whether `polaris_rag_ask` may request canonical web fallback. |
| `POLARIS_MCP_MAX_QUERY_CHARACTERS` | `8000` | No | Maximum accepted RAG query length. |
| `POLARIS_MCP_MAX_TOP_K` | `50` | No | Maximum accepted RAG retrieval depth. |
| `POLARIS_MCP_MAX_PAGE_SIZE` | `100` | No | Maximum accepted page size for list tools. |

Never commit a real bearer token, database URL with credentials, provider API
key, or service password in source, tests, documentation, logs, or snapshots.
Use placeholders in examples.

## Authentication behavior

Streamable HTTP requests to the configured MCP path must include:

```text
Authorization: Bearer <replace-with-generated-token>
```

Missing, malformed, wrong-scheme, and invalid bearer tokens all return the same
safe response:

```json
{"error": "unauthorized"}
```

The server does not echo supplied credentials, distinguish which authentication
check failed, or include token values in logs or telemetry.

## Exact V1 tool catalog

The V1 catalog is intentionally small and read-only.

| Tool | Purpose | Read-only | Idempotent | Open world |
| --- | --- | --- | --- | --- |
| `polaris_rag_ask` | Ask a grounded question through canonical Polaris RAG. | Yes | No | Yes |
| `polaris_rag_status` | Inspect canonical RAG dependency/projection readiness. | Yes | Yes | No |
| `polaris_workflows_list` | List registered workflow summaries. | Yes | Yes | No |
| `polaris_workflow_describe` | Describe one registered workflow graph. | Yes | Yes | No |
| `polaris_completed_runs_list` | List completed execution IDs for one workflow. | Yes | Yes | No |
| `polaris_completed_run_get` | Retrieve one completed-run summary and selected sections. | Yes | Yes | No |

`polaris_rag_ask` is non-idempotent because model output and persisted query-log
metadata may vary between invocations. It is the only open-world tool because the
canonical RAG service may use explicitly authorized web fallback when both server
configuration and the request allow it.

## Tool schemas and examples

The source of truth for schemas is `mcp_server/models.py`. The server registers
strict input and output models with unknown fields rejected.

### `polaris_rag_ask`

Input fields:

- `query` — required non-empty question.
- Optional filters: `symbols`, `source_types`, `source_tables`, `agent_names`,
  `agent_types`, `report_types`, `regimes`, `workflow_name`, `execution_id`,
  `runtime_id`, `as_of_start`, `as_of_end`.
- Controls: `top_k`, `allow_web`, `include_contexts`.

Example request:

```json
{
  "query": "What changed in the latest morning report risk assessment?",
  "workflow_name": "morning_report",
  "top_k": 8,
  "allow_web": false,
  "include_contexts": false
}
```

Response highlights:

- `query_id`
- `answer_text`
- `status`
- `route`
- `citations`
- optional `contexts`
- confidence, grounding, utility, injection, reflection, corrective-action, and
  generated-at fields

Successful answers and explicitly requested retrieved contexts are not silently
truncated or summarized by the MCP layer.

### `polaris_rag_status`

Input fields:

- `include_details` — whether dependency component details should be included.

Example request:

```json
{"include_details": true}
```

Response highlights:

- overall `status`, `message`, and `ready`
- canonical PostgreSQL document/chunk/job readiness
- Qdrant vector readiness
- Neo4j graph readiness
- embedding and reranker readiness

Degraded readiness is returned as a structured successful MCP response, not as a
transport exception.

### `polaris_workflows_list`

Input fields:

- `tag`
- `offset`
- `limit`

Example request:

```json
{"tag": "builtin", "offset": 0, "limit": 20}
```

Response highlights:

- `workflows`
- `total_count`
- `offset`
- `limit`
- `has_more`
- `next_offset`

Workflow order and tag filtering are delegated to `WorkflowFacade`; MCP only
applies transport pagination.

### `polaris_workflow_describe`

Input fields:

- `workflow_name`

Example request:

```json
{"workflow_name": "morning_report"}
```

Response highlights:

- `found`
- workflow name, description, tags, metadata
- graph definition with node names, node types, dependencies, retry policy,
  timeout, enabled state, tags, and metadata
- typed `workflow_not_found` error when missing

### `polaris_completed_runs_list`

Input fields:

- `workflow_name`
- `offset`
- `limit`

Example request:

```json
{"workflow_name": "morning_report", "offset": 0, "limit": 20}
```

Response highlights:

- `workflow_name`
- ordered `execution_ids`
- `total_count`
- `offset`
- `limit`
- `has_more`
- `next_offset`

Completed-run ordering is delegated to `WorkflowFacade`; MCP does not sort or
reinterpret execution IDs.

### `polaris_completed_run_get`

Input fields:

- `workflow_name`
- `execution_id`
- `include` — any of `workflow_inputs`, `node_outputs`, `errors`,
  `artifact_refs`, `trace_context`
- `node_names` — exact node-name selector; requires `node_outputs` in `include`

Example request:

```json
{
  "workflow_name": "morning_report",
  "execution_id": "example-execution-id",
  "include": ["node_outputs", "trace_context"],
  "node_names": ["portfolio_state_builder"]
}
```

Response highlights:

- `found`
- workflow, execution, runtime, mode, timestamp, context-version, count summary
- optional selected sections
- typed `completed_run_not_found` error when missing

Selected node outputs are returned exactly after boundary sanitization; the MCP
layer does not summarize or truncate long LLM-style response fields.

## Web-access policy

Web access is controlled twice:

1. Server configuration: `POLARIS_MCP_ALLOW_WEB` must be true.
2. Per-request intent: `polaris_rag_ask.allow_web` must be true.

If either is false, MCP requests cannot enable web fallback. MCP does not expose
Firecrawl, SerpApi, or any web provider as standalone tools. Web retrieval, when
allowed, remains a canonical RAG service behavior behind `polaris_rag_ask`.

## Service prerequisites

The MCP server itself starts as a transport boundary, but tool usefulness depends
on the canonical Polaris services behind it.

- Workflow catalog tools require the Polaris application container and workflow
  facade composition.
- Completed-run tools require completed-run persistence to be configured and
  reachable through `WorkflowFacade`.
- RAG status and RAG ask require the configured canonical RAG dependencies for
  the requested operation, typically PostgreSQL and any enabled projection/model
  services.
- `/healthz` does not validate those dependencies.

For live-service testing, start and verify required services before invoking live
MCP tools. Unit and isolated MCP transport tests should use fake-backed services
and must not contact PostgreSQL, Qdrant, Neo4j, model servers, or web providers.

## Security and sanitization

MCP responses sanitize returned metadata, node-output sections, errors, trace
attributes, and dependency error strings before crossing the transport boundary.
The MCP telemetry layer records approved dimensions only and must not record raw
queries, answers, node outputs, credentials, database URLs, exception messages,
or tracebacks.

## Deferred and prohibited V1 tools

The following are intentionally not part of V1:

- workflow run, pause, resume, or cancel
- RAG ingestion, embedding processing, graph processing, or projection rebuild
- completed-run deletion or cleanup
- direct SQL, Cypher, Qdrant, Neo4j, or provider/vendor operations
- Firecrawl or web search as standalone tools
- shell, filesystem, or plugin-management tools
- write/admin tools of any kind

Adding any of these requires a separate plan, explicit approval, and usually a
canonical Polaris application-service capability first.
