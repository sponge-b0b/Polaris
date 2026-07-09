from __future__ import annotations

from application.rag.contracts.rag_request import RagRequest
from application.rag.retrieval.rag_retrieval_filters import RagRetrievalFilterEvaluator
from core.storage.persistence.rag import JsonObject
from core.storage.persistence.rag import RagChunkRecord
from core.storage.persistence.rag import RagPersistenceRepository
from integration.providers.rag.embedding_provider import EmbeddingInput
from integration.providers.rag.embedding_provider import EmbeddingProvider
from integration.providers.rag.embedding_provider import EmbeddingRequest
from integration.providers.rag.embedding_provider import EmbeddingVector
from integration.providers.rag.vector_index_provider import VectorIndexProvider
from integration.providers.rag.vector_index_models import VectorSearchQuery
from integration.providers.rag.vector_index_models import VectorSearchResult


class RagCandidateCollector:
    """Collect canonical lexical and dense/sparse vector candidates."""

    def __init__(
        self,
        *,
        repository: RagPersistenceRepository,
        embedding_provider: EmbeddingProvider,
        vector_index_provider: VectorIndexProvider,
        filter_evaluator: RagRetrievalFilterEvaluator,
        collection_name: str,
        embedding_model: str,
        max_candidate_chunks: int,
        vector_search_multiplier: int,
    ) -> None:
        self._repository = repository
        self._embedding_provider = embedding_provider
        self._vector_index_provider = vector_index_provider
        self._filter_evaluator = filter_evaluator
        self._collection_name = collection_name
        self._embedding_model = embedding_model
        self._max_candidate_chunks = max_candidate_chunks
        self._vector_search_multiplier = vector_search_multiplier

    async def list_lexical_candidates(
        self,
        *,
        request: RagRequest,
        exact_filters: JsonObject,
    ) -> tuple[RagChunkRecord, ...]:
        chunks = tuple(
            await self._repository.list_chunks_by_metadata(
                metadata_filters=exact_filters,
                limit=self._max_candidate_chunks,
            )
        )
        return tuple(
            chunk
            for chunk in chunks
            if self._filter_evaluator.matches(chunk.metadata, request.filters)
        )

    async def embed_query(
        self,
        request: RagRequest,
    ) -> EmbeddingVector:
        embeddings = await self._embedding_provider.embed_texts(
            EmbeddingRequest(
                model=self._embedding_model,
                inputs=(
                    EmbeddingInput(
                        text_id=request.request_id,
                        text=request.normalized_query,
                        metadata=request.metadata,
                    ),
                ),
            )
        )
        for embedding in embeddings:
            if embedding.text_id == request.request_id:
                return embedding
        raise LookupError(
            f"Embedding provider did not return vector for {request.request_id}."
        )

    async def search_vectors(
        self,
        *,
        request: RagRequest,
        query_embedding: EmbeddingVector,
        exact_filters: JsonObject,
    ) -> tuple[VectorSearchResult, ...]:
        return await self._vector_index_provider.search(
            collection_name=self._collection_name,
            query=VectorSearchQuery(
                dense_vector=query_embedding.dense_vector,
                sparse_vector=query_embedding.sparse_vector,
                top_k=request.top_k * self._vector_search_multiplier,
                filters=exact_filters,
            ),
        )

    async def rehydrate_vector_chunks(
        self,
        vector_results: tuple[VectorSearchResult, ...],
    ) -> dict[str, RagChunkRecord]:
        chunks: dict[str, RagChunkRecord] = {}
        for result in vector_results:
            chunk = await self._repository.get_chunk(result.point_id)
            if chunk is None:
                continue
            chunks[result.point_id] = chunk
        return chunks
