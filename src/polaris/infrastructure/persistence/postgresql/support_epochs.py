from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, insert, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine
from sqlalchemy.sql.elements import ColumnElement

from polaris.application.evidence import EvidenceCommandReadUnavailable
from polaris.domain.evidence.judgments import (
    ClaimSpecificEvidenceScope,
    EvidenceJudgmentRef,
    EvidenceScope,
    EvidenceUse,
    evidence_judgment_family,
    evidence_scope_kind,
)
from polaris.domain.evidence.observations import EvidenceSupportVersion

from .runtime_qualification import require_qualified_postgres_runtime
from .schema import evidence_support_versions

type SupportScope = tuple[str, UUID, str, UUID | None, str]


def support_scope(
    target: EvidenceJudgmentRef,
    scope: EvidenceScope,
    evidence_use: EvidenceUse,
) -> SupportScope:
    return (
        evidence_judgment_family(target).value,
        target.value,
        evidence_scope_kind(scope).value,
        scope.claim_id.value if type(scope) is ClaimSpecificEvidenceScope else None,
        evidence_use.value,
    )


def support_scope_predicates(scope: SupportScope) -> tuple[ColumnElement[bool], ...]:
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


async def load_support_version(
    connection: AsyncConnection,
    scope: SupportScope,
    *,
    effective_at: datetime,
    known_at: datetime,
) -> EvidenceSupportVersion:
    value = await connection.scalar(
        select(func.max(evidence_support_versions.c.support_version)).where(
            *support_scope_predicates(scope),
            evidence_support_versions.c.effective_at <= effective_at,
            evidence_support_versions.c.recorded_at <= known_at,
        )
    )
    return EvidenceSupportVersion(0 if value is None else int(value))


async def advance_support_epochs(
    connection: AsyncConnection,
    scopes: frozenset[SupportScope],
    *,
    source_column: str,
    source_id: UUID,
    effective_at: datetime,
    recorded_at: datetime,
) -> None:
    """Append one epoch per affected key inside the fact's transaction lock."""
    if effective_at > recorded_at:
        return
    if source_column not in {
        "binding_id",
        "correction_id",
        "observation_id",
        "assessment_id",
    }:
        raise ValueError("unsupported Evidence support event source")
    for scope in sorted(scopes, key=lambda value: tuple(map(str, value))):
        current = await connection.scalar(
            select(func.max(evidence_support_versions.c.support_version)).where(
                *support_scope_predicates(scope)
            )
        )
        target_family, target_id, scope_kind, claim_id, evidence_use = scope
        await connection.execute(
            insert(evidence_support_versions).values(
                target_family=target_family,
                target_id=target_id,
                scope_kind=scope_kind,
                claim_id=claim_id,
                evidence_use=evidence_use,
                support_version=(current or 0) + 1,
                effective_at=effective_at,
                recorded_at=recorded_at,
                **{source_column: source_id},
            )
        )


class PostgresEvidenceSupportEpochStore:
    """PostgreSQL read adapter for the inward-owned scope-local epoch."""

    # duplicate-code: this read port owns its runtime qualification and typed
    # failure translation independently from Decision persistence.
    # arid: disable
    def __init__(self, engine: AsyncEngine) -> None:
        require_qualified_postgres_runtime()
        self._engine = engine

    async def load_support_version(
        self,
        target: EvidenceJudgmentRef,
        scope: EvidenceScope,
        evidence_use: EvidenceUse,
        *,
        effective_at: datetime,
        known_at: datetime,
    ) -> EvidenceSupportVersion:
        try:
            async with self._engine.connect() as connection:
                return await load_support_version(
                    connection,
                    support_scope(target, scope, evidence_use),
                    effective_at=effective_at,
                    known_at=known_at,
                )
        except (SQLAlchemyError, ValueError, TypeError) as error:
            raise EvidenceCommandReadUnavailable(
                "Evidence support epoch read is unavailable"
            ) from error

    # arid: enable
