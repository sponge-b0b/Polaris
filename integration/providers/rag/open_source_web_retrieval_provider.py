from __future__ import annotations

from hashlib import sha256
from typing import Protocol

from application.rag.contracts.rag_context import RagRetrievedContext, RagSource
from application.rag.security.rag_security import sanitize_untrusted_text
from core.storage.persistence.rag import JsonValue
from core.telemetry.emitters.integration_telemetry import IntegrationTelemetry
from integration.clients.rag.web_retrieval_models import (
    CrawledWebDocument,
    WebSearchCandidate,
)
from integration.providers.provider_telemetry import record_provider_call
from integration.providers.rag.web_retrieval_provider import (
    WebRetrievalProvider,
    WebRetrievalRequest,
)


class WebSearchClient(Protocol):
    async def search(
        self,
        *,
        query: str,
        limit: int,
    ) -> tuple[WebSearchCandidate, ...]: ...


class WebContentClient(Protocol):
    async def crawl(
        self,
        candidates: tuple[WebSearchCandidate, ...],
    ) -> tuple[CrawledWebDocument, ...]: ...


class OpenSourceWebRetrievalProvider(WebRetrievalProvider):
    """Compose SearXNG discovery and Crawl4AI acquisition into RAG context."""

    def __init__(
        self,
        *,
        search_client: WebSearchClient,
        content_client: WebContentClient,
        telemetry: IntegrationTelemetry | None = None,
    ) -> None:
        self._search_client = search_client
        self._content_client = content_client
        self._telemetry = telemetry

    async def retrieve(
        self,
        request: WebRetrievalRequest,
    ) -> tuple[RagRetrievedContext, ...]:
        return await record_provider_call(
            self._telemetry,
            "searxng+crawl4ai",
            "web_fallback_retrieval",
            lambda: self._retrieve(request),
            attributes={
                "rag_request_id": request.request_id,
                "top_k": request.top_k,
                "transient_context": True,
                "untrusted_context": True,
            },
        )

    async def _retrieve(
        self,
        request: WebRetrievalRequest,
    ) -> tuple[RagRetrievedContext, ...]:
        candidates = await self._search_client.search(
            query=request.query,
            limit=request.top_k,
        )
        if not candidates:
            return ()
        documents = await self._content_client.crawl(candidates)
        if not documents:
            return ()

        candidate_by_url = {candidate.url: candidate for candidate in candidates}
        contexts: list[RagRetrievedContext] = []
        seen_urls: set[str] = set()
        for document in documents:
            if document.url in seen_urls:
                continue
            seen_urls.add(document.url)
            context = _document_to_context(
                document,
                candidate=candidate_by_url.get(document.url),
                rank=len(contexts),
            )
            if context is not None:
                contexts.append(context)
            if len(contexts) >= request.top_k:
                break
        return tuple(contexts)


def _document_to_context(
    document: CrawledWebDocument,
    *,
    candidate: WebSearchCandidate | None,
    rank: int,
) -> RagRetrievedContext | None:
    sanitation = sanitize_untrusted_text(document.markdown)
    sanitized = sanitation.text
    if not sanitized:
        return None
    digest = sha256(document.url.encode("utf-8")).hexdigest()
    metadata: dict[str, JsonValue] = {
        "url": document.url,
        "content_hash": document.content_hash,
        "fetched_at": document.fetched_at.isoformat(),
        "transient": True,
        "untrusted": True,
        "provider": "searxng+crawl4ai",
        "search_provider": "searxng",
        "crawl_provider": "crawl4ai",
        "injection_detected": sanitation.injection_detected,
        "security_injection_detected": sanitation.injection_detected,
        "security_executable_markup_detected": sanitation.executable_markup_detected,
        "security_signals": list(sanitation.signals),
    }
    return RagRetrievedContext(
        context_id=f"web:{digest}",
        text=sanitized,
        source=RagSource(
            source_table="external_web",
            source_id=document.url,
            source_type="web_fallback",
            document_id=f"web_document:{digest}",
            title=document.title,
            metadata=metadata,
        ),
        score=candidate.score
        if candidate is not None and candidate.score is not None
        else 1.0,
        rank=rank,
        retrieval_route="web_fallback",
        metadata=metadata,
    )


def sanitize_web_content(content: str) -> tuple[str, bool]:
    """Apply the canonical untrusted-context sanitizer at the web boundary."""

    result = sanitize_untrusted_text(content)
    return result.text, result.injection_detected
