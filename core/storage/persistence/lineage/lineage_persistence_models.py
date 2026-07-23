from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

type JsonScalar = str | int | float | bool | None
type JsonValue = JsonScalar | Mapping[str, "JsonValue"] | Sequence["JsonValue"]
type JsonObject = Mapping[str, JsonValue]


@dataclass(
    frozen=True,
    slots=True,
)
class PersistenceLineage:
    """
    Shared workflow/runtime lineage for persistence-boundary records.

    This is intentionally a storage contract helper, not a replacement for
    runtime-core context models. Domain layers should carry typed objects and
    attach lineage only when crossing into durable persistence.
    """

    workflow_name: str | None = None
    execution_id: str | None = None
    runtime_id: str | None = None
    node_name: str | None = None

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "workflow_name",
            clean_optional_identifier(
                self.workflow_name,
                "workflow_name",
            ),
        )
        object.__setattr__(
            self,
            "execution_id",
            clean_optional_identifier(
                self.execution_id,
                "execution_id",
            ),
        )
        object.__setattr__(
            self,
            "runtime_id",
            clean_optional_identifier(
                self.runtime_id,
                "runtime_id",
            ),
        )
        object.__setattr__(
            self,
            "node_name",
            clean_optional_identifier(
                self.node_name,
                "node_name",
            ),
        )

    def as_dict(
        self,
    ) -> dict[str, str]:
        """
        Serialize non-empty lineage fields at persistence/telemetry boundaries.
        """

        return _omit_none(
            {
                "workflow_name": self.workflow_name,
                "execution_id": self.execution_id,
                "runtime_id": self.runtime_id,
                "node_name": self.node_name,
            }
        )


@dataclass(
    frozen=True,
    slots=True,
)
class PersistenceSourceReference:
    """
    Canonical source pointer for records derived from persisted platform data.
    """

    source_type: str
    source_id: str
    source_table: str | None = None

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "source_type",
            require_non_empty_identifier(
                self.source_type,
                "source_type",
            ),
        )
        object.__setattr__(
            self,
            "source_id",
            require_non_empty_identifier(
                self.source_id,
                "source_id",
            ),
        )
        object.__setattr__(
            self,
            "source_table",
            clean_optional_identifier(
                self.source_table,
                "source_table",
            ),
        )

    def as_dict(
        self,
    ) -> dict[str, str]:
        """
        Serialize source reference fields at persistence/telemetry boundaries.
        """

        return _omit_none(
            {
                "source_type": self.source_type,
                "source_id": self.source_id,
                "source_table": self.source_table,
            }
        )


@dataclass(
    frozen=True,
    slots=True,
)
class PersistenceRecordIdentity:
    """
    Stable identity for a persisted platform record.
    """

    record_type: str
    record_id: str

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
            "record_id",
            require_non_empty_identifier(
                self.record_id,
                "record_id",
            ),
        )

    def as_dict(
        self,
    ) -> dict[str, str]:
        """
        Serialize identity fields at persistence/telemetry boundaries.
        """

        return {
            "record_type": self.record_type,
            "record_id": self.record_id,
        }


@dataclass(
    frozen=True,
    slots=True,
)
class PersistenceRecordContext:
    """
    Reusable persistence-boundary context for curated platform records.
    """

    identity: PersistenceRecordIdentity
    lineage: PersistenceLineage = field(default_factory=PersistenceLineage)
    source: PersistenceSourceReference | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(
        self,
    ) -> None:
        require_timestamp_order(
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


@dataclass(
    frozen=True,
    slots=True,
)
class PersistenceLineageLinkRecord:
    """
    Generic cross-record link for auditability and future curated RAG lineage.

    Examples include report -> recommendation, recommendation -> signal, and
    signal -> workflow execution. The endpoints are generic persisted-record
    identities so this foundation can serve domains added later in V2 without
    coupling to those domain tables.
    """

    link_id: str
    source_record: PersistenceRecordIdentity
    target_record: PersistenceRecordIdentity
    relationship_type: str
    created_at: datetime
    lineage: PersistenceLineage = field(default_factory=PersistenceLineage)
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "link_id",
            require_non_empty_identifier(
                self.link_id,
                "link_id",
            ),
        )
        object.__setattr__(
            self,
            "relationship_type",
            require_non_empty_identifier(
                self.relationship_type,
                "relationship_type",
            ),
        )

        if self.source_record == self.target_record:
            raise ValueError("lineage links cannot target the same record identity.")


