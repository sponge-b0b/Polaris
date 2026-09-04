from __future__ import annotations

import pytest

from application.rag.contracts.rag_context import RagRetrievedContext, RagSource
from application.rag.contracts.rag_request import RagRequest
from application.rag.retrieval.web_fallback_service import RagWebFallbackService
from core.telemetry.emitters.application_rag_telemetry import ApplicationRagTelemetry
from core.telemetry.observability.observability_manager import ObservabilityManager
from core.telemetry.sinks.telemetry_sink import InMemoryTelemetrySink
from integration.providers.rag.web_retrieval_provider import WebRetrievalRequest


class FakeWebRetrievalProvider:
    def __init__(
        self,
        contexts: tuple[RagRetrievedContext, ...] = (),
        error: Exception | None = None,
    ) -> None:
        self.contexts = contexts
        self.error = error
        self.requests: list[WebRetrievalRequest] = []

    async def retrieve(
        self,
        request: WebRetrievalRequest,
    ) -> tuple[RagRetrievedContext, ...]:
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        return self.contexts


@pytest.mark.asyncio
async def test_web_fallback_is_disabled_by_default_without_provider_call() -> None:
    provider = FakeWebRetrievalProvider((_context(),))
    service = RagWebFallbackService(provider)

    contexts = await service.retrieve(RagRequest(query="SPY breadth"))

    assert contexts == ()
    assert provider.requests == []


@pytest.mark.asyncio
async def test_web_fallback_bounds_result_count_and_uses_normalized_query() -> None:
    provider = FakeWebRetrievalProvider((_context(),))
    service = RagWebFallbackService(provider, max_results=2)

    contexts = await service.retrieve(
        RagRequest(query="  SPY   breadth ", top_k=5, allow_web=True)
    )

    assert contexts == (_context(),)
    assert provider.requests[0].query == "SPY breadth"
    assert provider.requests[0].top_k == 2


@pytest.mark.asyncio
async def test_web_fallback_fails_closed_when_provider_errors() -> None:
    provider = FakeWebRetrievalProvider(error=RuntimeError("unavailable"))
    service = RagWebFallbackService(provider)

    contexts = await service.retrieve(RagRequest(query="SPY breadth", allow_web=True))

    assert contexts == ()


def _context() -> RagRetrievedContext:
    source = RagSource(
        source_table="external_web",
        source_id="https://example.com/breadth",
        source_type="web_fallback",
        document_id="web_document:test",
        title="Breadth Update",
        metadata={"transient": True, "untrusted": True},
    )
    return RagRetrievedContext(
        context_id="web:test",
        text="Breadth improved.",
        source=source,
        score=1.0,
        rank=0,
        retrieval_route="web_fallback",
        metadata={"transient": True, "untrusted": True},
    )


@pytest.mark.asyncio
async def test_web_fallback_failure_is_owned_by_canonical_telemetry() -> None:
    sink = InMemoryTelemetrySink()
    observability = ObservabilityManager()
    observability.add_sink(sink)
    provider = FakeWebRetrievalProvider(error=RuntimeError("unavailable"))
    service = RagWebFallbackService(
        provider,
        telemetry=ApplicationRagTelemetry(observability),
    )

    contexts = await service.retrieve(RagRequest(query="SPY breadth", allow_web=True))

    assert contexts == ()
    assert [event.event_type for event in sink.events] == [
        "application.rag.operation.started",
        "application.rag.operation.failed",
    ]
    assert sink.events[-1].exception_details is not None
    assert sink.events[-1].exception_details.message == "unavailable"
