from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from uuid import uuid4

from core.storage.persistence.lineage import JsonObject
from core.storage.persistence.lineage import PersistenceLineage
from core.storage.persistence.lineage import clean_optional_identifier
from core.storage.persistence.lineage import require_non_empty_identifier


@dataclass(frozen=True, slots=True)
class StrategyHypothesisRecord:
    """Typed persistence-boundary record for one strategy perspective hypothesis."""

    hypothesis_id: str
    symbol: str
    perspective: str
    thesis: str
    directional_bias: float
    hypothesis_strength: float
    confidence: float
    evidence_fingerprint: str
    created_at: datetime
    lineage: PersistenceLineage = field(default_factory=PersistenceLineage)
    horizon: str | None = None
    as_of: datetime | None = None
    invalidated: bool = False
    supporting_evidence: tuple[JsonObject, ...] = ()
    contradicting_evidence: tuple[JsonObject, ...] = ()
    key_assumptions: tuple[JsonObject, ...] = ()
    invalidation_conditions: tuple[JsonObject, ...] = ()
    risks: tuple[str, ...] = ()
    recommendations: tuple[str, ...] = ()
    data_quality_flags: tuple[str, ...] = ()
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "hypothesis_id",
            require_non_empty_identifier(self.hypothesis_id, "hypothesis_id"),
        )
        object.__setattr__(
            self,
            "symbol",
            require_non_empty_identifier(self.symbol, "symbol").upper(),
        )
        object.__setattr__(
            self,
            "perspective",
            require_non_empty_identifier(self.perspective, "perspective"),
        )
        object.__setattr__(
            self,
            "thesis",
            require_non_empty_identifier(self.thesis, "thesis"),
        )
        object.__setattr__(
            self,
            "evidence_fingerprint",
            require_non_empty_identifier(
                self.evidence_fingerprint,
                "evidence_fingerprint",
            ),
        )
        object.__setattr__(
            self,
            "horizon",
            clean_optional_identifier(self.horizon, "horizon"),
        )
        object.__setattr__(self, "invalidated", bool(self.invalidated))
        object.__setattr__(self, "risks", _string_tuple(self.risks, "risks"))
        object.__setattr__(
            self,
            "recommendations",
            _string_tuple(self.recommendations, "recommendations"),
        )
        object.__setattr__(
            self,
            "data_quality_flags",
            _string_tuple(self.data_quality_flags, "data_quality_flags"),
        )
        _require_score_range(self.hypothesis_strength, "hypothesis_strength")
        _require_score_range(self.confidence, "confidence")
        if self.directional_bias < -1.0 or self.directional_bias > 1.0:
            raise ValueError("directional_bias must be between -1.0 and 1.0.")


@dataclass(frozen=True, slots=True)
class StrategySynthesisDecisionRecord:
    """Typed persistence-boundary record for a synthesized strategy decision."""

    decision_id: str
    symbol: str
    selection_status: str
    directional_score: float
    confidence: float
    regime: str
    uncertainty: float
    thesis: str
    evidence_fingerprint: str
    created_at: datetime
    lineage: PersistenceLineage = field(default_factory=PersistenceLineage)
    selected_perspective: str | None = None
    horizon: str | None = None
    as_of: datetime | None = None
    signals: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    recommendations: tuple[str, ...] = ()
    degraded_reasons: tuple[str, ...] = ()
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "decision_id",
            require_non_empty_identifier(self.decision_id, "decision_id"),
        )
        object.__setattr__(
            self,
            "symbol",
            require_non_empty_identifier(self.symbol, "symbol").upper(),
        )
        object.__setattr__(
            self,
            "selection_status",
            require_non_empty_identifier(self.selection_status, "selection_status"),
        )
        object.__setattr__(
            self,
            "regime",
            require_non_empty_identifier(self.regime, "regime"),
        )
        object.__setattr__(
            self,
            "thesis",
            require_non_empty_identifier(self.thesis, "thesis"),
        )
        object.__setattr__(
            self,
            "evidence_fingerprint",
            require_non_empty_identifier(
                self.evidence_fingerprint,
                "evidence_fingerprint",
            ),
        )
        object.__setattr__(
            self,
            "selected_perspective",
            clean_optional_identifier(
                self.selected_perspective, "selected_perspective"
            ),
        )
        object.__setattr__(
            self,
            "horizon",
            clean_optional_identifier(self.horizon, "horizon"),
        )
        object.__setattr__(self, "signals", _string_tuple(self.signals, "signals"))
        object.__setattr__(self, "risks", _string_tuple(self.risks, "risks"))
        object.__setattr__(
            self,
            "recommendations",
            _string_tuple(self.recommendations, "recommendations"),
        )
        object.__setattr__(
            self,
            "degraded_reasons",
            _string_tuple(self.degraded_reasons, "degraded_reasons"),
        )
        if self.directional_score < -1.0 or self.directional_score > 1.0:
            raise ValueError("directional_score must be between -1.0 and 1.0.")
        _require_score_range(self.confidence, "confidence")
        _require_score_range(self.uncertainty, "uncertainty")


