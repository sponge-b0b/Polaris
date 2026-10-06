from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from polaris.domain.actors import (
    ActorAttribution,
    is_actor_attribution,
)
from polaris.domain.configuration import (
    EvidenceNoSufficiencyRequirementsWitness,
    EvidenceRequirementApplicabilityKey,
    EvidenceRequirementId,
    EvidenceRequirementNotApplicableWitness,
    EvidenceRequirementSetId,
    EvidenceRequirementSetVersion,
    EvidenceRequirementSetVersionId,
    FreshnessRequirementDefinition,
    SufficiencyRequirementApplicabilityState,
    SufficiencyRequirementDefinition,
)

from .bindings import EvidenceAvailability, EvidenceBinding
from .freshness import (
    EvidenceFreshnessApplicable,
    EvidenceFreshnessNoRequirementWitness,
    EvidenceFreshnessNotApplicable,
    EvidenceFreshnessResult,
    evaluate_evidence_freshness,
)
from .judgments import (
    ClaimSpecificEvidenceScope,
    EvidenceJudgmentRef,
    EvidenceScope,
    EvidenceUse,
    JudgmentWideEvidenceScope,
    is_evidence_judgment_ref,
)
from .observations import (
    EvidenceBindingId,
    EvidenceCorrectionId,
    EvidenceFactRef,
    EvidenceObservationId,
    EvidenceSubjectReference,
    EvidenceSufficiencyAssessmentId,
    EvidenceSupportVersion,
    is_evidence_fact_ref,
)
from .sufficiency_requirements import MinimumEligibleEvidence

if TYPE_CHECKING:
    from collections.abc import Iterable


class InvalidEvidenceSufficiency(ValueError):
    pass


class EvidenceSufficiencyResult(StrEnum):
    SUFFICIENT = "sufficient"
    INSUFFICIENT = "insufficient"
    INDETERMINATE = "indeterminate"


class EvidenceRequirementDisposition(StrEnum):
    SATISFIED = "satisfied"
    MISSING = "missing"
    UNAVAILABLE = "unavailable"
    STALE = "stale"
    UNKNOWN = "unknown"
    DISPUTED = "disputed"
    CONTESTED = "contested"
    NOT_APPLICABLE = "not_applicable"


class EvidenceBindingInterpretationState(StrEnum):
    DETERMINATE = "determinate"
    WITHDRAWN = "withdrawn"
    DISPUTED = "disputed"
    CONTESTED = "contested"


class EvidenceRequirementBindingProofKind(StrEnum):
    CONTRIBUTOR = "contributor"
    DEFICIENCY = "deficiency"
    VISIBLE = "visible"


class EvidenceRequirementDeficiencyReason(StrEnum):
    UNAVAILABLE = "unavailable"
    UNKNOWN_AVAILABILITY = "unknown_availability"
    STALE = "stale"
    INDETERMINATE_FRESHNESS = "indeterminate_freshness"
    DISPUTED = "disputed"
    CONTESTED = "contested"


type EvidenceAssessmentFreshness = (
    EvidenceFreshnessApplicable | EvidenceFreshnessNotApplicable
)

type EvidenceAssessmentFreshnessAuthority = (
    FreshnessRequirementDefinition | EvidenceFreshnessNoRequirementWitness
)


@dataclass(frozen=True, slots=True)
class EvidenceBindingInterpretation:
    """One complete interpreted binding assertion at an exact `(T,K)` boundary."""

    binding: EvidenceBinding
    subject: EvidenceSubjectReference
    state: EvidenceBindingInterpretationState
    fact_support: frozenset[EvidenceFactRef]
    surviving_subjects: frozenset[EvidenceSubjectReference] | None = None
    surviving_bindings: frozenset[EvidenceBinding] | None = None

    def __post_init__(self) -> None:
        if type(self.binding) is not EvidenceBinding:
            raise TypeError("binding must be EvidenceBinding")
        if type(self.subject) is not EvidenceSubjectReference:
            raise TypeError("subject must be EvidenceSubjectReference")
        if type(self.state) is not EvidenceBindingInterpretationState:
            raise TypeError("state must be EvidenceBindingInterpretationState")
        _require_fact_support(self.fact_support)
        if self.binding.binding_id not in self.fact_support:
            raise InvalidEvidenceSufficiency(
                "binding interpretation support must contain its binding root"
            )
        if self.binding.observation_id not in self.fact_support:
            raise InvalidEvidenceSufficiency(
                "binding interpretation support must contain its observation root"
            )
        subjects = (
            frozenset({self.subject})
            if self.surviving_subjects is None
            else self.surviving_subjects
        )
        _validate_surviving_subjects(self.subject, subjects, self.state)
        object.__setattr__(self, "surviving_subjects", subjects)
        bindings = (
            frozenset({self.binding})
            if self.surviving_bindings is None
            else self.surviving_bindings
        )
        _validate_surviving_bindings(self.binding, bindings, self.state)
        object.__setattr__(self, "surviving_bindings", bindings)


def _validate_surviving_bindings(
    root: EvidenceBinding,
    values: object,
    state: EvidenceBindingInterpretationState,
) -> None:
    if type(values) is not frozenset or any(
        type(value) is not EvidenceBinding for value in values
    ):
        raise TypeError("surviving_bindings must be frozenset[EvidenceBinding]")
    if not values and state is not EvidenceBindingInterpretationState.WITHDRAWN:
        raise InvalidEvidenceSufficiency(
            "a non-withdrawn binding interpretation requires a surviving assertion"
        )
    for value in values:
        if (
            value.binding_id != root.binding_id
            or value.observation_id != root.observation_id
            or value.target != root.target
            or value.scope != root.scope
            or value.evidence_use is not root.evidence_use
        ):
            raise InvalidEvidenceSufficiency(
                "surviving binding assertions must retain fixed root endpoints"
            )


