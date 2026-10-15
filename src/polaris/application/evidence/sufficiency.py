from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Protocol
from uuid import UUID, uuid4

from polaris.domain.actors import (
    ActorAttribution,
    is_actor_attribution,
)
from polaris.domain.configuration import (
    EvidenceRequirementApplicabilityKey,
    EvidenceRequirementSetVersion,
    EvidenceRequirementSetVersionId,
)
from polaris.domain.decisions import OperationId
from polaris.domain.evidence.observations import (
    EvidenceCorrectionId,
    EvidenceSufficiencyAssessmentId,
    EvidenceSupportVersion,
)
from polaris.domain.evidence.sufficiency import (
    EvidenceBindingInterpretation,
    EvidenceSufficiencyAssessment,
    EvidenceSufficiencyBasisGuards,
    EvidenceSufficiencyResult,
    evaluate_evidence_sufficiency,
)

from .contracts import (
    EvidenceApplicationError,
    EvidenceCommandReadUnavailable,
    EvidenceIdempotencyConflict,
    EvidencePersistenceUnavailable,
    require_aware_recording_time,
    require_exact_replay,
)
from .requirements import (
    ContestedEvidenceRequirementAuthority,
    InvalidEvidenceRequirementAuthority,
    MissingEvidenceRequirementAuthority,
    UnavailableEvidenceRequirementAuthority,
)


@dataclass(frozen=True, slots=True)
class RecordEvidenceSufficiencyAssessmentCommand:
    operation_id: OperationId
    # duplicate-code: keeping transport and semantic-request fields explicit makes
    # the deliberate exclusion of operation identity from replay semantics auditable.
    # arid: disable
    applicability_key: EvidenceRequirementApplicabilityKey
    attribution: ActorAttribution
    effective_at: datetime
    known_at: datetime
    # arid: enable
    reassesses_assessment_id: EvidenceSufficiencyAssessmentId | None = None

    def __post_init__(self) -> None:
        if type(self.operation_id) is not OperationId:
            raise TypeError("operation_id must be OperationId")
        if type(self.applicability_key) is not EvidenceRequirementApplicabilityKey:
            raise TypeError(
                "applicability_key must be EvidenceRequirementApplicabilityKey"
            )
        _validate_attribution(self.attribution)
        _aware(self.effective_at, "effective_at")
        _aware(self.known_at, "known_at")
        if (
            self.reassesses_assessment_id is not None
            and type(self.reassesses_assessment_id)
            is not EvidenceSufficiencyAssessmentId
        ):
            raise TypeError(
                "reassesses_assessment_id must be "
                "EvidenceSufficiencyAssessmentId or None"
            )


@dataclass(frozen=True, slots=True)
class EvidenceSufficiencySemanticRequest:
    applicability_key: EvidenceRequirementApplicabilityKey
    attribution: ActorAttribution
    effective_at: datetime
    known_at: datetime
    reassesses_assessment_id: EvidenceSufficiencyAssessmentId | None

    @classmethod
    def from_command(
        cls,
        command: RecordEvidenceSufficiencyAssessmentCommand,
    ) -> EvidenceSufficiencySemanticRequest:
        return cls(
            command.applicability_key,
            command.attribution,
            command.effective_at,
            command.known_at,
            command.reassesses_assessment_id,
        )


@dataclass(frozen=True, slots=True)
class EvidenceSufficiencyBasis:
    requirement_version: EvidenceRequirementSetVersion
    interpretations: tuple[EvidenceBindingInterpretation, ...]
    support_version: EvidenceSupportVersion
    guards: EvidenceSufficiencyBasisGuards

    def __post_init__(self) -> None:
        if type(self.requirement_version) is not EvidenceRequirementSetVersion:
            raise TypeError("requirement_version must be EvidenceRequirementSetVersion")
        if type(self.interpretations) is not tuple or any(
            type(value) is not EvidenceBindingInterpretation
            for value in self.interpretations
        ):
            raise TypeError(
                "interpretations must be tuple[EvidenceBindingInterpretation, ...]"
            )
        if type(self.support_version) is not EvidenceSupportVersion:
            raise TypeError("support_version must be EvidenceSupportVersion")
        if type(self.guards) is not EvidenceSufficiencyBasisGuards:
            raise TypeError("guards must be EvidenceSufficiencyBasisGuards")
        _require_exact_basis_guards(self)


