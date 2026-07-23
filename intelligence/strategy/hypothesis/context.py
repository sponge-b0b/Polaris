from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from json import dumps
from typing import Self

from intelligence.strategy.hypothesis.evidence import StrategyEvidenceItem
from intelligence.strategy.hypothesis.serialization import require_serialized_list


class StrategyEvidenceInputStatus(StrEnum):
    """Quality status for an upstream evidence input."""

    AVAILABLE = "available"
    DEGRADED = "degraded"
    MISSING = "missing"


@dataclass(frozen=True, slots=True)
class StrategyEvidenceInputQuality:
    """Explicit quality flag for one upstream strategy evidence input."""

    input_name: str
    required: bool
    status: StrategyEvidenceInputStatus
    reason: str | None = None
    evidence_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "input_name", _validate_non_empty(self.input_name, "input_name")
        )
        object.__setattr__(self, "status", _parse_input_status(self.status))
        object.__setattr__(
            self,
            "evidence_ids",
            _validate_string_tuple(self.evidence_ids, "evidence_ids"),
        )
        if self.reason is not None:
            object.__setattr__(
                self, "reason", _validate_non_empty(self.reason, "reason")
            )
        if (
            self.status is not StrategyEvidenceInputStatus.AVAILABLE
            and self.reason is None
        ):
            raise ValueError(
                "degraded or missing evidence inputs must include a reason."
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "input_name": self.input_name,
            "required": self.required,
            "status": self.status.value,
            "reason": self.reason,
            "evidence_ids": list(self.evidence_ids),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> Self:
        return cls(
            input_name=_required_string(payload, "input_name"),
            required=_required_bool(payload, "required"),
            status=_parse_input_status(_required_string(payload, "status")),
            reason=_optional_string(payload, "reason"),
            evidence_ids=_required_string_tuple(payload, "evidence_ids"),
        )


@dataclass(frozen=True, slots=True)
class StrategyEvidenceContext:
    """Shared strategy evidence package consumed by all hypothesis perspectives."""

    symbol: str
    required_evidence: tuple[StrategyEvidenceItem, ...]
    optional_evidence: tuple[StrategyEvidenceItem, ...] = ()
    input_quality: tuple[StrategyEvidenceInputQuality, ...] = ()
    as_of: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "symbol", _validate_non_empty(self.symbol, "symbol"))
        if self.as_of is not None:
            object.__setattr__(self, "as_of", _validate_non_empty(self.as_of, "as_of"))
        required_evidence = _validate_evidence_tuple(
            self.required_evidence,
            "required_evidence",
        )
        optional_evidence = _validate_evidence_tuple(
            self.optional_evidence,
            "optional_evidence",
        )
        _validate_unique_evidence_ids(required_evidence, optional_evidence)
        object.__setattr__(
            self,
            "required_evidence",
            tuple(sorted(required_evidence, key=lambda item: item.evidence_id)),
        )
        object.__setattr__(
            self,
            "optional_evidence",
            tuple(sorted(optional_evidence, key=lambda item: item.evidence_id)),
        )
        input_quality = _validate_input_quality_tuple(self.input_quality)
        object.__setattr__(
            self,
            "input_quality",
            tuple(
                sorted(
                    input_quality,
                    key=lambda item: (
                        item.input_name,
                        item.required,
                        item.status.value,
                    ),
                )
            ),
        )

    @property
    def all_evidence(self) -> tuple[StrategyEvidenceItem, ...]:
        return self.required_evidence + self.optional_evidence

    @property
    def has_missing_required_inputs(self) -> bool:
        return any(
            quality.required and quality.status is StrategyEvidenceInputStatus.MISSING
            for quality in self.input_quality
        )

    @property
    def has_degraded_required_inputs(self) -> bool:
        return any(
            quality.required and quality.status is StrategyEvidenceInputStatus.DEGRADED
            for quality in self.input_quality
        )

    def evidence_by_id(self) -> dict[str, StrategyEvidenceItem]:
        return {item.evidence_id: item for item in self.all_evidence}

    def to_dict(self) -> dict[str, object]:
        return {
            "symbol": self.symbol,
            "as_of": self.as_of,
            "required_evidence": [item.to_dict() for item in self.required_evidence],
            "optional_evidence": [item.to_dict() for item in self.optional_evidence],
            "input_quality": [quality.to_dict() for quality in self.input_quality],
            "evidence_fingerprint": self.evidence_fingerprint(),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> Self:
        return cls(
            symbol=_required_string(payload, "symbol"),
            as_of=_optional_string(payload, "as_of"),
            required_evidence=_required_evidence_tuple(payload, "required_evidence"),
            optional_evidence=_required_evidence_tuple(payload, "optional_evidence"),
            input_quality=_required_input_quality_tuple(payload, "input_quality"),
        )

    def to_canonical_json(self) -> str:
        return _canonical_json(self._fingerprint_payload())

    def evidence_fingerprint(self) -> str:
        return sha256(self.to_canonical_json().encode("utf-8")).hexdigest()

    def _fingerprint_payload(self) -> dict[str, object]:
        return {
            "symbol": self.symbol,
            "as_of": self.as_of,
            "required_evidence": [item.to_dict() for item in self.required_evidence],
            "optional_evidence": [item.to_dict() for item in self.optional_evidence],
            "input_quality": [quality.to_dict() for quality in self.input_quality],
        }


def _canonical_json(payload: dict[str, object]) -> str:
    return dumps(payload, sort_keys=True, separators=(",", ":"))


def _parse_input_status(
    value: StrategyEvidenceInputStatus | str,
) -> StrategyEvidenceInputStatus:
    if isinstance(value, StrategyEvidenceInputStatus):
        return value
    try:
        return StrategyEvidenceInputStatus(value.strip().lower())
    except ValueError as exc:
        supported = ", ".join(status.value for status in StrategyEvidenceInputStatus)
        raise ValueError(f"evidence input status must be one of: {supported}.") from exc


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


def _validate_evidence_tuple(
    values: tuple[StrategyEvidenceItem, ...],
    field_name: str,
) -> tuple[StrategyEvidenceItem, ...]:
    if not isinstance(values, tuple):
        raise TypeError(f"{field_name} must be a tuple.")
    for value in values:
        if not isinstance(value, StrategyEvidenceItem):
            raise TypeError(
                f"{field_name} entries must be StrategyEvidenceItem instances."
            )
    return values


def _validate_input_quality_tuple(
    values: tuple[StrategyEvidenceInputQuality, ...],
) -> tuple[StrategyEvidenceInputQuality, ...]:
    if not isinstance(values, tuple):
        raise TypeError("input_quality must be a tuple.")
    for value in values:
        if not isinstance(value, StrategyEvidenceInputQuality):
            raise TypeError(
                "input_quality entries must be StrategyEvidenceInputQuality instances."
            )
    return values


def _validate_unique_evidence_ids(
    required_evidence: tuple[StrategyEvidenceItem, ...],
    optional_evidence: tuple[StrategyEvidenceItem, ...],
) -> None:
    seen: set[str] = set()
    for item in required_evidence + optional_evidence:
        if item.evidence_id in seen:
            raise ValueError(f"duplicate strategy evidence_id: {item.evidence_id}")
        seen.add(item.evidence_id)


def _required_string(payload: dict[str, object], field_name: str) -> str:
    if field_name not in payload:
        raise KeyError(f"missing required field: {field_name}")
    value = payload[field_name]
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string.")
    return value


def _optional_string(payload: dict[str, object], field_name: str) -> str | None:
    value = payload.get(field_name)
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string when provided.")
    return value


def _required_bool(payload: dict[str, object], field_name: str) -> bool:
    if field_name not in payload:
        raise KeyError(f"missing required field: {field_name}")
    value = payload[field_name]
    if not isinstance(value, bool):
        raise TypeError(f"{field_name} must be a boolean.")
    return value


def _required_string_tuple(
    payload: dict[str, object], field_name: str
) -> tuple[str, ...]:
    value = require_serialized_list(payload, field_name)
    return tuple(_list_string(item, field_name) for item in value)


def _required_evidence_tuple(
    payload: dict[str, object],
    field_name: str,
) -> tuple[StrategyEvidenceItem, ...]:
    value = require_serialized_list(payload, field_name)
    return tuple(
        StrategyEvidenceItem.from_dict(_list_mapping(item, field_name))
        for item in value
    )


def _required_input_quality_tuple(
    payload: dict[str, object],
    field_name: str,
) -> tuple[StrategyEvidenceInputQuality, ...]:
    value = require_serialized_list(payload, field_name)
    return tuple(
        StrategyEvidenceInputQuality.from_dict(_list_mapping(item, field_name))
        for item in value
    )


def _list_mapping(value: object, field_name: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError(f"{field_name} entries must be mappings.")
    return {str(key): mapped_value for key, mapped_value in value.items()}


def _list_string(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} entries must be strings.")
    return value
