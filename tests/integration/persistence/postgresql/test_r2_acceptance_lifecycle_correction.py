from __future__ import annotations

import asyncio
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import UUID

from polaris.application.decisions import (
    ApplySubstantiveResolutionCommand,
    DecisionCommandEnvelope,
    DecisionInitiationService,
    DecisionMemoryService,
    DecisionOrdinaryWorkService,
    ExpectedDecisionVersion,
    InitiateDecisionCommand,
    InitiationResult,
)
from polaris.application.decisions.lifecycle_correction import (
    DecisionLifecycleCorrectionService,
    RecordDecisionLifecycleCorrectionCommand,
)
from polaris.domain.actors import ActorId, KnownActorAttribution
from polaris.domain.decisions import (
    ContestedDecisionLifecycleInterpretation,
    DecisionLifecycleCorrected,
    DecisionLifecycleCorrectionBasis,
    DecisionLifecycleCorrectionEffect,
    DecisionLifecycleDisposition,
    DecisionLifecycleFactId,
    DecisionScope,
    DecisionSubject,
    DecisionVersion,
    DeterminateDecisionLifecycleInterpretation,
    ExternalResolutionBasis,
    HumanInvestmentDecisionEffect,
    InvestmentDecisionId,
    OperationId,
    TechnicalProvenance,
    TechnicalReference,
    TechnicalReferenceKind,
    TriggerKind,
    TriggerProvenance,
    TrustedHumanInvestmentDecisionBasis,
)
from polaris.infrastructure.persistence.postgresql import PostgresDecisionStore

from .conftest import PostgresTestTarget, postgres_engine_store

START = datetime(2026, 9, 24, 8, 0, tzinfo=UTC)
RESOLUTION_AT = START + timedelta(minutes=10)
EARLIER_KNOWN_AT = START + timedelta(minutes=20)
LATE_EXTERNAL_RECORDED_AT = START + timedelta(minutes=30)
FUTURE_RECORDED_AT = START + timedelta(minutes=40)
BEFORE_FUTURE_EFFECTIVE = START + timedelta(minutes=45)
CONTEST_RECORDED_AT = START + timedelta(minutes=50)
LATE_EXTERNAL_EFFECTIVE_AT = START + timedelta(minutes=5)
FUTURE_EFFECTIVE_AT = START + timedelta(minutes=90)

ACTOR = KnownActorAttribution(ActorId(UUID("00000000-0000-4000-8000-000000000b01")))


# duplicate-code: this acceptance proof owns its deterministic temporal fixture;
# sharing it with other ticket proofs would couple independently diagnostic scenarios.
# arid: disable
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
    trigger_kind: TriggerKind = TriggerKind.HUMAN_REQUEST,
) -> DecisionCommandEnvelope:
    expected = (
        frozenset()
        if decision_id is None or version is None
        else frozenset({ExpectedDecisionVersion(decision_id, version)})
    )
    return DecisionCommandEnvelope(
        operation_id=OperationId(_uuid(operation)),
        actor_attribution=ACTOR,
        trigger=TriggerProvenance(trigger_kind, reference),
        effective_at=effective_at,
        technical_provenance=_technical(reference),
        expected_versions=expected,
    )


async def _initiate(store: PostgresDecisionStore) -> InitiationResult:
    generated = _ids(0xB02, 0xB03, 0xB04)
    return await DecisionInitiationService(
        reader=store,
        store=store,
        now=lambda: START,
        new_uuid=lambda: next(generated),
    ).initiate(
        InitiateDecisionCommand(
            envelope=_envelope(
                operation=0xB05,
                reference="acceptance-bitemporal-initiate",
                effective_at=START,
            ),
            need_statement="Decide whether to rebalance the portfolio",
            subject=DecisionSubject("Portfolio allocation"),
            scope=DecisionScope.unresolved(),
        )
    )


def _correction(
    *,
    decision_id: InvestmentDecisionId,
    resolution_fact_id: DecisionLifecycleFactId,
    version: DecisionVersion,
    operation: int,
    reference: str,
    effective_at: datetime,
    disposition: DecisionLifecycleDisposition,
    basis: ExternalResolutionBasis | TrustedHumanInvestmentDecisionBasis,
) -> RecordDecisionLifecycleCorrectionCommand:
    return RecordDecisionLifecycleCorrectionCommand(
        envelope=_envelope(
            operation=operation,
            reference=reference,
            effective_at=effective_at,
            decision_id=decision_id,
            version=version,
            trigger_kind=TriggerKind.EXTERNAL_OBSERVATION,
        ),
        decision_id=decision_id,
        target_fact_id=resolution_fact_id,
        effect=DecisionLifecycleCorrectionEffect.QUALIFY,
        correction_basis=DecisionLifecycleCorrectionBasis(reference),
        replacement_disposition=disposition,
        replacement_basis=basis,
    )


