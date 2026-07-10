from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime
from datetime import timezone

import pytest

from core.storage.persistence.rag import DEFAULT_RAG_ELIGIBILITY_REVIEWER
from core.storage.persistence.rag import DEFAULT_RAG_ELIGIBILITY_RULE_VERSION
from core.storage.persistence.rag import DefaultRagEligibilityRules
from core.storage.persistence.rag import RagEligibilitySourceCandidate
from core.storage.persistence.rag import evaluate_default_rag_source_eligibility


@pytest.mark.parametrize(
    ("source_table", "source_type", "expected_rule", "minimum_quality"),
    [
        ("reports", "morning_report", "curated_report_eligible", 0.9),
        ("report_sections", "report_section", "curated_report_eligible", 0.9),
        (
            "agent_signals",
            "agent_signal",
            "meaningful_agent_intelligence_eligible",
            0.8,
        ),
        (
            "agent_reasoning",
            "agent_reasoning",
            "meaningful_agent_intelligence_eligible",
            0.8,
        ),
        (
            "recommendation_rationales",
            "recommendation_rationale",
            "recommendation_rationale_eligible",
            0.85,
        ),
        ("macro_regime_snapshots", "macro_summary", "curated_summary_eligible", 0.8),
        (
            "technical_analysis_snapshots",
            "technical_summary",
            "curated_summary_eligible",
            0.8,
        ),
        (
            "market_context_snapshots",
            "market_context_summary",
            "curated_summary_eligible",
            0.8,
        ),
        (
            "market_breadth_snapshots",
            "market_breadth_summary",
            "curated_summary_eligible",
            0.8,
        ),
        (
            "portfolio_risk_snapshots",
            "portfolio_risk_summary",
            "curated_summary_eligible",
            0.8,
        ),
        (
            "portfolio_allocation_snapshots",
            "portfolio_allocation_summary",
            "curated_summary_eligible",
            0.8,
        ),
        ("news_analysis_snapshots", "news_summary", "curated_summary_eligible", 0.8),
        ("sentiment_snapshots", "sentiment_summary", "curated_summary_eligible", 0.8),
        ("backtest_runs", "backtest_summary", "curated_summary_eligible", 0.8),
        ("backtest_steps", "backtest_step_summary", "curated_summary_eligible", 0.8),
        (
            "backtest_portfolio_snapshots",
            "backtest_portfolio_summary",
            "curated_summary_eligible",
            0.8,
        ),
        (
            "backtest_metrics",
            "backtest_metric_summary",
            "curated_summary_eligible",
            0.8,
        ),
        ("backtest_artifacts", "backtest_artifact", "curated_summary_eligible", 0.8),
    ],
)
def test_default_rules_mark_curated_sources_eligible(
    source_table: str,
    source_type: str,
    expected_rule: str,
    minimum_quality: float,
) -> None:
    record = evaluate_default_rag_source_eligibility(
        RagEligibilitySourceCandidate(
            source_table=f" {source_table} ",
            source_id=" source-1 ",
            source_type=f" {source_type} ",
            metadata={"domain": "test"},
        ),
        reviewed_timestamp=_timestamp(),
    )

    assert record.source_table == source_table
    assert record.source_id == "source-1"
    assert record.source_type == source_type
    assert record.eligible is True
    assert record.quality_score >= minimum_quality
    assert record.reviewed_timestamp == _timestamp()
    assert record.metadata["reviewer"] == DEFAULT_RAG_ELIGIBILITY_REVIEWER
    assert record.metadata["rule_version"] == DEFAULT_RAG_ELIGIBILITY_RULE_VERSION
    assert record.metadata["rule_name"] == expected_rule
    assert record.metadata["domain"] == "test"
    assert record.eligibility_id == (
        f"rag_source_eligibility:{source_table}:{source_type}:source-1"
    )


def test_default_rules_require_rationale_for_recommendation_sources() -> None:
    without_rationale = DefaultRagEligibilityRules().evaluate(
        RagEligibilitySourceCandidate(
            source_table="recommendations",
            source_id="recommendation-1",
            source_type="recommendation",
            has_rationale=False,
        ),
        reviewed_timestamp=_timestamp(),
    )
    with_rationale = DefaultRagEligibilityRules().evaluate(
        RagEligibilitySourceCandidate(
            source_table="recommendations",
            source_id="recommendation-1",
            source_type="recommendation",
            has_rationale=True,
            quality_score=0.95,
        ),
        reviewed_timestamp=_timestamp(),
    )

    assert without_rationale.eligible is False
    assert without_rationale.reason == (
        "Recommendations without rationales are not curated RAG sources by default."
    )
    assert without_rationale.metadata["rule_name"] == (
        "recommendation_without_rationale_ineligible"
    )
    assert without_rationale.quality_score == 0.0

    assert with_rationale.eligible is True
    assert (
        with_rationale.reason
        == "Recommendations with rationales are eligible RAG sources."
    )
    assert (
        with_rationale.metadata["rule_name"] == "recommendation_with_rationale_eligible"
    )
    assert with_rationale.quality_score == 0.95


