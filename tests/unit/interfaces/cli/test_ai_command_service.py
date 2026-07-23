from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime

import pytest

from application.ai_optimization import (
    AiOptimizationRequest,
    AiOptimizationResult,
    AiOptimizationStatus,
    AiOptimizationTarget,
)
from application.evaluations import EvaluationRunServiceResult
from config.settings import Settings
from core.storage.persistence.ai_artifacts import (
    AiArtifactApprovalStatus,
    AiArtifactType,
    AiPromptProgramArtifactRecord,
)
from core.storage.persistence.evaluation import EvaluationPersistenceResult
from domain.evaluation import (
    EvaluationMetricResult,
    EvaluationRun,
    EvaluationScore,
    EvaluationStatus,
    EvaluationTargetType,
)
from integration.providers.ai_optimization import (
    DspyOptimizationProviderResult,
    DspyOptimizedArtifact,
    DspyOptimizedCaseOutput,
)
from interfaces.cli.services.ai_command_service import (
    AiCommandService,
    render_ai_artifact_command_result,
    render_ai_artifacts,
    render_ai_optimize_result,
)


@dataclass(slots=True)
class FakeOptimizationService:
    requests: list[AiOptimizationRequest]

    async def optimize(self, request: AiOptimizationRequest) -> AiOptimizationResult:
        self.requests.append(request)
        target = (
            request.target
            if isinstance(request.target, AiOptimizationTarget)
            else AiOptimizationTarget(request.target)
        )
        artifact = _artifact(
            artifact_id="artifact-generated",
            approval_status=AiArtifactApprovalStatus.DRAFT,
            active=False,
            target_component=target.value,
            evaluation_dataset_id=request.dataset_id,
            evaluation_run_id=f"{request.optimization_id}-evaluation",
        )
        return AiOptimizationResult(
            optimization_id=request.optimization_id,
            target=target,
            status=AiOptimizationStatus.SUCCEEDED,
            evaluation_result=_evaluation_result(
                f"{request.optimization_id}-evaluation"
            ),
            provider_result=_provider_result(request.optimization_id),
            artifact=artifact,
        )


@dataclass(slots=True)
class FakeArtifactRepository:
    records: dict[str, AiPromptProgramArtifactRecord]
    deactivated_ids: list[str]
    upserts: list[AiPromptProgramArtifactRecord]

    async def upsert_artifact(
        self,
        record: AiPromptProgramArtifactRecord,
    ) -> AiPromptProgramArtifactRecord:
        self.records[record.artifact_id] = record
        self.upserts.append(record)
        return record

    async def get_artifact(
        self,
        artifact_id: str,
    ) -> AiPromptProgramArtifactRecord | None:
        return self.records.get(artifact_id)

    async def list_artifacts(
        self,
        *,
        target_component: str | None = None,
        artifact_type: AiArtifactType | str | None = None,
        active: bool | None = None,
        limit: int | None = None,
    ) -> Sequence[AiPromptProgramArtifactRecord]:
        records = tuple(self.records.values())
        if target_component is not None:
            records = tuple(
                record
                for record in records
                if record.target_component == target_component
            )
        if artifact_type is not None:
            records = tuple(
                record for record in records if record.artifact_type == artifact_type
            )
        if active is not None:
            records = tuple(record for record in records if record.active is active)
        return records if limit is None else records[:limit]

    async def get_active_artifact(
        self,
        target_component: str,
        *,
        artifact_type: AiArtifactType | str | None = None,
    ) -> AiPromptProgramArtifactRecord | None:
        return next(
            (
                record
                for record in self.records.values()
                if record.target_component == target_component
                and record.active
                and (artifact_type is None or record.artifact_type == artifact_type)
            ),
            None,
        )

    async def approve_artifact(
        self,
        artifact_id: str,
        *,
        approved_by: str,
        approved_at: datetime,
    ) -> AiPromptProgramArtifactRecord | None:
        record = self.records.get(artifact_id)
        if record is None:
            return None
        approved = replace(
            record,
            approval_status=AiArtifactApprovalStatus.APPROVED,
            approved_by=approved_by,
            approved_at=approved_at,
            active=False,
        )
        self.records[artifact_id] = approved
        return approved

    async def deactivate_artifact(
        self,
        artifact_id: str,
    ) -> AiPromptProgramArtifactRecord | None:
        record = self.records.get(artifact_id)
        if record is None:
            return None
        inactive = replace(
            record,
            approval_status=AiArtifactApprovalStatus.INACTIVE,
            active=False,
        )
        self.records[artifact_id] = inactive
        self.deactivated_ids.append(artifact_id)
        return inactive


