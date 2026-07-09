from __future__ import annotations

import importlib.util
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.plugins.manifests.plugin_manifest import PluginManifest


@dataclass(frozen=True, slots=True)
class PluginDiscoveryResult:
    """
    Result of plugin manifest discovery.
    """

    plugin_dir: Path

    discovered_manifests: tuple[PluginManifest, ...] = ()

    skipped_files: tuple[str, ...] = ()

    errors: tuple[dict[str, Any], ...] = ()

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
            "plugin_dir": str(self.plugin_dir),
            "discovered_manifests": [
                manifest.to_dict() for manifest in self.discovered_manifests
            ],
            "skipped_files": list(self.skipped_files),
            "errors": [dict(error) for error in self.errors],
        }


class PluginDiscovery:
    """
    Discovers plugin manifests from a plugin directory.

    Supported manifest file names:
    - plugin.json
    - plugin_manifest.json
    - *.plugin.json

    This class does not import plugin runtime modules. It only discovers
    and validates manifests.
    """

    DEFAULT_MANIFEST_NAMES: tuple[str, ...] = (
        "plugin.json",
        "plugin_manifest.json",
    )

    def __init__(
        self,
        plugin_dir: str | Path = "plugins",
    ) -> None:
        self.plugin_dir = Path(
            plugin_dir,
        )

    def discover(
        self,
        recursive: bool = True,
    ) -> PluginDiscoveryResult:
        if not self.plugin_dir.exists():
            return PluginDiscoveryResult(
                plugin_dir=self.plugin_dir,
                errors=(
                    {
                        "error_type": "PluginDirectoryNotFound",
                        "message": f"Plugin directory not found: {self.plugin_dir}",
                    },
                ),
            )

        manifest_files = self._find_manifest_files(
            recursive=recursive,
        )

        manifests: list[PluginManifest] = []
        skipped_files: list[str] = []
        errors: list[dict[str, Any]] = []

        for manifest_file in manifest_files:
            try:
                manifest = self.load_manifest_file(
                    manifest_file,
                )

                if not manifest.enabled:
                    skipped_files.append(
                        str(manifest_file),
                    )
                    continue

                manifests.append(
                    manifest,
                )

            except Exception as exc:
                errors.append(
                    {
                        "file": str(manifest_file),
                        "error_type": type(exc).__name__,
                        "message": str(exc),
                    }
                )

        return PluginDiscoveryResult(
            plugin_dir=self.plugin_dir,
            discovered_manifests=tuple(manifests),
            skipped_files=tuple(skipped_files),
            errors=tuple(errors),
        )

    def load_manifest_file(
        self,
        manifest_file: str | Path,
    ) -> PluginManifest:
        path = Path(
            manifest_file,
        )

        if not path.exists():
            raise FileNotFoundError(f"Plugin manifest not found: {path}")

        with open(
            path,
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

        if not isinstance(data, dict):
            raise TypeError(f"Plugin manifest must be a JSON object: {path}")

        return PluginManifest.from_dict(
            data,
        )

    def validate_imports(
        self,
        manifest: PluginManifest,
    ) -> list[dict[str, Any]]:
        errors: list[dict[str, Any]] = []

        for module_name in (
            list(manifest.runtime_modules)
            + list(manifest.workflow_modules)
            + list(manifest.provider_modules)
        ):
            if importlib.util.find_spec(module_name) is None:
                errors.append(
                    {
                        "plugin_name": manifest.plugin_name,
                        "module_name": module_name,
                        "error_type": "ModuleNotFound",
                        "message": f"Module not importable: {module_name}",
                    }
                )

        return errors

    def _find_manifest_files(
        self,
        recursive: bool,
    ) -> list[Path]:
        candidates: list[Path] = []

        for manifest_name in self.DEFAULT_MANIFEST_NAMES:
            if recursive:
                candidates.extend(
                    self.plugin_dir.rglob(
                        manifest_name,
                    )
                )
            else:
                path = self.plugin_dir / manifest_name

                if path.exists():
                    candidates.append(
                        path,
                    )

        pattern = "**/*.plugin.json" if recursive else "*.plugin.json"

        candidates.extend(
            self.plugin_dir.glob(
                pattern,
            )
        )

        return sorted(
            set(candidates),
        )
