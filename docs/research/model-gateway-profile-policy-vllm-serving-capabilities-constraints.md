# Research: vLLM serving capabilities and constraints for Polaris

Research date: 2026-07-21  
Issue: [#54 Research vLLM serving capabilities and constraints](https://github.com/sponge-b0b/Polaris/issues/54)  
Scope: research only. No Polaris code, deployment configuration, or tests were implemented.

## Source policy

External facts in this note are drawn only from official vLLM sources and official LiteLLM documentation:

- vLLM latest GitHub release: [v0.25.1, published 2026-07-14](https://github.com/vllm-project/vllm/releases/tag/v0.25.1)
- vLLM docs: [OpenAI-compatible server](https://docs.vllm.ai/en/latest/serving/online_serving/openai_compatible_server/), [installation overview](https://docs.vllm.ai/en/latest/getting_started/installation/), [GPU installation](https://docs.vllm.ai/en/latest/getting_started/installation/gpu/), [CPU installation](https://docs.vllm.ai/en/latest/getting_started/installation/cpu/), [Docker deployment](https://docs.vllm.ai/en/latest/deployment/docker/), [Kubernetes deployment](https://docs.vllm.ai/en/latest/deployment/k8s/), [Production Stack](https://docs.vllm.ai/en/latest/deployment/integrations/production-stack/), [parallelism and scaling](https://docs.vllm.ai/en/latest/serving/parallelism_scaling/), [data-parallel deployment](https://docs.vllm.ai/en/latest/serving/data_parallel_deployment/), [pooling models](https://docs.vllm.ai/en/latest/models/pooling_models/), [scoring and reranking](https://docs.vllm.ai/en/latest/models/pooling_models/scoring/), [supported models](https://docs.vllm.ai/en/latest/models/supported_models/), [tool calling](https://docs.vllm.ai/en/stable/features/tool_calling/), [metrics](https://docs.vllm.ai/en/latest/usage/metrics/), [metrics design](https://docs.vllm.ai/en/latest/design/metrics/), [OpenTelemetry example](https://docs.vllm.ai/en/latest/examples/observability/opentelemetry/), [Prometheus/Grafana example](https://docs.vllm.ai/en/latest/examples/observability/prometheus_grafana/), [security](https://docs.vllm.ai/en/latest/usage/security/), and [serve CLI arguments](https://docs.vllm.ai/en/latest/cli/serve/)
- LiteLLM docs: [vLLM provider](https://docs.litellm.ai/docs/providers/vllm), [OpenAI-compatible provider](https://docs.litellm.ai/docs/providers/openai_compatible), and [LiteLLM overview](https://docs.litellm.ai/)

The vLLM documentation links above use the `latest` documentation channel unless explicitly marked stable by vLLM. Re-check the exact docs for the pinned vLLM release before production rollout.

## Executive answer for Polaris

vLLM is a strong candidate for Polaris **model serving infrastructure**, but it should not become a new Polaris application or intelligence dependency. For Polaris, vLLM matters as a deployable backend behind the existing LLM boundary:

```text
Polaris application / intelligence / runtime code
→ canonical Polaris LLM service / logical model alias
→ LiteLLM proxy or LiteLLM-compatible client boundary
→ hosted_vllm/OpenAI-compatible route
→ vLLM OpenAI-compatible server
→ model weights and accelerator runtime
```

The main value is local or self-hosted high-throughput inference for chat/completions, embeddings, audio transcription/translation, reranking/scoring, structured outputs, and tool-call-shaped chat responses. The main constraints are hardware/runtime specificity, per-instance runner/task choices, endpoint security gaps if vLLM is exposed directly, version/model compatibility churn, and the need to keep RAG orchestration and Polaris model selection above the serving layer.

## Documented facts

### Current release and versioning context

- The latest vLLM GitHub release observed during this research is [`v0.25.1`](https://github.com/vllm-project/vllm/releases/tag/v0.25.1), published on 2026-07-14.
- That release is a patch release. Its notes identify startup/import and mixed-dtype allreduce/RMSNorm quantization fixes rather than a new serving contract.
- vLLM documentation is moving quickly. The official docs include both `latest` and `stable` pages; production decisions should pin the image/wheel and validate the matching documentation for that version.

### Supported serving APIs

The official [OpenAI-compatible server](https://docs.vllm.ai/en/latest/serving/online_serving/openai_compatible_server/) is vLLM's primary online serving interface for Polaris-style integration. It supports:

- `/v1/completions` for text generation. The OpenAI `suffix` parameter is not supported.
- `/v1/chat/completions` for text generation with chat templates.
- `/v1/chat/completions/batch` for batch chat completions.
- `/v1/responses`, `/v1/responses/{response_id}`, and `/v1/responses/{response_id}/cancel` for the Responses-style API surface. The docs identify this as text-generation-only for now.
- `/v1/embeddings` for embedding models.
- `/v1/audio/transcriptions` and `/v1/audio/translations` for ASR models.
- Extra vLLM-specific sampling or serving parameters can be passed through OpenAI-compatible clients using an `extra_body` mechanism.
- `X-Request-Id` request headers are supported only when the server is started with `--enable-request-id-headers`.
- The server can be run with a command such as `vllm serve <model> --dtype auto --api-key <token>`, and OpenAI-compatible clients can point at the vLLM `base_url`.
- By default, vLLM applies a model repository's `generation_config.json` if present. Passing `--generation-config vllm` uses vLLM defaults instead.

Chat-specific documented caveats:

- The `user` parameter is ignored by vLLM's chat completion endpoint.
- `parallel_tool_calls=false` forces zero or one tool call; the default `true` allows multiple tool calls but does not guarantee them.
- Vision/audio-related chat parameters exist for multimodal models, but `image_url.detail` is not supported.

### Tool calling and structured outputs

The official [tool calling documentation](https://docs.vllm.ai/en/stable/features/tool_calling/) documents OpenAI-style named function calling in chat completions:

- Named function calling is supported by default in the chat completions API.
- Tool calling uses vLLM structured-output machinery; vLLM guarantees a syntactically parseable function call, not that the selected tool or arguments are semantically correct.
- `tool_choice='required'` and `tool_choice='none'` are supported.
- Schema-constrained decoding behavior depends on `tool_choice` and `strict`. Named and required choices use constraints; automatic tool choice uses constraints when at least one supplied tool has `strict: true`.
- vLLM's strict-tool guidance includes JSON Schema restrictions such as disallowing extra properties and representing optional fields via nullable required fields.
- The environment variable `VLLM_ENFORCE_STRICT_TOOL_CALLING` defaults to strict enforcement.

### Model and task coverage

The official [supported models](https://docs.vllm.ai/en/latest/models/supported_models/) page documents broad categories rather than a single universal capability promise:

- vLLM supports many text-only language models, multimodal language models, and pooling models.
- Generative text models use `LLM.generate`; chat/instruction-tuned models additionally support `LLM.chat`.
- The supported-models tables include text, image, video, and audio modality indicators for multimodal models.
- Multimodal or hybrid-only models can be run in language-model-only mode by disabling multimodal modality limits, which can reduce GPU memory and KV-cache use.
- LoRA support exists on the language backbone for most multimodal models and is experimental for some multimodal towers/connectors.
- Model-family support should be verified against the exact model name and vLLM version before treating it as a Polaris serving profile.

Pooling and retrieval-related support is documented separately in [pooling models](https://docs.vllm.ai/en/latest/models/pooling_models/) and [scoring/reranking](https://docs.vllm.ai/en/latest/models/pooling_models/scoring/):

- Pooling tasks include embedding, classification, token classification, token embedding, reward, scoring, and plugin-backed pooling behavior.
- `--runner pooling` selects pooling mode; `--runner auto` usually detects the task.
- Embedding and token-embedding pooling use L2 normalization by default.
- vLLM documents RAG support as the inference component only: embedding generation and reranking. It does not provide end-to-end RAG orchestration.
- vLLM scoring supports cross-encoder, late-interaction, and bi-encoder score types.
- Online scoring/reranking endpoints include `/score`, `/v1/score`, `/rerank`, `/v1/rerank`, and `/v2/rerank`.
- The previous `score` pooling task was removed in vLLM `v0.21`; scoring API support now depends on classification models with `num_labels=1`.

### Runtime and per-instance serving shape

The [serve CLI](https://docs.vllm.ai/en/latest/cli/serve/) exposes a `--runner` choice of `auto`, `draft`, `generate`, or `pooling`. This matters because a vLLM server instance is configured around a model and runner/task shape. Generation, embedding, reranking, and speculative/draft use cases should be planned as distinct serving profiles unless the exact target model/runtime combination explicitly supports a shared arrangement.

### Deployment modes

Official vLLM deployment options include:

- **Local/server process:** `vllm serve <model>` exposes the OpenAI-compatible HTTP server.
- **Offline/batched inference:** vLLM quickstart material documents offline batched inference as a separate usage mode from online serving.
- **Docker:** The [Docker deployment guide](https://docs.vllm.ai/en/latest/deployment/docker/) publishes an OpenAI-compatible image on Docker Hub as `vllm/vllm-openai`. GPU deployments use NVIDIA container runtime flags, bind Hugging Face cache/token material as needed, expose port 8000, and add model/engine arguments after the image tag.
- **Shared memory:** The Docker guide recommends `--ipc=host` or a sufficient `--shm-size` because PyTorch uses shared memory, especially for tensor-parallel workloads.
- **Optional dependencies:** The official image does not include every optional dependency. For example, audio extras or newer Hugging Face Transformers versions may require a custom image matching the chosen vLLM version.
- **Kubernetes:** The [Kubernetes guide](https://docs.vllm.ai/en/latest/deployment/k8s/) documents Deployment/Service-style serving and related ecosystem integrations. It notes CPU examples are for demonstration/testing and are not equivalent to GPU inference performance.
- **vLLM Production Stack:** The official [Production Stack](https://docs.vllm.ai/en/latest/deployment/integrations/production-stack/) is a Kubernetes/Helm-oriented deployment stack. Documented capabilities include Grafana dashboards, multi-model support, model-aware and prefix-aware routing, faster bootstrapping, and LMCache KV-cache offloading via `--kv-offloading-backend lmcache`.
- **Multi-node scaling:** The [parallelism/scaling guide](https://docs.vllm.ai/en/latest/serving/parallelism_scaling/) documents Ray as an optional runtime for multi-node deployments and describes common tensor-parallel and pipeline-parallel layouts.
- **Data parallel serving:** The [data-parallel deployment guide](https://docs.vllm.ai/en/latest/serving/data_parallel_deployment/) documents data parallelism as replicated model weights across instances/GPUs for independent batches; it can be combined with tensor parallelism and has internal, hybrid, and external load-balancing modes.

### Hardware and runtime requirements

The official [installation overview](https://docs.vllm.ai/en/latest/getting_started/installation/) lists supported hardware families:

- NVIDIA CUDA GPUs
- AMD ROCm GPUs
- Intel XPU GPUs
- Apple Silicon via vLLM-Metal
- CPU on Intel/AMD x86, ARM AArch64, Apple silicon, and IBM Z S390X
- Additional third-party hardware plugins

Documented GPU requirements and constraints from the [GPU installation guide](https://docs.vllm.ai/en/latest/getting_started/installation/gpu/) include:

- Linux is the supported operating system for GPU packages.
- Python 3.10 through 3.13 is supported.
- There is no native Windows support; WSL or community forks are the documented alternatives.
- NVIDIA precompiled binaries target CUDA 12.9.
- NVIDIA GPU support requires compute capability 7.5 or newer; documented examples include T4, RTX 20xx, A100, L4, H100, and B200-class hardware.
- ROCm support requires ROCm 6.3 or newer. Official ROCm wheels are documented for ROCm 7.0 and 7.2.1 with Python 3.12, and the `rocm700` wheel requires glibc 2.35 or newer.
- The docs identify MI200, MI300, MI350, Radeon RX 7900/9000, and Ryzen AI MAX/AI 300-class AMD hardware. Some newer AMD families require newer ROCm versions.
- Intel XPU support initially covers basic model inference and serving and uses `vllm-xpu-kernels`. The XPU wheel is Python-3.12-specific.
- Apple Silicon support is through the community-maintained vLLM-Metal plugin using MLX; it supports an OpenAI-compatible server but is not the same deployment target as the core CUDA/ROCm/XPU paths.
- vLLM recommends fresh Python environments because custom CUDA kernels and PyTorch binary compatibility can break when packages are mixed. The docs recommend using the bundled PyTorch version unless building vLLM from source for a different CUDA/PyTorch pairing.

Documented CPU constraints from the [CPU installation guide](https://docs.vllm.ai/en/latest/getting_started/installation/cpu/) include:

- CPU x86 supports basic inference and serving with FP32, FP16, and BF16.
- x86 CPU serving requires Linux; AVX-512 is recommended, while AVX2 has limited feature support.
- ARM CPU support depends on NEON and supports FP32, FP16, and BF16.
- macOS CPU and IBM Z S390X paths are documented as experimental/source-build paths.

### Observability surfaces

Official observability features are substantial enough to integrate with Polaris telemetry, but they should remain backend telemetry rather than a second workflow event stream.

Documented surfaces:

- The [metrics guide](https://docs.vllm.ai/en/latest/usage/metrics/) exposes Prometheus metrics at `/metrics` on the OpenAI-compatible API server.
- Metrics include request success counts, prompt and generation token counters, prefix-cache hit/query counters, multimodal-cache counters, preemption counters, and corrupted-request counters.
- The [metrics design](https://docs.vllm.ai/en/latest/design/metrics/) separates server-level and request-level metrics and identifies Prometheus metrics as the production-oriented export path, with log metrics more useful for development/debugging.
- The [OpenTelemetry example](https://docs.vllm.ai/en/latest/examples/observability/opentelemetry/) shows `vllm serve` using `--otlp-traces-endpoint` plus OpenTelemetry environment variables to export traces to an OTLP collector and propagate trace context from client requests.
- The [Prometheus/Grafana example](https://docs.vllm.ai/en/latest/examples/observability/prometheus_grafana/) states that Prometheus metric logging is enabled by default in the OpenAI-compatible server and demonstrates a Grafana dashboard.
- The OpenAI-compatible server can optionally accept and return request IDs through the `X-Request-Id` path when `--enable-request-id-headers` is set.

### Security and exposure constraints

The official [security guide](https://docs.vllm.ai/en/latest/usage/security/) is the most important operational caveat for Polaris.

Documented facts:

- vLLM uses `torch.distributed` for distributed communication, even on a single host. Its TCPStore behavior listens broadly by default, so vLLM deployments need explicit network isolation.
- The guide recommends exposing only the API server port and limiting internal distributed/KV-cache-transfer ports to trusted hosts.
- `--api-key` or `VLLM_API_KEY` authentication applies only to OpenAI-compatible and similar protected endpoint prefixes, not to every HTTP route served by vLLM.
- Protected endpoints include `/v1/models`, `/v1/chat/completions`, `/v1/chat/completions/batch`, `/v1/completions`, `/v1/embeddings`, `/v1/audio/transcriptions`, `/v1/audio/translations`, `/v1/responses`, `/v1/score`, `/v1/rerank`, and several related `/v2` or `/inference` endpoints.
- Several sensitive endpoints remain unprotected by `--api-key`, including non-`/v1` inference-style endpoints such as `/invocations`, `/pooling`, `/classify`, `/score`, and `/rerank`, plus operational controls such as pause/resume/abort/update-weights paths and utility endpoints such as tokenize/detokenize/health/ping/version/load.
- The docs specifically warn not to rely exclusively on vLLM `--api-key` and recommend a reverse proxy that allowlists only required endpoints, blocks everything else, and adds authentication, rate limiting, and logging.
- Development mode, profiler endpoints, and optional tokenizer-info surfaces should not be enabled in production unless intentionally protected.
- vLLM resource consumption can be affected by request parameters such as `n`. vLLM enforces `VLLM_MAX_N_SEQUENCES` with a high default; the docs recommend lower values for public-facing deployments.
- vLLM tool servers and MCP-related functionality are opt-in through `--tool-server`; demo tools require an additional package. They are not part of the default serving path.
- vLLM is not automatically FIPS-compliant. The docs identify hash/cipher knobs, but also note that internal inter-node communication is unencrypted by default and would require external encryption mechanisms for strict transit requirements.

The [serve CLI](https://docs.vllm.ai/en/latest/cli/serve/) also exposes CORS and TLS-related controls:

- `--allowed-origins`, `--allowed-methods`, and `--allowed-headers` default broadly.
- Server args include `--api-key`, SSL key/cert/CA/client-cert/cipher options, root path, middleware, request-ID header support, FastAPI docs disabling, and HTTP parser limits.

### LiteLLM integration patterns

Official LiteLLM documentation provides the integration path that best matches Polaris' existing LLM gateway assumptions.

From the LiteLLM [vLLM provider docs](https://docs.litellm.ai/docs/providers/vllm):

- LiteLLM supports vLLM through a hosted OpenAI-compatible route using the `hosted_vllm/` model prefix.
- The old `vllm/` SDK path is documented as deprecated for vLLM SDK usage.
- Supported LiteLLM-to-vLLM endpoints include chat completions, embeddings, completions, rerank, and audio transcriptions.
- SDK usage supplies `model="hosted_vllm/<model-name>"` and `api_base=<vllm-server-base-url>`.
- LiteLLM Proxy usage defines a `model_list` entry with a user-facing `model_name` alias and `litellm_params.model: hosted_vllm/<model-name>` plus `api_base`.
- Clients call the LiteLLM proxy alias rather than the vLLM model name directly.
- LiteLLM documents rerank support using `hosted_vllm/<rerank-model>`, `api_base`, and optional `api_key`.
- LiteLLM documents vLLM embeddings through the OpenAI-compatible `/v1/embeddings` endpoint.

From the LiteLLM [OpenAI-compatible provider docs](https://docs.litellm.ai/docs/providers/openai_compatible):

- LiteLLM can also route to OpenAI-compatible servers through the `openai/` or `text-completion-openai/` provider prefixes.
- LiteLLM recommends using a direct matching provider such as `hosted_vllm` when possible.
- For generic OpenAI-compatible routing, the docs caution that the base URL may need the `/v1` postfix and that endpoint suffixes should not be duplicated in `api_base`.

From the LiteLLM [overview](https://docs.litellm.ai/):

- LiteLLM can operate as both a proxy/gateway and an SDK/router.
- Documented gateway features include authentication/authorization, virtual keys, spend tracking, logging, guardrails, caching, and an admin dashboard.
- Documented router features include retries, fallbacks, load balancing, cost tracking, exception mapping, and observability callbacks.

## Polaris-specific recommendations and inferences

The items below are recommendations or architectural inferences for Polaris. They are not direct promises from vLLM or LiteLLM.

### 1. Keep vLLM behind Polaris' existing LLM boundary

Polaris should evaluate vLLM as a backend/profile behind logical model aliases and LiteLLM routing. Intelligence, runtime, reporting, RAG, MCP, and workflow code should not call vLLM SDKs or vLLM HTTP endpoints directly.

Recommended shape:

```text
Polaris logical alias, e.g. polaris-local-fast
→ LiteLLM proxy model_name
→ litellm_params.model: hosted_vllm/<exact-vllm-model>
→ private vLLM OpenAI-compatible server
```

This preserves the current architecture: Polaris application services coordinate use cases, LiteLLM remains the gateway/provider boundary, and vLLM remains a replaceable serving backend.

### 2. Use hosted_vllm rather than the deprecated LiteLLM vLLM SDK route

If Polaris adds a vLLM-backed profile, prefer LiteLLM's `hosted_vllm/` provider prefix. Avoid the deprecated `vllm/` SDK path because it would push local runtime/package coupling into the client side and make Polaris code or environments aware of vLLM internals.

### 3. Treat generation, embedding, and reranking as separate serving profiles

Because vLLM serving instances are model/runner/task-oriented, Polaris should not assume one vLLM instance can satisfy chat, embeddings, and reranking for all model families. Plan separate LiteLLM aliases and vLLM instances for:

- chat/completion generation
- structured-output or tool-call-sensitive generation, if it needs stricter validation
- embeddings
- reranking/scoring
- audio transcription/translation, if ever used

### 4. Do not move RAG orchestration into vLLM

vLLM can serve embedding and reranking inference, but it is not the RAG authority. Polaris should keep curated RAG records in PostgreSQL, retrieval projections in Qdrant/Neo4j, and orchestration/eligibility/ranking policy in canonical application services.

### 5. Put vLLM on a private network behind LiteLLM and/or a reverse proxy

vLLM `--api-key` is insufficient as the only control because official docs list unauthenticated inference-like and operational endpoints. For any non-local deployment:

- bind vLLM to private interfaces only
- expose only LiteLLM or a hardened reverse proxy to callers
- allowlist needed endpoints, usually `/v1/chat/completions`, `/v1/completions`, `/v1/embeddings`, `/v1/rerank` or `/v1/score`, `/metrics`, and `/health` as appropriate
- block non-OpenAI inference endpoints and operational controls from untrusted callers
- set explicit CORS, TLS, request size, rate limit, timeout, and logging policies outside vLLM
- lower request-expansion limits such as `VLLM_MAX_N_SEQUENCES` for any shared environment

### 6. Start production evaluation on CUDA unless there is a deliberate hardware reason not to

CUDA GPUs are the clearest primary path in the official docs. ROCm and XPU may be viable, but they add version, Python, glibc, kernel, and feature-matrix validation requirements. CPU, Apple Silicon, and community plugin routes can be useful for development or demos, but should not be assumed equivalent to production GPU serving.

### 7. Pin the serving stack

Avoid floating `latest` images for reproducible Polaris environments. A real rollout should pin:

- vLLM version or image digest
- model revision
- CUDA/ROCm/XPU runtime version
- Python version if using wheels/source builds
- LiteLLM proxy version
- tokenizer/chat template behavior
- generation-config behavior (`auto` versus `vllm` defaults)

### 8. Validate model behavior through LiteLLM, not through direct vLLM calls

Before enabling a Polaris alias, validate the behavior at the LiteLLM boundary:

- model appears through the configured LiteLLM route
- chat completions work for Polaris prompt shapes
- structured JSON/tool-call behavior works for required schemas
- embeddings produce dimensions and normalization expected by downstream retrieval policy
- reranking/scoring endpoint shape matches Polaris' expected ranking result contract
- token limits, context length, stop behavior, and generation defaults are explicit
- request IDs and telemetry correlation survive the Polaris → LiteLLM → vLLM path

### 9. Integrate observability once at the platform boundary

vLLM Prometheus metrics and OTLP traces are useful backend signals. Polaris should ingest or scrape them as infrastructure/backend metrics while preserving runtime events, workflow evidence, and application telemetry as the canonical business-level observability layer.

Useful vLLM metrics for Polaris capacity planning include request success, prompt tokens, generation tokens, cached prompt tokens, prefix-cache hit/query counters, preemptions, and corrupted requests.

### 10. Treat vLLM tool servers as out of scope for Polaris workflow tools

vLLM tool calling in chat completions can support structured tool-call-shaped outputs. That is different from delegating Polaris tools, MCP servers, or workflow actions to vLLM. Polaris should not expose or rely on vLLM `--tool-server` for platform actions unless a separate architecture decision approves that boundary.

## Operational caveats to carry into future implementation tickets

- vLLM endpoint behavior is not identical to OpenAI. Unsupported or ignored parameters such as `suffix`, `user`, and `image_url.detail` must be accounted for at the gateway/profile layer.
- Model repository `generation_config.json` can silently affect defaults unless the serving profile explicitly chooses vLLM defaults.
- Structured output validity is not the same as answer correctness; Polaris must keep existing validation and governance checks.
- Rerank/scoring support depends on model/task configuration and changed in recent vLLM versions; confirm selected reranker models against the current pooling/scoring docs.
- Distributed serving exposes extra internal ports and unencrypted internal traffic unless external network controls are added.
- Docker deployments need shared-memory planning (`--ipc=host` or `--shm-size`) and may need custom images for optional audio/multimodal dependencies.
- Kubernetes production serving should not be inferred from the CPU demo. GPU scheduling, model cache persistence, rollout strategy, and metrics/log collection require separate design.
- Public exposure requires a reverse proxy/API gateway in front of vLLM even when vLLM API keys are configured.

## Conclusion

vLLM can serve Polaris-relevant local or self-hosted model profiles for generation, structured/tool-call chat, embeddings, reranking/scoring, and selected audio workloads. The safest Polaris posture is to keep vLLM as a private serving backend behind LiteLLM and existing logical aliases, with separate profiles per task/runner, pinned versions, explicit security hardening, and observability wired into the existing platform telemetry boundary.

No Polaris implementation work should be done until a follow-up design ticket selects exact model families, hardware targets, LiteLLM aliases, endpoint allowlists, observability wiring, and rollout/rollback procedures.
