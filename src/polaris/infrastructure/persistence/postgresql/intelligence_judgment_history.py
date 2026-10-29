"""Atomic append and reconstruction of Intelligence-owned target acts."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, insert, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Row
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from polaris.application.intelligence_judgment_history import (
    IntelligenceJudgmentHistoryUnavailable,
)
from polaris.domain.evidence.judgments import (
    InvestmentHypothesisRef,
    InvestmentRecommendationRef,
    InvestmentViewRef,
    MeaningfulChallengeResultRef,
    RecommendationWithholdingJudgmentRef,
)
from polaris.domain.intelligence_judgment_history import (
    IntelligenceJudgmentActDraft,
    IntelligenceJudgmentHistory,
    IntelligenceJudgmentRoot,
    InvalidIntelligenceJudgmentHistory,
)

from .intelligence_contract_codec import (
    contract_value_from_payload,
    contract_value_payload,
)
from .runtime_qualification import require_qualified_postgres_runtime
from .schema import (
    investment_intelligence_act_publications,
    investment_intelligence_judgment_acts,
)

INTELLIGENCE_OWNER_LOCK = 6_934_842_191_352_427_103
_SLOT_SETUP_LOCK = 6_934_842_191_352_427_104
_SLOT_ARCHIVE_LOCK = 6_934_842_191_352_427_105
_POSTGRES_EPOCH = datetime(2000, 1, 1, tzinfo=UTC)
INTELLIGENCE_ROOT_TYPES = (
    InvestmentHypothesisRef,
    InvestmentViewRef,
    MeaningfulChallengeResultRef,
    InvestmentRecommendationRef,
    RecommendationWithholdingJudgmentRef,
)


async def ensure_intelligence_commit_slot(engine: AsyncEngine) -> str:
    """Install the durable WAL boundary before admitting an owner act."""
    async with engine.connect() as connection:
        connection = await connection.execution_options(isolation_level="AUTOCOMMIT")
        await connection.execute(select(func.pg_advisory_lock(_SLOT_SETUP_LOCK)))
        try:
            slot = await connection.scalar(
                text(
                    "SELECT 'polaris_ii_' || substr(md5(current_database() || ':' || "
                    "current_schema()), 1, 32)"
                )
            )
            if not isinstance(slot, str):
                raise IntelligenceJudgmentHistoryUnavailable(
                    "Intelligence commit slot identity is unavailable"
                )
            publication = await connection.scalar(
                text("SELECT pubname FROM pg_publication WHERE pubname = :slot"),
                {"slot": slot},
            )
            if publication != slot:
                raise IntelligenceJudgmentHistoryUnavailable(
                    "Intelligence commit publication is unavailable"
                )
            exists = await connection.scalar(
                text("SELECT 1 FROM pg_replication_slots WHERE slot_name = :slot"),
                {"slot": slot},
            )
            if exists is None:
                existing = await connection.scalar(
                    select(investment_intelligence_judgment_acts.c.act_id).limit(1)
                )
                if existing is not None:
                    raise IntelligenceJudgmentHistoryUnavailable(
                        "Intelligence commit slot is missing for existing owner acts"
                    )
                await connection.execute(
                    text(
                        "SELECT slot_name FROM "
                        "pg_create_logical_replication_slot(:slot, 'pgoutput')"
                    ),
                    {"slot": slot},
                )
            row = (
                await connection.execute(
                    text(
                        "SELECT plugin, database, temporary, wal_status, "
                        "invalidation_reason FROM pg_replication_slots "
                        "WHERE slot_name = :slot"
                    ),
                    {"slot": slot},
                )
            ).first()
            database = await connection.scalar(text("SELECT current_database()"))
            if (
                row is None
                or row.plugin != "pgoutput"
                or row.database != database
                or row.temporary
                or row.wal_status not in {"reserved", "extended"}
                or row.invalidation_reason is not None
            ):
                raise IntelligenceJudgmentHistoryUnavailable(
                    "Intelligence commit slot cannot retain owner history"
                )
            return slot
        finally:
            await connection.execute(select(func.pg_advisory_unlock(_SLOT_SETUP_LOCK)))


def _message_act_id(payload: bytes, slot: str) -> UUID | None:
    if len(payload) < 15 or payload[:1] != b"M":
        raise IntelligenceJudgmentHistoryUnavailable("invalid commit message")
    prefix_end = payload.find(b"\0", 10)
    if prefix_end < 0:
        raise IntelligenceJudgmentHistoryUnavailable("commit message prefix is missing")
    if payload[10:prefix_end].decode("utf-8") != slot:
        return None
    if payload[1] != 1 or len(payload) < prefix_end + 5:
        raise IntelligenceJudgmentHistoryUnavailable(
            "commit message is not transactional"
        )
    length = int.from_bytes(payload[prefix_end + 1 : prefix_end + 5], "big")
    content = payload[prefix_end + 5 :]
    if length != len(content):
        raise IntelligenceJudgmentHistoryUnavailable("commit message length differs")
    try:
        return UUID(content.decode("ascii"))
    except (UnicodeDecodeError, ValueError) as error:
        raise IntelligenceJudgmentHistoryUnavailable(
            "commit message has invalid act identity"
        ) from error


def _finish_commit(
    payload: bytes,
    xid: int,
    pending: dict[int, list[UUID]],
    publications: dict[UUID, datetime],
) -> int:
    if len(payload) != 26 or xid not in pending:
        raise IntelligenceJudgmentHistoryUnavailable("invalid WAL commit boundary")
    micros = int.from_bytes(payload[18:26], "big", signed=True)
    committed_at = _POSTGRES_EPOCH + timedelta(microseconds=micros)
    for act_id in pending.pop(xid):
        if act_id in publications:
            raise IntelligenceJudgmentHistoryUnavailable(
                "Intelligence act marker was repeated"
            )
        publications[act_id] = committed_at
    return int.from_bytes(payload[10:18], "big")


def _commit_publications(
    rows: Sequence[Row[Any]], slot: str
) -> tuple[dict[UUID, datetime], int | None]:
    pending: dict[int, list[UUID]] = {}
    publications: dict[UUID, datetime] = {}
    end_lsn: int | None = None
    for _, raw_xid, raw_payload in rows:
        if not isinstance(raw_xid, int) or not isinstance(raw_payload, bytes):
            raise IntelligenceJudgmentHistoryUnavailable("invalid WAL decoding row")
        kind = raw_payload[:1]
        if kind == b"B":
            pending[raw_xid] = []
        elif kind == b"M":
            act_id = _message_act_id(raw_payload, slot)
            if act_id is not None:
                if raw_xid not in pending:
                    raise IntelligenceJudgmentHistoryUnavailable(
                        "Intelligence act marker has no transaction"
                    )
                pending[raw_xid].append(act_id)
        elif kind == b"C":
            end_lsn = _finish_commit(raw_payload, raw_xid, pending, publications)
    if pending:
        raise IntelligenceJudgmentHistoryUnavailable(
            "WAL decoding ended inside a transaction"
        )
    return publications, end_lsn


def _root_identity(root: IntelligenceJudgmentRoot) -> tuple[str, UUID]:
    if type(root) not in INTELLIGENCE_ROOT_TYPES:
        raise TypeError("root must be an Investment Intelligence Evidence target")
    return type(root).__name__, root.value


def _act_values(
    draft: IntelligenceJudgmentActDraft,
    sequence: int,
    history: IntelligenceJudgmentHistory,
) -> dict[str, object]:
    family, root_id = _root_identity(draft.root)
    assertion = history.acts[0].assertion
    if assertion is None:
        raise InvalidIntelligenceJudgmentHistory("initial assertion is missing")
    return {
        "act_id": draft.act_id,
        "target_family": family,
        "target_id": root_id,
        "decision_id": assertion.decision_id.value,
        "sequence": sequence,
        "effective_at": draft.effective_at,
        "draft": contract_value_payload(draft),
    }


async def _load(
    connection: AsyncConnection, root: IntelligenceJudgmentRoot
) -> IntelligenceJudgmentHistory | None:
    family, root_id = _root_identity(root)
    # duplicate-code: Sharing would couple distinct owner schemas.
    # arid: disable
    rows = (
        (
            await connection.execute(
                select(
                    investment_intelligence_judgment_acts,
                    investment_intelligence_act_publications.c.committed_at.label(
                        "trusted_commit_at"
                    ),
                )
                .outerjoin(
                    investment_intelligence_act_publications,
                    investment_intelligence_act_publications.c.act_id
                    == investment_intelligence_judgment_acts.c.act_id,
                )
                .where(
                    investment_intelligence_judgment_acts.c.target_family == family,
                    investment_intelligence_judgment_acts.c.target_id == root_id,
                )
                .order_by(investment_intelligence_judgment_acts.c.sequence)
            )
        )
        .mappings()
        .all()
    )
    if not rows:
        return None
    # arid: enable
    history: IntelligenceJudgmentHistory | None = None
    for expected_sequence, row in enumerate(rows, start=1):
        draft = contract_value_from_payload(row["draft"])
        committed_at = row["trusted_commit_at"]
        if not isinstance(draft, IntelligenceJudgmentActDraft) or draft.root != root:
            raise InvalidIntelligenceJudgmentHistory(
                "stored draft has wrong typed root"
            )
        if not isinstance(committed_at, datetime):
            raise IntelligenceJudgmentHistoryUnavailable(
                "owner act commit timestamp is unavailable"
            )
        act = draft.at_boundary(committed_at)
        if (
            row["act_id"] != act.act_id
            or row["sequence"] != expected_sequence
            or row["effective_at"] != act.effective_at
        ):
            raise InvalidIntelligenceJudgmentHistory("stored draft metadata differs")
        history = (
            IntelligenceJudgmentHistory.form(act)
            if history is None
            else history.append(act)
        )
        initial = history.acts[0].assertion
        if initial is None or row["decision_id"] != initial.decision_id.value:
            raise InvalidIntelligenceJudgmentHistory("stored Decision identity differs")
    return history


async def _load_with_recovery(
    engine: AsyncEngine,
    connection: AsyncConnection,
    root: IntelligenceJudgmentRoot,
) -> IntelligenceJudgmentHistory | None:
    try:
        return await _load(connection, root)
    except IntelligenceJudgmentHistoryUnavailable:
        await archive_intelligence_act_commits(engine)
        return await _load(connection, root)


async def insert_initial_intelligence_act(
    connection: AsyncConnection, draft: IntelligenceJudgmentActDraft
) -> IntelligenceJudgmentHistory:
    """Join the initial target and complete catalog to the forming write."""
    now = await connection.scalar(select(func.clock_timestamp()))
    assert isinstance(now, datetime)
    history = IntelligenceJudgmentHistory.form(draft.at_boundary(now))
    await connection.execute(
        insert(investment_intelligence_judgment_acts).values(
            _act_values(draft, 1, history)
        )
    )
    return history


async def archive_intelligence_act_commits(engine: AsyncEngine) -> None:
    """Archive commit boundaries before advancing their durable WAL slot."""
    slot = await ensure_intelligence_commit_slot(engine)
    async with engine.connect() as connection:
        connection = await connection.execution_options(isolation_level="AUTOCOMMIT")
        await connection.execute(select(func.pg_advisory_lock(_SLOT_ARCHIVE_LOCK)))
        try:
            rows = (
                await connection.execute(
                    text(
                        "SELECT lsn, xid, data FROM "
                        "pg_logical_slot_peek_binary_changes("
                        ":slot, NULL, NULL, 'proto_version', '1', "
                        "'publication_names', :publication, "
                        "'messages', 'true')"
                    ),
                    {"slot": slot, "publication": slot},
                )
            ).all()
            publications, end_lsn = _commit_publications(rows, slot)
            for act_id, committed_at in publications.items():
                existing_act = await connection.scalar(
                    select(investment_intelligence_judgment_acts.c.act_id).where(
                        investment_intelligence_judgment_acts.c.act_id == act_id
                    )
                )
                if existing_act is None:
                    raise IntelligenceJudgmentHistoryUnavailable(
                        "WAL marker has no committed Intelligence act"
                    )
                await connection.execute(
                    pg_insert(investment_intelligence_act_publications)
                    .values(act_id=act_id, committed_at=committed_at)
                    .on_conflict_do_nothing(
                        index_elements=[
                            investment_intelligence_act_publications.c.act_id
                        ]
                    )
                )
                archived_at = await connection.scalar(
                    select(
                        investment_intelligence_act_publications.c.committed_at
                    ).where(investment_intelligence_act_publications.c.act_id == act_id)
                )
                if archived_at != committed_at:
                    raise IntelligenceJudgmentHistoryUnavailable(
                        "archived Intelligence commit boundary differs from WAL"
                    )
            if end_lsn is not None:
                await connection.execute(
                    text(
                        "SELECT end_lsn FROM pg_replication_slot_advance("
                        ":slot, CAST(:end_lsn AS pg_lsn))"
                    ),
                    {"slot": slot, "end_lsn": end_lsn},
                )
        finally:
            await connection.execute(
                select(func.pg_advisory_unlock(_SLOT_ARCHIVE_LOCK))
            )


@asynccontextmanager
async def intelligence_owner_write(
    engine: AsyncEngine,
) -> AsyncIterator[AsyncConnection]:
    """Recover prior commits before locking the owner for a new transaction."""
    await archive_intelligence_act_commits(engine)
    async with engine.begin() as connection:
        await connection.execute(
            select(func.pg_advisory_xact_lock(INTELLIGENCE_OWNER_LOCK))
        )
        yield connection


class PostgresIntelligenceJudgmentHistoryStore:
    """Revalidate same-root correction history under the owner write lock."""

    def __init__(
        self,
        engine: AsyncEngine,
        *,
        validation_connection: AsyncConnection | None = None,
    ) -> None:
        require_qualified_postgres_runtime()
        # duplicate-code: Sharing would couple distinct owner schemas.
        # arid: disable
        if (
            validation_connection is not None
            and validation_connection.engine is not engine
        ):
            raise ValueError("validation connection must use the owner engine")
        # arid: enable
        self._engine = engine
        self._validation_connection = validation_connection

    # duplicate-code: Sharing would couple distinct owner schemas.
    # arid: disable
    def for_validation(
        self, connection: AsyncConnection
    ) -> PostgresIntelligenceJudgmentHistoryStore:
        if not connection.in_transaction():
            raise ValueError("owner validation requires an open write transaction")
        return PostgresIntelligenceJudgmentHistoryStore(
            self._engine, validation_connection=connection
        )

    async def load(
        self, root: IntelligenceJudgmentRoot
    ) -> IntelligenceJudgmentHistory | None:
        if self._validation_connection is not None:
            connection = self._validation_connection
            if not connection.in_transaction():
                raise IntelligenceJudgmentHistoryUnavailable(
                    "owner validation transaction is closed"
                )
            try:
                await connection.execute(
                    select(investment_intelligence_judgment_acts.c.act_id)
                    .where(
                        investment_intelligence_judgment_acts.c.target_family
                        == type(root).__name__,
                        investment_intelligence_judgment_acts.c.target_id == root.value,
                    )
                    .with_for_update(read=True)
                )
                return await _load_with_recovery(self._engine, connection, root)
            except SQLAlchemyError as error:
                raise IntelligenceJudgmentHistoryUnavailable(
                    "owner history validation read failed"
                ) from error
        try:
            async with self._engine.connect() as connection:
                return await _load_with_recovery(self._engine, connection, root)
        except SQLAlchemyError as error:
            raise IntelligenceJudgmentHistoryUnavailable(
                "owner history read failed"
            ) from error

    # arid: enable

    async def append(
        self, draft: IntelligenceJudgmentActDraft
    ) -> IntelligenceJudgmentHistory:
        if self._validation_connection is not None:
            raise ValueError("validation reader cannot append owner acts")
        if type(draft) is not IntelligenceJudgmentActDraft:
            raise TypeError("correction must be a typed owner draft")
        try:
            async with intelligence_owner_write(self._engine) as connection:
                history = await _load(connection, draft.root)
                if history is None:
                    raise InvalidIntelligenceJudgmentHistory("target root is missing")
                existing = next(
                    (item for item in history.acts if item.act_id == draft.act_id),
                    None,
                )
                if existing is not None:
                    if draft.at_boundary(existing.known_at) != existing:
                        raise InvalidIntelligenceJudgmentHistory(
                            "act reference was used for another correction"
                        )
                else:
                    now = await connection.scalar(select(func.clock_timestamp()))
                    assert isinstance(now, datetime)
                    updated = history.append(draft.at_boundary(now))
                    await connection.execute(
                        insert(investment_intelligence_judgment_acts).values(
                            _act_values(draft, len(updated.acts), updated)
                        )
                    )
            await archive_intelligence_act_commits(self._engine)
            committed = await self.load(draft.root)
            assert committed is not None
            return committed
        except IntegrityError as error:
            raise InvalidIntelligenceJudgmentHistory(
                "owner act identity or sequence already exists"
            ) from error
        except SQLAlchemyError as error:
            raise IntelligenceJudgmentHistoryUnavailable(
                "owner correction append failed"
            ) from error
