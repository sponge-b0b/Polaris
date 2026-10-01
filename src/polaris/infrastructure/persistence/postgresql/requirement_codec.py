from __future__ import annotations

from datetime import timedelta
from typing import TypedDict
from uuid import UUID

from sqlalchemy.engine import RowMapping

from polaris.domain.configuration import (
    ConfigurationAuthority,
    EvidenceRequirementApplicabilityAssignment,
    EvidenceRequirementApplicabilityKey,
    EvidenceRequirementId,
    EvidenceRequirementPredecessor,
    EvidenceRequirementPredecessorEffect,
    EvidenceRequirementScopeAssignment,
    EvidenceRequirementSetId,
    EvidenceRequirementSetVersion,
    EvidenceRequirementSetVersionId,
    EvidenceRequirementTargetAssignment,
    FreshnessRequirementDefinition,
    InvestmentHorizon,
    SufficiencyRequirementDefinition,
)
from polaris.domain.evidence import (
    ClaimId,
    ClaimSpecificEvidenceScope,
    EvidenceJudgmentFamily,
    EvidenceScopeKind,
    EvidenceSubjectReference,
    EvidenceUse,
    JudgmentWideEvidenceScope,
    evidence_judgment_family,
    evidence_judgment_ref,
    evidence_scope_kind,
)
from polaris.domain.portfolio import FinancialInstrumentId, PortfolioId

from .codec_support import (
    aware_datetime,
    json_object,
    nonempty_string,
    uuid_value,
)

type JsonObject = dict[str, object]


class _ApplicabilityContext(TypedDict):
    subject: EvidenceSubjectReference | None
    portfolio_id: PortfolioId | None
    instrument_id: FinancialInstrumentId | None
    investment_horizon: InvestmentHorizon | None


def requirement_version_values(
    version: EvidenceRequirementSetVersion,
) -> dict[str, object]:
    predecessor = version.predecessor
    return {
        "set_id": version.set_id.value,
        "version_id": version.version_id.value,
        "authority_identity": version.authority.authority_identity,
        "source_reference": version.authority.source_reference,
        "effective_at": version.effective_at,
        "recorded_at": version.recorded_at,
        "applicability": applicability_payload(version.applicability),
        "predecessor_version_id": (
            predecessor.version_id.value if predecessor is not None else None
        ),
        "predecessor_effect": predecessor.effect.value if predecessor else None,
    }


def requirement_definition_values(
    version: EvidenceRequirementSetVersion,
) -> tuple[dict[str, object], ...]:
    rows: list[dict[str, object]] = []
    for position, definition in enumerate(version.requirements):
        if isinstance(definition, FreshnessRequirementDefinition):
            kind = "freshness"
            payload: JsonObject = {
                "maximum_age_microseconds": _timedelta_microseconds(
                    definition.maximum_age
                )
            }
        else:
            kind = "sufficiency"
            payload = {"predicate": definition.predicate}
        rows.append(
            {
                "set_id": version.set_id.value,
                "version_id": version.version_id.value,
                "requirement_id": definition.requirement_id.value,
                "position": position,
                "requirement_kind": kind,
                "definition": payload,
            }
        )
    return tuple(rows)


def requirement_version_from_rows(
    version_row: RowMapping,
    definition_rows: tuple[RowMapping, ...],
) -> EvidenceRequirementSetVersion:
    predecessor_id = version_row["predecessor_version_id"]
    predecessor_effect = version_row["predecessor_effect"]
    return EvidenceRequirementSetVersion(
        set_id=EvidenceRequirementSetId(uuid_value(version_row["set_id"], "set_id")),
        version_id=EvidenceRequirementSetVersionId(
            uuid_value(version_row["version_id"], "version_id")
        ),
        authority=ConfigurationAuthority(
            authority_identity=nonempty_string(
                version_row["authority_identity"], "authority_identity"
            ),
            source_reference=nonempty_string(
                version_row["source_reference"], "source_reference"
            ),
        ),
        effective_at=aware_datetime(version_row["effective_at"], "effective_at"),
        recorded_at=aware_datetime(version_row["recorded_at"], "recorded_at"),
        applicability=applicability_from_payload(
            json_object(version_row["applicability"], "applicability")
        ),
        requirements=tuple(
            _definition_from_row(row)
            for row in sorted(
                definition_rows,
                key=lambda item: _integer(item["position"], "position"),
            )
        ),
        predecessor=(
            EvidenceRequirementPredecessor(
                EvidenceRequirementSetVersionId(
                    uuid_value(predecessor_id, "predecessor_version_id")
                ),
                EvidenceRequirementPredecessorEffect(
                    nonempty_string(predecessor_effect, "predecessor_effect")
                ),
            )
            if predecessor_id is not None
            else None
        ),
    )


def _applicability_context_payload(
    subject: EvidenceSubjectReference | None,
    portfolio_id: PortfolioId | None,
    instrument_id: FinancialInstrumentId | None,
    investment_horizon: InvestmentHorizon | None,
) -> JsonObject:
    return {
        "subject": (
            {
                "identity": subject.subject_identity,
                "reference": subject.subject_reference,
            }
            if subject is not None
            else None
        ),
        "portfolio_id": str(portfolio_id.value) if portfolio_id is not None else None,
        "instrument_id": (
            str(instrument_id.value) if instrument_id is not None else None
        ),
        "investment_horizon": (
            investment_horizon.value if investment_horizon is not None else None
        ),
    }


