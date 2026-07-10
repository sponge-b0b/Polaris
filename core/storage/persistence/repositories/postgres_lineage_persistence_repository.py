from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.models.lineage import PersistenceLineageLinkModel
from core.storage.persistence.lineage.lineage_persistence_models import (
    PersistenceLineageLinkRecord,
)
from core.storage.persistence.lineage.lineage_persistence_models import (
    PersistenceLineageLinkResult,
)
from core.storage.persistence.lineage.lineage_persistence_models import (
    PersistenceRecordIdentity,
)
from core.storage.persistence.lineage.lineage_traversal_models import (
    DEFAULT_LINEAGE_TRAVERSAL_DEPTH,
)
from core.storage.persistence.lineage.lineage_traversal_models import (
    DEFAULT_LINEAGE_TRAVERSAL_EDGE_LIMIT,
)
from core.storage.persistence.lineage.lineage_traversal_models import (
    PersistenceLineagePath,
)
from core.storage.persistence.lineage.lineage_traversal_models import (
    PersistenceLineagePathSegment,
)
from core.storage.persistence.lineage.lineage_traversal_models import (
    PersistenceLineageTraversalDirection,
)
from core.storage.persistence.lineage.lineage_traversal_models import (
    PersistenceLineageTraversalRequest,
)
from core.storage.persistence.lineage.lineage_traversal_models import (
    PersistenceLineageTraversalResult,
)
from core.storage.persistence.lineage.lineage_persistence_repository import (
    PersistenceLineageLinkRepository,
)
from core.storage.persistence.serializers.lineage_persistence_serializer import (
    PersistenceLineageLinkSerializer,
)


class PostgresPersistenceLineageLinkRepository(PersistenceLineageLinkRepository):
    """
    PostgreSQL adapter for durable cross-record persistence lineage links.
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self._session = session

    async def persist_lineage_link(
        self,
        link: PersistenceLineageLinkRecord,
    ) -> PersistenceLineageLinkResult:
        try:
            await self._session.execute(
                _upsert_lineage_link_statement(
                    link,
                )
            )
            await self._session.commit()
        except SQLAlchemyError as exc:
            await self._session.rollback()

            return PersistenceLineageLinkResult.failed(
                str(exc),
            )

        return PersistenceLineageLinkResult.succeeded(
            link_id=link.link_id,
        )

    async def get_lineage_link(
        self,
        link_id: str,
    ) -> PersistenceLineageLinkRecord | None:
        stmt = select(PersistenceLineageLinkModel).where(
            PersistenceLineageLinkModel.link_id == link_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None

        return PersistenceLineageLinkSerializer.link_from_model(
            model,
        )

    async def list_links_for_source(
        self,
        source_record: PersistenceRecordIdentity,
    ) -> Sequence[PersistenceLineageLinkRecord]:
        stmt = select(PersistenceLineageLinkModel).where(
            PersistenceLineageLinkModel.source_record_type == source_record.record_type,
            PersistenceLineageLinkModel.source_record_id == source_record.record_id,
        )
        result = await self._session.execute(stmt)

        return tuple(
            PersistenceLineageLinkSerializer.link_from_model(
                model,
            )
            for model in result.scalars().all()
        )

    async def list_links_for_target(
        self,
        target_record: PersistenceRecordIdentity,
    ) -> Sequence[PersistenceLineageLinkRecord]:
        stmt = select(PersistenceLineageLinkModel).where(
            PersistenceLineageLinkModel.target_record_type == target_record.record_type,
            PersistenceLineageLinkModel.target_record_id == target_record.record_id,
        )
        result = await self._session.execute(stmt)

        return tuple(
            PersistenceLineageLinkSerializer.link_from_model(
                model,
            )
            for model in result.scalars().all()
        )

    async def traverse_lineage(
        self,
        request: PersistenceLineageTraversalRequest,
    ) -> PersistenceLineageTraversalResult:
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
                links = await self._list_traversal_links(
                    current_record=current_record,
                    request=request,
                )
                for link in links:
                    if edges_considered >= request.max_edges:
                        truncated = True
                        break

                    edges_considered += 1
                    from_record, to_record = _path_endpoints_for_link(
                        link=link,
                        direction=request.direction,
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
        max_depth: int = DEFAULT_LINEAGE_TRAVERSAL_DEPTH,
        max_edges: int = DEFAULT_LINEAGE_TRAVERSAL_EDGE_LIMIT,
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
        max_depth: int = DEFAULT_LINEAGE_TRAVERSAL_DEPTH,
        max_edges: int = DEFAULT_LINEAGE_TRAVERSAL_EDGE_LIMIT,
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

    async def _list_traversal_links(
        self,
        *,
        current_record: PersistenceRecordIdentity,
        request: PersistenceLineageTraversalRequest,
    ) -> Sequence[PersistenceLineageLinkRecord]:
        stmt = _lineage_traversal_statement(
            current_record=current_record,
            request=request,
        )
        result = await self._session.execute(stmt)

        return tuple(
            PersistenceLineageLinkSerializer.link_from_model(
                model,
            )
            for model in result.scalars().all()
        )


def _upsert_lineage_link_statement(
    link: PersistenceLineageLinkRecord,
) -> Any:
    values = PersistenceLineageLinkSerializer.link_values(link)
    stmt = insert(PersistenceLineageLinkModel).values(**values)
    excluded = stmt.excluded

    return stmt.on_conflict_do_update(
        index_elements=[
            "link_id",
        ],
        set_={
            "source_record_type": excluded.source_record_type,
            "source_record_id": excluded.source_record_id,
            "relationship_type": excluded.relationship_type,
            "target_record_type": excluded.target_record_type,
            "target_record_id": excluded.target_record_id,
            "workflow_name": excluded.workflow_name,
            "execution_id": excluded.execution_id,
            "runtime_id": excluded.runtime_id,
            "node_name": excluded.node_name,
            "created_at": excluded.created_at,
            "metadata": excluded.metadata,
            "row_updated_at": func.now(),
        },
    )


def _lineage_traversal_statement(
    *,
    current_record: PersistenceRecordIdentity,
    request: PersistenceLineageTraversalRequest,
) -> Any:
    if request.direction == PersistenceLineageTraversalDirection.DOWNSTREAM:
        stmt = select(PersistenceLineageLinkModel).where(
            PersistenceLineageLinkModel.source_record_type
            == current_record.record_type,
            PersistenceLineageLinkModel.source_record_id == current_record.record_id,
        )
    else:
        stmt = select(PersistenceLineageLinkModel).where(
            PersistenceLineageLinkModel.target_record_type
            == current_record.record_type,
            PersistenceLineageLinkModel.target_record_id == current_record.record_id,
        )

    if request.relationship_types:
        stmt = stmt.where(
            PersistenceLineageLinkModel.relationship_type.in_(
                request.relationship_types,
            )
        )

    return stmt.order_by(
        PersistenceLineageLinkModel.created_at.asc(),
        PersistenceLineageLinkModel.link_id.asc(),
    ).limit(
        request.max_edges,
    )


def _path_endpoints_for_link(
    *,
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
