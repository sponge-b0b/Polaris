from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from application.rag.ingestion.curated_rag_models import CuratedRagSource
from core.storage.persistence.agent_signals import AgentSignalPersistenceRepository
from core.storage.persistence.backtesting import BacktestPersistenceRepository
from core.storage.persistence.macro import MacroPersistenceRepository
from core.storage.persistence.market import MarketPersistenceRepository
from core.storage.persistence.news import NewsPersistenceRepository
from core.storage.persistence.portfolio import PortfolioExpansionPersistenceRepository
from core.storage.persistence.rag import RagSourceEligibilityRecord
from core.storage.persistence.recommendations import RecommendationPersistenceRepository
from core.storage.persistence.reports import ReportPersistenceRepository
from core.storage.persistence.sentiment import SentimentPersistenceRepository
from core.storage.persistence.strategy import StrategyPersistenceRepository


class CuratedRagSourceLoader(Protocol):
    @property
    def source_tables(self) -> tuple[str, ...]: ...

    async def load(
        self,
        eligibility: RagSourceEligibilityRecord,
    ) -> CuratedRagSource | None: ...


class CuratedRagSourceLoaderRegistry:
    """Routes eligible PostgreSQL records to their typed source loader."""

    def __init__(self, loaders: Sequence[CuratedRagSourceLoader]) -> None:
        loaders_by_table: dict[str, CuratedRagSourceLoader] = {}
        for loader in loaders:
            for source_table in loader.source_tables:
                if source_table in loaders_by_table:
                    raise ValueError(
                        f"Duplicate curated RAG source loader for '{source_table}'."
                    )
                loaders_by_table[source_table] = loader
        self._loaders_by_table = loaders_by_table

    async def load(
        self,
        eligibility: RagSourceEligibilityRecord,
    ) -> CuratedRagSource | None:
        loader = self._loaders_by_table.get(eligibility.source_table)
        if loader is None:
            return None
        return await loader.load(eligibility)


@dataclass(frozen=True, slots=True)
class ReportRagSourceLoader:
    repository: ReportPersistenceRepository

    @property
    def source_tables(self) -> tuple[str, ...]:
        return ("reports",)

    async def load(
        self,
        eligibility: RagSourceEligibilityRecord,
    ) -> CuratedRagSource | None:
        return await self.repository.get_report(eligibility.source_id)


@dataclass(frozen=True, slots=True)
class AgentSignalRagSourceLoader:
    repository: AgentSignalPersistenceRepository

    @property
    def source_tables(self) -> tuple[str, ...]:
        return ("agent_signals",)

    async def load(
        self,
        eligibility: RagSourceEligibilityRecord,
    ) -> CuratedRagSource | None:
        return await self.repository.get_signal(eligibility.source_id)


@dataclass(frozen=True, slots=True)
class RecommendationRagSourceLoader:
    repository: RecommendationPersistenceRepository

    @property
    def source_tables(self) -> tuple[str, ...]:
        return ("recommendations", "recommendation_rationales")

    async def load(
        self,
        eligibility: RagSourceEligibilityRecord,
    ) -> CuratedRagSource | None:
        if eligibility.source_table == "recommendations":
            return await self.repository.get_recommendation(eligibility.source_id)
        recommendation_id = metadata_str(eligibility, "recommendation_id")
        if recommendation_id is None:
            return None
        return find_by_attribute(
            await self.repository.list_rationales(recommendation_id),
            "rationale_id",
            eligibility.source_id,
        )


@dataclass(frozen=True, slots=True)
class MacroRagSourceLoader:
    repository: MacroPersistenceRepository

    @property
    def source_tables(self) -> tuple[str, ...]:
        return ("macro_regime_snapshots",)

    async def load(
        self,
        eligibility: RagSourceEligibilityRecord,
    ) -> CuratedRagSource | None:
        return find_by_attribute(
            await self.repository.list_regime_snapshots(),
            "regime_snapshot_id",
            eligibility.source_id,
        )


@dataclass(frozen=True, slots=True)
class MarketRagSourceLoader:
    repository: MarketPersistenceRepository

    @property
    def source_tables(self) -> tuple[str, ...]:
        return (
            "technical_analysis_snapshots",
            "market_context_snapshots",
            "market_breadth_snapshots",
        )

    async def load(
        self,
        eligibility: RagSourceEligibilityRecord,
    ) -> CuratedRagSource | None:
        table = eligibility.source_table
        if table == "market_context_snapshots":
            return find_by_attribute(
                await self.repository.list_context_snapshots(
                    universe=metadata_str(eligibility, "universe"),
                    source=metadata_str(eligibility, "source"),
                ),
                "context_snapshot_id",
                eligibility.source_id,
            )
        if table == "technical_analysis_snapshots":
            symbol = metadata_str(eligibility, "symbol")
            if symbol is None:
                return None
            return find_by_attribute(
                await self.repository.list_technical_snapshots(
                    symbol=symbol,
                    source=metadata_str(eligibility, "source"),
                ),
                "technical_snapshot_id",
                eligibility.source_id,
            )
        universe = metadata_str(eligibility, "universe")
        if universe is None:
            return None
        return find_by_attribute(
            await self.repository.list_breadth_snapshots(
                universe=universe,
                source=metadata_str(eligibility, "source"),
            ),
            "breadth_snapshot_id",
            eligibility.source_id,
        )


