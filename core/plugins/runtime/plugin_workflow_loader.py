from __future__ import annotations

import importlib
import inspect
from copy import deepcopy
from dataclasses import dataclass
from typing import Any
from typing import Type

from core.workflow.models.workflow_graph_definition import (
    WorkflowGraphDefinition,
)


@dataclass(frozen=True, slots=True)
class PluginWorkflowLoadResult:
    """
    Result of loading workflow definitions from a plugin module.
    """

    module_name: str

    loaded_workflows: tuple[str, ...]

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
            "loaded_workflows": list(self.loaded_workflows),
            "skipped_objects": list(self.skipped_objects),
            "errors": [deepcopy(error) for error in self.errors],
            "metadata": deepcopy(self.metadata or {}),
        }


class PluginWorkflowLoader:
    """
    Plugin workflow loader.

    Discovers WorkflowGraphDefinition classes from plugin workflow modules
    and instantiates them.

    DOES NOT:
    - execute workflows
    - compile workflows
    - mutate runtime state
    - register workflows directly
    """

    def load_module(
        self,
        module_name: str,
        include_imported_classes: bool = False,
    ) -> tuple[list[WorkflowGraphDefinition], PluginWorkflowLoadResult]:
        if not module_name.strip():
            raise ValueError("module_name cannot be empty.")

        workflows: list[WorkflowGraphDefinition] = []
        loaded_workflows: list[str] = []
        skipped_objects: list[str] = []
        errors: list[dict[str, Any]] = []

        try:
            module = importlib.import_module(
                module_name,
            )

        except Exception as exc:
            return (
                [],
                PluginWorkflowLoadResult(
                    module_name=module_name,
                    loaded_workflows=(),
                    skipped_objects=(),
                    errors=(
                        {
                            "module_name": module_name,
                            "error_type": type(exc).__name__,
                            "message": str(exc),
                        },
                    ),
                    metadata={
                        "loaded_count": 0,
                        "skipped_count": 0,
                        "error_count": 1,
                    },
                ),
            )

        for object_name, object_value in inspect.getmembers(module):
            if not inspect.isclass(object_value):
                continue

            if object_value is WorkflowGraphDefinition:
                skipped_objects.append(
                    object_name,
                )
                continue

            if not issubclass(object_value, WorkflowGraphDefinition):
                continue

            if (
                not include_imported_classes
                and object_value.__module__ != module.__name__
            ):
                skipped_objects.append(
                    object_name,
                )
                continue

            workflow_class: Type[WorkflowGraphDefinition] = object_value

            try:
                workflow = workflow_class()

                workflow.validate()

                workflows.append(
                    workflow,
                )

                loaded_workflows.append(
                    workflow.workflow_name,
                )

            except Exception as exc:
                skipped_objects.append(
                    object_name,
                )

                errors.append(
                    {
                        "object_name": object_name,
                        "workflow_class": workflow_class.__name__,
                        "error_type": type(exc).__name__,
                        "message": str(exc),
                    }
                )

        return (
            workflows,
            PluginWorkflowLoadResult(
                module_name=module_name,
                loaded_workflows=tuple(sorted(set(loaded_workflows))),
                skipped_objects=tuple(sorted(set(skipped_objects))),
                errors=tuple(errors),
                metadata={
                    "loaded_count": len(set(loaded_workflows)),
                    "skipped_count": len(set(skipped_objects)),
                    "error_count": len(errors),
                    "include_imported_classes": include_imported_classes,
                },
            ),
        )

    def load_modules(
        self,
        module_names: list[str],
        include_imported_classes: bool = False,
    ) -> tuple[list[WorkflowGraphDefinition], list[PluginWorkflowLoadResult]]:
        workflows: list[WorkflowGraphDefinition] = []
        results: list[PluginWorkflowLoadResult] = []

        for module_name in module_names:
            module_workflows, result = self.load_module(
                module_name=module_name,
                include_imported_classes=include_imported_classes,
            )

            workflows.extend(
                module_workflows,
            )

            results.append(
                result,
            )

        return workflows, results

    def load_from_manifest(
        self,
        manifest: dict[str, Any],
    ) -> tuple[list[WorkflowGraphDefinition], list[PluginWorkflowLoadResult]]:
        modules = manifest.get(
            "workflow_modules",
            [],
        )

        if not isinstance(
            modules,
            list,
        ):
            raise TypeError("Plugin manifest field 'workflow_modules' must be a list.")

        include_imported_classes = bool(
            manifest.get(
                "include_imported_classes",
                False,
            )
        )

        return self.load_modules(
            module_names=[str(module_name) for module_name in modules],
            include_imported_classes=include_imported_classes,
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "loader": self.__class__.__name__,
        }
