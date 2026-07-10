from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Sequence

from core.storage.persistence.lineage.lineage_persistence_models import (
    PersistenceLineageLinkRecord,
)
from core.storage.persistence.lineage.lineage_persistence_models import (
    PersistenceRecordIdentity,
)
from core.storage.persistence.lineage.lineage_persistence_models import (
    require_non_empty_identifier,
)

DEFAULT_LINEAGE_TRAVERSAL_DEPTH = 3
DEFAULT_LINEAGE_TRAVERSAL_EDGE_LIMIT = 250


class PersistenceLineageTraversalDirection(str, Enum):
    """
    Direction for traversing persisted cross-record lineage links.

    ``DOWNSTREAM`` follows existing lineage links from source record to target
    record. ``UPSTREAM`` follows existing lineage links from target record back
    to source record.
    """

    UPSTREAM = "upstream"
    DOWNSTREAM = "downstream"


@dataclass(
    frozen=True,
    slots=True,
)
class PersistenceLineageTraversalRequest:
    """
    Bounded traversal request rooted at a persisted record identity.
    """

    root_record: PersistenceRecordIdentity
    direction: PersistenceLineageTraversalDirection | str
    max_depth: int = DEFAULT_LINEAGE_TRAVERSAL_DEPTH
    max_edges: int = DEFAULT_LINEAGE_TRAVERSAL_EDGE_LIMIT
    relationship_types: tuple[str, ...] = ()

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "direction",
            _coerce_traversal_direction(
                self.direction,
            ),
        )
        _require_non_negative_integer(
            self.max_depth,
            "max_depth",
        )
        _require_positive_integer(
            self.max_edges,
            "max_edges",
        )
        object.__setattr__(
            self,
            "relationship_types",
            _normalize_relationship_types(
                self.relationship_types,
            ),
        )

    @property
    def is_upstream(
        self,
    ) -> bool:
        return self.direction == PersistenceLineageTraversalDirection.UPSTREAM

    @property
    def is_downstream(
        self,
    ) -> bool:
        return self.direction == PersistenceLineageTraversalDirection.DOWNSTREAM

    def as_dict(
        self,
    ) -> dict[str, object]:
        direction = self.direction
        direction_value = direction if isinstance(direction, str) else direction.value
        return {
            "root_record": self.root_record.as_dict(),
            "direction": direction_value,
            "max_depth": self.max_depth,
            "max_edges": self.max_edges,
            "relationship_types": self.relationship_types,
        }


@dataclass(
    frozen=True,
    slots=True,
)
class PersistenceLineagePathSegment:
    """
    One traversed lineage edge within a bounded lineage path.
    """

    depth: int
    from_record: PersistenceRecordIdentity
    to_record: PersistenceRecordIdentity
    link: PersistenceLineageLinkRecord

    def __post_init__(
        self,
    ) -> None:
        _require_positive_integer(
            self.depth,
            "depth",
        )
        if self.from_record == self.to_record:
            raise ValueError(
                "lineage path segments cannot traverse to the same record identity."
            )
        if not self.is_forward_link and not self.is_reverse_link:
            raise ValueError(
                "lineage path segment endpoints must match the lineage link endpoints."
            )

    @property
    def is_forward_link(
        self,
    ) -> bool:
        return (
            self.from_record == self.link.source_record
            and self.to_record == self.link.target_record
        )

    @property
    def is_reverse_link(
        self,
    ) -> bool:
        return (
            self.from_record == self.link.target_record
            and self.to_record == self.link.source_record
        )

    def as_dict(
        self,
    ) -> dict[str, object]:
        return {
            "depth": self.depth,
            "from_record": self.from_record.as_dict(),
            "to_record": self.to_record.as_dict(),
            "link_id": self.link.link_id,
            "relationship_type": self.link.relationship_type,
            "source_record": self.link.source_record.as_dict(),
            "target_record": self.link.target_record.as_dict(),
        }