@dataclass(frozen=True, slots=True)
class StrategyHypothesisEvaluationRecord:
    """Typed persistence-boundary record linking a decision to a hypothesis."""

    evaluation_id: str
    decision_id: str
    symbol: str
    perspective: str
    perspective_weight: float
    contradiction_burden: float
    assumption_support: float
    invalidated: bool
    candidate_score: float
    posterior_weight: float
    rank: int
    selection_status: str
    evidence_fingerprint: str
    created_at: datetime
    lineage: PersistenceLineage = field(default_factory=PersistenceLineage)
    hypothesis_id: str | None = None
    horizon: str | None = None
    as_of: datetime | None = None
    degraded_reasons: tuple[str, ...] = ()
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "evaluation_id",
            require_non_empty_identifier(self.evaluation_id, "evaluation_id"),
        )
        object.__setattr__(
            self,
            "decision_id",
            require_non_empty_identifier(self.decision_id, "decision_id"),
        )
        object.__setattr__(
            self,
            "symbol",
            require_non_empty_identifier(self.symbol, "symbol").upper(),
        )
        object.__setattr__(
            self,
            "perspective",
            require_non_empty_identifier(self.perspective, "perspective"),
        )
        object.__setattr__(
            self,
            "selection_status",
            require_non_empty_identifier(self.selection_status, "selection_status"),
        )
        object.__setattr__(
            self,
            "evidence_fingerprint",
            require_non_empty_identifier(
                self.evidence_fingerprint,
                "evidence_fingerprint",
            ),
        )
        object.__setattr__(
            self,
            "hypothesis_id",
            clean_optional_identifier(self.hypothesis_id, "hypothesis_id"),
        )
        object.__setattr__(
            self,
            "horizon",
            clean_optional_identifier(self.horizon, "horizon"),
        )
        object.__setattr__(self, "invalidated", bool(self.invalidated))
        object.__setattr__(
            self,
            "degraded_reasons",
            _string_tuple(self.degraded_reasons, "degraded_reasons"),
        )
        for field_name, value in (
            ("perspective_weight", self.perspective_weight),
            ("contradiction_burden", self.contradiction_burden),
            ("assumption_support", self.assumption_support),
            ("candidate_score", self.candidate_score),
            ("posterior_weight", self.posterior_weight),
        ):
            _require_score_range(value, field_name)
        if self.rank < 0:
            raise ValueError("rank cannot be negative.")


@dataclass(frozen=True, slots=True)
class StrategyHypothesisPersistenceResult:
    """Typed result for standalone strategy hypothesis persistence."""

    success: bool
    records_persisted: int = 0
    hypothesis_ids: tuple[str, ...] = ()
    error: str | None = None

    def __post_init__(self) -> None:
        if self.records_persisted < 0:
            raise ValueError("records_persisted cannot be negative.")
        object.__setattr__(self, "hypothesis_ids", tuple(self.hypothesis_ids))
        if self.success and self.error is not None:
            raise ValueError("successful persistence results cannot include an error.")
        if self.success and not self.hypothesis_ids:
            raise ValueError(
                "successful hypothesis persistence requires hypothesis_ids."
            )
        if not self.success:
            require_non_empty_identifier(self.error, "error")

    @classmethod
    def succeeded(
        cls,
        *,
        hypothesis_ids: tuple[str, ...],
        records_persisted: int | None = None,
    ) -> StrategyHypothesisPersistenceResult:
        return cls(
            success=True,
            hypothesis_ids=hypothesis_ids,
            records_persisted=len(hypothesis_ids)
            if records_persisted is None
            else records_persisted,
        )

    @classmethod
    def failed(cls, error: str) -> StrategyHypothesisPersistenceResult:
        return cls(success=False, error=error)


