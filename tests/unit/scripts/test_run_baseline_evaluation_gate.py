from __future__ import annotations

from types import SimpleNamespace

import pytest

from scripts.run_baseline_evaluation_gate import ReleaseGateOptions
from scripts.run_baseline_evaluation_gate import run_release_gate


class FakeEvaluationGateService:
    def __init__(
        self,
        *,
        expected_counts: dict[str, int],
        persisted_counts: dict[str, int],
        run_statuses: dict[str, str] | None = None,
    ) -> None:
        self._expected_counts = expected_counts
        self._persisted_counts = persisted_counts
        self._run_statuses = run_statuses or {}
        self.seed_calls: list[tuple[str | None, bool]] = []

    async def status(self) -> SimpleNamespace:
        return SimpleNamespace(
            enabled=True,
            configured=True,
            message="DeepEval evaluation is configured.",
        )

    async def seed_datasets(
        self,
        dataset_name: str | None = None,
        *,
        dry_run: bool = False,
    ) -> SimpleNamespace:
        self.seed_calls.append((dataset_name, dry_run))
        if dataset_name is None:
            raise AssertionError("tests pass selected datasets explicitly")
        return SimpleNamespace(
            success=True,
            seed_result=SimpleNamespace(
                items=(
                    SimpleNamespace(
                        name=dataset_name,
                        dataset_id=f"{dataset_name}_v1",
                        case_count=self._expected_counts[dataset_name],
                    ),
                ),
                case_count=self._expected_counts[dataset_name],
            ),
            error=None,
        )

    async def list_datasets(self) -> SimpleNamespace:
        return SimpleNamespace(
            success=True,
            items=tuple(
                SimpleNamespace(
                    name=name,
                    persisted=True,
                    persisted_case_count=count,
                )
                for name, count in self._persisted_counts.items()
            ),
            error=None,
        )

    async def run_dataset(self, dataset_name: str) -> SimpleNamespace:
        status = self._run_statuses.get(dataset_name, "passed")
        return SimpleNamespace(
            success=True,
            run_id=f"run-{dataset_name}",
            run_status=status,
            error=None,
        )


@pytest.mark.asyncio
async def test_release_gate_passes_matching_counts_and_live_run() -> None:
    service = FakeEvaluationGateService(
        expected_counts={"agent_task_completion": 4},
        persisted_counts={"agent_task_completion": 4},
        run_statuses={"agent_task_completion": "passed"},
    )

    exit_code = await run_release_gate(
        ReleaseGateOptions(datasets=("agent_task_completion",)),
        evaluation_service=service,
    )

    assert exit_code == 0
    assert service.seed_calls == [
        ("agent_task_completion", True),
        ("agent_task_completion", False),
    ]


@pytest.mark.asyncio
async def test_release_gate_fails_on_persisted_count_mismatch() -> None:
    service = FakeEvaluationGateService(
        expected_counts={"golden_rag_questions": 25},
        persisted_counts={"golden_rag_questions": 26},
    )

    exit_code = await run_release_gate(
        ReleaseGateOptions(
            datasets=("golden_rag_questions",),
            skip_live_evaluation=True,
        ),
        evaluation_service=service,
    )

    assert exit_code == 1


@pytest.mark.asyncio
async def test_release_gate_fails_on_failed_live_run() -> None:
    service = FakeEvaluationGateService(
        expected_counts={"agent_task_completion": 4},
        persisted_counts={"agent_task_completion": 4},
        run_statuses={"agent_task_completion": "failed"},
    )

    exit_code = await run_release_gate(
        ReleaseGateOptions(datasets=("agent_task_completion",)),
        evaluation_service=service,
    )

    assert exit_code == 1


@pytest.mark.asyncio
async def test_release_gate_can_skip_seed_writes() -> None:
    service = FakeEvaluationGateService(
        expected_counts={"mcp_tool_responses": 4},
        persisted_counts={"mcp_tool_responses": 4},
    )

    exit_code = await run_release_gate(
        ReleaseGateOptions(
            datasets=("mcp_tool_responses",),
            skip_seed=True,
            skip_live_evaluation=True,
        ),
        evaluation_service=service,
    )

    assert exit_code == 0
    assert service.seed_calls == [("mcp_tool_responses", True)]
