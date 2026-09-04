from __future__ import annotations

from application.observability.risk_authority import (
    risk_authority_attributes,
    risk_authority_metadata_payload,
    risk_authority_payload,
)
from domain.authority import classify_risk_authority
from tests.helpers.risk_authority_examples import workflow_curation_authority_input


def test_risk_authority_attributes_flatten_contract_for_operational_boundaries() -> (
    None
):
    contract = classify_risk_authority(workflow_curation_authority_input())

    attributes = risk_authority_attributes(
        contract,
        observable_reason="prohibited_outside_authority",
    )
    payload = risk_authority_payload(contract)

    assert attributes["authority_risk_tier"] == "enhanced"
    assert attributes["authority_effect"] == "canonical_record"
    assert attributes["authority_owner"] == "workflow_output_curation"
    assert attributes["authority_sink"] == "durable_domain_record"
    assert attributes["authority_source_of_truth_category"] == (
        "canonical_domain_record"
    )
    assert attributes["authority_gate_profile"] == "enhanced_provenance"
    assert attributes["authority_observable_reason"] == "prohibited_outside_authority"
    assert payload["risk_authority"]["risk_tier"] == "enhanced"


def test_risk_authority_metadata_payload_sanitizes_untrusted_metadata_values() -> None:
    class UnsupportedPayloadValue:
        pass

    payload = risk_authority_metadata_payload(
        {
            "risk_tier": "enhanced",
            "nested": {"value": UnsupportedPayloadValue()},
            "claims": ("risk_tier", UnsupportedPayloadValue()),
        }
    )

    risk_authority = payload["risk_authority"]
    assert risk_authority["risk_tier"] == "enhanced"
    assert "UnsupportedPayloadValue" in risk_authority["nested"]["value"]
    assert risk_authority["claims"][0] == "risk_tier"
    assert "UnsupportedPayloadValue" in risk_authority["claims"][1]
