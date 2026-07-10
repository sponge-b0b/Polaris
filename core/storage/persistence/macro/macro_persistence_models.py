from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from uuid import uuid4

from core.storage.persistence.lineage import JsonObject
from core.storage.persistence.lineage import PersistenceLineage
from core.storage.persistence.lineage import clean_optional_identifier
from core.storage.persistence.lineage import require_non_empty_identifier


@dataclass(
    frozen=True,
    slots=True,
)
class MacroObservationRecord:
    """
    Typed persistence-boundary record for curated macro indicator observations.

    Macro provider payloads should be normalized and curated before becoming
    this record. Raw vendor payloads remain at external/provider boundaries.
    """

    observation_id: str
    indicator_name: str
    observation_timestamp: datetime
    source: str
    value: float
    lineage: PersistenceLineage = field(default_factory=PersistenceLineage)
    indicator_category: str | None = None
    region: str | None = None
    unit: str | None = None
    frequency: str | None = None
    release_timestamp: datetime | None = None
    vintage_timestamp: datetime | None = None
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "observation_id",
            require_non_empty_identifier(
                self.observation_id,
                "observation_id",
            ),
        )
        object.__setattr__(
            self,
            "indicator_name",
            require_non_empty_identifier(
                self.indicator_name,
                "indicator_name",
            ),
        )
        object.__setattr__(
            self,
            "source",
            require_non_empty_identifier(
                self.source,
                "source",
            ),
        )
        _normalize_optional_identifier_fields(
            self,
            (
                "indicator_category",
                "region",
                "unit",
                "frequency",
            ),
        )


@dataclass(
    frozen=True,
    slots=True,
)
class MacroRegimeSnapshotRecord:
    """
    Append-only macro regime snapshot with final synthesized macro outputs.
    """

    regime_snapshot_id: str
    timestamp: datetime
    lineage: PersistenceLineage = field(default_factory=PersistenceLineage)
    source: str | None = None
    region: str | None = None
    inflation_regime: str | None = None
    liquidity_regime: str | None = None
    growth_regime: str | None = None
    fed_stance: str | None = None
    yield_curve_regime: str | None = None
    macro_regime: str | None = None
    economic_regime: str | None = None
    inflation_score: float | None = None
    liquidity_score: float | None = None
    growth_score: float | None = None
    yield_curve_score: float | None = None
    macro_score: float | None = None
    risk_score: float | None = None
    confidence: float | None = None
    inputs: JsonObject = field(default_factory=dict)
    outputs: JsonObject = field(default_factory=dict)
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "regime_snapshot_id",
            require_non_empty_identifier(
                self.regime_snapshot_id,
                "regime_snapshot_id",
            ),
        )
        _normalize_optional_identifier_fields(
            self,
            (
                "source",
                "region",
                "inflation_regime",
                "liquidity_regime",
                "growth_regime",
                "fed_stance",
                "yield_curve_regime",
                "macro_regime",
                "economic_regime",
            ),
        )
        _require_optional_stability_score(
            self.inflation_score,
            "inflation_score",
        )
        _require_optional_stability_score(
            self.liquidity_score,
            "liquidity_score",
        )
        _require_optional_stability_score(
            self.growth_score,
            "growth_score",
        )
        _require_optional_stability_score(
            self.yield_curve_score,
            "yield_curve_score",
        )
        _require_optional_stability_score(
            self.macro_score,
            "macro_score",
        )
        _require_optional_ratio(
            self.risk_score,
            "risk_score",
        )
        _require_optional_ratio(
            self.confidence,
            "confidence",
        )


@dataclass(
    frozen=True,
    slots=True,
)
class EconomicCalendarEventRecord:
    """
    Typed persistence-boundary record for curated economic calendar events.
    """

    event_id: str
    event_name: str
    event_timestamp: datetime
    source: str
    lineage: PersistenceLineage = field(default_factory=PersistenceLineage)
    region: str | None = None
    event_type: str | None = None
    importance_score: float | None = None
    actual_value: float | None = None
    forecast_value: float | None = None
    previous_value: float | None = None
    surprise_score: float | None = None
    unit: str | None = None
    currency: str | None = None
    release_status: str | None = None
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "event_id",
            require_non_empty_identifier(
                self.event_id,
                "event_id",
            ),
        )
        object.__setattr__(
            self,
            "event_name",
            require_non_empty_identifier(
                self.event_name,
                "event_name",
            ),
        )
        object.__setattr__(
            self,
            "source",
            require_non_empty_identifier(
                self.source,
                "source",
            ),
        )
        _normalize_optional_identifier_fields(
            self,
            (
                "region",
                "event_type",
                "unit",
                "currency",
                "release_status",
            ),
        )
        _require_optional_ratio(
            self.importance_score,
            "importance_score",
        )
        _require_optional_stability_score(
            self.surprise_score,
            "surprise_score",
        )


