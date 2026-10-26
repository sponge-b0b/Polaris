"""Atomic, idempotent persistence of Investment Intelligence-owned facts."""

from __future__ import annotations

import hashlib
import json
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Column, Table, insert, select, text
from sqlalchemy.engine import RowMapping
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from polaris.application.evidence.current_basis import (
    CurrentEvidenceBasis,
    CurrentEvidenceNoBasis,
    CurrentNoBasisReason,
)
from polaris.application.evidence.judgment_versions import ResolvedTargetJudgment
from polaris.application.evidence.reconstruction import StaleEvidenceBasis
from polaris.application.evidence.revalidation import CurrentEvidenceBasisRevalidator
from polaris.application.intelligence_judgment_history import (
    IntelligenceJudgmentTargetReader,
)
from polaris.application.investment_intelligence import JudgmentId, JudgmentReceipt
from polaris.application.investment_recommendation import (
    CurrentRecommendationSupport,
    RecommendationEvent,
    derive_current_recommendation_support,
)
from polaris.application.portfolio_judgment_history import (
    PortfolioJudgmentTargetReader,
)
from polaris.domain.actors import (
    ActorAttribution,
    ActorId,
    ContestedActorAttribution,
    KnownActorAttribution,
    UnknownActorAttribution,
)
from polaris.domain.configuration.evidence_requirements import InvestmentHorizon
from polaris.domain.decisions import (
    DecisionApplicability,
    DecisionLifecycleDisposition,
    DecisionVersion,
    DeterminateDecisionLifecycleInterpretation,
    InvestmentDecision,
    InvestmentDecisionId,
    OperationId,
)
from polaris.domain.evidence import EvidenceBindingId
from polaris.domain.evidence.judgments import (
    DecisionEvaluationRef,
    InvestmentHypothesisRef,
    InvestmentRecommendationRef,
    InvestmentViewRef,
    MeaningfulChallengeResultRef,
    ProjectedPortfolioConsequenceRef,
    RecommendationWithholdingJudgmentRef,
)
from polaris.domain.intelligence_judgment_history import (
    IntelligenceClaimCatalog,
    IntelligenceJudgmentAct,
    IntelligenceJudgmentStatus,
)
from polaris.domain.investment_intelligence import (
    ChallengeDisposition,
    DecisionAlternative,
    DecisionAlternativeId,
    EconomicDisposition,
    InvalidInvestmentJudgment,
    InvestmentHypothesis,
    InvestmentView,
    MeaningfulChallengeResult,
    R3InvestmentSlice,
    require_minimum_alternatives,
)
from polaris.domain.investment_recommendation import (
    InvestmentRecommendation,
    RecommendationWithholdingJudgment,
)
from polaris.domain.portfolio import FinancialInstrumentId, PortfolioId
from polaris.domain.portfolio_consequences import ProjectedPortfolioConsequence
from polaris.domain.portfolio_risk import PortfolioRiskAssessment

from .intelligence_basis_participation import (
    PostgresCurrentBasisReader,
    PostgresIntelligenceBasisParticipation,
)
from .intelligence_contract_codec import (
    basis_from_payload,
    basis_payload,
    contract_value_from_payload,
    contract_value_payload,
)
from .intelligence_judgment_history import (
    INTELLIGENCE_OWNER_LOCK,
    PostgresIntelligenceJudgmentHistoryStore,
    insert_initial_intelligence_act,
)
from .relationship_store import _load_decision, _load_relationship_history
from .runtime_qualification import require_qualified_postgres_runtime
from .schema import (
    decision_alternative_revisions,
    decision_alternative_selections,
    decision_alternatives,
    investment_decisions,
    investment_hypotheses,
    investment_intelligence_command_receipts,
    investment_intelligence_judgment_acts,
    investment_intelligence_judgment_bases,
    investment_views,
    meaningful_challenges,
)

_WRITE_LOCK = INTELLIGENCE_OWNER_LOCK
_MATERIAL_TARGETS = {
    "InvestmentViewRef": InvestmentViewRef,
    "MeaningfulChallengeResultRef": MeaningfulChallengeResultRef,
    "InvestmentRecommendationRef": InvestmentRecommendationRef,
    "DecisionEvaluationRef": DecisionEvaluationRef,
}
_RECEIPT_IDENTITIES = {
    "InvestmentHypothesisRef": InvestmentHypothesisRef,
    "InvestmentViewRef": InvestmentViewRef,
    "MeaningfulChallengeResultRef": MeaningfulChallengeResultRef,
    "DecisionAlternativeId": DecisionAlternativeId,
    "InvestmentRecommendationRef": InvestmentRecommendationRef,
    "RecommendationWithholdingJudgmentRef": RecommendationWithholdingJudgmentRef,
}


def _uuid(value: object) -> UUID:
    """Normalize asyncpg UUID values before strict domain identity validation."""
    return UUID(str(value))


class JudgmentConcurrencyConflict(InvalidInvestmentJudgment):
    pass


class JudgmentIdempotencyConflict(InvalidInvestmentJudgment):
    pass


class JudgmentPersistenceUnavailable(RuntimeError):
    pass


# duplicate-code: Intelligence serializes its own judgment actor payload;
# Decisions' private codec is independently versioned for Decision history.
# arid: disable
def _actor_payload(actor: ActorAttribution) -> dict[str, object]:
    if isinstance(actor, KnownActorAttribution):
        return {"kind": "known", "actor_id": str(actor.actor_id.value)}
    if isinstance(actor, UnknownActorAttribution):
        return {"kind": "unknown"}
    assert isinstance(actor, ContestedActorAttribution)
    return {
        "kind": "contested",
        "candidate_ids": sorted(str(item.value) for item in actor.candidate_actor_ids),
    }


# arid: enable


