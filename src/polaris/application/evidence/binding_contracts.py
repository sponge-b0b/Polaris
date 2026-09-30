from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from polaris.domain.decisions import OperationId
from polaris.domain.evidence.bindings import (
    EvidenceAvailability,
    EvidenceBinding,
    EvidenceFreshnessAuthorityReference,
    EvidenceFreshnessBasisReference,
    EvidenceMaterialQualification,
    EvidenceRole,
)
from polaris.domain.evidence.judgments import EvidenceJudgmentRef, EvidenceScope, EvidenceUse
from polaris.domain.evidence.observations import EvidenceBindingId, EvidenceObservationId


@dataclass(frozen=True, slots=True)
class RecordEvidenceBindingCommand:
    operation_id: OperationId
    observation_id: EvidenceObservationId
    target: EvidenceJudgmentRef
    scope: EvidenceScope
    evidence_use: EvidenceUse
    role: EvidenceRole
    availability: EvidenceAvailability
    materially_used: bool
    effective_at: datetime
    material_qualification: EvidenceMaterialQualification | None = None
    freshness_authority: EvidenceFreshnessAuthorityReference | None = None
    freshness_basis: EvidenceFreshnessBasisReference | None = None

    def __post_init__(self) -> None:
        if type(self.operation_id) is not OperationId:
            raise TypeError("operation_id must be OperationId")
        if type(self.observation_id) is not EvidenceObservationId:
            raise TypeError("observation_id must be EvidenceObservationId")
        if type(self.evidence_use) is not EvidenceUse:
            raise TypeError("evidence_use must be EvidenceUse")
        if type(self.role) is not EvidenceRole:
            raise TypeError("role must be EvidenceRole")
        if type(self.availability) is not EvidenceAvailability:
            raise TypeError("availability must be EvidenceAvailability")
        if type(self.materially_used) is not bool:
            raise TypeError("materially_used must be bool")
        _aware(self.effective_at, "effective_at")


@dataclass(frozen=True, slots=True)
class EvidenceBindingSemanticRequest:
    observation_id: EvidenceObservationId
    target: EvidenceJudgmentRef
    scope: EvidenceScope
    evidence_use: EvidenceUse
    role: EvidenceRole
    availability: EvidenceAvailability
    materially_used: bool
    effective_at: datetime
    material_qualification: EvidenceMaterialQualification | None
    freshness_authority: EvidenceFreshnessAuthorityReference | None
    freshness_basis: EvidenceFreshnessBasisReference | None

    @classmethod
    def from_command(
        cls,
        command: RecordEvidenceBindingCommand,
    ) -> EvidenceBindingSemanticRequest:
        return cls(
            observation_id=command.observation_id,
            target=command.target,
            scope=command.scope,
            evidence_use=command.evidence_use,
            role=command.role,
            availability=command.availability,
            materially_used=command.materially_used,
            effective_at=command.effective_at,
            material_qualification=command.material_qualification,
            freshness_authority=command.freshness_authority,
            freshness_basis=command.freshness_basis,
        )


@dataclass(frozen=True, slots=True)
class EvidenceBindingResult:
    binding_id: EvidenceBindingId
    replayed: bool = False


@dataclass(frozen=True, slots=True)
class EvidenceBindingReceipt:
    operation_id: OperationId
    request: EvidenceBindingSemanticRequest
    result: EvidenceBindingResult


@dataclass(frozen=True, slots=True)
class EvidenceBindingCommit:
    operation_id: OperationId
    request: EvidenceBindingSemanticRequest
    binding: EvidenceBinding
    committed_at: datetime

    def __post_init__(self) -> None:
        if type(self.operation_id) is not OperationId:
            raise TypeError("operation_id must be OperationId")
        if type(self.request) is not EvidenceBindingSemanticRequest:
            raise TypeError("request must be EvidenceBindingSemanticRequest")
        if type(self.binding) is not EvidenceBinding:
            raise TypeError("binding must be EvidenceBinding")
        _aware(self.committed_at, "committed_at")


@dataclass(frozen=True, slots=True)
class EvidenceBindingCommitted:
    receipt: EvidenceBindingReceipt


@dataclass(frozen=True, slots=True)
class EvidenceBindingReplayed:
    receipt: EvidenceBindingReceipt


@dataclass(frozen=True, slots=True)
class EvidenceBindingIdempotencyConflict:
    operation_id: OperationId


@dataclass(frozen=True, slots=True)
class EvidenceBindingObservationConflict:
    observation_id: EvidenceObservationId


@dataclass(frozen=True, slots=True)
class EvidenceBindingUnavailable:
    reason: str


type EvidenceBindingCommitOutcome = (
    EvidenceBindingCommitted
    | EvidenceBindingReplayed
    | EvidenceBindingIdempotencyConflict
    | EvidenceBindingObservationConflict
    | EvidenceBindingUnavailable
)


class EvidenceBindingStore(Protocol):
    async def get_binding_receipt(
        self,
        operation_id: OperationId,
    ) -> EvidenceBindingReceipt | None:
        ...

    async def commit_binding(
        self,
        commit: EvidenceBindingCommit,
    ) -> EvidenceBindingCommitOutcome: ...

    async def load_binding(
        self,
        binding_id: EvidenceBindingId,
    ) -> EvidenceBinding | None: ...


def _aware(value: object, field: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise ValueError(f"{field} must be timezone-aware")
