from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol

from core.storage.persistence.attribution.attribution_persistence_models import (
    AttributionPersistenceBundle,
    AttributionPersistenceResult,
    AttributionRecord,
    RecommendationAttributionRecord,
    SignalAttributionRecord,
)


class AttributionPersistenceRepository(Protocol):
    """
    Async repository contract for durable attribution records.

    Attribution persistence is append-friendly: generic, signal, and
    recommendation attribution rows are persisted by stable identifiers without
    deleting sibling attribution rows for the same target record.
    """

    async def persist_attribution_bundle(
        self,
        bundle: AttributionPersistenceBundle,
    ) -> AttributionPersistenceResult: ...

    async def persist_attribution(
        self,
        attribution: AttributionRecord,
    ) -> AttributionPersistenceResult: ...

    async def persist_signal_attribution(
        self,
        attribution: SignalAttributionRecord,
    ) -> AttributionPersistenceResult: ...

    async def persist_recommendation_attribution(
        self,
        attribution: RecommendationAttributionRecord,
    ) -> AttributionPersistenceResult: ...

    async def get_attribution(
        self,
        attribution_id: str,
    ) -> AttributionRecord | None: ...

    async def get_signal_attribution(
        self,
        signal_attribution_id: str,
    ) -> SignalAttributionRecord | None: ...

    async def get_recommendation_attribution(
        self,
        recommendation_attribution_id: str,
    ) -> RecommendationAttributionRecord | None: ...

    async def list_attributions(
        self,
        *,
        target_record_type: str | None = None,
        target_record_id: str | None = None,
        workflow_name: str | None = None,
        execution_id: str | None = None,
        agent_name: str | None = None,
        agent_type: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[AttributionRecord]: ...

    async def list_signal_attributions(
        self,
        *,
        signal_id: str | None = None,
        workflow_name: str | None = None,
        execution_id: str | None = None,
        agent_name: str | None = None,
        agent_type: str | None = None,
        symbol: str | None = None,
        universe: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[SignalAttributionRecord]: ...

    async def list_recommendation_attributions(
        self,
        *,
        recommendation_id: str | None = None,
        signal_id: str | None = None,
        workflow_name: str | None = None,
        execution_id: str | None = None,
        agent_name: str | None = None,
        agent_type: str | None = None,
        symbol: str | None = None,
        universe: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[RecommendationAttributionRecord]: ...
