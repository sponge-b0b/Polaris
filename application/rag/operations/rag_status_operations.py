from __future__ import annotations

from time import perf_counter

from application.rag.contracts.rag_operation_models import (
    RagCanonicalProjectionReadiness,
    RagGraphProjectionReadiness,
    RagModelReadiness,
    RagProjectionReadinessConfig,
    RagProjectionReadinessResult,
    RagStatusOperationRequest,
    RagVectorProjectionReadiness,
)
from core.storage.persistence.rag import RagPersistenceRepository
from core.telemetry.emitters.application_rag_telemetry import ApplicationRagTelemetry
from integration.providers.rag.embedding_provider import (
    EmbeddingInput,
    EmbeddingProvider,
    EmbeddingRequest,
)
from integration.providers.rag.graph_projection_provider import GraphProjectionProvider
from integration.providers.rag.reranking_provider import (
    RerankCandidate,
    RerankingProvider,
    RerankRequest,
)
from integration.providers.rag.vector_index_provider import (
    VectorCollectionLifecycleProvider,
)


class RagStatusOperationsService:
    """Reports typed readiness for canonical RAG records and projections."""

    def __init__(
        self,
        rag_repository: RagPersistenceRepository,
        vector_provider: VectorCollectionLifecycleProvider,
        graph_provider: GraphProjectionProvider,
        embedding_provider: EmbeddingProvider,
        reranking_provider: RerankingProvider,
        config: RagProjectionReadinessConfig,
        telemetry: ApplicationRagTelemetry | None = None,
    ) -> None:
        self._rag_repository = rag_repository
        self._vector_provider = vector_provider
        self._graph_provider = graph_provider
        self._embedding_provider = embedding_provider
        self._reranking_provider = reranking_provider
        self._config = config
        self._telemetry = telemetry

    async def status(
        self,
        request: RagStatusOperationRequest,
    ) -> RagProjectionReadinessResult:
        del request
        operation = "rag.status"
        started_at = perf_counter()
        if self._telemetry is not None:
            await self._telemetry.emit_operation_started(
                self.__class__.__name__, operation
            )

        canonical = await self._canonical_readiness()
        vector = await self._vector_readiness()
        graph = await self._graph_readiness()
        embedding = await self._embedding_readiness()
        reranker = await self._reranker_readiness()
        ready = all(
            (
                canonical.available,
                vector.ready,
                graph.ready,
                embedding.ready,
                reranker.ready,
            )
        )
        result = RagProjectionReadinessResult(
            operation=operation,
            status="ready" if ready else "degraded",
            message=(
                "RAG projections and model dependencies are ready."
                if ready
                else "One or more RAG projection dependencies require attention."
            ),
            canonical=canonical,
            vector=vector,
            graph=graph,
            embedding=embedding,
            reranker=reranker,
        )
        if self._telemetry is not None:
            attributes = {
                "ready": ready,
                "postgresql_available": canonical.available,
                "qdrant_ready": vector.ready,
                "neo4j_ready": graph.ready,
                "embedding_ready": embedding.ready,
                "reranker_ready": reranker.ready,
            }
            if ready:
                await self._telemetry.emit_operation_completed(
                    self.__class__.__name__,
                    operation,
                    duration_seconds=perf_counter() - started_at,
                    attributes=attributes,
                )
            else:
                await self._telemetry.emit_operation_degraded(
                    self.__class__.__name__,
                    operation,
                    duration_seconds=perf_counter() - started_at,
                    attributes=attributes,
                )
        return result

    async def _emit_readiness_degraded(
        self,
        operation: str,
        error: BaseException,
    ) -> None:
        if self._telemetry is None:
            return
        await self._telemetry.emit_operation_degraded(
            self.__class__.__name__,
            operation,
            error=error,
        )

    async def _canonical_readiness(self) -> RagCanonicalProjectionReadiness:
        try:
            counts = await self._rag_repository.get_canonical_record_counts()
            jobs = await self._rag_repository.list_embedding_jobs()
        except Exception as exc:
            await self._emit_readiness_degraded("rag.status.postgresql", exc)
            return RagCanonicalProjectionReadiness(
                available=False,
                document_count=None,
                chunk_count=None,
                embedding_job_count=None,
                graph_job_count=None,
                pending_embedding_jobs=None,
                retryable_embedding_jobs=None,
                failed_embedding_jobs=None,
                error=str(exc),
            )
        return RagCanonicalProjectionReadiness(
            available=True,
            document_count=counts.document_count,
            chunk_count=counts.chunk_count,
            embedding_job_count=counts.embedding_job_count,
            graph_job_count=counts.graph_job_count,
            pending_embedding_jobs=sum(
                job.status in {"queued", "processing"} for job in jobs
            ),
            retryable_embedding_jobs=sum(
                job.status == "queued" and job.attempts > 0 for job in jobs
            ),
            failed_embedding_jobs=sum(job.status == "failed" for job in jobs),
        )

    async def _vector_readiness(self) -> RagVectorProjectionReadiness:
        try:
            status = await self._vector_provider.inspect_collection(
                collection_name=self._config.collection_name,
                vector_size=self._config.vector_size,
            )
        except Exception as exc:
            await self._emit_readiness_degraded("rag.status.qdrant", exc)
            return RagVectorProjectionReadiness(
                collection_name=self._config.collection_name,
                exists=False,
                healthy=False,
                dense_vector_present=False,
                sparse_vector_present=False,
                configured_vector_size=self._config.vector_size,
                actual_vector_size=None,
                vector_size_compatible=False,
                points_count=0,
                error=str(exc),
            )
        return RagVectorProjectionReadiness(
            collection_name=status.collection_name,
            exists=status.exists,
            healthy=status.healthy,
            dense_vector_present=status.dense_vector_present,
            sparse_vector_present=status.sparse_vector_present,
            configured_vector_size=status.configured_vector_size,
            actual_vector_size=status.actual_vector_size,
            vector_size_compatible=status.vector_size_compatible,
            points_count=status.points_count,
            status=status.status,
        )

    async def _graph_readiness(self) -> RagGraphProjectionReadiness:
        try:
            status = await self._graph_provider.status()
        except Exception as exc:
            await self._emit_readiness_degraded("rag.status.neo4j", exc)
            return RagGraphProjectionReadiness(
                connected=False,
                healthy=False,
                entity_count=None,
                error=str(exc),
            )
        return RagGraphProjectionReadiness(
            connected=True,
            healthy=status.healthy,
            entity_count=status.entity_count,
        )

    async def _embedding_readiness(self) -> RagModelReadiness:
        try:
            vectors = await self._embedding_provider.embed_texts(
                EmbeddingRequest(
                    inputs=(
                        EmbeddingInput(
                            text_id="rag-readiness",
                            text="RAG embedding readiness probe.",
                        ),
                    ),
                    model=self._config.embedding_model,
                )
            )
            dimensions = vectors[0].dimensions if len(vectors) == 1 else None
            ready = dimensions == self._config.vector_size
            error = (
                None if ready else "Embedding dimensions do not match configuration."
            )
        except Exception as exc:
            await self._emit_readiness_degraded("rag.status.embedding", exc)
            dimensions = None
            ready = False
            error = str(exc)
        return RagModelReadiness(
            component="embedding",
            model=self._config.embedding_model,
            ready=ready,
            dimensions=dimensions,
            error=error,
        )

    async def _reranker_readiness(self) -> RagModelReadiness:
        try:
            results = await self._reranking_provider.rerank(
                RerankRequest(
                    query="RAG reranker readiness probe.",
                    candidates=(
                        RerankCandidate(
                            candidate_id="rag-readiness",
                            text="RAG reranker readiness probe.",
                        ),
                    ),
                    top_k=1,
                )
            )
            ready = len(results) == 1
            error = None if ready else "Reranker returned no readiness result."
        except Exception as exc:
            await self._emit_readiness_degraded("rag.status.reranker", exc)
            ready = False
            error = str(exc)
        return RagModelReadiness(
            component="reranker",
            model=self._config.reranker_model,
            ready=ready,
            error=error,
        )
