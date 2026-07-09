  # Staged Structural and Semantic Chunking Implementation Plan

  ## Summary

  Enhance the existing Markdown-aware parent-child chunking pipeline without replacing its deterministic structural foundation.

  The implementation will proceed through four gated stages:

  1. Structural boundary hardening
  2. Retrieval evaluation and provenance persistence
  3. Selective semantic chunking
  4. Bounded sibling-aware reranking

  Semantic chunking will initially be disabled. It becomes the default only for eligible narrative records after passing deterministic quality, latency, and regression gates.

  ### Canonical precedence

  Markdown structure
      → paragraph and sentence structure
          → semantic similarity
              → word boundary
                  → hard character limit

  The full curated RAG document remains the parent. Searchable chunks remain children. Semantic chunking changes only how child boundaries are selected.

  ## Selected Defaults and Architectural Decisions

  - Preserve the existing 4000-character hard maximum for child chunks.
  - Introduce these initial chunk budgets:
      - Minimum: 800 characters
      - Target: 2400 characters
      - Maximum: 4000 characters

  - Do not add artificial text overlap by default.
  - Use the configured BGE-M3 embedding provider for semantic-boundary analysis.
  - Use only BGE-M3 dense vectors when comparing adjacent sentences.
  - Keep CuratedRagDocumentBuilder deterministic and synchronous.
  - Perform semantic planning asynchronously before record assembly.
  - Never silently fall back from requested semantic chunking to structural chunking after a provider failure.
  - Keep compact structured records on deterministic structural chunking.
  - Apply semantic chunking only to eligible, sufficiently long narrative sections.
  - Persist chunking strategy and source-boundary provenance as first-class database fields rather than generic metadata.
  - Treat RAG documents, chunks, embeddings, and external projections as rebuildable derivatives of canonical curated source records.

  ## Public Contracts and Configuration

  Introduce typed contracts similar to:

  class RagChunkingStrategy(StrEnum):
      STRUCTURAL_V2 = "structural_v2"
      SEMANTIC_HYBRID_V1 = "semantic_hybrid_v1"

  @dataclass(frozen=True, slots=True)
  class RagChunkingOptions:
      strategy: RagChunkingStrategy
      min_chunk_characters: int = 800
      target_chunk_characters: int = 2400
      max_chunk_characters: int = 4000
      semantic_breakpoint_percentile: float = 80.0

  @dataclass(frozen=True, slots=True)
  class PlannedRagChunk:
      chunk_index: int
      section_index: int
      section_chunk_index: int
      source_start_offset: int
      source_end_offset: int
      section_path: tuple[str, ...]
      text: str

  @dataclass(frozen=True, slots=True)
  class RagChunkPlan:
      strategy: RagChunkingStrategy
      strategy_version: int
      embedding_model: str | None
      configuration_hash: str
      chunks: tuple[PlannedRagChunk, ...]

  Add configuration for:

  RAG_CHUNKING_STRATEGY=structural_v2
  RAG_SEMANTIC_CHUNKING_MODEL=BAAI/bge-m3
  RAG_SEMANTIC_CHUNKING_MIN_CHARACTERS=800
  RAG_SEMANTIC_CHUNKING_TARGET_CHARACTERS=2400
  RAG_SEMANTIC_CHUNKING_MAX_CHARACTERS=4000
  RAG_SEMANTIC_BREAKPOINT_PERCENTILE=80
  RAG_RERANK_CONTEXT_MAX_CHARACTERS=4000

  The semantic strategy remains disabled by default until the evaluation gate passes.

  ## Implementation Steps

  ### Stage 1 — Establish the Evaluation Baseline

  #### Step 1 — Capture current chunking behavior

  - Record current structural chunk boundaries for representative curated records.
  - Include Markdown reports, prose, tables, lists, financial abbreviations, decimals, tickers, and oversized paragraphs.
  - Preserve these fixtures as the structural_v1 comparison baseline.
  - Verify that existing chunking and retrieval tests pass before modification.

  #### Step 2 — Add typed evaluation contracts

  - Define immutable evaluation query, expected-evidence, result, and aggregate-metric models.
  - Include source document, expected section, expected source range, retrieved chunk IDs, rank, and latency.
  - Keep evaluation contracts independent from production retrieval contracts.

  #### Step 3 — Build the deterministic retrieval evaluator

  - Run the same query corpus against a selected chunking strategy.
  - Calculate:
      - Recall@5
      - MRR@5
      - expected-section retrieval
      - boundary-crossing evidence retrieval
      - average and p95 chunk count
      - ingestion planning duration
      - retrieval and reranking latency

  - Ensure evaluation output is deterministic and serializable.

  #### Step 4 — Record the structural-v1 baseline

  - Run the evaluator against current chunking.
  - Store the baseline metrics as a versioned test artifact or fixture.
  - Do not make semantic chunking decisions before establishing this baseline.

  ### Stage 2 — Deterministic Structural Boundary Hardening

  #### Step 5 — Introduce chunking strategy and plan contracts

  - Add the typed strategy, options, planned chunk, and chunk-plan models.
  - Validate:
      - 0 < min <= target <= max
      - offsets are non-negative and ordered
      - all chunks respect the hard maximum
      - strategy versions are explicit

  - Adapt existing build options without introducing dictionary-based internal contracts.

  #### Step 6 — Add deterministic sentence segmentation

  - Implement sentence-aware segmentation for oversized paragraphs.
  - Prevent false boundaries around:
      - decimal values
      - common financial abbreviations
      - initials
      - ticker notation
      - numbered lists

  - Preserve original text exactly; segmentation must not normalize whitespace or punctuation.

  #### Step 7 — Add word-aware emergency splitting

  - If a sentence exceeds the hard maximum, split at the last viable whitespace boundary.
  - Use raw character slicing only when a single uninterrupted token exceeds the maximum.
  - Record emergency hard splits through telemetry.

  #### Step 8 — Implement structural_v2

  - Keep Markdown heading and paragraph grouping behavior.
  - Replace raw fixed-width paragraph slicing with:
      1. sentence-aware packing
      2. word-aware splitting
      3. raw character splitting as the final fallback

  - Prefer chunks near the target size without violating the maximum.
  - Do not split a paragraph or sentence merely to reach the target size.

  #### Step 9 — Add lossless boundary verification

  - Verify all source text is represented exactly once by source offsets.
  - Permit repeated heading context in chunk_text, but exclude that context from source-span coverage calculations.
  - Verify:
      - no missing source ranges
      - no duplicated body ranges
      - stable chunk order
      - deterministic IDs
      - deterministic plans across repeated executions

  #### Step 10 — Add structural planning telemetry

  Instrument:

  - planning duration
  - source and section counts
  - sentence count
  - chunk count
  - chunk-size histogram
  - word-boundary fallback count
  - hard-split count
  - selected strategy and version

  Do not include source text in telemetry attributes.

  #### Step 11 — Evaluate structural-v2

  Compare structural_v2 against the recorded baseline.

  Required gate:

  - No overall Recall@5 regression greater than two percentage points.
  - No MRR@5 regression greater than two percentage points.
  - Boundary-focused Recall@5 improves or remains perfect.
  - All lossless reconstruction and determinism checks pass.

  Keep structural_v1 only as evaluation history, not as a production compatibility strategy.

  ### Stage 3 — First-Class Persistence and Selective Semantic Planning

  #### Step 12 — Add first-class chunking provenance fields

  Add document-level fields for:

  - chunking strategy
  - strategy version
  - semantic model, when applicable
  - configuration hash
  - minimum, target, and maximum chunk sizes
  - semantic breakpoint percentile, when applicable

  Add chunk-level fields for:

  - source start offset
  - source end offset
  - section index
  - section-local chunk index
  - section path

  Do not place these values in generic metadata.

  #### Step 13 — Add and verify the Alembic migration

  - Add the new schema fields and indexes required for document/strategy inspection.
  - Treat existing RAG derivatives as rebuildable.
  - Preserve canonical curated source records.
  - Rebuild derived RAG documents, chunks, embedding jobs, and external projections rather than maintaining ambiguous legacy provenance.
  - Verify a blank-database upgrade and ORM metadata agreement.

  PostgreSQL must be running for the live verification portion of this step.

  #### Step 14 — Update persistence mappings

  - Update SQLAlchemy models, persistence records, repository writes, and repository reads.
  - Require valid first-class provenance for all newly created records.
  - Add repository round-trip tests for structural and semantic plans.

  #### Step 15 — Separate content preparation from record assembly

  Refactor the builder into two deterministic responsibilities:

  1. Prepare the canonical parent document content.
  2. Assemble document, chunk, and embedding-job records from a completed RagChunkPlan.

  The builder must remain synchronous and must not call embedding providers.

  #### Step 16 — Add the selective semantic eligibility policy

  Semantic planning is eligible only when:

  - the curated record is an approved narrative source type
  - the section exceeds the target chunk size
  - the section contains enough sentence units to make semantic comparison meaningful

  Compact structured records, tables, short sections, and identifier-heavy records remain structural.

  Represent eligibility with a typed policy/result, not caller-specific conditionals.

  #### Step 17 — Add the asynchronous semantic chunk planner

  The planner will:

  1. Parse the prepared document into Markdown sections.
  2. Split eligible sections into deterministic sentence units.
  3. Batch sentence embedding requests through the existing EmbeddingProvider.
  4. Use the dense component of BGE-M3 vectors.
  5. Calculate cosine similarity between adjacent sentence vectors.
  6. Identify candidate breakpoints at local similarity minima at or above the configured distance percentile.
  7. Build chunks subject to minimum, target, and maximum budgets.
  8. Fall back to sentence or word boundaries only when semantic candidates cannot satisfy the hard limit.
  9. Return a typed RagChunkPlan.

  No provider or model logic may be added to the builder.

  #### Step 18 — Integrate semantic planning into ingestion

  Canonical flow:

  Curated source record
      → deterministic parent preparation
      → chunking eligibility policy
      → structural or semantic chunk planner
      → typed RagChunkPlan
      → deterministic record assembly
      → PostgreSQL persistence
      → embedding-job processing
      → Qdrant and Neo4j projections

  The ingestion service owns asynchronous orchestration.

  #### Step 19 — Implement explicit semantic failure behavior

  - Retry failures through existing provider retry behavior.
  - Fail the ingestion operation if semantic planning was explicitly selected and cannot complete.
  - Do not silently generate structurally different chunks.
  - Leave the canonical source record available for requeue.
  - Ensure partial document, chunk, or embedding-job writes are rolled back.

  #### Step 20 — Add semantic planning telemetry

  Capture:

  - selected strategy and model
  - eligibility decision
  - sentence embedding latency
  - embedded sentence count
  - semantic breakpoint count
  - structural fallback boundary count
  - resulting chunk-size distribution
  - planning failures
  - configuration hash

  Preserve trace context through the asynchronous embedding call.

  #### Step 21 — Add semantic determinism and algorithm tests

  Test:

  - identical inputs and vectors produce identical plans
  - short sections bypass semantic embedding
  - compact structured records remain structural
  - Markdown sections are never merged
  - semantic boundaries remain inside their source section
  - min/target/max policies are respected
  - provider failures do not silently change strategy
  - no body text is lost or duplicated
  - long single sentences use word-aware emergency splitting

  #### Step 22 — Run the semantic quality gate

  Compare semantic_hybrid_v1 against both structural baselines.

  Enable semantic chunking for eligible narrative records only if:

  - Boundary-focused Recall@5 improves by at least ten percentage points over structural_v1, or reaches at least 95%.
  - Overall Recall@5 has no regression greater than two percentage points against structural_v2.
  - MRR@5 has no regression greater than two percentage points.
  - Chunk planning is deterministic.
  - All source-span integrity checks pass.
  - Warm local semantic-planning p95 latency remains no more than 2.5 times structural-v2 planning latency.

  If the gate fails, retain structural_v2 as the default and preserve semantic mode as an explicit experimental option.

  ### Stage 4 — Bounded Sibling-Aware Reranking

  #### Step 23 — Add typed reranking-context contracts

  Represent reranking evidence as:

  - matched child chunk
  - optional previous sibling
  - optional next sibling
  - parent document identity
  - source offsets and section identity

  Do not concatenate anonymous strings or generic dictionaries.

  #### Step 24 — Build bounded sibling context

  - Keep siblings within the same parent and Markdown section.
  - Always prioritize the matched child.
  - Add the previous and next sibling only while remaining within the configured reranking character budget.
  - Do not rerank the entire parent document.
  - Do not add duplicate or overlapping sibling evidence.

  #### Step 25 — Correct the retrieval ordering

  Use this sequence:

  Hybrid chunk retrieval
      → rank fusion
      → bounded child/sibling reranking
      → document deduplication
      → full parent expansion
      → final context selection

  The full parent is evidence returned to synthesis, not the oversized input used to rank every candidate.

  #### Step 26 — Add reranking regression tests

  Verify:

  - child identity survives reranking
  - adjacent sibling evidence can improve a boundary-crossing result
  - unrelated sections are not included
  - reranking inputs respect the configured budget
  - parent expansion occurs only after ranking
  - returned parent context remains complete
  - duplicate documents are removed deterministically

  #### Step 27 — Run live retrieval and projection validation

  With PostgreSQL, Qdrant, Neo4j, BGE-M3, and BGE reranker running:

  - Reingest the deterministic corpus.
  - Process embedding and graph jobs.
  - Validate Qdrant hybrid retrieval.
  - Validate Neo4j parent/child relationships.
  - Validate reranking and parent expansion.
  - Confirm telemetry appears in Prometheus and Jaeger.
  - Run the full quality comparison.

  Notify the user before this step if any required service is unavailable.

  ### Final Verification and Documentation

  #### Step 28 — Update architecture documentation

  Document:

  - structural-v2 and semantic-hybrid strategies
  - eligibility rules
  - min/target/max budgets
  - why semantic chunking is selective
  - failure behavior
  - sibling-aware reranking order
  - quality-gated rollout procedure

  #### Step 29 — Run focused verification

  Run, in project order:

  ruff check --fix
  ruff format
  mypy
  focused chunking tests
  RAG ingestion tests
  RAG persistence tests
  retrieval and reranking tests
  migration tests

  Run Graphify update after source changes.

  #### Step 30 — Run the final acceptance gate

  The implementation is complete when:

  - all new and affected tests pass
  - MyPy and Ruff pass
  - migration and ORM metadata tests pass
  - every chunk respects the hard maximum
  - source-span reconstruction is lossless
  - plans are deterministic for pinned inputs and embeddings
  - semantic failure never silently changes chunk strategy
  - important provenance is stored in first-class fields
  - retrieval quality meets the selected rollout gate
  - Qdrant and Neo4j projections are successfully rebuilt
  - documentation reflects the production behavior

  ## Execution Protocol

  - Execute one numbered step at a time.
  - Record the files changed, tests run, results, and unresolved observations after every step.
  - Stop and request confirmation before beginning the next step.
  - Do not enable semantic chunking by default before Step 22 passes.
  - Request service startup before any step requiring PostgreSQL, Qdrant, Neo4j, BGE-M3, or BGE reranker.
  - Use timeouts based on the expected duration of each operation.
  - Avoid unrelated refactoring in the churn-heavy builder, retriever, and PostgreSQL repository.

  ## Assumptions

  - The approved plan authorizes the necessary RAG database-model and migration changes under core/.
  - BGE-M3 remains the initial model for both final hybrid embeddings and semantic-boundary sentence embeddings.
  - Parent documents remain the canonical reconstruction boundary.
  - PostgreSQL curated source records remain authoritative; RAG documents, chunks, jobs, and external projections may be rebuilt.
  - Semantic chunking does not cross Markdown section boundaries.
  - Structural-v2 remains available as the deterministic fallback strategy and default until the quality gate passes.