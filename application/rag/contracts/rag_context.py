from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from core.storage.persistence.rag import JsonObject


@dataclass(
    frozen=True,
    slots=True,
)
class RagRetrievalFilters:
    """
    Typed filters applied before RAG retrieval.

    These fields mirror persisted RAG chunk/document lineage so retrieval can
    filter first, retrieve second, and construct citations from canonical
    PostgreSQL-derived metadata.
    """

    source_tables: tuple[str, ...] = ()
    source_types: tuple[str, ...] = ()
    symbols: tuple[str, ...] = ()
    workflow_name: str | None = None
    execution_id: str | None = None
    runtime_id: str | None = None
    agent_names: tuple[str, ...] = ()
    agent_types: tuple[str, ...] = ()
    report_types: tuple[str, ...] = ()
    regimes: tuple[str, ...] = ()
    as_of_start: datetime | None = None
    as_of_end: datetime | None = None
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        for field_name in (
            "source_tables",
            "source_types",
            "symbols",
            "agent_names",
            "agent_types",
            "report_types",
            "regimes",
        ):
            object.__setattr__(
                self,
                field_name,
                _clean_tuple(
                    getattr(
                        self,
                        field_name,
                    ),
                ),
            )
        if (
            self.as_of_start is not None
            and self.as_of_end is not None
            and self.as_of_start > self.as_of_end
        ):
            raise ValueError("as_of_start cannot be after as_of_end.")

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "source_tables": list(self.source_tables),
            "source_types": list(self.source_types),
            "symbols": list(self.symbols),
            "workflow_name": self.workflow_name,
            "execution_id": self.execution_id,
            "runtime_id": self.runtime_id,
            "agent_names": list(self.agent_names),
            "agent_types": list(self.agent_types),
            "report_types": list(self.report_types),
            "regimes": list(self.regimes),
            "as_of_start": _datetime_to_string(
                self.as_of_start,
            ),
            "as_of_end": _datetime_to_string(
                self.as_of_end,
            ),
            "metadata": deepcopy(
                dict(self.metadata),
            ),
        }

    @classmethod
    def from_dict(
        cls,
        payload: Mapping[str, Any],
    ) -> RagRetrievalFilters:
        return cls(
            source_tables=_tuple_from_payload(
                payload,
                "source_tables",
            ),
            source_types=_tuple_from_payload(
                payload,
                "source_types",
            ),
            symbols=_tuple_from_payload(
                payload,
                "symbols",
            ),
            workflow_name=_optional_str(
                payload.get(
                    "workflow_name",
                )
            ),
            execution_id=_optional_str(
                payload.get(
                    "execution_id",
                )
            ),
            runtime_id=_optional_str(
                payload.get(
                    "runtime_id",
                )
            ),
            agent_names=_tuple_from_payload(
                payload,
                "agent_names",
            ),
            agent_types=_tuple_from_payload(
                payload,
                "agent_types",
            ),
            report_types=_tuple_from_payload(
                payload,
                "report_types",
            ),
            regimes=_tuple_from_payload(
                payload,
                "regimes",
            ),
            as_of_start=_datetime_from_payload(
                payload.get(
                    "as_of_start",
                )
            ),
            as_of_end=_datetime_from_payload(
                payload.get(
                    "as_of_end",
                )
            ),
            metadata=_json_object_from_payload(
                payload.get(
                    "metadata",
                )
            ),
        )


@dataclass(
    frozen=True,
    slots=True,
)
class RagSource:
    """
    Typed source/citation lineage for a retrieved RAG context.
    """

    source_table: str
    source_id: str
    source_type: str
    document_id: str
    title: str
    chunk_id: str | None = None
    section_name: str | None = None
    generated_at: datetime | None = None
    workflow_name: str | None = None
    execution_id: str | None = None
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        for field_name in (
            "source_table",
            "source_id",
            "source_type",
            "document_id",
            "title",
        ):
            _require_non_empty(
                getattr(
                    self,
                    field_name,
                ),
                field_name,
            )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "source_table": self.source_table,
            "source_id": self.source_id,
            "source_type": self.source_type,
            "document_id": self.document_id,
            "title": self.title,
            "chunk_id": self.chunk_id,
            "section_name": self.section_name,
            "generated_at": _datetime_to_string(
                self.generated_at,
            ),
            "workflow_name": self.workflow_name,
            "execution_id": self.execution_id,
            "metadata": deepcopy(
                dict(self.metadata),
            ),
        }

    @classmethod
    def from_dict(
        cls,
        payload: Mapping[str, Any],
    ) -> RagSource:
        return cls(
            source_table=_required_str(
                payload,
                "source_table",
            ),
            source_id=_required_str(
                payload,
                "source_id",
            ),
            source_type=_required_str(
                payload,
                "source_type",
            ),
            document_id=_required_str(
                payload,
                "document_id",
            ),
            title=_required_str(
                payload,
                "title",
            ),
            chunk_id=_optional_str(
                payload.get(
                    "chunk_id",
                )
            ),
            section_name=_optional_str(
                payload.get(
                    "section_name",
                )
            ),
            generated_at=_datetime_from_payload(
                payload.get(
                    "generated_at",
                )
            ),
            workflow_name=_optional_str(
                payload.get(
                    "workflow_name",
                )
            ),
            execution_id=_optional_str(
                payload.get(
                    "execution_id",
                )
            ),
            metadata=_json_object_from_payload(
                payload.get(
                    "metadata",
                )
            ),
        )


