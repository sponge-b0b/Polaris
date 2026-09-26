from __future__ import annotations

import asyncio
from dataclasses import fields
from datetime import timedelta
from typing import Any, cast
from uuid import uuid4

from sqlalchemy import inspect, select
from sqlalchemy.engine import Connection

from polaris.application.decisions import DecisionMemoryService
from polaris.application.decisions.memory import (
    DecisionHistoryView,
    DecisionLineageView,
    DecisionMemoryCurrentState,
    DecisionMemoryTemporalView,
    DecisionMemoryView,
)
from polaris.application.decisions.relationships import (
    DecisionRelationshipSemanticRequest,
    DecisionRelationshipService,
    OmittedRenewalLineagePayload,
    RelationshipCorrectionPayload,
    RelationshipCorrectionSetMemberPayload,
    RenewalPayload,
    RenewalPredecessor,
    RenewDecisionCommand,
    SupersessionPayload,
    SupersessionTarget,
)
from polaris.domain.decisions import (
    DecisionRelationshipCorrected,
    DecisionRelationshipFact,
    DecisionRelationshipFactMetadata,
    DecisionRelationshipInterpretation,
    DecisionRelationshipType,
    DecisionScope,
    DecisionSubject,
    OperationId,
    RenewedFromRelationshipBasis,
    SupersedesRelationshipBasis,
)
from polaris.infrastructure.persistence.postgresql import create_postgres_engine
from polaris.infrastructure.persistence.postgresql.schema import (
    investment_decision_command_receipts,
    investment_decision_relationships,
)

from .conftest import PostgresTestTarget, postgres_engine_store
from .test_relationship_store import (
    BASE,
    _create_decision,
    _envelope,
    _resolve,
    _supersede,
)

RELATIONSHIP_COLUMNS = frozenset(
    """
    row_id relationship_fact_id source_decision_id target_decision_id
    relationship_type fact_kind target_relationship_fact_id operation_id
    actor_attribution_kind actor_id actor_candidate_ids trigger_kind
    trigger_reference technical_provenance effective_at recorded_at
    correction_effect positive_claim_effective_at positive_basis correction_basis
    admission_evidence
    """.split()
)

REQUEST_FIELDS = frozenset(
    "kind actor_attribution trigger effective_at expected_versions payload".split()
)
ENDPOINT_ADMISSION_FIELDS = frozenset(
    "decision_id lifecycle_fact_ids support_fact_ids lifecycle_disposition".split()
)
BASE_ADMISSION_FIELDS = frozenset("known_at claim_effective_at source target".split())
RENEWAL_PREDECESSOR_ADMISSION_FIELDS = frozenset(
    "episode_start target_at_episode_start target_at_claim".split()
)

MEMORY_COMMON_FIELDS = frozenset(
    """
    decision_id need subject scope lifecycle_interpretation work_posture
    applicability lineage
    """.split()
)

EXPECTED_MODEL_FIELDS: dict[type[Any], frozenset[str]] = {
    DecisionRelationshipFactMetadata: frozenset(
        """
        relationship_fact_id operation_id actor_attribution trigger
        technical_provenance recorded_at
        """.split()
    ),
    DecisionRelationshipFact: frozenset(
        """
        metadata source_decision_id target_decision_id relationship_type
        relationship_effective_at relationship_basis
        """.split()
    ),
    DecisionRelationshipCorrected: frozenset(
        """
        metadata target_relationship_fact_id effect correction_effective_at
        correction_basis replacement_relationship_effective_at
        replacement_relationship_basis
        """.split()
    ),
    DecisionRelationshipInterpretation: frozenset(
        """
        source_decision_id relationship_type target_decision_id effective_at known_at
        state support_fact_ids basis_contributions surviving_positive_claims
        """.split()
    ),
    RenewedFromRelationshipBasis: frozenset({"references"}),
    SupersedesRelationshipBasis: frozenset({"references"}),
    RenewalPredecessor: frozenset("decision_id basis".split()),
    SupersessionTarget: frozenset("decision_id basis effective_at".split()),
    RenewalPayload: frozenset(
        "need_statement subject scope predecessors continuity".split()
    ),
    OmittedRenewalLineagePayload: frozenset("source_decision_id predecessors".split()),
    SupersessionPayload: frozenset("source_decision_id targets".split()),
    RelationshipCorrectionPayload: frozenset(
        """
        target_relationship_fact_id effect correction_effective_at correction_basis
        replacement_relationship_effective_at replacement_relationship_basis
        """.split()
    ),
    RelationshipCorrectionSetMemberPayload: frozenset(
        """
        target effect correction_effective_at correction_basis
        replacement_relationship_effective_at replacement_relationship_basis
        """.split()
    ),
    DecisionRelationshipSemanticRequest: REQUEST_FIELDS,
    DecisionLineageView: frozenset(
        """
        source_decision_id target_decision_id relationship_type direction effective_at
        known_at state support_fact_ids basis_contributions surviving_positive_claims
        history
        """.split()
    ),
    DecisionMemoryCurrentState: frozenset(
        "lifecycle_facts version relationship_history".split()
    ),
    DecisionMemoryView: MEMORY_COMMON_FIELDS | {"version"},
    DecisionMemoryTemporalView: MEMORY_COMMON_FIELDS,
    DecisionHistoryView: frozenset(
        "decision_id known_at lifecycle_facts relationship_facts".split()
    ),
}


