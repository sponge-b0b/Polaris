# Model Gateway & Profile Policy (Entity ID: model-gateway-profile-policy)

**Boundary Rationale:** The gateway/profile policy has independent invariants: logical aliases instead of concrete models in code, no silent fallback, central routing through LiteLLM, and profile-based operational constraints.
(source: owner-approved entity promotion)

### Strict Invariants

* Polaris calls its typed LLM provider and core gateway, which call the LiteLLM-compatible client and proxy, because model access must be centralized behind typed platform contracts. (source: docs/current/model-gateway-profile-policy-litellm-gateway.md)
* Polaris owns typed requests, typed results, telemetry, retries at the provider boundary, RAG orchestration, prompt provenance, and persistence; LiteLLM owns provider normalization, model aliases, backend routing, authentication, and request translation, because gateway and application responsibilities differ. (source: docs/current/model-gateway-profile-policy-litellm-gateway.md)
* Code and runtime configuration use logical model aliases and model profiles instead of hardcoding concrete backend replacements, because model allocation must remain operational policy rather than call-site behavior. (source: docs/current/model-gateway-profile-policy-model-profiles.md)
* Silent fallback is prohibited when `POLARIS_LITELLM_REJECT_MODEL_FALLBACK=true`; diagnostic fallback must be visible in metadata and cannot by itself validate canonical model replacement, because fallback changes evaluation and production semantics. (source: docs/current/model-gateway-profile-policy-model-profiles.md)

### Planned

* **Additional profile routing, provider allocation, and model-platform expansion** — proposed, not yet accepted. (source: docs/proposed/platform-future-architecture.md)
