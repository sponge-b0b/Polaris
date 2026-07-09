from __future__ import annotations

from core.runtime.state.state_manager import StateManager
from core.storage.persistence.completed_run_archive import CompletedRunArchive
from core.storage.persistence.completed_run_archive import CompletedRunBundle


class InMemoryCompletedRunArchive(CompletedRunArchive):
    def __init__(
        self,
        *,
        cleanup_count: int = 0,
    ) -> None:
        self.bundles: dict[tuple[str, str], CompletedRunBundle] = {}
        self.deleted: list[tuple[str, str]] = []
        self.cleanup_count = cleanup_count
        self.cleanup_calls: list[tuple[int | None, int | None]] = []

    async def archive_run(
        self,
        bundle: CompletedRunBundle,
    ) -> None:
        self.bundles[(bundle.run.workflow_name, bundle.run.execution_id)] = bundle

    async def load_archived_run(
        self,
        workflow_name: str,
        execution_id: str,
    ) -> CompletedRunBundle | None:
        return self.bundles.get(
            (workflow_name, execution_id),
        )

    async def list_archived_runs(
        self,
        workflow_name: str,
    ) -> list[str]:
        return sorted(
            execution_id
            for (stored_workflow_name, execution_id) in self.bundles
            if stored_workflow_name == workflow_name
        )

    async def delete_archived_run(
        self,
        workflow_name: str,
        execution_id: str,
    ) -> None:
        self.deleted.append(
            (workflow_name, execution_id),
        )
        self.bundles.pop(
            (workflow_name, execution_id),
            None,
        )

    async def cleanup_archived_runs(
        self,
        max_age_days: int | None = None,
        max_count: int | None = None,
    ) -> int:
        self.cleanup_calls.append(
            (max_age_days, max_count),
        )
        return self.cleanup_count


async def test_state_manager_archives_loads_lists_and_deletes_completed_runs() -> None:
    archive = InMemoryCompletedRunArchive()
    manager = StateManager(
        archive=archive,
    )
    context = manager.create_context(
        workflow_id="morning_report",
        execution_id="exec-1",
        workflow_inputs={"symbol": "SPY"},
    ).add_node_output(
        "node_a",
        {"success": True, "outputs": {"value": 42}},
    )

    await manager.archive_completed_run(
        context,
    )

    assert await manager.list_completed_runs("morning_report") == ["exec-1"]
    bundle = archive.bundles[("morning_report", "exec-1")]
    assert bundle.run.workflow_name == "morning_report"
    assert bundle.run.execution_id == "exec-1"
    assert bundle.run.context_json["workflow_id"] == "morning_report"
    assert bundle.node_outputs[0].node_name == "node_a"

    loaded = await manager.load_completed_run("morning_report", "exec-1")
    assert loaded is not None
    assert loaded.workflow_id == "morning_report"
    assert loaded.execution_id == "exec-1"
    assert loaded.node_outputs == {
        "node_a": {"success": True, "outputs": {"value": 42}},
    }
    assert loaded.workflow_inputs == {"symbol": "SPY"}
    assert loaded.context_version == 1

    await manager.delete_completed_run("morning_report", "exec-1")

    assert archive.deleted == [("morning_report", "exec-1")]
    assert await manager.load_completed_run("morning_report", "exec-1") is None


async def test_state_manager_cleanup_completed_runs_uses_archive_defaults() -> None:
    archive = InMemoryCompletedRunArchive(
        cleanup_count=3,
    )
    manager = StateManager(
        archive=archive,
    )

    assert (
        await manager.cleanup_completed_runs(
            max_age_days=30,
            max_count=50,
        )
        == 3
    )
    assert archive.cleanup_calls == [(30, 50)]


async def test_state_manager_completed_run_methods_return_empty_without_archive() -> (
    None
):
    manager = StateManager()
    context = manager.create_context(
        workflow_id="morning_report",
        execution_id="exec-1",
    )

    await manager.archive_completed_run(
        context,
    )

    assert await manager.list_completed_runs("morning_report") == []
    assert await manager.load_completed_run("morning_report", "exec-1") is None
    await manager.delete_completed_run("morning_report", "exec-1")
    assert await manager.cleanup_completed_runs() == 0
