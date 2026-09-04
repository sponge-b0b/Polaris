from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from domain.authority import RISK_AUTHORITY_METADATA_KEY, RiskAuthorityContract

_AUTHORITY_METADATA_LABELS: Mapping[str, str] = {
    "risk_tier": "authority_risk_tier",
    "authority_effect": "authority_effect",
    "content_type": "authority_content_type",
    "canonical_owner": "authority_canonical_owner",
    "source_of_truth": "authority_source_of_truth",
    "intended_sink": "authority_intended_sink",
    "gate_profile": "authority_gate_profile",
    "capital_relevant": "authority_capital_relevant",
    "durable_authority": "authority_durable_authority",
    "externally_visible": "authority_externally_visible",
    "governance_impact": "authority_governance_impact",
    "evidence_sufficient": "authority_evidence_sufficient",
}


def risk_authority_attributes(
    authority_contract: RiskAuthorityContract | None,
    *,
    observable_reason: str | None = None,
    gate_status: str | None = None,
    failure_mode: str | None = None,
) -> dict[str, object]:
    """Flatten canonical authority metadata for bounded logs, traces, and metrics."""

    authority_metadata = None
    if authority_contract is not None:
        authority_metadata = authority_contract.to_metadata()
    return risk_authority_metadata_attributes(
        authority_metadata,
        observable_reason=observable_reason,
        gate_status=gate_status,
        failure_mode=failure_mode,
    )


def risk_authority_metadata_attributes(
    authority_metadata: Mapping[str, object] | None,
    *,
    observable_reason: str | None = None,
    gate_status: str | None = None,
    failure_mode: str | None = None,
) -> dict[str, object]:
    """Flatten serialized authority metadata for operational observations.

    The returned attributes are deliberately scalar so the same mapping can be
    reused for logs, spans, event attributes, and metric labels without adding a
    parallel telemetry vocabulary at every boundary.
    """

    attributes: dict[str, object] = {}
    if authority_metadata is not None:
        attributes["authority_metadata_present"] = True
        for metadata_key, attribute_key in _AUTHORITY_METADATA_LABELS.items():
            if metadata_key in authority_metadata:
                value = authority_metadata[metadata_key]
                if _is_observable_scalar(value):
                    attributes[attribute_key] = value
        _add_aliases(attributes, authority_metadata)
        attributes["authority_ignored_model_authority_claim_count"] = _claim_count(
            authority_metadata.get("ignored_model_authority_claims")
        )
    elif observable_reason or gate_status or failure_mode:
        attributes["authority_metadata_present"] = False

    if observable_reason:
        attributes["authority_observable_reason"] = observable_reason
    if gate_status:
        attributes["authority_gate_status"] = gate_status
    if failure_mode:
        attributes["authority_failure_mode"] = failure_mode
    return attributes


def risk_authority_payload(
    authority_contract: RiskAuthorityContract | None,
) -> dict[str, Any]:
    """Return nested authority metadata for event payloads at owner boundaries."""

    if authority_contract is None:
        return {}
    return {RISK_AUTHORITY_METADATA_KEY: authority_contract.to_metadata()}


def risk_authority_metadata_payload(
    authority_metadata: Mapping[str, object] | None,
) -> dict[str, Any]:
    """Return nested serialized authority metadata for event payloads."""

    if authority_metadata is None:
        return {}
    return {
        RISK_AUTHORITY_METADATA_KEY: {
            str(key): _payload_value(value) for key, value in authority_metadata.items()
        }
    }


def _add_aliases(
    attributes: dict[str, object],
    authority_metadata: Mapping[str, object],
) -> None:
    owner = authority_metadata.get("canonical_owner")
    if _is_observable_scalar(owner):
        attributes["authority_owner"] = owner
    sink = authority_metadata.get("intended_sink")
    if _is_observable_scalar(sink):
        attributes["authority_sink"] = sink
    source = authority_metadata.get("source_of_truth")
    if _is_observable_scalar(source):
        attributes["authority_source_of_truth_category"] = source


def _claim_count(value: object) -> int:
    if isinstance(value, str):
        return 1
    if isinstance(value, list | tuple):
        return len(value)
    return 0


def _is_observable_scalar(value: object) -> bool:
    return isinstance(value, str | int | float | bool)


def _payload_value(value: object) -> object:
    if value is None or _is_observable_scalar(value):
        return value
    if isinstance(value, Mapping):
        return {str(key): _payload_value(nested) for key, nested in value.items()}
    if isinstance(value, list | tuple):
        return [_payload_value(item) for item in value]
    return str(value)
