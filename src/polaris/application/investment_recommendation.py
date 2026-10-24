"""Formation and derived support for attributable investment preferences."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from polaris.application.evidence.current_basis import (
    CurrentEvidenceBasis,
    CurrentEvidenceNoBasis,
)
from polaris.application.evidence.reconstruction import StaleEvidenceBasis
from polaris.domain.decisions import DecisionVersion, InvestmentDecisionId, OperationId
from polaris.domain.intelligence_judgment_history import IntelligenceClaimCatalog
from polaris.domain.investment_intelligence import InvalidInvestmentJudgment
from polaris.domain.investment_recommendation import (
    InvestmentRecommendation,
    RecommendationWithholdingJudgment,
)

from .investment_intelligence import JudgmentReceipt

type RecommendationEvent = InvestmentRecommendation | RecommendationWithholdingJudgment
type RecommendationWriteResult = (
    JudgmentReceipt | StaleEvidenceBasis | CurrentEvidenceNoBasis
)


class RecommendationSupportKind(StrEnum):
    NO_ATTEMPT = "no_attempt"
    WITHHELD = "withheld"
    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True, slots=True)
class CurrentRecommendationSupport:
    kind: RecommendationSupportKind
    latest: RecommendationEvent | None


def derive_current_recommendation_support(
    history: tuple[RecommendationEvent, ...],
    *,
    decision_applicable: bool,
    evidence_fit: bool,
    risk_fit: bool,
) -> CurrentRecommendationSupport:
    """Only the latest attributable act can hold current support."""
    if type(history) is not tuple or any(
        type(item) not in (InvestmentRecommendation, RecommendationWithholdingJudgment)
        for item in history
    ):
        raise TypeError("Recommendation history must contain typed owner acts")
    if not history:
        return CurrentRecommendationSupport(RecommendationSupportKind.NO_ATTEMPT, None)
    latest = history[-1]
    if type(latest) is RecommendationWithholdingJudgment:
        return CurrentRecommendationSupport(RecommendationSupportKind.WITHHELD, latest)
    kind = (
        RecommendationSupportKind.SUPPORTED
        if decision_applicable and evidence_fit and risk_fit
        else RecommendationSupportKind.UNSUPPORTED
    )
    return CurrentRecommendationSupport(kind, latest)


class InvestmentRecommendationStore(Protocol):
    async def record_recommendation(
        self,
        operation_id: OperationId,
        recommendation: InvestmentRecommendation,
        expected_decision_version: DecisionVersion,
        evidence_bases: tuple[CurrentEvidenceBasis, ...],
        initial_claim_catalog: IntelligenceClaimCatalog,
    ) -> RecommendationWriteResult: ...

    async def record_withholding(
        self,
        operation_id: OperationId,
        withholding: RecommendationWithholdingJudgment,
        expected_decision_version: DecisionVersion,
        initial_claim_catalog: IntelligenceClaimCatalog,
    ) -> JudgmentReceipt: ...

    async def recommendation_history(
        self, decision_id: InvestmentDecisionId
    ) -> tuple[RecommendationEvent, ...]: ...

    async def current_recommendation_support(
        self, decision_id: InvestmentDecisionId
    ) -> CurrentRecommendationSupport: ...


class InvestmentRecommendationService:
    def __init__(self, store: InvestmentRecommendationStore) -> None:
        self._store = store

    async def recommend(
        self,
        operation_id: OperationId,
        recommendation: InvestmentRecommendation,
        expected_decision_version: DecisionVersion,
        evidence_bases: tuple[CurrentEvidenceBasis, ...],
        initial_claim_catalog: IntelligenceClaimCatalog,
    ) -> RecommendationWriteResult:
        if (
            type(operation_id) is not OperationId
            or type(recommendation) is not InvestmentRecommendation
            or type(expected_decision_version) is not DecisionVersion
            or type(initial_claim_catalog) is not IntelligenceClaimCatalog
            or type(evidence_bases) is not tuple
            or any(type(item) is not CurrentEvidenceBasis for item in evidence_bases)
        ):
            raise InvalidInvestmentJudgment(
                "typed Recommendation formation is required"
            )
        required_targets = set(recommendation.view_ids) | set(
            recommendation.challenge_ids
        )
        actual_targets = {item.key.target for item in evidence_bases}
        if not required_targets.issubset(actual_targets):
            raise InvalidInvestmentJudgment(
                "each material View and challenge needs a current Evidence basis"
            )
        if any(
            item.key.decision_id != recommendation.decision_id
            for item in evidence_bases
        ):
            raise InvalidInvestmentJudgment("Evidence basis has another Decision")
        if len({item.key for item in evidence_bases}) != len(evidence_bases):
            raise InvalidInvestmentJudgment("Evidence basis keys must be distinct")
        binding_ids = frozenset(
            binding for item in evidence_bases for binding in item.guards.binding_ids
        )
        if not frozenset(recommendation.material_evidence).issubset(binding_ids):
            raise InvalidInvestmentJudgment(
                "material Evidence must occur in the captured exact bases"
            )
        return await self._store.record_recommendation(
            operation_id,
            recommendation,
            expected_decision_version,
            evidence_bases,
            initial_claim_catalog,
        )

    async def withhold(
        self,
        operation_id: OperationId,
        withholding: RecommendationWithholdingJudgment,
        expected_decision_version: DecisionVersion,
        initial_claim_catalog: IntelligenceClaimCatalog,
    ) -> JudgmentReceipt:
        if (
            type(operation_id) is not OperationId
            or type(withholding) is not RecommendationWithholdingJudgment
            or type(expected_decision_version) is not DecisionVersion
            or type(initial_claim_catalog) is not IntelligenceClaimCatalog
        ):
            raise InvalidInvestmentJudgment("typed withholding act is required")
        return await self._store.record_withholding(
            operation_id, withholding, expected_decision_version, initial_claim_catalog
        )

    async def history(
        self, decision_id: InvestmentDecisionId
    ) -> tuple[RecommendationEvent, ...]:
        if type(decision_id) is not InvestmentDecisionId:
            raise TypeError("Recommendation history requires a typed Decision")
        return await self._store.recommendation_history(decision_id)

    async def current_support(
        self, decision_id: InvestmentDecisionId
    ) -> CurrentRecommendationSupport:
        if type(decision_id) is not InvestmentDecisionId:
            raise TypeError("Recommendation support requires a typed Decision")
        return await self._store.current_recommendation_support(decision_id)
