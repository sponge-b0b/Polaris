"""Durable reconstruction boundary for Baseline runtime provenance."""

from typing import Protocol

from domain.governed_execution_evidence import BaselineRuntimeEvidence


class BaselineRuntimeEvidenceNotFoundError(LookupError):
    """Raised when canonical Baseline runtime provenance is unavailable."""


class BaselineRuntimeEvidenceRepository(Protocol):
    async def get(self, evidence_id: str) -> BaselineRuntimeEvidence | None: ...

    async def persist(
        self,
        evidence: BaselineRuntimeEvidence,
        *,
        commit: bool = True,
    ) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...


class BaselineRuntimeEvidencePersistenceService:
    """Reconstructs the sole accepted Baseline execution-evidence variant."""

    def __init__(self, repository: BaselineRuntimeEvidenceRepository) -> None:
        self._repository = repository

    async def reconstruct(self, evidence_id: str) -> BaselineRuntimeEvidence:
        evidence = await self._repository.get(evidence_id)
        if evidence is None:
            raise BaselineRuntimeEvidenceNotFoundError(
                f"Baseline runtime evidence was not found: {evidence_id}"
            )
        return evidence

    async def persist(
        self,
        evidence: BaselineRuntimeEvidence,
        *,
        commit: bool = True,
    ) -> None:
        """Persist canonical orchestration-produced Baseline provenance."""

        await self._repository.persist(evidence, commit=commit)

    async def commit(self) -> None:
        await self._repository.commit()

    async def rollback(self) -> None:
        await self._repository.rollback()
