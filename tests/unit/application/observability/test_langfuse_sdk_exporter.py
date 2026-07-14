from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from application.observability import AiEvaluationObservation
from application.observability import AiEvaluationScore
from application.observability import AiEvaluationDatasetBuildService
from application.observability import AiGenerationObservation
from application.observability import AiObservabilityCapturePolicy
from application.observability import AiObservabilityCorrelationIds
from application.observability import AiObservationType
from application.observability import AiPromptVersionReference
from application.observability import AiRedactionMode
from application.observability import AiScoreResult
from langfuse.api.resources.commons.types.dataset_status import DatasetStatus
from application.observability import LangfuseObservationMapper
from application.observability import LangfuseSdkExportClient
from application.observability.di import ApplicationObservabilityDIProvider
from config.settings import Settings


@dataclass(slots=True)
class RecordingLangfuseSdkClient:
    traces: list[dict[str, object]]
    generations: list[dict[str, object]]
    spans: list[dict[str, object]]
    scores: list[dict[str, object]]
    flushed: bool = False
    shutdown_called: bool = False
    datasets: list[dict[str, object]] | None = None
    dataset_items: list[dict[str, object]] | None = None

    def flush(self) -> None:
        self.flushed = True

    def shutdown(self) -> None:
        self.shutdown_called = True

    def trace(self, **kwargs: object) -> object:
        self.traces.append(kwargs)
        return kwargs

    def generation(self, **kwargs: object) -> object:
        self.generations.append(kwargs)
        return kwargs

    def span(self, **kwargs: object) -> object:
        self.spans.append(kwargs)
        return kwargs

    def score(self, **kwargs: object) -> object:
        self.scores.append(kwargs)
        return kwargs

    def create_dataset(
        self,
        name: str,
        description: str | None = None,
        metadata: object | None = None,
    ) -> object:
        if self.datasets is None:
            self.datasets = []
        self.datasets.append(
            {
                "name": name,
                "description": description,
                "metadata": metadata,
            }
        )
        return {"name": name}

    def create_dataset_item(
        self,
        dataset_name: str,
        input: object | None = None,
        expected_output: object | None = None,
        metadata: object | None = None,
        source_trace_id: str | None = None,
        source_observation_id: str | None = None,
        status: DatasetStatus | None = None,
        id: str | None = None,
    ) -> object:
        if self.dataset_items is None:
            self.dataset_items = []
        self.dataset_items.append(
            {
                "dataset_name": dataset_name,
                "input": input,
                "expected_output": expected_output,
                "metadata": metadata,
                "source_trace_id": source_trace_id,
                "source_observation_id": source_observation_id,
                "status": status,
                "id": id,
            }
        )
        return {"id": id}


def _client() -> tuple[LangfuseSdkExportClient, RecordingLangfuseSdkClient]:
    sdk_client = RecordingLangfuseSdkClient(
        traces=[],
        generations=[],
        spans=[],
        scores=[],
    )
    return LangfuseSdkExportClient(sdk_client), sdk_client


def _mapper() -> LangfuseObservationMapper:
    return LangfuseObservationMapper(
        capture_policy=AiObservabilityCapturePolicy(
            capture_prompts=True,
            capture_responses=True,
            redaction_mode=AiRedactionMode.PERMISSIVE,
        ),
        environment="test",
        release="2026.07",
    )


@pytest.mark.asyncio
async def test_sdk_client_exports_generation_with_deterministic_external_ids() -> None:
    client, sdk_client = _client()
    observation = AiGenerationObservation(
        observation_type=AiObservationType.RAG_GENERATION,
        name="answer_generation",
        correlation_ids=AiObservabilityCorrelationIds(
            trace_id="trace-1",
            parent_observation_id="parent-observation-1",
            observation_id="obs-1",
        ),
        model_name="qwen3.5:4b",
        provider_name="ollama",
        prompt="question plus context",
        response="grounded answer",
        prompt_reference=AiPromptVersionReference(
            prompt_name="rag.answer",
            prompt_version="v2",
        ),
        token_count_input=11,
        token_count_output=7,
        cost_usd=0.02,
    )
    payload = _mapper().to_payload(observation)

    first = await client.export(payload)
    second = await client.export(payload)

    assert first == second
    assert isinstance(first, dict)
    assert first["external_trace_id"]
    assert first["external_observation_id"]
    assert len(sdk_client.traces) == 2
    assert len(sdk_client.generations) == 2
    generation = sdk_client.generations[0]
    assert generation["id"] == first["external_observation_id"]
    assert generation["trace_id"] == first["external_trace_id"]
    assert generation["input"] == "question plus context"
    assert generation["output"] == "grounded answer"
    assert generation["model"] == "qwen3.5:4b"
    assert generation["usage_details"] == {"input": 11, "output": 7, "total": 18}
    assert generation["cost_details"] == {"total": 0.02}
    assert generation["version"] == "v2"
    metadata = generation["metadata"]
    assert isinstance(metadata, dict)
    assert metadata["prompt"]["name"] == "rag.answer"


