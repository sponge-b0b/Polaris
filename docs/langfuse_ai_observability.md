# Langfuse AI Observability

Polaris uses Langfuse as the required AI-observability projection for RAG and intelligence workflows. Langfuse complements, but does not replace, Polaris's canonical telemetry stack:

```text
Polaris logs, metrics, OpenTelemetry traces, PostgreSQL records
        ↓
Polaris typed AI-observation contracts
        ↓
Durable PostgreSQL Langfuse export queue
        ↓
Official Langfuse SDK ingestion boundary
        ↓
Langfuse traces, generations, prompts, datasets, scores, and evaluations
```

PostgreSQL remains the authoritative system of record. Jaeger, Prometheus, and Grafana remain the operational telemetry surfaces. Langfuse is the AI-engineering surface for LLM/RAG behavior, prompt provenance, datasets, and evaluation traces.

## Required configuration

Production AI-capable deployments must provide Langfuse configuration through environment variables. Do not commit Langfuse credentials or full authenticated connection strings.

| Variable | Required in production | Purpose |
| --- | --- | --- |
| `POLARIS_LANGFUSE_HOST` | Yes | Self-hosted or approved Langfuse endpoint URL. Must be `http://` or `https://`. |
| `POLARIS_LANGFUSE_PUBLIC_KEY` | Yes | Langfuse project public key. |
| `POLARIS_LANGFUSE_SECRET_KEY` | Yes | Langfuse project secret key. Keep environment-only. |
| `POLARIS_LANGFUSE_ENVIRONMENT` | Recommended | Langfuse environment label. Defaults to `development`. |
| `POLARIS_LANGFUSE_RELEASE` | Recommended | Release/build identifier for trace correlation. |
| `POLARIS_LANGFUSE_SAMPLE_RATE` | Optional | Export sample rate between `0.0` and `1.0`. Defaults to `1.0`. |
| `POLARIS_LANGFUSE_CAPTURE_PROMPTS` | Optional | Enables sanitized prompt body capture when policy allows it. Defaults to `false`. |
| `POLARIS_LANGFUSE_CAPTURE_RESPONSES` | Optional | Enables sanitized response body capture when policy allows it. Defaults to `false`. |
| `POLARIS_LANGFUSE_CAPTURE_CONTEXTS` | Optional | Enables sanitized retrieved-context capture when policy allows it. Defaults to `false`. |
| `POLARIS_LANGFUSE_CAPTURE_USER_INPUT` | Optional | Enables sanitized user-input capture when policy allows it. Defaults to `false`. |
| `POLARIS_LANGFUSE_REDACTION_MODE` | Optional | Capture policy mode: `strict`, `metadata_only`, or `permissive`. Defaults to `strict`. |
| `POLARIS_LANGFUSE_MAX_PAYLOAD_CHARACTERS` | Optional | Maximum captured prompt/response/context body size after redaction. Defaults to `8000`. |
| `POLARIS_LANGFUSE_MAX_METADATA_VALUE_CHARACTERS` | Optional | Maximum string metadata value size after redaction. Defaults to `512`. |
| `POLARIS_LANGFUSE_RETENTION_DAYS` | Optional | Retention window for terminal PostgreSQL export jobs. Defaults to `90`. |
| `POLARIS_LANGFUSE_ALLOW_CLOUD_HOST` | Optional | Required approval gate for `cloud.langfuse.com`. Defaults to `false`. |

The settings loader accepts unprefixed `LANGFUSE_*` aliases for standard Langfuse tooling compatibility, but Polaris-owned application export configuration should use the `POLARIS_LANGFUSE_*` names. The Docker Compose service database variables remain `LANGFUSE_POSTGRES_DB`, `LANGFUSE_POSTGRES_USER`, and `LANGFUSE_POSTGRES_PASSWORD` because they configure the self-hosted Langfuse container, not Polaris application export behavior.

## Bootstrap validation

`Settings.validate_langfuse_observability()` validates the AI-observability bootstrap configuration:

- production environments require host, public key, and secret key;
- the host must be an HTTP(S) URL;
- error messages identify missing variables without echoing configured secret values;
- `cloud.langfuse.com` is rejected unless `POLARIS_LANGFUSE_ALLOW_CLOUD_HOST=true` is set after explicit governance/security approval;
- local and unit-test execution may explicitly pass `require_configured=False` and inject fake sinks.

