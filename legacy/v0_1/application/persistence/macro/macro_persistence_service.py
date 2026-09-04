from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from application.persistence.query_result_helpers import (
    build_common_query,
    build_list_result,
)
from core.storage.persistence.lineage import clean_optional_identifier
from core.storage.persistence.macro import (
    EconomicCalendarEventRecord,
    MacroObservationRecord,
    MacroPersistenceBundle,
    MacroPersistenceRepository,
    MacroPersistenceResult,
    MacroRegimeSnapshotRecord,
)
from core.storage.persistence.query import PersistenceListResult


@dataclass(
    frozen=True,
    slots=True,
)
class MacroObservationPersistenceFilters:
    """
    Typed application-layer filters for curated macro observation retrieval.
    """

    indicator_name: str | None = None
    indicator_category: str | None = None
    source: str | None = None
    region: str | None = None
    start: datetime | None = None
    end: datetime | None = None

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "indicator_name",
            clean_optional_identifier(
                self.indicator_name,
                "indicator_name",
            ),
        )
        object.__setattr__(
            self,
            "indicator_category",
            clean_optional_identifier(
                self.indicator_category,
                "indicator_category",
            ),
        )
        object.__setattr__(
            self,
            "source",
            clean_optional_identifier(
                self.source,
                "source",
            ),
        )
        object.__setattr__(
            self,
            "region",
            clean_optional_identifier(
                self.region,
                "region",
            ),
        )
        _require_ordered_time_window(
            self.start,
            self.end,
        )


@dataclass(
    frozen=True,
    slots=True,
)
class MacroRegimeSnapshotPersistenceFilters:
    """
    Typed application-layer filters for curated macro regime snapshot retrieval.
    """

    region: str | None = None
    source: str | None = None
    macro_regime: str | None = None
    economic_regime: str | None = None
    start: datetime | None = None
    end: datetime | None = None

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "region",
            clean_optional_identifier(
                self.region,
                "region",
            ),
        )
        object.__setattr__(
            self,
            "source",
            clean_optional_identifier(
                self.source,
                "source",
            ),
        )
        object.__setattr__(
            self,
            "macro_regime",
            clean_optional_identifier(
                self.macro_regime,
                "macro_regime",
            ),
        )
        object.__setattr__(
            self,
            "economic_regime",
            clean_optional_identifier(
                self.economic_regime,
                "economic_regime",
            ),
        )
        _require_ordered_time_window(
            self.start,
            self.end,
        )


@dataclass(
    frozen=True,
    slots=True,
)
class EconomicCalendarEventPersistenceFilters:
    """
    Typed application-layer filters for curated economic calendar retrieval.
    """

    event_name: str | None = None
    event_type: str | None = None
    source: str | None = None
    region: str | None = None
    start: datetime | None = None
    end: datetime | None = None

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "event_name",
            clean_optional_identifier(
                self.event_name,
                "event_name",
            ),
        )
        object.__setattr__(
            self,
            "event_type",
            clean_optional_identifier(
                self.event_type,
                "event_type",
            ),
        )
        object.__setattr__(
            self,
            "source",
            clean_optional_identifier(
                self.source,
                "source",
            ),
        )
        object.__setattr__(
            self,
            "region",
            clean_optional_identifier(
                self.region,
                "region",
            ),
        )
        _require_ordered_time_window(
            self.start,
            self.end,
        )


