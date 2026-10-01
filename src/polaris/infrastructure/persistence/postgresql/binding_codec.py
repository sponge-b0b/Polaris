from __future__ import annotations

from sqlalchemy.engine import RowMapping

from polaris.application.evidence.binding_contracts import (
    EvidenceBindingReceipt,
    EvidenceBindingResult,
    EvidenceBindingSemanticRequest,
)
from polaris.domain.configuration import (
    EvidenceRequirementId,
    EvidenceRequirementSetId,
    EvidenceRequirementSetVersionId,
)
from polaris.domain.decisions import OperationId
from polaris.domain.evidence.bindings import (
    EvidenceAvailability,
    EvidenceBinding,
    EvidenceFreshnessAuthorityReference,
    EvidenceFreshnessBasisReference,
    EvidenceMaterialQualification,
    EvidenceRole,
)
from polaris.domain.evidence.judgments import (
    ClaimId,
    ClaimSpecificEvidenceScope,
    EvidenceJudgmentFamily,
    EvidenceScope,
    EvidenceScopeKind,
    EvidenceUse,
    JudgmentWideEvidenceScope,
    evidence_judgment_family,
    evidence_judgment_ref,
    evidence_scope_kind,
)
from polaris.domain.evidence.observations import (
    EvidenceBindingId,
    EvidenceObservationId,
)

from .codec_support import (
    JsonObject,
    aware_datetime,
    canonical_json_fingerprint,
    iso_aware_datetime,
    json_object,
    nonempty_string,
    optional_nonempty_string,
    uuid_value,
)


def binding_request_payload(request: EvidenceBindingSemanticRequest) -> JsonObject:
    return {
        "observation_id": str(request.observation_id.value),
        "target": {
            "family": evidence_judgment_family(request.target).value,
            "id": str(request.target.value),
        },
        "scope": _scope_payload(request.scope),
        "evidence_use": request.evidence_use.value,
        "role": request.role.value,
        "availability": request.availability.value,
        "materially_used": request.materially_used,
        "effective_at": request.effective_at.isoformat(),
        "material_qualification": (
            request.material_qualification.statement
            if request.material_qualification is not None
            else None
        ),
        "freshness": _freshness_payload(
            request.freshness_authority,
            request.freshness_basis,
        ),
    }


def binding_request_fingerprint(request: EvidenceBindingSemanticRequest) -> str:
    return canonical_json_fingerprint(binding_request_payload(request))


def binding_result_payload(result: EvidenceBindingResult) -> JsonObject:
    return {"binding_id": str(result.binding_id.value)}


def binding_values(binding: EvidenceBinding) -> dict[str, object]:
    authority = binding.freshness_authority
    basis = binding.freshness_basis
    return {
        "binding_id": binding.binding_id.value,
        "observation_id": binding.observation_id.value,
        "target_family": evidence_judgment_family(binding.target).value,
        "target_id": binding.target.value,
        "scope_kind": evidence_scope_kind(binding.scope).value,
        "claim_id": (
            binding.scope.claim_id.value
            if type(binding.scope) is ClaimSpecificEvidenceScope
            else None
        ),
        "evidence_use": binding.evidence_use.value,
        "role": binding.role.value,
        "availability": binding.availability.value,
        "materially_used": binding.materially_used,
        "effective_at": binding.effective_at,
        "recorded_at": binding.recorded_at,
        "material_qualification": (
            binding.material_qualification.statement
            if binding.material_qualification is not None
            else None
        ),
        "freshness_set_id": authority.set_id.value if authority is not None else None,
        "freshness_version_id": (
            authority.version_id.value if authority is not None else None
        ),
        "freshness_requirement_id": (
            authority.requirement_id.value if authority is not None else None
        ),
        "freshness_basis_reference": basis.reference if basis is not None else None,
    }


def binding_from_row(row: RowMapping) -> EvidenceBinding:
    authority = _freshness_authority_from_row(row)
    basis_reference = optional_nonempty_string(
        row["freshness_basis_reference"],
        "freshness_basis_reference",
    )
    return EvidenceBinding(
        binding_id=EvidenceBindingId(uuid_value(row["binding_id"], "binding_id")),
        observation_id=EvidenceObservationId(
            uuid_value(row["observation_id"], "observation_id")
        ),
        target=evidence_judgment_ref(
            EvidenceJudgmentFamily(
                nonempty_string(row["target_family"], "target_family")
            ),
            uuid_value(row["target_id"], "target_id"),
        ),
        scope=_scope_from_values(row["scope_kind"], row["claim_id"]),
        evidence_use=EvidenceUse(nonempty_string(row["evidence_use"], "evidence_use")),
        role=EvidenceRole(nonempty_string(row["role"], "role")),
        availability=EvidenceAvailability(
            nonempty_string(row["availability"], "availability")
        ),
        materially_used=_bool(row["materially_used"], "materially_used"),
        effective_at=aware_datetime(row["effective_at"], "effective_at"),
        recorded_at=aware_datetime(row["recorded_at"], "recorded_at"),
        material_qualification=(
            EvidenceMaterialQualification(
                nonempty_string(row["material_qualification"], "material_qualification")
            )
            if row["material_qualification"] is not None
            else None
        ),
        freshness_authority=authority,
        freshness_basis=(
            EvidenceFreshnessBasisReference(basis_reference)
            if basis_reference is not None
            else None
        ),
    )


