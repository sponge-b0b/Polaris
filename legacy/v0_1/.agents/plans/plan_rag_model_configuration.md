  # RAG Model Configuration Convention

  ## Summary

  Configure RAG models by semantic operation, not layer number.

  Avoid names such as:

  RAG_LAYER_2_MODEL
  RAG_LAYER_3_MODEL

  Layer numbering describes the current pipeline topology, but operation names describe stable responsibilities. Layers may later be reordered, split, or contain multiple model calls.

  Repeated model values are intentional. Although several operations currently use qwen3.5:4b, each operation should have an independent setting so it can change without affecting the others.

  ## Recommended Settings

  Add RAG-specific defaults and settings to config/settings.py:

  DEFAULT_RAG_QUERY_REWRITE_MODEL = "qwen2.5:7b"
  DEFAULT_RAG_ADAPTIVE_TRIAGE_MODEL = "qwen2.5:7b"
  DEFAULT_RAG_ROUTE_SELECTION_MODEL = "qwen3.5:4b"
  DEFAULT_RAG_HYDE_MODEL = "qwen3.5:4b"

  DEFAULT_RAG_HYBRID_EMBEDDING_MODEL = "bge-m3:567m"
  DEFAULT_RAG_RERANKER_MODEL = "BAAI/bge-reranker-large"
  DEFAULT_RAG_RERANKER_ENDPOINT = "http://localhost:8080/rerank"

  DEFAULT_RAG_CRAG_GRADER_MODEL = "qwen3.5:4b"
  DEFAULT_RAG_CRAG_QUERY_REWRITE_MODEL = "qwen3.5:4b"

  DEFAULT_RAG_SELF_REFLECTION_MODEL = "qwen3.5:4b"
  DEFAULT_RAG_SYNTHESIS_MODEL = "qwen3.5:4b"

  Corresponding environment-backed fields:

  class Settings(BaseSettings):
      RAG_QUERY_REWRITE_MODEL: str = DEFAULT_RAG_QUERY_REWRITE_MODEL
      RAG_ADAPTIVE_TRIAGE_MODEL: str = DEFAULT_RAG_ADAPTIVE_TRIAGE_MODEL
      RAG_ROUTE_SELECTION_MODEL: str = DEFAULT_RAG_ROUTE_SELECTION_MODEL
      RAG_HYDE_MODEL: str = DEFAULT_RAG_HYDE_MODEL

      RAG_HYBRID_EMBEDDING_MODEL: str = DEFAULT_RAG_HYBRID_EMBEDDING_MODEL
      RAG_RERANKER_MODEL: str = DEFAULT_RAG_RERANKER_MODEL
      RAG_RERANKER_ENDPOINT: str = DEFAULT_RAG_RERANKER_ENDPOINT

      RAG_CRAG_GRADER_MODEL: str = DEFAULT_RAG_CRAG_GRADER_MODEL
      RAG_CRAG_QUERY_REWRITE_MODEL: str = (
          DEFAULT_RAG_CRAG_QUERY_REWRITE_MODEL
      )

      RAG_SELF_REFLECTION_MODEL: str = DEFAULT_RAG_SELF_REFLECTION_MODEL
      RAG_SYNTHESIS_MODEL: str = DEFAULT_RAG_SYNTHESIS_MODEL

  The settings may be grouped with comments identifying their current layers, but layer numbers should not be part of the field names.

  ## Operation Mapping

   Pipeline responsibility                      Setting                         Initial model
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━
   Layer 1 standalone query rewriting           RAG_QUERY_REWRITE_MODEL         qwen2.5:7b
  ───────────────────────────────────────────  ──────────────────────────────  ─────────────────────────
   Layer 2 complexity/adaptive triage           RAG_ADAPTIVE_TRIAGE_MODEL       qwen2.5:7b
  ───────────────────────────────────────────  ──────────────────────────────  ─────────────────────────
   Layer 3 retrieval-route selection            RAG_ROUTE_SELECTION_MODEL       qwen3.5:4b
  ───────────────────────────────────────────  ──────────────────────────────  ─────────────────────────
   Layer 3 deep-research HyDE generation        RAG_HYDE_MODEL                  qwen3.5:4b
  ───────────────────────────────────────────  ──────────────────────────────  ─────────────────────────
   Layer 4 dense and learned-sparse encoding    RAG_HYBRID_EMBEDDING_MODEL      bge-m3:567m
  ───────────────────────────────────────────  ──────────────────────────────  ─────────────────────────
   Layer 4 cross-encoder reranking              RAG_RERANKER_MODEL              BAAI/bge-reranker-large
  ───────────────────────────────────────────  ──────────────────────────────  ─────────────────────────
   Layer 5 evidence/relevance grading           RAG_CRAG_GRADER_MODEL           qwen3.5:4b
  ───────────────────────────────────────────  ──────────────────────────────  ─────────────────────────
   Layer 5 corrective query rewriting           RAG_CRAG_QUERY_REWRITE_MODEL    qwen3.5:4b
  ───────────────────────────────────────────  ──────────────────────────────  ─────────────────────────
   Layer 6 Self-RAG critique/reflection         RAG_SELF_REFLECTION_MODEL       qwen3.5:4b
  ───────────────────────────────────────────  ──────────────────────────────  ─────────────────────────
   Layer 6 final answer synthesis               RAG_SYNTHESIS_MODEL             qwen3.5:4b

  Do not add a generic RAG_MEMORY_CONTEXT_MODEL unless Layer 1 introduces an actual independent memory summarization or context-compression model call.

  ## Implementation Changes
      - Replace the current combined CLASSIFY operation with independent adaptive-triage and route-selection operations.
      - Each operation receives its own prompt, structured result contract, model setting, trace span, and telemetry attributes.
      - This allows Layer 2 to use qwen2.5:7b while Layer 3 uses qwen3.5:4b.

  2. Pass model identities explicitly
      - Providers should receive the model identifier through constructor-injected typed configuration.
      - Do not let RAG providers implicitly use OllamaClient.llm_model, DEFAULT_MODEL, FAST_MODEL, or REASONING_MODEL.
      - Pass the selected model through OllamaClient.generate_json(..., model=model_id).

  3. Introduce a typed internal configuration
      - Build an immutable RagModelConfig at the composition boundary from Settings.
      - Keep environment-variable handling in Settings; use the typed configuration inside the RAG subsystem.
      - Include every operation-specific model and the reranker endpoint/model identity.

  4. Record actual model use
      - Telemetry and persisted query execution metadata should include:
          - semantic operation;
          - configured model;
          - provider;
          - latency;
          - success or failure.

      - The recorded model must be the model passed to the provider, not merely the Ollama client's default.

  5. Implement true BGE-M3 hybrid vectors
      - Layer 4 will use BGE-M3 learned dense and sparse representations rather than treating BM25 as the BGE-M3 sparse output.
      - Qdrant should store named dense and sparse vectors.
      - BM25 may remain only if deliberately retained as an auxiliary lexical retriever; it should not be described as BGE-M3 sparse retrieval.

  6. Clarify existing general settings
      - Keep DEFAULT_MODEL, FAST_MODEL, and REASONING_MODEL for non-RAG consumers.
      - Replace the ambiguous RAG use of EMBEDDING_MODEL with RAG_HYBRID_EMBEDDING_MODEL.
      - Replace BGE_RERANKER_ENDPOINT with the vendor-neutral RAG_RERANKER_ENDPOINT.
      - Refactor current consumers directly rather than adding permanent legacy aliases.

  ## Test Plan

  - Verify every RAG setting can be independently overridden through environment variables.
  - Verify query rewriting and adaptive triage use qwen2.5:7b.
  - Verify routing, HyDE, CRAG, reflection, and synthesis use their explicit operation settings.
  - Verify changing one model setting does not affect another operation.
  - Verify triage and route selection have separate structured result contracts and telemetry.
  - Verify telemetry reports the actual selected model rather than the client's default.
  - Verify BGE-M3 returns and persists both dense and learned-sparse representations.
  - Verify the reranker records both its configured endpoint and BAAI/bge-reranker-large model identity.
  - Run targeted RAG unit/integration tests, Ruff, MyPy, and Graphify update.

  ## Assumptions

  - Layer 2 triage and Layer 3 routing will be separate model calls.
  - Layer 4 means true BGE-M3 dense plus learned-sparse retrieval, not BGE-M3 dense plus BM25.
  - BGE-Reranker-Large remains externally hosted at the configured reranker endpoint.
  - Separate settings with identical initial values are intentional and provide future per-operation model independence.

  
