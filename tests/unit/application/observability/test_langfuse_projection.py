from __future__ import annotations

from dataclasses import dataclass, field
from typing import cast

from application.observability import (
    AiEvaluationObservation,
    AiEvaluationScore,
    AiGenerationObservation,
    AiObservabilityCapturePolicy,
    AiObservabilityCorrelationIds,
    AiObservabilityExportStatus,
    AiObservabilityProjector,
    AiObservationStatus,
    AiObservationType,
    AiPromptVersionReference,
    AiRedactionMode,
    AiRerankingObservation,
    AiRetrievalObservation,
    AiScoreResult,
    LangfuseAiObservabilitySink,
    LangfuseObservationMapper,
    LangfusePayload,
)


@dataclass(slots=True)
class RecordingLangfuseClient:
    response: object = field(default_factory=dict)
    payloads: list[LangfusePayload] = field(default_factory=list)

    async def export(self, payload: LangfusePayload) -> object:
        self.payloads.append(payload)
        return self.response


@dataclass(slots=True)
class FailingLangfuseClient:
    async def export(self, payload: LangfusePayload) -> object:
        raise RuntimeError("langfuse unavailable")


def test_mapper_exports_open_telemetry_correlation_and_redacted_generation() -> None:
    mapper = LangfuseObservationMapper(
        capture_policy=AiObservabilityCapturePolicy(),
        environment="test",
        release="2026.07",
    )
    observation = AiGenerationObservation(
        observation_type=AiObservationType.RAG_GENERATION,
        name="answer_generation",
        status=AiObservationStatus.SUCCESS,
        correlation_ids=AiObservabilityCorrelationIds(
            trace_id="trace-1",
            span_id="span-1",
            parent_span_id="parent-1",
            workflow_name="morning_report",
            execution_id="exec-1",
            node_name="rag_answer",
            observation_id="obs-1",
        ),
        model_name="qwen3.5:4b",
        provider_name="ollama",
        prompt="sensitive prompt",
        response="sensitive response",
        input_shape="question+context_ids",
        output_shape="answer+citations",
        prompt_reference=AiPromptVersionReference(
            prompt_name="rag.answer",
            prompt_version="v1",
            prompt_hash="hash-1",
        ),
        token_count_input=12,
        token_count_output=6,
        cost_usd=0.01,
        metadata={"context_count": 2, "degraded": False},
    )

    payload = mapper.to_payload(observation)

    assert payload["environment"] == "test"
    assert payload["release"] == "2026.07"
    assert payload["prompt_captured"] is False
    assert payload["response_captured"] is False
    assert "prompt_text" not in payload
    assert "response_text" not in payload
    assert payload["correlation"] == {
        "trace_id": "trace-1",
        "span_id": "span-1",
        "parent_span_id": "parent-1",
        "workflow_name": "morning_report",
        "execution_id": "exec-1",
        "runtime_id": None,
        "node_name": "rag_answer",
        "observation_id": "obs-1",
        "parent_observation_id": None,
        "dataset_id": None,
        "case_id": None,
        "run_id": None,
    }
    assert payload["otel"] == {
        "trace_id": "trace-1",
        "span_id": "span-1",
        "parent_span_id": "parent-1",
    }
    assert payload["generation"] == {
        "input_tokens": 12,
        "output_tokens": 6,
        "cost_usd": 0.01,
    }
    assert payload["prompt"] == {
        "name": "rag.answer",
        "version": "v1",
        "hash": "hash-1",
        "source": None,
    }


def test_mapper_captures_bounded_text_only_when_policy_is_permissive() -> None:
    mapper = LangfuseObservationMapper(
        capture_policy=AiObservabilityCapturePolicy(
            capture_prompts=True,
            capture_responses=True,
            redaction_mode=AiRedactionMode.PERMISSIVE,
            max_payload_characters=5,
        ),
        environment="test",
    )
    observation = AiGenerationObservation(
        observation_type=AiObservationType.INTELLIGENCE_REPORT_GENERATION,
        name="report_generation",
        prompt="123456789",
        response="abcdefghi",
    )

    payload = mapper.to_payload(observation)

    assert payload["prompt_text"] == "12345"
    assert payload["response_text"] == "abcde"
    assert payload["prompt_truncated"] is True
    assert payload["response_truncated"] is True


