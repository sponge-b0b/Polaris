from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from typing import Any

import pytest

from core.storage.persistence.lineage import (
    PersistenceLineageLinkRecord,
    PersistenceLineagePath,
    PersistenceLineagePathSegment,
    PersistenceLineageTraversalDirection,
    PersistenceLineageTraversalRequest,
    PersistenceLineageTraversalResult,
    PersistenceRecordIdentity,
    new_persistence_lineage_link_id,
)


def test_lineage_traversal_request_normalizes_and_bounds_queries() -> None:
    root = _identity(
        " report ",
        " morning-report-1 ",
    )
    request = PersistenceLineageTraversalRequest(
        root_record=root,
        direction=" downstream ",
        max_depth=2,
        max_edges=10,
        relationship_types=(
            " produced ",
            "uses",
            "produced",
        ),
    )

    assert request.root_record == _identity(
        "report",
        "morning-report-1",
    )
    assert request.direction == PersistenceLineageTraversalDirection.DOWNSTREAM
    assert request.is_downstream is True
    assert request.is_upstream is False
    assert request.relationship_types == (
        "produced",
        "uses",
    )
    assert request.as_dict() == {
        "root_record": {
            "record_type": "report",
            "record_id": "morning-report-1",
        },
        "direction": "downstream",
        "max_depth": 2,
        "max_edges": 10,
        "relationship_types": (
            "produced",
            "uses",
        ),
    }

    with pytest.raises(FrozenInstanceError):
        request.max_depth = 4  # type: ignore[misc]


@pytest.mark.parametrize(
    ("kwargs", "field_name"),
    [
        ({"direction": "sideways"}, "direction"),
        ({"direction": "upstream", "max_depth": -1}, "max_depth"),
        ({"direction": "upstream", "max_edges": 0}, "max_edges"),
        (
            {
                "direction": "upstream",
                "relationship_types": (
                    "uses",
                    " ",
                ),
            },
            "relationship_types",
        ),
    ],
)
def test_lineage_traversal_request_validates_bounds_and_filters(
    kwargs: dict[str, Any],
    field_name: str,
) -> None:
    with pytest.raises(ValueError, match=field_name):
        PersistenceLineageTraversalRequest(
            root_record=_identity(
                "report",
                "report-1",
            ),
            **kwargs,
        )


def test_downstream_lineage_path_follows_source_to_target_links() -> None:
    report = _identity(
        "report",
        "report-1",
    )
    recommendation = _identity(
        "recommendation",
        "rec-1",
    )
    signal = _identity(
        "signal",
        "signal-1",
    )
    produced = _link(
        report,
        recommendation,
        "produced",
    )
    uses = _link(
        recommendation,
        signal,
        "uses",
    )

    path = PersistenceLineagePath(
        root_record=report,
        direction=PersistenceLineageTraversalDirection.DOWNSTREAM,
        segments=(
            PersistenceLineagePathSegment(
                depth=1,
                from_record=report,
                to_record=recommendation,
                link=produced,
            ),
            PersistenceLineagePathSegment(
                depth=2,
                from_record=recommendation,
                to_record=signal,
                link=uses,
            ),
        ),
    )

    assert path.depth == 2
    assert path.terminal_record == signal
    assert path.records == (
        report,
        recommendation,
        signal,
    )
    assert path.as_dict()["direction"] == "downstream"


def test_upstream_lineage_path_follows_target_to_source_links() -> None:
    report = _identity(
        "report",
        "report-1",
    )
    recommendation = _identity(
        "recommendation",
        "rec-1",
    )
    signal = _identity(
        "signal",
        "signal-1",
    )
    produced = _link(
        report,
        recommendation,
        "produced",
    )
    uses = _link(
        recommendation,
        signal,
        "uses",
    )

    path = PersistenceLineagePath(
        root_record=signal,
        direction="upstream",
        segments=(
            PersistenceLineagePathSegment(
                depth=1,
                from_record=signal,
                to_record=recommendation,
                link=uses,
            ),
            PersistenceLineagePathSegment(
                depth=2,
                from_record=recommendation,
                to_record=report,
                link=produced,
            ),
        ),
    )

    assert path.direction == PersistenceLineageTraversalDirection.UPSTREAM
    assert path.terminal_record == report
    assert path.records == (
        signal,
        recommendation,
        report,
    )


def test_lineage_path_rejects_non_contiguous_or_wrong_direction_segments() -> None:
    report = _identity(
        "report",
        "report-1",
    )
    recommendation = _identity(
        "recommendation",
        "rec-1",
    )
    signal = _identity(
        "signal",
        "signal-1",
    )
    produced = _link(
        report,
        recommendation,
        "produced",
    )
    uses = _link(
        recommendation,
        signal,
        "uses",
    )

    with pytest.raises(ValueError, match="contiguous"):
        PersistenceLineagePath(
            root_record=report,
            direction="downstream",
            segments=(
                PersistenceLineagePathSegment(
                    depth=2,
                    from_record=report,
                    to_record=recommendation,
                    link=produced,
                ),
            ),
        )

    with pytest.raises(ValueError, match="contiguous"):
        PersistenceLineagePath(
            root_record=report,
            direction="downstream",
            segments=(
                PersistenceLineagePathSegment(
                    depth=1,
                    from_record=recommendation,
                    to_record=signal,
                    link=uses,
                ),
            ),
        )

    with pytest.raises(ValueError, match="downstream"):
        PersistenceLineagePath(
            root_record=recommendation,
            direction="downstream",
            segments=(
                PersistenceLineagePathSegment(
                    depth=1,
                    from_record=recommendation,
                    to_record=report,
                    link=produced,
                ),
            ),
        )


