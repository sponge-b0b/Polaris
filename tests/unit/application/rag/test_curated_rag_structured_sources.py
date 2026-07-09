from __future__ import annotations

from datetime import UTC
from datetime import datetime
from decimal import Decimal

import pytest

from application.rag.ingestion.curated_rag_document_builder import (
    CuratedRagDocumentBuilder,
)
from application.rag.ingestion.curated_rag_models import CuratedRagBuildOptions
from application.rag.ingestion.curated_rag_structured_sources import (
    StructuredCuratedRagSource,
)
from application.rag.ingestion.curated_rag_structured_sources import (
    structured_source_id,
)
from application.rag.ingestion.curated_rag_structured_sources import (
    structured_source_timestamp,
)
from core.storage.persistence.backtesting import BacktestArtifactRecord
from core.storage.persistence.backtesting import BacktestMetricRecord
from core.storage.persistence.backtesting import BacktestPortfolioSnapshotRecord
from core.storage.persistence.backtesting import BacktestRunRecord
from core.storage.persistence.backtesting import BacktestStepRecord
from core.storage.persistence.lineage import PersistenceLineage
from core.storage.persistence.macro import MacroRegimeSnapshotRecord
from core.storage.persistence.market import MarketBreadthSnapshotRecord
from core.storage.persistence.market import MarketContextSnapshotRecord
from core.storage.persistence.market import TechnicalAnalysisSnapshotRecord
from core.storage.persistence.news import NewsAnalysisSnapshotRecord
from core.storage.persistence.portfolio import PortfolioAllocationSnapshotRecord
from core.storage.persistence.portfolio import PortfolioRiskSnapshotRecord
from core.storage.persistence.rag import RagSourceEligibilityRecord
from core.storage.persistence.recommendations import RecommendationRationaleRecord
from core.storage.persistence.recommendations import RecommendationRecord
from core.storage.persistence.sentiment import SentimentSnapshotRecord


def _timestamp() -> datetime:
    return datetime(2026, 6, 1, 12, 0, tzinfo=UTC)


def _lineage() -> PersistenceLineage:
    return PersistenceLineage(
        workflow_name="morning_report",
        execution_id="execution-1",
        runtime_id="runtime-1",
        node_name="technical_node",
    )


