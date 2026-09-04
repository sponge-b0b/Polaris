from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class RagContextQuality(StrEnum):
    CORRECT = "correct"
    INCORRECT = "incorrect"
    AMBIGUOUS = "ambiguous"
    MISSING = "missing"


class RagCorrectiveAction(StrEnum):
    PROCEED = "proceed"
    DISCARD_WEAK_CONTEXT = "discard_weak_context"
    REWRITE = "rewrite"
    WEB_FALLBACK = "web_fallback"
    FAIL_CLOSED = "fail_closed"


@dataclass(frozen=True, slots=True)
class RagContextEvaluation:
    quality: RagContextQuality
    action: RagCorrectiveAction
    retained_context_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RagReflectionScores:
    retrieval_necessity: float
    source_relevance: float
    answer_support: float
    usefulness: float

    def __post_init__(self) -> None:
        for field_name in (
            "retrieval_necessity",
            "source_relevance",
            "answer_support",
            "usefulness",
        ):
            value = getattr(self, field_name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{field_name} must be between 0.0 and 1.0.")

    def to_dict(self) -> dict[str, float]:
        return {
            "retrieval_necessity": self.retrieval_necessity,
            "source_relevance": self.source_relevance,
            "answer_support": self.answer_support,
            "usefulness": self.usefulness,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> RagReflectionScores:
        return cls(
            retrieval_necessity=_required_score(payload, "retrieval_necessity"),
            source_relevance=_required_score(payload, "source_relevance"),
            answer_support=_required_score(payload, "answer_support"),
            usefulness=_required_score(payload, "usefulness"),
        )


@dataclass(frozen=True, slots=True)
class RagSelfReflection:
    scores: RagReflectionScores
    answer_supported: bool
    injection_detected: bool = False


def _required_score(payload: Mapping[str, Any], key: str) -> float:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise TypeError(f"{key} must be numeric.")
    return float(value)
