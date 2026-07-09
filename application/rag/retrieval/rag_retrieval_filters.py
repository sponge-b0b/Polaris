from __future__ import annotations

from datetime import date
from datetime import datetime
from typing import cast

from application.rag.contracts.rag_context import RagRetrievalFilters
from application.rag.contracts.rag_request import RagRequest
from core.storage.persistence.rag import JsonObject
from core.storage.persistence.rag import JsonScalar


class RagRetrievalFilterEvaluator:
    """Build exact storage filters and evaluate remaining typed filters."""

    def exact_metadata_filters(
        self,
        request: RagRequest,
    ) -> JsonObject:
        filters = request.filters
        exact: dict[str, JsonScalar] = {}
        _add_single_value_filter(exact, "source_table", filters.source_tables)
        _add_single_value_filter(exact, "source_type", filters.source_types)
        _add_single_value_filter(exact, "symbol", filters.symbols)
        _add_optional_filter(
            exact,
            "workflow_name",
            filters.workflow_name or request.workflow_name,
        )
        _add_optional_filter(
            exact,
            "execution_id",
            filters.execution_id or request.execution_id,
        )
        _add_optional_filter(exact, "runtime_id", filters.runtime_id)
        _add_single_value_filter(exact, "agent_name", filters.agent_names)
        _add_single_value_filter(exact, "agent_type", filters.agent_types)
        _add_single_value_filter(exact, "report_type", filters.report_types)
        _add_single_value_filter(exact, "regime", filters.regimes)
        for key, value in filters.metadata.items():
            if _is_json_scalar(value):
                exact[key] = cast(JsonScalar, value)
        return cast(JsonObject, exact)

    def matches(
        self,
        metadata: JsonObject,
        filters: RagRetrievalFilters,
    ) -> bool:
        return (
            _matches_tuple_filter(metadata, "source_table", filters.source_tables)
            and _matches_tuple_filter(metadata, "source_type", filters.source_types)
            and _matches_tuple_filter(metadata, "symbol", filters.symbols)
            and _matches_optional_filter(
                metadata,
                "workflow_name",
                filters.workflow_name,
            )
            and _matches_optional_filter(
                metadata,
                "execution_id",
                filters.execution_id,
            )
            and _matches_optional_filter(metadata, "runtime_id", filters.runtime_id)
            and _matches_tuple_filter(metadata, "agent_name", filters.agent_names)
            and _matches_tuple_filter(metadata, "agent_type", filters.agent_types)
            and _matches_tuple_filter(metadata, "report_type", filters.report_types)
            and _matches_tuple_filter(metadata, "regime", filters.regimes)
            and _matches_as_of_range(metadata, filters)
            and _matches_metadata_filters(metadata, filters.metadata)
        )


def _add_single_value_filter(
    exact: dict[str, JsonScalar],
    key: str,
    values: tuple[str, ...],
) -> None:
    if len(values) == 1:
        exact[key] = values[0]


def _add_optional_filter(
    exact: dict[str, JsonScalar],
    key: str,
    value: str | None,
) -> None:
    if value is not None and value.strip():
        exact[key] = value.strip()


def _matches_tuple_filter(
    metadata: JsonObject,
    key: str,
    values: tuple[str, ...],
) -> bool:
    if not values:
        return True
    return _metadata_optional_str(metadata, key) in values


def _matches_optional_filter(
    metadata: JsonObject,
    key: str,
    value: str | None,
) -> bool:
    if value is None:
        return True
    return _metadata_optional_str(metadata, key) == value


def _matches_metadata_filters(
    metadata: JsonObject,
    filters: JsonObject,
) -> bool:
    return all(metadata.get(key) == expected for key, expected in filters.items())


def _matches_as_of_range(
    metadata: JsonObject,
    filters: RagRetrievalFilters,
) -> bool:
    if filters.as_of_start is None and filters.as_of_end is None:
        return True
    as_of = _metadata_date(metadata, "as_of_date") or _metadata_date(
        metadata,
        "created_at",
    )
    if as_of is None:
        return False
    if filters.as_of_start is not None and as_of < filters.as_of_start.date():
        return False
    if filters.as_of_end is not None and as_of > filters.as_of_end.date():
        return False
    return True


def _metadata_optional_str(
    metadata: JsonObject,
    key: str,
) -> str | None:
    value = metadata.get(key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _metadata_date(
    metadata: JsonObject,
    key: str,
) -> date | None:
    value = metadata.get(key)
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.strip()
    if len(normalized) == 10:
        return date.fromisoformat(normalized)
    return datetime.fromisoformat(normalized).date()


def _is_json_scalar(
    value: object,
) -> bool:
    return value is None or isinstance(value, str | int | float | bool)
