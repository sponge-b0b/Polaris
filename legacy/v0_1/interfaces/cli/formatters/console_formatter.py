from __future__ import annotations

from typing import Any

from interfaces.cli.formatters.json_formatter import format_json
from interfaces.cli.formatters.workflow_payload import (
    additional_workflow_payload,
    ensure_workflow_render_envelope,
    workflow_morning_report,
    workflow_node_outputs,
)


def format_workflow_list(
    summaries: list[dict[str, Any]],
) -> str:
    if not summaries:
        return "No workflows registered."

    lines = ["Registered workflows:"]

    for summary in summaries:
        workflow_name = summary.get(
            "workflow_name",
            "",
        )
        description = summary.get(
            "description",
            "",
        )
        tags = summary.get(
            "tags",
            [],
        )

        tag_text = f" [{', '.join(tags)}]" if tags else ""

        suffix = f" - {description}" if description else ""

        lines.append(f"- {workflow_name}{tag_text}{suffix}")

    return "\n".join(lines)


def format_workflow_run(
    result: Any,
) -> str:
    envelope = ensure_workflow_render_envelope(
        result,
    )

    lines = [
        f"Workflow: {envelope.workflow_name}",
        f"Execution: {envelope.execution_id}",
        f"Success: {envelope.success}",
        f"Status: {envelope.status}",
    ]

    if envelope.error_message:
        lines.append(f"Error: {envelope.error_message}")

    if envelope.failed_nodes:
        lines.append(f"Failed nodes: {', '.join(envelope.failed_nodes)}")

    morning_report = workflow_morning_report(
        envelope,
    )

    if morning_report:
        lines.extend(
            [
                "",
                f"Symbol: {morning_report.get('symbol')}",
                f"Generated: {morning_report.get('generated_at')}",
                "",
                str(morning_report.get("summary", "")),
            ]
        )

        risks = morning_report.get(
            "risks",
            [],
        )
        if risks:
            lines.extend(
                [
                    "",
                    "Risks:",
                    *[f"- {risk}" for risk in risks],
                ]
            )

        opportunities = morning_report.get(
            "opportunities",
            [],
        )
        if opportunities:
            lines.extend(
                [
                    "",
                    "Opportunities:",
                    *[f"- {opportunity}" for opportunity in opportunities],
                ]
            )

    node_outputs = workflow_node_outputs(
        envelope,
    )

    if node_outputs:
        lines.extend(
            [
                "",
                "Runtime Node Outputs:",
            ]
        )
        for node_name, node_output in node_outputs.items():
            lines.extend(
                [
                    "",
                    f"Node: {node_name}",
                    _format_indented_json(
                        node_output,
                    ),
                ]
            )

    remaining_payload = additional_workflow_payload(
        envelope,
    )
    if remaining_payload:
        lines.extend(
            [
                "",
                "Additional Workflow Output:",
                _format_indented_json(
                    remaining_payload,
                ),
            ]
        )

    if envelope.errors:
        lines.extend(
            [
                "",
                "Errors:",
            ]
        )
        lines.extend(
            _format_error_line(
                error,
            )
            for error in envelope.errors
        )

    return "\n".join(lines)


def _format_indented_json(
    value: Any,
) -> str:
    return "\n".join(
        f"  {line}"
        for line in format_json(
            value,
        ).splitlines()
    )


def _format_error_line(
    error: Any,
) -> str:
    prefix = "-"
    if error.node_name:
        prefix = f"- [{error.node_name}]"

    suffix_parts: list[str] = []
    if error.error_type:
        suffix_parts.append(
            error.error_type,
        )

    if error.details:
        suffix_parts.append(
            str(
                error.details,
            )
        )

    suffix = f" ({'; '.join(suffix_parts)})" if suffix_parts else ""

    return f"{prefix} {error.message}{suffix}"


def format_mapping(
    title: str,
    values: dict[str, Any],
) -> str:
    lines = [title]

    for key, value in values.items():
        lines.append(f"- {key}: {value}")

    return "\n".join(lines)
