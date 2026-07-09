from __future__ import annotations

import asyncio

from collections.abc import Coroutine
from typing import Any
from typing import TypeVar


ResultT = TypeVar(
    "ResultT",
)


def run_cli_async(
    awaitable: Coroutine[Any, Any, ResultT],
) -> ResultT:
    """
    Execute an async CLI command service from the synchronous Typer boundary.
    """

    return asyncio.run(
        awaitable,
    )
