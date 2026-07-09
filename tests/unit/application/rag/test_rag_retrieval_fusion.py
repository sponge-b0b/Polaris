from __future__ import annotations

from application.rag.retrieval.rag_retrieval_fusion import RagRetrievalFusion
from core.storage.persistence.rag import RagChunkRecord
from integration.providers.rag.vector_index_models import VectorSearchResult


def test_hybrid_fusion_preserves_score_and_tie_break_order() -> None:
    fusion = RagRetrievalFusion(
        lexical_weight=0.5,
        vector_weight=0.5,
        rerank_multiplier=3,
    )
    lexical_chunk = _chunk("lexical", chunk_index=0)
    vector_chunk = _chunk("vector", chunk_index=1)

    ranked = fusion.rank(
        top_k=2,
        lexical_scores={"lexical": 1.0},
        vector_results=(VectorSearchResult(point_id="vector", score=2.0),),
        lexical_chunks=(lexical_chunk,),
        vector_chunks={"vector": vector_chunk},
    )

    assert [item.chunk.chunk_id for item in ranked] == ["vector", "lexical"]
    assert [item.retrieval_score for item in ranked] == [0.5, 0.5]
    assert [item.vector_score for item in ranked] == [0.5, 0.0]
    assert [item.lexical_score for item in ranked] == [0.0, 0.5]


def test_hybrid_fusion_normalizes_positive_vectors_and_caps_rerank_pool() -> None:
    fusion = RagRetrievalFusion(
        lexical_weight=0.45,
        vector_weight=0.55,
        rerank_multiplier=2,
    )
    chunks = tuple(_chunk(f"chunk-{index}", chunk_index=index) for index in range(4))
    results = tuple(
        VectorSearchResult(point_id=chunk.chunk_id, score=float(index + 1))
        for index, chunk in enumerate(chunks)
    )

    ranked = fusion.rank(
        top_k=1,
        lexical_scores={},
        vector_results=results,
        lexical_chunks=(),
        vector_chunks={chunk.chunk_id: chunk for chunk in chunks},
    )

    assert [item.chunk.chunk_id for item in ranked] == ["chunk-3", "chunk-2"]
    assert ranked[0].vector_score == 0.55
    assert ranked[1].vector_score == 0.55 * 0.75


def _chunk(
    chunk_id: str,
    *,
    chunk_index: int,
) -> RagChunkRecord:
    return RagChunkRecord(
        chunk_id=chunk_id,
        document_id=f"document-{chunk_id}",
        chunk_index=chunk_index,
        chunk_text=f"Text for {chunk_id}",
        token_count=3,
        metadata={},
    )
