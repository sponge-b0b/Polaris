from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Table, func, insert, select, text
from sqlalchemy.engine import RowMapping
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine
from sqlalchemy.sql import Executable

from polaris.application.evidence import EvidenceCommandReadUnavailable
from polaris.application.evidence.corrections import (
    EvidenceCorrectionCommit,
    EvidenceCorrectionCommitOutcome,
    EvidenceCorrectionCommitted,
    EvidenceCorrectionFamily,
    EvidenceCorrectionIdempotencyConflict,
    EvidenceCorrectionReceipt,
    EvidenceCorrectionReferenceConflict,
    EvidenceCorrectionReplayed,
    EvidenceCorrectionResult,
    EvidenceCorrectionUnavailable,
)
from polaris.domain.decisions import OperationId
from polaris.domain.evidence import (
    EvidenceObservationCorrection,
    EvidenceObservationCorrectionHistory,
    EvidenceObservationId,
    InvalidEvidenceCorrection,
    InvalidEvidenceCorrectionHistory,
)
from polaris.domain.evidence.bindings import EvidenceBinding

from .binding_codec import binding_from_row, binding_values
from .binding_store import EVIDENCE_BINDING_WRITE_LOCK
from .correction_codec import (
    correction_receipt_from_row,
    correction_request_fingerprint,
    correction_request_payload,
    correction_result_payload,
    correction_values,
    observation_correction_from_row,
)
from .evidence_codec import observation_from_row
from .runtime_qualification import require_qualified_postgres_runtime
from .schema import (
    evidence_bindings,
    evidence_correction_command_receipts,
    evidence_correction_identities,
    evidence_observation_command_receipts,
    evidence_observation_corrections,
    evidence_observations,
    evidence_support_versions,
)

EVIDENCE_CORRECTION_WRITE_LOCK = 4_566_144_311_625_725_313


class PostgresEvidenceCorrectionStore:
    """PostgreSQL adapter for typed append-only Evidence correction history."""

    def __init__(self, engine: AsyncEngine) -> None:
        require_qualified_postgres_runtime()
        self._engine = engine

    async def get_correction_receipt(
        self,
        operation_id: OperationId,
    ) -> EvidenceCorrectionReceipt | None:
        # duplicate-code: each adapter translates its own persisted receipt
        # failures into the corresponding inward-owned read contract.
        # arid: disable
        try:
            async with self._engine.connect() as connection:
                return await _get_receipt(connection, operation_id)
        except (SQLAlchemyError, ValueError, TypeError) as error:
            raise EvidenceCommandReadUnavailable(
                "Evidence correction receipt read is unavailable"
            ) from error
        # arid: enable

    async def commit_correction(
        self,
        commit: EvidenceCorrectionCommit,
    ) -> EvidenceCorrectionCommitOutcome:
        try:
            async with self._engine.begin() as connection:
                for lock_key in (
                    EVIDENCE_BINDING_WRITE_LOCK,
                    EVIDENCE_CORRECTION_WRITE_LOCK,
                ):
                    await connection.execute(
                        text("SELECT pg_advisory_xact_lock(:lock_key)"),
                        {"lock_key": lock_key},
                    )
                prior = await _get_receipt(connection, commit.operation_id)
                if prior is not None:
                    if prior.request != commit.request:
                        return EvidenceCorrectionIdempotencyConflict(
                            commit.operation_id
                        )
                    return EvidenceCorrectionReplayed(prior)
                conflict = await _validate_commit_history(connection, commit)
                if conflict is not None:
                    return conflict
                await connection.execute(
                    insert(evidence_correction_identities).values(
                        correction_id=commit.correction.correction_id.value,
                        family=EvidenceCorrectionFamily.OBSERVATION.value,
                    )
                )
                self._write_completed("identity")
                await connection.execute(
                    insert(evidence_observation_corrections).values(
                        **correction_values(commit.correction)
                    )
                )
                self._write_completed("correction")
                await _record_support_version_events(connection, commit)
                self._write_completed("support_version")
                result = EvidenceCorrectionResult(commit.correction.correction_id)
                receipt = EvidenceCorrectionReceipt(
                    commit.operation_id,
                    commit.request,
                    result,
                )
                # duplicate-code: correction receipts carry family identity and
                # correction payloads; sharing SQL with sufficiency couples tables.
                # arid: disable
                await connection.execute(
                    insert(evidence_correction_command_receipts).values(
                        operation_id=commit.operation_id.value,
                        family=EvidenceCorrectionFamily.OBSERVATION.value,
                        request_fingerprint=correction_request_fingerprint(
                            commit.request
                        ),
                        request_payload=correction_request_payload(commit.request),
                        result_payload=correction_result_payload(result),
                        committed_at=commit.committed_at,
                    )
                )
                # arid: enable
                self._write_completed("receipt")
                return EvidenceCorrectionCommitted(receipt)
        except (SQLAlchemyError, ValueError, TypeError, RuntimeError) as error:
            return EvidenceCorrectionUnavailable(
                f"Evidence correction transaction failed: {type(error).__name__}"
            )

    async def load_observation_history(
        self,
        root_id: EvidenceObservationId,
    ) -> EvidenceObservationCorrectionHistory | None:
        try:
            async with self._engine.connect() as connection:
                return await _load_observation_history(connection, root_id)
        except (SQLAlchemyError, ValueError, TypeError) as error:
            raise EvidenceCommandReadUnavailable(
                "Evidence observation correction history is unavailable"
            ) from error

    def _write_completed(self, step: str) -> None:
        """Test seam for proving transaction rollback."""
        del step


