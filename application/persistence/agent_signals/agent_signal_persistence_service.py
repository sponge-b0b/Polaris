from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from application.persistence.query_result_helpers import (
    build_common_query,
    build_list_result,
)
from core.storage.persistence.agent_signals import (
    AgentSignalPersistenceRepository,
    AgentSignalPersistenceResult,
    AgentSignalRecord,
)
from core.storage.persistence.query import PersistenceListResult


@dataclass(frozen=True, slots=True)
class AgentSignalPersistenceFilters:
    """Typed application-layer filters for curated agent signal retrieval."""

    workflow_name: str
    execution_id: str


class AgentSignalPersistenceService:
    """Application service for curated intelligence signal persistence."""

    def __init__(self, repository: AgentSignalPersistenceRepository) -> None:
        self._repository = repository

    async def persist_signal(
        self,
        signal: AgentSignalRecord,
    ) -> AgentSignalPersistenceResult:
        return await self._repository.persist_signal(signal)

    async def get_signal(self, signal_id: str) -> AgentSignalRecord | None:
        return await self._repository.get_signal(signal_id)

    async def list_signals_for_execution(
        self,
        filters: AgentSignalPersistenceFilters,
    ) -> Sequence[AgentSignalRecord]:
        result = await self.list_signals_for_execution_result(filters)
        return result.records

    async def list_signals_for_execution_result(
        self,
        filters: AgentSignalPersistenceFilters,
    ) -> PersistenceListResult[AgentSignalRecord]:
        records = await self._repository.list_signals_for_execution(
            workflow_name=filters.workflow_name,
            execution_id=filters.execution_id,
        )
        query = build_common_query(
            record_type="agent_signal",
            execution_id=filters.execution_id,
            metadata={"workflow_name": filters.workflow_name},
        )
        return build_list_result(records, query=query)
