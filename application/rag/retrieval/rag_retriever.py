from __future__ import annotations

from collections.abc import Awaitable
from collections.abc import Callable
from dataclasses import dataclass
from time import perf_counter
from typing import Any
from typing import Protocol
from typing import TypeVar

from application.rag.retrieval.rag_candidate_collector import RagCandidateCollector
from application.rag.contracts.rag_context import RagRetrievedContext
from application.rag.retrieval.rag_context_selector import RagContextSelector
from application.rag.contracts.rag_request import RagRequest
from application.rag.retrieval.rag_retrieval_filters import RagRetrievalFilterEvaluator
from application.rag.retrieval.rag_retrieval_fusion import RagRetrievalFusion
from application.rag.retrieval.retrieval_quality import Bm25LexicalRetriever
from application.rag.retrieval.retrieval_quality import ParentDocumentExpander
from application.rag.retrieval.retrieval_quality import RagContextDeduplicator
from application.rag.retrieval.retrieval_quality import RankedRagChunk
from application.rag.retrieval.structured_retrieval import StructuredRagRetriever
from config.settings import DEFAULT_RAG_HYBRID_EMBEDDING_MODEL
from config.settings import DEFAULT_QDRANT_COLLECTION
from core.storage.persistence.rag import JsonObject
from core.storage.persistence.rag import RagChunkRecord
from core.storage.persistence.rag import RagPersistenceRepository
from core.telemetry.emitters.application_rag_telemetry import ApplicationRagTelemetry
from integration.providers.rag.embedding_provider import EmbeddingProvider
from integration.providers.rag.embedding_provider import EmbeddingVector
from integration.providers.rag.reranking_provider import RerankingProvider
from integration.providers.rag.vector_index_provider import VectorIndexProvider
from integration.providers.rag.vector_index_models import VectorSearchResult


_StageResultT = TypeVar("_StageResultT")


class GraphRetrieverPort(Protocol):
    async def retrieve(
        self,
        request: RagRequest,
    ) -> tuple[RagRetrievedContext, ...]: ...


@dataclass(
    frozen=True,
    slots=True,
)
class RagRetrieverConfig:
    """Runtime controls for the platform-native V2 hybrid retriever."""

    collection_name: str = DEFAULT_QDRANT_COLLECTION
    embedding_model: str = DEFAULT_RAG_HYBRID_EMBEDDING_MODEL
    max_candidate_chunks: int = 200
    vector_search_multiplier: int = 3
    rerank_multiplier: int = 3
    lexical_weight: float = 0.45
    vector_weight: float = 0.55

    def __post_init__(
        self,
    ) -> None:
        _require_non_empty(self.collection_name, "collection_name")
        _require_non_empty(self.embedding_model, "embedding_model")
        if self.max_candidate_chunks <= 0:
            raise ValueError("max_candidate_chunks must be positive.")
        if self.vector_search_multiplier <= 0:
            raise ValueError("vector_search_multiplier must be positive.")
        if self.rerank_multiplier <= 0:
            raise ValueError("rerank_multiplier must be positive.")
        if self.lexical_weight < 0 or self.vector_weight < 0:
            raise ValueError("retrieval weights cannot be negative.")
        if self.lexical_weight == 0 and self.vector_weight == 0:
            raise ValueError("at least one retrieval weight must be positive.")


@dataclass(
    frozen=True,
    slots=True,
)
class RagRetrievalResult:
    """Typed retrieval result returned by the V2 hybrid retriever."""

    request_id: str
    route: str
    contexts: tuple[RagRetrievedContext, ...]

    @property
    def found_count(
        self,
    ) -> int:
        return len(self.contexts)


