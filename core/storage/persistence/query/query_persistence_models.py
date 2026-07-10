from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from enum import Enum
from typing import Generic
from typing import Mapping
from typing import Sequence
from typing import TypeAlias
from typing import TypeVar

from core.storage.persistence.lineage import clean_optional_identifier

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | Mapping[str, "JsonValue"] | Sequence["JsonValue"]
JsonObject: TypeAlias = Mapping[str, JsonValue]

TRecord = TypeVar("TRecord")

DEFAULT_QUERY_LIMIT = 100
DEFAULT_MAX_QUERY_LIMIT = 1000


class PersistenceSortDirection(str, Enum):
    """
    Stable sort directions for persistence read/query boundaries.
    """

    ASC = "asc"
    DESC = "desc"


@dataclass(
    frozen=True,
    slots=True,
)
class PersistencePagination:
    """
    Reusable limit/offset pagination contract for persistence reads.
    """

    limit: int = DEFAULT_QUERY_LIMIT
    offset: int = 0
    max_limit: int = DEFAULT_MAX_QUERY_LIMIT

    def __post_init__(
        self,
    ) -> None:
        _require_positive_integer(
            self.max_limit,
            "max_limit",
        )
        _require_positive_integer(
            self.limit,
            "limit",
        )
        _require_non_negative_integer(
            self.offset,
            "offset",
        )
        if self.limit > self.max_limit:
            raise ValueError("limit cannot exceed max_limit.")

    @property
    def next_offset(
        self,
    ) -> int:
        return self.offset + self.limit

    def as_dict(
        self,
    ) -> dict[str, int]:
        return {
            "limit": self.limit,
            "offset": self.offset,
            "max_limit": self.max_limit,
        }


@dataclass(
    frozen=True,
    slots=True,
)
class PersistenceSort:
    """
    Reusable sort contract for persistence reads.
    """

    field_name: str = "timestamp"
    direction: PersistenceSortDirection | str = PersistenceSortDirection.DESC

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "field_name",
            _require_non_empty(
                self.field_name,
                "field_name",
            ),
        )
        object.__setattr__(
            self,
            "direction",
            _coerce_sort_direction(
                self.direction,
            ),
        )

    def as_dict(
        self,
    ) -> dict[str, str]:
        direction = self.direction
        if isinstance(
            direction,
            str,
        ):
            direction_value = direction
        else:
            direction_value = direction.value
        return {
            "field_name": self.field_name,
            "direction": direction_value,
        }


@dataclass(
    frozen=True,
    slots=True,
)
class PersistenceTimeRange:
    """
    Reusable timestamp range contract for persistence reads.
    """

    start: datetime | None = None
    end: datetime | None = None

    def __post_init__(
        self,
    ) -> None:
        if self.start is not None and self.end is not None and self.end < self.start:
            raise ValueError("end cannot be earlier than start.")

    @property
    def is_empty(
        self,
    ) -> bool:
        return self.start is None and self.end is None

    def as_dict(
        self,
    ) -> dict[str, datetime]:
        values: dict[str, datetime] = {}
        if self.start is not None:
            values["start"] = self.start
        if self.end is not None:
            values["end"] = self.end
        return values


@dataclass(
    frozen=True,
    slots=True,
)
class PersistenceLineageQuery:
    """
    Shared workflow/runtime lineage filters for persistence reads.
    """

    workflow_name: str | None = None
    execution_id: str | None = None
    runtime_id: str | None = None
    node_name: str | None = None

    def __post_init__(
        self,
    ) -> None:
        for field_name in (
            "workflow_name",
            "execution_id",
            "runtime_id",
            "node_name",
        ):
            object.__setattr__(
                self,
                field_name,
                clean_optional_identifier(
                    getattr(
                        self,
                        field_name,
                    ),
                    field_name,
                ),
            )

    @property
    def is_empty(
        self,
    ) -> bool:
        return not self.as_dict()

    def as_dict(
        self,
    ) -> dict[str, str]:
        return _omit_none_str(
            {
                "workflow_name": self.workflow_name,
                "execution_id": self.execution_id,
                "runtime_id": self.runtime_id,
                "node_name": self.node_name,
            }
        )


