from __future__ import annotations

from time import perf_counter

from application.rag.contracts.rag_context import RagRetrievedContext
from application.rag.contracts.rag_request import RagRequest
from core.telemetry.emitters.application_rag_telemetry import ApplicationRagTelemetry
from integration.providers.rag.web_retrieval_provider import WebRetrievalProvider
from integration.providers.rag.web_retrieval_provider import WebRetrievalRequest


class RagWebFallbackService:
    """Application boundary for explicitly permitted transient web retrieval."""

    def __init__(
        self,
        provider: WebRetrievalProvider,
        telemetry: ApplicationRagTelemetry | None = None,
        max_results: int = 5,
    ) -> None:
        if max_results <= 0:
            raise ValueError("max_results must be positive.")
        self._provider = provider
        self._telemetry = telemetry
        self._max_results = max_results

    async def retrieve(self, request: RagRequest) -> tuple[RagRetrievedContext, ...]:
        if not request.allow_web:
            return ()
        operation = "firecrawl_web_fallback"
        started_at = perf_counter()
        if self._telemetry is not None:
            await self._telemetry.emit_operation_started(
                self.__class__.__name__,
                operation,
                correlation_id=request.request_id,
            )
        try:
            contexts = await self._provider.retrieve(
                WebRetrievalRequest(
                    request_id=request.request_id,
                    query=request.normalized_query,
                    top_k=min(request.top_k, self._max_results),
                )
            )
        except Exception as exc:
            if self._telemetry is not None:
                await self._telemetry.emit_operation_failed(
                    self.__class__.__name__,
                    operation,
                    error=exc,
                    duration_seconds=perf_counter() - started_at,
                    correlation_id=request.request_id,
                )
            return ()
        if self._telemetry is not None:
            await self._telemetry.emit_operation_completed(
                self.__class__.__name__,
                operation,
                duration_seconds=perf_counter() - started_at,
                correlation_id=request.request_id,
                attributes={"context_count": len(contexts)},
            )
        return contexts