def test_lineage_path_segment_requires_existing_link_endpoint_match() -> None:
    report = _identity(
        "report",
        "report-1",
    )
    signal = _identity(
        "signal",
        "signal-1",
    )
    recommendation = _identity(
        "recommendation",
        "rec-1",
    )
    produced = _link(
        report,
        recommendation,
        "produced",
    )

    with pytest.raises(ValueError, match="endpoints"):
        PersistenceLineagePathSegment(
            depth=1,
            from_record=report,
            to_record=signal,
            link=produced,
        )


def test_lineage_traversal_result_enforces_request_bounds_and_summarizes() -> None:
    report = _identity(
        "report",
        "report-1",
    )
    recommendation = _identity(
        "recommendation",
        "rec-1",
    )
    signal = _identity(
        "signal",
        "signal-1",
    )
    produced = _link(
        report,
        recommendation,
        "produced",
    )
    uses = _link(
        recommendation,
        signal,
        "uses",
    )
    path = PersistenceLineagePath(
        root_record=report,
        direction="downstream",
        segments=(
            PersistenceLineagePathSegment(
                depth=1,
                from_record=report,
                to_record=recommendation,
                link=produced,
            ),
            PersistenceLineagePathSegment(
                depth=2,
                from_record=recommendation,
                to_record=signal,
                link=uses,
            ),
        ),
    )
    request = PersistenceLineageTraversalRequest(
        root_record=report,
        direction="downstream",
        max_depth=2,
        max_edges=2,
        relationship_types=(
            "produced",
            "uses",
        ),
    )
    result = PersistenceLineageTraversalResult(
        request=request,
        paths=(path,),
        truncated=True,
        edges_considered=2,
    )

    assert result.path_count == 1
    assert result.visited_records == (
        report,
        recommendation,
        signal,
    )
    assert result.visited_record_count == 3
    assert result.summary_dict() == {
        "request": request.as_dict(),
        "path_count": 1,
        "visited_record_count": 3,
        "truncated": True,
        "edges_considered": 2,
    }


def test_lineage_traversal_result_rejects_out_of_bounds_paths() -> None:
    report = _identity(
        "report",
        "report-1",
    )
    recommendation = _identity(
        "recommendation",
        "rec-1",
    )
    signal = _identity(
        "signal",
        "signal-1",
    )
    produced = _link(
        report,
        recommendation,
        "produced",
    )
    uses = _link(
        recommendation,
        signal,
        "uses",
    )
    path = PersistenceLineagePath(
        root_record=report,
        direction="downstream",
        segments=(
            PersistenceLineagePathSegment(
                depth=1,
                from_record=report,
                to_record=recommendation,
                link=produced,
            ),
            PersistenceLineagePathSegment(
                depth=2,
                from_record=recommendation,
                to_record=signal,
                link=uses,
            ),
        ),
    )

    with pytest.raises(ValueError, match="max_depth"):
        PersistenceLineageTraversalResult(
            request=PersistenceLineageTraversalRequest(
                root_record=report,
                direction="downstream",
                max_depth=1,
            ),
            paths=(path,),
        )

    with pytest.raises(ValueError, match="relationship type"):
        PersistenceLineageTraversalResult(
            request=PersistenceLineageTraversalRequest(
                root_record=report,
                direction="downstream",
                relationship_types=("produced",),
            ),
            paths=(path,),
        )

    with pytest.raises(ValueError, match="max_edges"):
        PersistenceLineageTraversalResult(
            request=PersistenceLineageTraversalRequest(
                root_record=report,
                direction="downstream",
                max_edges=1,
            ),
            paths=(),
            edges_considered=2,
        )


def _identity(
    record_type: str,
    record_id: str,
) -> PersistenceRecordIdentity:
    return PersistenceRecordIdentity(
        record_type=record_type,
        record_id=record_id,
    )


def _link(
    source_record: PersistenceRecordIdentity,
    target_record: PersistenceRecordIdentity,
    relationship_type: str,
) -> PersistenceLineageLinkRecord:
    return PersistenceLineageLinkRecord(
        link_id=new_persistence_lineage_link_id(
            source_record=source_record,
            target_record=target_record,
            relationship_type=relationship_type,
        ),
        source_record=source_record,
        target_record=target_record,
        relationship_type=relationship_type,
        created_at=datetime(
            2026,
            5,
            30,
            tzinfo=UTC,
        ),
    )