@dataclass(
    frozen=True,
    slots=True,
)
class PersistenceSourceQuery:
    """
    Shared external/source-record filters for persistence reads.
    """

    source_type: str | None = None
    source_id: str | None = None
    source_table: str | None = None

    def __post_init__(
        self,
    ) -> None:
        for field_name in (
            "source_type",
            "source_id",
            "source_table",
        ):
            object.__setattr__(
                self,
                field_name,
                clean_optional_identifier(
                    getattr(
                        self,
                        field_name,
                    ),
                    field_name,
                ),
            )

    @property
    def is_empty(
        self,
    ) -> bool:
        return not self.as_dict()

    def as_dict(
        self,
    ) -> dict[str, str]:
        return _omit_none_str(
            {
                "source_type": self.source_type,
                "source_id": self.source_id,
                "source_table": self.source_table,
            }
        )


@dataclass(
    frozen=True,
    slots=True,
)
class PersistenceSymbolQuery:
    """
    Shared symbol/universe filters for persistence reads.
    """

    symbol: str | None = None
    symbols: tuple[str, ...] = ()

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "symbol",
            _clean_optional_symbol(
                self.symbol,
                "symbol",
            ),
        )
        object.__setattr__(
            self,
            "symbols",
            _normalize_symbols(
                self.symbols,
            ),
        )

    @property
    def all_symbols(
        self,
    ) -> tuple[str, ...]:
        values: list[str] = []
        if self.symbol is not None:
            values.append(
                self.symbol,
            )
        values.extend(
            self.symbols,
        )
        return _dedupe_preserving_order(
            values,
        )

    @property
    def is_empty(
        self,
    ) -> bool:
        return not self.all_symbols

    def as_dict(
        self,
    ) -> dict[str, str | tuple[str, ...]]:
        values: dict[str, str | tuple[str, ...]] = {}
        if self.symbol is not None:
            values["symbol"] = self.symbol
        if self.symbols:
            values["symbols"] = self.symbols
        return values


@dataclass(
    frozen=True,
    slots=True,
)
class PersistenceAccountQuery:
    """
    Shared account filter for portfolio/account-scoped persistence reads.
    """

    account_id: str | None = None

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "account_id",
            clean_optional_identifier(
                self.account_id,
                "account_id",
            ),
        )

    @property
    def is_empty(
        self,
    ) -> bool:
        return self.account_id is None

    def as_dict(
        self,
    ) -> dict[str, str]:
        return _omit_none_str(
            {
                "account_id": self.account_id,
            }
        )


@dataclass(
    frozen=True,
    slots=True,
)
class PersistenceCommonQuery:
    """
    Composable common query contract for application persistence services.
    """

    lineage: PersistenceLineageQuery = field(default_factory=PersistenceLineageQuery)
    source: PersistenceSourceQuery = field(default_factory=PersistenceSourceQuery)
    symbols: PersistenceSymbolQuery = field(default_factory=PersistenceSymbolQuery)
    account: PersistenceAccountQuery = field(default_factory=PersistenceAccountQuery)
    time_range: PersistenceTimeRange = field(default_factory=PersistenceTimeRange)
    pagination: PersistencePagination = field(default_factory=PersistencePagination)
    sort: PersistenceSort = field(default_factory=PersistenceSort)
    metadata: JsonObject = field(default_factory=dict)

    def as_dict(
        self,
    ) -> dict[str, object]:
        return {
            "lineage": self.lineage.as_dict(),
            "source": self.source.as_dict(),
            "symbols": self.symbols.as_dict(),
            "account": self.account.as_dict(),
            "time_range": self.time_range.as_dict(),
            "pagination": self.pagination.as_dict(),
            "sort": self.sort.as_dict(),
            "metadata": dict(
                self.metadata,
            ),
        }


def _coerce_sort_direction(
    direction: PersistenceSortDirection | str,
) -> PersistenceSortDirection:
    if isinstance(
        direction,
        PersistenceSortDirection,
    ):
        return direction

    normalized = direction.strip().lower()
    try:
        return PersistenceSortDirection(
            normalized,
        )
    except ValueError as exc:
        raise ValueError("direction must be 'asc' or 'desc'.") from exc


