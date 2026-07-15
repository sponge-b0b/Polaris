# Polaris LLM Evaluation

Polaris uses DeepEval as the canonical LLM evaluation engine for RAG and intelligence workflows. The evaluation layer measures answer quality, retrieval quality, citation support, report quality, strategy rationale quality, recommendation explanation quality, MCP tool response faithfulness, and agent task completion.

DeepEval is an evaluator. It is not the source of truth for Polaris records, workflow evidence, prompts, or observability. PostgreSQL remains authoritative for evaluation datasets, cases, runs, metric results, and artifacts. Langfuse receives sanitized score projections for AI-engineering analysis.

## Architecture

The canonical evaluation path is:

```text
workflow output / curated PostgreSQL record / approved fixture
        ↓
EvaluationCaseBuilder
        ↓
EvaluationDatasetService + EvaluationResultService
        ↓
PostgreSQL evaluation records
        ↓
EvaluationJobProcessor or EvaluationRunService
        ↓
DeepEvalEvaluationProvider
        ↓
EvaluationRun + EvaluationMetricResult
        ↓
PostgreSQL persistence
        ↓
EvaluationLangfuseProjectionService
        ↓
Langfuse score projection through the durable AI-observability queue
```

Production code must not call DeepEval directly from workflow nodes, RAG services, intelligence agents, CLI commands, MCP tools, or persistence code. The approved boundary is:

```text
integration.providers.llm_evaluation.DeepEvalEvaluationProvider
```

The provider owns DeepEval-specific metric construction, model invocation, concurrency limits, timeouts, and vendor result normalization. Application services own use-case orchestration and persistence.

## Canonical ownership model

| Concept | Canonical owner | Notes |
| --- | --- | --- |
| Evaluation target type | `domain.evaluation.EvaluationTargetType` | Defines what kind of output is being judged. |
| Evaluation dataset identity | `EvaluationDatasetReference` and PostgreSQL records | Datasets are versioned and durable. |
| Evaluation case | `EvaluationCase` and `EvaluationCaseRecord` | Input/output pair plus provenance and rubric. |
| Metric threshold | `EvaluationThreshold` and metric definitions | Higher score is always better in Polaris. |
| Evaluation run | `EvaluationRun` and `EvaluationRunRecord` | Captures evaluator, model, status, cases, and timing. |
| Metric result | `EvaluationMetricResult` and `EvaluationMetricResultRecord` | Stores normalized score, reason, status, threshold, and duration. |
| Langfuse projection | AI-observability export queue | Langfuse is a projection, not a second result store. |
| Evaluation telemetry | `EvaluationTelemetry` | Emits evaluation events and metrics at the application evaluation boundary. |

## Supported targets

Current target types are:

- `rag_answer`
- `rag_retrieval`
- `rag_generation`
- `morning_report`
- `strategy_synthesis`
- `recommendation_explanation`
- `mcp_tool_response`
- `agent_task`

Add a new target type only when there is a durable Polaris output worth evaluating and a clear owner for building cases from that output.

## Canonical datasets

The current canonical dataset definitions live in `application/evaluations/evaluation_datasets.py` and are mirrored by deterministic JSONL fixtures under `tests/evaluation/fixtures/`.

| Dataset name | Dataset ID | Target type | Purpose |
| --- | --- | --- | --- |
| `golden_rag_questions` | `golden_rag_questions_v1` | `rag_answer` | Grounded answer quality for canonical RAG questions. |
| `rag_citation_support` | `rag_citation_support_v1` | `rag_answer` | Citation and retrieved-context support. |
| `rag_security_prompt_injection` | `rag_security_prompt_injection_v1` | `rag_answer` | Prompt-injection resistance. |
| `morning_report_quality` | `morning_report_quality_v1` | `morning_report` | Professional report structure, clarity, attribution, and portfolio context. |
| `strategy_synthesis_quality` | `strategy_synthesis_quality_v1` | `strategy_synthesis` | Strategy rationale, conflict handling, and risk-aware synthesis. |
| `recommendation_explanations` | `recommendation_explanations_v1` | `recommendation_explanation` | Recommendation explanation quality and caveats. |
| `mcp_tool_responses` | `mcp_tool_responses_v1` | `mcp_tool_response` | Faithfulness of external transport output to canonical service responses. |
| `agent_task_completion` | `agent_task_completion_v1` | `agent_task` | Agent task satisfaction using supported Polaris evidence. |

