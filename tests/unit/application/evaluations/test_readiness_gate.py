from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from application.evaluations.evaluation_run_service import (
    expected_authority_metadata_for_evaluation_target,
)
from application.evaluations.evaluation_telemetry import EvaluationTelemetry
from application.evaluations.readiness_gate import (
    READINESS_GATE_ARTIFACT_TYPE,
    ReadinessArtifactEvidence,
    ReadinessGateEvidence,
    ReadinessGateRequest,
    ReadinessGateService,
    ReadinessSection,
    ReadinessSectionResult,
    ReadinessSectionStatus,
    ReadinessVerdictStatus,
)
from application.evaluations.readiness_profiles import (
    ReadinessRunMode,
    canonical_readiness_profiles,
)
from core.storage.persistence.evaluation import (
    EvaluationArtifactRecord,
    EvaluationRunRecord,
)
from core.telemetry.observability import ObservabilityManager
from core.telemetry.sinks.telemetry_sink import InMemoryTelemetrySink
from domain.authority import GateProfile, RiskTier
from domain.evaluation import EvaluationStatus, EvaluationTargetType


@dataclass
class _FakeReadinessRepository:
    run: EvaluationRunRecord | None = None
    artifacts: list[EvaluationArtifactRecord] = field(default_factory=list)

    async def get_run(self, run_id: str) -> EvaluationRunRecord | None:
        if self.run is None or self.run.run_id != run_id:
            return None
        return self.run

    async def list_artifacts(
        self,
        run_id: str,
    ) -> tuple[EvaluationArtifactRecord, ...]:
        return tuple(item for item in self.artifacts if item.run_id == run_id)

    async def create_artifact(
        self,
        record: EvaluationArtifactRecord,
    ) -> EvaluationArtifactRecord:
        self.artifacts.append(record)
        return record


def _baseline_evidence() -> ReadinessGateEvidence:
    return ReadinessGateEvidence(
        artifacts=(
            ReadinessArtifactEvidence(
                artifact_type="baseline_architecture_regression",
                artifact_id="baseline-regression-1",
                version="v1",
            ),
        )
    )


def _request(
    *,
    evidence: ReadinessGateEvidence | None = None,
    target_type: EvaluationTargetType = EvaluationTargetType.AGENT_TASK,
    run_mode: ReadinessRunMode = ReadinessRunMode.LOCAL_PR,
    persistence_run_id: str | None = None,
) -> ReadinessGateRequest:
    return ReadinessGateRequest(
        gate_run_id="readiness-1",
        correlation_id="correlation-1",
        target_type=target_type,
        run_mode=run_mode,
        evidence=evidence or _baseline_evidence(),
        persistence_run_id=persistence_run_id,
    )


def _section_status(
    verdict_sections: tuple[ReadinessSectionResult, ...],
    section: ReadinessSection,
) -> ReadinessSectionStatus:
    for item in verdict_sections:
        if item.section is section:
            return item.status
    raise AssertionError(f"Missing readiness section: {section.value}")


def test_readiness_profiles_are_versioned_and_tier_specific() -> None:
    profiles = canonical_readiness_profiles()

    assert [profile.risk_tier for profile in profiles] == [
        RiskTier.BASELINE,
        RiskTier.ENHANCED,
        RiskTier.VIGILANT,
        RiskTier.PROHIBITED_OUTSIDE_AUTHORITY,
    ]
    assert len({profile.profile_version for profile in profiles}) == 4

    baseline, enhanced, vigilant, prohibited = profiles
    assert baseline.gate_profile is GateProfile.BASELINE_INTERNAL
    assert baseline.cadence == (
        ReadinessRunMode.LOCAL_PR,
        ReadinessRunMode.RELEASE,
    )
    assert enhanced.dataset_requirements
    assert enhanced.metric_requirements
    assert all(
        0.0 <= item.minimum_score <= 1.0
        for item in enhanced.metric_requirements
    )
    assert all(
        0.0 <= item.allowed_drift <= 1.0
        for item in enhanced.metric_requirements
    )
    assert vigilant.dataset_requirements
    assert vigilant.metric_requirements
    assert max(item.allowed_drift for item in vigilant.metric_requirements) < max(
        item.allowed_drift for item in enhanced.metric_requirements
    )
    assert vigilant.live_service_requirements
    assert prohibited.gate_profile is GateProfile.PROHIBITED_BOUNDARY


