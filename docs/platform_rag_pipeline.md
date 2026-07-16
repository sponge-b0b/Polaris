# Platform-Native RAG Pipeline

Polaris's RAG pipeline turns curated PostgreSQL records into grounded research
answers. PostgreSQL is the system of record. Qdrant and Neo4j are derived,
rebuildable projections; SearXNG + Crawl4AI web fallback results are transient
corrective evidence and never become canonical records automatically.

The pipeline follows the platform's inside-out architecture: canonical
application services own the use case, integration providers own external
stores/models, and runtime/MCP/CLI layers remain thin transport boundaries.

## Architecture patterns and justification

### System-of-record plus rebuildable projections

PostgreSQL is the only canonical RAG authority. Curated source records are
converted into `rag_documents`, deterministic `rag_chunks`, and queued projection
jobs. Qdrant and Neo4j are intentionally derived projections: they can be
deleted, recreated, or left temporarily unavailable without losing source
content, lineage, query logs, or answer logs.

This pattern keeps retrieval stores optimized for search while preventing them
from becoming competing systems of record. It also makes destructive operations
safe: a Qdrant rebuild recreates the configured collection from PostgreSQL
embedding jobs, and a Neo4j rebuild clears only the configured projection before
replaying graph jobs.

### Runtime-first service boundary

RAG behavior is exposed through application services and the runtime uses those
same services through `RagResearchNode`. CLI and MCP transports should resolve
the canonical services through DI instead of opening their own PostgreSQL,
Qdrant, Neo4j, SearXNG, Crawl4AI, embedding, or reranking clients.

This preserves the platform rule that higher-level transport code must not
create a parallel runtime, persistence layer, or retrieval implementation.
Runtime nodes work with typed RAG contracts internally and serialize only at the
runtime boundary.

### Provider-owned infrastructure access

External infrastructure access is isolated behind integration providers:
PostgreSQL repositories, Qdrant vector providers, Neo4j graph providers,
embedding providers, reranking providers, LiteLLM-backed model providers, and the
SearXNG + Crawl4AI web-retrieval provider. Provider calls carry canonical provider telemetry and failures remain
visible to the application service rather than being hidden in transport code.

### Determinism, replayability, and observability

Canonical document and chunk records include stable IDs, ordered chunk indexes,
content hashes, source lineage, and projection job state. Queries and answers are
persisted for successful, empty, rejected, and failed outcomes. This makes RAG
runs auditable and replay-friendly: the platform can inspect which curated
records were eligible, which chunks were retrieved, which projections were used,
and why an answer failed closed.

## Pipeline application of the patterns

```text
Curated PostgreSQL source tables
    -> RagOperationsService / CuratedRagIngestionService
    -> rag_documents / rag_chunks
    -> rag_embedding_jobs ----------> BGE-M3 ----------> Qdrant
    -> rag_graph_jobs --------------> graph extractor -> Neo4j

User query
    -> memory-aware standalone rewrite
    -> adaptive triage
    -> branched route selection
    -> optional HyDE expansion
    -> PostgreSQL lexical + structured retrieval
       + Qdrant dense/sparse retrieval
       + Neo4j relationship retrieval
    -> parent expansion and deduplication
    -> BGE cross-encoder reranking
    -> CRAG context grading
    -> optional corrective rewrite or transient SearXNG + Crawl4AI web fallback
    -> secure prompt packaging and synthesis
    -> Self-RAG reflection and output security guard
    -> rag_query_logs / rag_answer_logs
```

### Ingestion path

Ingestion starts with curated PostgreSQL business records such as reports,
agent signals, recommendations, market snapshots, macro snapshots, portfolio
snapshots, and backtest records. The builder creates typed canonical RAG records
and queues projection jobs. It does not write directly to Qdrant or Neo4j.
Projection processors then consume the queued jobs and update the derived stores.

### Twin-engine retrieval: Vector RAG plus Graph RAG

The retrieval layer is intentionally a twin-engine design:

- **Vector RAG** combines PostgreSQL lexical/structured retrieval with Qdrant
  BGE-M3 dense and sparse vector search. PostgreSQL supplies canonical candidate
  chunks and filterable metadata. Qdrant supplies semantic and sparse lexical
  matching over the projected chunk points. Qdrant hits are rehydrated from
  PostgreSQL before they become answer evidence.
- **Graph RAG** uses Neo4j for entity and relationship retrieval. Neo4j stores
  projected relationships and document/chunk references, not complete canonical
  evidence. Retrieved graph context augments the answer with relationship-aware
  paths, but evidence is still grounded back to PostgreSQL records.

This split lets the platform retrieve both semantically similar passages and
relationship-aware context without allowing either projection store to replace
PostgreSQL as the source of truth.

### Fusion, parent expansion, and reranking

The hybrid retriever ranks PostgreSQL lexical candidates and Qdrant vector hits
with deterministic fusion weights. It then expands ranked child chunks back into
parent document context, deduplicates evidence, adds structured and graph
contexts, and optionally applies the BGE cross-encoder reranker. Parent expansion
is important because the answer model receives coherent report or signal context
rather than isolated fragments.

### Corrective and reflective layers

CRAG grades the retrieved evidence before generation. If evidence is weak, the
pipeline may perform one bounded corrective rewrite and, when explicitly allowed,
request transient SearXNG + Crawl4AI web evidence. After generation, Self-RAG reflection checks
support and usefulness. Unsupported or suspicious answers are replaced by a
stable safe-failure response instead of inventing evidence.

PostgreSQL records remain authoritative if Qdrant or Neo4j is unavailable. The
projection stores may be deleted and recreated without losing canonical source
content.

## Six logical RAG layers

| Layer | Responsibility | Default model or system |
| --- | --- | --- |
| 1. Memory and context | Convert conversational input into a standalone query. | `RAG_QUERY_REWRITE_MODEL=polaris-local-fast` |
| 2. Adaptive triage | Classify query complexity. | `RAG_ADAPTIVE_TRIAGE_MODEL=polaris-local-fast` |
| 3. Branched router | Select direct, standard, or deep-research routing; deep research may use HyDE. | `RAG_ROUTE_SELECTION_MODEL=polaris-local-structured`, `RAG_HYDE_MODEL=polaris-local-reasoning` |
| 4. Twin-engine retrieval | Search PostgreSQL, BGE-M3 dense/sparse Qdrant vectors, structured records, and Neo4j relationships; rerank and expand parents. | `RAG_HYBRID_EMBEDDING_MODEL=BAAI/bge-m3`, `RAG_RERANKER_MODEL=BAAI/bge-reranker-large` |
| 5. Corrective RAG | Grade evidence, rewrite weak queries, and optionally request transient web evidence. | `RAG_CRAG_GRADER_MODEL=polaris-local-structured`, `RAG_CRAG_QUERY_REWRITE_MODEL=polaris-local-structured` |
| 6. Self-RAG and synthesis | Generate the answer, reflect on support/usefulness, and fail closed when unsafe or ungrounded. | `RAG_SYNTHESIS_MODEL=polaris-local-synthesis`, `RAG_SELF_REFLECTION_MODEL=polaris-local-structured` |

Each setting is independent even when multiple stages currently use the same
model, allowing later model changes without changing stage contracts.
The default low-VRAM local LiteLLM profile maps fast, structured, evaluation,
and optimization aliases to `qwen2.5:7b`, while reasoning and synthesis aliases
map to `qwen3.5:4b`. This keeps the more reasoning-oriented model on synthesis
paths without making concrete model names architectural defaults.

Generation budgets are also stage-specific. Structured routing, CRAG, and
Self-RAG JSON calls default to `RAG_STRUCTURED_MAX_TOKENS=512`; HyDE defaults to
`RAG_HYDE_MAX_TOKENS=768`; final answer synthesis defaults to
`RAG_SYNTHESIS_MAX_TOKENS=1536`. These budgets keep structured operations,
including Self-RAG reflection, on faster JSON-oriented aliases while reserving
the larger thinking-model budget for final cited answer synthesis.

