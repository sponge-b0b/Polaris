from __future__ import annotations

from datetime import datetime
from typing import cast

from sqlalchemy.engine import RowMapping

from polaris.application.evidence.corrections import (
    EvidenceCorrectionFamily,
    EvidenceCorrectionReceipt,
    EvidenceCorrectionResult,
    EvidenceCorrectionSemanticRequest,
)
from polaris.domain.decisions import OperationId
from polaris.domain.evidence import (
    EvidenceAssessmentCorrection,
    EvidenceBindingCorrection,
    EvidenceBindingId,
    EvidenceCorrection,
    EvidenceCorrectionBasis,
    EvidenceCorrectionEffect,
    EvidenceCorrectionId,
    EvidenceObservationCorrection,
    EvidenceObservationId,
    EvidenceSufficiencyAssessmentId,
)

from .binding_codec import binding_snapshot_from_payload, binding_snapshot_payload
from .codec import actor_columns, actor_from_columns, actor_request_payload
from .codec_support import (
    JsonObject,
    canonical_json_fingerprint,
    iso_aware_datetime,
    json_object,
    json_safe,
    nonempty_string,
    uuid_value,
)
from .evidence_codec import observation_from_row, observation_values
from .sufficiency_codec import (
    sufficiency_assessment_snapshot_from_payload,
    sufficiency_assessment_snapshot_payload,
)


def correction_values(correction: EvidenceCorrection) -> dict[str, object]:
    target_root_id = (
        correction.target.value
        if type(correction.target)
        in (EvidenceObservationId, EvidenceBindingId, EvidenceSufficiencyAssessmentId)
        else None
    )
    target_correction_id = (
        correction.target.value
        if type(correction.target) is EvidenceCorrectionId
        else None
    )
    return {
        "correction_id": correction.correction_id.value,
        "root_id": correction.root_id.value,
        "target_root_id": target_root_id,
        "target_correction_id": target_correction_id,
        "effect": correction.effect.value,
        "replacement": (
            _replacement_payload(correction)
            if correction.replacement is not None
            else None
        ),
        **actor_columns(correction.attribution),
        "basis_reference": correction.basis.reference,
        "effective_at": correction.effective_at,
        "recorded_at": correction.recorded_at,
    }


def correction_request_payload(
    request: EvidenceCorrectionSemanticRequest,
) -> JsonObject:
    target_kind = (
        "correction" if type(request.target) is EvidenceCorrectionId else "root"
    )
    return {
        "family": request.family.value,
        "root_id": str(request.root_id.value),
        "target": {
            "kind": target_kind,
            "id": str(request.target.value),
        },
        "effect": request.effect.value,
        "attribution": actor_request_payload(request.attribution),
        "basis_reference": request.basis.reference,
        "effective_at": request.effective_at.isoformat(),
        "replacement": (
            _root_payload(request.replacement)
            if request.replacement is not None
            else None
        ),
    }


def correction_request_fingerprint(
    request: EvidenceCorrectionSemanticRequest,
) -> str:
    return canonical_json_fingerprint(correction_request_payload(request))


def correction_result_payload(result: EvidenceCorrectionResult) -> JsonObject:
    return {"correction_id": str(result.correction_id.value)}


def correction_receipt_from_row(row: RowMapping) -> EvidenceCorrectionReceipt:
    payload = json_object(row["request_payload"], "request_payload")
    result = json_object(row["result_payload"], "result_payload")
    return EvidenceCorrectionReceipt(
        OperationId(uuid_value(row["operation_id"], "operation_id")),
        correction_request_from_payload(payload),
        EvidenceCorrectionResult(
            EvidenceCorrectionId(
                uuid_value(result.get("correction_id"), "correction_id")
            )
        ),
    )


def correction_request_from_payload(
    payload: JsonObject,
) -> EvidenceCorrectionSemanticRequest:
    family = EvidenceCorrectionFamily(nonempty_string(payload.get("family"), "family"))
    target_payload = json_object(payload.get("target"), "target")
    root_id = _root_id(family, payload.get("root_id"))
    target = (
        EvidenceCorrectionId(uuid_value(target_payload.get("id"), "target id"))
        if target_payload.get("kind") == "correction"
        else _root_id(family, target_payload.get("id"))
    )
    attribution_payload = json_object(payload.get("attribution"), "attribution")
    replacement_payload = payload.get("replacement")
    return EvidenceCorrectionSemanticRequest(
        family=family,
        root_id=root_id,
        target=target,
        effect=EvidenceCorrectionEffect(
            nonempty_string(payload.get("effect"), "effect")
        ),
        attribution=actor_from_columns(
            {
                "actor_attribution_kind": attribution_payload.get("kind"),
                "actor_id": attribution_payload.get("actor_id"),
                "actor_candidate_ids": attribution_payload.get("candidate_ids"),
            }
        ),
        basis=EvidenceCorrectionBasis(
            nonempty_string(payload.get("basis_reference"), "basis_reference")
        ),
        effective_at=iso_aware_datetime(
            payload.get("effective_at"),
            "effective_at",
        ),
        replacement=(
            _root_from_payload(
                family,
                json_object(replacement_payload, "replacement"),
            )
            if replacement_payload is not None
            else None
        ),
    )


