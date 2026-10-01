from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from uuid import UUID, uuid4

from polaris.domain.decisions import OperationId
from polaris.domain.evidence.bindings import EvidenceBinding
from polaris.domain.evidence.claims import ClaimCatalogVersion
from polaris.domain.evidence.judgments import ClaimSpecificEvidenceScope
from polaris.domain.evidence.observations import EvidenceBindingId

from .binding_contracts import (
    EvidenceBindingCommit,
    EvidenceBindingCommitted,
    EvidenceBindingIdempotencyConflict,
    EvidenceBindingObservationConflict,
    EvidenceBindingReceipt,
    EvidenceBindingReplayed,
    EvidenceBindingResult,
    EvidenceBindingSemanticRequest,
    EvidenceBindingStore,
    EvidenceBindingUnavailable,
    RecordEvidenceBindingCommand,
)
from .freshness import evaluate_binding_freshness
from .claims import (
    ClaimCatalogMembershipResolver,
    ClaimMembershipFailure,
    InvalidClaimReference,
    ResolvedClaimMembership,
    UnavailableClaimCatalog,
)
from .requirements import EvidenceRequirementVersionResolver
from .contracts import (
    EvidenceApplicationError,
    EvidenceCommandReadUnavailable,
    EvidenceIdempotencyConflict,
    EvidencePersistenceUnavailable,
    require_aware_recording_time,
    require_exact_replay,
)


class EvidenceBindingObservationReferenceConflict(EvidenceApplicationError):
    def __init__(self, observation_id: object) -> None:
        super().__init__(f"Evidence observation does not exist: {observation_id}")
        self.observation_id = observation_id


class EvidenceBindingClaimMembershipRejected(EvidenceApplicationError):
    def __init__(self, resolution: ClaimMembershipFailure) -> None:
        super().__init__(f"Evidence claim membership was rejected: {resolution!r}")
        self.resolution = resolution


class EvidenceBindingClaimCatalogUnavailable(EvidenceApplicationError):
    def __init__(self, resolution: UnavailableClaimCatalog) -> None:
        super().__init__(resolution.reason)
        self.resolution = resolution


class EvidenceBindingService:
    def __init__(
        self,
        *,
        store: EvidenceBindingStore,
        now: Callable[[], datetime],
        new_uuid: Callable[[], UUID] = uuid4,
        claim_catalog: ClaimCatalogMembershipResolver | None = None,
        requirements: EvidenceRequirementVersionResolver,
    ) -> None:
        self._store = store
        self._now = now
        self._new_uuid = new_uuid
        self._claim_catalog = claim_catalog
        self._requirements = requirements

    async def record(
        self,
        command: RecordEvidenceBindingCommand,
    ) -> EvidenceBindingResult:
        request = EvidenceBindingSemanticRequest.from_command(command)
        receipt = await self._read_receipt(command.operation_id)
        if receipt is not None:
            return _replay(receipt, request, command.operation_id)

        committed_at = self._now()
        require_aware_recording_time(committed_at)
        await self._validate_claim_membership(command, known_at=committed_at)
        freshness = await evaluate_binding_freshness(
            self._requirements,
            request.requirement_key,
            request.freshness_basis,
            effective_at=command.effective_at,
            known_at=committed_at,
        )
        binding = EvidenceBinding(
            binding_id=EvidenceBindingId(self._new_uuid()),
            observation_id=command.observation_id,
            target=command.target,
            scope=command.scope,
            evidence_use=command.evidence_use,
            role=command.role,
            availability=command.availability,
            materially_used=command.materially_used,
            effective_at=command.effective_at,
            recorded_at=committed_at,
            material_qualification=command.material_qualification,
            freshness=freshness,
        )
        outcome = await self._store.commit_binding(
            EvidenceBindingCommit(
                operation_id=command.operation_id,
                request=request,
                binding=binding,
                committed_at=committed_at,
            )
        )
        if isinstance(outcome, EvidenceBindingCommitted):
            return outcome.receipt.result
        if isinstance(outcome, EvidenceBindingReplayed):
            return _replay(outcome.receipt, request, command.operation_id)
        if isinstance(outcome, EvidenceBindingIdempotencyConflict):
            raise EvidenceIdempotencyConflict(outcome.operation_id)
        if isinstance(outcome, EvidenceBindingObservationConflict):
            raise EvidenceBindingObservationReferenceConflict(outcome.observation_id)
        if isinstance(outcome, EvidenceBindingUnavailable):
            raise EvidencePersistenceUnavailable(outcome.reason)
        raise AssertionError("EvidenceBindingStore returned an unsupported outcome")

    async def _validate_claim_membership(
        self,
        command: RecordEvidenceBindingCommand,
        *,
        known_at: datetime,
    ) -> None:
        scope = command.scope
        if type(scope) is not ClaimSpecificEvidenceScope:
            return
        if self._claim_catalog is None:
            raise EvidenceBindingClaimCatalogUnavailable(
                UnavailableClaimCatalog(
                    command.target,
                    "target-owned claim catalog resolver is unavailable",
                )
            )
        resolution = await self._claim_catalog.resolve(
            command.target,
            scope.claim_id,
            effective_at=command.effective_at,
            known_at=known_at,
        )
        if isinstance(resolution, ResolvedClaimMembership):
            if (
                resolution.target != command.target
                or resolution.claim_id != scope.claim_id
                or type(resolution.catalog_version) is not ClaimCatalogVersion
            ):
                raise EvidenceBindingClaimMembershipRejected(
                    InvalidClaimReference(command.target, scope.claim_id)
                )
            return
        if isinstance(resolution, UnavailableClaimCatalog):
            raise EvidenceBindingClaimCatalogUnavailable(resolution)
        raise EvidenceBindingClaimMembershipRejected(resolution)

    async def _read_receipt(
        self, operation_id: OperationId
    ) -> EvidenceBindingReceipt | None:
        try:
            return await self._store.get_binding_receipt(operation_id)
        except EvidenceCommandReadUnavailable as error:
            raise EvidencePersistenceUnavailable(str(error)) from error


# duplicate-code: binding replay reconstruction is independently typed
# from observation replay despite sharing the exact-replay predicate.
# arid: disable
def _replay(
    receipt: EvidenceBindingReceipt,
    request: EvidenceBindingSemanticRequest,
    operation_id: OperationId,
) -> EvidenceBindingResult:
    require_exact_replay(
        receipt_operation_id=receipt.operation_id,
        receipt_request=receipt.request,
        operation_id=operation_id,
        request=request,
    )
    return EvidenceBindingResult(
        binding_id=receipt.result.binding_id,
        replayed=True,
    )


# arid: enable
