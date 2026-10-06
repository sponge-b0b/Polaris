from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Table, func, insert, select, text
from sqlalchemy.engine import RowMapping
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine
from sqlalchemy.sql import Executable
from sqlalchemy.sql.elements import ColumnElement

from polaris.application.evidence import EvidenceCommandReadUnavailable
from polaris.application.evidence.corrections import (
    EvidenceCorrectionAuthorityFailure,
    EvidenceCorrectionAuthorityKind,
    EvidenceCorrectionBasisConflict,
    EvidenceCorrectionCommit,
    EvidenceCorrectionCommitOutcome,
    EvidenceCorrectionCommitted,
    EvidenceCorrectionFamily,
    EvidenceCorrectionIdempotencyConflict,
    EvidenceCorrectionInvalidHistory,
    EvidenceCorrectionReceipt,
    EvidenceCorrectionReferenceConflict,
    EvidenceCorrectionReplayed,
    EvidenceCorrectionResult,
    EvidenceCorrectionStaleBasis,
    EvidenceCorrectionUnavailable,
    _authority_failure,
    _derived_assessment,
    _same_assessment_basis,
    _same_external_basis,
)
from polaris.application.evidence.sufficiency import (
    EvidenceSufficiencyBasis,
    EvidenceSufficiencyBasisResolution,
    EvidenceSufficiencyInvalidHistory,
)
from polaris.domain.configuration import EvidenceRequirementApplicabilityKey
from polaris.domain.decisions import OperationId
from polaris.domain.evidence import (
    EvidenceAssessmentCorrection,
    EvidenceAssessmentCorrectionHistory,
    EvidenceBindingCorrection,
    EvidenceBindingCorrectionHistory,
    EvidenceBindingId,
    EvidenceCorrectionEffect,
    EvidenceObservationCorrection,
    EvidenceObservationCorrectionHistory,
    EvidenceObservationId,
    EvidenceSufficiencyAssessmentId,
    InvalidEvidenceCorrection,
    InvalidEvidenceCorrectionHistory,
)
from polaris.domain.evidence.bindings import EvidenceBinding
from polaris.domain.evidence.judgments import (
    ClaimSpecificEvidenceScope,
    evidence_judgment_family,
    evidence_scope_kind,
)
from polaris.domain.evidence.sufficiency import EvidenceSufficiencyAssessment

from .binding_codec import binding_from_row, binding_values
from .binding_store import EVIDENCE_BINDING_WRITE_LOCK
from .correction_codec import (
    assessment_correction_from_row,
    binding_correction_from_row,
    correction_receipt_from_row,
    correction_request_fingerprint,
    correction_request_payload,
    correction_result_payload,
    correction_values,
    observation_correction_from_row,
)
from .evidence_codec import observation_from_row
from .requirement_store import EVIDENCE_REQUIREMENT_WRITE_LOCK
from .runtime_qualification import require_qualified_postgres_runtime
from .schema import (
    evidence_assessment_corrections,
    evidence_binding_corrections,
    evidence_bindings,
    evidence_correction_command_receipts,
    evidence_correction_identities,
    evidence_observation_command_receipts,
    evidence_observation_corrections,
    evidence_observations,
    evidence_support_versions,
)

EVIDENCE_CORRECTION_WRITE_LOCK = 4_566_144_311_625_725_313


