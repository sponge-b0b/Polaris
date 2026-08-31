from __future__ import annotations

from collections.abc import Hashable, Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from enum import StrEnum
from math import isfinite
from typing import Protocol, cast

from application.evaluations.evaluation_run_service import (
    expected_authority_metadata_for_evaluation_target,
)
from application.evaluations.readiness_profiles import (
    ReadinessDatasetRequirement,
    ReadinessDatasetScope,
    ReadinessFailurePolicy,
    ReadinessMetricRequirement,
    ReadinessProfile,
    ReadinessRunMode,
    readiness_profile_for_gate,
)
from application.evaluations.risk_authority_gate import (
    RiskAuthorityGateDecision,
    RiskAuthorityGateDecisionStatus,
    RiskAuthorityGateEvidence,
    RiskAuthorityGateFailureMode,
    select_risk_authority_gate,
)
from core.storage.persistence.evaluation import (
    EvaluationArtifactRecord,
    EvaluationRunRecord,
    JsonObject,
)
from domain.authority import (
    RiskAuthorityContract,
    RiskTier,
    risk_authority_contract_from_metadata,
)
from domain.evaluation import EvaluationTargetType

READINESS_GATE_ARTIFACT_TYPE = "readiness_gate_verdict.v1"
READINESS_GATE_ARTIFACT_SCHEMA_VERSION = 1


class ReadinessSection(StrEnum):
    """Stable ordered sections in one readiness verdict."""

    AUTHORITY = "authority"
    CADENCE = "cadence"
    DATASETS = "datasets"
    METRICS = "metrics"
    ARTIFACTS = "artifacts"
    LIVE_SERVICES = "live_services"
    PERSISTENCE = "persistence"


class ReadinessSectionStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ReadinessVerdictStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class ReadinessDatasetEvidence:
    name: str
    version: str
    scope: ReadinessDatasetScope
    evidence_id: str

    def __post_init__(self) -> None:
        for field_name in ("name", "version", "evidence_id"):
            object.__setattr__(
                self,
                field_name,
                _require_non_empty(getattr(self, field_name), field_name),
            )


@dataclass(frozen=True, slots=True)
class ReadinessMetricEvidence:
    metric_name: str
    version: str
    score: float
    drift: float
    evidence_id: str

    def __post_init__(self) -> None:
        for field_name in ("metric_name", "version", "evidence_id"):
            object.__setattr__(
                self,
                field_name,
                _require_non_empty(getattr(self, field_name), field_name),
            )
        _require_unit_score(self.score, "score")
        _require_unit_score(self.drift, "drift")


@dataclass(frozen=True, slots=True)
class ReadinessArtifactEvidence:
    artifact_type: str
    artifact_id: str
    version: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "artifact_type",
            _require_non_empty(self.artifact_type, "artifact_type"),
        )
        object.__setattr__(
            self,
            "artifact_id",
            _require_non_empty(self.artifact_id, "artifact_id"),
        )
        object.__setattr__(
            self,
            "version",
            _clean_optional(self.version, "version"),
        )


@dataclass(frozen=True, slots=True)
class ReadinessLiveServiceEvidence:
    service_name: str
    evidence_id: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "service_name",
            _require_non_empty(self.service_name, "service_name"),
        )
        object.__setattr__(
            self,
            "evidence_id",
            _require_non_empty(self.evidence_id, "evidence_id"),
        )


@dataclass(frozen=True, slots=True)
class ReadinessGateEvidence:
    """Evidence presented by existing evaluation/governance component owners."""

    authority: RiskAuthorityGateEvidence = RiskAuthorityGateEvidence()
    datasets: tuple[ReadinessDatasetEvidence, ...] = ()
    metrics: tuple[ReadinessMetricEvidence, ...] = ()
    artifacts: tuple[ReadinessArtifactEvidence, ...] = ()
    live_services: tuple[ReadinessLiveServiceEvidence, ...] = ()

    def __post_init__(self) -> None:
        _require_unique(
            ((item.scope, item.name, item.version) for item in self.datasets),
            "dataset evidence",
        )
        _require_unique(
            ((item.metric_name, item.version) for item in self.metrics),
            "metric evidence",
        )
        _require_unique(
            ((item.artifact_type, item.artifact_id) for item in self.artifacts),
            "artifact evidence",
        )
        _require_unique(
            (item.service_name for item in self.live_services),
            "live-service evidence",
        )


