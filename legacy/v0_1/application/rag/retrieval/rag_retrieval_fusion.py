from __future__ import annotations

from application.rag.retrieval.retrieval_quality import RankedRagChunk
from core.storage.persistence.rag import RagChunkRecord
from integration.providers.rag.vector_index_models import VectorSearchResult


class RagRetrievalFusion:
    """Apply the canonical deterministic hybrid score and tie-break policy."""

    def __init__(
        self,
        *,
        lexical_weight: float,
        vector_weight: float,
        rerank_multiplier: int,
    ) -> None:
        self._lexical_weight = lexical_weight
        self._vector_weight = vector_weight
        self._rerank_multiplier = rerank_multiplier

    def rank(
        self,
        *,
        top_k: int,
        lexical_scores: dict[str, float],
        vector_results: tuple[VectorSearchResult, ...],
        lexical_chunks: tuple[RagChunkRecord, ...],
        vector_chunks: dict[str, RagChunkRecord],
    ) -> tuple[RankedRagChunk, ...]:
        chunk_by_id = {chunk.chunk_id: chunk for chunk in lexical_chunks}
        chunk_by_id.update(vector_chunks)
        vector_scores = _normalized_vector_scores(vector_results)
        ranked = sorted(
            (
                RankedRagChunk(
                    chunk=chunk,
                    lexical_score=lexical_scores.get(chunk_id, 0.0)
                    * self._lexical_weight,
                    vector_score=vector_scores.get(chunk_id, 0.0) * self._vector_weight,
                )
                for chunk_id, chunk in chunk_by_id.items()
                if lexical_scores.get(chunk_id, 0.0) > 0
                or vector_scores.get(chunk_id, 0.0) > 0
            ),
            key=lambda item: (
                -item.retrieval_score,
                -item.vector_score,
                -item.lexical_score,
                item.chunk.chunk_index,
                item.chunk.chunk_id,
            ),
        )
        return tuple(ranked[: self._rerank_multiplier * top_k])


def _normalized_vector_scores(
    results: tuple[VectorSearchResult, ...],
) -> dict[str, float]:
    positive_scores = tuple(max(result.score, 0.0) for result in results)
    max_score = max(positive_scores, default=0.0)
    if max_score <= 0:
        return {}
    return {result.point_id: max(result.score, 0.0) / max_score for result in results}