def _actor_from_payload(
    value: dict[str, object],
) -> KnownActorAttribution | UnknownActorAttribution | ContestedActorAttribution:
    if value["kind"] == "known":
        return KnownActorAttribution(ActorId(UUID(str(value["actor_id"]))))
    if value["kind"] == "unknown":
        return UnknownActorAttribution()
    if value["kind"] == "contested":
        candidates = value["candidate_ids"]
        if not isinstance(candidates, list):
            raise InvalidInvestmentJudgment("stored Actor candidates are invalid")
        return ContestedActorAttribution(
            frozenset(ActorId(UUID(str(item))) for item in candidates)
        )
    raise InvalidInvestmentJudgment("stored Actor Attribution is invalid")


def _hypothesis_payload(hypothesis: InvestmentHypothesis) -> dict[str, object]:
    return {
        "statement": hypothesis.statement,
        "material_to_family": type(hypothesis.material_to).__name__,
        "material_to_id": str(hypothesis.material_to.value),
        "actor": _actor_payload(hypothesis.actor_attribution),
    }


def _hypotheses_request_payload(
    hypotheses: tuple[InvestmentHypothesis, ...],
) -> list[list[object]]:
    return [
        [
            str(item.hypothesis_id.value),
            str(item.decision_id.value),
            item.formed_at.isoformat(),
            _hypothesis_payload(item),
        ]
        for item in hypotheses
    ]


async def _append_hypotheses(
    connection: AsyncConnection, hypotheses: tuple[InvestmentHypothesis, ...]
) -> None:
    for hypothesis in hypotheses:
        await connection.execute(
            insert(investment_hypotheses).values(
                hypothesis_id=hypothesis.hypothesis_id.value,
                decision_id=hypothesis.decision_id.value,
                material_to_id=hypothesis.material_to.value,
                material_to_family=type(hypothesis.material_to).__name__,
                formed_at=hypothesis.formed_at,
                payload=_hypothesis_payload(hypothesis),
            )
        )
        await _append_initial_target(connection, hypothesis)


async def _append_initial_target(
    connection: AsyncConnection,
    assertion: (
        InvestmentHypothesis
        | InvestmentView
        | MeaningfulChallengeResult
        | InvestmentRecommendation
        | RecommendationWithholdingJudgment
    ),
    catalog: IntelligenceClaimCatalog | None = None,
) -> None:
    now = datetime.now(UTC)
    await insert_initial_intelligence_act(
        connection,
        IntelligenceJudgmentAct(
            act_id=uuid4(),
            root=assertion.evidence_target,
            attribution=assertion.actor_attribution,
            basis="initial accepted Investment Intelligence judgment",
            effective_at=assertion.formed_at,
            recorded_at=now,
            known_at=now,
            ancestry=(),
            assertion=assertion,
            catalog=IntelligenceClaimCatalog(()) if catalog is None else catalog,
            target_status=IntelligenceJudgmentStatus.ACTIVE,
        ),
    )


async def _require_decision_ordinary_work(
    connection: AsyncConnection,
    decision_id: InvestmentDecisionId,
    expected: DecisionVersion,
) -> None:
    """Lock the Decision and admit only its current ordinary-work meaning.

    Known future-effective history can change meaning without advancing its version.
    """
    current = (
        await connection.execute(
            select(investment_decisions.c.decision_version)
            .where(investment_decisions.c.decision_id == decision_id.value)
            .with_for_update()
        )
    ).one_or_none()
    if current is None or current.decision_version != expected.value:
        raise JudgmentConcurrencyConflict("governing Decision version changed")
    now = await connection.scalar(text("SELECT clock_timestamp()"))
    relationships = await _load_relationship_history(connection, known_at=now)
    loaded = await _load_decision(
        connection,
        decision_id,
        known_at=now,
        relationship_history=relationships,
    )
    if loaded is None:
        raise InvalidInvestmentJudgment("governing Decision history is unavailable")
    decision, applicability = loaded
    interpretation = decision.lifecycle_interpretation
    if (
        decision.version != expected
        or not isinstance(interpretation, DeterminateDecisionLifecycleInterpretation)
        or interpretation.disposition is not DecisionLifecycleDisposition.UNRESOLVED
        or applicability is not DecisionApplicability.OPERATIVE
    ):
        raise InvalidInvestmentJudgment(
            "governing Decision does not admit ordinary work"
        )


async def _require_decision_horizon(
    connection: AsyncConnection,
    decision_id: InvestmentDecisionId,
    horizon: InvestmentHorizon,
) -> None:
    """Keep all first-slice judgments on the Decision's one horizon."""
    view_payloads = (
        await connection.execute(
            select(investment_views.c.payload).where(
                investment_views.c.decision_id == decision_id.value
            )
        )
    ).scalars()
    alternative_payloads = (
        await connection.execute(
            select(decision_alternative_revisions.c.payload)
            .join(decision_alternatives)
            .where(decision_alternatives.c.decision_id == decision_id.value)
        )
    ).scalars()
    if any(
        payload["horizon"] != horizon.value
        for payload in (*view_payloads, *alternative_payloads)
    ):
        raise InvalidInvestmentJudgment(
            "one Decision requires one explicit Investment Horizon"
        )


def _view_payload(view: InvestmentView) -> dict[str, object]:
    return {
        "portfolio_id": str(view.slice.portfolio_id.value),
        "instrument_id": str(view.slice.instrument_id.value),
        "horizon": view.slice.horizon.value,
        "thesis": view.thesis,
        "actor": _actor_payload(view.actor_attribution),
        "material_evidence": [str(item.value) for item in view.material_evidence],
        "assumptions": list(view.assumptions),
        "uncertainty": view.uncertainty,
        "alternative_explanation_or_dissent": view.alternative_explanation_or_dissent,
        "invalidation_conditions": list(view.invalidation_conditions),
        "material_signal_provenance": list(view.material_signal_provenance),
        "hypothesis_ids": [str(item.value) for item in view.hypothesis_ids],
    }


def _challenge_payload(challenge: MeaningfulChallengeResult) -> dict[str, object]:
    return {
        "actor": _actor_payload(challenge.actor_attribution),
        "strongest_competing_interpretation": (
            challenge.strongest_competing_interpretation
        ),
        "conflicting_evidence": [
            str(item.value) for item in challenge.conflicting_evidence
        ],
        "challenged_assumptions_uncertainty_or_conditions": (
            challenge.challenged_assumptions_uncertainty_or_conditions
        ),
        "disposition": challenge.disposition.value,
        "disposition_basis": challenge.disposition_basis,
        "hypothesis_ids": [str(item.value) for item in challenge.hypothesis_ids],
    }