# arid: enable


def test_r2_acceptance_bitemporal_lifecycle_correction_survives_restart(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        async with postgres_engine_store(postgres_target) as (_, store):
            initiation = await _initiate(store)
            decision_id = initiation.decision_id
            resolution_fact_id = DecisionLifecycleFactId(_uuid(0xB06))

            resolved = await DecisionOrdinaryWorkService(
                store=store,
                now=lambda: RESOLUTION_AT,
                new_uuid=lambda: _uuid(0xB06),
            ).apply_substantive_resolution(
                ApplySubstantiveResolutionCommand(
                    _envelope(
                        operation=0xB07,
                        reference="acceptance-substantive-resolution",
                        effective_at=RESOLUTION_AT,
                        decision_id=decision_id,
                        version=DecisionVersion(1),
                    ),
                    decision_id,
                    TrustedHumanInvestmentDecisionBasis(
                        "acceptance-substantive-resolution",
                        HumanInvestmentDecisionEffect.SUBSTANTIVELY_RESOLVING,
                    ),
                )
            )
            assert resolved.version == DecisionVersion(2)

            base_memory = DecisionMemoryService(
                reader=store,
                now=lambda: RESOLUTION_AT,
            )
            original_history = (await base_memory.history(decision_id)).lifecycle_facts
            assert len(original_history) == 2

            late_external_command = _correction(
                decision_id=decision_id,
                resolution_fact_id=resolution_fact_id,
                version=resolved.version,
                operation=0xB08,
                reference="late-earlier-external-resolution",
                effective_at=LATE_EXTERNAL_EFFECTIVE_AT,
                disposition=DecisionLifecycleDisposition.EXTERNALLY_RESOLVED,
                basis=ExternalResolutionBasis("circumstances-ended-need-earlier"),
            )
            late_external = await DecisionLifecycleCorrectionService(
                store=store,
                now=lambda: LATE_EXTERNAL_RECORDED_AT,
                new_uuid=lambda: _uuid(0xB09),
            ).record_lifecycle_correction(late_external_command)
            assert late_external.version == DecisionVersion(3)

            after_late_memory = DecisionMemoryService(
                reader=store,
                now=lambda: LATE_EXTERNAL_RECORDED_AT,
            )
            earlier_known = await after_late_memory.as_known_at(
                decision_id,
                EARLIER_KNOWN_AT,
            )
            assert isinstance(
                earlier_known.lifecycle_interpretation,
                DeterminateDecisionLifecycleInterpretation,
            )
            assert earlier_known.lifecycle_interpretation.disposition is (
                DecisionLifecycleDisposition.SUBSTANTIVELY_RESOLVED
            )
            assert earlier_known.lifecycle_interpretation.support_fact_ids == frozenset(
                {resolution_fact_id}
            )

            current_after_late = await after_late_memory.current(decision_id)
            assert isinstance(
                current_after_late.lifecycle_interpretation,
                DeterminateDecisionLifecycleInterpretation,
            )
            assert current_after_late.lifecycle_interpretation.disposition is (
                DecisionLifecycleDisposition.EXTERNALLY_RESOLVED
            )
            assert current_after_late.lifecycle_interpretation.support_fact_ids == (
                frozenset({DecisionLifecycleFactId(_uuid(0xB09))})
            )

            future_command = _correction(
                decision_id=decision_id,
                resolution_fact_id=resolution_fact_id,
                version=late_external.version,
                operation=0xB0A,
                reference="known-future-substantive-support",
                effective_at=FUTURE_EFFECTIVE_AT,
                disposition=DecisionLifecycleDisposition.SUBSTANTIVELY_RESOLVED,
                basis=TrustedHumanInvestmentDecisionBasis(
                    "known-future-substantive-support",
                    HumanInvestmentDecisionEffect.SUBSTANTIVELY_RESOLVING,
                ),
            )
            future = await DecisionLifecycleCorrectionService(
                store=store,
                now=lambda: FUTURE_RECORDED_AT,
                new_uuid=lambda: _uuid(0xB0B),
            ).record_lifecycle_correction(future_command)
            assert future.version == late_external.version

            temporal_memory = DecisionMemoryService(
                reader=store,
                now=lambda: BEFORE_FUTURE_EFFECTIVE,
            )
            as_known = await temporal_memory.as_known_at(
                decision_id,
                BEFORE_FUTURE_EFFECTIVE,
            )
            same_boundary = await temporal_memory.effective_at(
                decision_id,
                BEFORE_FUTURE_EFFECTIVE,
                known_at=BEFORE_FUTURE_EFFECTIVE,
            )
            assert as_known == same_boundary
            assert isinstance(
                as_known.lifecycle_interpretation,
                DeterminateDecisionLifecycleInterpretation,
            )
            assert as_known.lifecycle_interpretation.disposition is (
                DecisionLifecycleDisposition.EXTERNALLY_RESOLVED
            )
            assert DecisionLifecycleFactId(_uuid(0xB0B)) not in (
                as_known.lifecycle_interpretation.support_fact_ids
            )

            future_boundary = await temporal_memory.effective_at(
                decision_id,
                FUTURE_EFFECTIVE_AT,
                known_at=BEFORE_FUTURE_EFFECTIVE,
            )
            assert isinstance(
                future_boundary.lifecycle_interpretation,
                ContestedDecisionLifecycleInterpretation,
            )
            assert future_boundary.lifecycle_interpretation.effective_at == (
                FUTURE_EFFECTIVE_AT
            )
            assert future_boundary.lifecycle_interpretation.known_at == (
                BEFORE_FUTURE_EFFECTIVE
            )
            assert future_boundary.lifecycle_interpretation.support_fact_ids == (
                frozenset(
                    {
                        DecisionLifecycleFactId(_uuid(0xB09)),
                        DecisionLifecycleFactId(_uuid(0xB0B)),
                    }
                )
            )

            contest_command = _correction(
                decision_id=decision_id,
                resolution_fact_id=resolution_fact_id,
                version=future.version,
                operation=0xB0C,
                reference="independent-current-substantive-support",
                effective_at=RESOLUTION_AT,
                disposition=DecisionLifecycleDisposition.SUBSTANTIVELY_RESOLVED,
                basis=TrustedHumanInvestmentDecisionBasis(
                    "independent-current-substantive-support",
                    HumanInvestmentDecisionEffect.SUBSTANTIVELY_RESOLVING,
                ),
            )
            contested = await DecisionLifecycleCorrectionService(
                store=store,
                now=lambda: CONTEST_RECORDED_AT,
                new_uuid=lambda: _uuid(0xB0D),
            ).record_lifecycle_correction(contest_command)
            assert contested.version == DecisionVersion(4)

            contested_memory = DecisionMemoryService(
                reader=store,
                now=lambda: CONTEST_RECORDED_AT,
            )
            current_contested = await contested_memory.current(decision_id)
            assert isinstance(
                current_contested.lifecycle_interpretation,
                ContestedDecisionLifecycleInterpretation,
            )
            assert current_contested.lifecycle_interpretation.effective_at == (
                CONTEST_RECORDED_AT
            )
            assert current_contested.lifecycle_interpretation.known_at == (
                CONTEST_RECORDED_AT
            )
            assert current_contested.lifecycle_interpretation.support_fact_ids == (
                frozenset(
                    {
                        DecisionLifecycleFactId(_uuid(0xB09)),
                        DecisionLifecycleFactId(_uuid(0xB0D)),
                    }
                )
            )

            history = await contested_memory.history(decision_id)
            assert history.lifecycle_facts[:2] == original_history
            assert len(history.lifecycle_facts) == 5

            late_fact = history.lifecycle_facts[2]
            future_fact = history.lifecycle_facts[3]
            contest_fact = history.lifecycle_facts[4]
            assert isinstance(late_fact, DecisionLifecycleCorrected)
            assert isinstance(future_fact, DecisionLifecycleCorrected)
            assert isinstance(contest_fact, DecisionLifecycleCorrected)

            assert late_fact.metadata.actor_attribution == ACTOR
            assert late_fact.metadata.trigger == late_external_command.envelope.trigger
            assert (
                late_fact.metadata.technical_provenance
                == late_external_command.envelope.technical_provenance
            )
            assert late_fact.metadata.effective_at == LATE_EXTERNAL_EFFECTIVE_AT
            assert late_fact.metadata.recorded_at == LATE_EXTERNAL_RECORDED_AT
            assert future_fact.metadata.effective_at == FUTURE_EFFECTIVE_AT
            assert future_fact.metadata.recorded_at == FUTURE_RECORDED_AT
            assert contest_fact.metadata.recorded_at == CONTEST_RECORDED_AT
            assert [
                fact.metadata.recorded_at for fact in history.lifecycle_facts
            ] == sorted(fact.metadata.recorded_at for fact in history.lifecycle_facts)

        async with postgres_engine_store(postgres_target) as (_, restarted_store):
            restarted_memory = DecisionMemoryService(
                reader=restarted_store,
                now=lambda: CONTEST_RECORDED_AT,
            )

            restarted_earlier = await restarted_memory.as_known_at(
                decision_id,
                EARLIER_KNOWN_AT,
            )
            restarted_before_future = await restarted_memory.as_known_at(
                decision_id,
                BEFORE_FUTURE_EFFECTIVE,
            )
            restarted_current = await restarted_memory.current(decision_id)
            restarted_history = await restarted_memory.history(decision_id)

            assert restarted_earlier == earlier_known
            assert restarted_before_future == as_known
            assert restarted_current == current_contested
            assert restarted_history == history

    asyncio.run(scenario())