def _validate_surviving_subjects(
    root: EvidenceSubjectReference,
    values: object,
    state: EvidenceBindingInterpretationState,
) -> None:
    if type(values) is not frozenset or any(
        type(value) is not EvidenceSubjectReference for value in values
    ):
        raise TypeError(
            "surviving_subjects must be frozenset[EvidenceSubjectReference]"
        )
    if not values and state is not EvidenceBindingInterpretationState.WITHDRAWN:
        raise InvalidEvidenceSufficiency(
            "a non-withdrawn binding interpretation requires a surviving subject"
        )


@dataclass(frozen=True, slots=True)
class EvidenceRequirementBindingAssertionProof:
    binding: EvidenceBinding
    freshness: EvidenceAssessmentFreshness
    freshness_authority: EvidenceAssessmentFreshnessAuthority
    kind: EvidenceRequirementBindingProofKind
    deficiency_reason: EvidenceRequirementDeficiencyReason | None = None

    def __post_init__(self) -> None:
        if type(self.binding) is not EvidenceBinding:
            raise TypeError("binding must be EvidenceBinding")
        if type(self.freshness) not in (
            EvidenceFreshnessApplicable,
            EvidenceFreshnessNotApplicable,
        ):
            raise TypeError("freshness must be a successful assessment-time result")
        if type(self.freshness_authority) not in (
            FreshnessRequirementDefinition,
            EvidenceFreshnessNoRequirementWitness,
        ):
            raise TypeError("freshness_authority has an unsupported type")
        if type(self.kind) is not EvidenceRequirementBindingProofKind:
            raise TypeError("kind must be EvidenceRequirementBindingProofKind")
        if self.freshness.basis != self.binding.freshness.basis:
            raise InvalidEvidenceSufficiency(
                "assertion freshness must use its exact binding basis"
            )
        _validate_proof_freshness_authority(self)
        _validate_binding_proof_reason(self)


@dataclass(frozen=True, slots=True)
class EvidenceRequirementBindingProof:
    binding_id: EvidenceBindingId
    observation_id: EvidenceObservationId
    kind: EvidenceRequirementBindingProofKind
    interpretation_state: EvidenceBindingInterpretationState
    fact_support: frozenset[EvidenceFactRef]
    assertion_proofs: tuple[EvidenceRequirementBindingAssertionProof, ...]
    deficiency_reason: EvidenceRequirementDeficiencyReason | None = None

    def __post_init__(self) -> None:
        _validate_binding_proof_identity(self)
        _validate_binding_proof_semantics(self)


def _validate_binding_proof_identity(proof: EvidenceRequirementBindingProof) -> None:
    if type(proof.binding_id) is not EvidenceBindingId:
        raise TypeError("binding_id must be EvidenceBindingId")
    if type(proof.observation_id) is not EvidenceObservationId:
        raise TypeError("observation_id must be EvidenceObservationId")
    if type(proof.kind) is not EvidenceRequirementBindingProofKind:
        raise TypeError("kind must be EvidenceRequirementBindingProofKind")
    if type(proof.interpretation_state) is not EvidenceBindingInterpretationState:
        raise TypeError(
            "interpretation_state must be EvidenceBindingInterpretationState"
        )
    _require_fact_support(proof.fact_support)
    if proof.binding_id not in proof.fact_support:
        raise InvalidEvidenceSufficiency(
            "binding proof support must contain its binding root"
        )
    if proof.observation_id not in proof.fact_support:
        raise InvalidEvidenceSufficiency(
            "binding proof support must contain its observation root"
        )


def _validate_binding_proof_semantics(proof: EvidenceRequirementBindingProof) -> None:
    if not isinstance(proof.assertion_proofs, tuple) or any(
        type(value) is not EvidenceRequirementBindingAssertionProof
        for value in proof.assertion_proofs
    ):
        raise TypeError("assertion_proofs must contain typed assertion proofs")
    if not proof.assertion_proofs and (
        proof.interpretation_state is not EvidenceBindingInterpretationState.WITHDRAWN
    ):
        raise InvalidEvidenceSufficiency(
            "a non-withdrawn binding proof requires surviving assertions"
        )
    if (
        proof.interpretation_state is EvidenceBindingInterpretationState.DETERMINATE
        and len(proof.assertion_proofs) != 1
    ):
        raise InvalidEvidenceSufficiency(
            "a determinate binding proof requires one surviving assertion"
        )
    first_binding = (
        proof.assertion_proofs[0].binding if proof.assertion_proofs else None
    )
    for assertion in proof.assertion_proofs:
        if (
            assertion.binding.binding_id != proof.binding_id
            or assertion.binding.observation_id != proof.observation_id
            or (
                first_binding is not None
                and (
                    assertion.binding.target != first_binding.target
                    or assertion.binding.scope != first_binding.scope
                    or assertion.binding.evidence_use is not first_binding.evidence_use
                )
            )
        ):
            raise InvalidEvidenceSufficiency(
                "assertion proof must retain its binding's fixed endpoints"
            )
    expected_kind = (
        EvidenceRequirementBindingProofKind.CONTRIBUTOR
        if any(
            value.kind is EvidenceRequirementBindingProofKind.CONTRIBUTOR
            for value in proof.assertion_proofs
        )
        else EvidenceRequirementBindingProofKind.DEFICIENCY
        if any(
            value.kind is EvidenceRequirementBindingProofKind.DEFICIENCY
            for value in proof.assertion_proofs
        )
        else EvidenceRequirementBindingProofKind.VISIBLE
    )
    if proof.kind is not expected_kind:
        raise InvalidEvidenceSufficiency(
            "binding proof kind must summarize its branches"
        )
    if (
        proof.interpretation_state is not EvidenceBindingInterpretationState.DETERMINATE
        and proof.kind is EvidenceRequirementBindingProofKind.CONTRIBUTOR
    ):
        raise InvalidEvidenceSufficiency(
            "an unresolved binding cannot contribute to sufficiency"
        )
    reasons = {
        value.deficiency_reason
        for value in proof.assertion_proofs
        if value.kind is EvidenceRequirementBindingProofKind.DEFICIENCY
    }
    if len(reasons) > 1 or proof.deficiency_reason != next(iter(reasons), None):
        raise InvalidEvidenceSufficiency(
            "binding proof reason must summarize every deficient branch"
        )
    _validate_binding_proof_reason(proof)


