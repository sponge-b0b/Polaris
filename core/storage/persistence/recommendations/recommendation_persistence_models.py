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
class RecommendationRecord:
    """
    Typed persistence-boundary record for a curated platform recommendation.

    The recommendation platform remains decision-support oriented: records may
    describe allocation/trade intent and rationale, but they do not represent an
    instruction to execute autonomously.
    """

    recommendation_id: str
    symbol: str
    bias: str
    confidence: float
    created_at: datetime
    lineage: PersistenceLineage = field(default_factory=PersistenceLineage)
    setup_quality: float | None = None
    risk_score: float | None = None
    risk_level: str | None = None
    time_horizon: str | None = None
    status: str | None = None
    entry_context: JsonObject = field(default_factory=dict)
    stop_context: JsonObject = field(default_factory=dict)
    target_context: JsonObject = field(default_factory=dict)
    supporting_signals: tuple[PersistenceRecordIdentity, ...] = ()
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "recommendation_id",
            require_non_empty_identifier(
                self.recommendation_id,
                "recommendation_id",
            ),
        )
        object.__setattr__(
            self,
            "symbol",
            require_non_empty_identifier(
                self.symbol,
                "symbol",
            ).upper(),
        )
        object.__setattr__(
            self,
            "bias",
            require_non_empty_identifier(
                self.bias,
                "bias",
            ),
        )
        object.__setattr__(
            self,
            "risk_level",
            clean_optional_identifier(
                self.risk_level,
                "risk_level",
            ),
        )
        object.__setattr__(
            self,
            "time_horizon",
            clean_optional_identifier(
                self.time_horizon,
                "time_horizon",
            ),
        )
        object.__setattr__(
            self,
            "status",
            clean_optional_identifier(
                self.status,
                "status",
            ),
        )
        _require_score_range(
            self.confidence,
            "confidence",
            minimum=0.0,
            maximum=1.0,
        )
        _require_score_range(
            self.setup_quality,
            "setup_quality",
            minimum=0.0,
            maximum=1.0,
        )
        _require_score_range(
            self.risk_score,
            "risk_score",
            minimum=0.0,
            maximum=1.0,
        )


@dataclass(
    frozen=True,
    slots=True,
)
class RecommendationRationaleRecord:
    """
    Full, untruncated rationale attached to a recommendation.
    """

    rationale_id: str
    recommendation_id: str
    rationale_type: str
    rationale_text: str
    created_at: datetime
    lineage: PersistenceLineage = field(default_factory=PersistenceLineage)
    supporting_signals: tuple[PersistenceRecordIdentity, ...] = ()
    confidence: float | None = None
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "rationale_id",
            require_non_empty_identifier(
                self.rationale_id,
                "rationale_id",
            ),
        )
        object.__setattr__(
            self,
            "recommendation_id",
            require_non_empty_identifier(
                self.recommendation_id,
                "recommendation_id",
            ),
        )
        object.__setattr__(
            self,
            "rationale_type",
            require_non_empty_identifier(
                self.rationale_type,
                "rationale_type",
            ),
        )
        _require_non_empty_text(
            self.rationale_text,
            "rationale_text",
        )
        _require_score_range(
            self.confidence,
            "confidence",
            minimum=0.0,
            maximum=1.0,
        )


@dataclass(
    frozen=True,
    slots=True,
)
class RecommendationOutcomeRecord:
    """
    Human action and outcome record for recommendation auditing.
    """

    outcome_id: str
    recommendation_id: str
    evaluated_at: datetime
    human_action: str | None = None
    outcome: str | None = None
    outcome_return: float | None = None
    outcome_notes: str | None = None
    lineage: PersistenceLineage = field(default_factory=PersistenceLineage)
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "outcome_id",
            require_non_empty_identifier(
                self.outcome_id,
                "outcome_id",
            ),
        )
        object.__setattr__(
            self,
            "recommendation_id",
            require_non_empty_identifier(
                self.recommendation_id,
                "recommendation_id",
            ),
        )
        object.__setattr__(
            self,
            "human_action",
            clean_optional_identifier(
                self.human_action,
                "human_action",
            ),
        )
        object.__setattr__(
            self,
            "outcome",
            clean_optional_identifier(
                self.outcome,
                "outcome",
            ),
        )
        object.__setattr__(
            self,
            "outcome_notes",
            clean_optional_identifier(
                self.outcome_notes,
                "outcome_notes",
            ),
        )


@dataclass(
    frozen=True,
    slots=True,
)
class TradeSetupRecord:
    """
    Broker-agnostic trade setup derived from a recommendation.
    """

    setup_id: str
    symbol: str
    setup_type: str
    bias: str
    created_at: datetime
    lineage: PersistenceLineage = field(default_factory=PersistenceLineage)
    recommendation_id: str | None = None
    setup_quality: float | None = None
    confidence: float | None = None
    risk_score: float | None = None
    risk_reward_ratio: float | None = None
    time_horizon: str | None = None
    entry_context: JsonObject = field(default_factory=dict)
    stop_context: JsonObject = field(default_factory=dict)
    target_context: JsonObject = field(default_factory=dict)
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "setup_id",
            require_non_empty_identifier(
                self.setup_id,
                "setup_id",
            ),
        )
        object.__setattr__(
            self,
            "symbol",
            require_non_empty_identifier(
                self.symbol,
                "symbol",
            ).upper(),
        )
        object.__setattr__(
            self,
            "setup_type",
            require_non_empty_identifier(
                self.setup_type,
                "setup_type",
            ),
        )
        object.__setattr__(
            self,
            "bias",
            require_non_empty_identifier(
                self.bias,
                "bias",
            ),
        )
        object.__setattr__(
            self,
            "recommendation_id",
            clean_optional_identifier(
                self.recommendation_id,
                "recommendation_id",
            ),
        )
        object.__setattr__(
            self,
            "time_horizon",
            clean_optional_identifier(
                self.time_horizon,
                "time_horizon",
            ),
        )
        _require_score_range(
            self.setup_quality,
            "setup_quality",
            minimum=0.0,
            maximum=1.0,
        )
        _require_score_range(
            self.confidence,
            "confidence",
            minimum=0.0,
            maximum=1.0,
        )
        _require_score_range(
            self.risk_score,
            "risk_score",
            minimum=0.0,
            maximum=1.0,
        )
        if self.risk_reward_ratio is not None and self.risk_reward_ratio < 0:
            raise ValueError("risk_reward_ratio cannot be negative.")


