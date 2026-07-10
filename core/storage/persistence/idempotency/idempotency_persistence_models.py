from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TypeAlias

from core.storage.persistence.lineage import JsonObject
from core.storage.persistence.lineage import clean_optional_identifier
from core.storage.persistence.lineage import require_non_empty_identifier

IdempotencyComponent: TypeAlias = str | int | float | bool | datetime


@dataclass(
    frozen=True,
    slots=True,
)
class PersistenceIdempotencyKey:
    """
    Typed stable key contract for idempotent persistence writes.

    Domain-specific ID helpers remain the preferred public APIs for known
    records. This shared contract closes the V3 gap for new persistence domains
    by providing one canonical way to assemble deterministic keys from natural
    source/timestamp/entity components without falling back to ad hoc strings.
    """

    record_type: str
    components: tuple[str, ...]
    namespace: str | None = None
    version: str | None = None

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "record_type",
            require_non_empty_identifier(
                self.record_type,
                "record_type",
            ),
        )
        object.__setattr__(
            self,
            "namespace",
            clean_optional_identifier(
                self.namespace,
                "namespace",
            ),
        )
        object.__setattr__(
            self,
            "version",
            clean_optional_identifier(
                self.version,
                "version",
            ),
        )
        object.__setattr__(
            self,
            "components",
            tuple(
                require_non_empty_identifier(
                    component,
                    "idempotency_component",
                )
                for component in self.components
            ),
        )
        if not self.components:
            raise ValueError("at least one idempotency component is required.")

    @property
    def key(
        self,
    ) -> str:
        parts = []
        if self.namespace is not None:
            parts.append(
                self.namespace,
            )
        if self.version is not None:
            parts.append(
                self.version,
            )
        parts.extend(
            (
                self.record_type,
                *self.components,
            )
        )
        return ":".join(
            parts,
        )

    def as_dict(
        self,
    ) -> JsonObject:
        result: dict[str, str | tuple[str, ...]] = {
            "record_type": self.record_type,
            "components": self.components,
            "key": self.key,
        }
        if self.namespace is not None:
            result["namespace"] = self.namespace
        if self.version is not None:
            result["version"] = self.version
        return result

    def __str__(
        self,
    ) -> str:
        return self.key


def build_persistence_idempotency_key(
    *,
    record_type: str,
    components: tuple[IdempotencyComponent, ...],
    optional_components: tuple[IdempotencyComponent | None, ...] = (),
    namespace: str | None = None,
    version: str | None = None,
) -> PersistenceIdempotencyKey:
    """
    Build a stable key from required and optional natural-key components.

    Required components must be present and non-blank. Optional ``None`` values
    are omitted so callers can include optional source references without
    producing unstable placeholder segments.
    """

    normalized_components: list[str] = []
    for component in components:
        key_part = _component_to_key_part(
            component,
            allow_none=False,
        )
        if key_part is None:
            raise ValueError("idempotency component cannot be None.")
        normalized_components.append(
            key_part,
        )
    for optional_component in optional_components:
        key_part = _component_to_key_part(
            optional_component,
            allow_none=True,
        )
        if key_part is not None:
            normalized_components.append(
                key_part,
            )
    return PersistenceIdempotencyKey(
        record_type=record_type,
        components=tuple(
            normalized_components,
        ),
        namespace=namespace,
        version=version,
    )


def symbol_idempotency_component(
    symbol: str | None,
) -> str | None:
    """
    Normalize an optional symbol for use in stable persistence keys.
    """

    clean_symbol = clean_optional_identifier(
        symbol,
        "symbol",
    )
    if clean_symbol is None:
        return None
    return clean_symbol.upper()


def timestamp_idempotency_component(
    timestamp: datetime,
) -> str:
    """
    Normalize timestamps through ISO-8601 for deterministic key segments.
    """

    return timestamp.isoformat()


def _component_to_key_part(
    component: IdempotencyComponent | None,
    *,
    allow_none: bool,
) -> str | None:
    if component is None:
        if allow_none:
            return None
        raise ValueError("idempotency component cannot be None.")

    if isinstance(
        component,
        datetime,
    ):
        return timestamp_idempotency_component(
            component,
        )

    if isinstance(
        component,
        bool,
    ):
        return str(
            component,
        ).lower()

    return require_non_empty_identifier(
        str(
            component,
        ),
        "idempotency_component",
    )
