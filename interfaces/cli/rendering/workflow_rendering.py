from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import Any

from interfaces.cli.formatters.json_formatter import format_json
from interfaces.cli.formatters.json_formatter import to_jsonable


@dataclass(frozen=True, slots=True)
class WorkflowRenderError:
    """
    CLI-boundary error model used to render failed workflow output.
    """

    message: str
    node_name: str | None = None
    error_type: str | None = None
    details: dict[str, Any] = field(
        default_factory=dict,
    )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "message": self.message,
            "node_name": self.node_name,
            "error_type": self.error_type,
            "details": to_jsonable(
                self.details,
            ),
        }


@dataclass(frozen=True, slots=True)
class WorkflowRenderEnvelope:
    """
    CLI-boundary view of a workflow run.

    The runtime remains the source of truth. This model exists only so the CLI
    can render a stable output shape for successful runs, failed runs, and
    exceptions raised before a WorkflowRunResult exists.
    """

    workflow_name: str | None
    execution_id: str | None
    success: bool
    status: str
    error_message: str | None = None
    errors: tuple[WorkflowRenderError, ...] = ()
    failed_nodes: tuple[str, ...] = ()
    summary: dict[str, Any] = field(
        default_factory=dict,
    )
    payload: dict[str, Any] = field(
        default_factory=dict,
    )
    raw_result: dict[str, Any] = field(
        default_factory=dict,
    )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "workflow_name": self.workflow_name,
            "execution_id": self.execution_id,
            "success": self.success,
            "status": self.status,
            "error_message": self.error_message,
            "errors": [error.to_dict() for error in self.errors],
            "failed_nodes": list(
                self.failed_nodes,
            ),
            "summary": to_jsonable(
                self.summary,
            ),
            "payload": to_jsonable(
                self.payload,
            ),
            "raw_result": to_jsonable(
                self.raw_result,
            ),
        }


def workflow_result_to_render_envelope(
    result: Any,
    *,
    workflow_name: str | None = None,
    execution_id: str | None = None,
) -> WorkflowRenderEnvelope:
    if isinstance(
        result,
        WorkflowRenderEnvelope,
    ):
        return result

    data = _as_mapping(
        to_jsonable(
            result,
        )
    )
    execution_result = _as_mapping(
        data.get(
            "execution_result",
        )
    )
    final_context = _as_mapping(
        execution_result.get(
            "final_context",
        )
    )

    resolved_workflow_name = _first_text(
        data.get(
            "workflow_name",
        ),
        execution_result.get(
            "workflow_name",
        ),
        final_context.get(
            "workflow_id",
        ),
        workflow_name,
    )
    resolved_execution_id = _first_text(
        data.get(
            "execution_id",
        ),
        execution_result.get(
            "execution_id",
        ),
        final_context.get(
            "execution_id",
        ),
        execution_id,
    )
    success = _resolve_success(
        data=data,
        execution_result=execution_result,
    )
    status = _resolve_status(
        success=success,
        data=data,
        execution_result=execution_result,
    )
    error_message = _first_text(
        execution_result.get(
            "error_message",
        ),
        data.get(
            "error_message",
        ),
    )
    errors = _extract_errors(
        error_message=error_message,
        execution_result=execution_result,
        final_context=final_context,
    )
    failed_nodes = _extract_failed_nodes(
        execution_result=execution_result,
        final_context=final_context,
        errors=errors,
    )
    payload = _extract_payload(
        final_context=final_context,
    )
    summary = _extract_summary(
        execution_result=execution_result,
        final_context=final_context,
    )

    return WorkflowRenderEnvelope(
        workflow_name=resolved_workflow_name,
        execution_id=resolved_execution_id,
        success=success,
        status=status,
        error_message=error_message,
        errors=errors,
        failed_nodes=failed_nodes,
        summary=summary,
        payload=payload,
        raw_result=data,
    )


