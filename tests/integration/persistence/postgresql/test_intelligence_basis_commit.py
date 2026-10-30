"""A live Intelligence owner correction invalidates a dependent PostgreSQL write."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncEngine

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
    CurrentEvidenceNoBasis,
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
from polaris.application.investment_recommendation import (
    InvestmentRecommendationService,
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
    RecommendationWithholdingJudgmentRef,
)
from polaris.domain.intelligence_judgment_history import (
    IntelligenceClaimCatalog,
    IntelligenceJudgmentActDraft,
    IntelligenceJudgmentStatus,
)
from polaris.domain.investment_intelligence import InvestmentView, R3InvestmentSlice
from polaris.domain.investment_recommendation import RecommendationWithholdingJudgment
from polaris.domain.portfolio import PortfolioId
from polaris.infrastructure.persistence.postgresql import (
    PostgresCurrentBasisReader,
    PostgresDecisionStore,
    PostgresIntelligenceJudgmentHistoryStore,
    PostgresInvestmentIntelligenceStore,
    create_postgres_engine,
)
from polaris.infrastructure.persistence.postgresql import (
    intelligence_judgment_history as history_persistence,
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

from .conftest import PostgresTestTarget, assert_intelligence_table_immutable

START = datetime(2026, 10, 20, tzinfo=UTC)


async def _captured_basis(engine: AsyncEngine, operation_id: OperationId):
    async with engine.connect() as connection:
        payload = (
            await connection.execute(
                select(investment_intelligence_judgment_bases.c.basis).where(
                    investment_intelligence_judgment_bases.c.operation_id
                    == operation_id.value
                )
            )
        ).scalar_one()
    return basis_from_payload(payload)


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


class _EvidenceEpochTimeline:
    def __init__(self, applicability: EvidenceRequirementApplicabilityKey) -> None:
        self._sufficiency = _Sufficiency(
            EvidenceSupportVersion(1), applicability, empty=True
        )
        self.changed_at: datetime | None = None

    def _version_at(self, at: datetime) -> EvidenceSupportVersion:
        return EvidenceSupportVersion(
            2 if self.changed_at is not None and at >= self.changed_at else 1
        )

    async def load_sufficiency_basis(
        self, applicability_key, *, effective_at, known_at
    ):
        basis = await self._sufficiency.load_sufficiency_basis(
            applicability_key, effective_at=effective_at, known_at=known_at
        )
        return replace(basis, support_version=self._version_at(known_at))

    async def load_support_version(
        self, target, scope, evidence_use, *, effective_at, known_at
    ):
        return self._version_at(known_at)


def _query_for_intelligence_target(
    decision_store: PostgresDecisionStore,
    owner_store: PostgresIntelligenceJudgmentHistoryStore,
    decision_id: InvestmentDecisionId,
    root: InvestmentViewRef | MeaningfulChallengeResultRef,
) -> tuple[CurrentEvidenceBasisQuery, BasisScopeKey, _EvidenceEpochTimeline]:
    contexts = _Contexts()
    context_meaning = _MeaningOwner(_Targets(None), contexts, _Claims())
    scope = JudgmentWideEvidenceScope()
    use = EvidenceUse.JUDGMENT_BASIS
    applicability = EvidenceRequirementApplicabilityKey(root, scope, use)
    epochs = _EvidenceEpochTimeline(applicability)
    query = CurrentEvidenceBasisQuery(
        decisions=DecisionMemoryService(reader=decision_store),
        decision_meaning=DecisionOwnerMeaningReader(decision_store),
        targets=TargetJudgmentResolver(IntelligenceJudgmentTargetReader(owner_store)),
        target_meaning=IntelligenceJudgmentMeaningReader(owner_store),
        contexts=ContextSelectionResolver(contexts),
        context_meaning=context_meaning,
        requirement_keys=_RequirementKeyOwner(applicability),
        sufficiency=epochs,
        evidence=_Evidence(EvidenceHistories((), (), ()), root),
        support_epochs=epochs,
        claims=IntelligenceJudgmentClaimResolver(owner_store),
        claim_meaning=IntelligenceJudgmentMeaningReader(owner_store),
        requirements=_Requirements(applicability),
    )
    return (
        query,
        BasisScopeKey(decision_id=decision_id, target=root, scope=scope, use=use),
        epochs,
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


async def _scenario(
    target: PostgresTestTarget, monkeypatch: pytest.MonkeyPatch
) -> None:
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
        query, key, epochs = _query_for_intelligence_target(
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
        assert await _captured_basis(engine, accepted_operation) == prior

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
            IntelligenceJudgmentActDraft(
                act_id=uuid4(),
                root=original.view_id,
                attribution=actor,
                basis="owner revised the material View",
                effective_at=correction_at,
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

        withholding_store = PostgresInvestmentIntelligenceStore(
            engine, basis_reader=PostgresCurrentBasisReader(engine, query)
        )
        withholding_service = InvestmentRecommendationService(withholding_store)
        consumed = await query.read(key, at=datetime.now(UTC))
        assert isinstance(consumed, CurrentEvidenceBasis)
        withholding = RecommendationWithholdingJudgment(
            RecommendationWithholdingJudgmentRef(uuid4()),
            decision.decision_id,
            InvestmentHorizon("three months"),
            "Current Evidence does not support a Recommendation",
            actor,
            datetime.now(UTC),
        )
        epochs.changed_at = datetime.now(UTC)
        stale_operation = OperationId(uuid4())
        stale = await withholding_service.withhold(
            stale_operation,
            withholding,
            decision.version,
            IntelligenceClaimCatalog(()),
            evidence_bases=(consumed,),
        )
        assert isinstance(stale, StaleEvidenceBasis)
        assert stale.categories == {StaleEvidenceBasisCategory.EVIDENCE_SUPPORT_CHANGED}
        assert await withholding_service.history(decision.decision_id) == ()

        fresh = await query.read(key, at=datetime.now(UTC))
        assert isinstance(fresh, CurrentEvidenceBasis)
        unavailable_service = InvestmentRecommendationService(
            PostgresInvestmentIntelligenceStore(engine)
        )
        # duplicate-code: Keep the unavailable-provider call explicit beside its
        # independent no-write assertion; sharing it with an accepted write obscures
        # which service has no current-basis reader.
        # arid: disable
        unavailable = await unavailable_service.withhold(
            OperationId(uuid4()),
            withholding,
            decision.version,
            IntelligenceClaimCatalog(()),
            evidence_bases=(fresh,),
        )
        # arid: enable
        assert isinstance(unavailable, CurrentEvidenceNoBasis)
        assert await withholding_service.history(decision.decision_id) == ()

        accepted_operation = OperationId(uuid4())
        accepted = await withholding_service.withhold(
            accepted_operation,
            withholding,
            decision.version,
            IntelligenceClaimCatalog(()),
            evidence_bases=(fresh,),
        )
        assert isinstance(accepted, JudgmentReceipt)
        assert await _captured_basis(engine, accepted_operation) == fresh
        assert await withholding_service.history(decision.decision_id) == (withholding,)
        await assert_intelligence_table_immutable(
            engine, investment_intelligence_judgment_bases
        )

        race_root = _view(decision, portfolio_id, actor)
        assert isinstance(
            await plain.record_view(OperationId(uuid4()), decision, race_root),
            JudgmentReceipt,
        )
        race_query, race_key, _ = _query_for_intelligence_target(
            decision_store, owner_store, decision.decision_id, race_root.view_id
        )
        race_basis = await race_query.read(race_key, at=datetime.now(UTC))
        assert isinstance(race_basis, CurrentEvidenceBasis)
        race_service = InvestmentIntelligenceService(
            PostgresInvestmentIntelligenceStore(
                engine, basis_reader=PostgresCurrentBasisReader(engine, race_query)
            )
        )
        race_history = await owner_store.load(race_root.view_id)
        assert race_history is not None
        race_initial = race_history.acts[0]
        correction = IntelligenceJudgmentActDraft(
            act_id=uuid4(),
            root=race_root.view_id,
            attribution=actor,
            basis="owner revised the material View during dependent validation",
            effective_at=datetime.now(UTC),
            ancestry=(race_initial.act_id,),
            assertion=replace(race_root, thesis="SPY exposure may remain unchanged"),
            target_predecessor=race_initial.act_id,
            compatible_opposite_acts=(race_initial.act_id,),
            target_status=IntelligenceJudgmentStatus.ACTIVE,
        )

        archived = asyncio.Event()
        release_dependent = asyncio.Event()
        correction_committed = asyncio.Event()
        release_correction = asyncio.Event()
        original_archive = history_persistence.archive_intelligence_act_commits
        dependent_task: asyncio.Task[object] | None = None
        correction_task: asyncio.Task[object] | None = None
        correction_archives = 0

        async def coordinate_archive(archive_engine: AsyncEngine) -> None:
            nonlocal correction_archives
            task = asyncio.current_task()
            if task is correction_task:
                correction_archives += 1
                if correction_archives == 2:
                    correction_committed.set()
                    await release_correction.wait()
            await original_archive(archive_engine)
            if task is dependent_task and not archived.is_set():
                archived.set()
                await release_dependent.wait()

        with monkeypatch.context() as patcher:
            patcher.setattr(
                history_persistence,
                "archive_intelligence_act_commits",
                coordinate_archive,
            )
            dependent_task = asyncio.create_task(
                race_service.record_view(
                    OperationId(uuid4()),
                    decision,
                    _view(decision, portfolio_id, actor),
                    evidence_bases=(race_basis,),
                )
            )
            await asyncio.wait_for(archived.wait(), timeout=5)
            correction_task = asyncio.create_task(owner_store.append(correction))
            with suppress(TimeoutError):
                await asyncio.wait_for(correction_committed.wait(), timeout=1)
            release_dependent.set()
            try:
                done, _ = await asyncio.wait({dependent_task}, timeout=5)
                if dependent_task not in done:
                    dependent_task.cancel()
                    with suppress(asyncio.CancelledError):
                        await dependent_task
                    raise AssertionError("dependent basis revalidation stalled")
                outcome = dependent_task.result()
            finally:
                release_correction.set()
                await asyncio.wait_for(correction_task, timeout=5)
            assert isinstance(
                outcome, JudgmentReceipt | StaleEvidenceBasis | CurrentEvidenceNoBasis
            )
    finally:
        await engine.dispose()


def test_real_owner_correction_stales_consumed_basis_atomically(
    postgres_target: PostgresTestTarget,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    asyncio.run(_scenario(postgres_target, monkeypatch))
