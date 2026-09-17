"""Async PostgreSQL adapter for foundational Investment Decision persistence."""

from __future__ import annotations

import re
from datetime import datetime
from uuid import UUID

from sqlalchemy import insert, select, text
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
)
from polaris.domain.decisions.facts import DecisionLifecycleFact

from .codec import (
    actor_columns,
    initiated_fact_from_rows,
    initiation_receipt_from_row,
    initiation_request_payload,
    initiation_result_payload,
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


def create_postgres_engine(
    database_url: str,
    *,
    schema: str | None = None,
) -> AsyncEngine:
    """Create the async engine owned by the PostgreSQL adapter boundary."""
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

    async def commit_initiation(
        self, commit: InitiationCommit
    ) -> InitiationCommitOutcome:
        try:
            async with self._engine.begin() as connection:
                await connection.execute(
                    text("SELECT pg_advisory_xact_lock(:lock_key)"),
                    {"lock_key": _INITIATION_LOCK_KEY},
                )
                prior = await _get_receipt(
                    connection,
                    commit.operation_id,
                    for_update=True,
                )
                if prior is not None:
                    return _receipt_outcome(prior, commit)

                candidates = await _current_continuity_candidates(connection)
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
                        command_kind="initiate_decision",
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
        except (ValueError, TypeError, RuntimeError) as error:
            return InitiationUnavailable(
                f"Decision initiation transaction failed: {type(error).__name__}"
            )

    async def find_unresolved_continuity_candidates(
        self, *, known_at: datetime
    ) -> tuple[InvestmentDecisionId, ...]:
        if known_at.tzinfo is None or known_at.utcoffset() is None:
            raise ValueError("known_at must be timezone-aware")
        try:
            async with self._engine.connect() as connection:
                rows = await connection.execute(
                    select(investment_decisions.c.decision_id)
                    .where(
                        investment_decisions.c.created_at <= known_at,
                        investment_decisions.c.lifecycle_disposition == "unresolved",
                        investment_decisions.c.applicability == "operative",
                    )
                    .order_by(investment_decisions.c.decision_id)
                )
                return tuple(
                    InvestmentDecisionId(_domain_uuid(row.decision_id))
                    for row in rows.fetchall()
                )
        except SQLAlchemyError as error:
            raise DecisionCommandReadUnavailable(
                "Decision continuity candidate read is unavailable"
            ) from error

    async def load_current_decision_state(
        self,
        decision_id: InvestmentDecisionId,
        *,
        known_at: datetime,
    ) -> DecisionMemoryCurrentState | None:
        del known_at
        try:
            async with self._engine.connect() as raw_connection:
                connection = await raw_connection.execution_options(
                    isolation_level="REPEATABLE READ"
                )
                async with connection.begin():
                    projection = (
                        await connection.execute(
                            select(investment_decisions.c.decision_version).where(
                                investment_decisions.c.decision_id == decision_id.value
                            )
                        )
                    ).one_or_none()
                    if projection is None:
                        return None
                    history = await _load_decision_history(connection, decision_id)
                    relationships = await _load_empty_relationship_history(connection)
                    return DecisionMemoryCurrentState(
                        lifecycle_facts=history,
                        version=_decision_version(projection.decision_version),
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
            prior = await self.get_initiation_receipt(commit.operation_id)
            if prior is not None:
                return _receipt_outcome(prior, commit)
            if commit.decision is not None:
                existing = await self._decision_for_need(commit.decision.need_id.value)
                if existing is not None:
                    return InitiationNeedAlreadyGrounded(existing)
        except DecisionCommandReadUnavailable:
            pass
        return InitiationUnavailable("Decision initiation persistence is unavailable")

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
    query = select(investment_decision_command_receipts).where(
        investment_decision_command_receipts.c.operation_id == operation_id.value,
        investment_decision_command_receipts.c.command_kind == "initiate_decision",
    )
    if for_update:
        query = query.with_for_update()
    row = (await connection.execute(query)).mappings().one_or_none()
    return initiation_receipt_from_row(row) if row is not None else None


async def _current_continuity_candidates(
    connection: AsyncConnection,
) -> frozenset[InvestmentDecisionId]:
    rows = await connection.execute(
        select(investment_decisions.c.decision_id).where(
            investment_decisions.c.lifecycle_disposition == "unresolved",
            investment_decisions.c.applicability == "operative",
        )
    )
    return frozenset(
        InvestmentDecisionId(_domain_uuid(row.decision_id)) for row in rows.fetchall()
    )


def _receipt_outcome(
    receipt: InitiationReceipt,
    commit: InitiationCommit,
) -> InitiationCommitOutcome:
    if receipt.request == commit.request:
        return InitiationReplayed(receipt)
    return InitiationIdempotencyConflict(commit.operation_id)


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
        if row["fact_kind"] != "decision_initiated":
            raise ValueError("unsupported lifecycle fact in foundation adapter")
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


def _decision_version(value: object) -> DecisionVersion:
    if type(value) is not int:
        raise ValueError("decision_version must be an integer")
    return DecisionVersion(value)


def _domain_uuid(value: object) -> UUID:
    if type(value) is UUID:
        return value
    if isinstance(value, UUID):
        return UUID(str(value))
    if isinstance(value, str):
        return UUID(value)
    raise ValueError("database UUID value is invalid")
