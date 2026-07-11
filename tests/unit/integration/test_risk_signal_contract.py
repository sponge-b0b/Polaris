from __future__ import annotations

from dataclasses import FrozenInstanceError
from typing import Any

import pytest

from integration.contracts.risk.risk_signal_contract import RiskSignalContract


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


def test_risk_signal_contract_is_immutable() -> None:
    contract = RiskSignalContract(composite_risk=0.25)

    contract_as_any: Any = contract

    with pytest.raises(FrozenInstanceError):
        contract_as_any.composite_risk = 0.50
