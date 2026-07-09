from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from datetime import timezone
from typing import cast

import pytest

from application.rag.contracts.rag_request import RagRequest
from application.rag.contracts.rag_context import RagRetrievedContext
from application.rag.contracts.rag_context import RagSource
from application.rag.contracts.rag_context import RagRetrievalFilters
from application.rag.retrieval.rag_retriever import RagRetriever
from application.rag.retrieval.rag_retriever import RagRetrieverConfig
from core.storage.persistence.rag import JsonObject
from core.storage.persistence.rag import RagChunkRecord
from core.storage.persistence.rag import RagDocumentRecord
from core.storage.persistence.rag import RagPersistenceRepository
from core.telemetry.emitters.application_rag_telemetry import ApplicationRagTelemetry
from core.telemetry.observability.observability_manager import ObservabilityManager
from core.telemetry.sinks.telemetry_sink import InMemoryTelemetrySink
from integration.providers.rag.embedding_provider import EmbeddingRequest
from integration.providers.rag.embedding_provider import EmbeddingVector
from integration.providers.rag.embedding_provider import SparseEmbeddingVector
from integration.providers.rag.reranking_provider import RerankRequest
from integration.providers.rag.reranking_provider import RerankResult
from integration.providers.rag.vector_index_models import VectorIndexPoint
from integration.providers.rag.vector_index_models import VectorSearchQuery
from integration.providers.rag.vector_index_models import VectorSearchResult


@pytest.mark.asyncio
async def test_rag_retriever_fuses_bm25_and_dense_results_deterministically() -> None:
    repository = FakeRagRepository(
        documents=(
            _document(
                "document-a",
                "# Breadth\n\nMarket breadth risk is weak and liquidity risk is elevated.",
                source_id="report-a",
            ),
            _document(
                "document-b",
                "# Calendar\n\nEarnings calendar and macro calendar updates.",
                source_id="report-b",
            ),
            _document(
                "document-c",
                "# Excluded\n\nMarket breadth risk for a different symbol.",
                source_id="report-c",
            ),
        ),
        chunks=(
            _chunk(
                "chunk-a",
                "document-a",
                "Market breadth risk is weak and liquidity risk is elevated.",
                source_id="report-a",
                section_name="breadth",
            ),
            _chunk(
                "chunk-b",
                "document-b",
                "Earnings calendar and macro calendar updates.",
                source_id="report-b",
                section_name="calendar",
            ),
            _chunk(
                "chunk-c",
                "document-c",
                "Market breadth risk for a different symbol.",
                source_id="report-c",
                symbol="AAPL",
                section_name="excluded",
            ),
        ),
    )
    embedding_provider = FakeEmbeddingProvider(
        vectors=(
            EmbeddingVector(
                text_id="request-1",
                dense_vector=(0.1, 0.2, 0.3),
                sparse_vector=SparseEmbeddingVector(indices=(1, 4), values=(0.7, 0.2)),
                model="bge-large",
            ),
        )
    )
    vector_provider = FakeVectorIndexProvider(
        results=(
            VectorSearchResult(point_id="chunk-b", score=0.4),
            VectorSearchResult(point_id="chunk-a", score=0.2),
        )
    )
    retriever = RagRetriever(
        repository=cast(RagPersistenceRepository, repository),
        embedding_provider=embedding_provider,
        vector_index_provider=vector_provider,
        config=RagRetrieverConfig(collection_name="polaris_rag_chunks"),
    )

    result = await retriever.retrieve(
        RagRequest(
            query="breadth risk",
            filters=RagRetrievalFilters(
                source_types=("morning_report",),
                symbols=("SPY",),
            ),
            top_k=2,
            request_id="request-1",
        )
    )

    assert result.found_count == 2
    assert [context.source.document_id for context in result.contexts] == [
        "document-a",
        "document-b",
    ]
    assert result.contexts[0].rank == 1
    assert result.contexts[0].source.title == "Morning Report"
    assert result.contexts[0].source.source_table == "reports"
    assert result.contexts[0].source.source_id == "report-a"
    assert result.contexts[0].metadata["parent_expanded"] is True
    assert result.contexts[0].metadata["matched_chunk_ids"] == ["chunk-a"]
    assert _float_metadata(result.contexts[0].metadata, "lexical_score") > 0
    assert _float_metadata(result.contexts[0].metadata, "vector_score") > 0
    assert repository.metadata_filter_calls == (
        ({"source_type": "morning_report", "symbol": "SPY"}, 200),
    )
    assert embedding_provider.requests[0].inputs[0].text == "breadth risk"
    assert vector_provider.searches == (
        (
            "polaris_rag_chunks",
            VectorSearchQuery(
                dense_vector=(0.1, 0.2, 0.3),
                sparse_vector=SparseEmbeddingVector(indices=(1, 4), values=(0.7, 0.2)),
                top_k=6,
                filters={"source_type": "morning_report", "symbol": "SPY"},
            ),
        ),
    )


