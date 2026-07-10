from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from uuid import uuid4

from core.storage.persistence.lineage import JsonObject
from core.storage.persistence.lineage import PersistenceLineage
from core.storage.persistence.lineage import PersistenceRecordIdentity
from core.storage.persistence.lineage import clean_optional_identifier
from core.storage.persistence.lineage import require_non_empty_identifier


@dataclass(
    frozen=True,
    slots=True,
)
class AttributionRecord:
    """
    Generic attribution record for a persisted platform target.

    Attribution records explain which persisted records contributed to another
    persisted record. They are diagnostic and audit-oriented, not execution
    instructions or signal mutations.
    """

    attribution_id: str
    target_record: PersistenceRecordIdentity
    attribution_type: str
    contribution_type: str
    contribution_score: float
    confidence: float
    explanation: str
    timestamp: datetime
    lineage: PersistenceLineage = field(default_factory=PersistenceLineage)
    agent_name: str | None = None
    agent_type: str | None = None
    source_records: tuple[PersistenceRecordIdentity, ...] = ()
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        _set_required_identifier(
            self,
            "attribution_id",
            self.attribution_id,
        )
        _set_required_identifier(
            self,
            "attribution_type",
            self.attribution_type,
        )
        _set_required_identifier(
            self,
            "contribution_type",
            self.contribution_type,
        )
        _set_required_text(
            self,
            "explanation",
            self.explanation,
        )
        _set_optional_agent_fields(
            self,
        )
        _require_non_empty_sources(
            self.source_records,
        )
        _require_signed_score(
            self.contribution_score,
            "contribution_score",
        )
        _require_ratio(
            self.confidence,
            "confidence",
        )


@dataclass(
    frozen=True,
    slots=True,
)
class SignalAttributionRecord:
    """
    Attribution record explaining source contributions to a signal.
    """

    signal_attribution_id: str
    signal_id: str
    attribution_type: str
    contribution_type: str
    contribution_score: float
    confidence: float
    explanation: str
    timestamp: datetime
    lineage: PersistenceLineage = field(default_factory=PersistenceLineage)
    signal_type: str | None = None
    agent_name: str | None = None
    agent_type: str | None = None
    symbol: str | None = None
    universe: str | None = None
    source_records: tuple[PersistenceRecordIdentity, ...] = ()
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        _set_required_identifier(
            self,
            "signal_attribution_id",
            self.signal_attribution_id,
        )
        _set_required_identifier(
            self,
            "signal_id",
            self.signal_id,
        )
        _set_required_identifier(
            self,
            "attribution_type",
            self.attribution_type,
        )
        _set_required_identifier(
            self,
            "contribution_type",
            self.contribution_type,
        )
        _set_required_text(
            self,
            "explanation",
            self.explanation,
        )
        object.__setattr__(
            self,
            "signal_type",
            clean_optional_identifier(
                self.signal_type,
                "signal_type",
            ),
        )
        _set_optional_agent_fields(
            self,
        )
        _set_optional_scope_fields(
            self,
        )
        _require_non_empty_sources(
            self.source_records,
        )
        _require_signed_score(
            self.contribution_score,
            "contribution_score",
        )
        _require_ratio(
            self.confidence,
            "confidence",
        )


