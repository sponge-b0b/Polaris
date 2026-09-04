# Audit: Current Polaris Model Alias and `qwen3.5` Usage

Issue: https://github.com/sponge-b0b/Polaris/issues/5
Date: 2026-07-19

## Question

Where does Polaris currently bind logical model aliases to concrete models, and which runtime, RAG, strategy, evaluation, Langfuse, DeepEval, LiteLLM, and documentation paths would be affected by replacing `qwen3.5:4b`?

This audit classifies each occurrence as an architectural default, deployment config, test fixture, documentation, or stale/historical reference.

## Method

Commands and tools used:

- `gh issue view 5 --json ...`
- Repowise `get_answer(...)` for repository-local architecture discovery. Result was low confidence because the Repowise index was behind the current HEAD and semantic embeddings were degraded, so source inspection and grep were used as authoritative verification.
- Graphify query for model-alias topology and related LLM/RAG paths.
- `git grep` for `qwen3.5`, `qwen3.5:4b`, `qwen2.5`, `deepseek-r1`, `polaris-local-*`, `RAG_*_MODEL`, `DEFAULT_LITELLM_*`, `STRUCTURED_OUTPUT_MODEL`, `DEEPEVAL_JUDGE_MODEL`, and `DSPY_OPTIMIZATION_MODEL`.
- Direct inspection of `config/settings.py`, `config/rag_model_config.py`, `config/litellm/config.yaml`, `core/llm/llm_service.py`, `core/llm/di.py`, and `integration/clients/llm/litellm_gateway_client.py`.

## Executive finding

Polaris already has the correct architectural separation for local model operations:

```text
Polaris source defaults
→ logical aliases in Settings / RAG model config
→ LiteLLM deployment config
→ concrete Ollama model names
```

The only live concrete `qwen3.5:4b` binding that changes runtime model behavior is in `config/litellm/config.yaml`, where:

- `polaris-local-reasoning` maps to `ollama_chat/qwen3.5:4b`
- `polaris-local-synthesis` maps to `ollama_chat/qwen3.5:4b`
- `qwen3.5:4b` exists as a direct diagnostic/operator override alias

Production Python source defaults do **not** hard-code `qwen3.5:4b`. They use logical aliases such as `polaris-local-reasoning`, `polaris-local-synthesis`, `polaris-local-structured`, and `polaris-local-evaluation`.

## Canonical owner boundaries

| Boundary | Current owner | What it owns | Concrete model names? | Replacement impact |
|---|---|---|---:|---|
| Architectural source defaults | `config/settings.py` | Default logical Polaris model aliases and per-capability env vars | No | Usually no source change required if aliases remain stable. |
| RAG per-stage model contract | `config/rag_model_config.py` | Typed RAG model configuration derived from `Settings` | No | RAG behavior changes when the alias binding changes in LiteLLM or env vars override aliases. |
| LiteLLM deployment mapping | `config/litellm/config.yaml` | Concrete local backend binding for logical aliases | Yes | Primary file to change when replacing `qwen3.5:4b`. |
| Core LLM service | `core/llm/llm_service.py`, `core/llm/di.py` | Model-agnostic gateway service using `settings.DEFAULT_MODEL` | No direct `qwen3.5` default | Affected indirectly if `DEFAULT_MODEL=polaris-local-synthesis` changes backend binding. |
| LiteLLM gateway client | `integration/clients/llm/litellm_gateway_client.py` | OpenAI-compatible transport to LiteLLM | No direct `qwen3.5` default | Affected only by configured model strings passed into requests. |
| Structured output | `integration/providers/llm_structured_output/...` and `POLARIS_STRUCTURED_OUTPUT_MODEL` | Instructor structured-output provider | No default `qwen3.5` | Currently defaults to `polaris-local-structured`, which maps to `qwen2.5:7b`. |
| DeepEval | `application/evaluations/...`, `integration/providers/llm_evaluation/...`, `POLARIS_DEEPEVAL_JUDGE_MODEL` | Evaluation run orchestration and judge model construction | No default `qwen3.5` | Currently env-driven; `.env.example` uses `polaris-local-evaluation`, which maps to `qwen2.5:7b`. |
| Langfuse | `application/observability/...` and RAG observability mappers | Observes and exports actual model names/observations | No default `qwen3.5` | Records whatever model was used; replacement changes observed model metadata, not Langfuse behavior. |
| Strategy/intelligence agents | `intelligence/...` | Domain strategy analysis and LLM telemetry tagging | No direct model names found | Affected only through injected `LLMService`/providers and their logical model settings. |
| Documentation | `docs/litellm_gateway.md`, `docs/platform_rag_pipeline.md` | Public architecture/operator docs | Mentions `qwen3.5:4b` | Must be updated after the final model allocation decision. |
| Historical plans/research | `.agents/plans/...`, `.agents/research/...` | Historical context and prior decision records | Yes | Do not treat as active defaults; append superseding notes only if needed. |
| Tests | `tests/...` | Fixtures, pass-through, persistence, and config override tests | Yes | Most literals are test data proving model strings pass through; not runtime defaults. Cleanup is optional to reduce confusion. |

