from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from sqlalchemy import func, insert, select, text
from sqlalchemy.engine import RowMapping
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from polaris.application.evidence import EvidenceCommandReadUnavailable
from polaris.application.evidence.requirements import (
    InvalidEvidenceRequirementAuthority,
    ResolvedEvidenceRequirementVersion,
    resolve_requirement_version,
)
from polaris.application.evidence.sufficiency import (
    EvidenceSufficiencyAssessmentResult,
    EvidenceSufficiencyBasis,
    EvidenceSufficiencyBasisResolution,
    EvidenceSufficiencyCommit,
    EvidenceSufficiencyCommitOutcome,
    EvidenceSufficiencyCommitted,
    EvidenceSufficiencyIdempotencyConflict,
    EvidenceSufficiencyInvalidHistory,
    EvidenceSufficiencyReassessmentConflict,
    EvidenceSufficiencyReceipt,
    EvidenceSufficiencyReplayed,
    EvidenceSufficiencyStaleBasis,
    EvidenceSufficiencyStoreUnavailable,
)
from polaris.domain.configuration import EvidenceRequirementApplicabilityKey
from polaris.domain.decisions import OperationId
from polaris.domain.evidence.corrections import EvidenceInterpretationState
from polaris.domain.evidence.judgments import (
    ClaimSpecificEvidenceScope,
    evidence_judgment_family,
    evidence_scope_kind,
)
from polaris.domain.evidence.observations import (
    EvidenceCorrectionId,
    EvidenceSufficiencyAssessmentId,
    EvidenceSupportVersion,
)
from polaris.domain.evidence.sufficiency import (
    EvidenceBindingInterpretation,
    EvidenceBindingInterpretationState,
    EvidenceBindingUniverseGuard,
    EvidenceCorrectionUniverseGuard,
    EvidenceRequirementAuthorityGuard,
    EvidenceSufficiencyAssessment,
    EvidenceSufficiencyBasisGuards,
    evaluate_evidence_sufficiency,
)

from .binding_codec import binding_from_row
from .binding_store import EVIDENCE_BINDING_WRITE_LOCK
from .correction_store import _load_observation_history
from .requirement_store import (
    EVIDENCE_REQUIREMENT_WRITE_LOCK,
    load_requirement_versions_from_connection,
)
from .runtime_qualification import require_qualified_postgres_runtime
from .schema import (
    evidence_bindings,
    evidence_sufficiency_assessments,
    evidence_sufficiency_command_receipts,
    evidence_sufficiency_contributors,
    evidence_support_versions,
)
from .sufficiency_codec import (
    sufficiency_assessment_from_row,
    sufficiency_assessment_values,
    sufficiency_receipt_from_row,
    sufficiency_request_fingerprint,
    sufficiency_request_payload,
    sufficiency_result_payload,
)


