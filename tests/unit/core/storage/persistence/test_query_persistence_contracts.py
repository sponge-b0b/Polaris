from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime
from datetime import timezone

import pytest

from core.storage.persistence.query import PersistenceAccountQuery
from core.storage.persistence.query import PersistenceCommonQuery
from core.storage.persistence.query import PersistenceLineageQuery
from core.storage.persistence.query import PersistenceListResult
from core.storage.persistence.query import PersistenceReadResult
from core.storage.persistence.query import PersistencePagination
from core.storage.persistence.query import PersistenceSort
from core.storage.persistence.query import PersistenceSortDirection
from core.storage.persistence.query import PersistenceSourceQuery
from core.storage.persistence.query import PersistenceSymbolQuery
from core.storage.persistence.query import PersistenceTimeRange


def test_pagination_validates_limits_and_offsets() -> None:
    pagination = PersistencePagination(
        limit=50,
        offset=25,
        max_limit=100,
    )

    assert pagination.next_offset == 75
    assert pagination.as_dict() == {
        "limit": 50,
        "offset": 25,
        "max_limit": 100,
    }

    with pytest.raises(ValueError, match="limit"):
        PersistencePagination(limit=0)

    with pytest.raises(ValueError, match="offset"):
        PersistencePagination(offset=-1)

    with pytest.raises(ValueError, match="max_limit"):
        PersistencePagination(max_limit=0)

    with pytest.raises(ValueError, match="limit cannot exceed max_limit"):
        PersistencePagination(
            limit=101,
            max_limit=100,
        )


def test_sort_normalizes_direction_and_is_immutable() -> None:
    sort = PersistenceSort(
        field_name=" generated_at ",
        direction="ASC",
    )

    assert sort.field_name == "generated_at"
    assert sort.direction is PersistenceSortDirection.ASC
    assert sort.as_dict() == {
        "field_name": "generated_at",
        "direction": "asc",
    }

    with pytest.raises(ValueError, match="field_name"):
        PersistenceSort(field_name=" ")

    with pytest.raises(ValueError, match="direction"):
        PersistenceSort(direction="newest")

    with pytest.raises(FrozenInstanceError):
        sort.field_name = "updated_at"  # type: ignore[misc]


def test_time_range_validates_order_and_omits_empty_values() -> None:
    start = datetime(2026, 6, 1, 9, tzinfo=timezone.utc)
    end = datetime(2026, 6, 1, 10, tzinfo=timezone.utc)

    time_range = PersistenceTimeRange(
        start=start,
        end=end,
    )

    assert not time_range.is_empty
    assert time_range.as_dict() == {
        "start": start,
        "end": end,
    }
    assert PersistenceTimeRange().is_empty

    with pytest.raises(ValueError, match="end"):
        PersistenceTimeRange(
            start=end,
            end=start,
        )


def test_lineage_source_and_account_queries_normalize_identifiers() -> None:
    lineage = PersistenceLineageQuery(
        workflow_name=" morning_report ",
        execution_id=" exec-1 ",
        runtime_id=" ",
        node_name=None,
    )
    source = PersistenceSourceQuery(
        source_type=" report ",
        source_id=" report-1 ",
        source_table=" reports ",
    )
    account = PersistenceAccountQuery(
        account_id=" account-1 ",
    )

    assert lineage.as_dict() == {
        "workflow_name": "morning_report",
        "execution_id": "exec-1",
    }
    assert source.as_dict() == {
        "source_type": "report",
        "source_id": "report-1",
        "source_table": "reports",
    }
    assert account.as_dict() == {"account_id": "account-1"}
    assert PersistenceLineageQuery().is_empty
    assert PersistenceSourceQuery().is_empty
    assert PersistenceAccountQuery().is_empty


def test_symbol_query_normalizes_uppercase_and_deduplicates() -> None:
    query = PersistenceSymbolQuery(
        symbol=" aapl ",
        symbols=(
            "MSFT",
            " aapl ",
            "msft",
        ),
    )

    assert query.symbol == "AAPL"
    assert query.symbols == (
        "MSFT",
        "AAPL",
    )
    assert query.all_symbols == (
        "AAPL",
        "MSFT",
    )
    assert query.as_dict() == {
        "symbol": "AAPL",
        "symbols": (
            "MSFT",
            "AAPL",
        ),
    }

    with pytest.raises(ValueError, match=r"symbols\[0\]"):
        PersistenceSymbolQuery(
            symbols=(" ",),
        )


