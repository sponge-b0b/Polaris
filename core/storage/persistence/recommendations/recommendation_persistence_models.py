from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

from core.storage.persistence.lineage import (
    JsonObject,
    PersistenceLineage,
    PersistenceRecordIdentity,
    clean_optional_identifier,
    require_non_empty_identifier,
)
from domain.authority import RiskTier


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
class RecommendationClaimEvidenceLinkRecord:
    """Authoritative recommendation claim-to-decision-evidence-packet link."""

    link_id: str
    recommendation_id: str
    claim_target_id: str
    packet_id: str
    packet_claim_id: str
    risk_tier: RiskTier
    material: bool
    supporting_evidence_ids: tuple[str, ...]
    reconstruction_reference_ids: tuple[str, ...]
    rationale_id: str | None = None
    uncertainty_ids: tuple[str, ...] = ()
    limitation_ids: tuple[str, ...] = ()

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "link_id",
            require_non_empty_identifier(self.link_id, "link_id"),
        )
        object.__setattr__(
            self,
            "recommendation_id",
            require_non_empty_identifier(self.recommendation_id, "recommendation_id"),
        )
        object.__setattr__(
            self,
            "rationale_id",
            clean_optional_identifier(self.rationale_id, "rationale_id"),
        )
        object.__setattr__(
            self,
            "claim_target_id",
            require_non_empty_identifier(self.claim_target_id, "claim_target_id"),
        )
        object.__setattr__(
            self,
            "packet_id",
            require_non_empty_identifier(self.packet_id, "packet_id"),
        )
        object.__setattr__(
            self,
            "packet_claim_id",
            require_non_empty_identifier(self.packet_claim_id, "packet_claim_id"),
        )
        object.__setattr__(
            self,
            "risk_tier",
            _coerce_claim_evidence_link_risk_tier(self.risk_tier),
        )
        if not isinstance(self.material, bool):
            raise ValueError("material must be a boolean.")
        object.__setattr__(
            self,
            "supporting_evidence_ids",
            _clean_identifier_tuple(
                self.supporting_evidence_ids,
                "supporting_evidence_id",
            ),
        )
        object.__setattr__(
            self,
            "reconstruction_reference_ids",
            _clean_identifier_tuple(
                self.reconstruction_reference_ids,
                "reconstruction_reference_id",
            ),
        )
        object.__setattr__(
            self,
            "uncertainty_ids",
            _clean_identifier_tuple(self.uncertainty_ids, "uncertainty_id"),
        )
        object.__setattr__(
            self,
            "limitation_ids",
            _clean_identifier_tuple(self.limitation_ids, "limitation_id"),
        )
        _validate_material_claim_evidence_link(
            material=self.material,
            risk_tier=self.risk_tier,
            supporting_evidence_ids=self.supporting_evidence_ids,
            reconstruction_reference_ids=self.reconstruction_reference_ids,
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
    claim_evidence_links: tuple[RecommendationClaimEvidenceLinkRecord, ...] = ()


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


def new_recommendation_claim_evidence_link_id(
    *,
    recommendation_id: str,
    claim_target_id: str,
    packet_id: str,
    packet_claim_id: str,
    rationale_id: str | None = None,
) -> str:
    """Build a stable recommendation claim evidence link id."""

    id_parts = [
        require_non_empty_identifier(recommendation_id, "recommendation_id"),
        "claim_evidence",
    ]
    clean_rationale_id = clean_optional_identifier(rationale_id, "rationale_id")
    if clean_rationale_id is not None:
        id_parts.append(clean_rationale_id)
    id_parts.extend(
        (
            require_non_empty_identifier(claim_target_id, "claim_target_id"),
            require_non_empty_identifier(packet_id, "packet_id"),
            require_non_empty_identifier(packet_claim_id, "packet_claim_id"),
        )
    )
    return ":".join(id_parts)


def _coerce_claim_evidence_link_risk_tier(value: object) -> RiskTier:
    if isinstance(value, RiskTier):
        risk_tier = value
    elif isinstance(value, str):
        risk_tier = RiskTier(value.strip().lower())
    else:
        raise ValueError("risk_tier must be a RiskTier.")
    if risk_tier not in {RiskTier.ENHANCED, RiskTier.VIGILANT}:
        raise ValueError(
            "claim evidence links require enhanced or vigilant risk tiers."
        )
    return risk_tier


def _clean_identifier_tuple(values: tuple[str, ...], label: str) -> tuple[str, ...]:
    return tuple(require_non_empty_identifier(value, label) for value in values)


def _validate_material_claim_evidence_link(
    *,
    material: bool,
    risk_tier: RiskTier,
    supporting_evidence_ids: tuple[str, ...],
    reconstruction_reference_ids: tuple[str, ...],
) -> None:
    if not material or risk_tier not in {RiskTier.ENHANCED, RiskTier.VIGILANT}:
        return
    if not supporting_evidence_ids:
        raise ValueError(
            "material enhanced and vigilant claim evidence links require "
            "supporting evidence identifiers."
        )
    if not reconstruction_reference_ids:
        raise ValueError(
            "material enhanced and vigilant claim evidence links require "
            "reconstruction reference identifiers."
        )


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
