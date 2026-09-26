from __future__ import annotations

import asyncio
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine

from polaris.application.decisions import (
    ApplyExternalResolutionCommand,
    ApplyHumanDeferralCommand,
    ApplySubstantiveResolutionCommand,
    DecisionCommandEnvelope,
    DecisionHistoryView,
    DecisionInitiationService,
    DecisionMemoryService,
    DecisionMemoryView,
    DecisionMutationResultKind,
    DecisionOrdinaryWorkService,
    EstablishOrReviseDecisionScopeCommand,
    ExpectedDecisionVersion,
    InitiateDecisionCommand,
    InitiationResult,
    InitiationResultKind,
    InvalidTrustedBasis,
    ResumeDecisionWorkCommand,
    WithdrawDecisionWorkCommand,
)
from polaris.application.decisions.lifecycle_correction import (
    DecisionLifecycleCorrectionService,
    RetractUnsupportedDecisionNeedCommand,
)
from polaris.domain.actors import ActorId, KnownActorAttribution
from polaris.domain.decisions import (
    DecisionContinuity,
    DecisionDeferred,
    DecisionExternallyResolved,
    DecisionInitiated,
    DecisionInitiationDetermination,
    DecisionLifecycleCorrected,
    DecisionLifecycleCorrectionBasis,
    DecisionLifecycleDisposition,
    DecisionScope,
    DecisionScopeEstablished,
    DecisionScopeRevised,
    DecisionSubject,
    DecisionSubstantivelyResolved,
    DecisionVersion,
    DecisionWorkControlBasis,
    DecisionWorkPosture,
    DecisionWorkResumed,
    DecisionWorkWithdrawn,
    DeterminateDecisionLifecycleInterpretation,
    ExternalResolutionBasis,
    HumanInvestmentDecisionEffect,
    InvalidDecisionScope,
    InvestmentDecisionId,
    OperationId,
    PortfolioId,
    TechnicalProvenance,
    TechnicalReference,
    TechnicalReferenceKind,
    TriggerKind,
    TriggerProvenance,
    TrustedHumanInvestmentDecisionBasis,
    UnsupportedDecisionNeedBasis,
)
from polaris.infrastructure.persistence.postgresql import (
    PostgresDecisionStore,
    create_postgres_engine,
)

from .conftest import PostgresTestTarget

START = datetime(2026, 9, 19, 6, 0, tzinfo=UTC)
ACTOR = KnownActorAttribution(ActorId(UUID("00000000-0000-4000-8000-000000000101")))
PORTFOLIO_A = PortfolioId(UUID("00000000-0000-4000-8000-000000000102"))
PORTFOLIO_B = PortfolioId(UUID("00000000-0000-4000-8000-000000000103"))


def _uuid(value: int) -> UUID:
    return UUID(f"00000000-0000-4000-8000-{value:012x}")


def _ids(*values: int) -> Iterator[UUID]:
    yield from (_uuid(value) for value in values)


def _technical(reference: str) -> TechnicalProvenance:
    return TechnicalProvenance(
        (
            TechnicalReference(TechnicalReferenceKind.TRACE, f"trace-{reference}"),
            TechnicalReference(TechnicalReferenceKind.REQUEST, reference),
        )
    )


def _envelope(
    *,
    operation: int,
    reference: str,
    effective_at: datetime,
    decision_id: InvestmentDecisionId | None = None,
    version: DecisionVersion | None = None,
) -> DecisionCommandEnvelope:
    expected = (
        frozenset()
        if decision_id is None or version is None
        else frozenset({ExpectedDecisionVersion(decision_id, version)})
    )
    return DecisionCommandEnvelope(
        operation_id=OperationId(_uuid(operation)),
        actor_attribution=ACTOR,
        trigger=TriggerProvenance(TriggerKind.HUMAN_REQUEST, reference),
        effective_at=effective_at,
        technical_provenance=_technical(reference),
        expected_versions=expected,
    )


