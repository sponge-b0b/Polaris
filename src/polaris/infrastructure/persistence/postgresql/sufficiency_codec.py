from __future__ import annotations

from datetime import timedelta
from typing import cast

from sqlalchemy.engine import RowMapping

from polaris.application.evidence.sufficiency import (
    EvidenceSufficiencyAssessmentResult,
    EvidenceSufficiencyReceipt,
    EvidenceSufficiencySemanticRequest,
)
from polaris.domain.configuration import (
    EvidenceNoSufficiencyRequirementsWitness,
    EvidenceRequirementId,
    EvidenceRequirementNotApplicableWitness,
    EvidenceRequirementSetId,
    EvidenceRequirementSetVersionId,
    FreshnessRequirementDefinition,
)
from polaris.domain.decisions import OperationId
from polaris.domain.evidence.bindings import EvidenceAvailability, EvidenceRole
from polaris.domain.evidence.freshness import (
    EvidenceFreshnessApplicable,
    EvidenceFreshnessAuthorityReference,
    EvidenceFreshnessBasisReference,
    EvidenceFreshnessNoRequirementWitness,
    EvidenceFreshnessNotApplicable,
    EvidenceFreshnessResult,
)
from polaris.domain.evidence.judgments import (
    ClaimSpecificEvidenceScope,
    evidence_judgment_family,
    evidence_scope_kind,
)
from polaris.domain.evidence.observations import (
    EvidenceBindingId,
    EvidenceCorrectionId,
    EvidenceFactRef,
    EvidenceObservationId,
    EvidenceSufficiencyAssessmentId,
    EvidenceSupportVersion,
)
from polaris.domain.evidence.sufficiency import (
    EvidenceBindingInterpretationState,
    EvidenceBindingUniverseGuard,
    EvidenceCorrectionUniverseGuard,
    EvidenceRequirementAssessment,
    EvidenceRequirementAuthorityGuard,
    EvidenceRequirementBindingProof,
    EvidenceRequirementBindingProofKind,
    EvidenceRequirementDeficiencyReason,
    EvidenceRequirementDisposition,
    EvidenceSufficiencyAssessment,
    EvidenceSufficiencyBasisGuards,
    EvidenceSufficiencyResult,
)
from polaris.domain.evidence.sufficiency_requirements import MinimumEligibleEvidence

from .codec import actor_columns, actor_from_columns
from .codec_support import (
    aware_datetime,
    canonical_json_fingerprint,
    iso_aware_datetime,
    json_object,
    nonempty_string,
    uuid_value,
)
from .requirement_codec import (
    applicability_key_from_payload,
    applicability_key_payload,
)

type JsonObject = dict[str, object]


def sufficiency_assessment_values(
    assessment: EvidenceSufficiencyAssessment,
) -> dict[str, object]:
    key = assessment.applicability_key
    return {
        "assessment_id": assessment.assessment_id.value,
        "target_family": evidence_judgment_family(assessment.target).value,
        "target_id": assessment.target.value,
        "scope_kind": evidence_scope_kind(assessment.scope).value,
        "claim_id": (
            assessment.scope.claim_id.value
            if type(assessment.scope) is ClaimSpecificEvidenceScope
            else None
        ),
        "evidence_use": assessment.evidence_use.value,
        "applicability": applicability_key_payload(key),
        "requirement_set_id": assessment.requirement_set_id.value,
        "requirement_version_id": assessment.requirement_version_id.value,
        "support_version": assessment.support_version.value,
        "binding_guard_ids": sorted(
            (value.value for value in assessment.basis_guards.bindings.binding_ids),
            key=str,
        ),
        "correction_guard_ids": sorted(
            (
                value.value
                for value in assessment.basis_guards.corrections.correction_ids
            ),
            key=str,
        ),
        "requirement_authority_guard_ids": sorted(
            (
                value.value
                for value in assessment.basis_guards.requirement_authority.version_ids
            ),
            key=str,
        ),
        "proof": _assessment_proof_payload(assessment),
        **actor_columns(assessment.attribution),
        "effective_at": assessment.effective_at,
        "known_at": assessment.known_at,
        "recorded_at": assessment.recorded_at,
        "result": assessment.result.value,
        "reassesses_assessment_id": (
            assessment.reassesses_assessment_id.value
            if assessment.reassesses_assessment_id is not None
            else None
        ),
    }