def test_mapper_projects_retrieval_reranking_and_evaluation_fields() -> None:
    mapper = LangfuseObservationMapper(
        capture_policy=AiObservabilityCapturePolicy(
            capture_responses=True,
            redaction_mode=AiRedactionMode.PERMISSIVE,
        ),
        environment="test",
    )
    retrieval = AiRetrievalObservation(
        observation_type=AiObservationType.RAG_RETRIEVAL_VECTOR,
        name="vector_retrieval",
        retrieved_count=3,
        selected_context_ids=("chunk-1", "chunk-2"),
        retrieval_scores=(0.91, 0.82),
    )
    reranking = AiRerankingObservation(
        observation_type=AiObservationType.RAG_RERANKING,
        name="reranker",
        candidate_count=5,
        selected_count=2,
        reranking_scores=(0.77, 0.75),
    )
    evaluation = AiEvaluationObservation(
        observation_type=AiObservationType.RAG_ANSWER_QUALITY,
        name="answer_quality",
        correlation_ids=AiObservabilityCorrelationIds(
            dataset_id="dataset-rag",
            case_id="case-1",
            run_id="run-1",
        ),
        scores=(
            AiEvaluationScore(
                metric_name="groundedness",
                score=0.88,
                threshold=0.8,
                result=AiScoreResult.PASS,
                reason="supported by cited chunks",
                evaluator_model="qwen3.5:4b",
                evaluator_provider="deepeval",
            ),
        ),
        evaluated_observation_id="generation-1",
    )

    retrieval_payload = mapper.to_payload(retrieval)
    reranking_payload = mapper.to_payload(reranking)
    evaluation_payload = mapper.to_payload(evaluation)

    assert retrieval_payload["retrieval"] == {
        "retrieved_count": 3,
        "selected_context_ids": ["chunk-1", "chunk-2"],
        "scores": [0.91, 0.82],
    }
    assert reranking_payload["reranking"] == {
        "candidate_count": 5,
        "selected_count": 2,
        "scores": [0.77, 0.75],
    }
    assert evaluation_payload["evaluation"] == {
        "evaluated_observation_id": "generation-1",
        "dataset_id": "dataset-rag",
        "case_id": "case-1",
        "run_id": "run-1",
        "scores": [
            {
                "metric_name": "groundedness",
                "score": 0.88,
                "threshold": 0.8,
                "result": "pass",
                "reason": "supported by cited chunks",
                "evaluator_model": "qwen3.5:4b",
                "evaluator_provider": "deepeval",
            }
        ],
    }


async def test_sink_exports_payload_and_maps_external_ids() -> None:
    client = RecordingLangfuseClient(
        response={
            "external_trace_id": "lf-trace-1",
            "external_observation_id": "lf-obs-1",
        }
    )
    sink = LangfuseAiObservabilitySink(
        client=client,
        mapper=LangfuseObservationMapper(
            capture_policy=AiObservabilityCapturePolicy(),
            environment="test",
        ),
    )
    observation = AiGenerationObservation(
        observation_type=AiObservationType.RAG_GENERATION,
        name="answer_generation",
        correlation_ids=AiObservabilityCorrelationIds(observation_id="obs-1"),
    )

    result = await sink.export(observation)

    assert result.status is AiObservabilityExportStatus.EXPORTED
    assert result.observation_id == "obs-1"
    assert result.external_trace_id == "lf-trace-1"
    assert result.external_observation_id == "lf-obs-1"
    assert client.payloads[0]["idempotency_key"] == observation.idempotency_key()


async def test_sink_returns_failed_result_without_raising() -> None:
    sink = LangfuseAiObservabilitySink(
        client=FailingLangfuseClient(),
        mapper=LangfuseObservationMapper(
            capture_policy=AiObservabilityCapturePolicy(),
            environment="test",
        ),
    )
    observation = AiGenerationObservation(
        observation_type=AiObservationType.RAG_GENERATION,
        name="answer_generation",
    )

    result = await sink.export(observation)

    assert result.status is AiObservabilityExportStatus.FAILED
    assert result.idempotency_key == observation.idempotency_key()
    assert result.error_message == "langfuse unavailable"


async def test_projector_delegates_to_configured_sink() -> None:
    client = RecordingLangfuseClient(response={"trace_id": "lf-trace-2"})
    projector = AiObservabilityProjector(
        sink=LangfuseAiObservabilitySink(
            client=client,
            mapper=LangfuseObservationMapper(
                capture_policy=AiObservabilityCapturePolicy(),
                environment="test",
            ),
        )
    )
    observation = AiGenerationObservation(
        observation_type=AiObservationType.RAG_GENERATION,
        name="answer_generation",
    )

    result = await projector.project(observation)

    assert result.status is AiObservabilityExportStatus.EXPORTED
    assert result.external_trace_id == "lf-trace-2"
    assert len(client.payloads) == 1


