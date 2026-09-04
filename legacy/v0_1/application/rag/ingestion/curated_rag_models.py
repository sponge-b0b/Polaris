from __future__ import annotations

from dataclasses import dataclass

from config.settings import DEFAULT_RAG_HYBRID_EMBEDDING_MODEL
from core.storage.persistence.agent_signals import AgentSignalRecord
from core.storage.persistence.backtesting import (
    BacktestArtifactRecord,
    BacktestMetricRecord,
    BacktestPortfolioSnapshotRecord,
    BacktestRunRecord,
    BacktestStepRecord,
)
from core.storage.persistence.macro import MacroRegimeSnapshotRecord
from core.storage.persistence.market import (
    MarketBreadthSnapshotRecord,
    MarketContextSnapshotRecord,
    TechnicalAnalysisSnapshotRecord,
)
from core.storage.persistence.news import NewsAnalysisSnapshotRecord
from core.storage.persistence.portfolio import (
    PortfolioAllocationSnapshotRecord,
    PortfolioRiskSnapshotRecord,
)
from core.storage.persistence.recommendations import (
    RecommendationRationaleRecord,
    RecommendationRecord,
)
from core.storage.persistence.reports import ReportRecord
from core.storage.persistence.sentiment import SentimentSnapshotRecord
from core.storage.persistence.strategy import (
    StrategyHypothesisRecord,
    StrategyPersistenceBundle,
)

type CuratedRagSource = (
    ReportRecord
    | AgentSignalRecord
    | RecommendationRecord
    | RecommendationRationaleRecord
    | MacroRegimeSnapshotRecord
    | MarketContextSnapshotRecord
    | TechnicalAnalysisSnapshotRecord
    | MarketBreadthSnapshotRecord
    | PortfolioRiskSnapshotRecord
    | PortfolioAllocationSnapshotRecord
    | NewsAnalysisSnapshotRecord
    | SentimentSnapshotRecord
    | BacktestRunRecord
    | BacktestStepRecord
    | BacktestPortfolioSnapshotRecord
    | BacktestMetricRecord
    | BacktestArtifactRecord
    | StrategyHypothesisRecord
    | StrategyPersistenceBundle
)


@dataclass(
    frozen=True,
    slots=True,
)
class CuratedRagBuildOptions:
    """
    Options for building canonical RAG source records.

    This builder creates PostgreSQL source records and optional queued
    embedding job records. It never writes to a vector store directly.
    """

    max_chunk_characters: int = 4000
    queue_embedding_jobs: bool = False
    target_store: str = "qdrant"
    embedding_model: str = DEFAULT_RAG_HYBRID_EMBEDDING_MODEL
    require_source_eligibility: bool = False

    def __post_init__(
        self,
    ) -> None:
        if self.max_chunk_characters <= 0:
            raise ValueError("max_chunk_characters must be positive.")
        _require_non_empty(
            self.target_store,
            "target_store",
        )
        _require_non_empty(
            self.embedding_model,
            "embedding_model",
        )


class CuratedRagSourceNotEligibleError(ValueError):
    """Raised when optional curated RAG eligibility gating rejects a source."""


def _require_non_empty(
    value: str | None,
    field_name: str,
) -> None:
    if value is None or not value.strip():
        raise ValueError(f"{field_name} cannot be empty.")
