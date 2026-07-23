from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

import pytest

from application.persistence.lineage import LineagePersistenceService
from core.storage.persistence.lineage import (
    PersistenceLineageLinkRecord,
    PersistenceLineageLinkResult,
    PersistenceLineagePath,
    PersistenceLineagePathSegment,
    PersistenceLineageTraversalDirection,
    PersistenceLineageTraversalRequest,
    PersistenceLineageTraversalResult,
    PersistenceRecordIdentity,
    new_persistence_lineage_link_id,
)


@pytest.mark.asyncio
async def test_trace_downstream_lineage_returns_typed_report_to_workflow_paths() -> (
    None
):
    report = _identity(
        "report",
        "morning-report-1",
    )
    recommendation = _identity(
        "recommendation",
        "rec-1",
    )
    signal = _identity(
        "signal",
        "signal-1",
    )
    workflow = _identity(
        "workflow_execution",
        "exec-1",
    )
    repository = FakeLineageRepository(
        links=(
            _link(
                report,
                recommendation,
                "produced",
            ),
            _link(
                recommendation,
                signal,
                "uses",
            ),
            _link(
                signal,
                workflow,
                "derived_from",
            ),
        )
    )
    service = LineagePersistenceService(
        repository,
    )

    result = await service.trace_downstream_lineage(
        report,
        max_depth=3,
        max_edges=10,
        relationship_types=(
            "produced",
            "uses",
            "derived_from",
        ),
    )

    assert result.request.root_record == report
    assert result.request.direction == PersistenceLineageTraversalDirection.DOWNSTREAM
    assert result.path_count == 3
    assert result.paths[-1].terminal_record == workflow
    assert result.paths[-1].records == (
        report,
        recommendation,
        signal,
        workflow,
    )
    assert repository.last_request is not None
    assert repository.last_request.max_depth == 3
    assert repository.last_request.max_edges == 10


@pytest.mark.asyncio
async def test_trace_upstream_lineage_returns_reverse_workflow_to_report_paths() -> (
    None
):
    report = _identity(
        "report",
        "morning-report-1",
    )
    recommendation = _identity(
        "recommendation",
        "rec-1",
    )
    signal = _identity(
        "signal",
        "signal-1",
    )
    workflow = _identity(
        "workflow_execution",
        "exec-1",
    )
    repository = FakeLineageRepository(
        links=(
            _link(
                report,
                recommendation,
                "produced",
            ),
            _link(
                recommendation,
                signal,
                "uses",
            ),
            _link(
                signal,
                workflow,
                "derived_from",
            ),
        )
    )
    service = LineagePersistenceService(
        repository,
    )

    result = await service.trace_upstream_lineage(
        workflow,
        max_depth=3,
        max_edges=10,
    )

    assert result.request.direction == PersistenceLineageTraversalDirection.UPSTREAM
    assert result.path_count == 3
    assert result.paths[-1].terminal_record == report
    assert result.paths[-1].records == (
        workflow,
        signal,
        recommendation,
        report,
    )


@pytest.mark.asyncio
async def test_trace_lineage_delegates_explicit_traversal_request() -> None:
    report = _identity(
        "report",
        "morning-report-1",
    )
    recommendation = _identity(
        "recommendation",
        "rec-1",
    )
    repository = FakeLineageRepository(
        links=(
            _link(
                report,
                recommendation,
                "produced",
            ),
        )
    )
    service = LineagePersistenceService(
        repository,
    )
    request = PersistenceLineageTraversalRequest(
        root_record=report,
        direction="downstream",
        max_depth=1,
        max_edges=5,
    )

    result = await service.trace_lineage(
        request,
    )

    assert repository.last_request == request
    assert result.path_count == 1
    assert result.paths[0].terminal_record == recommendation


@pytest.mark.asyncio
async def test_list_lineage_links_preserves_sequence_api_and_result_envelope() -> None:
    report = _identity(
        "report",
        "morning-report-1",
    )
    recommendation = _identity(
        "recommendation",
        "rec-1",
    )
    link = _link(
        report,
        recommendation,
        "produced",
    )
    service = LineagePersistenceService(FakeLineageRepository(links=(link,)))

    source_records = await service.list_links_for_source(
        report,
    )
    source_result = await service.list_links_for_source_result(
        report,
    )
    target_records = await service.list_links_for_target(
        recommendation,
    )
    target_result = await service.list_links_for_target_result(
        recommendation,
    )

    assert source_records == (link,)
    assert source_result.records == (link,)
    assert source_result.total_count == 1
    assert source_result.query is not None
    assert source_result.query.metadata["lineage_query_direction"] == "downstream"
    assert target_records == (link,)
    assert target_result.records == (link,)
    assert target_result.query is not None
    assert target_result.query.metadata["lineage_query_direction"] == "upstream"