def _validate_proof_freshness_authority(
    proof: EvidenceRequirementBindingAssertionProof,
) -> None:
    freshness = proof.freshness
    authority = proof.freshness_authority
    if isinstance(freshness, EvidenceFreshnessApplicable):
        if not isinstance(authority, FreshnessRequirementDefinition):
            raise InvalidEvidenceSufficiency(
                "applicable freshness requires its exact definition"
            )
        if freshness.authority.requirement_id != authority.requirement_id:
            raise InvalidEvidenceSufficiency(
                "freshness definition must match its authority reference"
            )
        return
    if (
        not isinstance(authority, EvidenceFreshnessNoRequirementWitness)
        or freshness.witness != authority
    ):
        raise InvalidEvidenceSufficiency(
            "no-freshness proof requires its exact same-version witness"
        )


def _validate_binding_proof_reason(
    proof: EvidenceRequirementBindingProof | EvidenceRequirementBindingAssertionProof,
) -> None:
    if proof.kind is EvidenceRequirementBindingProofKind.DEFICIENCY:
        if type(proof.deficiency_reason) is not EvidenceRequirementDeficiencyReason:
            raise InvalidEvidenceSufficiency(
                "a deficiency proof requires a typed deficiency reason"
            )
    elif proof.deficiency_reason is not None:
        raise InvalidEvidenceSufficiency(
            "only a deficiency proof may carry a deficiency reason"
        )


@dataclass(frozen=True, slots=True)
class EvidenceRequirementAssessment:
    requirement_id: EvidenceRequirementId
    predicate: MinimumEligibleEvidence
    disposition: EvidenceRequirementDisposition
    counted_observation_ids: frozenset[EvidenceObservationId]
    binding_proofs: tuple[EvidenceRequirementBindingProof, ...]
    not_applicable_witness: EvidenceRequirementNotApplicableWitness | None = None

    def __post_init__(self) -> None:
        _validate_requirement_assessment_shape(self)
        _validate_requirement_assessment_entailment(self)


def _validate_requirement_assessment_shape(
    assessment: EvidenceRequirementAssessment,
) -> None:
    if type(assessment.requirement_id) is not EvidenceRequirementId:
        raise TypeError("requirement_id must be EvidenceRequirementId")
    if type(assessment.predicate) is not MinimumEligibleEvidence:
        raise TypeError("predicate must be MinimumEligibleEvidence")
    if type(assessment.disposition) is not EvidenceRequirementDisposition:
        raise TypeError("disposition must be EvidenceRequirementDisposition")
    _require_observation_ids(assessment.counted_observation_ids)
    if not isinstance(assessment.binding_proofs, tuple) or any(
        type(proof) is not EvidenceRequirementBindingProof
        for proof in assessment.binding_proofs
    ):
        raise TypeError(
            "binding_proofs must be tuple[EvidenceRequirementBindingProof, ...]"
        )
    proof_ids = [proof.binding_id for proof in assessment.binding_proofs]
    if len(proof_ids) != len(set(proof_ids)):
        raise InvalidEvidenceSufficiency(
            "one requirement cannot repeat a binding proof"
        )


def _validate_requirement_assessment_entailment(
    assessment: EvidenceRequirementAssessment,
) -> None:
    contributor_observations = frozenset(
        proof.observation_id
        for proof in assessment.binding_proofs
        if proof.kind is EvidenceRequirementBindingProofKind.CONTRIBUTOR
    )
    if contributor_observations != assessment.counted_observation_ids:
        raise InvalidEvidenceSufficiency(
            "counted observations must exactly match distinct contributors"
        )
    if assessment.disposition is EvidenceRequirementDisposition.NOT_APPLICABLE:
        if type(assessment.not_applicable_witness) is not (
            EvidenceRequirementNotApplicableWitness
        ):
            raise InvalidEvidenceSufficiency(
                "NOT_APPLICABLE requires its exact Configuration witness"
            )
        if (
            assessment.not_applicable_witness.requirement_id
            != assessment.requirement_id
        ):
            raise InvalidEvidenceSufficiency(
                "negative witness must identify the assessed requirement"
            )
        if assessment.binding_proofs or assessment.counted_observation_ids:
            raise InvalidEvidenceSufficiency(
                "NOT_APPLICABLE cannot retain support proof"
            )
        return
    if assessment.not_applicable_witness is not None:
        raise InvalidEvidenceSufficiency(
            "an applicable requirement cannot carry a negative witness"
        )
    if assessment.disposition is not _entailed_disposition(
        assessment.predicate,
        assessment.binding_proofs,
    ):
        raise InvalidEvidenceSufficiency(
            "requirement disposition is not entailed by its persisted proof"
        )