def test_mapper_redacts_sensitive_metadata_and_account_identifiers() -> None:
    mapper = LangfuseObservationMapper(
        capture_policy=AiObservabilityCapturePolicy(max_metadata_value_characters=12),
        environment="test",
    )
    observation = AiGenerationObservation(
        observation_type=AiObservationType.RAG_GENERATION,
        name="answer_generation",
        metadata={
            "api_key": "secret-value",
            "account_id": "acct-123",
            "safe_note": "password=secret-token and extra text",
            "long_note": "x" * 20,
        },
    )

    payload = mapper.to_payload(observation)

    metadata = payload["metadata"]
    assert isinstance(metadata, dict)
    assert metadata["api_key"] == "[redacted]"
    assert str(metadata["account_id"]).startswith("sha256:")
    assert metadata["account_id"] != "acct-123"
    safe_note = str(metadata["safe_note"])
    assert safe_note.startswith("password=")
    assert "secret-token" not in safe_note
    assert metadata["long_note"] == "xxxxxxxxxxxx"
    redaction = payload["redaction"]
    assert isinstance(redaction, dict)
    assert "metadata.api_key" in redaction["redacted_fields"]
    assert "metadata.account_id" in redaction["redacted_fields"]
    assert "metadata.safe_note" in redaction["redacted_fields"]
    assert "metadata.long_note" in redaction["truncated_fields"]


def test_mapper_redacts_captured_prompt_response_and_records_dropped_fields() -> None:
    redacted_mapper = LangfuseObservationMapper(
        capture_policy=AiObservabilityCapturePolicy(),
        environment="test",
    )
    permissive_mapper = LangfuseObservationMapper(
        capture_policy=AiObservabilityCapturePolicy(
            capture_prompts=True,
            capture_responses=True,
            redaction_mode=AiRedactionMode.PERMISSIVE,
            max_payload_characters=80,
        ),
        environment="test",
    )
    credential_url = "postgresql://" + "user" + ":" + "pass" + "@localhost/db"
    observation = AiGenerationObservation(
        observation_type=AiObservationType.RAG_GENERATION,
        name="answer_generation",
        prompt="Use api_key=abc123 and Authorization: Bearer token-value",
        response=f"Connect to {credential_url}",
    )

    redacted_payload = redacted_mapper.to_payload(observation)
    permissive_payload = permissive_mapper.to_payload(observation)

    redacted_redaction = cast(dict[str, object], redacted_payload["redaction"])
    permissive_redaction = cast(dict[str, object], permissive_payload["redaction"])

    assert "prompt_text" not in redacted_payload
    assert "prompt_text" in cast(tuple[str, ...], redacted_redaction["dropped_fields"])
    assert permissive_payload["prompt_text"] == (
        "Use api_key=[redacted] and Authorization=[redacted]"
    )
    assert permissive_payload["response_text"] == (
        "Connect to postgresql://[redacted]@localhost/db"
    )
    assert "prompt_text" in cast(
        tuple[str, ...], permissive_redaction["redacted_fields"]
    )
    assert "response_text" in cast(
        tuple[str, ...], permissive_redaction["redacted_fields"]
    )


def test_mapper_removes_reasoning_traces_from_permissive_observability_payloads() -> (
    None
):
    mapper = LangfuseObservationMapper(
        capture_policy=AiObservabilityCapturePolicy(
            capture_prompts=True,
            capture_responses=True,
            redaction_mode=AiRedactionMode.PERMISSIVE,
            max_payload_characters=200,
        ),
        environment="test",
    )
    observation = AiGenerationObservation(
        observation_type=AiObservationType.RAG_GENERATION,
        name="answer_generation",
        prompt="<think>private prompt planning</think>\nVisible prompt.",
        response="```reasoning\nprivate response trace\n```\nVisible response.",
        metadata={
            "model_note": "Scratchpad: hidden note\nFinal answer: visible note",
        },
    )

    payload = mapper.to_payload(observation)

    assert payload["prompt_text"] == "Visible prompt."
    assert payload["response_text"] == "Visible response."
    metadata = payload["metadata"]
    assert isinstance(metadata, dict)
    assert metadata["model_note"] == "visible note"
    assert "private prompt planning" not in str(payload)
    assert "private response trace" not in str(payload)
    assert "hidden note" not in str(payload)
    redaction = payload["redaction"]
    assert isinstance(redaction, dict)
    assert "prompt_text" in cast(tuple[str, ...], redaction["redacted_fields"])
    assert "response_text" in cast(tuple[str, ...], redaction["redacted_fields"])
    assert "metadata.model_note" in cast(
        tuple[str, ...],
        redaction["redacted_fields"],
    )
