from __future__ import annotations

from dishka import Provider
from dishka import Scope
from dishka import provide

from config.rag_model_config import RagModelConfig
from config.settings import Settings
from core.llm.ollama_client import OllamaClient
from core.telemetry.emitters.integration_telemetry import IntegrationTelemetry
from integration.clients.rag.bge_m3_embedding_client import BgeM3EmbeddingClient
from integration.clients.rag.bge_reranker_client import BgeRerankerClient
from integration.clients.rag.firecrawl_web_client import FirecrawlWebClient
from integration.clients.rag.neo4j_rag_client import Neo4jRagClient
from integration.clients.rag.qdrant_rag_client import QdrantRagClient
from integration.providers.rag.bge_m3_embedding_provider import BgeM3EmbeddingProvider
from integration.providers.rag.bge_reranking_provider import BgeRerankingProvider
from integration.providers.rag.firecrawl_web_retrieval_provider import (
    FirecrawlWebRetrievalProvider,
)
from integration.providers.rag.neo4j_graph_projection_provider import (
    Neo4jGraphProjectionProvider,
)
from integration.providers.llm_structured_output import (
    InstructorStructuredOutputProvider,
)
from integration.providers.llm_structured_output import StructuredOutputRetryPolicy
from integration.providers.rag.structured_answer_generation_provider import (
    StructuredRagAnswerGenerationProvider,
)
from integration.providers.rag.structured_answer_generation_provider import (
    StructuredRagAnswerGenerationProviderConfig,
)
from integration.providers.rag.ollama_quality_evaluation_provider import (
    OllamaRagQualityModelProvider,
)
from integration.providers.rag.ollama_query_routing_provider import (
    OllamaRagQueryModelProvider,
)
from integration.providers.rag.qdrant_vector_index_provider import (
    QdrantVectorIndexProvider,
)


class RagProvidersDIProvider(Provider):
    """Application-scoped platform providers for RAG infrastructure."""

    scope = Scope.APP

    @provide
    def provide_embedding_provider(
        self,
        client: BgeM3EmbeddingClient,
        telemetry: IntegrationTelemetry,
    ) -> BgeM3EmbeddingProvider:
        return BgeM3EmbeddingProvider(
            client,
            telemetry=telemetry,
        )

    @provide
    def provide_reranking_provider(
        self,
        client: BgeRerankerClient,
        telemetry: IntegrationTelemetry,
    ) -> BgeRerankingProvider:
        return BgeRerankingProvider(
            client,
            telemetry=telemetry,
        )

    @provide
    def provide_vector_index_provider(
        self,
        client: QdrantRagClient,
        telemetry: IntegrationTelemetry,
    ) -> QdrantVectorIndexProvider:
        return QdrantVectorIndexProvider(
            client,
            telemetry=telemetry,
        )

    @provide
    def provide_graph_projection_provider(
        self,
        client: Neo4jRagClient,
        telemetry: IntegrationTelemetry,
    ) -> Neo4jGraphProjectionProvider:
        return Neo4jGraphProjectionProvider(
            client,
            telemetry=telemetry,
        )

    @provide
    def provide_query_model_provider(
        self,
        client: OllamaClient,
        model_config: RagModelConfig,
        telemetry: IntegrationTelemetry,
    ) -> OllamaRagQueryModelProvider:
        return OllamaRagQueryModelProvider(
            client,
            model_config.query_routing,
            telemetry=telemetry,
        )

    @provide
    def provide_quality_model_provider(
        self,
        client: OllamaClient,
        model_config: RagModelConfig,
        telemetry: IntegrationTelemetry,
    ) -> OllamaRagQualityModelProvider:
        return OllamaRagQualityModelProvider(
            client,
            model_config.quality_evaluation,
            telemetry=telemetry,
        )

    @provide
    def provide_structured_output_provider(
        self,
        settings: Settings,
        telemetry: IntegrationTelemetry,
    ) -> InstructorStructuredOutputProvider:
        return InstructorStructuredOutputProvider.from_settings(
            settings,
            telemetry=telemetry,
        )

    @provide
    def provide_answer_generation_provider(
        self,
        structured_output_provider: InstructorStructuredOutputProvider,
        settings: Settings,
    ) -> StructuredRagAnswerGenerationProvider:
        return StructuredRagAnswerGenerationProvider(
            structured_output_provider=structured_output_provider,
            config=StructuredRagAnswerGenerationProviderConfig(
                model=settings.STRUCTURED_OUTPUT_MODEL,
                provider_name=settings.STRUCTURED_OUTPUT_PROVIDER,
                retry_policy=StructuredOutputRetryPolicy(
                    max_retries=settings.STRUCTURED_OUTPUT_MAX_RETRIES,
                    timeout_seconds=settings.STRUCTURED_OUTPUT_TIMEOUT_SECONDS,
                ),
            ),
        )

    @provide
    def provide_web_retrieval_provider(
        self,
        client: FirecrawlWebClient,
        telemetry: IntegrationTelemetry,
    ) -> FirecrawlWebRetrievalProvider:
        return FirecrawlWebRetrievalProvider(
            client,
            telemetry=telemetry,
        )