def sufficiency_assessment_from_row(row: RowMapping) -> EvidenceSufficiencyAssessment:
    key = applicability_key_from_payload(
        json_object(row["applicability"], "applicability")
    )
    _validate_endpoint_columns(row, key)
    set_id = EvidenceRequirementSetId(
        uuid_value(row["requirement_set_id"], "requirement_set_id")
    )
    version_id = EvidenceRequirementSetVersionId(
        uuid_value(row["requirement_version_id"], "requirement_version_id")
    )
    proof = json_object(row["proof"], "proof")
    requirements = tuple(
        _requirement_assessment_from_payload(value, set_id, version_id, key)
        for value in _object_list(proof.get("requirements"), "requirements")
    )
    no_requirements = proof.get("no_requirements_witness")
    return EvidenceSufficiencyAssessment(
        assessment_id=EvidenceSufficiencyAssessmentId(
            uuid_value(row["assessment_id"], "assessment_id")
        ),
        # duplicate-code: persistence reconstruction must state the stored key
        # projection independently from application-time assessment construction.
        # arid: disable
        target=key.target,
        scope=key.scope,
        evidence_use=key.evidence_use,
        applicability_key=key,
        # arid: enable
        requirement_set_id=set_id,
        requirement_version_id=version_id,
        support_version=EvidenceSupportVersion(
            _integer(row["support_version"], "support_version")
        ),
        basis_guards=EvidenceSufficiencyBasisGuards(
            EvidenceBindingUniverseGuard(
                frozenset(
                    EvidenceBindingId(uuid_value(value, "binding_guard_id"))
                    for value in _list(row["binding_guard_ids"], "binding_guard_ids")
                )
            ),
            EvidenceCorrectionUniverseGuard(
                frozenset(
                    EvidenceCorrectionId(uuid_value(value, "correction_guard_id"))
                    for value in _list(
                        row["correction_guard_ids"],
                        "correction_guard_ids",
                    )
                )
            ),
            EvidenceRequirementAuthorityGuard(
                frozenset(
                    EvidenceRequirementSetVersionId(
                        uuid_value(value, "requirement_authority_guard_id")
                    )
                    for value in _list(
                        row["requirement_authority_guard_ids"],
                        "requirement_authority_guard_ids",
                    )
                )
            ),
        ),
        requirement_assessments=requirements,
        attribution=actor_from_columns(row),
        effective_at=aware_datetime(row["effective_at"], "effective_at"),
        known_at=aware_datetime(row["known_at"], "known_at"),
        recorded_at=aware_datetime(row["recorded_at"], "recorded_at"),
        result=EvidenceSufficiencyResult(nonempty_string(row["result"], "result")),
        no_requirements_witness=(
            _no_requirements_witness_from_payload(no_requirements, key)
            if no_requirements is not None
            else None
        ),
        reassesses_assessment_id=(
            EvidenceSufficiencyAssessmentId(
                uuid_value(
                    row["reassesses_assessment_id"],
                    "reassesses_assessment_id",
                )
            )
            if row["reassesses_assessment_id"] is not None
            else None
        ),
    )


