from __future__ import annotations

from hashlib import sha256

from application.rag.contracts.rag_context import RagRetrievedContext
from application.rag.contracts.rag_context import RagSource
from application.rag.security.rag_security import sanitize_untrusted_text
from core.telemetry.emitters.integration_telemetry import IntegrationTelemetry
from integration.clients.rag.firecrawl_web_client import FirecrawlWebSearchClient
from integration.providers.provider_telemetry import record_provider_call
from integration.providers.rag.web_retrieval_provider import WebRetrievalProvider
from integration.providers.rag.web_retrieval_provider import WebRetrievalRequest


class FirecrawlWebRetrievalProvider(WebRetrievalProvider):
    """Normalize Firecrawl search results into transient untrusted RAG context."""

    def __init__(
        self,
        client: FirecrawlWebSearchClient,
        telemetry: IntegrationTelemetry | None = None,
    ) -> None:
        self._client = client
        self._telemetry = telemetry

    async def retrieve(
        self,
        request: WebRetrievalRequest,
    ) -> tuple[RagRetrievedContext, ...]:
        results = await record_provider_call(
            self._telemetry,
            "firecrawl",
            "web_fallback_search",
            lambda: self._client.search(query=request.query, limit=request.top_k),
            attributes={
                "rag_request_id": request.request_id,
                "top_k": request.top_k,
                "transient_context": True,
            },
        )
        contexts: list[RagRetrievedContext] = []
        seen_urls: set[str] = set()
        for result in results:
            if result.url in seen_urls:
                continue
            seen_urls.add(result.url)
            sanitation = sanitize_untrusted_text(result.content)
            sanitized = sanitation.text
            if not sanitized:
                continue
            digest = sha256(result.url.encode("utf-8")).hexdigest()
            contexts.append(
                RagRetrievedContext(
                    context_id=f"web:{digest}",
                    text=sanitized,
                    source=RagSource(
                        source_table="external_web",
                        source_id=result.url,
                        source_type="web_fallback",
                        document_id=f"web_document:{digest}",
                        title=result.title,
                        metadata={
                            "url": result.url,
                            "transient": True,
                            "untrusted": True,
                            "provider": "firecrawl",
                            "injection_detected": sanitation.injection_detected,
                            "security_injection_detected": (
                                sanitation.injection_detected
                            ),
                            "security_executable_markup_detected": (
                                sanitation.executable_markup_detected
                            ),
                            "security_signals": list(sanitation.signals),
                        },
                    ),
                    score=1.0,
                    rank=len(contexts),
                    retrieval_route="web_fallback",
                    metadata={
                        "transient": True,
                        "untrusted": True,
                        "provider": "firecrawl",
                        "injection_detected": sanitation.injection_detected,
                        "security_injection_detected": sanitation.injection_detected,
                        "security_executable_markup_detected": (
                            sanitation.executable_markup_detected
                        ),
                        "security_signals": list(sanitation.signals),
                    },
                )
            )
        return tuple(contexts[: request.top_k])


def sanitize_web_content(content: str) -> tuple[str, bool]:
    """Apply the canonical untrusted-context sanitizer at the web boundary."""

    result = sanitize_untrusted_text(content)
    return result.text, result.injection_detected