## Canonical ingestion source matrix

Use `polaris rag ingest --source <source>` with one of these source groups:

| CLI source | Canonical PostgreSQL tables |
| --- | --- |
| `reports` | `reports` |
| `agent-signals` | `agent_signals` |
| `recommendations` | `recommendations`, `recommendation_rationales` |
| `market` | `technical_analysis_snapshots`, `market_context_snapshots`, `market_breadth_snapshots` |
| `macro` | `macro_regime_snapshots` |
| `news` | `news_analysis_snapshots` |
| `sentiment` | `sentiment_snapshots` |
| `portfolio` | `portfolio_risk_snapshots`, `portfolio_allocation_snapshots` |
| `backtests` | `backtest_runs`, `backtest_steps`, `backtest_portfolio_snapshots`, `backtest_metrics`, `backtest_artifacts` |

Only curated records are eligible for canonical ingestion. Raw runtime dumps,
raw vendor responses, arbitrary JSON, and transient web pages must not be stored as
canonical RAG documents merely because they were retrieved.

## PostgreSQL RAG records

`PostgresRagPersistenceRepository` owns the RAG persistence contracts:

- `RagDocumentRecord`: canonical document derived from a curated source;
- `RagChunkRecord`: deterministic child chunk with source lineage;
- `RagSourceEligibilityRecord`: metadata-only eligibility decision;
- `RagEmbeddingJobRecord`: Qdrant projection work and status;
- `RagGraphJobRecord`: Neo4j projection work and status;
- `RagQueryLogRecord`: query, route, retrieval, and outcome metadata;
- `RagAnswerLogRecord`: answer status, model attribution, citations, and lineage.

Query and answer logs are written for success, no-result, rejected, and failure
outcomes. Transient raw web/provider payloads are not written into those logs;
only bounded provenance metadata is retained.

## Chunking strategy and justification

Curated ingestion uses a record-aware parent-child strategy optimized for
financial reports, agent signals, and structured platform records. In Polaris,
**the parent is the complete curated `RagDocumentRecord`**, while the
individually embedded and searched `RagChunkRecord` values are its children.
The parent is not another 4,000-character chunk.

### Parent and child sizes

- **Parent size:** the parent is the complete, canonical
  `RagDocumentRecord.content_text`. It has no separate character-size setting at
  ingestion. PostgreSQL retains this full text so a child hit can be expanded
  back to the complete source document.
- **Default child-chunk budget:**
  `CuratedRagBuildOptions.max_chunk_characters` defaults to **4,000
  characters**. This is a maximum, not a target; shorter semantic sections and
  paragraph groups remain shorter.
- **Heading budget:** for record-aware Markdown, a section heading is repeated
  on every child created from that section. The heading counts toward the
  4,000-character maximum, and the available body budget is reduced by the
  heading length.
- **Configurable override:** callers may supply a different
  `max_chunk_characters`. The same value governs section splitting and the
  generic paragraph-preserving fallback, so there is currently no independent
  child-size or fallback-size setting.

The 4,000 value must not be confused with the frequently cited **500–1,000
_token_** chunk range. Polaris's setting is measured in characters. For typical
English financial prose, 4,000 characters is roughly 1,000 tokens and commonly
falls in an approximate 800–1,200-token band, although the exact ratio varies
with tables, symbols, numbers, tokenization, and formatting.
The default therefore falls near the upper end of that common token range
rather than being four to eight times larger.

Polaris deliberately favors that upper end because its curated sources contain
section-level financial reasoning, evidence, qualifications, and related
metrics that lose meaning when fragmented into very small pieces. A roughly
4,000-character child normally preserves a coherent report section or several
related paragraphs while remaining narrow enough for dense and sparse
embedding, vector retrieval, cross-encoder reranking, and retrieval filtering.
The value is a practical content budget rather than a claim that every source
or language has the same token density. If the corpus changes materially, it
should be reevaluated with retrieval-quality measurements rather than adjusted
solely from generic chunk-size guidance.

