from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from json import dumps
from math import isclose
from typing import Self

from intelligence.strategy.hypothesis.contracts import Confidence
from intelligence.strategy.hypothesis.contracts import DirectionalBias
from intelligence.strategy.hypothesis.contracts import StrategyPerspective
from intelligence.strategy.hypothesis.contracts import parse_strategy_perspective
from intelligence.strategy.hypothesis.contracts import validate_confidence
from intelligence.strategy.hypothesis.contracts import validate_directional_bias


class StrategySynthesisSelectionStatus(str, Enum):
    """Canonical selection status for a strategy hypothesis candidate."""

    CANDIDATE = "candidate"
    SELECTED = "selected"
    REJECTED = "rejected"
    INVALIDATED = "invalidated"
    TIED = "tied"
    DEGRADED = "degraded"


class StrategySynthesisDegradedReason(str, Enum):
    """Typed reasons why synthesis cannot produce a clean selected decision."""

    MISSING_HYPOTHESIS = "missing_hypothesis"
    MISSING_PERSPECTIVE_WEIGHT = "missing_perspective_weight"
    ALL_HYPOTHESES_INVALIDATED = "all_hypotheses_invalidated"
    TIED_CANDIDATES = "tied_candidates"
    LOW_CONFIDENCE = "low_confidence"
    CONFLICTING_EVIDENCE = "conflicting_evidence"
    DATA_QUALITY_DEGRADED = "data_quality_degraded"
    SYNTHESIS_INPUT_UNAVAILABLE = "synthesis_input_unavailable"