@pytest.mark.asyncio
async def test_optimize_builds_request_and_renders_persisted_artifact() -> None:
    optimization_service = FakeOptimizationService([])

    result = await AiCommandService(
        optimization_service=optimization_service,
        settings=_settings(),
    ).optimize(
        target="rag_answer_generation",
        dataset="golden-rag-questions",
        max_cases=3,
    )

    assert result.success is True
    assert len(optimization_service.requests) == 1
    request = optimization_service.requests[0]
    assert request.dataset_id == "golden_rag_questions_v1"
    assert request.max_trainset_cases == 3
    assert request.model_name == "qwen2.5:7b"
    rendered = render_ai_optimize_result(result)
    assert "AI Optimization" in rendered
    assert "Artifact persisted: yes" in rendered
    assert "artifact-generated" in rendered


@pytest.mark.asyncio
async def test_approve_artifact_does_not_activate_artifact() -> None:
    repository = FakeArtifactRepository(
        records={"artifact-1": _artifact(artifact_id="artifact-1")},
        deactivated_ids=[],
        upserts=[],
    )

    result = await AiCommandService(artifact_repository=repository).approve_artifact(
        "artifact-1",
        approved_by="reviewer",
    )

    assert result.success is True
    assert result.artifact is not None
    assert result.artifact.approval_status is AiArtifactApprovalStatus.APPROVED
    assert result.artifact.active is False
    rendered = render_ai_artifact_command_result(result)
    assert "Activate it explicitly" in rendered
    assert "Active: no" in rendered


@pytest.mark.asyncio
async def test_activate_artifact_denies_draft_artifact() -> None:
    repository = FakeArtifactRepository(
        records={"draft-1": _artifact(artifact_id="draft-1")},
        deactivated_ids=[],
        upserts=[],
    )

    result = await AiCommandService(artifact_repository=repository).activate_artifact(
        "draft-1"
    )

    assert result.success is False
    assert result.error == "Only approved AI artifacts can be activated."
    assert repository.upserts == []


@pytest.mark.asyncio
async def test_activate_artifact_deactivates_existing_active_peer() -> None:
    active = _artifact(
        artifact_id="active-1",
        approval_status=AiArtifactApprovalStatus.APPROVED,
        approved_by="reviewer",
        approved_at=datetime(2026, 7, 15, tzinfo=UTC),
        active=True,
    )
    candidate = _artifact(
        artifact_id="candidate-1",
        approval_status=AiArtifactApprovalStatus.APPROVED,
        approved_by="reviewer",
        approved_at=datetime(2026, 7, 15, tzinfo=UTC),
        active=False,
    )
    repository = FakeArtifactRepository(
        records={active.artifact_id: active, candidate.artifact_id: candidate},
        deactivated_ids=[],
        upserts=[],
    )

    result = await AiCommandService(artifact_repository=repository).activate_artifact(
        "candidate-1"
    )

    assert result.success is True
    assert result.artifact is not None
    assert result.artifact.active is True
    assert repository.deactivated_ids == ["active-1"]
    assert repository.records["active-1"].active is False
    assert repository.records["candidate-1"].active is True