async def _initiate(
    store: PostgresDecisionStore,
    *,
    scope: DecisionScope,
    recorded_at: datetime,
    ids: tuple[int, int, int],
    operation: int,
    reference: str,
) -> InitiationResult:
    generated = _ids(*ids)
    # duplicate-code: shared setup would couple separate proof layers.
    # arid: disable
    result = await DecisionInitiationService(
        reader=store,
        store=store,
        now=lambda: recorded_at,
        new_uuid=lambda: next(generated),
    ).initiate(
        # arid: enable
        InitiateDecisionCommand(
            envelope=_envelope(
                operation=operation,
                reference=reference,
                effective_at=recorded_at,
            ),
            need_statement="Decide whether to adjust the portfolio",
            subject=DecisionSubject("Portfolio allocation"),
            scope=scope,
        )
    )
    return result


def _ordinary_service(
    store: PostgresDecisionStore,
    *,
    recorded_at: datetime,
    fact_id: int,
) -> DecisionOrdinaryWorkService:
    return DecisionOrdinaryWorkService(
        store=store,
        now=lambda: recorded_at,
        new_uuid=lambda: _uuid(fact_id),
    )


def _store(
    postgres_target: PostgresTestTarget,
) -> tuple[AsyncEngine, PostgresDecisionStore]:
    engine = create_postgres_engine(
        postgres_target.database_url,
        schema=postgres_target.schema,
    )
    return engine, PostgresDecisionStore(engine)


async def _start_decision(
    postgres_target: PostgresTestTarget,
    *,
    scope: DecisionScope,
    ids: tuple[int, int, int],
    operation: int,
    reference: str,
) -> tuple[AsyncEngine, PostgresDecisionStore, InitiationResult]:
    engine, store = _store(postgres_target)
    initiation = await _initiate(
        store,
        scope=scope,
        recorded_at=START,
        ids=ids,
        operation=operation,
        reference=reference,
    )
    return engine, store, initiation


async def _restart_views(
    engine: AsyncEngine,
    postgres_target: PostgresTestTarget,
    known_at: datetime,
    decision_id: InvestmentDecisionId,
) -> tuple[AsyncEngine, DecisionMemoryView, DecisionHistoryView]:
    # duplicate-code: shared restart setup would couple separate proof layers.
    # arid: disable
    await engine.dispose()
    restarted_engine = create_postgres_engine(
        postgres_target.database_url,
        schema=postgres_target.schema,
    )
    # arid: enable
    memory = DecisionMemoryService(
        reader=PostgresDecisionStore(restarted_engine),
        now=lambda: known_at,
    )
    return (
        restarted_engine,
        await memory.current(decision_id),
        await memory.history(decision_id),
    )


async def _current_view(
    store: PostgresDecisionStore,
    known_at: datetime,
    decision_id: InvestmentDecisionId,
) -> DecisionMemoryView:
    return await DecisionMemoryService(
        reader=store,
        now=lambda: known_at,
    ).current(decision_id)


def _assert_disposition(
    current: DecisionMemoryView,
    expected: DecisionLifecycleDisposition,
) -> None:
    assert isinstance(
        current.lifecycle_interpretation,
        DeterminateDecisionLifecycleInterpretation,
    )
    assert current.lifecycle_interpretation.disposition is expected


