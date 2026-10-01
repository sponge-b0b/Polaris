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
    EvidenceMaterialQualification,
    EvidenceRole,
)
from polaris.domain.evidence.freshness import (
    EvidenceFreshnessApplicable,
    EvidenceFreshnessAuthorityReference,
    EvidenceFreshnessBasisReference,
    EvidenceFreshnessContestedAuthority,
    EvidenceFreshnessEvaluation,
    EvidenceFreshnessInvalidAuthority,
    EvidenceFreshnessMissingAuthority,
    EvidenceFreshnessNoRequirementWitness,
    EvidenceFreshnessNotApplicable,
    EvidenceFreshnessResult,
    EvidenceFreshnessUnavailableAuthority,
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
from .requirement_codec import (
    applicability_key_from_payload,
    applicability_key_payload,
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
        "freshness_basis": _basis_payload(request.freshness_basis),
    }


def binding_request_fingerprint(request: EvidenceBindingSemanticRequest) -> str:
    return canonical_json_fingerprint(binding_request_payload(request))


def binding_result_payload(result: EvidenceBindingResult) -> JsonObject:
    return {"binding_id": str(result.binding_id.value)}


def binding_values(binding: EvidenceBinding) -> dict[str, object]:
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
        **_freshness_values(binding.freshness),
    }


def binding_from_row(row: RowMapping) -> EvidenceBinding:
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
        freshness=_freshness_from_row(row),
        material_qualification=(
            EvidenceMaterialQualification(
                nonempty_string(row["material_qualification"], "material_qualification")
            )
            if row["material_qualification"] is not None
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
    qualification = optional_nonempty_string(
        payload.get("material_qualification"),
        "material_qualification",
    )
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
        freshness_basis=_basis_from_payload(
            json_object(payload.get("freshness_basis"), "freshness_basis")
        ),
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


def _basis_payload(basis: EvidenceFreshnessBasisReference) -> JsonObject:
    return {
        "reference": basis.reference,
        "as_of_at": basis.as_of_at.isoformat(),
        "applicability_key": applicability_key_payload(basis.applicability_key),
    }


def _basis_from_payload(payload: JsonObject) -> EvidenceFreshnessBasisReference:
    return EvidenceFreshnessBasisReference(
        nonempty_string(payload.get("reference"), "freshness basis reference"),
        iso_aware_datetime(payload.get("as_of_at"), "freshness basis as_of_at"),
        applicability_key_from_payload(
            json_object(payload.get("applicability_key"), "freshness applicability key")
        ),
    )


def _freshness_values(freshness: EvidenceFreshnessEvaluation) -> dict[str, object]:
    state: str
    set_id = None
    version_id = None
    requirement_id = None
    result = None
    failure_reason = None
    contested_version_ids = None

    if isinstance(freshness, EvidenceFreshnessApplicable):
        state = "applicable"
        set_id = freshness.authority.set_id.value
        version_id = freshness.authority.version_id.value
        requirement_id = freshness.authority.requirement_id.value
        result = freshness.result.value
        basis = freshness.basis
    elif isinstance(freshness, EvidenceFreshnessNotApplicable):
        state = "not_applicable"
        set_id = freshness.witness.set_id.value
        version_id = freshness.witness.version_id.value
        basis = freshness.basis
    elif isinstance(freshness, EvidenceFreshnessMissingAuthority):
        state = "missing_authority"
        result = freshness.result.value
        basis = freshness.basis
    elif isinstance(freshness, EvidenceFreshnessUnavailableAuthority):
        state = "unavailable_authority"
        result = freshness.result.value
        failure_reason = freshness.reason
        basis = freshness.basis
    elif isinstance(freshness, EvidenceFreshnessContestedAuthority):
        state = "contested_authority"
        result = freshness.result.value
        contested_version_ids = sorted(
            (version_id.value for version_id in freshness.version_ids),
            key=str,
        )
        basis = freshness.basis
    elif isinstance(freshness, EvidenceFreshnessInvalidAuthority):
        state = "invalid_authority"
        failure_reason = freshness.reason
        basis = freshness.basis
    else:
        raise TypeError("freshness must be a supported Evidence freshness evaluation")

    return {
        "freshness_state": state,
        "freshness_set_id": set_id,
        "freshness_version_id": version_id,
        "freshness_requirement_id": requirement_id,
        "freshness_basis_reference": basis.reference,
        "freshness_basis_at": basis.as_of_at,
        "freshness_applicability": applicability_key_payload(
            basis.applicability_key
        ),
        "freshness_result": result,
        "freshness_failure_reason": failure_reason,
        "freshness_contested_version_ids": contested_version_ids,
    }


def _freshness_from_row(row: RowMapping) -> EvidenceFreshnessEvaluation:
    state = nonempty_string(row["freshness_state"], "freshness_state")
    basis = EvidenceFreshnessBasisReference(
        nonempty_string(row["freshness_basis_reference"], "freshness_basis_reference"),
        aware_datetime(row["freshness_basis_at"], "freshness_basis_at"),
        applicability_key_from_payload(
            json_object(row["freshness_applicability"], "freshness_applicability")
        ),
    )
    result_value = row["freshness_result"]
    result = (
        EvidenceFreshnessResult(nonempty_string(result_value, "freshness_result"))
        if result_value is not None
        else None
    )
    set_value = row["freshness_set_id"]
    version_value = row["freshness_version_id"]
    requirement_value = row["freshness_requirement_id"]
    reason = optional_nonempty_string(
        row["freshness_failure_reason"],
        "freshness_failure_reason",
    )
    contested = row["freshness_contested_version_ids"]

    if state == "applicable":
        if set_value is None or version_value is None or requirement_value is None:
            raise ValueError("persisted applicable freshness authority is incomplete")
        if result is None:
            raise ValueError("persisted applicable freshness result is missing")
        return EvidenceFreshnessApplicable(
            EvidenceFreshnessAuthorityReference(
                EvidenceRequirementSetId(uuid_value(set_value, "freshness_set_id")),
                EvidenceRequirementSetVersionId(
                    uuid_value(version_value, "freshness_version_id")
                ),
                EvidenceRequirementId(
                    uuid_value(requirement_value, "freshness_requirement_id")
                ),
            ),
            basis,
            result,
        )
    if state == "not_applicable":
        if set_value is None or version_value is None:
            raise ValueError("persisted no-requirement witness is incomplete")
        return EvidenceFreshnessNotApplicable(
            EvidenceFreshnessNoRequirementWitness(
                EvidenceRequirementSetId(uuid_value(set_value, "freshness_set_id")),
                EvidenceRequirementSetVersionId(
                    uuid_value(version_value, "freshness_version_id")
                ),
            ),
            basis,
        )
    if state == "missing_authority":
        return EvidenceFreshnessMissingAuthority(basis)
    if state == "unavailable_authority":
        if reason is None:
            raise ValueError("persisted unavailable authority reason is missing")
        return EvidenceFreshnessUnavailableAuthority(basis, reason)
    if state == "contested_authority":
        if not isinstance(contested, (list, tuple)):
            raise ValueError("persisted contested version IDs are missing")
        return EvidenceFreshnessContestedAuthority(
            basis,
            frozenset(
                EvidenceRequirementSetVersionId(
                    uuid_value(value, "freshness_contested_version_id")
                )
                for value in contested
            ),
        )
    if state == "invalid_authority":
        if reason is None:
            raise ValueError("persisted invalid authority reason is missing")
        return EvidenceFreshnessInvalidAuthority(basis, reason)
    raise ValueError("unsupported persisted freshness state")


def _bool(value: object, field: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{field} must be bool")
    return value