The production export worker resolves `LangfuseSdkExportClient.from_settings()`, which validates that the official SDK can be configured before any queued export is sent. RAG execution itself queues durable export jobs and does not require a live Langfuse service in-process.

## Canonical boundaries

Polaris code must not call Langfuse directly from RAG services, intelligence agents, workflow nodes, providers, CLI commands, or tests. The approved production SDK boundary is:

```text
application.observability.langfuse_sdk_exporter.LangfuseSdkExportClient
```

The export flow is:

1. RAG or intelligence code creates a typed `AiObservation`.
2. `AiObservabilityProjector` sends it to `DurableLangfuseAiObservabilitySink`.
3. `AiObservabilityExportQueueService` maps the observation to a sanitized payload and stores it as a PostgreSQL export job.
4. `AiObservabilityExportWorker` claims queued jobs and calls `LangfuseSdkExportClient`.
5. `LangfuseSdkExportClient` uses the official `langfuse` package boundary to create deterministic trace, generation/span, and score records.
6. The worker persists external Langfuse trace and observation IDs back to PostgreSQL.

Deterministic Langfuse IDs are derived from Polaris idempotency keys so retrying a durable export job does not create duplicate Langfuse observations.

## Capture policy posture

Langfuse being required does not mean raw prompts, responses, retrieved contexts, portfolio data, or user inputs are automatically exported.

Default local and production-safe behavior is metadata-first:

- prompt capture: disabled
- response capture: disabled
- retrieved-context capture: disabled
- user-input capture: disabled
- redaction mode: `strict`

Prompt, response, context, and user-input bodies are exported only when the capture flag is enabled **and** the redaction mode permits it. The current permissive text capture remains bounded by `AiObservabilityCapturePolicy.max_payload_characters`.

All exported payloads pass through the Polaris security boundary before reaching the durable queue or the Langfuse SDK adapter:

- metadata keys that look like secrets, credentials, tokens, cookies, sessions, or authorization values are replaced with `[redacted]`;
- broker, account, customer, client, and user identifiers in metadata are hashed instead of exported in raw form;
- prompt, response, evaluation-reason, and metadata text are scanned for common secret assignment, bearer-token, and authenticated-URL patterns;
- text fields are truncated after redaction according to the configured payload or metadata budgets;
- dropped, redacted, and truncated field paths are recorded in the exported `redaction` payload so operators can monitor capture-policy behavior without seeing the sensitive content itself.

## Prompt management and governance

Langfuse is the prompt authoring, comparison, and observability workspace. Polaris remains the production prompt-governance authority.

Production AI generation observations must include a typed prompt reference:

- `prompt_name` identifies the canonical prompt contract;
- `prompt_version` identifies the pinned production version;
- `prompt_hash` fingerprints the exact source-controlled or approved Langfuse prompt text;
- `source` identifies the approved origin, such as `polaris.source_controlled` or `langfuse.approved`.

Runtime exports use `AiPromptGovernancePolicy` before mapping observations to Langfuse. In production, generation observations without a prompt reference are rejected by the export boundary, and mutable prompt labels such as `latest`, `draft`, `dev`, or `mutable` are not accepted. This prevents split-brain behavior where Langfuse prompt edits can silently change production reasoning.

The supported lifecycle is:

```text
source-controlled fallback prompt or Langfuse candidate
        ↓
evaluation dataset / DeepEval run / human review
        ↓
AiPromptPromotionRequest
        ↓
AiPromptPromotionPolicy
        ↓
approved pinned prompt reference
        ↓
production RAG or intelligence observation
        ↓
Langfuse projection with prompt provenance
```

Source-controlled fallback prompts remain required for deterministic tests, replay, disaster recovery, and offline execution. If a future workflow resolves prompt text from Langfuse, it must first convert that prompt to a pinned, approved Polaris prompt reference before production use.

## DeepEval-ready contract shape

The Langfuse projection contracts intentionally include DeepEval-ready identifiers and score fields:

- `dataset_id`, `case_id`, and `run_id` correlation IDs;
- `AiEvaluationObservation` and `AiScoreProjection` score records;
- score reason, threshold, evaluator model, and evaluator provider metadata;
- trace and observation correlation IDs that allow DeepEval scores to attach to the evaluated generation or retrieval stage.