### Record-aware Markdown strategy

Curated report and agent-signal paths use
`record_aware_markdown_sections`. Markdown headings define semantic sections;
chunks carry section name, section title, section index, source table, source
record ID, workflow lineage, symbol metadata, score metadata, and projection
status. When a section exceeds the child budget, it is split while its heading
is retained on every resulting child so each vector point remains
self-identifying.

### Paragraph-preserving fallback

Generic text uses the `paragraph_preserving_character_limit` strategy. Its
configured limit is the same `max_chunk_characters` value described above:
**4,000 characters by default**. Paragraphs are accumulated, with blank-line
separators, until adding another paragraph would exceed that limit. A completed
paragraph is not split merely to fill unused space in a chunk.

Using one default limit for both strategies keeps embedding granularity
consistent across curated source types. The paragraph-preserving behavior is
preferred over fixed-width slicing because paragraph boundaries usually align
with complete claims, evidence, and qualifications. Only a single paragraph
that is itself longer than the configured limit is split into consecutive
fixed-width character slices.

### Oversized paragraphs, overlap, and context completeness

The oversized-paragraph fallback currently uses deterministic, non-overlapping
character slices. A split can occur inside a sentence or word, and no text from
an adjacent slice is copied into the child. Child chunks are retrieval indexes;
once one is matched, the final application context is expanded from the parent
rather than assembled from only that child.

When any child is retrieved, `ParentDocumentExpander` restores context as
follows:

1. Group matching children by their shared `document_id`.
2. Load the canonical parent `RagDocumentRecord` from PostgreSQL.
3. Load and order all persisted children by `chunk_index` for lineage metadata
   and deterministic fallback reconstruction.
4. Return the parent's complete `content_text` as one
   `RagRetrievedContext`. Because `RagDocumentRecord` requires non-empty
   `content_text`, this is the normal path.
5. If a noncanonical repository implementation ever returns an empty parent
   body, reconstruct the context from all ordered children rather than only the
   matched slice.
6. Record both `matched_chunk_ids` and all `parent_chunk_ids` in retrieval
   metadata so the triggering evidence and the expanded source remain
   inspectable.

Consequently, a vector match on either side of an oversized-paragraph split
expands to the entire canonical document, including every sibling slice and all
text surrounding the boundary. The application-level context selector limits
the number of parent documents with `top_k`; it does not alter the stored text
of a selected `RagRetrievedContext`. The completeness guarantee therefore
applies to each successfully selected parent document, not to every document in
the corpus.

There are two important limits to that guarantee:

1. **Expansion does not guarantee boundary recall.** Parent expansion occurs
   only after at least one child is retrieved. If the only useful evidence is a
   phrase or relationship split across two fixed-width children, neither child
   is guaranteed to rank strongly enough to trigger expansion. The current
   implementation has deterministic source fidelity after a hit, but it does
   not prove perfect retrieval recall at every artificial character boundary.
2. **External models still have input limits.** Polaris preserves the full parent
   text in `RagRetrievedContext`, but the BGE reranker client sends
   `"truncate": true` to the TEI endpoint. TEI may therefore truncate an
   oversized parent for reranking computation even though the full text remains
   attached to the selected application context. A downstream synthesis model
   may likewise impose its own context-window limit.

The present design favors lossless PostgreSQL storage and full parent recovery,
but very large parents need retrieval-quality monitoring. If boundary misses or
model-input truncation become material, the preferred change is a tested,
token-aware policy: split oversized paragraphs on sentence or word boundaries,
consider a small controlled overlap only for forced splits, and rerank the
matched child plus bounded adjacent siblings before expanding the final selected
source. Any bounded expansion must expose completeness and truncation metadata;
silent truncation or uncontrolled overlap would weaken auditability and could
overweight duplicated evidence.

### Determinism and source fidelity

- **Deterministic identity:** chunk IDs are derived from `document_id` and
  ordered `chunk_index`; chunk records also store `content_hash` and estimated
  token count. Re-ingesting the same source content with the same options
  produces the same chunk ordering and IDs.
