from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol

from core.storage.persistence.macro.macro_persistence_models import (
    EconomicCalendarEventRecord,
)
from core.storage.persistence.macro.macro_persistence_models import (
    MacroObservationRecord,
)
from core.storage.persistence.macro.macro_persistence_models import (
    MacroPersistenceBundle,
)
from core.storage.persistence.macro.macro_persistence_models import (
    MacroPersistenceResult,
)
from core.storage.persistence.macro.macro_persistence_models import (
    MacroRegimeSnapshotRecord,
)


class MacroPersistenceRepository(Protocol):
    """
    Async repository contract for durable curated macro records.

    Macro observations and economic calendar events are upserted by natural
    source keys. Macro regime snapshots are append-only records that preserve
    final curated inputs and outputs for audit, replay, and future RAG ingestion.
    """

    async def persist_macro_bundle(
        self,
        bundle: MacroPersistenceBundle,
    ) -> MacroPersistenceResult: ...

    async def list_observations(
        self,
        *,
        indicator_name: str | None = None,
        indicator_category: str | None = None,
        source: str | None = None,
        region: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[MacroObservationRecord]: ...

    async def list_regime_snapshots(
        self,
        *,
        region: str | None = None,
        source: str | None = None,
        macro_regime: str | None = None,
        economic_regime: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[MacroRegimeSnapshotRecord]: ...

    async def list_calendar_events(
        self,
        *,
        event_name: str | None = None,
        event_type: str | None = None,
        source: str | None = None,
        region: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[EconomicCalendarEventRecord]: ...