## Current logical alias graph

### Source defaults

`config/settings.py` defines source-level architectural defaults as logical aliases:

| Setting/default | Current source default | Role |
|---|---|---|
| `DEFAULT_MODEL` | `polaris-local-synthesis` | Core LLM service default. |
| `DEFAULT_LITELLM_FAST_MODEL` | `polaris-local-fast` | Fast/simple tasks. |
| `DEFAULT_LITELLM_REASONING_MODEL` | `polaris-local-reasoning` | Reasoning-heavy tasks. |
| `DEFAULT_LITELLM_SYNTHESIS_MODEL` | `polaris-local-synthesis` | Synthesis/generation tasks. |
| `DEFAULT_LITELLM_STRUCTURED_MODEL` | `polaris-local-structured` | Structured JSON/schema tasks. |
| `DEFAULT_LITELLM_EVALUATION_MODEL` | `polaris-local-evaluation` | DeepEval judge default via env. |
| `DEFAULT_LITELLM_OPTIMIZATION_MODEL` | `polaris-local-optimization` | DSPy optimization model. |

### RAG model stages

`config/rag_model_config.py` derives the typed `RagModelConfig` from `Settings`:

| RAG stage | Setting | Current default alias |
|---|---|---|
| Query rewrite | `RAG_QUERY_REWRITE_MODEL` | `polaris-local-fast` |
| Adaptive triage | `RAG_ADAPTIVE_TRIAGE_MODEL` | `polaris-local-fast` |
| Route selection | `RAG_ROUTE_SELECTION_MODEL` | `polaris-local-structured` |
| HyDE generation | `RAG_HYDE_MODEL` | `polaris-local-reasoning` |
| CRAG grading | `RAG_CRAG_GRADER_MODEL` | `polaris-local-structured` |
| CRAG rewrite | `RAG_CRAG_QUERY_REWRITE_MODEL` | `polaris-local-structured` |
| Self-RAG reflection | `RAG_SELF_REFLECTION_MODEL` | `polaris-local-structured` |
| Final answer synthesis | `RAG_SYNTHESIS_MODEL` | `polaris-local-synthesis` |
| Embeddings | `RAG_HYBRID_EMBEDDING_MODEL` | `BAAI/bge-m3` |
| Reranking | `RAG_RERANKER_MODEL` | `BAAI/bge-reranker-large` |

## Concrete `qwen3.5:4b` bindings and classifications

### Deployment config — active runtime impact

`config/litellm/config.yaml` contains the active concrete deployment binding:

| Logical alias | Current concrete backend | Classification | Replacement action |
|---|---|---|---|
| `polaris-local-reasoning` | `ollama_chat/qwen3.5:4b` | Deployment config | Change here if replacing the reasoning backend. |
| `polaris-local-synthesis` | `ollama_chat/qwen3.5:4b` | Deployment config | Change here if replacing the synthesis backend. |
| `qwen3.5:4b` | `ollama_chat/qwen3.5:4b` | Direct diagnostic/operator override alias | Optional to keep for diagnostics; remove only if direct operator override should disappear. |

