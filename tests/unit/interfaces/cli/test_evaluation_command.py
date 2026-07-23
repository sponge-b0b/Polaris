from __future__ import annotations

from dataclasses import dataclass

from typer.testing import CliRunner

from application.evaluations import (
    EvaluationDatasetSeedItem,
    EvaluationDatasetSeedResult,
)
from interfaces.cli.app import create_app
from interfaces.cli.commands import evaluation_command
from interfaces.cli.services.evaluation_command_service import (
    EvaluationDatasetListItem,
    EvaluationDatasetsCommandResult,
    EvaluationDatasetSeedCommandResult,
    EvaluationResultsCommandResult,
    EvaluationRunCommandResult,
    EvaluationStatusCommandResult,
)


@dataclass(slots=True)
class FakeEvaluationCommandService:
    async def status(self) -> EvaluationStatusCommandResult:
        return EvaluationStatusCommandResult(
            enabled=True,
            configured=True,
            strict_mode=False,
            judge_provider="litellm",
            judge_model="qwen3.5:4b",
            default_threshold=0.7,
            max_concurrency=4,
            timeout_seconds=60.0,
            canonical_dataset_count=8,
            message="DeepEval evaluation is configured.",
        )

    async def list_datasets(self) -> EvaluationDatasetsCommandResult:
        return EvaluationDatasetsCommandResult(
            success=True,
            items=(
                EvaluationDatasetListItem(
                    name="golden_rag_questions",
                    dataset_id="golden_rag_questions_v1",
                    version="v1",
                    target_type="rag_answer",
                    description="Golden cases",
                    active=True,
                    persisted=True,
                    persisted_case_count=1,
                ),
            ),
        )

    async def seed_datasets(
        self,
        dataset_name: str | None = None,
        *,
        dry_run: bool = False,
    ) -> EvaluationDatasetSeedCommandResult:
        return EvaluationDatasetSeedCommandResult(
            success=True,
            seed_result=EvaluationDatasetSeedResult(
                dry_run=dry_run,
                items=(
                    EvaluationDatasetSeedItem(
                        name=dataset_name or "golden_rag_questions",
                        dataset_id="golden_rag_questions_v1",
                        fixture_uri="tests/evaluation/fixtures/golden_rag_questions.jsonl",
                        case_count=25,
                        persisted=not dry_run,
                    ),
                ),
                datasets_written=0 if dry_run else 1,
                cases_written=0 if dry_run else 25,
            ),
        )

    async def run_dataset(self, dataset_name: str) -> EvaluationRunCommandResult:
        return EvaluationRunCommandResult(
            success=dataset_name == "golden_rag_questions",
            message="Evaluation run completed.",
            error=None if dataset_name == "golden_rag_questions" else "missing dataset",
        )

    async def run_rag_case(self, case_id: str) -> EvaluationRunCommandResult:
        return EvaluationRunCommandResult(
            success=case_id == "case-1",
            message="Evaluation run completed.",
            error=None if case_id == "case-1" else "missing case",
        )

    async def run_latest_rag(self) -> EvaluationRunCommandResult:
        return EvaluationRunCommandResult(
            success=True,
            message="Evaluation run completed.",
        )

    async def results(self, run_id: str) -> EvaluationResultsCommandResult:
        return EvaluationResultsCommandResult(
            success=False,
            error=f"No evaluation run found for {run_id}.",
        )


def test_eval_status_command_renders_configuration(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        evaluation_command,
        "EvaluationCommandService",
        FakeEvaluationCommandService,
    )
    runner = CliRunner()

    result = runner.invoke(create_app(), ["eval", "status"])

    assert result.exit_code == 0
    assert "Polaris Evaluation Status" in result.output
    assert "Judge provider: litellm" in result.output


def test_eval_datasets_list_command_renders_datasets(monkeypatch) -> None:
    monkeypatch.setattr(
        evaluation_command,
        "EvaluationCommandService",
        FakeEvaluationCommandService,
    )
    runner = CliRunner()

    result = runner.invoke(create_app(), ["eval", "datasets", "list"])

    assert result.exit_code == 0
    assert "golden_rag_questions" in result.output
    assert "Cases: 1" in result.output


def test_eval_datasets_seed_command_supports_dry_run(monkeypatch) -> None:
    monkeypatch.setattr(
        evaluation_command,
        "EvaluationCommandService",
        FakeEvaluationCommandService,
    )
    runner = CliRunner()

    result = runner.invoke(
        create_app(),
        [
            "eval",
            "datasets",
            "seed",
            "--dataset",
            "golden_rag_questions",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert "Evaluation Dataset Seed" in result.output
    assert "Dry run: yes" in result.output
    assert "Cases: 25" in result.output


def test_eval_run_command_delegates_dataset_name(monkeypatch) -> None:
    monkeypatch.setattr(
        evaluation_command,
        "EvaluationCommandService",
        FakeEvaluationCommandService,
    )
    runner = CliRunner()

    result = runner.invoke(
        create_app(),
        ["eval", "run", "--dataset", "golden_rag_questions"],
    )

    assert result.exit_code == 0
    assert "Evaluation Run" in result.output
    assert "Status: succeeded" in result.output


def test_eval_run_rag_command_delegates_case_id(monkeypatch) -> None:
    monkeypatch.setattr(
        evaluation_command,
        "EvaluationCommandService",
        FakeEvaluationCommandService,
    )
    runner = CliRunner()

    result = runner.invoke(create_app(), ["eval", "run-rag", "--case", "case-1"])

    assert result.exit_code == 0
    assert "Status: succeeded" in result.output


def test_eval_results_command_exits_nonzero_when_run_missing(monkeypatch) -> None:
    monkeypatch.setattr(
        evaluation_command,
        "EvaluationCommandService",
        FakeEvaluationCommandService,
    )
    runner = CliRunner()

    result = runner.invoke(create_app(), ["eval", "results", "--run", "run-1"])

    assert result.exit_code == 1
    assert "No evaluation run found for run-1" in result.output
