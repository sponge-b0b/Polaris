from __future__ import annotations

import json

from pathlib import Path
from typing import Any

from core.runtime.telemetry.runtime_telemetry import (
    RuntimeTelemetryEvent,
    RuntimeTelemetrySink,
)


class JsonlRuntimeTelemetrySink(RuntimeTelemetrySink):
    """
    JSONL runtime telemetry sink.

    PURPOSE
    ============================================================
    Writes one RuntimeTelemetryEvent per line.

    Useful for:
    - local debugging
    - replay auditing
    - workflow execution traces
    - lightweight observability before external telemetry adapters
    """

    def __init__(
        self,
        file_path: str = "storage/telemetry/runtime_telemetry.jsonl",
    ) -> None:
        self.file_path = Path(
            file_path,
        )

        self.file_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    async def emit(
        self,
        event: RuntimeTelemetryEvent,
    ) -> None:
        payload = event.to_dict()

        with open(
            self.file_path,
            "a",
            encoding="utf-8",
        ) as file:
            file.write(
                json.dumps(
                    payload,
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
            file.write("\n")

    def clear(
        self,
    ) -> None:
        if self.file_path.exists():
            self.file_path.unlink()

    def read_events(
        self,
    ) -> list[dict[str, Any]]:
        if not self.file_path.exists():
            return []

        events: list[dict[str, Any]] = []

        with open(
            self.file_path,
            "r",
            encoding="utf-8",
        ) as file:
            for line in file:
                line = line.strip()

                if not line:
                    continue

                events.append(
                    json.loads(line),
                )

        return events

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "sink": self.__class__.__name__,
            "file_path": str(self.file_path),
            "exists": self.file_path.exists(),
        }
