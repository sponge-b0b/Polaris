"""Async PostgreSQL adapter for foundational Investment Decision persistence."""

from __future__ import annotations

import re
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, insert, select, text
from sqlalchemy.engine import RowMapping
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine

from polaris.application.decisions.contracts import (
    DecisionCommandReadUnavailable,
    InitiationCommit,
    InitiationCommitOutcome,
    InitiationCommitted,
    InitiationContinuityConflict,
    InitiationIdempotencyConflict,
    InitiationNeedAlreadyGrounded,
    InitiationReceipt,
    InitiationReplayed,
    InitiationResultKind,
    InitiationUnavailable,
)
from polaris.application.decisions.memory import DecisionMemoryCurrentState
from polaris.application.decisions.ordinary_work import (
    DecisionCommandState,
    DecisionMutationCommit,
    DecisionMutationCommitOutcome,
    DecisionMutationCommitted,
    DecisionMutationConcurrencyConflict,
    DecisionMutationIdempotencyConflict,
    DecisionMutationKind,
    DecisionMutationReceipt,
    DecisionMutationReplayed,
    DecisionMutationResultKind,
    DecisionMutationUnavailable,
)
from polaris.domain.decisions import (
    ContestedDecisionLifecycleInterpretation,
    DecisionApplicability,
    DecisionInitiated,
    DecisionRelationshipHistoryFact,
    DecisionVersion,
    DeterminateDecisionLifecycleInterpretation,
    InvestmentDecision,
    InvestmentDecisionId,
    NotYetEffectiveDecisionLifecycleInterpretation,
    OperationId,
    derive_relationship_applicability,
    reconstruct_decision,
)
from polaris.domain.decisions.facts import DecisionLifecycleFact

from .codec import (
    actor_columns,
    initiated_fact_from_rows,
    initiation_receipt_from_row,
    initiation_request_payload,
    initiation_result_payload,
    mutation_fact_from_row,
    mutation_fact_values,
    mutation_receipt_from_row,
    mutation_request_fingerprint,
    mutation_request_payload,
    mutation_result_payload,
    request_fingerprint,
    technical_payload,
    trigger_columns,
)
from .schema import (
    decision_needs,
    investment_decision_command_receipts,
    investment_decision_lifecycle_facts,
    investment_decision_relationships,
    investment_decisions,
)

_SCHEMA_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_INITIATION_LOCK_KEY = 5_620_113_451_159_393_619
_INITIATION_COMMAND_KIND = "initiate_decision"
_CONTINUITY_NEUTRAL_MUTATIONS = frozenset(
    {
        DecisionMutationKind.REVISE_SUBJECT,
        DecisionMutationKind.ESTABLISH_OR_REVISE_SCOPE,
        DecisionMutationKind.APPLY_HUMAN_DEFERRAL,
        DecisionMutationKind.WITHDRAW_WORK,
        DecisionMutationKind.RESUME_WORK,
    }
)


def _require_qualified_postgres_runtime() -> None:
    is_gil_enabled = getattr(sys, "_is_gil_enabled", None)
    if is_gil_enabled is not None and not is_gil_enabled():
        raise RuntimeError(
            "PostgreSQL persistence is not qualified for GIL-disabled CPython; "
            "run the persistence-owning role under standard CPython until ADR 0005 "
            "requalification succeeds"
        )


def create_postgres_engine(
    database_url: str,
    *,
    schema: str | None = None,
) -> AsyncEngine:
    """Create the async engine owned by the PostgreSQL adapter boundary."""
    _require_qualified_postgres_runtime()
    if not database_url.startswith("postgresql+asyncpg://"):
        raise ValueError("database_url must use the postgresql+asyncpg driver")
    connect_args: dict[str, object] = {}
    if schema is not None:
        if _SCHEMA_NAME.fullmatch(schema) is None:
            raise ValueError("schema must be a PostgreSQL identifier")
        connect_args["server_settings"] = {"search_path": schema}
    return create_async_engine(
        database_url,
        pool_pre_ping=True,
        connect_args=connect_args,
    )


@asynccontextmanager
async def _repeatable_read(engine: AsyncEngine) -> AsyncIterator[AsyncConnection]:
    async with engine.connect() as raw_connection:
        connection = await raw_connection.execution_options(
            isolation_level="REPEATABLE READ"
        )
        async with connection.begin():
            yield connection