When DeepEval is integrated, it should emit canonical Polaris evaluation observations and let the same durable Langfuse export queue project those scores to Langfuse.



## Local self-host setup

The repository Docker Compose stack includes a self-hosted Langfuse service for local development. The application integration only needs the Langfuse HTTP endpoint and project credentials; the Langfuse container's own PostgreSQL credentials are separate infrastructure settings.

Minimal local setup flow:

1. Start the local PostgreSQL and Langfuse services.
2. Create or select a Langfuse project for local Polaris testing.
3. Export only Polaris application variables; do not write real credentials into tracked files:

   ```bash
   export POLARIS_LANGFUSE_HOST="http://localhost:3000"
   export POLARIS_LANGFUSE_PUBLIC_KEY="<public-key>"
   export POLARIS_LANGFUSE_SECRET_KEY="<secret-key>"
   export POLARIS_LANGFUSE_ENVIRONMENT="development"
   ```

4. Keep capture flags disabled unless a specific redaction test requires sanitized bodies.
5. Run unit tests with fake clients first. Run live export checks only after confirming Langfuse is reachable.

The RAG and intelligence workflows should remain usable when the export worker is stopped. Workflow code queues AI-observability jobs; the worker is responsible for delivery to Langfuse.

## Operational signals and dashboards

Langfuse adds an AI-engineering dashboard, but operational ownership remains in Polaris telemetry. Monitor the projection pipeline through logs, metrics, traces, PostgreSQL queue state, and Langfuse UI views.

Operational status is exposed through the Polaris CLI:

```bash
uv run polaris observability ai-status
uv run polaris observability ai-status --format json
```

The command reads PostgreSQL export-queue state and Langfuse configuration through the canonical application DI scope. It does not read Langfuse as a source of truth. `healthy` means the projection is configured and has no queued, running, retryable, or exhausted jobs. `backlogged`, `retrying`, `degraded`, and `not_configured` are actionable operator states. Reachability remains `not_checked` unless a separate live-smoke operation is explicitly run after confirming the Langfuse service is available.

Current Polaris metric names emitted by the queue, worker, and status surfaces include:

| Metric | Kind | Purpose |
| --- | --- | --- |
| `application.ai_observability.observations.queued` | Counter | Number of typed AI observations accepted into the durable export queue. |
| `application.ai_observability.export.attempts` | Counter | Worker attempts to send queued observations to Langfuse. |
| `application.ai_observability.exports` | Counter | Successful Langfuse exports. |
| `application.ai_observability.export.failures` | Counter | Failed export attempts. |
| `application.ai_observability.export.retries` | Counter | Failed attempts that enter retry or exhausted state. |
| `application.ai_observability.export.duration_seconds` | Histogram | Worker-side export call duration. |
| `application.ai_observability.export.delivery_latency_seconds` | Histogram | Time from observation creation to successful export. |
| `application.ai_observability.langfuse.configured` | Gauge | Whether required Langfuse configuration is present. |
| `application.ai_observability.export_queue.jobs` | Gauge | Queue depth grouped by job status. |
| `application.ai_observability.export_queue.backlog` | Gauge | Pending, running, and retryable failed jobs. |
| `application.ai_observability.export_queue.exhausted_failed` | Gauge | Jobs that exhausted retry attempts and require operator action. |
| `application.ai_observability.retention.deleted_jobs` | Counter | Terminal Langfuse export jobs removed by PostgreSQL retention enforcement. |

Recommended Polaris metrics and dashboard panels:

| Signal | Purpose |
| --- | --- |
| Queued export jobs by status | Confirms backlog health: queued, in-progress, exported, failed, dead-lettered when supported. |
| Export attempts and retry count | Shows unstable Langfuse connectivity, credential problems, or payload mapping regressions. |
| Export latency histogram | Measures time from observation creation to successful Langfuse projection. |
| Export failure rate | Alerts when Langfuse projection is unhealthy while preserving domain workflow success. |
| Observation volume by family/type/status | Shows RAG, intelligence, retrieval, reranking, generation, and evaluation coverage. |
| Capture-policy flags and redaction mode | Confirms production deployments remain metadata-first unless explicitly approved. |
| Dataset and evaluation scores | Tracks quality trends for RAG, citations, report QA, strategy rationale, and prompt-injection resistance. |

