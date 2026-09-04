from __future__ import annotations

from abc import ABC, abstractmethod

from .decision_evidence_persistence_models import (
    DecisionEvidencePacketPersistenceResult,
    DecisionEvidencePacketRecord,
)


class DecisionEvidencePacketPersistenceRepository(ABC):
    """Persistence contract for canonical decision evidence packet audit records."""

    @abstractmethod
    async def persist_packet_record(
        self,
        record: DecisionEvidencePacketRecord,
    ) -> DecisionEvidencePacketPersistenceResult:
        raise NotImplementedError

    @abstractmethod
    async def get_packet_record(
        self,
        packet_id: str,
    ) -> DecisionEvidencePacketRecord | None:
        raise NotImplementedError