class MacroPersistenceService:
    """
    Application service for curated macro persistence.

    This service coordinates typed macro persistence through the repository
    protocol only. It intentionally accepts curated typed records, not raw
    provider payloads, and does not auto-capture workflow node output.
    """

    def __init__(
        self,
        repository: MacroPersistenceRepository,
    ) -> None:
        self._repository = repository

    async def persist_bundle(
        self,
        bundle: MacroPersistenceBundle,
    ) -> MacroPersistenceResult:
        return await self._repository.persist_macro_bundle(
            bundle,
        )

    async def persist_records(
        self,
        *,
        observations: Sequence[MacroObservationRecord] = (),
        regime_snapshots: Sequence[MacroRegimeSnapshotRecord] = (),
        calendar_events: Sequence[EconomicCalendarEventRecord] = (),
    ) -> MacroPersistenceResult:
        return await self.persist_bundle(
            MacroPersistenceBundle(
                observations=tuple(
                    observations,
                ),
                regime_snapshots=tuple(
                    regime_snapshots,
                ),
                calendar_events=tuple(
                    calendar_events,
                ),
            )
        )

    async def list_observations(
        self,
        filters: MacroObservationPersistenceFilters | None = None,
    ) -> Sequence[MacroObservationRecord]:
        result = await self.list_observations_result(
            filters,
        )
        return result.records

    async def list_observations_result(
        self,
        filters: MacroObservationPersistenceFilters | None = None,
    ) -> PersistenceListResult[MacroObservationRecord]:
        active_filters = filters or MacroObservationPersistenceFilters()
        records = await self._repository.list_observations(
            indicator_name=active_filters.indicator_name,
            indicator_category=active_filters.indicator_category,
            source=active_filters.source,
            region=active_filters.region,
            start=active_filters.start,
            end=active_filters.end,
        )
        query = build_common_query(
            record_type="macro_observation",
            source=active_filters.source,
            start=active_filters.start,
            end=active_filters.end,
            metadata={
                "indicator_name": active_filters.indicator_name,
                "indicator_category": active_filters.indicator_category,
                "region": active_filters.region,
            },
        )
        return build_list_result(
            records,
            query=query,
        )

    async def list_regime_snapshots(
        self,
        filters: MacroRegimeSnapshotPersistenceFilters | None = None,
    ) -> Sequence[MacroRegimeSnapshotRecord]:
        result = await self.list_regime_snapshots_result(
            filters,
        )
        return result.records

    async def list_regime_snapshots_result(
        self,
        filters: MacroRegimeSnapshotPersistenceFilters | None = None,
    ) -> PersistenceListResult[MacroRegimeSnapshotRecord]:
        active_filters = filters or MacroRegimeSnapshotPersistenceFilters()
        records = await self._repository.list_regime_snapshots(
            region=active_filters.region,
            source=active_filters.source,
            macro_regime=active_filters.macro_regime,
            economic_regime=active_filters.economic_regime,
            start=active_filters.start,
            end=active_filters.end,
        )
        query = build_common_query(
            record_type="macro_regime_snapshot",
            source=active_filters.source,
            start=active_filters.start,
            end=active_filters.end,
            metadata={
                "region": active_filters.region,
                "macro_regime": active_filters.macro_regime,
                "economic_regime": active_filters.economic_regime,
            },
        )
        return build_list_result(
            records,
            query=query,
        )

    async def list_calendar_events(
        self,
        filters: EconomicCalendarEventPersistenceFilters | None = None,
    ) -> Sequence[EconomicCalendarEventRecord]:
        result = await self.list_calendar_events_result(
            filters,
        )
        return result.records

    async def list_calendar_events_result(
        self,
        filters: EconomicCalendarEventPersistenceFilters | None = None,
    ) -> PersistenceListResult[EconomicCalendarEventRecord]:
        active_filters = filters or EconomicCalendarEventPersistenceFilters()
        records = await self._repository.list_calendar_events(
            event_name=active_filters.event_name,
            event_type=active_filters.event_type,
            source=active_filters.source,
            region=active_filters.region,
            start=active_filters.start,
            end=active_filters.end,
        )
        query = build_common_query(
            record_type="economic_calendar_event",
            source=active_filters.source,
            start=active_filters.start,
            end=active_filters.end,
            metadata={
                "event_name": active_filters.event_name,
                "event_type": active_filters.event_type,
                "region": active_filters.region,
            },
        )
        return build_list_result(
            records,
            query=query,
        )


def _require_ordered_time_window(
    start: datetime | None,
    end: datetime | None,
) -> None:
    if start is not None and end is not None and start > end:
        raise ValueError("start must be less than or equal to end.")
