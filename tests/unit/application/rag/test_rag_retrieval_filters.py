from __future__ import annotations

from datetime import datetime
from datetime import timezone

from application.rag.contracts.rag_context import RagRetrievalFilters
from application.rag.contracts.rag_request import RagRequest
from application.rag.retrieval.rag_retrieval_filters import RagRetrievalFilterEvaluator


def test_filter_evaluator_splits_exact_storage_and_in_memory_filters() -> None:
    evaluator = RagRetrievalFilterEvaluator()
    request = RagRequest(
        query="risk",
        workflow_name="morning_report",
        execution_id="execution-1",
        filters=RagRetrievalFilters(
            source_types=("report",),
            symbols=("SPY", "QQQ"),
            regimes=("risk_off",),
            metadata={"tenant": "primary", "nested": {"ignored": True}},
        ),
    )

    assert evaluator.exact_metadata_filters(request) == {
        "source_type": "report",
        "workflow_name": "morning_report",
        "execution_id": "execution-1",
        "regime": "risk_off",
        "tenant": "primary",
    }


def test_filter_evaluator_preserves_temporal_and_tuple_matching_policy() -> None:
    evaluator = RagRetrievalFilterEvaluator()
    filters = RagRetrievalFilters(
        symbols=("SPY", "QQQ"),
        as_of_start=datetime(2026, 6, 10, tzinfo=timezone.utc),
        as_of_end=datetime(2026, 6, 20, tzinfo=timezone.utc),
    )

    assert evaluator.matches(
        {"symbol": "SPY", "as_of_date": "2026-06-15"},
        filters,
    )
    assert not evaluator.matches(
        {"symbol": "IWM", "as_of_date": "2026-06-15"},
        filters,
    )
    assert not evaluator.matches(
        {"symbol": "SPY", "as_of_date": "2026-06-21"},
        filters,
    )
    assert not evaluator.matches({"symbol": "SPY"}, filters)