class PostgresDecisionStore:
    """Satisfy the foundational Decision command and memory-reader ports."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def get_initiation_receipt(
        self, operation_id: OperationId
    ) -> InitiationReceipt | None:
        try:
            async with self._engine.connect() as connection:
                return await _get_receipt(connection, operation_id)
        except (SQLAlchemyError, ValueError, TypeError) as error:
            raise DecisionCommandReadUnavailable(
                "Decision initiation receipt read is unavailable"
            ) from error

    async def get_mutation_receipt(
        self, operation_id: OperationId
    ) -> DecisionMutationReceipt | None:
        try:
            async with self._engine.connect() as connection:
                return await _get_mutation_receipt(connection, operation_id)
        except (SQLAlchemyError, ValueError, TypeError) as error:
            raise DecisionCommandReadUnavailable(
                "Decision mutation receipt read is unavailable"
            ) from error

    async def commit_initiation(
        self, commit: InitiationCommit
    ) -> InitiationCommitOutcome:
        try:
            async with self._engine.begin() as connection:
                await _acquire_initiation_lock(connection)
                prior = await _get_initiation_operation_receipt(
                    connection,
                    commit.operation_id,
                    for_update=True,
                )
                if prior is not None:
                    return _receipt_outcome(prior, commit)

                known_at = await _continuity_knowledge_boundary(
                    connection,
                    minimum=commit.candidate_basis.known_at,
                )
                candidates = await self._authoritative_continuity_candidates(
                    connection,
                    effective_at=commit.candidate_basis.known_at,
                    known_at=known_at,
                )
                if candidates != commit.candidate_basis.candidate_decision_ids:
                    return InitiationContinuityConflict(candidates)

                if commit.decision is not None:
                    _validate_created_commit(commit)
                    await self._insert_created_decision(connection, commit.decision)
                else:
                    _validate_continued_commit(commit)

                receipt = InitiationReceipt(
                    operation_id=commit.operation_id,
                    request=commit.request,
                    result=commit.result,
                )
                await connection.execute(
                    insert(investment_decision_command_receipts).values(
                        operation_id=commit.operation_id.value,
                        command_kind=_INITIATION_COMMAND_KIND,
                        request_fingerprint=request_fingerprint(commit.request),
                        request_payload=initiation_request_payload(commit.request),
                        result_payload=initiation_result_payload(commit.result),
                        committed_at=commit.candidate_basis.known_at,
                    )
                )
                self._write_completed("receipt")
                return InitiationCommitted(receipt)
        except SQLAlchemyError as error:
            return await self._translate_write_failure(commit, error)
        except (
            DecisionCommandReadUnavailable,
            ValueError,
            TypeError,
            RuntimeError,
        ) as error:
            return InitiationUnavailable(
                f"Decision initiation transaction failed: {type(error).__name__}"
            )

    async def find_unresolved_continuity_candidates(
        self, *, known_at: datetime
    ) -> tuple[InvestmentDecisionId, ...]:
        if known_at.tzinfo is None or known_at.utcoffset() is None:
            raise ValueError("known_at must be timezone-aware")
        try:
            async with _repeatable_read(self._engine) as connection:
                candidates = await self._authoritative_continuity_candidates(
                    connection,
                    effective_at=known_at,
                    known_at=known_at,
                )
                return tuple(sorted(candidates, key=lambda value: value.value.int))
        except (SQLAlchemyError, ValueError, TypeError) as error:
            raise DecisionCommandReadUnavailable(
                "Decision continuity candidate read is unavailable"
            ) from error

    async def _authoritative_continuity_candidates(
        self,
        connection: AsyncConnection,
        *,
        effective_at: datetime,
        known_at: datetime,
    ) -> frozenset[InvestmentDecisionId]:
        """Reconstruct candidates at one effective and knowledge boundary."""
        await _load_empty_relationship_history(connection)
        rows = await connection.execute(
            select(investment_decisions.c.decision_id).where(
                investment_decisions.c.created_at <= known_at
            )
        )
        candidates: set[InvestmentDecisionId] = set()
        for row in rows:
            identity = InvestmentDecisionId(_domain_uuid(row.decision_id))
            history = tuple(
                fact
                for fact in await _load_decision_history(connection, identity)
                if fact.metadata.recorded_at <= known_at
            )
            decision = reconstruct_decision(
                history,
                observed_at=known_at,
                applicability=DecisionApplicability.OPERATIVE,
            ).effective_at(
                effective_at,
                known_at=known_at,
                applicability=DecisionApplicability.OPERATIVE,
            )
            if (
                isinstance(
                    decision.lifecycle_interpretation,
                    DeterminateDecisionLifecycleInterpretation,
                )
                and decision.lifecycle_interpretation.disposition.value == "unresolved"
            ):
                candidates.add(identity)
        return frozenset(candidates)

    async def load_decision_for_command(
        self,
        decision_id: InvestmentDecisionId,
        *,
        known_at: datetime,
    ) -> DecisionCommandState | None:
        try:
            async with _repeatable_read(self._engine) as connection:
                projection = (
                    await connection.execute(
                        select(
                            investment_decisions.c.applicability,
                            investment_decisions.c.decision_version,
                        ).where(investment_decisions.c.decision_id == decision_id.value)
                    )
                ).one_or_none()
                if projection is None:
                    return None
                history = await _load_decision_history(connection, decision_id)
                applicability = DecisionApplicability(projection.applicability)
                return DecisionCommandState(
                    decision=reconstruct_decision(
                        history,
                        observed_at=known_at,
                        applicability=applicability,
                        decision_version=_decision_version(projection.decision_version),
                    ),
                    applicability=applicability,
                )
        except (SQLAlchemyError, ValueError, TypeError) as error:
            raise DecisionCommandReadUnavailable(
                "Decision command-state read is unavailable"
            ) from error

    async def commit_mutation(
        self, commit: DecisionMutationCommit
    ) -> DecisionMutationCommitOutcome:
        try:
            async with self._engine.begin() as connection:
                await _acquire_continuity_mutation_lock(
                    connection,
                    commit.request.kind,
                )
                prior_row = await _get_operation_receipt(
                    connection,
                    commit.operation_id,
                    for_update=True,
                )
                if prior_row is not None and (
                    prior_row["command_kind"] != "decision_mutation"
                ):
                    return DecisionMutationIdempotencyConflict(commit.operation_id)
                if prior_row is not None:
                    prior = mutation_receipt_from_row(prior_row)
                    return _mutation_receipt_outcome(prior, commit)

                projection = (
                    await connection.execute(
                        select(investment_decisions.c.decision_version)
                        .where(
                            investment_decisions.c.decision_id
                            == commit.decision.decision_id.value
                        )
                        .with_for_update()
                    )
                ).one_or_none()

                # A missing receipt row cannot be locked. The Decision row is the
                # serialization point for same-Decision commits, so re-read after
                # acquiring it before reporting a stale version/history guard.
                # duplicate-code: operations require independent control flow.
                # arid: disable
                prior_row = await _get_operation_receipt(
                    connection,
                    commit.operation_id,
                    for_update=True,
                )
                if prior_row is not None and (
                    prior_row["command_kind"] != "decision_mutation"
                ):
                    return DecisionMutationIdempotencyConflict(commit.operation_id)
                if prior_row is not None:
                    prior = mutation_receipt_from_row(prior_row)
                    return _mutation_receipt_outcome(prior, commit)
                # arid: enable

                if projection is None or (
                    projection.decision_version != commit.expected_version.value
                ):
                    return DecisionMutationConcurrencyConflict(
                        commit.decision.decision_id
                    )
                tail = (
                    await connection.execute(
                        select(investment_decision_lifecycle_facts.c.fact_id)
                        .where(
                            investment_decision_lifecycle_facts.c.decision_id
                            == commit.decision.decision_id.value
                        )
                        .order_by(
                            investment_decision_lifecycle_facts.c.lifecycle_sequence.desc()
                        )
                        .limit(1)
                    )
                ).one()
                if tail.fact_id != commit.expected_history_tail_fact_id.value:
                    return DecisionMutationConcurrencyConflict(
                        commit.decision.decision_id
                    )

                fact = _mutation_fact(commit)
                if fact is not None:
                    await connection.execute(
                        insert(investment_decision_lifecycle_facts).values(
                            **mutation_fact_values(fact)
                        )
                    )
                    self._write_completed("lifecycle_fact")
                    await connection.execute(
                        investment_decisions.update()
                        .where(
                            investment_decisions.c.decision_id
                            == commit.decision.decision_id.value
                        )
                        .values(**_mutation_projection_values(commit.decision))
                    )
                    self._write_completed("projection")
                receipt = DecisionMutationReceipt(
                    # duplicate-code: operations require independent control flow.
                    # arid: disable
                    operation_id=commit.operation_id,
                    request=commit.request,
                    result=commit.result,
                )
                await connection.execute(
                    insert(investment_decision_command_receipts).values(
                        operation_id=commit.operation_id.value,
                        # arid: enable
                        command_kind="decision_mutation",
                        request_fingerprint=mutation_request_fingerprint(
                            commit.request
                        ),
                        request_payload=mutation_request_payload(commit.request),
                        result_payload=mutation_result_payload(commit.result),
                        committed_at=(
                            fact.metadata.recorded_at
                            if fact is not None
                            else func.now()
                        ),
                    )
                )
                self._write_completed("receipt")
                return DecisionMutationCommitted(receipt)
        except SQLAlchemyError as error:
            return await self._translate_mutation_failure(commit, error)
        except (ValueError, TypeError, RuntimeError) as error:
            return DecisionMutationUnavailable(
                f"Decision mutation transaction failed: {type(error).__name__}"
            )

    async def load_current_decision_state(
        self,
        decision_id: InvestmentDecisionId,
        *,
        known_at: datetime,
    ) -> DecisionMemoryCurrentState | None:
        del known_at
        try:
            async with _repeatable_read(self._engine) as connection:
                projection = await _load_decision_projection(connection, decision_id)
                if projection is None:
                    return None
                history = await _load_decision_history(connection, decision_id)
                relationships = await _load_empty_relationship_history(connection)
                _validate_lifecycle_projection(
                    projection,
                    history,
                    relationships,
                )
                return DecisionMemoryCurrentState(
                    lifecycle_facts=history,
                    version=_decision_version(projection["decision_version"]),
                    relationship_history=relationships,
                )
        except (SQLAlchemyError, ValueError, TypeError) as error:
            raise DecisionCommandReadUnavailable(
                "Decision current-state read is unavailable"
            ) from error

    async def load_decision_history(
        self, decision_id: InvestmentDecisionId
    ) -> tuple[DecisionLifecycleFact, ...] | None:
        try:
            async with self._engine.connect() as connection:
                history = await _load_decision_history(connection, decision_id)
                return history or None
        except (SQLAlchemyError, ValueError, TypeError) as error:
            raise DecisionCommandReadUnavailable(
                "Decision lifecycle history read is unavailable"
            ) from error

    async def load_relationship_history(
        self,
    ) -> tuple[DecisionRelationshipHistoryFact, ...]:
        try:
            async with self._engine.connect() as connection:
                return await _load_empty_relationship_history(connection)
        except SQLAlchemyError as error:
            raise DecisionCommandReadUnavailable(
                "Decision relationship history read is unavailable"
            ) from error

    async def _insert_created_decision(
        self,
        connection: AsyncConnection,
        decision: InvestmentDecision,
    ) -> None:
        fact = decision.history[0]
        if not isinstance(fact, DecisionInitiated):
            raise ValueError("foundational creation requires DecisionInitiated")
        need = decision.need
        await connection.execute(
            insert(decision_needs).values(
                need_id=need.need_id.value,
                statement=need.statement,
                effective_at=need.effective_at,
                recorded_at=need.recorded_at,
                operation_id=need.operation_id.value,
                **actor_columns(need.actor_attribution),
                **trigger_columns(need.trigger),
                technical_provenance=technical_payload(need.technical_provenance),
            )
        )
        self._write_completed("need")

        await connection.execute(
            insert(investment_decisions).values(
                decision_id=decision.decision_id.value,
                need_id=decision.need_id.value,
                subject_statement=decision.subject.statement,
                scope_completeness=decision.scope.completeness.value,
                scope_portfolio_ids=sorted(
                    (identity.value for identity in decision.scope.portfolio_ids),
                    key=str,
                ),
                **_projection_values(decision),
            )
        )
        self._write_completed("projection")

        metadata = fact.metadata
        await connection.execute(
            insert(investment_decision_lifecycle_facts).values(
                fact_id=metadata.fact_id.value,
                decision_id=metadata.decision_id.value,
                lifecycle_sequence=metadata.sequence.value,
                decision_version=metadata.decision_version.value,
                fact_kind="decision_initiated",
                operation_id=metadata.operation_id.value,
                **actor_columns(metadata.actor_attribution),
                **trigger_columns(metadata.trigger),
                technical_provenance=technical_payload(metadata.technical_provenance),
                effective_at=metadata.effective_at,
                recorded_at=metadata.recorded_at,
                need_id=fact.need.need_id.value,
                subject_statement=fact.subject.statement,
                scope_completeness=fact.scope.completeness.value,
                scope_portfolio_ids=sorted(
                    (identity.value for identity in fact.scope.portfolio_ids),
                    key=str,
                ),
                continuity_determination=fact.continuity.determination.value,
                continuity_candidate_ids=sorted(
                    (
                        identity.value
                        for identity in fact.continuity.candidate_decision_ids
                    ),
                    key=str,
                ),
                continuity_known_at=fact.continuity.known_at,
                continuity_rationale=fact.continuity.rationale,
            )
        )
        self._write_completed("lifecycle_fact")

    def _write_completed(self, step: str) -> None:
        """Test seam for proving rollback between semantic writes."""

    async def _translate_write_failure(
        self,
        commit: InitiationCommit,
        error: SQLAlchemyError,
    ) -> InitiationCommitOutcome:
        del error
        try:
            async with self._engine.connect() as connection:
                prior = await _get_initiation_operation_receipt(
                    connection,
                    commit.operation_id,
                    for_update=False,
                )
            if prior is not None:
                return _receipt_outcome(prior, commit)
            if commit.decision is not None:
                existing = await self._decision_for_need(commit.decision.need_id.value)
                if existing is not None:
                    return InitiationNeedAlreadyGrounded(existing)
        except DecisionCommandReadUnavailable, SQLAlchemyError, ValueError, TypeError:
            pass
        return InitiationUnavailable("Decision initiation persistence is unavailable")

    async def _translate_mutation_failure(
        self,
        commit: DecisionMutationCommit,
        error: SQLAlchemyError,
    ) -> DecisionMutationCommitOutcome:
        del error
        try:
            async with self._engine.connect() as connection:
                prior_row = await _get_operation_receipt(
                    connection,
                    commit.operation_id,
                    # duplicate-code: operations require independent control flow.
                    # arid: disable
                )
            if prior_row is not None and (
                prior_row["command_kind"] != "decision_mutation"
            ):
                return DecisionMutationIdempotencyConflict(commit.operation_id)
            if prior_row is not None:
                prior = mutation_receipt_from_row(prior_row)
                return _mutation_receipt_outcome(prior, commit)
                # arid: enable
        except SQLAlchemyError, ValueError, TypeError:
            pass
        return DecisionMutationUnavailable(
            "Decision mutation persistence is unavailable"
        )

    async def _decision_for_need(self, need_id: object) -> InvestmentDecisionId | None:
        try:
            async with self._engine.connect() as connection:
                row = (
                    await connection.execute(
                        select(investment_decisions.c.decision_id).where(
                            investment_decisions.c.need_id == need_id
                        )
                    )
                ).one_or_none()
            return (
                InvestmentDecisionId(_domain_uuid(row.decision_id))
                if row is not None
                else None
            )
        except SQLAlchemyError as error:
            raise DecisionCommandReadUnavailable(
                "Decision Need grounding read is unavailable"
            ) from error


async def _get_receipt(
    connection: AsyncConnection,
    operation_id: OperationId,
    *,
    for_update: bool = False,
) -> InitiationReceipt | None:
    row = await _get_operation_receipt(
        connection,
        operation_id,
        for_update=for_update,
    )
    if row is None or row["command_kind"] != _INITIATION_COMMAND_KIND:
        return None
    return _initiation_receipt(row)


async def _get_initiation_operation_receipt(
    connection: AsyncConnection,
    operation_id: OperationId,
    *,
    for_update: bool,
) -> InitiationReceipt | InitiationIdempotencyConflict | None:
    # duplicate-code: operations require independent control flow.
    # arid: disable
    row = await _get_operation_receipt(
        connection,
        operation_id,
        for_update=for_update,
    )
    # arid: enable
    if row is None:
        return None
    if row["command_kind"] != _INITIATION_COMMAND_KIND:
        return InitiationIdempotencyConflict(operation_id)
    return _initiation_receipt(row)


def _initiation_receipt(row: RowMapping) -> InitiationReceipt:
    receipt = initiation_receipt_from_row(row)
    if row["request_fingerprint"] != request_fingerprint(receipt.request):
        raise ValueError("stored initiation receipt fingerprint is invalid")
    return receipt


async def _acquire_initiation_lock(connection: AsyncConnection) -> None:
    await connection.execute(
        text("SELECT pg_advisory_xact_lock(:lock_key)"),
        {"lock_key": _INITIATION_LOCK_KEY},
    )


async def _acquire_continuity_mutation_lock(
    connection: AsyncConnection,
    kind: DecisionMutationKind,
) -> None:
    if kind not in _CONTINUITY_NEUTRAL_MUTATIONS:
        await _acquire_initiation_lock(connection)


async def _get_mutation_receipt(
    connection: AsyncConnection,
    operation_id: OperationId,
    *,
    for_update: bool = False,
) -> DecisionMutationReceipt | None:
    # duplicate-code: operations require independent control flow.
    # arid: disable
    row = await _get_operation_receipt(
        connection,
        operation_id,
        for_update=for_update,
    )
    # arid: enable
    if row is None or row["command_kind"] != "decision_mutation":
        return None
    return mutation_receipt_from_row(row)


async def _get_operation_receipt(
    connection: AsyncConnection,
    operation_id: OperationId,
    *,
    for_update: bool = False,
) -> RowMapping | None:
    query = select(investment_decision_command_receipts).where(
        investment_decision_command_receipts.c.operation_id == operation_id.value
    )
    if for_update:
        query = query.with_for_update()
    return (await connection.execute(query)).mappings().one_or_none()


async def _continuity_knowledge_boundary(
    connection: AsyncConnection,
    *,
    minimum: datetime,
) -> datetime:
    # Revalidation advances only when durable history advances. Wall-clock passage
    # alone must not reinterpret the basis captured at ``minimum``.
    lifecycle_recorded_at = (
        await connection.execute(
            select(func.max(investment_decision_lifecycle_facts.c.recorded_at))
        )
    ).scalar_one()
    relationship_recorded_at = (
        await connection.execute(
            select(func.max(investment_decision_relationships.c.recorded_at))
        )
    ).scalar_one()
    return max(
        boundary
        for boundary in (minimum, lifecycle_recorded_at, relationship_recorded_at)
        if boundary is not None
    )


def _receipt_outcome(
    receipt: InitiationReceipt | InitiationIdempotencyConflict,
    commit: InitiationCommit,
) -> InitiationCommitOutcome:
    if isinstance(receipt, InitiationIdempotencyConflict):
        return receipt
    if receipt.request == commit.request:
        return InitiationReplayed(receipt)
    return InitiationIdempotencyConflict(commit.operation_id)


def _mutation_receipt_outcome(
    receipt: DecisionMutationReceipt,
    commit: DecisionMutationCommit,
) -> DecisionMutationCommitOutcome:
    if receipt.request == commit.request:
        return DecisionMutationReplayed(receipt)
    return DecisionMutationIdempotencyConflict(commit.operation_id)


def _mutation_fact(
    commit: DecisionMutationCommit,
) -> DecisionLifecycleFact | None:
    _validate_mutation_commit_identity(commit)
    if commit.result.kind is DecisionMutationResultKind.NO_OP:
        _validate_no_op_commit(commit)
        return None
    if commit.result.kind is not DecisionMutationResultKind.APPLIED:
        raise ValueError("unsupported Decision mutation result kind")
    history = commit.decision.history
    if len(history) < 2:
        raise ValueError("Decision mutation must append one lifecycle fact")
    fact = history[-1]
    if isinstance(fact, DecisionInitiated):
        raise ValueError("unsupported Decision mutation fact")
    if fact.metadata.operation_id != commit.operation_id:
        raise ValueError("Decision mutation fact operation does not match commit")
    if history[-2].metadata.fact_id != commit.expected_history_tail_fact_id:
        raise ValueError("Decision mutation history tail does not match commit guard")
    return fact


def _validate_mutation_commit_identity(commit: DecisionMutationCommit) -> None:
    if commit.request.expected_version != commit.expected_version:
        raise ValueError(
            "Decision mutation request version does not match commit guard"
        )
    if commit.request.decision_id != commit.decision.decision_id:
        raise ValueError("Decision mutation request identity does not match Decision")
    if commit.result.decision_id != commit.decision.decision_id:
        raise ValueError("Decision mutation result identity does not match Decision")
    if commit.result.version != commit.decision.version:
        raise ValueError("Decision mutation result version does not match Decision")


def _validate_no_op_commit(commit: DecisionMutationCommit) -> None:
    if commit.request.kind not in {
        DecisionMutationKind.REVISE_SUBJECT,
        DecisionMutationKind.ESTABLISH_OR_REVISE_SCOPE,
    }:
        raise ValueError("Decision mutation kind does not support semantic no-op")
    if commit.decision.version != commit.expected_version:
        raise ValueError("Decision no-op must preserve aggregate version")
    if (
        commit.decision.history[-1].metadata.fact_id
        != commit.expected_history_tail_fact_id
    ):
        raise ValueError("Decision no-op history tail does not match commit guard")


def _validate_created_commit(commit: InitiationCommit) -> None:
    decision = commit.decision
    assert decision is not None
    if commit.result.kind is not InitiationResultKind.CREATED:
        raise ValueError("created Decision requires CREATED result")
    if commit.result.decision_id != decision.decision_id:
        raise ValueError("result Decision identity must match created Decision")
    if commit.result.need_id != decision.need_id:
        raise ValueError("result Need identity must match created Decision")


def _validate_continued_commit(commit: InitiationCommit) -> None:
    if commit.result.kind is not InitiationResultKind.CONTINUED:
        raise ValueError(
            "continuation without Decision payload requires CONTINUED result"
        )
    if commit.result.need_id is not None:
        raise ValueError("continued initiation cannot create a Need")


def _projection_values(decision: InvestmentDecision) -> dict[str, object]:
    interpretation = decision.lifecycle_interpretation
    disposition = None
    support = []
    if isinstance(interpretation, DeterminateDecisionLifecycleInterpretation):
        disposition = interpretation.disposition.value
        support = sorted(
            (identity.value for identity in interpretation.support_fact_ids), key=str
        )
    elif isinstance(interpretation, ContestedDecisionLifecycleInterpretation):
        support = sorted(
            (identity.value for identity in interpretation.support_fact_ids), key=str
        )
    elif not isinstance(interpretation, NotYetEffectiveDecisionLifecycleInterpretation):
        raise TypeError("unsupported lifecycle interpretation")
    return {
        "lifecycle_interpretation_kind": interpretation.kind,
        "lifecycle_disposition": disposition,
        "lifecycle_effective_at": interpretation.effective_at,
        "lifecycle_known_at": interpretation.known_at,
        "lifecycle_support_fact_ids": support,
        "work_posture": (
            decision.work_posture.value if decision.work_posture is not None else None
        ),
        "applicability": DecisionApplicability.OPERATIVE.value,
        "decision_version": decision.version.value,
        "created_at": decision.created_at,
        "rebuild_required": False,
    }


def _mutation_projection_values(decision: InvestmentDecision) -> dict[str, object]:
    values = _projection_values(decision)
    values.pop("applicability")
    values.pop("created_at")
    values["subject_statement"] = decision.subject.statement
    values["scope_completeness"] = decision.scope.completeness.value
    values["scope_portfolio_ids"] = sorted(
        (identity.value for identity in decision.scope.portfolio_ids), key=str
    )
    return values


async def _load_decision_projection(
    connection: AsyncConnection,
    decision_id: InvestmentDecisionId,
) -> RowMapping | None:
    return (
        (
            await connection.execute(
                select(investment_decisions).where(
                    investment_decisions.c.decision_id == decision_id.value
                )
            )
        )
        .mappings()
        .one_or_none()
    )


async def _load_decision_history(
    connection: AsyncConnection,
    decision_id: InvestmentDecisionId,
) -> tuple[DecisionLifecycleFact, ...]:
    rows = (
        (
            await connection.execute(
                select(investment_decision_lifecycle_facts)
                .where(
                    investment_decision_lifecycle_facts.c.decision_id
                    == decision_id.value
                )
                .order_by(investment_decision_lifecycle_facts.c.lifecycle_sequence)
            )
        )
        .mappings()
        .all()
    )
    history: list[DecisionLifecycleFact] = []
    for row in rows:
        if row["fact_kind"] == "decision_initiated":
            need_row = (
                (
                    await connection.execute(
                        select(decision_needs).where(
                            decision_needs.c.need_id == row["need_id"]
                        )
                    )
                )
                .mappings()
                .one()
            )
            history.append(initiated_fact_from_rows(row, need_row))
        else:
            history.append(mutation_fact_from_row(row))
    return tuple(history)


async def _load_empty_relationship_history(
    connection: AsyncConnection,
) -> tuple[DecisionRelationshipHistoryFact, ...]:
    row = (
        await connection.execute(
            select(investment_decision_relationships.c.row_id).limit(1)
        )
    ).first()
    if row is not None:
        raise DecisionCommandReadUnavailable(
            "relationship reconstruction belongs to the relationship persistence stage"
        )
    return ()


def _validate_lifecycle_projection(
    projection: RowMapping,
    history: tuple[DecisionLifecycleFact, ...],
    relationships: tuple[DecisionRelationshipHistoryFact, ...],
) -> None:
    if not history:
        raise ValueError("Decision projection requires lifecycle history")
    authoritative_version = history[-1].metadata.decision_version
    decision_id = InvestmentDecisionId(_domain_uuid(projection["decision_id"]))
    observation_boundary = projection["lifecycle_known_at"]
    applicability = derive_relationship_applicability(
        decision_id,
        relationships,
        effective_at=observation_boundary,
        known_at=observation_boundary,
    )
    rebuilt = reconstruct_decision(
        history,
        observed_at=observation_boundary,
        applicability=applicability,
        decision_version=authoritative_version,
    )
    expected = _projection_values(rebuilt)
    expected["applicability"] = applicability.value
    scalar_fields = (
        "lifecycle_interpretation_kind",
        "lifecycle_disposition",
        "lifecycle_effective_at",
        "lifecycle_known_at",
        "work_posture",
        "applicability",
        "decision_version",
        "created_at",
        "rebuild_required",
    )
    scalar_drift = any(projection[field] != expected[field] for field in scalar_fields)
    identity_drift = (
        _domain_uuid(projection["decision_id"]) != rebuilt.decision_id.value
        or _domain_uuid(projection["need_id"]) != rebuilt.need_id.value
    )
    state_drift = (
        observation_boundary != history[-1].metadata.recorded_at
        or projection["subject_statement"] != rebuilt.subject.statement
        or projection["scope_completeness"] != rebuilt.scope.completeness.value
        or _uuid_values(projection["scope_portfolio_ids"])
        != frozenset(identity.value for identity in rebuilt.scope.portfolio_ids)
        or _uuid_values(projection["lifecycle_support_fact_ids"])
        != frozenset(
            identity.value
            for identity in rebuilt.lifecycle_interpretation.support_fact_ids
        )
    )
    if scalar_drift or identity_drift or state_drift:
        raise ValueError("stored Decision projection does not match lifecycle history")


def _uuid_values(value: object) -> frozenset[UUID]:
    if not isinstance(value, (list, tuple)):
        raise ValueError("database UUID collection is invalid")
    identities = frozenset(_domain_uuid(item) for item in value)
    if len(identities) != len(value):
        raise ValueError("database UUID collection contains duplicates")
    return identities


def _decision_version(value: object) -> DecisionVersion:
    if type(value) is not int:
        raise ValueError("decision_version must be an integer")
    return DecisionVersion(value)


def _domain_uuid(value: object) -> UUID:
    # duplicate-code: operations require independent control flow.
    # arid: disable
    if type(value) is UUID:
        return value
    if isinstance(value, UUID):
        return UUID(str(value))
    if isinstance(value, str):
        return UUID(value)
    # arid: enable
    raise ValueError("database UUID value is invalid")
