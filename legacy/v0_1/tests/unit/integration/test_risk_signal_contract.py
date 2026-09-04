from __future__ import annotations

from dataclasses import FrozenInstanceError
from math import inf, nan
from typing import Any

import pytest

from integration.adapters.risk import risk_runtime_adapter
from integration.contracts.risk.risk_signal_contract import RiskSignalContract

UNIT_RISK_FIELDS = (
    "volatility_risk",
    "drawdown_risk",
    "exposure_risk",
    "composite_risk",
    "risk_pressure",
    "stability_score",
)


def test_risk_signal_contract_accepts_unit_risk_and_stability_values() -> None:
    contract = RiskSignalContract(
        volatility_risk=0.0,
        drawdown_risk=0.20,
        exposure_risk=0.40,
        composite_risk=0.60,
        risk_pressure=0.80,
        stability_score=1.0,
    )

    assert contract.volatility_risk == 0.0
    assert contract.drawdown_risk == 0.20
    assert contract.exposure_risk == 0.40
    assert contract.composite_risk == 0.60
    assert contract.risk_pressure == 0.80
    assert contract.stability_score == 1.0


@pytest.mark.parametrize("field_name", UNIT_RISK_FIELDS)
@pytest.mark.parametrize("invalid_value", (-0.01, 1.01, True, False, nan, inf, -inf))
def test_risk_signal_contract_rejects_invalid_unit_values(
    field_name: str,
    invalid_value: Any,
) -> None:
    payload: dict[str, Any] = {field_name: invalid_value}

    with pytest.raises(ValueError):
        RiskSignalContract(**payload)


def test_risk_signal_contract_from_dict_rejects_boolean_risk_values() -> None:
    with pytest.raises(ValueError):
        RiskSignalContract.from_dict({"composite_risk": True})


def test_risk_signal_contract_from_dict_round_trips_boundary_payload() -> None:
    contract = RiskSignalContract.from_dict(
        {
            "volatility_risk": 0.12,
            "drawdown_risk": 0.23,
            "exposure_risk": 0.34,
            "composite_risk": 0.45,
            "risk_regime": "elevated",
            "risk_pressure": 0.56,
            "stability_score": 0.44,
            "risk_bias": "risk_off",
            "recommendations": ["reduce_exposure"],
            "features": {"source": "risk_aggregator_agent"},
        }
    )

    assert contract.to_dict() == {
        "volatility_risk": 0.12,
        "drawdown_risk": 0.23,
        "exposure_risk": 0.34,
        "composite_risk": 0.45,
        "risk_regime": "elevated",
        "risk_pressure": 0.56,
        "stability_score": 0.44,
        "risk_bias": "risk_off",
        "recommendations": ["reduce_exposure"],
        "features": {"source": "risk_aggregator_agent"},
    }


def test_risk_runtime_adapter_maps_unit_risk_to_signed_direction() -> None:
    output = risk_runtime_adapter.to_runtime_output(
        node_name="risk_aggregator_agent",
        node_type="risk",
        contract=RiskSignalContract(
            volatility_risk=0.25,
            drawdown_risk=0.50,
            exposure_risk=0.75,
            composite_risk=0.75,
            risk_pressure=0.65,
            stability_score=0.25,
            risk_regime="high_risk",
        ),
    )

    assert output.outputs["directional_score"] == -0.75
    assert output.outputs["confidence"] == 0.25
    assert output.execution_metadata["confidence"] == 0.25
    assert output.outputs["features"]["composite_risk"] == 0.75
    assert output.outputs["features"]["risk_pressure"] == 0.65
    assert output.outputs["features"]["stability_score"] == 0.25


def test_risk_signal_contract_is_immutable() -> None:
    contract = RiskSignalContract(composite_risk=0.25)

    contract_as_any: Any = contract

    with pytest.raises(FrozenInstanceError):
        contract_as_any.composite_risk = 0.50