- **No artificial overlap:** the current implementation does not duplicate text
  between children. Parent expansion supplies surrounding context without
  creating multiple vector points for the same fact, inflating token counts, or
  overweighting repeated evidence during hybrid retrieval.
- **No summarization or truncation:** chunking preserves source text. Long LLM
  responses and financial rationales are split deterministically rather than
  summarized, and the canonical parent retains their complete content.

The result supports both precise retrieval and coherent grounding: the platform
searches focused child chunks, expands a hit to its complete authoritative
parent, and traces the final answer to the exact curated source record and the
children that caused the match.

## Embedding model and vector dimension policy

The canonical RAG embedding configuration is:

| Setting | Default | Purpose |
| --- | --- | --- |
| `RAG_HYBRID_EMBEDDING_MODEL` | `BAAI/bge-m3` | Dense and sparse retrieval embeddings for Layer 4. |
| `VECTOR_SIZE` | `1024` | Expected dense-vector dimension for BGE-M3 Qdrant points. |
| `RAG_RERANKER_MODEL` | `BAAI/bge-reranker-large` | Cross-encoder reranking after retrieval and parent expansion. |

`VECTOR_SIZE=1024` is a model-contract choice, not an arbitrary storage tuning.
BGE-M3 produces 1024-dimensional dense embeddings and sparse lexical weights,
which matches the Qdrant named-vector schema used by the pipeline. The embedding
job processor validates every generated embedding against `VECTOR_SIZE` before
upsert, and Qdrant readiness/rebuild checks verify that the collection exposes
the required named dense and sparse vectors with the configured dimension.

A 1536-dimensional vector size is common for other embedding families, but it
would be incorrect for the current BGE-M3 projection unless the embedding model
and vector provider changed. The platform should never pad, truncate, or coerce
vectors to fit an unrelated dimension. If a future embedding model uses a
different dimension, update the model setting and `VECTOR_SIZE` together, then
recreate the Qdrant projection from canonical PostgreSQL chunks.

## Local services

Start the containerized stores, reranker, and LiteLLM gateway as needed:

```bash
docker compose up -d postgres qdrant neo4j bge-reranker litellm
```

Polaris calls models through LiteLLM. For local development, LiteLLM routes
logical aliases such as `polaris-local-fast` and `polaris-local-synthesis` to
host Ollama, but Ollama must be reachable from the
LiteLLM container. If Ollama binds only to `127.0.0.1:11434`, restart it with
`OLLAMA_HOST=0.0.0.0:11434` or set `POLARIS_LITELLM_OLLAMA_API_BASE` to another
container-reachable endpoint. Then pull the concrete models referenced by the
local LiteLLM alias profile:

```bash
OLLAMA_HOST=0.0.0.0:11434 ollama serve
ollama pull qwen2.5:7b
ollama pull qwen3.5:4b
```

Apply PostgreSQL migrations:

```bash
uv run alembic upgrade head
```

Default endpoints and projection settings:

| Setting | Default |
| --- | --- |
| PostgreSQL | `POLARIS_DATABASE_URL` or `POLARIS_POSTGRES_*` environment settings |
| Qdrant | `http://localhost:6333` |
| Qdrant collection | `polaris` |
| Qdrant dense vector size | `1024` |
| Neo4j Bolt URI | `bolt://localhost:7687` |
| Neo4j database | `neo4j` |
| Neo4j projection | `polaris_rag` |
| LiteLLM gateway | `http://localhost:4000/v1` |
| LiteLLM Ollama backend | `POLARIS_LITELLM_OLLAMA_API_BASE`, default `http://host.docker.internal:11434` from the container |
| BGE reranker | `http://localhost:8080/rerank` |
| SearXNG | `http://localhost:8888` when web fallback is explicitly enabled |
| Crawl4AI | Local browser-backed content acquisition when web fallback is explicitly enabled |

