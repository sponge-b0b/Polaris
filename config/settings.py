from typing import ClassVar
from typing import Optional

from pydantic import AliasChoices
from pydantic import Field
from pydantic import field_validator
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
DEFAULT_LANGFUSE_ENVIRONMENT = "development"
DEFAULT_LANGFUSE_SAMPLE_RATE = 1.0
DEFAULT_LANGFUSE_REDACTION_MODE = "strict"
DEFAULT_LANGFUSE_MAX_PAYLOAD_CHARACTERS = 8_000
DEFAULT_LANGFUSE_MAX_METADATA_VALUE_CHARACTERS = 512
DEFAULT_LANGFUSE_RETENTION_DAYS = 90
DEFAULT_DEEPEVAL_DEFAULT_THRESHOLD = 0.7
DEFAULT_DEEPEVAL_MAX_CONCURRENCY = 4
DEFAULT_DEEPEVAL_TIMEOUT_SECONDS = 60.0
DEFAULT_STRUCTURED_OUTPUT_PROVIDER = "instructor"
DEFAULT_STRUCTURED_OUTPUT_MODEL = DEFAULT_RAG_SYNTHESIS_MODEL
DEFAULT_STRUCTURED_OUTPUT_MAX_RETRIES = 2
DEFAULT_STRUCTURED_OUTPUT_TIMEOUT_SECONDS = 60.0
DEFAULT_DSPY_OPTIMIZATION_MODEL = DEFAULT_RAG_SYNTHESIS_MODEL
DEFAULT_DSPY_MAX_TRAINSET_CASES = 100
DEFAULT_DSPY_ARTIFACT_RETENTION_DAYS = 90
STRUCTURED_OUTPUT_PROVIDERS = frozenset({"instructor"})
LANGFUSE_REDACTION_MODES = frozenset({"strict", "metadata_only", "permissive"})
PRODUCTION_ENVIRONMENTS = frozenset({"prod", "production"})


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
    # POLARIS DATABASE
    # ============================================================

    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "polaris"
    POSTGRES_USER: str = "polaris"
    POSTGRES_PASSWORD: Optional[str] = None

    # ============================================================
    # LANGFUSE DATABASE
    # ============================================================

    LANGFUSE_POSTGRES_DB: str = "langfuse"
    LANGFUSE_POSTGRES_USER: str = "langfuse"
    LANGFUSE_POSTGRES_PASSWORD: Optional[str] = None

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
    # STRUCTURED LLM OUTPUT / INSTRUCTOR
    # ============================================================

    STRUCTURED_OUTPUT_PROVIDER: str = Field(
        default=DEFAULT_STRUCTURED_OUTPUT_PROVIDER,
        validation_alias=AliasChoices(
            "POLARIS_STRUCTURED_OUTPUT_PROVIDER",
            "STRUCTURED_OUTPUT_PROVIDER",
        ),
    )
    STRUCTURED_OUTPUT_MODEL: str = Field(
        default=DEFAULT_STRUCTURED_OUTPUT_MODEL,
        validation_alias=AliasChoices(
            "POLARIS_STRUCTURED_OUTPUT_MODEL",
            "STRUCTURED_OUTPUT_MODEL",
        ),
    )
    STRUCTURED_OUTPUT_MAX_RETRIES: int = Field(
        default=DEFAULT_STRUCTURED_OUTPUT_MAX_RETRIES,
        ge=0,
        validation_alias=AliasChoices(
            "POLARIS_STRUCTURED_OUTPUT_MAX_RETRIES",
            "STRUCTURED_OUTPUT_MAX_RETRIES",
        ),
    )
    STRUCTURED_OUTPUT_TIMEOUT_SECONDS: float = Field(
        default=DEFAULT_STRUCTURED_OUTPUT_TIMEOUT_SECONDS,
        gt=0.0,
        validation_alias=AliasChoices(
            "POLARIS_STRUCTURED_OUTPUT_TIMEOUT_SECONDS",
            "STRUCTURED_OUTPUT_TIMEOUT_SECONDS",
        ),
    )

    # ============================================================
    # DSPY AI OPTIMIZATION
    # ============================================================

    DSPY_ENABLED: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "POLARIS_DSPY_ENABLED",
            "DSPY_ENABLED",
        ),
    )
    DSPY_OPTIMIZATION_MODEL: str = Field(
        default=DEFAULT_DSPY_OPTIMIZATION_MODEL,
        validation_alias=AliasChoices(
            "POLARIS_DSPY_OPTIMIZATION_MODEL",
            "DSPY_OPTIMIZATION_MODEL",
        ),
    )
    DSPY_MAX_TRAINSET_CASES: int = Field(
        default=DEFAULT_DSPY_MAX_TRAINSET_CASES,
        gt=0,
        validation_alias=AliasChoices(
            "POLARIS_DSPY_MAX_TRAINSET_CASES",
            "DSPY_MAX_TRAINSET_CASES",
        ),
    )
    DSPY_ARTIFACT_RETENTION_DAYS: int = Field(
        default=DEFAULT_DSPY_ARTIFACT_RETENTION_DAYS,
        gt=0,
        validation_alias=AliasChoices(
            "POLARIS_DSPY_ARTIFACT_RETENTION_DAYS",
            "DSPY_ARTIFACT_RETENTION_DAYS",
        ),
    )

    # ============================================================
    # AI OBSERVABILITY / LANGFUSE
    # ============================================================

    LANGFUSE_HOST: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("POLARIS_LANGFUSE_HOST", "LANGFUSE_HOST"),
    )
    LANGFUSE_PUBLIC_KEY: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices(
            "POLARIS_LANGFUSE_PUBLIC_KEY",
            "LANGFUSE_PUBLIC_KEY",
        ),
    )
    LANGFUSE_SECRET_KEY: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices(
            "POLARIS_LANGFUSE_SECRET_KEY",
            "LANGFUSE_SECRET_KEY",
        ),
    )
    LANGFUSE_ENVIRONMENT: str = Field(
        default=DEFAULT_LANGFUSE_ENVIRONMENT,
        validation_alias=AliasChoices(
            "POLARIS_LANGFUSE_ENVIRONMENT",
            "LANGFUSE_ENVIRONMENT",
        ),
    )
    LANGFUSE_RELEASE: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices(
            "POLARIS_LANGFUSE_RELEASE",
            "LANGFUSE_RELEASE",
        ),
    )
    LANGFUSE_SAMPLE_RATE: float = Field(
        default=DEFAULT_LANGFUSE_SAMPLE_RATE,
        ge=0.0,
        le=1.0,
        validation_alias=AliasChoices(
            "POLARIS_LANGFUSE_SAMPLE_RATE",
            "LANGFUSE_SAMPLE_RATE",
        ),
    )
    LANGFUSE_CAPTURE_PROMPTS: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "POLARIS_LANGFUSE_CAPTURE_PROMPTS",
            "LANGFUSE_CAPTURE_PROMPTS",
        ),
    )
    LANGFUSE_CAPTURE_RESPONSES: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "POLARIS_LANGFUSE_CAPTURE_RESPONSES",
            "LANGFUSE_CAPTURE_RESPONSES",
        ),
    )
    LANGFUSE_CAPTURE_CONTEXTS: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "POLARIS_LANGFUSE_CAPTURE_CONTEXTS",
            "LANGFUSE_CAPTURE_CONTEXTS",
        ),
    )
    LANGFUSE_CAPTURE_USER_INPUT: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "POLARIS_LANGFUSE_CAPTURE_USER_INPUT",
            "LANGFUSE_CAPTURE_USER_INPUT",
        ),
    )
    LANGFUSE_REDACTION_MODE: str = Field(
        default=DEFAULT_LANGFUSE_REDACTION_MODE,
        validation_alias=AliasChoices(
            "POLARIS_LANGFUSE_REDACTION_MODE",
            "LANGFUSE_REDACTION_MODE",
        ),
    )

    LANGFUSE_MAX_PAYLOAD_CHARACTERS: int = Field(
        default=DEFAULT_LANGFUSE_MAX_PAYLOAD_CHARACTERS,
        gt=0,
        validation_alias=AliasChoices(
            "POLARIS_LANGFUSE_MAX_PAYLOAD_CHARACTERS",
            "LANGFUSE_MAX_PAYLOAD_CHARACTERS",
        ),
    )
    LANGFUSE_MAX_METADATA_VALUE_CHARACTERS: int = Field(
        default=DEFAULT_LANGFUSE_MAX_METADATA_VALUE_CHARACTERS,
        gt=0,
        validation_alias=AliasChoices(
            "POLARIS_LANGFUSE_MAX_METADATA_VALUE_CHARACTERS",
            "LANGFUSE_MAX_METADATA_VALUE_CHARACTERS",
        ),
    )
    LANGFUSE_RETENTION_DAYS: int = Field(
        default=DEFAULT_LANGFUSE_RETENTION_DAYS,
        gt=0,
        validation_alias=AliasChoices(
            "POLARIS_LANGFUSE_RETENTION_DAYS",
            "LANGFUSE_RETENTION_DAYS",
        ),
    )
    LANGFUSE_ALLOW_CLOUD_HOST: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "POLARIS_LANGFUSE_ALLOW_CLOUD_HOST",
            "LANGFUSE_ALLOW_CLOUD_HOST",
        ),
    )

    # ============================================================
    # LLM EVALUATION / DEEPEVAL
    # ============================================================

    DEEPEVAL_ENABLED: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "POLARIS_DEEPEVAL_ENABLED",
            "DEEPEVAL_ENABLED",
        ),
    )
    DEEPEVAL_JUDGE_PROVIDER: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices(
            "POLARIS_DEEPEVAL_JUDGE_PROVIDER",
            "DEEPEVAL_JUDGE_PROVIDER",
        ),
    )
    DEEPEVAL_JUDGE_MODEL: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices(
            "POLARIS_DEEPEVAL_JUDGE_MODEL",
            "DEEPEVAL_JUDGE_MODEL",
        ),
    )
    DEEPEVAL_OLLAMA_BASE_URL: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices(
            "POLARIS_DEEPEVAL_OLLAMA_BASE_URL",
            "DEEPEVAL_OLLAMA_BASE_URL",
        ),
    )
    DEEPEVAL_STRICT_MODE: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "POLARIS_DEEPEVAL_STRICT_MODE",
            "DEEPEVAL_STRICT_MODE",
        ),
    )
    DEEPEVAL_TELEMETRY_OPT_OUT: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "POLARIS_DEEPEVAL_TELEMETRY_OPT_OUT",
            "DEEPEVAL_TELEMETRY_OPT_OUT",
        ),
    )
    DEEPEVAL_DEFAULT_THRESHOLD: float = Field(
        default=DEFAULT_DEEPEVAL_DEFAULT_THRESHOLD,
        ge=0.0,
        le=1.0,
        validation_alias=AliasChoices(
            "POLARIS_DEEPEVAL_DEFAULT_THRESHOLD",
            "DEEPEVAL_DEFAULT_THRESHOLD",
        ),
    )
    DEEPEVAL_MAX_CONCURRENCY: int = Field(
        default=DEFAULT_DEEPEVAL_MAX_CONCURRENCY,
        gt=0,
        validation_alias=AliasChoices(
            "POLARIS_DEEPEVAL_MAX_CONCURRENCY",
            "DEEPEVAL_MAX_CONCURRENCY",
        ),
    )
    DEEPEVAL_TIMEOUT_SECONDS: float = Field(
        default=DEFAULT_DEEPEVAL_TIMEOUT_SECONDS,
        gt=0.0,
        validation_alias=AliasChoices(
            "POLARIS_DEEPEVAL_TIMEOUT_SECONDS",
            "DEEPEVAL_TIMEOUT_SECONDS",
        ),
    )

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
        populate_by_name=True,
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

    @field_validator(
        "DEEPEVAL_JUDGE_PROVIDER",
        "DEEPEVAL_JUDGE_MODEL",
        "DEEPEVAL_OLLAMA_BASE_URL",
        mode="before",
    )
    @classmethod
    def _normalize_optional_non_empty_string(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value

    @field_validator("STRUCTURED_OUTPUT_PROVIDER")
    @classmethod
    def _validate_structured_output_provider(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in STRUCTURED_OUTPUT_PROVIDERS:
            allowed = ", ".join(sorted(STRUCTURED_OUTPUT_PROVIDERS))
            raise ValueError(f"STRUCTURED_OUTPUT_PROVIDER must be one of: {allowed}.")
        return normalized

    @field_validator("STRUCTURED_OUTPUT_MODEL", "DSPY_OPTIMIZATION_MODEL")
    @classmethod
    def _validate_non_empty_ai_model_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("AI model names cannot be empty.")
        return stripped

    @field_validator("LANGFUSE_REDACTION_MODE")
    @classmethod
    def _validate_langfuse_redaction_mode(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in LANGFUSE_REDACTION_MODES:
            allowed = ", ".join(sorted(LANGFUSE_REDACTION_MODES))
            raise ValueError(f"LANGFUSE_REDACTION_MODE must be one of: {allowed}.")
        return normalized

    def validate_deepeval_evaluation(
        self,
        *,
        require_configured: bool | None = None,
    ) -> None:
        """Validate DeepEval LLM-evaluation bootstrap configuration."""

        required = require_configured
        if required is None:
            required = self.DEEPEVAL_STRICT_MODE

        if not required:
            return

        missing = []
        if not self.DEEPEVAL_ENABLED:
            missing.append("POLARIS_DEEPEVAL_ENABLED")
        if not self.DEEPEVAL_JUDGE_PROVIDER:
            missing.append("POLARIS_DEEPEVAL_JUDGE_PROVIDER")
        if not self.DEEPEVAL_JUDGE_MODEL:
            missing.append("POLARIS_DEEPEVAL_JUDGE_MODEL")

        if missing:
            joined = ", ".join(missing)
            raise ValueError(
                f"DeepEval LLM-evaluation configuration is required; missing: {joined}."
            )

    def validate_langfuse_observability(
        self,
        *,
        require_configured: bool | None = None,
    ) -> None:
        """Validate Langfuse AI-observability bootstrap configuration."""

        if self.LANGFUSE_HOST is not None and not self.LANGFUSE_HOST.startswith(
            ("http://", "https://")
        ):
            raise ValueError("POLARIS_LANGFUSE_HOST must be an http(s) URL.")

        if (
            self.LANGFUSE_HOST is not None
            and "cloud.langfuse.com" in self.LANGFUSE_HOST.lower()
            and not self.LANGFUSE_ALLOW_CLOUD_HOST
        ):
            raise ValueError(
                "Langfuse Cloud requires explicit approval; set "
                "POLARIS_LANGFUSE_ALLOW_CLOUD_HOST=true only after governance approval."
            )

        required = require_configured
        if required is None:
            required = self.ENVIRONMENT.strip().lower() in PRODUCTION_ENVIRONMENTS

        if not required:
            return

        missing = []
        if not self.LANGFUSE_HOST:
            missing.append("POLARIS_LANGFUSE_HOST")
        if not self.LANGFUSE_PUBLIC_KEY:
            missing.append("POLARIS_LANGFUSE_PUBLIC_KEY")
        if not self.LANGFUSE_SECRET_KEY:
            missing.append("POLARIS_LANGFUSE_SECRET_KEY")

        if missing:
            joined = ", ".join(missing)
            raise ValueError(
                "Langfuse AI-observability configuration is required; "
                f"missing: {joined}."
            )