@pytest.mark.asyncio
async def test_rag_retriever_applies_deterministic_as_of_range_filter() -> None:
    repository = FakeRagRepository(
        documents=(
            _document(
                "document-old", "Breadth evidence from early June.", source_id="old"
            ),
            _document(
                "document-new", "Breadth evidence from late June.", source_id="new"
            ),
        ),
        chunks=(
            _chunk(
                "chunk-old",
                "document-old",
                "Breadth evidence from early June.",
                source_id="old",
                section_name="breadth",
                as_of_date="2026-06-01",
            ),
            _chunk(
                "chunk-new",
                "document-new",
                "Breadth evidence from late June.",
                source_id="new",
                section_name="breadth",
                as_of_date="2026-06-20",
            ),
        ),
    )
    retriever = RagRetriever(
        repository=cast(RagPersistenceRepository, repository),
        embedding_provider=FakeEmbeddingProvider(
            vectors=(
                EmbeddingVector(
                    text_id="request-date-range",
                    dense_vector=(0.1, 0.2, 0.3),
                    sparse_vector=SparseEmbeddingVector(indices=(1,), values=(0.5,)),
                    model="bge-large",
                ),
            )
        ),
        vector_index_provider=FakeVectorIndexProvider(results=()),
    )

    result = await retriever.retrieve(
        RagRequest(
            query="breadth evidence",
            filters=RagRetrievalFilters(
                as_of_start=datetime(2026, 6, 15, tzinfo=timezone.utc),
                as_of_end=datetime(2026, 6, 30, tzinfo=timezone.utc),
            ),
            top_k=2,
            request_id="request-date-range",
        )
    )

    assert [context.source.source_id for context in result.contexts] == ["new"]


@pytest.mark.asyncio
async def test_rag_retriever_rehydrates_dense_hits_and_expands_parent() -> None:
    repository = FakeRagRepository(
        documents=(
            _document(
                "document-a",
                "# Risk\n\nCapital preservation risk controls are active.",
                source_id="report-a",
            ),
        ),
        chunks=(
            _chunk(
                "chunk-a",
                "document-a",
                "Capital preservation risk controls are active.",
                source_id="report-a",
                section_name="risk",
            ),
        ),
        list_chunks_result=(),
    )
    retriever = RagRetriever(
        repository=cast(RagPersistenceRepository, repository),
        embedding_provider=FakeEmbeddingProvider(
            vectors=(
                EmbeddingVector(
                    text_id="request-2",
                    dense_vector=(0.4, 0.5, 0.6),
                    sparse_vector=SparseEmbeddingVector(indices=(2,), values=(0.8,)),
                    model="bge-large",
                ),
            )
        ),
        vector_index_provider=FakeVectorIndexProvider(
            results=(VectorSearchResult(point_id="chunk-a", score=0.7),)
        ),
    )

    result = await retriever.retrieve(
        RagRequest(
            query="capital preservation",
            top_k=1,
            request_id="request-2",
        )
    )

    assert result.found_count == 1
    assert result.contexts[0].text.startswith("# Risk")
    assert result.contexts[0].metadata["parent_chunk_ids"] == ["chunk-a"]
    assert _float_metadata(result.contexts[0].metadata, "lexical_score") == 0.0
    assert _float_metadata(result.contexts[0].metadata, "vector_score") > 0.0
    assert repository.get_chunk_calls == ("chunk-a",)


