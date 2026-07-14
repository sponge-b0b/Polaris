from __future__ import annotations

from pathlib import Path

from alembic.config import Config

from core.database.base import Base
import core.database.models  # noqa: F401


def test_alembic_config_points_to_migrations_directory() -> None:
    config = Config("alembic.ini")

    assert config.get_main_option("script_location") == "migrations"
    assert Path("migrations/env.py").exists()
    assert Path("migrations/script.py.mako").exists()
    assert Path("migrations/versions").is_dir()


def test_database_models_are_imported_into_base_metadata() -> None:
    assert "portfolio_state_history" in Base.metadata.tables
    assert "portfolio_state_latest" in Base.metadata.tables
    assert "workflow_runs" in Base.metadata.tables
    assert "workflow_node_runs" in Base.metadata.tables
    assert "workflow_events" in Base.metadata.tables
    assert "workflow_state_snapshots" in Base.metadata.tables
    assert "reports" in Base.metadata.tables
    assert "report_sections" in Base.metadata.tables
    assert "report_artifacts" in Base.metadata.tables
    assert "report_versions" in Base.metadata.tables
    assert "report_publications" in Base.metadata.tables
    assert "agent_signals" in Base.metadata.tables
    assert "agent_reasoning" in Base.metadata.tables
    assert "agent_recommendations" in Base.metadata.tables
    assert "agent_risk_assessments" in Base.metadata.tables
    assert "recommendation_attribution" in Base.metadata.tables
    assert "signal_attribution" in Base.metadata.tables
    assert "attribution_records" in Base.metadata.tables
    assert "rag_embedding_jobs" in Base.metadata.tables
    assert "rag_chunks" in Base.metadata.tables
    assert "rag_documents" in Base.metadata.tables
    assert "rag_source_eligibility" in Base.metadata.tables
    assert "rag_graph_jobs" in Base.metadata.tables
    assert "rag_query_logs" in Base.metadata.tables
    assert "rag_answer_logs" in Base.metadata.tables
    assert "persistence_lineage_links" in Base.metadata.tables
    assert "persistence_audit_events" in Base.metadata.tables
    assert "persistence_retention_policies" in Base.metadata.tables
    assert "recommendations" in Base.metadata.tables
    assert "recommendation_rationales" in Base.metadata.tables
    assert "recommendation_outcomes" in Base.metadata.tables
    assert "trade_setups" in Base.metadata.tables
    assert "watchlist_items" in Base.metadata.tables
    assert "portfolio_positions_history" in Base.metadata.tables
    assert "portfolio_positions_latest" in Base.metadata.tables
    assert "portfolio_exposure_snapshots" in Base.metadata.tables
    assert "portfolio_risk_snapshots" in Base.metadata.tables
    assert "portfolio_allocation_snapshots" in Base.metadata.tables
    assert "market_ohlcv" in Base.metadata.tables
    assert "market_indicators" in Base.metadata.tables
    assert "market_context_snapshots" in Base.metadata.tables
    assert "technical_analysis_snapshots" in Base.metadata.tables
    assert "market_breadth_snapshots" in Base.metadata.tables
    assert "market_event_snapshots" in Base.metadata.tables
    assert "macro_observations" in Base.metadata.tables
    assert "macro_regime_snapshots" in Base.metadata.tables
    assert "economic_calendar_events" in Base.metadata.tables
    assert "news_analysis_snapshots" in Base.metadata.tables
    assert "news_articles" in Base.metadata.tables
    assert "sentiment_snapshots" in Base.metadata.tables
    assert "sentiment_sources" in Base.metadata.tables
    assert "telemetry_events" in Base.metadata.tables
    assert "telemetry_metrics" in Base.metadata.tables
    assert "telemetry_traces" in Base.metadata.tables
    assert "workflow_metrics" in Base.metadata.tables
    assert "agent_metrics" in Base.metadata.tables
    assert "provider_metrics" in Base.metadata.tables
    assert "ai_observability_export_jobs" in Base.metadata.tables
    assert "evaluation_datasets" in Base.metadata.tables
    assert "evaluation_cases" in Base.metadata.tables
    assert "evaluation_runs" in Base.metadata.tables
    assert "evaluation_metric_results" in Base.metadata.tables
    assert "evaluation_artifacts" in Base.metadata.tables
