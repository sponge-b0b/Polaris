"""PostgreSQL reconstruction repository for Baseline runtime provenance."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.models.baseline_runtime_evidence import BaselineRuntimeEvidenceModel
from domain.authority import risk_authority_contract_from_metadata
from domain.governed_execution_evidence import BaselineRuntimeEvidence


class PostgresBaselineRuntimeEvidenceRepository:
    """Loads durable Baseline authority and provenance by its immutable ID."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, evidence_id: str) -> BaselineRuntimeEvidence | None:
        result = await self._session.execute(
            select(BaselineRuntimeEvidenceModel).where(
                BaselineRuntimeEvidenceModel.evidence_id == evidence_id,
            )
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return BaselineRuntimeEvidence(
            evidence_id=model.evidence_id,
            authority=risk_authority_contract_from_metadata(model.authority_metadata),
            workflow_name=model.workflow_name,
            workflow_version=model.workflow_version,
            provenance_digest=model.provenance_digest,
            schema_version=model.schema_version,
        )

    async def persist(self, evidence: BaselineRuntimeEvidence) -> None:
        """Store evidence supplied only by canonical orchestration."""

        self._session.add(
            BaselineRuntimeEvidenceModel(
                evidence_id=evidence.evidence_id,
                schema_version=evidence.schema_version,
                workflow_name=evidence.workflow_name,
                workflow_version=evidence.workflow_version,
                provenance_digest=evidence.provenance_digest,
                authority_metadata=evidence.authority.to_metadata(),
            )
        )
        await self._session.commit()
