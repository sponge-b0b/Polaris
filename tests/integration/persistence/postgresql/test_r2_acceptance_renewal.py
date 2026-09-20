from __future__ import annotations

import asyncio
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine

from polaris.application.decisions import (
    ApplyExternalResolutionCommand,
    ApplySubstantiveResolutionCommand,
    DecisionCommandEnvelope,
    DecisionInitiationService,
    DecisionLineageDirection,
    DecisionMemoryService,
    DecisionMemoryView,
    DecisionOrdinaryWorkService,
    DecisionRelationshipService,
    ExpectedDecisionVersion,
    InitiateDecisionCommand,
    RenewalPredecessor,
    RenewDecisionCommand,
)
from polaris.domain.actors import ActorId, KnownActorAttribution
from polaris.domain.decisions import (
    DecisionInitiated,
    DecisionLifecycleDisposition,
    DecisionNeedId,
    DecisionRelationshipBasisRole,
    DecisionRelationshipFact,
    DecisionRelationshipFactId,
    DecisionRelationshipState,
    DecisionRelationshipType,
    DecisionScope,
    DecisionSubject,
    DecisionVersion,
    DecisionWorkPosture,
    DeterminateDecisionLifecycleInterpretation,
    ExternalResolutionBasis,
    HumanInvestmentDecisionEffect,
    InvestmentDecisionId,
    OperationId,
    RenewedFromRelationshipBasis,
    TechnicalProvenance,
    TechnicalReference,
    TechnicalReferenceKind,
    TriggerKind,
    TriggerProvenance,
    TrustedHumanInvestmentDecisionBasis,
)
from polaris.infrastructure.persistence.postgresql import (
    PostgresDecisionStore,
    create_postgres_engine,
)

from .conftest import PostgresTestTarget

START = datetime(2026, 9, 20, 6, 0, tzinfo=UTC)
ACTOR = KnownActorAttribution(ActorId(UUID("00000000-0000-4000-8000-000000000701")))


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


def _store(
    postgres_target: PostgresTestTarget,
) -> tuple[AsyncEngine, PostgresDecisionStore]:
    engine = create_postgres_engine(
        postgres_target.database_url,
        schema=postgres_target.schema,
    )
    return engine, PostgresDecisionStore(engine)


async def _initiate_predecessor(
    store: PostgresDecisionStore,
    *,
    identity_base: int,
) -> tuple[InvestmentDecisionId, DecisionNeedId]:
    generated = _ids(identity_base + 1, identity_base + 2, identity_base + 3)
    result = await DecisionInitiationService(
        reader=store,
        store=store,
        now=lambda: START,
        new_uuid=lambda: next(generated),
    ).initiate(
        InitiateDecisionCommand(
            envelope=_envelope(
                operation=identity_base + 4,
                reference="acceptance-renewal-predecessor-initiate",
                effective_at=START,
            ),
            need_statement="Decide whether to adjust portfolio exposure",
            subject=DecisionSubject("Portfolio exposure"),
            scope=DecisionScope.unresolved(),
        )
    )
    assert result.need_id is not None
    return result.decision_id, result.need_id


async def _resolve_predecessor(
    store: PostgresDecisionStore,
    *,
    decision_id: InvestmentDecisionId,
    identity_base: int,
    resolution_kind: str,
) -> tuple[DecisionVersion, DecisionLifecycleDisposition]:
    resolved_at = START + timedelta(minutes=10)
    service = DecisionOrdinaryWorkService(
        store=store,
        now=lambda: resolved_at,
        new_uuid=lambda: _uuid(identity_base + 5),
    )
    envelope = _envelope(
        operation=identity_base + 6,
        reference=f"acceptance-renewal-{resolution_kind}-resolution",
        effective_at=resolved_at,
        decision_id=decision_id,
        version=DecisionVersion(1),
    )
    if resolution_kind == "substantive":
        result = await service.apply_substantive_resolution(
            ApplySubstantiveResolutionCommand(
                envelope=envelope,
                decision_id=decision_id,
                basis=TrustedHumanInvestmentDecisionBasis(
                    "governance-human-decision-renewal-predecessor",
                    HumanInvestmentDecisionEffect.SUBSTANTIVELY_RESOLVING,
                ),
            )
        )
        return result.version, DecisionLifecycleDisposition.SUBSTANTIVELY_RESOLVED
    assert resolution_kind == "external"
    result = await service.apply_external_resolution(
        ApplyExternalResolutionCommand(
            envelope=envelope,
            decision_id=decision_id,
            basis=ExternalResolutionBasis(
                "external-fact-eliminated-the-predecessor-need"
            ),
        )
    )
    return result.version, DecisionLifecycleDisposition.EXTERNALLY_RESOLVED


