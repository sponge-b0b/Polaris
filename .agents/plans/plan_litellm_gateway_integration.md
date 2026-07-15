  # Polaris LiteLLM Gateway Integration Plan

  ## Summary

  Polaris should integrate LiteLLM proxy-first as the canonical LLM gateway, not as a second in-process LLM abstraction. LiteLLM’s documented strengths are an OpenAI-compatible proxy, provider normalization, auth, rate limits,
  cost tracking, fallback/routing, and multi-provider access through one API surface (LiteLLM docs (https://docs.litellm.ai/), GitHub (https://github.com/BerriAI/litellm)).

  Implementation default:

  - Run LiteLLM as a Docker Compose service.
  - Polaris calls LiteLLM through an async OpenAI-compatible client.
  - Existing Ollama-specific generation paths are directly migrated to the gateway.
  - LiteLLM owns provider/model routing; Polaris owns typed requests, telemetry, RAG/intelligence orchestration, and persistence.
  - BGE embeddings/reranking remain unchanged because they are already dedicated provider/client boundaries.

  ## Key Changes

  - Add canonical LiteLLM settings:
      - POLARIS_LITELLM_BASE_URL, default http://localhost:4000/v1
      - POLARIS_LITELLM_API_KEY, required when LiteLLM strict mode is enabled
      - POLARIS_LITELLM_TIMEOUT_SECONDS
      - POLARIS_LITELLM_ENABLED
      - Optional strict validation for production environments.

  - Add config/litellm/config.yaml with model mappings from existing Polaris model settings to LiteLLM provider targets, initially routing local models to Ollama.
  - Add a litellm Docker Compose service using the official LiteLLM proxy image and mounted config.
  - Keep LiteLLM proxy persistence separate from Polaris canonical PostgreSQL records; LiteLLM’s internal database, if enabled, is infrastructure state for proxy keys/spend, not a Polaris system-of-record table.
  - Add a typed async gateway client, for example LiteLlmGatewayClient, wrapping openai.AsyncOpenAI against the LiteLLM proxy.
  - Replace direct Ollama use in RAG query routing, CRAG/Self-RAG quality evaluation, and answer generation with LiteLLM-backed providers.
  - Update Instructor, DSPy, and DeepEval configuration so their model calls can target the LiteLLM gateway through OpenAI-compatible base URL and model names.
  - Remove obsolete direct Ollama provider wiring once no production path depends on it.
  - Preserve existing model-setting names where possible; Polaris sends configured model identifiers to LiteLLM, and LiteLLM maps them to concrete providers.

  ## Implementation Steps

  1. [x] Configuration and Compose
      - Add LiteLLM settings to config/settings.py and .env.example.
      - Add config/litellm/config.yaml with local Ollama-backed model entries for current Polaris RAG and evaluation model names.
      - Add a litellm service to docker-compose.yml.
      - Verification: settings unit tests, docker compose config --quiet.

  2. [x] Canonical Gateway Client
      - Add an async OpenAI-compatible LiteLLM gateway client under the existing LLM/provider boundary.
      - Support:
          - chat text generation
          - JSON/object generation
          - model metadata in results
          - timeout/error normalization

      - Do not expose raw OpenAI SDK response objects outside the client boundary.
      - Verification: unit tests using a fake OpenAI-compatible transport/client.

  3. [x] RAG LLM Provider Migration
      - Replace OllamaRagQueryModelProvider and OllamaRagQualityModelProvider with LiteLLM gateway-backed providers.
      - Update RAG answer generation / structured output wiring so final synthesis uses the gateway path.
      - Ensure provider telemetry records provider_name="litellm" plus the logical model name and operation.
      - Verification: focused RAG routing, quality, answer-generation, and DI tests.

  4. [x] Structured Output, DeepEval, and DSPy Alignment
      - Reconfigure Instructor provider construction to use the LiteLLM OpenAI-compatible endpoint.
      - Add DeepEval judge-provider support for LiteLLM/OpenAI-compatible execution where possible.
      - Configure DSPy optimization model calls through LiteLLM rather than direct provider-specific endpoints.
      - Verification: structured-output tests, DeepEval provider tests, DSPy provider tests.

  5. [x] Remove Obsolete Direct Ollama Runtime Paths
      - Remove or demote direct Ollama client/service wiring that is no longer used by production RAG/intelligence paths.
      - Keep Ollama only as a backend model provider behind LiteLLM, not as a Polaris application dependency boundary.
      - Verification: import audit confirms no application/intelligence/provider code directly depends on OllamaClient except transitional tests if explicitly retained.

  6. [x] Operational Readiness
      - Document required services and local startup flow.
      - Ensure logs and telemetry show LiteLLM failures without leaking API keys.
      - Verification: live smoke test with LiteLLM + Ollama running:
          - gateway health/model-list check
          - RAG structured routing call
          - RAG answer-generation call
          - DeepEval or Instructor narrow call if configured.

  7. [x] Final Regression and Documentation
      - Update RAG, LLM, and local setup documentation.
      - Run:
          - uv run ruff check .
          - uv run ruff format .
          - uv run mypy . --explicit-package-bases
          - focused LLM/RAG/provider tests
          - live LiteLLM smoke tests only when required services are confirmed running
          - uv run graphify update . after Python changes.

  ## Test Plan

  - Unit:
      - settings validation
      - LiteLLM gateway request/result mapping
      - JSON generation success/failure
      - timeout and provider-error normalization
      - telemetry attributes do not contain secrets

  - Integration:
      - Dishka composition resolves LiteLLM providers
      - RAG routing and quality providers use LiteLLM-backed model calls
      - Instructor structured output uses the LiteLLM endpoint
      - DeepEval/DSPy paths use LiteLLM-compatible model configuration

  - Live:
      - docker compose up -d litellm ollama
      - verify /v1/models
      - run a narrow RAG query through the gateway
      - confirm telemetry records provider/model/operation

  - Regression:
      - no remaining production direct-Ollama LLM calls
      - BGE embedding and reranking paths unchanged
      - no secrets in source, tests, docs, or plan files.

  ## Assumptions and Defaults

  - User-selected integration shape: proxy-first.
  - User-selected migration style: direct migration.
  - LiteLLM is the canonical LLM gateway; Polaris does not implement provider routing itself.
  - Existing Polaris model setting names remain the model identifiers sent to LiteLLM unless a later plan renames them to pure aliases.
  - Ollama remains useful as a local model backend but is no longer called directly by Polaris application/intelligence code.
  - LiteLLM proxy state is infrastructure state, not canonical Polaris business persistence.
  - This plan requires modifying core/llm or replacing it with an equivalent canonical boundary; obtain explicit core-modification authorization before implementation.

## Step Results
### Step 1 — Configuration and Compose

Status: completed.

What changed:
- Added canonical LiteLLM gateway settings to `config/settings.py`, including enablement, base URL, API key, timeout, strict-mode validation, URL normalization, and production/strict required-configuration checks.
- Added LiteLLM local-development environment placeholders to `.env.example` without including secret values.
- Added `config/litellm/config.yaml` with initial Ollama-backed model mappings for the current Polaris local model names: `qwen2.5:7b`, `qwen3.5:4b`, and `qwen3.5:9b`.
- Added a `litellm` Docker Compose service using the LiteLLM proxy image, mounted config, `LITELLM_MASTER_KEY` environment mapping from `POLARIS_LITELLM_API_KEY`, and `host.docker.internal` access for local Ollama.
- Added focused settings tests in `tests/unit/config/test_litellm_settings.py`.
- Reconciled the plan checklist format and restored the missing Step 6 heading so later execution remains aligned.

Key files touched:
- `config/settings.py`
- `.env.example`
- `config/litellm/config.yaml`
- `docker-compose.yml`
- `tests/unit/config/test_litellm_settings.py`
- `.agents/plans/plan_litellm_gateway_integration.md`

Verification commands run:
- `uv run ruff format config/settings.py tests/unit/config/test_litellm_settings.py`
- `uv run ruff check config/settings.py tests/unit/config/test_litellm_settings.py`
- `docker compose config --quiet`
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/config/test_litellm_settings.py tests/unit/config/test_ai_structured_output_settings.py tests/unit/config/test_deepeval_evaluation_settings.py tests/unit/config/test_rag_model_config.py`
- `UV_CACHE_DIR=/tmp/uv-cache uv run mypy config/settings.py tests/unit/config/test_litellm_settings.py --explicit-package-bases`

Pass/fail summary:
- Ruff format/check passed.
- Docker Compose configuration validation passed.
- Focused settings regression passed: 24 tests passed.
- Focused MyPy validation passed: no issues found in 2 source files.

Notes, recommendations, and service requirements:
- `config/settings.py` is a high-churn/high-risk configuration file, so Step 1 kept changes bounded to LiteLLM settings and validation only.
- No live LiteLLM container was started in this step; this step validated compose shape only.
- Live LiteLLM validation should wait until the operational smoke-test step and will require Ollama plus the LiteLLM service running.
- The LiteLLM config uses environment indirection for the master key; do not put API keys directly in config files, tests, docs, or plans.

Residual risks or deferred items:
- The actual OpenAI-compatible gateway client and provider migration are intentionally deferred to Step 2 and Step 3.
- LiteLLM model mapping may need adjustment during live validation if the proxy image expects a different Ollama provider string or if local model names differ from installed Ollama models.

### Step 2 — Canonical Gateway Client

Status: completed.

What changed:
- Added a canonical async LiteLLM gateway client boundary under `integration/clients/llm/` instead of modifying `core/`, keeping this step within the integration/client layer.
- Added immutable typed request/result/message contracts for LiteLLM chat, text generation, and JSON-object generation.
- Added sanitized response metadata extraction for requested model, response format, response id, finish reason, and token usage without exposing raw OpenAI SDK objects outside the client boundary.
- Added normalized client exceptions for general gateway failures, timeout failures, and malformed responses.
- Added `from_settings()` construction using `openai.AsyncOpenAI` against the configured LiteLLM OpenAI-compatible base URL.
- Added focused unit tests with a fake OpenAI-compatible chat-completions client.

Key files touched:
- `integration/clients/llm/__init__.py`
- `integration/clients/llm/litellm_gateway_client.py`
- `tests/unit/integration/clients/llm/test_litellm_gateway_client.py`
- `.agents/plans/plan_litellm_gateway_integration.md`

Verification commands run:
- `uv run ruff format integration/clients/llm tests/unit/integration/clients/llm`
- `uv run ruff check integration/clients/llm tests/unit/integration/clients/llm`
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/integration/clients/llm/test_litellm_gateway_client.py`
- `UV_CACHE_DIR=/tmp/uv-cache uv run mypy integration/clients/llm tests/unit/integration/clients/llm/test_litellm_gateway_client.py --explicit-package-bases`
- `uv run ruff format config/settings.py tests/unit/config/test_litellm_settings.py integration/clients/llm tests/unit/integration/clients/llm`
- `uv run ruff check config/settings.py tests/unit/config/test_litellm_settings.py integration/clients/llm tests/unit/integration/clients/llm`
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/config/test_litellm_settings.py tests/unit/integration/clients/llm/test_litellm_gateway_client.py`
- `UV_CACHE_DIR=/tmp/uv-cache uv run mypy config/settings.py tests/unit/config/test_litellm_settings.py integration/clients/llm tests/unit/integration/clients/llm/test_litellm_gateway_client.py --explicit-package-bases`
- `GRAPHIFY_VIZ_NODE_LIMIT=10000 uv run graphify update .`

Pass/fail summary:
- Ruff format/check passed.
- Focused LiteLLM gateway client tests passed: 6 tests passed.
- Combined LiteLLM settings and gateway-client regression passed: 11 tests passed.
- Focused MyPy validation passed for the gateway client and combined LiteLLM settings/client scope.
- Graphify update completed successfully; generated graph artifacts remain ignored by git.

Notes, recommendations, and service requirements:
- No live LiteLLM, Ollama, or external LLM service was required or started for this step.
- The client was intentionally built with an injected minimal OpenAI-compatible completion protocol, which keeps provider tests deterministic and avoids coupling downstream providers to raw SDK response objects.
- The client uses `POLARIS_LITELLM_API_KEY` when configured and a local placeholder key only for development client construction when the proxy does not require a master key. Do not put real API keys in source, tests, docs, or plans.

Residual risks or deferred items:
- DI wiring and production provider migration are intentionally deferred to Step 3.
- Live compatibility with the actual LiteLLM proxy and local Ollama model mappings remains deferred to the operational smoke-test step.
- Structured-output, DeepEval, and DSPy alignment remain deferred to Step 4.

### Step 3 — RAG LLM Provider Migration

Status: completed.

What changed:
- Added LiteLLM gateway-backed RAG query-routing and quality-evaluation providers, replacing production DI wiring that previously used the direct Ollama-backed providers.
- Added a LiteLLM gateway-backed RAG answer-generation provider for the non-structured answer provider boundary.
- Updated RAG DI wiring so `RagQueryRoutingService` and `RagQualityService` receive LiteLLM-backed providers.
- Added a request/app-scoped LiteLLM gateway client provider under the existing RAG client DI boundary.
- Rewired the Instructor structured-output provider construction to use the LiteLLM OpenAI-compatible endpoint through `openai.AsyncOpenAI`, so structured RAG final synthesis now reaches models through the gateway path instead of direct Ollama provider construction.
- Preserved the older direct Ollama provider modules for now as transitional code pending the later cleanup step that removes obsolete direct Ollama runtime paths.

Key files touched:
- `integration/clients/rag/di.py`
- `integration/providers/rag/di.py`
- `application/rag/di.py`
- `integration/providers/rag/litellm_query_routing_provider.py`
- `integration/providers/rag/litellm_quality_evaluation_provider.py`
- `integration/providers/rag/litellm_answer_generation_provider.py`
- `integration/providers/llm_structured_output/instructor_structured_output_provider.py`
- `tests/unit/integration/providers/rag/test_litellm_query_routing_provider.py`
- `tests/unit/integration/providers/rag/test_litellm_quality_evaluation_provider.py`
- `tests/unit/integration/providers/rag/test_litellm_answer_generation_provider.py`
- `tests/unit/integration/providers/llm_structured_output/test_instructor_structured_output_provider.py`
- `.agents/plans/plan_litellm_gateway_integration.md`

Verification commands run:
- `uv run ruff format integration/clients/rag/di.py integration/providers/rag/di.py application/rag/di.py integration/providers/rag/litellm_query_routing_provider.py integration/providers/rag/litellm_quality_evaluation_provider.py integration/providers/rag/litellm_answer_generation_provider.py integration/providers/llm_structured_output/instructor_structured_output_provider.py tests/unit/integration/providers/rag/test_litellm_query_routing_provider.py tests/unit/integration/providers/rag/test_litellm_quality_evaluation_provider.py tests/unit/integration/providers/rag/test_litellm_answer_generation_provider.py tests/unit/integration/providers/llm_structured_output/test_instructor_structured_output_provider.py`
- `uv run ruff check integration/clients/rag/di.py integration/providers/rag/di.py application/rag/di.py integration/providers/rag/litellm_query_routing_provider.py integration/providers/rag/litellm_quality_evaluation_provider.py integration/providers/rag/litellm_answer_generation_provider.py integration/providers/llm_structured_output/instructor_structured_output_provider.py tests/unit/integration/providers/rag/test_litellm_query_routing_provider.py tests/unit/integration/providers/rag/test_litellm_quality_evaluation_provider.py tests/unit/integration/providers/rag/test_litellm_answer_generation_provider.py tests/unit/integration/providers/llm_structured_output/test_instructor_structured_output_provider.py`
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/integration/providers/rag/test_litellm_query_routing_provider.py tests/unit/integration/providers/rag/test_litellm_quality_evaluation_provider.py tests/unit/integration/providers/rag/test_litellm_answer_generation_provider.py tests/unit/integration/providers/llm_structured_output/test_instructor_structured_output_provider.py tests/unit/application/rag/test_query_routing_service.py tests/unit/application/rag/test_rag_quality_service.py tests/unit/core/bootstrap/test_rag_di_composition.py`
- `UV_CACHE_DIR=/tmp/uv-cache uv run mypy integration/clients/rag/di.py integration/providers/rag/di.py application/rag/di.py integration/providers/rag/litellm_query_routing_provider.py integration/providers/rag/litellm_quality_evaluation_provider.py integration/providers/rag/litellm_answer_generation_provider.py integration/providers/llm_structured_output/instructor_structured_output_provider.py tests/unit/integration/providers/rag/test_litellm_query_routing_provider.py tests/unit/integration/providers/rag/test_litellm_quality_evaluation_provider.py tests/unit/integration/providers/rag/test_litellm_answer_generation_provider.py tests/unit/integration/providers/llm_structured_output/test_instructor_structured_output_provider.py --explicit-package-bases`
- `GRAPHIFY_VIZ_NODE_LIMIT=10000 uv run graphify update .`

Pass/fail summary:
- Ruff format/check passed.
- Focused RAG provider, structured-output, routing-service, quality-service, and DI-composition regression passed: 39 tests passed.
- Focused MyPy validation passed for the changed provider/client/DI/test scope.
- Graphify update completed successfully; generated graph artifacts remain ignored by git.

Notes, recommendations, and service requirements:
- No live LiteLLM, Ollama, PostgreSQL, Qdrant, Neo4j, or reranker service was required for this step; all verification used deterministic fakes.
- The application-facing RAG query and quality providers now emit integration telemetry with `provider_name="litellm"`, semantic operation, configured logical model, and request id attributes.
- Structured final answer generation remains schema-enforced through Instructor, but Instructor now uses the LiteLLM OpenAI-compatible gateway endpoint instead of direct Ollama provider construction.
- The direct Ollama provider modules are intentionally left in place until the explicit obsolete-path removal step so this step stays surgical and focused on production wiring.

Residual risks or deferred items:
- DeepEval and DSPy gateway alignment remain deferred to Step 4.
- Removal of direct Ollama runtime paths remains deferred to Step 5.
- Live gateway compatibility remains deferred to the operational readiness smoke-test step and will require LiteLLM plus at least one backend model service running.

### Step 4 — Structured Output, DeepEval, and DSPy Alignment

Status: completed.

What changed:
- Completed the remaining Step 4 alignment work for DeepEval and DSPy while preserving the Instructor LiteLLM endpoint change completed in Step 3.
- Extended `DeepEvalJudgeModelConfig` and `DeepEvalEvaluationProvider` so DeepEval's `LiteLLMModel` receives the canonical LiteLLM gateway base URL and optional API key from Polaris settings.
- Added canonical LiteLLM model-name normalization for DeepEval so unprefixed Polaris logical model names are routed through the OpenAI-compatible LiteLLM proxy as `openai/<model>`, while already-prefixed model names are preserved.
- Updated evaluation DI to pass `POLARIS_LITELLM_BASE_URL` and `POLARIS_LITELLM_API_KEY` into the DeepEval provider boundary.
- Updated the DSPy optimization provider to construct a `dspy.LM` against the LiteLLM OpenAI-compatible gateway, use that LM in DSPy context, and record non-secret gateway/model metadata in the serialized program manifest.
- Updated the CLI AI optimization default composition path so DSPy optimization receives LiteLLM settings from the request-scoped DI container.
- Added focused DeepEval and DSPy tests for LiteLLM base URL/API key propagation and canonical model-name normalization.

Key files touched:
- `integration/providers/llm_evaluation/deepeval_evaluation_provider.py`
- `application/evaluations/di.py`
- `integration/providers/ai_optimization/dspy_optimization_provider.py`
- `interfaces/cli/services/ai_command_service.py`
- `tests/unit/integration/providers/llm_evaluation/test_deepeval_evaluation_provider.py`
- `tests/unit/integration/providers/ai_optimization/test_dspy_optimization_provider.py`
- `.agents/plans/plan_litellm_gateway_integration.md`

Verification commands run:
- `uv run ruff format integration/providers/llm_evaluation/deepeval_evaluation_provider.py application/evaluations/di.py integration/providers/ai_optimization/dspy_optimization_provider.py interfaces/cli/services/ai_command_service.py tests/unit/integration/providers/llm_evaluation/test_deepeval_evaluation_provider.py tests/unit/integration/providers/ai_optimization/test_dspy_optimization_provider.py`
- `uv run ruff check integration/providers/llm_evaluation/deepeval_evaluation_provider.py application/evaluations/di.py integration/providers/ai_optimization/dspy_optimization_provider.py interfaces/cli/services/ai_command_service.py tests/unit/integration/providers/llm_evaluation/test_deepeval_evaluation_provider.py tests/unit/integration/providers/ai_optimization/test_dspy_optimization_provider.py`
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/integration/providers/llm_structured_output/test_instructor_structured_output_provider.py tests/unit/integration/providers/llm_evaluation/test_deepeval_evaluation_provider.py tests/unit/integration/providers/ai_optimization/test_dspy_optimization_provider.py tests/unit/application/ai_optimization/test_ai_optimization_service.py tests/unit/interfaces/cli/test_ai_command_service.py`
- `UV_CACHE_DIR=/tmp/uv-cache uv run mypy integration/providers/llm_evaluation/deepeval_evaluation_provider.py application/evaluations/di.py integration/providers/ai_optimization/dspy_optimization_provider.py interfaces/cli/services/ai_command_service.py tests/unit/integration/providers/llm_evaluation/test_deepeval_evaluation_provider.py tests/unit/integration/providers/ai_optimization/test_dspy_optimization_provider.py --explicit-package-bases`
- `GRAPHIFY_VIZ_NODE_LIMIT=10000 uv run graphify update .`

Pass/fail summary:
- Ruff format/check passed.
- Focused Step 4 regression passed: 33 tests passed.
- Focused MyPy validation passed: no issues found in 6 source files.
- Graphify update completed successfully; generated graph artifacts remain ignored by git.

Notes, recommendations, and service requirements:
- No live LiteLLM, Ollama, DeepEval, DSPy, or external LLM service was required or started for this step; tests used local unit seams and constructors only.
- DSPy still emits upstream deprecation warnings from its own package internals during import/use; these are non-fatal and outside Polaris source.
- The DeepEval `LiteLLMModel` path uses the LiteLLM Python client pointed at the LiteLLM proxy, so Polaris now supplies `base_url`, optional API key, and an `openai/` provider prefix for unprefixed logical model names.
- API keys were not written to source, tests, docs, or the plan; tests use non-secret placeholder strings only.

Residual risks or deferred items:
- Live compatibility with the actual LiteLLM proxy, local Ollama backend, DeepEval judge calls, and DSPy model calls remains deferred to the operational readiness smoke-test step.
- Obsolete direct Ollama runtime paths are intentionally retained until Step 5, where they will be removed or demoted after an import audit.

### Step 5 — Remove Obsolete Direct Ollama Runtime Paths

Status: completed after Step 5B core LiteLLM boundary authorization and implementation.

What changed:
- Removed the obsolete direct-Ollama RAG provider modules now replaced by LiteLLM-backed providers.
- Removed the obsolete direct-Ollama RAG provider unit tests.
- Removed direct DeepEval Ollama judge-provider support from the Polaris evaluation provider boundary. DeepEval now uses the canonical LiteLLM/OpenAI-compatible judge-provider path for local models.
- Removed the DeepEval Ollama base-url setting and direct Ollama app placeholders from `.env.example`.
- Updated evaluation DI so DeepEval no longer receives Ollama-specific configuration.
- Updated evaluation/provider/CLI tests so LiteLLM is the canonical configured judge provider.

Key files touched:
- `.env.example`
- `application/evaluations/di.py`
- `config/settings.py`
- `integration/providers/llm_evaluation/deepeval_evaluation_provider.py`
- `integration/providers/rag/ollama_answer_generation_provider.py`
- `integration/providers/rag/ollama_query_routing_provider.py`
- `integration/providers/rag/ollama_quality_evaluation_provider.py`
- `tests/unit/config/test_deepeval_evaluation_settings.py`
- `tests/unit/integration/providers/llm_evaluation/test_deepeval_evaluation_provider.py`
- `tests/unit/integration/providers/rag/test_ollama_query_routing_provider.py`
- `tests/unit/integration/providers/rag/test_ollama_quality_evaluation_provider.py`
- `tests/unit/interfaces/cli/test_ai_command_service.py`
- `tests/unit/interfaces/cli/test_evaluation_command.py`
- `tests/unit/interfaces/cli/test_evaluation_command_service.py`

Verification commands run:
- `uv run ruff format application/evaluations/di.py config/settings.py integration/providers/llm_evaluation/deepeval_evaluation_provider.py tests/unit/config/test_deepeval_evaluation_settings.py tests/unit/integration/providers/llm_evaluation/test_deepeval_evaluation_provider.py tests/unit/interfaces/cli/test_evaluation_command.py tests/unit/interfaces/cli/test_evaluation_command_service.py tests/unit/interfaces/cli/test_ai_command_service.py`
- `uv run ruff check application/evaluations/di.py config/settings.py integration/providers/llm_evaluation/deepeval_evaluation_provider.py tests/unit/config/test_deepeval_evaluation_settings.py tests/unit/integration/providers/llm_evaluation/test_deepeval_evaluation_provider.py tests/unit/interfaces/cli/test_evaluation_command.py tests/unit/interfaces/cli/test_evaluation_command_service.py tests/unit/interfaces/cli/test_ai_command_service.py`
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/config/test_deepeval_evaluation_settings.py tests/unit/integration/providers/llm_evaluation/test_deepeval_evaluation_provider.py tests/unit/integration/providers/rag/test_litellm_query_routing_provider.py tests/unit/integration/providers/rag/test_litellm_quality_evaluation_provider.py tests/unit/integration/providers/rag/test_litellm_answer_generation_provider.py tests/unit/interfaces/cli/test_evaluation_command.py tests/unit/interfaces/cli/test_evaluation_command_service.py tests/unit/interfaces/cli/test_ai_command_service.py`
- `UV_CACHE_DIR=/tmp/uv-cache uv run mypy application/evaluations/di.py config/settings.py integration/providers/llm_evaluation/deepeval_evaluation_provider.py tests/unit/config/test_deepeval_evaluation_settings.py tests/unit/integration/providers/llm_evaluation/test_deepeval_evaluation_provider.py tests/unit/interfaces/cli/test_evaluation_command.py tests/unit/interfaces/cli/test_evaluation_command_service.py tests/unit/interfaces/cli/test_ai_command_service.py --explicit-package-bases`
- `GRAPHIFY_VIZ_NODE_LIMIT=10000 uv run graphify update .`
- Import audit: `grep -R "OllamaClient\|OllamaRag\|DEEPEVAL_OLLAMA\|ollama_base_url" -n application integration interfaces config tests/unit intelligence core --exclude-dir=__pycache__ --exclude='*.pyc'`

Pass/fail summary:
- Ruff format/check passed.
- Focused provider/config/CLI regression passed: 50 tests passed, 1 upstream deprecation warning from `websockets.legacy`.
- Focused MyPy validation passed: no issues found in 8 source files.
- Graphify update completed successfully.
- Import audit passed for `application/`, `integration/`, `interfaces/`, `config/`, `tests/unit/`, and `intelligence/` direct references to `OllamaClient`, `OllamaRag`, `DEEPEVAL_OLLAMA`, and `ollama_base_url`.

Notes, recommendations, and service requirements:
- No live LiteLLM, Ollama, PostgreSQL, Qdrant, Neo4j, or reranker service was required for this cleanup step.
- Ollama remains valid only as a backend model provider behind LiteLLM; the removed DeepEval direct-Ollama path should be replaced operationally by `DEEPEVAL_JUDGE_PROVIDER=litellm` with LiteLLM routing to local Ollama when desired.
- The remaining direct Ollama runtime path is in `core/llm`: `core/llm/ollama_client.py`, `core/llm/di.py`, and `core/llm/llm_service.py`. Intelligence agents still depend on `core.llm.llm_service.LLMService`, which is backed by `OllamaClient`.

Residual risks or deferred items:
- The initial Step 5 pass left the production-intelligence LLM boundary blocked until explicit `core/` authorization was granted. That remaining work was completed in Step 5B below.

### Step 5B — Core LiteLLM LLM Boundary Completion

Status: completed.

What changed:
- Added a typed async core `LLMGateway` protocol with immutable text and JSON result contracts so core LLM consumers depend on a stable boundary rather than a vendor-specific client.
- Refactored `core.llm.LLMService` to be async and gateway-backed; it now returns typed text or JSON results through the `LLMGateway` abstraction.
- Refactored `CoreLLMsDIProvider` to receive the gateway through Dishka instead of constructing an `OllamaClient`.
- Removed `core/llm/ollama_client.py` and removed `Settings.OLLAMA_HOST`; Ollama is now only a LiteLLM backend, not a Polaris core application dependency.
- Added `LiteLlmCoreGatewayAdapter` in the integration client layer to adapt the canonical `LiteLlmGatewayClient` to the core `LLMGateway` protocol.
- Moved the canonical `LiteLlmGatewayClient` provider into `IntegrationClientsDIProvider` and removed duplicate RAG-client provisioning.
- Updated fundamental, technical, news, and sentiment intelligence agents to await the async `LLMService.chat()` path.
- Updated intelligence test fakes and service stabilization tests to use async LLM fakes.
- Added focused unit tests for `LLMService` and the LiteLLM core-gateway adapter.

Key files touched:
- `core/llm/llm_gateway.py`
- `core/llm/llm_service.py`
- `core/llm/di.py`
- `core/llm/ollama_client.py`
- `integration/clients/llm/core_gateway_adapter.py`
- `integration/clients/llm/litellm_gateway_client.py`
- `integration/clients/llm/__init__.py`
- `integration/clients/di.py`
- `integration/clients/rag/di.py`
- `config/settings.py`
- `intelligence/analysts/fundamental/fundamental_agent.py`
- `intelligence/analysts/technical/technical_agent.py`
- `intelligence/research/news/news_agent.py`
- `intelligence/research/sentiment/sentiment_agent.py`
- `tests/unit/core/llm/test_llm_service.py`
- `tests/unit/integration/clients/llm/test_core_gateway_adapter.py`
- `tests/unit/intelligence/analysts/fundamental/test_fundamental_agent.py`
- `tests/unit/intelligence/analysts/technical/test_technical_agent.py`
- `tests/unit/intelligence/research/test_news_sentiment_output_contracts.py`
- `tests/unit/application/services/test_service_stabilization.py`

Verification commands run:
- `uv run ruff format core/llm integration/clients/llm integration/clients/di.py integration/clients/rag/di.py intelligence/analysts/fundamental/fundamental_agent.py intelligence/analysts/technical/technical_agent.py intelligence/research/news/news_agent.py intelligence/research/sentiment/sentiment_agent.py tests/unit/core/llm tests/unit/integration/clients/llm tests/unit/intelligence/analysts/fundamental/test_fundamental_agent.py tests/unit/intelligence/analysts/technical/test_technical_agent.py tests/unit/intelligence/research/test_news_sentiment_output_contracts.py tests/unit/application/services/test_service_stabilization.py config/settings.py`
- `uv run ruff check core/llm integration/clients/llm integration/clients/di.py integration/clients/rag/di.py intelligence/analysts/fundamental/fundamental_agent.py intelligence/analysts/technical/technical_agent.py intelligence/research/news/news_agent.py intelligence/research/sentiment/sentiment_agent.py tests/unit/core/llm tests/unit/integration/clients/llm tests/unit/intelligence/analysts/fundamental/test_fundamental_agent.py tests/unit/intelligence/analysts/technical/test_technical_agent.py tests/unit/intelligence/research/test_news_sentiment_output_contracts.py tests/unit/application/services/test_service_stabilization.py config/settings.py`
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/core/llm/test_llm_service.py tests/unit/integration/clients/llm/test_litellm_gateway_client.py tests/unit/integration/clients/llm/test_core_gateway_adapter.py tests/unit/intelligence/analysts/fundamental/test_fundamental_agent.py tests/unit/intelligence/analysts/technical/test_technical_agent.py tests/unit/intelligence/research/test_news_sentiment_output_contracts.py tests/unit/application/services/test_service_stabilization.py tests/unit/core/bootstrap/test_rag_di_composition.py`
- `UV_CACHE_DIR=/tmp/uv-cache uv run mypy core/llm integration/clients/llm integration/clients/di.py integration/clients/rag/di.py intelligence/analysts/fundamental/fundamental_agent.py intelligence/analysts/technical/technical_agent.py intelligence/research/news/news_agent.py intelligence/research/sentiment/sentiment_agent.py tests/unit/core/llm/test_llm_service.py tests/unit/integration/clients/llm/test_core_gateway_adapter.py tests/unit/intelligence/analysts/fundamental/test_fundamental_agent.py tests/unit/intelligence/analysts/technical/test_technical_agent.py tests/unit/intelligence/research/test_news_sentiment_output_contracts.py tests/unit/application/services/test_service_stabilization.py --explicit-package-bases`
- `grep -R "from core.llm.ollama_client\|core.llm.ollama_client\|OllamaClient\|OLLAMA_HOST\|DEEPEVAL_OLLAMA" -n application integration interfaces config tests/unit intelligence core --exclude-dir=__pycache__ --exclude='*.pyc' || true`
- `GRAPHIFY_VIZ_NODE_LIMIT=10000 uv run graphify update .`

Pass/fail summary:
- Ruff format/check passed.
- Focused LLM, LiteLLM adapter, intelligence-agent, stabilization, and RAG DI regression tests passed: 40 tests passed, 1 upstream `websockets.legacy` deprecation warning.
- Focused MyPy validation passed: no issues found in 22 source files.
- Direct core Ollama import/config audit passed for targeted source and unit-test paths.
- Graphify update completed successfully.

Notes, recommendations, and service requirements:
- No live LiteLLM, Ollama, PostgreSQL, Qdrant, Neo4j, or reranker service was required for Step 5B; verification used fakes and DI composition tests.
- Ollama may still appear in LiteLLM configuration as a backend provider target and in test fixture metadata; that is expected because LiteLLM owns provider/model routing.
- Live LiteLLM + Ollama smoke validation remains the responsibility of Step 6.

Residual risks or deferred items:
- Step 6 should verify the actual LiteLLM proxy and local model backend are reachable and that RAG/intelligence calls succeed through the gateway under live conditions.

### Step 6 — Operational Readiness

Status: completed with one documented local-service requirement.

What changed:
- Added `docs/litellm_gateway.md` documenting the LiteLLM proxy architecture, required local services, startup flow, configuration, health checks, local smoke validation, and failure/observability behavior.
- Updated `.env.example` with `POLARIS_LITELLM_OLLAMA_API_BASE` so Docker-based LiteLLM can be pointed at a container-reachable Ollama endpoint without editing source-controlled LiteLLM config.
- Updated `config/litellm/config.yaml` to read the Ollama backend URL from `POLARIS_LITELLM_OLLAMA_API_BASE` instead of hard-coding `host.docker.internal:11434`.
- Updated the `litellm` Docker Compose service to pass `POLARIS_LITELLM_OLLAMA_API_BASE` with a local-development default.
- Updated `docs/llm_evaluation.md` so local DeepEval judging is documented through the canonical LiteLLM/OpenAI-compatible path rather than the removed direct-Ollama path.
- Added a focused gateway-client regression test proving provider exception messages are normalized without leaking lower-level sensitive values into the public `LiteLlmGatewayError` message.

Key files touched:
- `.env.example`
- `config/litellm/config.yaml`
- `docker-compose.yml`
- `docs/litellm_gateway.md`
- `docs/llm_evaluation.md`
- `tests/unit/integration/clients/llm/test_litellm_gateway_client.py`
- `.agents/plans/plan_litellm_gateway_integration.md`

Verification commands run:
- `docker compose ps litellm --format json`
- `curl http://localhost:11434/api/tags`
- `docker compose up -d litellm`
- `POLARIS_LITELLM_API_KEY=polaris-local-dev-key docker compose up -d --force-recreate litellm`
- `docker compose exec -T litellm python - <<'PY' ... http://host.docker.internal:11435/api/tags ... PY`
- `POLARIS_LITELLM_ENABLED=true POLARIS_LITELLM_API_KEY=polaris-local-dev-key POLARIS_STRUCTURED_OUTPUT_PROVIDER=instructor POLARIS_STRUCTURED_OUTPUT_MODEL=qwen2.5:7b UV_CACHE_DIR=/tmp/uv-cache timeout 90s uv run python /tmp/litellm_step6_smoke.py`
- `POLARIS_LITELLM_API_KEY=polaris-local-dev-key docker compose up -d --force-recreate litellm`
- `UV_CACHE_DIR=/tmp/uv-cache uv run python - <<'PY' ... /v1/models ... PY`
- `uv run ruff format tests/unit/integration/clients/llm/test_litellm_gateway_client.py`
- `uv run ruff check tests/unit/integration/clients/llm/test_litellm_gateway_client.py config/settings.py integration/clients/llm`
- `docker compose config --quiet`
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/integration/clients/llm/test_litellm_gateway_client.py`
- `UV_CACHE_DIR=/tmp/uv-cache uv run mypy tests/unit/integration/clients/llm/test_litellm_gateway_client.py --explicit-package-bases`
- `GRAPHIFY_VIZ_NODE_LIMIT=10000 uv run graphify update .`

Pass/fail summary:
- LiteLLM container startup passed.
- LiteLLM `/v1/models` passed with the local development API key and returned the configured model aliases: `qwen2.5:7b`, `qwen3.5:4b`, and `qwen3.5:9b`.
- Live LiteLLM + Ollama smoke validation passed using the configured `qwen2.5:7b` model through the LiteLLM gateway:
  - gateway model-list check passed
  - RAG structured route-selection provider call passed with JSON keys `reason` and `route`
  - RAG answer-generation provider call passed
  - Instructor structured-output call passed with a schema-validated response
- Ruff format/check passed after rerunning with the correct Python-file scope. An initial check command incorrectly included YAML files and failed because Ruff parsed `docker-compose.yml` as Python; no code issue was found.
- Docker Compose configuration validation passed.
- Focused LiteLLM gateway-client regression passed: 7 tests passed.
- Focused MyPy validation passed for the updated gateway-client test file.
- Graphify update completed successfully.

Notes, recommendations, and service requirements:
- Host Ollama is currently listening on `127.0.0.1:11434`, which means a Docker container cannot reach it through `host.docker.internal:11434`. Direct backend calls from the LiteLLM container failed until a temporary host TCP bridge exposed Ollama on a container-reachable address.
- The temporary TCP bridge was used only for the live smoke test, then stopped. The LiteLLM container was recreated afterward with the default Compose environment.
- For durable local operation, start Ollama with `OLLAMA_HOST=0.0.0.0:11434` or set `POLARIS_LITELLM_OLLAMA_API_BASE` to another endpoint that is reachable from the LiteLLM container.
- `qwen3.5:4b` is available through LiteLLM, but the narrow live provider smoke used `qwen2.5:7b` because the local `qwen3.5:4b` thinking-model path was slower and produced reasoning-heavy responses under short smoke constraints. Full default-model tuning remains a runtime/model-operations concern, not a gateway wiring issue.
- Failure visibility was improved at the client boundary: lower-level provider exceptions are normalized and do not leak provider secret values through the public exception message.

Residual risks or deferred items:
- Step 7 should run the broader final regression gate and update any remaining setup/RAG documentation.
- If the project wants `qwen3.5:4b` as the default live local model for all RAG generation paths, a follow-up model-operations pass should tune prompts, max-token budgets, or model aliases so smoke tests do not depend on the faster `qwen2.5:7b` alias.
- Docker LiteLLM backend calls will fail again until Ollama is made reachable from Docker as described above.

### Step 7 — Final Regression and Documentation

Status: completed.

What changed:
- Updated final RAG and setup documentation so LiteLLM is documented as the canonical LLM gateway and Ollama is described only as a possible backend behind LiteLLM.
- Updated DeepEval live-test documentation to route local model judging through `POLARIS_DEEPEVAL_JUDGE_PROVIDER=litellm` and the LiteLLM OpenAI-compatible endpoint instead of the removed direct-Ollama setting.
- Updated local setup documentation to include the `litellm` Docker Compose service and the required Docker-to-host Ollama reachability note.
- Updated the evaluation test README so live DeepEval instructions match the new LiteLLM-backed judge path.

Key files touched:
- `README.md`
- `docs/platform_rag_pipeline.md`
- `docs/llm_evaluation.md`
- `docs/testing_guide.md`
- `tests/evaluation/README.md`
- `.agents/plans/plan_litellm_gateway_integration.md`

Verification commands run:
- `rg -n "DEEPEVAL_OLLAMA|OllamaClient|Ollama-compatible endpoints|Start Ollama separately|Ollama \|" README.md docs tests/evaluation/README.md .env.example config/settings.py tests`
- `uv run ruff format .`
- `uv run ruff check .`
- `UV_CACHE_DIR=/tmp/uv-cache uv run mypy . --explicit-package-bases`
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/config/test_litellm_settings.py tests/unit/core/llm/test_llm_service.py tests/unit/integration/clients/llm/test_litellm_gateway_client.py tests/unit/integration/clients/llm/test_core_gateway_adapter.py tests/unit/integration/providers/rag/test_litellm_query_routing_provider.py tests/unit/integration/providers/rag/test_litellm_quality_evaluation_provider.py tests/unit/integration/providers/rag/test_litellm_answer_generation_provider.py tests/unit/integration/providers/llm_structured_output/test_instructor_structured_output_provider.py tests/unit/integration/providers/llm_evaluation/test_deepeval_evaluation_provider.py tests/unit/integration/providers/ai_optimization/test_dspy_optimization_provider.py tests/unit/application/rag/test_query_routing_service.py tests/unit/application/rag/test_rag_quality_service.py tests/unit/core/bootstrap/test_rag_di_composition.py tests/unit/intelligence/analysts/fundamental/test_fundamental_agent.py tests/unit/intelligence/analysts/technical/test_technical_agent.py tests/unit/intelligence/research/test_news_sentiment_output_contracts.py`
- `UV_CACHE_DIR=/tmp/uv-cache uv run python - <<'PY' ... LiteLLM /v1/models ... PY`
- `docker compose exec -T litellm python - <<'PY' ... socket check host.docker.internal:11434 ... PY`
- `GRAPHIFY_VIZ_NODE_LIMIT=10000 uv run graphify update .`
- `git diff --check`

Pass/fail summary:
- Documentation audit for obsolete direct-Ollama DeepEval/runtime references passed for the targeted docs, config, and tests scope.
- Ruff format passed: 1362 files left unchanged.
- Ruff check passed for the full repository.
- Full MyPy passed: no issues found in 1359 source files.
- Focused LiteLLM, LLM, RAG provider, structured-output, DeepEval, DSPy, RAG service, DI, and intelligence-agent regression passed: 82 tests passed.
- The focused test run reported only upstream/dependency deprecation warnings from `websockets.legacy` and DSPy internals.
- LiteLLM `/v1/models` live health passed and returned `qwen2.5:7b`, `qwen3.5:4b`, and `qwen3.5:9b`.
- Full live backend-generation smoke was not rerun in Step 7 because the LiteLLM container still cannot reach host Ollama at the default `host.docker.internal:11434`; the socket check failed with `ConnectionRefusedError`. Step 6 already proved the gateway/provider path with a temporary container-reachable bridge.
- Graphify update passed and reported no code-graph topology changes.
- `git diff --check` passed.

Notes, recommendations, and service requirements:
- Durable local live generation requires making the model backend reachable from the LiteLLM container. For host Ollama, start it with `OLLAMA_HOST=0.0.0.0:11434` or set `POLARIS_LITELLM_OLLAMA_API_BASE` to another container-reachable endpoint before running live generation or live DeepEval.
- The remaining warnings are from third-party packages and do not indicate Polaris source failures.
- No PostgreSQL, Qdrant, Neo4j, BGE reranker, Langfuse, Prometheus, Jaeger, or Grafana live test was required for this final LiteLLM regression gate.

Residual risks or deferred items:
- Live generation will fail in the current local Docker configuration until the Ollama reachability requirement is satisfied.
- If the team wants the default local generation smoke to use `qwen3.5:4b`, a follow-up model-operations pass should tune the local model alias, prompts, and max-token settings to account for its reasoning-heavy output behavior.
