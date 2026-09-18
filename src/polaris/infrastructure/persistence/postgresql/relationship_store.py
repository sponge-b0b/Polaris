"""PostgreSQL persistence for temporal Investment Decision relationships."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import insert, select
from sqlalchemy.engine import RowMapping
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncConnection

from polaris.application.decisions.contracts import (
    DecisionApplicationError,
    DecisionCommandReadUnavailable,
)
from polaris.application.decisions.memory import DecisionMemoryCurrentState
from polaris.application.decisions.ordinary_work import DecisionCommandState
from polaris.application.decisions.relationships import (
    DecisionRelationshipCommit,
    DecisionRelationshipCommitOutcome,
    DecisionRelationshipCommitted,
    DecisionRelationshipConcurrencyConflict,
    DecisionRelationshipContinuityConflict,
    DecisionRelationshipIdempotencyConflict,
    DecisionRelationshipReceipt,
    DecisionRelationshipReplayed,
    DecisionRelationshipRevalidationConflict,
    DecisionRelationshipState,
    DecisionRelationshipUnavailable,
)
from polaris.domain.decisions import (
    ContestedDecisionLifecycleInterpretation,
    DecisionApplicability,
    DecisionLifecycleFactId,
    DecisionLifecycleLineageCycle,
    DecisionLifecycleLineageSafetyIndeterminate,
    DecisionRelationshipAdmissionRejected,
    DecisionRelationshipCommandResult,
    DecisionRelationshipCorrected,
    DecisionRelationshipCorrectionEffect,
    DecisionRelationshipFact,
    DecisionRelationshipFactId,
    DecisionRelationshipHistoryFact,
    DecisionRelationshipType,
    DecisionVersion,
    DeterminateDecisionLifecycleInterpretation,
    InvalidDecisionRelationshipBasis,
    InvalidDecisionRelationshipHistory,
    InvalidDecisionTransition,
    InvestmentDecision,
    InvestmentDecisionId,
    OperationId,
    apply_relationship_command,
    derive_relationship_applicability,
    reconstruct_decision,
)
from polaris.domain.decisions.facts import DecisionLifecycleFact

from .decisions import (
    PostgresDecisionStore as _BasePostgresDecisionStore,
)
from .decisions import (
    _acquire_initiation_lock,
    _domain_uuid,
    _get_operation_receipt,
    _load_decision_history,
    _load_decision_projection,
    _repeatable_read,
)
from .relationship_codec import (
    relationship_fact_from_row,
    relationship_fact_values,
    relationship_receipt_from_row,
    relationship_request_fingerprint,
    relationship_request_payload,
    relationship_result_payload,
)
from .schema import (
    investment_decision_command_receipts,
    investment_decision_relationships,
    investment_decisions,
)

_RELATIONSHIP_COMMAND_KIND = "decision_relationship"


class PostgresDecisionStore(_BasePostgresDecisionStore):
    """Add durable relationship commands and temporal relationship reads."""

    async def get_relationship_receipt(
        self, operation_id: OperationId
    ) -> DecisionRelationshipReceipt | None:
        try:
            async with self._engine.connect() as connection:
                row = await _get_operation_receipt(connection, operation_id)
                if row is None or row["command_kind"] != _RELATIONSHIP_COMMAND_KIND:
                    return None
                return _relationship_receipt(row)
        except (
            SQLAlchemyError,
            DecisionApplicationError,
            ValueError,
            TypeError,
        ) as error:
            raise DecisionCommandReadUnavailable(
                "Decision relationship receipt read is unavailable"
            ) from error

    async def load_relationship_state(
        self, *, known_at: datetime
    ) -> DecisionRelationshipState:
        _aware(known_at, "known_at")
        try:
            async with _repeatable_read(self._engine) as connection:
                history = await _load_relationship_history(
                    connection, known_at=known_at
                )
                loaded = await _load_decisions(
                    connection,
                    known_at=known_at,
                    relationship_history=history,
                )
                return DecisionRelationshipState(
                    history,
                    {identity: value[0] for identity, value in loaded.items()},
                )
        # duplicate-code: relationship persistence operations have distinct transaction and failure semantics; extracting this local shape would couple independently evolving command paths.
        # arid: disable
        except (
            SQLAlchemyError,
            DecisionApplicationError,
            ValueError,
            TypeError,
        ) as error:
            raise DecisionCommandReadUnavailable(
        # arid: enable
                "Decision relationship state read is unavailable"
            ) from error

    async def load_relationship_history(
        self,
    ) -> tuple[DecisionRelationshipHistoryFact, ...]:
        try:
            async with self._engine.connect() as connection:
                return await _load_relationship_history(connection)
        # duplicate-code: relationship persistence operations have distinct transaction and failure semantics; extracting this local shape would couple independently evolving command paths.
        # arid: disable
        except (
            SQLAlchemyError,
            DecisionApplicationError,
            ValueError,
            TypeError,
        ) as error:
            raise DecisionCommandReadUnavailable(
        # arid: enable
                "Decision relationship history read is unavailable"
            # duplicate-code: relationship persistence operations have distinct transaction and failure semantics; extracting this local shape would couple independently evolving command paths.
            # arid: disable
            ) from error

    async def load_decision_for_command(
        self,
        decision_id: InvestmentDecisionId,
        *,
        known_at: datetime,
    ) -> DecisionCommandState | None:
        _aware(known_at, "known_at")
        try:
            async with _repeatable_read(self._engine) as connection:
            # arid: enable
                relationships = await _load_relationship_history(
                    connection, known_at=known_at
                )
                loaded = await _load_decision(
                    connection,
                    decision_id,
                    known_at=known_at,
                    relationship_history=relationships,
                )
                if loaded is None:
                    return None
                decision, applicability = loaded
                return DecisionCommandState(decision, applicability)
        # duplicate-code: relationship persistence operations have distinct transaction and failure semantics; extracting this local shape would couple independently evolving command paths.
        # arid: disable
        except (
            SQLAlchemyError,
            DecisionApplicationError,
            ValueError,
            TypeError,
        ) as error:
            raise DecisionCommandReadUnavailable(
        # arid: enable
                "Decision command-state read is unavailable"
            # duplicate-code: relationship persistence operations have distinct transaction and failure semantics; extracting this local shape would couple independently evolving command paths.
            # arid: disable
            ) from error

    async def load_current_decision_state(
        self,
        decision_id: InvestmentDecisionId,
        *,
        known_at: datetime,
    ) -> DecisionMemoryCurrentState | None:
        _aware(known_at, "known_at")
        try:
            async with _repeatable_read(self._engine) as connection:
                projection = await _load_decision_projection(
                    connection, decision_id
                )
                if projection is None:
                    return None
            # arid: enable
                all_relationships = await _load_relationship_history(connection)
                all_history = await _load_decision_history(connection, decision_id)
                if not all_history:
                    raise ValueError(
                        "Decision projection requires lifecycle history"
                    )
                projection_version = await _authoritative_decision_version(
                    connection, decision_id
                )
                _validate_projection(
                    projection,
                    all_history,
                    all_relationships,
                    version=projection_version,
                )

                history = tuple(
                    fact
                    for fact in all_history
                    if fact.metadata.recorded_at <= known_at
                )
                if not history:
                    return None
                relationships = tuple(
                    fact
                    for fact in all_relationships
                    if fact.metadata.recorded_at <= known_at
                )
                version = await _authoritative_decision_version(
                    connection, decision_id, known_at=known_at
                )
                return DecisionMemoryCurrentState(
                    lifecycle_facts=history,
                    version=version,
                    relationship_history=relationships,
                # duplicate-code: relationship persistence operations have distinct transaction and failure semantics; extracting this local shape would couple independently evolving command paths.
                # arid: disable
                )
        except (
            SQLAlchemyError,
            DecisionApplicationError,
            ValueError,
            TypeError,
        ) as error:
            raise DecisionCommandReadUnavailable(
                # arid: enable
                "Decision current-state read is unavailable"
            # duplicate-code: relationship persistence operations have distinct transaction and failure semantics; extracting this local shape would couple independently evolving command paths.
            # arid: disable
            ) from error

    async def find_unresolved_continuity_candidates(
        self, *, known_at: datetime
    ) -> tuple[InvestmentDecisionId, ...]:
        _aware(known_at, "known_at")
        try:
            async with _repeatable_read(self._engine) as connection:
                relationships = await _load_relationship_history(
                    connection, known_at=known_at
                )
            # arid: enable
                decisions = await _load_decisions(
                    connection,
                    known_at=known_at,
                    relationship_history=relationships,
                )
                return tuple(
                    sorted(
                        (
                            identity
                            for identity, (decision, applicability) in (
                                decisions.items()
                            )
                            if isinstance(
                                decision.lifecycle_interpretation,
                                DeterminateDecisionLifecycleInterpretation,
                            )
                            and decision.lifecycle_interpretation.disposition.value
                            == "unresolved"
                            and applicability is DecisionApplicability.OPERATIVE
                        ),
                        key=lambda identity: identity.value.int,
                    )
                # duplicate-code: relationship persistence operations have distinct transaction and failure semantics; extracting this local shape would couple independently evolving command paths.
                # arid: disable
                )
        except (
            SQLAlchemyError,
            DecisionApplicationError,
            ValueError,
            TypeError,
        ) as error:
            raise DecisionCommandReadUnavailable(
                "Decision continuity candidate read is unavailable"
            ) from error

    async def commit_relationship(
        self, commit: DecisionRelationshipCommit
    ) -> DecisionRelationshipCommitOutcome:
        try:
            async with self._engine.begin() as connection:
                await _acquire_initiation_lock(connection)
                # arid: enable
                prior = await _relationship_operation_receipt(
                    connection, commit.operation_id, for_update=True
                )
                if prior is not None:
                    return _relationship_receipt_outcome(prior, commit)

                expected = dict(commit.expected_versions)
                projections = await _lock_expected_decisions(connection, expected)

                # A missing receipt row cannot be locked. Endpoint rows serialize
                # directly touched same-Decision commits, so re-read after acquiring
                # them before proceeding.
                # duplicate-code: relationship persistence operations have distinct transaction and failure semantics; extracting this local shape would couple independently evolving command paths.
                # arid: disable
                prior = await _relationship_operation_receipt(
                    connection, commit.operation_id, for_update=True
                )
                if prior is not None:
                    return _relationship_receipt_outcome(prior, commit)
                # arid: enable

                guarded = await _guard_relationship_commit(
                    connection, commit, expected, projections
                )
                if isinstance(guarded, _RELATIONSHIP_CONFLICT_OUTCOMES):
                    return guarded

                await _write_relationship_commit(self, connection, commit, guarded)
                receipt = DecisionRelationshipReceipt(
                    commit.operation_id, commit.request, commit.result
                )
                await connection.execute(
                    insert(investment_decision_command_receipts).values(
                        operation_id=commit.operation_id.value,
                        command_kind=_RELATIONSHIP_COMMAND_KIND,
                        request_fingerprint=relationship_request_fingerprint(
                            commit.request
                        ),
                        request_payload=relationship_request_payload(commit.request),
                        result_payload=relationship_result_payload(commit.result),
                        committed_at=guarded.recorded_at,
                    )
                )
                self._write_completed("receipt")
                return DecisionRelationshipCommitted(receipt)
        except SQLAlchemyError as error:
            return await self._translate_relationship_failure(commit, error)
        except (DecisionApplicationError, ValueError, TypeError, RuntimeError) as error:
            return DecisionRelationshipUnavailable(
                f"Decision relationship transaction failed: {type(error).__name__}"
            )

    async def _translate_relationship_failure(
        self,
        commit: DecisionRelationshipCommit,
        error: SQLAlchemyError,
    ) -> DecisionRelationshipCommitOutcome:
        del error
        try:
            async with self._engine.connect() as connection:
                row = await _get_operation_receipt(connection, commit.operation_id)
            if row is not None:
                if row["command_kind"] != _RELATIONSHIP_COMMAND_KIND:
                    return DecisionRelationshipIdempotencyConflict(commit.operation_id)
                return _relationship_receipt_outcome(_relationship_receipt(row), commit)
        except SQLAlchemyError, DecisionApplicationError, ValueError, TypeError:
            pass
        return DecisionRelationshipUnavailable(
            "Decision relationship persistence is unavailable"
        )


@dataclass(frozen=True, slots=True)
class _RelationshipCommitPlan:
    recorded_at: datetime
    proposed: tuple[DecisionRelationshipHistoryFact, ...]
    current_history: tuple[DecisionRelationshipHistoryFact, ...]
    current_decisions: Mapping[InvestmentDecisionId, InvestmentDecision]
    new_decision: InvestmentDecision | None


_RELATIONSHIP_CONFLICT_OUTCOMES = (
    DecisionRelationshipConcurrencyConflict,
    DecisionRelationshipContinuityConflict,
    DecisionRelationshipRevalidationConflict,
)

_RELATIONSHIP_REVALIDATION_ERRORS = (
    # duplicate-code: relationship persistence operations have distinct transaction and failure semantics; extracting this local shape would couple independently evolving command paths.
    # arid: disable
    DecisionRelationshipAdmissionRejected,
    DecisionLifecycleLineageCycle,
    DecisionLifecycleLineageSafetyIndeterminate,
    InvalidDecisionRelationshipBasis,
    InvalidDecisionRelationshipHistory,
    InvalidDecisionTransition,
)
    # arid: enable


async def _guard_relationship_commit(
    connection: AsyncConnection,
    commit: DecisionRelationshipCommit,
    expected: Mapping[InvestmentDecisionId, DecisionVersion],
    projections: Mapping[InvestmentDecisionId, int],
) -> _RelationshipCommitPlan | DecisionRelationshipCommitOutcome:
    conflict = _version_conflict(projections, expected)
    if conflict is not None:
        return DecisionRelationshipConcurrencyConflict(conflict)

    current_history = await _load_relationship_history(connection)
    if not _same_history(current_history, commit.expected_relationship_history):
        return DecisionRelationshipRevalidationConflict(
            "complete relationship history changed before commit"
        )

    recorded_at, proposed = _proposed_facts(current_history, commit)
    loaded_decisions = await _load_decisions(
        connection,
        known_at=recorded_at,
        relationship_history=current_history,
    )
    current_decisions = {
        identity: value[0] for identity, value in loaded_decisions.items()
    }
    expected_conflict = _expected_decision_conflict(
        current_decisions, commit.expected_decisions
    )
    if expected_conflict is not None:
        return DecisionRelationshipRevalidationConflict(expected_conflict)

    if commit.candidate_basis is not None:
        candidates = _continuity_candidates(loaded_decisions)
        if candidates != commit.candidate_basis.candidate_decision_ids:
            return DecisionRelationshipContinuityConflict(candidates)

    new_decision = _new_decision(commit)
    try:
        mismatch = _semantic_revalidation_mismatch(
            commit,
            current_history=current_history,
            proposed=proposed,
            current_decisions=current_decisions,
            new_decision=new_decision,
            recorded_at=recorded_at,
            expected=expected,
        )
    except _RELATIONSHIP_REVALIDATION_ERRORS as error:
        return DecisionRelationshipRevalidationConflict(str(error))
    if mismatch is not None:
        return DecisionRelationshipRevalidationConflict(mismatch)

    return _RelationshipCommitPlan(
        recorded_at, proposed, current_history, current_decisions, new_decision
    )


def _semantic_revalidation_mismatch(
    commit: DecisionRelationshipCommit,
    *,
    current_history: tuple[DecisionRelationshipHistoryFact, ...],
    proposed: tuple[DecisionRelationshipHistoryFact, ...],
    current_decisions: Mapping[InvestmentDecisionId, InvestmentDecision],
    new_decision: InvestmentDecision | None,
    recorded_at: datetime,
    expected: Mapping[InvestmentDecisionId, DecisionVersion],
) -> str | None:
    validation_decisions = dict(current_decisions)
    new_ids: set[InvestmentDecisionId] = set()
    if new_decision is not None:
        validation_decisions[new_decision.decision_id] = new_decision
        new_ids.add(new_decision.decision_id)
    result = apply_relationship_command(
        current_history,
        proposed,
        decisions=validation_decisions,
        expected_versions=expected,
        recording_boundary=recorded_at,
        new_decision_ids=new_ids,
    )
    return _revalidation_mismatch(result, commit)


async def _write_relationship_commit(
    store: PostgresDecisionStore,
    connection: AsyncConnection,
    commit: DecisionRelationshipCommit,
    plan: _RelationshipCommitPlan,
) -> None:
    if plan.new_decision is not None:
        await store._insert_created_decision(connection, plan.new_decision)

    all_decisions = {
        **plan.current_decisions,
        **{item.decision_id: item for item in commit.updated_decisions},
    }
    if plan.new_decision is not None:
        all_decisions[plan.new_decision.decision_id] = plan.new_decision

    for fact in _topological_new_facts(plan.current_history, plan.proposed):
        group = _relationship_group(fact, commit.history)
        evidence = _admission_evidence(
            fact,
            group=group,
            decisions=all_decisions,
            recorded_at=plan.recorded_at,
        )
        await connection.execute(
            insert(investment_decision_relationships).values(
                **relationship_fact_values(
                    fact, group=group, admission_evidence=evidence
                )
            )
        )
        store._write_completed("relationship_fact")

    await _update_relationship_projections(
        connection,
        commit.updated_decisions,
        relationship_history=commit.history,
        recorded_at=plan.recorded_at,
    )
    store._write_completed("relationship_projection")


async def _relationship_operation_receipt(
    connection: AsyncConnection,
    operation_id: OperationId,
    *,
    for_update: bool,
) -> DecisionRelationshipReceipt | DecisionRelationshipIdempotencyConflict | None:
    # duplicate-code: relationship persistence operations have distinct transaction and failure semantics; extracting this local shape would couple independently evolving command paths.
    # arid: disable
    row = await _get_operation_receipt(
        connection,
        operation_id,
        for_update=for_update,
    )
    if row is None:
        return None
    # arid: enable
    if row["command_kind"] != _RELATIONSHIP_COMMAND_KIND:
        return DecisionRelationshipIdempotencyConflict(operation_id)
    return _relationship_receipt(row)


def _relationship_receipt(row: RowMapping) -> DecisionRelationshipReceipt:
    receipt = relationship_receipt_from_row(row)
    if row["request_fingerprint"] != relationship_request_fingerprint(receipt.request):
        raise ValueError("stored relationship receipt fingerprint is invalid")
    return receipt


def _relationship_receipt_outcome(
    prior: DecisionRelationshipReceipt | DecisionRelationshipIdempotencyConflict,
    commit: DecisionRelationshipCommit,
) -> DecisionRelationshipCommitOutcome:
    if isinstance(prior, DecisionRelationshipIdempotencyConflict):
        return prior
    if prior.request == commit.request:
        return DecisionRelationshipReplayed(prior)
    return DecisionRelationshipIdempotencyConflict(commit.operation_id)


async def _lock_expected_decisions(
    connection: AsyncConnection,
    expected: Mapping[InvestmentDecisionId, DecisionVersion],
) -> dict[InvestmentDecisionId, int]:
    if not expected:
        return {}
    ids = sorted((identity.value for identity in expected), key=str)
    rows = (
        await connection.execute(
            select(
                investment_decisions.c.decision_id,
                investment_decisions.c.decision_version,
            )
            .where(investment_decisions.c.decision_id.in_(ids))
            .order_by(investment_decisions.c.decision_id)
            .with_for_update()
        )
    ).all()
    return {
        InvestmentDecisionId(_domain_uuid(row.decision_id)): row.decision_version
        for row in rows
    }


def _version_conflict(
    actual: Mapping[InvestmentDecisionId, int],
    expected: Mapping[InvestmentDecisionId, DecisionVersion],
) -> str | None:
    for identity, version in expected.items():
        if actual.get(identity) != version.value:
            return f"stale Decision version for {identity.value}"
    return None


async def _load_relationship_history(
    connection: AsyncConnection,
    *,
    known_at: datetime | None = None,
) -> tuple[DecisionRelationshipHistoryFact, ...]:
    query = select(investment_decision_relationships)
    if known_at is not None:
        query = query.where(investment_decision_relationships.c.recorded_at <= known_at)
    rows = (
        (
            await connection.execute(
                query.order_by(
                    investment_decision_relationships.c.recorded_at,
                    investment_decision_relationships.c.relationship_fact_id,
                )
            )
        )
        .mappings()
        .all()
    )
    _validate_relationship_rows(rows)
    await _validate_relationship_receipts(connection, rows)
    return tuple(relationship_fact_from_row(row) for row in rows)


async def _validate_relationship_receipts(
    connection: AsyncConnection, rows: Iterable[RowMapping]
) -> None:
    grouped: dict[UUID, set[UUID]] = {}
    for row in rows:
        operation_id = _domain_uuid(row["operation_id"])
        grouped.setdefault(operation_id, set()).add(
            _domain_uuid(row["relationship_fact_id"])
        )
    for operation_id, fact_ids in grouped.items():
        row = await _get_operation_receipt(connection, OperationId(operation_id))
        if row is None or row["command_kind"] != _RELATIONSHIP_COMMAND_KIND:
            raise ValueError("relationship history is missing its durable receipt")
        receipt = _relationship_receipt(row)
        recorded = {identity.value for identity in receipt.result.relationship_fact_ids}
        if recorded != fact_ids:
            raise ValueError(
                "relationship receipt does not identify its complete persisted fact set"
            )


def _validate_relationship_rows(rows: Iterable[RowMapping]) -> None:
    materialized = tuple(rows)
    by_id = {row["relationship_fact_id"]: row for row in materialized}
    if len(by_id) != len(materialized):
        raise ValueError("relationship fact identity must be globally unique")
    for row in materialized:
        _validate_relationship_row(row, by_id)


def _validate_relationship_row(
    row: RowMapping, by_id: Mapping[object, RowMapping]
) -> None:
    if row["fact_kind"] == "base":
        _validate_base_relationship_row(row)
        return
    if row["fact_kind"] != "correction":
        raise ValueError("stored relationship fact kind is invalid")
    _validate_correction_relationship_row(row, by_id)


def _validate_base_relationship_row(row: RowMapping) -> None:
    invalid = (
        row["target_relationship_fact_id"] is not None
        or row["correction_effect"] is not None
        or row["positive_claim_effective_at"] is not None
        or row["positive_basis"] is None
        or row["correction_basis"] is not None
        or row["admission_evidence"] is None
    )
    if invalid:
        raise ValueError("stored base relationship shape is invalid")


def _validate_correction_relationship_row(
    row: RowMapping, by_id: Mapping[object, RowMapping]
) -> None:
    target = by_id.get(row["target_relationship_fact_id"])
    if target is None:
        raise ValueError("relationship correction ancestry is incomplete")
    if target["recorded_at"] > row["recorded_at"]:
        raise ValueError("relationship correction targets later-recorded history")
    _validate_correction_shape(row)
    root = _root_row(row, by_id)
    if (
        row["source_decision_id"] != root["source_decision_id"]
        or row["target_decision_id"] != root["target_decision_id"]
        or row["relationship_type"] != root["relationship_type"]
    ):
        raise ValueError("relationship correction changed lineage identity")


def _validate_correction_shape(row: RowMapping) -> None:
    effect = row["correction_effect"]
    qualify = effect == DecisionRelationshipCorrectionEffect.QUALIFY.value
    disconfirm = effect == DecisionRelationshipCorrectionEffect.DISCONFIRM.value
    if not (qualify or disconfirm) or row["correction_basis"] is None:
        raise ValueError("stored relationship correction shape is invalid")
    replacement = (
        row["positive_claim_effective_at"] is not None
        and row["positive_basis"] is not None
        and row["admission_evidence"] is not None
    )
    if qualify != replacement:
        raise ValueError("stored QUALIFY relationship shape is invalid")
    if disconfirm and (
        row["positive_claim_effective_at"] is not None
        or row["positive_basis"] is not None
    ):
        raise ValueError("stored DISCONFIRM relationship shape is invalid")


def _root_row(
    row: RowMapping,
    by_id: Mapping[object, RowMapping],
) -> RowMapping:
    current = row
    seen: set[object] = set()
    while current["fact_kind"] == "correction":
        identity = current["relationship_fact_id"]
        if identity in seen:
            raise ValueError("relationship correction ancestry must be acyclic")
        seen.add(identity)
        target = by_id.get(current["target_relationship_fact_id"])
        if target is None:
            raise ValueError("relationship correction ancestry is incomplete")
        current = target
    if current["fact_kind"] != "base":
        raise ValueError("relationship correction ancestry must root in a base fact")
    return current


async def _load_known_lifecycle_history(
    connection: AsyncConnection,
    decision_id: InvestmentDecisionId,
    known_at: datetime,
) -> tuple[DecisionLifecycleFact, ...]:
    return tuple(
        fact
        for fact in await _load_decision_history(connection, decision_id)
        if fact.metadata.recorded_at <= known_at
    )


async def _load_decision(
    connection: AsyncConnection,
    decision_id: InvestmentDecisionId,
    *,
    known_at: datetime,
    relationship_history: tuple[DecisionRelationshipHistoryFact, ...],
) -> tuple[InvestmentDecision, DecisionApplicability] | None:
    history = await _load_known_lifecycle_history(connection, decision_id, known_at)
    if not history:
        return None
    version = await _authoritative_decision_version(
        connection, decision_id, known_at=known_at
    )
    applicability = derive_relationship_applicability(
        decision_id,
        relationship_history,
        effective_at=known_at,
        known_at=known_at,
    )
    return (
        reconstruct_decision(
            history,
            observed_at=known_at,
            applicability=applicability,
            decision_version=version,
        ),
        applicability,
    )


async def _load_decisions(
    connection: AsyncConnection,
    *,
    known_at: datetime,
    relationship_history: tuple[DecisionRelationshipHistoryFact, ...],
) -> dict[InvestmentDecisionId, tuple[InvestmentDecision, DecisionApplicability]]:
    rows = await connection.execute(
        select(investment_decisions.c.decision_id).where(
            investment_decisions.c.created_at <= known_at
        )
    )
    decisions: dict[
        InvestmentDecisionId, tuple[InvestmentDecision, DecisionApplicability]
    ] = {}
    for row in rows:
        identity = InvestmentDecisionId(_domain_uuid(row.decision_id))
        loaded = await _load_decision(
            connection,
            identity,
            known_at=known_at,
            relationship_history=relationship_history,
        )
        if loaded is None:
            raise ValueError("persisted Decision is missing lifecycle history")
        decisions[identity] = loaded
    return decisions


async def _authoritative_decision_version(
    connection: AsyncConnection,
    decision_id: InvestmentDecisionId,
    *,
    known_at: datetime | None = None,
) -> DecisionVersion:
    history = await _load_decision_history(connection, decision_id)
    if known_at is not None:
        history = tuple(
            fact for fact in history if fact.metadata.recorded_at <= known_at
        )
    if not history:
        raise ValueError("Decision version requires lifecycle history")
    versions = [history[-1].metadata.decision_version.value]
    query = select(investment_decision_relationships.c.operation_id).where(
        (investment_decision_relationships.c.source_decision_id == decision_id.value)
        | (investment_decision_relationships.c.target_decision_id == decision_id.value)
    )
    if known_at is not None:
        query = query.where(investment_decision_relationships.c.recorded_at <= known_at)
    operation_rows = await connection.execute(query.distinct())
    for operation_row in operation_rows:
        row = await _get_operation_receipt(
            connection, OperationId(_domain_uuid(operation_row.operation_id))
        )
        if row is None or row["command_kind"] != _RELATIONSHIP_COMMAND_KIND:
            raise ValueError("relationship fact is missing its durable command receipt")
        receipt = _relationship_receipt(row)
        expected = dict(receipt.request.expected_versions)
        if receipt.result.new_decision_id == decision_id:
            versions.append(1)
            continue
        before = expected.get(decision_id)
        if before is None:
            raise ValueError(
                "relationship receipt is missing endpoint version evidence"
            )
        versions.append(
            before.value + (decision_id in receipt.result.versioned_decision_ids)
        )
    return DecisionVersion(max(versions))


def _validate_projection(
    projection: RowMapping,
    history: tuple[DecisionLifecycleFact, ...],
    relationships: tuple[DecisionRelationshipHistoryFact, ...],
    *,
    version: DecisionVersion,
) -> None:
    if not history:
        raise ValueError("Decision projection requires lifecycle history")
    decision_id = InvestmentDecisionId(_domain_uuid(projection["decision_id"]))
    lifecycle_boundary = projection["lifecycle_known_at"]
    lifecycle_history = tuple(
        fact for fact in history if fact.metadata.recorded_at <= lifecycle_boundary
    )
    if (
        not lifecycle_history
        or lifecycle_boundary != history[-1].metadata.recorded_at
        or lifecycle_boundary != lifecycle_history[-1].metadata.recorded_at
    ):
        raise ValueError("stored lifecycle projection boundary is invalid")

    lifecycle_relationships = tuple(
        fact
        for fact in relationships
        if fact.metadata.recorded_at <= lifecycle_boundary
    )
    lifecycle_applicability = derive_relationship_applicability(
        decision_id,
        lifecycle_relationships,
        effective_at=lifecycle_boundary,
        known_at=lifecycle_boundary,
    )
    lifecycle = reconstruct_decision(
        lifecycle_history,
        observed_at=lifecycle_boundary,
        applicability=lifecycle_applicability,
    )
    interpretation = lifecycle.lifecycle_interpretation
    disposition = (
        interpretation.disposition.value
        if isinstance(interpretation, DeterminateDecisionLifecycleInterpretation)
        else None
    )
    support = (
        interpretation.support_fact_ids
        if isinstance(
            interpretation,
            (
                DeterminateDecisionLifecycleInterpretation,
                ContestedDecisionLifecycleInterpretation,
            ),
        )
        else frozenset()
    )

    relationship_boundary = _relationship_projection_boundary(
        decision_id, relationships, created_at=projection["created_at"]
    )
    relationship_history = tuple(
        fact
        for fact in relationships
        if fact.metadata.recorded_at <= relationship_boundary
    )
    applicability = derive_relationship_applicability(
        decision_id,
        relationship_history,
        effective_at=relationship_boundary,
        known_at=relationship_boundary,
    )

    posture_boundary = max(lifecycle_boundary, relationship_boundary)
    posture_history = tuple(
        fact for fact in history if fact.metadata.recorded_at <= posture_boundary
    )
    posture_relationships = tuple(
        fact for fact in relationships if fact.metadata.recorded_at <= posture_boundary
    )
    posture_applicability = derive_relationship_applicability(
        decision_id,
        posture_relationships,
        effective_at=posture_boundary,
        known_at=posture_boundary,
    )
    posture = reconstruct_decision(
        posture_history,
        observed_at=posture_boundary,
        applicability=posture_applicability,
    ).work_posture

    drift = (
        _domain_uuid(projection["need_id"]) != lifecycle.need_id.value
        or projection["subject_statement"] != lifecycle.subject.statement
        or projection["scope_completeness"] != lifecycle.scope.completeness.value
        or _uuid_set(projection["scope_portfolio_ids"])
        != frozenset(identity.value for identity in lifecycle.scope.portfolio_ids)
        or projection["lifecycle_interpretation_kind"] != interpretation.kind
        or projection["lifecycle_disposition"] != disposition
        or projection["lifecycle_effective_at"] != interpretation.effective_at
        or _uuid_set(projection["lifecycle_support_fact_ids"])
        != frozenset(identity.value for identity in support)
        or projection["created_at"] != lifecycle.created_at
        or projection["applicability"] != applicability.value
        or projection["work_posture"]
        != (posture.value if posture is not None else None)
        or projection["rebuild_required"] is not False
        or projection["decision_version"] != version.value
    )
    if drift:
        raise ValueError("stored Decision projection does not match immutable history")


def _relationship_projection_boundary(
    decision_id: InvestmentDecisionId,
    relationships: tuple[DecisionRelationshipHistoryFact, ...],
    *,
    created_at: datetime,
) -> datetime:
    boundaries = [created_at]
    groups = _relationship_fact_groups(relationships)
    for fact in relationships:
        source, _, target = groups[fact.metadata.relationship_fact_id]
        if decision_id in {source, target}:
            boundaries.append(fact.metadata.recorded_at)
    return max(boundaries)


def _relationship_fact_groups(
    history: tuple[DecisionRelationshipHistoryFact, ...],
) -> dict[
    DecisionRelationshipFactId,
    tuple[InvestmentDecisionId, DecisionRelationshipType, InvestmentDecisionId],
]:
    by_id = _history_map(history)
    groups: dict[
        DecisionRelationshipFactId,
        tuple[InvestmentDecisionId, DecisionRelationshipType, InvestmentDecisionId],
    ] = {}
    for fact in history:
        root = _relationship_root_fact(fact, by_id)
        groups[fact.metadata.relationship_fact_id] = (
            root.source_decision_id,
            root.relationship_type,
            root.target_decision_id,
        )
    return groups


def _uuid_set(value: object) -> frozenset[UUID]:
    if not isinstance(value, (list, tuple)):
        raise ValueError("database UUID collection is invalid")
    values = tuple(_domain_uuid(item) for item in value)
    if len(set(values)) != len(values):
        raise ValueError("database UUID collection contains duplicates")
    return frozenset(values)


def _same_history(
    left: Iterable[DecisionRelationshipHistoryFact],
    right: Iterable[DecisionRelationshipHistoryFact],
) -> bool:
    return _history_map(left) == _history_map(right)


def _history_map(
    history: Iterable[DecisionRelationshipHistoryFact],
) -> dict[DecisionRelationshipFactId, DecisionRelationshipHistoryFact]:
    values: dict[DecisionRelationshipFactId, DecisionRelationshipHistoryFact] = {}
    for fact in history:
        identity = fact.metadata.relationship_fact_id
        if identity in values:
            raise ValueError("relationship fact identity must be unique")
        values[identity] = fact
    return values


def _proposed_facts(
    current: tuple[DecisionRelationshipHistoryFact, ...],
    commit: DecisionRelationshipCommit,
) -> tuple[datetime, tuple[DecisionRelationshipHistoryFact, ...]]:
    before = _history_map(current)
    post = _history_map(commit.history)
    if any(post.get(identity) != fact for identity, fact in before.items()):
        raise ValueError("relationship commit rewrote existing history")
    proposed = tuple(
        fact
        for fact in commit.history
        if fact.metadata.relationship_fact_id not in before
    )
    if not proposed:
        raise ValueError("relationship commit requires at least one new fact")
    if {fact.metadata.relationship_fact_id for fact in proposed} != set(
        commit.result.relationship_fact_ids
    ):
        raise ValueError("relationship result does not identify the committed facts")
    recorded = {fact.metadata.recorded_at for fact in proposed}
    operations = {fact.metadata.operation_id for fact in proposed}
    if len(recorded) != 1 or operations != {commit.operation_id}:
        raise ValueError("relationship command facts require one recording boundary")
    return next(iter(recorded)), proposed


def _expected_decision_conflict(
    current: Mapping[InvestmentDecisionId, InvestmentDecision],
    expected: Iterable[InvestmentDecision],
) -> str | None:
    for decision in expected:
        if current.get(decision.decision_id) != decision:
            return f"endpoint Decision history changed for {decision.decision_id.value}"
    return None


def _continuity_candidates(
    decisions: Mapping[
        InvestmentDecisionId, tuple[InvestmentDecision, DecisionApplicability]
    ],
) -> frozenset[InvestmentDecisionId]:
    return frozenset(
        identity
        for identity, (decision, applicability) in decisions.items()
        if isinstance(
            decision.lifecycle_interpretation,
            DeterminateDecisionLifecycleInterpretation,
        )
        and decision.lifecycle_interpretation.disposition.value == "unresolved"
        and applicability is DecisionApplicability.OPERATIVE
    )


def _new_decision(commit: DecisionRelationshipCommit) -> InvestmentDecision | None:
    identity = commit.result.new_decision_id
    if identity is None:
        return None
    if commit.candidate_basis is None:
        raise ValueError("renewal result requires a continuity candidate basis")
    matches = [
        item for item in commit.updated_decisions if item.decision_id == identity
    ]
    if len(matches) != 1:
        raise ValueError("renewal result requires exactly one new Decision")
    decision = matches[0]
    if commit.result.need_id != decision.need_id or decision.version != DecisionVersion(
        1
    ):
        raise ValueError("renewal result does not match its new Decision")
    return decision


def _revalidation_mismatch(
    result: DecisionRelationshipCommandResult,
    commit: DecisionRelationshipCommit,
) -> str | None:
    if not hasattr(result, "history") or not hasattr(result, "updated_decisions"):
        return "relationship revalidation returned an invalid result"
    if not _same_history(result.history, commit.history):
        return "relationship history changed during commit revalidation"
    actual = {item.decision_id: item for item in result.updated_decisions}
    expected = {item.decision_id: item for item in commit.updated_decisions}
    if actual != expected:
        return "relationship endpoint versions changed during commit revalidation"
    if result.versioned_decision_ids != commit.result.versioned_decision_ids:
        return "relationship version consequences changed during commit revalidation"
    return None


def _topological_new_facts(
    current: Iterable[DecisionRelationshipHistoryFact],
    proposed: Iterable[DecisionRelationshipHistoryFact],
) -> tuple[DecisionRelationshipHistoryFact, ...]:
    available = {fact.metadata.relationship_fact_id for fact in current}
    remaining = list(proposed)
    ordered: list[DecisionRelationshipHistoryFact] = []
    while remaining:
        progress = False
        for fact in tuple(remaining):
            if isinstance(fact, DecisionRelationshipCorrected) and (
                fact.target_relationship_fact_id not in available
            ):
                continue
            ordered.append(fact)
            available.add(fact.metadata.relationship_fact_id)
            remaining.remove(fact)
            progress = True
        if not progress:
            raise ValueError("relationship correction ancestry cannot be persisted")
    return tuple(ordered)


def _relationship_root_fact(
    fact: DecisionRelationshipHistoryFact,
    by_id: Mapping[DecisionRelationshipFactId, DecisionRelationshipHistoryFact],
) -> DecisionRelationshipFact:
    current = fact
    seen: set[DecisionRelationshipFactId] = set()
    while isinstance(current, DecisionRelationshipCorrected):
        identity = current.metadata.relationship_fact_id
        if identity in seen:
            raise ValueError("relationship correction ancestry must be acyclic")
        seen.add(identity)
        target = by_id.get(current.target_relationship_fact_id)
        if target is None:
            raise ValueError("relationship correction ancestry is incomplete")
        current = target
    if not isinstance(current, DecisionRelationshipFact):
        raise ValueError("relationship correction ancestry must root in a base fact")
    return current


def _relationship_group(
    fact: DecisionRelationshipHistoryFact,
    history: Iterable[DecisionRelationshipHistoryFact],
) -> tuple[InvestmentDecisionId, DecisionRelationshipType, InvestmentDecisionId]:
    root = _relationship_root_fact(fact, _history_map(history))
    # duplicate-code: relationship persistence operations have distinct transaction and failure semantics; extracting this local shape would couple independently evolving command paths.
    # arid: disable
    return (
        root.source_decision_id,
        root.relationship_type,
        root.target_decision_id,
    )
    # arid: enable


def _admission_evidence(
    fact: DecisionRelationshipHistoryFact,
    *,
    group: tuple[InvestmentDecisionId, DecisionRelationshipType, InvestmentDecisionId],
    decisions: Mapping[InvestmentDecisionId, InvestmentDecision],
    recorded_at: datetime,
) -> dict[str, object] | None:
    claim_at: datetime | None
    if isinstance(fact, DecisionRelationshipFact):
        claim_at = fact.relationship_effective_at
    elif fact.effect is DecisionRelationshipCorrectionEffect.QUALIFY:
        claim_at = fact.replacement_relationship_effective_at
    else:
        return None
    if claim_at is None:
        raise ValueError("positive relationship claim requires an effective instant")
    source = decisions.get(group[0])
    target = decisions.get(group[2])
    if source is None or target is None:
        raise ValueError("relationship admission evidence requires both endpoints")
    evidence: dict[str, object] = {
        "known_at": recorded_at.isoformat(),
        "claim_effective_at": claim_at.isoformat(),
        "source": _endpoint_evidence(source, claim_at, recorded_at),
        "target": _endpoint_evidence(target, claim_at, recorded_at),
    }
    if group[1] is DecisionRelationshipType.RENEWED_FROM:
        episode_start = source.need.effective_at
        evidence["renewal_predecessor"] = {
            "episode_start": episode_start.isoformat(),
            "target_at_episode_start": _endpoint_evidence(
                target, episode_start, recorded_at
            ),
            "target_at_claim": _endpoint_evidence(target, claim_at, recorded_at),
        }
    return evidence


def _endpoint_evidence(
    decision: InvestmentDecision,
    effective_at: datetime,
    known_at: datetime,
) -> dict[str, object]:
    view = decision.effective_at(
        effective_at,
        known_at=known_at,
        applicability=DecisionApplicability.OPERATIVE,
    )
    interpretation = view.lifecycle_interpretation
    support: frozenset[DecisionLifecycleFactId] = getattr(
        interpretation, "support_fact_ids", frozenset()
    )
    return {
        "decision_id": str(decision.decision_id.value),
        "lifecycle_fact_ids": [
            str(item.metadata.fact_id.value) for item in decision.history
        ],
        "support_fact_ids": sorted(str(identity.value) for identity in support),
        "lifecycle_disposition": getattr(
            getattr(interpretation, "disposition", None), "value", None
        ),
    }


async def _update_relationship_projections(
    connection: AsyncConnection,
    decisions: Iterable[InvestmentDecision],
    *,
    relationship_history: tuple[DecisionRelationshipHistoryFact, ...],
    recorded_at: datetime,
) -> None:
    for decision in decisions:
        applicability = derive_relationship_applicability(
            decision.decision_id,
            relationship_history,
            effective_at=recorded_at,
            known_at=recorded_at,
        )
        view = reconstruct_decision(
            decision.history,
            observed_at=recorded_at,
            applicability=applicability,
            decision_version=decision.version,
        )
        await connection.execute(
            investment_decisions.update()
            .where(investment_decisions.c.decision_id == decision.decision_id.value)
            .values(
                decision_version=decision.version.value,
                applicability=applicability.value,
                work_posture=(
                    view.work_posture.value if view.work_posture is not None else None
                ),
            )
        )


def _aware(value: datetime, field: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