def test_common_query_composes_reusable_filters() -> None:
    query = PersistenceCommonQuery(
        lineage=PersistenceLineageQuery(
            workflow_name="morning_report",
        ),
        source=PersistenceSourceQuery(
            source_type="provider",
            source_id="fmp",
        ),
        symbols=PersistenceSymbolQuery(
            symbol="spy",
        ),
        account=PersistenceAccountQuery(
            account_id="paper",
        ),
        time_range=PersistenceTimeRange(
            start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        ),
        pagination=PersistencePagination(
            limit=10,
        ),
        sort=PersistenceSort(
            field_name="created_at",
            direction=PersistenceSortDirection.DESC,
        ),
        metadata={"request_id": "request-1"},
    )

    assert query.as_dict() == {
        "lineage": {"workflow_name": "morning_report"},
        "source": {
            "source_type": "provider",
            "source_id": "fmp",
        },
        "symbols": {"symbol": "SPY"},
        "account": {"account_id": "paper"},
        "time_range": {"start": datetime(2026, 6, 1, tzinfo=timezone.utc)},
        "pagination": {
            "limit": 10,
            "offset": 0,
            "max_limit": 1000,
        },
        "sort": {
            "field_name": "created_at",
            "direction": "desc",
        },
        "metadata": {"request_id": "request-1"},
    }


def test_read_result_preserves_typed_record_and_metadata() -> None:
    query = PersistenceCommonQuery(
        lineage=PersistenceLineageQuery(
            execution_id="exec-1",
        ),
    )
    result = PersistenceReadResult[str](
        record="record-1",
        query=query,
        metadata={"request_id": "request-1"},
    )
    missing = PersistenceReadResult[str](
        record=None,
    )

    assert result.found is True
    assert result.record == "record-1"
    assert result.metadata_dict() == {
        "found": True,
        "metadata": {"request_id": "request-1"},
        "query": query.as_dict(),
    }
    assert missing.found is False
    assert missing.metadata_dict() == {
        "found": False,
        "metadata": {},
    }


def test_list_result_preserves_typed_records_and_pagination_metadata() -> None:
    query = PersistenceCommonQuery(
        symbols=PersistenceSymbolQuery(
            symbol="aapl",
        ),
        pagination=PersistencePagination(
            limit=2,
            offset=2,
        ),
    )
    pagination = PersistencePagination(
        limit=2,
        offset=2,
    )
    sort = PersistenceSort(
        field_name="generated_at",
        direction="desc",
    )
    result = PersistenceListResult[str](
        records=(
            "record-3",
            "record-4",
        ),
        total_count=5,
        pagination=pagination,
        sort=sort,
        query=query,
        metadata={"source": "unit-test"},
    )

    assert result.records == (
        "record-3",
        "record-4",
    )
    assert result.returned_count == 2
    assert result.has_more is True
    assert result.page_metadata() == {
        "returned_count": 2,
        "total_count": 5,
        "has_more": True,
        "pagination": pagination.as_dict(),
        "sort": sort.as_dict(),
        "metadata": {"source": "unit-test"},
        "query": query.as_dict(),
    }


def test_list_result_validates_total_count_and_infers_unknown_has_more() -> None:
    full_page = PersistenceListResult[str](
        records=(
            "record-1",
            "record-2",
        ),
        pagination=PersistencePagination(
            limit=2,
        ),
    )
    partial_page = PersistenceListResult[str](
        records=("record-1",),
        pagination=PersistencePagination(
            limit=2,
        ),
    )

    assert full_page.has_more is True
    assert partial_page.has_more is False

    with pytest.raises(ValueError, match="total_count"):
        PersistenceListResult[str](
            records=(
                "record-1",
                "record-2",
            ),
            total_count=1,
        )

    with pytest.raises(ValueError, match="total_count"):
        PersistenceListResult[str](
            total_count=-1,
        )
