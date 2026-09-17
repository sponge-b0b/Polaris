from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import timedelta
from uuid import UUID, uuid4

from polaris.application.decisions import (
    DecisionCommandEnvelope,
    DecisionMemoryService,
    ExpectedDecisionVersion,
)
from polaris.application.decisions.relationships import (
    CorrectDecisionRelationshipCommand,
    DecisionRelationshipCorrectionService,
    DecisionRelationshipService,
    EstablishSupersessionCommand,
    SupersessionTarget,
)
from polaris.domain.actors import ActorId, KnownActorAttribution
from polaris.domain.decisions import (
    DecisionLifecycleDisposition,
    DecisionRelationshipCorrectionBasis,
    DecisionRelationshipCorrectionEffect,
    DecisionRelationshipFact,
    DecisionRelationshipFactId,
    DecisionRelationshipState,
    DeterminateDecisionLifecycleInterpretation,
    OperationId,
    SupersedesRelationshipBasis,
    TechnicalProvenance,
    TechnicalReference,
    TechnicalReferenceKind,
    TriggerKind,
    TriggerProvenance,
)
from polaris.infrastructure.persistence.postgresql import (
    PostgresDecisionStore,
    create_postgres_engine,
)

from .conftest import PostgresTestTarget
from .test_relationship_store import (
    BASE,
    _create_decision,
    _envelope,
    _resolve,
    _supersede,
    _version,
)


@asynccontextmanager
async def _store(
    target: PostgresTestTarget,
) -> AsyncIterator[PostgresDecisionStore]:
    engine = create_postgres_engine(target.database_url, schema=target.schema)
    try:
        yield PostgresDecisionStore(engine)
    finally:
        await engine.dispose()


async def _qualify_base(
    store: PostgresDecisionStore,
    *,
    source: object,
    target: object,
    base_fact_id: UUID,
    recorded_at: object,
    replacement_effective_at: object,
    reference: str,
) -> UUID:
    from datetime import datetime

    from polaris.domain.decisions import InvestmentDecisionId

    if not isinstance(source, InvestmentDecisionId):
        raise TypeError("source must be InvestmentDecisionId")
    if not isinstance(target, InvestmentDecisionId):
        raise TypeError("target must be InvestmentDecisionId")
    if not isinstance(recorded_at, datetime):
        raise TypeError("recorded_at must be datetime")
    if not isinstance(replacement_effective_at, datetime):
        raise TypeError("replacement_effective_at must be datetime")

    fact_id = uuid4()
    result = await DecisionRelationshipCorrectionService(
        store=store,
        now=lambda: recorded_at,
        new_uuid=lambda: fact_id,
    ).correct(
        CorrectDecisionRelationshipCommand(
            envelope=_envelope(
                operation_id=OperationId(uuid4()),
                effective_at=recorded_at,
                versions={
                    source: await _version(store, source, recorded_at),
                    target: await _version(store, target, recorded_at),
                },
                reference=reference,
            ),
            target_relationship_fact_id=DecisionRelationshipFactId(base_fact_id),
            effect=DecisionRelationshipCorrectionEffect.QUALIFY,
            correction_effective_at=recorded_at,
            correction_basis=DecisionRelationshipCorrectionBasis(
                (f"{reference}-correction",)
            ),
            replacement_relationship_effective_at=replacement_effective_at,
            replacement_relationship_basis=SupersedesRelationshipBasis(
                (f"{reference}-replacement",)
            ),
        )
    )
    assert result.relationship_fact_ids == (DecisionRelationshipFactId(fact_id),)
    return fact_id


