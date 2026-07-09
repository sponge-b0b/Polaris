from __future__ import annotations

import json

from core.storage.persistence.agent_signals import AgentSignalRecord


def render_agent_signal_text(
    signal: AgentSignalRecord,
) -> str:
    lines = [
        f"# {agent_signal_title(signal)}",
        "",
        f"Agent: {signal.agent_name}",
        f"Agent Type: {signal.agent_type}",
        f"Timestamp: {signal.timestamp.isoformat()}",
    ]
    _append_optional_line(
        lines,
        "Workflow",
        signal.workflow_name,
    )
    _append_optional_line(
        lines,
        "Execution ID",
        signal.execution_id,
    )
    _append_optional_line(
        lines,
        "Runtime ID",
        signal.runtime_id,
    )
    _append_optional_line(
        lines,
        "Node",
        signal.node_name,
    )
    _append_optional_line(
        lines,
        "Symbol",
        signal.symbol,
    )
    if signal.universe:
        lines.append(f"Universe: {', '.join(signal.universe)}")
    _append_optional_line(
        lines,
        "Directional Score",
        _format_optional_float(
            signal.directional_score,
        ),
    )
    _append_optional_line(
        lines,
        "Confidence",
        _format_optional_float(
            signal.confidence,
        ),
    )
    _append_optional_line(
        lines,
        "Regime",
        signal.regime,
    )

    _append_json_section(
        lines,
        "Signals",
        signal.signals,
    )
    _append_json_section(
        lines,
        "Risks",
        signal.risks,
    )
    _append_json_section(
        lines,
        "Recommendations",
        signal.recommendations,
    )
    _append_json_section(
        lines,
        "Features",
        signal.features,
    )
    _append_text_section(
        lines,
        "Reasoning",
        signal.reasoning_text,
    )
    _append_text_section(
        lines,
        "LLM Response",
        signal.llm_response,
    )

    return "\n".join(
        lines,
    )


def agent_signal_title(
    signal: AgentSignalRecord,
) -> str:
    if signal.symbol is not None and signal.symbol.strip():
        return f"{signal.agent_name} Signal - {signal.symbol.strip()}"

    return f"{signal.agent_name} Signal"


def _append_optional_line(
    lines: list[str],
    label: str,
    value: str | None,
) -> None:
    if value is not None and value.strip():
        lines.append(f"{label}: {value}")


def _append_json_section(
    lines: list[str],
    title: str,
    payload: object,
) -> None:
    if not payload:
        return

    lines.extend(
        [
            "",
            f"## {title}",
            "",
            json.dumps(
                payload,
                indent=2,
                sort_keys=True,
            ),
        ]
    )


def _append_text_section(
    lines: list[str],
    title: str,
    text: str | None,
) -> None:
    if text is None or not text.strip():
        return

    lines.extend(
        [
            "",
            f"## {title}",
            "",
            text,
        ]
    )


def _format_optional_float(
    value: float | None,
) -> str | None:
    if value is None:
        return None

    return f"{value:.4f}"
