from __future__ import annotations

from dataclasses import dataclass

from application.evaluations.contracts import EvaluationDatasetRegistrationRequest
from core.storage.persistence.evaluation import EvaluationPersistenceRepository
from core.storage.persistence.evaluation import EvaluationDatasetRecord


@dataclass(frozen=True, slots=True)
class EvaluationDatasetService:
    """Register and load canonical evaluation dataset records."""

    repository: EvaluationPersistenceRepository

    async def register_dataset(
        self,
        request: EvaluationDatasetRegistrationRequest,
    ) -> EvaluationDatasetRecord:
        record = EvaluationDatasetRecord.from_reference(
            request.reference,
            target_type=request.target_type,
            description=request.description,
            source_lineage=request.source_lineage,
            deterministic_fixture_uri=request.deterministic_fixture_uri,
            threshold_profile=request.threshold_profile,
        )
        if record.active != request.active:
            record = EvaluationDatasetRecord(
                dataset_id=record.dataset_id,
                name=record.name,
                version=record.version,
                target_type=record.target_type,
                description=record.description,
                tags=record.tags,
                source_lineage=record.source_lineage,
                deterministic_fixture_uri=record.deterministic_fixture_uri,
                threshold_profile=record.threshold_profile,
                active=request.active,
                created_at=record.created_at,
                updated_at=record.updated_at,
            )
        return await self.repository.upsert_dataset(record)

    async def get_dataset(self, dataset_id: str) -> EvaluationDatasetRecord | None:
        return await self.repository.get_dataset(dataset_id)
