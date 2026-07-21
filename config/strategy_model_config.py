from __future__ import annotations

from dataclasses import dataclass

from config.settings import (
    DEFAULT_STRATEGY_PERSPECTIVE_REASONING_MODEL,
    DEFAULT_STRATEGY_SYNTHESIS_MODEL,
    Settings,
)


@dataclass(frozen=True, slots=True)
class StrategyModelConfig:
    """Logical model aliases for strategy AI reasoning and synthesis lanes."""

    perspective_reasoning_model: str = DEFAULT_STRATEGY_PERSPECTIVE_REASONING_MODEL
    synthesis_model: str = DEFAULT_STRATEGY_SYNTHESIS_MODEL

    def __post_init__(self) -> None:
        for field_name in self.__dataclass_fields__:
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} cannot be empty.")
            object.__setattr__(self, field_name, value.strip())

    @classmethod
    def from_settings(cls, settings: Settings) -> StrategyModelConfig:
        return cls(
            perspective_reasoning_model=settings.STRATEGY_PERSPECTIVE_REASONING_MODEL,
            synthesis_model=settings.STRATEGY_SYNTHESIS_MODEL,
        )