@pytest.mark.asyncio
async def test_baseline_readiness_is_deterministic_and_service_free() -> None:
    verdict = await ReadinessGateService().evaluate(_request())

    assert verdict.status is ReadinessVerdictStatus.PASSED
    assert verdict.profile.gate_profile is GateProfile.BASELINE_INTERNAL
    assert [item.section for item in verdict.sections] == list(ReadinessSection)
    assert _section_status(verdict.sections, ReadinessSection.AUTHORITY) is (
        ReadinessSectionStatus.PASSED
    )
    assert _section_status(verdict.sections, ReadinessSection.ARTIFACTS) is (
        ReadinessSectionStatus.PASSED
    )
    assert _section_status(verdict.sections, ReadinessSection.DATASETS) is (
        ReadinessSectionStatus.SKIPPED
    )
    assert _section_status(verdict.sections, ReadinessSection.METRICS) is (
        ReadinessSectionStatus.SKIPPED
    )
    assert _section_status(verdict.sections, ReadinessSection.LIVE_SERVICES) is (
        ReadinessSectionStatus.SKIPPED
    )
    assert _section_status(verdict.sections, ReadinessSection.PERSISTENCE) is (
        ReadinessSectionStatus.SKIPPED
    )


@pytest.mark.asyncio
async def test_baseline_release_requires_durable_persistence() -> None:
    verdict = await ReadinessGateService().evaluate(
        _request(run_mode=ReadinessRunMode.RELEASE)
    )

    assert verdict.status is ReadinessVerdictStatus.FAILED
    assert _section_status(verdict.sections, ReadinessSection.PERSISTENCE) is (
        ReadinessSectionStatus.FAILED
    )


@pytest.mark.asyncio
async def test_baseline_missing_required_artifact_fails_closed() -> None:
    request = _request(evidence=ReadinessGateEvidence())

    verdict = await ReadinessGateService().evaluate(request)

    assert verdict.status is ReadinessVerdictStatus.FAILED
    assert _section_status(verdict.sections, ReadinessSection.ARTIFACTS) is (
        ReadinessSectionStatus.FAILED
    )
    assert "baseline_architecture_regression" in next(
        item.reason
        for item in verdict.sections
        if item.section is ReadinessSection.ARTIFACTS
    )


@pytest.mark.asyncio
async def test_caller_metadata_cannot_downgrade_selected_profile() -> None:
    baseline_metadata = expected_authority_metadata_for_evaluation_target(
        EvaluationTargetType.AGENT_TASK
    )
    request = ReadinessGateRequest(
        gate_run_id="readiness-downgrade",
        correlation_id="correlation-downgrade",
        target_type=EvaluationTargetType.RAG_ANSWER,
        run_mode=ReadinessRunMode.RELEASE,
        evidence=ReadinessGateEvidence(),
        supplied_authority_metadata=baseline_metadata,
    )

    verdict = await ReadinessGateService().evaluate(request)

    assert verdict.profile.gate_profile is GateProfile.ENHANCED_PROVENANCE
    assert verdict.authority.risk_tier is RiskTier.ENHANCED
    assert verdict.status is ReadinessVerdictStatus.FAILED
    assert _section_status(verdict.sections, ReadinessSection.AUTHORITY) is (
        ReadinessSectionStatus.FAILED
    )


@pytest.mark.asyncio
async def test_prohibited_boundary_is_explicit_negative_gate() -> None:
    evidence = ReadinessGateEvidence(
        artifacts=(
            ReadinessArtifactEvidence(
                artifact_type="prohibited_boundary_negative_test",
                artifact_id="negative-boundary-1",
            ),
        )
    )
    request = _request(
        evidence=evidence,
        target_type=EvaluationTargetType.MCP_TOOL_RESPONSE,
    )

    verdict = await ReadinessGateService().evaluate(request)

    assert verdict.profile.gate_profile is GateProfile.PROHIBITED_BOUNDARY
    assert verdict.status is ReadinessVerdictStatus.FAILED
    assert _section_status(verdict.sections, ReadinessSection.AUTHORITY) is (
        ReadinessSectionStatus.PASSED
    )
    assert "rejected" in next(
        item.reason
        for item in verdict.sections
        if item.section is ReadinessSection.AUTHORITY
    ).lower()