@dataclass(
    frozen=True,
    slots=True,
)
class PersistenceLineagePath:
    """
    Typed lineage path from the traversal root to a terminal record.
    """

    root_record: PersistenceRecordIdentity
    direction: PersistenceLineageTraversalDirection | str
    segments: tuple[PersistenceLineagePathSegment, ...] = ()

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "direction",
            _coerce_traversal_direction(
                self.direction,
            ),
        )
        object.__setattr__(
            self,
            "segments",
            tuple(
                self.segments,
            ),
        )
        self._validate_path_contiguity()

    @property
    def depth(
        self,
    ) -> int:
        return len(
            self.segments,
        )

    @property
    def terminal_record(
        self,
    ) -> PersistenceRecordIdentity:
        if not self.segments:
            return self.root_record
        return self.segments[-1].to_record

    @property
    def records(
        self,
    ) -> tuple[PersistenceRecordIdentity, ...]:
        values: list[PersistenceRecordIdentity] = [
            self.root_record,
        ]
        values.extend(segment.to_record for segment in self.segments)
        return tuple(
            values,
        )

    def as_dict(
        self,
    ) -> dict[str, object]:
        direction = self.direction
        direction_value = direction if isinstance(direction, str) else direction.value
        return {
            "root_record": self.root_record.as_dict(),
            "terminal_record": self.terminal_record.as_dict(),
            "direction": direction_value,
            "depth": self.depth,
            "segments": tuple(segment.as_dict() for segment in self.segments),
        }

    def _validate_path_contiguity(
        self,
    ) -> None:
        current_record = self.root_record
        for expected_depth, segment in enumerate(
            self.segments,
            start=1,
        ):
            if segment.depth != expected_depth:
                raise ValueError(
                    "lineage path segment depth must be contiguous from the root."
                )
            if segment.from_record != current_record:
                raise ValueError(
                    "lineage path segments must be contiguous from the root record."
                )
            if self.direction == PersistenceLineageTraversalDirection.DOWNSTREAM:
                if not segment.is_forward_link:
                    raise ValueError(
                        "downstream lineage paths must follow source-to-target links."
                    )
            if self.direction == PersistenceLineageTraversalDirection.UPSTREAM:
                if not segment.is_reverse_link:
                    raise ValueError(
                        "upstream lineage paths must follow target-to-source links."
                    )
            current_record = segment.to_record


@dataclass(
    frozen=True,
    slots=True,
)
class PersistenceLineageTraversalResult:
    """
    Typed result for bounded lineage traversal over persisted lineage links.
    """

    request: PersistenceLineageTraversalRequest
    paths: tuple[PersistenceLineagePath, ...] = ()
    truncated: bool = False
    edges_considered: int = 0

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "paths",
            tuple(
                self.paths,
            ),
        )
        _require_non_negative_integer(
            self.edges_considered,
            "edges_considered",
        )
        if self.edges_considered > self.request.max_edges:
            raise ValueError("edges_considered cannot exceed the request max_edges.")
        for path in self.paths:
            if path.root_record != self.request.root_record:
                raise ValueError(
                    "lineage traversal paths must share the request root record."
                )
            if path.direction != self.request.direction:
                raise ValueError(
                    "lineage traversal paths must share the request direction."
                )
            if path.depth > self.request.max_depth:
                raise ValueError(
                    "lineage traversal paths cannot exceed the request max_depth."
                )
            if self.request.relationship_types:
                for segment in path.segments:
                    if (
                        segment.link.relationship_type
                        not in self.request.relationship_types
                    ):
                        raise ValueError(
                            "lineage traversal path relationship type is not allowed."
                        )

    @property
    def path_count(
        self,
    ) -> int:
        return len(
            self.paths,
        )

    @property
    def visited_records(
        self,
    ) -> tuple[PersistenceRecordIdentity, ...]:
        records: list[PersistenceRecordIdentity] = [
            self.request.root_record,
        ]
        for path in self.paths:
            records.extend(
                path.records[1:],
            )
        return _dedupe_record_identities(
            records,
        )

    @property
    def visited_record_count(
        self,
    ) -> int:
        return len(
            self.visited_records,
        )

    def summary_dict(
        self,
    ) -> dict[str, object]:
        return {
            "request": self.request.as_dict(),
            "path_count": self.path_count,
            "visited_record_count": self.visited_record_count,
            "truncated": self.truncated,
            "edges_considered": self.edges_considered,
        }


def _coerce_traversal_direction(
    direction: PersistenceLineageTraversalDirection | str,
) -> PersistenceLineageTraversalDirection:
    if isinstance(
        direction,
        PersistenceLineageTraversalDirection,
    ):
        return direction

    normalized = direction.strip().lower()
    try:
        return PersistenceLineageTraversalDirection(
            normalized,
        )
    except ValueError as exc:
        raise ValueError("direction must be 'upstream' or 'downstream'.") from exc


def _normalize_relationship_types(
    values: Sequence[str],
) -> tuple[str, ...]:
    normalized: list[str] = []
    for index, value in enumerate(
        values,
    ):
        normalized.append(
            require_non_empty_identifier(
                value,
                f"relationship_types[{index}]",
            ),
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


def _dedupe_record_identities(
    values: Sequence[PersistenceRecordIdentity],
) -> tuple[PersistenceRecordIdentity, ...]:
    seen: set[tuple[str, str]] = set()
    deduped: list[PersistenceRecordIdentity] = []
    for value in values:
        key = (
            value.record_type,
            value.record_id,
        )
        if key in seen:
            continue
        seen.add(
            key,
        )
        deduped.append(
            value,
        )
    return tuple(
        deduped,
    )


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
