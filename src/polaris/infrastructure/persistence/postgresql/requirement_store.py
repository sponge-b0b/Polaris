from __future__ import annotations

from collections import defaultdict

from sqlalchemy import insert, select, text
from sqlalchemy.engine import RowMapping
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from polaris.application.evidence import (
    EvidenceRequirementAppendOutcome,
    EvidenceRequirementHistoryRejected,
    EvidenceRequirementReadUnavailable,
    EvidenceRequirementStoreUnavailable,
    EvidenceRequirementVersionAppended,
    EvidenceRequirementVersionConflict,
)
from polaris.domain.configuration import (
    EvidenceRequirementSetVersion,
    EvidenceRequirementSetVersionId,
    InvalidEvidenceRequirementHistory,
    validate_requirement_history,
)

from .requirement_codec import (
    requirement_definition_values,
    requirement_version_from_rows,
    requirement_version_values,
)
from .runtime_qualification import require_qualified_postgres_runtime
from .schema import (
    evidence_requirement_definitions,
    evidence_requirement_set_versions,
)

EVIDENCE_REQUIREMENT_WRITE_LOCK = 4_566_144_311_625_725_310


class PostgresEvidenceRequirementStore:
    """PostgreSQL adapter for the inward Evidence-requirements contract."""

    # duplicate-code: each persistence adapter independently owns runtime
    # qualification and engine lifetime; a shared base would couple store contracts.
    # arid: disable
    def __init__(self, engine: AsyncEngine) -> None:
        require_qualified_postgres_runtime()
        self._engine = engine

    # arid: enable

    async def load_requirement_versions(
        self,
    ) -> tuple[EvidenceRequirementSetVersion, ...]:
        try:
            async with self._engine.connect() as connection:
                return await load_requirement_versions_from_connection(connection)
        except (SQLAlchemyError, ValueError, TypeError) as error:
            raise EvidenceRequirementReadUnavailable(
                "Evidence requirement authority read is unavailable"
            ) from error

    async def append_requirement_version(
        self,
        version: EvidenceRequirementSetVersion,
    ) -> EvidenceRequirementAppendOutcome:
        # duplicate-code: this transaction's lock protects requirement-history
        # validation; sharing another command's transaction would couple invariants.
        # arid: disable
        try:
            async with self._engine.begin() as connection:
                await connection.execute(
                    text("SELECT pg_advisory_xact_lock(:lock_key)"),
                    {"lock_key": EVIDENCE_REQUIREMENT_WRITE_LOCK},
                )
                existing = await _load_version(connection, version.version_id)
                if existing is not None:
                    if existing == version:
                        return EvidenceRequirementVersionAppended(existing)
                    return EvidenceRequirementVersionConflict(version.version_id)
                # arid: enable

                history = await load_requirement_versions_from_connection(connection)
                try:
                    validate_requirement_history((*history, version))
                except InvalidEvidenceRequirementHistory as error:
                    return EvidenceRequirementHistoryRejected(str(error))

                await connection.execute(
                    insert(evidence_requirement_set_versions).values(
                        **requirement_version_values(version)
                    )
                )
                self._write_completed("version")
                definition_rows = requirement_definition_values(version)
                if definition_rows:
                    await connection.execute(
                        insert(evidence_requirement_definitions), definition_rows
                    )
                self._write_completed("definitions")
                return EvidenceRequirementVersionAppended(version)
        except (SQLAlchemyError, ValueError, TypeError, RuntimeError) as error:
            return EvidenceRequirementStoreUnavailable(
                f"Evidence requirement transaction failed: {type(error).__name__}"
            )

    def _write_completed(self, step: str) -> None:
        """Test seam for proving transaction rollback."""
        del step


async def load_requirement_versions_from_connection(
    connection: AsyncConnection,
) -> tuple[EvidenceRequirementSetVersion, ...]:
    version_rows = (
        (
            await connection.execute(
                select(evidence_requirement_set_versions).order_by(
                    evidence_requirement_set_versions.c.row_id
                )
            )
        )
        .mappings()
        .all()
    )
    definition_rows = (
        (
            await connection.execute(
                select(evidence_requirement_definitions).order_by(
                    evidence_requirement_definitions.c.row_id
                )
            )
        )
        .mappings()
        .all()
    )
    by_version: defaultdict[object, list[RowMapping]] = defaultdict(list)
    for row in definition_rows:
        by_version[row["version_id"]].append(row)
    return tuple(
        requirement_version_from_rows(
            row,
            tuple(by_version[row["version_id"]]),
        )
        for row in version_rows
    )


async def _load_version(
    connection: AsyncConnection,
    version_id: EvidenceRequirementSetVersionId,
) -> EvidenceRequirementSetVersion | None:
    row = (
        (
            await connection.execute(
                select(evidence_requirement_set_versions).where(
                    evidence_requirement_set_versions.c.version_id == version_id.value
                )
            )
        )
        .mappings()
        .first()
    )
    if row is None:
        return None
    definitions = (
        (
            await connection.execute(
                select(evidence_requirement_definitions).where(
                    evidence_requirement_definitions.c.version_id == version_id.value
                )
            )
        )
        .mappings()
        .all()
    )
    return requirement_version_from_rows(row, tuple(definitions))