def workflow_exception_to_render_envelope(
    exc: BaseException,
    *,
    workflow_name: str | None = None,
    execution_id: str | None = None,
    summary: dict[str, Any] | None = None,
) -> WorkflowRenderEnvelope:
    error = WorkflowRenderError(
        message=str(
            exc,
        )
        or exc.__class__.__name__,
        error_type=exc.__class__.__name__,
    )

    return WorkflowRenderEnvelope(
        workflow_name=workflow_name,
        execution_id=execution_id,
        success=False,
        status="failed",
        error_message=error.message,
        errors=(error,),
        summary=to_jsonable(
            summary or {},
        ),
        raw_result={
            "exception": {
                "type": exc.__class__.__name__,
                "message": error.message,
            }
        },
    )


def build_workflow_render_envelope(
    value: Any,
    *,
    workflow_name: str | None = None,
    execution_id: str | None = None,
) -> WorkflowRenderEnvelope:
    if isinstance(
        value,
        BaseException,
    ):
        return workflow_exception_to_render_envelope(
            value,
            workflow_name=workflow_name,
            execution_id=execution_id,
        )

    return workflow_result_to_render_envelope(
        value,
        workflow_name=workflow_name,
        execution_id=execution_id,
    )


def render_workflow_output(
    envelope: WorkflowRenderEnvelope,
    output_format: str,
) -> str:
    if output_format == "json":
        return format_json(
            envelope,
        )

    if output_format == "console":
        from interfaces.cli.formatters.console_formatter import format_workflow_run

        return format_workflow_run(
            envelope,
        )

    if output_format == "markdown":
        from interfaces.cli.formatters.markdown_formatter import (
            format_workflow_run_markdown,
        )

        return format_workflow_run_markdown(
            envelope,
        )

    raise ValueError("format must be one of: console, json, markdown")


def _as_mapping(
    value: Any,
) -> dict[str, Any]:
    if isinstance(
        value,
        dict,
    ):
        return value

    return {}


def _first_text(
    *values: Any,
) -> str | None:
    for value in values:
        if (
            isinstance(
                value,
                str,
            )
            and value.strip()
        ):
            return value

    return None


def _resolve_success(
    *,
    data: dict[str, Any],
    execution_result: dict[str, Any],
) -> bool:
    for source in (
        data,
        execution_result,
    ):
        success = source.get(
            "success",
        )
        if isinstance(
            success,
            bool,
        ):
            return success

    return False


def _resolve_status(
    *,
    success: bool,
    data: dict[str, Any],
    execution_result: dict[str, Any],
) -> str:
    for source in (
        execution_result,
        data,
    ):
        status = source.get(
            "status",
        )
        if (
            isinstance(
                status,
                str,
            )
            and status.strip()
        ):
            return status

    return "succeeded" if success else "failed"


def _extract_errors(
    *,
    error_message: str | None,
    execution_result: dict[str, Any],
    final_context: dict[str, Any],
) -> tuple[WorkflowRenderError, ...]:
    errors: list[WorkflowRenderError] = []

    if error_message:
        errors.append(
            WorkflowRenderError(
                message=error_message,
                error_type="WorkflowExecutionError",
            )
        )

    _extend_errors_from_value(
        errors,
        final_context.get(
            "errors",
            [],
        ),
    )
    _extend_errors_from_value(
        errors,
        execution_result.get(
            "errors",
            [],
        ),
    )

    node_outputs = _as_mapping(
        final_context.get(
            "node_outputs",
        )
    )
    for node_name, node_output_value in node_outputs.items():
        node_output = _as_mapping(
            node_output_value,
        )
        _extend_errors_from_value(
            errors,
            node_output.get(
                "errors",
                [],
            ),
            node_name=str(
                node_name,
            ),
        )

    return _deduplicate_errors(
        errors,
    )


def _extend_errors_from_value(
    errors: list[WorkflowRenderError],
    value: Any,
    *,
    node_name: str | None = None,
) -> None:
    if value is None:
        return

    if isinstance(
        value,
        dict,
    ):
        errors.append(
            _error_from_mapping(
                value,
                node_name=node_name,
            )
        )
        return

    if isinstance(
        value,
        (list, tuple),
    ):
        for item in value:
            _extend_errors_from_value(
                errors,
                item,
                node_name=node_name,
            )
        return

    message = str(
        value,
    )
    if message:
        errors.append(
            WorkflowRenderError(
                message=message,
                node_name=node_name,
            )
        )


