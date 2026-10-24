"""Investment Intelligence-owned analytical judgments for the first R3 slice."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from polaris.domain.actors import ActorAttribution, is_actor_attribution
from polaris.domain.configuration.evidence_requirements import InvestmentHorizon
from polaris.domain.decisions import InvestmentDecisionId
from polaris.domain.evidence import EvidenceBindingId
from polaris.domain.evidence.judgments import (
    DecisionEvaluationRef,
    InvestmentHypothesisRef,
    InvestmentRecommendationRef,
    InvestmentViewRef,
    MeaningfulChallengeResultRef,
)
from polaris.domain.portfolio import FinancialInstrumentId, PortfolioId


class InvalidInvestmentJudgment(ValueError):
    """The proposed analytical fact fails its domain contract."""


def _text(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InvalidInvestmentJudgment(f"{field} must be substantive text")
    return value.strip()


# duplicate-code: each domain owns its own judgment-time failure contract;
# importing Decisions' private validator would couple distinct domain errors.
# arid: disable
def _time(value: datetime, field: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise InvalidInvestmentJudgment(f"{field} must be timezone-aware")


# arid: enable


def _attribution(value: ActorAttribution) -> None:
    if not is_actor_attribution(value):
        raise InvalidInvestmentJudgment("actor attribution is required")


def _bindings(value: tuple[EvidenceBindingId, ...]) -> None:
    if type(value) is not tuple or any(
        type(item) is not EvidenceBindingId for item in value
    ):
        raise InvalidInvestmentJudgment("material Evidence bindings must be typed")
    if len(set(value)) != len(value):
        raise InvalidInvestmentJudgment("material Evidence bindings must be distinct")


class EconomicDisposition(StrEnum):
    INCREASE = "increase"
    HOLD = "hold"
    REDUCE = "reduce"


class ChallengeDisposition(StrEnum):
    INCONCLUSIVE = "INCONCLUSIVE"
    QUALIFIED = "QUALIFIED"
    REJECTED = "REJECTED"
    SURVIVES_CHALLENGE = "SURVIVES_CHALLENGE"


@dataclass(frozen=True, slots=True)
class DecisionAlternativeId:
    value: UUID

    def __post_init__(self) -> None:
        if type(self.value) is not UUID or self.value.version != 4:
            raise InvalidInvestmentJudgment("DecisionAlternativeId must be UUIDv4")


@dataclass(frozen=True, slots=True)
class R3InvestmentSlice:
    """Instrument identity stays independent of the first slice's SPY configuration."""

    portfolio_id: PortfolioId
    instrument_id: FinancialInstrumentId
    horizon: InvestmentHorizon

    def __post_init__(self) -> None:
        if type(self.portfolio_id) is not PortfolioId:
            raise InvalidInvestmentJudgment("one Portfolio is required")
        if type(self.instrument_id) is not FinancialInstrumentId:
            raise InvalidInvestmentJudgment("one investable instrument is required")
        if type(self.horizon) is not InvestmentHorizon:
            raise InvalidInvestmentJudgment(
                "an explicit Investment Horizon is required"
            )


@dataclass(frozen=True, slots=True)
class InvestmentHypothesis:
    hypothesis_id: InvestmentHypothesisRef
    decision_id: InvestmentDecisionId
    statement: str
    material_to: (
        InvestmentViewRef
        | MeaningfulChallengeResultRef
        | InvestmentRecommendationRef
        | DecisionEvaluationRef
    )
    actor_attribution: ActorAttribution
    formed_at: datetime

    @property
    def evidence_target(self) -> InvestmentHypothesisRef:
        return self.hypothesis_id

    def __post_init__(self) -> None:
        if (
            type(self.hypothesis_id) is not InvestmentHypothesisRef
            or type(self.decision_id) is not InvestmentDecisionId
        ):
            raise InvalidInvestmentJudgment(
                "typed Hypothesis and Decision identities are required"
            )
        if type(self.material_to) not in (
            InvestmentViewRef,
            MeaningfulChallengeResultRef,
            InvestmentRecommendationRef,
            DecisionEvaluationRef,
        ):
            raise InvalidInvestmentJudgment("a material judgment use is required")
        object.__setattr__(self, "statement", _text(self.statement, "hypothesis"))
        _attribution(self.actor_attribution)
        _time(self.formed_at, "formed_at")


@dataclass(frozen=True, slots=True)
class InvestmentView:
    view_id: InvestmentViewRef
    decision_id: InvestmentDecisionId
    slice: R3InvestmentSlice
    thesis: str
    actor_attribution: ActorAttribution
    formed_at: datetime
    material_evidence: tuple[EvidenceBindingId, ...]
    assumptions: tuple[str, ...]
    uncertainty: str
    alternative_explanation_or_dissent: str
    invalidation_conditions: tuple[str, ...]
    material_signal_provenance: tuple[str, ...] = ()
    hypothesis_ids: tuple[InvestmentHypothesisRef, ...] = ()

    @property
    def evidence_target(self) -> InvestmentViewRef:
        return self.view_id

    def __post_init__(self) -> None:
        if (
            type(self.view_id) is not InvestmentViewRef
            or type(self.decision_id) is not InvestmentDecisionId
        ):
            raise InvalidInvestmentJudgment(
                "typed View and Decision identities are required"
            )
        if type(self.slice) is not R3InvestmentSlice:
            raise InvalidInvestmentJudgment("R3 investment slice is required")
        object.__setattr__(self, "thesis", _text(self.thesis, "view thesis"))
        _attribution(self.actor_attribution)
        _time(self.formed_at, "formed_at")
        _bindings(self.material_evidence)
        for field in (
            "assumptions",
            "invalidation_conditions",
            "material_signal_provenance",
        ):
            values = getattr(self, field)
            if type(values) is not tuple:
                raise InvalidInvestmentJudgment(f"{field} must be a tuple")
            object.__setattr__(
                self, field, tuple(_text(item, field) for item in values)
            )
        object.__setattr__(self, "uncertainty", _text(self.uncertainty, "uncertainty"))
        object.__setattr__(
            self,
            "alternative_explanation_or_dissent",
            _text(
                self.alternative_explanation_or_dissent,
                "alternative explanation or dissent",
            ),
        )
        if type(self.hypothesis_ids) is not tuple or any(
            type(item) is not InvestmentHypothesisRef for item in self.hypothesis_ids
        ):
            raise InvalidInvestmentJudgment("hypothesis references must be typed")
        if len(set(self.hypothesis_ids)) != len(self.hypothesis_ids):
            raise InvalidInvestmentJudgment(
                "View Hypothesis references must be distinct"
            )