class FakeLineageRepository:
    def __init__(
        self,
        *,
        links: Sequence[PersistenceLineageLinkRecord],
    ) -> None:
        self._links = tuple(
            links,
        )
        self.last_request: PersistenceLineageTraversalRequest | None = None

    async def persist_lineage_link(
        self,
        link: PersistenceLineageLinkRecord,
    ) -> PersistenceLineageLinkResult:
        return PersistenceLineageLinkResult.succeeded(
            link_id=link.link_id,
        )

    async def get_lineage_link(
        self,
        link_id: str,
    ) -> PersistenceLineageLinkRecord | None:
        for link in self._links:
            if link.link_id == link_id:
                return link
        return None

    async def list_links_for_source(
        self,
        source_record: PersistenceRecordIdentity,
    ) -> Sequence[PersistenceLineageLinkRecord]:
        return tuple(
            link for link in self._links if link.source_record == source_record
        )

    async def list_links_for_target(
        self,
        target_record: PersistenceRecordIdentity,
    ) -> Sequence[PersistenceLineageLinkRecord]:
        return tuple(
            link for link in self._links if link.target_record == target_record
        )

    async def traverse_lineage(
        self,
        request: PersistenceLineageTraversalRequest,
    ) -> PersistenceLineageTraversalResult:
        self.last_request = request
        frontier: tuple[
            tuple[PersistenceRecordIdentity, PersistenceLineagePath], ...
        ] = (
            (
                request.root_record,
                PersistenceLineagePath(
                    root_record=request.root_record,
                    direction=request.direction,
                ),
            ),
        )
        paths: list[PersistenceLineagePath] = []
        edges_considered = 0
        truncated = False

        for depth in range(
            1,
            request.max_depth + 1,
        ):
            next_frontier: list[
                tuple[PersistenceRecordIdentity, PersistenceLineagePath]
            ] = []
            for current_record, current_path in frontier:
                for link in self._links_for_request(
                    current_record,
                    request,
                ):
                    if edges_considered >= request.max_edges:
                        truncated = True
                        break
                    edges_considered += 1
                    from_record, to_record = _path_endpoints_for_link(
                        link,
                        request.direction,
                    )
                    if to_record in current_path.records:
                        continue
                    segment = PersistenceLineagePathSegment(
                        depth=depth,
                        from_record=from_record,
                        to_record=to_record,
                        link=link,
                    )
                    next_path = PersistenceLineagePath(
                        root_record=request.root_record,
                        direction=request.direction,
                        segments=(
                            *current_path.segments,
                            segment,
                        ),
                    )
                    paths.append(
                        next_path,
                    )
                    next_frontier.append(
                        (
                            to_record,
                            next_path,
                        )
                    )
                if truncated:
                    break
            if truncated or not next_frontier:
                break
            frontier = tuple(
                next_frontier,
            )

        return PersistenceLineageTraversalResult(
            request=request,
            paths=tuple(
                paths,
            ),
            truncated=truncated,
            edges_considered=edges_considered,
        )

    async def traverse_upstream_lineage(
        self,
        root_record: PersistenceRecordIdentity,
        *,
        max_depth: int = 3,
        max_edges: int = 250,
        relationship_types: tuple[str, ...] = (),
    ) -> PersistenceLineageTraversalResult:
        return await self.traverse_lineage(
            PersistenceLineageTraversalRequest(
                root_record=root_record,
                direction=PersistenceLineageTraversalDirection.UPSTREAM,
                max_depth=max_depth,
                max_edges=max_edges,
                relationship_types=relationship_types,
            )
        )

    async def traverse_downstream_lineage(
        self,
        root_record: PersistenceRecordIdentity,
        *,
        max_depth: int = 3,
        max_edges: int = 250,
        relationship_types: tuple[str, ...] = (),
    ) -> PersistenceLineageTraversalResult:
        return await self.traverse_lineage(
            PersistenceLineageTraversalRequest(
                root_record=root_record,
                direction=PersistenceLineageTraversalDirection.DOWNSTREAM,
                max_depth=max_depth,
                max_edges=max_edges,
                relationship_types=relationship_types,
            )
        )

    def _links_for_request(
        self,
        current_record: PersistenceRecordIdentity,
        request: PersistenceLineageTraversalRequest,
    ) -> tuple[PersistenceLineageLinkRecord, ...]:
        if request.direction == PersistenceLineageTraversalDirection.DOWNSTREAM:
            links = tuple(
                link for link in self._links if link.source_record == current_record
            )
        else:
            links = tuple(
                link for link in self._links if link.target_record == current_record
            )
        if request.relationship_types:
            links = tuple(
                link
                for link in links
                if link.relationship_type in request.relationship_types
            )
        return links


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


def _path_endpoints_for_link(
    link: PersistenceLineageLinkRecord,
    direction: PersistenceLineageTraversalDirection | str,
) -> tuple[PersistenceRecordIdentity, PersistenceRecordIdentity]:
    if direction == PersistenceLineageTraversalDirection.DOWNSTREAM:
        return (
            link.source_record,
            link.target_record,
        )
    return (
        link.target_record,
        link.source_record,
    )