@pytest.mark.parametrize(
    ("source", "source_table", "source_type", "expected_text"),
    [
        (
            RecommendationRecord(
                recommendation_id="recommendation-1",
                symbol="SPY",
                bias="bullish",
                confidence=0.82,
                created_at=_timestamp(),
                lineage=_lineage(),
                setup_quality=0.74,
                risk_score=0.22,
                risk_level="moderate",
                time_horizon="swing",
                status="active",
                entry_context={"trigger": "breadth confirmation"},
                metadata={"has_rationale": True},
            ),
            "recommendations",
            "recommendation",
            "Breadth Confirmation",
        ),
        (
            RecommendationRationaleRecord(
                rationale_id="rationale-1",
                recommendation_id="recommendation-1",
                rationale_type="technical",
                rationale_text="Full rationale text is retained without truncation.",
                created_at=_timestamp(),
                lineage=_lineage(),
                confidence=0.81,
            ),
            "recommendation_rationales",
            "recommendation_rationale",
            "Full rationale text is retained without truncation.",
        ),
        (
            MacroRegimeSnapshotRecord(
                regime_snapshot_id="macro-1",
                timestamp=_timestamp(),
                lineage=_lineage(),
                region="US",
                macro_regime="expansion",
                economic_regime="growth",
                macro_score=0.71,
                risk_score=0.28,
                confidence=0.77,
                outputs={"summary": "growth remains resilient"},
            ),
            "macro_regime_snapshots",
            "macro_summary",
            "Growth Remains Resilient",
        ),
        (
            MarketContextSnapshotRecord(
                context_snapshot_id="market-context-1",
                timestamp=_timestamp(),
                lineage=_lineage(),
                universe="SP500",
                market_regime="risk_on",
                volatility_regime="contained",
                breadth_regime="constructive",
                trend_score=0.33,
                volatility_score=0.12,
                breadth_score=0.64,
                risk_score=0.21,
                vix=14.2,
                market_context_payload={"summary": "constructive context"},
            ),
            "market_context_snapshots",
            "market_context_summary",
            "Constructive Context",
        ),
        (
            TechnicalAnalysisSnapshotRecord(
                technical_snapshot_id="technical-1",
                symbol="SPY",
                timestamp=_timestamp(),
                lineage=_lineage(),
                technical_regime="bullish",
                trend_regime="uptrend",
                technical_score=0.69,
                confidence=0.8,
                regime_payload={"summary": "trend confirmed"},
            ),
            "technical_analysis_snapshots",
            "technical_summary",
            "Trend Confirmed",
        ),
        (
            MarketBreadthSnapshotRecord(
                breadth_snapshot_id="breadth-1",
                timestamp=_timestamp(),
                universe="SP500",
                lineage=_lineage(),
                breadth_regime="broad",
                risk_regime="low",
                advances_count=310,
                declines_count=190,
                ad_line=1234.5,
                ad_line_trend_score=0.66,
                breadth_payload={"summary": "participation improved"},
            ),
            "market_breadth_snapshots",
            "market_breadth_summary",
            "Participation Improved",
        ),
        (
            PortfolioRiskSnapshotRecord(
                risk_snapshot_id="risk-1",
                account_id="account-1",
                timestamp=_timestamp(),
                lineage=_lineage(),
                account_health="healthy",
                risk_level="moderate",
                risk_score=0.31,
                risk_signals={"summary": "risk within limits"},
            ),
            "portfolio_risk_snapshots",
            "portfolio_risk_summary",
            "Risk Within Limits",
        ),
        (
            PortfolioAllocationSnapshotRecord(
                allocation_snapshot_id="allocation-1",
                account_id="account-1",
                timestamp=_timestamp(),
                allocation_type="sector",
                allocation_name="technology",
                current_weight=0.24,
                lineage=_lineage(),
                target_weight=0.22,
                drift=0.02,
            ),
            "portfolio_allocation_snapshots",
            "portfolio_allocation_summary",
            "Technology",
        ),
        (
            NewsAnalysisSnapshotRecord(
                analysis_snapshot_id="news-1",
                timestamp=_timestamp(),
                lineage=_lineage(),
                source="curated_news",
                symbols=("SPY",),
                themes=("macro",),
                importance_score=0.72,
                confidence=0.83,
                llm_summary="Concise curated news summary.",
                full_llm_response="Full LLM response remains complete. " * 20,
            ),
            "news_analysis_snapshots",
            "news_summary",
            "Full LLM Response Remains Complete",
        ),
        (
            SentimentSnapshotRecord(
                sentiment_snapshot_id="sentiment-1",
                timestamp=_timestamp(),
                lineage=_lineage(),
                source="curated_sentiment",
                symbol="SPY",
                market_regime="positive",
                composite_sentiment=0.63,
                confidence=0.79,
                sentiment_payload={"summary": "sentiment improved"},
            ),
            "sentiment_snapshots",
            "sentiment_summary",
            "Sentiment Improved",
        ),
        (
            BacktestRunRecord(
                backtest_run_id="backtest-1",
                scenario_id="scenario-1",
                workflow_name="morning_report",
                status="succeeded",
                success=True,
                started_at=_timestamp(),
                completed_at=_timestamp(),
                metrics={"return": "0.12"},
            ),
            "backtest_runs",
            "backtest_summary",
            "Morning_Report",
        ),
        (
            BacktestStepRecord(
                step_id="step-1",
                backtest_run_id="backtest-1",
                step_index=1,
                timestamp=_timestamp(),
                workflow_run_id="workflow-run-1",
                success=True,
                node_output_keys=("technical_signal",),
                summary={"assessment": "trade recommendation matched fixture"},
            ),
            "backtest_steps",
            "backtest_step_summary",
            "Trade Recommendation Matched Fixture",
        ),
        (
            BacktestPortfolioSnapshotRecord(
                snapshot_id="backtest-portfolio-1",
                backtest_run_id="backtest-1",
                step_id="step-1",
                timestamp=_timestamp(),
                cash=Decimal("1000.00"),
                equity=Decimal("1200.00"),
                market_value=Decimal("2200.00"),
                positions={"SPY": "3"},
            ),
            "backtest_portfolio_snapshots",
            "backtest_portfolio_summary",
            "1000.00",
        ),
        (
            BacktestMetricRecord(
                metric_id="metric-1",
                backtest_run_id="backtest-1",
                metric_name="max_drawdown",
                metric_value=Decimal("0.08"),
                recorded_at=_timestamp(),
                metadata={"timestamp": "1970-01-01T00:00:00+00:00"},
            ),
            "backtest_metrics",
            "backtest_metric_summary",
            "Max_Drawdown",
        ),
        (
            BacktestArtifactRecord(
                artifact_id="artifact-1",
                backtest_run_id="backtest-1",
                artifact_format="markdown",
                content="# Backtest Report\n\nDeterministic result verified.",
                mime_type="text/markdown",
                generated_at=_timestamp(),
                metadata={"created_at": "1970-01-01T00:00:00+00:00"},
            ),
            "backtest_artifacts",
            "backtest_artifact",
            "Deterministic Result Verified",
        ),
    ],
)
def test_structured_curated_sources_build_deterministic_human_readable_chunks(
    source: StructuredCuratedRagSource,
    source_table: str,
    source_type: str,
    expected_text: str,
) -> None:
    builder = CuratedRagDocumentBuilder()
    options = CuratedRagBuildOptions(
        max_chunk_characters=800,
        queue_embedding_jobs=True,
    )
    eligibility = _eligibility(
        source_table=source_table,
        source_id=structured_source_id(source),
        source_type=source_type,
    )

    first = builder.build_from_source(
        source,
        options=options,
        source_eligibility=eligibility,
    )
    second = builder.build_from_source(
        source,
        options=options,
        source_eligibility=eligibility,
    )

    assert first.document == second.document
    assert first.chunks == second.chunks
    assert first.embedding_jobs == second.embedding_jobs
    assert first.document.source_table == source_table
    assert first.document.source_type == source_type
    assert first.document.metadata["curated_source"] is True
    assert first.document.generated_at == _timestamp()
    assert all(
        chunk.metadata["created_at"] == _timestamp().isoformat()
        and chunk.metadata["as_of_date"] == _timestamp().date().isoformat()
        for chunk in first.chunks
    )
    assert all(job.queued_at == _timestamp() for job in first.embedding_jobs)
    assert "## Source Lineage" in first.document.content_text
    assert "## Curated Summary" in first.document.content_text
    assert expected_text.lower() in first.document.content_text.lower()
    assert first.chunks
    assert first.embedding_jobs


def test_structured_source_timestamp_rejects_missing_domain_timestamp() -> None:
    source = BacktestMetricRecord(
        metric_id="metric-missing-timestamp",
        backtest_run_id="backtest-1",
        metric_name="max_drawdown",
        metric_value=Decimal("0.08"),
        recorded_at=_timestamp(),
        metadata={"timestamp": "1970-01-01T00:00:00+00:00"},
    )
    object.__setattr__(source, "recorded_at", None)

    with pytest.raises(ValueError, match="recorded_at must contain a domain timestamp"):
        structured_source_timestamp(source)


def _eligibility(
    *,
    source_table: str,
    source_id: str,
    source_type: str,
) -> RagSourceEligibilityRecord:
    return RagSourceEligibilityRecord(
        eligibility_id=f"eligibility-{source_id}",
        source_table=source_table,
        source_id=source_id,
        source_type=source_type,
        eligible=True,
        reason="test eligible",
        quality_score=0.9,
        reviewed_timestamp=_timestamp(),
        metadata={"rule_name": "test_rule"},
    )
