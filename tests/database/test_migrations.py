from __future__ import annotations

from pytest_alembic import tests as alembic_tests
from pytest_alembic.runner import MigrationContext


def test_migration_history_has_single_head(
    alembic_runner: MigrationContext,
) -> None:
    alembic_tests.test_single_head_revision(alembic_runner)


def test_migrations_upgrade_from_blank_database(
    alembic_runner: MigrationContext,
) -> None:
    alembic_tests.test_upgrade(alembic_runner)


def test_migration_downgrades_are_consistent(
    alembic_runner: MigrationContext,
) -> None:
    alembic_tests.test_up_down_consistency(alembic_runner)


def test_model_definitions_match_migrated_ddl(
    alembic_runner: MigrationContext,
) -> None:
    alembic_tests.test_model_definitions_match_ddl(alembic_runner)


def test_backtest_domain_schema_has_first_class_timestamps(
    alembic_runner: MigrationContext,
    alembic_engine: object,
) -> None:
    from sqlalchemy import Engine
    from sqlalchemy import inspect

    engine = alembic_engine
    assert isinstance(engine, Engine)
    alembic_runner.migrate_up_to("heads")

    inspector = inspect(engine)
    metric_columns = {
        column["name"]: column for column in inspector.get_columns("backtest_metrics")
    }
    artifact_columns = {
        column["name"]: column for column in inspector.get_columns("backtest_artifacts")
    }

    assert "recorded_at" in metric_columns
    assert metric_columns["recorded_at"]["nullable"] is False
    assert "generated_at" in artifact_columns
    assert artifact_columns["generated_at"]["nullable"] is False


def test_rag_query_audit_schema_has_promoted_fields(
    alembic_runner: MigrationContext,
    alembic_engine: object,
) -> None:
    from sqlalchemy import Engine
    from sqlalchemy import inspect

    engine = alembic_engine
    assert isinstance(engine, Engine)
    alembic_runner.migrate_up_to("heads")

    inspector = inspect(engine)
    rag_query_columns = {
        column["name"]: column for column in inspector.get_columns("rag_query_logs")
    }
    assert {
        "model_executions",
        "context_count",
        "citation_count",
        "grounding_score",
        "utility_score",
        "injection_detected",
        "reflection_scores",
        "corrective_actions",
    } <= set(rag_query_columns)

    assert rag_query_columns["model_executions"]["nullable"] is False
    assert rag_query_columns["context_count"]["nullable"] is False
    assert rag_query_columns["citation_count"]["nullable"] is False
    assert rag_query_columns["injection_detected"]["nullable"] is False
    assert rag_query_columns["reflection_scores"]["nullable"] is False
    assert rag_query_columns["corrective_actions"]["nullable"] is False

    index_names = {index["name"] for index in inspector.get_indexes("rag_query_logs")}
    assert {
        "idx_rag_query_logs_injection_detected_true",
        "idx_rag_query_logs_grounding_score",
        "idx_rag_query_logs_utility_score",
    } <= index_names


def test_strategy_persistence_migration_creates_canonical_schema(
    alembic_runner: MigrationContext,
    alembic_engine: object,
) -> None:
    from sqlalchemy import Engine
    from sqlalchemy import inspect

    engine = alembic_engine
    assert isinstance(engine, Engine)
    alembic_runner.migrate_up_to("heads")

    inspector = inspect(engine)
    assert {
        "strategy_hypotheses",
        "strategy_synthesis_decisions",
        "strategy_hypothesis_evaluations",
    } <= set(inspector.get_table_names())

    hypothesis_columns = {
        column["name"] for column in inspector.get_columns("strategy_hypotheses")
    }
    assert {
        "hypothesis_id",
        "symbol",
        "perspective",
        "thesis",
        "directional_bias",
        "hypothesis_strength",
        "confidence",
        "evidence_fingerprint",
        "invalidated",
        "horizon",
        "as_of",
        "workflow_name",
        "execution_id",
        "runtime_id",
        "node_name",
        "created_at",
        "supporting_evidence",
        "contradicting_evidence",
        "key_assumptions",
        "invalidation_conditions",
        "risks",
        "recommendations",
        "data_quality_flags",
        "metadata",
        "row_created_at",
        "row_updated_at",
    } <= hypothesis_columns

    decision_columns = {
        column["name"]
        for column in inspector.get_columns("strategy_synthesis_decisions")
    }
    assert {
        "decision_id",
        "symbol",
        "selected_perspective",
        "selection_status",
        "directional_score",
        "confidence",
        "regime",
        "uncertainty",
        "thesis",
        "evidence_fingerprint",
        "horizon",
        "as_of",
        "workflow_name",
        "execution_id",
        "runtime_id",
        "node_name",
        "created_at",
        "signals",
        "risks",
        "recommendations",
        "degraded_reasons",
        "metadata",
        "row_created_at",
        "row_updated_at",
    } <= decision_columns

    evaluation_columns = {
        column["name"]
        for column in inspector.get_columns("strategy_hypothesis_evaluations")
    }
    assert {
        "evaluation_id",
        "decision_id",
        "hypothesis_id",
        "symbol",
        "perspective",
        "perspective_weight",
        "contradiction_burden",
        "assumption_support",
        "invalidated",
        "candidate_score",
        "synthesis_weight",
        "rank",
        "selection_status",
        "evidence_fingerprint",
        "horizon",
        "as_of",
        "workflow_name",
        "execution_id",
        "runtime_id",
        "node_name",
        "created_at",
        "degraded_reasons",
        "metadata",
        "row_created_at",
        "row_updated_at",
    } <= evaluation_columns

    indexes_by_table = {
        table_name: {index["name"] for index in inspector.get_indexes(table_name)}
        for table_name in (
            "strategy_hypotheses",
            "strategy_synthesis_decisions",
            "strategy_hypothesis_evaluations",
        )
    }
    assert {
        "idx_strategy_hypotheses_execution_node",
        "idx_strategy_hypotheses_symbol_horizon_as_of",
        "idx_strategy_hypotheses_perspective_fingerprint",
    } <= indexes_by_table["strategy_hypotheses"]
    assert {
        "idx_strategy_decisions_execution_node",
        "idx_strategy_decisions_symbol_horizon_as_of",
        "idx_strategy_decisions_status_confidence",
    } <= indexes_by_table["strategy_synthesis_decisions"]
    assert {
        "idx_strategy_evaluations_decision_perspective",
        "idx_strategy_evaluations_execution_node",
        "idx_strategy_evaluations_symbol_rank",
    } <= indexes_by_table["strategy_hypothesis_evaluations"]

    foreign_keys = inspector.get_foreign_keys("strategy_hypothesis_evaluations")
    decisions_fk = next(
        foreign_key
        for foreign_key in foreign_keys
        if foreign_key["referred_table"] == "strategy_synthesis_decisions"
    )
    hypotheses_fk = next(
        foreign_key
        for foreign_key in foreign_keys
        if foreign_key["referred_table"] == "strategy_hypotheses"
    )
    assert decisions_fk["constrained_columns"] == ["decision_id"]
    assert decisions_fk["referred_columns"] == ["decision_id"]
    assert decisions_fk["options"] == {"ondelete": "CASCADE"}
    assert hypotheses_fk["constrained_columns"] == ["hypothesis_id"]
    assert hypotheses_fk["referred_columns"] == ["hypothesis_id"]
    assert hypotheses_fk["options"] == {"ondelete": "SET NULL"}
