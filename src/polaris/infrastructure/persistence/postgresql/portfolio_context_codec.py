"""Closed JSON encoding for Portfolio context owner history."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import cast
from uuid import UUID

from polaris.application.evidence.context_versions import ContextContribution
from polaris.application.portfolio_context import (
    PortfolioContextCommit,
    PortfolioContextFactAct,
    PortfolioContextSelectionAct,
)
from polaris.domain.configuration.evidence_requirements import InvestmentHorizon
from polaris.domain.decisions.facts import InvestmentDecisionId
from polaris.domain.evidence.context_versions import (
    BasisScopeKey,
    ContextSelectionRole,
    InvestmentMandateId,
    InvestmentMandateRevision,
    InvestmentMandateVersionRef,
    InvestmentStrategyId,
    InvestmentStrategyRevision,
    InvestmentStrategyVersionRef,
    PortfolioBoundaryId,
    PortfolioBoundaryRevision,
    PortfolioBoundaryVersionRef,
    PortfolioStateRevision,
    PortfolioStateVersionRef,
    ProjectedPortfolioStateId,
    ProjectedPortfolioStateRevision,
    ProjectedPortfolioStateVersionRef,
)
from polaris.domain.evidence.judgments import (
    ClaimId,
    ClaimSpecificEvidenceScope,
    DecisionEvaluationRef,
    EvidenceUse,
    HumanInvestmentDecisionRef,
    InvestmentHypothesisRef,
    InvestmentRecommendationRef,
    InvestmentViewRef,
    JudgmentWideEvidenceScope,
    LessonRef,
    MeaningfulChallengeResultRef,
    PortfolioRiskAssessmentRef,
    ProjectedPortfolioConsequenceRef,
    RecommendationWithholdingJudgmentRef,
)
from polaris.domain.portfolio import (
    FinancialInstrumentId,
    PortfolioId,
    PortfolioSource,
    PortfolioState,
    PortfolioStateId,
    RecordedPortfolioState,
)
from polaris.domain.portfolio_context import (
    ActualPortfolioStateMeaning,
    InvestmentMandateMeaning,
    InvestmentStrategyMeaning,
    MandateMember,
    MandateMemberKind,
    MandateMemberRef,
    PortfolioBoundaryMeaning,
    ProjectedPortfolioStateMeaning,
)

_TYPES = {
    item.__name__: item
    for item in (
        PortfolioContextCommit,
        PortfolioContextFactAct,
        PortfolioContextSelectionAct,
        BasisScopeKey,
        InvestmentDecisionId,
        JudgmentWideEvidenceScope,
        ClaimSpecificEvidenceScope,
        ClaimId,
        InvestmentHypothesisRef,
        InvestmentViewRef,
        MeaningfulChallengeResultRef,
        ProjectedPortfolioConsequenceRef,
        PortfolioRiskAssessmentRef,
        InvestmentRecommendationRef,
        RecommendationWithholdingJudgmentRef,
        HumanInvestmentDecisionRef,
        DecisionEvaluationRef,
        LessonRef,
        PortfolioBoundaryId,
        PortfolioBoundaryRevision,
        PortfolioBoundaryVersionRef,
        PortfolioStateId,
        PortfolioStateRevision,
        PortfolioStateVersionRef,
        ProjectedPortfolioStateId,
        ProjectedPortfolioStateRevision,
        ProjectedPortfolioStateVersionRef,
        InvestmentMandateId,
        InvestmentMandateRevision,
        InvestmentMandateVersionRef,
        InvestmentStrategyId,
        InvestmentStrategyRevision,
        InvestmentStrategyVersionRef,
        PortfolioBoundaryMeaning,
        ActualPortfolioStateMeaning,
        ProjectedPortfolioStateMeaning,
        InvestmentMandateMeaning,
        InvestmentStrategyMeaning,
        MandateMemberRef,
        MandateMember,
        PortfolioId,
        FinancialInstrumentId,
        PortfolioSource,
        PortfolioState,
        RecordedPortfolioState,
        InvestmentHorizon,
        ContextContribution,
        ContextSelectionRole,
        EvidenceUse,
        MandateMemberKind,
    )
}


def _encode(value: object) -> object:
    if value is None or type(value) in (str, int, bool):
        return value
    if type(value) is UUID:
        return {"type": "UUID", "value": str(value)}
    if type(value) is datetime:
        return {"type": "datetime", "value": value.isoformat()}
    if type(value) is Decimal:
        return {"type": "Decimal", "value": str(value)}
    if isinstance(value, StrEnum) and type(value).__name__ in _TYPES:
        return {"type": type(value).__name__, "value": value.value}
    if type(value) is tuple:
        return {"type": "tuple", "items": [_encode(item) for item in value]}
    if type(value) is frozenset:
        return {
            "type": "frozenset",
            "items": [_encode(item) for item in sorted(value, key=repr)],
        }
    kind = type(value)
    if (
        kind.__name__ in _TYPES
        and _TYPES[kind.__name__] is kind
        and is_dataclass(value)
    ):
        return {
            "type": kind.__name__,
            "fields": {
                field.name: _encode(getattr(value, field.name))
                for field in fields(value)
            },
        }
    raise TypeError(f"unsupported Portfolio context payload: {kind.__name__}")


def _decode(value: object) -> object:
    if value is None or type(value) in (str, int, bool):
        return value
    if type(value) is not dict:
        raise ValueError("Portfolio context payload must be tagged")
    kind = value.get("type")
    if type(kind) is not str:
        raise ValueError("Portfolio context payload type is missing")
    if kind in ("UUID", "datetime", "Decimal", "tuple", "frozenset"):
        return _decode_builtin(kind, value)
    cls = _TYPES.get(kind)
    if cls is None:
        raise ValueError("unknown Portfolio context payload type")
    if issubclass(cls, StrEnum):
        return cls(_string(value.get("value")))
    raw = value.get("fields")
    if type(raw) is not dict or set(raw) != {field.name for field in fields(cls)}:
        raise ValueError("Portfolio context fields are incomplete")
    return cls(**{name: _decode(item) for name, item in raw.items()})


def _decode_builtin(kind: str, value: dict[str, object]) -> object:
    if kind == "UUID":
        return UUID(_string(value.get("value")))
    if kind == "datetime":
        result = datetime.fromisoformat(_string(value.get("value")))
        if result.utcoffset() is None:
            raise ValueError("Portfolio context time must be aware")
        return result
    if kind == "Decimal":
        return Decimal(_string(value.get("value")))
    items = value.get("items")
    if type(items) is not list:
        raise ValueError("Portfolio context items must be a list")
    decoded = (_decode(item) for item in items)
    return tuple(decoded) if kind == "tuple" else frozenset(decoded)


def _string(value: object) -> str:
    if type(value) is not str:
        raise ValueError("Portfolio context scalar must be a string")
    return value


def commit_payload(commit: PortfolioContextCommit) -> dict[str, object]:
    encoded = _encode(commit)
    if type(encoded) is not dict:
        raise TypeError("Portfolio context commit must encode as an object")
    return cast(dict[str, object], encoded)


def commit_from_payload(payload: object) -> PortfolioContextCommit:
    decoded = _decode(payload)
    if type(decoded) is not PortfolioContextCommit:
        raise ValueError("Portfolio context payload is not a commit")
    return decoded
