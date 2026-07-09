from __future__ import annotations

import importlib
import inspect
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Type

from core.runtime.contracts.runtime_node import RuntimeNode
from core.runtime.factory.runtime_node_factory import RuntimeNodeFactory


@dataclass(frozen=True, slots=True)
class RuntimePluginLoadResult:
    """
    Result of loading runtime plugin nodes.
    """

    module_name: str
    loaded_nodes: tuple[str, ...]
    skipped_objects: tuple[str, ...] = ()
    errors: tuple[dict[str, Any], ...] = ()
    metadata: dict[str, Any] | None = None

    @property
    def success(
        self,
    ) -> bool:
        return not self.errors

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "success": self.success,
            "module_name": self.module_name,
            "loaded_nodes": list(self.loaded_nodes),
            "skipped_objects": list(self.skipped_objects),
            "errors": [deepcopy(error) for error in self.errors],
            "metadata": deepcopy(self.metadata or {}),
        }


class PluginRuntimeLoader:
    """
    Runtime plugin loader.

    Discovers RuntimeNode classes from Python modules and registers them
    with RuntimeNodeFactory.

    This class only loads node classes. It does not execute workflows,
    instantiate business services directly, mutate runtime context, or run
    plugin nodes.
    """

    def __init__(
        self,
        node_factory: RuntimeNodeFactory,
    ) -> None:
        self.node_factory = node_factory

    # ========================================================
    # LOAD MODULE
    # ========================================================

    def load_module(
        self,
        module_name: str,
        overwrite: bool = False,
        include_imported_classes: bool = False,
    ) -> RuntimePluginLoadResult:
        if not module_name.strip():
            raise ValueError("module_name cannot be empty.")

        loaded_nodes: list[str] = []
        skipped_objects: list[str] = []
        errors: list[dict[str, Any]] = []

        try:
            module = importlib.import_module(
                module_name,
            )

        except Exception as exc:
            return RuntimePluginLoadResult(
                module_name=module_name,
                loaded_nodes=(),
                skipped_objects=(),
                errors=(
                    {
                        "error_type": type(exc).__name__,
                        "message": str(exc),
                        "module_name": module_name,
                    },
                ),
                metadata={
                    "loaded_count": 0,
                    "skipped_count": 0,
                    "error_count": 1,
                },
            )

        for object_name, object_value in inspect.getmembers(module):
            if not inspect.isclass(object_value):
                continue

            if object_value is RuntimeNode:
                skipped_objects.append(
                    object_name,
                )
                continue

            if not issubclass(object_value, RuntimeNode):
                continue

            if (
                not include_imported_classes
                and object_value.__module__ != module.__name__
            ):
                skipped_objects.append(
                    object_name,
                )
                continue

            node_class: Type[RuntimeNode] = object_value
            node_name = self._node_registration_name(
                node_class=node_class,
                fallback_name=object_name,
            )

            try:
                self.node_factory.register(
                    node_type=node_class,
                    name=node_name,
                    overwrite=overwrite,
                )

                loaded_nodes.append(
                    node_name,
                )

            except Exception as exc:
                skipped_objects.append(
                    object_name,
                )

                errors.append(
                    {
                        "object_name": object_name,
                        "node_name": node_name,
                        "node_class": node_class.__name__,
                        "error_type": type(exc).__name__,
                        "message": str(exc),
                    }
                )

        return RuntimePluginLoadResult(
            module_name=module_name,
            loaded_nodes=tuple(sorted(set(loaded_nodes))),
            skipped_objects=tuple(sorted(set(skipped_objects))),
            errors=tuple(errors),
            metadata={
                "loaded_count": len(set(loaded_nodes)),
                "skipped_count": len(set(skipped_objects)),
                "error_count": len(errors),
                "include_imported_classes": include_imported_classes,
            },
        )

    # ========================================================
    # LOAD MANY
    # ========================================================

    def load_modules(
        self,
        module_names: list[str],
        overwrite: bool = False,
        include_imported_classes: bool = False,
    ) -> list[RuntimePluginLoadResult]:
        return [
            self.load_module(
                module_name=module_name,
                overwrite=overwrite,
                include_imported_classes=include_imported_classes,
            )
            for module_name in module_names
        ]

    # ========================================================
    # MANIFEST SUPPORT
    # ========================================================

    def load_from_manifest(
        self,
        manifest: dict[str, Any],
        overwrite: bool = False,
    ) -> list[RuntimePluginLoadResult]:
        modules = manifest.get(
            "runtime_modules",
            [],
        )

        if not isinstance(modules, list):
            raise TypeError("Plugin manifest field 'runtime_modules' must be a list.")

        include_imported_classes = bool(
            manifest.get(
                "include_imported_classes",
                False,
            )
        )

        return self.load_modules(
            module_names=[str(module_name) for module_name in modules],
            overwrite=overwrite,
            include_imported_classes=include_imported_classes,
        )

    # ========================================================
    # INSPECTION
    # ========================================================

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "loader": self.__class__.__name__,
            "node_factory": self.node_factory.to_dict(),
        }

    # ========================================================
    # INTERNALS
    # ========================================================

    def _node_registration_name(
        self,
        node_class: Type[RuntimeNode],
        fallback_name: str,
    ) -> str:
        node_name = getattr(
            node_class,
            "node_name",
            "",
        )

        if isinstance(node_name, str) and node_name.strip():
            return node_name

        return fallback_name
