from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, cast

from application.rag.contracts.rag_context import RagRetrievedContext, RagSource
from application.rag.contracts.rag_request import RagRequest
from core.storage.persistence.market import TechnicalAnalysisSnapshotRecord
from core.storage.persistence.market.market_persistence_repository import (
    MarketPersistenceRepository,
)
from core.storage.persistence.rag import JsonObject

_TECHNICAL_SNAPSHOT_TABLE = "technical_analysis_snapshots"
_TECHNICAL_SNAPSHOT_TYPE = "technical_analysis_snapshot"


class StructuredRagRetriever(Protocol):
    async def retrieve(
        self,
        request: RagRequest,
    ) -> tuple[RagRetrievedContext, ...]: ...


@dataclass(
    frozen=True,
    slots=True,
)
class MarketStructuredRagRetriever:
    """Approved typed repository path for current technical market facts."""

    repository: MarketPersistenceRepository

    async def retrieve(
        self,
        request: RagRequest,
    ) -> tuple[RagRetrievedContext, ...]:
        if not _allows_technical_snapshots(request):
            return ()
        contexts: list[RagRetrievedContext] = []
        for symbol in request.filters.symbols:
            records = tuple(
                await self.repository.list_technical_snapshots(
                    symbol=symbol,
                    technical_regime=_single_value(request.filters.regimes),
                    start=request.filters.as_of_start,
                    end=request.filters.as_of_end,
                )
            )
            matching_records = tuple(
                record
                for record in records
                if _matches_request_lineage(record, request)
            )
            if matching_records:
                contexts.append(
                    _technical_context(
                        request=request,
                        record=max(
                            matching_records,
                            key=lambda record: (
                                record.timestamp,
                                record.technical_snapshot_id,
                            ),
                        ),
                        rank=len(contexts) + 1,
                    )
                )
        return tuple(contexts[: request.top_k])


def _allows_technical_snapshots(
    request: RagRequest,
) -> bool:
    filters = request.filters
    source_tables = filters.source_tables
    source_types = filters.source_types
    unsupported_filters = (
        filters.agent_names
        or filters.agent_types
        or filters.report_types
        or filters.metadata
    )
    return (
        bool(filters.symbols)
        and not unsupported_filters
        and (not source_tables or _TECHNICAL_SNAPSHOT_TABLE in source_tables)
        and (not source_types or _TECHNICAL_SNAPSHOT_TYPE in source_types)
    )


def _matches_request_lineage(
    record: TechnicalAnalysisSnapshotRecord,
    request: RagRequest,
) -> bool:
    filters = request.filters
    workflow_name = filters.workflow_name or request.workflow_name
    execution_id = filters.execution_id or request.execution_id
    return (
        (workflow_name is None or record.lineage.workflow_name == workflow_name)
        and (execution_id is None or record.lineage.execution_id == execution_id)
        and (
            filters.runtime_id is None
            or record.lineage.runtime_id == filters.runtime_id
        )
    )


def _single_value(
    values: tuple[str, ...],
) -> str | None:
    if len(values) == 1:
        return values[0]
    return None


def _technical_context(
    *,
    request: RagRequest,
    record: TechnicalAnalysisSnapshotRecord,
    rank: int,
) -> RagRetrievedContext:
    facts = tuple(
        fact
        for fact in (
            _fact("technical_regime", record.technical_regime),
            _fact("trend_regime", record.trend_regime),
            _fact("volatility_regime", record.volatility_regime),
            _fact("breadth_regime", record.breadth_regime),
            _fact("technical_score", record.technical_score),
            _fact("trend_score", record.trend_score),
            _fact("volatility_score", record.volatility_score),
            _fact("breadth_score", record.breadth_score),
            _fact("risk_score", record.risk_score),
            _fact("confidence", record.confidence),
            _fact("strategy_environment", record.strategy_environment),
        )
        if fact is not None
    )
    text = (
        f"Technical analysis facts for {record.symbol} at "
        f"{record.timestamp.isoformat()}: " + "; ".join(facts)
    )
    metadata = cast(
        JsonObject,
        {
            **dict(record.metadata),
            "symbol": record.symbol,
            "timestamp": record.timestamp.isoformat(),
            "structured_retrieval": True,
            "repository_path": "MarketPersistenceRepository.list_technical_snapshots",
        },
    )
    return RagRetrievedContext(
        context_id=f"{request.request_id}:structured:{record.technical_snapshot_id}",
        text=text,
        source=RagSource(
            source_table=_TECHNICAL_SNAPSHOT_TABLE,
            source_id=record.technical_snapshot_id,
            source_type=_TECHNICAL_SNAPSHOT_TYPE,
            document_id=f"structured:{record.technical_snapshot_id}",
            title=f"{record.symbol} Technical Analysis Snapshot",
            generated_at=record.timestamp,
            workflow_name=record.lineage.workflow_name,
            execution_id=record.lineage.execution_id,
            metadata=metadata,
        ),
        score=1.0,
        rank=rank,
        retrieval_route="structured",
        metadata=metadata,
    )


def _fact(
    name: str,
    value: object,
) -> str | None:
    if value is None:
        return None
    return f"{name}={value}"
