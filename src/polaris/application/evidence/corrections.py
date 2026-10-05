from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID, uuid4

from polaris.domain.actors import ActorAttribution, is_actor_attribution
from polaris.domain.decisions import OperationId
from polaris.domain.evidence import (
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
)
from polaris.domain.evidence.bindings import EvidenceBinding

from .contracts import (
    EvidenceApplicationError,
    EvidenceCommandReadUnavailable,
    EvidenceIdempotencyConflict,
    EvidencePersistenceUnavailable,
    require_aware_recording_time,
    require_exact_replay,
)


class EvidenceCorrectionFamily(StrEnum):
    OBSERVATION = "observation"
    BINDING = "binding"


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


# arid: enable


type RecordEvidenceCorrectionCommand = (
    RecordEvidenceObservationCorrectionCommand | RecordEvidenceBindingCorrectionCommand
)
type EvidenceCorrectionRootId = EvidenceObservationId | EvidenceBindingId
type EvidenceCorrectionTarget = (
    EvidenceObservationId | EvidenceBindingId | EvidenceCorrectionId
)
type EvidenceCorrectionReplacement = EvidenceObservation | EvidenceBinding | None


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
    if command.effect is EvidenceCorrectionEffect.REVISE:
        if type(command.replacement) is not replacement_type:
            raise ValueError("REVISE requires a complete family-specific replacement")
    elif command.replacement is not None:
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
            replacement=command.replacement,
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
            replacement=correction.replacement,
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

    def __post_init__(self) -> None:
        if type(self.operation_id) is not OperationId:
            raise TypeError("operation_id must be OperationId")
        if type(self.request) is not EvidenceCorrectionSemanticRequest:
            raise TypeError("request must be EvidenceCorrectionSemanticRequest")
        if type(self.correction) not in (
            EvidenceObservationCorrection,
            EvidenceBindingCorrection,
        ):
            raise TypeError("correction must be a family-specific Evidence correction")
        if self.request != EvidenceCorrectionSemanticRequest.from_correction(
            self.correction
        ):
            raise ValueError("correction fact must match the semantic request")
        require_aware_recording_time(self.committed_at)
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


type EvidenceCorrectionCommitOutcome = (
    EvidenceCorrectionCommitted
    | EvidenceCorrectionReplayed
    | EvidenceCorrectionIdempotencyConflict
    | EvidenceCorrectionReferenceConflict
    | EvidenceCorrectionUnavailable
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


class EvidenceCorrectionHistoryConflict(EvidenceApplicationError):
    def __init__(self, conflict: EvidenceCorrectionReferenceConflict) -> None:
        super().__init__(conflict.reason)
        self.conflict = conflict


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
        correction = _new_correction(
            command,
            EvidenceCorrectionId(self._new_uuid()),
            recorded_at,
        )
        outcome = await self._store.commit_correction(
            EvidenceCorrectionCommit(
                command.operation_id,
                request,
                correction,
                recorded_at,
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
        raise AssertionError("EvidenceCorrectionStore returned an unsupported outcome")

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
    raise TypeError("unsupported Evidence correction command")


def _new_correction(
    command: RecordEvidenceCorrectionCommand,
    correction_id: EvidenceCorrectionId,
    recorded_at: datetime,
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
    raise TypeError("unsupported Evidence correction")


__all__ = [
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
    "RecordEvidenceObservationCorrectionCommand",
    "correction_family",
]
