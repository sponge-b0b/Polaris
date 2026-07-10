from __future__ import annotations

from typing import Protocol
from typing import Sequence

from core.storage.persistence.agent_signals.agent_signal_persistence_models import (
    AgentSignalPersistenceResult,
)
from core.storage.persistence.agent_signals.agent_signal_persistence_models import (
    AgentSignalRecord,
)


class AgentSignalPersistenceRepository(Protocol):
    """
    Async repository contract for durable curated agent signal persistence.
    """

    async def persist_signal(
        self,
        signal: AgentSignalRecord,
    ) -> AgentSignalPersistenceResult: ...

    async def get_signal(
        self,
        signal_id: str,
    ) -> AgentSignalRecord | None: ...

    async def list_signals_for_execution(
        self,
        *,
        workflow_name: str,
        execution_id: str,
    ) -> Sequence[AgentSignalRecord]: ...