def _assert_disposition(
    current: DecisionMemoryView,
    expected: DecisionLifecycleDisposition,
) -> None:
    assert isinstance(
        current.lifecycle_interpretation,
        DeterminateDecisionLifecycleInterpretation,
    )
    assert current.lifecycle_interpretation.disposition is expected


def _assert_no_database_mechanics(metadata: object) -> None:
    for database_mechanic in (
        "lock_id",
        "advisory_lock_key",
        "continuity_token",
        "row_version",
        "generation_token",
    ):
        assert not hasattr(metadata, database_mechanic)


@pytest.mark.parametrize(
    ("resolution_kind", "identity_base"),
    (("substantive", 710), ("external", 730)),
)
def test_r2_acceptance_renewal_lineage_survives_restart_through_decision_memory(
    postgres_target: PostgresTestTarget,
    resolution_kind: str,
    identity_base: int,
) -> None:
    async def scenario() -> None:
        engine, store = _store(postgres_target)
        predecessor_id, predecessor_need_id = await _initiate_predecessor(
            store,
            identity_base=identity_base,
        )
        predecessor_version, expected_disposition = await _resolve_predecessor(
            store,
            decision_id=predecessor_id,
            identity_base=identity_base,
            resolution_kind=resolution_kind,
        )
        resolved_at = START + timedelta(minutes=10)
        before_memory = DecisionMemoryService(reader=store, now=lambda: resolved_at)
        predecessor_before = await before_memory.current(predecessor_id)
        predecessor_history_before = await before_memory.history(predecessor_id)
        _assert_disposition(predecessor_before, expected_disposition)
        assert predecessor_before.work_posture is None
        assert predecessor_history_before.relationship_facts == ()

        renewal_at = START + timedelta(minutes=20)
        relationship_fact_id = DecisionRelationshipFactId(_uuid(identity_base + 10))
        renewal_basis = RenewedFromRelationshipBasis(
            (f"renewal-basis-{resolution_kind}",)
        )
        renewal_envelope = _envelope(
            operation=identity_base + 11,
            reference=f"acceptance-renewal-{resolution_kind}",
            effective_at=renewal_at,
            decision_id=predecessor_id,
            version=predecessor_version,
        )
        generated = _ids(
            identity_base + 7,
            identity_base + 8,
            identity_base + 9,
            identity_base + 10,
        )
        renewal = await DecisionRelationshipService(
            reader=store,
            store=store,
            now=lambda: renewal_at,
            new_uuid=lambda: next(generated),
        ).renew(
            RenewDecisionCommand(
                envelope=renewal_envelope,
                need_statement="Revisit portfolio exposure after renewed judgment",
                subject=DecisionSubject("Portfolio exposure"),
                scope=DecisionScope.unresolved(),
                predecessors=(RenewalPredecessor(predecessor_id, renewal_basis),),
            )
        )
        assert renewal.new_decision_id == InvestmentDecisionId(_uuid(identity_base + 7))
        assert renewal.need_id is not None
        assert renewal.need_id.value == _uuid(identity_base + 8)
        assert renewal.need_id != predecessor_need_id
        assert renewal.relationship_fact_ids == (relationship_fact_id,)

        await engine.dispose()
        restarted_engine = create_postgres_engine(
            postgres_target.database_url,
            schema=postgres_target.schema,
        )
        restarted_store = PostgresDecisionStore(restarted_engine)
        memory = DecisionMemoryService(
            reader=restarted_store,
            now=lambda: renewal_at,
        )
        try:
            source = await memory.current(renewal.new_decision_id)
            predecessor = await memory.current(predecessor_id)
            source_history = await memory.history(renewal.new_decision_id)
            predecessor_history = await memory.history(predecessor_id)
            outgoing = await memory.lineage(
                renewal.new_decision_id,
                known_at=renewal_at,
            )
            incoming = await memory.lineage(
                predecessor_id,
                known_at=renewal_at,
            )

            assert source.decision_id == renewal.new_decision_id
            assert source.need.need_id == renewal.need_id
            assert source.need.need_id != predecessor.need.need_id
            _assert_disposition(source, DecisionLifecycleDisposition.UNRESOLVED)
            assert source.work_posture is DecisionWorkPosture.ACTIVE

            assert predecessor.decision_id == predecessor_before.decision_id
            assert predecessor.need == predecessor_before.need
            assert predecessor.subject == predecessor_before.subject
            assert predecessor.scope == predecessor_before.scope
            assert predecessor.work_posture is None
            _assert_disposition(predecessor, expected_disposition)
            assert (
                predecessor_history.lifecycle_facts
                == predecessor_history_before.lifecycle_facts
            )

            assert len(source_history.lifecycle_facts) == 1
            initiated = source_history.lifecycle_facts[0]
            assert isinstance(initiated, DecisionInitiated)
            assert initiated.need.need_id == renewal.need_id
            assert initiated.metadata.actor_attribution == ACTOR
            assert initiated.metadata.trigger == renewal_envelope.trigger
            assert (
                initiated.metadata.technical_provenance
                == renewal_envelope.technical_provenance
            )

            assert len(outgoing) == 1
            assert len(incoming) == 1
            lineage = outgoing[0]
            assert incoming[0].source_decision_id == lineage.source_decision_id
            assert incoming[0].target_decision_id == lineage.target_decision_id
            assert incoming[0].direction is DecisionLineageDirection.INCOMING
            assert lineage.direction is DecisionLineageDirection.OUTGOING
            assert lineage.source_decision_id == renewal.new_decision_id
            assert lineage.target_decision_id == predecessor_id
            assert lineage.relationship_type is DecisionRelationshipType.RENEWED_FROM
            assert lineage.state is DecisionRelationshipState.SUPPORTED
            assert lineage.effective_at == renewal_at
            assert lineage.known_at == renewal_at
            assert lineage.support_fact_ids == frozenset({relationship_fact_id})
            assert {
                (
                    contribution.relationship_fact_id,
                    contribution.role,
                    contribution.basis,
                )
                for contribution in lineage.basis_contributions
            } == {
                (
                    relationship_fact_id,
                    DecisionRelationshipBasisRole.RELATIONSHIP,
                    renewal_basis,
                )
            }
            assert len(lineage.history) == 1
            relationship = lineage.history[0]
            assert isinstance(relationship, DecisionRelationshipFact)
            assert relationship.metadata.relationship_fact_id == relationship_fact_id
            assert relationship.metadata.operation_id == renewal_envelope.operation_id
            assert relationship.metadata.actor_attribution == ACTOR
            assert relationship.metadata.trigger == renewal_envelope.trigger
            assert (
                relationship.metadata.technical_provenance
                == renewal_envelope.technical_provenance
            )
            assert relationship.metadata.recorded_at == renewal_at
            assert relationship.source_decision_id == renewal.new_decision_id
            assert relationship.target_decision_id == predecessor_id
            assert (
                relationship.relationship_type is DecisionRelationshipType.RENEWED_FROM
            )
            assert relationship.relationship_effective_at == renewal_at
            assert relationship.relationship_basis == renewal_basis
            _assert_no_database_mechanics(relationship.metadata)

            assert (
                len(
                    {
                        predecessor.decision_id.value,
                        predecessor.need.need_id.value,
                        source.decision_id.value,
                        source.need.need_id.value,
                        relationship_fact_id.value,
                        renewal_envelope.operation_id.value,
                    }
                )
                == 6
            )
        finally:
            await restarted_engine.dispose()

    asyncio.run(scenario())