def _require_exact_basis_guards(basis: EvidenceSufficiencyBasis) -> None:
    binding_ids = frozenset(value.binding.binding_id for value in basis.interpretations)
    if basis.guards.bindings.binding_ids != binding_ids:
        raise ValueError("binding absence guard must cover the complete universe")
    correction_ids = frozenset(
        fact
        for value in basis.interpretations
        for fact in value.fact_support
        if type(fact) is EvidenceCorrectionId
    )
    if basis.guards.corrections.correction_ids != correction_ids:
        raise ValueError("correction absence guard must cover interpreted ancestry")
    if basis.guards.requirement_authority.version_ids != frozenset(
        {basis.requirement_version.version_id}
    ):
        raise ValueError("requirement authority guard must identify one exact version")


@dataclass(frozen=True, slots=True)
class EvidenceSufficiencyAssessmentResult:
    assessment_id: EvidenceSufficiencyAssessmentId
    result: EvidenceSufficiencyResult
    replayed: bool = False


@dataclass(frozen=True, slots=True)
class EvidenceSufficiencyReceipt:
    operation_id: OperationId
    request: EvidenceSufficiencySemanticRequest
    result: EvidenceSufficiencyAssessmentResult


@dataclass(frozen=True, slots=True)
class EvidenceSufficiencyCommit:
    operation_id: OperationId
    request: EvidenceSufficiencySemanticRequest
    basis: EvidenceSufficiencyBasis
    assessment: EvidenceSufficiencyAssessment
    committed_at: datetime

    def __post_init__(self) -> None:
        if type(self.operation_id) is not OperationId:
            raise TypeError("operation_id must be OperationId")
        if type(self.request) is not EvidenceSufficiencySemanticRequest:
            raise TypeError("request must be EvidenceSufficiencySemanticRequest")
        if type(self.basis) is not EvidenceSufficiencyBasis:
            raise TypeError("basis must be EvidenceSufficiencyBasis")
        if type(self.assessment) is not EvidenceSufficiencyAssessment:
            raise TypeError("assessment must be EvidenceSufficiencyAssessment")
        require_aware_recording_time(self.committed_at)


@dataclass(frozen=True, slots=True)
class EvidenceSufficiencyCommitted:
    receipt: EvidenceSufficiencyReceipt


@dataclass(frozen=True, slots=True)
class EvidenceSufficiencyReplayed:
    receipt: EvidenceSufficiencyReceipt


@dataclass(frozen=True, slots=True)
class EvidenceSufficiencyIdempotencyConflict:
    operation_id: OperationId


@dataclass(frozen=True, slots=True)
class EvidenceSufficiencyStaleBasis:
    reason: str


@dataclass(frozen=True, slots=True)
class EvidenceSufficiencyInvalidHistory:
    reason: str


@dataclass(frozen=True, slots=True)
class EvidenceSufficiencyReassessmentConflict:
    assessment_id: EvidenceSufficiencyAssessmentId


@dataclass(frozen=True, slots=True)
class EvidenceSufficiencyStoreUnavailable:
    reason: str


type _EvidenceRequirementAuthorityFailure = (
    MissingEvidenceRequirementAuthority
    | UnavailableEvidenceRequirementAuthority
    | ContestedEvidenceRequirementAuthority
    | InvalidEvidenceRequirementAuthority
)


type EvidenceSufficiencyCommitOutcome = (
    EvidenceSufficiencyCommitted
    | EvidenceSufficiencyReplayed
    | EvidenceSufficiencyIdempotencyConflict
    | EvidenceSufficiencyStaleBasis
    | EvidenceSufficiencyInvalidHistory
    | EvidenceSufficiencyReassessmentConflict
    | EvidenceSufficiencyStoreUnavailable
    | _EvidenceRequirementAuthorityFailure
)

