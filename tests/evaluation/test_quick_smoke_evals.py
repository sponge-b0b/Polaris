from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from application.evaluations import (
    EvaluationRunService,
    EvaluationRunServiceRequest,
    canonical_evaluation_dataset_definition_by_name,
)
from domain.evaluation import (
    EvaluationStatus,
    EvaluationTargetType,
    EvaluationThreshold,
)
from integration.providers.llm_evaluation import EvaluationMetricSpec
from tests.evaluation._helpers import (
    InMemoryEvaluationRepository,
    PassingEvaluationProvider,
    RecordingProjectionService,
    evaluation_case_from_row,
)

LoadJsonlFixture = Callable[[Path], tuple[dict[str, Any], ...]]

pytestmark = pytest.mark.eval_smoke


@pytest.mark.asyncio()
async def test_quick_smoke_eval_runs_without_live_judge_model(
    evaluation_fixture_dir: Path,
    load_jsonl_fixture: LoadJsonlFixture,
) -> None:
    dataset_definition = canonical_evaluation_dataset_definition_by_name(
        "golden_rag_questions"
    )
    row = load_jsonl_fixture(evaluation_fixture_dir / "golden_rag_questions.jsonl")[0]
    evaluation_case = evaluation_case_from_row(
        row,
        dataset=dataset_definition.reference,
    )
    repository = InMemoryEvaluationRepository()
    projection_service = RecordingProjectionService()
    service = EvaluationRunService(
        provider=PassingEvaluationProvider(score=0.91),
        repository=repository,
        projection_service=projection_service,
    )

    result = await service.run_evaluation(
        EvaluationRunServiceRequest(
            run_id="ci-smoke-rag-run-001",
            target_type=EvaluationTargetType.RAG_ANSWER,
            cases=(evaluation_case,),
            metrics=(
                EvaluationMetricSpec(
                    metric_name="faithfulness",
                    threshold=EvaluationThreshold("faithfulness", 0.80),
                ),
            ),
            evaluator_provider="deterministic_ci",
            evaluator_model="fixture_judge",
            dataset=dataset_definition.reference,
            timeout_seconds=5.0,
        )
    )

    assert result.run.status is EvaluationStatus.PASSED
    assert result.metric_result_count == 1
    assert result.persistence_result.datasets_written == 1
    assert result.persistence_result.cases_written == 1
    assert result.persistence_result.runs_written == 2
    assert result.persistence_result.metric_results_written == 1
    assert repository.runs[result.run.run_id].status is EvaluationStatus.PASSED
    assert projection_service.requests[0].run.run_id == result.run.run_id
