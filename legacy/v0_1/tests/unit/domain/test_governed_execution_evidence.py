import pytest

from domain.authority import RiskTier, classify_risk_authority
from domain.governed_execution_evidence import (
    BaselineRuntimeEvidence,
    BaselineRuntimeEvidenceValidationError,
)
from tests.helpers.risk_authority_examples import authority_input_for_tier


def test_baseline_runtime_evidence_binds_baseline_authority_and_provenance() -> None:
    authority = classify_risk_authority(authority_input_for_tier(RiskTier.BASELINE))
    evidence = BaselineRuntimeEvidence(
        evidence_id="baseline-evidence-1",
        authority=authority,
        workflow_name="governance-test-workflow",
        workflow_version="1",
        execution_id="execution-one",
        provenance_digest=BaselineRuntimeEvidence.calculate_provenance_digest(
            authority=authority,
            workflow_name="governance-test-workflow",
            workflow_version="1",
            execution_id="execution-one",
        ),
    )

    assert evidence.authority is authority


def test_baseline_runtime_evidence_rejects_non_baseline_authority() -> None:
    authority = classify_risk_authority(authority_input_for_tier(RiskTier.ENHANCED))

    with pytest.raises(BaselineRuntimeEvidenceValidationError):
        BaselineRuntimeEvidence(
            evidence_id="baseline-evidence-1",
            authority=authority,
            workflow_name="governance-test-workflow",
            workflow_version="1",
            execution_id="execution-one",
            provenance_digest=BaselineRuntimeEvidence.calculate_provenance_digest(
                authority=authority,
                workflow_name="governance-test-workflow",
                workflow_version="1",
                execution_id="execution-one",
            ),
        )
