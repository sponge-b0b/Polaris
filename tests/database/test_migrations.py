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


def test_backtest_domain_timestamp_migration_backfills_precedence(
    alembic_runner: MigrationContext,
    alembic_engine: object,
) -> None:
    import json
    from datetime import datetime
    from datetime import timezone

    from sqlalchemy import Engine
    from sqlalchemy import text

    engine = alembic_engine
    assert isinstance(engine, Engine)
    alembic_runner.migrate_up_before("e5f6a7b8c9d0")

    parent_completed_at = datetime(2026, 6, 25, 12, tzinfo=timezone.utc)
    legacy_timestamp = datetime(2026, 6, 24, 10, tzinfo=timezone.utc)
    legacy_created_at = datetime(2026, 6, 23, 9, tzinfo=timezone.utc)

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO backtest_scenarios (
                    scenario_id, name, workflow_name, start_date, end_date,
                    symbols, benchmark_symbol, initial_cash, provider_profile,
                    initial_positions, parameters, expected_outcomes, metadata
                ) VALUES (
                    'scenario-1', 'Scenario', 'morning_report', '2026-06-24',
                    '2026-06-25', '["SPY"]'::jsonb, 'SPY', 100000,
                    'backtest_synthetic', '[]'::jsonb, '{}'::jsonb, '[]'::jsonb,
                    '{}'::jsonb
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO backtest_runs (
                    backtest_run_id, scenario_id, workflow_name, status, success,
                    started_at, completed_at, metrics, metadata
                ) VALUES (
                    'run-1', 'scenario-1', 'morning_report', 'succeeded', true,
                    :started_at, :completed_at, '{}'::jsonb, '{}'::jsonb
                )
                """
            ),
            {
                "started_at": parent_completed_at,
                "completed_at": parent_completed_at,
            },
        )
        for record_id, metadata in (
            ("timestamp", {"timestamp": legacy_timestamp.isoformat()}),
            ("created-at", {"created_at": legacy_created_at.isoformat()}),
            ("parent", {"timestamp": "not-a-timestamp"}),
        ):
            connection.execute(
                text(
                    """
                    INSERT INTO backtest_metrics (
                        metric_id, backtest_run_id, metric_name, metric_value, metadata
                    ) VALUES (
                        :record_id, 'run-1', :record_id, 1, CAST(:metadata AS jsonb)
                    )
                    """
                ),
                {"record_id": record_id, "metadata": json.dumps(metadata)},
            )
            connection.execute(
                text(
                    """
                    INSERT INTO backtest_artifacts (
                        artifact_id, backtest_run_id, artifact_format, content,
                        mime_type, metadata
                    ) VALUES (
                        :record_id, 'run-1', :record_id, 'content', 'text/plain',
                        CAST(:metadata AS jsonb)
                    )
                    """
                ),
                {"record_id": record_id, "metadata": json.dumps(metadata)},
            )

    alembic_runner.migrate_up_to("e5f6a7b8c9d0")

    with engine.connect() as connection:
        metric_rows: dict[str, datetime] = {
            str(row.metric_id): row.recorded_at
            for row in connection.execute(
                text("SELECT metric_id, recorded_at FROM backtest_metrics")
            )
        }
        artifact_rows: dict[str, datetime] = {
            str(row.artifact_id): row.generated_at
            for row in connection.execute(
                text("SELECT artifact_id, generated_at FROM backtest_artifacts")
            )
        }

    expected = {
        "timestamp": legacy_timestamp,
        "created-at": legacy_created_at,
        "parent": parent_completed_at,
    }
    assert metric_rows == expected
    assert artifact_rows == expected


def test_rag_query_audit_migration_promotes_metadata_fields(
    alembic_runner: MigrationContext,
    alembic_engine: object,
) -> None:
    import json
    from datetime import datetime
    from datetime import timezone

    from sqlalchemy import Engine
    from sqlalchemy import text

    engine = alembic_engine
    assert isinstance(engine, Engine)
    alembic_runner.migrate_up_before("f6a7b8c9d0e1")

    started_at = datetime(2026, 6, 25, 13, tzinfo=timezone.utc)
    model_executions = [
        {
            "operation": f"operation-{index}",
            "configured_model": "qwen3.5:4b",
            "provider_name": "ollama",
            "duration_ms": float(index),
            "success": True,
        }
        for index in range(35)
    ]
    promoted_metadata = {
        "model_executions": model_executions,
        "context_count": 7,
        "citation_count": 4,
        "grounding_score": 0.83,
        "utility_score": 0.77,
        "injection_detected": True,
        "reflection_scores": {
            "retrieval_necessity": 0.9,
            "source_relevance": 0.8,
            "answer_support": 0.7,
            "usefulness": 0.6,
        },
        "corrective_actions": ["rewrite", "proceed"],
        "debug_note": "preserve me",
    }
    malformed_metadata = {
        "model_executions": {"not": "an array"},
        "context_count": -1,
        "citation_count": 1.5,
        "grounding_score": 1.5,
        "utility_score": "not-a-score",
        "injection_detected": "true",
        "reflection_scores": [],
        "corrective_actions": {},
        "debug_note": "also preserve me",
    }

    with engine.begin() as connection:
        for query_id, metadata in (
            ("query-promoted", promoted_metadata),
            ("query-malformed", malformed_metadata),
        ):
            connection.execute(
                text(
                    """
                    INSERT INTO rag_query_logs (
                        query_id, query_text, normalized_query, requester,
                        workflow_name, execution_id, retrieval_route, top_k,
                        filters, status, started_at, completed_at, duration_ms,
                        error, metadata
                    ) VALUES (
                        :query_id, 'What changed?', 'what changed', 'test',
                        'test_workflow', 'execution-1', 'retrieval', 5,
                        '{}'::jsonb, 'succeeded', :started_at, :started_at, 10.0,
                        NULL, CAST(:metadata AS jsonb)
                    )
                    """
                ),
                {
                    "query_id": query_id,
                    "started_at": started_at,
                    "metadata": json.dumps(metadata),
                },
            )

    alembic_runner.migrate_up_to("f6a7b8c9d0e1")

    with engine.connect() as connection:
        rows = {
            str(row.query_id): row
            for row in connection.execute(
                text(
                    """
                    SELECT query_id, model_executions, context_count,
                           citation_count, grounding_score, utility_score,
                           injection_detected, reflection_scores,
                           corrective_actions, metadata
                    FROM rag_query_logs
                    ORDER BY query_id
                    """
                )
            )
        }
        index_names = {
            str(row.indexname)
            for row in connection.execute(
                text(
                    """
                    SELECT indexname
                    FROM pg_indexes
                    WHERE schemaname = current_schema()
                      AND tablename = 'rag_query_logs'
                    """
                )
            )
        }

    promoted = rows["query-promoted"]
    assert promoted.model_executions == model_executions[:32]
    assert promoted.context_count == 7
    assert promoted.citation_count == 4
    assert promoted.grounding_score == 0.83
    assert promoted.utility_score == 0.77
    assert promoted.injection_detected is True
    assert promoted.reflection_scores == promoted_metadata["reflection_scores"]
    assert promoted.corrective_actions == ["rewrite", "proceed"]
    assert promoted.metadata == {"debug_note": "preserve me"}

    malformed = rows["query-malformed"]
    assert malformed.model_executions == []
    assert malformed.context_count == 0
    assert malformed.citation_count == 0
    assert malformed.grounding_score is None
    assert malformed.utility_score is None
    assert malformed.injection_detected is False
    assert malformed.reflection_scores == {}
    assert malformed.corrective_actions == []
    assert malformed.metadata == {"debug_note": "also preserve me"}

    assert {
        "idx_rag_query_logs_injection_detected_true",
        "idx_rag_query_logs_grounding_score",
        "idx_rag_query_logs_utility_score",
    } <= index_names
