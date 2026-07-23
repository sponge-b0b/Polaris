from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from core.plugins.lifecycle.plugin_lifecycle_hooks import (
    PluginLifecycleHook,
)

if TYPE_CHECKING:
    from core.plugins.manifests.plugin_manifest import PluginManifest
    from core.plugins.runtime.plugin_discovery import PluginDiscoveryResult
    from core.plugins.runtime.plugin_runtime_loader import (
        RuntimePluginLoadResult,
    )


PluginHookCallback = Callable[
    [PluginLifecycleHook],
    Awaitable[None],
]

PluginHookFailureHandler = Callable[
    [str, PluginLifecycleHook, BaseException],
    Awaitable[None],
]


class PluginLifecycleManager:
    def __init__(
        self,
        hooks: list[PluginLifecycleHook] | None = None,
        fail_fast: bool = False,
        failure_handler: PluginHookFailureHandler | None = None,
    ) -> None:
        self._hooks: list[PluginLifecycleHook] = list(hooks or [])
        self.fail_fast = fail_fast
        self._failure_handler = failure_handler

    def register(
        self,
        hook: PluginLifecycleHook,
    ) -> None:
        if hook not in self._hooks:
            self._hooks.append(hook)

    def unregister(
        self,
        hook: PluginLifecycleHook,
    ) -> None:
        if hook in self._hooks:
            self._hooks.remove(hook)

    def clear(self) -> None:
        self._hooks.clear()

    async def before_plugin_discovery(
        self,
        plugin_dir: str,
    ) -> None:
        await self._dispatch(
            "before_plugin_discovery",
            lambda hook: hook.before_plugin_discovery(plugin_dir),
        )

    async def after_plugin_discovery(
        self,
        result: PluginDiscoveryResult,
    ) -> None:
        await self._dispatch(
            "after_plugin_discovery",
            lambda hook: hook.after_plugin_discovery(result),
        )

    async def before_plugin_validate(
        self,
        manifest: PluginManifest,
    ) -> None:
        await self._dispatch(
            "before_plugin_validate",
            lambda hook: hook.before_plugin_validate(manifest),
        )

    async def after_plugin_validate(
        self,
        manifest: PluginManifest,
        errors: list[dict],
    ) -> None:
        await self._dispatch(
            "after_plugin_validate",
            lambda hook: hook.after_plugin_validate(manifest, errors),
        )

    async def before_plugin_load(
        self,
        manifest: PluginManifest,
    ) -> None:
        await self._dispatch(
            "before_plugin_load",
            lambda hook: hook.before_plugin_load(manifest),
        )

    async def after_plugin_load(
        self,
        manifest: PluginManifest,
        results: list[RuntimePluginLoadResult],
    ) -> None:
        await self._dispatch(
            "after_plugin_load",
            lambda hook: hook.after_plugin_load(manifest, results),
        )

    @property
    def hooks(
        self,
    ) -> tuple[PluginLifecycleHook, ...]:
        return tuple(self._hooks)

    def hook_count(self) -> int:
        return len(self._hooks)

    def to_dict(self) -> dict[str, object]:
        return {
            "manager": self.__class__.__name__,
            "hook_count": len(self._hooks),
            "hooks": [hook.__class__.__name__ for hook in self._hooks],
            "fail_fast": self.fail_fast,
        }

    async def _dispatch(  # noqa: C901
        self,
        lifecycle_event: str,
        callback: PluginHookCallback,
    ) -> None:
        if not self._hooks:
            return

        if self.fail_fast:
            for hook in self._hooks:
                try:
                    await callback(hook)
                except asyncio.CancelledError:
                    raise
                except BaseException as error:
                    if self._failure_handler is not None:
                        await self._failure_handler(
                            lifecycle_event,
                            hook,
                            error,
                        )
                    raise
            return

        results = await asyncio.gather(
            *[callback(hook) for hook in self._hooks],
            return_exceptions=True,
        )

        for result in results:
            if isinstance(result, asyncio.CancelledError):
                raise result

        if self._failure_handler is None:
            return

        for hook, result in zip(self._hooks, results, strict=False):
            if isinstance(result, BaseException):
                await self._failure_handler(
                    lifecycle_event,
                    hook,
                    result,
                )