@dataclass(frozen=True, slots=True)
class ReadinessGateRequest:
    """Typed request for one architecture-wide readiness evaluation."""

    gate_run_id: str
    correlation_id: str
    target_type: EvaluationTargetType
    run_mode: ReadinessRunMode
    evidence: ReadinessGateEvidence
    supplied_authority_metadata: Mapping[str, object] | RiskAuthorityContract | None = (
        None
    )
    persistence_run_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "gate_run_id",
            _require_non_empty(self.gate_run_id, "gate_run_id"),
        )
        object.__setattr__(
            self,
            "correlation_id",
            _require_non_empty(self.correlation_id, "correlation_id"),
        )
        object.__setattr__(
            self,
            "persistence_run_id",
            _clean_optional(self.persistence_run_id, "persistence_run_id"),
        )


@dataclass(frozen=True, slots=True)
class ReadinessSectionResult:
    section: ReadinessSection
    status: ReadinessSectionStatus
    reason: str
    evidence_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "reason", _require_non_empty(self.reason, "reason"))
        object.__setattr__(
            self,
            "evidence_ids",
            tuple(
                _require_non_empty(value, "evidence_id") for value in self.evidence_ids
            ),
        )


@dataclass(frozen=True, slots=True)
class ReadinessGateVerdict:
    """One typed, deterministic, reconstructable readiness verdict."""

    gate_run_id: str
    correlation_id: str
    target_type: EvaluationTargetType
    run_mode: ReadinessRunMode
    status: ReadinessVerdictStatus
    profile: ReadinessProfile
    authority: RiskAuthorityContract
    sections: tuple[ReadinessSectionResult, ...]
    evidence: ReadinessGateEvidence
    persistence_artifact_id: str | None = None

    @property
    def passed(self) -> bool:
        return self.status is ReadinessVerdictStatus.PASSED

    @property
    def failed_sections(self) -> tuple[ReadinessSectionResult, ...]:
        return tuple(
            item
            for item in self.sections
            if item.status is ReadinessSectionStatus.FAILED
        )

    @property
    def skipped_sections(self) -> tuple[ReadinessSectionResult, ...]:
        return tuple(
            item
            for item in self.sections
            if item.status is ReadinessSectionStatus.SKIPPED
        )

    def to_artifact_payload(self) -> JsonObject:
        """Serialize required and observed evidence at the artifact boundary."""

        return cast(
            JsonObject,
            {
                "schema_version": READINESS_GATE_ARTIFACT_SCHEMA_VERSION,
                "gate_run_id": self.gate_run_id,
                "correlation_id": self.correlation_id,
                "target_type": self.target_type.value,
                "run_mode": self.run_mode.value,
                "status": self.status.value,
                "profile": _profile_payload(self.profile),
                "authority_metadata": self.authority.to_metadata(),
                "authority_evidence": _authority_evidence_payload(
                    self.evidence.authority
                ),
                "sections": [_section_payload(item) for item in self.sections],
                "dataset_evidence": [
                    _dataset_evidence_payload(item) for item in self.evidence.datasets
                ],
                "metric_evidence": [
                    _metric_evidence_payload(item) for item in self.evidence.metrics
                ],
                "artifact_evidence": [
                    _artifact_evidence_payload(item) for item in self.evidence.artifacts
                ],
                "live_service_evidence": [
                    _live_service_evidence_payload(item)
                    for item in self.evidence.live_services
                ],
                "persistence_artifact_id": self.persistence_artifact_id,
            },
        )


class ReadinessPersistencePort(Protocol):
    async def get_run(self, run_id: str) -> EvaluationRunRecord | None: ...

    async def list_artifacts(
        self,
        run_id: str,
    ) -> Sequence[EvaluationArtifactRecord]: ...

    async def create_artifact(
        self,
        record: EvaluationArtifactRecord,
    ) -> EvaluationArtifactRecord: ...


class ReadinessGateTelemetry(Protocol):
    async def emit_readiness_gate_verdict(
        self,
        *,
        gate_run_id: str,
        correlation_id: str,
        profile_id: str,
        profile_version: str,
        status: str,
        failed_section_count: int,
        skipped_section_count: int,
    ) -> None: ...


