from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from typing import Literal
from typing import Protocol

from langfuse import Langfuse
from langfuse.api.resources.commons.types.dataset_status import DatasetStatus

from application.observability.ai_evaluation_datasets import AiEvaluationDataset
from application.observability.ai_evaluation_datasets import (
    AiEvaluationDatasetExportResult,
)
from application.observability.langfuse_projection import LangfusePayload
from config.settings import Settings

LangfuseLevel = Literal["DEBUG", "DEFAULT", "WARNING", "ERROR"]
LangfuseScoreDataType = Literal["NUMERIC", "CATEGORICAL", "BOOLEAN"]


class LangfuseSdkClientProtocol(Protocol):
    """Small protocol over the official Langfuse SDK used by Polaris."""

    def flush(self) -> None: ...

    def shutdown(self) -> None: ...

    def trace(
        self,
        *,
        id: str | None = None,
        name: str | None = None,
        input: object | None = None,
        output: object | None = None,
        metadata: object | None = None,
        timestamp: datetime | None = None,
        version: str | None = None,
    ) -> object: ...

    def generation(
        self,
        *,
        id: str | None = None,
        trace_id: str | None = None,
        parent_observation_id: str | None = None,
        name: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        metadata: object | None = None,
        level: LangfuseLevel | None = None,
        version: str | None = None,
        model: str | None = None,
        input: object | None = None,
        output: object | None = None,
        usage_details: dict[str, int] | None = None,
        cost_details: dict[str, float] | None = None,
    ) -> object: ...

    def span(
        self,
        *,
        id: str | None = None,
        trace_id: str | None = None,
        parent_observation_id: str | None = None,
        name: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        metadata: object | None = None,
        level: LangfuseLevel | None = None,
        input: object | None = None,
        output: object | None = None,
        version: str | None = None,
    ) -> object: ...

    def score(
        self,
        *,
        name: str,
        value: float | str,
        data_type: LangfuseScoreDataType | None = None,
        trace_id: str | None = None,
        id: str | None = None,
        comment: str | None = None,
        observation_id: str | None = None,
    ) -> object: ...

    def create_dataset(
        self,
        name: str,
        description: str | None = None,
        metadata: object | None = None,
    ) -> object: ...

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
            self.client.trace,
            id=export.trace_id,
            name=_string_or_default(
                self.payload_value(payload, "family"), "polaris.ai"
            ),
            input=export.input_value,
            output=export.output_value,
            metadata=export.metadata,
            timestamp=export.timestamp_datetime,
            version=export.release,
        )
        if export.is_generation:
            await asyncio.to_thread(
                self.client.generation,
                id=export.observation_id,
                trace_id=export.trace_id,
                parent_observation_id=export.parent_observation_id,
                name=export.name,
                start_time=export.timestamp_datetime,
                end_time=export.end_time,
                metadata=export.metadata,
                level=export.level,
                version=export.prompt_version_string,
                model=export.model,
                input=export.input_value,
                output=export.output_value,
                usage_details=export.usage_details,
                cost_details=export.cost_details,
            )
        else:
            await asyncio.to_thread(
                self.client.span,
                id=export.observation_id,
                trace_id=export.trace_id,
                parent_observation_id=export.parent_observation_id,
                name=export.name,
                start_time=export.timestamp_datetime,
                end_time=export.end_time,
                metadata=export.metadata,
                level=export.level,
                input=export.input_value,
                output=export.output_value,
                version=export.prompt_version_string,
            )
        for score in export.score_payloads:
            score_value = _float_or_default(score.get("value"), 0.0)
            await asyncio.to_thread(
                self.client.score,
                id=_optional_string(score.get("id")),
                trace_id=export.trace_id,
                observation_id=export.observation_id,
                name=_string_or_default(score.get("name"), "ai_score"),
                value=score_value,
                data_type="NUMERIC",
                comment=_optional_string(score.get("comment")),
            )
        return export.response

    @staticmethod
    def payload_value(payload: LangfusePayload, key: str) -> object:
        return payload.get(key)

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
                    "input_schema_name": dataset.input_schema_name,
                    "expected_output_schema_name": dataset.expected_output_schema_name,
                },
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
        return _stable_hex_id(f"trace:{trace_seed}")

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
    def response(self) -> dict[str, str | None]:
        correlation = _mapping(self.payload.get("correlation"))
        return {
            "external_trace_id": self.trace_id,
            "external_observation_id": self.observation_id,
            "dataset_id": _optional_string(correlation.get("dataset_id")),
            "case_id": _optional_string(correlation.get("case_id")),
            "run_id": _optional_string(correlation.get("run_id")),
        }

    @property
    def name(self) -> str:
        return _string_or_default(self.payload.get("name"), "ai observation")

    @property
    def model(self) -> str | None:
        return _optional_string(self.payload.get("model"))

    @property
    def release(self) -> str | None:
        return _optional_string(self.payload.get("release"))

    @property
    def input_value(self) -> object:
        return self.payload.get("prompt_text") or self.payload.get("input_shape")

    @property
    def output_value(self) -> object:
        return self.payload.get("response_text") or self.payload.get("output_shape")

    @property
    def is_generation(self) -> bool:
        return (
            self.payload.get("type") == "rag.generation" or "generation" in self.payload
        )

    @property
    def level(self) -> LangfuseLevel:
        status = self.payload.get("status")
        if status == "failed":
            return "ERROR"
        if status == "degraded":
            return "WARNING"
        return "DEFAULT"

    @property
    def end_time(self) -> datetime | None:
        latency_ms = self.payload.get("latency_ms")
        if not isinstance(latency_ms, int | float):
            return None
        return self.timestamp_datetime

    @property
    def parent_observation_id(self) -> str | None:
        correlation = _mapping(self.payload.get("correlation"))
        return _optional_string(correlation.get("parent_observation_id"))

    @property
    def prompt_version_string(self) -> str | None:
        prompt = _mapping(self.payload.get("prompt"))
        return _optional_string(prompt.get("version"))

    @property
    def usage_details(self) -> dict[str, int] | None:
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

    @property
    def cost_details(self) -> dict[str, float] | None:
        generation = _mapping(self.payload.get("generation"))
        cost_usd = generation.get("cost_usd")
        if not isinstance(cost_usd, int | float):
            return None
        return {"total": float(cost_usd)}

    @property
    def score_payloads(self) -> list[dict[str, object]]:
        evaluation = _mapping(self.payload.get("evaluation"))
        scores = evaluation.get("scores")
        if not isinstance(scores, list):
            return []
        payloads: list[dict[str, object]] = []
        for index, score_payload in enumerate(scores):
            score = _mapping(score_payload)
            metric_name = _optional_string(score.get("metric_name"))
            score_value = score.get("score")
            if metric_name is None or not isinstance(score_value, int | float):
                continue
            score_id = _stable_hex_id(
                f"score:{self.idempotency_key}:{metric_name}:{index}",
            )
            result = _optional_string(score.get("result"))
            reason = _optional_string(score.get("reason"))
            threshold = score.get("threshold")
            comment_parts = [part for part in (result, reason) if part]
            if isinstance(threshold, int | float):
                comment_parts.append(f"threshold={float(threshold)}")
            payloads.append(
                {
                    "id": score_id,
                    "name": metric_name,
                    "value": float(score_value),
                    "comment": "; ".join(comment_parts),
                }
            )
        return payloads

    @property
    def metadata(self) -> dict[str, object]:
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
                "environment": self.payload.get("environment"),
            }
        )
        for key in ("generation", "retrieval", "reranking", "evaluation"):
            if key in self.payload:
                metadata[key] = self.payload[key]
        return metadata


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


def _float_or_default(value: object, default: float) -> float:
    if isinstance(value, bool):
        return default
    if isinstance(value, int | float):
        return float(value)
    return default
