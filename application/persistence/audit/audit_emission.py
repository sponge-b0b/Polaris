from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from typing import Protocol

from core.storage.persistence.audit import PersistenceAuditActor
from core.storage.persistence.audit import PersistenceAuditEventRecord
from core.storage.persistence.audit import PersistenceAuditEventResult
from core.storage.persistence.lineage import JsonObject
from core.storage.persistence.lineage import PersistenceLineage
from core.storage.persistence.lineage import require_non_empty_identifier

from application.persistence.audit.audit_persistence_service import (
    AuditPersistenceService,
)


@dataclass(
    frozen=True,
    slots=True,
)
class PersistenceAuditEmission:
    """
    Application-service request to emit a persistence audit event.

    This helper is intentionally application-layer only: persistence services can
    describe the safe audit event they want to emit while the runtime remains
    untouched and audit storage failures remain outside the primary write path.
    """

    entity_type: str
    entity_id: str
    action: str
    timestamp: datetime
    lineage: PersistenceLineage = field(default_factory=PersistenceLineage)
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
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

    def to_event(
        self,
        actor: PersistenceAuditActor,
    ) -> PersistenceAuditEventRecord:
        return PersistenceAuditEventRecord(
            entity_type=self.entity_type,
            entity_id=self.entity_id,
            action=self.action,
            timestamp=self.timestamp,
            actor=actor,
            lineage=self.lineage,
            metadata=self.metadata,
        )


class PersistenceAuditEmitter(Protocol):
    """
    Protocol for optional non-fatal persistence audit emitters.
    """

    async def emit(
        self,
        emission: PersistenceAuditEmission,
    ) -> PersistenceAuditEventResult | None: ...

    async def emit_many(
        self,
        emissions: Sequence[PersistenceAuditEmission],
    ) -> Sequence[PersistenceAuditEventResult | None]: ...


class NonFatalPersistenceAuditEmitter:
    """
    Emits persistence audit events without making audit storage part of the
    primary service success path.
    """

    def __init__(
        self,
        audit_service: AuditPersistenceService | None,
        actor: PersistenceAuditActor,
        *,
        enabled: bool = True,
    ) -> None:
        self._audit_service = audit_service
        self._actor = actor
        self._enabled = enabled

    async def emit(
        self,
        emission: PersistenceAuditEmission,
    ) -> PersistenceAuditEventResult | None:
        if not self._enabled or self._audit_service is None:
            return None

        try:
            return await self._audit_service.persist_audit_event(
                emission.to_event(
                    self._actor,
                )
            )
        except Exception as exc:
            return PersistenceAuditEventResult.failed(
                _error_message(
                    exc,
                )
            )

    async def emit_many(
        self,
        emissions: Sequence[PersistenceAuditEmission],
    ) -> Sequence[PersistenceAuditEventResult | None]:
        results: list[PersistenceAuditEventResult | None] = []
        for emission in emissions:
            results.append(
                await self.emit(
                    emission,
                )
            )
        return tuple(
            results,
        )


async def emit_persistence_audit_events_non_fatal(
    audit_emitter: PersistenceAuditEmitter | None,
    emissions: Sequence[PersistenceAuditEmission],
) -> None:
    """
    Best-effort service-boundary audit emission.

    Application persistence services use this helper after their primary write
    succeeds. It intentionally swallows emitter exceptions so an optional audit
    path cannot flip a successful business persistence operation into failure.
    """

    if audit_emitter is None or not emissions:
        return

    try:
        await audit_emitter.emit_many(
            emissions,
        )
    except Exception:
        return


def _error_message(
    exc: Exception,
) -> str:
    message = str(
        exc,
    ).strip()
    if message:
        return message
    return exc.__class__.__name__