Recommended Langfuse views:

- RAG trace timeline by workflow execution, node, route, model, and stage;
- generation observations with prompt-version references when prompt management is implemented;
- retrieval and reranking observations with bounded score/count metadata;
- evaluation score trends by dataset, case, run, and release;
- failed or degraded AI stages correlated back to Polaris trace, workflow, and runtime IDs.

Logging requirements:

- exporter failures must log exceptions with tracebacks;
- retryable failures must include export job ID, idempotency key, observation type/name, attempt count, and max attempts;
- telemetry failures must stay non-fatal to valid RAG or intelligence results;
- secrets and raw credential values must never be logged.

Trace requirements:

- Polaris trace, span, workflow, runtime, node, dataset, case, and run identifiers are carried as correlation fields on AI observations;
- exported Langfuse trace and observation IDs are persisted back to PostgreSQL when available;
- Langfuse IDs do not replace Polaris trace IDs, runtime IDs, workflow execution IDs, or PostgreSQL record IDs.

## Production security posture

Langfuse is a required AI-observability projection for production AI-capable Polaris deployments, but it is not a new source of truth.

Production rules:

- PostgreSQL remains authoritative for workflow evidence, curated records, export jobs, and audit history.
- Langfuse receives sanitized AI-observability projections only.
- Use self-hosted Langfuse by default unless cloud Langfuse is explicitly approved by governance/security.
- Store Langfuse credentials in environment variables or a secrets manager only.
- Do not import the official `langfuse` SDK outside `application.observability.langfuse_sdk_exporter`.
- Do not export raw portfolio holdings, account identifiers, prompts, responses, retrieved contexts, user inputs, or web content unless the capture policy and redaction mode explicitly allow it.
- Do not build workflow, RAG, intelligence, or recommendation behavior that depends on reading back from Langfuse.
- Treat deletion from Langfuse as projection cleanup; authoritative deletion, retention, and audit policies remain PostgreSQL-owned.

## Retention and redaction responsibilities

Retention is layered:

1. PostgreSQL owns canonical records, workflow evidence, export jobs, audit history, and retention enforcement.
2. Langfuse owns AI-observability projections used for prompt, trace, dataset, and evaluation workflows.
3. Qdrant, Neo4j, dashboards, rendered files, and Langfuse are rebuildable or disposable projections unless explicitly promoted through a canonical Polaris contract.

Guidelines:

- Langfuse retention should be no longer than the approved retention period for the corresponding Polaris canonical records.
- If PostgreSQL retention deletes or anonymizes canonical AI-observability/export records, the Langfuse projection should be deleted or anonymized as part of the same operational policy.
- `AiObservabilityRetentionService` deletes terminal PostgreSQL export jobs with `exported` or `skipped` status once their `updated_at` timestamp is older than `POLARIS_LANGFUSE_RETENTION_DAYS`. Failed, pending, and running jobs are retained for operator action.
- Langfuse project retention/deletion remains an external administrative operation unless a future approved Langfuse deletion API integration is added.
- Keep strict redaction as the production default.
- Dataset cases should use synthetic, curated, or explicitly approved examples. They should not contain customer PII, raw account identifiers, or unredacted portfolio details.
- Evaluation scores and reasons may be durable; ensure reasons do not echo sensitive prompt, context, response, or customer data.

## Dataset and evaluation operations

The current integration includes typed dataset contracts and SDK-backed dataset export support. DeepEval integration is still governed by the separate DeepEval plan.

Current supported operations:

- build canonical Polaris regression cases for RAG answer quality, citation groundedness, report QA, strategy rationale, and prompt-injection resistance;
- export dataset definitions and dataset items to Langfuse through the official SDK boundary;
- map numeric scores to `PASS`, `WARN`, and `FAIL` while preserving threshold, evaluator, dataset, case, and run metadata;
- project evaluation observations through the same durable export queue used by RAG and intelligence observations.

DeepEval should later produce canonical Polaris evaluation records and observations, then let this existing Langfuse projection path export scores and reasons. It should not call Langfuse directly from evaluator code.

## Test support

Unit tests use fake clients/sinks to verify AI-observability emission and SDK payload mapping without a live Langfuse service. Live Langfuse tests must be explicitly marked/documented and should run only after the user confirms the Langfuse service is available.
