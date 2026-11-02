"""Durable Governance target corrections and commit-boundary reconstruction."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, insert, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Row
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from polaris.domain.decisions import OperationId
from polaris.domain.evidence.judgments import HumanInvestmentDecisionRef
from polaris.domain.governance_judgment_history import (
    HumanDecisionTargetCorrectionDraft,
    HumanDecisionTargetHistory,
    HumanDecisionTargetNeedsReevaluation,
    HumanDecisionTargetNotKnown,
    HumanDecisionTargetSelection,
    InvalidHumanDecisionTargetHistory,
)
from polaris.domain.human_investment_decision import require_human_decision_authority

from .governance import (
    HumanDecisionStoreUnavailable,
    _decision_from_row,
    _load_regime,
    _require_recommendation_links,
)
from .intelligence_contract_codec import (
    contract_value_from_payload,
    contract_value_payload,
)
from .runtime_qualification import require_qualified_postgres_runtime
from .schema import (
    human_decision_act_publications,
    human_decision_target_corrections,
    human_investment_decisions,
)
from .wal_commit_custody import (
    advance_commit_slot,
    commit_boundary,
    ensure_commit_slot,
    owner_archive_connection,
    peek_commit_rows,
    transactional_message,
)

_SLOT_SETUP_LOCK = 6_934_842_191_352_427_201
_SLOT_ARCHIVE_LOCK = 6_934_842_191_352_427_202
_GOVERNANCE_OWNER_LOCK = 6_934_842_191_352_427_203


async def ensure_governance_commit_slot(engine: AsyncEngine) -> str:
    """Require durable WAL custody before an owner act can commit."""
    require_qualified_postgres_runtime()
    return await ensure_commit_slot(
        engine,
        prefix="polaris_ga_",
        setup_lock=_SLOT_SETUP_LOCK,
        owner_acts=human_investment_decisions,
        error_type=HumanDecisionStoreUnavailable,
    )


def _commit_markers(
    rows: Sequence[Row[Any]], slot: str
) -> tuple[dict[UUID, tuple[str, datetime]], int | None]:
    pending: dict[int, list[tuple[str, UUID]]] = {}
    committed: dict[UUID, tuple[str, datetime]] = {}
    end_lsn: int | None = None
    for _, xid, payload in rows:
        if not isinstance(xid, int) or not isinstance(payload, bytes):
            raise HumanDecisionStoreUnavailable("invalid Governance WAL row")
        if payload[:1] == b"B":
            pending[xid] = []
        elif payload[:1] == b"M":
            marker = _parse_message(payload, slot)
            if marker is None:
                continue
            if xid not in pending:
                raise HumanDecisionStoreUnavailable(
                    "Governance WAL act has no transaction"
                )
            pending[xid].append(marker)
        elif payload[:1] == b"C":
            end_lsn = _finish_commit(payload, xid, pending, committed)
    if pending:
        raise HumanDecisionStoreUnavailable(
            "Governance WAL decoding ended inside a transaction"
        )
    return committed, end_lsn


def _parse_message(payload: bytes, slot: str) -> tuple[str, UUID] | None:
    content = transactional_message(payload, slot, HumanDecisionStoreUnavailable)
    if content is None:
        return None
    try:
        kind_bytes, raw_id = content.split(b":", 1)
        kind = kind_bytes.decode("ascii")
        identity = UUID(raw_id.decode("ascii"))
    except (ValueError, UnicodeDecodeError) as error:
        raise HumanDecisionStoreUnavailable(
            "Governance WAL act identity is invalid"
        ) from error
    if kind not in {"root", "correction"}:
        raise HumanDecisionStoreUnavailable("Governance WAL act kind is invalid")
    return kind, identity


def _finish_commit(
    payload: bytes,
    xid: int,
    pending: dict[int, list[tuple[str, UUID]]],
    committed: dict[UUID, tuple[str, datetime]],
) -> int:
    committed_at, end_lsn = commit_boundary(
        payload, xid, pending, HumanDecisionStoreUnavailable
    )
    for kind, identity in pending.pop(xid):
        if identity in committed:
            raise HumanDecisionStoreUnavailable("Governance act marker was repeated")
        committed[identity] = (kind, committed_at)
    return end_lsn


async def archive_governance_act_commits(engine: AsyncEngine) -> None:
    """Archive exact commits before the WAL slot may advance."""
    slot = await ensure_governance_commit_slot(engine)
    async with owner_archive_connection(engine, _SLOT_ARCHIVE_LOCK) as connection:
        rows = await peek_commit_rows(connection, slot)
        publications, end_lsn = _commit_markers(rows, slot)
        for identity, (kind, committed_at) in publications.items():
            table = (
                human_investment_decisions
                if kind == "root"
                else human_decision_target_corrections
            )
            key = table.c.decision_ref if kind == "root" else table.c.correction_id
            exists = await connection.scalar(select(key).where(key == identity))
            if exists is None:
                raise HumanDecisionStoreUnavailable(
                    "Governance WAL marker has no committed owner act"
                )
            await connection.execute(
                pg_insert(human_decision_act_publications)
                .values(act_id=identity, kind=kind, committed_at=committed_at)
                .on_conflict_do_nothing(
                    index_elements=[human_decision_act_publications.c.act_id]
                )
            )
            archived = (
                (
                    await connection.execute(
                        select(human_decision_act_publications).where(
                            human_decision_act_publications.c.act_id == identity
                        )
                    )
                )
                .mappings()
                .one()
            )
            if archived["kind"] != kind or archived["committed_at"] != committed_at:
                raise HumanDecisionStoreUnavailable(
                    "archived Governance commit boundary differs from WAL"
                )
        await advance_commit_slot(connection, slot, end_lsn)


async def _load(
    connection: AsyncConnection, root: HumanInvestmentDecisionRef
) -> HumanDecisionTargetHistory | None:
    # duplicate-code: Root and correction rows have different owner identities
    # and reconstruction rules, so their explicit history reads stay separate.
    # arid: disable
    root_row = (
        (
            await connection.execute(
                select(
                    human_investment_decisions,
                    human_decision_act_publications.c.committed_at.label(
                        "trusted_commit_at"
                    ),
                )
                .outerjoin(
                    human_decision_act_publications,
                    human_decision_act_publications.c.act_id
                    == human_investment_decisions.c.decision_ref,
                )
                .where(human_investment_decisions.c.decision_ref == root.value)
            )
        )
        .mappings()
        .first()
    )
    # arid: enable
    if root_row is None:
        return None
    committed_at = root_row["trusted_commit_at"]
    if not isinstance(committed_at, datetime):
        raise HumanDecisionStoreUnavailable("root commit boundary is unavailable")
    history = HumanDecisionTargetHistory.form(
        _decision_from_row(root_row), committed_at
    )
    # duplicate-code: The correction read joins a different committed-act
    # identity and orders the root-local owner history.
    # arid: disable
    correction_rows = (
        (
            await connection.execute(
                select(
                    human_decision_target_corrections,
                    human_decision_act_publications.c.committed_at.label(
                        "trusted_commit_at"
                    ),
                )
                .outerjoin(
                    human_decision_act_publications,
                    human_decision_act_publications.c.act_id
                    == human_decision_target_corrections.c.correction_id,
                )
                .where(human_decision_target_corrections.c.decision_ref == root.value)
                .order_by(human_decision_target_corrections.c.sequence)
            )
        )
        .mappings()
        .all()
    )
    # arid: enable
    for sequence, row in enumerate(correction_rows, start=1):
        committed_at = row["trusted_commit_at"]
        draft = contract_value_from_payload(row["draft"])
        if not isinstance(draft, HumanDecisionTargetCorrectionDraft):
            raise InvalidHumanDecisionTargetHistory(
                "stored Governance correction type differs"
            )
        if (
            not isinstance(committed_at, datetime)
            or draft.root != root
            or draft.correction_id != row["correction_id"]
            or row["sequence"] != sequence
            or row["effective_at"] != draft.effective_at
        ):
            raise InvalidHumanDecisionTargetHistory(
                "stored Governance correction metadata differs"
            )
        history = history.append(draft.at_boundary(committed_at))
    return history


class PostgresHumanDecisionTargetHistoryStore:
    """Append and reconstruct one Governance target from owner history."""

    def __init__(self, engine: AsyncEngine) -> None:
        require_qualified_postgres_runtime()
        self._engine = engine

    async def load(
        self, root: HumanInvestmentDecisionRef
    ) -> HumanDecisionTargetHistory | None:
        if type(root) is not HumanInvestmentDecisionRef:
            raise TypeError("root must be HumanInvestmentDecisionRef")
        try:
            await archive_governance_act_commits(self._engine)
            async with self._engine.connect() as connection:
                return await _load(connection, root)
        except SQLAlchemyError as error:
            raise HumanDecisionStoreUnavailable(
                "Governance target history read failed"
            ) from error

    async def read_at(
        self,
        root: HumanInvestmentDecisionRef,
        *,
        effective_at: datetime,
        known_at: datetime,
    ) -> HumanDecisionTargetSelection | None:
        history = await self.load(root)
        if history is None:
            return None
        try:
            return history.select(effective_at, known_at)
        except HumanDecisionTargetNotKnown, HumanDecisionTargetNeedsReevaluation:
            return None

    async def append(
        self, operation_id: OperationId, draft: HumanDecisionTargetCorrectionDraft
    ) -> HumanDecisionTargetHistory:
        if (
            type(operation_id) is not OperationId
            or type(draft) is not HumanDecisionTargetCorrectionDraft
        ):
            raise TypeError("typed correction command inputs are required")
        try:
            await archive_governance_act_commits(self._engine)
            async with self._engine.begin() as connection:
                await connection.execute(
                    select(func.pg_advisory_xact_lock(_GOVERNANCE_OWNER_LOCK))
                )
                prior = (
                    (
                        await connection.execute(
                            select(human_decision_target_corrections).where(
                                human_decision_target_corrections.c.operation_id
                                == operation_id.value
                            )
                        )
                    )
                    .mappings()
                    .first()
                )
                if prior is not None:
                    if contract_value_from_payload(prior["draft"]) != draft:
                        raise InvalidHumanDecisionTargetHistory(
                            "operation ID has another correction"
                        )
                else:
                    history = await _load(connection, draft.root)
                    if history is None:
                        raise InvalidHumanDecisionTargetHistory(
                            "Human Decision target root is missing"
                        )
                    now = await connection.scalar(select(func.clock_timestamp()))
                    assert isinstance(now, datetime)
                    history.append(draft.at_boundary(now))
                    if draft.replacement is not None:
                        if draft.replacement.made_at > now:
                            raise InvalidHumanDecisionTargetHistory(
                                "corrected act time is later than the store clock"
                            )
                        regime = await _load_regime(
                            connection, draft.replacement.authority_regime_id
                        )
                        require_human_decision_authority(regime, draft.replacement)
                        await _require_recommendation_links(
                            connection, draft.replacement
                        )
                    await connection.execute(
                        insert(human_decision_target_corrections).values(
                            correction_id=draft.correction_id,
                            operation_id=operation_id.value,
                            decision_ref=draft.root.value,
                            sequence=len(history.corrections) + 1,
                            effective_at=draft.effective_at,
                            draft=contract_value_payload(draft),
                        )
                    )
            # duplicate-code: Correction admission reloads its own root history
            # after commit; Intelligence replays a different owner act schema.
            # arid: disable
            await archive_governance_act_commits(self._engine)
            committed = await self.load(draft.root)
            assert committed is not None
            return committed
        except IntegrityError as error:
            # arid: enable
            raise InvalidHumanDecisionTargetHistory(
                "correction identity or sequence already exists"
            ) from error
        except SQLAlchemyError as error:
            raise HumanDecisionStoreUnavailable(
                "Governance correction append failed"
            ) from error
