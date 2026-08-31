from __future__ import annotations

from dataclasses import replace

import pytest

from application.evaluations.model_replacement_gate import (
    MODEL_REPLACEMENT_DATASET_SLICE_NAME,
)
from application.evaluations.readiness_gate import (
    ReadinessSection,
    ReadinessSectionStatus,
    ReadinessVerdictStatus,
)
from application.evaluations.readiness_profiles import ReadinessRunMode
from application.evaluations.risk_authority_gate import RiskAuthorityGateEvidence
from tests.unit.application.evaluations.test_enhanced_readiness import (
    _rag_answer_dataset_definition,
    _request,
    _section_status,
    _seed_repository,
    _service,
)


@pytest.mark.asyncio
async def test_authority_preserves_validated_metric_result_count() -> None:
    repository = _seed_repository()
    first = repository.metrics["current-run"][0]
    repository.metrics["current-run"] = (
        *repository.metrics["current-run"],
        replace(
            first,
            metric_result_id="current-run-extra-metric-result",
            case_id="current-run-extra-case",
        ),
    )
    repository.runs["current-run"] = replace(
        repository.runs["current-run"],
        case_ids=("current-run-case", "current-run-extra-case"),
    )

    verdict = await _service(repository).evaluate(_request())

    assert verdict.status is ReadinessVerdictStatus.PASSED
    assert verdict.evidence.authority.metric_result_count == sum(
        len(repository.metrics[run_id])
        for run_id in verdict.evidence.authority.evaluation_run_ids
    )


@pytest.mark.asyncio
async def test_missing_required_dataset_fails_closed() -> None:
    repository = _seed_repository()
    definition = _rag_answer_dataset_definition()
    repository.datasets.pop(definition.reference.dataset_id)

    verdict = await _service(repository).evaluate(_request())

    assert verdict.status is ReadinessVerdictStatus.FAILED
    assert _section_status(verdict, ReadinessSection.DATASETS) is (
        ReadinessSectionStatus.FAILED
    )


@pytest.mark.asyncio
async def test_missing_required_artifact_fails_closed() -> None:
    repository = _seed_repository()
    repository.artifacts = [
        item
        for item in repository.artifacts
        if item.artifact_type != "structured_output_conformance"
    ]

    verdict = await _service(repository).evaluate(_request())

    assert verdict.status is ReadinessVerdictStatus.FAILED
    assert _section_status(verdict, ReadinessSection.ARTIFACTS) is (
        ReadinessSectionStatus.FAILED
    )


@pytest.mark.asyncio
async def test_unversioned_required_artifact_fails_closed() -> None:
    repository = _seed_repository()
    repository.artifacts = [
        replace(item, payload={"evidence": "present"})
        if item.artifact_type == "structured_output_conformance"
        else item
        for item in repository.artifacts
    ]

    verdict = await _service(repository).evaluate(_request())

    assert verdict.status is ReadinessVerdictStatus.FAILED
    assert _section_status(verdict, ReadinessSection.ARTIFACTS) is (
        ReadinessSectionStatus.FAILED
    )


@pytest.mark.asyncio
async def test_missing_provenance_packet_fails_closed() -> None:
    repository = _seed_repository()
    request = replace(
        _request(),
        authority_evidence=RiskAuthorityGateEvidence(
            provenance_record_ids=("rag-source-1",),
        ),
    )

    verdict = await _service(repository).evaluate(request)

    assert verdict.status is ReadinessVerdictStatus.FAILED
    assert _section_status(verdict, ReadinessSection.AUTHORITY) is (
        ReadinessSectionStatus.FAILED
    )
    assert _section_status(verdict, ReadinessSection.ARTIFACTS) is (
        ReadinessSectionStatus.FAILED
    )


@pytest.mark.asyncio
async def test_missing_model_replacement_evidence_fails_closed() -> None:
    repository = _seed_repository()

    verdict = await _service(repository).evaluate(
        _request(run_mode=ReadinessRunMode.MODEL_PROFILE_REPLACEMENT)
    )

    assert verdict.status is ReadinessVerdictStatus.FAILED
    assert _section_status(verdict, ReadinessSection.DATASETS) is (
        ReadinessSectionStatus.FAILED
    )
    assert not any(
        item.name == MODEL_REPLACEMENT_DATASET_SLICE_NAME
        for item in verdict.evidence.datasets
    )
