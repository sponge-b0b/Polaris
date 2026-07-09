from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime

import pytest

from application.rag.ingestion.curated_rag_models import CuratedRagSource
from application.rag.ingestion.rag_source_loaders import CuratedRagSourceLoaderRegistry
from core.storage.persistence.rag import RagSourceEligibilityRecord


@dataclass(slots=True)
class TrackingSourceLoader:
    source_tables: tuple[str, ...]
    calls: int = 0

    async def load(
        self,
        eligibility: RagSourceEligibilityRecord,
    ) -> CuratedRagSource | None:
        self.calls += 1
        return None


def test_registry_routes_source_to_registered_typed_loader() -> None:
    loader = TrackingSourceLoader(source_tables=("reports",))
    registry = CuratedRagSourceLoaderRegistry((loader,))

    result = asyncio.run(registry.load(_eligibility("reports")))

    assert result is None
    assert loader.calls == 1


def test_registry_returns_none_for_unregistered_source_table() -> None:
    loader = TrackingSourceLoader(source_tables=("reports",))
    registry = CuratedRagSourceLoaderRegistry((loader,))

    result = asyncio.run(registry.load(_eligibility("agent_signals")))

    assert result is None
    assert loader.calls == 0


def test_registry_rejects_duplicate_source_table_ownership() -> None:
    first = TrackingSourceLoader(source_tables=("reports",))
    second = TrackingSourceLoader(source_tables=("reports",))

    with pytest.raises(
        ValueError,
        match="Duplicate curated RAG source loader for 'reports'",
    ):
        CuratedRagSourceLoaderRegistry((first, second))


def _eligibility(source_table: str) -> RagSourceEligibilityRecord:
    return RagSourceEligibilityRecord(
        eligibility_id="eligibility-1",
        source_table=source_table,
        source_id="source-1",
        source_type="test",
        eligible=True,
        reason="test",
        quality_score=1.0,
        reviewed_timestamp=datetime(2026, 1, 1, tzinfo=UTC),
    )