@dataclass(
    frozen=True,
    slots=True,
)
class RecommendationAttributionRecord:
    """
    Attribution record explaining source or signal contributions to a recommendation.
    """

    recommendation_attribution_id: str
    recommendation_id: str
    attribution_type: str
    contribution_type: str
    contribution_score: float
    confidence: float
    explanation: str
    timestamp: datetime
    lineage: PersistenceLineage = field(default_factory=PersistenceLineage)
    signal_id: str | None = None
    agent_name: str | None = None
    agent_type: str | None = None
    symbol: str | None = None
    universe: str | None = None
    source_records: tuple[PersistenceRecordIdentity, ...] = ()
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        _set_required_identifier(
            self,
            "recommendation_attribution_id",
            self.recommendation_attribution_id,
        )
        _set_required_identifier(
            self,
            "recommendation_id",
            self.recommendation_id,
        )
        _set_required_identifier(
            self,
            "attribution_type",
            self.attribution_type,
        )
        _set_required_identifier(
            self,
            "contribution_type",
            self.contribution_type,
        )
        _set_required_text(
            self,
            "explanation",
            self.explanation,
        )
        object.__setattr__(
            self,
            "signal_id",
            clean_optional_identifier(
                self.signal_id,
                "signal_id",
            ),
        )
        _set_optional_agent_fields(
            self,
        )
        _set_optional_scope_fields(
            self,
        )
        _require_non_empty_sources(
            self.source_records,
        )
        _require_signed_score(
            self.contribution_score,
            "contribution_score",
        )
        _require_ratio(
            self.confidence,
            "confidence",
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AttributionPersistenceBundle:
    """
    Atomic attribution persistence payload.
    """

    attribution_records: tuple[AttributionRecord, ...] = ()
    signal_attributions: tuple[SignalAttributionRecord, ...] = ()
    recommendation_attributions: tuple[RecommendationAttributionRecord, ...] = ()


@dataclass(
    frozen=True,
    slots=True,
)
class AttributionPersistenceResult:
    """
    Typed result returned by attribution persistence adapters.
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
    ) -> AttributionPersistenceResult:
        return cls(
            success=True,
            records_persisted=records_persisted,
            primary_record_id=primary_record_id,
        )

    @classmethod
    def failed(
        cls,
        error: str,
    ) -> AttributionPersistenceResult:
        return cls(
            success=False,
            records_persisted=0,
            error=error,
        )


def new_attribution_record_id(
    *,
    target_record: PersistenceRecordIdentity,
    timestamp: datetime,
    attribution_key: str | None = None,
) -> str:
    return _new_attribution_id(
        prefix="attribution_record",
        timestamp=timestamp,
        parts=(
            target_record.record_type,
            target_record.record_id,
        ),
        key=attribution_key,
    )


def new_signal_attribution_id(
    *,
    signal_id: str,
    timestamp: datetime,
    attribution_key: str | None = None,
) -> str:
    clean_signal_id = require_non_empty_identifier(
        signal_id,
        "signal_id",
    )
    return _new_attribution_id(
        prefix="signal_attribution",
        timestamp=timestamp,
        parts=(clean_signal_id,),
        key=attribution_key,
    )


def new_recommendation_attribution_id(
    *,
    recommendation_id: str,
    timestamp: datetime,
    attribution_key: str | None = None,
    signal_id: str | None = None,
) -> str:
    clean_recommendation_id = require_non_empty_identifier(
        recommendation_id,
        "recommendation_id",
    )
    clean_signal_id = clean_optional_identifier(
        signal_id,
        "signal_id",
    )
    parts: tuple[str, ...] = (clean_recommendation_id,)
    if clean_signal_id is not None:
        parts = (
            *parts,
            clean_signal_id,
        )

    return _new_attribution_id(
        prefix="recommendation_attribution",
        timestamp=timestamp,
        parts=parts,
        key=attribution_key,
    )


def new_random_attribution_id(
    prefix: str,
) -> str:
    clean_prefix = require_non_empty_identifier(
        prefix,
        "prefix",
    )
    return f"{clean_prefix}:{uuid4().hex}"


def _new_attribution_id(
    *,
    prefix: str,
    timestamp: datetime,
    parts: tuple[str, ...],
    key: str | None,
) -> str:
    clean_prefix = require_non_empty_identifier(
        prefix,
        "prefix",
    )
    clean_parts = tuple(
        require_non_empty_identifier(
            part,
            "id_part",
        )
        for part in parts
    )
    clean_key = clean_optional_identifier(
        key,
        "key",
    )
    id_parts = [
        clean_prefix,
        *clean_parts,
        timestamp.isoformat(),
    ]
    if clean_key is not None:
        id_parts.append(
            clean_key,
        )

    return ":".join(
        id_parts,
    )


def _set_required_identifier(
    record: object,
    field_name: str,
    value: str,
) -> None:
    object.__setattr__(
        record,
        field_name,
        require_non_empty_identifier(
            value,
            field_name,
        ),
    )


def _set_required_text(
    record: object,
    field_name: str,
    value: str,
) -> None:
    object.__setattr__(
        record,
        field_name,
        _require_non_empty_text(
            value,
            field_name,
        ),
    )


def _set_optional_agent_fields(
    record: object,
) -> None:
    object.__setattr__(
        record,
        "agent_name",
        clean_optional_identifier(
            getattr(record, "agent_name"),
            "agent_name",
        ),
    )
    object.__setattr__(
        record,
        "agent_type",
        clean_optional_identifier(
            getattr(record, "agent_type"),
            "agent_type",
        ),
    )


def _set_optional_scope_fields(
    record: object,
) -> None:
    object.__setattr__(
        record,
        "symbol",
        _clean_optional_symbol(
            getattr(record, "symbol"),
        ),
    )
    object.__setattr__(
        record,
        "universe",
        clean_optional_identifier(
            getattr(record, "universe"),
            "universe",
        ),
    )


def _clean_optional_symbol(
    symbol: str | None,
) -> str | None:
    clean_symbol = clean_optional_identifier(
        symbol,
        "symbol",
    )
    if clean_symbol is None:
        return None

    return clean_symbol.upper()


def _require_non_empty_text(
    value: str,
    field_name: str,
) -> str:
    clean_value = value.strip()
    if not clean_value:
        raise ValueError(f"{field_name} cannot be empty.")

    return clean_value


def _require_non_empty_sources(
    source_records: tuple[PersistenceRecordIdentity, ...],
) -> None:
    if not source_records:
        raise ValueError("source_records cannot be empty.")


def _require_signed_score(
    value: float,
    field_name: str,
) -> None:
    if not -1.0 <= value <= 1.0:
        raise ValueError(f"{field_name} must be between -1.0 and 1.0.")


def _require_ratio(
    value: float,
    field_name: str,
) -> None:
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{field_name} must be between 0.0 and 1.0.")
