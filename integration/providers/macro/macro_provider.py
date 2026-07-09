from __future__ import annotations

from typing import Protocol, runtime_checkable

from domain.macro.models import MacroDataSnapshot


@runtime_checkable
class MacroProvider(Protocol):
    """Canonical platform-facing macro provider contract."""

    async def get_macro_snapshot(self) -> MacroDataSnapshot: ...
