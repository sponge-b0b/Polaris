from __future__ import annotations

from collections.abc import Sequence
from typing import cast

import pytest

from application.rag.contracts.rag_context import RagRetrievalFilters
from application.rag.contracts.rag_request import RagRequest
from application.rag.retrieval.rag_candidate_collector import RagCandidateCollector
from application.rag.retrieval.rag_retrieval_filters import RagRetrievalFilterEvaluator
from core.storage.persistence.rag import (
    JsonObject,
    RagChunkRecord,
    RagPersistenceRepository,
)
from integration.providers.rag.embedding_provider import (
    EmbeddingRequest,
    EmbeddingVector,
    SparseEmbeddingVector,
)
from integration.providers.rag.vector_index_models import (
    VectorIndexPoint,
    VectorSearchQuery,
    VectorSearchResult,
)


@pytest.mark.asyncio
async def test_candidate_collector_preserves_hybrid_candidate_contract() -> None:
    included = _chunk("included", symbol="SPY")
    excluded = _chunk("excluded", symbol="QQQ")
    repository = FakeRepository(chunks=(included, excluded))
    embedding = EmbeddingVector(
        text_id="request-1",
        dense_vector=(0.1, 0.2),
        sparse_vector=SparseEmbeddingVector(indices=(1,), values=(0.7,)),
        model="bge-m3",
    )
    embedding_provider = FakeEmbeddingProvider(embedding=embedding)
    vector_provider = FakeVectorProvider(
        results=(VectorSearchResult(point_id="included", score=0.9),)
    )
    collector = RagCandidateCollector(
        repository=cast(RagPersistenceRepository, repository),
        embedding_provider=embedding_provider,
        vector_index_provider=vector_provider,
        filter_evaluator=RagRetrievalFilterEvaluator(),
        collection_name="rag",
        embedding_model="bge-m3",
        max_candidate_chunks=25,
        vector_search_multiplier=3,
    )
    request = RagRequest(
        query="  breadth   risk  ",
        filters=RagRetrievalFilters(symbols=("SPY",)),
        top_k=2,
        request_id="request-1",
    )

    candidates = await collector.list_lexical_candidates(
        request=request,
        exact_filters={"symbol": "SPY"},
    )
    query_embedding = await collector.embed_query(request)
    vector_results = await collector.search_vectors(
        request=request,
        query_embedding=query_embedding,
        exact_filters={"symbol": "SPY"},
    )
    rehydrated = await collector.rehydrate_vector_chunks(vector_results)

    assert candidates == (included,)
    assert repository.list_calls == (({"symbol": "SPY"}, 25),)
    assert embedding_provider.requests[0].model == "bge-m3"
    assert embedding_provider.requests[0].inputs[0].text == "breadth risk"
    assert vector_provider.searches == (
        (
            "rag",
            VectorSearchQuery(
                dense_vector=(0.1, 0.2),
                sparse_vector=SparseEmbeddingVector(indices=(1,), values=(0.7,)),
                top_k=6,
                filters={"symbol": "SPY"},
            ),
        ),
    )
    assert rehydrated == {"included": included}


class FakeRepository:
    def __init__(self, *, chunks: tuple[RagChunkRecord, ...]) -> None:
        self._chunks = chunks
        self.list_calls: tuple[tuple[JsonObject, int | None], ...] = ()

    async def list_chunks_by_metadata(
        self,
        *,
        metadata_filters: JsonObject,
        limit: int | None = None,
    ) -> Sequence[RagChunkRecord]:
        self.list_calls += ((metadata_filters, limit),)
        return tuple(
            chunk
            for chunk in self._chunks
            if all(
                chunk.metadata.get(key) == value
                for key, value in metadata_filters.items()
            )
        )

    async def get_chunk(self, chunk_id: str) -> RagChunkRecord | None:
        return next(
            (chunk for chunk in self._chunks if chunk.chunk_id == chunk_id),
            None,
        )


class FakeEmbeddingProvider:
    def __init__(self, *, embedding: EmbeddingVector) -> None:
        self._embedding = embedding
        self.requests: list[EmbeddingRequest] = []

    async def embed_texts(
        self,
        request: EmbeddingRequest,
    ) -> tuple[EmbeddingVector, ...]:
        self.requests.append(request)
        return (self._embedding,)


class FakeVectorProvider:
    def __init__(self, *, results: tuple[VectorSearchResult, ...]) -> None:
        self._results = results
        self.searches: tuple[tuple[str, VectorSearchQuery], ...] = ()

    async def upsert_points(
        self,
        *,
        collection_name: str,
        points: tuple[VectorIndexPoint, ...],
    ) -> int:
        return len(points)

    async def search(
        self,
        *,
        collection_name: str,
        query: VectorSearchQuery,
    ) -> tuple[VectorSearchResult, ...]:
        self.searches += ((collection_name, query),)
        return self._results


def _chunk(chunk_id: str, *, symbol: str) -> RagChunkRecord:
    return RagChunkRecord(
        chunk_id=chunk_id,
        document_id=f"document-{chunk_id}",
        chunk_index=0,
        chunk_text=f"Breadth evidence for {symbol}",
        token_count=4,
        metadata={"symbol": symbol},
    )