def _require_non_empty(
    value: str | None,
    field_name: str,
) -> str:
    if value is None:
        raise ValueError(f"{field_name} cannot be empty.")
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{field_name} cannot be empty.")
    return stripped


def _require_positive_integer(
    value: int,
    field_name: str,
) -> None:
    if (
        isinstance(
            value,
            bool,
        )
        or value <= 0
    ):
        raise ValueError(f"{field_name} must be positive.")


def _require_non_negative_integer(
    value: int,
    field_name: str,
) -> None:
    if (
        isinstance(
            value,
            bool,
        )
        or value < 0
    ):
        raise ValueError(f"{field_name} cannot be negative.")


def _clean_optional_symbol(
    value: str | None,
    field_name: str,
) -> str | None:
    cleaned = clean_optional_identifier(
        value,
        field_name,
    )
    if cleaned is None:
        return None
    return cleaned.upper()


def _normalize_symbols(
    values: Sequence[str],
) -> tuple[str, ...]:
    normalized: list[str] = []
    for index, value in enumerate(
        values,
    ):
        symbol = _clean_optional_symbol(
            value,
            f"symbols[{index}]",
        )
        if symbol is None:
            raise ValueError(f"symbols[{index}] cannot be empty.")
        normalized.append(
            symbol,
        )
    return _dedupe_preserving_order(
        normalized,
    )


def _dedupe_preserving_order(
    values: Sequence[str],
) -> tuple[str, ...]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(
            value,
        )
        deduped.append(
            value,
        )
    return tuple(
        deduped,
    )


def _omit_none_str(
    values: Mapping[str, str | None],
) -> dict[str, str]:
    return {key: value for key, value in values.items() if value is not None}


@dataclass(
    frozen=True,
    slots=True,
)
class PersistenceReadResult(Generic[TRecord]):
    """
    Typed envelope for single-record persistence reads.

    The record remains strongly typed. Boundary serialization is intentionally
    limited to query metadata so callers do not coerce domain records to raw
    dictionaries inside the platform.
    """

    record: TRecord | None
    query: PersistenceCommonQuery | None = None
    metadata: JsonObject = field(default_factory=dict)

    @property
    def found(
        self,
    ) -> bool:
        return self.record is not None

    def metadata_dict(
        self,
    ) -> dict[str, object]:
        values: dict[str, object] = {
            "found": self.found,
            "metadata": dict(
                self.metadata,
            ),
        }
        if self.query is not None:
            values["query"] = self.query.as_dict()
        return values


@dataclass(
    frozen=True,
    slots=True,
)
class PersistenceListResult(Generic[TRecord]):
    """
    Typed envelope for list persistence reads with pagination metadata.
    """

    records: tuple[TRecord, ...] = ()
    total_count: int | None = None
    pagination: PersistencePagination = field(default_factory=PersistencePagination)
    sort: PersistenceSort = field(default_factory=PersistenceSort)
    query: PersistenceCommonQuery | None = None
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "records",
            tuple(
                self.records,
            ),
        )
        if self.total_count is not None:
            _require_non_negative_integer(
                self.total_count,
                "total_count",
            )
            if self.total_count < len(
                self.records,
            ):
                raise ValueError("total_count cannot be less than records returned.")

    @property
    def returned_count(
        self,
    ) -> int:
        return len(
            self.records,
        )

    @property
    def has_more(
        self,
    ) -> bool:
        if self.total_count is not None:
            return self.pagination.offset + self.returned_count < self.total_count
        return self.returned_count == self.pagination.limit

    def page_metadata(
        self,
    ) -> dict[str, object]:
        values: dict[str, object] = {
            "returned_count": self.returned_count,
            "total_count": self.total_count,
            "has_more": self.has_more,
            "pagination": self.pagination.as_dict(),
            "sort": self.sort.as_dict(),
            "metadata": dict(
                self.metadata,
            ),
        }
        if self.query is not None:
            values["query"] = self.query.as_dict()
        return values
