"""Acceptance boundary for Investment Intelligence-owned judgments."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from polaris.application.evidence.current_basis import (
    CurrentEvidenceBasis,
    CurrentEvidenceNoBasis,
)
from polaris.application.evidence.reconstruction import StaleEvidenceBasis
from polaris.domain.decisions import (
    DecisionScopeCompleteness,
    DecisionVersion,
    InvestmentDecision,
    InvestmentDecisionId,
    OperationId,
    TriggerKind,
)
from polaris.domain.evidence import EvidenceBindingId
from polaris.domain.evidence.judgments import (
    InvestmentHypothesisRef,
    InvestmentRecommendationRef,
    InvestmentViewRef,
    MeaningfulChallengeResultRef,
    RecommendationWithholdingJudgmentRef,
)
from polaris.domain.investment_intelligence import (
    DecisionAlternative,
    DecisionAlternativeId,
    InvalidInvestmentJudgment,
    InvestmentHypothesis,
    InvestmentView,
    MeaningfulChallengeResult,
    require_minimum_alternatives,
)
from polaris.domain.portfolio import FinancialInstrumentId

# Stable first-slice binding; domain judgments continue to carry instrument IDs.
FIRST_R3_SPY_INSTRUMENT_ID = FinancialInstrumentId(
    UUID("0b9c6c29-45c7-4a7b-9452-a0b75b94337f")
)

type JudgmentId = (
    InvestmentHypothesisRef
    | InvestmentViewRef
    | MeaningfulChallengeResultRef
    | DecisionAlternativeId
    | InvestmentRecommendationRef
    | RecommendationWithholdingJudgmentRef
)
type JudgmentWriteResult = JudgmentReceipt | StaleEvidenceBasis | CurrentEvidenceNoBasis


def _require_basis_coverage(
    decision_id: InvestmentDecisionId,
    material_evidence: tuple[EvidenceBindingId, ...],
    bases: tuple[CurrentEvidenceBasis, ...],
) -> None:
    if type(bases) is not tuple or any(
        type(item) is not CurrentEvidenceBasis for item in bases
    ):
        raise InvalidInvestmentJudgment(
            "consumed Evidence bases must be complete and typed"
        )
    if any(item.key.decision_id != decision_id for item in bases):
        raise InvalidInvestmentJudgment("Evidence basis belongs to another Decision")
    if len({item.key for item in bases}) != len(bases):
        raise InvalidInvestmentJudgment("one exact Evidence basis is allowed per key")
    if material_evidence and not bases:
        raise InvalidInvestmentJudgment(
            "material Evidence requires captured current bases"
        )
    covered = frozenset(
        binding for item in bases for binding in item.guards.binding_ids
    )
    if not frozenset(material_evidence).issubset(covered):
        raise InvalidInvestmentJudgment(
            "material Evidence is absent from consumed bases"
        )


@dataclass(frozen=True, slots=True)
class JudgmentReceipt:
    operation_id: OperationId
    judgment_ids: tuple[JudgmentId, ...]

    def __post_init__(self) -> None:
        if (
            type(self.operation_id) is not OperationId
            or type(self.judgment_ids) is not tuple
        ):
            raise TypeError("JudgmentReceipt requires typed operation and judgment IDs")
        if any(
            type(item)
            not in (
                InvestmentHypothesisRef,
                InvestmentViewRef,
                MeaningfulChallengeResultRef,
                DecisionAlternativeId,
                InvestmentRecommendationRef,
                RecommendationWithholdingJudgmentRef,
            )
            for item in self.judgment_ids
        ):
            raise TypeError("JudgmentReceipt identities must be typed")


class InvestmentIntelligenceStore(Protocol):
    async def record_view(
        self,
        operation_id: OperationId,
        view: InvestmentView,
        hypotheses: tuple[InvestmentHypothesis, ...],
        expected_decision_version: DecisionVersion,
        evidence_bases: tuple[CurrentEvidenceBasis, ...] = (),
    ) -> JudgmentWriteResult: ...

    async def record_challenge(
        self,
        operation_id: OperationId,
        challenge: MeaningfulChallengeResult,
        hypotheses: tuple[InvestmentHypothesis, ...],
        expected_decision_version: DecisionVersion,
        evidence_bases: tuple[CurrentEvidenceBasis, ...] = (),
    ) -> JudgmentWriteResult: ...

    async def record_alternatives(
        self,
        operation_id: OperationId,
        alternatives: tuple[DecisionAlternative, ...],
        expected_decision_version: DecisionVersion,
    ) -> JudgmentReceipt: ...

    async def revise_alternative(
        self,
        operation_id: OperationId,
        replacement: DecisionAlternative,
        expected_revision: int,
    ) -> JudgmentReceipt: ...

    async def select_alternative(
        self,
        operation_id: OperationId,
        decision: InvestmentDecision,
        selected_id: DecisionAlternativeId | None,
        expected_selection_revision: int,
        expected_selected_revision: int | None,
    ) -> JudgmentReceipt: ...


class InvestmentIntelligenceService:
    """Accepts typed domain judgments; model/provider output has no commit power."""

    def __init__(
        self,
        store: InvestmentIntelligenceStore,
    ) -> None:
        self._store = store

    def _first_slice(self, decision: InvestmentDecision, view: InvestmentView) -> None:
        if type(decision) is not InvestmentDecision or type(view) is not InvestmentView:
            raise InvalidInvestmentJudgment("accepted View requires typed domain facts")
        if decision.decision_id != view.decision_id:
            raise InvalidInvestmentJudgment("View belongs to a different Decision")
        if (
            decision.scope.completeness is not DecisionScopeCompleteness.ESTABLISHED
            or len(decision.scope.portfolio_ids) != 1
            or view.slice.portfolio_id not in decision.scope.portfolio_ids
        ):
            raise InvalidInvestmentJudgment(
                "first R3 slice requires one Decision Portfolio"
            )
        if decision.history[0].metadata.trigger.kind is not TriggerKind.HUMAN_REQUEST:
            raise InvalidInvestmentJudgment("first R3 Decision must be user-initiated")
        if view.slice.instrument_id != FIRST_R3_SPY_INSTRUMENT_ID:
            raise InvalidInvestmentJudgment(
                "View must concern the configured first-slice instrument"
            )

    async def record_view(
        self,
        operation_id: OperationId,
        decision: InvestmentDecision,
        view: InvestmentView,
        hypotheses: tuple[InvestmentHypothesis, ...] = (),
        evidence_bases: tuple[CurrentEvidenceBasis, ...] = (),
    ) -> JudgmentWriteResult:
        self._first_slice(decision, view)
        if (
            type(operation_id) is not OperationId
            or type(hypotheses) is not tuple
            or any(type(item) is not InvestmentHypothesis for item in hypotheses)
        ):
            raise InvalidInvestmentJudgment(
                "typed View operation and Hypotheses required"
            )
        if any(
            hypothesis.decision_id != view.decision_id
            or hypothesis.material_to != view.view_id
            for hypothesis in hypotheses
        ):
            raise InvalidInvestmentJudgment(
                "Hypotheses must materially shape this View"
            )
        if {item.hypothesis_id for item in hypotheses} != set(view.hypothesis_ids):
            raise InvalidInvestmentJudgment(
                "View must name exactly its committed Hypotheses"
            )
        _require_basis_coverage(
            decision.decision_id, view.material_evidence, evidence_bases
        )
        return await self._store.record_view(
            operation_id, view, hypotheses, decision.version, evidence_bases
        )

    async def record_challenge(
        self,
        operation_id: OperationId,
        challenge: MeaningfulChallengeResult,
        expected_decision_version: DecisionVersion,
        hypotheses: tuple[InvestmentHypothesis, ...] = (),
        evidence_bases: tuple[CurrentEvidenceBasis, ...] = (),
    ) -> JudgmentWriteResult:
        if (
            type(operation_id) is not OperationId
            or type(challenge) is not MeaningfulChallengeResult
        ):
            raise InvalidInvestmentJudgment("typed Challenge operation required")
        if type(expected_decision_version) is not DecisionVersion:
            raise InvalidInvestmentJudgment("expected Decision version is required")
        if type(hypotheses) is not tuple or any(
            type(item) is not InvestmentHypothesis for item in hypotheses
        ):
            raise InvalidInvestmentJudgment("typed Challenge Hypotheses required")
        if any(
            item.decision_id != challenge.decision_id
            or item.material_to != challenge.challenge_id
            for item in hypotheses
        ):
            raise InvalidInvestmentJudgment(
                "Hypotheses must materially shape this Challenge"
            )
        if {item.hypothesis_id for item in hypotheses} != set(challenge.hypothesis_ids):
            raise InvalidInvestmentJudgment(
                "Challenge must name exactly its committed Hypotheses"
            )
        _require_basis_coverage(
            challenge.decision_id, challenge.conflicting_evidence, evidence_bases
        )
        return await self._store.record_challenge(
            operation_id,
            challenge,
            hypotheses,
            expected_decision_version,
            evidence_bases,
        )

    async def record_alternatives(
        self,
        operation_id: OperationId,
        decision: InvestmentDecision,
        alternatives: tuple[DecisionAlternative, ...],
    ) -> JudgmentReceipt:
        if (
            type(operation_id) is not OperationId
            or type(decision) is not InvestmentDecision
        ):
            raise InvalidInvestmentJudgment("typed Alternative operation required")
        require_minimum_alternatives(alternatives)
        if (
            decision.scope.completeness is not DecisionScopeCompleteness.ESTABLISHED
            or len(decision.scope.portfolio_ids) != 1
            or decision.history[0].metadata.trigger.kind
            is not TriggerKind.HUMAN_REQUEST
            or any(item.decision_id != decision.decision_id for item in alternatives)
        ):
            raise InvalidInvestmentJudgment(
                "first-slice Alternatives require one user-initiated Decision"
            )
        if any(
            item.instrument_id != FIRST_R3_SPY_INSTRUMENT_ID for item in alternatives
        ):
            raise InvalidInvestmentJudgment(
                "Alternatives must concern the configured first-slice instrument"
            )
        ordered = tuple(
            sorted(alternatives, key=lambda item: item.alternative_id.value.hex)
        )
        return await self._store.record_alternatives(
            operation_id, ordered, decision.version
        )

    async def revise_alternative(
        self,
        operation_id: OperationId,
        replacement: DecisionAlternative,
        expected_revision: int,
    ) -> JudgmentReceipt:
        if (
            type(operation_id) is not OperationId
            or type(replacement) is not DecisionAlternative
        ):
            raise InvalidInvestmentJudgment("typed Alternative revision required")
        if replacement.revision != expected_revision + 1:
            raise InvalidInvestmentJudgment(
                "root-local Alternative revision must advance once"
            )
        return await self._store.revise_alternative(
            operation_id, replacement, expected_revision
        )

    async def select_alternative(
        self,
        operation_id: OperationId,
        decision: InvestmentDecision,
        selected_id: DecisionAlternativeId | None,
        expected_selection_revision: int,
        expected_selected_revision: int | None,
    ) -> JudgmentReceipt:
        if (
            type(operation_id) is not OperationId
            or type(decision) is not InvestmentDecision
        ):
            raise InvalidInvestmentJudgment("typed Decision selection required")
        if selected_id is not None and type(selected_id) is not DecisionAlternativeId:
            raise InvalidInvestmentJudgment(
                "selected Alternative identity must be typed"
            )
        if (
            type(expected_selection_revision) is not int
            or expected_selection_revision < 0
        ):
            raise InvalidInvestmentJudgment("selection guard must be nonnegative")
        if selected_id is None:
            if expected_selected_revision is not None:
                raise InvalidInvestmentJudgment(
                    "absence selection has no root revision"
                )
        elif (
            type(expected_selected_revision) is not int
            or expected_selected_revision < 1
        ):
            raise InvalidInvestmentJudgment(
                "selected Alternative root revision required"
            )
        return await self._store.select_alternative(
            operation_id,
            decision,
            selected_id,
            expected_selection_revision,
            expected_selected_revision,
        )
