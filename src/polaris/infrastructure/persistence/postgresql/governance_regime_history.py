"""Durable owner history and revision reads for R3 authority regimes."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, insert, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from polaris.domain.decisions import OperationId
from polaris.domain.evidence.context_versions import InvestmentAuthorityRegimeId
from polaris.domain.governance_regime_history import (
    AuthorityRegimeCorrectionDraft,
    AuthorityRegimeHistory,
    AuthorityRegimeSelection,
    InvalidAuthorityRegimeHistory,
)

from .governance import HumanDecisionStoreUnavailable, _regime_from_row
from .governance_history import (
    _GOVERNANCE_OWNER_LOCK,
    archive_governance_act_commits,
)
from .intelligence_contract_codec import (
    contract_value_from_payload,
    contract_value_payload,
)
from .runtime_qualification import require_qualified_postgres_runtime
from .schema import (
    authority_regime_corrections,
    governance_authority_regimes,
    human_decision_act_publications,
)


async def load_regime_history(
    connection: AsyncConnection, root: InvestmentAuthorityRegimeId
) -> AuthorityRegimeHistory | None:
    if type(root) is not InvestmentAuthorityRegimeId:
        raise TypeError("regime root must be typed")
    row = (
        (
            await connection.execute(
                select(
                    governance_authority_regimes,
                    # duplicate-code: Regime root and catalog history read distinct
                    # committed owner acts; a shared query would obscure their act
                    # identities.
                    # arid: disable
                    human_decision_act_publications.c.committed_at.label(
                        "trusted_commit_at"
                    ),
                )
                .outerjoin(
                    human_decision_act_publications,
                    human_decision_act_publications.c.act_id
                    # arid: enable
                    == governance_authority_regimes.c.regime_id,
                )
                .where(governance_authority_regimes.c.regime_id == root.value)
                # duplicate-code: Regime root absence and Evidence requirement absence
                # are independent persistence contracts.
                # arid: disable
            )
        )
        .mappings()
        .first()
    )
    if row is None:
        return None
        # arid: enable
    committed_at = row["trusted_commit_at"]
    if not isinstance(committed_at, datetime):
        raise HumanDecisionStoreUnavailable(
            "authority root commit boundary is unavailable"
        )
    history = AuthorityRegimeHistory.form(_regime_from_row(row), committed_at)
    rows = (
        (
            await connection.execute(
                select(
                    authority_regime_corrections,
                    # duplicate-code: Regime correction and catalog history read
                    # distinct committed owner acts; keep their joins explicit.
                    # arid: disable
                    human_decision_act_publications.c.committed_at.label(
                        "trusted_commit_at"
                    ),
                )
                .outerjoin(
                    human_decision_act_publications,
                    human_decision_act_publications.c.act_id
                    # arid: enable
                    == authority_regime_corrections.c.correction_id,
                )
                .where(authority_regime_corrections.c.regime_id == root.value)
                .order_by(authority_regime_corrections.c.sequence)
            )
        )
        .mappings()
        .all()
    )
    for sequence, correction in enumerate(rows, start=1):
        committed_at = correction["trusted_commit_at"]
        draft = contract_value_from_payload(correction["draft"])
        if not isinstance(draft, AuthorityRegimeCorrectionDraft):
            raise InvalidAuthorityRegimeHistory(
                "stored authority correction type differs"
            )
        if (
            not isinstance(committed_at, datetime)
            or draft.root != root
            or draft.correction_id != correction["correction_id"]
            or correction["sequence"] != sequence
            or correction["effective_at"] != draft.effective_at
        ):
            raise InvalidAuthorityRegimeHistory(
                "stored authority correction or commit boundary differs"
            )
        history = history.append(draft.at_boundary(committed_at))
    return history


class PostgresAuthorityRegimeHistoryStore:
    """Append and reconstruct one Governance regime without reissuing its root."""

    def __init__(self, engine: AsyncEngine) -> None:
        require_qualified_postgres_runtime()
        self._engine = engine

    async def load(
        self, root: InvestmentAuthorityRegimeId
    ) -> AuthorityRegimeHistory | None:
        try:
            await archive_governance_act_commits(self._engine)
            async with self._engine.connect() as connection:
                return await load_regime_history(connection, root)
        except SQLAlchemyError as error:
            raise HumanDecisionStoreUnavailable(
                "authority regime history read failed"
                # duplicate-code: Regime and target as-of readers have different owner
                # selection and absence semantics.
                # arid: disable
            ) from error

    async def read_at(
        self,
        root: InvestmentAuthorityRegimeId,
        *,
        effective_at: datetime,
        known_at: datetime,
    ) -> AuthorityRegimeSelection | None:
        history = await self.load(root)
        if history is None:
            return None
            # arid: enable
        return history.select(effective_at, known_at)

    async def append(
        self, operation_id: OperationId, draft: AuthorityRegimeCorrectionDraft
    ) -> AuthorityRegimeHistory:
        if (
            type(operation_id) is not OperationId
            or type(draft) is not AuthorityRegimeCorrectionDraft
        ):
            raise TypeError("typed authority correction inputs are required")
        # duplicate-code: Regime correction admission has its own root-local sequence
        # and idempotency checks; sharing a transaction body would couple distinct owner
        # acts.
        # arid: disable
        try:
            await archive_governance_act_commits(self._engine)
            async with self._engine.begin() as connection:
                await connection.execute(
                    select(func.pg_advisory_xact_lock(_GOVERNANCE_OWNER_LOCK))
                )
                prior = (
                    (
                        await connection.execute(
                            select(authority_regime_corrections).where(
                                authority_regime_corrections.c.operation_id
                                == operation_id.value
                            )
                        )
                    )
                    .mappings()
                    .first()
                )
                if prior is not None:
                    if contract_value_from_payload(prior["draft"]) != draft:
                        # arid: enable
                        raise InvalidAuthorityRegimeHistory(
                            "operation ID has another authority correction"
                        )
                else:
                    history = await load_regime_history(connection, draft.root)
                    if history is None:
                        raise InvalidAuthorityRegimeHistory("authority root is missing")
                    now = await connection.scalar(select(func.clock_timestamp()))
                    assert isinstance(now, datetime)
                    history.append(draft.at_boundary(now))
                    await connection.execute(
                        insert(authority_regime_corrections).values(
                            correction_id=draft.correction_id,
                            operation_id=operation_id.value,
                            regime_id=draft.root.value,
                            sequence=len(history.corrections) + 1,
                            effective_at=draft.effective_at,
                            draft=contract_value_payload(draft),
                        )
                    )
            await archive_governance_act_commits(self._engine)
            # duplicate-code: Regime and Intelligence corrections reconstruct different
            # owner histories after commit.
            # arid: disable
            committed = await self.load(draft.root)
            assert committed is not None
            return committed
        except IntegrityError as error:
            # arid: enable
            raise InvalidAuthorityRegimeHistory(
                "authority correction identity or sequence already exists"
            ) from error
        except SQLAlchemyError as error:
            raise HumanDecisionStoreUnavailable(
                "authority correction append failed"
            ) from error
