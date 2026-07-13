from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from typing import Any
from typing import Protocol

from langfuse import Langfuse
from langfuse.api.commons.types import ObservationLevel
from langfuse.api.commons.types import DatasetStatus
from langfuse.api.commons.types import ScoreDataType
from langfuse.api.ingestion.types import CreateGenerationBody
from langfuse.api.ingestion.types import IngestionEvent_GenerationCreate
from langfuse.api.ingestion.types import IngestionEvent_ObservationCreate
from langfuse.api.ingestion.types import IngestionEvent_ScoreCreate
from langfuse.api.ingestion.types import IngestionEvent_TraceCreate
from langfuse.api.ingestion.types import ObservationBody
from langfuse.api.ingestion.types import ObservationType
from langfuse.api.ingestion.types import ScoreBody
from langfuse.api.ingestion.types import TraceBody

from application.observability.ai_evaluation_datasets import AiEvaluationDataset
from application.observability.ai_evaluation_datasets import (
    AiEvaluationDatasetExportResult,
)
from application.observability.langfuse_projection import LangfusePayload
from config.settings import Settings


class LangfuseSdkClientProtocol(Protocol):
    """Small protocol over the official Langfuse SDK used by Polaris."""

    api: Any

    def flush(self) -> None: ...

    def shutdown(self) -> None: ...

    def create_dataset(
        self,
        *,
        name: str,
        description: str | None = None,
        metadata: object | None = None,
        input_schema: object | None = None,
        expected_output_schema: object | None = None,
    ) -> object: ...

    def create_dataset_item(
        self,
        *,
        dataset_name: str,
        input: object | None = None,
        expected_output: object | None = None,
        metadata: object | None = None,
        source_trace_id: str | None = None,
        source_observation_id: str | None = None,
        status: DatasetStatus | None = None,
        id: str | None = None,
    ) -> object: ...


@dataclass(frozen=True, slots=True)
class LangfuseSdkExportClient:
    """Official Langfuse SDK export adapter for durable Polaris AI observations."""

    client: LangfuseSdkClientProtocol

    @classmethod
    def from_settings(cls, settings: Settings) -> LangfuseSdkExportClient:
        settings.validate_langfuse_observability(require_configured=True)
        assert settings.LANGFUSE_HOST is not None
        assert settings.LANGFUSE_PUBLIC_KEY is not None
        assert settings.LANGFUSE_SECRET_KEY is not None
        client = Langfuse(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            host=settings.LANGFUSE_HOST,
            environment=settings.LANGFUSE_ENVIRONMENT,
            release=settings.LANGFUSE_RELEASE,
            sample_rate=settings.LANGFUSE_SAMPLE_RATE,
        )
        return cls(client)

    async def export(self, payload: LangfusePayload) -> object:
        export = _LangfuseSdkPayloadExport(payload)
        await asyncio.to_thread(
            self.client.api.ingestion.batch,
            batch=export.events,
            metadata={
                "source": "polaris.ai_observability",
                "idempotency_key": export.idempotency_key,
            },
        )
        return export.response

    async def export_dataset(
        self,
        dataset: AiEvaluationDataset,
    ) -> AiEvaluationDatasetExportResult:
        try:
            await asyncio.to_thread(
                self.client.create_dataset,
                name=dataset.name,
                description=dataset.description,
                metadata={
                    "dataset_id": dataset.dataset_id,
                    "source": "polaris.ai_observability",
                    "case_count": len(dataset.cases),
                    "created_at": dataset.created_at.isoformat(),
                },
                input_schema={"name": dataset.input_schema_name},
                expected_output_schema={"name": dataset.expected_output_schema_name},
            )
            for case in dataset.cases:
                await asyncio.to_thread(
                    self.client.create_dataset_item,
                    dataset_name=dataset.name,
                    input={
                        "case_id": case.case_id,
                        "kind": case.kind.value,
                        "text": case.input_text,
                    },
                    expected_output={"text": case.expected_output_text},
                    metadata={
                        "dataset_id": case.dataset_id,
                        "case_id": case.case_id,
                        "case_name": case.name,
                        "kind": case.kind.value,
                        "evaluation_criteria": list(case.evaluation_criteria),
                        "tags": list(case.tags),
                        "metadata": dict(case.metadata or {}),
                    },
                    source_trace_id=case.source_trace_id,
                    source_observation_id=case.source_observation_id,
                    status=DatasetStatus.ACTIVE,
                    id=case.case_id,
                )
        except Exception as exc:
            return AiEvaluationDatasetExportResult.failed(
                dataset_id=dataset.dataset_id,
                case_ids=tuple(case.case_id for case in dataset.cases),
                error_message=str(exc),
            )
        return AiEvaluationDatasetExportResult.exported(
            dataset_id=dataset.dataset_id,
            case_ids=tuple(case.case_id for case in dataset.cases),
        )

    async def flush(self) -> None:
        await asyncio.to_thread(self.client.flush)

    async def shutdown(self) -> None:
        await asyncio.to_thread(self.client.shutdown)


