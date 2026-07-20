# Model Allocation Readiness Check

This runbook records the final service-free readiness check for GitHub issue #24
against the parent model-allocation plan in issue #14. It complements the
canonical policy in [Polaris Model Profile Policy](model_profile_policy.md) and
keeps live-service validation prerequisites explicit before any optional live
run.

## Scope

The final readiness gate confirms that the model allocation work is integrated
across configuration, structured generation, RAG, strategy, evaluation, and
operator documentation. The required acceptance matrix is:

| Acceptance item | Service-free verification | Status |
| --- | --- | --- |
| approved aliases configured and discoverable | `tests/unit/config/test_litellm_model_alias_config.py` confirms every `polaris-local-*` alias maps to the approved LiteLLM binding and DeepSeek-R1 remains challenger-only. | Required |
| no concrete local model names in architectural defaults | `tests/unit/config/test_litellm_model_alias_config.py` statically scans production Python source roots for concrete local backend names outside LiteLLM config. | Required |
| reasoning-trace safety | `tests/unit/domain/test_reasoning_trace_safety.py`, `tests/unit/integration/clients/test_non_rag_client_stabilization.py`, and RAG security tests confirm reasoning traces are stripped or rejected before typed contracts, persistence-bound paths, RAG citations, reports, telemetry, and customer-visible output. | Required |
| structured-output | `tests/unit/config/test_ai_structured_output_settings.py`, `tests/unit/integration/providers/llm_structured_output`, and `tests/unit/application/structured_outputs/test_intelligence_workflow_structured_outputs.py` cover structured-output settings, provider contracts, and workflow schema compliance. | Required |
| strategy | `tests/unit/config/test_strategy_model_config.py`, `tests/unit/intelligence/strategy/test_strategy_model_alias_behavior.py`, and `tests/evaluation/test_strategy_synthesis_evals.py` cover strategy alias routing and deterministic quality fixtures. | Required |
| RAG | `tests/unit/config/test_rag_model_config.py`, `tests/unit/application/rag/test_rag_security.py`, `tests/unit/application/rag/test_secure_rag_generation.py`, `tests/unit/integration/providers/rag/test_litellm_query_routing_provider.py`, `tests/unit/integration/providers/rag/test_litellm_quality_evaluation_provider.py`, `tests/unit/integration/providers/rag/test_structured_answer_generation_provider.py`, `tests/evaluation/test_structured_rag_output_evals.py`, and `tests/evaluation/test_rag_regression_evals.py` cover RAG alias routing, secure generation, structured answer generation, quality checks, and deterministic RAG regression fixtures. | Required |
| evaluation gate | `tests/evaluation/test_golden_dataset_fixtures.py`, `tests/unit/application/evaluations/test_evaluation_datasets.py`, and `tests/unit/application/evaluations/test_model_replacement_gate.py` cover the canonical dataset slice and the model replacement validation gate. | Required |
| documentation current | `docs/model_profile_policy.md`, this readiness check, `docs/testing_guide.md`, `docs/litellm_gateway.md`, `docs/platform_rag_pipeline.md`, and `tests/unit/config/test_model_allocation_readiness.py` document and enforce local and production alias policy, test scope, and live-service requirements. | Required |
| live-service requirements | See [Optional live validation requirements](#optional-live-validation-requirements) before any live run. | Required before live validation |

## Service-free readiness command

The targeted service-free command is intentionally narrower than the full test
suite and is tied directly to the model-allocation acceptance items:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q \
  tests/unit/config/test_litellm_model_alias_config.py \
  tests/unit/config/test_ai_structured_output_settings.py \
  tests/unit/config/test_rag_model_config.py \
  tests/unit/config/test_strategy_model_config.py \
  tests/unit/config/test_model_allocation_readiness.py \
  tests/unit/domain/test_reasoning_trace_safety.py \
  tests/unit/integration/clients/test_non_rag_client_stabilization.py \
  tests/unit/integration/providers/llm_structured_output \
  tests/unit/application/structured_outputs/test_intelligence_workflow_structured_outputs.py \
  tests/unit/application/rag/test_rag_security.py \
  tests/unit/application/rag/test_secure_rag_generation.py \
  tests/unit/integration/providers/rag/test_litellm_query_routing_provider.py \
  tests/unit/integration/providers/rag/test_litellm_quality_evaluation_provider.py \
  tests/unit/integration/providers/rag/test_structured_answer_generation_provider.py \
  tests/unit/intelligence/strategy/test_strategy_model_alias_behavior.py \
  tests/evaluation/test_strategy_synthesis_evals.py \
  tests/evaluation/test_structured_rag_output_evals.py \
  tests/evaluation/test_rag_regression_evals.py \
  tests/evaluation/test_golden_dataset_fixtures.py \
  tests/unit/application/evaluations/test_evaluation_datasets.py \
  tests/unit/application/evaluations/test_model_replacement_gate.py
```

The full pytest suite was not run because issue #24 is a model-allocation
readiness check over already-scoped model, RAG, strategy, structured-output, and
evaluation boundaries. The repository testing policy prefers targeted checks and
requires live-service tests to be selected only after their services are
identified and confirmed healthy.

## Optional live validation requirements

Do not run these checks until the required services are confirmed healthy and
any necessary credentials are available only through local environment variables
or the approved secrets manager.

| Optional live validation | Required services | Required non-secret configuration | Notes |
| --- | --- | --- | --- |
| LiteLLM alias discovery and local model smoke | LiteLLM gateway and Ollama with configured local models pulled | `POLARIS_LITELLM_BASE_URL`, `POLARIS_LITELLM_API_KEY` when the gateway requires one, `POLARIS_LITELLM_OLLAMA_API_BASE` when Docker must reach host Ollama | Confirms `/v1/models` exposes `polaris-local-fast`, `polaris-local-reasoning`, `polaris-local-structured`, `polaris-local-synthesis`, `polaris-local-evaluation`, and `polaris-local-optimization`. |
| Live RAG projection checks | PostgreSQL, Qdrant, Neo4j, and BGE reranker as required by the selected `tests/integration/rag` file | Test database URL and local service endpoints from the operator shell | Qdrant and Neo4j remain rebuildable projections; PostgreSQL remains authoritative. |
| Live DeepEval replacement smoke | LiteLLM gateway plus its configured model backend, DeepEval, and optional PostgreSQL persistence depending on the command | `POLARIS_DEEPEVAL_ENABLED`, `POLARIS_DEEPEVAL_JUDGE_PROVIDER`, `POLARIS_DEEPEVAL_JUDGE_MODEL`, `POLARIS_RUN_LIVE_EVALS`; set `POLARIS_EVAL_REQUIRED` only for an explicit release gate | Live smoke is not replacement approval by itself; canonical replacement approval requires `ModelReplacementValidationGate` in `replacement_approval` mode. |
| Langfuse projection validation | Langfuse plus any PostgreSQL state needed by the selected export path | `POLARIS_LANGFUSE_HOST`, public key, secret key, environment, and release values from local secrets | Keep observation payloads redacted according to the active Langfuse redaction policy. |
| Observability dashboard/manual scrape checks | Prometheus, Jaeger, and Grafana when validating runtime dashboards or trace topology | Local endpoints and opt-in live trace environment variables | Current routine service-free tests use fakes or in-memory sinks for most telemetry coverage. |

A local Docker status check on 2026-07-20 returned no running Compose services,
so this readiness check used the service-free command above and did not start or
wait on unavailable PostgreSQL, Qdrant, Neo4j, LiteLLM, Ollama, Langfuse, BGE
reranker, Prometheus, Jaeger, or Grafana services.

## Last service-free result

The result should be updated whenever this readiness gate is rerun for a new
model allocation change.

| Date | Command | Result | Notes |
| --- | --- | --- | --- |
| 2026-07-20 | Targeted service-free readiness command in this document | Passed: 111 tests with this document self-check included. | Full suite and live-service checks intentionally skipped unless justified by scope and confirmed services. |
