from __future__ import annotations

from datetime import datetime

from polaris.domain.configuration import (
    EvidenceRequirementApplicabilityKey,
    FreshnessRequirementDefinition,
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

from .requirements import (
    ContestedEvidenceRequirementAuthority,
    EvidenceRequirementVersionResolver,
    InvalidEvidenceRequirementAuthority,
    MissingEvidenceRequirementAuthority,
    ResolvedEvidenceRequirementVersion,
    UnavailableEvidenceRequirementAuthority,
)


async def evaluate_binding_freshness(
    resolver: EvidenceRequirementVersionResolver,
    key: EvidenceRequirementApplicabilityKey,
    basis: EvidenceFreshnessBasisReference,
    *,
    effective_at: datetime,
    known_at: datetime,
) -> EvidenceFreshnessEvaluation:
    resolution = await resolver.resolve(
        key,
        effective_at=effective_at,
        known_at=known_at,
    )
    if isinstance(resolution, ResolvedEvidenceRequirementVersion):
        version = resolution.version
        if (
            version.recorded_at > known_at
            or version.effective_at > effective_at
            or not version.applicability.matches(key)
        ):
            return EvidenceFreshnessInvalidAuthority(
                basis,
                "resolved requirement version contradicts the requested boundary",
            )
        freshness_requirements = tuple(
            definition
            for definition in version.requirements
            if isinstance(definition, FreshnessRequirementDefinition)
        )
        if not freshness_requirements:
            return EvidenceFreshnessNotApplicable(
                EvidenceFreshnessNoRequirementWitness(
                    version.set_id,
                    version.version_id,
                ),
                basis,
            )
        if len(freshness_requirements) != 1:
            return EvidenceFreshnessInvalidAuthority(
                basis,
                "resolved requirement version has multiple freshness definitions",
            )
        requirement = freshness_requirements[0]
        result = (
            EvidenceFreshnessResult.INDETERMINATE
            if basis.as_of_at > effective_at
            else (
                EvidenceFreshnessResult.FRESH
                if effective_at - basis.as_of_at <= requirement.maximum_age
                else EvidenceFreshnessResult.STALE
            )
        )
        return EvidenceFreshnessApplicable(
            EvidenceFreshnessAuthorityReference(
                version.set_id,
                version.version_id,
                requirement.requirement_id,
            ),
            basis,
            result,
        )
    if isinstance(resolution, MissingEvidenceRequirementAuthority):
        return EvidenceFreshnessMissingAuthority(basis)
    if isinstance(resolution, UnavailableEvidenceRequirementAuthority):
        return EvidenceFreshnessUnavailableAuthority(basis, resolution.reason)
    if isinstance(resolution, ContestedEvidenceRequirementAuthority):
        return EvidenceFreshnessContestedAuthority(basis, resolution.version_ids)
    if isinstance(resolution, InvalidEvidenceRequirementAuthority):
        return EvidenceFreshnessInvalidAuthority(basis, resolution.reason)
    raise AssertionError("Evidence requirement resolver returned an unsupported outcome")
