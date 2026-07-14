from __future__ import annotations

import logging
from typing import Any

from core.storage.persistence.evaluation import EvaluationMetricResultRecord
from core.telemetry.events.telemetry_event import TelemetryEvent
from core.telemetry.events.telemetry_event import TelemetryEventLevel
from core.telemetry.events.telemetry_exception_details import TelemetryExceptionDetails
from core.telemetry.observability.observability_manager import ObservabilityManager
from domain.evaluation import EvaluationMetricResult
from domain.evaluation import EvaluationStatus
from domain.evaluation import EvaluationTargetType

logger = logging.getLogger(__name__)

_SOURCE = "application.evaluations"


class EvaluationTelemetry:
    """Canonical telemetry boundary for DeepEval evaluation workflows."""

    def __init__(
        self,
        observability_manager: ObservabilityManager | None,
    ) -> None:
        self._observability_manager = observability_manager

    async def emit_run_started(
        self,
        *,
        run_id: str,
        target_type: EvaluationTargetType,
        evaluator_provider: str,
        evaluator_model: str,
        case_count: int,
        metric_count: int,
        dataset_id: str | None,
    ) -> None:
        await self._emit(
            event_type="evaluation.run.started",
            level=TelemetryEventLevel.INFO,
            success=None,
            run_id=run_id,
            attributes={
                "target_type": target_type.value,
                "evaluator_provider": evaluator_provider,
                "evaluator_model": evaluator_model,
                "case_count": case_count,
                "metric_count": metric_count,
                "dataset_id": dataset_id,
            },
        )

    async def emit_run_completed(
        self,
        *,
        run_id: str,
        target_type: EvaluationTargetType,
        status: EvaluationStatus,
        evaluator_provider: str,
        evaluator_model: str,
        case_count: int,
        metric_result_count: int,
        dataset_id: str | None,
        duration_seconds: float,
    ) -> None:
        attributes = {
            "target_type": target_type.value,
            "status": status.value,
            "evaluator_provider": evaluator_provider,
            "evaluator_model": evaluator_model,
            "case_count": case_count,
            "metric_result_count": metric_result_count,
            "dataset_id": dataset_id,
        }
        self._increment(
            "evaluation_runs_total",
            attributes={**attributes, "outcome": status.value},
        )
        self._observe(
            "evaluation_run_duration_seconds",
            duration_seconds,
            attributes=attributes,
        )
        await self._emit(
            event_type="evaluation.run.completed",
            level=TelemetryEventLevel.INFO,
            success=status is not EvaluationStatus.ERRORED,
            run_id=run_id,
            duration_seconds=duration_seconds,
            attributes=attributes,
        )

    async def emit_run_failed(
        self,
        *,
        run_id: str,
        target_type: EvaluationTargetType,
        evaluator_provider: str,
        evaluator_model: str,
        case_count: int,
        dataset_id: str | None,
        duration_seconds: float,
        error: BaseException | str,
    ) -> None:
        attributes = {
            "target_type": target_type.value,
            "evaluator_provider": evaluator_provider,
            "evaluator_model": evaluator_model,
            "case_count": case_count,
            "dataset_id": dataset_id,
            "outcome": EvaluationStatus.ERRORED.value,
        }
        self._increment("evaluation_runs_total", attributes=attributes)
        self.record_judge_model_failure(
            target_type=target_type,
            evaluator_provider=evaluator_provider,
            evaluator_model=evaluator_model,
        )
        await self._emit(
            event_type="evaluation.run.failed",
            level=TelemetryEventLevel.ERROR,
            success=False,
            error_count=1,
            run_id=run_id,
            duration_seconds=duration_seconds,
            attributes=attributes,
            payload=_error_payload(error),
            exception_details=_exception_details(error),
        )

    def record_cases_evaluated(
        self,
        *,
        target_type: EvaluationTargetType,
        evaluator_provider: str,
        evaluator_model: str,
        case_count: int,
    ) -> None:
        if case_count <= 0:
            return
        self._increment(
            "evaluation_cases_evaluated_total",
            value=float(case_count),
            attributes={
                "target_type": target_type.value,
                "evaluator_provider": evaluator_provider,
                "evaluator_model": evaluator_model,
            },
        )

    def record_metric_result(
        self,
        metric_result: EvaluationMetricResult | EvaluationMetricResultRecord,
        *,
        target_type: EvaluationTargetType,
    ) -> None:
        attributes = {
            "target_type": target_type.value,
            "metric_name": _metric_name(metric_result),
            "status": _metric_status(metric_result).value,
            "evaluator_provider": metric_result.evaluator_provider,
            "evaluator_model": metric_result.evaluator_model,
        }
        duration_ms = metric_result.duration_ms
        if duration_ms is not None:
            self._observe(
                "evaluation_metric_duration_seconds",
                duration_ms / 1000.0,
                attributes=attributes,
            )
        if _metric_status(metric_result) is EvaluationStatus.ERRORED:
            self._increment("evaluation_metric_failures_total", attributes=attributes)
        if metric_result.passed is False:
            self._increment(
                "evaluation_threshold_failures_total", attributes=attributes
            )

    def record_judge_model_failure(
        self,
        *,
        target_type: EvaluationTargetType,
        evaluator_provider: str,
        evaluator_model: str,
    ) -> None:
        self._increment(
            "evaluation_judge_model_failures_total",
            attributes={
                "target_type": target_type.value,
                "evaluator_provider": evaluator_provider,
                "evaluator_model": evaluator_model,
            },
        )

    async def emit_dataset_load_failed(
        self,
        *,
        job_id: str,
        job_type: str,
        case_id: str,
        dataset_id: str,
    ) -> None:
        attributes = {
            "job_id": job_id,
            "job_type": job_type,
            "case_id": case_id,
            "dataset_id": dataset_id,
        }
        self._increment("evaluation_dataset_load_failures_total", attributes=attributes)
        await self._emit(
            event_type="evaluation.dataset.load_failed",
            level=TelemetryEventLevel.WARNING,
            success=False,
            error_count=1,
            run_id=None,
            attributes=attributes,
            payload={
                **attributes,
                "error_message": "Evaluation case references a missing dataset.",
            },
        )

    def record_langfuse_projection_failures(
        self,
        *,
        run_id: str,
        target_type: EvaluationTargetType | str,
        failed_count: int,
    ) -> None:
        if failed_count <= 0:
            return
        self._increment(
            "evaluation_langfuse_projection_failures_total",
            value=float(failed_count),
            attributes={
                "run_id": run_id,
                "target_type": _target_value(target_type),
            },
        )

    def record_retry_count(
        self,
        *,
        job_id: str,
        job_type: str,
        retry_count: int = 1,
    ) -> None:
        if retry_count <= 0:
            return
        self._increment(
            "evaluation_retry_jobs_total",
            value=float(retry_count),
            attributes={"job_id": job_id, "job_type": job_type},
        )

    def record_skipped_cases(
        self,
        *,
        job_id: str,
        job_type: str,
        skipped_count: int,
        reason: str,
    ) -> None:
        if skipped_count <= 0:
            return
        self._increment(
            "evaluation_skipped_cases_total",
            value=float(skipped_count),
            attributes={
                "job_id": job_id,
                "job_type": job_type,
                "reason": reason,
            },
        )

    async def _emit(
        self,
        *,
        event_type: str,
        level: TelemetryEventLevel,
        success: bool | None,
        run_id: str | None,
        attributes: dict[str, Any],
        payload: dict[str, Any] | None = None,
        duration_seconds: float | None = None,
        error_count: int = 0,
        exception_details: TelemetryExceptionDetails | None = None,
    ) -> None:
        if self._observability_manager is None:
            return
        try:
            await self._observability_manager.emit(
                TelemetryEvent(
                    event_type=event_type,
                    source=_SOURCE,
                    level=level,
                    success=success,
                    error_count=error_count,
                    exception_details=exception_details,
                    correlation_id=run_id,
                    duration_seconds=duration_seconds,
                    attributes=attributes,
                    payload={**attributes, **dict(payload or {})},
                )
            )
        except Exception:
            logger.exception(
                "Evaluation telemetry event emission failed.",
                extra={"event_type": event_type, "run_id": run_id},
            )

    def _increment(
        self,
        name: str,
        *,
        value: float = 1.0,
        attributes: dict[str, Any],
    ) -> None:
        if self._observability_manager is None:
            return
        try:
            self._observability_manager.increment(
                name,
                value=value,
                attributes=attributes,
            )
        except Exception:
            logger.exception(
                "Evaluation telemetry counter recording failed.",
                extra={"metric_name": name},
            )

    def _observe(
        self,
        name: str,
        value: float,
        *,
        attributes: dict[str, Any],
    ) -> None:
        if self._observability_manager is None:
            return
        try:
            self._observability_manager.observe(
                name,
                value=value,
                attributes=attributes,
            )
        except Exception:
            logger.exception(
                "Evaluation telemetry histogram recording failed.",
                extra={"metric_name": name},
            )


def _metric_name(
    metric_result: EvaluationMetricResult | EvaluationMetricResultRecord,
) -> str:
    if isinstance(metric_result, EvaluationMetricResult):
        return metric_result.score.metric_name
    return metric_result.metric_name


def _metric_status(
    metric_result: EvaluationMetricResult | EvaluationMetricResultRecord,
) -> EvaluationStatus:
    if isinstance(metric_result.status, EvaluationStatus):
        return metric_result.status
    return EvaluationStatus(metric_result.status)


def _target_value(target_type: EvaluationTargetType | str) -> str:
    if isinstance(target_type, EvaluationTargetType):
        return target_type.value
    return str(target_type)


def _exception_details(error: BaseException | str) -> TelemetryExceptionDetails | None:
    if isinstance(error, BaseException):
        return TelemetryExceptionDetails.from_exception(error)
    return None


def _error_payload(error: BaseException | str) -> dict[str, str]:
    return {
        "error_type": type(error).__name__
        if isinstance(error, BaseException)
        else "EvaluationError",
        "error_message": str(error),
    }
