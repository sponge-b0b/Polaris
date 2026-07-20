# Polaris LiteLLM Gateway

Polaris uses LiteLLM as the canonical LLM gateway. Polaris does not call local Ollama, OpenAI, Anthropic, or other model providers directly from application, RAG, or intelligence code. Provider-specific model routing belongs behind the LiteLLM proxy.

## Architecture

```text
Polaris application / RAG / intelligence service
    → typed Polaris LLM provider or core LLM gateway protocol
    → LiteLLM OpenAI-compatible client
    → LiteLLM proxy
    → configured model backend, such as local Ollama
```

Polaris owns typed requests, typed results, telemetry, retries at the provider boundary, RAG orchestration, prompt provenance, and persistence. LiteLLM owns provider normalization, model aliases, backend routing, backend authentication, and provider-specific request translation.

## Required services for local operation

For local LLM-backed Polaris features, run:

- Ollama on the host at `http://localhost:11434`, with the configured local models pulled.
- LiteLLM from Docker Compose on `http://localhost:4000/v1`.

Optional services depend on the workflow being tested:

- PostgreSQL for persisted workflow, RAG, evaluation, and telemetry records.
- Qdrant and Neo4j for full RAG retrieval/projection validation.
- BGE reranker for reranking validation.
- Langfuse for AI-observability export validation.

## Local startup

1. Confirm Ollama is reachable from the host and has the configured models:

   ```bash
   curl http://localhost:11434/api/tags
   ```

2. Configure `POLARIS_LITELLM_API_KEY` in local environment or `.env` when the LiteLLM proxy is running with a master key.
   For local Docker development, `docker-compose.yml` falls back to `polaris-local-dev-key` when `POLARIS_LITELLM_API_KEY` is unset; the Polaris client uses the same local fallback. Use an explicit non-default key outside local development.

   If LiteLLM runs in Docker and Ollama runs on the host, Ollama must be reachable from the container. On Linux/WSL, a host Ollama server bound only to `127.0.0.1:11434` is not reachable from Docker. Restart Ollama with `OLLAMA_HOST=0.0.0.0:11434` or set `POLARIS_LITELLM_OLLAMA_API_BASE` to an endpoint the container can reach.

3. Start the LiteLLM proxy:

   ```bash
   docker compose up -d litellm
   ```

4. Confirm the proxy exposes the configured model aliases:

   ```bash
   curl -H "Authorization: Bearer $POLARIS_LITELLM_API_KEY" \
     http://localhost:4000/v1/models
   ```

## Configuration

Polaris application settings:

| Variable | Purpose |
| --- | --- |
| `POLARIS_LITELLM_ENABLED` | Enables the LiteLLM gateway feature gate. |
| `POLARIS_LITELLM_BASE_URL` | OpenAI-compatible LiteLLM base URL, usually `http://localhost:4000/v1`. |
| `POLARIS_LITELLM_API_KEY` | Proxy API key used by Polaris clients. Do not commit real values. |
| `POLARIS_LITELLM_TIMEOUT_SECONDS` | Request timeout for LiteLLM-backed calls. This value is also recorded in sanitized operation metadata. |
| `POLARIS_LITELLM_MAX_CONCURRENCY` | Polaris-side concurrency cap for local LiteLLM gateway calls. Defaults to `1` for predictable 8GB-VRAM execution. |
| `POLARIS_LITELLM_REQUEST_BUDGET_TOKENS` | Default and maximum completion token budget enforced by the Polaris gateway client. Defaults to `4096`. |
| `POLARIS_LITELLM_REJECT_MODEL_FALLBACK` | Rejects alias/model fallback by default. Set to `false` only when an approved gateway profile intentionally reports backend model names while preserving visible fallback metadata. |
| `POLARIS_LITELLM_STRICT_MODE` | Requires complete gateway configuration during settings validation. |
| `POLARIS_LITELLM_OLLAMA_API_BASE` | LiteLLM-container-reachable Ollama API base used by `config/litellm/config.yaml`. |

LiteLLM model aliases are defined in `config/litellm/config.yaml`. Polaris source defaults use logical aliases such as `polaris-local-fast`, `polaris-local-structured`, and `polaris-local-synthesis`; LiteLLM maps those aliases to concrete local backends such as Ollama `qwen2.5:7b` or `qwen3.5:4b`. Change the LiteLLM alias mapping for model-operations tuning instead of hard-coding concrete model names in application defaults.

The Polaris client enforces a local operations policy before and after each gateway call:

- missing `max_tokens` is filled with `POLARIS_LITELLM_REQUEST_BUDGET_TOKENS`;
- requested `max_tokens` values above the configured budget fail before a model call starts;
- concurrent gateway calls are bounded by `POLARIS_LITELLM_MAX_CONCURRENCY`;
- timeout and budget settings are attached to result metadata for observability;
- response-model mismatch is rejected by default so LiteLLM fallback cannot silently change model behavior.

DeepEval defaults to `POLARIS_DEEPEVAL_MAX_CONCURRENCY=1` for the same low-VRAM local profile. Raise model concurrency only after validating the active machine and model set.

## Observability and failure behavior

LiteLLM-backed Polaris providers emit canonical integration telemetry through the provider telemetry wrapper. Recorded attributes include:

- `provider_name="litellm"`
- semantic operation name
- logical configured model name
- request identifier when available
- success or failure status
- latency
- normalized error type and safe error message

Secrets must not be included in logs, telemetry payloads, plan files, docs, or test assertions. Client-level exceptions are normalized to safe Polaris gateway errors before provider telemetry records failure details.

## Local smoke validation

A narrow operational smoke test should verify:

1. LiteLLM model-list endpoint responds through the configured API key.
2. RAG structured query routing can obtain a JSON object through LiteLLM.
3. RAG answer generation can obtain text through LiteLLM.
4. Instructor or DeepEval can make a narrow gateway-backed call when configured.

Full RAG validation additionally requires the RAG datastore services and corpus/projection state required by the specific test.
