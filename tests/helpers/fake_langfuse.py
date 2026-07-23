from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class FakeLangfuseExportResult:
    """Small test-only export result used until production contracts are wired."""

    external_id: str
    exported: bool = True


@dataclass(slots=True)
class FakeLangfuseAiObservabilitySink:
    """In-memory Langfuse sink for unit and integration tests."""

    exported_payloads: list[Mapping[str, object]] = field(default_factory=list)

    async def export(self, payload: Mapping[str, object]) -> FakeLangfuseExportResult:
        self.exported_payloads.append(dict(payload))
        return FakeLangfuseExportResult(
            external_id=f"fake-langfuse-{len(self.exported_payloads)}"
        )
