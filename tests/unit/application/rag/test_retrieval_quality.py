from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import cast

import pytest

from application.rag.contracts.rag_context import RagRetrievedContext, RagSource
from application.rag.contracts.rag_request import RagRequest
from application.rag.retrieval.retrieval_quality import (
    Bm25LexicalRetriever,
    ParentDocumentExpander,
    RagContextDeduplicator,
    RankedRagChunk,
)
from core.storage.persistence.rag import (
    JsonObject,
    RagChunkRecord,
    RagDocumentRecord,
    RagPersistenceRepository,
)


def test_bm25_orders_fixed_corpus_deterministically() -> None:
    chunks = (
        _chunk("chunk-1", "doc-1", "liquidity risk liquidity pressure", 0),
        _chunk("chunk-2", "doc-2", "market risk outlook", 0),
        _chunk("chunk-3", "doc-3", "earnings calendar update", 0),
    )

    scores = Bm25LexicalRetriever().score(
        query="liquidity risk",
        chunks=chunks,
    )

    assert list(scores) == ["chunk-1", "chunk-2"]
    assert scores["chunk-1"] == 1.0
    assert 0 < scores["chunk-2"] < scores["chunk-1"]


@pytest.mark.asyncio
async def test_parent_expansion_returns_one_canonical_parent_for_multiple_child_hits() -> (  # noqa: E501 - descriptive pytest node id
    None
):
    document = _document(
        "doc-1",
        "# Full report\n\nBreadth weakened.\n\nLiquidity tightened.",
    )
    chunks = (
        _chunk("chunk-1", "doc-1", "Breadth weakened.", 0),
        _chunk("chunk-2", "doc-1", "Liquidity tightened.", 1),
    )
    repository = FakeRagRepository(documents=(document,), chunks=chunks)

    contexts = await ParentDocumentExpander(
        cast(RagPersistenceRepository, repository)
    ).expand(
        request=RagRequest(query="breadth liquidity", request_id="request-1"),
        ranked_chunks=(
            RankedRagChunk(chunks[0], lexical_score=0.8, vector_score=0.1),
            RankedRagChunk(chunks[1], lexical_score=0.2, vector_score=0.7),
        ),
    )

    assert len(contexts) == 1
    assert contexts[0].text == document.content_text
    assert contexts[0].source.document_id == "doc-1"
    assert contexts[0].metadata["matched_chunk_ids"] == ["chunk-1", "chunk-2"]
    assert contexts[0].metadata["parent_chunk_ids"] == ["chunk-1", "chunk-2"]


def test_context_deduplicator_removes_duplicate_citations_across_routes() -> None:
    dense = _context(
        context_id="dense:doc-1",
        document_id="doc-1",
        route="dense",
        score=0.7,
    )
    graph = _context(
        context_id="graph:node-8",
        document_id="graph-node-8",
        route="graph",
        score=0.9,
    )
    distinct = _context(
        context_id="web:doc-2",
        document_id="web-doc-2",
        route="web",
        score=0.6,
        source_id="report-2",
        text="Different evidence.",
    )

    contexts = RagContextDeduplicator().deduplicate((dense, graph, distinct))

    assert [context.context_id for context in contexts] == [
        "graph:node-8",
        "web:doc-2",
    ]
    assert [context.rank for context in contexts] == [1, 2]


class FakeRagRepository:
    def __init__(
        self,
        *,
        documents: Sequence[RagDocumentRecord],
        chunks: Sequence[RagChunkRecord],
    ) -> None:
        self.documents = tuple(documents)
        self.chunks = tuple(chunks)

    async def get_document(self, document_id: str) -> RagDocumentRecord | None:
        return next(
            (
                document
                for document in self.documents
                if document.document_id == document_id
            ),
            None,
        )

    async def list_chunks(self, document_id: str) -> Sequence[RagChunkRecord]:
        return tuple(chunk for chunk in self.chunks if chunk.document_id == document_id)


def _document(document_id: str, content_text: str) -> RagDocumentRecord:
    return RagDocumentRecord(
        document_id=document_id,
        source_table="reports",
        source_id="report-1",
        source_type="morning_report",
        title="Morning Report",
        content_text=content_text,
        generated_at=datetime(2026, 6, 1, tzinfo=UTC),
    )


def _chunk(
    chunk_id: str,
    document_id: str,
    text: str,
    chunk_index: int,
) -> RagChunkRecord:
    return RagChunkRecord(
        chunk_id=chunk_id,
        document_id=document_id,
        chunk_index=chunk_index,
        chunk_text=text,
        metadata={"source_table": "reports", "source_record_id": "report-1"},
    )


def _context(
    *,
    context_id: str,
    document_id: str,
    route: str,
    score: float,
    source_id: str = "report-1",
    text: str = "Same canonical evidence.",
) -> RagRetrievedContext:
    metadata: JsonObject = {"route": route}
    return RagRetrievedContext(
        context_id=context_id,
        text=text,
        source=RagSource(
            source_table="reports",
            source_id=source_id,
            source_type="morning_report",
            document_id=document_id,
            title="Report",
        ),
        score=score,
        rank=0,
        retrieval_route=route,
        metadata=metadata,
    )