Dataset definitions should include source lineage and a deterministic fixture URI. Dataset cases created from live workflow outputs must preserve source record IDs, workflow execution IDs, and Langfuse trace or observation IDs when available.

## Golden dataset baseline

A Polaris golden dataset is a reviewed, versioned evaluation benchmark that acts as the platform's baseline for LLM-assisted behavior. It is not a random test sample and it is not generated from live data at execution time. Each case is a durable question, prompt, report, recommendation, or tool-response scenario with specific expected behavior, attribution, and metric intent.

The source-controlled JSONL fixtures under `tests/evaluation/fixtures/` are the canonical reviewed baseline. They are intentionally committed so changes are visible in code review, reproducible across machines, and protected from accidental mutation by database state. PostgreSQL is the durable operational copy used by local and release-gate CLI runs after seeding. If fixture content and PostgreSQL content differ, reseed from the fixture source of truth rather than manually editing database rows. Canonical seeding replaces dataset membership exactly: cases no longer present in the fixture are detached from the active dataset while preserving their historical evaluation rows.

The baseline currently contains 100 curated cases distributed across RAG answer quality, citation grounding, prompt-injection resistance, morning-report quality, strategy synthesis, recommendation explanations, MCP tool responses, and agent task completion. The baseline should grow only through intentional reviewed changes because adding, removing, or rewriting cases changes what Polaris considers acceptable platform behavior.

## Golden dataset quality rules

- Cases must be reviewed deliberately; do not bulk-generate cases blindly and treat them as authoritative.
- Expected outputs, rubrics, and supporting context must be specific enough for an evaluator to distinguish a correct response from a plausible but unsupported one.
- Attribution must be preserved through source record IDs, workflow execution IDs, retrieval context IDs, citation context IDs, or trace/observation IDs when available.
- Coverage must include positive, negative, edge, and adversarial scenarios, especially for financial claims, refusal behavior, citation support, and prompt-injection attempts.
- Facts derived from live market or portfolio data must be frozen into deterministic fixture text before becoming golden baseline material.
- Metric thresholds should not be changed casually to make a benchmark pass; threshold changes require a versioned policy decision.
- Benchmark changes require intentional review because they redefine the platform baseline and may affect release gates.

## Adding a golden case safely

1. Confirm the output under evaluation has a durable Polaris owner and target type.
2. Add the case to the matching JSONL fixture under `tests/evaluation/fixtures/`, using a stable globally unique case ID.
3. Include expected output or a rubric, source lineage metadata, tags, and retrieval or citation context when relevant.
4. Run fixture validation and focused evaluation tests before seeding.
5. Dry-run seeding with `uv run polaris eval datasets seed --dry-run`, then seed the affected dataset with `uv run polaris eval datasets seed --dataset <dataset-name>` when PostgreSQL is available.
6. Confirm persisted counts with `uv run polaris eval datasets list` and run the selected dataset through DeepEval only when a live judge model is intentionally part of the validation.

## Metric and threshold policy

Polaris normalizes all scores to a `0.0` to `1.0` higher-is-better scale. This includes DeepEval metrics that are naturally lower-is-better, such as hallucination. The DeepEval provider converts those into absence or quality scores before returning them to application services.

RAG metric thresholds:

| Metric | Minimum score | Purpose |
| --- | ---: | --- |
| `faithfulness` | `0.80` | Answer support from retrieved context. |
| `answer_relevancy` | `0.75` | Whether the answer addresses the question. |
| `contextual_relevancy` | `0.70` | Whether retrieved evidence is relevant. |
| `contextual_precision` | `0.70` | Whether the most relevant evidence is ranked highly. |
| `contextual_recall` | `0.70` | Whether expected supporting evidence is retrieved. |
| `hallucination` | `0.85` | Absence of unsupported hallucinated content. |
| `citation_support` | `0.80` | Citation-backed factual support. |
| `financial_answer_quality` | `0.75` | Financial answer usefulness and clarity. |
| `risk_explanation_quality` | `0.75` | Risk caveat quality. |
| `unsupported_claim_penalty` | `0.85` | Penalizes unsupported financial claims. |
| `refusal_correctness` | `0.80` | Correct refusal for unsafe or unsupported requests. |
| `prompt_injection_resistance` | `0.90` | Resistance to prompt-injection attempts. |

Intelligence and report metric thresholds:

| Metric | Minimum score | Purpose |
| --- | ---: | --- |
| `strategy_synthesis_quality` | `0.80` | Quality of strategy synthesis and perspective weighting. |
| `recommendation_rationale_quality` | `0.80` | Recommendation rationale quality. |
| `report_completeness` | `0.80` | Completeness of generated reports. |
| `risk_assessment_quality` | `0.80` | Risk assessment quality. |
| `portfolio_context_alignment` | `0.75` | Alignment to portfolio context. |
| `reasoning_consistency` | `0.75` | Internal reasoning consistency. |
| `unsupported_financial_claims` | `0.85` | Absence of unsupported financial claims. |

Thresholds are versioned. Do not silently change existing thresholds in place after they have been used for release gates; create a new versioned threshold profile instead.

## Required environment variables

Use Polaris-prefixed variables for application behavior. Unprefixed DeepEval aliases may be accepted by settings for compatibility, but tracked documentation and deployment configuration should prefer the Polaris names.

| Variable | Purpose |
| --- | --- |
| `POLARIS_DEEPEVAL_ENABLED` | Enables the evaluation feature gate. |
| `POLARIS_DEEPEVAL_JUDGE_PROVIDER` | Logical judge provider name used in records and status output. |
| `POLARIS_DEEPEVAL_JUDGE_MODEL` | Judge model used by DeepEval metrics. |
| `POLARIS_DEEPEVAL_OLLAMA_BASE_URL` | Optional Ollama base URL used when the judge provider is `ollama`; defaults to the platform Ollama host when omitted. |
| `POLARIS_DEEPEVAL_STRICT_MODE` | Requires complete configuration during settings validation. |
| `POLARIS_DEEPEVAL_TELEMETRY_OPT_OUT` | Sets DeepEval telemetry opt-out behavior; defaults to privacy-preserving opt-out. |
| `POLARIS_DEEPEVAL_DEFAULT_THRESHOLD` | Fallback threshold for metrics without a specific threshold. |
| `POLARIS_DEEPEVAL_MAX_CONCURRENCY` | Maximum concurrent metric evaluations per run. |
| `POLARIS_DEEPEVAL_TIMEOUT_SECONDS` | Per-metric timeout. |
| `POLARIS_RUN_LIVE_EVALS` | Test-only gate for live DeepEval smoke tests. |
| `POLARIS_EVAL_REQUIRED` | Test-only release gate that fails when live eval config is missing instead of skipping. |

Keep judge-provider credentials in the provider's own approved environment variables or secrets manager. Do not commit API keys, passwords, tokens, or authenticated URLs.

Supported judge provider values are `openai`, `ollama`, and `litellm`. Polaris maps these values to DeepEval-native judge model classes instead of relying on ambiguous string inference. For local Ollama judging, configure `POLARIS_DEEPEVAL_JUDGE_PROVIDER=ollama`, `POLARIS_DEEPEVAL_JUDGE_MODEL=<local-model>`, and optionally `POLARIS_DEEPEVAL_OLLAMA_BASE_URL` when the default Ollama host is not correct.

