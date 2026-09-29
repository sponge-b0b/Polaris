from __future__ import annotations

from sqlalchemy import insert, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from polaris.application.evidence import (
    EvidenceCommandReadUnavailable,
    EvidenceObservationCommit,
    EvidenceObservationCommitted,
    EvidenceObservationCommitOutcome,
    EvidenceObservationIdempotencyConflict,
    EvidenceObservationReceipt,
    EvidenceObservationReplayed,
    EvidenceObservationResult,
    EvidenceObservationSuccessionConflict,
    EvidenceObservationUnavailable,
)
from polaris.domain.decisions import OperationId
from polaris.domain.evidence import EvidenceObservation, EvidenceObservationId

from .evidence_codec import (
    observation_from_row,
    observation_receipt_from_row,
    observation_request_fingerprint,
    observation_request_payload,
    observation_result_payload,
    observation_values,
)
from .runtime_qualification import require_qualified_postgres_runtime
from .schema import evidence_observation_command_receipts, evidence_observations

_EVIDENCE_OBSERVATION_WRITE_LOCK = 4_566_144_311_625_725_309


class PostgresEvidenceStore:
    """PostgreSQL adapter for the inward-owned Evidence observation port."""

    def __init__(self, engine: AsyncEngine) -> None:
        require_qualified_postgres_runtime()
        self._engine = engine

    async def get_observation_receipt(
        self, operation_id: OperationId
    ) -> EvidenceObservationReceipt | None:
        try:
            async with self._engine.connect() as connection:
                return await _get_receipt(connection, operation_id)
        except (SQLAlchemyError, ValueError, TypeError) as error:
            raise EvidenceCommandReadUnavailable(
                "Evidence observation receipt read is unavailable"
            ) from error

    async def load_observation(
        self, observation_id: EvidenceObservationId
    ) -> EvidenceObservation | None:
        try:
            async with self._engine.connect() as connection:
                row = (
                    await connection.execute(
                        select(evidence_observations).where(
                            evidence_observations.c.observation_id
                            == observation_id.value
                        )
                    )
                ).mappings().first()
                return observation_from_row(row) if row is not None else None
        except (SQLAlchemyError, ValueError, TypeError) as error:
            raise EvidenceCommandReadUnavailable(
                "Evidence observation read is unavailable"
            ) from error

    async def commit_observation(
        self, commit: EvidenceObservationCommit
    ) -> EvidenceObservationCommitOutcome:
        try:
            async with self._engine.begin() as connection:
                await connection.execute(
                    select(
                        text(
                            f"pg_advisory_xact_lock({_EVIDENCE_OBSERVATION_WRITE_LOCK})"
                        )
                    )
                )
                prior = await _get_receipt(
                    connection, commit.operation_id, for_update=True
                )
                if prior is not None:
                    return _receipt_outcome(prior, commit)

                predecessor = commit.observation.supersedes_observation_id
                if predecessor is not None and not await _observation_exists(
                    connection, predecessor
                ):
                    return EvidenceObservationSuccessionConflict(predecessor)

                await connection.execute(
                    insert(evidence_observations).values(
                        **observation_values(commit.observation)
                    )
                )
                self._write_completed("observation")

                result = EvidenceObservationResult(commit.observation.observation_id)
                receipt = EvidenceObservationReceipt(
                    operation_id=commit.operation_id,
                    request=commit.request,
                    result=result,
                )
                await connection.execute(
                    insert(evidence_observation_command_receipts).values(
                        operation_id=commit.operation_id.value,
                        request_fingerprint=observation_request_fingerprint(
                            commit.request
                        ),
                        request_payload=observation_request_payload(commit.request),
                        result_payload=observation_result_payload(result),
                        committed_at=commit.committed_at,
                    )
                )
                self._write_completed("receipt")
                return EvidenceObservationCommitted(receipt)
        except SQLAlchemyError as error:
            return EvidenceObservationUnavailable(
                f"Evidence observation transaction failed: {type(error).__name__}"
            )
        except (ValueError, TypeError, RuntimeError) as error:
            return EvidenceObservationUnavailable(
                f"Evidence observation transaction failed: {type(error).__name__}"
            )

    def _write_completed(self, step: str) -> None:
        """Test seam for proving transaction rollback."""
        del step


async def _get_receipt(
    connection: AsyncConnection,
    operation_id: OperationId,
    *,
    for_update: bool = False,
) -> EvidenceObservationReceipt | None:
    statement = select(evidence_observation_command_receipts).where(
        evidence_observation_command_receipts.c.operation_id == operation_id.value
    )
    if for_update:
        statement = statement.with_for_update()
    row = (await connection.execute(statement)).mappings().first()
    return observation_receipt_from_row(row) if row is not None else None


async def _observation_exists(
    connection: AsyncConnection,
    observation_id: EvidenceObservationId,
) -> bool:
    return (
        await connection.scalar(
            select(evidence_observations.c.observation_id)
            .where(
                evidence_observations.c.observation_id == observation_id.value
            )
            .limit(1)
        )
    ) is not None


def _receipt_outcome(
    receipt: EvidenceObservationReceipt,
    commit: EvidenceObservationCommit,
) -> EvidenceObservationReplayed | EvidenceObservationIdempotencyConflict:
    if receipt.request != commit.request:
        return EvidenceObservationIdempotencyConflict(commit.operation_id)
    return EvidenceObservationReplayed(receipt)