async def _validate_commit_history(
    connection: AsyncConnection,
    commit: EvidenceCorrectionCommit,
) -> EvidenceCorrectionReferenceConflict | None:
    correction = commit.correction
    history = await _load_observation_history(connection, correction.root_id)
    if history is None:
        return EvidenceCorrectionReferenceConflict(
            correction.root_id,
            correction.target,
            "Evidence correction root does not exist",
        )
    if correction.replacement is not None:
        predecessor = correction.replacement.supersedes_observation_id
        if predecessor is not None:
            # Root admission requires an existing predecessor; decreasing row
            # identities keep corrected succession chains earlier and acyclic.
            root_row = await _one_row(
                connection,
                select(evidence_observations.c.row_id).where(
                    evidence_observations.c.observation_id == correction.root_id.value
                ),
            )
            predecessor_row = await _one_row(
                connection,
                select(evidence_observations.c.row_id).where(
                    evidence_observations.c.observation_id == predecessor.value
                ),
            )
            if (
                root_row is None
                or predecessor_row is None
                or predecessor_row["row_id"] >= root_row["row_id"]
            ):
                return EvidenceCorrectionReferenceConflict(
                    correction.root_id,
                    correction.target,
                    "Evidence correction predecessor must be an earlier "
                    "observation root",
                )
    try:
        candidate = EvidenceObservationCorrectionHistory(
            history.root,
            history.root_recorded_at,
            (*history.corrections, correction),
        )
        candidate.interpret(
            effective_at=commit.committed_at,
            known_at=commit.committed_at,
        )
    except (InvalidEvidenceCorrection, InvalidEvidenceCorrectionHistory) as error:
        return EvidenceCorrectionReferenceConflict(
            correction.root_id,
            correction.target,
            str(error),
        )
    return None


async def _load_observation_history(
    connection: AsyncConnection,
    root_id: EvidenceObservationId,
) -> EvidenceObservationCorrectionHistory | None:
    row = await _one_row(
        connection,
        select(evidence_observations).where(
            evidence_observations.c.observation_id == root_id.value
        ),
    )
    if row is None:
        return None
    corrections = await _correction_rows(
        connection,
        evidence_observation_corrections,
        root_id.value,
    )
    receipt_rows = (
        (
            await connection.execute(
                select(evidence_observation_command_receipts.c.committed_at)
                .where(
                    evidence_observation_command_receipts.c.result_payload[
                        "observation_id"
                    ].astext
                    == str(root_id.value)
                )
                .limit(2)
            )
        )
        .mappings()
        .all()
    )
    if len(receipt_rows) != 1:
        raise ValueError("observation root requires one immutable commit receipt")
    root = observation_from_row(row)
    return EvidenceObservationCorrectionHistory(
        root,
        receipt_rows[0]["committed_at"],
        tuple(observation_correction_from_row(value) for value in corrections),
    )