def sufficiency_request_payload(
    request: EvidenceSufficiencySemanticRequest,
) -> JsonObject:
    actor = actor_columns(request.attribution)
    return {
        "applicability": applicability_key_payload(request.applicability_key),
        "attribution": {
            "kind": actor["actor_attribution_kind"],
            "actor_id": (
                str(actor["actor_id"]) if actor["actor_id"] is not None else None
            ),
            "candidate_ids": (
                [
                    str(value)
                    for value in cast(
                        list[object],
                        actor["actor_candidate_ids"],
                    )
                ]
                if actor["actor_candidate_ids"] is not None
                else None
            ),
        },
        "effective_at": request.effective_at.isoformat(),
        "known_at": request.known_at.isoformat(),
        "reassesses_assessment_id": (
            str(request.reassesses_assessment_id.value)
            if request.reassesses_assessment_id is not None
            else None
        ),
    }


def sufficiency_request_fingerprint(
    request: EvidenceSufficiencySemanticRequest,
) -> str:
    return canonical_json_fingerprint(sufficiency_request_payload(request))


def sufficiency_result_payload(
    result: EvidenceSufficiencyAssessmentResult,
) -> JsonObject:
    return {
        "assessment_id": str(result.assessment_id.value),
        "result": result.result.value,
    }


def sufficiency_receipt_from_row(row: RowMapping) -> EvidenceSufficiencyReceipt:
    request = json_object(row["request_payload"], "request_payload")
    result = json_object(row["result_payload"], "result_payload")
    attribution = json_object(request.get("attribution"), "attribution")
    return EvidenceSufficiencyReceipt(
        operation_id=OperationId(uuid_value(row["operation_id"], "operation_id")),
        request=EvidenceSufficiencySemanticRequest(
            applicability_key=applicability_key_from_payload(
                json_object(request.get("applicability"), "applicability")
            ),
            attribution=actor_from_columns(
                {
                    "actor_attribution_kind": attribution.get("kind"),
                    "actor_id": attribution.get("actor_id"),
                    "actor_candidate_ids": attribution.get("candidate_ids"),
                }
            ),
            effective_at=iso_aware_datetime(
                request.get("effective_at"),
                "effective_at",
            ),
            known_at=iso_aware_datetime(request.get("known_at"), "known_at"),
            reassesses_assessment_id=(
                EvidenceSufficiencyAssessmentId(
                    uuid_value(
                        request.get("reassesses_assessment_id"),
                        "reassesses_assessment_id",
                    )
                )
                if request.get("reassesses_assessment_id") is not None
                else None
            ),
        ),
        result=EvidenceSufficiencyAssessmentResult(
            EvidenceSufficiencyAssessmentId(
                uuid_value(result.get("assessment_id"), "assessment_id")
            ),
            EvidenceSufficiencyResult(nonempty_string(result.get("result"), "result")),
        ),
    )


def _assessment_proof_payload(
    assessment: EvidenceSufficiencyAssessment,
) -> JsonObject:
    return {
        "requirements": [
            _requirement_assessment_payload(value)
            for value in assessment.requirement_assessments
        ],
        "no_requirements_witness": (
            _no_requirements_witness_payload(assessment.no_requirements_witness)
            if assessment.no_requirements_witness is not None
            else None
        ),
    }


def _requirement_assessment_payload(
    assessment: EvidenceRequirementAssessment,
) -> JsonObject:
    return {
        "requirement_id": str(assessment.requirement_id.value),
        "predicate": {
            "minimum_distinct_observations": (
                assessment.predicate.minimum_distinct_observations
            ),
            "qualifying_roles": sorted(
                role.value for role in assessment.predicate.qualifying_roles
            ),
        },
        "disposition": assessment.disposition.value,
        "counted_observation_ids": sorted(
            str(value.value) for value in assessment.counted_observation_ids
        ),
        "binding_proofs": [
            _binding_proof_payload(value) for value in assessment.binding_proofs
        ],
        "not_applicable_witness": (
            _not_applicable_witness_payload(assessment.not_applicable_witness)
            if assessment.not_applicable_witness is not None
            else None
        ),
    }


