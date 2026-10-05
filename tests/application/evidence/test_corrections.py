import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from polaris.application.evidence import (
    EvidenceCorrectionCommit,
    EvidenceCorrectionCommitted,
    EvidenceCorrectionReceipt,
    EvidenceCorrectionResult,
    EvidenceCorrectionSemanticRequest,
    EvidenceCorrectionService,
    EvidenceCorrectionStore,
    RecordEvidenceObservationCorrectionCommand,
)
from polaris.domain.actors import UnknownActorAttribution
from polaris.domain.decisions import OperationId
from polaris.domain.evidence import (
    EvidenceBindingId,
    EvidenceCorrectionBasis,
    EvidenceCorrectionEffect,
    EvidenceCorrectionId,
    EvidenceObservation,
    EvidenceObservationCorrection,
    EvidenceObservationId,
    EvidenceObservationMaterial,
    EvidenceSourceProvenance,
    EvidenceSubjectReference,
)

OPERATION_ID = OperationId(UUID("00000000-0000-4000-8000-000000000201"))
ROOT_ID = EvidenceObservationId(UUID("00000000-0000-4000-8000-000000000202"))
CORRECTION_ID = UUID("00000000-0000-4000-8000-000000000203")
RECORDED_AT = datetime(2026, 9, 29, 13, 3, tzinfo=UTC)


def _observation(value: str) -> EvidenceObservation:
    return EvidenceObservation(
        observation_id=ROOT_ID,
        source=EvidenceSourceProvenance("fred", "series:cpi", "publisher"),
        subject=EvidenceSubjectReference("US:CPI", "2026-08"),
        observed_at=RECORDED_AT - timedelta(minutes=3),
        acquired_at=RECORDED_AT - timedelta(minutes=2),
        effective_at=RECORDED_AT - timedelta(minutes=3),
        material=EvidenceObservationMaterial(
            retained_representation=f'{{"value": {value}}}'
        ),
    )


class _Store(EvidenceCorrectionStore):
    def __init__(self) -> None:
        self.commits: list[EvidenceCorrectionCommit] = []

    async def get_correction_receipt(
        self,
        operation_id: OperationId,
    ) -> EvidenceCorrectionReceipt | None:
        del operation_id
        return None

    async def commit_correction(self, commit: EvidenceCorrectionCommit):
        self.commits.append(commit)
        return EvidenceCorrectionCommitted(
            EvidenceCorrectionReceipt(
                commit.operation_id,
                commit.request,
                EvidenceCorrectionResult(commit.correction.correction_id),
            )
        )

    async def load_observation_history(self, root_id: EvidenceObservationId):
        del root_id
        return None

    async def load_binding_history(self, root_id: EvidenceBindingId):
        del root_id
        return None


def test_application_allocates_correction_identity_before_store_commit() -> None:
    store = _Store()
    root = _observation("321.1")
    # duplicate-code: this application-boundary proof constructs its command
    # locally so it cannot share a faulty domain-test correction fixture.
    # arid: disable
    command = RecordEvidenceObservationCorrectionCommand(
        operation_id=OPERATION_ID,
        root_id=ROOT_ID,
        target=ROOT_ID,
        effect=EvidenceCorrectionEffect.REVISE,
        attribution=UnknownActorAttribution(),
        basis=EvidenceCorrectionBasis("publisher correction"),
        effective_at=RECORDED_AT - timedelta(minutes=1),
        replacement=replace(
            root,
            material=EvidenceObservationMaterial(
                retained_representation='{"value": 321.2}'
            ),
        ),
    )
    # arid: enable
    service = EvidenceCorrectionService(
        store=store,
        now=lambda: RECORDED_AT,
        new_uuid=lambda: CORRECTION_ID,
    )

    result = asyncio.run(service.record(command))

    assert result == EvidenceCorrectionResult(EvidenceCorrectionId(CORRECTION_ID))
    assert store.commits[0].correction.correction_id == result.correction_id
    assert store.commits[0].correction.recorded_at == RECORDED_AT


def test_commit_rejects_request_that_differs_from_immutable_correction() -> None:
    root = _observation("321.1")
    # Keep this direct commit-contract falsifier independent from domain shape tests.
    # arid: disable
    correction = EvidenceObservationCorrection(
        correction_id=EvidenceCorrectionId(CORRECTION_ID),
        root_id=ROOT_ID,
        target=ROOT_ID,
        effect=EvidenceCorrectionEffect.REVISE,
        attribution=UnknownActorAttribution(),
        basis=EvidenceCorrectionBasis("publisher correction"),
        effective_at=RECORDED_AT - timedelta(minutes=1),
        recorded_at=RECORDED_AT,
        replacement=replace(
            root,
            material=EvidenceObservationMaterial(
                retained_representation='{"value": 321.2}'
            ),
        ),
    )
    # arid: enable
    request = replace(
        EvidenceCorrectionSemanticRequest.from_correction(correction),
        effect=EvidenceCorrectionEffect.RETRACT,
        replacement=None,
    )

    with pytest.raises(ValueError, match="semantic request"):
        EvidenceCorrectionCommit(OPERATION_ID, request, correction, RECORDED_AT)

    exact_request = EvidenceCorrectionSemanticRequest.from_correction(correction)
    with pytest.raises(ValueError, match="recorded_at must match"):
        EvidenceCorrectionCommit(
            OPERATION_ID,
            exact_request,
            correction,
            RECORDED_AT - timedelta(days=1),
        )
