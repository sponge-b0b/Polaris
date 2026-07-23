from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

from core.storage.persistence.lineage import (
    JsonObject,
    JsonValue,
    PersistenceLineage,
    PersistenceRecordIdentity,
    clean_optional_identifier,
    require_non_empty_identifier,
)


@dataclass(
    frozen=True,
    slots=True,
)
class PersistenceAuditActor:
    """
    Actor or system source responsible for a persistence audit event.
    """

    system_source: str
    actor_id: str | None = None
    actor_type: str | None = None

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "system_source",
            require_non_empty_identifier(
                self.system_source,
                "system_source",
            ),
        )
        object.__setattr__(
            self,
            "actor_id",
            clean_optional_identifier(
                self.actor_id,
                "actor_id",
            ),
        )
        object.__setattr__(
            self,
            "actor_type",
            clean_optional_identifier(
                self.actor_type,
                "actor_type",
            ),
        )

    def as_dict(
        self,
    ) -> dict[str, str]:
        result = {
            "system_source": self.system_source,
        }
        if self.actor_id is not None:
            result["actor_id"] = self.actor_id
        if self.actor_type is not None:
            result["actor_type"] = self.actor_type
        return result


@dataclass(
    frozen=True,
    slots=True,
)
class PersistenceAuditEventRecord:
    """
    Append-only audit event contract for persisted platform records.

    The event records who or what changed a persisted entity and carries
    workflow/runtime lineage when available. It is a persistence-boundary DTO;
    domain layers should continue to use strongly typed domain objects.
    """

    entity_type: str
    entity_id: str
    action: str
    timestamp: datetime
    actor: PersistenceAuditActor
    audit_event_id: str = field(default_factory=lambda: uuid4().hex)
    lineage: PersistenceLineage = field(default_factory=PersistenceLineage)
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "audit_event_id",
            require_non_empty_identifier(
                self.audit_event_id,
                "audit_event_id",
            ),
        )
        object.__setattr__(
            self,
            "entity_type",
            require_non_empty_identifier(
                self.entity_type,
                "entity_type",
            ),
        )
        object.__setattr__(
            self,
            "entity_id",
            require_non_empty_identifier(
                self.entity_id,
                "entity_id",
            ),
        )
        object.__setattr__(
            self,
            "action",
            require_non_empty_identifier(
                self.action,
                "action",
            ),
        )
        object.__setattr__(
            self,
            "metadata",
            dict(
                self.metadata,
            ),
        )

    @property
    def entity(
        self,
    ) -> PersistenceRecordIdentity:
        return PersistenceRecordIdentity(
            record_type=self.entity_type,
            record_id=self.entity_id,
        )

    @property
    def system_source(
        self,
    ) -> str:
        return self.actor.system_source

    @property
    def actor_id(
        self,
    ) -> str | None:
        return self.actor.actor_id

    @property
    def actor_type(
        self,
    ) -> str | None:
        return self.actor.actor_type

    def as_dict(
        self,
    ) -> dict[str, JsonValue]:
        return {
            "audit_event_id": self.audit_event_id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "action": self.action,
            "timestamp": self.timestamp.isoformat(),
            "actor": self.actor.as_dict(),
            "lineage": self.lineage.as_dict(),
            "metadata": self.metadata,
        }


@dataclass(
    frozen=True,
    slots=True,
)
class PersistenceAuditEventResult:
    """
    Typed result returned by persistence audit write adapters.
    """

    success: bool
    audit_event_id: str | None = None
    records_persisted: int = 0
    error: str | None = None

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "audit_event_id",
            clean_optional_identifier(
                self.audit_event_id,
                "audit_event_id",
            ),
        )
        if self.records_persisted < 0:
            raise ValueError("records_persisted must be non-negative.")
        if self.success and self.audit_event_id is None:
            raise ValueError("audit_event_id is required when success is true.")
        if not self.success and self.error is None:
            raise ValueError("error is required when success is false.")

    @classmethod
    def succeeded(
        cls,
        *,
        audit_event_id: str,
    ) -> PersistenceAuditEventResult:
        return cls(
            success=True,
            audit_event_id=audit_event_id,
            records_persisted=1,
        )

    @classmethod
    def failed(
        cls,
        error: str,
    ) -> PersistenceAuditEventResult:
        return cls(
            success=False,
            error=error,
        )


def new_persistence_audit_event_id() -> str:
    """
    Build a unique audit event id for append-only persistence audit records.
    """

    return f"persistence_audit_event:{uuid4().hex}"