@dataclass(frozen=True, slots=True)
class ReadinessGateService:
    """Select, execute, persist, and observe canonical readiness profiles."""

    repository: ReadinessPersistencePort | None = None
    telemetry: ReadinessGateTelemetry | None = None

    async def evaluate(self, request: ReadinessGateRequest) -> ReadinessGateVerdict:
        authority = risk_authority_contract_from_metadata(
            expected_authority_metadata_for_evaluation_target(request.target_type)
        )
        profile = readiness_profile_for_gate(authority.gate_profile)
        supplied_metadata = (
            authority
            if request.supplied_authority_metadata is None
            else request.supplied_authority_metadata
        )
        authority_decision = select_risk_authority_gate(
            supplied_metadata,
            evidence=request.evidence.authority,
            expected_authority_metadata=authority,
        )
        sections = (
            _authority_section(profile, authority_decision),
            _cadence_section(profile, request.run_mode),
            _dataset_section(profile, request),
            _metric_section(profile, request),
            _artifact_section(profile, request.evidence),
            _live_service_section(profile, request.evidence),
        )
        verdict = ReadinessGateVerdict(
            gate_run_id=request.gate_run_id,
            correlation_id=request.correlation_id,
            target_type=request.target_type,
            run_mode=request.run_mode,
            status=_status_for(profile, sections),
            profile=profile,
            authority=authority,
            sections=sections,
            evidence=request.evidence,
        )
        verdict = await self._persist(request, verdict)
        await self._emit(verdict)
        return verdict

    async def _persist(
        self,
        request: ReadinessGateRequest,
        verdict: ReadinessGateVerdict,
    ) -> ReadinessGateVerdict:
        if request.persistence_run_id is None:
            status = (
                ReadinessSectionStatus.FAILED
                if _profile_requires_persistence(verdict.profile, request.run_mode)
                else ReadinessSectionStatus.SKIPPED
            )
            reason = (
                "Selected profile requires durable evaluation persistence."
                if status is ReadinessSectionStatus.FAILED
                else "Local readiness run did not request durable persistence."
            )
            return _append_section(
                verdict,
                ReadinessSectionResult(ReadinessSection.PERSISTENCE, status, reason),
            )
        if self.repository is None:
            return _append_section(
                verdict,
                ReadinessSectionResult(
                    ReadinessSection.PERSISTENCE,
                    ReadinessSectionStatus.FAILED,
                    "Durable readiness persistence was requested but unavailable.",
                ),
            )
        try:
            run = await self.repository.get_run(request.persistence_run_id)
        except Exception:
            return _append_section(
                verdict,
                ReadinessSectionResult(
                    ReadinessSection.PERSISTENCE,
                    ReadinessSectionStatus.FAILED,
                    "Evaluation persistence could not load the requested run.",
                ),
            )
        if run is None:
            return _append_section(
                verdict,
                ReadinessSectionResult(
                    ReadinessSection.PERSISTENCE,
                    ReadinessSectionStatus.FAILED,
                    "Persistence run does not exist in evaluation persistence.",
                ),
            )
        if run.target_type is not request.target_type:
            return _append_section(
                verdict,
                ReadinessSectionResult(
                    ReadinessSection.PERSISTENCE,
                    ReadinessSectionStatus.FAILED,
                    "Persistence run target does not match the readiness target.",
                ),
            )

        artifact_id = (
            f"readiness_gate:{request.persistence_run_id}:{request.gate_run_id}"
        )
        persisted = replace(
            verdict,
            persistence_artifact_id=artifact_id,
            sections=(
                *verdict.sections,
                ReadinessSectionResult(
                    ReadinessSection.PERSISTENCE,
                    ReadinessSectionStatus.PASSED,
                    "Readiness verdict persisted through evaluation artifacts.",
                    (artifact_id,),
                ),
            ),
        )
        persisted = _recompute_status(persisted)
        artifact = EvaluationArtifactRecord(
            artifact_id=artifact_id,
            run_id=request.persistence_run_id,
            artifact_type=READINESS_GATE_ARTIFACT_TYPE,
            payload=persisted.to_artifact_payload(),
        )
        try:
            existing = next(
                (
                    item
                    for item in await self.repository.list_artifacts(
                        request.persistence_run_id
                    )
                    if item.artifact_id == artifact_id
                ),
                None,
            )
            if existing is not None:
                if _same_artifact_evidence(existing, artifact):
                    return persisted
                return _append_section(
                    verdict,
                    ReadinessSectionResult(
                        ReadinessSection.PERSISTENCE,
                        ReadinessSectionStatus.FAILED,
                        "Readiness gate-run identity collides with different evidence.",
                    ),
                )
            await self.repository.create_artifact(artifact)
        except Exception:
            return _append_section(
                verdict,
                ReadinessSectionResult(
                    ReadinessSection.PERSISTENCE,
                    ReadinessSectionStatus.FAILED,
                    "Readiness verdict persistence failed.",
                ),
            )
        return persisted

    async def _emit(self, verdict: ReadinessGateVerdict) -> None:
        if self.telemetry is None:
            return
        await self.telemetry.emit_readiness_gate_verdict(
            gate_run_id=verdict.gate_run_id,
            correlation_id=verdict.correlation_id,
            profile_id=verdict.profile.profile_id,
            profile_version=verdict.profile.profile_version,
            status=verdict.status.value,
            failed_section_count=len(verdict.failed_sections),
            skipped_section_count=len(verdict.skipped_sections),
        )