@dataclass(frozen=True, slots=True)
class EvidenceBindingUniverseGuard:
    binding_ids: frozenset[EvidenceBindingId]

    def __post_init__(self) -> None:
        if type(self.binding_ids) is not frozenset or any(
            type(value) is not EvidenceBindingId for value in self.binding_ids
        ):
            raise TypeError("binding_ids must be frozenset[EvidenceBindingId]")


@dataclass(frozen=True, slots=True)
class EvidenceCorrectionUniverseGuard:
    correction_ids: frozenset[EvidenceCorrectionId]

    def __post_init__(self) -> None:
        if type(self.correction_ids) is not frozenset or any(
            type(value) is not EvidenceCorrectionId for value in self.correction_ids
        ):
            raise TypeError("correction_ids must be frozenset[EvidenceCorrectionId]")


@dataclass(frozen=True, slots=True)
class EvidenceRequirementAuthorityGuard:
    version_ids: frozenset[EvidenceRequirementSetVersionId]

    def __post_init__(self) -> None:
        if type(self.version_ids) is not frozenset or any(
            type(value) is not EvidenceRequirementSetVersionId
            for value in self.version_ids
        ):
            raise TypeError(
                "version_ids must be frozenset[EvidenceRequirementSetVersionId]"
            )


@dataclass(frozen=True, slots=True)
class EvidenceSufficiencyBasisGuards:
    bindings: EvidenceBindingUniverseGuard
    corrections: EvidenceCorrectionUniverseGuard
    requirement_authority: EvidenceRequirementAuthorityGuard

    def __post_init__(self) -> None:
        if type(self.bindings) is not EvidenceBindingUniverseGuard:
            raise TypeError("bindings must be EvidenceBindingUniverseGuard")
        if type(self.corrections) is not EvidenceCorrectionUniverseGuard:
            raise TypeError("corrections must be EvidenceCorrectionUniverseGuard")
        if type(self.requirement_authority) is not EvidenceRequirementAuthorityGuard:
            raise TypeError(
                "requirement_authority must be EvidenceRequirementAuthorityGuard"
            )


@dataclass(frozen=True, slots=True)
class EvidenceSufficiencyEvaluation:
    requirement_assessments: tuple[EvidenceRequirementAssessment, ...]
    result: EvidenceSufficiencyResult
    no_requirements_witness: EvidenceNoSufficiencyRequirementsWitness | None = None


@dataclass(frozen=True, slots=True)
class EvidenceSufficiencyAssessment:
    """Immutable derived proof over one exact requirement and support basis."""

    assessment_id: EvidenceSufficiencyAssessmentId
    target: EvidenceJudgmentRef
    scope: EvidenceScope
    evidence_use: EvidenceUse
    applicability_key: EvidenceRequirementApplicabilityKey
    requirement_set_id: EvidenceRequirementSetId
    requirement_version_id: EvidenceRequirementSetVersionId
    support_version: EvidenceSupportVersion
    basis_guards: EvidenceSufficiencyBasisGuards
    requirement_assessments: tuple[EvidenceRequirementAssessment, ...]
    attribution: ActorAttribution
    effective_at: datetime
    known_at: datetime
    recorded_at: datetime
    result: EvidenceSufficiencyResult
    no_requirements_witness: EvidenceNoSufficiencyRequirementsWitness | None = None
    reassesses_assessment_id: EvidenceSufficiencyAssessmentId | None = None

    def __post_init__(self) -> None:
        _validate_assessment_authority(self)
        _validate_assessment_requirements(self)
        _validate_assessment_temporality(self)
        _validate_assessment_result(self)

    @property
    def contributing_binding_ids(self) -> frozenset[EvidenceBindingId]:
        return frozenset(
            proof.binding_id
            for requirement in self.requirement_assessments
            for proof in requirement.binding_proofs
            if proof.kind is EvidenceRequirementBindingProofKind.CONTRIBUTOR
        )


def _validate_assessment_authority(assessment: EvidenceSufficiencyAssessment) -> None:
    _validate_assessment_identity(assessment)
    _validate_assessment_endpoint(assessment)
    if type(assessment.support_version) is not EvidenceSupportVersion:
        raise TypeError("support_version must be EvidenceSupportVersion")
    if type(assessment.basis_guards) is not EvidenceSufficiencyBasisGuards:
        raise TypeError("basis_guards must be EvidenceSufficiencyBasisGuards")
    if assessment.requirement_version_id not in (
        assessment.basis_guards.requirement_authority.version_ids
    ):
        raise InvalidEvidenceSufficiency(
            "requirement authority guard must contain the resolved version"
        )


def _validate_assessment_requirements(
    assessment: EvidenceSufficiencyAssessment,
) -> None:
    if not isinstance(assessment.requirement_assessments, tuple) or any(
        type(item) is not EvidenceRequirementAssessment
        for item in assessment.requirement_assessments
    ):
        raise TypeError(
            "requirement_assessments must be tuple[EvidenceRequirementAssessment, ...]"
        )
    requirement_ids = [
        item.requirement_id for item in assessment.requirement_assessments
    ]
    if len(requirement_ids) != len(set(requirement_ids)):
        raise InvalidEvidenceSufficiency(
            "each sufficiency requirement must have exactly one assessment"
        )
    for requirement in assessment.requirement_assessments:
        _validate_requirement_authority_binding(assessment, requirement)