def _alternative_payload(alternative: DecisionAlternative) -> dict[str, object]:
    return {
        "instrument_id": str(alternative.instrument_id.value),
        "horizon": alternative.horizon.value,
        "disposition": alternative.disposition.value,
        "material_comparison": alternative.material_comparison,
        "actor": _actor_payload(alternative.actor_attribution),
        "formed_at": alternative.formed_at.isoformat(),
        "valid": alternative.valid,
        "contested": alternative.contested,
    }


def _fingerprint(kind: str, payload: object) -> str:
    encoded = json.dumps([kind, payload], sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


def _receipt_ids_from_payload(value: object) -> tuple[JudgmentId, ...]:
    if not isinstance(value, list):
        raise ValueError("stored judgment receipt identities are invalid")
    identities: list[JudgmentId] = []
    for item in value:
        if not isinstance(item, list) or len(item) != 2:
            raise ValueError("stored judgment receipt identity is invalid")
        family, raw_id = item
        if not isinstance(family, str) or not isinstance(raw_id, str):
            raise ValueError("stored judgment receipt identity is invalid")
        identities.append(_RECEIPT_IDENTITIES[family](UUID(raw_id)))
    return tuple(identities)


def _receipt_ids_payload(identities: tuple[JudgmentId, ...]) -> list[list[str]]:
    return [[type(item).__name__, str(item.value)] for item in identities]


async def _latest_alternative(
    connection: AsyncConnection, alternative_id: DecisionAlternativeId
) -> DecisionAlternative | None:
    # duplicate-code: Alternative-root lookup must stay scoped to its own revision
    # history; sharing Configuration's unrelated row loader would conflate owners.
    # arid: disable
    row = (
        (
            await connection.execute(
                select(
                    decision_alternatives.c.decision_id, decision_alternative_revisions
                )
                .join(
                    decision_alternative_revisions,
                    decision_alternatives.c.alternative_id
                    == decision_alternative_revisions.c.alternative_id,
                )
                .where(decision_alternatives.c.alternative_id == alternative_id.value)
                .order_by(decision_alternative_revisions.c.revision.desc())
                .limit(1)
            )
        )
        .mappings()
        .first()
    )
    # arid: enable
    if row is None:
        return None
    return _alternative_from_row(alternative_id, row)


def _alternative_from_row(
    alternative_id: DecisionAlternativeId, row: RowMapping
) -> DecisionAlternative:
    payload = row["payload"]
    return DecisionAlternative(
        alternative_id,
        InvestmentDecisionId(_uuid(row["decision_id"])),
        FinancialInstrumentId(UUID(payload["instrument_id"])),
        InvestmentHorizon(payload["horizon"]),
        EconomicDisposition(payload["disposition"]),
        payload["material_comparison"],
        _actor_from_payload(payload["actor"]),
        datetime.fromisoformat(payload["formed_at"]),
        row["revision"],
        payload["valid"],
        payload["contested"],
    )


async def _material_alternatives_for_decision(
    connection: AsyncConnection, decision_id: InvestmentDecisionId
) -> tuple[DecisionAlternative, ...]:
    rows = (
        (
            await connection.execute(
                select(
                    decision_alternatives.c.decision_id,
                    decision_alternative_revisions,
                )
                .join(
                    decision_alternative_revisions,
                    decision_alternatives.c.alternative_id
                    == decision_alternative_revisions.c.alternative_id,
                )
                .where(decision_alternatives.c.decision_id == decision_id.value)
                .order_by(
                    decision_alternative_revisions.c.alternative_id,
                    decision_alternative_revisions.c.revision.desc(),
                )
            )
        )
        .mappings()
        .all()
    )
    latest: dict[DecisionAlternativeId, DecisionAlternative] = {}
    for row in rows:
        alternative_id = DecisionAlternativeId(_uuid(row["alternative_id"]))
        if alternative_id not in latest:
            latest[alternative_id] = _alternative_from_row(alternative_id, row)
    return tuple(latest.values())


async def _row_by_id(
    connection: AsyncConnection, table: Table, identity: Column[Any], value: UUID
) -> RowMapping | None:
    result = await connection.execute(select(table).where(identity == value))
    return result.mappings().first()


async def _latest_selection(
    connection: AsyncConnection, decision_id: InvestmentDecisionId
) -> RowMapping | None:
    result = await connection.execute(
        select(decision_alternative_selections)
        .where(decision_alternative_selections.c.decision_id == decision_id.value)
        .order_by(decision_alternative_selections.c.selection_revision.desc())
        .limit(1)
    )
    return result.mappings().first()


class PostgresInvestmentIntelligenceStore:
    """Store typed business judgments, without promoting adapter/process identity."""

    def __init__(
        self,
        engine: AsyncEngine,
        *,
        basis_reader: PostgresCurrentBasisReader | None = None,
    ) -> None:
        require_qualified_postgres_runtime()
        if basis_reader is not None and basis_reader.engine is not engine:
            raise ValueError("Evidence owner query must use the write engine")
        self._engine = engine
        self._basis_reader = basis_reader

    @asynccontextmanager
    async def _read_connection(self, purpose: str) -> AsyncIterator[AsyncConnection]:
        try:
            async with self._engine.connect() as connection:
                yield connection
        except (SQLAlchemyError, ValueError, TypeError, KeyError) as error:
            raise JudgmentPersistenceUnavailable(
                f"{purpose} read unavailable"
            ) from error

    async def _commit(
        self,
        operation_id: OperationId,
        kind: str,
        payload: object,
        write: Callable[[AsyncConnection], Awaitable[tuple[JudgmentId, ...]]],
        evidence_bases: tuple[CurrentEvidenceBasis, ...] = (),
    ) -> JudgmentReceipt | StaleEvidenceBasis | CurrentEvidenceNoBasis:
        if type(operation_id) is not OperationId:
            raise TypeError("operation_id must be OperationId")
        captured = tuple(basis_payload(item) for item in evidence_bases)
        fingerprint = _fingerprint(kind, [payload, captured])
        try:
            async with self._engine.begin() as connection:
                await connection.execute(
                    text("SELECT pg_advisory_xact_lock(:key)"), {"key": _WRITE_LOCK}
                )
                prior = (
                    (
                        await connection.execute(
                            select(investment_intelligence_command_receipts).where(
                                investment_intelligence_command_receipts.c.operation_id
                                == operation_id.value
                            )
                        )
                    )
                    .mappings()
                    .first()
                )
                if prior is not None:
                    if prior["request_fingerprint"] != fingerprint:
                        raise JudgmentIdempotencyConflict(
                            "operation ID was used for another judgment request"
                        )
                    return JudgmentReceipt(
                        operation_id, _receipt_ids_from_payload(prior["judgment_ids"])
                    )
                invalid = await self._validate_bases(connection, evidence_bases)
                if invalid is not None:
                    return invalid
                judgment_ids = await write(connection)
                await connection.execute(
                    insert(investment_intelligence_command_receipts).values(
                        operation_id=operation_id.value,
                        request_fingerprint=fingerprint,
                        judgment_ids=_receipt_ids_payload(judgment_ids),
                        committed_at=datetime.now(UTC),
                    )
                )
                for index, basis in enumerate(captured):
                    await connection.execute(
                        insert(investment_intelligence_judgment_bases).values(
                            operation_id=operation_id.value,
                            basis_index=index,
                            basis=basis,
                        )
                    )
                return JudgmentReceipt(operation_id, judgment_ids)
        except (SQLAlchemyError, ValueError, TypeError, KeyError) as error:
            if isinstance(
                error,
                (
                    JudgmentConcurrencyConflict,
                    JudgmentIdempotencyConflict,
                    InvalidInvestmentJudgment,
                ),
            ):
                raise
            raise JudgmentPersistenceUnavailable(
                "Investment Intelligence commit unavailable"
            ) from error

    async def _validate_bases(
        self,
        connection: AsyncConnection,
        bases: tuple[CurrentEvidenceBasis, ...],
    ) -> StaleEvidenceBasis | CurrentEvidenceNoBasis | None:
        if not bases:
            return None
        reader = self._basis_reader
        if reader is None:
            basis = bases[0]
            return CurrentEvidenceNoBasis(
                basis.key,
                basis.at,
                CurrentNoBasisReason.UNAVAILABLE,
                "current-basis provider is unavailable",
            )
        participation = PostgresIntelligenceBasisParticipation(connection, reader)
        revalidator = CurrentEvidenceBasisRevalidator()
        for basis in bases:
            outcome = await revalidator.revalidate(basis, participation)
            if outcome is not None:
                return outcome
        return None

    async def _require_recommendation_inputs(
        self,
        connection: AsyncConnection,
        recommendation: InvestmentRecommendation,
        expected_decision_version: DecisionVersion,
    ) -> None:
        """Check the real owner facts protected by the complete basis lock."""
        from .portfolio_consequences import PostgresPortfolioConsequenceStore
        from .portfolio_judgment_history import PostgresPortfolioJudgmentHistoryStore
        from .portfolio_states import PostgresPortfolioStateStore

        await _require_decision_ordinary_work(
            connection, recommendation.decision_id, expected_decision_version
        )
        # duplicate-code: Sharing would hide distinct judgment checks.
        # arid: disable
        decision = await _row_by_id(
            connection,
            investment_decisions,
            investment_decisions.c.decision_id,
            recommendation.decision_id.value,
        )
        # arid: enable
        state = await PostgresPortfolioStateStore(self._engine).get(
            recommendation.source_state_id
        )
        if (
            decision is None
            or decision["applicability"] != "operative"
            or state is None
            or state.state.portfolio_id.value not in decision["scope_portfolio_ids"]
            or state.state.as_of > recommendation.formed_at
            or state.known_at > recommendation.formed_at
        ):
            raise InvalidInvestmentJudgment(
                "Recommendation requires an applicable Decision and actual State"
            )
        for view_id in recommendation.view_ids:
            row = await _row_by_id(
                connection, investment_views, investment_views.c.view_id, view_id.value
            )
            if (
                row is None
                or row["decision_id"] != recommendation.decision_id.value
                or row["payload"]["horizon"] != recommendation.horizon.value
            ):
                raise InvalidInvestmentJudgment("material View is not applicable")
        challenged_view_ids: set[InvestmentViewRef] = set()
        for challenge_id in recommendation.challenge_ids:
            # duplicate-code: Sharing would hide distinct judgment checks.
            # arid: disable
            row = await _row_by_id(
                connection,
                meaningful_challenges,
                meaningful_challenges.c.challenge_id,
                challenge_id.value,
            )
            # arid: enable
            if (
                row is None
                or row["decision_id"] != recommendation.decision_id.value
                or InvestmentViewRef(_uuid(row["view_id"]))
                not in recommendation.view_ids
            ):
                raise InvalidInvestmentJudgment(
                    "material challenge does not belong to a relied-upon View"
                )
            challenged_view_ids.add(InvestmentViewRef(_uuid(row["view_id"])))
        if challenged_view_ids != set(recommendation.view_ids):
            raise InvalidInvestmentJudgment(
                "each relied-upon View needs a substantive Challenge result"
            )
        alternatives = await _material_alternatives_for_decision(
            connection, recommendation.decision_id
        )
        require_minimum_alternatives(alternatives)
        if {(item.alternative_id.value, item.revision) for item in alternatives} != {
            (item.root.value, item.revision.value)
            for item in recommendation.alternatives
        } or any(
            not item.valid or item.contested or item.horizon != recommendation.horizon
            for item in alternatives
        ):
            raise InvalidInvestmentJudgment(
                "material Alternative versions are stale or incomplete"
            )
        consequence_store = PostgresPortfolioConsequenceStore(self._engine)
        at = await connection.scalar(text("SELECT clock_timestamp()"))
        assert isinstance(at, datetime)
        portfolio_reader = PortfolioJudgmentTargetReader(
            PostgresPortfolioJudgmentHistoryStore(self._engine).for_validation(
                connection
            )
        )
        for link in recommendation.consequences:
            recorded = await consequence_store.get(link.consequence_id)
            current = await portfolio_reader.read_at(
                link.consequence_id, effective_at=at, known_at=at
            )
            if (
                recorded is None
                or not isinstance(current, ResolvedTargetJudgment)
                or not isinstance(current.assertion, ProjectedPortfolioConsequence)
                or current.correction_support[-1].known_at > recommendation.formed_at
                or current.assertion.alternative != link.alternative
                or current.assertion.source_state_id != recommendation.source_state_id
                or current.assertion.source_as_of != state.state.as_of
                or current.assertion.horizon != recommendation.horizon
                or recorded.known_at > recommendation.formed_at
            ):
                raise InvalidInvestmentJudgment(
                    "each material Alternative needs its attributable consequence"
                )
        consequence_ids = {item.consequence_id for item in recommendation.consequences}
        await self._require_recommendation_risks(
            recommendation, state.state.as_of, consequence_ids, portfolio_reader, at
        )

    async def _require_recommendation_risks(
        self,
        recommendation: InvestmentRecommendation,
        state_as_of: datetime,
        consequence_ids: set[ProjectedPortfolioConsequenceRef],
        portfolio_reader: PortfolioJudgmentTargetReader,
        at: datetime,
    ) -> None:
        from .portfolio_risk import PostgresPortfolioRiskStore

        risk_store = PostgresPortfolioRiskStore(self._engine)
        for risk_id in recommendation.risk_assessment_ids:
            recorded = await risk_store.get(risk_id)
            current = await portfolio_reader.read_at(
                risk_id, effective_at=at, known_at=at
            )
            if (
                recorded is None
                or not isinstance(current, ResolvedTargetJudgment)
                or not isinstance(current.assertion, PortfolioRiskAssessment)
                or current.correction_support[-1].known_at > recommendation.formed_at
                or current.assertion.source_state_id != recommendation.source_state_id
                or current.assertion.source_as_of != state_as_of
                or current.assertion.horizon != recommendation.horizon
                or (
                    current.assertion.projected_consequence_id is not None
                    and current.assertion.projected_consequence_id
                    not in consequence_ids
                )
                or recorded.known_at > recommendation.formed_at
                or current.assertion.unresolved
            ):
                raise InvalidInvestmentJudgment(
                    "unresolved or mismatched Portfolio Risk cannot support finality"
                )

    async def record_view(
        self,
        operation_id: OperationId,
        view: InvestmentView,
        hypotheses: tuple[InvestmentHypothesis, ...],
        expected_decision_version: DecisionVersion,
        evidence_bases: tuple[CurrentEvidenceBasis, ...] = (),
    ) -> JudgmentReceipt | StaleEvidenceBasis | CurrentEvidenceNoBasis:
        payload = [
            expected_decision_version.value,
            _view_payload(view),
            _hypotheses_request_payload(hypotheses),
            str(view.view_id.value),
            str(view.decision_id.value),
            view.formed_at.isoformat(),
        ]

        async def write(connection: AsyncConnection) -> tuple[JudgmentId, ...]:
            await _require_decision_ordinary_work(
                connection, view.decision_id, expected_decision_version
            )
            await _require_decision_horizon(
                connection, view.decision_id, view.slice.horizon
            )
            await connection.execute(
                insert(investment_views).values(
                    view_id=view.view_id.value,
                    decision_id=view.decision_id.value,
                    formed_at=view.formed_at,
                    payload=_view_payload(view),
                )
            )
            await _append_initial_target(connection, view)
            await _append_hypotheses(connection, hypotheses)
            return (
                view.view_id,
                *(item.hypothesis_id for item in hypotheses),
            )

        return await self._commit(operation_id, "view", payload, write, evidence_bases)

    async def record_challenge(
        self,
        operation_id: OperationId,
        challenge: MeaningfulChallengeResult,
        hypotheses: tuple[InvestmentHypothesis, ...],
        expected_decision_version: DecisionVersion,
        evidence_bases: tuple[CurrentEvidenceBasis, ...] = (),
    ) -> JudgmentReceipt | StaleEvidenceBasis | CurrentEvidenceNoBasis:
        payload = [
            expected_decision_version.value,
            str(challenge.challenge_id.value),
            str(challenge.view_id.value),
            str(challenge.decision_id.value),
            challenge.formed_at.isoformat(),
            _challenge_payload(challenge),
            _hypotheses_request_payload(hypotheses),
        ]

        async def write(connection: AsyncConnection) -> tuple[JudgmentId, ...]:
            await _require_decision_ordinary_work(
                connection, challenge.decision_id, expected_decision_version
            )
            view_decision = await connection.scalar(
                select(investment_views.c.decision_id).where(
                    investment_views.c.view_id == challenge.view_id.value
                )
            )
            if view_decision != challenge.decision_id.value:
                raise InvalidInvestmentJudgment(
                    "Challenge must reference a View for the same Decision"
                )
            await connection.execute(
                insert(meaningful_challenges).values(
                    challenge_id=challenge.challenge_id.value,
                    view_id=challenge.view_id.value,
                    decision_id=challenge.decision_id.value,
                    formed_at=challenge.formed_at,
                    payload=_challenge_payload(challenge),
                )
            )
            await _append_initial_target(connection, challenge)
            await _append_hypotheses(connection, hypotheses)
            return (
                challenge.challenge_id,
                *(item.hypothesis_id for item in hypotheses),
            )

        return await self._commit(
            operation_id, "challenge", payload, write, evidence_bases
        )

    async def record_alternatives(
        self,
        operation_id: OperationId,
        alternatives: tuple[DecisionAlternative, ...],
        expected_decision_version: DecisionVersion,
    ) -> JudgmentReceipt:
        payload = [
            expected_decision_version.value,
            [
                [
                    str(item.alternative_id.value),
                    str(item.decision_id.value),
                    item.revision,
                    _alternative_payload(item),
                ]
                for item in alternatives
            ],
        ]

        async def write(connection: AsyncConnection) -> tuple[JudgmentId, ...]:
            await _require_decision_ordinary_work(
                connection, alternatives[0].decision_id, expected_decision_version
            )
            await _require_decision_horizon(
                connection, alternatives[0].decision_id, alternatives[0].horizon
            )
            for item in alternatives:
                if item.revision != 1:
                    raise InvalidInvestmentJudgment(
                        "new Alternative must begin at revision 1"
                    )
                await connection.execute(
                    insert(decision_alternatives).values(
                        alternative_id=item.alternative_id.value,
                        decision_id=item.decision_id.value,
                    )
                )
                await connection.execute(
                    insert(decision_alternative_revisions).values(
                        alternative_id=item.alternative_id.value,
                        revision=1,
                        recorded_at=datetime.now(UTC),
                        payload=_alternative_payload(item),
                    )
                )
            return tuple(item.alternative_id for item in alternatives)

        return await self._commit(operation_id, "alternatives", payload, write)

    async def revise_alternative(
        self,
        operation_id: OperationId,
        replacement: DecisionAlternative,
        expected_revision: int,
    ) -> JudgmentReceipt:
        payload = [
            str(replacement.alternative_id.value),
            expected_revision,
            replacement.revision,
            _alternative_payload(replacement),
        ]

        async def write(connection: AsyncConnection) -> tuple[JudgmentId, ...]:
            current = await _latest_alternative(connection, replacement.alternative_id)
            if current is None or current.revision != expected_revision:
                raise JudgmentConcurrencyConflict("Alternative root revision changed")
            if (
                current.decision_id != replacement.decision_id
                or current.instrument_id != replacement.instrument_id
                or current.horizon != replacement.horizon
                or current.disposition != replacement.disposition
            ):
                raise InvalidInvestmentJudgment(
                    "Alternative root identity, horizon, and choice cannot change"
                )
            if _alternative_payload(current) == _alternative_payload(replacement):
                raise InvalidInvestmentJudgment(
                    "unchanged Alternative does not advance root revision"
                )
            await connection.execute(
                insert(decision_alternative_revisions).values(
                    alternative_id=replacement.alternative_id.value,
                    revision=replacement.revision,
                    recorded_at=datetime.now(UTC),
                    payload=_alternative_payload(replacement),
                )
            )
            return (replacement.alternative_id,)

        return await self._commit(operation_id, "revise_alternative", payload, write)

    async def select_alternative(
        self,
        operation_id: OperationId,
        decision: InvestmentDecision,
        selected_id: DecisionAlternativeId | None,
        expected_selection_revision: int,
        expected_selected_revision: int | None,
    ) -> JudgmentReceipt:
        payload = [
            str(decision.decision_id.value),
            decision.version.value,
            str(selected_id.value) if selected_id is not None else None,
            expected_selection_revision,
            expected_selected_revision,
        ]

        async def write(connection: AsyncConnection) -> tuple[JudgmentId, ...]:
            await _require_decision_ordinary_work(
                connection, decision.decision_id, decision.version
            )
            previous = await _latest_selection(connection, decision.decision_id)
            actual = previous["selection_revision"] if previous else 0
            if actual != expected_selection_revision:
                raise JudgmentConcurrencyConflict("Alternative selection guard changed")
            previous_id = previous["selected_alternative_id"] if previous else None
            next_id = selected_id.value if selected_id is not None else None
            if selected_id is not None:
                selected = await _latest_alternative(connection, selected_id)
                if (
                    selected is None
                    or selected.decision_id != decision.decision_id
                    or not selected.valid
                    or selected.contested
                ):
                    raise InvalidInvestmentJudgment(
                        "selected Alternative is not currently applicable to Decision"
                    )
                if selected.revision != expected_selected_revision:
                    raise JudgmentConcurrencyConflict(
                        "selected Alternative root changed"
                    )
            if previous_id == next_id:
                return tuple(() if selected_id is None else (selected_id,))
            for changed_id in {
                item for item in (previous_id, next_id) if item is not None
            }:
                identity = DecisionAlternativeId(_uuid(changed_id))
                current = await _latest_alternative(connection, identity)
                assert current is not None
                await connection.execute(
                    insert(decision_alternative_revisions).values(
                        alternative_id=changed_id,
                        revision=current.revision + 1,
                        recorded_at=datetime.now(UTC),
                        payload=_alternative_payload(current),
                    )
                )
            await connection.execute(
                insert(decision_alternative_selections).values(
                    decision_id=decision.decision_id.value,
                    selection_revision=actual + 1,
                    selected_alternative_id=next_id,
                    recorded_at=datetime.now(UTC),
                )
            )
            return tuple(() if selected_id is None else (selected_id,))

        return await self._commit(operation_id, "select_alternative", payload, write)

    async def record_recommendation(
        self,
        operation_id: OperationId,
        recommendation: InvestmentRecommendation,
        expected_decision_version: DecisionVersion,
        evidence_bases: tuple[CurrentEvidenceBasis, ...],
        initial_claim_catalog: IntelligenceClaimCatalog,
    ) -> JudgmentReceipt | StaleEvidenceBasis | CurrentEvidenceNoBasis:
        if (
            type(recommendation) is not InvestmentRecommendation
            or type(initial_claim_catalog) is not IntelligenceClaimCatalog
            or type(evidence_bases) is not tuple
            or not evidence_bases
        ):
            raise InvalidInvestmentJudgment(
                "Recommendation needs typed judgment, catalog, and Evidence bases"
            )
        targets = {basis.key.target for basis in evidence_bases}
        if not (
            set(recommendation.view_ids) | set(recommendation.challenge_ids)
        ).issubset(targets):
            raise InvalidInvestmentJudgment(
                "each relied-upon View and challenge needs a current basis"
            )
        payload = [
            expected_decision_version.value,
            contract_value_payload(recommendation),
            contract_value_payload(initial_claim_catalog),
        ]

        async def write(connection: AsyncConnection) -> tuple[JudgmentId, ...]:
            await self._require_recommendation_inputs(
                connection, recommendation, expected_decision_version
            )
            await _append_initial_target(
                connection, recommendation, initial_claim_catalog
            )
            return (recommendation.recommendation_id,)

        return await self._commit(
            operation_id, "recommendation", payload, write, evidence_bases
        )

    async def record_withholding(
        self,
        operation_id: OperationId,
        withholding: RecommendationWithholdingJudgment,
        expected_decision_version: DecisionVersion,
        initial_claim_catalog: IntelligenceClaimCatalog,
        evidence_bases: tuple[CurrentEvidenceBasis, ...] = (),
    ) -> JudgmentReceipt | StaleEvidenceBasis | CurrentEvidenceNoBasis:
        if (
            type(withholding) is not RecommendationWithholdingJudgment
            or type(initial_claim_catalog) is not IntelligenceClaimCatalog
            or type(evidence_bases) is not tuple
            or any(type(item) is not CurrentEvidenceBasis for item in evidence_bases)
        ):
            raise InvalidInvestmentJudgment("typed withholding and catalog required")
        payload = [
            expected_decision_version.value,
            contract_value_payload(withholding),
            contract_value_payload(initial_claim_catalog),
        ]

        async def write(connection: AsyncConnection) -> tuple[JudgmentId, ...]:
            await _require_decision_ordinary_work(
                connection, withholding.decision_id, expected_decision_version
            )
            await _append_initial_target(connection, withholding, initial_claim_catalog)
            return (withholding.withholding_id,)

        return await self._commit(
            operation_id,
            "recommendation_withholding",
            payload,
            write,
            evidence_bases,
        )

    async def recommendation_history(
        self, decision_id: InvestmentDecisionId
    ) -> tuple[RecommendationEvent, ...]:
        if type(decision_id) is not InvestmentDecisionId:
            raise TypeError("history requires a typed Decision")
        async with self._read_connection("Recommendation history") as connection:
            rows = (
                (
                    await connection.execute(
                        select(investment_intelligence_judgment_acts.c.act)
                        .where(
                            investment_intelligence_judgment_acts.c.decision_id
                            == decision_id.value,
                            investment_intelligence_judgment_acts.c.sequence == 1,
                            investment_intelligence_judgment_acts.c.target_family.in_(
                                (
                                    "InvestmentRecommendationRef",
                                    "RecommendationWithholdingJudgmentRef",
                                )
                            ),
                        )
                        .order_by(investment_intelligence_judgment_acts.c.row_id)
                    )
                )
                .scalars()
                .all()
            )
        history: list[RecommendationEvent] = []
        for row in rows:
            act = contract_value_from_payload(row)
            if not isinstance(act, IntelligenceJudgmentAct):
                raise JudgmentPersistenceUnavailable(
                    "Recommendation history has invalid owner acts"
                )
            assertion = act.assertion
            if (
                not isinstance(
                    assertion,
                    (InvestmentRecommendation, RecommendationWithholdingJudgment),
                )
                or assertion.decision_id != decision_id
            ):
                raise JudgmentPersistenceUnavailable(
                    "Recommendation history has invalid owner acts"
                )
            history.append(assertion)
        return tuple(history)

    async def current_recommendation_support(
        self, decision_id: InvestmentDecisionId
    ) -> CurrentRecommendationSupport:
        """Derive current support from only the latest durable owner act."""
        if type(decision_id) is not InvestmentDecisionId:
            raise TypeError("support requires a typed Decision")
        async with self._engine.begin() as connection:
            await connection.execute(
                text("SELECT pg_advisory_xact_lock(:key)"), {"key": _WRITE_LOCK}
            )
            history = await self.recommendation_history(decision_id)
            if not history or type(history[-1]) is RecommendationWithholdingJudgment:
                return derive_current_recommendation_support(
                    history,
                    decision_applicable=False,
                    evidence_fit=False,
                    risk_fit=False,
                )
            latest = history[-1]
            assert isinstance(latest, InvestmentRecommendation)
            at = await connection.scalar(text("SELECT clock_timestamp()"))
            assert isinstance(at, datetime)
            current_recommendation = await IntelligenceJudgmentTargetReader(
                PostgresIntelligenceJudgmentHistoryStore(self._engine).for_validation(
                    connection
                )
            ).read_at(latest.recommendation_id, effective_at=at, known_at=at)
            recommendation_fit = (
                isinstance(current_recommendation, ResolvedTargetJudgment)
                and current_recommendation.assertion == latest
            )
            receipt = (
                (
                    await connection.execute(
                        select(
                            investment_intelligence_command_receipts.c.operation_id
                        ).where(
                            investment_intelligence_command_receipts.c.judgment_ids.contains(
                                [
                                    [
                                        "InvestmentRecommendationRef",
                                        str(latest.recommendation_id.value),
                                    ]
                                ]
                            )
                        )
                    )
                )
                .scalars()
                .one_or_none()
            )
            if receipt is None:
                raise JudgmentPersistenceUnavailable(
                    "Recommendation is missing its accepted command receipt"
                )
            basis_rows = (
                (
                    await connection.execute(
                        select(investment_intelligence_judgment_bases.c.basis)
                        .where(
                            investment_intelligence_judgment_bases.c.operation_id
                            == receipt
                        )
                        .order_by(investment_intelligence_judgment_bases.c.basis_index)
                    )
                )
                .scalars()
                .all()
            )
            bases = tuple(basis_from_payload(row) for row in basis_rows)
            reader = self._basis_reader
            evidence_fit = recommendation_fit and bool(bases) and reader is not None
            if evidence_fit:
                participation = PostgresIntelligenceBasisParticipation(
                    connection, reader
                )
                revalidator = CurrentEvidenceBasisRevalidator()
                for basis in bases:
                    if await revalidator.revalidate(basis, participation) is not None:
                        evidence_fit = False
                        break
            decision = await _row_by_id(
                connection,
                investment_decisions,
                investment_decisions.c.decision_id,
                decision_id.value,
            )
            decision_applicable = (
                decision is not None and decision["applicability"] == "operative"
            )
            risk_fit = evidence_fit and await self._current_risks_fit(
                latest, at, connection
            )
            return derive_current_recommendation_support(
                history,
                decision_applicable=decision_applicable,
                evidence_fit=evidence_fit,
                risk_fit=risk_fit,
            )

    async def _current_risks_fit(
        self,
        recommendation: InvestmentRecommendation,
        at: datetime,
        connection: AsyncConnection,
    ) -> bool:
        from .portfolio_judgment_history import PostgresPortfolioJudgmentHistoryStore
        from .portfolio_states import PostgresPortfolioStateStore

        state = await PostgresPortfolioStateStore(self._engine).get(
            recommendation.source_state_id
        )
        if state is None:
            return False
        risk_reader = PortfolioJudgmentTargetReader(
            PostgresPortfolioJudgmentHistoryStore(self._engine).for_validation(
                connection
            )
        )
        for risk_id in recommendation.risk_assessment_ids:
            risk = await risk_reader.read_at(risk_id, effective_at=at, known_at=at)
            if (
                not isinstance(risk, ResolvedTargetJudgment)
                or risk.target != risk_id
                or risk.assertion.unresolved
                or risk.assertion.source_as_of != state.state.as_of
            ):
                return False
        return True

    async def load_view(self, view_id: InvestmentViewRef) -> InvestmentView | None:
        async with self._read_connection("View") as connection:
            row = await _row_by_id(
                connection, investment_views, investment_views.c.view_id, view_id.value
            )
            if row is None:
                return None
            p = row["payload"]
            return InvestmentView(
                view_id,
                InvestmentDecisionId(_uuid(row["decision_id"])),
                R3InvestmentSlice(
                    PortfolioId(UUID(p["portfolio_id"])),
                    FinancialInstrumentId(UUID(p["instrument_id"])),
                    InvestmentHorizon(p["horizon"]),
                ),
                p["thesis"],
                _actor_from_payload(p["actor"]),
                row["formed_at"],
                tuple(
                    EvidenceBindingId(UUID(value)) for value in p["material_evidence"]
                ),
                tuple(p["assumptions"]),
                p["uncertainty"],
                p["alternative_explanation_or_dissent"],
                tuple(p["invalidation_conditions"]),
                tuple(p["material_signal_provenance"]),
                tuple(
                    InvestmentHypothesisRef(UUID(value))
                    for value in p["hypothesis_ids"]
                ),
            )

    async def load_hypothesis(
        self, hypothesis_id: InvestmentHypothesisRef
    ) -> InvestmentHypothesis | None:
        async with self._read_connection("Hypothesis") as connection:
            row = await _row_by_id(
                connection,
                investment_hypotheses,
                investment_hypotheses.c.hypothesis_id,
                hypothesis_id.value,
            )
            if row is None:
                return None
            payload = row["payload"]
            target_type = _MATERIAL_TARGETS[row["material_to_family"]]
            return InvestmentHypothesis(
                hypothesis_id,
                InvestmentDecisionId(_uuid(row["decision_id"])),
                payload["statement"],
                target_type(_uuid(row["material_to_id"])),
                _actor_from_payload(payload["actor"]),
                row["formed_at"],
            )

    async def load_challenge(
        self, challenge_id: MeaningfulChallengeResultRef
    ) -> MeaningfulChallengeResult | None:
        async with self._read_connection("Challenge") as connection:
            row = await _row_by_id(
                connection,
                meaningful_challenges,
                meaningful_challenges.c.challenge_id,
                challenge_id.value,
            )
            if row is None:
                return None
            p = row["payload"]
            return MeaningfulChallengeResult(
                challenge_id,
                InvestmentViewRef(_uuid(row["view_id"])),
                InvestmentDecisionId(_uuid(row["decision_id"])),
                _actor_from_payload(p["actor"]),
                row["formed_at"],
                p["strongest_competing_interpretation"],
                tuple(
                    EvidenceBindingId(UUID(value))
                    for value in p["conflicting_evidence"]
                ),
                p["challenged_assumptions_uncertainty_or_conditions"],
                ChallengeDisposition(p["disposition"]),
                p["disposition_basis"],
                tuple(
                    InvestmentHypothesisRef(UUID(value))
                    for value in p["hypothesis_ids"]
                ),
            )

    async def load_alternative(
        self, alternative_id: DecisionAlternativeId, *, revision: int | None = None
    ) -> DecisionAlternative | None:
        if revision is not None and (type(revision) is not int or revision < 1):
            raise InvalidInvestmentJudgment("Alternative revision must be positive")
        async with self._read_connection("Alternative") as connection:
            if revision is None:
                return await _latest_alternative(connection, alternative_id)
            result = await connection.execute(
                select(
                    decision_alternatives.c.decision_id, decision_alternative_revisions
                )
                .join(decision_alternative_revisions)
                .where(
                    decision_alternatives.c.alternative_id == alternative_id.value,
                    decision_alternative_revisions.c.revision == revision,
                )
            )
            row = result.mappings().first()
            return (
                _alternative_from_row(alternative_id, row) if row is not None else None
            )

    async def for_decision(
        self, decision_id: InvestmentDecisionId
    ) -> tuple[DecisionAlternative, ...]:
        """Read every material Alternative at its current owner-issued revision."""
        if type(decision_id) is not InvestmentDecisionId:
            raise TypeError("decision_id must be InvestmentDecisionId")
        async with self._read_connection("material Alternatives") as connection:
            return await _material_alternatives_for_decision(connection, decision_id)

    async def load_selection(
        self, decision_id: InvestmentDecisionId
    ) -> tuple[DecisionAlternativeId | None, int]:
        async with self._read_connection("Alternative selection") as connection:
            row = await _latest_selection(connection, decision_id)
            if row is None:
                return None, 0
            selected = row["selected_alternative_id"]
            return (
                DecisionAlternativeId(_uuid(selected))
                if selected is not None
                else None,
                row["selection_revision"],
            )