`qwen3.5:9b` is also present only as a direct diagnostic/operator override alias in the same file.

### Architectural defaults — no active concrete qwen3.5 binding

`config/settings.py` does not hard-code `qwen3.5:4b`. It hard-codes logical aliases and RAG model constants. Therefore, replacing the concrete qwen3.5 backend should not require changing `Settings` unless the logical alias taxonomy itself changes.

### Runtime and intelligence — indirect impact only

No direct `qwen`, `qwen3.5`, or `polaris-local-*` literals were found in `intelligence/`, `application/services/`, `workflows/`, or `interfaces/cli/` production code.

The runtime and intelligence layers are affected indirectly:

- `CoreLLMsDIProvider` injects `LLMService(model=settings.DEFAULT_MODEL)`.
- `settings.DEFAULT_MODEL` defaults to `polaris-local-synthesis`.
- Intelligence agents that use `LLMService` therefore follow the concrete backend bound to `polaris-local-synthesis` in LiteLLM.
- Strategy/intelligence code is not currently coupled directly to `qwen3.5:4b`.

### RAG — indirect impact through aliases

RAG uses typed model settings and model-execution metadata, not concrete defaults in source:

- `RAG_HYDE_MODEL=polaris-local-reasoning` is currently the main RAG path affected by replacing qwen3.5 if the LiteLLM alias stays mapped to qwen3.5.
- `RAG_SYNTHESIS_MODEL=polaris-local-synthesis` is the other main path affected.
- CRAG grading, CRAG rewrite, self-reflection, route selection, and structured-output paths currently default to `polaris-local-structured`, which maps to `qwen2.5:7b` in LiteLLM.
- RAG observability records `configured_model` / `generation_model` metadata; it does not choose qwen3.5 itself.

### Evaluation and DeepEval — mostly env-driven or fixture-only

DeepEval receives `judge_model` from `settings.DEEPEVAL_JUDGE_MODEL`. `.env.example` sets:

```text
POLARIS_DEEPEVAL_JUDGE_MODEL=polaris-local-evaluation
```

The active local LiteLLM deployment maps `polaris-local-evaluation` to `qwen2.5:7b`, not qwen3.5.

`qwen3.5:4b` appears frequently in evaluation tests as fixture data for `evaluator_model`, persistence, telemetry, and provider pass-through behavior. These are not architectural defaults.

### Langfuse — observation metadata only

Langfuse code exports AI observations, generations, scores, and evaluation data using observed model fields such as `model_name` and `evaluator_model`. It does not own the model-selection decision. Replacing `qwen3.5:4b` changes the metadata Langfuse receives when a run uses a different backend, but no Langfuse architecture changes are required.

### Documentation — update after final decision

Documentation contains active explanatory references:

- `docs/litellm_gateway.md` explains that logical aliases map through `config/litellm/config.yaml` to concrete Ollama backends such as `qwen2.5:7b` or `qwen3.5:4b`.
- `docs/platform_rag_pipeline.md` states that reasoning/synthesis currently map to `qwen3.5:4b` and includes `ollama pull qwen3.5:4b` in setup instructions.

These should be updated after the final replacement decision is made.

### Historical/stale references

The following files contain historical plan or research context, not current source-of-truth runtime defaults:

- `.agents/plans/plan_litellm_gateway_integration.md`
- `.agents/plans/plan_platform_rag_pipeline_master.md`
- `.agents/plans/plan_rag_model_configuration.md`
- `.agents/research/local_model_capabilities_constraints_issue_4.md`

Notably, `.agents/plans/plan_rag_model_configuration.md` still shows older concrete qwen3.5 defaults for several RAG stages. Current source no longer follows that old concrete-default design; it uses logical aliases in `config/settings.py` and concrete deployment mapping in `config/litellm/config.yaml`.

### Test fixtures

`qwen3.5:4b` appears in many tests as a sample model identifier. These test literals fall into several fixture categories:

