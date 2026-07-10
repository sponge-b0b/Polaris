from __future__ import annotations

from typing import Mapping

from core.runtime.contracts.runtime_node import RuntimeNode
from core.runtime.state.runtime_context import RuntimeContext
from core.runtime.state.runtime_node_output import RuntimeNodeOutput
from intelligence.strategy.bear.bear_hypothesis_policy import build_bear_hypothesis
from intelligence.strategy.hypothesis.context import StrategyEvidenceContext


class BearAgent(RuntimeNode):
    """
    Polaris Bear Agent

    Produces the bear strategy perspective from the canonical shared
    StrategyEvidenceContext created by StrategyEvidenceBuilder.
    """

    node_name = "bear_agent"
    node_type = "bear_strategy"

    async def _execute(
        self,
        context: RuntimeContext,
    ) -> RuntimeNodeOutput:
        evidence_context = _strategy_evidence_context_from_runtime(
            context.node_outputs,
        )
        decision = build_bear_hypothesis(evidence_context)

        return RuntimeNodeOutput.success_output(
            outputs=decision.to_runtime_outputs(),
            execution_metadata={
                "node_name": self.node_name,
                "node_type": self.node_type,
                "confidence": decision.hypothesis.confidence,
                "evidence_fingerprint": decision.hypothesis.evidence_fingerprint,
                "hypothesis_strength": decision.hypothesis.hypothesis_strength,
                "invalidated": decision.hypothesis.invalidated,
            },
            output_contract="StrategyHypothesis",
            output_schema_version=1,
        )


def _strategy_evidence_context_from_runtime(
    node_outputs: Mapping[str, object],
) -> StrategyEvidenceContext:
    raw_output = node_outputs.get("strategy_evidence_builder")
    if raw_output is None:
        raise ValueError(
            "BearAgent requires 'strategy_evidence_builder' in node_outputs."
        )

    outputs = _unwrap_outputs(raw_output)
    payload = outputs.get("strategy_evidence_context")
    if not isinstance(payload, Mapping):
        raise ValueError(
            "BearAgent requires 'strategy_evidence_builder' to produce "
            "'strategy_evidence_context'."
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
