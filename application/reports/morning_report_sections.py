from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

BoundaryMapping = Mapping[str, Any]


# ============================================================
# WORKFLOW RESULT EXTRACTION HELPERS
# ============================================================


def get_node_outputs(
    workflow_result: BoundaryMapping,
    node_name: str,
) -> dict[str, Any]:
    """
    Return a node's canonical RuntimeNodeOutput.outputs mapping.

    Supports both raw workflow result shape and WorkflowRenderEnvelope.to_dict()
    shape. Empty mapping means node output was unavailable or malformed.
    """

    node_output = get_node_output(
        workflow_result,
        node_name,
    )
    return safe_mapping(
        node_output.get(
            "outputs",
        )
    )


def get_node_metadata(
    workflow_result: BoundaryMapping,
    node_name: str,
) -> dict[str, Any]:
    """
    Return a node's runtime execution metadata without exposing it directly.
    """

    node_output = get_node_output(
        workflow_result,
        node_name,
    )
    return safe_mapping(
        node_output.get(
            "execution_metadata",
        )
    )


def get_node_output(
    workflow_result: BoundaryMapping,
    node_name: str,
) -> dict[str, Any]:
    node_outputs = get_node_outputs_map(
        workflow_result,
    )
    return safe_mapping(
        node_outputs.get(
            node_name,
        )
    )


def get_node_outputs_map(
    workflow_result: BoundaryMapping,
) -> dict[str, Any]:
    """
    Extract the workflow node_outputs mapping from known boundary shapes.
    """

    payload = safe_mapping(
        workflow_result.get(
            "payload",
        )
    )
    payload_node_outputs = safe_mapping(
        payload.get(
            "node_outputs",
        )
    )
    if payload_node_outputs:
        return payload_node_outputs

    final_context = get_final_context(
        workflow_result,
    )
    return safe_mapping(
        final_context.get(
            "node_outputs",
        )
    )


def get_final_context(
    workflow_result: BoundaryMapping,
) -> dict[str, Any]:
    execution_result = safe_mapping(
        workflow_result.get(
            "execution_result",
        )
    )
    final_context = safe_mapping(
        execution_result.get(
            "final_context",
        )
    )
    if final_context:
        return final_context

    raw_result = safe_mapping(
        workflow_result.get(
            "raw_result",
        )
    )
    raw_execution_result = safe_mapping(
        raw_result.get(
            "execution_result",
        )
    )
    return safe_mapping(
        raw_execution_result.get(
            "final_context",
        )
    )


def get_workflow_inputs(
    workflow_result: BoundaryMapping,
) -> dict[str, Any]:
    payload = safe_mapping(
        workflow_result.get(
            "payload",
        )
    )
    workflow_inputs = safe_mapping(
        payload.get(
            "workflow_inputs",
        )
    )
    if workflow_inputs:
        return workflow_inputs

    return safe_mapping(
        get_final_context(
            workflow_result,
        ).get(
            "workflow_inputs",
        )
    )


def get_execution_id(
    workflow_result: BoundaryMapping,
) -> str:
    return first_text(
        workflow_result.get(
            "execution_id",
        ),
        safe_mapping(
            workflow_result.get(
                "summary",
            )
        ).get(
            "execution_id",
        ),
        safe_mapping(
            workflow_result.get(
                "execution_result",
            )
        ).get(
            "execution_id",
        ),
        get_final_context(
            workflow_result,
        ).get(
            "execution_id",
        ),
        fallback="unknown",
    )


def get_workflow_status(
    workflow_result: BoundaryMapping,
) -> str:
    return first_text(
        workflow_result.get(
            "status",
        ),
        safe_mapping(
            workflow_result.get(
                "execution_result",
            )
        ).get(
            "status",
        ),
        fallback="unknown",
    )


def get_symbol(
    workflow_result: BoundaryMapping,
    *,
    fallback: str = "SPY",
) -> str:
    workflow_inputs = get_workflow_inputs(
        workflow_result,
    )
    return first_text(
        workflow_inputs.get(
            "symbol",
        ),
        safe_mapping(
            workflow_result.get(
                "summary",
            )
        ).get(
            "symbol",
        ),
        fallback=fallback,
    )


# ============================================================
# SAFE VALUE HELPERS
# ============================================================


def safe_mapping(
    value: Any,
) -> dict[str, Any]:
    if isinstance(
        value,
        Mapping,
    ):
        return dict(
            value,
        )

    return {}


def safe_score(
    value: Any,
) -> float | None:
    if value is None or isinstance(
        value,
        bool,
    ):
        return None

    try:
        return float(
            value,
        )
    except (TypeError, ValueError):
        return None


def safe_text(
    value: Any,
    *,
    fallback: str = "",
) -> str:
    if value is None:
        return fallback

    text = str(
        value,
    ).strip()
    return text or fallback


def safe_list(
    value: Any,
) -> tuple[str, ...]:
    if value is None:
        return ()

    if isinstance(
        value,
        str,
    ):
        text = value.strip()
        return (text,) if text else ()

    if isinstance(
        value,
        Mapping,
    ):
        text = _mapping_to_summary_text(
            value,
        )
        return (text,) if text else ()

    if isinstance(
        value,
        Sequence,
    ):
        items: list[str] = []
        for item in value:
            text = safe_text(
                _coerce_list_item(
                    item,
                )
            )
            if text:
                items.append(
                    text,
                )
        return tuple(
            items,
        )

    text = safe_text(
        value,
    )
    return (text,) if text else ()


def first_text(
    *values: Any,
    fallback: str = "",
) -> str:
    for value in values:
        text = safe_text(
            value,
        )
        if text:
            return text

    return fallback


def first_score(
    *values: Any,
) -> float | None:
    for value in values:
        score = safe_score(
            value,
        )
        if score is not None:
            return score

    return None


def get_path(
    mapping: BoundaryMapping,
    *path: str,
) -> Any:
    current: Any = mapping
    for key in path:
        current_mapping = safe_mapping(
            current,
        )
        if not current_mapping:
            return None
        current = current_mapping.get(
            key,
        )

    return current


def summarize_long_text(
    text: str,
    max_chars: int = 1200,
) -> str:
    clean = " ".join(
        text.split(),
    )
    if (
        len(
            clean,
        )
        <= max_chars
    ):
        return clean

    truncated = clean[: max_chars - 1].rstrip()
    sentence_end = max(
        truncated.rfind("."),
        truncated.rfind("!"),
        truncated.rfind("?"),
    )
    if sentence_end >= max_chars // 2:
        truncated = truncated[: sentence_end + 1]

    return f"{truncated}…"


# ============================================================
# INTERNAL NORMALIZATION HELPERS
# ============================================================


def _coerce_list_item(
    item: Any,
) -> Any:
    if isinstance(
        item,
        Mapping,
    ):
        return first_text(
            item.get(
                "title",
            ),
            item.get(
                "headline",
            ),
            item.get(
                "summary",
            ),
            item.get(
                "description",
            ),
            item.get(
                "text",
            ),
            _mapping_to_summary_text(
                item,
            ),
        )

    return item


def _mapping_to_summary_text(
    value: Mapping[str, Any],
) -> str:
    parts: list[str] = []
    for key, item in value.items():
        if (
            item is None
            or isinstance(
                item,
                (Mapping, Sequence),
            )
            and not isinstance(
                item,
                str,
            )
        ):
            continue

        item_text = safe_text(
            item,
        )
        if item_text:
            parts.append(
                f"{key}: {item_text}",
            )

    return "; ".join(
        parts,
    )
