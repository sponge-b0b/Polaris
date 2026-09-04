from __future__ import annotations

import asyncio

import pytest

from core.plugins.lifecycle.plugin_lifecycle_manager import (
    PluginLifecycleManager,
)
from core.plugins.lifecycle.plugin_telemetry_hook import (
    PluginTelemetryHook,
)
from core.plugins.manifests.plugin_manifest import PluginManifest
from core.plugins.runtime.plugin_discovery import PluginDiscoveryResult
from core.plugins.runtime.plugin_runtime_loader import RuntimePluginLoadResult
from core.plugins.runtime.plugin_runtime_manager import (
    PluginRuntimeManager,
)
from core.plugins.runtime.plugin_workflow_loader import (
    PluginWorkflowLoader,
)
from core.telemetry.observability.observability_manager import (
    ObservabilityManager,
)
from core.telemetry.sinks.telemetry_sink import (
    InMemoryTelemetrySink,
)
from core.workflow.bootstrap.workflow_bootstrap import (
    build_workflow_runtime,
)


@pytest.mark.asyncio
async def test_plugin_lifecycle_events_emit_telemetry() -> None:
    telemetry_sink = InMemoryTelemetrySink()

    observability_manager = ObservabilityManager()
    observability_manager.add_sink(
        telemetry_sink,
    )

    lifecycle_manager = PluginLifecycleManager(
        hooks=[
            PluginTelemetryHook(
                observability_manager=observability_manager,
            )
        ]
    )

    runtime = build_workflow_runtime(
        observability_manager=observability_manager,
    )

    assert runtime.facade.plugin_runtime_loader is not None

    plugin_manager = PluginRuntimeManager(
        runtime_loader=runtime.facade.plugin_runtime_loader,
        workflow_loader=PluginWorkflowLoader(),
        lifecycle_manager=lifecycle_manager,
    )

    result = await plugin_manager.discover_and_load(
        plugin_dir="plugins/example_market_plugin",
        recursive=False,
        overwrite=True,
    )

    assert result.success is True

    event_types = [event.event_type for event in telemetry_sink.events]

    assert "plugin.discovery.started" in event_types
    assert "plugin.discovery.completed" in event_types
    assert "plugin.validation.started" in event_types
    assert "plugin.validation.completed" in event_types
    assert "plugin.load.started" in event_types
    assert "plugin.load.completed" in event_types

    completed_events = [
        event
        for event in telemetry_sink.events
        if event.event_type == "plugin.load.completed"
    ]

    assert completed_events
    assert completed_events[-1].success is True
    assert completed_events[-1].error_count == 0

    payload = completed_events[-1].payload

    assert payload["plugin_name"] == "example_market_plugin"
    assert payload["version"] == "1.0.0"
    assert payload["results"][0]["success"] is True


class FailingPluginLifecycleHook:
    async def before_plugin_discovery(
        self,
        plugin_dir: str,
    ) -> None:
        raise RuntimeError("plugin hook exploded")

    async def after_plugin_discovery(self, result: PluginDiscoveryResult) -> None:
        return None

    async def before_plugin_validate(self, manifest: PluginManifest) -> None:
        return None

    async def after_plugin_validate(
        self,
        manifest: PluginManifest,
        errors: list[dict],
    ) -> None:
        return None

    async def before_plugin_load(self, manifest: PluginManifest) -> None:
        return None

    async def after_plugin_load(
        self,
        manifest: PluginManifest,
        results: list[RuntimePluginLoadResult],
    ) -> None:
        return None


class CancelledPluginLifecycleHook(FailingPluginLifecycleHook):
    async def before_plugin_discovery(
        self,
        plugin_dir: str,
    ) -> None:
        raise asyncio.CancelledError


@pytest.mark.asyncio
async def test_plugin_lifecycle_reports_hook_failure_once() -> None:
    telemetry_sink = InMemoryTelemetrySink()
    observability_manager = ObservabilityManager()
    observability_manager.add_sink(telemetry_sink)
    telemetry_hook = PluginTelemetryHook(observability_manager)
    lifecycle_manager = PluginLifecycleManager(
        hooks=[FailingPluginLifecycleHook(), telemetry_hook],
        failure_handler=telemetry_hook.emit_hook_failure,
    )

    await lifecycle_manager.before_plugin_discovery("plugins")

    failure_events = [
        event
        for event in telemetry_sink.events
        if event.event_type == "plugin.lifecycle.hook_failed"
    ]
    assert len(failure_events) == 1
    failure_event = failure_events[0]
    assert failure_event.payload == {
        "lifecycle_event": "before_plugin_discovery",
        "hook": "FailingPluginLifecycleHook",
    }
    assert failure_event.exception_details is not None
    assert failure_event.exception_details.exception_type == "RuntimeError"
    assert failure_event.exception_details.message == "plugin hook exploded"
    assert "before_plugin_discovery" in failure_event.exception_details.stack_trace


@pytest.mark.asyncio
async def test_plugin_lifecycle_propagates_hook_cancellation() -> None:
    telemetry_sink = InMemoryTelemetrySink()
    observability_manager = ObservabilityManager()
    observability_manager.add_sink(telemetry_sink)
    telemetry_hook = PluginTelemetryHook(observability_manager)
    lifecycle_manager = PluginLifecycleManager(
        hooks=[CancelledPluginLifecycleHook(), telemetry_hook],
        failure_handler=telemetry_hook.emit_hook_failure,
    )

    with pytest.raises(asyncio.CancelledError):
        await lifecycle_manager.before_plugin_discovery("plugins")

    assert not any(
        event.event_type == "plugin.lifecycle.hook_failed"
        for event in telemetry_sink.events
    )


@pytest.mark.asyncio
async def test_plugin_lifecycle_reports_fail_fast_failure_before_raising() -> None:
    telemetry_sink = InMemoryTelemetrySink()
    observability_manager = ObservabilityManager()
    observability_manager.add_sink(telemetry_sink)
    telemetry_hook = PluginTelemetryHook(observability_manager)
    lifecycle_manager = PluginLifecycleManager(
        hooks=[FailingPluginLifecycleHook()],
        fail_fast=True,
        failure_handler=telemetry_hook.emit_hook_failure,
    )

    with pytest.raises(RuntimeError, match="plugin hook exploded"):
        await lifecycle_manager.before_plugin_discovery("plugins")

    failure_events = [
        event
        for event in telemetry_sink.events
        if event.event_type == "plugin.lifecycle.hook_failed"
    ]
    assert len(failure_events) == 1