def _field_names(value: type[Any]) -> frozenset[str]:
    return frozenset(item.name for item in fields(value))


def _mapping(value: object) -> dict[str, object]:
    assert isinstance(value, dict)
    return cast(dict[str, object], value)


def _list(value: object) -> list[object]:
    assert isinstance(value, list)
    return cast(list[object], value)


def _assert_endpoint_shape(value: object) -> None:
    assert frozenset(_mapping(value)) == ENDPOINT_ADMISSION_FIELDS


def _assert_admission_shape(
    value: object,
    relationship_type: DecisionRelationshipType,
) -> None:
    admission = _mapping(value)
    expected = BASE_ADMISSION_FIELDS
    if relationship_type is DecisionRelationshipType.RENEWED_FROM:
        expected |= {"renewal_predecessor"}
    assert frozenset(admission) == expected
    _assert_endpoint_shape(admission["source"])
    _assert_endpoint_shape(admission["target"])
    if relationship_type is not DecisionRelationshipType.RENEWED_FROM:
        return
    renewal = _mapping(admission["renewal_predecessor"])
    assert frozenset(renewal) == RENEWAL_PREDECESSOR_ADMISSION_FIELDS
    _assert_endpoint_shape(renewal["target_at_episode_start"])
    _assert_endpoint_shape(renewal["target_at_claim"])


def _assert_request_payload_shape(
    value: object,
    relationship_type: DecisionRelationshipType,
) -> None:
    request = _mapping(value)
    assert frozenset(request) == REQUEST_FIELDS
    body = _mapping(request["payload"])
    if relationship_type is DecisionRelationshipType.RENEWED_FROM:
        assert frozenset(body) == _field_names(RenewalPayload)
        predecessor = _mapping(_list(body["predecessors"])[0])
        assert frozenset(predecessor) == _field_names(RenewalPredecessor)
        basis = _mapping(predecessor["basis"])
    else:
        assert frozenset(body) == _field_names(SupersessionPayload)
        target = _mapping(_list(body["targets"])[0])
        assert frozenset(target) == _field_names(SupersessionTarget)
        basis = _mapping(target["basis"])
    assert frozenset(basis) == {"kind", "references"}


async def _migrated_relationship_shape(
    target: PostgresTestTarget,
) -> tuple[frozenset[str], tuple[str, ...]]:
    engine = create_postgres_engine(target.database_url, schema=target.schema)
    try:
        async with engine.connect() as connection:

            def inspect_shape(
                sync_connection: Connection,
            ) -> tuple[frozenset[str], tuple[str, ...]]:
                inspector = inspect(sync_connection)
                columns = frozenset(
                    item["name"]
                    for item in inspector.get_columns(
                        "investment_decision_relationships",
                        schema=target.schema,
                    )
                )
                checks = tuple(
                    cast(str, item["sqltext"])
                    for item in inspector.get_check_constraints(
                        "investment_decision_relationships",
                        schema=target.schema,
                    )
                    if item["sqltext"] is not None
                )
                return columns, checks

            return await connection.run_sync(inspect_shape)
    finally:
        await engine.dispose()


def test_r2_relationship_contract_excludes_prior_context_payload() -> None:
    for model, expected in EXPECTED_MODEL_FIELDS.items():
        assert _field_names(model) == expected

    assert {item.value for item in DecisionRelationshipType} == {
        "renewed_from",
        "supersedes",
    }
    assert frozenset(investment_decision_relationships.c.keys()) == (
        RELATIONSHIP_COLUMNS
    )