## Step Results

### Step 1 — Separate adaptive triage from route selection

- Replaced the combined `CLASSIFY` model operation with independent `ADAPTIVE_TRIAGE` and `ROUTE_SELECTION` operations.
- Replaced the combined `RagComplexityClassification` contract with typed `RagAdaptiveTriage` and `RagRouteSelection` domain objects.
- Updated `RagQueryRoutingDecision` to carry triage and route-selection results independently, with HyDE still restricted to the deep-research route.
- Split the combined prompt and strict JSON contract into a complexity-only triage prompt and a route-only selection prompt.
- Passed the typed triage complexity into the route-selection prompt so the router can make an informed independent decision.
- Updated exports and fail-closed unit coverage for invalid triage and invalid route-selection outputs.
- Verification: targeted Ruff checks passed; 15 focused query-routing/provider tests passed.

### Step 2 — Pass query-routing model identities explicitly

- Added immutable `RagQueryModelConfig` with independent model identities for query rewriting, adaptive triage, route selection, and HyDE generation.
- Made `OllamaRagQueryModelProvider` require the typed model configuration through constructor injection.
- Selected the configured model from the semantic `RagQueryModelOperation` and passed it explicitly to `OllamaClient.generate_json(..., model=model)`.
- Updated `RagQueryModelResult.model` to report the actual selected operation model instead of `OllamaClient.llm_model`.
- Added validation that rejects empty model identities and parameterized coverage proving all four operations use their own configured models.
- Left `core/llm/ollama_client.py` unchanged because its existing per-call model override already satisfies the required core contract.
- Verification: 22 focused query-routing tests passed; targeted Ruff checks, formatting, and MyPy passed.

