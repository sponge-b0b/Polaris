from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime

import pytest

from application.evaluations import EvaluationDatasetSeedItem
from application.evaluations import EvaluationDatasetSeedRequest
from application.evaluations import EvaluationDatasetSeedResult
from application.evaluations import EvaluationResultBundle
from application.evaluations import EvaluationRunServiceRequest
from application.evaluations import EvaluationRunServiceResult
from config.settings import Settings
from core.storage.persistence.evaluation import EvaluationCaseRecord
from core.storage.persistence.evaluation import EvaluationDatasetRecord
from core.storage.persistence.evaluation import EvaluationMetricResultRecord
from core.storage.persistence.evaluation import EvaluationPersistenceResult
from core.storage.persistence.evaluation import EvaluationRunRecord
from domain.evaluation import EvaluationMetricResult
from domain.evaluation import EvaluationRun
from domain.evaluation import EvaluationScore
from domain.evaluation import EvaluationStatus
from domain.evaluation import EvaluationTargetType
from interfaces.cli.services.evaluation_command_service import EvaluationCommandService
from interfaces.cli.services.evaluation_command_service import (
    render_evaluation_dataset_seed_result,
)
from interfaces.cli.services.evaluation_command_service import render_evaluation_results
from interfaces.cli.services.evaluation_command_service import render_evaluation_status


@dataclass(slots=True)
class FakeEvaluationResultService:
    datasets: dict[str, EvaluationDatasetRecord]
    cases: dict[str, EvaluationCaseRecord]
    bundles: dict[str, EvaluationResultBundle]

    async def get_dataset(self, dataset_id: str) -> EvaluationDatasetRecord | None:
        return self.datasets.get(dataset_id)

    async def get_case(self, case_id: str) -> EvaluationCaseRecord | None:
        return self.cases.get(case_id)

    async def get_run_results(self, run_id: str) -> EvaluationResultBundle | None:
        return self.bundles.get(run_id)

    async def list_dataset_cases(
        self,
        dataset_id: str,
        *,
        limit: int | None = None,
    ) -> Sequence[EvaluationCaseRecord]:
        cases = tuple(
            case for case in self.cases.values() if case.dataset_id == dataset_id
        )
        return cases if limit is None else cases[:limit]

    async def list_latest_cases(
        self,
        target_type: EvaluationTargetType,
        *,
        limit: int | None = None,
    ) -> Sequence[EvaluationCaseRecord]:
        cases = tuple(
            case for case in self.cases.values() if case.target_type is target_type
        )
        return cases if limit is None else cases[:limit]


@dataclass(slots=True)
class FakeEvaluationRunService:
    requests: list[EvaluationRunServiceRequest]

    async def run_evaluation(
        self,
        request: EvaluationRunServiceRequest,
    ) -> EvaluationRunServiceResult:
        self.requests.append(request)
        metric = request.metrics[0]
        return EvaluationRunServiceResult(
            run=EvaluationRun(
                run_id=request.run_id,
                target_type=request.target_type,
                status=EvaluationStatus.PASSED,
                evaluator_provider=request.evaluator_provider,
                evaluator_model=request.evaluator_model,
                dataset=request.dataset,
                case_ids=tuple(case.case_id for case in request.cases),
            ),
            metric_results=(
                EvaluationMetricResult(
                    run_id=request.run_id,
                    case_id=request.cases[0].case_id,
                    score=EvaluationScore(
                        metric_name=metric.metric_name,
                        score=0.91,
                        threshold=metric.threshold,
                        reason="grounded answer",
                    ),
                    status=EvaluationStatus.PASSED,
                    evaluator_provider=request.evaluator_provider,
                    evaluator_model=request.evaluator_model,
                ),
            ),
            persistence_result=EvaluationPersistenceResult(metric_results_written=1),
        )


@dataclass(slots=True)
class FakeEvaluationDatasetSeedService:
    requests: list[EvaluationDatasetSeedRequest]

    async def seed_canonical_datasets(
        self,
        request: EvaluationDatasetSeedRequest,
    ) -> EvaluationDatasetSeedResult:
        self.requests.append(request)
        return EvaluationDatasetSeedResult(
            dry_run=request.dry_run,
            items=(
                EvaluationDatasetSeedItem(
                    name=request.dataset_name or "golden_rag_questions",
                    dataset_id="golden_rag_questions_v1",
                    fixture_uri="tests/evaluation/fixtures/golden_rag_questions.jsonl",
                    case_count=25,
                    persisted=not request.dry_run,
                ),
            ),
            datasets_written=0 if request.dry_run else 1,
            cases_written=0 if request.dry_run else 25,
        )


def _settings() -> Settings:
    return Settings(
        DEEPEVAL_ENABLED=True,
        DEEPEVAL_JUDGE_PROVIDER="ollama",
        DEEPEVAL_JUDGE_MODEL="qwen3.5:4b",
    )