@dataclass(frozen=True, slots=True)
class StrategyPersistenceBundle:
    """Atomic strategy persistence payload for hypotheses, decision, and lineage."""

    decision: StrategySynthesisDecisionRecord
    hypotheses: tuple[StrategyHypothesisRecord, ...] = ()
    evaluations: tuple[StrategyHypothesisEvaluationRecord, ...] = ()


@dataclass(frozen=True, slots=True)
class StrategyPersistenceResult:
    """Typed result returned by strategy persistence adapters."""

    success: bool
    records_persisted: int = 0
    decision_id: str | None = None
    error: str | None = None

    def __post_init__(self) -> None:
        if self.records_persisted < 0:
            raise ValueError("records_persisted cannot be negative.")
        if self.success and self.error is not None:
            raise ValueError("successful persistence results cannot include an error.")
        if self.success:
            require_non_empty_identifier(self.decision_id, "decision_id")
        if not self.success:
            require_non_empty_identifier(self.error, "error")

    @classmethod
    def succeeded(
        cls,
        *,
        decision_id: str,
        records_persisted: int = 1,
    ) -> StrategyPersistenceResult:
        return cls(
            success=True,
            decision_id=decision_id,
            records_persisted=records_persisted,
        )

    @classmethod
    def failed(cls, error: str) -> StrategyPersistenceResult:
        return cls(success=False, error=error)


def new_strategy_hypothesis_id(
    *,
    symbol: str,
    perspective: str,
    evidence_fingerprint: str,
    execution_id: str | None = None,
) -> str:
    clean_symbol = require_non_empty_identifier(symbol, "symbol").upper()
    clean_perspective = require_non_empty_identifier(perspective, "perspective")
    clean_fingerprint = require_non_empty_identifier(
        evidence_fingerprint,
        "evidence_fingerprint",
    )
    clean_execution_id = clean_optional_identifier(execution_id, "execution_id")
    if clean_execution_id is not None:
        return ":".join(
            (
                "strategy_hypothesis",
                clean_execution_id,
                clean_symbol,
                clean_perspective,
                clean_fingerprint,
            )
        )
    return f"strategy_hypothesis:{clean_symbol}:{clean_perspective}:{uuid4().hex}"


def new_strategy_decision_id(
    *,
    symbol: str,
    evidence_fingerprint: str,
    execution_id: str | None = None,
    decision_key: str | None = None,
) -> str:
    clean_symbol = require_non_empty_identifier(symbol, "symbol").upper()
    clean_fingerprint = require_non_empty_identifier(
        evidence_fingerprint,
        "evidence_fingerprint",
    )
    clean_execution_id = clean_optional_identifier(execution_id, "execution_id")
    clean_decision_key = clean_optional_identifier(decision_key, "decision_key")
    if clean_execution_id is not None:
        parts = ["strategy_decision", clean_execution_id, clean_symbol]
        if clean_decision_key is not None:
            parts.append(clean_decision_key)
        parts.append(clean_fingerprint)
        return ":".join(parts)
    return f"strategy_decision:{clean_symbol}:{uuid4().hex}"


def new_strategy_evaluation_id(
    *,
    decision_id: str,
    perspective: str,
) -> str:
    clean_decision_id = require_non_empty_identifier(decision_id, "decision_id")
    clean_perspective = require_non_empty_identifier(perspective, "perspective")
    return f"{clean_decision_id}:evaluation:{clean_perspective}"


def _require_score_range(value: float, field_name: str) -> None:
    if value < 0.0 or value > 1.0:
        raise ValueError(f"{field_name} must be between 0.0 and 1.0.")


def _string_tuple(values: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise TypeError(f"{field_name} must be a tuple.")
    return tuple(require_non_empty_identifier(value, field_name) for value in values)