@pytest.mark.parametrize(
    ("source_table", "source_type", "expected_rule"),
    [
        ("workflow_events", "workflow_event", "raw_runtime_ineligible"),
        ("workflow_node_runs", "runtime_node_run", "raw_runtime_ineligible"),
        ("telemetry_events", "telemetry_event", "raw_telemetry_ineligible"),
        ("provider_metrics", "provider_metric", "raw_telemetry_ineligible"),
        ("raw_provider_payloads", "raw_provider_payload", "raw_provider_ineligible"),
        ("market_ohlcv", "raw_market_data", "raw_provider_ineligible"),
        ("news_articles", "raw_news_article", "raw_provider_ineligible"),
        ("sentiment_sources", "raw_sentiment_source", "raw_provider_ineligible"),
        (
            "operational_error_logs",
            "operational_error_log",
            "operational_error_log_ineligible",
        ),
    ],
)
def test_default_rules_mark_raw_operational_sources_ineligible(
    source_table: str,
    source_type: str,
    expected_rule: str,
) -> None:
    record = evaluate_default_rag_source_eligibility(
        RagEligibilitySourceCandidate(
            source_table=source_table,
            source_id="raw-1",
            source_type=source_type,
        ),
        reviewed_timestamp=_timestamp(),
    )

    assert record.eligible is False
    assert record.quality_score == 0.0
    assert record.metadata["rule_name"] == expected_rule
    assert "not curated RAG sources" in record.reason


def test_default_rules_mark_sources_without_meaningful_content_ineligible() -> None:
    record = evaluate_default_rag_source_eligibility(
        RagEligibilitySourceCandidate(
            source_table="reports",
            source_id="empty-report-1",
            source_type="morning_report",
            has_meaningful_content=False,
        ),
        reviewed_timestamp=_timestamp(),
    )

    assert record.eligible is False
    assert record.quality_score == 0.0
    assert record.reason == "Source lacks meaningful curated text for RAG retrieval."
    assert record.metadata["rule_name"] == "missing_meaningful_content_ineligible"


def test_default_rules_mark_unknown_sources_ineligible() -> None:
    record = evaluate_default_rag_source_eligibility(
        RagEligibilitySourceCandidate(
            source_table="custom_operational_table",
            source_id="custom-1",
            source_type="custom_event",
        ),
        reviewed_timestamp=_timestamp(),
    )

    assert record.eligible is False
    assert record.quality_score == 0.0
    assert (
        record.reason == "No default curated RAG eligibility rule matched this source."
    )
    assert record.metadata["rule_name"] == "unknown_source_ineligible"


def test_default_rules_can_use_curated_source_type_when_table_is_new() -> None:
    record = evaluate_default_rag_source_eligibility(
        RagEligibilitySourceCandidate(
            source_table="custom_report_archive",
            source_id="report-archive-1",
            source_type="report",
        ),
        reviewed_timestamp=_timestamp(),
    )

    assert record.eligible is True
    assert record.quality_score == 0.8
    assert record.metadata["rule_name"] == "curated_source_type_eligible"


def test_source_candidate_validates_and_is_immutable() -> None:
    candidate = RagEligibilitySourceCandidate(
        source_table=" Reports ",
        source_id=" Report-1 ",
        source_type=" Morning_Report ",
        quality_score=0.7,
    )

    assert candidate.source_table == "reports"
    assert candidate.source_id == "Report-1"
    assert candidate.source_type == "morning_report"
    assert candidate.quality_score == 0.7

    with pytest.raises(FrozenInstanceError):
        candidate.source_id = "other"  # type: ignore[misc]

    with pytest.raises(ValueError, match="source_table"):
        RagEligibilitySourceCandidate(
            source_table=" ",
            source_id="source-1",
            source_type="report",
        )

    with pytest.raises(ValueError, match="quality_score"):
        RagEligibilitySourceCandidate(
            source_table="reports",
            source_id="source-1",
            source_type="report",
            quality_score=1.01,
        )


def test_eligibility_rule_output_remains_metadata_only() -> None:
    payload = evaluate_default_rag_source_eligibility(
        RagEligibilitySourceCandidate(
            source_table="reports",
            source_id="report-1",
            source_type="morning_report",
        ),
        reviewed_timestamp=_timestamp(),
    ).as_dict()

    assert "document_id" not in payload
    assert "chunk_id" not in payload
    assert "job_id" not in payload
    assert "embedding" not in payload
    assert "vector_store" not in payload
    assert "graph_store" not in payload


def _timestamp() -> datetime:
    return datetime(
        2026,
        6,
        1,
        12,
        0,
        tzinfo=timezone.utc,
    )
