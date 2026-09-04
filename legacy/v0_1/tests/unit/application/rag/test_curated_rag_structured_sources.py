from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from application.rag.ingestion.curated_rag_document_builder import (
    CuratedRagDocumentBuilder,
)
from application.rag.ingestion.curated_rag_models import CuratedRagBuildOptions
from application.rag.ingestion.curated_rag_structured_sources import (
    StructuredCuratedRagSource,
    structured_source_id,
    structured_source_timestamp,
)
from core.storage.persistence.backtesting import (
    BacktestArtifactRecord,
    BacktestMetricRecord,
    BacktestPortfolioSnapshotRecord,
    BacktestRunRecord,
    BacktestStepRecord,
)
from core.storage.persistence.lineage import PersistenceLineage
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
from core.storage.persistence.rag import RagSourceEligibilityRecord
from core.storage.persistence.recommendations import (
    RecommendationRationaleRecord,
    RecommendationRecord,
)
from core.storage.persistence.sentiment import SentimentSnapshotRecord
from core.storage.persistence.strategy import (
    StrategyHypothesisEvaluationRecord,
    StrategyHypothesisRecord,
    StrategyPersistenceBundle,
    StrategySynthesisDecisionRecord,
)


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


def test_strategy_decision_bundle_builds_primary_curated_rag_document_with_hypothesis_attribution() -> (  # noqa: E501 - descriptive pytest node id
    None
):
    bundle = _strategy_bundle()
    builder = CuratedRagDocumentBuilder()
    options = CuratedRagBuildOptions(
        max_chunk_characters=10_000,
        queue_embedding_jobs=True,
    )
    eligibility = _eligibility(
        source_table="strategy_synthesis_decisions",
        source_id=bundle.decision.decision_id,
        source_type="strategy_synthesis_decision",
    )

    result = builder.build_from_source(
        bundle,
        options=options,
        source_eligibility=eligibility,
    )

    assert result.document.source_table == "strategy_synthesis_decisions"
    assert result.document.source_id == bundle.decision.decision_id
    assert result.document.source_type == "strategy_synthesis_decision"
    assert result.document.metadata["source_kind"] == "strategy_synthesis_decision"
    assert result.document.metadata["related_hypothesis_ids"] == [
        hypothesis.hypothesis_id for hypothesis in bundle.hypotheses
    ]
    assert "## Why This Decision" in result.document.content_text
    assert "## Evaluated Hypotheses" in result.document.content_text
    assert "## Why Not / Contradictions" in result.document.content_text
    assert "## What Would Invalidate This Decision" in result.document.content_text
    assert "SPY closes below 50dma" in result.document.content_text
    assert "breadth expanded across sectors" in result.document.content_text
    assert "macro risk remains elevated" in result.document.content_text
    assert all(
        chunk.metadata["source_table"] == "strategy_synthesis_decisions"
        and chunk.metadata["source_record_id"] == bundle.decision.decision_id
        and chunk.metadata["related_hypothesis_ids"]
        == [hypothesis.hypothesis_id for hypothesis in bundle.hypotheses]
        for chunk in result.chunks
    )
    assert result.embedding_jobs


def test_strategy_hypothesis_builds_attributable_why_why_not_and_invalidation_content() -> (  # noqa: E501 - descriptive pytest node id
    None
):
    hypothesis = _strategy_hypothesis()
    builder = CuratedRagDocumentBuilder()
    options = CuratedRagBuildOptions(
        max_chunk_characters=10_000,
        queue_embedding_jobs=True,
    )
    eligibility = _eligibility(
        source_table="strategy_hypotheses",
        source_id=hypothesis.hypothesis_id,
        source_type="strategy_hypothesis",
    )

    result = builder.build_from_source(
        hypothesis,
        options=options,
        source_eligibility=eligibility,
    )

    assert result.document.source_table == "strategy_hypotheses"
    assert result.document.source_id == hypothesis.hypothesis_id
    assert result.document.source_type == "strategy_hypothesis"
    assert result.document.metadata["source_kind"] == "strategy_hypothesis"
    assert result.document.metadata["perspective"] == "bull"
    assert "## Why This Hypothesis" in result.document.content_text
    assert "## Why Not / Contradictions" in result.document.content_text
    assert "## Key Assumptions" in result.document.content_text
    assert "## What Would Invalidate This Decision" in result.document.content_text
    assert "breadth expanded across sectors" in result.document.content_text
    assert "macro risk remains elevated" in result.document.content_text
    assert "SPY closes below 50dma" in result.document.content_text
    assert result.embedding_jobs