@pytest.mark.asyncio
async def test_rag_retriever_applies_reranker_order_after_hybrid_retrieval() -> None:
    repository = FakeRagRepository(
        documents=(
            _document("document-a", "Broad market risk evidence.", source_id="a"),
            _document("document-b", "Specific liquidity risk evidence.", source_id="b"),
        ),
        chunks=(
            _chunk(
                "chunk-a",
                "document-a",
                "Broad market risk evidence.",
                source_id="a",
                section_name="risk",
            ),
            _chunk(
                "chunk-b",
                "document-b",
                "Specific liquidity risk evidence.",
                source_id="b",
                section_name="liquidity",
            ),
        ),
    )
    reranker = FakeRerankingProvider(preferred_document_id="document-b")
    retriever = RagRetriever(
        repository=cast(RagPersistenceRepository, repository),
        embedding_provider=FakeEmbeddingProvider(
            vectors=(
                EmbeddingVector(
                    text_id="request-rerank",
                    dense_vector=(0.1, 0.2),
                    sparse_vector=SparseEmbeddingVector(indices=(3,), values=(0.9,)),
                    model="bge-large",
                ),
            )
        ),
        vector_index_provider=FakeVectorIndexProvider(
            results=(
                VectorSearchResult(point_id="chunk-a", score=0.9),
                VectorSearchResult(point_id="chunk-b", score=0.4),
            )
        ),
        reranking_provider=reranker,
    )

    result = await retriever.retrieve(
        RagRequest(
            query="specific liquidity risk",
            top_k=2,
            request_id="request-rerank",
        )
    )

    assert [context.source.document_id for context in result.contexts] == [
        "document-b",
        "document-a",
    ]
    assert [context.rank for context in result.contexts] == [1, 2]
    assert _float_metadata(result.contexts[0].metadata, "rerank_score") == 0.95
    assert reranker.requests[0].query == "specific liquidity risk"


@pytest.mark.asyncio
async def test_rag_retriever_merges_graph_contexts_before_reranking() -> None:
    repository = FakeRagRepository(documents=(), chunks=())
    graph_context = RagRetrievedContext(
        context_id="graph:document-graph",
        text="SPY is linked to a risk-on technical regime.",
        source=RagSource(
            source_table="agent_signals",
            source_id="signal-1",
            source_type="technical_signal",
            document_id="document-graph",
            title="Technical Signal",
        ),
        score=2.0,
        rank=1,
        retrieval_route="graph",
    )
    graph_retriever = FakeGraphRetriever(contexts=(graph_context,))
    retriever = RagRetriever(
        repository=cast(RagPersistenceRepository, repository),
        embedding_provider=FakeEmbeddingProvider(
            vectors=(
                EmbeddingVector(
                    text_id="request-graph",
                    dense_vector=(0.1, 0.2, 0.3),
                    sparse_vector=SparseEmbeddingVector(indices=(1,), values=(0.5,)),
                    model="bge-large",
                ),
            )
        ),
        vector_index_provider=FakeVectorIndexProvider(results=()),
        graph_retriever=graph_retriever,
    )

    result = await retriever.retrieve(
        RagRequest(query="SPY risk-on", top_k=1, request_id="request-graph")
    )

    assert result.contexts == (graph_context,)
    assert graph_retriever.requests[0].request_id == "request-graph"


