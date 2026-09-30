from __future__ import annotations

from datetime import datetime

from sqlalchemy.engine import RowMapping

from polaris.application.evidence import (
    EvidenceObservationReceipt,
    EvidenceObservationResult,
    EvidenceObservationSemanticRequest,
)
from polaris.domain.decisions import OperationId
from polaris.domain.evidence import (
    EvidenceObservation,
    EvidenceObservationId,
    EvidenceObservationMaterial,
    EvidenceSourceProvenance,
    EvidenceSubjectReference,
)

from .codec_support import canonical_json_fingerprint, uuid_value

type JsonObject = dict[str, object]


def observation_request_payload(
    request: EvidenceObservationSemanticRequest,
) -> JsonObject:
    return {
        "source": {
            "identity": request.source.source_identity,
            "reference": request.source.source_reference,
            "authority": request.source.source_authority,
        },
        "subject": {
            "identity": request.subject.subject_identity,
            "reference": request.subject.subject_reference,
        },
        "observed_at": request.observed_at.isoformat(),
        "acquired_at": request.acquired_at.isoformat(),
        "effective_at": (
            request.effective_at.isoformat()
            if request.effective_at is not None
            else None
        ),
        "material": {
            "retained_representation": request.material.retained_representation,
            "verification_reference": request.material.verification_reference,
        },
        "supersedes_observation_id": (
            str(request.supersedes_observation_id.value)
            if request.supersedes_observation_id is not None
            else None
        ),
    }


def observation_request_fingerprint(
    request: EvidenceObservationSemanticRequest,
) -> str:
    return canonical_json_fingerprint(observation_request_payload(request))


def observation_result_payload(result: EvidenceObservationResult) -> JsonObject:
    return {"observation_id": str(result.observation_id.value)}


def observation_values(observation: EvidenceObservation) -> dict[str, object]:
    return {
        "observation_id": observation.observation_id.value,
        "source_identity": observation.source.source_identity,
        "source_reference": observation.source.source_reference,
        "source_authority": observation.source.source_authority,
        "subject_identity": observation.subject.subject_identity,
        "subject_reference": observation.subject.subject_reference,
        "observed_at": observation.observed_at,
        "acquired_at": observation.acquired_at,
        "effective_at": observation.effective_at,
        "retained_representation": observation.material.retained_representation,
        "verification_reference": observation.material.verification_reference,
        "supersedes_observation_id": (
            observation.supersedes_observation_id.value
            if observation.supersedes_observation_id is not None
            else None
        ),
    }


def observation_from_row(row: RowMapping) -> EvidenceObservation:
    supersedes = row["supersedes_observation_id"]
    return EvidenceObservation(
        observation_id=EvidenceObservationId(
            uuid_value(row["observation_id"], "observation_id")
        ),
        source=EvidenceSourceProvenance(
            source_identity=_string(row["source_identity"], "source_identity"),
            source_reference=_string(row["source_reference"], "source_reference"),
            source_authority=_string(row["source_authority"], "source_authority"),
        ),
        subject=EvidenceSubjectReference(
            subject_identity=_string(row["subject_identity"], "subject_identity"),
            subject_reference=_string(row["subject_reference"], "subject_reference"),
        ),
        observed_at=_datetime(row["observed_at"], "observed_at"),
        acquired_at=_datetime(row["acquired_at"], "acquired_at"),
        effective_at=_optional_datetime(row["effective_at"], "effective_at"),
        material=EvidenceObservationMaterial(
            retained_representation=_optional_string(
                row["retained_representation"], "retained_representation"
            ),
            verification_reference=_optional_string(
                row["verification_reference"], "verification_reference"
            ),
        ),
        supersedes_observation_id=(
            EvidenceObservationId(uuid_value(supersedes, "supersedes_observation_id"))
            if supersedes is not None
            else None
        ),
    )


def observation_receipt_from_row(row: RowMapping) -> EvidenceObservationReceipt:
    request_payload = _object(row["request_payload"], "request_payload")
    result_payload = _object(row["result_payload"], "result_payload")
    return EvidenceObservationReceipt(
        operation_id=OperationId(uuid_value(row["operation_id"], "operation_id")),
        request=_request_from_payload(request_payload),
        result=EvidenceObservationResult(
            EvidenceObservationId(
                uuid_value(
                    result_payload.get("observation_id"), "result observation_id"
                )
            )
        ),
    )


def _request_from_payload(payload: JsonObject) -> EvidenceObservationSemanticRequest:
    source = _object(payload.get("source"), "source")
    subject = _object(payload.get("subject"), "subject")
    material = _object(payload.get("material"), "material")
    supersedes = payload.get("supersedes_observation_id")
    return EvidenceObservationSemanticRequest(
        source=EvidenceSourceProvenance(
            source_identity=_string(source.get("identity"), "source identity"),
            source_reference=_string(source.get("reference"), "source reference"),
            source_authority=_string(source.get("authority"), "source authority"),
        ),
        subject=EvidenceSubjectReference(
            subject_identity=_string(subject.get("identity"), "subject identity"),
            subject_reference=_string(subject.get("reference"), "subject reference"),
        ),
        observed_at=_iso_datetime(payload.get("observed_at"), "observed_at"),
        acquired_at=_iso_datetime(payload.get("acquired_at"), "acquired_at"),
        effective_at=_optional_iso_datetime(
            payload.get("effective_at"), "effective_at"
        ),
        material=EvidenceObservationMaterial(
            retained_representation=_optional_string(
                material.get("retained_representation"), "retained representation"
            ),
            verification_reference=_optional_string(
                material.get("verification_reference"), "verification reference"
            ),
        ),
        supersedes_observation_id=(
            EvidenceObservationId(uuid_value(supersedes, "supersedes observation id"))
            if supersedes is not None
            else None
        ),
    )


def _object(value: object, field: str) -> JsonObject:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise ValueError(f"{field} must be an object")
    return value


def _string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _optional_string(value: object, field: str) -> str | None:
    return None if value is None else _string(value, field)


# duplicate-code: persisted-value decoding owns adapter failure semantics;
# sharing a domain validator here would leak domain validation into infrastructure.
# arid: disable
def _datetime(value: object, field: str) -> datetime:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise ValueError(f"{field} must be timezone-aware datetime")
    return value


# arid: enable


def _optional_datetime(value: object, field: str) -> datetime | None:
    return None if value is None else _datetime(value, field)


def _iso_datetime(value: object, field: str) -> datetime:
    return _datetime(datetime.fromisoformat(_string(value, field)), field)


def _optional_iso_datetime(value: object, field: str) -> datetime | None:
    return None if value is None else _iso_datetime(value, field)