### Step 3 — Introduce complete typed RAG model configuration

- Added immutable, slotted `RagModelConfig` as the internal model-configuration contract for every planned RAG operation plus the reranker endpoint and model identity.
- Added independent environment-backed `Settings` fields for query rewriting, adaptive triage, route selection, HyDE, hybrid embedding, reranking, CRAG grading, CRAG rewriting, self-reflection, and synthesis.
- Added `RagModelConfig.from_settings(...)` so environment parsing remains at the settings boundary while internal RAG composition consumes a strongly typed object.
- Exposed the existing `RagQueryModelConfig` as a typed query-routing subset rather than duplicating provider mapping logic.
- Updated the active CLI RAG composition boundaries to build `RagModelConfig` once and use its hybrid-embedding and reranker-endpoint values for retriever and projection construction.
- Added deterministic tests for defaults, independent environment overrides, query-routing subset mapping, and frozen configuration behavior.
- Kept the pre-existing generic `EMBEDDING_MODEL` and `BGE_RERANKER_ENDPOINT` fields untouched in this step because direct consumer migration and removal are explicitly owned by Step 6; no compatibility adapter or alias was introduced.
- Verification: 37 focused configuration, query-routing, provider, and CLI tests passed; targeted Ruff and formatting checks passed; focused MyPy passed; full-project MyPy passed across 990 source files.

### Step 4 — Record actual RAG model execution metadata

