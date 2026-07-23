from __future__ import annotations

from collections.abc import Mapping

from intelligence.strategy.hypothesis.context import StrategyEvidenceContext

STRATEGY_EVIDENCE_BUILDER_NODE = "strategy_evidence_builder"
STRATEGY_EVIDENCE_CONTEXT_OUTPUT = "strategy_evidence_context"


def strategy_evidence_context_from_node_outputs(
    node_outputs: Mapping[str, object],
    *,
    consumer_name: str,
) -> StrategyEvidenceContext:
    """Load the canonical strategy evidence context from runtime node outputs."""

    raw_output = node_outputs.get(STRATEGY_EVIDENCE_BUILDER_NODE)
    if raw_output is None:
        raise ValueError(
            f"{consumer_name} requires '{STRATEGY_EVIDENCE_BUILDER_NODE}' "
            "in node_outputs."
        )

    outputs = _unwrap_outputs(raw_output)
    payload = outputs.get(STRATEGY_EVIDENCE_CONTEXT_OUTPUT)
    if not isinstance(payload, Mapping):
        raise ValueError(
            f"{consumer_name} requires '{STRATEGY_EVIDENCE_BUILDER_NODE}' "
            f"to produce '{STRATEGY_EVIDENCE_CONTEXT_OUTPUT}'."
        )

    return StrategyEvidenceContext.from_dict(_mapping_to_dict(payload))


def _unwrap_outputs(raw_output: object) -> Mapping[str, object]:
    object_outputs = getattr(raw_output, "outputs", None)
    if isinstance(object_outputs, Mapping):
        return object_outputs
    if isinstance(raw_output, Mapping):
        nested_outputs = raw_output.get("outputs")
        if isinstance(nested_outputs, Mapping):
            return nested_outputs
        return raw_output
    return {}


def _mapping_to_dict(value: Mapping[object, object]) -> dict[str, object]:
    return {str(key): mapped_value for key, mapped_value in value.items()}