def _rag_case(case_id: str = "case-1") -> EvaluationCaseRecord:
    return EvaluationCaseRecord(
        case_id=case_id,
        dataset_id="golden_rag_questions_v1",
        target_type=EvaluationTargetType.RAG_ANSWER,
        input_text="What changed?",
        actual_output="The report cites stronger breadth.",
        rubric="Answer must be grounded in retrieved context.",
        retrieval_context=("breadth improved",),
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


@pytest.mark.asyncio
async def test_status_reports_deepeval_configuration() -> None:
    result = await EvaluationCommandService(settings=_settings()).status()

    assert result.configured is True
    rendered = render_evaluation_status(result)
    assert "Polaris Evaluation Status" in rendered
    assert "Judge provider: ollama" in rendered


@pytest.mark.asyncio
async def test_list_datasets_uses_result_service_and_marks_persisted() -> None:
    result_service = FakeEvaluationResultService(
        datasets={
            "golden_rag_questions_v1": EvaluationDatasetRecord(
                dataset_id="golden_rag_questions_v1",
                name="golden_rag_questions",
                version="v1",
                target_type=EvaluationTargetType.RAG_ANSWER,
            )
        },
        cases={"case-1": _rag_case()},
        bundles={},
    )

    result = await EvaluationCommandService(
        result_service=result_service,
        settings=_settings(),
    ).list_datasets()

    assert result.success is True
    golden = next(item for item in result.items if item.name == "golden_rag_questions")
    assert golden.persisted is True
    assert golden.persisted_case_count == 1


@pytest.mark.asyncio
async def test_seed_datasets_delegates_to_dataset_seed_service() -> None:
    seed_service = FakeEvaluationDatasetSeedService([])

    result = await EvaluationCommandService(
        dataset_seed_service=seed_service,
        settings=_settings(),
    ).seed_datasets("golden_rag_questions", dry_run=True)

    assert result.success is True
    assert seed_service.requests == [
        EvaluationDatasetSeedRequest(
            dataset_name="golden_rag_questions",
            dry_run=True,
        )
    ]
    rendered = render_evaluation_dataset_seed_result(result)
    assert "Evaluation Dataset Seed" in rendered
    assert "Dry run: yes" in rendered
    assert "Cases: 25" in rendered


@pytest.mark.asyncio
async def test_run_dataset_delegates_to_run_service_with_canonical_metrics() -> None:
    result_service = FakeEvaluationResultService(
        datasets={},
        cases={"case-1": _rag_case()},
        bundles={},
    )
    run_service = FakeEvaluationRunService([])

    result = await EvaluationCommandService(
        result_service=result_service,
        run_service=run_service,
        settings=_settings(),
    ).run_dataset("golden_rag_questions")

    assert result.success is True
    assert len(run_service.requests) == 1
    request = run_service.requests[0]
    assert request.dataset is not None
    assert request.dataset.name == "golden_rag_questions"
    assert request.target_type is EvaluationTargetType.RAG_ANSWER
    assert {metric.metric_name for metric in request.metrics} >= {
        "faithfulness",
        "citation_support",
    }


@pytest.mark.asyncio
async def test_run_rag_case_rejects_non_rag_case() -> None:
    result_service = FakeEvaluationResultService(
        datasets={},
        cases={
            "case-1": EvaluationCaseRecord(
                case_id="case-1",
                target_type=EvaluationTargetType.MORNING_REPORT,
                input_text="Prompt",
                actual_output="Output",
                rubric="Must be clear.",
            )
        },
        bundles={},
    )
    run_service = FakeEvaluationRunService([])

    result = await EvaluationCommandService(
        result_service=result_service,
        run_service=run_service,
        settings=_settings(),
    ).run_rag_case("case-1")

    assert result.success is False
    assert run_service.requests == []
    assert result.error is not None
    assert "morning_report" in result.error


@pytest.mark.asyncio
async def test_results_renderer_outputs_persisted_metrics() -> None:
    run = EvaluationRunRecord(
        run_id="run-1",
        target_type=EvaluationTargetType.RAG_ANSWER,
        status=EvaluationStatus.PASSED,
        evaluator_provider="deepeval",
        evaluator_model="qwen3.5:4b",
        dataset_id="golden_rag_questions_v1",
    )
    metric = EvaluationMetricResultRecord(
        metric_result_id="metric-1",
        run_id="run-1",
        case_id="case-1",
        metric_name="faithfulness",
        score=0.91,
        threshold=0.8,
        passed=True,
        reason="grounded",
        status=EvaluationStatus.PASSED,
        evaluator_provider="deepeval",
        evaluator_model="qwen3.5:4b",
    )
    result_service = FakeEvaluationResultService(
        datasets={},
        cases={},
        bundles={
            "run-1": EvaluationResultBundle(
                run=run,
                metric_results=(metric,),
                artifacts=(),
            )
        },
    )

    result = await EvaluationCommandService(
        result_service=result_service,
        settings=_settings(),
    ).results("run-1")

    rendered = render_evaluation_results(result)
    assert "Evaluation Results" in rendered
    assert "faithfulness" in rendered
    assert "score=0.91" in rendered