@dataclass(
    frozen=True,
    slots=True,
)
class RagRetrievedContext:
    """
    Typed retrieval result consumed by secure generation and citation builders.
    """

    context_id: str
    text: str
    source: RagSource
    score: float
    rank: int
    retrieval_route: str
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        _require_non_empty(
            self.context_id,
            "context_id",
        )
        _require_non_empty(
            self.text,
            "text",
        )
        _require_non_empty(
            self.retrieval_route,
            "retrieval_route",
        )
        if self.rank < 0:
            raise ValueError("rank cannot be negative.")

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "context_id": self.context_id,
            "text": self.text,
            "source": self.source.to_dict(),
            "score": self.score,
            "rank": self.rank,
            "retrieval_route": self.retrieval_route,
            "metadata": deepcopy(
                dict(self.metadata),
            ),
        }

    @classmethod
    def from_dict(
        cls,
        payload: Mapping[str, Any],
    ) -> RagRetrievedContext:
        return cls(
            context_id=_required_str(
                payload,
                "context_id",
            ),
            text=_required_str(
                payload,
                "text",
            ),
            source=RagSource.from_dict(
                _mapping_from_payload(
                    payload,
                    "source",
                )
            ),
            score=float(
                payload.get(
                    "score",
                    0.0,
                )
            ),
            rank=int(
                payload.get(
                    "rank",
                    0,
                )
            ),
            retrieval_route=_required_str(
                payload,
                "retrieval_route",
            ),
            metadata=_json_object_from_payload(
                payload.get(
                    "metadata",
                )
            ),
        )


def _clean_tuple(
    values: tuple[str, ...],
) -> tuple[str, ...]:
    return tuple(value.strip() for value in values if value.strip())


def _tuple_from_payload(
    payload: Mapping[str, Any],
    key: str,
) -> tuple[str, ...]:
    value = payload.get(
        key,
        (),
    )
    if value is None:
        return ()
    if isinstance(
        value,
        str,
    ):
        return _clean_tuple(
            (value,),
        )
    return _clean_tuple(
        tuple(str(item) for item in value),
    )


def _datetime_to_string(
    value: datetime | None,
) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _datetime_from_payload(
    value: object,
) -> datetime | None:
    if value is None:
        return None
    if isinstance(
        value,
        datetime,
    ):
        return value
    if isinstance(
        value,
        str,
    ):
        return datetime.fromisoformat(
            value,
        )
    raise TypeError("datetime payload values must be ISO strings or datetime objects.")


def _required_str(
    payload: Mapping[str, Any],
    key: str,
) -> str:
    value = payload.get(
        key,
    )
    if not isinstance(
        value,
        str,
    ):
        raise TypeError(f"{key} must be a string.")
    _require_non_empty(
        value,
        key,
    )
    return value


def _optional_str(
    value: object,
) -> str | None:
    if value is None:
        return None
    if not isinstance(
        value,
        str,
    ):
        raise TypeError("optional string payload values must be strings or None.")
    if not value.strip():
        return None
    return value


def _mapping_from_payload(
    payload: Mapping[str, Any],
    key: str,
) -> Mapping[str, Any]:
    value = payload.get(
        key,
    )
    if not isinstance(
        value,
        Mapping,
    ):
        raise TypeError(f"{key} must be an object.")
    return value


def _json_object_from_payload(
    value: object,
) -> JsonObject:
    if value is None:
        return {}
    if not isinstance(
        value,
        Mapping,
    ):
        raise TypeError("metadata payload values must be objects.")
    return dict(value)


def _require_non_empty(
    value: str | None,
    field_name: str,
) -> None:
    if value is None or not value.strip():
        raise ValueError(f"{field_name} cannot be empty.")