def test_r2_persisted_relationships_exclude_prior_context_payload_after_restart(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        migrated_columns, checks = await _migrated_relationship_shape(postgres_target)
        assert migrated_columns == RELATIONSHIP_COLUMNS
        relationship_type_checks = tuple(
            check.lower() for check in checks if "relationship_type" in check.lower()
        )
        assert len(relationship_type_checks) == 1
        relationship_type_check = relationship_type_checks[0]
        assert "renewed_from" in relationship_type_check
        assert "supersedes" in relationship_type_check
        assert "prior_decision_context" not in relationship_type_check

        renewal_at = BASE + timedelta(hours=1)
        supersession_at = BASE + timedelta(hours=2)
        async with postgres_engine_store(postgres_target) as (engine, store):
            predecessor = await _create_decision(
                store,
                recorded_at=BASE,
                label="prior-context-predecessor",
            )
            predecessor_version, _ = await _resolve(
                store,
                predecessor,
                recorded_at=BASE + timedelta(minutes=30),
            )
            renewal_operation = OperationId(uuid4())
            renewal_envelope = _envelope(
                operation_id=renewal_operation,
                effective_at=renewal_at,
                versions={predecessor: predecessor_version},
                reference="prior-context-renewal",
            )
            renewal_predecessor = RenewalPredecessor(
                predecessor,
                RenewedFromRelationshipBasis(("renewal-basis",)),
            )
            renewal_command = RenewDecisionCommand(
                envelope=renewal_envelope,
                need_statement="Renew the resolved choice",
                subject=DecisionSubject("Prior-context renewal"),
                scope=DecisionScope.unresolved(),
                predecessors=(renewal_predecessor,),
            )
            renewal_result = await DecisionRelationshipService(
                reader=store,
                store=store,
                now=lambda: renewal_at,
                new_uuid=uuid4,
            ).renew(renewal_command)
            assert renewal_result.new_decision_id is not None
            renewal_source = renewal_result.new_decision_id

            supersession_source = await _create_decision(
                store,
                recorded_at=BASE + timedelta(minutes=70),
                label="prior-context-supersession-source",
            )
            supersession_target = await _create_decision(
                store,
                recorded_at=BASE + timedelta(minutes=80),
                label="prior-context-supersession-target",
            )
            supersession_operation = OperationId(uuid4())
            _, supersession_result = await _supersede(
                store,
                source=supersession_source,
                targets=(supersession_target,),
                recorded_at=supersession_at,
                operation_id=supersession_operation,
                reference="prior-context-supersession",
            )

            fact_ids = {
                renewal_result.relationship_fact_ids[0].value,
                supersession_result.relationship_fact_ids[0].value,
            }
            operation_ids = {
                renewal_operation.value,
                supersession_operation.value,
            }
            async with engine.connect() as connection:
                relationship_rows = (
                    (
                        await connection.execute(
                            select(investment_decision_relationships).where(
                                investment_decision_relationships.c.relationship_fact_id.in_(
                                    fact_ids
                                )
                            )
                        )
                    )
                    .mappings()
                    .all()
                )
                receipt_rows = (
                    (
                        await connection.execute(
                            select(
                                investment_decision_command_receipts.c.operation_id,
                                investment_decision_command_receipts.c.request_payload,
                            ).where(
                                investment_decision_command_receipts.c.operation_id.in_(
                                    operation_ids
                                )
                            )
                        )
                    )
                    .mappings()
                    .all()
                )

            assert len(relationship_rows) == 2
            for row in relationship_rows:
                assert frozenset(row.keys()) == RELATIONSHIP_COLUMNS
                relationship_type = DecisionRelationshipType(row["relationship_type"])
                _assert_admission_shape(row["admission_evidence"], relationship_type)

            assert len(receipt_rows) == 2
            receipt_payloads = {
                row["operation_id"]: row["request_payload"] for row in receipt_rows
            }
            _assert_request_payload_shape(
                receipt_payloads[renewal_operation.value],
                DecisionRelationshipType.RENEWED_FROM,
            )
            _assert_request_payload_shape(
                receipt_payloads[supersession_operation.value],
                DecisionRelationshipType.SUPERSEDES,
            )

        async with postgres_engine_store(postgres_target) as (_, restarted):
            memory = DecisionMemoryService(
                reader=restarted,
                now=lambda: supersession_at,
            )
            renewal_lineage = await memory.lineage(
                renewal_source,
                known_at=supersession_at,
            )
            supersession_lineage = await memory.lineage(
                supersession_target,
                known_at=supersession_at,
            )
            assert len(renewal_lineage) == 1
            assert len(supersession_lineage) == 1
            assert renewal_lineage[0].relationship_type is (
                DecisionRelationshipType.RENEWED_FROM
            )
            assert supersession_lineage[0].relationship_type is (
                DecisionRelationshipType.SUPERSEDES
            )
            assert type(renewal_lineage[0]) is DecisionLineageView
            assert type(supersession_lineage[0]) is DecisionLineageView

    asyncio.run(scenario())
