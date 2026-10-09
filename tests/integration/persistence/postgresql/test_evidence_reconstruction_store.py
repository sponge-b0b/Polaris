from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

from polaris.application.evidence import (
    EvidenceRequirementResolver,
    EvidenceRequirementVersionAppended,
    EvidenceSufficiencyService,
    RecordEvidenceSufficiencyAssessmentCommand,
)
from polaris.domain.actors import ActorId, KnownActorAttribution
from polaris.domain.decisions import InvestmentDecisionId, OperationId
from polaris.domain.evidence import (
    BasisScopeKey,
    EvidenceInterpretationState,
    EvidenceUse,
)
from polaris.infrastructure.persistence.postgresql import (
    PostgresEvidenceBindingStore,
    PostgresEvidenceRequirementStore,
    PostgresEvidenceStore,
    PostgresEvidenceSufficiencyStore,
    PostgresHistoricalEvidenceStore,
)
from tests.binding_support import BINDING_ID, binding_command, binding_service
from tests.configuration_support import requirement_key, requirement_version
from tests.evidence_support import OBSERVATION_ID, evidence_command, evidence_service

from .conftest import PostgresTestTarget, postgres_store

EFFECTIVE = datetime(2026, 9, 29, 14, 2, tzinfo=UTC)
KNOWN = datetime(2026, 9, 29, 14, 3, tzinfo=UTC)
COMMITTED = datetime(2026, 9, 29, 14, 4, tzinfo=UTC)


def test_historical_store_loads_complete_target_roots_from_one_snapshot(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        key = requirement_key()
        assert key.subject is not None
        async with postgres_store(postgres_target, PostgresEvidenceStore) as (_, store):
            await evidence_service(store, OBSERVATION_ID).record(
                replace(evidence_command(), subject=key.subject)
            )
        async with postgres_store(
            postgres_target, PostgresEvidenceRequirementStore
        ) as (_, store):
            result = await store.append_requirement_version(requirement_version())
            assert isinstance(result, EvidenceRequirementVersionAppended)
        async with postgres_store(postgres_target, PostgresEvidenceBindingStore) as (
            engine,
            store,
        ):
            # duplicate-code: this read-adapter contract seeds a real binding
            # independently of correction-store tests to avoid common-mode proof.
            # arid: disable
            await binding_service(
                store,
                BINDING_ID,
                requirements=EvidenceRequirementResolver(
                    PostgresEvidenceRequirementStore(engine)
                ),
            ).record(binding_command())
            # arid: enable
        async with postgres_store(
            postgres_target, PostgresEvidenceSufficiencyStore
        ) as (_, store):
            service = EvidenceSufficiencyService(
                store=store,
                now=lambda: COMMITTED,
                new_uuid=lambda: UUID("00000000-0000-4000-8000-000000000b01"),
            )
            await service.assess(
                RecordEvidenceSufficiencyAssessmentCommand(
                    operation_id=OperationId(
                        UUID("00000000-0000-4000-8000-000000000b02")
                    ),
                    applicability_key=key,
                    attribution=KnownActorAttribution(
                        ActorId(UUID("00000000-0000-4000-8000-000000000b03"))
                    ),
                    effective_at=EFFECTIVE,
                    known_at=KNOWN,
                )
            )
        async with postgres_store(postgres_target, PostgresHistoricalEvidenceStore) as (
            _,
            store,
        ):
            histories = await store.load_target_histories(key.target)
            scope = BasisScopeKey(
                InvestmentDecisionId(uuid4()),
                key.target,
                key.scope,
                key.evidence_use,
            )
            current = await store.load_scope_histories(scope, at=COMMITTED)
            other_use = await store.load_scope_histories(
                replace(scope, use=EvidenceUse.CHALLENGE_BASIS), at=COMMITTED
            )
        assert len(histories.observations) == 1
        assert len(histories.bindings) == 1
        assert len(histories.assessments) == 1
        assert current == histories
        assert other_use == type(histories)((), (), ())
        assert histories.bindings[0].root.observation_id == (
            histories.observations[0].root.observation_id
        )
        interpretation = histories.assessments[0].interpret(
            effective_at=EFFECTIVE, known_at=COMMITTED
        )
        assert interpretation.state is EvidenceInterpretationState.DETERMINATE
        assert histories.assessments[0].root.requirement_version_id == (
            requirement_version().version_id
        )

    asyncio.run(scenario())