class RagRetriever:
    """BGE-M3 dense/sparse retriever with auxiliary BM25 and reranking."""

    def __init__(
        self,
        *,
        repository: RagPersistenceRepository,
        embedding_provider: EmbeddingProvider,
        vector_index_provider: VectorIndexProvider,
        reranking_provider: RerankingProvider | None = None,
        structured_retriever: StructuredRagRetriever | None = None,
        graph_retriever: GraphRetrieverPort | None = None,
        telemetry: ApplicationRagTelemetry | None = None,
        config: RagRetrieverConfig | None = None,
    ) -> None:
        self._structured_retriever = structured_retriever
        self._graph_retriever = graph_retriever
        self._telemetry = telemetry
        self._config = config or RagRetrieverConfig()
        self._filter_evaluator = RagRetrievalFilterEvaluator()
        self._candidate_collector = RagCandidateCollector(
            repository=repository,
            embedding_provider=embedding_provider,
            vector_index_provider=vector_index_provider,
            filter_evaluator=self._filter_evaluator,
            collection_name=self._config.collection_name,
            embedding_model=self._config.embedding_model,
            max_candidate_chunks=self._config.max_candidate_chunks,
            vector_search_multiplier=self._config.vector_search_multiplier,
        )
        self._fusion = RagRetrievalFusion(
            lexical_weight=self._config.lexical_weight,
            vector_weight=self._config.vector_weight,
            rerank_multiplier=self._config.rerank_multiplier,
        )
        self._context_selector = RagContextSelector(
            reranking_provider=reranking_provider,
            rerank_multiplier=self._config.rerank_multiplier,
        )
        self._lexical_retriever = Bm25LexicalRetriever()
        self._parent_expander = ParentDocumentExpander(repository)
        self._deduplicator = RagContextDeduplicator()

    async def retrieve(
        self,
        request: RagRequest,
    ) -> RagRetrievalResult:
        started_at = perf_counter()
        await self._emit_started(request)
        try:
            contexts = await self._retrieve_contexts(request)
        except Exception as exc:
            await self._emit_failed(
                request=request,
                error=exc,
                duration_seconds=perf_counter() - started_at,
            )
            raise

        result = RagRetrievalResult(
            request_id=request.request_id,
            route=request.route,
            contexts=contexts,
        )
        await self._emit_completed(
            request=request,
            result=result,
            duration_seconds=perf_counter() - started_at,
        )
        return result

    async def _retrieve_contexts(
        self,
        request: RagRequest,
    ) -> tuple[RagRetrievedContext, ...]:
        exact_filters = self._filter_evaluator.exact_metadata_filters(request)
        candidate_chunks = await self._timed_candidate_chunks(
            request=request,
            exact_filters=exact_filters,
        )
        lexical_scores = await self._timed_lexical_scores(
            request=request,
            candidate_chunks=candidate_chunks,
        )
        query_embedding = await self._timed_query_embedding(request)
        vector_results = await self._timed_vector_search(
            request=request,
            query_embedding=query_embedding,
            exact_filters=exact_filters,
        )
        vector_chunks = await self._timed_vector_rehydration(
            request=request,
            vector_results=vector_results,
        )
        ranked_chunks = self._fusion.rank(
            top_k=request.top_k,
            lexical_scores=lexical_scores,
            vector_results=vector_results,
            lexical_chunks=candidate_chunks,
            vector_chunks=vector_chunks,
        )
        parent_contexts = await self._timed_parent_expansion(
            request=request,
            ranked_chunks=ranked_chunks,
        )
        structured_contexts = await self._timed_structured_retrieval(request)
        graph_contexts = await self._timed_graph_retrieval(request)
        deduplicated = await self._timed_deduplication(
            request=request,
            contexts=parent_contexts + structured_contexts + graph_contexts,
        )
        return await self._timed_reranking(
            request=request,
            contexts=deduplicated,
        )

    async def _timed_candidate_chunks(
        self,
        *,
        request: RagRequest,
        exact_filters: JsonObject,
    ) -> tuple[RagChunkRecord, ...]:
        return await self._run_observed_stage(
            request=request,
            operation="rag.retrieval.candidates",
            action=lambda: self._candidate_collector.list_lexical_candidates(
                request=request,
                exact_filters=exact_filters,
            ),
            attributes=lambda chunks: {
                "candidate_count": len(chunks),
                "exact_filter_count": len(exact_filters),
            },
        )

    async def _timed_lexical_scores(
        self,
        *,
        request: RagRequest,
        candidate_chunks: tuple[RagChunkRecord, ...],
    ) -> dict[str, float]:
        started_at = perf_counter()
        scores = self._lexical_retriever.score(
            query=request.normalized_query,
            chunks=candidate_chunks,
        )
        await self._emit_stage_completed(
            request=request,
            operation="rag.retrieval.bm25",
            duration_seconds=perf_counter() - started_at,
            attributes={
                "candidate_count": len(candidate_chunks),
                "lexical_match_count": len(scores),
            },
        )
        return scores

    async def _timed_query_embedding(
        self,
        request: RagRequest,
    ) -> EmbeddingVector:
        return await self._run_observed_stage(
            request=request,
            operation="rag.retrieval.query_embedding",
            action=lambda: self._candidate_collector.embed_query(request),
            attributes=lambda query_embedding: {
                "dense_vector_dimensions": query_embedding.dimensions,
                "sparse_vector_dimensions": len(query_embedding.sparse_vector.indices),
                "embedding_model": self._config.embedding_model,
            },
        )

    async def _timed_vector_search(
        self,
        *,
        request: RagRequest,
        query_embedding: EmbeddingVector,
        exact_filters: JsonObject,
    ) -> tuple[VectorSearchResult, ...]:
        return await self._run_observed_stage(
            request=request,
            operation="rag.retrieval.vector_search",
            action=lambda: self._candidate_collector.search_vectors(
                request=request,
                query_embedding=query_embedding,
                exact_filters=exact_filters,
            ),
            attributes=lambda results: {"vector_result_count": len(results)},
        )

    async def _timed_vector_rehydration(
        self,
        *,
        request: RagRequest,
        vector_results: tuple[VectorSearchResult, ...],
    ) -> dict[str, RagChunkRecord]:
        started_at = perf_counter()
        chunks = await self._candidate_collector.rehydrate_vector_chunks(vector_results)
        attributes: dict[str, object] = {
            "vector_result_count": len(vector_results),
            "rehydrated_chunk_count": len(chunks),
            "missing_chunk_count": len(vector_results) - len(chunks),
        }
        if attributes["missing_chunk_count"]:
            await self._emit_stage_degraded(
                request=request,
                operation="rag.retrieval.vector_rehydrate",
                duration_seconds=perf_counter() - started_at,
                attributes=attributes,
            )
        else:
            await self._emit_stage_completed(
                request=request,
                operation="rag.retrieval.vector_rehydrate",
                duration_seconds=perf_counter() - started_at,
                attributes=attributes,
            )
        return chunks

    async def _timed_parent_expansion(
        self,
        *,
        request: RagRequest,
        ranked_chunks: tuple[RankedRagChunk, ...],
    ) -> tuple[RagRetrievedContext, ...]:
        return await self._run_observed_stage(
            request=request,
            operation="rag.retrieval.parent_expansion",
            action=lambda: self._parent_expander.expand(
                request=request,
                ranked_chunks=ranked_chunks,
            ),
            attributes=lambda contexts: {
                "child_hit_count": len(ranked_chunks),
                "parent_context_count": len(contexts),
            },
        )

    async def _timed_structured_retrieval(
        self,
        request: RagRequest,
    ) -> tuple[RagRetrievedContext, ...]:
        async def retrieve_structured() -> tuple[RagRetrievedContext, ...]:
            if self._structured_retriever is None:
                return ()
            return await self._structured_retriever.retrieve(request)

        return await self._run_observed_stage(
            request=request,
            operation="rag.retrieval.structured",
            action=retrieve_structured,
            attributes=lambda contexts: {
                "structured_context_count": len(contexts),
                "structured_retriever_enabled": self._structured_retriever is not None,
            },
        )

    async def _timed_graph_retrieval(
        self,
        request: RagRequest,
    ) -> tuple[RagRetrievedContext, ...]:
        started_at = perf_counter()
        if self._graph_retriever is None:
            contexts: tuple[RagRetrievedContext, ...] = ()
            available = False
        else:
            try:
                contexts = await self._graph_retriever.retrieve(request)
                available = True
            except Exception as exc:
                await self._emit_stage_failed(
                    request=request,
                    operation="rag.retrieval.graph",
                    error=exc,
                    duration_seconds=perf_counter() - started_at,
                )
                return ()
        await self._emit_stage_completed(
            request=request,
            operation="rag.retrieval.graph",
            duration_seconds=perf_counter() - started_at,
            attributes={
                "graph_context_count": len(contexts),
                "graph_available": available,
            },
        )
        return contexts

    async def _timed_deduplication(
        self,
        *,
        request: RagRequest,
        contexts: tuple[RagRetrievedContext, ...],
    ) -> tuple[RagRetrievedContext, ...]:
        started_at = perf_counter()
        deduplicated = self._deduplicator.deduplicate(contexts)
        await self._emit_stage_completed(
            request=request,
            operation="rag.retrieval.deduplicate",
            duration_seconds=perf_counter() - started_at,
            attributes={
                "input_context_count": len(contexts),
                "deduplicated_context_count": len(deduplicated),
            },
        )
        return deduplicated

    async def _timed_reranking(
        self,
        *,
        request: RagRequest,
        contexts: tuple[RagRetrievedContext, ...],
    ) -> tuple[RagRetrievedContext, ...]:
        return await self._run_observed_stage(
            request=request,
            operation="rag.retrieval.rerank",
            action=lambda: self._context_selector.select(
                request=request,
                contexts=contexts,
            ),
            attributes=lambda reranked: {
                "rerank_candidate_count": len(contexts),
                "reranked_context_count": len(reranked),
                "reranker_enabled": self._context_selector.reranker_enabled,
            },
        )

    async def _run_observed_stage(
        self,
        *,
        request: RagRequest,
        operation: str,
        action: Callable[[], Awaitable[_StageResultT]],
        attributes: Callable[[_StageResultT], dict[str, Any]],
    ) -> _StageResultT:
        started_at = perf_counter()
        try:
            result = await action()
        except Exception as exc:
            await self._emit_stage_failed(
                request=request,
                operation=operation,
                error=exc,
                duration_seconds=perf_counter() - started_at,
            )
            raise
        await self._emit_stage_completed(
            request=request,
            operation=operation,
            duration_seconds=perf_counter() - started_at,
            attributes=attributes(result),
        )
        return result

    async def _emit_started(
        self,
        request: RagRequest,
    ) -> None:
        if self._telemetry is None:
            return
        await self._telemetry.emit_operation_started(
            "RagRetriever",
            "rag.retrieval.hybrid_v2",
            correlation_id=request.request_id,
            attributes={
                "collection_name": self._config.collection_name,
                "top_k": request.top_k,
                "route": request.route,
            },
        )

    async def _emit_completed(
        self,
        *,
        request: RagRequest,
        result: RagRetrievalResult,
        duration_seconds: float,
    ) -> None:
        if self._telemetry is None:
            return
        await self._telemetry.emit_operation_completed(
            "RagRetriever",
            "rag.retrieval.hybrid_v2",
            duration_seconds=duration_seconds,
            correlation_id=request.request_id,
            attributes={
                "found_count": result.found_count,
                "top_k": request.top_k,
                "route": request.route,
            },
        )

    async def _emit_failed(
        self,
        *,
        request: RagRequest,
        error: Exception,
        duration_seconds: float,
    ) -> None:
        if self._telemetry is None:
            return
        await self._telemetry.emit_operation_failed(
            "RagRetriever",
            "rag.retrieval.hybrid_v2",
            error=error,
            duration_seconds=duration_seconds,
            correlation_id=request.request_id,
        )

    async def _emit_stage_failed(
        self,
        *,
        request: RagRequest,
        operation: str,
        error: Exception,
        duration_seconds: float,
    ) -> None:
        if self._telemetry is None:
            return
        await self._telemetry.emit_operation_failed(
            "RagRetriever",
            operation,
            error=error,
            duration_seconds=duration_seconds,
            correlation_id=request.request_id,
            attributes={
                "route": request.route,
                "top_k": request.top_k,
                "collection_name": self._config.collection_name,
            },
        )

    async def _emit_stage_degraded(
        self,
        *,
        request: RagRequest,
        operation: str,
        duration_seconds: float,
        attributes: dict[str, object],
    ) -> None:
        if self._telemetry is None:
            return
        await self._telemetry.emit_operation_degraded(
            "RagRetriever",
            operation,
            duration_seconds=duration_seconds,
            correlation_id=request.request_id,
            attributes=attributes,
        )

    async def _emit_stage_completed(
        self,
        *,
        request: RagRequest,
        operation: str,
        duration_seconds: float,
        attributes: dict[str, Any],
    ) -> None:
        if self._telemetry is None:
            return
        await self._telemetry.emit_operation_completed(
            "RagRetriever",
            operation,
            duration_seconds=duration_seconds,
            correlation_id=request.request_id,
            attributes={
                **attributes,
                "route": request.route,
                "top_k": request.top_k,
                "collection_name": self._config.collection_name,
            },
        )


def _require_non_empty(
    value: str | None,
    field_name: str,
) -> None:
    if value is None or not value.strip():
        raise ValueError(f"{field_name} cannot be empty.")
