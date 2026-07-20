# Research: candidate local model capabilities and constraints for Polaris

Issue: [Research candidate local model capabilities and constraints](https://github.com/sponge-b0b/Polaris/issues/4)

Date: 2026-07-19

## Question

What do current primary sources and local model documentation indicate about `qwen3.5:4b`, `qwen2.5:7b`, `qwen2.5-coder:7b`, and `deepseek-r1:8b` for Polaris's structured reasoning, JSON/schema, synthesis, and low-VRAM constraints?

This research separates source-backed model facts from local empirical validation requirements.

## Current Polaris baseline observed locally

Current code/config already uses logical model aliases rather than hard-coding architectural roles directly to concrete models:

- `config/settings.py` defines logical defaults such as `polaris-local-fast`, `polaris-local-reasoning`, `polaris-local-synthesis`, `polaris-local-structured`, `polaris-local-evaluation`, and `polaris-local-optimization`.
- `config/litellm/config.yaml` currently maps:
  - fast / structured / evaluation / optimization -> `ollama_chat/qwen2.5:7b`
  - reasoning / synthesis -> `ollama_chat/qwen3.5:4b`
  - direct diagnostic aliases for `qwen2.5:7b`, `qwen3.5:4b`, and `qwen3.5:9b`
- Current RAG token budgets in `config/settings.py` are conservative: structured 512, HyDE 768, synthesis 1536.

## Source-backed model facts

### `qwen3.5:4b`

Primary sources:

- Hugging Face model card: <https://huggingface.co/Qwen/Qwen3.5-4B>
- Ollama library: <https://ollama.com/library/qwen3.5>

Relevant source facts:

- The Hugging Face card identifies Qwen3.5-4B as a post-trained model compatible with serving stacks such as Transformers, vLLM, SGLang, and KTransformers.
- Qwen3.5 models operate in thinking mode by default and can emit `<think>...</think>` content before the final answer.
- The Hugging Face card lists a default context length of 262,144 tokens, but explicitly warns to reduce context length when out-of-memory occurs and says the model relies on long context for complex tasks.
- The Ollama library reports `qwen3.5:4b` as a 3.4GB model with a 256K context window and text/image input.

Polaris implications:

- Good candidate for low-VRAM reasoning experiments because it is the smallest currently configured reasoning-family option.
- Not automatically safe for deterministic JSON/schema workflows because thinking-mode output can add non-schema text unless the serving stack and prompt/output parser suppress or strip it reliably.
- The advertised 256K context is not the practical default under 8GB VRAM; context must be capped by profile and validated with `ollama ps`/LiteLLM smoke tests.
- Because the model is multimodal in Ollama, it may become useful for chart/report-image analysis later, but current Polaris RAG and strategy workflows are text-first.

### `qwen2.5:7b`

Primary sources:

- Hugging Face model card: <https://huggingface.co/Qwen/Qwen2.5-7B-Instruct>
- Ollama model page: <https://ollama.com/library/qwen2.5:7b-instruct>

Relevant source facts:

- Qwen2.5-7B-Instruct has 7.61B parameters and a full 131,072-token context length in the Hugging Face model card.
- The model card states improvements in instruction following, long-text generation, structured-data understanding, and JSON-style structured output.
- The Ollama `qwen2.5:7b-instruct` page reports a 4.7GB Q4_K_M model.
- The Ollama page reports Apache-2.0 licensing for this 7B instruct variant.

Polaris implications:

- Reasonable local default for fast/query-routing/triage tasks because it is already configured and is less reasoning-heavy than `qwen3.5:4b`.
- Source claims support structured data and JSON-style output, but Polaris still needs empirical validation through Instructor structured-output tests and golden datasets.
- On 8GB VRAM, its 4.7GB quantized size competes with KV cache and loaded services; 16K+ context may fit only if concurrency and other loaded models are controlled.

### `qwen2.5-coder:7b`

Primary sources:

- Hugging Face model card: <https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct>
- Ollama model page: <https://ollama.com/library/qwen2.5-coder>
- Qwen2.5-Coder technical report: <https://arxiv.org/abs/2409.12186>

Relevant source facts:

- Qwen2.5-Coder is explicitly a code-specific Qwen series covering 0.5B through 32B sizes.
- The model card describes improvements in code generation, code reasoning, and code fixing, while also preserving mathematics and general competencies.
- The 7B instruct model has 7.61B parameters and full 131,072-token context in the Hugging Face model card.
- The model card notes that its current static configuration is commonly set for 32,768 tokens unless YaRN scaling is configured for longer contexts.
- The Ollama `qwen2.5-coder:7b` page reports a 4.7GB text model with a 32K context window.

Polaris implications:

- Strong candidate for `polaris-local-structured`, `polaris-local-synthesis`, `polaris-local-evaluation`, and `polaris-local-optimization` because Polaris uses typed schema contracts, code-owned formulas, deterministic projection, and JSON-like structured outputs.
- It should not be treated as a magic math executor. Formula calculations should remain in Polaris code; the model should classify, explain, extract, and fill schemas.
- This model may be a better synthesis default than `qwen3.5:4b` if the synthesis task is mostly schema-constrained consolidation rather than open-ended causal reasoning.
- Empirical validation must include malformed-output rate, Instructor retry rate, DeepEval score stability, latency, and memory/offload behavior.

### `deepseek-r1:8b`

Primary sources:

- Ollama model page: <https://ollama.com/library/deepseek-r1:8b>
- DeepSeek-R1 Hugging Face model card: <https://huggingface.co/deepseek-ai/DeepSeek-R1>
- DeepSeek-R1 paper: <https://arxiv.org/abs/2501.12948>

Relevant source facts:

- The Ollama `deepseek-r1:8b` tag currently identifies the model as `DeepSeek-R1-0528-Qwen3-8B`, with qwen3 architecture, 8.19B parameters, Q4_K_M quantization, and a 5.2GB size.
- The same Ollama page states that the 8B tag was upgraded to the R1-0528 Qwen3 8B distilled model.
- The DeepSeek Hugging Face card distinguishes Qwen-derived R1 distill models from Llama-derived models; Qwen distills inherit from Qwen-2.5 series, while DeepSeek-R1-Distill-Llama-8B is derived from Llama 3.1.
- The DeepSeek-R1 paper says DeepSeek open-sourced dense distilled models at 1.5B, 7B, 8B, 14B, 32B, and 70B sizes.

Polaris implications:

- A key naming hazard exists: `deepseek-r1:8b` in Ollama is not necessarily the same artifact as Hugging Face `DeepSeek-R1-Distill-Llama-8B`. For Polaris decisions, the concrete model artifact must be pinned by provider/tag/digest where possible.
- It is a plausible perspective-reasoning candidate, but less attractive for strict output surfaces unless the provider strips reasoning text and validates schema output.
- At 5.2GB plus KV cache, it is a tighter fit than `qwen3.5:4b` or `qwen2.5:7b` on 8GB VRAM, especially with multiple services/models loaded.
- If used locally, operations should serialize heavy calls, constrain context/output budgets, and validate latency under representative strategy prompts.

## Ollama low-VRAM constraints

Primary sources:

- Ollama context-length docs: <https://docs.ollama.com/context-length>
- Ollama FAQ: <https://docs.ollama.com/faq>

Relevant source facts:

- Ollama describes context length as the token count the model has access to in memory.
- Ollama defaults context based on VRAM: under 24 GiB defaults to 4K, 24-48 GiB defaults to 32K, and 48 GiB or more defaults to 256K.
- Ollama states larger context length increases memory requirements and recommends checking `ollama ps` for context and CPU/GPU offload.
- Ollama FAQ says the default context window is 4096 tokens and can be changed via `OLLAMA_CONTEXT_LENGTH`, model parameters, or API `num_ctx`.

Polaris implications:

- The 8GB VRAM target must be treated as an operational profile, not as a model-card capability.
- Do not equate advertised max context with safe local context. Start with conservative 4K-8K for smoke tests and 8K-16K for selected heavier workflows, then raise only with measured memory and latency evidence.
- Avoid concurrent loading of `qwen2.5-coder:7b` and `deepseek-r1:8b` on 8GB unless one is unloaded/offloaded or calls are serialized.
- Record `actual_model`, `configured_model`, context length, max tokens, latency, and success/failure in AI observability records so model profile decisions are evidence-backed.

## Recommended candidate mapping to evaluate next

This issue is research-only, so the table below is a recommendation for later decision tickets, not an implementation decision.

| Polaris role / alias | Candidate to evaluate first | Rationale | Main risk to validate |
| --- | --- | --- | --- |
| `polaris-local-fast` | `qwen2.5:7b` | Already configured; source-backed structured-data and JSON capability; general-purpose fast path. | Memory/latency at 8K-16K context under LiteLLM. |
| `polaris-local-structured` | `qwen2.5-coder:7b` | Best source-backed fit for schema-constrained extraction/classification and deterministic JSON-style workflows. | Must prove lower malformed-output/retry rate than `qwen2.5:7b`. |
| `polaris-local-synthesis` | `qwen2.5-coder:7b` first, `qwen3.5:4b` as challenger | Polaris synthesis is code-owned math plus schema output, not unconstrained creative reasoning. | Need verify response quality does not regress versus Qwen3.5. |
| `polaris-local-reasoning` | `qwen3.5:4b` first, `deepseek-r1:8b` as heavyweight challenger | Qwen3.5 is smaller; DeepSeek R1 may reason better but is heavier and thinking-oriented. | CoT/thinking leakage, latency, and VRAM pressure. |
| `polaris-local-evaluation` | `qwen2.5-coder:7b` first | Evaluation needs stable schema/score/reason outputs. | Judge-quality drift; may later need larger/cloud judge profile. |
| `polaris-local-optimization` | `qwen2.5-coder:7b` first | Optimization prompts resemble code/math/rule evaluation. | Avoid delegating numeric truth to the model; Polaris code remains authoritative. |

## Non-negotiable validation requirements before replacing defaults

1. Pin the exact local artifact in LiteLLM/Ollama documentation: provider, tag, and digest when available.
2. Run structured-output smoke tests with Instructor and measure parse/retry/failure rates.
3. Run at least one RAG answer path and one strategy synthesis path with AI observability enabled.
4. Run selected golden dataset slices for RAG quality, strategy synthesis, and recommendation explanation.
5. Capture `ollama ps` or equivalent model/offload/context evidence during local profile validation.
6. Compare latency under realistic token budgets, not only one-line prompts.
7. Verify that reasoning/thinking text never crosses into JSON contracts, final reports, RAG citations, or durable curated records unless explicitly modeled.

## Bottom-line conclusion

Primary sources support moving away from concrete model names as architectural defaults and toward role-specific logical aliases with measured deployment profiles.

The strongest low-VRAM hypothesis to test next is:

- Keep `qwen2.5:7b` for fast/general routing and triage.
- Evaluate `qwen2.5-coder:7b` as the preferred structured/synthesis/evaluation/optimization model.
- Keep `qwen3.5:4b` as the first reasoning challenger because it is smaller than DeepSeek R1 and already available in the current architecture.
- Evaluate `deepseek-r1:8b` only as a heavyweight reasoning challenger after pinning its exact Ollama artifact, because the current Ollama tag maps to `DeepSeek-R1-0528-Qwen3-8B` and is not interchangeable with the older Llama-derived 8B distill.
