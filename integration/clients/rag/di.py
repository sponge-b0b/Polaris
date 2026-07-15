from __future__ import annotations

from collections.abc import AsyncIterator

from dishka import Provider
from dishka import Scope
from dishka import provide

from config.rag_model_config import RagModelConfig
from config.settings import Settings
from integration.clients.rag.bge_m3_embedding_client import BgeM3EmbeddingClient
from integration.clients.rag.bge_reranker_client import BgeRerankerClient
from integration.clients.rag.crawl4ai_content_client import Crawl4AiContentClient
from integration.clients.rag.crawl4ai_content_client import Crawl4AiContentClientConfig
from integration.clients.rag.searxng_search_client import SearxngSearchClient
from integration.clients.rag.neo4j_rag_client import Neo4jRagClient
from integration.clients.rag.qdrant_rag_client import QdrantRagClient


class RagClientsDIProvider(Provider):
    """Application-scoped vendor clients used by the RAG pipeline."""

    scope = Scope.APP

    @provide
    def provide_rag_model_config(
        self,
        settings: Settings,
    ) -> RagModelConfig:
        return RagModelConfig.from_settings(settings)

    @provide
    def provide_embedding_client(
        self,
        model_config: RagModelConfig,
    ) -> BgeM3EmbeddingClient:
        return BgeM3EmbeddingClient(
            model_name=model_config.hybrid_embedding_model,
        )

    @provide
    def provide_reranker_client(
        self,
        model_config: RagModelConfig,
    ) -> BgeRerankerClient:
        return BgeRerankerClient(
            endpoint=model_config.reranker_endpoint,
        )

    @provide
    async def provide_qdrant_client(
        self,
        settings: Settings,
    ) -> AsyncIterator[QdrantRagClient]:
        client = QdrantRagClient(
            settings=settings,
        )
        try:
            yield client
        finally:
            await client.close()

    @provide
    async def provide_neo4j_client(
        self,
        settings: Settings,
    ) -> AsyncIterator[Neo4jRagClient]:
        client = Neo4jRagClient(
            settings=settings,
        )
        try:
            yield client
        finally:
            await client.close()

    @provide
    def provide_searxng_search_client(
        self,
        settings: Settings,
    ) -> SearxngSearchClient:
        return SearxngSearchClient(
            base_url=settings.SEARXNG_BASE_URL,
            timeout_seconds=settings.SEARXNG_TIMEOUT_SECONDS,
            safe_search=settings.SEARXNG_SAFE_SEARCH,
            language=settings.SEARXNG_LANGUAGE,
            categories=settings.SEARXNG_CATEGORIES,
        )

    @provide
    def provide_crawl4ai_content_client(
        self,
        settings: Settings,
    ) -> Crawl4AiContentClient:
        return Crawl4AiContentClient(
            config=Crawl4AiContentClientConfig(
                timeout_seconds=settings.CRAWL4AI_TIMEOUT_SECONDS,
                headless=settings.CRAWL4AI_HEADLESS,
                cache_enabled=settings.CRAWL4AI_CACHE_ENABLED,
                max_concurrency=settings.CRAWL4AI_MAX_CONCURRENCY,
                user_agent=settings.CRAWL4AI_USER_AGENT,
            ),
        )