def test_r2_acceptance_core_lifecycle_survives_restart_through_application_boundary(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        engine, store, initiation = await _start_decision(
            postgres_target,
            scope=DecisionScope.unresolved(PORTFOLIO_A),
            ids=(201, 202, 203),
            operation=204,
            reference="acceptance-initiate",
        )
        decision_id = initiation.decision_id
        assert initiation.kind is InitiationResultKind.CREATED
        assert initiation.need_id is not None
        assert decision_id == InvestmentDecisionId(_uuid(201))
        assert initiation.need_id.value == _uuid(202)
        assert await store.find_unresolved_continuity_candidates(known_at=START) == (
            decision_id,
        )

        established_at = START + timedelta(minutes=10)
        established = await _ordinary_service(
            store,
            recorded_at=established_at,
            fact_id=205,
        ).establish_or_revise_scope(
            EstablishOrReviseDecisionScopeCommand(
                envelope=_envelope(
                    operation=206,
                    reference="acceptance-establish-scope",
                    effective_at=established_at,
                    decision_id=decision_id,
                    version=DecisionVersion(1),
                ),
                decision_id=decision_id,
                scope=DecisionScope.established(PORTFOLIO_A),
                continuity=DecisionContinuity.SAME_COHERENT_CHOICE,
            )
        )
        assert established.version == DecisionVersion(2)

        revised_at = START + timedelta(minutes=20)
        revised = await _ordinary_service(
            store,
            recorded_at=revised_at,
            fact_id=207,
        ).establish_or_revise_scope(
            EstablishOrReviseDecisionScopeCommand(
                envelope=_envelope(
                    operation=208,
                    reference="acceptance-revise-scope",
                    effective_at=revised_at,
                    decision_id=decision_id,
                    version=DecisionVersion(2),
                ),
                decision_id=decision_id,
                scope=DecisionScope.established(PORTFOLIO_A, PORTFOLIO_B),
                continuity=DecisionContinuity.SAME_COHERENT_CHOICE,
            )
        )
        assert revised.version == DecisionVersion(3)

        noop_at = START + timedelta(minutes=30)
        noop = await _ordinary_service(
            store,
            recorded_at=noop_at,
            fact_id=209,
        ).establish_or_revise_scope(
            EstablishOrReviseDecisionScopeCommand(
                envelope=_envelope(
                    operation=210,
                    reference="acceptance-scope-noop",
                    effective_at=noop_at,
                    decision_id=decision_id,
                    version=DecisionVersion(3),
                ),
                decision_id=decision_id,
                scope=DecisionScope.established(PORTFOLIO_B, PORTFOLIO_A),
                continuity=DecisionContinuity.SAME_COHERENT_CHOICE,
            )
        )
        assert noop.kind is DecisionMutationResultKind.NO_OP
        assert noop.version == DecisionVersion(3)
        with pytest.raises(InvalidDecisionScope):
            DecisionScope.established()

        deferral_one_at = START + timedelta(minutes=40)
        deferred_once = await _ordinary_service(
            store,
            recorded_at=deferral_one_at,
            fact_id=211,
        ).apply_human_deferral(
            ApplyHumanDeferralCommand(
                envelope=_envelope(
                    operation=212,
                    reference="acceptance-deferral-1",
                    effective_at=deferral_one_at,
                    decision_id=decision_id,
                    version=DecisionVersion(3),
                ),
                decision_id=decision_id,
                basis=TrustedHumanInvestmentDecisionBasis(
                    "governance-human-decision-deferral-1",
                    HumanInvestmentDecisionEffect.DEFERRING,
                ),
            )
        )
        assert deferred_once.version == DecisionVersion(4)
        deferred_once_current = await _current_view(store, deferral_one_at, decision_id)
        assert deferred_once_current.decision_id == decision_id
        _assert_disposition(
            deferred_once_current,
            DecisionLifecycleDisposition.UNRESOLVED,
        )
        assert deferred_once_current.work_posture is DecisionWorkPosture.DEFERRED

        deferral_two_at = START + timedelta(minutes=50)
        deferred_twice = await _ordinary_service(
            store,
            recorded_at=deferral_two_at,
            fact_id=213,
        ).apply_human_deferral(
            ApplyHumanDeferralCommand(
                envelope=_envelope(
                    operation=214,
                    reference="acceptance-deferral-2",
                    effective_at=deferral_two_at,
                    decision_id=decision_id,
                    version=DecisionVersion(4),
                ),
                decision_id=decision_id,
                basis=TrustedHumanInvestmentDecisionBasis(
                    "governance-human-decision-deferral-2",
                    HumanInvestmentDecisionEffect.DEFERRING,
                ),
            )
        )
        assert deferred_twice.version == DecisionVersion(5)
        deferred_twice_current = await _current_view(
            store, deferral_two_at, decision_id
        )
        assert deferred_twice_current.decision_id == decision_id
        _assert_disposition(
            deferred_twice_current,
            DecisionLifecycleDisposition.UNRESOLVED,
        )
        assert deferred_twice_current.work_posture is DecisionWorkPosture.DEFERRED

        resumed_after_deferral_at = START + timedelta(minutes=60)
        resumed_after_deferral = await _ordinary_service(
            store,
            recorded_at=resumed_after_deferral_at,
            fact_id=215,
        ).resume_work(
            ResumeDecisionWorkCommand(
                envelope=_envelope(
                    operation=216,
                    reference="acceptance-resume-after-deferral",
                    effective_at=resumed_after_deferral_at,
                    decision_id=decision_id,
                    version=DecisionVersion(5),
                ),
                decision_id=decision_id,
                basis=DecisionWorkControlBasis("resume-after-deferral"),
                continuity=DecisionContinuity.SAME_COHERENT_CHOICE,
            )
        )
        assert resumed_after_deferral.version == DecisionVersion(6)
        resumed_after_deferral_current = await _current_view(
            store, resumed_after_deferral_at, decision_id
        )
        _assert_disposition(
            resumed_after_deferral_current,
            DecisionLifecycleDisposition.UNRESOLVED,
        )
        assert resumed_after_deferral_current.work_posture is DecisionWorkPosture.ACTIVE

        withdrawn_at = START + timedelta(minutes=70)
        withdrawn = await _ordinary_service(
            store,
            recorded_at=withdrawn_at,
            fact_id=217,
        ).withdraw_work(
            WithdrawDecisionWorkCommand(
                envelope=_envelope(
                    operation=218,
                    reference="acceptance-withdraw",
                    effective_at=withdrawn_at,
                    decision_id=decision_id,
                    version=DecisionVersion(6),
                ),
                decision_id=decision_id,
                basis=DecisionWorkControlBasis("operator-withdrawal"),
            )
        )
        assert withdrawn.version == DecisionVersion(7)
        withdrawn_current = await _current_view(store, withdrawn_at, decision_id)
        _assert_disposition(
            withdrawn_current,
            DecisionLifecycleDisposition.UNRESOLVED,
        )
        assert withdrawn_current.work_posture is DecisionWorkPosture.WITHDRAWN

        resumed_at = START + timedelta(minutes=80)
        resumed = await _ordinary_service(
            store,
            recorded_at=resumed_at,
            fact_id=219,
        ).resume_work(
            ResumeDecisionWorkCommand(
                envelope=_envelope(
                    operation=220,
                    reference="acceptance-resume",
                    effective_at=resumed_at,
                    decision_id=decision_id,
                    version=DecisionVersion(7),
                ),
                decision_id=decision_id,
                basis=DecisionWorkControlBasis("operator-resumption"),
                continuity=DecisionContinuity.SAME_COHERENT_CHOICE,
            )
        )
        assert resumed.version == DecisionVersion(8)
        resumed_current = await _current_view(store, resumed_at, decision_id)
        _assert_disposition(
            resumed_current,
            DecisionLifecycleDisposition.UNRESOLVED,
        )
        assert resumed_current.work_posture is DecisionWorkPosture.ACTIVE

        resolved_at = START + timedelta(minutes=90)
        resolved = await _ordinary_service(
            store,
            recorded_at=resolved_at,
            fact_id=221,
        ).apply_external_resolution(
            ApplyExternalResolutionCommand(
                envelope=_envelope(
                    operation=222,
                    reference="acceptance-external-resolution",
                    effective_at=resolved_at,
                    decision_id=decision_id,
                    version=DecisionVersion(8),
                ),
                decision_id=decision_id,
                basis=ExternalResolutionBasis("need-eliminated-by-external-fact"),
            )
        )
        assert resolved.version == DecisionVersion(9)

        restarted_engine, current, history = await _restart_views(
            engine, postgres_target, resolved_at, decision_id
        )
        try:
            assert current.decision_id == decision_id
            assert current.need.need_id == initiation.need_id
            assert current.subject == DecisionSubject("Portfolio allocation")
            assert current.scope == DecisionScope.established(
                PORTFOLIO_B,
                PORTFOLIO_A,
            )
            assert current.version == DecisionVersion(9)
            assert current.work_posture is None
            _assert_disposition(
                current,
                DecisionLifecycleDisposition.EXTERNALLY_RESOLVED,
            )
            expected_history = [
                (DecisionInitiated, START, "acceptance-initiate"),
                (
                    DecisionScopeEstablished,
                    established_at,
                    "acceptance-establish-scope",
                ),
                (DecisionScopeRevised, revised_at, "acceptance-revise-scope"),
                (DecisionDeferred, deferral_one_at, "acceptance-deferral-1"),
                (DecisionDeferred, deferral_two_at, "acceptance-deferral-2"),
                (
                    DecisionWorkResumed,
                    resumed_after_deferral_at,
                    "acceptance-resume-after-deferral",
                ),
                (DecisionWorkWithdrawn, withdrawn_at, "acceptance-withdraw"),
                (DecisionWorkResumed, resumed_at, "acceptance-resume"),
                (
                    DecisionExternallyResolved,
                    resolved_at,
                    "acceptance-external-resolution",
                ),
            ]
            assert [type(fact) for fact in history.lifecycle_facts] == [
                fact_type for fact_type, _, _ in expected_history
            ]
            initiation_fact = history.lifecycle_facts[0]
            assert isinstance(initiation_fact, DecisionInitiated)
            assert initiation_fact.need.need_id == initiation.need_id
            assert initiation_fact.subject == DecisionSubject("Portfolio allocation")
            assert initiation_fact.continuity.determination is (
                DecisionInitiationDetermination.NO_CANDIDATES
            )
            assert initiation_fact.continuity.candidate_decision_ids == frozenset()
            assert initiation_fact.continuity.known_at == START

            deferred_facts = [
                fact
                for fact in history.lifecycle_facts
                if isinstance(fact, DecisionDeferred)
            ]
            assert [fact.basis for fact in deferred_facts] == [
                TrustedHumanInvestmentDecisionBasis(
                    "governance-human-decision-deferral-1",
                    HumanInvestmentDecisionEffect.DEFERRING,
                ),
                TrustedHumanInvestmentDecisionBasis(
                    "governance-human-decision-deferral-2",
                    HumanInvestmentDecisionEffect.DEFERRING,
                ),
            ]
            assert (
                deferred_facts[0].metadata.fact_id != deferred_facts[1].metadata.fact_id
            )
            external_resolution = history.lifecycle_facts[-1]
            assert isinstance(external_resolution, DecisionExternallyResolved)
            assert external_resolution.basis == ExternalResolutionBasis(
                "need-eliminated-by-external-fact"
            )

            sequences = [
                fact.metadata.sequence.value for fact in history.lifecycle_facts
            ]
            assert sequences == list(range(1, 10))
            versions = [
                fact.metadata.decision_version.value for fact in history.lifecycle_facts
            ]
            assert versions == list(range(1, 10))
            for fact, (_, expected_at, expected_reference) in zip(
                history.lifecycle_facts,
                expected_history,
                strict=True,
            ):
                assert fact.metadata.actor_attribution == ACTOR
                assert fact.metadata.trigger == TriggerProvenance(
                    TriggerKind.HUMAN_REQUEST,
                    expected_reference,
                )
                assert fact.metadata.technical_provenance == _technical(
                    expected_reference
                )
                assert fact.metadata.effective_at == expected_at
                assert fact.metadata.recorded_at == expected_at
                assert not hasattr(fact.metadata, "lock_id")
                assert not hasattr(fact.metadata, "continuity_token")
                assert not hasattr(fact.metadata, "row_version")
        finally:
            await restarted_engine.dispose()

    asyncio.run(scenario())


def test_r2_acceptance_trusted_human_resolution_requires_canonical_basis(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        engine, store, initiation = await _start_decision(
            postgres_target,
            scope=DecisionScope.unresolved(),
            ids=(301, 302, 303),
            operation=304,
            reference="acceptance-human-resolution-initiate",
        )
        decision_id = initiation.decision_id
        human_resolved_at = START + timedelta(minutes=10)
        resolving_basis = TrustedHumanInvestmentDecisionBasis(
            "governance-human-decision-hold-no-action",
            HumanInvestmentDecisionEffect.SUBSTANTIVELY_RESOLVING,
        )
        resolved = await _ordinary_service(
            store,
            recorded_at=human_resolved_at,
            fact_id=305,
        ).apply_substantive_resolution(
            ApplySubstantiveResolutionCommand(
                envelope=_envelope(
                    operation=306,
                    reference="acceptance-human-resolution",
                    effective_at=human_resolved_at,
                    decision_id=decision_id,
                    version=DecisionVersion(1),
                ),
                decision_id=decision_id,
                basis=resolving_basis,
            )
        )
        assert resolved.version == DecisionVersion(2)
        restarted_engine, current, history = await _restart_views(
            engine, postgres_target, human_resolved_at, decision_id
        )
        try:
            assert current.decision_id == decision_id
            _assert_disposition(
                current,
                DecisionLifecycleDisposition.SUBSTANTIVELY_RESOLVED,
            )
            assert isinstance(
                history.lifecycle_facts[-1],
                DecisionSubstantivelyResolved,
            )
            assert history.lifecycle_facts[-1].basis == resolving_basis
        finally:
            await restarted_engine.dispose()

    asyncio.run(scenario())

    decision_id = InvestmentDecisionId(_uuid(307))
    command_envelope = _envelope(
        operation=308,
        reference="acceptance-reject-noncanonical-basis",
        effective_at=START,
        decision_id=decision_id,
        version=DecisionVersion(1),
    )
    invalid_bases = (
        TrustedHumanInvestmentDecisionBasis(
            "governance-human-decision-deferral-only",
            HumanInvestmentDecisionEffect.DEFERRING,
        ),
        cast(
            TrustedHumanInvestmentDecisionBasis,
            ExternalResolutionBasis("advisory-or-unauthorized-substitute"),
        ),
    )
    for basis in invalid_bases:
        with pytest.raises(InvalidTrustedBasis):
            ApplySubstantiveResolutionCommand(
                envelope=command_envelope,
                decision_id=decision_id,
                basis=basis,
            )


def test_r2_acceptance_unsupported_need_correction_preserves_prior_work_after_restart(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        engine, store, initiation = await _start_decision(
            postgres_target,
            scope=DecisionScope.unresolved(PORTFOLIO_A),
            ids=(401, 402, 403),
            operation=404,
            reference="acceptance-unsupported-initiate",
        )
        decision_id = initiation.decision_id

        withdrawn_at = START + timedelta(minutes=10)
        withdrawn = await _ordinary_service(
            store,
            recorded_at=withdrawn_at,
            fact_id=405,
        ).withdraw_work(
            WithdrawDecisionWorkCommand(
                envelope=_envelope(
                    operation=406,
                    reference="acceptance-unsupported-prior-work",
                    effective_at=withdrawn_at,
                    decision_id=decision_id,
                    version=DecisionVersion(1),
                ),
                decision_id=decision_id,
                basis=DecisionWorkControlBasis("pause-before-support-review"),
            )
        )
        assert withdrawn.version == DecisionVersion(2)

        corrected_at = START + timedelta(minutes=20)
        corrected = await DecisionLifecycleCorrectionService(
            store=store,
            now=lambda: corrected_at,
            new_uuid=lambda: _uuid(407),
        ).retract_unsupported_decision_need(
            RetractUnsupportedDecisionNeedCommand(
                envelope=_envelope(
                    operation=408,
                    reference="acceptance-unsupported-correction",
                    effective_at=corrected_at,
                    decision_id=decision_id,
                    version=DecisionVersion(2),
                ),
                decision_id=decision_id,
                correction_basis=DecisionLifecycleCorrectionBasis(
                    "support-review-correction"
                ),
                unsupported_need_basis=UnsupportedDecisionNeedBasis(
                    "original-need-was-unsupported"
                ),
            )
        )
        assert corrected.version == DecisionVersion(3)
        restarted_engine, current, history = await _restart_views(
            engine, postgres_target, corrected_at, decision_id
        )
        try:
            assert current.decision_id == decision_id
            assert current.need.need_id.value == _uuid(402)
            assert current.version == DecisionVersion(3)
            assert current.work_posture is None
            _assert_disposition(
                current,
                DecisionLifecycleDisposition.NEED_RETRACTED_UNSUPPORTED,
            )
            assert len(history.lifecycle_facts) == 3
            assert isinstance(history.lifecycle_facts[1], DecisionWorkWithdrawn)
            assert isinstance(history.lifecycle_facts[2], DecisionLifecycleCorrected)
            assert history.lifecycle_facts[2].replacement_disposition is (
                DecisionLifecycleDisposition.NEED_RETRACTED_UNSUPPORTED
            )
            assert history.lifecycle_facts[2].replacement_basis == (
                UnsupportedDecisionNeedBasis("original-need-was-unsupported")
            )
        finally:
            await restarted_engine.dispose()

    asyncio.run(scenario())