def test_competing_persisted_corrections_reconstruct_contested(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        async with _store(postgres_target) as store:
            source = await _create_decision(
                store, recorded_at=BASE, label="correction-source"
            )
            target = await _create_decision(
                store,
                recorded_at=BASE + timedelta(minutes=1),
                label="correction-target",
            )
            base_at = BASE + timedelta(hours=1)
            base_fact_id = uuid4()
            await _supersede(
                store,
                source=source,
                targets=(target,),
                recorded_at=base_at,
                fact_ids=(base_fact_id,),
                relationship_effective_at=base_at,
                reference="correction-base",
            )

            first_at = base_at + timedelta(minutes=10)
            first_fact_id = await _qualify_base(
                store,
                source=source,
                target=target,
                base_fact_id=base_fact_id,
                recorded_at=first_at,
                replacement_effective_at=base_at,
                reference="first-qualification",
            )
            second_at = first_at + timedelta(minutes=10)
            second_fact_id = await _qualify_base(
                store,
                source=source,
                target=target,
                base_fact_id=base_fact_id,
                recorded_at=second_at,
                replacement_effective_at=base_at + timedelta(minutes=1),
                reference="second-qualification",
            )

        async with _store(postgres_target) as restarted:
            lineage = await DecisionMemoryService(
                reader=restarted, now=lambda: second_at
            ).lineage(target, known_at=second_at)
            assert len(lineage) == 1
            assert lineage[0].state is DecisionRelationshipState.CONTESTED
            assert {
                DecisionRelationshipFactId(first_fact_id),
                DecisionRelationshipFactId(second_fact_id),
            } <= lineage[0].support_fact_ids

    asyncio.run(scenario())


def test_resolved_target_supersession_preserves_lifecycle_history(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        async with _store(postgres_target) as store:
            source = await _create_decision(
                store, recorded_at=BASE, label="resolved-supersession-source"
            )
            target = await _create_decision(
                store,
                recorded_at=BASE + timedelta(minutes=1),
                label="resolved-supersession-target",
            )
            resolved_at = BASE + timedelta(minutes=30)
            await _resolve(store, target, recorded_at=resolved_at)
            history_before = await store.load_decision_history(target)
            assert history_before is not None

            superseded_at = BASE + timedelta(hours=1)
            await _supersede(
                store,
                source=source,
                targets=(target,),
                recorded_at=superseded_at,
                relationship_effective_at=superseded_at,
                reference="resolved-target-supersession",
            )

            history_after = await store.load_decision_history(target)
            assert history_after == history_before
            view = await DecisionMemoryService(
                reader=store, now=lambda: superseded_at
            ).current(target)
            assert isinstance(
                view.lifecycle_interpretation,
                DeterminateDecisionLifecycleInterpretation,
            )
            assert (
                view.lifecycle_interpretation.disposition
                is DecisionLifecycleDisposition.SUBSTANTIVELY_RESOLVED
            )
            lineage = await DecisionMemoryService(
                reader=store, now=lambda: superseded_at
            ).lineage(target, known_at=superseded_at)
            assert len(lineage) == 1
            assert lineage[0].state is DecisionRelationshipState.SUPPORTED

    asyncio.run(scenario())


def test_relationship_fact_provenance_round_trips_separately(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        actor = KnownActorAttribution(ActorId(uuid4()))
        trigger = TriggerProvenance(
            TriggerKind.HUMAN_REQUEST,
            "relationship-provenance-trigger",
        )
        technical = TechnicalProvenance(
            {
                TechnicalReference(
                    TechnicalReferenceKind.TRACE,
                    "relationship-provenance-trace",
                )
            }
        )
        fact_id = uuid4()
        operation_id = OperationId(uuid4())
        recorded_at = BASE + timedelta(hours=1)

        async with _store(postgres_target) as store:
            source = await _create_decision(
                store, recorded_at=BASE, label="provenance-source"
            )
            target = await _create_decision(
                store,
                recorded_at=BASE + timedelta(minutes=1),
                label="provenance-target",
            )
            command = EstablishSupersessionCommand(
                envelope=DecisionCommandEnvelope(
                    operation_id=operation_id,
                    actor_attribution=actor,
                    trigger=trigger,
                    effective_at=recorded_at,
                    technical_provenance=technical,
                    expected_versions=frozenset(
                        (
                            ExpectedDecisionVersion(
                                source, await _version(store, source, recorded_at)
                            ),
                            ExpectedDecisionVersion(
                                target, await _version(store, target, recorded_at)
                            ),
                        )
                    ),
                ),
                source_decision_id=source,
                targets=(
                    SupersessionTarget(
                        target,
                        SupersedesRelationshipBasis(("provenance-basis",)),
                        recorded_at,
                    ),
                ),
            )
            result = await DecisionRelationshipService(
                reader=store,
                store=store,
                now=lambda: recorded_at,
                new_uuid=lambda: fact_id,
            ).establish_supersession(command)
            assert result.relationship_fact_ids == (
                DecisionRelationshipFactId(fact_id),
            )

        async with _store(postgres_target) as restarted:
            history = await restarted.load_relationship_history()
            persisted = next(
                fact
                for fact in history
                if fact.metadata.relationship_fact_id
                == DecisionRelationshipFactId(fact_id)
            )
            assert isinstance(persisted, DecisionRelationshipFact)
            assert persisted.metadata.operation_id == operation_id
            assert persisted.metadata.actor_attribution == actor
            assert persisted.metadata.trigger == trigger
            assert persisted.metadata.technical_provenance == technical

    asyncio.run(scenario())