- Core LLM pass-through fixtures: `tests/unit/core/llm/test_llm_service.py`
- LiteLLM client/gateway pass-through fixtures: `tests/unit/integration/clients/llm/...`
- Structured-output provider fixtures: `tests/unit/integration/providers/llm_structured_output/...`
- RAG structured generation provider fixtures: `tests/unit/integration/providers/rag/test_structured_answer_generation_provider.py`
- DeepEval/evaluation service and CLI fixtures: `tests/unit/application/evaluations/...`, `tests/unit/interfaces/cli/test_evaluation_command_service.py`, `tests/unit/interfaces/cli/test_ai_command_service.py`
- Langfuse/AI-observability fixtures: `tests/unit/application/observability/...`
- Persistence fixtures: `tests/integration/core/storage/persistence/test_postgres_ai_artifact_persistence_repository.py`, `tests/unit/core/storage/persistence/...`

These tests generally assert that a configured model string is preserved through typed contracts, telemetry, persistence, and provider boundaries. They do not require changing merely because the deployment alias changes. A later cleanup could replace generic fixture values with neutral names such as `sample-model` or logical aliases to reduce confusion.

## Affected paths if `qwen3.5:4b` is replaced

### Must change for runtime behavior

1. `config/litellm/config.yaml`
   - Replace concrete backend mappings for `polaris-local-reasoning` and/or `polaris-local-synthesis`.
   - Optionally add new direct diagnostic aliases such as `qwen2.5-coder:7b` or `deepseek-r1:8b`.
   - Optionally remove or retain the direct `qwen3.5:*` diagnostic aliases.

### Should update with the decision

2. `.env.example`
   - Usually no change if logical aliases remain the public config surface.
   - Update comments only if the recommended alias roles or env var examples change.

3. `docs/litellm_gateway.md`
   - Update the alias-to-backend examples and operator guidance.

4. `docs/platform_rag_pipeline.md`
   - Update the RAG model table, setup commands, and low-VRAM profile narrative.

### Likely no production source change required

5. `config/settings.py`
   - Keep logical alias defaults stable unless the alias taxonomy changes.

6. `config/rag_model_config.py`
   - Keep stage-specific typed model settings stable.

7. `core/llm/*`, `integration/clients/llm/*`, `integration/providers/rag/*`, `application/rag/*`, `application/evaluations/*`, `application/observability/*`, `intelligence/*`
   - These are already alias/pass-through consumers or observers.

### Optional cleanup

8. Tests with `qwen3.5:4b` fixtures
   - Optional cleanup to reduce operator confusion.
   - Do not treat as required for replacing the deployment backend.

9. Historical plan files
   - Leave intact as historical records unless the plan file needs a superseding note.

## Recommendation

Do not replace `qwen3.5:4b` by editing application/runtime/RAG/strategy/evaluation code. Polaris already has the right seam: change concrete model bindings at the LiteLLM deployment boundary and validate with model-behavior gates.

Recommended next implementation path:

1. Keep logical aliases as canonical platform contracts.
2. Change only `config/litellm/config.yaml` for concrete backend substitution.
3. Add/confirm direct diagnostic aliases for any candidates selected for validation, such as `qwen2.5-coder:7b` and `deepseek-r1:8b`.
4. Run targeted gates before finalizing any replacement:
   - fast RAG route smoke
   - structured output smoke
   - RAG synthesis smoke
   - strategy synthesis / structured hypothesis smoke
   - DeepEval judge smoke
   - Langfuse observation export smoke
   - one real RAG answer path
5. After the final decision, update `docs/litellm_gateway.md` and `docs/platform_rag_pipeline.md` to reflect the actual supported local profile.
6. Optionally perform a test-fixture hygiene cleanup so pass-through tests use neutral model names or logical aliases instead of `qwen3.5:4b` where the concrete model identity is irrelevant.

## Resolution

`qwen3.5:4b` is currently an active runtime model only through LiteLLM deployment alias mappings for `polaris-local-reasoning` and `polaris-local-synthesis`. It is not embedded as a production architectural default in Python application code. Replacing it should be treated as a model-operations/profile change first, followed by targeted validation and documentation updates.
