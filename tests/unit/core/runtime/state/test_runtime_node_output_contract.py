from __future__ import annotations

import pytest

from core.runtime.state.runtime_node_output import RuntimeNodeOutput


def test_runtime_node_output_preserves_contract_identity() -> None:
    output = RuntimeNodeOutput.success_output(
        outputs={"technical_score": 0.12345678901234568},
        output_contract="polaris.market.technical_analysis",
        output_schema_version=1,
    )

    payload = output.to_dict()
    restored = RuntimeNodeOutput.from_dict(payload)

    assert payload["output_contract"] == "polaris.market.technical_analysis"
    assert payload["output_schema_version"] == 1
    assert restored == output


def test_runtime_node_output_loads_legacy_payload_without_contract_identity() -> None:
    restored = RuntimeNodeOutput.from_dict(
        {
            "success": True,
            "outputs": {"score": 0.12345678901234568},
            "execution_metadata": {"node_name": "technical_agent"},
        }
    )

    assert restored.output_contract is None
    assert restored.output_schema_version is None
    assert restored.outputs == {"score": 0.12345678901234568}


def test_runtime_node_output_rejects_invalid_contract_identity() -> None:
    with pytest.raises(ValueError, match="output_schema_version is required"):
        RuntimeNodeOutput.success_output(
            outputs={},
            output_contract="polaris.market.technical_analysis",
        )

    with pytest.raises(ValueError, match="output_schema_version must be positive"):
        RuntimeNodeOutput.success_output(
            outputs={},
            output_contract="polaris.market.technical_analysis",
            output_schema_version=0,
        )
