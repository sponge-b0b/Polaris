from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import cast

from sqlalchemy import Select, SQLColumnExpression, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.dml import Update


async def claim_locked_durable_job[ModelT](
    session: AsyncSession,
    stmt: Select[tuple[ModelT]],
    *,
    update_for: Callable[[ModelT], Update],
    attempt_count_column: SQLColumnExpression[int],
    running_status: str,
    reset_values: Mapping[str, object] | None = None,
) -> ModelT | None:
    """Claim one already-locking durable-job selection as running."""
    try:
        result = await session.execute(stmt)
        model = cast(ModelT | None, result.scalar_one_or_none())
        if model is None:
            return None

        values = dict(reset_values or {})
        values.update(
            status=running_status,
            attempt_count=attempt_count_column + 1,
            started_at=func.now(),
            last_error=None,
            updated_at=func.now(),
        )
        update_result = await session.execute(update_for(model).values(**values))
        updated_model = cast(ModelT, update_result.scalar_one())
        await session.commit()
    except SQLAlchemyError:
        await session.rollback()
        raise

    return updated_model