@dataclass(
    frozen=True,
    slots=True,
)
class WatchlistItemRecord:
    """
    Curated watchlist entry produced by recommendation intelligence.
    """

    watchlist_item_id: str
    symbol: str
    reason: str
    created_at: datetime
    lineage: PersistenceLineage = field(default_factory=PersistenceLineage)
    recommendation_id: str | None = None
    priority: int = 0
    status: str | None = None
    bias: str | None = None
    confidence: float | None = None
    setup_quality: float | None = None
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "watchlist_item_id",
            require_non_empty_identifier(
                self.watchlist_item_id,
                "watchlist_item_id",
            ),
        )
        object.__setattr__(
            self,
            "symbol",
            require_non_empty_identifier(
                self.symbol,
                "symbol",
            ).upper(),
        )
        object.__setattr__(
            self,
            "reason",
            require_non_empty_identifier(
                self.reason,
                "reason",
            ),
        )
        object.__setattr__(
            self,
            "recommendation_id",
            clean_optional_identifier(
                self.recommendation_id,
                "recommendation_id",
            ),
        )
        object.__setattr__(
            self,
            "status",
            clean_optional_identifier(
                self.status,
                "status",
            ),
        )
        object.__setattr__(
            self,
            "bias",
            clean_optional_identifier(
                self.bias,
                "bias",
            ),
        )
        _require_non_negative(
            self.priority,
            "priority",
        )
        _require_score_range(
            self.confidence,
            "confidence",
            minimum=0.0,
            maximum=1.0,
        )
        _require_score_range(
            self.setup_quality,
            "setup_quality",
            minimum=0.0,
            maximum=1.0,
        )


@dataclass(
    frozen=True,
    slots=True,
)
class RecommendationPersistenceBundle:
    """
    Atomic recommendation persistence payload.
    """

    recommendation: RecommendationRecord
    rationales: tuple[RecommendationRationaleRecord, ...] = ()
    outcomes: tuple[RecommendationOutcomeRecord, ...] = ()
    trade_setups: tuple[TradeSetupRecord, ...] = ()
    watchlist_items: tuple[WatchlistItemRecord, ...] = ()


@dataclass(
    frozen=True,
    slots=True,
)
class RecommendationPersistenceResult:
    """
    Typed result returned by recommendation persistence adapters.
    """

    success: bool
    records_persisted: int = 0
    recommendation_id: str | None = None
    error: str | None = None

    def __post_init__(
        self,
    ) -> None:
        _require_non_negative(
            self.records_persisted,
            "records_persisted",
        )

        if self.success and self.error is not None:
            raise ValueError("successful persistence results cannot include an error.")

        if self.success:
            require_non_empty_identifier(
                self.recommendation_id,
                "recommendation_id",
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
        recommendation_id: str,
        records_persisted: int = 1,
    ) -> RecommendationPersistenceResult:
        return cls(
            success=True,
            records_persisted=records_persisted,
            recommendation_id=recommendation_id,
        )

    @classmethod
    def failed(
        cls,
        error: str,
    ) -> RecommendationPersistenceResult:
        return cls(
            success=False,
            records_persisted=0,
            error=error,
        )


def new_recommendation_id(
    *,
    symbol: str,
    execution_id: str | None = None,
    recommendation_key: str | None = None,
) -> str:
    clean_symbol = require_non_empty_identifier(
        symbol,
        "symbol",
    ).upper()
    clean_execution_id = clean_optional_identifier(
        execution_id,
        "execution_id",
    )
    clean_recommendation_key = clean_optional_identifier(
        recommendation_key,
        "recommendation_key",
    )

    if clean_execution_id is not None:
        parts = [
            "recommendation",
            clean_execution_id,
            clean_symbol,
        ]
        if clean_recommendation_key is not None:
            parts.append(clean_recommendation_key)
        return ":".join(parts)

    return f"recommendation:{clean_symbol}:{uuid4().hex}"


def new_recommendation_child_id(
    *,
    recommendation_id: str,
    child_type: str,
    child_key: str,
) -> str:
    clean_recommendation_id = require_non_empty_identifier(
        recommendation_id,
        "recommendation_id",
    )
    clean_child_type = require_non_empty_identifier(
        child_type,
        "child_type",
    )
    clean_child_key = require_non_empty_identifier(
        child_key,
        "child_key",
    )

    return f"{clean_recommendation_id}:{clean_child_type}:{clean_child_key}"


def _require_non_empty_text(
    value: str | None,
    field_name: str,
) -> None:
    if value is None or not value.strip():
        raise ValueError(f"{field_name} cannot be empty.")


def _require_non_negative(
    value: int,
    field_name: str,
) -> None:
    if value < 0:
        raise ValueError(f"{field_name} cannot be negative.")


def _require_score_range(
    value: float | None,
    field_name: str,
    *,
    minimum: float,
    maximum: float,
) -> None:
    if value is None:
        return

    if value < minimum or value > maximum:
        raise ValueError(f"{field_name} must be between {minimum} and {maximum}.")
