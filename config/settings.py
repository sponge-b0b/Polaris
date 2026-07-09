from typing import ClassVar
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_QDRANT_COLLECTION = "polaris"
DEFAULT_EMBEDDING_MODEL = "bge-m3:567m"
DEFAULT_VECTOR_SIZE = 1024
DEFAULT_RAG_QUERY_REWRITE_MODEL = "qwen2.5:7b"
DEFAULT_RAG_ADAPTIVE_TRIAGE_MODEL = "qwen2.5:7b"
DEFAULT_RAG_ROUTE_SELECTION_MODEL = "qwen3.5:4b"
DEFAULT_RAG_HYDE_MODEL = "qwen3.5:4b"
DEFAULT_RAG_HYBRID_EMBEDDING_MODEL = "BAAI/bge-m3"
DEFAULT_RAG_RERANKER_MODEL = "BAAI/bge-reranker-large"
DEFAULT_RAG_RERANKER_ENDPOINT = "http://localhost:8080/rerank"
DEFAULT_RAG_CRAG_GRADER_MODEL = "qwen3.5:4b"
DEFAULT_RAG_CRAG_QUERY_REWRITE_MODEL = "qwen3.5:4b"
DEFAULT_RAG_SELF_REFLECTION_MODEL = "qwen3.5:4b"
DEFAULT_RAG_SYNTHESIS_MODEL = "qwen3.5:4b"
DEFAULT_RAG_GRAPH_MODEL = "polaris-rag-graph-v1"