@pytest.mark.asyncio
async def test_list_artifacts_renders_filters() -> None:
    repository = FakeArtifactRepository(
        records={
            "artifact-1": _artifact(artifact_id="artifact-1", active=False),
            "artifact-2": _artifact(
                artifact_id="artifact-2",
                approval_status=AiArtifactApprovalStatus.APPROVED,
                approved_by="reviewer",
                approved_at=datetime(2026, 7, 15, tzinfo=UTC),
                active=True,
            ),
        },
        deactivated_ids=[],
        upserts=[],
    )

    result = await AiCommandService(artifact_repository=repository).list_artifacts(
        target_component="rag_answer_generation",
        active=True,
    )

    assert result.success is True
    assert tuple(artifact.artifact_id for artifact in result.artifacts) == (
        "artifact-2",
    )
    rendered = render_ai_artifacts(result)
    assert "Count: 1" in rendered
    assert "artifact-2" in rendered


def _settings() -> Settings:
    return Settings(
        DSPY_OPTIMIZATION_MODEL="qwen2.5:7b",
        DEEPEVAL_ENABLED=True,
        DEEPEVAL_JUDGE_PROVIDER="litellm",
        DEEPEVAL_JUDGE_MODEL="qwen3.5:4b",
    )


def _artifact(
    *,
    artifact_id: str,
    approval_status: AiArtifactApprovalStatus = AiArtifactApprovalStatus.DRAFT,
    approved_by: str | None = None,
    approved_at: datetime | None = None,
    active: bool = False,
    target_component: str = "rag_answer_generation",
    evaluation_dataset_id: str | None = None,
    evaluation_run_id: str | None = None,
) -> AiPromptProgramArtifactRecord:
    return AiPromptProgramArtifactRecord(
        artifact_id=artifact_id,
        artifact_type=AiArtifactType.DSPY_COMPILED_PROMPT,
        artifact_name="rag_answer_generation_dspy",
        artifact_version="v1",
        target_component=target_component,
        model_name="qwen2.5:7b",
        provider_name="dspy",
        prompt_reference=f"dspy://{target_component}/{artifact_id}",
        prompt_hash=hashlib.sha256(artifact_id.encode("utf-8")).hexdigest(),
        source="tests",
        approval_status=approval_status,
        approved_by=approved_by,
        approved_at=approved_at,
        active=active,
        evaluation_dataset_id=evaluation_dataset_id,
        evaluation_run_id=evaluation_run_id,
    )


def _evaluation_result(run_id: str) -> EvaluationRunServiceResult:
    return EvaluationRunServiceResult(
        run=EvaluationRun(
            run_id=run_id,
            target_type=EvaluationTargetType.RAG_GENERATION,
            status=EvaluationStatus.PASSED,
            evaluator_provider="litellm",
            evaluator_model="qwen3.5:4b",
            case_ids=("case-1",),
        ),
        metric_results=(
            EvaluationMetricResult(
                run_id=run_id,
                case_id="case-1",
                score=EvaluationScore(
                    metric_name="answer_quality",
                    score=0.91,
                    reason="grounded",
                ),
                status=EvaluationStatus.PASSED,
                evaluator_provider="litellm",
                evaluator_model="qwen3.5:4b",
            ),
        ),
        persistence_result=EvaluationPersistenceResult(metric_results_written=1),
    )


def _provider_result(optimization_id: str) -> DspyOptimizationProviderResult:
    prompt_hash = hashlib.sha256(optimization_id.encode("utf-8")).hexdigest()
    return DspyOptimizationProviderResult(
        optimization_id=optimization_id,
        target_component="rag_answer_generation",
        provider_name="dspy",
        model_name="qwen2.5:7b",
        artifact=DspyOptimizedArtifact(
            artifact_name="rag_answer_generation_dspy",
            artifact_version="v1",
            prompt_reference=f"dspy://rag_answer_generation/{prompt_hash[:12]}",
            prompt_hash=prompt_hash,
            program_text="{}",
        ),
        case_outputs=(
            DspyOptimizedCaseOutput(case_id="case-1", actual_output="grounded answer"),
        ),
        candidate_count=1,
        selected_candidate_id=f"{optimization_id}:candidate:baseline",
    )