## Local workflow

1. Start PostgreSQL if you need persisted datasets, cases, runs, and results.
2. Apply migrations.
3. Configure DeepEval judge settings in local shell state.
4. Confirm readiness:

   ```bash
   uv run polaris eval status
   ```

5. Dry-run and seed canonical source-controlled fixtures into PostgreSQL:

   ```bash
   uv run polaris eval datasets seed --dry-run
   uv run polaris eval datasets seed
   ```

   To seed one dataset only, add `--dataset <dataset-name>`.

6. Inspect canonical datasets and persisted case counts:

   ```bash
   uv run polaris eval datasets list
   ```

7. Run an evaluation against persisted cases:

   ```bash
   uv run polaris eval run --dataset golden_rag_questions
   uv run polaris eval run-rag --case <case-id>
   uv run polaris eval run-latest-rag
   ```

8. Inspect persisted results:

   ```bash
   uv run polaris eval results --run <run-id>
   ```

The CLI resolves services through the application DI scope. It does not call DeepEval, PostgreSQL repositories, or Langfuse SDKs directly.

## Baseline benchmark execution workflow

The 100-case golden baseline is an explicit local or release-gate workflow. It is not part of normal CI because full DeepEval runs require a live judge model, may take longer than deterministic tests, and can introduce evaluator-model variability.

Recommended execution sequence:

1. Seed canonical datasets into PostgreSQL:

   ```bash
   uv run polaris eval datasets seed
   ```

2. Confirm persisted dataset and case counts:

   ```bash
   uv run polaris eval datasets list
   ```

3. Run selected datasets through DeepEval. Prefer one dataset at a time so failures are attributable and retries are bounded:

   ```bash
   uv run polaris eval run --dataset golden_rag_questions
   ```

4. Inspect the persisted run output with the run ID printed by the previous command:

   ```bash
   uv run polaris eval results --run <run-id>
   ```

5. Drain and verify Langfuse score projection. Export delivery is handled by the configured `AiObservabilityExportWorker` or deployment scheduler, not by the evaluation CLI itself. Use the operational status command to confirm the durable export queue reaches zero backlog:

   ```bash
   uv run polaris observability ai-status
   ```

Run the full 100-case benchmark only when intentionally changing the platform baseline, preparing a release gate, validating a judge-model change, or verifying evaluation-pipeline changes. Normal CI should continue to use deterministic fixture validation, fake-provider tests, and non-live evaluation suites.

For release gates, use the dedicated script so fixture counts, PostgreSQL seed state, optional Langfuse queue health, and DeepEval run status are checked consistently:

```bash
uv run python scripts/run_baseline_evaluation_gate.py --dataset agent_task_completion
```

Use `--skip-live-evaluation` when you only want to verify fixture loading, PostgreSQL seeding, and persisted-count parity. The script fails if the PostgreSQL operational copy contains stale case membership that no longer matches the source-controlled fixtures.

## Async evaluation jobs

`EvaluationJobProcessor` is the application-level handoff for background evaluation work. Supported job types are:

- `evaluate_rag_result`
- `evaluate_strategy_output`
- `evaluate_report`
- `project_eval_scores_to_langfuse`
- `retry_failed_eval_projection`

The normal production flow is:

```text
workflow completes
→ output persisted
→ curated records projected
→ evaluation jobs enqueued
→ DeepEval runs asynchronously
→ results persisted
→ Langfuse scores projected
```

The job processor is intentionally queue-agnostic. A scheduler, daemon, CLI command, or future MCP tool may submit typed jobs, but the evaluation logic remains in application services.

## Langfuse relationship

DeepEval produces canonical Polaris evaluation records. Langfuse receives sanitized score projections.

Rules:

- evaluator code must not call Langfuse directly;
- scores are persisted to PostgreSQL before projection;
- projection failures must not erase successful evaluation results;
- Langfuse trace and observation IDs may be used for correlation, but they do not replace Polaris run, case, dataset, workflow, or PostgreSQL IDs;
- score reasons are subject to the same redaction and capture policy as other AI-observability payloads.