def _error_from_mapping(
    value: dict[str, Any],
    *,
    node_name: str | None,
) -> WorkflowRenderError:
    resolved_node_name = _first_text(
        value.get(
            "node_name",
        ),
        value.get(
            "node",
        ),
        node_name,
    )
    message = _first_text(
        value.get(
            "message",
        ),
        value.get(
            "error",
        ),
        value.get(
            "reason",
        ),
        value.get(
            "detail",
        ),
    ) or str(
        value,
    )
    error_type = _first_text(
        value.get(
            "type",
        ),
        value.get(
            "error_type",
        ),
        value.get(
            "exception_type",
        ),
    )

    details = {
        key: item
        for key, item in value.items()
        if key
        not in {
            "message",
            "error",
            "reason",
            "detail",
            "node_name",
            "node",
            "type",
            "error_type",
            "exception_type",
        }
    }

    return WorkflowRenderError(
        message=message,
        node_name=resolved_node_name,
        error_type=error_type,
        details=details,
    )


def _deduplicate_errors(
    errors: list[WorkflowRenderError],
) -> tuple[WorkflowRenderError, ...]:
    unique: list[WorkflowRenderError] = []
    seen: set[tuple[str, str | None, str | None, str]] = set()

    for error in errors:
        key = (
            error.message,
            error.node_name,
            error.error_type,
            repr(
                to_jsonable(
                    error.details,
                )
            ),
        )
        if key in seen:
            continue

        seen.add(
            key,
        )
        unique.append(
            error,
        )

    return tuple(
        unique,
    )


def _extract_failed_nodes(
    *,
    execution_result: dict[str, Any],
    final_context: dict[str, Any],
    errors: tuple[WorkflowRenderError, ...],
) -> tuple[str, ...]:
    failed_nodes: list[str] = []

    existing = execution_result.get(
        "failed_nodes",
        [],
    )
    if isinstance(
        existing,
        (list, tuple),
    ):
        failed_nodes.extend(str(node) for node in existing if str(node).strip())

    failed_nodes.extend(error.node_name for error in errors if error.node_name)

    node_outputs = _as_mapping(
        final_context.get(
            "node_outputs",
        )
    )
    for node_name, node_output_value in node_outputs.items():
        node_output = _as_mapping(
            node_output_value,
        )
        if node_output.get(
            "success",
        ) is False and not node_output.get(
            "skipped",
            False,
        ):
            failed_nodes.append(
                str(
                    node_name,
                )
            )

    return tuple(
        dict.fromkeys(
            failed_nodes,
        )
    )


def _extract_payload(
    *,
    final_context: dict[str, Any],
) -> dict[str, Any]:
    workflow_inputs = _workflow_inputs_from_context(
        final_context,
    )
    payload: dict[str, Any] = {}

    if workflow_inputs:
        payload["workflow_inputs"] = workflow_inputs

    morning_report = _extract_morning_report_from_workflow_inputs(
        workflow_inputs,
    )
    if morning_report:
        payload["morning_report"] = morning_report

    node_outputs = _as_mapping(
        final_context.get(
            "node_outputs",
        )
    )
    if node_outputs:
        payload["node_outputs"] = node_outputs

    return payload


def _extract_summary(
    *,
    execution_result: dict[str, Any],
    final_context: dict[str, Any],
) -> dict[str, Any]:
    summary: dict[str, Any] = {}

    for key in (
        "workflow_name",
        "execution_id",
        "runtime_id",
        "started_at",
        "completed_at",
        "duration_seconds",
    ):
        value = execution_result.get(
            key,
        )
        if value is not None:
            summary[key] = value

    mode = final_context.get(
        "mode",
    )
    if mode is not None:
        summary["mode"] = mode

    context_version = final_context.get(
        "context_version",
    )
    if context_version is not None:
        summary["context_version"] = context_version

    return summary


def _workflow_inputs_from_context(
    final_context: dict[str, Any],
) -> dict[str, Any]:
    return _as_mapping(
        final_context.get(
            "workflow_inputs",
        )
    )


def _extract_morning_report_from_workflow_inputs(
    workflow_inputs: dict[str, Any],
) -> dict[str, Any]:
    morning_report = _as_mapping(
        workflow_inputs.get(
            "morning_report",
        )
    )
    result = morning_report.get(
        "result",
        morning_report,
    )

    return _as_mapping(
        result,
    )
