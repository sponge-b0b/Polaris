from __future__ import annotations

from typing import Any, cast

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Executable

from core.database.models.decision_evidence import DecisionEvidencePacketModel
from core.storage.persistence.decision_evidence import (
    DecisionEvidencePacketPersistenceRepository,
    DecisionEvidencePacketPersistenceResult,
    DecisionEvidencePacketRecord,
)
from core.storage.persistence.serializers import (
    DecisionEvidencePacketPersistenceSerializer,
)


class PostgresDecisionEvidencePacketRepository(
    DecisionEvidencePacketPersistenceRepository,
):
    """PostgreSQL repository for decision evidence packet audit records."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def persist_packet_record(
        self,
        record: DecisionEvidencePacketRecord,
    ) -> DecisionEvidencePacketPersistenceResult:
        try:
            result = await self._session.execute(_upsert_packet_statement(record))
            await self._session.commit()
        except SQLAlchemyError as exc:
            await self._session.rollback()
            return DecisionEvidencePacketPersistenceResult.failed(
                str(exc),
                packet_id=record.packet_id,
            )

        return DecisionEvidencePacketPersistenceResult.succeeded(
            record.packet_id,
            records_persisted=_rowcount(cast(Any, result).rowcount),
        )

    async def get_packet_record(
        self,
        packet_id: str,
    ) -> DecisionEvidencePacketRecord | None:
        result = await self._session.execute(
            select(DecisionEvidencePacketModel).where(
                DecisionEvidencePacketModel.packet_id == packet_id,
            )
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return DecisionEvidencePacketPersistenceSerializer.record_from_model(model)


def _upsert_packet_statement(
    record: DecisionEvidencePacketRecord,
) -> Executable:
    values = DecisionEvidencePacketPersistenceSerializer.packet_values(record)
    stmt = insert(DecisionEvidencePacketModel).values(**values)
    update_values = {key: value for key, value in values.items() if key != "packet_id"}
    update_values["updated_at"] = func.now()
    return stmt.on_conflict_do_update(
        index_elements=["packet_id"],
        set_=update_values,
    )


def _rowcount(value: object) -> int:
    if isinstance(value, int):
        return value
    return 0


__all__ = ["PostgresDecisionEvidencePacketRepository"]
