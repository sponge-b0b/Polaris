from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID, uuid4

from polaris.domain.actors import ActorAttribution, is_actor_attribution
from polaris.domain.configuration import EvidenceRequirementApplicabilityKey
from polaris.domain.decisions import OperationId
from polaris.domain.evidence import (
    EvidenceAssessmentCorrection,
    EvidenceAssessmentCorrectionHistory,
    EvidenceBindingCorrection,
    EvidenceBindingCorrectionHistory,
    EvidenceBindingId,
    EvidenceCorrection,
    EvidenceCorrectionBasis,
    EvidenceCorrectionEffect,
    EvidenceCorrectionId,
    EvidenceInterpretation,
    EvidenceObservation,
    EvidenceObservationCorrection,
    EvidenceObservationCorrectionHistory,
    EvidenceObservationId,
    EvidenceSufficiencyAssessmentId,
)
from polaris.domain.evidence.bindings import EvidenceBinding
from polaris.domain.evidence.sufficiency import (
    EvidenceSufficiencyAssessment,
    matches_assessment_requirement_version,
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
from .sufficiency import (
    EvidenceSufficiencyBasis,
    EvidenceSufficiencyBasisResolution,
    EvidenceSufficiencyInvalidHistory,
    rederive_evidence_assessment,
)


class EvidenceCorrectionFamily(StrEnum):
    OBSERVATION = "observation"
    BINDING = "binding"
    ASSESSMENT = "assessment"


# duplicate-code: family commands and correction facts have distinct typed
# contracts even though their common metadata fields intentionally align.
# arid: disable
@dataclass(frozen=True, slots=True)
class RecordEvidenceObservationCorrectionCommand:
    operation_id: OperationId
    root_id: EvidenceObservationId
    target: EvidenceObservationId | EvidenceCorrectionId
    # duplicate-code: the command and committed fact are separate contracts;
    # sharing their fields would couple application input to immutable history.
    # arid: disable
    effect: EvidenceCorrectionEffect
    attribution: ActorAttribution
    basis: EvidenceCorrectionBasis
    effective_at: datetime
    # arid: enable
    replacement: EvidenceObservation | None = None

    def __post_init__(self) -> None:
        _validate_command(
            self,
            EvidenceObservationId,
            EvidenceObservation,
        )


@dataclass(frozen=True, slots=True)
class RecordEvidenceBindingCorrectionCommand:
    operation_id: OperationId
    root_id: EvidenceBindingId
    target: EvidenceBindingId | EvidenceCorrectionId
    effect: EvidenceCorrectionEffect
    attribution: ActorAttribution
    basis: EvidenceCorrectionBasis
    effective_at: datetime
    replacement: EvidenceBinding | None = None

    def __post_init__(self) -> None:
        _validate_command(self, EvidenceBindingId, EvidenceBinding)


@dataclass(frozen=True, slots=True)
class RecordEvidenceAssessmentCorrectionCommand:
    operation_id: OperationId
    root_id: EvidenceSufficiencyAssessmentId
    target: EvidenceSufficiencyAssessmentId | EvidenceCorrectionId
    # duplicate-code: the assessment command owns its own typed request fields;
    # sharing these with binding commands would hide the caller-proof exclusion.
    # arid: disable
    effect: EvidenceCorrectionEffect
    attribution: ActorAttribution
    basis: EvidenceCorrectionBasis
    effective_at: datetime
    # arid: enable

    def __post_init__(self) -> None:
        _validate_command(
            self, EvidenceSufficiencyAssessmentId, EvidenceSufficiencyAssessment
        )


# arid: enable


type RecordEvidenceCorrectionCommand = (
    RecordEvidenceObservationCorrectionCommand
    | RecordEvidenceBindingCorrectionCommand
    | RecordEvidenceAssessmentCorrectionCommand
)
type EvidenceCorrectionRootId = (
    EvidenceObservationId | EvidenceBindingId | EvidenceSufficiencyAssessmentId
)
# duplicate-code: the application command union and domain fact-reference union
# serve separate validation boundaries that must remain explicit.
# arid: disable
type EvidenceCorrectionTarget = (
    EvidenceObservationId
    | EvidenceBindingId
    | EvidenceSufficiencyAssessmentId
    | EvidenceCorrectionId
)
# arid: enable
type EvidenceCorrectionReplacement = (
    EvidenceObservation | EvidenceBinding | EvidenceSufficiencyAssessment | None
)


def _validate_command(
    command: RecordEvidenceCorrectionCommand,
    root_type: type[object],
    replacement_type: type[object],
) -> None:
    if type(command.operation_id) is not OperationId:
        raise TypeError("operation_id must be OperationId")
    if type(command.root_id) is not root_type:
        raise TypeError(f"root_id must be {root_type.__name__}")
    if type(command.target) not in (root_type, EvidenceCorrectionId):
        raise TypeError(f"target must be {root_type.__name__} or EvidenceCorrectionId")
    if type(command.effect) is not EvidenceCorrectionEffect:
        raise TypeError("effect must be EvidenceCorrectionEffect")
    if not is_actor_attribution(command.attribution):
        raise TypeError("attribution must be an ActorAttribution")
    if type(command.basis) is not EvidenceCorrectionBasis:
        raise TypeError("basis must be EvidenceCorrectionBasis")
    require_aware_recording_time(command.effective_at)
    if command.effect is EvidenceCorrectionEffect.REVISE and not isinstance(
        command, RecordEvidenceAssessmentCorrectionCommand
    ):
        if type(command.replacement) is not replacement_type:
            raise ValueError("REVISE requires a complete family-specific replacement")
    elif getattr(command, "replacement", None) is not None:
        raise ValueError("RETRACT cannot carry a replacement")


@dataclass(frozen=True, slots=True)
class EvidenceCorrectionSemanticRequest:
    # duplicate-code: the semantic request is the receipt identity contract,
    # distinct from both transport commands and durable domain correction facts.
    # arid: disable
    family: EvidenceCorrectionFamily
    root_id: EvidenceCorrectionRootId
    target: EvidenceCorrectionTarget
    effect: EvidenceCorrectionEffect
    attribution: ActorAttribution
    basis: EvidenceCorrectionBasis
    effective_at: datetime
    replacement: EvidenceCorrectionReplacement
    # arid: enable

    @classmethod
    def from_command(
        cls,
        command: RecordEvidenceCorrectionCommand,
    ) -> EvidenceCorrectionSemanticRequest:
        return cls(
            family=_command_family(command),
            root_id=command.root_id,
            target=command.target,
            effect=command.effect,
            attribution=command.attribution,
            basis=command.basis,
            effective_at=command.effective_at,
            replacement=(
                command.replacement
                if isinstance(
                    command,
                    (
                        RecordEvidenceObservationCorrectionCommand,
                        RecordEvidenceBindingCorrectionCommand,
                    ),
                )
                else None
            ),
        )

    @classmethod
    def from_correction(
        cls,
        correction: EvidenceCorrection,
    ) -> EvidenceCorrectionSemanticRequest:
        return cls(
            family=correction_family(correction),
            root_id=correction.root_id,
            target=correction.target,
            effect=correction.effect,
            attribution=correction.attribution,
            basis=correction.basis,
            effective_at=correction.effective_at,
            replacement=(
                None
                if type(correction) is EvidenceAssessmentCorrection
                else correction.replacement
            ),
        )


@dataclass(frozen=True, slots=True)
class EvidenceCorrectionResult:
    correction_id: EvidenceCorrectionId
    replayed: bool = False


@dataclass(frozen=True, slots=True)
class EvidenceCorrectionReceipt:
    operation_id: OperationId
    request: EvidenceCorrectionSemanticRequest
    result: EvidenceCorrectionResult


@dataclass(frozen=True, slots=True)
class EvidenceCorrectionCommit:
    operation_id: OperationId
    request: EvidenceCorrectionSemanticRequest
    correction: EvidenceCorrection
    committed_at: datetime
    assessment_basis: EvidenceSufficiencyBasis | None = None
    assessment_commit_basis: EvidenceSufficiencyBasis | None = None

    def __post_init__(self) -> None:
        if type(self.operation_id) is not OperationId:
            raise TypeError("operation_id must be OperationId")
        if type(self.request) is not EvidenceCorrectionSemanticRequest:
            raise TypeError("request must be EvidenceCorrectionSemanticRequest")
        if type(self.correction) not in (
            EvidenceObservationCorrection,
            EvidenceBindingCorrection,
            EvidenceAssessmentCorrection,
        ):
            raise TypeError("correction must be a family-specific Evidence correction")
        if self.request != EvidenceCorrectionSemanticRequest.from_correction(
            self.correction
        ):
            raise ValueError("correction fact must match the semantic request")
        require_aware_recording_time(self.committed_at)
        if type(self.correction) is EvidenceAssessmentCorrection:
            if (
                type(self.assessment_basis) is not EvidenceSufficiencyBasis
                or type(self.assessment_commit_basis) is not EvidenceSufficiencyBasis
            ):
                raise TypeError("assessment correction requires both exact bases")
        elif (
            self.assessment_basis is not None
            or self.assessment_commit_basis is not None
        ):
            raise TypeError("non-assessment correction cannot carry assessment bases")
        if self.correction.recorded_at != self.committed_at:
            raise ValueError("correction recorded_at must match committed_at")


@dataclass(frozen=True, slots=True)
class EvidenceCorrectionCommitted:
    receipt: EvidenceCorrectionReceipt


@dataclass(frozen=True, slots=True)
class EvidenceCorrectionReplayed:
    receipt: EvidenceCorrectionReceipt


@dataclass(frozen=True, slots=True)
class EvidenceCorrectionIdempotencyConflict:
    operation_id: OperationId


@dataclass(frozen=True, slots=True)
class EvidenceCorrectionReferenceConflict:
    root_id: EvidenceCorrectionRootId
    target: EvidenceCorrectionTarget
    reason: str


@dataclass(frozen=True, slots=True)
class EvidenceCorrectionUnavailable:
    reason: str


@dataclass(frozen=True, slots=True)
class EvidenceCorrectionStaleBasis:
    reason: str


class EvidenceCorrectionAuthorityKind(StrEnum):
    MISSING = "missing"
    UNAVAILABLE = "unavailable"
    CONTESTED = "contested"
    INVALID = "invalid"


@dataclass(frozen=True, slots=True)
class EvidenceCorrectionAuthorityFailure:
    kind: EvidenceCorrectionAuthorityKind
    reason: str


@dataclass(frozen=True, slots=True)
class EvidenceCorrectionInvalidHistory:
    reason: str


type EvidenceCorrectionCommitOutcome = (
    EvidenceCorrectionCommitted
    | EvidenceCorrectionReplayed
    | EvidenceCorrectionIdempotencyConflict
    | EvidenceCorrectionReferenceConflict
    | EvidenceCorrectionUnavailable
    | EvidenceCorrectionStaleBasis
    | EvidenceCorrectionAuthorityFailure
    | EvidenceCorrectionInvalidHistory
)


class EvidenceCorrectionStore(Protocol):
    async def get_correction_receipt(
        self,
        operation_id: OperationId,
    ) -> EvidenceCorrectionReceipt | None: ...

    async def commit_correction(
        self,
        commit: EvidenceCorrectionCommit,
    ) -> EvidenceCorrectionCommitOutcome: ...

    async def load_observation_history(
        self,
        root_id: EvidenceObservationId,
    ) -> EvidenceObservationCorrectionHistory | None: ...

    async def load_binding_history(
        self,
        root_id: EvidenceBindingId,
    ) -> EvidenceBindingCorrectionHistory | None: ...

    async def load_assessment_history(
        self,
        root_id: EvidenceSufficiencyAssessmentId,
    ) -> EvidenceAssessmentCorrectionHistory | None: ...

    async def load_sufficiency_basis(
        self,
        applicability_key: EvidenceRequirementApplicabilityKey,
        *,
        effective_at: datetime,
        known_at: datetime,
    ) -> EvidenceSufficiencyBasisResolution: ...


class EvidenceCorrectionHistoryConflict(EvidenceApplicationError):
    def __init__(self, conflict: EvidenceCorrectionReferenceConflict) -> None:
        super().__init__(conflict.reason)
        self.conflict = conflict


class EvidenceCorrectionBasisConflict(EvidenceApplicationError):
    pass


class EvidenceCorrectionAuthorityConflict(EvidenceApplicationError):
    def __init__(self, failure: EvidenceCorrectionAuthorityFailure) -> None:
        super().__init__(failure.reason)
        self.kind = failure.kind


class EvidenceCorrectionRootNotFound(EvidenceApplicationError):
    def __init__(self, root_id: EvidenceCorrectionRootId) -> None:
        super().__init__("Evidence correction root was not found")
        self.root_id = root_id


class EvidenceCorrectionService:
    def __init__(
        self,
        *,
        store: EvidenceCorrectionStore,
        now: Callable[[], datetime],
        new_uuid: Callable[[], UUID] = uuid4,
    ) -> None:
        self._store = store
        self._now = now
        self._new_uuid = new_uuid

    async def record(
        self,
        command: RecordEvidenceCorrectionCommand,
    ) -> EvidenceCorrectionResult:
        # duplicate-code: correction command replay has correction-specific
        # outcomes; sharing service flow with sufficiency would couple ports.
        # arid: disable
        request = EvidenceCorrectionSemanticRequest.from_command(command)
        receipt = await self._read_receipt(command.operation_id)
        if receipt is not None:
            return _replay(receipt, request, command.operation_id)
        recorded_at = self._now()
        require_aware_recording_time(recorded_at)
        # arid: enable
        assessment_bases = (
            await self._prepare_assessment(command, recorded_at)
            if type(command) is RecordEvidenceAssessmentCorrectionCommand
            else None
        )
        correction = _new_correction(
            command,
            EvidenceCorrectionId(self._new_uuid()),
            recorded_at,
            replacement=(assessment_bases[0] if assessment_bases else None),
        )
        outcome = await self._store.commit_correction(
            EvidenceCorrectionCommit(
                command.operation_id,
                request,
                correction,
                recorded_at,
                assessment_bases[1] if assessment_bases else None,
                assessment_bases[2] if assessment_bases else None,
            )
        )
        if isinstance(outcome, EvidenceCorrectionCommitted):
            return outcome.receipt.result
        if isinstance(outcome, EvidenceCorrectionReplayed):
            return _replay(outcome.receipt, request, command.operation_id)
        if isinstance(outcome, EvidenceCorrectionIdempotencyConflict):
            raise EvidenceIdempotencyConflict(outcome.operation_id)
        if isinstance(outcome, EvidenceCorrectionReferenceConflict):
            raise EvidenceCorrectionHistoryConflict(outcome)
        if isinstance(outcome, EvidenceCorrectionUnavailable):
            raise EvidencePersistenceUnavailable(outcome.reason)
        if isinstance(outcome, EvidenceCorrectionStaleBasis):
            raise EvidenceCorrectionBasisConflict(outcome.reason)
        if isinstance(outcome, EvidenceCorrectionAuthorityFailure):
            raise EvidenceCorrectionAuthorityConflict(outcome)
        if isinstance(outcome, EvidenceCorrectionInvalidHistory):
            raise _history_conflict(command, outcome.reason)
        raise AssertionError("EvidenceCorrectionStore returned an unsupported outcome")

    async def _prepare_assessment(
        self,
        command: RecordEvidenceAssessmentCorrectionCommand,
        recorded_at: datetime,
    ) -> tuple[
        EvidenceSufficiencyAssessment | None,
        EvidenceSufficiencyBasis,
        EvidenceSufficiencyBasis,
    ]:
        history = await self._load_assessment_history(command.root_id)
        root = history.root
        if recorded_at < root.recorded_at:
            raise _history_conflict(
                command, "assessment correction cannot be recorded before its root"
            )
        if command.effective_at < root.effective_at:
            raise EvidenceCorrectionBasisConflict(
                "assessment correction cannot precede its attributable boundary"
            )
        original = await self._assessment_basis(
            command,
            root.applicability_key,
            effective_at=root.effective_at,
            known_at=root.known_at,
        )
        current = await self._assessment_basis(
            command,
            root.applicability_key,
            effective_at=recorded_at,
            known_at=recorded_at,
        )
        # duplicate-code: preparation and trusted transactional revalidation
        # independently derive the same proof to detect changes before append.
        # arid: disable
        replacement = _derived_assessment(
            root,
            original,
            effective_at=root.effective_at,
            known_at=root.known_at,
        )
        # arid: enable
        current_assessment = _derived_assessment(
            root,
            current,
            effective_at=recorded_at,
            known_at=recorded_at,
        )
        if not _same_external_basis(original, current) or not _same_assessment_basis(
            replacement,
            current_assessment,
            allow_support_drift=bool(history.corrections),
        ):
            raise EvidenceCorrectionBasisConflict(
                "assessment basis changed; record a new reassessment root"
            )
        if (
            not history.corrections
            and original.support_version != current.support_version
        ):
            raise EvidenceCorrectionBasisConflict(
                "assessment support version changed; record a new reassessment root"
            )
        return (
            replacement if command.effect is EvidenceCorrectionEffect.REVISE else None,
            original,
            current,
        )

    async def _load_assessment_history(
        self,
        root_id: EvidenceSufficiencyAssessmentId,
    ) -> EvidenceAssessmentCorrectionHistory:
        try:
            history = await self._store.load_assessment_history(root_id)
        except EvidenceCommandReadUnavailable as error:
            raise EvidencePersistenceUnavailable(str(error)) from error
        if history is None:
            raise EvidenceCorrectionRootNotFound(root_id)
        return history

    async def _assessment_basis(
        self,
        command: RecordEvidenceAssessmentCorrectionCommand,
        key: EvidenceRequirementApplicabilityKey,
        *,
        effective_at: datetime,
        known_at: datetime,
    ) -> EvidenceSufficiencyBasis:
        try:
            result = await self._store.load_sufficiency_basis(
                key, effective_at=effective_at, known_at=known_at
            )
        except EvidenceCommandReadUnavailable as error:
            raise EvidenceCorrectionAuthorityConflict(
                EvidenceCorrectionAuthorityFailure(
                    EvidenceCorrectionAuthorityKind.UNAVAILABLE, str(error)
                )
            ) from error
        if isinstance(result, EvidenceSufficiencyBasis):
            return result
        if isinstance(result, EvidenceSufficiencyInvalidHistory):
            raise _history_conflict(command, result.reason)
        raise EvidenceCorrectionAuthorityConflict(_authority_failure(result))

    async def inspect_observation(
        self,
        root_id: EvidenceObservationId,
        *,
        effective_at: datetime,
        known_at: datetime,
    ) -> EvidenceInterpretation[EvidenceObservation]:
        history = await self._load_observation_history(root_id)
        return history.interpret(effective_at=effective_at, known_at=known_at)

    async def inspect_binding(
        self,
        root_id: EvidenceBindingId,
        *,
        effective_at: datetime,
        known_at: datetime,
    ) -> EvidenceInterpretation[EvidenceBinding]:
        # duplicate-code: each typed history load retains its root-specific
        # port and result; a generic loader would hide the family boundary.
        # arid: disable
        try:
            history = await self._store.load_binding_history(root_id)
        except EvidenceCommandReadUnavailable as error:
            raise EvidencePersistenceUnavailable(str(error)) from error
        if history is None:
            raise EvidenceCorrectionRootNotFound(root_id)
        # arid: enable
        return history.interpret(effective_at=effective_at, known_at=known_at)

    async def inspect_assessment(
        self,
        root_id: EvidenceSufficiencyAssessmentId,
        *,
        effective_at: datetime,
        known_at: datetime,
    ) -> EvidenceInterpretation[EvidenceSufficiencyAssessment]:
        history = await self._load_assessment_history(root_id)
        return history.interpret(effective_at=effective_at, known_at=known_at)

    async def _read_receipt(
        self,
        operation_id: OperationId,
    ) -> EvidenceCorrectionReceipt | None:
        try:
            return await self._store.get_correction_receipt(operation_id)
        except EvidenceCommandReadUnavailable as error:
            raise EvidencePersistenceUnavailable(str(error)) from error

    async def _load_observation_history(
        self,
        root_id: EvidenceObservationId,
    ) -> EvidenceObservationCorrectionHistory:
        # duplicate-code: this loader preserves the observation-specific port
        # and failure type independently from binding inspection.
        # arid: disable
        try:
            history = await self._store.load_observation_history(root_id)
        except EvidenceCommandReadUnavailable as error:
            raise EvidencePersistenceUnavailable(str(error)) from error
        if history is None:
            raise EvidenceCorrectionRootNotFound(root_id)
        # arid: enable
        return history


def _command_family(
    command: RecordEvidenceCorrectionCommand,
) -> EvidenceCorrectionFamily:
    if type(command) is RecordEvidenceObservationCorrectionCommand:
        return EvidenceCorrectionFamily.OBSERVATION
    if type(command) is RecordEvidenceBindingCorrectionCommand:
        return EvidenceCorrectionFamily.BINDING
    if type(command) is RecordEvidenceAssessmentCorrectionCommand:
        return EvidenceCorrectionFamily.ASSESSMENT
    raise TypeError("unsupported Evidence correction command")


def _new_correction(
    command: RecordEvidenceCorrectionCommand,
    correction_id: EvidenceCorrectionId,
    recorded_at: datetime,
    *,
    replacement: EvidenceSufficiencyAssessment | None = None,
) -> EvidenceCorrection:
    # duplicate-code: explicit typed constructors keep the family-specific
    # root and replacement types visible at this application boundary.
    # arid: disable
    if type(command) is RecordEvidenceBindingCorrectionCommand:
        return EvidenceBindingCorrection(
            correction_id,
            command.root_id,
            command.target,
            command.effect,
            command.attribution,
            command.basis,
            command.effective_at,
            recorded_at,
            command.replacement,
        )
    if type(command) is RecordEvidenceAssessmentCorrectionCommand:
        return EvidenceAssessmentCorrection(
            correction_id,
            command.root_id,
            command.target,
            command.effect,
            command.attribution,
            command.basis,
            command.effective_at,
            recorded_at,
            replacement,
        )
    if type(command) is not RecordEvidenceObservationCorrectionCommand:
        raise TypeError("unsupported Evidence correction command")
    return EvidenceObservationCorrection(
        correction_id,
        command.root_id,
        command.target,
        command.effect,
        command.attribution,
        command.basis,
        command.effective_at,
        recorded_at,
        command.replacement,
    )
    # arid: enable


def _replay(
    receipt: EvidenceCorrectionReceipt,
    request: EvidenceCorrectionSemanticRequest,
    operation_id: OperationId,
) -> EvidenceCorrectionResult:
    # duplicate-code: the canonical replay validator is shared; this wrapper
    # intentionally constructs the correction-specific public result.
    # arid: disable
    require_exact_replay(
        receipt_operation_id=receipt.operation_id,
        receipt_request=receipt.request,
        operation_id=operation_id,
        request=request,
    )
    return EvidenceCorrectionResult(receipt.result.correction_id, replayed=True)
    # arid: enable


def correction_family(
    correction: EvidenceCorrection,
) -> EvidenceCorrectionFamily:
    if type(correction) is EvidenceObservationCorrection:
        return EvidenceCorrectionFamily.OBSERVATION
    if type(correction) is EvidenceBindingCorrection:
        return EvidenceCorrectionFamily.BINDING
    if type(correction) is EvidenceAssessmentCorrection:
        return EvidenceCorrectionFamily.ASSESSMENT
    raise TypeError("unsupported Evidence correction")


def _history_conflict(
    command: RecordEvidenceCorrectionCommand,
    reason: str,
) -> EvidenceCorrectionHistoryConflict:
    return EvidenceCorrectionHistoryConflict(
        EvidenceCorrectionReferenceConflict(command.root_id, command.target, reason)
    )


def _derived_assessment(
    root: EvidenceSufficiencyAssessment,
    basis: EvidenceSufficiencyBasis,
    *,
    effective_at: datetime,
    known_at: datetime,
) -> EvidenceSufficiencyAssessment:
    version = basis.requirement_version
    if not matches_assessment_requirement_version(root, version):
        raise EvidenceCorrectionBasisConflict(
            "changed requirement assignment/version requires a new assessment root"
        )
    return rederive_evidence_assessment(
        root, basis, effective_at=effective_at, known_at=known_at
    )


def _same_assessment_basis(
    original: EvidenceSufficiencyAssessment,
    current: EvidenceSufficiencyAssessment,
    *,
    allow_support_drift: bool = False,
) -> bool:
    return (
        original.requirement_set_id == current.requirement_set_id
        and original.requirement_version_id == current.requirement_version_id
        and (allow_support_drift or original.support_version == current.support_version)
        and original.basis_guards == current.basis_guards
        and original.requirement_assessments == current.requirement_assessments
        and original.result is current.result
        and original.no_requirements_witness == current.no_requirements_witness
    )


def _same_external_basis(
    original: EvidenceSufficiencyBasis,
    current: EvidenceSufficiencyBasis,
) -> bool:
    return (
        original.requirement_version == current.requirement_version
        and original.interpretations == current.interpretations
        and original.guards == current.guards
    )


def _authority_failure(
    result: EvidenceSufficiencyBasisResolution,
) -> EvidenceCorrectionAuthorityFailure:
    if isinstance(result, MissingEvidenceRequirementAuthority):
        return EvidenceCorrectionAuthorityFailure(
            EvidenceCorrectionAuthorityKind.MISSING, "requirement authority is missing"
        )
    if isinstance(result, UnavailableEvidenceRequirementAuthority):
        return EvidenceCorrectionAuthorityFailure(
            EvidenceCorrectionAuthorityKind.UNAVAILABLE, result.reason
        )
    if isinstance(result, ContestedEvidenceRequirementAuthority):
        return EvidenceCorrectionAuthorityFailure(
            EvidenceCorrectionAuthorityKind.CONTESTED,
            "requirement authority is contested",
        )
    if isinstance(result, InvalidEvidenceRequirementAuthority):
        return EvidenceCorrectionAuthorityFailure(
            EvidenceCorrectionAuthorityKind.INVALID, result.reason
        )
    raise TypeError("unsupported assessment authority result")


# duplicate-code: module exports and the package facade are separate public
# import contracts; deriving one list from the other would hide export drift.
# arid: disable
__all__ = [
    "EvidenceCorrectionAuthorityConflict",
    "EvidenceCorrectionAuthorityFailure",
    "EvidenceCorrectionAuthorityKind",
    "EvidenceCorrectionBasisConflict",
    "EvidenceCorrectionInvalidHistory",
    "EvidenceCorrectionStaleBasis",
    "EvidenceCorrectionCommit",
    "EvidenceCorrectionCommitOutcome",
    "EvidenceCorrectionCommitted",
    "EvidenceCorrectionFamily",
    "EvidenceCorrectionHistoryConflict",
    "EvidenceCorrectionIdempotencyConflict",
    "EvidenceCorrectionReceipt",
    "EvidenceCorrectionReferenceConflict",
    "EvidenceCorrectionReplayed",
    "EvidenceCorrectionResult",
    "EvidenceCorrectionRootNotFound",
    "EvidenceCorrectionSemanticRequest",
    "EvidenceCorrectionService",
    "EvidenceCorrectionStore",
    "EvidenceCorrectionUnavailable",
    "RecordEvidenceCorrectionCommand",
    "RecordEvidenceBindingCorrectionCommand",
    "RecordEvidenceAssessmentCorrectionCommand",
    "RecordEvidenceObservationCorrectionCommand",
    "correction_family",
]
# arid: enable