def _requirement_assessment_from_payload(
    value: object,
    set_id: EvidenceRequirementSetId,
    version_id: EvidenceRequirementSetVersionId,
    key: object,
) -> EvidenceRequirementAssessment:
    payload = json_object(value, "requirement assessment")
    typed_key = applicability_key_from_payload(applicability_key_payload(key))
    predicate = json_object(payload.get("predicate"), "predicate")
    requirement_id = EvidenceRequirementId(
        uuid_value(payload.get("requirement_id"), "requirement_id")
    )
    witness = payload.get("not_applicable_witness")
    return EvidenceRequirementAssessment(
        requirement_id=requirement_id,
        predicate=MinimumEligibleEvidence(
            _integer(
                predicate.get("minimum_distinct_observations"),
                "minimum_distinct_observations",
            ),
            frozenset(
                EvidenceRole(nonempty_string(role, "qualifying_role"))
                for role in _list(
                    predicate.get("qualifying_roles"),
                    "qualifying_roles",
                )
            ),
        ),
        disposition=EvidenceRequirementDisposition(
            nonempty_string(payload.get("disposition"), "disposition")
        ),
        counted_observation_ids=frozenset(
            EvidenceObservationId(uuid_value(item, "counted_observation_id"))
            for item in _list(
                payload.get("counted_observation_ids"),
                "counted_observation_ids",
            )
        ),
        binding_proofs=tuple(
            _binding_proof_from_payload(item)
            for item in _object_list(
                payload.get("binding_proofs"),
                "binding_proofs",
            )
        ),
        not_applicable_witness=(
            _not_applicable_witness_from_payload(
                witness,
                set_id,
                version_id,
                requirement_id,
                typed_key,
            )
            if witness is not None
            else None
        ),
    )


def _binding_proof_payload(proof: EvidenceRequirementBindingProof) -> JsonObject:
    return {
        "binding_id": str(proof.binding_id.value),
        "observation_id": str(proof.observation_id.value),
        "kind": proof.kind.value,
        "interpretation_state": proof.interpretation_state.value,
        "fact_support": [_fact_ref_payload(value) for value in proof.fact_support],
        "role": proof.role.value,
        "availability": proof.availability.value,
        "materially_used": proof.materially_used,
        "freshness": _freshness_payload(proof),
        "deficiency_reason": (
            proof.deficiency_reason.value
            if proof.deficiency_reason is not None
            else None
        ),
    }


def _binding_proof_from_payload(value: object) -> EvidenceRequirementBindingProof:
    payload = json_object(value, "binding proof")
    freshness, authority = _freshness_from_payload(
        json_object(payload.get("freshness"), "freshness")
    )
    reason = payload.get("deficiency_reason")
    return EvidenceRequirementBindingProof(
        binding_id=EvidenceBindingId(
            uuid_value(payload.get("binding_id"), "binding_id")
        ),
        observation_id=EvidenceObservationId(
            uuid_value(payload.get("observation_id"), "observation_id")
        ),
        kind=EvidenceRequirementBindingProofKind(
            nonempty_string(payload.get("kind"), "kind")
        ),
        interpretation_state=EvidenceBindingInterpretationState(
            nonempty_string(
                payload.get("interpretation_state"),
                "interpretation_state",
            )
        ),
        fact_support=frozenset(
            _fact_ref_from_payload(item)
            for item in _object_list(payload.get("fact_support"), "fact_support")
        ),
        role=EvidenceRole(nonempty_string(payload.get("role"), "role")),
        availability=EvidenceAvailability(
            nonempty_string(payload.get("availability"), "availability")
        ),
        materially_used=_boolean(payload.get("materially_used"), "materially_used"),
        freshness=freshness,
        freshness_authority=authority,
        deficiency_reason=(
            EvidenceRequirementDeficiencyReason(nonempty_string(reason, "reason"))
            if reason is not None
            else None
        ),
    )


