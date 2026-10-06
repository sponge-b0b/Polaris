from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine

from polaris.application.evidence.contracts import EvidenceCommandReadUnavailable
from polaris.application.evidence.reconstruction import EvidenceHistories
from polaris.domain.evidence import (
    EvidenceBindingId,
    EvidenceJudgmentRef,
    EvidenceObservationId,
    EvidenceSufficiencyAssessmentId,
    evidence_judgment_family,
)

from .correction_store import (
    _load_assessment_history,
    _load_binding_history,
    _load_observation_history,
)
from .runtime_qualification import require_qualified_postgres_runtime
from .schema import evidence_bindings, evidence_sufficiency_assessments


def _required[FactT](value: FactT | None) -> FactT:
    if value is None:
        raise ValueError("Evidence root disappeared during historical read")
    return value


class PostgresHistoricalEvidenceStore:
    """Read a complete target Evidence history from one database snapshot."""

    def __init__(self, engine: AsyncEngine) -> None:
        require_qualified_postgres_runtime()
        self._engine = engine

    async def load_target_histories(
        self, target: EvidenceJudgmentRef
    ) -> EvidenceHistories:
        family = evidence_judgment_family(target).value
        try:
            async with self._engine.connect() as connection:
                await connection.exec_driver_sql(
                    "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"
                )
                binding_rows = (
                    (
                        await connection.execute(
                            select(
                                evidence_bindings.c.binding_id,
                                evidence_bindings.c.observation_id,
                            )
                            .where(
                                evidence_bindings.c.target_family == family,
                                evidence_bindings.c.target_id == target.value,
                            )
                            .order_by(evidence_bindings.c.binding_id)
                        )
                    )
                    .mappings()
                    .all()
                )
                assessment_rows = (
                    (
                        await connection.execute(
                            select(evidence_sufficiency_assessments.c.assessment_id)
                            .where(
                                evidence_sufficiency_assessments.c.target_family
                                == family,
                                evidence_sufficiency_assessments.c.target_id
                                == target.value,
                            )
                            .order_by(evidence_sufficiency_assessments.c.assessment_id)
                        )
                    )
                    .scalars()
                    .all()
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
