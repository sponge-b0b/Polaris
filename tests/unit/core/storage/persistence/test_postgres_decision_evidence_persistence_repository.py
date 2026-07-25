from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast

import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.models.decision_evidence import DecisionEvidencePacketModel
from core.storage.persistence.decision_evidence import DecisionEvidencePacketRecord
from core.storage.persistence.repositories import (
    PostgresDecisionEvidencePacketRepository,
)
from core.storage.persistence.serializers import (
    DecisionEvidencePacketPersistenceSerializer,
)
from domain.authority import RiskTier


@pytest.mark.asyncio
async def test_persist_packet_record_uses_idempotent_upsert() -> None:
    session = FakeAsyncSession(result=FakeExecuteResult(rowcount=1))
    repository = PostgresDecisionEvidencePacketRepository(cast(AsyncSession, session))

    result = await repository.persist_packet_record(_record())

    assert result.success is True
    assert result.records_persisted == 1
    assert session.committed is True
    assert session.rolled_back is False
    assert len(session.statements) == 1
    assert "ON CONFLICT" in str(session.statements[0])


@pytest.mark.asyncio
async def test_persist_packet_record_rolls_back_database_errors() -> None:
    session = FakeAsyncSession(error=SQLAlchemyError("database unavailable"))
    repository = PostgresDecisionEvidencePacketRepository(cast(AsyncSession, session))

    result = await repository.persist_packet_record(_record())

    assert result.success is False
    assert result.packet_id == "packet-1"
    assert session.committed is False
    assert session.rolled_back is True


@pytest.mark.asyncio
async def test_get_packet_record_rehydrates_model_values() -> None:
    record = _record()
    model = DecisionEvidencePacketModel(
        **DecisionEvidencePacketPersistenceSerializer.packet_values(record),
        created_at=datetime(2026, 7, 25, 13, tzinfo=UTC),
        updated_at=datetime(2026, 7, 25, 13, 5, tzinfo=UTC),
    )
    session = FakeAsyncSession(result=FakeExecuteResult(model=model))
    repository = PostgresDecisionEvidencePacketRepository(cast(AsyncSession, session))

    loaded = await repository.get_packet_record("packet-1")

    assert loaded is not None
    assert loaded.packet_id == record.packet_id
    assert loaded.output_id == record.output_id
    assert loaded.risk_tier is RiskTier.ENHANCED
    assert loaded.reconstruction_reference_ids == record.reconstruction_reference_ids


@pytest.mark.asyncio
async def test_get_packet_record_returns_none_when_absent() -> None:
    session = FakeAsyncSession(result=FakeExecuteResult(model=None))
    repository = PostgresDecisionEvidencePacketRepository(cast(AsyncSession, session))

    assert await repository.get_packet_record("missing-packet") is None


class FakeExecuteResult:
    def __init__(
        self,
        *,
        model: DecisionEvidencePacketModel | None = None,
        rowcount: int = 0,
    ) -> None:
        self._model = model
        self.rowcount = rowcount

    def scalar_one_or_none(self) -> DecisionEvidencePacketModel | None:
        return self._model


class FakeAsyncSession:
    def __init__(
        self,
        *,
        result: FakeExecuteResult | None = None,
        error: SQLAlchemyError | None = None,
    ) -> None:
        self.result = result or FakeExecuteResult(rowcount=1)
        self.error = error
        self.statements: list[Any] = []
        self.committed = False
        self.rolled_back = False

    async def execute(self, statement: Any) -> FakeExecuteResult:
        self.statements.append(statement)
        if self.error is not None:
            raise self.error
        return self.result

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


def _record() -> DecisionEvidencePacketRecord:
    return DecisionEvidencePacketRecord(
        packet_id="packet-1",
        output_id="strategy-decision-1",
        schema_version=1,
        risk_tier=RiskTier.ENHANCED,
        authority_metadata={
            "risk_tier": "enhanced",
            "authority_level": "operator_approval_required",
            "requires_decision_evidence": True,
            "profile_id": "enhanced_authority",
        },
        retention_metadata={
            "retain_until": "2031-07-25T00:00:00Z",
            "policy_id": "enhanced-provenance-5y",
            "legal_hold": False,
        },
        reconstruction_reference_ids=(
            "evidence-synthesis:completed-run",
            "evidence-synthesis:node-output",
        ),
        claim_audit=(
            {
                "claim_id": "claim-1",
                "text": "The synthesis selected a bullish strategy posture.",
                "material": True,
                "evidence": {
                    "supporting_evidence_ids": ("evidence-synthesis",),
                    "conflicting_evidence_ids": (),
                    "constraint_ids": (),
                    "uncertainty_ids": (),
                    "limitation_ids": (),
                },
            },
        ),
        evidence_references=(
            {
                "evidence_id": "evidence-synthesis",
                "kind": "workflow_node_output",
                "reconstruction_reference_ids": (
                    "evidence-synthesis:completed-run",
                    "evidence-synthesis:node-output",
                ),
                "summary": "Persisted strategy synthesis node output.",
                "source_of_truth": "runtime_evidence",
            },
        ),
        reconstruction_references=(
            {
                "reference_id": "evidence-synthesis:completed-run",
                "kind": "completed_workflow_run",
                "record_id": "morning_report:exec-1",
                "source_of_truth": "runtime_evidence",
                "snapshot_id": "run-1",
                "content_digest": None,
            },
            {
                "reference_id": "evidence-synthesis:node-output",
                "kind": "workflow_node_output",
                "record_id": "node-output-synthesis",
                "source_of_truth": "runtime_evidence",
                "snapshot_id": "morning_report:exec-1:strategy_synthesis_agent",
                "content_digest": "digest-1",
            },
        ),
    )