def _freshness_payload(proof: EvidenceRequirementBindingProof) -> JsonObject:
    freshness = proof.freshness
    basis = {
        "reference": freshness.basis.reference,
        "as_of_at": freshness.basis.as_of_at.isoformat(),
        "applicability": applicability_key_payload(freshness.basis.applicability_key),
    }
    if isinstance(freshness, EvidenceFreshnessApplicable):
        authority = cast(FreshnessRequirementDefinition, proof.freshness_authority)
        return {
            "state": "applicable",
            "set_id": str(freshness.authority.set_id.value),
            "version_id": str(freshness.authority.version_id.value),
            "requirement_id": str(freshness.authority.requirement_id.value),
            "maximum_age_microseconds": (
                authority.maximum_age // timedelta(microseconds=1)
            ),
            "basis": basis,
            "result": freshness.result.value,
        }
    witness = cast(EvidenceFreshnessNoRequirementWitness, proof.freshness_authority)
    return {
        "state": "not_applicable",
        "set_id": str(witness.set_id.value),
        "version_id": str(witness.version_id.value),
        "basis": basis,
        "result": None,
    }


def _freshness_from_payload(
    payload: JsonObject,
) -> tuple[
    EvidenceFreshnessApplicable | EvidenceFreshnessNotApplicable,
    FreshnessRequirementDefinition | EvidenceFreshnessNoRequirementWitness,
]:
    set_id = EvidenceRequirementSetId(uuid_value(payload.get("set_id"), "set_id"))
    version_id = EvidenceRequirementSetVersionId(
        uuid_value(payload.get("version_id"), "version_id")
    )
    basis_payload = json_object(payload.get("basis"), "basis")
    basis = EvidenceFreshnessBasisReference(
        nonempty_string(basis_payload.get("reference"), "reference"),
        iso_aware_datetime(basis_payload.get("as_of_at"), "as_of_at"),
        applicability_key_from_payload(
            json_object(basis_payload.get("applicability"), "applicability")
        ),
    )
    state = nonempty_string(payload.get("state"), "state")
    if state == "not_applicable":
        witness = EvidenceFreshnessNoRequirementWitness(set_id, version_id)
        return EvidenceFreshnessNotApplicable(witness, basis), witness
    if state != "applicable":
        raise ValueError("unsupported assessment-time freshness state")
    requirement_id = EvidenceRequirementId(
        uuid_value(payload.get("requirement_id"), "requirement_id")
    )
    definition = FreshnessRequirementDefinition(
        requirement_id,
        timedelta(
            microseconds=_integer(
                payload.get("maximum_age_microseconds"),
                "maximum_age_microseconds",
            )
        ),
    )
    return (
        EvidenceFreshnessApplicable(
            EvidenceFreshnessAuthorityReference(
                set_id,
                version_id,
                requirement_id,
            ),
            basis,
            EvidenceFreshnessResult(nonempty_string(payload.get("result"), "result")),
        ),
        definition,
    )


def _fact_ref_payload(value: EvidenceFactRef) -> JsonObject:
    if type(value) is EvidenceObservationId:
        kind = "observation"
    elif type(value) is EvidenceBindingId:
        kind = "binding"
    elif type(value) is EvidenceCorrectionId:
        kind = "correction"
    else:
        kind = "sufficiency_assessment"
    return {"kind": kind, "id": str(value.value)}


def _fact_ref_from_payload(value: object) -> EvidenceFactRef:
    payload = json_object(value, "fact reference")
    identity = uuid_value(payload.get("id"), "fact reference id")
    kind = nonempty_string(payload.get("kind"), "fact reference kind")
    constructors = {
        "observation": EvidenceObservationId,
        "binding": EvidenceBindingId,
        "correction": EvidenceCorrectionId,
        "sufficiency_assessment": EvidenceSufficiencyAssessmentId,
    }
    try:
        return constructors[kind](identity)
    except KeyError as error:
        raise ValueError("unsupported Evidence fact-reference kind") from error


