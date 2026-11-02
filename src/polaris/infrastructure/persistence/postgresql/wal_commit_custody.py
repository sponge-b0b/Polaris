"""Shared PostgreSQL commit custody for owner-specific logical publications."""

from __future__ import annotations

from collections.abc import AsyncIterator, Mapping, Sequence
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import Table, func, select, text
from sqlalchemy.engine import Row
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

_POSTGRES_EPOCH = datetime(2000, 1, 1, tzinfo=UTC)


async def ensure_commit_slot(
    engine: AsyncEngine,
    *,
    prefix: str,
    setup_lock: int,
    owner_acts: Table,
    error_type: type[Exception],
) -> str:
    """Establish durable custody before an owner writes its first act."""
    async with engine.connect() as connection:
        connection = await connection.execution_options(isolation_level="AUTOCOMMIT")
        await connection.execute(select(func.pg_advisory_lock(setup_lock)))
        try:
            slot = await connection.scalar(
                text(
                    "SELECT :prefix || substr(md5(current_database() || ':' || "
                    "current_schema()), 1, 32)"
                ),
                {"prefix": prefix},
            )
            if not isinstance(slot, str):
                raise error_type("commit slot identity is unavailable")
            publication = await connection.scalar(
                text("SELECT pubname FROM pg_publication WHERE pubname = :slot"),
                {"slot": slot},
            )
            if publication != slot:
                raise error_type("commit publication is unavailable")
            exists = await connection.scalar(
                text("SELECT 1 FROM pg_replication_slots WHERE slot_name = :slot"),
                {"slot": slot},
            )
            if exists is None:
                existing = await connection.scalar(select(owner_acts.c[0]).limit(1))
                if existing is not None:
                    raise error_type("commit slot is missing for existing owner acts")
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
                raise error_type("commit slot cannot retain owner history")
            return slot
        finally:
            await connection.execute(select(func.pg_advisory_unlock(setup_lock)))


def transactional_message(
    payload: bytes, slot: str, error_type: type[Exception]
) -> bytes | None:
    """Decode one transactional pgoutput message for a named owner slot."""
    if len(payload) < 15 or payload[:1] != b"M":
        raise error_type("invalid commit message")
    prefix_end = payload.find(b"\0", 10)
    if prefix_end < 0:
        raise error_type("commit message prefix is missing")
    if payload[10:prefix_end].decode("utf-8") != slot:
        return None
    if payload[1] != 1 or len(payload) < prefix_end + 5:
        raise error_type("commit message is not transactional")
    length = int.from_bytes(payload[prefix_end + 1 : prefix_end + 5], "big")
    content = payload[prefix_end + 5 :]
    if length != len(content):
        raise error_type("commit message length differs")
    return content


def commit_boundary(
    payload: bytes, xid: int, pending: Mapping[int, object], error_type: type[Exception]
) -> tuple[datetime, int]:
    """Read the server commit timestamp and end LSN of a complete transaction."""
    if len(payload) != 26 or xid not in pending:
        raise error_type("invalid WAL commit boundary")
    micros = int.from_bytes(payload[18:26], "big", signed=True)
    committed_at = _POSTGRES_EPOCH + timedelta(microseconds=micros)
    return committed_at, int.from_bytes(payload[10:18], "big")


async def peek_commit_rows(
    connection: AsyncConnection, slot: str
) -> Sequence[Row[Any]]:
    """Inspect committed owner messages without consuming their durable slot."""
    return list(
        (
            await connection.execute(
                text(
                    "SELECT lsn, xid, data FROM "
                    "pg_logical_slot_peek_binary_changes("
                    ":slot, NULL, NULL, 'proto_version', '1', "
                    "'publication_names', :publication, 'messages', 'true')"
                ),
                {"slot": slot, "publication": slot},
            )
        ).all()
    )


async def advance_commit_slot(
    connection: AsyncConnection, slot: str, end_lsn: int | None
) -> None:
    if end_lsn is not None:
        await connection.execute(
            text(
                "SELECT end_lsn FROM pg_replication_slot_advance("
                ":slot, CAST(:end_lsn AS pg_lsn))"
            ),
            {"slot": slot, "end_lsn": end_lsn},
        )


@asynccontextmanager
async def owner_archive_connection(
    engine: AsyncEngine, archive_lock: int
) -> AsyncIterator[AsyncConnection]:
    """Serialize WAL archival while keeping slot operations in autocommit."""
    async with engine.connect() as connection:
        connection = await connection.execution_options(isolation_level="AUTOCOMMIT")
        await connection.execute(select(func.pg_advisory_lock(archive_lock)))
        try:
            yield connection
        finally:
            await connection.execute(select(func.pg_advisory_unlock(archive_lock)))
