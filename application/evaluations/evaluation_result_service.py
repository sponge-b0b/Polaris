from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from application.evaluations.contracts import EvaluationResultBundle
from core.storage.persistence.evaluation import (
    EvaluationCaseRecord,
    EvaluationDatasetRecord,
    EvaluationPersistenceRepository,
    EvaluationRunRecord,
)
from domain.evaluation import EvaluationTargetType


@dataclass(frozen=True, slots=True)
class EvaluationResultService:
    """Read persisted evaluation datasets, cases, runs, metrics, and artifacts."""

    repository: EvaluationPersistenceRepository

    async def get_dataset(self, dataset_id: str) -> EvaluationDatasetRecord | None:
        return await self.repository.get_dataset(dataset_id)

    async def get_case(self, case_id: str) -> EvaluationCaseRecord | None:
        return await self.repository.get_case(case_id)

    async def get_run(self, run_id: str) -> EvaluationRunRecord | None:
        return await self.repository.get_run(run_id)

    async def list_dataset_cases(
        self,
        dataset_id: str,
        *,
        limit: int | None = None,
    ) -> Sequence[EvaluationCaseRecord]:
        return await self.repository.list_cases_by_dataset(dataset_id, limit=limit)

    async def list_latest_cases(
        self,
        target_type: EvaluationTargetType,
        *,
        limit: int | None = None,
    ) -> Sequence[EvaluationCaseRecord]:
        return await self.repository.list_cases_by_target_type(
            target_type,
            limit=limit,
        )

    async def get_run_results(self, run_id: str) -> EvaluationResultBundle | None:
        run = await self.repository.get_run(run_id)
        if run is None:
            return None
        metric_results = await self.repository.list_metric_results(run_id)
        artifacts = await self.repository.list_artifacts(run_id)
        return EvaluationResultBundle(
            run=run,
            metric_results=tuple(metric_results),
            artifacts=tuple(artifacts),
        )
