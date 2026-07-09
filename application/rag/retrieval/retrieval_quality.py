from __future__ import annotations

import math
import re

from collections import Counter
from dataclasses import dataclass
from dataclasses import replace
from typing import cast

from application.rag.contracts.rag_context import RagRetrievedContext
from application.rag.contracts.rag_context import RagSource
from application.rag.contracts.rag_request import RagRequest
from core.storage.persistence.rag import JsonObject
from core.storage.persistence.rag import RagChunkRecord
from core.storage.persistence.rag import RagDocumentRecord
from core.storage.persistence.rag import RagPersistenceRepository

_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+")
_STOP_WORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "the",
        "to",
        "with",
    }
)


@dataclass(
    frozen=True,
    slots=True,
)
class RankedRagChunk:
    chunk: RagChunkRecord
    lexical_score: float
    vector_score: float

    @property
    def retrieval_score(
        self,
    ) -> float:
        return self.lexical_score + self.vector_score


class Bm25LexicalRetriever:
    """Deterministic BM25 scoring over canonical PostgreSQL RAG chunks."""

    def __init__(
        self,
        *,
        k1: float = 1.5,
        b: float = 0.75,
    ) -> None:
        if k1 <= 0:
            raise ValueError("k1 must be positive.")
        if not 0 <= b <= 1:
            raise ValueError("b must be between 0 and 1.")
        self._k1 = k1
        self._b = b

    def score(
        self,
        *,
        query: str,
        chunks: tuple[RagChunkRecord, ...],
    ) -> dict[str, float]:
        query_terms = tuple(
            dict.fromkeys(token for token in _tokens(query) if token not in _STOP_WORDS)
        )
        if not query_terms or not chunks:
            return {}

        tokenized_chunks = tuple(_tokens(chunk.chunk_text) for chunk in chunks)
        average_length = sum(len(tokens) for tokens in tokenized_chunks) / len(chunks)
        document_frequency = {
            term: sum(1 for tokens in tokenized_chunks if term in set(tokens))
            for term in query_terms
        }
        raw_scores: dict[str, float] = {}
        for chunk, tokens in zip(chunks, tokenized_chunks, strict=True):
            frequencies = Counter(tokens)
            score = sum(
                self._term_score(
                    term_frequency=frequencies[term],
                    document_frequency=document_frequency[term],
                    document_count=len(chunks),
                    document_length=len(tokens),
                    average_length=average_length,
                )
                for term in query_terms
            )
            if score > 0:
                raw_scores[chunk.chunk_id] = score
        return _normalize_scores(raw_scores)

    def _term_score(
        self,
        *,
        term_frequency: int,
        document_frequency: int,
        document_count: int,
        document_length: int,
        average_length: float,
    ) -> float:
        if term_frequency <= 0:
            return 0.0
        inverse_document_frequency = math.log(
            1 + (document_count - document_frequency + 0.5) / (document_frequency + 0.5)
        )
        length_ratio = document_length / max(average_length, 1.0)
        denominator = term_frequency + self._k1 * (1 - self._b + self._b * length_ratio)
        return inverse_document_frequency * (
            term_frequency * (self._k1 + 1) / denominator
        )


class ParentDocumentExpander:
    """Expand ranked child hits to one canonical parent-document context."""

    def __init__(
        self,
        repository: RagPersistenceRepository,
    ) -> None:
        self._repository = repository

    async def expand(
        self,
        *,
        request: RagRequest,
        ranked_chunks: tuple[RankedRagChunk, ...],
    ) -> tuple[RagRetrievedContext, ...]:
        grouped: dict[str, list[RankedRagChunk]] = {}
        for ranked_chunk in ranked_chunks:
            grouped.setdefault(ranked_chunk.chunk.document_id, []).append(ranked_chunk)

        contexts: list[RagRetrievedContext] = []
        for document_id, matches in grouped.items():
            document = await self._repository.get_document(document_id)
            if document is None:
                continue
            contexts.append(
                await self._parent_context(
                    request=request,
                    document=document,
                    matches=tuple(matches),
                )
            )
        return tuple(
            replace(context, rank=rank)
            for rank, context in enumerate(
                sorted(
                    contexts,
                    key=lambda context: (-context.score, context.source.document_id),
                ),
                start=1,
            )
        )

    async def _parent_context(
        self,
        *,
        request: RagRequest,
        document: RagDocumentRecord,
        matches: tuple[RankedRagChunk, ...],
    ) -> RagRetrievedContext:
        child_chunks = tuple(await self._repository.list_chunks(document.document_id))
        ordered_children = tuple(
            sorted(child_chunks, key=lambda chunk: (chunk.chunk_index, chunk.chunk_id))
        )
        text = document.content_text.strip() or "\n\n".join(
            chunk.chunk_text for chunk in ordered_children
        )
        best_match = max(
            matches,
            key=lambda item: (item.retrieval_score, -item.chunk.chunk_index),
        )
        matched_chunk_ids = tuple(
            item.chunk.chunk_id
            for item in sorted(
                matches,
                key=lambda item: (item.chunk.chunk_index, item.chunk.chunk_id),
            )
        )
        metadata = {
            **dict(document.metadata),
            **dict(best_match.chunk.metadata),
            "matched_chunk_ids": list(matched_chunk_ids),
            "parent_chunk_ids": [chunk.chunk_id for chunk in ordered_children],
            "lexical_score": best_match.lexical_score,
            "vector_score": best_match.vector_score,
            "retrieval_score": best_match.retrieval_score,
            "parent_expanded": True,
        }
        return RagRetrievedContext(
            context_id=f"{request.request_id}:{document.document_id}",
            text=text,
            source=RagSource(
                source_table=document.source_table,
                source_id=document.source_id,
                source_type=document.source_type,
                document_id=document.document_id,
                title=document.title,
                generated_at=document.generated_at,
                workflow_name=document.workflow_name,
                execution_id=document.execution_id,
                metadata=cast(JsonObject, dict(document.metadata)),
            ),
            score=best_match.retrieval_score,
            rank=0,
            retrieval_route=request.route,
            metadata=cast(JsonObject, metadata),
        )


class RagContextDeduplicator:
    """Deterministically deduplicate contexts from all retrieval channels."""

    def deduplicate(
        self,
        contexts: tuple[RagRetrievedContext, ...],
    ) -> tuple[RagRetrievedContext, ...]:
        selected: dict[tuple[str, ...], RagRetrievedContext] = {}
        for context in contexts:
            identity = _context_identity(context)
            existing = selected.get(identity)
            if existing is None or context.score > existing.score:
                selected[identity] = context
        ranked = sorted(
            selected.values(),
            key=lambda context: (
                -context.score,
                context.source.source_table,
                context.source.source_id,
                context.context_id,
            ),
        )
        return tuple(
            replace(context, rank=rank) for rank, context in enumerate(ranked, start=1)
        )


def _context_identity(
    context: RagRetrievedContext,
) -> tuple[str, ...]:
    normalized_text = " ".join(context.text.lower().split())
    return (
        context.source.source_table,
        context.source.source_id,
        normalized_text,
    )


def _normalize_scores(
    scores: dict[str, float],
) -> dict[str, float]:
    maximum = max(scores.values(), default=0.0)
    if maximum <= 0:
        return {}
    return {key: value / maximum for key, value in scores.items()}


def _tokens(
    value: str,
) -> tuple[str, ...]:
    return tuple(match.group(0).lower() for match in _TOKEN_PATTERN.finditer(value))
