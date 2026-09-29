from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from polaris.application.evidence import (
    EvidenceObservationService,
    EvidenceObservationStore,
    RecordEvidenceObservationCommand,
)
from polaris.domain.decisions import OperationId
from polaris.domain.evidence import (
    EvidenceObservationId,
    EvidenceObservationMaterial,
    EvidenceSourceProvenance,
    EvidenceSubjectReference,
)

OPERATION_ID = UUID("00000000-0000-4000-8000-000000000201")
SECOND_OPERATION_ID = UUID("00000000-0000-4000-8000-000000000202")
OBSERVATION_ID = UUID("00000000-0000-4000-8000-000000000203")
SECOND_OBSERVATION_ID = UUID("00000000-0000-4000-8000-000000000204")
MISSING_OBSERVATION_ID = UUID("00000000-0000-4000-8000-000000000205")
OBSERVED_AT = datetime(2026, 9, 29, 14, 0, tzinfo=UTC)
ACQUIRED_AT = datetime(2026, 9, 29, 14, 1, tzinfo=UTC)
COMMITTED_AT = datetime(2026, 9, 29, 14, 2, tzinfo=UTC)


def evidence_command(
    operation_id: UUID = OPERATION_ID,
    *,
    supersedes: EvidenceObservationId | None = None,
    retained_representation: str = '{"value": 321.1}',
    verification_reference: str | None = "sha256:cpi-2026-08",
) -> RecordEvidenceObservationCommand:
    return RecordEvidenceObservationCommand(
        operation_id=OperationId(operation_id),
        source=EvidenceSourceProvenance(
            "fred",
            "series:CPIAUCSL:2026-08",
            "Federal Reserve Bank of St. Louis / source publisher",
        ),
        subject=EvidenceSubjectReference("US:CPI", "2026-08"),
        observed_at=OBSERVED_AT,
        acquired_at=ACQUIRED_AT,
        effective_at=OBSERVED_AT,
        material=EvidenceObservationMaterial(
            retained_representation=retained_representation,
            verification_reference=verification_reference,
        ),
        supersedes_observation_id=supersedes,
    )


def evidence_service(
    store: EvidenceObservationStore,
    *identities: UUID,
) -> EvidenceObservationService:
    values = iter(identities)
    return EvidenceObservationService(
        store=store,
        now=lambda: COMMITTED_AT,
        new_uuid=lambda: next(values),
    )
