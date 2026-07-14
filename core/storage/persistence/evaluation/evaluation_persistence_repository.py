from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from domain.evaluation import EvaluationTargetType
from core.storage.persistence.evaluation.evaluation_persistence_models import (
    EvaluationArtifactRecord,
)
from core.storage.persistence.evaluation.evaluation_persistence_models import (
    EvaluationCaseRecord,
)
from core.storage.persistence.evaluation.evaluation_persistence_models import (
    EvaluationDatasetRecord,
)
from core.storage.persistence.evaluation.evaluation_persistence_models import (
    EvaluationMetricResultRecord,
)
from core.storage.persistence.evaluation.evaluation_persistence_models import (
    EvaluationPersistenceBundle,
)
from core.storage.persistence.evaluation.evaluation_persistence_models import (
    EvaluationPersistenceResult,
)
from core.storage.persistence.evaluation.evaluation_persistence_models import (
    EvaluationRunRecord,
)


class EvaluationPersistenceRepository(Protocol):
    """Async repository contract for durable LLM evaluation records."""

    async def persist_evaluation_bundle(
        self,
        bundle: EvaluationPersistenceBundle,
    ) -> EvaluationPersistenceResult: ...

    async def upsert_dataset(
        self,
        record: EvaluationDatasetRecord,
    ) -> EvaluationDatasetRecord: ...

    async def upsert_case(
        self,
        record: EvaluationCaseRecord,
    ) -> EvaluationCaseRecord: ...

    async def upsert_run(
        self,
        record: EvaluationRunRecord,
    ) -> EvaluationRunRecord: ...

    async def upsert_metric_result(
        self,
        record: EvaluationMetricResultRecord,
    ) -> EvaluationMetricResultRecord: ...

    async def create_artifact(
        self,
        record: EvaluationArtifactRecord,
    ) -> EvaluationArtifactRecord: ...

    async def get_dataset(
        self,
        dataset_id: str,
    ) -> EvaluationDatasetRecord | None: ...

    async def get_case(
        self,
        case_id: str,
    ) -> EvaluationCaseRecord | None: ...

    async def get_run(
        self,
        run_id: str,
    ) -> EvaluationRunRecord | None: ...

    async def list_cases_by_dataset(
        self,
        dataset_id: str,
        *,
        limit: int | None = None,
    ) -> Sequence[EvaluationCaseRecord]: ...

    async def list_cases_by_target_type(
        self,
        target_type: EvaluationTargetType,
        *,
        limit: int | None = None,
    ) -> Sequence[EvaluationCaseRecord]: ...

    async def list_metric_results(
        self,
        run_id: str,
    ) -> Sequence[EvaluationMetricResultRecord]: ...

    async def list_artifacts(
        self,
        run_id: str,
    ) -> Sequence[EvaluationArtifactRecord]: ...