type EvidenceSufficiencyBasisResolution = (
    EvidenceSufficiencyBasis
    | EvidenceSufficiencyInvalidHistory
    | _EvidenceRequirementAuthorityFailure
)


class EvidenceSufficiencyStore(Protocol):
    async def get_sufficiency_receipt(
        self,
        operation_id: OperationId,
    ) -> EvidenceSufficiencyReceipt | None: ...

    async def load_sufficiency_basis(
        self,
        applicability_key: EvidenceRequirementApplicabilityKey,
        *,
        effective_at: datetime,
        known_at: datetime,
    ) -> EvidenceSufficiencyBasisResolution: ...

    async def commit_sufficiency(
        self,
        commit: EvidenceSufficiencyCommit,
    ) -> EvidenceSufficiencyCommitOutcome: ...

    async def load_sufficiency_assessment(
        self,
        assessment_id: EvidenceSufficiencyAssessmentId,
    ) -> EvidenceSufficiencyAssessment | None: ...


@dataclass(frozen=True, slots=True)
class _IndeterminateSufficiencyAuthority:
    result: EvidenceSufficiencyResult = field(
        default=EvidenceSufficiencyResult.INDETERMINATE,
        init=False,
    )


@dataclass(frozen=True, slots=True)
class EvidenceSufficiencyMissingAuthority(_IndeterminateSufficiencyAuthority):
    pass


@dataclass(frozen=True, slots=True)
class EvidenceSufficiencyUnavailableAuthority(_IndeterminateSufficiencyAuthority):
    reason: str


@dataclass(frozen=True, slots=True)
class EvidenceSufficiencyContestedAuthority(_IndeterminateSufficiencyAuthority):
    version_ids: frozenset[EvidenceRequirementSetVersionId]


@dataclass(frozen=True, slots=True)
class EvidenceSufficiencyInvalidAuthority:
    reason: str


type EvidenceSufficiencyServiceOutcome = (
    EvidenceSufficiencyAssessmentResult
    | EvidenceSufficiencyMissingAuthority
    | EvidenceSufficiencyUnavailableAuthority
    | EvidenceSufficiencyContestedAuthority
    | EvidenceSufficiencyInvalidAuthority
)


class EvidenceSufficiencyBasisConflict(EvidenceApplicationError):
    pass


class EvidenceSufficiencyHistoryConflict(EvidenceApplicationError):
    pass


class EvidenceSufficiencyReassessmentReferenceConflict(EvidenceApplicationError):
    def __init__(self, assessment_id: EvidenceSufficiencyAssessmentId) -> None:
        super().__init__("reassessment predecessor does not match the assessment scope")
        self.assessment_id = assessment_id