def _same_artifact_evidence(
    left: EvaluationArtifactRecord,
    right: EvaluationArtifactRecord,
) -> bool:
    return (
        left.artifact_id == right.artifact_id
        and left.run_id == right.run_id
        and left.artifact_type == right.artifact_type
        and left.case_id == right.case_id
        and left.uri == right.uri
        and left.payload == right.payload
    )


def _profile_requires_persistence(
    profile: ReadinessProfile,
    run_mode: ReadinessRunMode,
) -> bool:
    return (
        profile.risk_tier in {RiskTier.ENHANCED, RiskTier.VIGILANT}
        or run_mode is not ReadinessRunMode.LOCAL_PR
    )


def _append_section(
    verdict: ReadinessGateVerdict,
    section: ReadinessSectionResult,
) -> ReadinessGateVerdict:
    return _recompute_status(replace(verdict, sections=(*verdict.sections, section)))


def _recompute_status(verdict: ReadinessGateVerdict) -> ReadinessGateVerdict:
    return replace(
        verdict,
        status=_status_for(verdict.profile, verdict.sections),
    )


def _status_for(
    profile: ReadinessProfile,
    sections: tuple[ReadinessSectionResult, ...],
) -> ReadinessVerdictStatus:
    if profile.failure_policy is ReadinessFailurePolicy.PROHIBITED_NEGATIVE:
        return ReadinessVerdictStatus.FAILED
    if any(item.status is ReadinessSectionStatus.FAILED for item in sections):
        return ReadinessVerdictStatus.FAILED
    return ReadinessVerdictStatus.PASSED


def _authority_section(
    profile: ReadinessProfile,
    decision: RiskAuthorityGateDecision,
) -> ReadinessSectionResult:
    if profile.failure_policy is ReadinessFailurePolicy.PROHIBITED_NEGATIVE:
        rejected = (
            decision.status is RiskAuthorityGateDecisionStatus.FAILED
            and decision.failure_mode
            is RiskAuthorityGateFailureMode.PROHIBITED_BOUNDARY
        )
        return ReadinessSectionResult(
            ReadinessSection.AUTHORITY,
            (
                ReadinessSectionStatus.PASSED
                if rejected
                else ReadinessSectionStatus.FAILED
            ),
            (
                "Canonical authority rejected the prohibited boundary."
                if rejected
                else "Canonical authority did not reject the prohibited boundary."
            ),
        )
    status = (
        ReadinessSectionStatus.PASSED
        if decision.status is RiskAuthorityGateDecisionStatus.PASSED
        else ReadinessSectionStatus.FAILED
    )
    return ReadinessSectionResult(ReadinessSection.AUTHORITY, status, decision.message)


def _cadence_section(
    profile: ReadinessProfile,
    run_mode: ReadinessRunMode,
) -> ReadinessSectionResult:
    if run_mode in profile.cadence:
        return ReadinessSectionResult(
            ReadinessSection.CADENCE,
            ReadinessSectionStatus.PASSED,
            f"Run mode {run_mode.value!r} is allowed by the profile.",
        )
    return ReadinessSectionResult(
        ReadinessSection.CADENCE,
        ReadinessSectionStatus.FAILED,
        f"Run mode {run_mode.value!r} is not allowed by the profile.",
    )


