from __future__ import annotations

from copy import deepcopy

from core.runtime.state.runtime_node_output import RuntimeNodeOutput
from intelligence.analysts.technical.technical_breadth_context import (
    TechnicalBreadthContext,
)


def breadth_signal_tags(
    breadth_context: TechnicalBreadthContext,
) -> list[str]:
    """Build canonical explanatory tags for risk-node breadth context."""

    if not breadth_context.has_breadth_data:
        return []

    return [
        f"breadth:{breadth_context.breadth_regime}",
        f"breadth_risk:{breadth_context.breadth_risk_score}",
        f"breadth_confirmation:{breadth_context.confirmation_score}",
        f"price_ad_divergence:{str(breadth_context.price_ad_divergence).lower()}",
    ]


def deduplicate_strings(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def annotate_risk_runtime_output(
    *,
    runtime_output: RuntimeNodeOutput,
    breadth_context: TechnicalBreadthContext,
) -> RuntimeNodeOutput:
    """Add canonical breadth signals and risks at the runtime boundary."""

    if not breadth_context.has_breadth_data:
        return runtime_output

    outputs = deepcopy(runtime_output.outputs)
    outputs["signals"] = deduplicate_strings(
        list(outputs.get("signals", [])) + breadth_signal_tags(breadth_context)
    )
    outputs["risks"] = deduplicate_strings(
        list(outputs.get("risks", [])) + list(breadth_context.risk_flags())
    )
    outputs["recommendations"] = deduplicate_strings(
        list(outputs.get("recommendations", []))
    )

    return RuntimeNodeOutput.success_output(
        outputs=outputs,
        execution_metadata=runtime_output.execution_metadata,
        output_contract=runtime_output.output_contract,
        output_schema_version=runtime_output.output_schema_version,
    )
