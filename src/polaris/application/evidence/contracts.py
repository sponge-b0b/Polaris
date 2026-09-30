from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from polaris.domain.decisions import OperationId
from polaris.domain.evidence import (
    EvidenceObservation,
    EvidenceObservationId,
    EvidenceObservationMaterial,
    EvidenceSourceProvenance,
    EvidenceSubjectReference,
)


class EvidenceApplicationError(Exception):
    """Base class for Evidence application-boundary failures."""


@dataclass(slots=True)
class EvidenceIdempotencyConflict(EvidenceApplicationError):
    operation_id: OperationId


@dataclass(slots=True)
class EvidenceSuccessionConflict(EvidenceApplicationError):
    predecessor_id: EvidenceObservationId


class EvidencePersistenceUnavailable(EvidenceApplicationError):
    pass


class EvidenceCommandReadUnavailable(Exception):
    """Technology-neutral failure contract for Evidence persistence reads."""


@dataclass(frozen=True, slots=True)
class RecordEvidenceObservationCommand:
    # duplicate-code: the application command must carry pre-allocation Evidence
    # input explicitly; sharing the domain root shape would collapse the
    # application-owned identity-allocation boundary.
    # arid: disable
    operation_id: OperationId
    source: EvidenceSourceProvenance
    subject: EvidenceSubjectReference
    observed_at: datetime
    acquired_at: datetime
    material: EvidenceObservationMaterial
    effective_at: datetime | None = None
    supersedes_observation_id: EvidenceObservationId | None = None

    def __post_init__(self) -> None:
        if type(self.operation_id) is not OperationId:
            raise TypeError("operation_id must be OperationId")
        if type(self.source) is not EvidenceSourceProvenance:
            raise TypeError("source must be EvidenceSourceProvenance")
        if type(self.subject) is not EvidenceSubjectReference:
            raise TypeError("subject must be EvidenceSubjectReference")
        if type(self.material) is not EvidenceObservationMaterial:
            raise TypeError("material must be EvidenceObservationMaterial")
        _aware(self.observed_at, "observed_at")
        _aware(self.acquired_at, "acquired_at")
        if self.effective_at is not None:
            _aware(self.effective_at, "effective_at")
        if (
            self.supersedes_observation_id is not None
            and type(self.supersedes_observation_id) is not EvidenceObservationId
        ):
            raise TypeError(
                "supersedes_observation_id must be EvidenceObservationId or None"
            )

    # arid: enable


@dataclass(frozen=True, slots=True)
class EvidenceObservationSemanticRequest:
    # duplicate-code: the persisted idempotency request is an application receipt
    # contract, not a domain Evidence root; keeping it explicit preserves that
    # independently evolvable boundary.
    # arid: disable
    source: EvidenceSourceProvenance
    subject: EvidenceSubjectReference
    observed_at: datetime
    acquired_at: datetime
    material: EvidenceObservationMaterial
    effective_at: datetime | None
    supersedes_observation_id: EvidenceObservationId | None
    # arid: enable

    @classmethod
    def from_command(
        cls, command: RecordEvidenceObservationCommand
    ) -> EvidenceObservationSemanticRequest:
        return cls(
            source=command.source,
            subject=command.subject,
            observed_at=command.observed_at,
            acquired_at=command.acquired_at,
            material=command.material,
            effective_at=command.effective_at,
            supersedes_observation_id=command.supersedes_observation_id,
        )


@dataclass(frozen=True, slots=True)
class EvidenceObservationResult:
    observation_id: EvidenceObservationId
    replayed: bool = False


@dataclass(frozen=True, slots=True)
class EvidenceObservationReceipt:
    operation_id: OperationId
    request: EvidenceObservationSemanticRequest
    result: EvidenceObservationResult


@dataclass(frozen=True, slots=True)
class EvidenceObservationCommit:
    operation_id: OperationId
    request: EvidenceObservationSemanticRequest
    observation: EvidenceObservation
    committed_at: datetime

    def __post_init__(self) -> None:
        if type(self.operation_id) is not OperationId:
            raise TypeError("operation_id must be OperationId")
        if type(self.request) is not EvidenceObservationSemanticRequest:
            raise TypeError("request must be EvidenceObservationSemanticRequest")
        if type(self.observation) is not EvidenceObservation:
            raise TypeError("observation must be EvidenceObservation")
        _aware(self.committed_at, "committed_at")


@dataclass(frozen=True, slots=True)
class EvidenceObservationCommitted:
    receipt: EvidenceObservationReceipt


@dataclass(frozen=True, slots=True)
class EvidenceObservationReplayed:
    receipt: EvidenceObservationReceipt


@dataclass(frozen=True, slots=True)
class EvidenceObservationIdempotencyConflict:
    operation_id: OperationId


@dataclass(frozen=True, slots=True)
class EvidenceObservationSuccessionConflict:
    predecessor_id: EvidenceObservationId


@dataclass(frozen=True, slots=True)
class EvidenceObservationUnavailable:
    reason: str


EvidenceObservationCommitOutcome = (
    EvidenceObservationCommitted
    | EvidenceObservationReplayed
    | EvidenceObservationIdempotencyConflict
    | EvidenceObservationSuccessionConflict
    | EvidenceObservationUnavailable
)


class EvidenceObservationStore(Protocol):
    async def get_observation_receipt(
        self, operation_id: OperationId
    ) -> EvidenceObservationReceipt | None:
        """Return a receipt or raise EvidenceCommandReadUnavailable."""
        ...

    async def commit_observation(
        self, commit: EvidenceObservationCommit
    ) -> EvidenceObservationCommitOutcome: ...

    async def load_observation(
        self, observation_id: EvidenceObservationId
    ) -> EvidenceObservation | None:
        """Return the durable observation or raise EvidenceCommandReadUnavailable."""
        ...


# duplicate-code: application timestamp validation owns application-boundary
# failure semantics; sharing a domain or adapter validator would couple layers.
# arid: disable
def _aware(value: object, field: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise ValueError(f"{field} must be timezone-aware")


# arid: enable