- Extended the canonical provider telemetry wrapper so provider calls may attach operation-specific structured attributes and payloads on both success and failure without changing existing callers.
- Updated the Ollama query-routing provider to emit the semantic operation, actual configured model passed to Ollama, provider identity, request correlation ID, measured latency, and success/failure outcome.
- Expanded `RagQueryModelResult` so successful model calls return their actual model, provider, duration, and outcome rather than relying on the Ollama client's default model identity.
- Added immutable `RagQueryModelExecution` records to routing decisions for query rewriting, adaptive triage, route selection, and HyDE generation when those operations execute.
- Added serialization-ready routing-decision metadata and included it in application RAG completion/failure telemetry.
- Reused the existing PostgreSQL RAG query-log JSON metadata boundary instead of introducing a parallel execution-log table or modifying core persistence contracts; a focused service test proves the model execution records survive query-log persistence under `request_metadata`.
- Verification: 35 focused telemetry/routing/persistence tests passed; 127 broader RAG/provider/config/CLI tests passed; targeted Ruff checks and formatting passed; focused MyPy passed; full-project MyPy passed across 990 source files.

### Step 5 — Implement true BGE-M3 hybrid vectors

- Added the native `FlagEmbedding` BGE-M3 client/provider path and changed the active RAG composition to use `BAAI/bge-m3`, which emits both the model's dense vectors and learned lexical sparse weights.
- Replaced the internal dense-only embedding contract with typed `EmbeddingVector` and `SparseEmbeddingVector` contracts; ingestion and retrieval now carry both representations without boundary dictionaries.
- Changed the canonical BGE-M3 dense dimension from the obsolete 1536 setting to the model's actual 1024 dimensions.
- Updated Qdrant projection storage to named `dense` and `sparse` vectors and implemented hybrid retrieval with dense and sparse prefetches fused by Qdrant reciprocal-rank fusion (RRF).
- Kept PostgreSQL BM25 retrieval deliberately as an auxiliary lexical signal; it is no longer described or treated as BGE-M3 learned-sparse retrieval.
- Rewired CLI retrieval and queued embedding processing to `BgeM3EmbeddingProvider`; the dense-only Ollama provider is no longer exported or used by active composition and now fails closed if invoked.
- Added `FlagEmbedding` through `uv` and added deterministic client/provider, Qdrant translation/fusion, embedding-job, retriever, configuration, and CLI coverage.
- Existing Qdrant collections created with the former unnamed dense-vector schema must be recreated through the existing projection rebuild operation before hybrid ingestion/search. No live collection was destructively recreated during this step.
- Verification: 26 focused hybrid-vector tests passed; 133 broader RAG/config/provider/CLI tests passed; targeted Ruff checks and formatting passed; focused MyPy passed; full-project MyPy passed across 994 source files; Graphify was updated.

### Step 6 — Clarify existing general settings

- Migrated `CuratedRagBuildOptions` from the generic `DEFAULT_EMBEDDING_MODEL` to the semantic `DEFAULT_RAG_HYBRID_EMBEDDING_MODEL`, so queued RAG jobs now default explicitly to `BAAI/bge-m3`.
- Removed the obsolete `DEFAULT_BGE_RERANKER_ENDPOINT` and `Settings.BGE_RERANKER_ENDPOINT`; the live reranker integration test now consumes the vendor-neutral `RAG_RERANKER_ENDPOINT` setting.
- Retained `DEFAULT_EMBEDDING_MODEL` and `Settings.EMBEDDING_MODEL` only for the general, non-RAG `OllamaClient.embeddings()` default. The churn-heavy core client did not require modification.
- Added tests proving the canonical RAG hybrid-embedding default, intentional retention of the general embedding setting, and removal of the legacy BGE-specific endpoint setting.
- Introduced no compatibility aliases, adapters, or shims.
- Verification: 45 focused tests passed; 135 broader RAG/config/provider/CLI tests passed; targeted Ruff checks and formatting passed; focused MyPy passed; full-project MyPy passed across 993 source files; `git diff --check` passed; Graphify was updated.
