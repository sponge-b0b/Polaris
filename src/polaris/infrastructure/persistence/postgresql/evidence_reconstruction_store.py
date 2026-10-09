from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Table, select
from sqlalchemy.engine import RowMapping
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine
from sqlalchemy.sql.elements import ColumnElement

from polaris.application.evidence.contracts import EvidenceCommandReadUnavailable
from polaris.application.evidence.current_basis import (
    EvidenceHistoryIncomplete,
    EvidenceHistoryInvalid,
)
from polaris.application.evidence.reconstruction import EvidenceHistories
from polaris.domain.evidence import (
    BasisScopeKey,
    ClaimSpecificEvidenceScope,
    EvidenceBindingId,
    EvidenceJudgmentRef,
    EvidenceObservationId,
    EvidenceSufficiencyAssessmentId,
    evidence_judgment_family,
    evidence_scope_kind,
)

from .correction_store import (
    _load_assessment_history,
    _load_binding_history,
    _load_observation_history,
)
from .runtime_qualification import require_qualified_postgres_runtime
from .schema import (
    evidence_bindings,
    evidence_sufficiency_assessments,
)


def _required[FactT](value: FactT | None) -> FactT:
    if value is None:
        raise ValueError("Evidence root disappeared during historical read")
    return value


def _current_required[FactT](value: FactT | None) -> FactT:
    if value is None:
        raise EvidenceHistoryIncomplete("selected Evidence root disappeared")
    return value


def _scope_conditions(
    table: Table, key: BasisScopeKey
) -> tuple[ColumnElement[bool], ...]:
    claim_id = (
        key.scope.claim_id.value
        if type(key.scope) is ClaimSpecificEvidenceScope
        else None
    )
    return (
        table.c.target_family == evidence_judgment_family(key.target).value,
        table.c.target_id == key.target.value,
        table.c.scope_kind == evidence_scope_kind(key.scope).value,
        table.c.claim_id.is_(None)
        if claim_id is None
        else table.c.claim_id == claim_id,
        table.c.evidence_use == key.use.value,
    )


async def _binding_rows(
    connection: AsyncConnection, conditions: tuple[ColumnElement[bool], ...]
) -> tuple[RowMapping, ...]:
    return tuple(
        (
            await connection.execute(
                select(
                    evidence_bindings.c.binding_id,
                    evidence_bindings.c.observation_id,
                )
                .where(*conditions)
                .order_by(evidence_bindings.c.binding_id)
            )
        )
        .mappings()
        .all()
    )


async def _assessment_ids(
    connection: AsyncConnection, conditions: tuple[ColumnElement[bool], ...]
) -> tuple[UUID, ...]:
    return tuple(
        (
            await connection.execute(
                select(evidence_sufficiency_assessments.c.assessment_id)
                .where(*conditions)
                .order_by(evidence_sufficiency_assessments.c.assessment_id)
            )
        )
        .scalars()
        .all()
    )


class PostgresHistoricalEvidenceStore:
    """Read a complete target Evidence history from one database snapshot."""

    # This adapter owns its own runtime qualification and current snapshot boundary;
    # sharing another adapter or the historical read setup would couple independent
    # queries.
    # arid: disable
    def __init__(self, engine: AsyncEngine) -> None:
        require_qualified_postgres_runtime()
        self._engine = engine

    async def load_scope_histories(
        self, key: BasisScopeKey, *, at: datetime
    ) -> EvidenceHistories:
        """Attest the complete visible root universe for one current key."""
        try:
            async with self._engine.connect() as connection:
                await connection.exec_driver_sql(
                    "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"
                )
                binding_rows = await _binding_rows(
                    # arid: enable
                    connection,
                    (
                        *_scope_conditions(evidence_bindings, key),
                        evidence_bindings.c.recorded_at <= at,
                    ),
                )
                assessment_ids = await _assessment_ids(
                    connection,
                    (
                        *_scope_conditions(evidence_sufficiency_assessments, key),
                        evidence_sufficiency_assessments.c.recorded_at <= at,
                    ),
                )
                bindings = []
                for row in binding_rows:
                    bindings.append(
                        _current_required(
                            await _load_binding_history(
                                connection,
                                EvidenceBindingId(UUID(str(row["binding_id"]))),
                            )
                        )
                    )
                assessments = []
                for value in assessment_ids:
                    assessments.append(
                        _current_required(
                            await _load_assessment_history(
                                connection,
                                EvidenceSufficiencyAssessmentId(UUID(str(value))),
                            )
                        )
                    )
                pending = {row["observation_id"] for row in binding_rows}
                observations = {}
                while pending:
                    observation_id = pending.pop()
                    if observation_id in observations:
                        continue
                    history = await _load_observation_history(
                        connection, EvidenceObservationId(UUID(str(observation_id)))
                    )
                    if history is None:
                        raise EvidenceHistoryIncomplete(
                            "selected binding observation ancestry is missing"
                        )
                    observations[observation_id] = history
                    predecessor = history.root.supersedes_observation_id
                    if predecessor is not None:
                        pending.add(predecessor.value)
                return EvidenceHistories(
                    tuple(observations[key] for key in sorted(observations, key=str)),
                    tuple(bindings),
                    tuple(assessments),
                )
        except (ValueError, TypeError) as error:
            raise EvidenceHistoryInvalid(
                "current Evidence scope history is invalid"
            ) from error
        except SQLAlchemyError as error:
            raise EvidenceCommandReadUnavailable(
                "current Evidence scope read is unavailable"
            ) from error

    async def load_target_histories(
        self, target: EvidenceJudgmentRef
    ) -> EvidenceHistories:
        family = evidence_judgment_family(target).value
        try:
            async with self._engine.connect() as connection:
                await connection.exec_driver_sql(
                    "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"
                )
                binding_rows = await _binding_rows(
                    connection,
                    (
                        evidence_bindings.c.target_family == family,
                        evidence_bindings.c.target_id == target.value,
                    ),
                )
                assessment_rows = await _assessment_ids(
                    connection,
                    (
                        evidence_sufficiency_assessments.c.target_family == family,
                        evidence_sufficiency_assessments.c.target_id == target.value,
                    ),
                )
                bindings = []
                for row in binding_rows:
                    history = await _load_binding_history(
                        connection, EvidenceBindingId(UUID(str(row["binding_id"])))
                    )
                    bindings.append(_required(history))
                observations = []
                for value in sorted(
                    {row["observation_id"] for row in binding_rows}, key=str
                ):
                    history = await _load_observation_history(
                        connection, EvidenceObservationId(UUID(str(value)))
                    )
                    observations.append(_required(history))
                assessments = []
                for value in assessment_rows:
                    history = await _load_assessment_history(
                        connection, EvidenceSufficiencyAssessmentId(UUID(str(value)))
                    )
                    assessments.append(_required(history))
                return EvidenceHistories(
                    tuple(observations), tuple(bindings), tuple(assessments)
                )
        except (SQLAlchemyError, ValueError, TypeError) as error:
            raise EvidenceCommandReadUnavailable(
                "historical Evidence read is unavailable"
            ) from error