class EvidenceSufficiencyService:
    def __init__(
        self,
        *,
        store: EvidenceSufficiencyStore,
        now: Callable[[], datetime],
        new_uuid: Callable[[], UUID] = uuid4,
    ) -> None:
        self._store = store
        self._now = now
        self._new_uuid = new_uuid

    async def assess(
        self,
        command: RecordEvidenceSufficiencyAssessmentCommand,
    ) -> EvidenceSufficiencyServiceOutcome:
        request = EvidenceSufficiencySemanticRequest.from_command(command)
        receipt = await self._read_receipt(command.operation_id)
        if receipt is not None:
            return _replay(receipt, request, command.operation_id)
        recorded_at = self._now()
        require_aware_recording_time(recorded_at)
        if command.known_at > recorded_at:
            return EvidenceSufficiencyInvalidAuthority(
                "known_at cannot be later than the trusted commit instant"
            )
        resolution = await self._load_basis(command)
        if isinstance(resolution, EvidenceSufficiencyInvalidHistory):
            raise EvidenceSufficiencyHistoryConflict(resolution.reason)
        authority_failure = _authority_failure(resolution)
        if authority_failure is not None:
            return authority_failure
        if not isinstance(resolution, EvidenceSufficiencyBasis):
            raise AssertionError("unsupported sufficiency-basis resolution")
        assessment = _new_assessment(
            command,
            resolution,
            recorded_at=recorded_at,
            assessment_id=EvidenceSufficiencyAssessmentId(self._new_uuid()),
        )
        outcome = await self._store.commit_sufficiency(
            EvidenceSufficiencyCommit(
                command.operation_id,
                request,
                resolution,
                assessment,
                recorded_at,
            )
        )
        return _commit_result(outcome, request, command.operation_id)

    async def _read_receipt(
        self,
        operation_id: OperationId,
    ) -> EvidenceSufficiencyReceipt | None:
        try:
            return await self._store.get_sufficiency_receipt(operation_id)
        except EvidenceCommandReadUnavailable as error:
            raise EvidencePersistenceUnavailable(str(error)) from error

    async def _load_basis(
        self,
        command: RecordEvidenceSufficiencyAssessmentCommand,
    ) -> EvidenceSufficiencyBasisResolution:
        try:
            return await self._store.load_sufficiency_basis(
                command.applicability_key,
                effective_at=command.effective_at,
                known_at=command.known_at,
            )
        except EvidenceCommandReadUnavailable as error:
            return UnavailableEvidenceRequirementAuthority(str(error))


def _new_assessment(
    command: RecordEvidenceSufficiencyAssessmentCommand,
    basis: EvidenceSufficiencyBasis,
    *,
    recorded_at: datetime,
    assessment_id: EvidenceSufficiencyAssessmentId,
) -> EvidenceSufficiencyAssessment:
    evaluation = evaluate_evidence_sufficiency(
        basis.requirement_version,
        command.applicability_key,
        basis.interpretations,
        effective_at=command.effective_at,
        known_at=command.known_at,
    )
    key = command.applicability_key
    version = basis.requirement_version
    return EvidenceSufficiencyAssessment(
        assessment_id=assessment_id,
        target=key.target,
        scope=key.scope,
        evidence_use=key.evidence_use,
        applicability_key=key,
        requirement_set_id=version.set_id,
        requirement_version_id=version.version_id,
        support_version=basis.support_version,
        basis_guards=basis.guards,
        requirement_assessments=evaluation.requirement_assessments,
        attribution=command.attribution,
        effective_at=command.effective_at,
        known_at=command.known_at,
        recorded_at=recorded_at,
        result=evaluation.result,
        no_requirements_witness=evaluation.no_requirements_witness,
        reassesses_assessment_id=command.reassesses_assessment_id,
    )


def rederive_evidence_assessment(
    assessment: EvidenceSufficiencyAssessment,
    basis: EvidenceSufficiencyBasis,
    *,
    effective_at: datetime,
    known_at: datetime,
) -> EvidenceSufficiencyAssessment:
    """Derive the complete assertion from one authoritative basis and boundary."""
    evaluation = evaluate_evidence_sufficiency(
        basis.requirement_version,
        assessment.applicability_key,
        basis.interpretations,
        effective_at=effective_at,
        known_at=known_at,
    )
    return replace(
        assessment,
        support_version=basis.support_version,
        basis_guards=basis.guards,
        requirement_assessments=evaluation.requirement_assessments,
        result=evaluation.result,
        no_requirements_witness=evaluation.no_requirements_witness,
    )


def _authority_failure(
    resolution: object,
) -> (
    EvidenceSufficiencyMissingAuthority
    | EvidenceSufficiencyUnavailableAuthority
    | EvidenceSufficiencyContestedAuthority
    | EvidenceSufficiencyInvalidAuthority
    | None
):
    if isinstance(resolution, MissingEvidenceRequirementAuthority):
        return EvidenceSufficiencyMissingAuthority()
    if isinstance(resolution, UnavailableEvidenceRequirementAuthority):
        return EvidenceSufficiencyUnavailableAuthority(resolution.reason)
    if isinstance(resolution, ContestedEvidenceRequirementAuthority):
        return EvidenceSufficiencyContestedAuthority(resolution.version_ids)
    if isinstance(resolution, InvalidEvidenceRequirementAuthority):
        return EvidenceSufficiencyInvalidAuthority(resolution.reason)
    return None