def _strategy_bundle() -> StrategyPersistenceBundle:
    decision = StrategySynthesisDecisionRecord(
        decision_id="strategy-decision-1",
        symbol="SPY",
        selection_status="selected",
        selected_perspective="bull",
        directional_score=0.62,
        confidence=0.78,
        regime="risk_on",
        uncertainty=0.22,
        thesis=(
            "Bull perspective is selected because breadth and trend evidence dominate "
            "unresolved macro risks."
        ),
        evidence_fingerprint="fingerprint-1",
        created_at=_timestamp(),
        lineage=_lineage(),
        horizon="swing",
        signals=("breadth confirmation", "trend persistence"),
        risks=("macro risk remains elevated",),
        recommendations=("maintain constructive exposure",),
    )
    hypotheses = (
        _strategy_hypothesis(
            perspective="bull",
            hypothesis_id="hypothesis-bull",
            thesis=(
                "Bullish continuation is supported by stronger participation and trend "
                "confirmation."
            ),
        ),
        _strategy_hypothesis(
            perspective="bear",
            hypothesis_id="hypothesis-bear",
            thesis=(
                "Bearish reversal would require macro risk to overpower breadth "
                "confirmation."
            ),
            directional_bias=-0.55,
            hypothesis_strength=0.41,
            confidence=0.46,
        ),
        _strategy_hypothesis(
            perspective="sideways",
            hypothesis_id="hypothesis-sideways",
            thesis=(
                "Sideways consolidation remains possible if breadth stalls without a "
                "volatility break."
            ),
            directional_bias=0.0,
            hypothesis_strength=0.37,
            confidence=0.44,
        ),
    )
    evaluations = (
        _strategy_evaluation("bull", "hypothesis-bull", rank=1, status="selected"),
        _strategy_evaluation("bear", "hypothesis-bear", rank=2, status="rejected"),
        _strategy_evaluation(
            "sideways",
            "hypothesis-sideways",
            rank=3,
            status="rejected",
        ),
    )
    return StrategyPersistenceBundle(
        decision=decision,
        hypotheses=hypotheses,
        evaluations=evaluations,
    )


def _strategy_hypothesis(
    *,
    perspective: str = "bull",
    hypothesis_id: str = "hypothesis-bull",
    thesis: str = (
        "Bullish continuation is supported by stronger participation "
        "and trend confirmation."
    ),
    directional_bias: float = 0.65,
    hypothesis_strength: float = 0.74,
    confidence: float = 0.81,
) -> StrategyHypothesisRecord:
    return StrategyHypothesisRecord(
        hypothesis_id=hypothesis_id,
        symbol="SPY",
        perspective=perspective,
        thesis=thesis,
        directional_bias=directional_bias,
        hypothesis_strength=hypothesis_strength,
        confidence=confidence,
        evidence_fingerprint="fingerprint-1",
        created_at=_timestamp(),
        lineage=_lineage(),
        horizon="swing",
        supporting_evidence=(
            {
                "claim": "breadth expanded across sectors",
                "source": "technical_analysis_service",
            },
        ),
        contradicting_evidence=(
            {
                "claim": "macro risk remains elevated",
                "source": "macro_service",
            },
        ),
        key_assumptions=(
            {
                "assumption": "breadth persists through the next session",
                "source": "strategy_evidence_context",
            },
        ),
        invalidation_conditions=(
            {
                "condition": "SPY closes below 50dma",
                "threshold": "50dma",
                "source": "technical_analysis_service",
            },
        ),
        risks=("macro risk remains elevated",),
        recommendations=("monitor breadth confirmation",),
        data_quality_flags=("complete_evidence_context",),
    )


def _strategy_evaluation(
    perspective: str,
    hypothesis_id: str,
    *,
    rank: int,
    status: str,
) -> StrategyHypothesisEvaluationRecord:
    return StrategyHypothesisEvaluationRecord(
        evaluation_id=f"strategy-decision-1:evaluation:{perspective}",
        decision_id="strategy-decision-1",
        symbol="SPY",
        perspective=perspective,
        perspective_weight=0.5 if perspective == "bull" else 0.25,
        contradiction_burden=0.2,
        assumption_support=0.8,
        invalidated=False,
        candidate_score=0.7 if perspective == "bull" else 0.4,
        synthesis_weight=0.55 if perspective == "bull" else 0.225,
        rank=rank,
        selection_status=status,
        evidence_fingerprint="fingerprint-1",
        created_at=_timestamp(),
        lineage=_lineage(),
        hypothesis_id=hypothesis_id,
        horizon="swing",
    )


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
