from __future__ import annotations

from sqlalchemy import insert, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from polaris.application.evidence import EvidenceCommandReadUnavailable
from polaris.application.evidence.binding_contracts import (
    EvidenceBindingCommit,
    EvidenceBindingCommitOutcome,
    EvidenceBindingCommitted,
    EvidenceBindingIdempotencyConflict,
    EvidenceBindingObservationConflict,
    EvidenceBindingReceipt,
    EvidenceBindingReplayed,
    EvidenceBindingResult,
    EvidenceBindingUnavailable,
)
from polaris.domain.decisions import OperationId
from polaris.domain.evidence.bindings import EvidenceBinding
from polaris.domain.evidence.observations import EvidenceBindingId

from .binding_codec import (
    binding_from_row,
    binding_receipt_from_row,
    binding_request_fingerprint,
    binding_request_payload,
    binding_result_payload,
    binding_values,
)
from .runtime_qualification import require_qualified_postgres_runtime
from .schema import (
    evidence_binding_command_receipts,
    evidence_bindings,
    evidence_observations,
)
from .support_epochs import advance_support_epochs, support_scope

EVIDENCE_BINDING_WRITE_LOCK = 4_566_144_311_625_725_311


class PostgresEvidenceBindingStore:
    """PostgreSQL adapter for the inward-owned Evidence binding port."""

    def __init__(self, engine: AsyncEngine) -> None:
        require_qualified_postgres_runtime()
        self._engine = engine

    # duplicate-code: each aggregate adapter owns its read translation and
    # receipt codec; sharing this body would couple independent persistence ports.
    # arid: disable
    async def get_binding_receipt(
        self,
        operation_id: OperationId,
    ) -> EvidenceBindingReceipt | None:
        try:
            async with self._engine.connect() as connection:
                return await _get_receipt(connection, operation_id)
        except (SQLAlchemyError, ValueError, TypeError) as error:
            raise EvidenceCommandReadUnavailable(
                "Evidence binding receipt read is unavailable"
            ) from error

    # arid: enable

    # duplicate-code: binding-row reconstruction is independently owned from
    # observation/Decision reads despite similar SQLAlchemy scaffolding.
    # arid: disable
    async def load_binding(
        self,
        binding_id: EvidenceBindingId,
    ) -> EvidenceBinding | None:
        try:
            async with self._engine.connect() as connection:
                row = (
                    (
                        await connection.execute(
                            select(evidence_bindings).where(
                                evidence_bindings.c.binding_id == binding_id.value
                            )
                        )
                    )
                    .mappings()
                    .first()
                )
                return None if row is None else binding_from_row(row)
        except (SQLAlchemyError, ValueError, TypeError) as error:
            raise EvidenceCommandReadUnavailable(
                "Evidence binding read is unavailable"
            ) from error

    # arid: enable

    async def commit_binding(
        self,
        commit: EvidenceBindingCommit,
    ) -> EvidenceBindingCommitOutcome:
        # duplicate-code: the binding aggregate owns its transaction and lock
        # semantics; extracting shared transaction scaffolding would couple
        # independently evolvable Evidence aggregates.
        # arid: disable
        try:
            async with self._engine.begin() as connection:
                await connection.execute(
                    text("SELECT pg_advisory_xact_lock(:lock_key)"),
                    {"lock_key": EVIDENCE_BINDING_WRITE_LOCK},
                )
                # arid: enable
                prior = await _get_receipt(connection, commit.operation_id)
                if prior is not None:
                    if prior.request != commit.request:
                        return EvidenceBindingIdempotencyConflict(commit.operation_id)
                    return EvidenceBindingReplayed(prior)

                observation_exists = await connection.scalar(
                    select(evidence_observations.c.observation_id).where(
                        evidence_observations.c.observation_id
                        == commit.binding.observation_id.value
                    )
                )
                if observation_exists is None:
                    return EvidenceBindingObservationConflict(
                        commit.binding.observation_id
                    )

                values = binding_values(commit.binding)
                await connection.execute(insert(evidence_bindings).values(**values))
                self._write_completed("binding")
                await advance_support_epochs(
                    connection,
                    frozenset(
                        {
                            support_scope(
                                commit.binding.target,
                                commit.binding.scope,
                                commit.binding.evidence_use,
                            )
                        }
                    ),
                    source_column="binding_id",
                    source_id=commit.binding.binding_id.value,
                    effective_at=commit.binding.effective_at,
                    recorded_at=commit.binding.recorded_at,
                )
                self._write_completed("support_version")
                # duplicate-code: binding receipts are a distinct inward-owned
                # contract; a generic receipt factory would erase result typing.
                # arid: disable
                result = EvidenceBindingResult(commit.binding.binding_id)
                receipt = EvidenceBindingReceipt(
                    operation_id=commit.operation_id,
                    request=commit.request,
                    result=result,
                )
                # arid: enable
                # duplicate-code: each Evidence aggregate persists its own
                # immutable receipt schema and codec payload.
                # arid: disable
                await connection.execute(
                    insert(evidence_binding_command_receipts).values(
                        operation_id=commit.operation_id.value,
                        request_fingerprint=binding_request_fingerprint(commit.request),
                        request_payload=binding_request_payload(commit.request),
                        result_payload=binding_result_payload(result),
                        committed_at=commit.committed_at,
                    )
                )
                self._write_completed("receipt")
                # arid: enable
                return EvidenceBindingCommitted(receipt)
        except (SQLAlchemyError, ValueError, TypeError, RuntimeError) as error:
            return EvidenceBindingUnavailable(
                f"Evidence binding transaction failed: {type(error).__name__}"
            )

    def _write_completed(self, step: str) -> None:
        """Test seam for proving transaction rollback."""
        del step


async def _get_receipt(
    connection: AsyncConnection,
    operation_id: OperationId,
) -> EvidenceBindingReceipt | None:
    row = (
        (
            await connection.execute(
                select(evidence_binding_command_receipts).where(
                    evidence_binding_command_receipts.c.operation_id
                    == operation_id.value
                )
            )
        )
        .mappings()
        .first()
    )
    return None if row is None else binding_receipt_from_row(row)