def _dataset_section(
    profile: ReadinessProfile,
    request: ReadinessGateRequest,
) -> ReadinessSectionResult:
    required = tuple(
        item
        for item in profile.dataset_requirements
        if item.applies_to(
            target_type=request.target_type,
            run_mode=request.run_mode,
        )
    )
    if not required:
        if profile.dataset_requirements:
            return _failed(
                ReadinessSection.DATASETS,
                "Selected profile has no dataset coverage for this target/run mode.",
            )
        return _skipped(ReadinessSection.DATASETS, "Profile requires no datasets.")
    observed = {
        (item.scope, item.name, item.version): item
        for item in request.evidence.datasets
    }
    missing = [item for item in required if _dataset_key(item) not in observed]
    if missing:
        names = ", ".join(_dataset_requirement_label(item) for item in missing)
        return _failed(ReadinessSection.DATASETS, f"Missing dataset evidence: {names}.")
    return ReadinessSectionResult(
        ReadinessSection.DATASETS,
        ReadinessSectionStatus.PASSED,
        "All profile-required dataset evidence is present.",
        tuple(observed[_dataset_key(item)].evidence_id for item in required),
    )


def _metric_section(
    profile: ReadinessProfile,
    request: ReadinessGateRequest,
) -> ReadinessSectionResult:
    required = tuple(
        item
        for item in profile.metric_requirements
        if item.applies_to(request.target_type)
    )
    if not required:
        if profile.metric_requirements:
            return _failed(
                ReadinessSection.METRICS,
                "Selected profile has no metric coverage for this target type.",
            )
        return _skipped(ReadinessSection.METRICS, "Profile requires no metrics.")
    observed = {
        (item.metric_name, item.version): item for item in request.evidence.metrics
    }
    failures: list[str] = []
    evidence_ids: list[str] = []
    for requirement in required:
        evidence = observed.get((requirement.metric_name, requirement.version))
        if evidence is None:
            failures.append(f"{requirement.metric_name}@{requirement.version} missing")
            continue
        evidence_ids.append(evidence.evidence_id)
        _append_metric_failures(requirement, evidence, failures)
    if failures:
        return _failed(ReadinessSection.METRICS, "; ".join(failures) + ".")
    return ReadinessSectionResult(
        ReadinessSection.METRICS,
        ReadinessSectionStatus.PASSED,
        "All required metrics satisfy score and drift thresholds.",
        tuple(evidence_ids),
    )


def _append_metric_failures(
    requirement: ReadinessMetricRequirement,
    evidence: ReadinessMetricEvidence,
    failures: list[str],
) -> None:
    if evidence.score < requirement.minimum_score:
        failures.append(
            f"{requirement.metric_name} score {evidence.score} below "
            f"{requirement.minimum_score}"
        )
    if evidence.drift > requirement.allowed_drift:
        failures.append(
            f"{requirement.metric_name} drift {evidence.drift} above "
            f"{requirement.allowed_drift}"
        )


def _artifact_section(
    profile: ReadinessProfile,
    evidence: ReadinessGateEvidence,
) -> ReadinessSectionResult:
    if not profile.required_artifacts:
        return _skipped(ReadinessSection.ARTIFACTS, "Profile requires no artifacts.")
    evidence_ids: list[str] = []
    missing: list[str] = []
    for required_type in profile.required_artifacts:
        matches = tuple(
            item for item in evidence.artifacts if item.artifact_type == required_type
        )
        if not matches:
            missing.append(required_type)
            continue
        evidence_ids.extend(item.artifact_id for item in matches)
    if missing:
        return _failed(
            ReadinessSection.ARTIFACTS,
            "Missing required artifacts: " + ", ".join(missing) + ".",
        )
    return ReadinessSectionResult(
        ReadinessSection.ARTIFACTS,
        ReadinessSectionStatus.PASSED,
        "All profile-required artifacts are present.",
        tuple(evidence_ids),
    )


def _live_service_section(
    profile: ReadinessProfile,
    evidence: ReadinessGateEvidence,
) -> ReadinessSectionResult:
    if not profile.live_service_requirements:
        return _skipped(
            ReadinessSection.LIVE_SERVICES,
            "Profile requires no live-service evidence.",
        )
    observed = {item.service_name: item for item in evidence.live_services}
    missing = [
        name for name in profile.live_service_requirements if name not in observed
    ]
    if missing:
        return _failed(
            ReadinessSection.LIVE_SERVICES,
            "Missing live-service evidence: " + ", ".join(missing) + ".",
        )
    return ReadinessSectionResult(
        ReadinessSection.LIVE_SERVICES,
        ReadinessSectionStatus.PASSED,
        "All profile-required live-service evidence is present.",
        tuple(observed[name].evidence_id for name in profile.live_service_requirements),
    )