def _commit_result(
    outcome: EvidenceSufficiencyCommitOutcome,
    request: EvidenceSufficiencySemanticRequest,
    operation_id: OperationId,
) -> EvidenceSufficiencyServiceOutcome:
    if isinstance(outcome, EvidenceSufficiencyCommitted):
        return outcome.receipt.result
    if isinstance(outcome, EvidenceSufficiencyReplayed):
        return _replay(outcome.receipt, request, operation_id)
    if isinstance(outcome, EvidenceSufficiencyIdempotencyConflict):
        raise EvidenceIdempotencyConflict(outcome.operation_id)
    if isinstance(outcome, EvidenceSufficiencyReassessmentConflict):
        raise EvidenceSufficiencyReassessmentReferenceConflict(outcome.assessment_id)
    if isinstance(outcome, EvidenceSufficiencyStaleBasis):
        raise EvidenceSufficiencyBasisConflict(outcome.reason)
    if isinstance(outcome, EvidenceSufficiencyInvalidHistory):
        raise EvidenceSufficiencyHistoryConflict(outcome.reason)
    authority_failure = _authority_failure(outcome)
    if authority_failure is not None:
        return authority_failure
    if isinstance(outcome, EvidenceSufficiencyStoreUnavailable):
        raise EvidencePersistenceUnavailable(outcome.reason)
    raise AssertionError("EvidenceSufficiencyStore returned an unsupported outcome")


def _replay(
    receipt: EvidenceSufficiencyReceipt,
    request: EvidenceSufficiencySemanticRequest,
    operation_id: OperationId,
) -> EvidenceSufficiencyAssessmentResult:
    # duplicate-code: the shared replay guard is canonical; this local call maps its
    # success into the sufficiency-specific immutable result type.
    # arid: disable
    require_exact_replay(
        receipt_operation_id=receipt.operation_id,
        receipt_request=receipt.request,
        operation_id=operation_id,
        request=request,
    )
    # arid: enable
    return EvidenceSufficiencyAssessmentResult(
        receipt.result.assessment_id,
        receipt.result.result,
        replayed=True,
    )


def _validate_attribution(value: ActorAttribution) -> None:
    if not is_actor_attribution(value):
        raise TypeError("attribution must be an ActorAttribution")


# duplicate-code: this command boundary owns its public validation failure type.
# arid: disable
def _aware(value: object, field_name: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise ValueError(f"{field_name} must be timezone-aware")


# arid: enable


__all__ = [
    "EvidenceSufficiencyAssessmentResult",
    "EvidenceSufficiencyBasis",
    "EvidenceSufficiencyBasisConflict",
    "EvidenceSufficiencyBasisResolution",
    "EvidenceSufficiencyCommit",
    "EvidenceSufficiencyCommitOutcome",
    "EvidenceSufficiencyCommitted",
    "EvidenceSufficiencyContestedAuthority",
    "EvidenceSufficiencyIdempotencyConflict",
    "EvidenceSufficiencyInvalidAuthority",
    "EvidenceSufficiencyInvalidHistory",
    "EvidenceSufficiencyMissingAuthority",
    "EvidenceSufficiencyReassessmentConflict",
    "EvidenceSufficiencyReassessmentReferenceConflict",
    "EvidenceSufficiencyReceipt",
    "EvidenceSufficiencyReplayed",
    "EvidenceSufficiencySemanticRequest",
    "EvidenceSufficiencyService",
    "EvidenceSufficiencyServiceOutcome",
    "EvidenceSufficiencyStaleBasis",
    "EvidenceSufficiencyStore",
    "EvidenceSufficiencyStoreUnavailable",
    "EvidenceSufficiencyUnavailableAuthority",
    "RecordEvidenceSufficiencyAssessmentCommand",
]