BGE-M3 embeddings run through the local `FlagEmbedding` client and may download
or warm the configured model on first use. The reranker container may also need
time to become healthy before live queries.

## CLI operations

### Inspect status

```bash
uv run polaris rag status
```

Status is loaded from PostgreSQL and reports eligibility plus queued,
processing, completed, and failed projection jobs. It does not treat Qdrant or
Neo4j as the source of truth.

### Ingest curated records

Preview eligible records without writing:

```bash
uv run polaris rag ingest --source reports --dry-run
```

Persist documents and queue both projections:

```bash
uv run polaris rag ingest --source reports --limit 100
```

Queue only selected projections when required:

```bash
uv run polaris rag ingest --source market \
  --queue-embedding-jobs \
  --no-queue-graph-jobs
```

Ingestion is deterministic for the same source content and build options.

### Process embedding jobs

```bash
uv run polaris rag process-embeddings --dry-run
uv run polaris rag process-embeddings --batch-size 25
```

The processor reads chunks from PostgreSQL, computes BGE-M3 dense and sparse
vectors, ensures the Qdrant collection exists, and upserts deterministic vector
points. Job states are `queued`, `processing`, `completed`, or `failed`.

### Process graph jobs

The default is a safe dry run:

```bash
uv run polaris rag process-graph
uv run polaris rag process-graph --execute
```

Graph projection extracts a bounded deterministic entity/relationship model and
upserts it into the configured Neo4j projection. Neo4j stores document IDs and
relationships; complete evidence is rehydrated from PostgreSQL during retrieval.

### Rebuild Qdrant

Preview the destructive action:

```bash
uv run polaris rag rebuild --projection qdrant
```

Recreate the collection and requeue its PostgreSQL embedding jobs:

```bash
uv run polaris rag rebuild --projection qdrant --confirm-delete
uv run polaris rag process-embeddings
```

`--confirm-delete` is required. Rebuild never uses Qdrant as the recovery source.

### Rebuild Neo4j

Preview the destructive action:

```bash
uv run polaris rag rebuild --projection neo4j
```

Clear only the configured projection and recreate it from PostgreSQL graph jobs:

```bash
uv run polaris rag rebuild --projection neo4j --confirm-delete
```

Projection identity scopes Neo4j entities so a test or development projection
does not overwrite another configured projection.

### Ask a question

```bash
uv run polaris rag ask "Summarize SPY breadth risk." --symbol SPY --top-k 8
```

Available filters include repeatable `--symbol`, `--source-type`,
`--source-table`, `--agent-name`, and `--report-type`, plus `--workflow-name`,
`--execution-id`, `--runtime-id`, `--as-of-start`, and `--as-of-end`.
`--route` defaults to `hybrid`. CLI output preserves the full generated answer
and its citations.

## Routing and corrective behavior

The graph first rewrites conversational input into a standalone query, performs
adaptive triage, and selects a route:

- direct-answer routes avoid unnecessary retrieval;
- standard routes run the normal branched retrieval path;
- deep-research routes add a HyDE hypothetical document before retrieval.

Retrieved evidence is sanitized, deduplicated, parent-expanded, and reranked.
CRAG then grades the evidence:

- sufficient evidence proceeds to secure generation;
- weak evidence may trigger one bounded corrective query rewrite;
- web fallback is considered only when CRAG requests it, the caller supplied
  `--web`, and open-source web fallback is enabled and configured;
- unavailable or empty corrective evidence fails closed rather than inventing an
  answer.

After synthesis, Self-RAG reflection evaluates support and usefulness. An
unsupported or suspicious answer is replaced with the canonical safe grounding
failure response.

## Open-source web fallback

Transient web fallback is disabled by default. Enable it explicitly in `.env`:

```dotenv
RAG_WEB_FALLBACK_ENABLED=true
SEARXNG_BASE_URL=http://localhost:8888
# Optional Crawl4AI tuning:
# CRAWL4AI_TIMEOUT_SECONDS=30
# CRAWL4AI_MAX_CONCURRENCY=4
```

Then allow it for an individual request:

```bash
uv run polaris rag ask "What new event may explain today's move?" --web
```

Both configuration and per-request permission are required. SearXNG handles
search/discovery, Crawl4AI handles concurrent content acquisition and Markdown
extraction, and `OpenSourceWebRetrievalProvider` converts sanitized documents
into transient `RagRetrievedContext` evidence. Web fallback is not a normal
retrieval branch, does not run when curated context is sufficient, and does not
automatically populate PostgreSQL, Qdrant, or Neo4j. Returned content passes
through the same untrusted-context security boundary as all other retrieved
evidence.

Local setup for the open-source fallback stack is intentionally explicit:

```bash
docker compose up -d searxng
uv run crawl4ai-setup
uv run crawl4ai-doctor
# If browser dependencies are missing:
uv run python -m playwright install --with-deps chromium
```

The default SearXNG endpoint is `http://localhost:8888`; port `8080` is reserved
by the local BGE reranker endpoint in the default compose stack.

## Security guarantees

The RAG boundary provides deterministic, fail-closed controls:

- direct prompt-injection inspection occurs before routing or model calls;
- all retrieved contexts are treated as untrusted evidence;
- executable HTML, role/system markup, and instruction-override segments are
  removed before CRAG or synthesis;
- classifier, router, CRAG, rewrite, and Self-RAG model calls require strict
  structured outputs;
- prompt policy is kept separate from serialized evidence;
- generated output is inspected for prompt disclosure, role override, policy
  bypass, and credential-like disclosure;
- unsafe or ungrounded answers use a stable safe-failure response;
- security detections and grounding failures emit RAG telemetry.

These controls reduce risk but do not make arbitrary web content trustworthy.
Curated PostgreSQL evidence remains preferred.

## RAG evaluation and quality gates

The RAG pipeline is evaluated by the canonical Polaris LLM evaluation layer, not by ad hoc scripts inside retrieval code. DeepEval runs through the application evaluation boundary after workflow outputs, curated records, or deterministic fixtures have been converted into typed evaluation cases.

The evaluation flow is:

```text
RAG query/result and retrieved evidence
        ↓
PostgreSQL query logs, curated records, and Langfuse correlation IDs
        ↓
EvaluationCaseBuilder
        ↓
DeepEval-backed EvaluationRunService or EvaluationJobProcessor
        ↓
PostgreSQL evaluation runs and metric results
        ↓
Langfuse score projection
```

RAG-specific target types include `rag_answer`, `rag_retrieval`, and `rag_generation`. Current canonical RAG datasets cover golden questions, citation support, and prompt-injection resistance. RAG quality metrics include faithfulness, answer relevancy, contextual relevancy, contextual precision, contextual recall, hallucination absence, citation support, financial answer quality, risk explanation quality, unsupported-claim penalties, refusal correctness, and prompt-injection resistance.

This separation is intentional:

- retrieval and generation stay focused on producing grounded answers;
- evaluation cases remain attributable to PostgreSQL records, workflow executions, retrieved chunks, citations, and Langfuse observations;
- thresholds are versioned and persist with metric results;
- DeepEval failures do not corrupt successful RAG results;
- Langfuse is used for AI-engineering score analysis, while PostgreSQL remains authoritative.

Use `docs/llm_evaluation.md` for the full evaluation contract, threshold table, CLI commands, and live-test requirements.

## Observability

The default CLI composition uses one shared `ApplicationRagTelemetry` emitter.
Telemetry covers:

- source selection and ingestion;
- embedding processing, retries, and Qdrant collection lifecycle;
- query rewrite, adaptive triage, route selection, and HyDE;
- lexical, structured, vector, graph, parent-expansion, and reranking stages;
- CRAG grading, corrective rewrites, and SearXNG + Crawl4AI web fallback;
- generation, Self-RAG reflection, and security failures;
- graph batches and individual Neo4j projection jobs;
- PostgreSQL query and answer persistence.

External calls remain behind integration providers and `record_provider_call()`.
Failures include correlation IDs and stage-specific operation names where a RAG
request or projection job supplies them.