class Settings(BaseSettings):
    # ============================================================
    # PROJECT
    # ============================================================

    PROJECT_NAME: str = "Polaris"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # ============================================================
    # API KEYS and CREDENTIALS
    # ============================================================

    ALPACA_API_KEY: Optional[str] = None
    ALPACA_API_SECRET_KEY: Optional[str] = None
    ALPHAVANTAGE_API_KEY: Optional[str] = None
    FINNHUB_API_KEY: Optional[str] = None
    FIRECRAWL_API_KEY: Optional[str] = None
    FIRECRAWL_ENABLED: bool = False
    FIRECRAWL_API_URL: str = "https://api.firecrawl.dev"
    FIRECRAWL_TIMEOUT_SECONDS: float = 30.0
    FMP_API_KEY: Optional[str] = None
    FRED_API_KEY: Optional[str] = None
    MASSIVE_API_KEY: Optional[str] = None
    NEWSAPI_API_KEY: Optional[str] = None
    OLLAMA_API_KEY: Optional[str] = None

    # ============================================================
    # PROVIDERS
    # ============================================================

    # Provider Profile
    LIVE_PROVIDER_PROFILE: ClassVar[str] = "live"
    BACKTEST_SYNTHETIC_PROVIDER_PROFILE: ClassVar[str] = "backtest_synthetic"
    BACKTEST_POSTGRES_PROVIDER_PROFILE: ClassVar[str] = "backtest_postgres"
    PROVIDER_PROFILE: str = LIVE_PROVIDER_PROFILE

    # Macro Provider
    BACKTEST_MACRO_PROVIDER: ClassVar[str] = "backtest_macro_provider"
    LIVE_MACRO_PROVIDER: ClassVar[str] = "live_macro_provider"
    MACRO_PROVIDER: str = LIVE_MACRO_PROVIDER

    # Market Data Provider
    BACKTEST_DATA_PROVIDER: ClassVar[str] = "backtest_data_provider"
    BACKTEST_POSTGRES_DATA_PROVIDER: ClassVar[str] = "backtest_postgres_data_provider"
    LIVE_DATA_PROVIDER: ClassVar[str] = "live_data_provider"
    MARKET_DATA_PROVIDER: str = LIVE_DATA_PROVIDER
    BACKTEST_POSTGRES_MARKET_DATA_SOURCE: Optional[str] = None
    BACKTEST_POSTGRES_SP500_UNIVERSE: str = "sp500"
    BACKTEST_POSTGRES_MISSING_DATA_POLICY: str = "fail_fast"

    # Market Events Provider
    BACKTEST_EVENTS_PROVIDER: ClassVar[str] = "backtest_events_provider"
    LIVE_EVENTS_PROVIDER: ClassVar[str] = "live_events_provider"
    MARKET_EVENTS_PROVIDER: str = LIVE_EVENTS_PROVIDER

    # News Provider
    BACKTEST_NEWS_PROVIDER: ClassVar[str] = "backtest_news_provider"
    LIVE_NEWS_PROVIDER: ClassVar[str] = "live_news_provider"
    NEWS_PROVIDER: str = LIVE_NEWS_PROVIDER

    # Portfolio Provider
    BACKTEST_PORTFOLIO_PROVIDER: ClassVar[str] = "backtest_portfolio_provider"
    LIVE_PORTFOLIO_PROVIDER: ClassVar[str] = "live_portfolio_provider"
    PORTFOLIO_PROVIDER: str = LIVE_PORTFOLIO_PROVIDER

    # Sentiment Provider
    BACKTEST_SENTIMENT_PROVIDER: ClassVar[str] = "backtest_sentiment_provider"
    LIVE_SENTIMENT_PROVIDER: ClassVar[str] = "live_sentiment_provider"
    SENTIMENT_PROVIDER: str = LIVE_SENTIMENT_PROVIDER

    # ============================================================
    # DATABASE
    # ============================================================

    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "polaris"
    POSTGRES_USER: str = "polaris"
    POSTGRES_PASSWORD: Optional[str] = None

    # ============================================================
    # QDRANT
    # ============================================================

    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION: str = DEFAULT_QDRANT_COLLECTION

    # ============================================================
    # NEO4J
    # ============================================================

    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: Optional[str] = None
    NEO4J_PASSWORD: Optional[str] = None
    NEO4J_DATABASE: str = "neo4j"

    # ============================================================
    # OLLAMA
    # ============================================================

    OLLAMA_HOST: str = "http://localhost:11434"

    DEFAULT_MODEL: str = "qwen3.5:4b"  # "qwen3.5:9b"
    EMBEDDING_MODEL: str = DEFAULT_EMBEDDING_MODEL
    RAG_WEB_FALLBACK_MAX_RESULTS: int = 5

    # ============================================================
    # MEMORY / RAG
    # ============================================================

    RAG_QUERY_REWRITE_MODEL: str = DEFAULT_RAG_QUERY_REWRITE_MODEL
    RAG_ADAPTIVE_TRIAGE_MODEL: str = DEFAULT_RAG_ADAPTIVE_TRIAGE_MODEL
    RAG_ROUTE_SELECTION_MODEL: str = DEFAULT_RAG_ROUTE_SELECTION_MODEL
    RAG_HYDE_MODEL: str = DEFAULT_RAG_HYDE_MODEL
    RAG_HYBRID_EMBEDDING_MODEL: str = DEFAULT_RAG_HYBRID_EMBEDDING_MODEL
    RAG_RERANKER_MODEL: str = DEFAULT_RAG_RERANKER_MODEL
    RAG_RERANKER_ENDPOINT: str = DEFAULT_RAG_RERANKER_ENDPOINT
    RAG_CRAG_GRADER_MODEL: str = DEFAULT_RAG_CRAG_GRADER_MODEL
    RAG_CRAG_QUERY_REWRITE_MODEL: str = DEFAULT_RAG_CRAG_QUERY_REWRITE_MODEL
    RAG_SELF_REFLECTION_MODEL: str = DEFAULT_RAG_SELF_REFLECTION_MODEL
    RAG_SYNTHESIS_MODEL: str = DEFAULT_RAG_SYNTHESIS_MODEL
    RAG_GRAPH_MODEL: str = DEFAULT_RAG_GRAPH_MODEL
    RAG_GRAPH_PROJECTION_NAME: str = "polaris_rag"

    VECTOR_SIZE: int = DEFAULT_VECTOR_SIZE
    TOP_K_RESULTS: int = 5

    # ============================================================
    # REPORTS
    # ============================================================

    REPORT_OUTPUT_DIR: str = "storage/reports"

    # ============================================================
    # LOGGING
    # ============================================================

    LOG_LEVEL: str = "INFO"

    # ============================================================
    # Pydantic Settings Config
    # ============================================================

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ============================================================
    # Computed Properties
    # ============================================================

    @property
    def postgres_url(self) -> str:
        if self.POSTGRES_PASSWORD is None:
            raise ValueError("POSTGRES_PASSWORD is required to build postgres_url.")

        return (
            f"postgresql://"
            f"{self.POSTGRES_USER}:"
            f"{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_HOST}:"
            f"{self.POSTGRES_PORT}/"
            f"{self.POSTGRES_DB}"
        )

    @property
    def qdrant_url(self) -> str:
        return f"http://{self.QDRANT_HOST}:{self.QDRANT_PORT}"
