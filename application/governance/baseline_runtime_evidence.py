"""Durable reconstruction boundary for Baseline runtime provenance."""

from typing import Protocol

from domain.governed_execution_evidence import BaselineRuntimeEvidence


class BaselineRuntimeEvidenceNotFoundError(LookupError):
    """Raised when canonical Baseline runtime provenance is unavailable."""


class BaselineRuntimeEvidenceRepository(Protocol):
    async def get(self, evidence_id: str) -> BaselineRuntimeEvidence | None: ...


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