def _validate_requirement_authority_binding(
    assessment: EvidenceSufficiencyAssessment,
    requirement: EvidenceRequirementAssessment,
) -> None:
    witness = requirement.not_applicable_witness
    if witness is not None and not _matches_assessment_authority(
        assessment,
        set_id=witness.set_id,
        version_id=witness.version_id,
        applicability_key=witness.applicability_key,
    ):
        raise InvalidEvidenceSufficiency(
            "negative requirement witness must match assessment authority"
        )
    for proof in requirement.binding_proofs:
        for assertion in proof.assertion_proofs:
            freshness = assertion.freshness
            freshness_set_id = (
                freshness.authority.set_id
                if isinstance(freshness, EvidenceFreshnessApplicable)
                else freshness.witness.set_id
            )
            freshness_version_id = (
                freshness.authority.version_id
                if isinstance(freshness, EvidenceFreshnessApplicable)
                else freshness.witness.version_id
            )
            if (
                freshness_set_id != assessment.requirement_set_id
                or freshness_version_id != assessment.requirement_version_id
                or freshness.basis.applicability_key != assessment.applicability_key
            ):
                raise InvalidEvidenceSufficiency(
                    "binding freshness proof must match assessment authority"
                )


def _validate_assessment_temporality(
    assessment: EvidenceSufficiencyAssessment,
) -> None:
    _validate_attribution(assessment.attribution)
    _aware(assessment.effective_at, "effective_at")
    _aware(assessment.known_at, "known_at")
    _aware(assessment.recorded_at, "recorded_at")
    if assessment.known_at > assessment.recorded_at:
        raise InvalidEvidenceSufficiency(
            "known_at cannot be later than the trusted recording instant"
        )


def _validate_assessment_result(assessment: EvidenceSufficiencyAssessment) -> None:
    if type(assessment.result) is not EvidenceSufficiencyResult:
        raise TypeError("result must be EvidenceSufficiencyResult")
    if not assessment.requirement_assessments:
        witness = assessment.no_requirements_witness
        if type(witness) is not EvidenceNoSufficiencyRequirementsWitness:
            raise InvalidEvidenceSufficiency(
                "zero requirements require the exact version-level witness"
            )
        # duplicate-code: version-level and predicate-level negative witnesses are
        # distinct proof forms that independently consume the canonical matcher.
        # arid: disable
        if not _matches_assessment_authority(
            assessment,
            set_id=witness.set_id,
            version_id=witness.version_id,
            applicability_key=witness.applicability_key,
        ):
            # arid: enable
            raise InvalidEvidenceSufficiency(
                "version-level witness must match assessment authority"
            )
    elif assessment.no_requirements_witness is not None:
        raise InvalidEvidenceSufficiency(
            "a non-empty assessment cannot carry a no-requirements witness"
        )
    if assessment.result is not evidence_sufficiency_result(
        assessment.requirement_assessments
    ):
        raise InvalidEvidenceSufficiency(
            "result must obey the accepted requirement-disposition algebra"
        )


def _matches_assessment_authority(
    assessment: EvidenceSufficiencyAssessment,
    *,
    set_id: EvidenceRequirementSetId,
    version_id: EvidenceRequirementSetVersionId,
    applicability_key: EvidenceRequirementApplicabilityKey,
) -> bool:
    return (
        set_id == assessment.requirement_set_id
        and version_id == assessment.requirement_version_id
        and applicability_key == assessment.applicability_key
    )


def matches_assessment_requirement_version(
    assessment: EvidenceSufficiencyAssessment,
    version: EvidenceRequirementSetVersion,
) -> bool:
    return _matches_assessment_authority(
        assessment,
        set_id=version.set_id,
        version_id=version.version_id,
        applicability_key=assessment.applicability_key,
    ) and version.applicability.matches(assessment.applicability_key)


def evaluate_evidence_sufficiency(
    version: EvidenceRequirementSetVersion,
    applicability_key: EvidenceRequirementApplicabilityKey,
    interpretations: tuple[EvidenceBindingInterpretation, ...],
    *,
    effective_at: datetime,
    known_at: datetime,
) -> EvidenceSufficiencyEvaluation:
    if type(version) is not EvidenceRequirementSetVersion:
        raise TypeError("version must be EvidenceRequirementSetVersion")
    if type(applicability_key) is not EvidenceRequirementApplicabilityKey:
        raise TypeError("applicability_key must be EvidenceRequirementApplicabilityKey")
    _aware(effective_at, "effective_at")
    _aware(known_at, "known_at")
    if not version.applicability.matches(applicability_key):
        raise InvalidEvidenceSufficiency(
            "requirement version does not match assessment applicability"
        )
    _validate_interpretation_universe(
        interpretations,
        applicability_key,
        effective_at=effective_at,
        known_at=known_at,
    )
    definitions = tuple(
        item
        for item in version.requirements
        if isinstance(item, SufficiencyRequirementDefinition)
    )
    if not definitions:
        witness = version.no_sufficiency_requirements_witness(applicability_key)
        if witness is None:
            raise InvalidEvidenceSufficiency(
                "resolved zero-definition authority did not supply its witness"
            )
        return EvidenceSufficiencyEvaluation(
            (),
            EvidenceSufficiencyResult.SUFFICIENT,
            witness,
        )
    assessments = tuple(
        _evaluate_requirement(
            version,
            definition,
            applicability_key,
            interpretations,
            effective_at=effective_at,
        )
        for definition in definitions
    )
    return EvidenceSufficiencyEvaluation(
        assessments,
        evidence_sufficiency_result(assessments),
    )


