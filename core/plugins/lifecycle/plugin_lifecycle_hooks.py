from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Protocol

if TYPE_CHECKING:
    from core.plugins.manifests.plugin_manifest import PluginManifest
    from core.plugins.runtime.plugin_discovery import PluginDiscoveryResult
    from core.plugins.runtime.plugin_runtime_loader import (
        RuntimePluginLoadResult,
    )


class PluginLifecycleHook(Protocol):
    async def before_plugin_discovery(
        self,
        plugin_dir: str,
    ) -> None: ...

    async def after_plugin_discovery(
        self,
        result: PluginDiscoveryResult,
    ) -> None: ...

    async def before_plugin_validate(
        self,
        manifest: PluginManifest,
    ) -> None: ...

    async def after_plugin_validate(
        self,
        manifest: PluginManifest,
        errors: list[dict],
    ) -> None: ...

    async def before_plugin_load(
        self,
        manifest: PluginManifest,
    ) -> None: ...

    async def after_plugin_load(
        self,
        manifest: PluginManifest,
        results: list[RuntimePluginLoadResult],
    ) -> None: ...