@dataclass(frozen=True, slots=True)
class StrategyHypothesisEvaluation:
    """Typed synthesis evaluation for one strategy perspective hypothesis."""

    perspective: StrategyPerspective
    perspective_weight: float
    contradiction_burden: float
    assumption_support: float
    invalidated: bool
    candidate_score: float
    posterior_weight: float
    rank: int
    selection_status: StrategySynthesisSelectionStatus
    degraded_reasons: tuple[StrategySynthesisDegradedReason, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "perspective",
            parse_strategy_perspective(self.perspective),
        )
        object.__setattr__(
            self,
            "perspective_weight",
            _validate_unit_interval(self.perspective_weight, "perspective_weight"),
        )
        object.__setattr__(
            self,
            "contradiction_burden",
            _validate_unit_interval(
                self.contradiction_burden,
                "contradiction_burden",
            ),
        )
        object.__setattr__(
            self,
            "assumption_support",
            _validate_unit_interval(self.assumption_support, "assumption_support"),
        )
        object.__setattr__(self, "invalidated", bool(self.invalidated))
        object.__setattr__(
            self,
            "candidate_score",
            _validate_unit_interval(self.candidate_score, "candidate_score"),
        )
        object.__setattr__(
            self,
            "posterior_weight",
            _validate_unit_interval(self.posterior_weight, "posterior_weight"),
        )
        object.__setattr__(self, "rank", _validate_rank(self.rank))
        object.__setattr__(
            self,
            "selection_status",
            _parse_selection_status(self.selection_status),
        )
        object.__setattr__(
            self,
            "degraded_reasons",
            _parse_degraded_reasons(self.degraded_reasons),
        )

    def with_outcome(
        self,
        *,
        posterior_weight: float,
        rank: int,
        selection_status: StrategySynthesisSelectionStatus,
        degraded_reasons: tuple[StrategySynthesisDegradedReason, ...] | None = None,
    ) -> StrategyHypothesisEvaluation:
        return StrategyHypothesisEvaluation(
            perspective=self.perspective,
            perspective_weight=self.perspective_weight,
            contradiction_burden=self.contradiction_burden,
            assumption_support=self.assumption_support,
            invalidated=self.invalidated,
            candidate_score=self.candidate_score,
            posterior_weight=posterior_weight,
            rank=rank,
            selection_status=selection_status,
            degraded_reasons=(
                self.degraded_reasons if degraded_reasons is None else degraded_reasons
            ),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "perspective": self.perspective.value,
            "perspective_weight": self.perspective_weight,
            "contradiction_burden": self.contradiction_burden,
            "assumption_support": self.assumption_support,
            "invalidated": self.invalidated,
            "candidate_score": self.candidate_score,
            "posterior_weight": self.posterior_weight,
            "rank": self.rank,
            "selection_status": self.selection_status.value,
            "degraded_reasons": [reason.value for reason in self.degraded_reasons],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> Self:
        return cls(
            perspective=parse_strategy_perspective(
                _required_string(payload, "perspective")
            ),
            perspective_weight=_required_float(payload, "perspective_weight"),
            contradiction_burden=_required_float(payload, "contradiction_burden"),
            assumption_support=_required_float(payload, "assumption_support"),
            invalidated=_required_bool(payload, "invalidated"),
            candidate_score=_required_float(payload, "candidate_score"),
            posterior_weight=_required_float(payload, "posterior_weight"),
            rank=_required_int(payload, "rank"),
            selection_status=_parse_selection_status(
                _required_string(payload, "selection_status")
            ),
            degraded_reasons=_required_degraded_reason_tuple(
                payload,
                "degraded_reasons",
            ),
        )

    def to_canonical_json(self) -> str:
        return _canonical_json(self.to_dict())


@dataclass(frozen=True, slots=True)
class StrategySynthesisDecision:
    """Complete typed synthesis decision produced from hypothesis evaluations."""

    selected_perspective: StrategyPerspective | None
    selection_status: StrategySynthesisSelectionStatus
    directional_score: DirectionalBias
    confidence: Confidence
    regime: str
    uncertainty: float
    evaluations: tuple[StrategyHypothesisEvaluation, ...]
    degraded_reasons: tuple[StrategySynthesisDegradedReason, ...]
    thesis: str
    signals: tuple[str, ...]
    risks: tuple[str, ...]
    recommendations: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.selected_perspective is not None:
            object.__setattr__(
                self,
                "selected_perspective",
                parse_strategy_perspective(self.selected_perspective),
            )
        object.__setattr__(
            self,
            "selection_status",
            _parse_selection_status(self.selection_status),
        )
        object.__setattr__(
            self,
            "directional_score",
            validate_directional_bias(self.directional_score),
        )
        object.__setattr__(self, "confidence", validate_confidence(self.confidence))
        object.__setattr__(self, "regime", _validate_non_empty(self.regime, "regime"))
        object.__setattr__(
            self,
            "uncertainty",
            _validate_unit_interval(self.uncertainty, "uncertainty"),
        )
        object.__setattr__(
            self,
            "evaluations",
            _validate_evaluation_tuple(self.evaluations),
        )
        object.__setattr__(
            self,
            "degraded_reasons",
            _parse_degraded_reasons(self.degraded_reasons),
        )
        object.__setattr__(self, "thesis", _validate_non_empty(self.thesis, "thesis"))
        object.__setattr__(
            self, "signals", _validate_string_tuple(self.signals, "signals")
        )
        object.__setattr__(self, "risks", _validate_string_tuple(self.risks, "risks"))
        object.__setattr__(
            self,
            "recommendations",
            _validate_string_tuple(self.recommendations, "recommendations"),
        )

    @classmethod
    def from_evaluations(
        cls,
        *,
        evaluations: tuple[StrategyHypothesisEvaluation, ...],
        directional_score: float,
        confidence: float,
        regime: str,
        uncertainty: float,
        thesis: str,
        signals: tuple[str, ...] = (),
        risks: tuple[str, ...] = (),
        recommendations: tuple[str, ...] = (),
        degraded_reasons: tuple[StrategySynthesisDegradedReason, ...] = (),
    ) -> StrategySynthesisDecision:
        normalized = normalize_strategy_hypothesis_evaluations(evaluations)
        selected = tuple(
            evaluation
            for evaluation in normalized
            if evaluation.selection_status is StrategySynthesisSelectionStatus.SELECTED
        )
        typed_reasons = set(_parse_degraded_reasons(degraded_reasons))
        if all(evaluation.invalidated for evaluation in normalized):
            typed_reasons.add(
                StrategySynthesisDegradedReason.ALL_HYPOTHESES_INVALIDATED
            )
        if any(
            evaluation.selection_status is StrategySynthesisSelectionStatus.TIED
            for evaluation in normalized
        ):
            typed_reasons.add(StrategySynthesisDegradedReason.TIED_CANDIDATES)

        selection_status = (
            StrategySynthesisSelectionStatus.SELECTED
            if len(selected) == 1 and not typed_reasons
            else StrategySynthesisSelectionStatus.DEGRADED
        )
        selected_perspective = selected[0].perspective if len(selected) == 1 else None
        return cls(
            selected_perspective=selected_perspective,
            selection_status=selection_status,
            directional_score=directional_score,
            confidence=confidence,
            regime=regime,
            uncertainty=uncertainty,
            evaluations=normalized,
            degraded_reasons=tuple(
                sorted(typed_reasons, key=lambda reason: reason.value)
            ),
            thesis=thesis,
            signals=signals,
            risks=risks,
            recommendations=recommendations,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "selected_perspective": (
                None
                if self.selected_perspective is None
                else self.selected_perspective.value
            ),
            "selection_status": self.selection_status.value,
            "directional_score": self.directional_score,
            "confidence": self.confidence,
            "regime": self.regime,
            "uncertainty": self.uncertainty,
            "evaluations": [evaluation.to_dict() for evaluation in self.evaluations],
            "degraded_reasons": [reason.value for reason in self.degraded_reasons],
            "thesis": self.thesis,
            "signals": list(self.signals),
            "risks": list(self.risks),
            "recommendations": list(self.recommendations),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> Self:
        selected = payload.get("selected_perspective")
        if selected is not None and not isinstance(selected, str):
            raise TypeError("selected_perspective must be a string or None.")
        return cls(
            selected_perspective=(
                None if selected is None else parse_strategy_perspective(selected)
            ),
            selection_status=_parse_selection_status(
                _required_string(payload, "selection_status")
            ),
            directional_score=_required_float(payload, "directional_score"),
            confidence=_required_float(payload, "confidence"),
            regime=_required_string(payload, "regime"),
            uncertainty=_required_float(payload, "uncertainty"),
            evaluations=_required_evaluation_tuple(payload, "evaluations"),
            degraded_reasons=_required_degraded_reason_tuple(
                payload,
                "degraded_reasons",
            ),
            thesis=_required_string(payload, "thesis"),
            signals=_required_string_tuple(payload, "signals"),
            risks=_required_string_tuple(payload, "risks"),
            recommendations=_required_string_tuple(payload, "recommendations"),
        )

    def to_canonical_json(self) -> str:
        return _canonical_json(self.to_dict())


def normalize_strategy_hypothesis_evaluations(
    evaluations: tuple[StrategyHypothesisEvaluation, ...],
) -> tuple[StrategyHypothesisEvaluation, ...]:
    """Rank evaluations and normalize valid candidate scores into posteriors."""

    if not evaluations:
        raise ValueError("evaluations must not be empty.")

    ordered = tuple(
        sorted(
            evaluations,
            key=lambda item: (-item.candidate_score, item.perspective.value),
        )
    )
    rank_by_perspective: dict[StrategyPerspective, int] = {}
    previous_score: float | None = None
    current_rank = 0
    for index, evaluation in enumerate(ordered, start=1):
        if previous_score is None or not isclose(
            evaluation.candidate_score,
            previous_score,
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            current_rank = index
            previous_score = evaluation.candidate_score
        rank_by_perspective[evaluation.perspective] = current_rank

    valid = tuple(
        evaluation for evaluation in evaluations if not evaluation.invalidated
    )
    if not valid:
        return tuple(
            evaluation.with_outcome(
                posterior_weight=0.0,
                rank=rank_by_perspective[evaluation.perspective],
                selection_status=StrategySynthesisSelectionStatus.INVALIDATED,
                degraded_reasons=_append_unique_reason(
                    evaluation.degraded_reasons,
                    StrategySynthesisDegradedReason.ALL_HYPOTHESES_INVALIDATED,
                ),
            )
            for evaluation in evaluations
        )

    score_total = sum(evaluation.candidate_score for evaluation in valid)
    if score_total <= 0.0:
        posterior_by_perspective = {
            evaluation.perspective: 1.0 / len(valid) for evaluation in valid
        }
    else:
        posterior_by_perspective = {
            evaluation.perspective: evaluation.candidate_score / score_total
            for evaluation in valid
        }

    max_posterior = max(posterior_by_perspective.values())
    top_perspectives = frozenset(
        perspective
        for perspective, posterior in posterior_by_perspective.items()
        if isclose(posterior, max_posterior, rel_tol=0.0, abs_tol=1e-12)
    )
    tied = len(top_perspectives) > 1

    normalized: list[StrategyHypothesisEvaluation] = []
    for evaluation in evaluations:
        rank = rank_by_perspective[evaluation.perspective]
        if evaluation.invalidated:
            normalized.append(
                evaluation.with_outcome(
                    posterior_weight=0.0,
                    rank=rank,
                    selection_status=StrategySynthesisSelectionStatus.INVALIDATED,
                )
            )
            continue

        posterior_weight = posterior_by_perspective[evaluation.perspective]
        is_top = evaluation.perspective in top_perspectives
        if tied and is_top:
            status = StrategySynthesisSelectionStatus.TIED
            reasons = _append_unique_reason(
                evaluation.degraded_reasons,
                StrategySynthesisDegradedReason.TIED_CANDIDATES,
            )
        elif is_top:
            status = StrategySynthesisSelectionStatus.SELECTED
            reasons = evaluation.degraded_reasons
        else:
            status = StrategySynthesisSelectionStatus.REJECTED
            reasons = evaluation.degraded_reasons
        normalized.append(
            evaluation.with_outcome(
                posterior_weight=posterior_weight,
                rank=rank,
                selection_status=status,
                degraded_reasons=reasons,
            )
        )
    return tuple(normalized)


def _append_unique_reason(
    reasons: tuple[StrategySynthesisDegradedReason, ...],
    reason: StrategySynthesisDegradedReason,
) -> tuple[StrategySynthesisDegradedReason, ...]:
    parsed = list(_parse_degraded_reasons(reasons))
    if reason not in parsed:
        parsed.append(reason)
    return tuple(parsed)


def _validate_unit_interval(value: float, field_name: str) -> float:
    return validate_confidence(value, field_name=field_name)


def _validate_rank(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("rank must be an integer.")
    if value < 0:
        raise ValueError("rank must be greater than or equal to 0.")
    return value


def _parse_selection_status(
    value: StrategySynthesisSelectionStatus | str,
) -> StrategySynthesisSelectionStatus:
    if isinstance(value, StrategySynthesisSelectionStatus):
        return value
    try:
        return StrategySynthesisSelectionStatus(value.strip().lower())
    except ValueError as exc:
        supported = ", ".join(
            status.value for status in StrategySynthesisSelectionStatus
        )
        raise ValueError(f"selection_status must be one of: {supported}.") from exc


def _parse_degraded_reason(
    value: StrategySynthesisDegradedReason | str,
) -> StrategySynthesisDegradedReason:
    if isinstance(value, StrategySynthesisDegradedReason):
        return value
    try:
        return StrategySynthesisDegradedReason(value.strip().lower())
    except ValueError as exc:
        supported = ", ".join(
            reason.value for reason in StrategySynthesisDegradedReason
        )
        raise ValueError(f"degraded reason must be one of: {supported}.") from exc


def _parse_degraded_reasons(
    values: tuple[StrategySynthesisDegradedReason, ...] | tuple[str, ...],
) -> tuple[StrategySynthesisDegradedReason, ...]:
    if not isinstance(values, tuple):
        raise TypeError("degraded_reasons must be a tuple.")
    return tuple(_parse_degraded_reason(value) for value in values)


def _validate_non_empty(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string.")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty.")
    return normalized


def _validate_string_tuple(values: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise TypeError(f"{field_name} must be a tuple.")
    return tuple(_validate_non_empty(value, field_name) for value in values)


def _validate_evaluation_tuple(
    values: tuple[StrategyHypothesisEvaluation, ...],
) -> tuple[StrategyHypothesisEvaluation, ...]:
    if not isinstance(values, tuple):
        raise TypeError("evaluations must be a tuple.")
    if not values:
        raise ValueError("evaluations must not be empty.")
    for value in values:
        if not isinstance(value, StrategyHypothesisEvaluation):
            raise TypeError(
                "evaluations entries must be StrategyHypothesisEvaluation instances."
            )
    return values


def _canonical_json(payload: dict[str, object]) -> str:
    return dumps(payload, sort_keys=True, separators=(",", ":"))


def _required_string(payload: dict[str, object], field_name: str) -> str:
    if field_name not in payload:
        raise KeyError(f"missing required field: {field_name}")
    value = payload[field_name]
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string.")
    return value


def _required_float(payload: dict[str, object], field_name: str) -> float:
    if field_name not in payload:
        raise KeyError(f"missing required field: {field_name}")
    value = payload[field_name]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be numeric.")
    return float(value)


def _required_bool(payload: dict[str, object], field_name: str) -> bool:
    if field_name not in payload:
        raise KeyError(f"missing required field: {field_name}")
    value = payload[field_name]
    if not isinstance(value, bool):
        raise TypeError(f"{field_name} must be a boolean.")
    return value


def _required_int(payload: dict[str, object], field_name: str) -> int:
    if field_name not in payload:
        raise KeyError(f"missing required field: {field_name}")
    value = payload[field_name]
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an integer.")
    return value


def _required_string_tuple(
    payload: dict[str, object],
    field_name: str,
) -> tuple[str, ...]:
    if field_name not in payload:
        raise KeyError(f"missing required field: {field_name}")
    value = payload[field_name]
    if not isinstance(value, list):
        raise TypeError(f"{field_name} must be a list in serialized payloads.")
    strings: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise TypeError(f"{field_name} entries must be strings.")
        strings.append(_validate_non_empty(item, field_name))
    return tuple(strings)


def _required_degraded_reason_tuple(
    payload: dict[str, object],
    field_name: str,
) -> tuple[StrategySynthesisDegradedReason, ...]:
    if field_name not in payload:
        raise KeyError(f"missing required field: {field_name}")
    value = payload[field_name]
    if not isinstance(value, list):
        raise TypeError(f"{field_name} must be a list in serialized payloads.")
    reasons: list[StrategySynthesisDegradedReason] = []
    for item in value:
        if not isinstance(item, str):
            raise TypeError(f"{field_name} entries must be strings.")
        reasons.append(_parse_degraded_reason(item))
    return tuple(reasons)


def _required_evaluation_tuple(
    payload: dict[str, object],
    field_name: str,
) -> tuple[StrategyHypothesisEvaluation, ...]:
    if field_name not in payload:
        raise KeyError(f"missing required field: {field_name}")
    value = payload[field_name]
    if not isinstance(value, list):
        raise TypeError(f"{field_name} must be a list in serialized payloads.")
    evaluations: list[StrategyHypothesisEvaluation] = []
    for item in value:
        if not isinstance(item, dict):
            raise TypeError(f"{field_name} entries must be dictionaries.")
        evaluations.append(
            StrategyHypothesisEvaluation.from_dict(
                {str(key): mapped_value for key, mapped_value in item.items()}
            )
        )
    return tuple(evaluations)