## Runtime integration

`RagResearchNode` exposes the application RAG service through the existing core
runtime. It accepts serialized `rag_request`, `rag_query`, `rag_filters`,
`rag_route`, and `rag_top_k` inputs, builds typed contracts internally, and
serializes the `RagResult` only at the runtime boundary. It does not introduce a
parallel execution engine.

## Operational validation

Run deterministic RAG and boundary tests:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q \
  tests/unit/application/rag \
  tests/unit/integration/providers/rag \
  tests/unit/integration/clients/rag \
  tests/unit/interfaces/cli/test_rag_command.py \
  tests/unit/intelligence/research/test_rag_research_node.py \
  tests/unit/telemetry/test_application_rag_telemetry.py
```

With services running, execute the guarded live checks:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/integration/rag
UV_CACHE_DIR=/tmp/uv-cache uv run polaris rag status
```

The Qdrant and Neo4j integration tests create isolated temporary projections and
clean them up. The BGE test validates that the live cross-encoder ranks relevant
text first.

## Troubleshooting

- **PostgreSQL connection failure:** confirm `docker compose ps postgres`, then
  run migrations with the same `POLARIS_DATABASE_URL` used by the CLI.
- **Qdrant unavailable:** confirm port `6333`; canonical data remains safe in
  PostgreSQL. Rebuild after service recovery.
- **Neo4j unavailable:** graph retrieval degrades without failing the canonical
  PostgreSQL/Qdrant path. Confirm Bolt port `7687` before processing graph jobs.
- **BGE model warm-up:** first embedding or reranking calls may be slow. Wait for
  the reranker health check and allow the local BGE-M3 model to load.
- **LiteLLM model backend unavailable:** confirm `docker compose ps litellm`, verify `/v1/models` with the configured API key, and ensure the LiteLLM backend endpoint can reach the configured local model provider. For local Ollama, pull every concrete model referenced by `config/litellm/config.yaml` and ensure `POLARIS_LITELLM_OLLAMA_API_BASE` is container-reachable. Polaris `RAG_*_MODEL` settings should normally name logical LiteLLM aliases, not concrete Ollama models.
- **Web fallback not used:** verify `RAG_WEB_FALLBACK_ENABLED=true`,
  `SEARXNG_BASE_URL`, local Crawl4AI browser setup, and the request's `--web`
  flag; fallback still occurs only when CRAG requests corrective web evidence.

## Structured generation and prompt artifact governance

The RAG synthesis stage uses Instructor-backed structured output through the canonical structured-output provider boundary. The schema-enforced output is mapped back into the existing `RagResult` contract, so callers continue to receive the same application-level RAG response while generation becomes easier to validate, evaluate, and observe.

Prompt/program optimization is intentionally outside the normal RAG runtime path. DSPy is available through the explicit AI optimization workbench:

```bash
polaris ai optimize --target rag_answer_generation --dataset <dataset-name>
polaris ai artifacts approve <artifact-id> --approved-by <reviewer>
polaris ai artifacts activate <artifact-id>
```

At runtime, `RagAnswerGenerator` resolves an approved active artifact for the `rag_answer_generation` target when one exists. If no approved active artifact exists, it uses the source-controlled fallback prompt metadata. The runtime does not execute DSPy optimization, select mutable prompt labels, or read unapproved local artifacts.

The ownership model is:

| Capability | Owner |
| --- | --- |
| Structured answer schema enforcement | Instructor provider boundary |
| RAG orchestration and secure generation | Polaris RAG application services |
| Prompt/program candidate optimization | DSPy offline workbench |
| Semantic quality and safety evaluation | DeepEval evaluation services |
| Prompt, trace, dataset, score, and artifact observability | Langfuse projection services |
| Workflow evidence, curated records, query/answer logs, evaluations, and approved artifacts | PostgreSQL |

This keeps RAG generation typed and observable without turning Instructor, DSPy, or Langfuse into parallel runtime or persistence systems.