def binding_receipt_from_row(row: RowMapping) -> EvidenceBindingReceipt:
    request_payload = json_object(row["request_payload"], "request_payload")
    result_payload = json_object(row["result_payload"], "result_payload")
    return EvidenceBindingReceipt(
        operation_id=OperationId(uuid_value(row["operation_id"], "operation_id")),
        request=_request_from_payload(request_payload),
        result=EvidenceBindingResult(
            EvidenceBindingId(
                uuid_value(result_payload.get("binding_id"), "result binding_id")
            )
        ),
    )


def _request_from_payload(payload: JsonObject) -> EvidenceBindingSemanticRequest:
    target = json_object(payload.get("target"), "target")
    freshness = payload.get("freshness")
    qualification = optional_nonempty_string(
        payload.get("material_qualification"),
        "material_qualification",
    )
    authority, basis = _freshness_from_payload(freshness)
    scope = _scope_from_payload(payload.get("scope"))
    return EvidenceBindingSemanticRequest(
        observation_id=EvidenceObservationId(
            uuid_value(payload.get("observation_id"), "observation_id")
        ),
        target=evidence_judgment_ref(
            EvidenceJudgmentFamily(
                nonempty_string(target.get("family"), "target family")
            ),
            uuid_value(target.get("id"), "target id"),
        ),
        scope=scope,
        evidence_use=EvidenceUse(
            nonempty_string(payload.get("evidence_use"), "evidence_use")
        ),
        role=EvidenceRole(nonempty_string(payload.get("role"), "role")),
        availability=EvidenceAvailability(
            nonempty_string(payload.get("availability"), "availability")
        ),
        materially_used=_bool(payload.get("materially_used"), "materially_used"),
        effective_at=iso_aware_datetime(payload.get("effective_at"), "effective_at"),
        material_qualification=(
            EvidenceMaterialQualification(qualification)
            if qualification is not None
            else None
        ),
        freshness_authority=authority,
        freshness_basis=basis,
    )


def _scope_payload(scope: EvidenceScope) -> JsonObject:
    if type(scope) is JudgmentWideEvidenceScope:
        return {"kind": EvidenceScopeKind.JUDGMENT_WIDE.value, "claim_id": None}
    if type(scope) is ClaimSpecificEvidenceScope:
        return {
            "kind": EvidenceScopeKind.CLAIM_SPECIFIC.value,
            "claim_id": str(scope.claim_id.value),
        }
    raise TypeError("scope must be an EvidenceScope")


def _scope_from_payload(value: object) -> EvidenceScope:
    payload = json_object(value, "scope")
    return _scope_from_values(payload.get("kind"), payload.get("claim_id"))


def _scope_from_values(kind_value: object, claim_value: object) -> EvidenceScope:
    kind = EvidenceScopeKind(nonempty_string(kind_value, "scope kind"))
    if kind is EvidenceScopeKind.JUDGMENT_WIDE:
        if claim_value is not None:
            raise ValueError("judgment-wide binding scope must not carry claim_id")
        return JudgmentWideEvidenceScope()
    return ClaimSpecificEvidenceScope(ClaimId(uuid_value(claim_value, "claim_id")))


def _freshness_payload(
    authority: EvidenceFreshnessAuthorityReference | None,
    basis: EvidenceFreshnessBasisReference | None,
) -> JsonObject | None:
    if authority is None and basis is None:
        return None
    if authority is None or basis is None:
        raise ValueError("freshness authority and basis must be complete")
    return {
        "set_id": str(authority.set_id.value),
        "version_id": str(authority.version_id.value),
        "requirement_id": str(authority.requirement_id.value),
        "basis_reference": basis.reference,
    }


def _freshness_from_payload(
    value: object,
) -> tuple[
    EvidenceFreshnessAuthorityReference | None,
    EvidenceFreshnessBasisReference | None,
]:
    if value is None:
        return None, None
    payload = json_object(value, "freshness")
    return (
        EvidenceFreshnessAuthorityReference(
            set_id=EvidenceRequirementSetId(
                uuid_value(payload.get("set_id"), "freshness set_id")
            ),
            version_id=EvidenceRequirementSetVersionId(
                uuid_value(payload.get("version_id"), "freshness version_id")
            ),
            requirement_id=EvidenceRequirementId(
                uuid_value(payload.get("requirement_id"), "freshness requirement_id")
            ),
        ),
        EvidenceFreshnessBasisReference(
            nonempty_string(payload.get("basis_reference"), "freshness basis_reference")
        ),
    )


def _freshness_authority_from_row(
    row: RowMapping,
) -> EvidenceFreshnessAuthorityReference | None:
    values = (
        row["freshness_set_id"],
        row["freshness_version_id"],
        row["freshness_requirement_id"],
    )
    if all(value is None for value in values):
        return None
    if any(value is None for value in values):
        raise ValueError("persisted freshness authority reference is incomplete")
    return EvidenceFreshnessAuthorityReference(
        set_id=EvidenceRequirementSetId(uuid_value(values[0], "freshness_set_id")),
        version_id=EvidenceRequirementSetVersionId(
            uuid_value(values[1], "freshness_version_id")
        ),
        requirement_id=EvidenceRequirementId(
            uuid_value(values[2], "freshness_requirement_id")
        ),
    )


def _bool(value: object, field: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{field} must be bool")
    return value