@pytest.mark.asyncio
async def test_readiness_verdict_persists_reconstructable_evidence() -> None:
    repository = _FakeReadinessRepository(
        run=EvaluationRunRecord(
            run_id="eval-run-1",
            target_type=EvaluationTargetType.AGENT_TASK,
            status=EvaluationStatus.PASSED,
            evaluator_provider="fake",
            evaluator_model="fake",
        )
    )
    request = _request(persistence_run_id="eval-run-1")

    verdict = await ReadinessGateService(repository=repository).evaluate(request)

    assert verdict.status is ReadinessVerdictStatus.PASSED
    assert verdict.persistence_artifact_id == "readiness_gate:eval-run-1:readiness-1"
    assert len(repository.artifacts) == 1
    artifact = repository.artifacts[0]
    assert artifact.artifact_type == READINESS_GATE_ARTIFACT_TYPE
    assert artifact.run_id == "eval-run-1"
    assert artifact.payload is not None
    assert artifact.payload["gate_run_id"] == "readiness-1"
    assert artifact.payload["correlation_id"] == "correlation-1"
    assert artifact.payload["target_type"] == EvaluationTargetType.AGENT_TASK.value
    assert artifact.payload["persistence_artifact_id"] == artifact.artifact_id
    profile = artifact.payload["profile"]
    assert isinstance(profile, dict)
    assert profile["profile_version"] == "baseline_v1"
    assert profile["required_artifacts"] == ["baseline_architecture_regression"]
    artifacts = artifact.payload["artifact_evidence"]
    assert artifacts == [
        {
            "artifact_type": "baseline_architecture_regression",
            "artifact_id": "baseline-regression-1",
            "version": "v1",
        }
    ]


@pytest.mark.asyncio
async def test_readiness_persistence_retry_is_idempotent() -> None:
    repository = _FakeReadinessRepository(
        run=EvaluationRunRecord(
            run_id="eval-run-1",
            target_type=EvaluationTargetType.AGENT_TASK,
            status=EvaluationStatus.PASSED,
            evaluator_provider="fake",
            evaluator_model="fake",
        )
    )
    service = ReadinessGateService(repository=repository)
    request = _request(persistence_run_id="eval-run-1")

    first = await service.evaluate(request)
    second = await service.evaluate(request)

    assert first == second
    assert first.status is ReadinessVerdictStatus.PASSED
    assert len(repository.artifacts) == 1


@pytest.mark.asyncio
async def test_enhanced_missing_evidence_and_persistence_fails_closed() -> None:
    request = ReadinessGateRequest(
        gate_run_id="readiness-enhanced",
        correlation_id="correlation-enhanced",
        target_type=EvaluationTargetType.RAG_ANSWER,
        run_mode=ReadinessRunMode.RELEASE,
        evidence=ReadinessGateEvidence(),
    )

    verdict = await ReadinessGateService().evaluate(request)

    assert verdict.profile.gate_profile is GateProfile.ENHANCED_PROVENANCE
    assert verdict.status is ReadinessVerdictStatus.FAILED
    assert _section_status(verdict.sections, ReadinessSection.DATASETS) is (
        ReadinessSectionStatus.FAILED
    )
    assert _section_status(verdict.sections, ReadinessSection.METRICS) is (
        ReadinessSectionStatus.FAILED
    )
    assert _section_status(verdict.sections, ReadinessSection.PERSISTENCE) is (
        ReadinessSectionStatus.FAILED
    )


@pytest.mark.asyncio
async def test_readiness_outcome_uses_canonical_evaluation_telemetry_seam() -> None:
    sink = InMemoryTelemetrySink()
    observability = ObservabilityManager()
    observability.add_sink(sink)
    telemetry = EvaluationTelemetry(observability)

    service = ReadinessGateService(telemetry=telemetry)
    verdict = await service.evaluate(_request())

    assert verdict.status is ReadinessVerdictStatus.PASSED
    assert sink.events[-1].event_type == "evaluation.readiness_gate.completed"
    assert sink.events[-1].correlation_id == "correlation-1"
    assert sink.events[-1].attributes["gate_run_id"] == "readiness-1"
    assert sink.events[-1].attributes["profile_id"] == (
        GateProfile.BASELINE_INTERNAL.value
    )
    assert sink.events[-1].attributes["profile_version"] == "baseline_v1"
    assert sink.events[-1].attributes["status"] == ReadinessVerdictStatus.PASSED.value

    failed = await service.evaluate(_request(evidence=ReadinessGateEvidence()))

    assert failed.status is ReadinessVerdictStatus.FAILED
    assert sink.events[-1].success is False
    metric_names = [point.name for point in observability.metrics_store.points()]
    assert "evaluation_readiness_gate_outcomes_total" in metric_names
    assert "evaluation_readiness_gate_failed_sections_total" in metric_names
    assert "evaluation_readiness_gate_skipped_sections_total" in metric_names