class PostgresEvidenceSufficiencyStore:
    """PostgreSQL adapter that re-derives sufficiency inside the write boundary."""

    # duplicate-code: each PostgreSQL adapter owns its runtime qualification and
    # domain-specific read-failure mapping; a shared base would couple adapters.
    # arid: disable
    def __init__(self, engine: AsyncEngine) -> None:
        require_qualified_postgres_runtime()
        self._engine = engine

    async def get_sufficiency_receipt(
        self,
        operation_id: OperationId,
    ) -> EvidenceSufficiencyReceipt | None:
        try:
            async with self._engine.connect() as connection:
                return await _get_receipt(connection, operation_id)
        except (SQLAlchemyError, ValueError, TypeError) as error:
            raise EvidenceCommandReadUnavailable(
                "Evidence sufficiency receipt read is unavailable"
            ) from error

    # arid: enable

    async def load_sufficiency_basis(
        self,
        applicability_key: EvidenceRequirementApplicabilityKey,
        *,
        effective_at: datetime,
        known_at: datetime,
    ) -> EvidenceSufficiencyBasisResolution:
        try:
            async with self._engine.connect() as connection:
                return await _load_basis(
                    connection,
                    applicability_key,
                    effective_at=effective_at,
                    known_at=known_at,
                )
        except SQLAlchemyError as error:
            raise EvidenceCommandReadUnavailable(
                "Evidence sufficiency basis read is unavailable"
            ) from error
        except (ValueError, TypeError) as error:
            return InvalidEvidenceRequirementAuthority(str(error))

    async def load_sufficiency_assessment(
        self,
        assessment_id: EvidenceSufficiencyAssessmentId,
    ) -> EvidenceSufficiencyAssessment | None:
        try:
            async with self._engine.connect() as connection:
                return await _load_assessment(connection, assessment_id)
        except (SQLAlchemyError, ValueError, TypeError) as error:
            raise EvidenceCommandReadUnavailable(
                "Evidence sufficiency assessment read is unavailable"
            ) from error

    async def commit_sufficiency(
        self,
        commit: EvidenceSufficiencyCommit,
    ) -> EvidenceSufficiencyCommitOutcome:
        try:
            async with self._engine.begin() as connection:
                await _lock_authorities(connection)
                prior = await _get_receipt(connection, commit.operation_id)
                if prior is not None:
                    if prior.request != commit.request:
                        return EvidenceSufficiencyIdempotencyConflict(
                            commit.operation_id
                        )
                    return EvidenceSufficiencyReplayed(prior)
                basis = await _load_basis(
                    connection,
                    commit.request.applicability_key,
                    effective_at=commit.request.effective_at,
                    known_at=commit.request.known_at,
                )
                if isinstance(basis, EvidenceSufficiencyInvalidHistory):
                    return basis
                if not isinstance(basis, EvidenceSufficiencyBasis):
                    return basis
                if basis != commit.basis:
                    return EvidenceSufficiencyStaleBasis(
                        "commit-time requirement or support basis changed"
                    )
                revalidated = _revalidated_assessment(commit, basis)
                if revalidated != commit.assessment:
                    return EvidenceSufficiencyStaleBasis(
                        "commit-time derived proof changed"
                    )
                predecessor_conflict = await _reassessment_conflict(
                    connection,
                    commit.assessment,
                )
                if predecessor_conflict is not None:
                    return predecessor_conflict
                await connection.execute(
                    insert(evidence_sufficiency_assessments).values(
                        **sufficiency_assessment_values(commit.assessment)
                    )
                )
                self._write_completed("assessment")
                contributor_rows = [
                    {
                        "assessment_id": commit.assessment.assessment_id.value,
                        "binding_id": binding_id.value,
                    }
                    for binding_id in commit.assessment.contributing_binding_ids
                ]
                if contributor_rows:
                    await connection.execute(
                        insert(evidence_sufficiency_contributors),
                        contributor_rows,
                    )
                self._write_completed("contributors")
                result = EvidenceSufficiencyAssessmentResult(
                    commit.assessment.assessment_id,
                    commit.assessment.result,
                )
                receipt = EvidenceSufficiencyReceipt(
                    commit.operation_id,
                    commit.request,
                    result,
                )
                await connection.execute(
                    insert(evidence_sufficiency_command_receipts).values(
                        operation_id=commit.operation_id.value,
                        request_fingerprint=sufficiency_request_fingerprint(
                            commit.request
                        ),
                        request_payload=sufficiency_request_payload(commit.request),
                        result_payload=sufficiency_result_payload(result),
                        committed_at=commit.committed_at,
                    )
                )
                self._write_completed("receipt")
                return EvidenceSufficiencyCommitted(receipt)
        except (SQLAlchemyError, ValueError, TypeError, RuntimeError) as error:
            return EvidenceSufficiencyStoreUnavailable(
                f"Evidence sufficiency transaction failed: {type(error).__name__}"
            )

    def _write_completed(self, step: str) -> None:
        """Test seam for proving transaction rollback."""
        del step


async def _lock_authorities(connection: AsyncConnection) -> None:
    for lock_key in (
        EVIDENCE_REQUIREMENT_WRITE_LOCK,
        EVIDENCE_BINDING_WRITE_LOCK,
    ):
        await connection.execute(
            text("SELECT pg_advisory_xact_lock(:lock_key)"),
            {"lock_key": lock_key},
        )