async def _one_row(
    connection: AsyncConnection,
    statement: Executable,
) -> RowMapping | None:
    return (await connection.execute(statement)).mappings().first()


async def _correction_rows(
    connection: AsyncConnection,
    table: Table,
    root_id: UUID,
) -> tuple[RowMapping, ...]:
    rows = (
        (
            await connection.execute(
                select(table).where(table.c.root_id == root_id).order_by(table.c.row_id)
            )
        )
        .mappings()
        .all()
    )
    return tuple(rows)


async def _get_receipt(
    connection: AsyncConnection,
    operation_id: OperationId,
) -> EvidenceCorrectionReceipt | None:
    row = await _one_row(
        connection,
        select(evidence_correction_command_receipts).where(
            evidence_correction_command_receipts.c.operation_id == operation_id.value
        ),
    )
    if row is None:
        return None
    receipt = correction_receipt_from_row(row)
    if row["request_fingerprint"] != correction_request_fingerprint(receipt.request):
        raise ValueError("stored correction receipt fingerprint does not match")
    if row["family"] != receipt.request.family.value:
        raise ValueError("stored correction receipt family does not match")
    return receipt


type _SupportScope = tuple[str, UUID, str, UUID | None, str]


async def _record_support_version_events(
    connection: AsyncConnection,
    commit: EvidenceCorrectionCommit,
) -> None:
    correction = commit.correction
    if correction.effective_at > commit.committed_at:
        return
    scopes = await _affected_support_scopes(connection, correction, commit.committed_at)
    for scope in sorted(scopes, key=lambda value: tuple(map(str, value))):
        target_family, target_id, scope_kind, claim_id, evidence_use = scope
        predicates = (
            evidence_support_versions.c.target_family == target_family,
            evidence_support_versions.c.target_id == target_id,
            evidence_support_versions.c.scope_kind == scope_kind,
            (
                evidence_support_versions.c.claim_id.is_(None)
                if claim_id is None
                else evidence_support_versions.c.claim_id == claim_id
            ),
            evidence_support_versions.c.evidence_use == evidence_use,
        )
        current = await connection.scalar(
            select(func.max(evidence_support_versions.c.support_version)).where(
                *predicates
            )
        )
        await connection.execute(
            insert(evidence_support_versions).values(
                target_family=target_family,
                target_id=target_id,
                scope_kind=scope_kind,
                claim_id=claim_id,
                evidence_use=evidence_use,
                binding_id=None,
                correction_id=correction.correction_id.value,
                support_version=(current or 0) + 1,
                effective_at=correction.effective_at,
                recorded_at=commit.committed_at,
            )
        )


async def _affected_support_scopes(
    connection: AsyncConnection,
    correction: EvidenceObservationCorrection,
    committed_at: datetime,
) -> frozenset[_SupportScope]:
    rows = (
        (
            await connection.execute(
                select(evidence_bindings).where(
                    evidence_bindings.c.observation_id == correction.root_id.value,
                    evidence_bindings.c.effective_at <= committed_at,
                    evidence_bindings.c.recorded_at <= committed_at,
                )
            )
        )
        .mappings()
        .all()
    )
    return frozenset(_binding_scope(binding_from_row(row)) for row in rows)


def _binding_scope(binding: EvidenceBinding) -> _SupportScope:
    values = binding_values(binding)
    return (
        str(values["target_family"]),
        binding.target.value,
        str(values["scope_kind"]),
        values["claim_id"] if isinstance(values["claim_id"], UUID) else None,
        str(values["evidence_use"]),
    )


__all__ = ["EVIDENCE_CORRECTION_WRITE_LOCK", "PostgresEvidenceCorrectionStore"]