def evidence_sufficiency_result(
    assessments: Iterable[EvidenceRequirementAssessment],
) -> EvidenceSufficiencyResult:
    dispositions = {assessment.disposition for assessment in assessments}
    if dispositions & {
        EvidenceRequirementDisposition.MISSING,
        EvidenceRequirementDisposition.UNAVAILABLE,
        EvidenceRequirementDisposition.STALE,
    }:
        return EvidenceSufficiencyResult.INSUFFICIENT
    if dispositions & {
        EvidenceRequirementDisposition.UNKNOWN,
        EvidenceRequirementDisposition.DISPUTED,
        EvidenceRequirementDisposition.CONTESTED,
    }:
        return EvidenceSufficiencyResult.INDETERMINATE
    return EvidenceSufficiencyResult.SUFFICIENT


def _evaluate_requirement(
    version: EvidenceRequirementSetVersion,
    definition: SufficiencyRequirementDefinition,
    applicability_key: EvidenceRequirementApplicabilityKey,
    interpretations: tuple[EvidenceBindingInterpretation, ...],
    *,
    effective_at: datetime,
) -> EvidenceRequirementAssessment:
    if (
        definition.applicability_state
        is SufficiencyRequirementApplicabilityState.NOT_APPLICABLE
    ):
        witness = version.not_applicable_witness(
            definition.requirement_id,
            applicability_key,
        )
        if witness is None:
            raise InvalidEvidenceSufficiency(
                "NOT_APPLICABLE authority did not supply its exact witness"
            )
        return EvidenceRequirementAssessment(
            definition.requirement_id,
            definition.predicate,
            EvidenceRequirementDisposition.NOT_APPLICABLE,
            frozenset(),
            (),
            witness,
        )
    proofs = tuple(
        _binding_proof(
            version,
            definition.predicate,
            interpretation,
            effective_at=effective_at,
        )
        for interpretation in interpretations
    )
    counted = frozenset(
        proof.observation_id
        for proof in proofs
        if proof.kind is EvidenceRequirementBindingProofKind.CONTRIBUTOR
    )
    return EvidenceRequirementAssessment(
        definition.requirement_id,
        definition.predicate,
        _entailed_disposition(definition.predicate, proofs),
        counted,
        proofs,
    )


def _binding_proof(
    version: EvidenceRequirementSetVersion,
    predicate: MinimumEligibleEvidence,
    interpretation: EvidenceBindingInterpretation,
    *,
    effective_at: datetime,
) -> EvidenceRequirementBindingProof:
    surviving = interpretation.surviving_bindings
    assert surviving is not None
    assertions = tuple(
        _assertion_proof(version, interpretation, binding, predicate, effective_at)
        for binding in sorted(surviving, key=repr)
    )
    deficiencies = tuple(
        value
        for value in assertions
        if value.kind is EvidenceRequirementBindingProofKind.DEFICIENCY
    )
    kind = (
        EvidenceRequirementBindingProofKind.CONTRIBUTOR
        if any(
            value.kind is EvidenceRequirementBindingProofKind.CONTRIBUTOR
            for value in assertions
        )
        else EvidenceRequirementBindingProofKind.DEFICIENCY
        if deficiencies
        else EvidenceRequirementBindingProofKind.VISIBLE
    )
    reason = deficiencies[0].deficiency_reason if deficiencies else None
    return EvidenceRequirementBindingProof(
        interpretation.binding.binding_id,
        interpretation.binding.observation_id,
        kind,
        interpretation.state,
        interpretation.fact_support,
        assertions,
        reason,
    )


def _assertion_proof(
    version: EvidenceRequirementSetVersion,
    interpretation: EvidenceBindingInterpretation,
    binding: EvidenceBinding,
    predicate: MinimumEligibleEvidence,
    effective_at: datetime,
) -> EvidenceRequirementBindingAssertionProof:
    freshness, freshness_authority = _assessment_freshness(
        version, binding, effective_at
    )
    kind, reason = _classify_binding_proof(
        interpretation, binding, predicate, freshness
    )
    return EvidenceRequirementBindingAssertionProof(
        binding,
        freshness,
        freshness_authority,
        kind,
        reason,
    )


def _classify_binding_proof(
    interpretation: EvidenceBindingInterpretation,
    binding: EvidenceBinding,
    predicate: MinimumEligibleEvidence,
    freshness: EvidenceAssessmentFreshness,
) -> tuple[
    EvidenceRequirementBindingProofKind,
    EvidenceRequirementDeficiencyReason | None,
]:
    if binding.role not in predicate.qualifying_roles:
        return EvidenceRequirementBindingProofKind.VISIBLE, None
    if interpretation.state is EvidenceBindingInterpretationState.WITHDRAWN:
        return EvidenceRequirementBindingProofKind.VISIBLE, None
    if interpretation.state is EvidenceBindingInterpretationState.CONTESTED:
        return _unresolved_binding_proof(
            binding,
            EvidenceRequirementDeficiencyReason.CONTESTED,
        )
    if interpretation.state is EvidenceBindingInterpretationState.DISPUTED:
        return _unresolved_binding_proof(
            binding,
            EvidenceRequirementDeficiencyReason.DISPUTED,
        )
    return _determinate_binding_proof(binding, freshness)


def _unresolved_binding_proof(
    binding: EvidenceBinding,
    reason: EvidenceRequirementDeficiencyReason,
) -> tuple[
    EvidenceRequirementBindingProofKind,
    EvidenceRequirementDeficiencyReason | None,
]:
    if binding.materially_used or binding.availability in (
        EvidenceAvailability.UNAVAILABLE,
        EvidenceAvailability.UNKNOWN,
    ):
        return EvidenceRequirementBindingProofKind.DEFICIENCY, reason
    return EvidenceRequirementBindingProofKind.VISIBLE, None