@pytest.mark.asyncio
async def test_rag_retriever_continues_when_optional_graph_store_is_unavailable() -> (
    None
):
    telemetry, sink, _ = _telemetry()
    repository = FakeRagRepository(documents=(), chunks=())
    retriever = RagRetriever(
        repository=cast(RagPersistenceRepository, repository),
        embedding_provider=FakeEmbeddingProvider(
            vectors=(
                EmbeddingVector(
                    text_id="request-graph-failure",
                    dense_vector=(0.1, 0.2, 0.3),
                    sparse_vector=SparseEmbeddingVector(indices=(1,), values=(0.5,)),
                    model="bge-large",
                ),
            )
        ),
        vector_index_provider=FakeVectorIndexProvider(results=()),
        graph_retriever=FailingGraphRetriever(),
        telemetry=telemetry,
    )

    result = await retriever.retrieve(
        RagRequest(
            query="SPY risk-on",
            top_k=1,
            request_id="request-graph-failure",
        )
    )

    assert result.contexts == ()
    graph_events = [
        event
        for event in sink.events
        if event.attributes.get("operation") == "rag.retrieval.graph"
    ]
    assert len(graph_events) == 1
    assert graph_events[0].event_type == "application.rag.operation.failed"
    assert graph_events[0].payload["error_type"] == "ConnectionError"


@pytest.mark.asyncio
async def test_rag_retriever_emits_observability_for_v2_retrieval_stages() -> None:
    telemetry, sink, observability = _telemetry()
    repository = FakeRagRepository(
        documents=(
            _document(
                "document-a",
                "Market breadth risk is improving.",
                source_id="report-a",
            ),
        ),
        chunks=(
            _chunk(
                "chunk-a",
                "document-a",
                "Market breadth risk is improving.",
                source_id="report-a",
                section_name="breadth",
            ),
        ),
    )
    retriever = RagRetriever(
        repository=cast(RagPersistenceRepository, repository),
        embedding_provider=FakeEmbeddingProvider(
            vectors=(
                EmbeddingVector(
                    text_id="request-observability",
                    dense_vector=(0.1, 0.2, 0.3),
                    sparse_vector=SparseEmbeddingVector(
                        indices=(1, 4), values=(0.7, 0.2)
                    ),
                    model="bge-large",
                ),
            )
        ),
        vector_index_provider=FakeVectorIndexProvider(
            results=(VectorSearchResult(point_id="chunk-a", score=0.8),)
        ),
        telemetry=telemetry,
    )

    result = await retriever.retrieve(
        RagRequest(
            query="breadth risk",
            top_k=1,
            request_id="request-observability",
        )
    )

    operations = _operations(sink)
    assert result.found_count == 1
    assert {
        "rag.retrieval.hybrid_v2",
        "rag.retrieval.candidates",
        "rag.retrieval.bm25",
        "rag.retrieval.query_embedding",
        "rag.retrieval.vector_search",
        "rag.retrieval.vector_rehydrate",
        "rag.retrieval.parent_expansion",
        "rag.retrieval.structured",
        "rag.retrieval.graph",
        "rag.retrieval.deduplicate",
        "rag.retrieval.rerank",
    }.issubset(set(operations))
    assert any(
        point.name == "application.rag.operations.total"
        for point in observability.metrics_store.points()
    )


class FailingGraphRetriever:
    async def retrieve(
        self,
        request: RagRequest,
    ) -> tuple[RagRetrievedContext, ...]:
        raise ConnectionError(f"Neo4j unavailable for {request.request_id}")


class FakeGraphRetriever:
    def __init__(self, *, contexts: tuple[RagRetrievedContext, ...]) -> None:
        self.contexts = contexts
        self.requests: list[RagRequest] = []

    async def retrieve(
        self,
        request: RagRequest,
    ) -> tuple[RagRetrievedContext, ...]:
        self.requests.append(request)
        return self.contexts


class FakeEmbeddingProvider:
    def __init__(self, *, vectors: tuple[EmbeddingVector, ...]) -> None:
        self.vectors = vectors
        self.requests: list[EmbeddingRequest] = []

    async def embed_texts(
        self,
        request: EmbeddingRequest,
    ) -> tuple[EmbeddingVector, ...]:
        self.requests.append(request)
        return self.vectors


class FakeVectorIndexProvider:
    def __init__(self, *, results: tuple[VectorSearchResult, ...]) -> None:
        self.results = results
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
        self.searches = self.searches + ((collection_name, query),)
        return self.results