@dataclass(
    frozen=True,
    slots=True,
)
class PersistenceLineageLinkResult:
    """
    Typed result returned by lineage link persistence adapters.
    """

    success: bool
    records_persisted: int = 0
    link_id: str | None = None
    error: str | None = None

    def __post_init__(
        self,
    ) -> None:
        _require_non_negative(
            self.records_persisted,
            "records_persisted",
        )

        if self.success and self.error is not None:
            raise ValueError("successful persistence results cannot include an error.")

        if self.success:
            require_non_empty_identifier(
                self.link_id,
                "link_id",
            )

        if not self.success:
            require_non_empty_identifier(
                self.error,
                "error",
            )

    @classmethod
    def succeeded(
        cls,
        *,
        link_id: str,
        records_persisted: int = 1,
    ) -> PersistenceLineageLinkResult:
        return cls(
            success=True,
            records_persisted=records_persisted,
            link_id=link_id,
        )

    @classmethod
    def failed(
        cls,
        error: str,
    ) -> PersistenceLineageLinkResult:
        return cls(
            success=False,
            records_persisted=0,
            error=error,
        )


def build_source_reference(
    *,
    source_type: str,
    source_id: str,
    source_table: str | None = None,
) -> PersistenceSourceReference:
    """
    Construct a validated source pointer for persistence-boundary records.
    """

    return PersistenceSourceReference(
        source_type=source_type,
        source_id=source_id,
        source_table=source_table,
    )


def new_persistence_lineage_link_id(
    *,
    source_record: PersistenceRecordIdentity,
    target_record: PersistenceRecordIdentity,
    relationship_type: str,
) -> str:
    """
    Build a deterministic lineage-link id from normalized link endpoints.
    """

    relationship = require_non_empty_identifier(
        relationship_type,
        "relationship_type",
    )
    return (
        "persistence_lineage_link:"
        f"{source_record.record_type}:{source_record.record_id}:"
        f"{relationship}:"
        f"{target_record.record_type}:{target_record.record_id}"
    )


def new_random_persistence_lineage_link_id() -> str:
    """
    Build a unique lineage-link id when no stable natural key is available.
    """

    return f"persistence_lineage_link:{uuid4().hex}"


def clean_optional_identifier(
    value: str | None,
    field_name: str,
) -> str | None:
    """
    Normalize optional identifiers by trimming blanks to ``None``.
    """

    if value is None:
        return None

    stripped = value.strip()
    if not stripped:
        return None

    return stripped


def require_non_empty_identifier(
    value: str | None,
    field_name: str,
) -> str:
    """
    Normalize and require an identifier that is not empty after trimming.
    """

    if value is None:
        raise ValueError(f"{field_name} cannot be empty.")

    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{field_name} cannot be empty.")

    return stripped


def require_timestamp_order(
    *,
    created_at: datetime | None,
    updated_at: datetime | None,
) -> None:
    """
    Validate persistence timestamps when both creation and update are present.
    """

    if created_at is None or updated_at is None:
        return

    if updated_at < created_at:
        raise ValueError("updated_at cannot be earlier than created_at.")


def _omit_none(
    values: dict[str, str | None],
) -> dict[str, str]:
    return {key: value for key, value in values.items() if value is not None}


def _require_non_negative(
    value: int,
    field_name: str,
) -> None:
    if value < 0:
        raise ValueError(f"{field_name} cannot be negative.")
