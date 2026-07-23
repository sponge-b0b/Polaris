from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class PluginManifest:
    """
    Immutable plugin manifest.

    Describes a plugin package without loading or executing plugin code.
    """

    plugin_name: str

    version: str

    description: str = ""

    runtime_modules: tuple[str, ...] = ()

    workflow_modules: tuple[str, ...] = ()

    provider_modules: tuple[str, ...] = ()

    tags: tuple[str, ...] = ()

    enabled: bool = True

    include_imported_classes: bool = False

    metadata: dict[str, Any] = field(
        default_factory=dict,
    )

    def validate(
        self,
    ) -> None:
        if not self.plugin_name.strip():
            raise ValueError("plugin_name cannot be empty.")

        if not self.version.strip():
            raise ValueError("version cannot be empty.")

        self._validate_modules(
            name="runtime_modules",
            modules=self.runtime_modules,
        )

        self._validate_modules(
            name="workflow_modules",
            modules=self.workflow_modules,
        )

        self._validate_modules(
            name="provider_modules",
            modules=self.provider_modules,
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "plugin_name": self.plugin_name,
            "version": self.version,
            "description": self.description,
            "runtime_modules": list(self.runtime_modules),
            "workflow_modules": list(self.workflow_modules),
            "provider_modules": list(self.provider_modules),
            "tags": list(self.tags),
            "enabled": self.enabled,
            "include_imported_classes": self.include_imported_classes,
            "metadata": deepcopy(self.metadata),
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> PluginManifest:
        manifest = cls(
            plugin_name=str(data["plugin_name"]),
            version=str(data["version"]),
            description=str(data.get("description", "")),
            runtime_modules=tuple(
                str(module) for module in data.get("runtime_modules", ())
            ),
            workflow_modules=tuple(
                str(module) for module in data.get("workflow_modules", ())
            ),
            provider_modules=tuple(
                str(module) for module in data.get("provider_modules", ())
            ),
            tags=tuple(str(tag) for tag in data.get("tags", ())),
            enabled=bool(data.get("enabled", True)),
            include_imported_classes=bool(
                data.get("include_imported_classes", False),
            ),
            metadata=deepcopy(data.get("metadata", {})),
        )

        manifest.validate()

        return manifest

    def as_runtime_loader_manifest(
        self,
    ) -> dict[str, Any]:
        return {
            "runtime_modules": list(self.runtime_modules),
            "include_imported_classes": self.include_imported_classes,
        }

    def _validate_modules(
        self,
        name: str,
        modules: tuple[str, ...],
    ) -> None:
        for module in modules:
            if not module.strip():
                raise ValueError(f"{name} contains an empty module path.")
