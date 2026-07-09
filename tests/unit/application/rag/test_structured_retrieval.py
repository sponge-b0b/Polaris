from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from datetime import timezone
from typing import cast

import pytest

from application.rag.retrieval.structured_retrieval import MarketStructuredRagRetriever
from application.rag.contracts.rag_request import RagRequest
from application.rag.contracts.rag_context import RagRetrievalFilters
from core.storage.persistence.lineage import PersistenceLineage
from core.storage.persistence.market import TechnicalAnalysisSnapshotRecord
from core.storage.persistence.market.market_persistence_repository import (
    MarketPersistenceRepository,
)


@pytest.mark.asyncio
async def test_structured_retrieval_uses_only_typed_market_repository_path() -> None:
    repository = FakeMarketRepository(
        records=(
            _snapshot("older", datetime(2026, 6, 1, tzinfo=timezone.utc), 0.4),
            _snapshot("latest", datetime(2026, 6, 2, tzinfo=timezone.utc), 0.8),
        )
    )
    retriever = MarketStructuredRagRetriever(
        cast(MarketPersistenceRepository, repository)
    )

    contexts = await retriever.retrieve(
        RagRequest(
            query="What is the current SPY technical regime?",
            filters=RagRetrievalFilters(
                source_tables=("technical_analysis_snapshots",),
                source_types=("technical_analysis_snapshot",),
                symbols=("SPY",),
                regimes=("bullish",),
                workflow_name="morning_report",
                execution_id="exec-1",
            ),
            request_id="structured-1",
        )
    )

    assert len(contexts) == 1
    assert contexts[0].source.source_id == "latest"
    assert "technical_regime=bullish" in contexts[0].text
    assert "technical_score=0.8" in contexts[0].text
    assert contexts[0].metadata["repository_path"] == (
        "MarketPersistenceRepository.list_technical_snapshots"
    )
    assert repository.calls == [
        {
            "symbol": "SPY",
            "technical_regime": "bullish",
            "start": None,
            "end": None,
        }
    ]


@pytest.mark.asyncio
async def test_structured_retrieval_does_not_query_unapproved_source_table() -> None:
    repository = FakeMarketRepository(records=())
    retriever = MarketStructuredRagRetriever(
        cast(MarketPersistenceRepository, repository)
    )

    contexts = await retriever.retrieve(
        RagRequest(
            query="SPY facts",
            filters=RagRetrievalFilters(
                source_tables=("provider_payloads",),
                symbols=("SPY",),
            ),
        )
    )

    assert contexts == ()
    assert repository.calls == []


class FakeMarketRepository:
    def __init__(
        self,
        *,
        records: Sequence[TechnicalAnalysisSnapshotRecord],
    ) -> None:
        self.records = tuple(records)
        self.calls: list[dict[str, object]] = []

    async def list_technical_snapshots(
        self,
        *,
        symbol: str,
        source: str | None = None,
        technical_regime: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[TechnicalAnalysisSnapshotRecord]:
        self.calls.append(
            {
                "symbol": symbol,
                "technical_regime": technical_regime,
                "start": start,
                "end": end,
            }
        )
        return self.records


def _snapshot(
    snapshot_id: str,
    timestamp: datetime,
    technical_score: float,
) -> TechnicalAnalysisSnapshotRecord:
    return TechnicalAnalysisSnapshotRecord(
        technical_snapshot_id=snapshot_id,
        symbol="SPY",
        timestamp=timestamp,
        lineage=PersistenceLineage(
            workflow_name="morning_report",
            execution_id="exec-1",
        ),
        technical_regime="bullish",
        trend_regime="uptrend",
        volatility_regime="contained",
        breadth_regime="constructive",
        technical_score=technical_score,
        trend_score=0.6,
        volatility_score=0.5,
        breadth_score=0.7,
        risk_score=0.2,
        confidence=0.9,
    )


@pytest.mark.asyncio
async def test_structured_retrieval_honors_source_type_and_lineage_filters() -> None:
    repository = FakeMarketRepository(
        records=(_snapshot("latest", datetime(2026, 6, 2, tzinfo=timezone.utc), 0.8),)
    )
    retriever = MarketStructuredRagRetriever(
        cast(MarketPersistenceRepository, repository)
    )

    wrong_source_type = await retriever.retrieve(
        RagRequest(
            query="SPY facts",
            filters=RagRetrievalFilters(
                source_types=("morning_report",),
                symbols=("SPY",),
            ),
        )
    )
    wrong_execution = await retriever.retrieve(
        RagRequest(
            query="SPY facts",
            filters=RagRetrievalFilters(
                source_types=("technical_analysis_snapshot",),
                symbols=("SPY",),
                execution_id="other-execution",
            ),
        )
    )

    assert wrong_source_type == ()
    assert wrong_execution == ()
    assert len(repository.calls) == 1