def applicability_payload(
    applicability: EvidenceRequirementApplicabilityAssignment,
) -> JsonObject:
    return {
        "target_family": applicability.target.family.value,
        "target_id": (
            str(applicability.target.target.value)
            if applicability.target.target is not None
            else None
        ),
        "scope_kind": applicability.scope.kind.value,
        "claim_id": (
            str(applicability.scope.claim_id.value)
            if applicability.scope.claim_id is not None
            else None
        ),
        "evidence_use": applicability.evidence_use.value,
        **_applicability_context_payload(
            applicability.subject,
            applicability.portfolio_id,
            applicability.instrument_id,
            applicability.investment_horizon,
        ),
    }


def applicability_key_payload(
    key: EvidenceRequirementApplicabilityKey,
) -> JsonObject:
    return {
        "target_family": evidence_judgment_family(key.target).value,
        "target_id": str(key.target.value),
        "scope_kind": evidence_scope_kind(key.scope).value,
        "claim_id": (
            str(key.scope.claim_id.value)
            if type(key.scope) is ClaimSpecificEvidenceScope
            else None
        ),
        "evidence_use": key.evidence_use.value,
        **_applicability_context_payload(
            key.subject,
            key.portfolio_id,
            key.instrument_id,
            key.investment_horizon,
        ),
    }


def _applicability_context_from_payload(
    payload: JsonObject,
) -> _ApplicabilityContext:
    subject_payload = payload.get("subject")
    portfolio_id = _optional_uuid(payload.get("portfolio_id"), "portfolio_id")
    instrument_id = _optional_uuid(payload.get("instrument_id"), "instrument_id")
    horizon = payload.get("investment_horizon")
    return {
        "subject": (
            _subject_from_payload(json_object(subject_payload, "subject"))
            if subject_payload is not None
            else None
        ),
        "portfolio_id": (
            PortfolioId(portfolio_id) if portfolio_id is not None else None
        ),
        "instrument_id": (
            FinancialInstrumentId(instrument_id) if instrument_id is not None else None
        ),
        "investment_horizon": (
            InvestmentHorizon(nonempty_string(horizon, "investment_horizon"))
            if horizon is not None
            else None
        ),
    }


def applicability_key_from_payload(
    payload: JsonObject,
) -> EvidenceRequirementApplicabilityKey:
    family = EvidenceJudgmentFamily(
        nonempty_string(payload.get("target_family"), "target_family")
    )
    target_id = uuid_value(payload.get("target_id"), "target_id")
    kind = EvidenceScopeKind(nonempty_string(payload.get("scope_kind"), "scope_kind"))
    claim_id = _optional_uuid(payload.get("claim_id"), "claim_id")
    if kind is EvidenceScopeKind.JUDGMENT_WIDE:
        if claim_id is not None:
            raise ValueError("judgment-wide key must not identify a claim")
        scope = JudgmentWideEvidenceScope()
    else:
        if claim_id is None:
            raise ValueError("claim-specific key must identify a claim")
        scope = ClaimSpecificEvidenceScope(ClaimId(claim_id))
    return EvidenceRequirementApplicabilityKey(
        target=evidence_judgment_ref(family, target_id),
        scope=scope,
        evidence_use=EvidenceUse(
            nonempty_string(payload.get("evidence_use"), "evidence_use")
        ),
        **_applicability_context_from_payload(payload),
    )


def applicability_from_payload(
    payload: JsonObject,
) -> EvidenceRequirementApplicabilityAssignment:
    target_id = _optional_uuid(payload.get("target_id"), "target_id")
    claim_id = _optional_uuid(payload.get("claim_id"), "claim_id")
    family = EvidenceJudgmentFamily(
        nonempty_string(payload.get("target_family"), "target_family")
    )
    return EvidenceRequirementApplicabilityAssignment(
        target=EvidenceRequirementTargetAssignment(
            family,
            evidence_judgment_ref(family, target_id) if target_id is not None else None,
        ),
        scope=EvidenceRequirementScopeAssignment(
            EvidenceScopeKind(nonempty_string(payload.get("scope_kind"), "scope_kind")),
            ClaimId(claim_id) if claim_id is not None else None,
        ),
        evidence_use=EvidenceUse(
            nonempty_string(payload.get("evidence_use"), "evidence_use")
        ),
        **_applicability_context_from_payload(payload),
    )


def _definition_from_row(
    row: RowMapping,
) -> FreshnessRequirementDefinition | SufficiencyRequirementDefinition:
    requirement_id = EvidenceRequirementId(
        uuid_value(row["requirement_id"], "requirement_id")
    )
    kind = nonempty_string(row["requirement_kind"], "requirement_kind")
    payload = json_object(row["definition"], "definition")
    if kind == "freshness":
        microseconds = _integer(
            payload.get("maximum_age_microseconds"), "maximum_age_microseconds"
        )
        return FreshnessRequirementDefinition(
            requirement_id,
            timedelta(microseconds=microseconds),
        )
    if kind == "sufficiency":
        return SufficiencyRequirementDefinition(
            requirement_id,
            nonempty_string(payload.get("predicate"), "predicate"),
        )
    raise ValueError("unsupported requirement kind")


def _subject_from_payload(payload: JsonObject) -> EvidenceSubjectReference:
    return EvidenceSubjectReference(
        nonempty_string(payload.get("identity"), "subject identity"),
        nonempty_string(payload.get("reference"), "subject reference"),
    )


def _timedelta_microseconds(value: timedelta) -> int:
    return value.microseconds + 1_000_000 * value.seconds + 86_400_000_000 * value.days


def _integer(value: object, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{field} must be an integer")
    return value


def _optional_uuid(value: object, field: str) -> UUID | None:
    return None if value is None else uuid_value(value, field)
