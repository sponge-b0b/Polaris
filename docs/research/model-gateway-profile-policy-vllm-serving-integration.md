# Research: vLLM serving integration architecture for Polaris

Research date: 2026-08-19  
Repository snapshot: `main` at `9f9bf86dfe1bf54ea0ee0eeaf348574bc8f9ffb0`  
Primary entity: `model-gateway-profile-policy`  
Related Wayfinder: [#53 vLLM model-serving integration](https://github.com/sponge-b0b/Polaris/issues/53)  
Companion research: [vLLM serving capabilities and constraints](model-gateway-profile-policy-vllm-serving-capabilities-constraints.md)

## Research status and authority

This document is **research only**. It records current Polaris implementation evidence, current external vLLM/LiteLLM evidence, integration pressure points, and decision support for a later `$wayfinder` pass.

It does not:

- make or accept an architectural decision;
- change the authority of current Polaris architecture or accepted ADRs;
- select vLLM as a canonical serving backend;
- satisfy, close, or advance Wayfinder issue #53 or child issues #55–#63;
- authorize source, deployment, model-profile, or production changes;
- claim that vLLM is superior to the current Ollama-backed local profile.

The authoritative `$wayfinder` workflow must independently revalidate repository state, current/accepted architecture sources, external documentation, and empirical evidence at its own starting HEAD before recording decisions.

## Relationship to the existing vLLM capability research

The existing [vLLM serving capabilities and constraints](model-gateway-profile-policy-vllm-serving-capabilities-constraints.md) research from issue #54 answers the external question: **what can vLLM do, and what constraints does it impose?**

This document answers the complementary internal question: **where could vLLM fit into Polaris without bypassing or weakening the model gateway/profile architecture that already exists?**

The #54 document observed vLLM `v0.25.1` on 2026-07-21. As of this research date, the current vLLM release is [`v0.27.1`](https://github.com/vllm-project/vllm/releases/tag/v0.27.1), released 2026-08-11. The `v0.27.0` release immediately beneath it added material capabilities relevant to Polaris, including Qwen3.5 text-model support, broader non-generative Model Runner V2 workloads including BGE-M3 pooling, and `vllm-bench` integration into the CLI. These deltas make the earlier capability research worth revalidating during Wayfinder, but they do not invalidate its architectural conclusion that vLLM belongs at the serving layer rather than inside Polaris application/intelligence code.

Relevant current primary sources:

- [vLLM v0.27.1 release](https://github.com/vllm-project/vllm/releases/tag/v0.27.1)
- [vLLM v0.27.0 release notes](https://github.com/vllm-project/vllm/releases/tag/v0.27.0)
- [vLLM OpenAI-compatible server](https://docs.vllm.ai/en/latest/serving/online_serving/openai_compatible_server/)
- [vLLM Docker deployment](https://docs.vllm.ai/en/latest/deployment/docker/)
- [vLLM security guidance](https://docs.vllm.ai/en/latest/usage/security/)
- [vLLM metrics](https://docs.vllm.ai/en/latest/design/metrics/)
- [LiteLLM vLLM provider](https://docs.litellm.ai/docs/providers/vllm)

## Executive findings

These are research findings, not Wayfinder decisions.

1. **Polaris already has a backend-interchange seam.** Source code uses logical aliases and typed LLM boundaries; LiteLLM owns concrete provider/backend routing. A vLLM integration does not inherently require a new application-layer dependency.

2. **The lowest-pressure candidate topology is behind the existing LiteLLM proxy.** LiteLLM currently documents `hosted_vllm/<model>` for routing an alias to a vLLM OpenAI-compatible server. That aligns closely with Polaris's existing rule that concrete model bindings belong in LiteLLM/deployment configuration.

3. **The current Polaris guardrails should remain authoritative even if vLLM supplies similar capabilities.** Model identity/fallback rejection, reasoning-trace sanitization, typed structured-output handling, request budgets, telemetry, and model-replacement validation are Polaris responsibilities today. A serving backend should not silently replace those controls.

4. **The most important integration risk is response-model identity semantics.** `LiteLlmGatewayClient` compares the returned model identity to the requested Polaris alias and rejects a mismatch by default. Before any vLLM-backed alias can be treated as compatible, live evidence must establish what LiteLLM returns in the model field for the selected `hosted_vllm` route and whether that behavior preserves Polaris's no-silent-fallback invariant.

5. **The 8GB local profile remains an empirical question.** vLLM supports quantized models and a wide range of runtimes, but support does not establish that a specific model/quantization/runtime will fit or outperform Ollama on Polaris's current low-VRAM workstation profile.

6. **Embeddings and reranking are separate adoption questions.** vLLM and LiteLLM expose embedding/reranking paths, but Polaris currently has separate RAG provider/runtime surfaces. Generation, embeddings, and reranking should not be collapsed into one integration decision merely because one serving product can expose all three.

7. **Deployment and security are first-class architecture inputs.** A production/self-hosted vLLM service needs version pinning, GPU/resource policy, model-cache ownership, health/readiness behavior, network isolation, and endpoint exposure controls. vLLM's own security guidance recommends minimizing exposed ports and placing the HTTP server behind an allowlisting reverse proxy rather than relying on its API-key option alone.

## 1. Current Polaris model-serving architecture

The current generation path is intentionally layered:

```text
Application / RAG / intelligence use case
        |
        v
Typed Polaris LLM boundary
  - LLMService / LLMGateway
  - or a typed provider such as structured output
        |
        v
LiteLLM-compatible client boundary
  - LiteLlmCoreGatewayAdapter
  - LiteLlmGatewayClient
  - Instructor over AsyncOpenAI for structured output
        |
        v
LiteLLM proxy
        |
        v
Logical alias -> concrete backend binding
        |
        v
Current local backend: Ollama
```

The significant point is not the current Ollama binding. It is the ownership split around it.

### Polaris-owned responsibilities

Current implementation and architecture assign Polaris responsibility for:

- typed application/provider requests and results;
- logical capability aliases used by source code;
- request budgets and client-side concurrency policy;
- timeout normalization and gateway error handling;
- response-model identity/fallback detection;
- reasoning-trace sanitization and fail-closed structured boundaries;
- structured-output provider contracts;
- integration/application telemetry;
- RAG orchestration and evidence handling;
- evaluation datasets, model-regression checks, and replacement-readiness evidence;
- persistence and durable business records.

### LiteLLM/deployment-owned responsibilities

Current architecture assigns LiteLLM/runtime deployment responsibility for:

- concrete provider/model bindings;
- provider normalization;
- backend routing;
- backend authentication;
- provider-specific request translation;
- environment-specific model allocation.

That split is already codified in:

- [`core/llm/llm_service.py`](../../core/llm/llm_service.py)
- [`core/llm/llm_gateway.py`](../../core/llm/llm_gateway.py)
- [`integration/clients/llm/core_gateway_adapter.py`](../../integration/clients/llm/core_gateway_adapter.py)
- [`integration/clients/llm/litellm_gateway_client.py`](../../integration/clients/llm/litellm_gateway_client.py)
- [`config/litellm/config.yaml`](../../config/litellm/config.yaml)
- [Polaris LiteLLM Gateway](../current/model-gateway-profile-policy-litellm-gateway.md)
- [Polaris Model Profile Policy](../current/model-gateway-profile-policy-model-profiles.md)

## 2. Composition and call path

Dishka currently composes the active gateway without provider-specific knowledge in application code:

```text
Settings
  |
  +-> LiteLlmGatewayClient.from_settings(...)
          |
          v
      LiteLlmCoreGatewayAdapter
          |
          v
       LLMGateway
          |
          v
       LLMService
```

`integration/clients/di.py` provides `LiteLlmGatewayClient` and adapts it to the core `LLMGateway` protocol. `core/llm/di.py` injects that protocol into `LLMService`, using `settings.DEFAULT_MODEL`.

If vLLM remains behind LiteLLM, this composition can plausibly remain unchanged. That is a useful architectural property: backend selection can remain an operator/profile concern instead of becoming a new dependency-composition branch.

This is not proof that no source changes will be required. It identifies the seam that should be preserved unless later evidence demonstrates a real gap.

## 3. Logical alias policy

Polaris currently treats these aliases as capability contracts:

| Logical alias | Contracted role | Current local binding |
| --- | --- | --- |
| `polaris-local-fast` | Low-latency planning, query rewrite, triage | `ollama_chat/qwen2.5:7b` |
| `polaris-local-reasoning` | Heavier local reasoning | `ollama_chat/qwen3.5:4b` |
| `polaris-local-structured` | JSON/schema-oriented output and routing | `ollama_chat/qwen2.5-coder:7b` |
| `polaris-local-synthesis` | User-facing/RAG/strategy synthesis | `ollama_chat/qwen2.5-coder:7b` |
| `polaris-local-evaluation` | Evaluation/judge work | `ollama_chat/qwen2.5-coder:7b` |
| `polaris-local-optimization` | Prompt/DSPy optimization | `ollama_chat/qwen2.5-coder:7b` |

The contract is the alias, not the model on the right.

A vLLM experiment that preserves this model should conceptually change only the concrete binding, for example:

```yaml
model_name: polaris-local-fast
litellm_params:
  model: hosted_vllm/<candidate-model>
  api_base: <operator-owned-vllm-endpoint>
```

That example illustrates the current LiteLLM provider mechanism; it is **not** a selected Polaris configuration.

Changing an alias meaning, changing source defaults to a different alias, or promoting a challenger model remains a model-policy/replacement decision and should not be smuggled into a backend experiment.

## 4. Failure, fallback, and identity behavior

`LiteLlmGatewayClient` is more than an HTTP wrapper. It enforces behavior that a vLLM profile must preserve:

- bounded concurrency;
- request token budgets;
- timeout normalization;
- safe gateway exceptions;
- response-model capture;
- fallback detection;
- default rejection of model mismatch;
- reasoning-trace sanitization;
- fail-closed reasoning contamination for JSON output;
- sanitized result metadata.

Current defaults include:

```text
LITELLM_MAX_CONCURRENCY = 1
LITELLM_TIMEOUT_SECONDS = 60
LITELLM_REQUEST_BUDGET_TOKENS = 4096
LITELLM_REJECT_MODEL_FALLBACK = true
```

### Integration pressure point: model identity

The current client computes:

```text
requested model alias
        vs
response.model
```

and rejects a difference when fallback rejection is enabled.

This deserves an explicit vLLM compatibility test because there are at least three identities in play:

```text
Polaris logical alias
        |
        v
LiteLLM configured concrete route
        |
        v
vLLM served model identity
```

The research question is not merely "does vLLM return a model name?" It is:

> Does the complete LiteLLM `hosted_vllm` path preserve enough stable identity for Polaris to distinguish an intentional alias binding from an unapproved fallback without disabling the no-silent-fallback invariant?

Possible outcomes should be measured before Wayfinder decides whether any adapter/configuration change is warranted.

## 5. Structured output and reasoning-trace safety

Polaris has two relevant structured paths:

1. `LLMGateway.generate_json()` / JSON chat responses through the LiteLLM client and adapter.
2. `InstructorStructuredOutputProvider`, which uses Instructor over an OpenAI-compatible client pointed at the LiteLLM gateway.

The second path is especially useful evidence that "OpenAI-compatible" alone is not the architecture. Polaris still owns a typed provider, schema, retry/error behavior, and telemetry around that wire protocol.

vLLM supports OpenAI-compatible chat and structured/tool-oriented output features. Those capabilities may improve backend behavior, but they should not become a reason to bypass:

- Polaris Pydantic/domain schemas;
- Instructor/provider contracts where they remain applicable;
- reasoning-trace sanitization;
- fail-closed JSON behavior;
- model-replacement evaluation.

A vLLM-specific reasoning parser or structured-output mechanism should therefore be treated as backend implementation behavior until Wayfinder explicitly decides otherwise.

## 6. Telemetry and observability

Polaris currently has two observability layers relevant to this integration:

### Polaris semantic telemetry

Polaris/provider/application telemetry owns semantic operation identity, logical model/profile identity, safe failure reporting, evaluation evidence, and durable workflow/business context.

### Backend serving telemetry

vLLM exposes Prometheus metrics and OpenTelemetry-capable tracing surfaces. These are useful for serving-level information such as request/engine behavior, throughput, cache behavior, queueing, and resource health.

The useful integration model is likely correlation rather than duplication:

```text
Polaris semantic operation
        |
        +---- logical alias / workflow / evaluation identity
        |
        +---- request correlation
                 |
                 v
           LiteLLM request
                 |
                 v
             vLLM trace/metrics
```

Backend metrics should not become a second authoritative workflow event stream. Wayfinder #60 should decide the exact correlation contract, request-ID behavior, and which metrics are required for acceptance.

## 7. Evaluation and model-replacement gates

Polaris already has a model-replacement gate in `application/evaluations/model_replacement_gate.py` and a documented readiness matrix in:

[Model Allocation Readiness Check](../reference/model-gateway-profile-policy-model-allocation-readiness.md)

Current policy requires replacement-validation evidence across areas including:

- static/config boundary checks;
- structured output;
- RAG quality, grounding, and prompt-injection behavior;
- strategy and synthesis behavior;
- execution-risk/recommendation behavior;
- DeepEval execution;
- Langfuse projection;
- local operations readiness;
- executable local-operations cases.

That means a vLLM benchmark showing higher tokens/second would be necessary performance evidence for some profiles, but insufficient acceptance evidence for Polaris.

The backend must preserve the behavioral contract of the alias, not merely serve a compatible HTTP endpoint.

## 8. Deployment surface

The current local deployment has a LiteLLM Compose service but no active vLLM service. `docker-compose.yml` contains a commented historical `depends_on: vllm` placeholder; that is not current architecture or evidence of a chosen deployment.

A future vLLM profile could pressure several operator-owned surfaces:

- vLLM image/version pinning;
- GPU device/resource allocation;
- shared-memory configuration;
- model cache/mount ownership;
- Hugging Face or model-repository credentials;
- service health/readiness checks;
- startup/shutdown order;
- internal API endpoint/base URL;
- LiteLLM-to-vLLM authentication;
- local vs production network exposure;
- reverse-proxy or gateway policy;
- Prometheus/OTel integration;
- production lifecycle and rollback.

vLLM's current Docker guidance publishes an OpenAI-compatible image (`vllm/vllm-openai`) and documents GPU/container runtime and shared-memory requirements. Its current security guidance also makes network topology part of the design: internal distributed ports should remain isolated, and the vLLM HTTP server should not be treated as safely exposed merely because an API key is configured.

## 9. Repository integration inventory

| Surface | Current responsibility | Expected vLLM pressure |
| --- | --- | --- |
| `core/llm/llm_gateway.py` | Typed provider-neutral gateway protocol/results | Normally none if vLLM stays behind LiteLLM |
| `core/llm/llm_service.py` | Canonical async application LLM service | Normally none |
| `core/llm/di.py` | Compose `LLMService` from `LLMGateway` and logical default | Normally none |
| `integration/clients/llm/core_gateway_adapter.py` | Adapt LiteLLM client to core protocol | Normally none; verify identity/JSON semantics |
| `integration/clients/llm/litellm_gateway_client.py` | OpenAI-compatible gateway client, budgets, fallback rejection, trace safety, metadata | High-value compatibility surface; should not be bypassed |
| `integration/clients/di.py` | Compose LiteLLM client as the gateway implementation | Normally none if LiteLLM remains canonical |
| `config/settings.py` | Stable Polaris alias defaults and LLM operational policy | Avoid concrete vLLM/model defaults; new operator settings only if justified |
| `config/litellm/config.yaml` | Logical alias -> concrete backend routing | Primary candidate binding surface |
| `integration/providers/llm_structured_output/` | Typed Instructor/schema output through LiteLLM | Compatibility verification required |
| `application/evaluations/model_replacement_gate.py` | Replacement validation evidence | Required acceptance surface |
| `docs/reference/model-gateway-profile-policy-model-allocation-readiness.md` | Cross-boundary readiness matrix | Likely later amendment if a vLLM profile is accepted |
| `docker-compose.yml` | Local service deployment | Candidate local vLLM service/profile surface |
| `deployment/` | Operator/production infrastructure | Candidate production surface depending on #59 |
| `core/llm/embeddings.py` | Currently empty placeholder | Do not infer ownership or fill merely because vLLM supports embeddings |
| `core/llm/reranker.py` | Currently empty placeholder | Do not infer ownership or fill merely because vLLM supports reranking |
| `docs/research/model-gateway-profile-policy-vllm-serving-capabilities-constraints.md` | Existing external capability research | Companion source, not active authority |

## 10. High-risk or brittle integration points

### 10.1 Response-model identity

This is the first live compatibility test to run. A backend route that causes every legitimate response to look like a fallback would conflict with current operations policy; disabling fallback rejection globally just to make the backend work would weaken a deliberate invariant.

### 10.2 Structured-output provider compatibility

The Instructor provider currently sends a logical model through LiteLLM. Tests must verify that selected vLLM models and vLLM/LiteLLM versions preserve the required JSON/schema semantics, retries, error behavior, and trace safety.

### 10.3 `drop_params: true`

LiteLLM is currently configured with `drop_params: true`. That is useful for provider normalization, but vLLM experiments should explicitly verify that parameters important to correctness are not silently dropped in a way that changes an alias contract.

### 10.4 Reasoning-model behavior

Current Polaris policy prohibits raw model-internal reasoning from crossing the boundary into typed records, telemetry, reports, RAG evidence, MCP, or customer-visible output. vLLM reasoning parsers/features cannot weaken that rule.

### 10.5 Version/runtime churn

The move from vLLM `v0.25.1` in the July research to `v0.27.1` in August, plus a PyTorch 2.13 environment change in `v0.27.0`, reinforces that production artifacts should pin and validate an exact serving stack rather than follow floating tags.

### 10.6 Deployment exposure

A directly exposed vLLM server has a materially different security surface from "an OpenAI-compatible endpoint with an API key." Endpoint allowlisting and network isolation must be part of the deployment design.

### 10.7 Generation vs embeddings/reranking

vLLM can serve multiple workload types, and LiteLLM documents vLLM routes for chat, embeddings, completions, reranking, and audio. Polaris should still decide these lanes independently because their current application/provider contracts and performance characteristics differ.

## 11. Candidate topology analysis

The following are research candidates, not decisions.

| Candidate | Shape | Alignment with current Polaris | Main pressure |
| --- | --- | --- | --- |
| **A. LiteLLM `hosted_vllm` binding** | Polaris alias -> LiteLLM -> `hosted_vllm/<model>` -> vLLM server | Strongest apparent fit | Identity semantics, deployment, live validation |
| **B. Generic OpenAI-compatible binding in LiteLLM** | Polaris alias -> LiteLLM generic OpenAI-compatible route -> vLLM | Plausible | Less provider-specific clarity; capability mapping must be verified |
| **C. Direct vLLM endpoint behind a new/changed Polaris gateway adapter** | Polaris -> `LLMGateway` implementation -> vLLM | Would preserve core protocol but bypass current LiteLLM ownership | Changes canonical gateway/provider normalization architecture |
| **D. Direct vLLM SDK/client from application, RAG, strategy, report, MCP, or intelligence code** | Call-site -> vLLM | Conflicts with current strict invariants | Creates provider-specific application dependency and alternate routing authority |

Candidate A creates the least apparent source-code pressure because LiteLLM explicitly documents `hosted_vllm/` for the OpenAI-compatible vLLM server and Polaris already treats LiteLLM as the concrete-binding owner. That is a reason to prioritize it for validation, not an architectural decision.

## 12. Operating-profile research matrix

| Profile | Current research position | Evidence required |
| --- | --- | --- |
| Existing 8GB-VRAM local development | **Unresolved** | Exact GPU compatibility, model/quantization fit, VRAM headroom, startup behavior, latency, concurrency, structured-output quality, comparison with current Ollama baseline |
| Higher-VRAM single-GPU workstation | **Plausible candidate** | Same-model benchmark, operational ergonomics, quantization choice, failure/restart behavior |
| Production self-hosted GPU | **Plausible candidate** | Capacity model, security topology, image/version pin, observability, health/readiness, cache/model lifecycle, rollback |
| Generation/synthesis aliases | **Primary architectural fit to investigate** | Alias-by-alias quality and performance validation |
| Embeddings | **Separate candidate** | Exact model support, vector semantics/dimensions, RAG provider ownership, rebuild compatibility |
| Reranking | **Separate candidate** | Exact reranker support, endpoint semantics, quality/latency comparison with current BGE service |
| Evaluation/optimization models | **Possible later candidate** | Judge/optimization reproducibility, cost/throughput, isolation from production-serving contention |

The current vLLM release supports additional quantization and pooling capabilities, but none of those facts answer the 8GB question by themselves. Hardware fit must be measured with the intended model, quantization, context/token budget, concurrency, and workload.

## 13. Wayfinder decision support

### #56 — Decide vLLM integration topology

**Repository-established facts**

- LiteLLM is the canonical concrete backend router.
- Source layers consume typed Polaris boundaries and logical aliases.
- Direct provider calls from application/RAG/intelligence layers violate current architecture.

**External facts**

- LiteLLM explicitly supports an OpenAI-compatible vLLM route via `hosted_vllm/`.
- vLLM exposes OpenAI-compatible serving APIs.

**Research pressure**

Validate Candidate A first because it preserves the most current architecture and demands the fewest ownership changes.

**Decision still required**

Wayfinder must decide whether that topology is sufficient for every intended vLLM lane and whether any alternate topology is justified.

### #57 — Decide vLLM target operating profiles

**Repository-established facts**

- Current local development targets an 8GB-VRAM conservative profile.
- Current model concurrency defaults to one.
- Larger model/profile claims require validation.

**External facts**

- vLLM supports multiple GPU/runtime/quantization configurations.
- Runtime compatibility and memory use depend on exact hardware/model/quantization.

**Research pressure**

Do not make the 8GB machine the proof point for vLLM as a platform. Treat it as one profile to benchmark. Higher-VRAM workstation and production self-hosted profiles may have a different value proposition.

**Decision still required**

Which profile is first-adoption scope, and which profiles are explicitly deferred?

### #58 — Decide alias and backend-binding semantics

**Repository-established facts**

- Polaris aliases are stable source contracts.
- Concrete bindings belong in LiteLLM/runtime/deployment configuration.
- Silent fallback is prohibited by default.

**Research pressure**

Keep the existing aliases during the experiment. Put vLLM-specific concrete identities behind LiteLLM. Validate response-model identity behavior before deciding whether any gateway adaptation is necessary.

**Decision still required**

Exact binding/configuration ownership and how intentional concrete response identity is represented without weakening fallback detection.

### #59 — Decide deployment and operations ownership

**Repository-established facts**

- Local LiteLLM is already Compose-managed.
- Production bindings are operator/deployment concerns.
- Secrets must remain outside source/docs/tests.

**External facts**

- vLLM publishes Docker deployment guidance and requires hardware/runtime-aware configuration.
- vLLM security guidance requires deliberate network isolation and endpoint exposure policy.

**Research pressure**

Treat the vLLM server as operator-owned infrastructure. Do not make `LLMService` or an application use case responsible for starting, locating, caching, or configuring model weights.

**Decision still required**

Local Compose vs separate runbook vs production deployment artifacts, image pinning, health/readiness, cache ownership, GPU controls, network/reverse proxy, and lifecycle.

### #60 — Decide observability and safety requirements

**Repository-established facts**

- Polaris already owns semantic telemetry and reasoning-trace safety.
- Gateway results carry requested/response model identity and sanitized metadata.
- Structured paths fail closed on reasoning contamination.

**External facts**

- vLLM exposes Prometheus metrics and tracing capabilities.
- Request/serving telemetry can provide backend-level evidence.

**Research pressure**

Correlate vLLM telemetry with Polaris operations; do not duplicate workflow lifecycle semantics in the serving engine. Preserve Polaris safety filtering regardless of vLLM parser behavior.

**Decision still required**

Required metrics/traces, correlation IDs, redaction, cardinality, storage/retention, and failure behavior.

### #61 — Decide benchmark and validation gates

A useful future validation matrix should separate:

**Service-free checks**

- alias/source invariants;
- no direct vLLM imports/calls in prohibited layers;
- configuration shape;
- fallback rejection logic;
- reasoning-trace tests;
- structured-output contracts;
- evaluation/readiness unit tests.

**Live compatibility checks**

- LiteLLM alias discovery;
- `hosted_vllm` chat request;
- returned model identity;
- JSON/Instructor structured output;
- timeout/error normalization;
- fallback/mismatch behavior;
- reasoning-trace contamination cases;
- request metadata/correlation;
- service restart/readiness.

**Benchmark checks**

For each selected alias/profile, record at minimum:

- exact GPU/CPU/RAM and driver/runtime;
- exact vLLM version/image;
- exact concrete model and revision;
- exact quantization;
- token/context limits;
- concurrency;
- cold startup and warm startup;
- time to first token;
- end-to-end latency distribution;
- throughput;
- peak VRAM/RAM;
- structured-output success rate;
- quality/regression gate outcome;
- backend failure/recovery behavior.

Where feasible, compare vLLM and the current backend on the same model/revision/quantization or explicitly document why the comparison is not apples-to-apples.

vLLM `v0.27.0` integrates `vllm-bench` into the CLI, which can help measure serving behavior, but Polaris still owns the workload definition and acceptance criteria.

### #62 — Decide rollout, fallback, and acceptance

A candidate evidence-driven rollout shape for Wayfinder to evaluate is:

```text
research
  -> opt-in experimental profile
  -> validated optional profile
  -> production candidate
  -> default-eligible only after explicit acceptance
```

At every stage, rollback should restore the prior alias binding without source call-site changes.

This sequence is a research suggestion, not a selected policy.

## 14. Questions already answered by current Polaris authority

A future Wayfinder pass should not spend decision time reopening these unless it finds a genuine source conflict:

- **Should application code hard-code vLLM model names?** No; current model-profile policy requires logical aliases.
- **Should intelligence/RAG/report/MCP code call vLLM directly?** No; current gateway policy centralizes model access.
- **Who currently owns concrete model routing?** LiteLLM plus runtime/deployment configuration.
- **May a backend silently fall back to another model?** No by default.
- **May raw reasoning traces become business records or presentation output?** No.
- **Is throughput alone enough to promote a model/profile?** No; the model-replacement/readiness gate is broader.
- **Should credentials be committed in source/config/docs/tests?** No.

Wayfinder should verify these are still authoritative at its execution time, then spend its decision budget on the unresolved vLLM-specific choices.

## 15. Questions requiring architectural judgment

The repository does not currently decide:

- whether vLLM is local-only, production-only, or both;
- which operating profile should be adopted first;
- whether generation is the only first-stage workload;
- whether embedding/reranking lanes should later move to vLLM;
- whether a dedicated vLLM deployment belongs in Compose, deployment infrastructure, a runbook, or multiple profile-specific artifacts;
- what exact backend identity contract should exist between a Polaris alias, LiteLLM route, and vLLM model;
- what backend telemetry must be correlated into Polaris observability;
- what staged rollout status vocabulary and rollback policy should govern adoption.

Those are appropriate Wayfinder decisions after evidence collection.

## 16. Questions requiring empirical validation

The following should not be decided from documentation alone:

- whether the current 8GB GPU can run a useful vLLM profile;
- whether that profile is faster, slower, or more reliable than Ollama for Polaris workloads;
- whether selected models produce equivalent or better structured output;
- what `response.model` LiteLLM returns for the chosen vLLM route;
- whether fallback detection behaves correctly through the complete route;
- whether reasoning-trace handling remains safe for selected reasoning models;
- whether the selected quantization changes output quality enough to fail model-regression gates;
- startup time, warmup behavior, memory headroom, concurrency limit, and restart characteristics;
- production capacity/latency under representative Polaris traffic.

## 17. Suggested evidence package for the later Wayfinder pass

When `$wayfinder` is run for #53, useful input would be:

1. this integration research document;
2. the companion #54 capabilities/constraints research;
3. the current `model-gateway-profile-policy` entity and its cited `current` documents;
4. current issue #53 and decision children #55–#63;
5. current `config/litellm/config.yaml` and `config/settings.py`;
6. current gateway/client/structured-output implementations;
7. current model-allocation readiness matrix and model-replacement gate;
8. freshly checked vLLM and LiteLLM primary-source docs;
9. any live compatibility evidence for alias/model identity;
10. any hardware/profile benchmark packet.

Suggested reading order:

```text
current Polaris authority
        ->
this integration research
        ->
#54 external capability research
        ->
fresh external docs
        ->
live/benchmark evidence
        ->
Wayfinder decisions
```

Research should shorten discovery. It must not replace decision authority.

## Research handoff

This document is research only. It does not satisfy, close, or modify `$wayfinder` ticket #53 or children #55–#63. The authoritative workflow must independently revalidate repository state, accepted/current architecture sources, external documentation, and empirical evidence at its starting HEAD before recording decisions.