class FakeRerankingProvider:
    def __init__(self, *, preferred_document_id: str) -> None:
        self.preferred_document_id = preferred_document_id
        self.requests: list[RerankRequest] = []

    async def rerank(self, request: RerankRequest) -> tuple[RerankResult, ...]:
        self.requests.append(request)
        ordered = sorted(
            request.candidates,
            key=lambda candidate: candidate.candidate_id.endswith(
                self.preferred_document_id
            ),
            reverse=True,
        )
        return tuple(
            RerankResult(
                candidate_id=candidate.candidate_id,
                score=0.95 if rank == 1 else 0.25,
                rank=rank,
            )
            for rank, candidate in enumerate(ordered[: request.top_k], start=1)
        )


class FakeRagRepository:
    def __init__(
        self,
        *,
        documents: Sequence[RagDocumentRecord],
        chunks: Sequence[RagChunkRecord],
        list_chunks_result: Sequence[RagChunkRecord] | None = None,
    ) -> None:
        self.documents = tuple(documents)
        self.chunks = tuple(chunks)
        self.list_chunks_result = (
            tuple(list_chunks_result)
            if list_chunks_result is not None
            else tuple(chunks)
        )
        self.metadata_filter_calls: tuple[
            tuple[dict[str, object], int | None], ...
        ] = ()
        self.get_chunk_calls: tuple[str, ...] = ()

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

    async def list_chunks_by_metadata(
        self,
        *,
        metadata_filters: JsonObject,
        limit: int | None = None,
    ) -> Sequence[RagChunkRecord]:
        self.metadata_filter_calls = self.metadata_filter_calls + (
            (dict(metadata_filters), limit),
        )
        return tuple(
            chunk
            for chunk in self.list_chunks_result
            if _matches_exact_metadata(chunk.metadata, metadata_filters)
        )

    async def get_chunk(self, chunk_id: str) -> RagChunkRecord | None:
        self.get_chunk_calls = self.get_chunk_calls + (chunk_id,)
        return next(
            (chunk for chunk in self.chunks if chunk.chunk_id == chunk_id),
            None,
        )


def _float_metadata(metadata: JsonObject, key: str) -> float:
    value = metadata[key]
    assert isinstance(value, int | float)
    return float(value)


def _matches_exact_metadata(metadata: JsonObject, filters: JsonObject) -> bool:
    return all(metadata.get(key) == expected for key, expected in filters.items())


def _document(
    document_id: str,
    content_text: str,
    *,
    source_id: str,
) -> RagDocumentRecord:
    return RagDocumentRecord(
        document_id=document_id,
        source_table="reports",
        source_id=source_id,
        source_type="morning_report",
        title="Morning Report",
        content_text=content_text,
        workflow_name="morning_report",
        execution_id="exec-1",
        generated_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
    )


def _chunk(
    chunk_id: str,
    document_id: str,
    text: str,
    *,
    source_id: str,
    symbol: str = "SPY",
    section_name: str,
    as_of_date: str = "2026-06-01",
) -> RagChunkRecord:
    return RagChunkRecord(
        chunk_id=chunk_id,
        document_id=document_id,
        chunk_index=0,
        chunk_text=text,
        token_count=8,
        metadata={
            "source_table": "reports",
            "source_record_id": source_id,
            "source_type": "morning_report",
            "workflow_name": "morning_report",
            "execution_id": "exec-1",
            "symbol": symbol,
            "section_name": section_name,
            "as_of_date": as_of_date,
        },
    )


def _telemetry() -> tuple[
    ApplicationRagTelemetry,
    InMemoryTelemetrySink,
    ObservabilityManager,
]:
    sink = InMemoryTelemetrySink()
    observability = ObservabilityManager()
    observability.add_sink(sink)
    return (
        ApplicationRagTelemetry(observability_manager=observability),
        sink,
        observability,
    )


def _operations(sink: InMemoryTelemetrySink) -> list[object]:
    return [event.attributes.get("operation") for event in sink.events]
