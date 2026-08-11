"""Typed evidence variants accepted by governed workflow execution."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from domain.authority import RiskAuthorityContract, RiskTier
from domain.decision_evidence import DecisionEvidencePacket

BASELINE_RUNTIME_EVIDENCE_SCHEMA_VERSION = 1


class BaselineRuntimeEvidenceValidationError(ValueError):
    """Raised when Baseline runtime provenance is not canonical."""


@dataclass(frozen=True, slots=True)
class BaselineRuntimeEvidence:
    """Durable authority and runtime provenance for a Baseline execution."""

    evidence_id: str
    authority: RiskAuthorityContract
    workflow_name: str
    workflow_version: str
    provenance_digest: str
    schema_version: int = BASELINE_RUNTIME_EVIDENCE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _validate_identifier(self.evidence_id, "evidence_id")
        _validate_identifier(self.workflow_name, "workflow_name")
        _validate_identifier(self.workflow_version, "workflow_version")
        if self.authority.risk_tier is not RiskTier.BASELINE:
            raise BaselineRuntimeEvidenceValidationError(
                "Baseline runtime evidence requires Baseline authority."
            )
        if self.schema_version < 1:
            raise BaselineRuntimeEvidenceValidationError(
                "schema_version must be positive."
            )
        expected_digest = self.calculate_provenance_digest(
            authority=self.authority,
            workflow_name=self.workflow_name,
            workflow_version=self.workflow_version,
            schema_version=self.schema_version,
        )
        if self.provenance_digest != expected_digest:
            raise BaselineRuntimeEvidenceValidationError(
                "Baseline runtime evidence provenance digest does not match."
            )

    @staticmethod
    def calculate_provenance_digest(
        *,
        authority: RiskAuthorityContract,
        workflow_name: str,
        workflow_version: str,
        schema_version: int = BASELINE_RUNTIME_EVIDENCE_SCHEMA_VERSION,
    ) -> str:
        payload = {
            "authority": authority.to_metadata(),
            "workflow_name": workflow_name,
            "workflow_version": workflow_version,
            "schema_version": schema_version,
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


type GovernedExecutionEvidence = BaselineRuntimeEvidence | DecisionEvidencePacket


def _validate_identifier(value: str, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise BaselineRuntimeEvidenceValidationError(f"{label} must be non-empty.")
