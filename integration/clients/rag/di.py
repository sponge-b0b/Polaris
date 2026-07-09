from __future__ import annotations

from collections.abc import AsyncIterator

from dishka import Provider
from dishka import Scope
from dishka import provide

from config.rag_model_config import RagModelConfig
from config.settings import Settings
from integration.clients.rag.bge_m3_embedding_client import BgeM3EmbeddingClient
from integration.clients.rag.bge_reranker_client import BgeRerankerClient
from integration.clients.rag.firecrawl_web_client import FirecrawlWebClient
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
    def provide_firecrawl_client(
        self,
        settings: Settings,
    ) -> FirecrawlWebClient:
        return FirecrawlWebClient(
            api_key=settings.FIRECRAWL_API_KEY,
            api_url=settings.FIRECRAWL_API_URL,
            timeout_seconds=settings.FIRECRAWL_TIMEOUT_SECONDS,
        )