@dataclass(frozen=True, slots=True)
class NewsRagSourceLoader:
    repository: NewsPersistenceRepository

    @property
    def source_tables(self) -> tuple[str, ...]:
        return ("news_analysis_snapshots",)

    async def load(
        self,
        eligibility: RagSourceEligibilityRecord,
    ) -> CuratedRagSource | None:
        return find_by_attribute(
            await self.repository.list_analysis_snapshots(
                source=metadata_str(eligibility, "source"),
                symbol=first_metadata_str(eligibility, "symbols"),
                theme=first_metadata_str(eligibility, "themes"),
            ),
            "analysis_snapshot_id",
            eligibility.source_id,
        )


@dataclass(frozen=True, slots=True)
class SentimentRagSourceLoader:
    repository: SentimentPersistenceRepository

    @property
    def source_tables(self) -> tuple[str, ...]:
        return ("sentiment_snapshots",)

    async def load(
        self,
        eligibility: RagSourceEligibilityRecord,
    ) -> CuratedRagSource | None:
        return find_by_attribute(
            await self.repository.list_snapshots(
                source=metadata_str(eligibility, "source"),
                symbol=metadata_str(eligibility, "symbol"),
                universe=metadata_str(eligibility, "universe"),
            ),
            "sentiment_snapshot_id",
            eligibility.source_id,
        )


@dataclass(frozen=True, slots=True)
class PortfolioRagSourceLoader:
    repository: PortfolioExpansionPersistenceRepository

    @property
    def source_tables(self) -> tuple[str, ...]:
        return ("portfolio_risk_snapshots", "portfolio_allocation_snapshots")

    async def load(
        self,
        eligibility: RagSourceEligibilityRecord,
    ) -> CuratedRagSource | None:
        account_id = metadata_str(eligibility, "account_id")
        if account_id is None:
            return None
        if eligibility.source_table == "portfolio_risk_snapshots":
            return find_by_attribute(
                await self.repository.list_risk_snapshots(account_id=account_id),
                "risk_snapshot_id",
                eligibility.source_id,
            )
        return find_by_attribute(
            await self.repository.list_allocation_snapshots(account_id=account_id),
            "allocation_snapshot_id",
            eligibility.source_id,
        )


@dataclass(frozen=True, slots=True)
class StrategyRagSourceLoader:
    repository: StrategyPersistenceRepository

    @property
    def source_tables(self) -> tuple[str, ...]:
        return ("strategy_hypotheses", "strategy_synthesis_decisions")

    async def load(
        self,
        eligibility: RagSourceEligibilityRecord,
    ) -> CuratedRagSource | None:
        if eligibility.source_table == "strategy_hypotheses":
            return await self.repository.get_hypothesis(eligibility.source_id)
        return await self.repository.get_decision_bundle(eligibility.source_id)


@dataclass(frozen=True, slots=True)
class BacktestRagSourceLoader:
    repository: BacktestPersistenceRepository

    @property
    def source_tables(self) -> tuple[str, ...]:
        return (
            "backtest_runs",
            "backtest_steps",
            "backtest_portfolio_snapshots",
            "backtest_metrics",
            "backtest_artifacts",
        )

    async def load(
        self,
        eligibility: RagSourceEligibilityRecord,
    ) -> CuratedRagSource | None:
        if eligibility.source_table == "backtest_runs":
            return await self.repository.get_run(eligibility.source_id)
        backtest_run_id = metadata_str(eligibility, "backtest_run_id")
        if backtest_run_id is None:
            return None
        records, attribute = await self._child_records(
            eligibility.source_table,
            backtest_run_id,
        )
        return find_by_attribute(records, attribute, eligibility.source_id)

    async def _child_records(
        self,
        source_table: str,
        backtest_run_id: str,
    ) -> tuple[Sequence[CuratedRagSource], str]:
        if source_table == "backtest_steps":
            return await self.repository.list_steps(backtest_run_id), "step_id"
        if source_table == "backtest_portfolio_snapshots":
            return (
                await self.repository.list_portfolio_snapshots(backtest_run_id),
                "snapshot_id",
            )
        if source_table == "backtest_metrics":
            return await self.repository.list_metrics(backtest_run_id), "metric_id"
        return await self.repository.list_artifacts(backtest_run_id), "artifact_id"


def metadata_str(
    eligibility: RagSourceEligibilityRecord,
    key: str,
) -> str | None:
    value = eligibility.metadata.get(key)
    if isinstance(value, str) and value.strip():
        return value
    return None


def first_metadata_str(
    eligibility: RagSourceEligibilityRecord,
    key: str,
) -> str | None:
    value = eligibility.metadata.get(key)
    if isinstance(value, str) and value.strip():
        return value
    if isinstance(value, tuple | list):
        for item in value:
            if isinstance(item, str) and item.strip():
                return item
    return None


def find_by_attribute[T](
    records: Sequence[T],
    attribute: str,
    expected: str,
) -> T | None:
    for record in records:
        if str(getattr(record, attribute, "")) == expected:
            return record
    return None