def _determinate_binding_proof(
    binding: EvidenceBinding,
    freshness: EvidenceAssessmentFreshness,
) -> tuple[
    EvidenceRequirementBindingProofKind,
    EvidenceRequirementDeficiencyReason | None,
]:
    if binding.availability is EvidenceAvailability.UNAVAILABLE:
        return (
            EvidenceRequirementBindingProofKind.DEFICIENCY,
            EvidenceRequirementDeficiencyReason.UNAVAILABLE,
        )
    if binding.availability is EvidenceAvailability.UNKNOWN:
        return (
            EvidenceRequirementBindingProofKind.DEFICIENCY,
            EvidenceRequirementDeficiencyReason.UNKNOWN_AVAILABILITY,
        )
    if not binding.materially_used:
        return EvidenceRequirementBindingProofKind.VISIBLE, None
    freshness_result = (
        freshness.result
        if isinstance(freshness, EvidenceFreshnessApplicable)
        else EvidenceFreshnessResult.FRESH
    )
    if freshness_result is EvidenceFreshnessResult.FRESH:
        return EvidenceRequirementBindingProofKind.CONTRIBUTOR, None
    if freshness_result is EvidenceFreshnessResult.STALE:
        return (
            EvidenceRequirementBindingProofKind.DEFICIENCY,
            EvidenceRequirementDeficiencyReason.STALE,
        )
    return (
        EvidenceRequirementBindingProofKind.DEFICIENCY,
        EvidenceRequirementDeficiencyReason.INDETERMINATE_FRESHNESS,
    )


def _assessment_freshness(
    version: EvidenceRequirementSetVersion,
    binding: EvidenceBinding,
    effective_at: datetime,
) -> tuple[EvidenceAssessmentFreshness, EvidenceAssessmentFreshnessAuthority]:
    requirements = tuple(
        item
        for item in version.requirements
        if isinstance(item, FreshnessRequirementDefinition)
    )
    basis = binding.freshness.basis
    if not requirements:
        witness = EvidenceFreshnessNoRequirementWitness(
            version.set_id,
            version.version_id,
        )
        return EvidenceFreshnessNotApplicable(
            witness,
            basis,
        ), witness
    requirement = requirements[0]
    return evaluate_evidence_freshness(
        basis=basis,
        authority_set_id=version.set_id,
        authority_version_id=version.version_id,
        requirement=requirement,
        effective_at=effective_at,
    ), requirement


def _entailed_disposition(
    predicate: MinimumEligibleEvidence,
    proofs: Iterable[EvidenceRequirementBindingProof],
) -> EvidenceRequirementDisposition:
    proof_values = tuple(proofs)
    contributors = _observations(
        proof_values,
        kind=EvidenceRequirementBindingProofKind.CONTRIBUTOR,
    )
    minimum = predicate.minimum_distinct_observations
    if len(contributors) >= minimum:
        return EvidenceRequirementDisposition.SATISFIED
    unresolved = _observations(
        proof_values,
        reasons={
            EvidenceRequirementDeficiencyReason.CONTESTED,
            EvidenceRequirementDeficiencyReason.DISPUTED,
            EvidenceRequirementDeficiencyReason.UNKNOWN_AVAILABILITY,
            EvidenceRequirementDeficiencyReason.INDETERMINATE_FRESHNESS,
        },
    )
    if len(contributors | unresolved) >= minimum:
        reasons = {
            proof.deficiency_reason
            for proof in proof_values
            if proof.observation_id in unresolved
        }
        if EvidenceRequirementDeficiencyReason.CONTESTED in reasons:
            return EvidenceRequirementDisposition.CONTESTED
        if EvidenceRequirementDeficiencyReason.DISPUTED in reasons:
            return EvidenceRequirementDisposition.DISPUTED
        return EvidenceRequirementDisposition.UNKNOWN
    stale = _observations(
        proof_values,
        reasons={EvidenceRequirementDeficiencyReason.STALE},
    )
    if len(contributors | stale) >= minimum:
        return EvidenceRequirementDisposition.STALE
    unavailable = _observations(
        proof_values,
        reasons={EvidenceRequirementDeficiencyReason.UNAVAILABLE},
    )
    if len(contributors | stale | unavailable) >= minimum:
        return EvidenceRequirementDisposition.UNAVAILABLE
    return EvidenceRequirementDisposition.MISSING


def _observations(
    proofs: Iterable[EvidenceRequirementBindingProof],
    *,
    kind: EvidenceRequirementBindingProofKind | None = None,
    reasons: set[EvidenceRequirementDeficiencyReason] | None = None,
) -> frozenset[EvidenceObservationId]:
    return frozenset(
        proof.observation_id
        for proof in proofs
        if (kind is None or proof.kind is kind)
        and (reasons is None or proof.deficiency_reason in reasons)
    )