## Observability

Evaluation emits canonical telemetry for:

- evaluation run started, completed, and failed;
- metric execution latency;
- judge-model failures;
- threshold failures;
- dataset load failures;
- Langfuse projection failures;
- retry counts;
- skipped cases.

Current metric names include:

- `evaluation_runs_total`
- `evaluation_run_duration_seconds`
- `evaluation_cases_evaluated_total`
- `evaluation_metric_duration_seconds`
- `evaluation_metric_failures_total`
- `evaluation_threshold_failures_total`
- `evaluation_judge_model_failures_total`
- `evaluation_dataset_load_failures_total`
- `evaluation_langfuse_projection_failures_total`
- `evaluation_retry_jobs_total`
- `evaluation_skipped_cases_total`

Telemetry failures are non-fatal to successful evaluation persistence, but they must be defensively logged.

## CI workflow

Run non-live evaluation tests with:

```bash
uv run pytest -q tests/evaluation -m "not live_deepeval"
```

Run the focused unit coverage with:

```bash
uv run pytest -q \
  tests/unit/application/evaluations \
  tests/unit/integration/providers/llm_evaluation \
  tests/unit/config/test_deepeval_evaluation_settings.py
```

Live DeepEval checks are opt-in:

```bash
POLARIS_RUN_LIVE_EVALS=true \
POLARIS_DEEPEVAL_ENABLED=true \
POLARIS_DEEPEVAL_JUDGE_PROVIDER=<provider> \
POLARIS_DEEPEVAL_JUDGE_MODEL=<model> \
POLARIS_DEEPEVAL_OLLAMA_BASE_URL=http://localhost:11434 \
uv run pytest -q tests/evaluation -m live_deepeval
```

Set `POLARIS_EVAL_REQUIRED=true` only in explicit release-gate jobs where missing live evaluation configuration should fail instead of skip.

## Live service requirements

| Operation | Required services |
| --- | --- |
| Unit tests and non-live CI evaluation suite | None. Uses deterministic fixtures and fake providers. |
| Persisted dataset/case/run/result CLI workflows | PostgreSQL with migrations applied. |
| Live DeepEval smoke test or real evaluation run | Configured judge model/provider and any provider-specific backing service or credentials. |
| Langfuse score projection worker | PostgreSQL plus configured Langfuse service. |
| Build cases from live RAG outputs | Whatever services were required to produce those RAG outputs; evaluation itself reads persisted cases. |

Notify collaborators before running tests that require live services. Do not wait for Neo4j, Qdrant, Langfuse, or model endpoints to time out unless that service is required for the selected test.

## Privacy and redaction rules

- Prefer synthetic, curated, or explicitly approved evaluation cases.
- Do not store raw customer identifiers, account numbers, credentials, API keys, authenticated URLs, cookies, or bearer tokens in fixtures, cases, reasons, metadata, docs, or plans.
- Keep prompt, response, and context capture disabled by default unless redaction policy explicitly allows it.
- Evaluation reasons may quote parts of model outputs; treat them as durable AI-observability content and redact before Langfuse projection.
- Use source record IDs, workflow execution IDs, case IDs, and trace IDs for attribution instead of copying sensitive raw payloads.

## Adding a new evaluation dataset

1. Define the durable output or curated record that deserves evaluation.
2. Add or update an `EvaluationTargetType` only when no existing target fits.
3. Add a canonical dataset definition in `application/evaluations/evaluation_datasets.py`.
4. Add deterministic JSONL fixtures under `tests/evaluation/fixtures/`.
5. Add metric definitions or threshold-profile entries when the existing policy is insufficient.
6. Add tests that validate the dataset definition, fixture shape, source lineage, and selected metric policy.
7. Register or project persisted cases through the canonical application services, not by inserting arbitrary metadata.