@dataclass(frozen=True, slots=True)
class _LangfuseSdkPayloadExport:
    payload: LangfusePayload

    @property
    def idempotency_key(self) -> str:
        return _string_or_default(self.payload.get("idempotency_key"), "unknown")

    @property
    def trace_id(self) -> str:
        correlation = _mapping(self.payload.get("correlation"))
        trace_seed = (
            _optional_string(correlation.get("trace_id")) or self.idempotency_key
        )
        return Langfuse.create_trace_id(seed=trace_seed)

    @property
    def observation_id(self) -> str:
        return _stable_hex_id(f"observation:{self.idempotency_key}", length=16)

    @property
    def timestamp(self) -> str:
        return _string_or_default(
            self.payload.get("timestamp"),
            datetime.now(UTC).isoformat(),
        )

    @property
    def timestamp_datetime(self) -> datetime:
        raw_timestamp = self.timestamp
        try:
            parsed = datetime.fromisoformat(raw_timestamp)
        except ValueError:
            return datetime.now(UTC)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed

    @property
    def events(self) -> list[Any]:
        events: list[Any] = [self._trace_event(), self._observation_event()]
        events.extend(self._score_events())
        return events

    @property
    def response(self) -> dict[str, str | None]:
        correlation = _mapping(self.payload.get("correlation"))
        return {
            "external_trace_id": self.trace_id,
            "external_observation_id": self.observation_id,
            "dataset_id": _optional_string(correlation.get("dataset_id")),
            "case_id": _optional_string(correlation.get("case_id")),
            "run_id": _optional_string(correlation.get("run_id")),
        }

    def _trace_event(self) -> IngestionEvent_TraceCreate:
        return IngestionEvent_TraceCreate(
            id=_stable_hex_id(f"trace-event:{self.idempotency_key}"),
            timestamp=self.timestamp,
            body=TraceBody(
                id=self.trace_id,
                timestamp=self.timestamp_datetime,
                name=_string_or_default(self.payload.get("family"), "polaris.ai"),
                input=self._input_value(),
                output=self._output_value(),
                release=_optional_string(self.payload.get("release")),
                metadata=self._metadata(),
                environment=_optional_string(self.payload.get("environment")),
            ),
            metadata={"source": "polaris.ai_observability"},
        )

    def _observation_event(
        self,
    ) -> IngestionEvent_GenerationCreate | IngestionEvent_ObservationCreate:
        if self._is_generation():
            return IngestionEvent_GenerationCreate(
                id=_stable_hex_id(f"generation-event:{self.idempotency_key}"),
                timestamp=self.timestamp,
                body=CreateGenerationBody(
                    id=self.observation_id,
                    trace_id=self.trace_id,
                    name=_string_or_default(self.payload.get("name"), "ai observation"),
                    start_time=self.timestamp_datetime,
                    end_time=self._end_time(),
                    model=_optional_string(self.payload.get("model")),
                    input=self._input_value(),
                    output=self._output_value(),
                    metadata=self._metadata(),
                    level=self._level(),
                    parent_observation_id=self._parent_observation_id(),
                    version=self._prompt_version_string(),
                    environment=_optional_string(self.payload.get("environment")),
                    usage_details=self._usage_details(),
                    cost_details=self._cost_details(),
                    prompt_name=self._prompt_name(),
                    prompt_version=self._prompt_version_int(),
                ),
                metadata={"source": "polaris.ai_observability"},
            )
        return IngestionEvent_ObservationCreate(
            id=_stable_hex_id(f"observation-event:{self.idempotency_key}"),
            timestamp=self.timestamp,
            body=ObservationBody(
                id=self.observation_id,
                trace_id=self.trace_id,
                type=self._observation_type(),
                name=_string_or_default(self.payload.get("name"), "ai observation"),
                start_time=self.timestamp_datetime,
                end_time=self._end_time(),
                model=_optional_string(self.payload.get("model")),
                input=self._input_value(),
                output=self._output_value(),
                metadata=self._metadata(),
                level=self._level(),
                parent_observation_id=self._parent_observation_id(),
                version=self._prompt_version_string(),
                environment=_optional_string(self.payload.get("environment")),
            ),
            metadata={"source": "polaris.ai_observability"},
        )

    def _score_events(self) -> list[IngestionEvent_ScoreCreate]:
        evaluation = _mapping(self.payload.get("evaluation"))
        scores = evaluation.get("scores")
        if not isinstance(scores, list):
            return []
        events: list[IngestionEvent_ScoreCreate] = []
        for index, score_payload in enumerate(scores):
            score = _mapping(score_payload)
            metric_name = _optional_string(score.get("metric_name"))
            score_value = score.get("score")
            if metric_name is None or not isinstance(score_value, int | float):
                continue
            score_id = _stable_hex_id(
                f"score:{self.idempotency_key}:{metric_name}:{index}",
            )
            events.append(
                IngestionEvent_ScoreCreate(
                    id=_stable_hex_id(f"score-event:{score_id}"),
                    timestamp=self.timestamp,
                    body=ScoreBody(
                        id=score_id,
                        trace_id=self.trace_id,
                        observation_id=self.observation_id,
                        name=metric_name,
                        value=float(score_value),
                        comment=_optional_string(score.get("reason")),
                        metadata={
                            "result": _optional_string(score.get("result")),
                            "threshold": score.get("threshold"),
                            "evaluator_model": _optional_string(
                                score.get("evaluator_model")
                            ),
                            "evaluator_provider": _optional_string(
                                score.get("evaluator_provider")
                            ),
                        },
                        data_type=ScoreDataType.NUMERIC,
                        environment=_optional_string(self.payload.get("environment")),
                    ),
                    metadata={"source": "polaris.ai_observability"},
                )
            )
        return events

    def _metadata(self) -> dict[str, object]:
        metadata = dict(_mapping(self.payload.get("metadata")))
        metadata.update(
            {
                "polaris_payload_type": self.payload.get("type"),
                "family": self.payload.get("family"),
                "status": self.payload.get("status"),
                "provider": self.payload.get("provider"),
                "latency_ms": self.payload.get("latency_ms"),
                "idempotency_key": self.idempotency_key,
                "correlation": self.payload.get("correlation"),
                "otel": self.payload.get("otel"),
                "capture_policy": self.payload.get("capture_policy"),
                "prompt": self.payload.get("prompt"),
            }
        )
        for key in ("generation", "retrieval", "reranking", "evaluation"):
            if key in self.payload:
                metadata[key] = self.payload[key]
        return metadata

    def _input_value(self) -> object:
        return self.payload.get("prompt_text") or self.payload.get("input_shape")

    def _output_value(self) -> object:
        return self.payload.get("response_text") or self.payload.get("output_shape")

    def _is_generation(self) -> bool:
        return (
            self.payload.get("type") == "rag.generation" or "generation" in self.payload
        )

    def _observation_type(self) -> ObservationType:
        payload_type = _string_or_default(self.payload.get("type"), "")
        if payload_type.endswith("security"):
            return ObservationType.GUARDRAIL
        if "retrieval" in payload_type or payload_type.endswith("parent_expansion"):
            return ObservationType.RETRIEVER
        if payload_type.endswith("reranking"):
            return ObservationType.RETRIEVER
        if payload_type.endswith(("crag", "self_rag", "answer_quality")):
            return ObservationType.EVALUATOR
        if payload_type.endswith("agent_reasoning"):
            return ObservationType.AGENT
        if payload_type.startswith("intelligence."):
            return ObservationType.CHAIN
        return ObservationType.SPAN

    def _level(self) -> ObservationLevel:
        status = self.payload.get("status")
        if status == "failed":
            return ObservationLevel.ERROR
        if status == "degraded":
            return ObservationLevel.WARNING
        return ObservationLevel.DEFAULT

    def _end_time(self) -> datetime | None:
        latency_ms = self.payload.get("latency_ms")
        if not isinstance(latency_ms, int | float):
            return None
        return self.timestamp_datetime

    def _parent_observation_id(self) -> str | None:
        correlation = _mapping(self.payload.get("correlation"))
        return _optional_string(correlation.get("parent_observation_id"))

    def _prompt_name(self) -> str | None:
        prompt = _mapping(self.payload.get("prompt"))
        return _optional_string(prompt.get("name"))

    def _prompt_version_string(self) -> str | None:
        prompt = _mapping(self.payload.get("prompt"))
        return _optional_string(prompt.get("version"))

    def _prompt_version_int(self) -> int | None:
        version = self._prompt_version_string()
        if version is None:
            return None
        if version.startswith("v"):
            version = version[1:]
        try:
            return int(version)
        except ValueError:
            return None

    def _usage_details(self) -> dict[str, int] | None:
        generation = _mapping(self.payload.get("generation"))
        input_tokens = generation.get("input_tokens")
        output_tokens = generation.get("output_tokens")
        usage: dict[str, int] = {}
        if isinstance(input_tokens, int):
            usage["input"] = input_tokens
        if isinstance(output_tokens, int):
            usage["output"] = output_tokens
        if not usage:
            return None
        usage["total"] = usage.get("input", 0) + usage.get("output", 0)
        return usage

    def _cost_details(self) -> dict[str, float] | None:
        generation = _mapping(self.payload.get("generation"))
        cost_usd = generation.get("cost_usd")
        if not isinstance(cost_usd, int | float):
            return None
        return {"total": float(cost_usd)}


def _mapping(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return {str(key): item for key, item in value.items()}
    return {}


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value or None
    return str(value)


def _string_or_default(value: object, default: str) -> str:
    return _optional_string(value) or default


def _stable_hex_id(seed: str, *, length: int = 32) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:length]