class PostgresEvidenceCorrectionStore:
    """PostgreSQL adapter for typed append-only Evidence correction history."""

    def __init__(
        self,
        engine: AsyncEngine,
        *,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        require_qualified_postgres_runtime()
        self._engine = engine
        self._now = now

    async def get_correction_receipt(
        self,
        operation_id: OperationId,
    ) -> EvidenceCorrectionReceipt | None:
        # duplicate-code: each adapter translates its own persisted receipt
        # failures into the corresponding inward-owned read contract.
        # arid: disable
        try:
            async with self._engine.connect() as connection:
                return await _get_receipt(connection, operation_id)
        except (SQLAlchemyError, ValueError, TypeError) as error:
            raise EvidenceCommandReadUnavailable(
                "Evidence correction receipt read is unavailable"
            ) from error
        # arid: enable

    async def commit_correction(
        self,
        commit: EvidenceCorrectionCommit,
    ) -> EvidenceCorrectionCommitOutcome:
        try:
            async with self._engine.begin() as connection:
                if type(commit.correction) is EvidenceAssessmentCorrection:
                    await connection.execute(
                        text("SELECT pg_advisory_xact_lock(:lock_key)"),
                        {"lock_key": EVIDENCE_REQUIREMENT_WRITE_LOCK},
                    )
                for lock_key in (
                    EVIDENCE_BINDING_WRITE_LOCK,
                    EVIDENCE_CORRECTION_WRITE_LOCK,
                ):
                    await connection.execute(
                        text("SELECT pg_advisory_xact_lock(:lock_key)"),
                        {"lock_key": lock_key},
                    )
                prior = await _get_receipt(connection, commit.operation_id)
                if prior is not None:
                    if prior.request != commit.request:
                        return EvidenceCorrectionIdempotencyConflict(
                            commit.operation_id
                        )
                    return EvidenceCorrectionReplayed(prior)
                if type(commit.correction) is EvidenceAssessmentCorrection:
                    trusted = await _trusted_assessment_commit(
                        connection, commit, self._now()
                    )
                    if not isinstance(trusted, EvidenceCorrectionCommit):
                        return trusted
                    commit = trusted
                conflict = await _validate_commit_history(connection, commit)
                if conflict is not None:
                    return conflict
                await connection.execute(
                    insert(evidence_correction_identities).values(
                        correction_id=commit.correction.correction_id.value,
                        family=commit.request.family.value,
                    )
                )
                self._write_completed("identity")
                await connection.execute(
                    insert(_correction_table(commit.request.family)).values(
                        **correction_values(commit.correction)
                    )
                )
                self._write_completed("correction")
                await _record_support_version_events(connection, commit)
                self._write_completed("support_version")
                result = EvidenceCorrectionResult(commit.correction.correction_id)
                receipt = EvidenceCorrectionReceipt(
                    commit.operation_id,
                    commit.request,
                    result,
                )
                # duplicate-code: correction receipts carry family identity and
                # correction payloads; sharing SQL with sufficiency couples tables.
                # arid: disable
                await connection.execute(
                    insert(evidence_correction_command_receipts).values(
                        operation_id=commit.operation_id.value,
                        family=commit.request.family.value,
                        request_fingerprint=correction_request_fingerprint(
                            commit.request
                        ),
                        request_payload=correction_request_payload(commit.request),
                        result_payload=correction_result_payload(result),
                        committed_at=commit.committed_at,
                    )
                )
                # arid: enable
                self._write_completed("receipt")
                return EvidenceCorrectionCommitted(receipt)
        except (SQLAlchemyError, ValueError, TypeError, RuntimeError) as error:
            return EvidenceCorrectionUnavailable(
                f"Evidence correction transaction failed: {type(error).__name__}"
            )

    async def load_observation_history(
        self,
        root_id: EvidenceObservationId,
    ) -> EvidenceObservationCorrectionHistory | None:
        try:
            async with self._engine.connect() as connection:
                return await _load_observation_history(connection, root_id)
        except (SQLAlchemyError, ValueError, TypeError) as error:
            raise EvidenceCommandReadUnavailable(
                "Evidence observation correction history is unavailable"
            ) from error

    async def load_binding_history(
        self,
        root_id: EvidenceBindingId,
    ) -> EvidenceBindingCorrectionHistory | None:
        try:
            async with self._engine.connect() as connection:
                return await _load_binding_history(connection, root_id)
        except (SQLAlchemyError, ValueError, TypeError) as error:
            raise EvidenceCommandReadUnavailable(
                "Evidence binding correction history is unavailable"
            ) from error

    async def load_assessment_history(
        self,
        root_id: EvidenceSufficiencyAssessmentId,
    ) -> EvidenceAssessmentCorrectionHistory | None:
        try:
            async with self._engine.connect() as connection:
                return await _load_assessment_history(connection, root_id)
        except (SQLAlchemyError, ValueError, TypeError) as error:
            raise EvidenceCommandReadUnavailable(
                "Evidence assessment correction history is unavailable"
            ) from error

    async def load_sufficiency_basis(
        self,
        applicability_key: EvidenceRequirementApplicabilityKey,
        *,
        effective_at: datetime,
        known_at: datetime,
    ) -> EvidenceSufficiencyBasisResolution:
        from .sufficiency_store import PostgresEvidenceSufficiencyStore

        return await PostgresEvidenceSufficiencyStore(
            self._engine
        ).load_sufficiency_basis(
            applicability_key, effective_at=effective_at, known_at=known_at
        )

    def _write_completed(self, step: str) -> None:
        """Test seam for proving transaction rollback."""
        del step


async def _trusted_assessment_commit(
    connection: AsyncConnection,
    commit: EvidenceCorrectionCommit,
    trusted_at: datetime,
) -> (
    EvidenceCorrectionCommit
    | EvidenceCorrectionReferenceConflict
    | EvidenceCorrectionStaleBasis
    | EvidenceCorrectionAuthorityFailure
    | EvidenceCorrectionInvalidHistory
):
    correction = commit.correction
    assert type(correction) is EvidenceAssessmentCorrection
    history = await _load_trusted_assessment_history(connection, correction, trusted_at)
    if not isinstance(history, EvidenceAssessmentCorrectionHistory):
        return history
    root = history.root
    original = await _load_trusted_assessment_basis(
        connection,
        root.applicability_key,
        effective_at=root.effective_at,
        known_at=root.known_at,
    )
    if not isinstance(original, EvidenceSufficiencyBasis):
        return original
    current = await _load_trusted_assessment_basis(
        connection,
        root.applicability_key,
        effective_at=trusted_at,
        known_at=trusted_at,
    )
    if not isinstance(current, EvidenceSufficiencyBasis):
        return current
    if original != commit.assessment_basis or current != commit.assessment_commit_basis:
        return EvidenceCorrectionStaleBasis(
            "commit-time requirement, binding, correction, or support basis changed"
        )
    try:
        trusted_original = _derived_assessment(
            root,
            original,
            effective_at=root.effective_at,
            known_at=root.known_at,
        )
        trusted_current = _derived_assessment(
            root,
            current,
            effective_at=trusted_at,
            known_at=trusted_at,
        )
    except EvidenceCorrectionBasisConflict as error:
        return EvidenceCorrectionStaleBasis(str(error))
    if (
        not _same_external_basis(original, current)
        or not _same_assessment_basis(
            trusted_original,
            trusted_current,
            allow_support_drift=bool(history.corrections),
        )
        or not await _only_own_assessment_support_events(
            connection, root, original, current, trusted_at
        )
    ):
        return EvidenceCorrectionStaleBasis(
            "trusted commit-time derivation changed; reassess under a new root"
        )
    if correction.effect is EvidenceCorrectionEffect.REVISE:
        if correction.replacement != trusted_original:
            return EvidenceCorrectionStaleBasis(
                "assessment replacement is not Evidence-derived from its exact basis"
            )
        replacement = trusted_original
    else:
        replacement = None
    trusted_correction = replace(
        correction,
        recorded_at=trusted_at,
        replacement=replacement,
    )
    return replace(commit, correction=trusted_correction, committed_at=trusted_at)


async def _load_trusted_assessment_history(
    connection: AsyncConnection,
    correction: EvidenceAssessmentCorrection,
    trusted_at: datetime,
) -> (
    EvidenceAssessmentCorrectionHistory
    | EvidenceCorrectionInvalidHistory
    | EvidenceCorrectionReferenceConflict
):
    try:
        history = await _load_assessment_history(connection, correction.root_id)
    except (ValueError, TypeError) as error:
        return EvidenceCorrectionInvalidHistory(str(error))
    # duplicate-code: trusted assessment preparation reports a typed missing
    # authority root independently from generic lineage validation.
    # arid: disable
    if history is None:
        return EvidenceCorrectionReferenceConflict(
            correction.root_id,
            correction.target,
            "Evidence assessment correction root does not exist",
        )
    # arid: enable
    if trusted_at < history.root.recorded_at:
        return EvidenceCorrectionInvalidHistory(
            "assessment correction cannot be recorded before its root"
        )
    if correction.effective_at < history.root.effective_at:
        return EvidenceCorrectionReferenceConflict(
            correction.root_id,
            correction.target,
            "assessment correction precedes the root assessment boundary",
        )
    return history


async def _load_trusted_assessment_basis(
    connection: AsyncConnection,
    key: EvidenceRequirementApplicabilityKey,
    *,
    effective_at: datetime,
    known_at: datetime,
) -> (
    EvidenceSufficiencyBasis
    | EvidenceCorrectionAuthorityFailure
    | EvidenceCorrectionInvalidHistory
):
    from .sufficiency_store import _load_basis

    try:
        result = await _load_basis(
            connection, key, effective_at=effective_at, known_at=known_at
        )
    except SQLAlchemyError:
        return EvidenceCorrectionAuthorityFailure(
            EvidenceCorrectionAuthorityKind.UNAVAILABLE,
            "requirement or binding revalidation is unavailable",
        )
    return _assessment_basis_or_failure(result)


def _assessment_basis_or_failure(
    result: EvidenceSufficiencyBasisResolution,
) -> (
    EvidenceSufficiencyBasis
    | EvidenceCorrectionAuthorityFailure
    | EvidenceCorrectionInvalidHistory
):
    if isinstance(result, EvidenceSufficiencyBasis):
        return result
    if isinstance(result, EvidenceSufficiencyInvalidHistory):
        return EvidenceCorrectionInvalidHistory(result.reason)
    return _authority_failure(result)


async def _only_own_assessment_support_events(
    connection: AsyncConnection,
    root: EvidenceSufficiencyAssessment,
    original: EvidenceSufficiencyBasis,
    current: EvidenceSufficiencyBasis,
    trusted_at: datetime,
) -> bool:
    start = original.support_version.value
    end = current.support_version.value
    if end < start:
        return False
    if end == start:
        return True
    scope = _assessment_scope(root)
    rows = (
        (
            await connection.execute(
                select(
                    evidence_support_versions.c.support_version,
                    evidence_support_versions.c.binding_id,
                    evidence_support_versions.c.correction_id,
                ).where(
                    *_support_scope_predicates(scope),
                    evidence_support_versions.c.support_version > start,
                    evidence_support_versions.c.support_version <= end,
                    evidence_support_versions.c.effective_at <= trusted_at,
                    evidence_support_versions.c.recorded_at <= trusted_at,
                )
            )
        )
        .mappings()
        .all()
    )
    if {row["support_version"] for row in rows} != set(range(start + 1, end + 1)):
        return False
    for row in rows:
        if row["binding_id"] is not None or row["correction_id"] is None:
            return False
        owner = await _one_row(
            connection,
            select(evidence_assessment_corrections.c.root_id).where(
                evidence_assessment_corrections.c.correction_id == row["correction_id"]
            ),
        )
        if owner is None or owner["root_id"] != root.assessment_id.value:
            return False
    return True


async def _validate_commit_history(
    connection: AsyncConnection,
    commit: EvidenceCorrectionCommit,
) -> EvidenceCorrectionReferenceConflict | None:
    correction = commit.correction
    if type(correction) is EvidenceBindingCorrection:
        history = await _load_binding_history(connection, correction.root_id)
    elif type(correction) is EvidenceAssessmentCorrection:
        history = await _load_assessment_history(connection, correction.root_id)
    elif type(correction) is EvidenceObservationCorrection:
        history = await _load_observation_history(connection, correction.root_id)
    else:
        raise TypeError("unsupported Evidence correction")
    if history is None:
        return EvidenceCorrectionReferenceConflict(
            correction.root_id,
            correction.target,
            "Evidence correction root does not exist",
        )
    if type(correction) is EvidenceObservationCorrection:
        conflict = await _observation_predecessor_conflict(connection, correction)
        if conflict is not None:
            return conflict
    try:
        if type(history) is EvidenceBindingCorrectionHistory:
            assert type(correction) is EvidenceBindingCorrection
            candidate = EvidenceBindingCorrectionHistory(
                history.root, (*history.corrections, correction)
            )
        elif type(history) is EvidenceAssessmentCorrectionHistory:
            assert type(correction) is EvidenceAssessmentCorrection
            candidate = EvidenceAssessmentCorrectionHistory(
                history.root, (*history.corrections, correction)
            )
        else:
            assert type(history) is EvidenceObservationCorrectionHistory
            assert type(correction) is EvidenceObservationCorrection
            candidate = EvidenceObservationCorrectionHistory(
                history.root,
                history.root_recorded_at,
                (*history.corrections, correction),
            )
        candidate.interpret(
            effective_at=commit.committed_at,
            known_at=commit.committed_at,
        )
    except (InvalidEvidenceCorrection, InvalidEvidenceCorrectionHistory) as error:
        return EvidenceCorrectionReferenceConflict(
            correction.root_id,
            correction.target,
            str(error),
        )
    return None


async def _observation_predecessor_conflict(
    connection: AsyncConnection,
    correction: EvidenceObservationCorrection,
) -> EvidenceCorrectionReferenceConflict | None:
    if correction.replacement is None:
        return None
    predecessor = correction.replacement.supersedes_observation_id
    if predecessor is None:
        return None
    # Root admission requires an existing predecessor; decreasing row identities
    # keep corrected succession chains earlier and acyclic.
    root_row = await _one_row(
        connection,
        select(evidence_observations.c.row_id).where(
            evidence_observations.c.observation_id == correction.root_id.value
        ),
    )
    predecessor_row = await _one_row(
        connection,
        select(evidence_observations.c.row_id).where(
            evidence_observations.c.observation_id == predecessor.value
        ),
    )
    if (
        root_row is None
        or predecessor_row is None
        or predecessor_row["row_id"] >= root_row["row_id"]
    ):
        return EvidenceCorrectionReferenceConflict(
            correction.root_id,
            correction.target,
            "Evidence correction predecessor must be an earlier observation root",
        )
    return None


def _correction_table(family: EvidenceCorrectionFamily) -> Table:
    if family is EvidenceCorrectionFamily.OBSERVATION:
        return evidence_observation_corrections
    if family is EvidenceCorrectionFamily.BINDING:
        return evidence_binding_corrections
    if family is EvidenceCorrectionFamily.ASSESSMENT:
        return evidence_assessment_corrections
    raise TypeError("unsupported Evidence correction family")


async def _load_observation_history(
    connection: AsyncConnection,
    root_id: EvidenceObservationId,
) -> EvidenceObservationCorrectionHistory | None:
    row = await _one_row(
        connection,
        select(evidence_observations).where(
            evidence_observations.c.observation_id == root_id.value
        ),
    )
    if row is None:
        return None
    corrections = await _correction_rows(
        connection,
        evidence_observation_corrections,
        root_id.value,
    )
    receipt_rows = (
        (
            await connection.execute(
                select(evidence_observation_command_receipts.c.committed_at)
                .where(
                    evidence_observation_command_receipts.c.result_payload[
                        "observation_id"
                    ].astext
                    == str(root_id.value)
                )
                .limit(2)
            )
        )
        .mappings()
        .all()
    )
    if len(receipt_rows) != 1:
        raise ValueError("observation root requires one immutable commit receipt")
    root = observation_from_row(row)
    return EvidenceObservationCorrectionHistory(
        root,
        receipt_rows[0]["committed_at"],
        tuple(observation_correction_from_row(value) for value in corrections),
    )


async def _load_binding_history(
    connection: AsyncConnection,
    root_id: EvidenceBindingId,
) -> EvidenceBindingCorrectionHistory | None:
    row = await _one_row(
        connection,
        select(evidence_bindings).where(
            evidence_bindings.c.binding_id == root_id.value
        ),
    )
    if row is None:
        return None
    corrections = await _correction_rows(
        connection, evidence_binding_corrections, root_id.value
    )
    return EvidenceBindingCorrectionHistory(
        binding_from_row(row),
        tuple(binding_correction_from_row(value) for value in corrections),
    )


async def _load_assessment_history(
    connection: AsyncConnection,
    root_id: EvidenceSufficiencyAssessmentId,
) -> EvidenceAssessmentCorrectionHistory | None:
    from .sufficiency_store import _load_assessment

    root = await _load_assessment(connection, root_id)
    if root is None:
        return None
    corrections = await _correction_rows(
        connection, evidence_assessment_corrections, root_id.value
    )
    return EvidenceAssessmentCorrectionHistory(
        root,
        tuple(assessment_correction_from_row(row) for row in corrections),
    )


async def _one_row(
    connection: AsyncConnection,
    statement: Executable,
) -> RowMapping | None:
    return (await connection.execute(statement)).mappings().first()


async def _correction_rows(
    connection: AsyncConnection,
    table: Table,
    root_id: UUID,
) -> tuple[RowMapping, ...]:
    rows = (
        (
            await connection.execute(
                select(table).where(table.c.root_id == root_id).order_by(table.c.row_id)
            )
        )
        .mappings()
        .all()
    )
    return tuple(rows)


async def _get_receipt(
    connection: AsyncConnection,
    operation_id: OperationId,
) -> EvidenceCorrectionReceipt | None:
    row = await _one_row(
        connection,
        select(evidence_correction_command_receipts).where(
            evidence_correction_command_receipts.c.operation_id == operation_id.value
        ),
    )
    if row is None:
        return None
    receipt = correction_receipt_from_row(row)
    if row["request_fingerprint"] != correction_request_fingerprint(receipt.request):
        raise ValueError("stored correction receipt fingerprint does not match")
    if row["family"] != receipt.request.family.value:
        raise ValueError("stored correction receipt family does not match")
    return receipt


type _SupportScope = tuple[str, UUID, str, UUID | None, str]


def _support_scope_predicates(scope: _SupportScope) -> tuple[ColumnElement[bool], ...]:
    target_family, target_id, scope_kind, claim_id, evidence_use = scope
    return (
        evidence_support_versions.c.target_family == target_family,
        evidence_support_versions.c.target_id == target_id,
        evidence_support_versions.c.scope_kind == scope_kind,
        (
            evidence_support_versions.c.claim_id.is_(None)
            if claim_id is None
            else evidence_support_versions.c.claim_id == claim_id
        ),
        evidence_support_versions.c.evidence_use == evidence_use,
    )


async def _record_support_version_events(
    connection: AsyncConnection,
    commit: EvidenceCorrectionCommit,
) -> None:
    correction = commit.correction
    if correction.effective_at > commit.committed_at:
        return
    scopes = await _affected_support_scopes(connection, correction, commit.committed_at)
    for scope in sorted(scopes, key=lambda value: tuple(map(str, value))):
        target_family, target_id, scope_kind, claim_id, evidence_use = scope
        predicates = _support_scope_predicates(scope)
        current = await connection.scalar(
            select(func.max(evidence_support_versions.c.support_version)).where(
                *predicates
            )
        )
        await connection.execute(
            insert(evidence_support_versions).values(
                target_family=target_family,
                target_id=target_id,
                scope_kind=scope_kind,
                claim_id=claim_id,
                evidence_use=evidence_use,
                binding_id=None,
                correction_id=correction.correction_id.value,
                support_version=(current or 0) + 1,
                effective_at=correction.effective_at,
                recorded_at=commit.committed_at,
            )
        )


async def _affected_support_scopes(
    connection: AsyncConnection,
    correction: (
        EvidenceObservationCorrection
        | EvidenceBindingCorrection
        | EvidenceAssessmentCorrection
    ),
    committed_at: datetime,
) -> frozenset[_SupportScope]:
    if type(correction) is EvidenceAssessmentCorrection:
        history = await _load_assessment_history(connection, correction.root_id)
        if history is None:
            raise ValueError("assessment correction root disappeared")
        return frozenset({_assessment_scope(history.root)})
    if type(correction) is EvidenceBindingCorrection:
        row = await _one_row(
            connection,
            select(evidence_bindings).where(
                evidence_bindings.c.binding_id == correction.root_id.value,
                evidence_bindings.c.recorded_at <= committed_at,
            ),
        )
        if row is None:
            return frozenset()
        return frozenset({_binding_scope(binding_from_row(row))})
    rows = (
        (
            await connection.execute(
                select(evidence_bindings).where(
                    evidence_bindings.c.observation_id == correction.root_id.value,
                    evidence_bindings.c.effective_at <= committed_at,
                    evidence_bindings.c.recorded_at <= committed_at,
                )
            )
        )
        .mappings()
        .all()
    )
    return frozenset(_binding_scope(binding_from_row(row)) for row in rows)


def _binding_scope(binding: EvidenceBinding) -> _SupportScope:
    values = binding_values(binding)
    return (
        str(values["target_family"]),
        binding.target.value,
        str(values["scope_kind"]),
        values["claim_id"] if isinstance(values["claim_id"], UUID) else None,
        str(values["evidence_use"]),
    )


def _assessment_scope(assessment: EvidenceSufficiencyAssessment) -> _SupportScope:
    return (
        evidence_judgment_family(assessment.target).value,
        assessment.target.value,
        evidence_scope_kind(assessment.scope).value,
        (
            assessment.scope.claim_id.value
            if type(assessment.scope) is ClaimSpecificEvidenceScope
            else None
        ),
        assessment.evidence_use.value,
    )


__all__ = ["EVIDENCE_CORRECTION_WRITE_LOCK", "PostgresEvidenceCorrectionStore"]