@dataclass(frozen=True, slots=True)
class MeaningfulChallengeResult:
    challenge_id: MeaningfulChallengeResultRef
    view_id: InvestmentViewRef
    decision_id: InvestmentDecisionId
    actor_attribution: ActorAttribution
    formed_at: datetime
    strongest_competing_interpretation: str
    conflicting_evidence: tuple[EvidenceBindingId, ...]
    challenged_assumptions_uncertainty_or_conditions: str
    disposition: ChallengeDisposition
    disposition_basis: str
    hypothesis_ids: tuple[InvestmentHypothesisRef, ...] = ()

    @property
    def evidence_target(self) -> MeaningfulChallengeResultRef:
        return self.challenge_id

    def __post_init__(self) -> None:
        if (
            type(self.challenge_id) is not MeaningfulChallengeResultRef
            or type(self.view_id) is not InvestmentViewRef
            or type(self.decision_id) is not InvestmentDecisionId
        ):
            raise InvalidInvestmentJudgment(
                "typed Challenge, View, and Decision identities are required"
            )
        _attribution(self.actor_attribution)
        _time(self.formed_at, "formed_at")
        _bindings(self.conflicting_evidence)
        for field in (
            "strongest_competing_interpretation",
            "challenged_assumptions_uncertainty_or_conditions",
            "disposition_basis",
        ):
            object.__setattr__(self, field, _text(getattr(self, field), field))
        if type(self.disposition) is not ChallengeDisposition:
            raise InvalidInvestmentJudgment("closed challenge disposition is required")
        if (
            type(self.hypothesis_ids) is not tuple
            or any(
                type(item) is not InvestmentHypothesisRef
                for item in self.hypothesis_ids
            )
            or len(set(self.hypothesis_ids)) != len(self.hypothesis_ids)
        ):
            raise InvalidInvestmentJudgment(
                "Challenge Hypothesis references must be distinct and typed"
            )


@dataclass(frozen=True, slots=True)
class DecisionAlternative:
    alternative_id: DecisionAlternativeId
    decision_id: InvestmentDecisionId
    instrument_id: FinancialInstrumentId
    horizon: InvestmentHorizon
    disposition: EconomicDisposition
    material_comparison: str
    actor_attribution: ActorAttribution
    formed_at: datetime
    revision: int = 1
    valid: bool = True
    contested: bool = False

    def __post_init__(self) -> None:
        if (
            type(self.alternative_id) is not DecisionAlternativeId
            or type(self.decision_id) is not InvestmentDecisionId
            or type(self.instrument_id) is not FinancialInstrumentId
        ):
            raise InvalidInvestmentJudgment(
                "typed Alternative, Decision, and Instrument identities are required"
            )
        if type(self.horizon) is not InvestmentHorizon:
            raise InvalidInvestmentJudgment(
                "Alternative requires an explicit Investment Horizon"
            )
        if type(self.disposition) is not EconomicDisposition:
            raise InvalidInvestmentJudgment(
                "economic disposition must be increase, hold, or reduce"
            )
        object.__setattr__(
            self,
            "material_comparison",
            _text(self.material_comparison, "material comparison"),
        )
        _attribution(self.actor_attribution)
        _time(self.formed_at, "formed_at")
        if type(self.revision) is not int or self.revision < 1:
            raise InvalidInvestmentJudgment("Alternative revision must be positive")
        if type(self.valid) is not bool or type(self.contested) is not bool:
            raise InvalidInvestmentJudgment("Alternative validity must be explicit")


def require_minimum_alternatives(alternatives: tuple[DecisionAlternative, ...]) -> None:
    """A material first-slice comparison preserves all three economic choices."""
    if (
        type(alternatives) is not tuple
        or not alternatives
        or any(type(item) is not DecisionAlternative for item in alternatives)
    ):
        raise InvalidInvestmentJudgment("material alternatives are required")
    decision_ids = {item.decision_id for item in alternatives}
    instrument_ids = {item.instrument_id for item in alternatives}
    horizons = {item.horizon for item in alternatives}
    if (
        len(decision_ids) != 1
        or len(instrument_ids) != 1
        or len(horizons) != 1
        or {item.disposition for item in alternatives} != set(EconomicDisposition)
    ):
        raise InvalidInvestmentJudgment(
            "one Decision comparison requires increase, hold, and reduce"
        )
    if len({item.alternative_id for item in alternatives}) != len(alternatives):
        raise InvalidInvestmentJudgment("Alternative identities must be distinct")