async def _load_basis(
    connection: AsyncConnection,
    applicability_key: EvidenceRequirementApplicabilityKey,
    *,
    effective_at: datetime,
    known_at: datetime,
) -> EvidenceSufficiencyBasisResolution:
    try:
        versions = await load_requirement_versions_from_connection(connection)
        resolution = resolve_requirement_version(
            versions,
            applicability_key,
            effective_at=effective_at,
            known_at=known_at,
        )
    except (ValueError, TypeError) as error:
        return InvalidEvidenceRequirementAuthority(str(error))
    if not isinstance(resolution, ResolvedEvidenceRequirementVersion):
        return resolution
    rows = (
        (
            await connection.execute(
                select(evidence_bindings)
                .where(evidence_bindings.c.recorded_at <= known_at)
                .order_by(evidence_bindings.c.row_id)
            )
        )
        .mappings()
        .all()
    )
    try:
        interpreted: list[EvidenceBindingInterpretation] = []
        for row in rows:
            value = await _interpretation_for_key(
                connection,
                row,
                applicability_key,
                effective_at=effective_at,
                known_at=known_at,
            )
            if value is not None:
                interpreted.append(value)
        interpretations = tuple(interpreted)
    except (ValueError, TypeError) as error:
        return EvidenceSufficiencyInvalidHistory(str(error))
    binding_ids = frozenset(value.binding.binding_id for value in interpretations)
    # duplicate-code: basis reconstruction and epoch lookup consume the same
    # coordinates but remain separate dependency reads with distinct outcomes.
    # arid: disable
    support_version = await _load_support_version(
        connection,
        applicability_key,
        effective_at=effective_at,
        known_at=known_at,
    )
    # arid: enable
    guards = EvidenceSufficiencyBasisGuards(
        EvidenceBindingUniverseGuard(binding_ids),
        EvidenceCorrectionUniverseGuard(
            frozenset(
                fact
                for value in interpretations
                for fact in value.fact_support
                if type(fact) is EvidenceCorrectionId
            )
        ),
        EvidenceRequirementAuthorityGuard(frozenset({resolution.version.version_id})),
    )
    return EvidenceSufficiencyBasis(
        resolution.version,
        interpretations,
        EvidenceSupportVersion(support_version),
        guards,
    )


async def _interpretation_for_key(
    connection: AsyncConnection,
    row: RowMapping,
    applicability_key: EvidenceRequirementApplicabilityKey,
    *,
    effective_at: datetime,
    known_at: datetime,
) -> EvidenceBindingInterpretation | None:
    binding = binding_from_row(row)
    if (
        binding.target != applicability_key.target
        or binding.scope != applicability_key.scope
        or binding.evidence_use is not applicability_key.evidence_use
        or binding.freshness.basis.applicability_key != applicability_key
    ):
        return None
    if binding.effective_at > effective_at:
        return None
    history = await _load_observation_history(connection, binding.observation_id)
    if history is None:
        raise ValueError("binding correction history requires its observation root")
    observed = history.interpret(effective_at=effective_at, known_at=known_at)
    if observed.state is EvidenceInterpretationState.NOT_KNOWN:
        raise ValueError(
            "binding references an observation not known at the assessment cutoff"
        )
    if observed.state is EvidenceInterpretationState.NOT_EFFECTIVE:
        raise ValueError(
            "binding references an observation not effective at the assessment cutoff"
        )
    if any(
        value.observed_at > known_at or value.acquired_at > known_at
        for value in observed.assertions
    ):
        raise ValueError(
            "binding references an observation not known at the assessment cutoff"
        )
    subjects = frozenset(value.subject for value in observed.assertions)
    if (
        applicability_key.subject is not None
        and subjects
        and applicability_key.subject not in subjects
    ):
        raise ValueError("binding applicability subject contradicts its observation")
    state = (
        EvidenceBindingInterpretationState.WITHDRAWN
        if observed.state is EvidenceInterpretationState.WITHDRAWN
        else EvidenceBindingInterpretationState.CONTESTED
        if observed.state is EvidenceInterpretationState.CONTESTED
        else EvidenceBindingInterpretationState.DETERMINATE
    )
    subject = (
        next(iter(subjects))
        if state is EvidenceBindingInterpretationState.DETERMINATE
        else history.root.subject
    )
    return EvidenceBindingInterpretation(
        binding,
        subject,
        state,
        observed.fact_support | {binding.binding_id},
        subjects,
    )