def _dataset_key(
    requirement: ReadinessDatasetRequirement,
) -> tuple[ReadinessDatasetScope, str, str]:
    return requirement.scope, requirement.name, requirement.version


def _dataset_requirement_label(requirement: ReadinessDatasetRequirement) -> str:
    return f"{requirement.scope.value}:{requirement.name}@{requirement.version}"


def _skipped(section: ReadinessSection, reason: str) -> ReadinessSectionResult:
    return ReadinessSectionResult(section, ReadinessSectionStatus.SKIPPED, reason)


def _failed(section: ReadinessSection, reason: str) -> ReadinessSectionResult:
    return ReadinessSectionResult(section, ReadinessSectionStatus.FAILED, reason)


def _profile_payload(profile: ReadinessProfile) -> dict[str, object]:
    return {
        "profile_version": profile.profile_version,
        "risk_tier": profile.risk_tier.value,
        "gate_profile": profile.gate_profile.value,
        "dataset_requirements": [
            {
                "name": item.name,
                "version": item.version,
                "scope": item.scope.value,
                "target_types": [value.value for value in item.target_types],
                "run_modes": [value.value for value in item.run_modes],
            }
            for item in profile.dataset_requirements
        ],
        "metric_requirements": [
            {
                "metric_name": item.metric_name,
                "version": item.version,
                "minimum_score": item.minimum_score,
                "allowed_drift": item.allowed_drift,
                "target_types": [value.value for value in item.target_types],
            }
            for item in profile.metric_requirements
        ],
        "cadence": [value.value for value in profile.cadence],
        "required_artifacts": list(profile.required_artifacts),
        "live_service_requirements": list(profile.live_service_requirements),
        "failure_policy": profile.failure_policy.value,
    }


def _authority_evidence_payload(
    evidence: RiskAuthorityGateEvidence,
) -> dict[str, object]:
    return {
        "provenance_record_ids": list(evidence.provenance_record_ids),
        "evaluation_run_ids": list(evidence.evaluation_run_ids),
        "decision_evidence_ids": list(evidence.decision_evidence_ids),
        "model_replacement_gate_ids": list(evidence.model_replacement_gate_ids),
        "rejected_evidence_ids": list(evidence.rejected_evidence_ids),
        "metric_result_count": evidence.metric_result_count,
        "governance_evidence": [
            {
                "evidence_packet_id": item.evidence_packet_id,
                "evidence_packet_version": item.evidence_packet_version,
                "review_task_id": item.review_task_id,
                "residual_risk_acceptance_id": item.residual_risk_acceptance_id,
            }
            for item in evidence.output_governance_evidence
        ],
    }


def _section_payload(item: ReadinessSectionResult) -> dict[str, object]:
    return {
        "section": item.section.value,
        "status": item.status.value,
        "reason": item.reason,
        "evidence_ids": list(item.evidence_ids),
    }


def _dataset_evidence_payload(item: ReadinessDatasetEvidence) -> dict[str, object]:
    return {
        "name": item.name,
        "version": item.version,
        "scope": item.scope.value,
        "evidence_id": item.evidence_id,
    }


def _metric_evidence_payload(item: ReadinessMetricEvidence) -> dict[str, object]:
    return {
        "metric_name": item.metric_name,
        "version": item.version,
        "score": item.score,
        "drift": item.drift,
        "evidence_id": item.evidence_id,
    }


def _artifact_evidence_payload(item: ReadinessArtifactEvidence) -> dict[str, object]:
    return {
        "artifact_type": item.artifact_type,
        "artifact_id": item.artifact_id,
        "version": item.version,
    }


def _live_service_evidence_payload(
    item: ReadinessLiveServiceEvidence,
) -> dict[str, object]:
    return {"service_name": item.service_name, "evidence_id": item.evidence_id}


def _require_unique(values: Iterable[Hashable], label: str) -> None:
    seen: set[Hashable] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"Duplicate {label} identity: {value!r}.")
        seen.add(value)


def _clean_optional(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    return _require_non_empty(value, field_name)


def _require_non_empty(value: str, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} cannot be empty.")
    return cleaned


def _require_unit_score(value: float, field_name: str) -> None:
    if not isfinite(value) or value < 0.0 or value > 1.0:
        raise ValueError(f"{field_name} must be between 0.0 and 1.0.")
