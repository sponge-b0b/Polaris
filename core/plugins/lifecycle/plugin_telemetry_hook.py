from __future__ import annotations

from typing import TYPE_CHECKING, Any

from core.telemetry.events.telemetry_event import TelemetryEventLevel
from core.telemetry.events.telemetry_exception_details import (
    TelemetryExceptionDetails,
)
from core.telemetry.observability.observability_manager import (
    ObservabilityManager,
)

if TYPE_CHECKING:
    from core.plugins.manifests.plugin_manifest import PluginManifest
    from core.plugins.runtime.plugin_discovery import PluginDiscoveryResult
    from core.plugins.runtime.plugin_runtime_loader import (
        RuntimePluginLoadResult,
    )


class PluginTelemetryHook:
    """
    Plugin lifecycle telemetry hook.

    Bridges plugin lifecycle events into the platform observability layer.
    """

    def __init__(
        self,
        observability_manager: ObservabilityManager,
        source: str = "plugins",
    ) -> None:
        self.observability_manager = observability_manager
        self.source = source

    async def before_plugin_discovery(
        self,
        plugin_dir: str,
    ) -> None:
        await self.observability_manager.info(
            event_type="plugin.discovery.started",
            source=self.source,
            payload={
                "plugin_dir": plugin_dir,
            },
        )

    async def after_plugin_discovery(
        self,
        result: PluginDiscoveryResult,
    ) -> None:
        await self.observability_manager.emit(
            self._event(
                event_type="plugin.discovery.completed",
                level=(
                    TelemetryEventLevel.INFO
                    if result.success
                    else TelemetryEventLevel.ERROR
                ),
                success=result.success,
                error_count=len(result.errors),
                payload=result.to_dict(),
            )
        )

    async def before_plugin_validate(
        self,
        manifest: PluginManifest,
    ) -> None:
        await self.observability_manager.info(
            event_type="plugin.validation.started",
            source=self.source,
            payload={
                "plugin_name": manifest.plugin_name,
                "version": manifest.version,
            },
        )

    async def after_plugin_validate(
        self,
        manifest: PluginManifest,
        errors: list[dict],
    ) -> None:
        await self.observability_manager.emit(
            self._event(
                event_type="plugin.validation.completed",
                level=(
                    TelemetryEventLevel.INFO
                    if not errors
                    else TelemetryEventLevel.ERROR
                ),
                success=not errors,
                error_count=len(errors),
                payload={
                    "plugin_name": manifest.plugin_name,
                    "version": manifest.version,
                    "errors": errors,
                },
            )
        )

    async def before_plugin_load(
        self,
        manifest: PluginManifest,
    ) -> None:
        await self.observability_manager.info(
            event_type="plugin.load.started",
            source=self.source,
            payload={
                "plugin_name": manifest.plugin_name,
                "version": manifest.version,
                "runtime_modules": list(manifest.runtime_modules),
                "workflow_modules": list(manifest.workflow_modules),
            },
        )

    async def after_plugin_load(
        self,
        manifest: PluginManifest,
        results: list[RuntimePluginLoadResult],
    ) -> None:
        success = all(result.success for result in results)

        error_count = sum(len(result.errors) for result in results)

        await self.observability_manager.emit(
            self._event(
                event_type="plugin.load.completed",
                level=(
                    TelemetryEventLevel.INFO if success else TelemetryEventLevel.ERROR
                ),
                success=success,
                error_count=error_count,
                payload={
                    "plugin_name": manifest.plugin_name,
                    "version": manifest.version,
                    "results": [result.to_dict() for result in results],
                },
            )
        )

    async def emit_hook_failure(
        self,
        lifecycle_event: str,
        hook: object,
        error: BaseException,
    ) -> None:
        await self.observability_manager.emit(
            self._event(
                event_type="plugin.lifecycle.hook_failed",
                level=TelemetryEventLevel.ERROR,
                success=False,
                error_count=1,
                payload={
                    "lifecycle_event": lifecycle_event,
                    "hook": hook.__class__.__name__,
                },
                exception_details=TelemetryExceptionDetails.from_exception(error),
            )
        )

    def _event(
        self,
        event_type: str,
        level: TelemetryEventLevel,
        success: bool | None = None,
        error_count: int = 0,
        payload: dict[str, Any] | None = None,
        exception_details: TelemetryExceptionDetails | None = None,
    ):
        from core.telemetry.events.telemetry_event import TelemetryEvent

        return TelemetryEvent(
            event_type=event_type,
            source=self.source,
            level=level,
            success=success,
            error_count=error_count,
            exception_details=exception_details,
            payload=dict(payload or {}),
        )