def _not_applicable_witness_payload(
    witness: EvidenceRequirementNotApplicableWitness,
) -> JsonObject:
    return {
        "set_id": str(witness.set_id.value),
        "version_id": str(witness.version_id.value),
        "requirement_id": str(witness.requirement_id.value),
        "applicability": applicability_key_payload(witness.applicability_key),
    }


def _not_applicable_witness_from_payload(
    value: object,
    set_id: EvidenceRequirementSetId,
    version_id: EvidenceRequirementSetVersionId,
    requirement_id: EvidenceRequirementId,
    key: object,
) -> EvidenceRequirementNotApplicableWitness:
    payload = json_object(value, "not_applicable_witness")
    witness = EvidenceRequirementNotApplicableWitness(
        EvidenceRequirementSetId(uuid_value(payload.get("set_id"), "set_id")),
        EvidenceRequirementSetVersionId(
            uuid_value(payload.get("version_id"), "version_id")
        ),
        EvidenceRequirementId(
            uuid_value(payload.get("requirement_id"), "requirement_id")
        ),
        applicability_key_from_payload(
            json_object(payload.get("applicability"), "applicability")
        ),
    )
    if (
        witness.set_id != set_id
        or witness.version_id != version_id
        or witness.requirement_id != requirement_id
        or witness.applicability_key != key
    ):
        raise ValueError("negative requirement witness does not match its root")
    return witness


def _no_requirements_witness_payload(
    witness: EvidenceNoSufficiencyRequirementsWitness,
) -> JsonObject:
    return {
        "set_id": str(witness.set_id.value),
        "version_id": str(witness.version_id.value),
        "applicability": applicability_key_payload(witness.applicability_key),
    }


def _no_requirements_witness_from_payload(
    value: object,
    key: object,
) -> EvidenceNoSufficiencyRequirementsWitness:
    payload = json_object(value, "no_requirements_witness")
    witness = EvidenceNoSufficiencyRequirementsWitness(
        EvidenceRequirementSetId(uuid_value(payload.get("set_id"), "set_id")),
        EvidenceRequirementSetVersionId(
            uuid_value(payload.get("version_id"), "version_id")
        ),
        applicability_key_from_payload(
            json_object(payload.get("applicability"), "applicability")
        ),
    )
    if witness.applicability_key != key:
        raise ValueError("zero-requirement witness applicability does not match")
    return witness


def _validate_endpoint_columns(row: RowMapping, key: object) -> None:
    typed_key = applicability_key_from_payload(applicability_key_payload(key))
    claim_id = (
        typed_key.scope.claim_id.value
        if type(typed_key.scope) is ClaimSpecificEvidenceScope
        else None
    )
    if (
        nonempty_string(row["target_family"], "target_family")
        != evidence_judgment_family(typed_key.target).value
        or uuid_value(row["target_id"], "target_id") != typed_key.target.value
        or nonempty_string(row["scope_kind"], "scope_kind")
        != evidence_scope_kind(typed_key.scope).value
        or row["claim_id"] != claim_id
        or nonempty_string(row["evidence_use"], "evidence_use")
        != typed_key.evidence_use.value
    ):
        raise ValueError("stored sufficiency endpoint contradicts applicability")


def _object_list(value: object, field: str) -> list[JsonObject]:
    return [json_object(item, field) for item in _list(value, field)]


def _list(value: object, field: str) -> list[object]:
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{field} must be a list")
    return list(value)


def _integer(value: object, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{field} must be an integer")
    return value


def _boolean(value: object, field: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{field} must be a boolean")
    return value


__all__ = [
    "sufficiency_assessment_from_row",
    "sufficiency_assessment_values",
    "sufficiency_receipt_from_row",
    "sufficiency_request_fingerprint",
    "sufficiency_request_payload",
    "sufficiency_result_payload",
]