@dataclass(
    frozen=True,
    slots=True,
)
class MacroPersistenceBundle:
    """
    Atomic macro persistence payload.
    """

    observations: tuple[MacroObservationRecord, ...] = ()
    regime_snapshots: tuple[MacroRegimeSnapshotRecord, ...] = ()
    calendar_events: tuple[EconomicCalendarEventRecord, ...] = ()


@dataclass(
    frozen=True,
    slots=True,
)
class MacroPersistenceResult:
    """
    Typed result returned by macro persistence adapters.
    """

    success: bool
    records_persisted: int = 0
    primary_record_id: str | None = None
    error: str | None = None

    def __post_init__(
        self,
    ) -> None:
        if self.records_persisted < 0:
            raise ValueError("records_persisted cannot be negative.")

        if self.success and self.error is not None:
            raise ValueError("successful persistence results cannot include an error.")

        if self.success:
            require_non_empty_identifier(
                self.primary_record_id,
                "primary_record_id",
            )

        if not self.success:
            require_non_empty_identifier(
                self.error,
                "error",
            )

    @classmethod
    def succeeded(
        cls,
        *,
        primary_record_id: str,
        records_persisted: int = 1,
    ) -> MacroPersistenceResult:
        return cls(
            success=True,
            records_persisted=records_persisted,
            primary_record_id=primary_record_id,
        )

    @classmethod
    def failed(
        cls,
        error: str,
    ) -> MacroPersistenceResult:
        return cls(
            success=False,
            records_persisted=0,
            error=error,
        )


def new_macro_observation_id(
    *,
    indicator_name: str,
    observation_timestamp: datetime,
    source: str,
    region: str | None = None,
) -> str:
    parts = [
        require_non_empty_identifier(
            indicator_name,
            "indicator_name",
        ),
        require_non_empty_identifier(
            source,
            "source",
        ),
    ]
    clean_region = clean_optional_identifier(
        region,
        "region",
    )
    if clean_region is not None:
        parts.append(clean_region)

    return _stable_macro_id(
        "macro_observation",
        observation_timestamp,
        *parts,
    )


def new_macro_regime_snapshot_id(
    *,
    timestamp: datetime,
    execution_id: str | None = None,
    snapshot_key: str | None = None,
    region: str | None = None,
) -> str:
    clean_region = clean_optional_identifier(
        region,
        "region",
    )
    parts = () if clean_region is None else (clean_region,)
    return _snapshot_macro_id(
        record_type="macro_regime_snapshot",
        timestamp=timestamp,
        execution_id=execution_id,
        key=snapshot_key,
        parts=parts,
    )


def new_economic_calendar_event_id(
    *,
    event_name: str,
    event_timestamp: datetime,
    source: str,
    region: str | None = None,
) -> str:
    parts = [
        require_non_empty_identifier(
            event_name,
            "event_name",
        ),
        require_non_empty_identifier(
            source,
            "source",
        ),
    ]
    clean_region = clean_optional_identifier(
        region,
        "region",
    )
    if clean_region is not None:
        parts.append(clean_region)

    return _stable_macro_id(
        "economic_calendar_event",
        event_timestamp,
        *parts,
    )


def _stable_macro_id(
    record_type: str,
    timestamp: datetime,
    *parts: str,
) -> str:
    clean_record_type = require_non_empty_identifier(
        record_type,
        "record_type",
    )
    clean_parts = tuple(
        require_non_empty_identifier(
            part,
            "id_part",
        )
        for part in parts
    )

    return ":".join(
        (
            clean_record_type,
            timestamp.isoformat(),
            *clean_parts,
        )
    )


def _snapshot_macro_id(
    *,
    record_type: str,
    timestamp: datetime,
    execution_id: str | None,
    key: str | None,
    parts: tuple[str, ...] = (),
) -> str:
    clean_record_type = require_non_empty_identifier(
        record_type,
        "record_type",
    )
    clean_execution_id = clean_optional_identifier(
        execution_id,
        "execution_id",
    )
    clean_key = clean_optional_identifier(
        key,
        "snapshot_key",
    )

    if clean_execution_id is None:
        return f"{clean_record_type}:{uuid4().hex}"

    id_parts = [
        clean_record_type,
        clean_execution_id,
        timestamp.isoformat(),
        *parts,
    ]
    if clean_key is not None:
        id_parts.append(clean_key)

    return ":".join(id_parts)


def _normalize_optional_identifier_fields(
    record: object,
    field_names: tuple[str, ...],
) -> None:
    for field_name in field_names:
        object.__setattr__(
            record,
            field_name,
            clean_optional_identifier(
                getattr(record, field_name),
                field_name,
            ),
        )


def _require_optional_ratio(
    value: float | None,
    field_name: str,
) -> None:
    if value is None:
        return

    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{field_name} must be between 0.0 and 1.0.")


def _require_optional_stability_score(
    value: float | None,
    field_name: str,
) -> None:
    if value is None:
        return

    if not -1.0 <= value <= 1.0:
        raise ValueError(f"{field_name} must be between -1.0 and 1.0.")
