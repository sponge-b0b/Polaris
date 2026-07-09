from __future__ import annotations

import json
import re
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Any

from core.runtime.checkpoints.runtime_checkpoint import RuntimeCheckpoint
from core.runtime.events.event_bus import EventBus
from core.runtime.events.runtime_events import RuntimeEvent
from core.runtime.events.runtime_events import RuntimeEventType
from core.runtime.state.runtime_context import RuntimeContext


class CheckpointManager:
    """
    Canonical runtime checkpoint manager.

    Provides deterministic checkpoint persistence for:
    - replay
    - recovery
    - resumability
    - auditability
    - simulation continuity
    """

    def __init__(
        self,
        checkpoint_dir: str,
        event_bus: EventBus | None = None,
    ) -> None:
        self.checkpoint_dir = Path(checkpoint_dir)

        self.checkpoint_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.event_bus = event_bus

    # ========================================================
    # SAVE CHECKPOINT
    # ========================================================

    async def save_checkpoint(
        self,
        context: RuntimeContext,
        checkpoint_name: str | None = None,
        wave_index: int = 0,
        completed_nodes: tuple[str, ...] | None = None,
        failed_nodes: tuple[str, ...] | None = None,
        skipped_nodes: tuple[str, ...] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Path:
        timestamp = datetime.now(timezone.utc).strftime(
            "%Y%m%d_%H%M%S",
        )

        checkpoint_id = self._sanitize_checkpoint_id(
            checkpoint_name or f"{context.execution_id}_{timestamp}",
        )

        checkpoint = RuntimeCheckpoint.from_context(
            checkpoint_id=checkpoint_id,
            context=context,
            wave_index=wave_index,
            completed_nodes=completed_nodes,
            failed_nodes=failed_nodes,
            skipped_nodes=skipped_nodes,
            metadata={
                **dict(metadata or {}),
                "saved_at": datetime.now(timezone.utc).isoformat(),
            },
        )

        file_path = self.checkpoint_dir / f"{checkpoint_id}.json"
        tmp_path = self.checkpoint_dir / f"{checkpoint_id}.json.tmp"

        payload = checkpoint.to_dict()

        with open(
            tmp_path,
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                payload,
                file,
                indent=2,
                ensure_ascii=False,
                sort_keys=True,
            )

        tmp_path.replace(file_path)

        await self._emit(
            RuntimeEvent(
                event_type=RuntimeEventType.CHECKPOINT_CREATED,
                execution_id=context.execution_id,
                workflow_id=context.workflow_id,
                runtime_id=context.runtime_id,
                payload={
                    "checkpoint_id": checkpoint_id,
                    "file_path": str(file_path),
                    "wave_index": wave_index,
                    "completed_nodes": list(completed_nodes or ()),
                    "failed_nodes": list(failed_nodes or ()),
                    "skipped_nodes": list(skipped_nodes or ()),
                },
            )
        )

        return file_path

    # ========================================================
    # LOAD CHECKPOINT
    # ========================================================

    async def load_checkpoint(
        self,
        checkpoint_file: str | Path,
    ) -> dict[str, Any]:
        file_path = Path(checkpoint_file)

        if not file_path.exists():
            raise FileNotFoundError(f"Checkpoint not found: {file_path}")

        with open(
            file_path,
            "r",
            encoding="utf-8",
        ) as file:
            payload: dict[str, Any] = json.load(file)

        checkpoint = RuntimeCheckpoint.from_dict(
            payload,
        )

        await self._emit(
            RuntimeEvent(
                event_type=RuntimeEventType.CHECKPOINT_RESTORED,
                execution_id=checkpoint.execution_id,
                workflow_id=checkpoint.workflow_id,
                runtime_id=checkpoint.runtime_id,
                payload={
                    "checkpoint_id": checkpoint.checkpoint_id,
                    "checkpoint_file": str(file_path),
                    "wave_index": checkpoint.wave_index,
                    "completed_nodes": list(checkpoint.completed_nodes),
                    "failed_nodes": list(checkpoint.failed_nodes),
                    "skipped_nodes": list(checkpoint.skipped_nodes),
                },
            )
        )

        return payload

    # ========================================================
    # RESTORE CHECKPOINT / CONTEXT
    # ========================================================

    async def restore_checkpoint(
        self,
        checkpoint_file: str | Path,
    ) -> RuntimeCheckpoint:
        payload = await self.load_checkpoint(
            checkpoint_file,
        )

        return RuntimeCheckpoint.from_dict(
            payload,
        )

    async def restore_context(
        self,
        checkpoint_file: str | Path,
    ) -> RuntimeContext:
        checkpoint = await self.restore_checkpoint(
            checkpoint_file,
        )

        if checkpoint.runtime_context is None:
            raise ValueError("Checkpoint payload does not contain runtime_context.")

        return checkpoint.runtime_context

    # ========================================================
    # LIST CHECKPOINTS
    # ========================================================

    def list_checkpoints(
        self,
    ) -> list[Path]:
        return sorted(self.checkpoint_dir.glob("*.json"))

    # ========================================================
    # DELETE CHECKPOINT
    # ========================================================

    def delete_checkpoint(
        self,
        checkpoint_file: str | Path,
    ) -> None:
        file_path = Path(checkpoint_file)

        if file_path.exists():
            file_path.unlink()

    # ========================================================
    # CLEAR ALL
    # ========================================================

    def clear_all(
        self,
    ) -> None:
        for checkpoint in self.list_checkpoints():
            checkpoint.unlink()

    # ========================================================
    # EXISTS
    # ========================================================

    def checkpoint_exists(
        self,
        checkpoint_file: str | Path,
    ) -> bool:
        return Path(checkpoint_file).exists()

    # ========================================================
    # SERIALIZATION
    # ========================================================

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "checkpoint_dir": str(self.checkpoint_dir),
            "checkpoint_count": len(self.list_checkpoints()),
        }

    # ========================================================
    # INTERNALS
    # ========================================================

    async def _emit(
        self,
        event: RuntimeEvent,
    ) -> None:
        if self.event_bus is None:
            return

        await self.event_bus.emit(event)

    def _sanitize_checkpoint_id(
        self,
        checkpoint_id: str,
    ) -> str:
        checkpoint_id = checkpoint_id.strip()

        if not checkpoint_id:
            raise ValueError("checkpoint_id cannot be empty.")

        return re.sub(
            r"[^a-zA-Z0-9_.-]+",
            "_",
            checkpoint_id,
        )
