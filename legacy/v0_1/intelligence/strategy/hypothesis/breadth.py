from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from intelligence.analysts.technical.technical_breadth_context import (
    TechnicalBreadthContext,
)


@dataclass(frozen=True, slots=True)
class BreadthMessageRule:
    condition: Callable[[TechnicalBreadthContext], bool]
    message: str


def breadth_messages(
    breadth_context: TechnicalBreadthContext,
    rules: tuple[BreadthMessageRule, ...],
    *,
    include_regime: bool = False,
) -> tuple[str, ...]:
    """Build deterministic breadth messages from perspective-specific rules."""

    if not breadth_context.has_breadth_data:
        return ()

    messages: list[str] = []
    if include_regime:
        messages.append(f"breadth:{breadth_context.breadth_regime}")

    for rule in rules:
        if rule.condition(breadth_context):
            messages.append(rule.message)
    return tuple(messages)