def observation_correction_from_row(row: RowMapping) -> EvidenceObservationCorrection:
    return EvidenceObservationCorrection(
        **_correction_kwargs(EvidenceCorrectionFamily.OBSERVATION, row)
    )


def binding_correction_from_row(row: RowMapping) -> EvidenceBindingCorrection:
    return EvidenceBindingCorrection(
        **_correction_kwargs(EvidenceCorrectionFamily.BINDING, row)
    )


def assessment_correction_from_row(row: RowMapping) -> EvidenceAssessmentCorrection:
    return EvidenceAssessmentCorrection(
        **_correction_kwargs(EvidenceCorrectionFamily.ASSESSMENT, row)
    )


def _correction_kwargs(
    family: EvidenceCorrectionFamily,
    row: RowMapping,
) -> dict[str, object]:
    target_correction_id = row["target_correction_id"]
    replacement = row["replacement"]
    return {
        "correction_id": EvidenceCorrectionId(
            uuid_value(row["correction_id"], "correction_id")
        ),
        "root_id": _root_id(family, row["root_id"]),
        "target": (
            EvidenceCorrectionId(
                uuid_value(target_correction_id, "target_correction_id")
            )
            if target_correction_id is not None
            else _root_id(family, row["target_root_id"])
        ),
        "effect": EvidenceCorrectionEffect(nonempty_string(row["effect"], "effect")),
        "attribution": actor_from_columns(row),
        "basis": EvidenceCorrectionBasis(
            nonempty_string(row["basis_reference"], "basis_reference")
        ),
        "effective_at": _row_datetime(row["effective_at"], "effective_at"),
        "recorded_at": _row_datetime(row["recorded_at"], "recorded_at"),
        "replacement": (
            _root_from_payload(family, json_object(replacement, "replacement"))
            if replacement is not None
            else None
        ),
    }


def _replacement_payload(correction: EvidenceCorrection) -> JsonObject:
    assert correction.replacement is not None
    return _root_payload(correction.replacement)


def _root_payload(value: object) -> JsonObject:
    from polaris.domain.evidence.bindings import EvidenceBinding
    from polaris.domain.evidence.observations import EvidenceObservation
    from polaris.domain.evidence.sufficiency import EvidenceSufficiencyAssessment

    if type(value) is EvidenceObservation:
        return cast(JsonObject, json_safe(observation_values(value)))
    if type(value) is EvidenceBinding:
        return binding_snapshot_payload(value)
    if type(value) is EvidenceSufficiencyAssessment:
        return sufficiency_assessment_snapshot_payload(value)
    raise TypeError("unsupported Evidence correction replacement")


def _root_from_payload(
    family: EvidenceCorrectionFamily,
    payload: JsonObject,
) -> object:
    values = dict(payload)
    if family is EvidenceCorrectionFamily.BINDING:
        return binding_snapshot_from_payload(payload)
    if family is EvidenceCorrectionFamily.ASSESSMENT:
        return sufficiency_assessment_snapshot_from_payload(payload)
    if family is not EvidenceCorrectionFamily.OBSERVATION:
        raise ValueError("unsupported correction family")
    for field in ("observed_at", "acquired_at"):
        values[field] = iso_aware_datetime(values.get(field), field)
    if values.get("effective_at") is not None:
        values["effective_at"] = iso_aware_datetime(
            values.get("effective_at"),
            "effective_at",
        )
    return observation_from_row(cast(RowMapping, values))


def _root_id(
    family: EvidenceCorrectionFamily, value: object
) -> EvidenceObservationId | EvidenceBindingId | EvidenceSufficiencyAssessmentId:
    if family is EvidenceCorrectionFamily.OBSERVATION:
        return EvidenceObservationId(uuid_value(value, "root identity"))
    if family is EvidenceCorrectionFamily.BINDING:
        return EvidenceBindingId(uuid_value(value, "root identity"))
    if family is EvidenceCorrectionFamily.ASSESSMENT:
        return EvidenceSufficiencyAssessmentId(uuid_value(value, "root identity"))
    raise ValueError("unsupported correction family")


def _row_datetime(value: object, field: str) -> datetime:
    if isinstance(value, datetime):
        return value
    return iso_aware_datetime(value, field)


__all__ = [
    "assessment_correction_from_row",
    "binding_correction_from_row",
    "correction_receipt_from_row",
    "correction_request_fingerprint",
    "correction_request_from_payload",
    "correction_request_payload",
    "correction_result_payload",
    "correction_values",
    "observation_correction_from_row",
]
