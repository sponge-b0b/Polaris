"""A live Intelligence owner correction invalidates a dependent PostgreSQL write."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select, text

from polaris.application.decisions import (
    DecisionCommandEnvelope,
    DecisionInitiationService,
    InitiateDecisionCommand,
)
from polaris.application.decisions.memory import DecisionMemoryService
from polaris.application.decisions.owner_meaning import DecisionOwnerMeaningReader
from polaris.application.evidence.context_versions import ContextSelectionResolver
from polaris.application.evidence.current_basis import (
    CurrentEvidenceBasis,
    CurrentEvidenceBasisQuery,
    ResolvedRequirementKey,
)
from polaris.application.evidence.judgment_versions import TargetJudgmentResolver
from polaris.application.evidence.reconstruction import (
    EvidenceHistories,
    StaleEvidenceBasis,
    StaleEvidenceBasisCategory,
)
from polaris.application.evidence.requirements import ResolvedEvidenceRequirementVersion
from polaris.application.intelligence_judgment_history import (
    IntelligenceJudgmentClaimResolver,
    IntelligenceJudgmentMeaningReader,
    IntelligenceJudgmentTargetReader,
)
from polaris.application.investment_intelligence import (
    FIRST_R3_SPY_INSTRUMENT_ID,
    InvestmentIntelligenceService,
    JudgmentReceipt,
)
from polaris.domain.actors import ActorId, KnownActorAttribution
from polaris.domain.configuration import (
    EvidenceRequirementApplicabilityKey,
    InvestmentHorizon,
)
from polaris.domain.decisions import (
    DecisionScope,
    DecisionSubject,
    InvestmentDecisionId,
    OperationId,
    TechnicalProvenance,
    TriggerKind,
    TriggerProvenance,
)
from polaris.domain.evidence import EvidenceSupportVersion
from polaris.domain.evidence.context_versions import BasisScopeKey
from polaris.domain.evidence.judgments import (
    EvidenceUse,
    InvestmentViewRef,
    JudgmentWideEvidenceScope,
    MeaningfulChallengeResultRef,
)
from polaris.domain.intelligence_judgment_history import (
    IntelligenceJudgmentAct,
    IntelligenceJudgmentStatus,
)
from polaris.domain.investment_intelligence import InvestmentView, R3InvestmentSlice
from polaris.domain.portfolio import PortfolioId
from polaris.infrastructure.persistence.postgresql import (
    PostgresCurrentBasisReader,
    PostgresDecisionStore,
    PostgresIntelligenceJudgmentHistoryStore,
    PostgresInvestmentIntelligenceStore,
    create_postgres_engine,
)
from polaris.infrastructure.persistence.postgresql.intelligence_contract_codec import (
    basis_from_payload,
    register_owner_value_type,
)
from polaris.infrastructure.persistence.postgresql.schema import (
    investment_intelligence_judgment_bases,
)
from tests.application.evidence.test_current_basis import (
    _Claims,
    _Contexts,
    _Epochs,
    _Evidence,
    _MeaningOwner,
    _Relationship,
    _Sufficiency,
    _Targets,
    _Universe,
)
from tests.domain.configuration.configuration_support import (
    requirement_assignment_for_key,
    requirement_version,
)

from .conftest import PostgresTestTarget

START = datetime(2026, 10, 20, tzinfo=UTC)


class _RequirementKeyOwner:
    def __init__(self, applicability: EvidenceRequirementApplicabilityKey) -> None:
        self.applicability = applicability

    async def read_current(self, key, target, context, *, at):
        assert target.target == key.target and context.key == key
        return ResolvedRequirementKey(key, at, self.applicability)


class _Requirements:
    def __init__(self, applicability: EvidenceRequirementApplicabilityKey) -> None:
        self.version = replace(
            requirement_version(),
            applicability=requirement_assignment_for_key(applicability),
        )

    async def resolve(self, key, *, effective_at, known_at):
        return ResolvedEvidenceRequirementVersion(self.version)


class _PauseFreshQuery:
    def __init__(self, query: CurrentEvidenceBasisQuery, prior_at: datetime) -> None:
        self.query = query
        self.prior_at = prior_at
        self.entered = asyncio.Event()
        self.release = asyncio.Event()

    async def read(self, key, *, at):
        result = await self.query.read(key, at=at)
        if at > self.prior_at:
            self.entered.set()
            await self.release.wait()
        return result

    async def verify_owner_meaning(self, basis, *, validation_at):
        return await self.query.verify_owner_meaning(basis, validation_at=validation_at)


def _query_for_intelligence_target(
    decision_store: PostgresDecisionStore,
    owner_store: PostgresIntelligenceJudgmentHistoryStore,
    decision_id: InvestmentDecisionId,
    root: InvestmentViewRef | MeaningfulChallengeResultRef,
) -> tuple[CurrentEvidenceBasisQuery, BasisScopeKey]:
    contexts = _Contexts()
    context_meaning = _MeaningOwner(_Targets(None), contexts, _Claims())
    scope = JudgmentWideEvidenceScope()
    use = EvidenceUse.JUDGMENT_BASIS
    applicability = EvidenceRequirementApplicabilityKey(root, scope, use)
    query = CurrentEvidenceBasisQuery(
        decisions=DecisionMemoryService(reader=decision_store),
        decision_meaning=DecisionOwnerMeaningReader(decision_store),
        targets=TargetJudgmentResolver(IntelligenceJudgmentTargetReader(owner_store)),
        target_meaning=IntelligenceJudgmentMeaningReader(owner_store),
        contexts=ContextSelectionResolver(contexts),
        context_meaning=context_meaning,
        requirement_keys=_RequirementKeyOwner(applicability),
        sufficiency=_Sufficiency(EvidenceSupportVersion(1), applicability, empty=True),
        evidence=_Evidence(EvidenceHistories((), (), ()), root),
        support_epochs=_Epochs(EvidenceSupportVersion(1)),
        claims=IntelligenceJudgmentClaimResolver(owner_store),
        claim_meaning=IntelligenceJudgmentMeaningReader(owner_store),
        requirements=_Requirements(applicability),
    )
    return query, BasisScopeKey(
        decision_id=decision_id, target=root, scope=scope, use=use
    )


def _view(decision, portfolio_id: PortfolioId, actor) -> InvestmentView:
    return InvestmentView(
        InvestmentViewRef(uuid4()),
        decision.decision_id,
        R3InvestmentSlice(
            portfolio_id, FIRST_R3_SPY_INSTRUMENT_ID, InvestmentHorizon("three months")
        ),
        "SPY exposure may merit review",
        actor,
        START,
        (),
        ("cash remains adequate",),
        "outcomes remain uncertain",
        "holding cash may be preferable",
        ("liquidity deteriorates",),
        # duplicate-code: Sharing would hide atomic-basis proof.
        # arid: disable
    )


async def _scenario(target: PostgresTestTarget) -> None:
    register_owner_value_type(_Relationship)
    register_owner_value_type(_Universe)
    engine = create_postgres_engine(target.database_url, schema=target.schema)
    try:
        # arid: enable
        decision_store = PostgresDecisionStore(engine)
        actor = KnownActorAttribution(ActorId(uuid4()))
        portfolio_id = PortfolioId(uuid4())
        accepted = await DecisionInitiationService(
            reader=decision_store,
            store=decision_store,
            now=lambda: START,
            # duplicate-code: Sharing would hide atomic-basis proof.
            # arid: disable
        ).initiate(
            InitiateDecisionCommand(
                envelope=DecisionCommandEnvelope(
                    operation_id=OperationId(uuid4()),
                    actor_attribution=actor,
                    trigger=TriggerProvenance(TriggerKind.HUMAN_REQUEST, "user-399"),
                    # arid: enable
                    effective_at=START,
                    # duplicate-code: Sharing would hide atomic-basis proof.
                    # arid: disable
                    technical_provenance=TechnicalProvenance(),
                    expected_versions=frozenset(),
                ),
                need_statement="Choose SPY exposure",
                subject=DecisionSubject("Increase, hold, or reduce SPY"),
                # arid: enable
                scope=DecisionScope.established(portfolio_id),
            )
        )
        state = await decision_store.load_decision_for_command(
            accepted.decision_id, known_at=START
        )
        assert state is not None
        decision = state.decision
        plain = InvestmentIntelligenceService(
            PostgresInvestmentIntelligenceStore(engine)
        )
        original = _view(decision, portfolio_id, actor)
        assert isinstance(
            await plain.record_view(OperationId(uuid4()), decision, original),
            JudgmentReceipt,
        )

        owner_store = PostgresIntelligenceJudgmentHistoryStore(engine)
        query, key = _query_for_intelligence_target(
            decision_store, owner_store, decision.decision_id, original.view_id
        )
        prior = await query.read(key, at=datetime.now(UTC))
        assert isinstance(prior, CurrentEvidenceBasis)
        store = PostgresInvestmentIntelligenceStore(
            engine, basis_reader=PostgresCurrentBasisReader(engine, query)
        )
        service = InvestmentIntelligenceService(store)
        accepted_view = _view(decision, portfolio_id, actor)
        accepted_operation = OperationId(uuid4())
        accepted_result = await service.record_view(
            accepted_operation, decision, accepted_view, evidence_bases=(prior,)
        )
        assert isinstance(accepted_result, JudgmentReceipt)
        async with engine.connect() as connection:
            captured = (
                await connection.execute(
                    select(investment_intelligence_judgment_bases.c.basis).where(
                        investment_intelligence_judgment_bases.c.operation_id
                        == accepted_operation.value
                    )
                )
            ).scalar_one()
        assert basis_from_payload(captured) == prior

        paused = _PauseFreshQuery(query, prior.at)
        paused_service = InvestmentIntelligenceService(
            PostgresInvestmentIntelligenceStore(
                engine, basis_reader=PostgresCurrentBasisReader(engine, paused)
            )
        )
        protected_view = _view(decision, portfolio_id, actor)
        dependent = asyncio.create_task(
            paused_service.record_view(
                OperationId(uuid4()),
                decision,
                protected_view,
                evidence_bases=(prior,),
            )
        )
        await asyncio.wait_for(paused.entered.wait(), timeout=5)

        async def unrelated_owner_write() -> None:
            async with engine.begin() as connection:
                await connection.execute(
                    text(
                        "UPDATE investment_decisions "
                        "SET subject_statement = subject_statement "
                        "WHERE decision_id = :decision_id"
                    ),
                    {"decision_id": decision.decision_id.value},
                )

        concurrent = asyncio.create_task(unrelated_owner_write())
        await asyncio.sleep(0.05)
        assert not concurrent.done()
        paused.release.set()
        assert isinstance(await asyncio.wait_for(dependent, timeout=5), JudgmentReceipt)
        await asyncio.wait_for(concurrent, timeout=5)

        history = await owner_store.load(original.view_id)
        assert history is not None
        initial = history.acts[0]
        correction_at = datetime.now(UTC)
        await owner_store.append(
            IntelligenceJudgmentAct(
                act_id=uuid4(),
                root=original.view_id,
                attribution=actor,
                basis="owner revised the material View",
                effective_at=correction_at,
                recorded_at=correction_at,
                known_at=correction_at,
                ancestry=(initial.act_id,),
                assertion=replace(original, thesis="SPY exposure may remain unchanged"),
                target_predecessor=initial.act_id,
                compatible_opposite_acts=(initial.act_id,),
                target_status=IntelligenceJudgmentStatus.ACTIVE,
            )
        )
        rejected_view = _view(decision, portfolio_id, actor)
        rejected = await service.record_view(
            OperationId(uuid4()), decision, rejected_view, evidence_bases=(prior,)
        )
        assert isinstance(rejected, StaleEvidenceBasis)
        assert rejected.categories == {StaleEvidenceBasisCategory.TARGET_CHANGED}
        assert await store.load_view(rejected_view.view_id) is None
    finally:
        await engine.dispose()


def test_real_owner_correction_stales_consumed_basis_atomically(
    postgres_target: PostgresTestTarget,
) -> None:
    asyncio.run(_scenario(postgres_target))
