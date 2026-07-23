from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

import pytest

from application.persistence.audit.audit_emission import (
    NonFatalPersistenceAuditEmitter,
    PersistenceAuditEmission,
)
from application.persistence.audit.audit_persistence_service import (
    AuditPersistenceService,
)
from core.storage.persistence.audit import (
    PersistenceAuditActor,
    PersistenceAuditEventRecord,
    PersistenceAuditEventResult,
)
from core.storage.persistence.lineage import PersistenceLineage


class FakeAuditService:
    def __init__(
        self,
        *,
        fail: bool = False,
    ) -> None:
        self.fail = fail
        self.events: list[PersistenceAuditEventRecord] = []

    async def persist_audit_event(
        self,
        event: PersistenceAuditEventRecord,
    ) -> PersistenceAuditEventResult:
        if self.fail:
            raise RuntimeError("audit store unavailable")
        self.events.append(
            event,
        )
        return PersistenceAuditEventResult.succeeded(
            audit_event_id=event.audit_event_id,
        )


@pytest.mark.asyncio
async def test_non_fatal_audit_emitter_persists_typed_event() -> None:
    audit_service = FakeAuditService()
    emitter = NonFatalPersistenceAuditEmitter(
        cast(
            AuditPersistenceService,
            audit_service,
        ),
        PersistenceAuditActor(
            system_source="application.persistence.news",
            actor_id="news-service",
            actor_type="application_service",
        ),
    )
    emission = PersistenceAuditEmission(
        entity_type="news_article",
        entity_id="article-1",
        action="persist",
        timestamp=_timestamp(),
        lineage=PersistenceLineage(
            workflow_name="morning_report",
            execution_id="exec-1",
        ),
        metadata={
            "source": "reuters",
        },
    )

    result = await emitter.emit(
        emission,
    )

    assert result is not None
    assert result.success is True
    assert len(audit_service.events) == 1
    event = audit_service.events[0]
    assert event.entity_type == "news_article"
    assert event.entity_id == "article-1"
    assert event.action == "persist"
    assert event.actor.system_source == "application.persistence.news"
    assert event.actor.actor_id == "news-service"
    assert event.lineage.workflow_name == "morning_report"
    assert event.metadata == {
        "source": "reuters",
    }


@pytest.mark.asyncio
async def test_non_fatal_audit_emitter_returns_none_when_disabled() -> None:
    audit_service = FakeAuditService()
    emitter = NonFatalPersistenceAuditEmitter(
        cast(
            AuditPersistenceService,
            audit_service,
        ),
        PersistenceAuditActor(
            system_source="application.persistence.news",
        ),
        enabled=False,
    )

    result = await emitter.emit(
        _emission(),
    )

    assert result is None
    assert audit_service.events == []


@pytest.mark.asyncio
async def test_non_fatal_audit_emitter_converts_audit_exception_to_failure() -> None:
    audit_service = FakeAuditService(
        fail=True,
    )
    emitter = NonFatalPersistenceAuditEmitter(
        cast(
            AuditPersistenceService,
            audit_service,
        ),
        PersistenceAuditActor(
            system_source="application.persistence.news",
        ),
    )

    result = await emitter.emit(
        _emission(),
    )

    assert result is not None
    assert result.success is False
    assert result.error == "audit store unavailable"
    assert audit_service.events == []


@pytest.mark.asyncio
async def test_non_fatal_audit_emitter_emits_many_in_order() -> None:
    audit_service = FakeAuditService()
    emitter = NonFatalPersistenceAuditEmitter(
        cast(
            AuditPersistenceService,
            audit_service,
        ),
        PersistenceAuditActor(
            system_source="application.persistence.news",
        ),
    )
    emissions = (
        _emission(
            entity_id="article-1",
        ),
        _emission(
            entity_id="article-2",
        ),
    )

    results = await emitter.emit_many(
        emissions,
    )

    assert len(results) == 2
    assert [event.entity_id for event in audit_service.events] == [
        "article-1",
        "article-2",
    ]


def _emission(
    *,
    entity_id: str = "article-1",
) -> PersistenceAuditEmission:
    return PersistenceAuditEmission(
        entity_type="news_article",
        entity_id=entity_id,
        action="persist",
        timestamp=_timestamp(),
    )


def _timestamp() -> datetime:
    return datetime(2026, 5, 31, 14, 0, tzinfo=UTC)
