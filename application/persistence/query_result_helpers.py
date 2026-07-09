from __future__ import annotations

from collections.abc import Mapping
from collections.abc import Sequence
from datetime import datetime
from typing import TypeAlias
from typing import TypeVar

from core.storage.persistence.query import PersistenceAccountQuery
from core.storage.persistence.query import PersistenceCommonQuery
from core.storage.persistence.query import PersistenceLineageQuery
from core.storage.persistence.query import PersistenceListResult
from core.storage.persistence.query import PersistenceSymbolQuery
from core.storage.persistence.query import PersistenceTimeRange

MetadataScalar: TypeAlias = str | int | float | bool | None
TRecord = TypeVar("TRecord")


def build_common_query(
    *,
    record_type: str,
    source: str | None = None,
    symbol: str | None = None,
    account_id: str | None = None,
    workflow_name: str | None = None,
    execution_id: str | None = None,
    runtime_id: str | None = None,
    node_name: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    metadata: Mapping[str, MetadataScalar] | None = None,
) -> PersistenceCommonQuery:
    """
    Build the shared persistence query envelope from application filters.

    Domain-specific filters remain on their typed service filter classes. Values
    without a shared primitive are kept as query metadata so callers can inspect
    the read boundary without weakening internal record typing.
    """

    query_metadata: dict[str, MetadataScalar] = {
        "record_type": record_type,
    }
    if source is not None:
        query_metadata["source"] = source
    if metadata is not None:
        query_metadata.update(
            {key: value for key, value in metadata.items() if value is not None}
        )

    return PersistenceCommonQuery(
        lineage=PersistenceLineageQuery(
            workflow_name=workflow_name,
            execution_id=execution_id,
            runtime_id=runtime_id,
            node_name=node_name,
        ),
        symbols=PersistenceSymbolQuery(
            symbol=symbol,
        ),
        account=PersistenceAccountQuery(
            account_id=account_id,
        ),
        time_range=PersistenceTimeRange(
            start=start,
            end=end,
        ),
        metadata=query_metadata,
    )


def build_list_result(
    records: Sequence[TRecord],
    *,
    query: PersistenceCommonQuery,
) -> PersistenceListResult[TRecord]:
    record_tuple = tuple(
        records,
    )
    return PersistenceListResult(
        records=record_tuple,
        total_count=len(
            record_tuple,
        ),
        pagination=query.pagination,
        sort=query.sort,
        query=query,
    )
