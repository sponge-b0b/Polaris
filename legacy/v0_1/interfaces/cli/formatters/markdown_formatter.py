from __future__ import annotations

from typing import Any

from interfaces.cli.formatters.json_formatter import format_json
from interfaces.cli.formatters.workflow_payload import (
    additional_workflow_payload,
    ensure_workflow_render_envelope,
    workflow_morning_report,
    workflow_node_outputs,
)


def format_workflow_run_markdown(
    result: Any,
) -> str:
    envelope = ensure_workflow_render_envelope(
        result,
    )

    lines = [
        f"# {envelope.workflow_name}",
        "",
        f"- Execution: `{envelope.execution_id}`",
        f"- Success: `{envelope.success}`",
        f"- Status: `{envelope.status}`",
    ]

    if envelope.error_message:
        lines.append(f"- Error: `{envelope.error_message}`")

    morning_report = workflow_morning_report(
        envelope,
    )

    if morning_report:
        lines.extend(
            [
                "",
                "## Summary",
                "",
                f"Symbol: `{morning_report.get('symbol')}`",
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
                    "## Risks",
                    "",
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
                    "## Opportunities",
                    "",
                    *[f"- {opportunity}" for opportunity in opportunities],
                ]
            )

    if envelope.failed_nodes:
        lines.extend(
            [
                "",
                "## Failed Nodes",
                "",
                *[f"- `{node}`" for node in envelope.failed_nodes],
            ]
        )

    node_outputs = workflow_node_outputs(
        envelope,
    )

    if node_outputs:
        lines.extend(
            [
                "",
                "## Runtime Node Outputs",
            ]
        )
        for node_name, node_output in node_outputs.items():
            lines.extend(
                [
                    "",
                    f"### `{node_name}`",
                    "",
                    "```json",
                    format_json(
                        node_output,
                    ),
                    "```",
                ]
            )

    remaining_payload = additional_workflow_payload(
        envelope,
    )
    if remaining_payload:
        lines.extend(
            [
                "",
                "## Additional Workflow Output",
                "",
                "```json",
                format_json(
                    remaining_payload,
                ),
                "```",
            ]
        )

    if envelope.errors:
        lines.extend(
            [
                "",
                "## Errors",
                "",
            ]
        )
        lines.extend(
            _format_error_line(
                error,
            )
            for error in envelope.errors
        )

    return "\n".join(lines)


def _format_error_line(
    error: Any,
) -> str:
    prefix = "-"
    if error.node_name:
        prefix = f"- `{error.node_name}`:"

    suffix = f" _{error.error_type}_" if error.error_type else ""

    return f"{prefix} {error.message}{suffix}"
