from __future__ import annotations

from application.decision_evidence._reconstruction_contracts import (
    CanonicalDomainRecordRepository,
    CanonicalDomainSourceRecord,
    MalformedDecisionEvidenceReconstructionIdentifierError,
    MissingDecisionEvidenceSourceError,
    StaleDecisionEvidenceSourceError,
    SubstitutedDecisionEvidenceSourceError,
    TamperedDecisionEvidenceSourceError,
)
from application.decision_evidence._reconstruction_digest import stable_content_digest
from domain.authority import SourceOfTruthCategory
from domain.decision_evidence import ReconstructionReference


async def validate_canonical_domain_record(
    *,
    repository: CanonicalDomainRecordRepository | None,
    reference: ReconstructionReference,
) -> None:
    _validate_canonical_domain_record_reference(reference)
    if repository is None:
        raise MissingDecisionEvidenceSourceError(
            "canonical domain record repository is required to reconstruct "
            f"source record '{reference.record_id}'."
        )

    source_record = await repository.get_canonical_domain_record(reference.record_id)
    if source_record is None:
        raise MissingDecisionEvidenceSourceError(
            f"canonical domain source record '{reference.record_id}' was not found."
        )
    _validate_canonical_domain_record_identity(
        reference=reference,
        source_record=source_record,
    )


def _validate_canonical_domain_record_reference(
    reference: ReconstructionReference,
) -> None:
    if reference.source_of_truth is not SourceOfTruthCategory.CANONICAL_DOMAIN_RECORD:
        raise MalformedDecisionEvidenceReconstructionIdentifierError(
            "canonical domain record reconstruction reference must identify "
            "canonical_domain_record as its source of truth."
        )


def _validate_canonical_domain_record_identity(
    *,
    reference: ReconstructionReference,
    source_record: CanonicalDomainSourceRecord,
) -> None:
    if source_record.record_id != reference.record_id:
        raise SubstitutedDecisionEvidenceSourceError(
            "canonical domain record evidence does not match reconstruction "
            f"identifier '{reference.record_id}'."
        )
    if (
        source_record.source_of_truth
        is not SourceOfTruthCategory.CANONICAL_DOMAIN_RECORD
    ):
        raise SubstitutedDecisionEvidenceSourceError(
            "canonical domain record evidence has non-canonical source of truth "
            f"'{source_record.source_of_truth.value}'."
        )

    _validate_canonical_domain_record_payload_digest(
        reference=reference,
        source_record=source_record,
    )
    digest_verified = _validate_canonical_domain_record_digest(
        reference=reference,
        source_record=source_record,
    )
    snapshot_verified = _validate_canonical_domain_record_snapshot(
        reference=reference,
        source_record=source_record,
    )
    if not digest_verified and not snapshot_verified:
        raise MalformedDecisionEvidenceReconstructionIdentifierError(
            "canonical domain record reconstruction reference must include a "
            "content digest, version, or snapshot identifier."
        )


def _validate_canonical_domain_record_payload_digest(
    *,
    reference: ReconstructionReference,
    source_record: CanonicalDomainSourceRecord,
) -> None:
    if source_record.snapshot_payload is None or source_record.content_digest is None:
        return
    payload_digest = stable_content_digest(source_record.snapshot_payload)
    if payload_digest != source_record.content_digest:
        raise TamperedDecisionEvidenceSourceError(
            "canonical domain source record content digest does not match "
            f"retained source content for '{reference.record_id}'."
        )


def _validate_canonical_domain_record_digest(
    *,
    reference: ReconstructionReference,
    source_record: CanonicalDomainSourceRecord,
) -> bool:
    if reference.content_digest is None:
        return False
    if source_record.content_digest is None:
        raise StaleDecisionEvidenceSourceError(
            "canonical domain source record does not expose the required "
            f"content digest for '{reference.record_id}'."
        )
    if source_record.content_digest != reference.content_digest:
        raise StaleDecisionEvidenceSourceError(
            "canonical domain record evidence content digest is stale for "
            f"'{reference.record_id}'."
        )
    return True


def _validate_canonical_domain_record_snapshot(
    *,
    reference: ReconstructionReference,
    source_record: CanonicalDomainSourceRecord,
) -> bool:
    if reference.snapshot_id is None:
        return False
    valid_source_snapshots = tuple(
        value
        for value in (source_record.snapshot_id, source_record.version)
        if value is not None
    )
    if not valid_source_snapshots:
        raise StaleDecisionEvidenceSourceError(
            "canonical domain source record does not expose the required "
            f"version or snapshot identifier for '{reference.record_id}'."
        )
    if reference.snapshot_id not in valid_source_snapshots:
        raise StaleDecisionEvidenceSourceError(
            "canonical domain record evidence version or snapshot is stale for "
            f"'{reference.record_id}'."
        )
    return True