def _validate_interpretation_universe(
    interpretations: tuple[EvidenceBindingInterpretation, ...],
    key: EvidenceRequirementApplicabilityKey,
    *,
    effective_at: datetime,
    known_at: datetime,
) -> None:
    if not isinstance(interpretations, tuple) or any(
        type(value) is not EvidenceBindingInterpretation for value in interpretations
    ):
        raise TypeError(
            "interpretations must be tuple[EvidenceBindingInterpretation, ...]"
        )
    identifiers = [value.binding.binding_id for value in interpretations]
    if len(identifiers) != len(set(identifiers)):
        raise InvalidEvidenceSufficiency(
            "the complete binding universe cannot repeat a binding root"
        )
    for interpretation in interpretations:
        binding = interpretation.binding
        surviving_bindings = interpretation.surviving_bindings
        assert surviving_bindings is not None
        surviving_subjects = interpretation.surviving_subjects
        assert surviving_subjects is not None
        if (
            interpretation.state is EvidenceBindingInterpretationState.DETERMINATE
            and interpretation.subject not in surviving_subjects
        ):
            raise InvalidEvidenceSufficiency(
                "binding observation subject does not match surviving assertion"
            )
        if (
            binding.target != key.target
            or binding.scope != key.scope
            or binding.evidence_use is not key.evidence_use
            or binding.freshness.basis.applicability_key != key
            or any(
                value.freshness.basis.applicability_key != key
                for value in surviving_bindings
            )
        ):
            raise InvalidEvidenceSufficiency(
                "binding endpoint or applicability coordinates do not match"
            )
        if (
            key.subject is not None
            and interpretation.state is not EvidenceBindingInterpretationState.WITHDRAWN
            and key.subject not in surviving_subjects
        ):
            raise InvalidEvidenceSufficiency(
                "binding observation subject does not match applicability"
            )
        # A withdrawn history may use its immutable root as an anchor even
        # when that root was future-effective at the requested boundary.
        if binding.recorded_at > known_at or any(
            value.effective_at > effective_at or value.recorded_at > known_at
            for value in surviving_bindings
        ):
            raise InvalidEvidenceSufficiency(
                "binding universe contains history outside the requested boundary"
            )


def _validate_assessment_identity(assessment: EvidenceSufficiencyAssessment) -> None:
    if type(assessment.assessment_id) is not EvidenceSufficiencyAssessmentId:
        raise TypeError("assessment_id must be EvidenceSufficiencyAssessmentId")
    if type(assessment.requirement_set_id) is not EvidenceRequirementSetId:
        raise TypeError("requirement_set_id must be EvidenceRequirementSetId")
    if type(assessment.requirement_version_id) is not EvidenceRequirementSetVersionId:
        raise TypeError(
            "requirement_version_id must be EvidenceRequirementSetVersionId"
        )
    predecessor = assessment.reassesses_assessment_id
    if (
        predecessor is not None
        and type(predecessor) is not EvidenceSufficiencyAssessmentId
    ):
        raise TypeError(
            "reassesses_assessment_id must be EvidenceSufficiencyAssessmentId or None"
        )
    if predecessor == assessment.assessment_id:
        raise InvalidEvidenceSufficiency("an assessment cannot reassess itself")


def _validate_assessment_endpoint(assessment: EvidenceSufficiencyAssessment) -> None:
    if not is_evidence_judgment_ref(assessment.target):
        raise TypeError("target must be an EvidenceJudgmentRef")
    if type(assessment.scope) not in (
        JudgmentWideEvidenceScope,
        ClaimSpecificEvidenceScope,
    ):
        raise TypeError("scope must be an EvidenceScope")
    if type(assessment.evidence_use) is not EvidenceUse:
        raise TypeError("evidence_use must be EvidenceUse")
    if type(assessment.applicability_key) is not EvidenceRequirementApplicabilityKey:
        raise TypeError("applicability_key must be EvidenceRequirementApplicabilityKey")
    key = assessment.applicability_key
    if (
        key.target != assessment.target
        or key.scope != assessment.scope
        or key.evidence_use is not assessment.evidence_use
    ):
        raise InvalidEvidenceSufficiency(
            "requirement applicability target/scope/use must match assessment"
        )


def _validate_attribution(attribution: ActorAttribution) -> None:
    if not is_actor_attribution(attribution):
        raise TypeError("attribution must be an ActorAttribution")


def _require_fact_support(value: object) -> None:
    if (
        type(value) is not frozenset
        or not value
        or any(not is_evidence_fact_ref(item) for item in value)
    ):
        raise TypeError("fact_support must be a non-empty frozenset[EvidenceFactRef]")


def _require_observation_ids(value: object) -> None:
    if type(value) is not frozenset or any(
        type(item) is not EvidenceObservationId for item in value
    ):
        raise TypeError(
            "counted_observation_ids must be frozenset[EvidenceObservationId]"
        )


# duplicate-code: sufficiency owns its temporal failure semantics independently.
# arid: disable
def _aware(value: object, field_name: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise InvalidEvidenceSufficiency(f"{field_name} must be timezone-aware")


# arid: enable


__all__ = [
    "EvidenceAssessmentFreshness",
    "EvidenceAssessmentFreshnessAuthority",
    "EvidenceBindingInterpretation",
    "EvidenceBindingInterpretationState",
    "EvidenceBindingUniverseGuard",
    "EvidenceCorrectionUniverseGuard",
    "EvidenceRequirementAssessment",
    "EvidenceRequirementAuthorityGuard",
    "EvidenceRequirementBindingAssertionProof",
    "EvidenceRequirementBindingProof",
    "EvidenceRequirementBindingProofKind",
    "EvidenceRequirementDeficiencyReason",
    "EvidenceRequirementDisposition",
    "EvidenceSufficiencyAssessment",
    "EvidenceSufficiencyBasisGuards",
    "EvidenceSufficiencyEvaluation",
    "EvidenceSufficiencyResult",
    "InvalidEvidenceSufficiency",
    "evaluate_evidence_sufficiency",
    "evidence_sufficiency_result",
    "matches_assessment_requirement_version",
]
