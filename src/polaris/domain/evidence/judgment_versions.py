"""Owner-issued versions of the ten Evidence judgment target families."""

from __future__ import annotations

from dataclasses import dataclass

from .judgments import (
    DecisionEvaluationRef,
    EvidenceJudgmentRef,
    HumanInvestmentDecisionRef,
    InvestmentHypothesisRef,
    InvestmentRecommendationRef,
    InvestmentViewRef,
    LessonRef,
    MeaningfulChallengeResultRef,
    PortfolioRiskAssessmentRef,
    ProjectedPortfolioConsequenceRef,
    RecommendationWithholdingJudgmentRef,
)


@dataclass(frozen=True, slots=True)
class JudgmentRevision:
    """Positive root-local owner epoch, distinct from ClaimCatalogVersion.

    The owner starts a new root at 1 and advances at most once per atomic commit
    changing that root's current assertion, support, validity, or applicability.
    Queries and clock passage never issue a revision.
    """

    value: int

    def __post_init__(self) -> None:
        if type(self.value) is not int or self.value < 1:
            raise ValueError("JudgmentRevision.value must be positive")


# Each public variant names its own owner root. A universal (kind, id) value
# would erase the persistence-visible family distinction fixed by ADR 0015.
@dataclass(frozen=True, slots=True)
class InvestmentHypothesisVersionRef:
    root: InvestmentHypothesisRef
    revision: JudgmentRevision

    def __post_init__(self) -> None:
        _validate(self.root, InvestmentHypothesisRef, self.revision)


@dataclass(frozen=True, slots=True)
class InvestmentViewVersionRef:
    root: InvestmentViewRef
    revision: JudgmentRevision

    def __post_init__(self) -> None:
        _validate(self.root, InvestmentViewRef, self.revision)


@dataclass(frozen=True, slots=True)
class MeaningfulChallengeResultVersionRef:
    root: MeaningfulChallengeResultRef
    revision: JudgmentRevision

    def __post_init__(self) -> None:
        _validate(self.root, MeaningfulChallengeResultRef, self.revision)


@dataclass(frozen=True, slots=True)
class ProjectedPortfolioConsequenceVersionRef:
    root: ProjectedPortfolioConsequenceRef
    revision: JudgmentRevision

    def __post_init__(self) -> None:
        _validate(self.root, ProjectedPortfolioConsequenceRef, self.revision)


@dataclass(frozen=True, slots=True)
class PortfolioRiskAssessmentVersionRef:
    root: PortfolioRiskAssessmentRef
    revision: JudgmentRevision

    def __post_init__(self) -> None:
        _validate(self.root, PortfolioRiskAssessmentRef, self.revision)


@dataclass(frozen=True, slots=True)
class InvestmentRecommendationVersionRef:
    root: InvestmentRecommendationRef
    revision: JudgmentRevision

    def __post_init__(self) -> None:
        _validate(self.root, InvestmentRecommendationRef, self.revision)


@dataclass(frozen=True, slots=True)
class RecommendationWithholdingJudgmentVersionRef:
    root: RecommendationWithholdingJudgmentRef
    revision: JudgmentRevision

    def __post_init__(self) -> None:
        _validate(self.root, RecommendationWithholdingJudgmentRef, self.revision)


@dataclass(frozen=True, slots=True)
class HumanInvestmentDecisionVersionRef:
    root: HumanInvestmentDecisionRef
    revision: JudgmentRevision

    def __post_init__(self) -> None:
        _validate(self.root, HumanInvestmentDecisionRef, self.revision)


@dataclass(frozen=True, slots=True)
class DecisionEvaluationVersionRef:
    root: DecisionEvaluationRef
    revision: JudgmentRevision

    def __post_init__(self) -> None:
        _validate(self.root, DecisionEvaluationRef, self.revision)


@dataclass(frozen=True, slots=True)
class LessonVersionRef:
    root: LessonRef
    revision: JudgmentRevision

    def __post_init__(self) -> None:
        _validate(self.root, LessonRef, self.revision)


type TargetJudgmentVersionRef = (
    InvestmentHypothesisVersionRef
    | InvestmentViewVersionRef
    | MeaningfulChallengeResultVersionRef
    | ProjectedPortfolioConsequenceVersionRef
    | PortfolioRiskAssessmentVersionRef
    | InvestmentRecommendationVersionRef
    | RecommendationWithholdingJudgmentVersionRef
    | HumanInvestmentDecisionVersionRef
    | DecisionEvaluationVersionRef
    | LessonVersionRef
)


_VERSION_TYPES = (
    InvestmentHypothesisVersionRef,
    InvestmentViewVersionRef,
    MeaningfulChallengeResultVersionRef,
    ProjectedPortfolioConsequenceVersionRef,
    PortfolioRiskAssessmentVersionRef,
    InvestmentRecommendationVersionRef,
    RecommendationWithholdingJudgmentVersionRef,
    HumanInvestmentDecisionVersionRef,
    DecisionEvaluationVersionRef,
    LessonVersionRef,
)


def _validate(
    root: EvidenceJudgmentRef,
    expected_type: type[EvidenceJudgmentRef],
    revision: JudgmentRevision,
) -> None:
    if type(root) is not expected_type:
        raise TypeError(f"root must be {expected_type.__name__}")
    if type(revision) is not JudgmentRevision:
        raise TypeError("revision must be JudgmentRevision")


def is_target_judgment_version_ref(value: object) -> bool:
    return type(value) in _VERSION_TYPES
