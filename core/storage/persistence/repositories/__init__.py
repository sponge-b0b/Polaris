from __future__ import annotations

from core.storage.persistence.repositories.postgres_backtest_persistence_repository import (
    PostgresBacktestPersistenceRepository,
)
from core.storage.persistence.repositories.postgres_audit_persistence_repository import (
    PostgresPersistenceAuditEventRepository,
)
from core.storage.persistence.repositories.postgres_attribution_persistence_repository import (
    PostgresAttributionPersistenceRepository,
)
from core.storage.persistence.repositories.postgres_agent_intelligence_persistence_repository import (
    PostgresAgentIntelligencePersistenceRepository,
)
from core.storage.persistence.repositories.postgres_macro_persistence_repository import (
    PostgresMacroPersistenceRepository,
)
from core.storage.persistence.repositories.postgres_news_persistence_repository import (
    PostgresNewsPersistenceRepository,
)
from core.storage.persistence.repositories.postgres_sentiment_persistence_repository import (
    PostgresSentimentPersistenceRepository,
)
from core.storage.persistence.portfolio.portfolio_state_repository import (
    PortfolioStateRepository,
)
from core.storage.persistence.repositories.postgres_market_persistence_repository import (
    PostgresMarketPersistenceRepository,
)
from core.storage.persistence.repositories.postgres_completed_run_repository import (
    PostgresCompletedRunRepository,
)
from core.storage.persistence.repositories.postgres_lineage_persistence_repository import (
    PostgresPersistenceLineageLinkRepository,
)
from core.storage.persistence.repositories.postgres_agent_signal_persistence_repository import (
    PostgresAgentSignalPersistenceRepository,
)
from core.storage.persistence.repositories.postgres_portfolio_state_repository import (
    PostgresPortfolioStateRepository,
)
from core.storage.persistence.repositories.postgres_portfolio_expansion_persistence_repository import (
    PostgresPortfolioExpansionPersistenceRepository,
)
from core.storage.persistence.repositories.postgres_recommendation_persistence_repository import (
    PostgresRecommendationPersistenceRepository,
)
from core.storage.persistence.repositories.postgres_rag_persistence_repository import (
    PostgresRagPersistenceRepository,
)
from core.storage.persistence.repositories.postgres_report_persistence_repository import (
    PostgresReportPersistenceRepository,
)
from core.storage.persistence.repositories.postgres_runtime_persistence_repository import (
    PostgresRuntimePersistenceRepository,
)
from core.storage.persistence.repositories.postgres_telemetry_persistence_repository import (
    PostgresTelemetryPersistenceRepository,
)
from core.storage.persistence.repositories.postgres_workflow_output_projection_job_repository import (
    PostgresWorkflowOutputProjectionJobRepository,
)

__all__ = [
    "PortfolioStateRepository",
    "PostgresAgentIntelligencePersistenceRepository",
    "PostgresAgentSignalPersistenceRepository",
    "PostgresAttributionPersistenceRepository",
    "PostgresBacktestPersistenceRepository",
    "PostgresCompletedRunRepository",
    "PostgresMacroPersistenceRepository",
    "PostgresMarketPersistenceRepository",
    "PostgresNewsPersistenceRepository",
    "PostgresPersistenceAuditEventRepository",
    "PostgresPersistenceLineageLinkRepository",
    "PostgresPortfolioExpansionPersistenceRepository",
    "PostgresPortfolioStateRepository",
    "PostgresRagPersistenceRepository",
    "PostgresRecommendationPersistenceRepository",
    "PostgresReportPersistenceRepository",
    "PostgresRuntimePersistenceRepository",
    "PostgresSentimentPersistenceRepository",
    "PostgresTelemetryPersistenceRepository",
    "PostgresWorkflowOutputProjectionJobRepository",
]