async def _load_support_version(
    connection: AsyncConnection,
    applicability_key: EvidenceRequirementApplicabilityKey,
    *,
    effective_at: datetime,
    known_at: datetime,
) -> int:
    claim_id = (
        applicability_key.scope.claim_id.value
        if type(applicability_key.scope) is ClaimSpecificEvidenceScope
        else None
    )
    value = await connection.scalar(
        select(func.max(evidence_support_versions.c.support_version)).where(
            evidence_support_versions.c.target_family
            == evidence_judgment_family(applicability_key.target).value,
            evidence_support_versions.c.target_id == applicability_key.target.value,
            evidence_support_versions.c.scope_kind
            == evidence_scope_kind(applicability_key.scope).value,
            (
                evidence_support_versions.c.claim_id.is_(None)
                if claim_id is None
                else evidence_support_versions.c.claim_id == claim_id
            ),
            evidence_support_versions.c.evidence_use
            == applicability_key.evidence_use.value,
            evidence_support_versions.c.effective_at <= effective_at,
            evidence_support_versions.c.recorded_at <= known_at,
        )
    )
    return 0 if value is None else int(value)


def _revalidated_assessment(
    commit: EvidenceSufficiencyCommit,
    basis: EvidenceSufficiencyBasis,
) -> EvidenceSufficiencyAssessment:
    assessment = commit.assessment
    evaluation = evaluate_evidence_sufficiency(
        basis.requirement_version,
        commit.request.applicability_key,
        basis.interpretations,
        effective_at=commit.request.effective_at,
        known_at=commit.request.known_at,
    )
    return replace(
        assessment,
        support_version=basis.support_version,
        basis_guards=basis.guards,
        requirement_assessments=evaluation.requirement_assessments,
        result=evaluation.result,
        no_requirements_witness=evaluation.no_requirements_witness,
    )


async def _reassessment_conflict(
    connection: AsyncConnection,
    assessment: EvidenceSufficiencyAssessment,
) -> EvidenceSufficiencyReassessmentConflict | None:
    predecessor_id = assessment.reassesses_assessment_id
    if predecessor_id is None:
        return None
    predecessor = await _load_assessment(connection, predecessor_id)
    if predecessor is None or (
        predecessor.target != assessment.target
        or predecessor.scope != assessment.scope
        or predecessor.evidence_use is not assessment.evidence_use
    ):
        return EvidenceSufficiencyReassessmentConflict(predecessor_id)
    return None


async def _load_assessment(
    connection: AsyncConnection,
    assessment_id: EvidenceSufficiencyAssessmentId,
) -> EvidenceSufficiencyAssessment | None:
    row = (
        (
            await connection.execute(
                select(evidence_sufficiency_assessments).where(
                    evidence_sufficiency_assessments.c.assessment_id
                    == assessment_id.value
                )
            )
        )
        .mappings()
        .first()
    )
    return None if row is None else sufficiency_assessment_from_row(row)


async def _get_receipt(
    connection: AsyncConnection,
    operation_id: OperationId,
) -> EvidenceSufficiencyReceipt | None:
    # duplicate-code: this query is table- and codec-specific receipt loading;
    # abstracting it with requirement-version reads would create false coupling.
    # arid: disable
    row = (
        (
            await connection.execute(
                select(evidence_sufficiency_command_receipts).where(
                    evidence_sufficiency_command_receipts.c.operation_id
                    == operation_id.value
                )
            )
        )
        .mappings()
        .first()
    )
    # arid: enable
    if row is None:
        return None
    receipt = sufficiency_receipt_from_row(row)
    if row["request_fingerprint"] != sufficiency_request_fingerprint(receipt.request):
        raise ValueError("stored sufficiency receipt fingerprint does not match")
    return receipt


__all__ = ["PostgresEvidenceSufficiencyStore"]
