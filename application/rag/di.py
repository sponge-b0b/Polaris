from __future__ import annotations

from dishka import Provider
from dishka import Scope
from dishka import provide

from application.rag.ingestion.curated_rag_bundle_persistence import (
    CuratedRagBundlePersister,
)
from application.rag.ingestion.curated_rag_document_builder import (
    CuratedRagDocumentBuilder,
)
from application.rag.ingestion.curated_rag_document_builder import (
    CuratedRagIngestionService,
)
from application.rag.ingestion.curated_rag_document_factory import (
    CuratedRagDocumentFactory,
)
from application.rag.operations.embedding_job_processor import EmbeddingJobProcessor
from application.rag.operations.embedding_job_processor import (
    EmbeddingJobProcessorConfig,
)
from application.rag.generation.answer_generator import RagAnswerGenerator
from application.rag.projections.graph_projection import GraphProjectionJobProcessor
from application.rag.projections.graph_projection import Neo4jGraphRetriever
from application.rag.graphs.rag_service_graph import RagServiceGraph
from application.rag.routing.query_routing_service import RagQueryRoutingService
from application.rag.operations.rag_embedding_operations import (
    RagEmbeddingJobOperationsService,
)
from application.rag.operations.rag_ingestion_operations import (
    RagIngestionOperationsService,
)
from application.rag.contracts.rag_operation_models import RagProjectionConfig
from application.rag.contracts.rag_operation_models import RagProjectionReadinessConfig
from application.rag.operations.rag_projection_operations import (
    RagProjectionOperationsService,
)
from application.rag.ingestion.rag_source_loaders import AgentSignalRagSourceLoader
from application.rag.ingestion.rag_source_loaders import BacktestRagSourceLoader
from application.rag.ingestion.rag_source_loaders import CuratedRagSourceLoaderRegistry
from application.rag.ingestion.rag_source_loaders import MacroRagSourceLoader
from application.rag.ingestion.rag_source_loaders import MarketRagSourceLoader
from application.rag.ingestion.rag_source_loaders import NewsRagSourceLoader
from application.rag.ingestion.rag_source_loaders import PortfolioRagSourceLoader
from application.rag.ingestion.rag_source_loaders import RecommendationRagSourceLoader
from application.rag.ingestion.rag_source_loaders import ReportRagSourceLoader
from application.rag.ingestion.rag_source_loaders import SentimentRagSourceLoader
from application.rag.operations.rag_status_operations import RagStatusOperationsService
from application.rag.quality.rag_quality_service import RagQualityService
from application.rag.retrieval.rag_retriever import RagRetriever
from application.rag.retrieval.rag_retriever import RagRetrieverConfig
from application.rag.security.rag_security import RagSecurityGuard
from application.rag.rag_service import RagService
from application.rag.retrieval.structured_retrieval import MarketStructuredRagRetriever
from application.rag.retrieval.web_fallback_service import RagWebFallbackService
from config.rag_model_config import RagModelConfig
from config.settings import Settings
from core.storage.persistence.rag import RagPersistenceRepository
from core.storage.persistence.repositories.postgres_agent_signal_persistence_repository import (
    PostgresAgentSignalPersistenceRepository,
)
from core.storage.persistence.repositories.postgres_backtest_persistence_repository import (
    PostgresBacktestPersistenceRepository,
)
from core.storage.persistence.repositories.postgres_macro_persistence_repository import (
    PostgresMacroPersistenceRepository,
)
from core.storage.persistence.repositories.postgres_market_persistence_repository import (
    PostgresMarketPersistenceRepository,
)
from core.storage.persistence.repositories.postgres_news_persistence_repository import (
    PostgresNewsPersistenceRepository,
)
from core.storage.persistence.repositories.postgres_portfolio_expansion_persistence_repository import (
    PostgresPortfolioExpansionPersistenceRepository,
)
from core.storage.persistence.repositories.postgres_recommendation_persistence_repository import (
    PostgresRecommendationPersistenceRepository,
)
from core.storage.persistence.repositories.postgres_report_persistence_repository import (
    PostgresReportPersistenceRepository,
)
from core.storage.persistence.repositories.postgres_sentiment_persistence_repository import (
    PostgresSentimentPersistenceRepository,
)
from core.telemetry.emitters.application_rag_telemetry import ApplicationRagTelemetry
from integration.providers.rag.bge_m3_embedding_provider import BgeM3EmbeddingProvider
from integration.providers.rag.bge_reranking_provider import BgeRerankingProvider
from integration.providers.rag.firecrawl_web_retrieval_provider import (
    FirecrawlWebRetrievalProvider,
)
from integration.providers.rag.neo4j_graph_projection_provider import (
    Neo4jGraphProjectionProvider,
)
from integration.providers.rag.ollama_answer_generation_provider import (
    OllamaRagAnswerGenerationProvider,
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


class RagApplicationDIProvider(Provider):
    """Request-scoped composition for canonical RAG application services."""

    scope = Scope.REQUEST

    @provide
    def provide_projection_config(
        self,
        settings: Settings,
        model_config: RagModelConfig,
    ) -> RagProjectionConfig:
        return RagProjectionConfig(
            collection_name=settings.QDRANT_COLLECTION,
            vector_size=settings.VECTOR_SIZE,
            embedding_model=model_config.hybrid_embedding_model,
        )

    @provide
    def provide_curated_document_factory(
        self,
    ) -> CuratedRagDocumentFactory:
        return CuratedRagDocumentFactory()

    @provide
    def provide_curated_document_builder(
        self,
        document_factory: CuratedRagDocumentFactory,
    ) -> CuratedRagDocumentBuilder:
        return CuratedRagDocumentBuilder(document_factory)

    @provide
    def provide_curated_bundle_persister(
        self,
        repository: RagPersistenceRepository,
    ) -> CuratedRagBundlePersister:
        return CuratedRagBundlePersister(repository)

    @provide
    def provide_ingestion_service(
        self,
        repository: RagPersistenceRepository,
        builder: CuratedRagDocumentBuilder,
        bundle_persister: CuratedRagBundlePersister,
        telemetry: ApplicationRagTelemetry,
    ) -> CuratedRagIngestionService:
        return CuratedRagIngestionService(
            repository,
            builder=builder,
            bundle_persister=bundle_persister,
            telemetry=telemetry,
        )

    @provide
    def provide_embedding_job_processor(
        self,
        repository: RagPersistenceRepository,
        embedding_provider: BgeM3EmbeddingProvider,
        vector_provider: QdrantVectorIndexProvider,
        telemetry: ApplicationRagTelemetry,
        settings: Settings,
    ) -> EmbeddingJobProcessor:
        return EmbeddingJobProcessor(
            repository=repository,
            embedding_provider=embedding_provider,
            vector_index_provider=vector_provider,
            collection_lifecycle_provider=vector_provider,
            telemetry=telemetry,
            config=EmbeddingJobProcessorConfig(
                collection_name=settings.QDRANT_COLLECTION,
                vector_size=settings.VECTOR_SIZE,
            ),
        )

    @provide
    def provide_graph_projection_processor(
        self,
        repository: RagPersistenceRepository,
        provider: Neo4jGraphProjectionProvider,
        telemetry: ApplicationRagTelemetry,
        settings: Settings,
    ) -> GraphProjectionJobProcessor:
        return GraphProjectionJobProcessor(
            repository=repository,
            provider=provider,
            telemetry=telemetry,
            graph_model=settings.RAG_GRAPH_MODEL,
        )

    @provide
    def provide_graph_retriever(
        self,
        repository: RagPersistenceRepository,
        provider: Neo4jGraphProjectionProvider,
        telemetry: ApplicationRagTelemetry,
    ) -> Neo4jGraphRetriever:
        return Neo4jGraphRetriever(
            repository=repository,
            provider=provider,
            telemetry=telemetry,
        )

    @provide
    def provide_structured_retriever(
        self,
        repository: PostgresMarketPersistenceRepository,
    ) -> MarketStructuredRagRetriever:
        return MarketStructuredRagRetriever(repository)

    @provide
    def provide_rag_retriever(
        self,
        repository: RagPersistenceRepository,
        embedding_provider: BgeM3EmbeddingProvider,
        vector_provider: QdrantVectorIndexProvider,
        reranking_provider: BgeRerankingProvider,
        structured_retriever: MarketStructuredRagRetriever,
        graph_retriever: Neo4jGraphRetriever,
        telemetry: ApplicationRagTelemetry,
        settings: Settings,
        model_config: RagModelConfig,
    ) -> RagRetriever:
        return RagRetriever(
            repository=repository,
            embedding_provider=embedding_provider,
            vector_index_provider=vector_provider,
            reranking_provider=reranking_provider,
            structured_retriever=structured_retriever,
            graph_retriever=graph_retriever,
            telemetry=telemetry,
            config=RagRetrieverConfig(
                collection_name=settings.QDRANT_COLLECTION,
                embedding_model=model_config.hybrid_embedding_model,
            ),
        )

    @provide
    def provide_query_routing_service(
        self,
        provider: OllamaRagQueryModelProvider,
        telemetry: ApplicationRagTelemetry,
    ) -> RagQueryRoutingService:
        return RagQueryRoutingService(
            provider,
            telemetry=telemetry,
        )

    @provide
    def provide_quality_service(
        self,
        provider: OllamaRagQualityModelProvider,
        telemetry: ApplicationRagTelemetry,
    ) -> RagQualityService:
        return RagQualityService(
            provider,
            telemetry=telemetry,
        )

    @provide
    def provide_answer_generator(
        self,
        provider: OllamaRagAnswerGenerationProvider,
        telemetry: ApplicationRagTelemetry,
    ) -> RagAnswerGenerator:
        return RagAnswerGenerator(
            answer_provider=provider,
            telemetry=telemetry,
        )

    @provide
    def provide_security_guard(
        self,
        telemetry: ApplicationRagTelemetry,
    ) -> RagSecurityGuard:
        return RagSecurityGuard(telemetry)

    @provide
    def provide_rag_service_graph(
        self,
        query_routing_service: RagQueryRoutingService,
        retriever: RagRetriever,
        answer_generator: RagAnswerGenerator,
        quality_service: RagQualityService,
        web_provider: FirecrawlWebRetrievalProvider,
        security_guard: RagSecurityGuard,
        telemetry: ApplicationRagTelemetry,
        settings: Settings,
    ) -> RagServiceGraph:
        web_fallback = (
            RagWebFallbackService(
                web_provider,
                telemetry=telemetry,
                max_results=settings.RAG_WEB_FALLBACK_MAX_RESULTS,
            )
            if settings.FIRECRAWL_ENABLED
            else None
        )
        return RagServiceGraph(
            query_routing_service=query_routing_service,
            retriever=retriever,
            answer_generator=answer_generator,
            context_evaluator=quality_service,
            corrective_query_rewriter=quality_service,
            answer_reflector=quality_service,
            web_fallback_retriever=web_fallback,
            security_guard=security_guard,
            max_loops=1,
        )

    @provide
    def provide_rag_service(
        self,
        pipeline: RagServiceGraph,
        repository: RagPersistenceRepository,
        telemetry: ApplicationRagTelemetry,
    ) -> RagService:
        return RagService(
            pipeline=pipeline,
            repository=repository,
            telemetry=telemetry,
        )

    @provide
    def provide_source_loader_registry(
        self,
        report_repository: PostgresReportPersistenceRepository,
        agent_signal_repository: PostgresAgentSignalPersistenceRepository,
        recommendation_repository: PostgresRecommendationPersistenceRepository,
        macro_repository: PostgresMacroPersistenceRepository,
        market_repository: PostgresMarketPersistenceRepository,
        news_repository: PostgresNewsPersistenceRepository,
        sentiment_repository: PostgresSentimentPersistenceRepository,
        portfolio_repository: PostgresPortfolioExpansionPersistenceRepository,
        backtest_repository: PostgresBacktestPersistenceRepository,
    ) -> CuratedRagSourceLoaderRegistry:
        return CuratedRagSourceLoaderRegistry(
            (
                ReportRagSourceLoader(report_repository),
                AgentSignalRagSourceLoader(agent_signal_repository),
                RecommendationRagSourceLoader(recommendation_repository),
                MacroRagSourceLoader(macro_repository),
                MarketRagSourceLoader(market_repository),
                NewsRagSourceLoader(news_repository),
                SentimentRagSourceLoader(sentiment_repository),
                PortfolioRagSourceLoader(portfolio_repository),
                BacktestRagSourceLoader(backtest_repository),
            )
        )

    @provide
    def provide_rag_ingestion_operations_service(
        self,
        rag_repository: RagPersistenceRepository,
        source_loader_registry: CuratedRagSourceLoaderRegistry,
        ingestion_service: CuratedRagIngestionService,
        graph_projection_processor: GraphProjectionJobProcessor,
        projection_config: RagProjectionConfig,
        telemetry: ApplicationRagTelemetry,
    ) -> RagIngestionOperationsService:
        return RagIngestionOperationsService(
            rag_repository=rag_repository,
            source_loader_registry=source_loader_registry,
            ingestion_service=ingestion_service,
            graph_document_queue=graph_projection_processor,
            projection_config=projection_config,
            telemetry=telemetry,
        )

    @provide
    def provide_rag_embedding_operations_service(
        self,
        rag_repository: RagPersistenceRepository,
        embedding_job_processor: EmbeddingJobProcessor,
        telemetry: ApplicationRagTelemetry,
    ) -> RagEmbeddingJobOperationsService:
        return RagEmbeddingJobOperationsService(
            rag_repository=rag_repository,
            embedding_job_processor=embedding_job_processor,
            telemetry=telemetry,
        )

    @provide
    def provide_rag_projection_operations_service(
        self,
        rag_repository: RagPersistenceRepository,
        graph_projection_processor: GraphProjectionJobProcessor,
        vector_provider: QdrantVectorIndexProvider,
        embedding_job_processor: EmbeddingJobProcessor,
        projection_config: RagProjectionConfig,
        telemetry: ApplicationRagTelemetry,
    ) -> RagProjectionOperationsService:
        return RagProjectionOperationsService(
            rag_repository=rag_repository,
            graph_projection_processor=graph_projection_processor,
            vector_collection_provider=vector_provider,
            embedding_job_processor=embedding_job_processor,
            projection_config=projection_config,
            telemetry=telemetry,
        )

    @provide
    def provide_rag_status_operations_service(
        self,
        rag_repository: RagPersistenceRepository,
        vector_provider: QdrantVectorIndexProvider,
        graph_provider: Neo4jGraphProjectionProvider,
        embedding_provider: BgeM3EmbeddingProvider,
        reranking_provider: BgeRerankingProvider,
        model_config: RagModelConfig,
        settings: Settings,
        telemetry: ApplicationRagTelemetry,
    ) -> RagStatusOperationsService:
        return RagStatusOperationsService(
            rag_repository=rag_repository,
            vector_provider=vector_provider,
            graph_provider=graph_provider,
            embedding_provider=embedding_provider,
            reranking_provider=reranking_provider,
            config=RagProjectionReadinessConfig(
                collection_name=settings.QDRANT_COLLECTION,
                vector_size=settings.VECTOR_SIZE,
                embedding_model=model_config.hybrid_embedding_model,
                reranker_model=model_config.reranker_model,
            ),
            telemetry=telemetry,
        )