@pytest.mark.asyncio
async def test_sdk_client_exports_evaluation_scores_as_langfuse_score_events() -> None:
    client, sdk_client = _client()
    observation = AiEvaluationObservation(
        observation_type=AiObservationType.RAG_ANSWER_QUALITY,
        name="answer_quality",
        correlation_ids=AiObservabilityCorrelationIds(
            trace_id="trace-2",
            dataset_id="dataset-1",
            case_id="case-1",
            run_id="run-1",
        ),
        evaluated_observation_id="generation-1",
        scores=(
            AiEvaluationScore(
                metric_name="groundedness",
                score=0.91,
                threshold=0.8,
                result=AiScoreResult.PASS,
                reason="supported by cited chunks",
                evaluator_model="judge-model",
                evaluator_provider="deepeval",
            ),
        ),
    )

    result = await client.export(_mapper().to_payload(observation))

    assert isinstance(result, dict)
    assert result["dataset_id"] == "dataset-1"
    assert result["case_id"] == "case-1"
    assert result["run_id"] == "run-1"
    assert len(sdk_client.traces) == 1
    assert len(sdk_client.spans) == 1
    assert len(sdk_client.scores) == 1
    observation_event = sdk_client.spans[0]
    score_event = sdk_client.scores[0]
    assert observation_event["trace_id"] == result["external_trace_id"]
    assert score_event["trace_id"] == result["external_trace_id"]
    assert score_event["observation_id"] == result["external_observation_id"]
    assert score_event["name"] == "groundedness"
    assert score_event["value"] == 0.91
    assert "supported by cited chunks" in str(score_event["comment"])
    assert "pass" in str(score_event["comment"])


@pytest.mark.asyncio
async def test_sdk_client_flush_and_shutdown_delegate_to_official_client() -> None:
    client, sdk_client = _client()

    await client.flush()
    await client.shutdown()

    assert sdk_client.flushed is True
    assert sdk_client.shutdown_called is True


def test_application_observability_di_builds_capture_policy_from_settings() -> None:
    provider = ApplicationObservabilityDIProvider()
    settings = Settings(
        LANGFUSE_CAPTURE_PROMPTS=True,
        LANGFUSE_CAPTURE_RESPONSES=True,
        LANGFUSE_CAPTURE_CONTEXTS=True,
        LANGFUSE_CAPTURE_USER_INPUT=True,
        LANGFUSE_REDACTION_MODE="permissive",
    )

    policy = provider.provide_ai_observability_capture_policy(settings)
    prompt_policy = provider.provide_ai_prompt_governance_policy(settings)
    mapper = provider.provide_langfuse_observation_mapper(
        policy,
        prompt_policy,
        settings,
    )

    assert policy.capture_prompts is True
    assert policy.capture_responses is True
    assert policy.capture_contexts is True
    assert policy.capture_user_input is True
    assert policy.redaction_mode is AiRedactionMode.PERMISSIVE
    assert mapper.environment == "development"
    assert mapper.prompt_governance_policy is prompt_policy


def test_langfuse_sdk_imports_are_isolated_to_approved_boundary() -> None:
    production_roots = (
        Path("application"),
        Path("core"),
        Path("config"),
        Path("domain"),
        Path("integration"),
        Path("intelligence"),
        Path("interfaces"),
        Path("mcp_server"),
    )
    allowed = {Path("application/observability/langfuse_sdk_exporter.py")}
    offenders: list[str] = []

    for root in production_roots:
        for path in root.rglob("*.py"):
            if path in allowed:
                continue
            text = path.read_text()
            if "from langfuse" in text or "import langfuse" in text:
                offenders.append(str(path))

    assert offenders == []


@pytest.mark.asyncio
async def test_sdk_client_exports_evaluation_dataset_and_cases() -> None:
    client, sdk_client = _client()
    dataset = AiEvaluationDatasetBuildService().build_default_regression_dataset()

    result = await client.export_dataset(dataset)

    assert result.status.value == "exported"
    assert result.dataset_id == dataset.dataset_id
    assert result.case_ids == tuple(case.case_id for case in dataset.cases)
    assert sdk_client.datasets is not None
    assert sdk_client.datasets[0]["name"] == dataset.name
    assert sdk_client.dataset_items is not None
    assert len(sdk_client.dataset_items) == len(dataset.cases)
    first_item = sdk_client.dataset_items[0]
    assert first_item["dataset_name"] == dataset.name
    assert first_item["id"] == dataset.cases[0].case_id
    assert first_item["status"] is DatasetStatus.ACTIVE
    assert isinstance(first_item["metadata"], dict)
    assert first_item["metadata"]["case_id"] == dataset.cases[0].case_id
