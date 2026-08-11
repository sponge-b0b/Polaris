from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.models.governed_execution_evidence_selection import (
    GovernedExecutionEvidenceSelectionModel,
)
from core.storage.persistence.governed_execution_evidence import (
    GovernedExecutionEvidenceSelection,
    GovernedExecutionEvidenceSelectionConflictError,
)
from core.workflow.registry.workflow_registry import WorkflowIdentity
from domain.authority import RiskTier


class PostgresGovernedExecutionEvidenceSelectionRepository:
    """PostgreSQL system-of-record adapter for execution-scoped selections."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, selection: GovernedExecutionEvidenceSelection) -> None:
        self._session.add(
            GovernedExecutionEvidenceSelectionModel(
                execution_id=selection.execution_id,
                workflow_name=selection.identity.workflow_name,
                workflow_version=selection.identity.definition_fingerprint,
                risk_tier=selection.risk_tier.value,
                evidence_id=selection.evidence_id,
            )
        )
        try:
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise GovernedExecutionEvidenceSelectionConflictError(
                "Durable governed-evidence selection is not unique."
            ) from exc

    async def get(
        self, *, execution_id: str, identity: WorkflowIdentity
    ) -> tuple[GovernedExecutionEvidenceSelection, ...]:
        result = await self._session.execute(
            select(GovernedExecutionEvidenceSelectionModel).where(
                GovernedExecutionEvidenceSelectionModel.execution_id == execution_id,
                GovernedExecutionEvidenceSelectionModel.workflow_name
                == identity.workflow_name,
                GovernedExecutionEvidenceSelectionModel.workflow_version
                == identity.definition_fingerprint,
            )
        )
        return tuple(
            GovernedExecutionEvidenceSelection(
                execution_id=model.execution_id,
                identity=WorkflowIdentity(
                    workflow_name=model.workflow_name,
                    definition_fingerprint=model.workflow_version,
                ),
                risk_tier=RiskTier(model.risk_tier),
                evidence_id=model.evidence_id,
            )
            for model in result.scalars()
        )
