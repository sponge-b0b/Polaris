from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.runtime.events.event_bus import EventBus
from core.storage.persistence.completed_run_archive import CompletedRunArchive
from core.workflow.bootstrap.workflow_bootstrap import (
    WorkflowBootstrapConfig,
    WorkflowBootstrapResult,
    build_workflow_runtime,
)
from core.workflow.models.workflow_graph_definition import (
    WorkflowGraphDefinition,
)


@dataclass(frozen=True, slots=True)
class WorkflowModuleConfig:
    """
    Workflow module configuration.

    This is the application-level module wrapper around workflow bootstrap.
    """

    checkpoint_dir: str = "storage/checkpoints"

    enable_checkpoints: bool = True


class WorkflowModule:
    """
    Application workflow module.

    PURPOSE
    ============================================================
    Provides a stable application-level entrypoint for wiring the
    workflow runtime stack.

    USED BY
    ============================================================
    - API startup
    - CLI startup
    - scheduler startup
    - notebook/bootstrap scripts
    - integration tests

    DOES NOT
    ============================================================
    - execute workflows automatically
    - define business workflows
    - contain RuntimeNode logic
    """

    def __init__(
        self,
        config: WorkflowModuleConfig | None = None,
        workflow_definitions: list[WorkflowGraphDefinition] | None = None,
        workflow_tags: dict[str, tuple[str, ...]] | None = None,
        workflow_metadata: dict[str, dict[str, Any]] | None = None,
        event_bus: EventBus | None = None,
        archive: CompletedRunArchive | None = None,
        overwrite: bool = False,
    ) -> None:
        self.config = config or WorkflowModuleConfig()
        self.workflow_definitions = workflow_definitions or []
        self.workflow_tags = workflow_tags or {}
        self.workflow_metadata = workflow_metadata or {}
        self.event_bus = event_bus
        self.archive = archive
        self.overwrite = overwrite

        self._bootstrap_result: WorkflowBootstrapResult | None = None

    # ========================================================
    # STARTUP
    # ========================================================

    def start(
        self,
    ) -> WorkflowBootstrapResult:
        """
        Build workflow runtime stack and register configured workflows.
        """

        if self._bootstrap_result is not None:
            return self._bootstrap_result

        self._bootstrap_result = build_workflow_runtime(
            workflow_definitions=self.workflow_definitions,
            config=WorkflowBootstrapConfig(
                checkpoint_dir=self.config.checkpoint_dir,
                enable_checkpoints=self.config.enable_checkpoints,
            ),
            event_bus=self.event_bus,
            archive=self.archive,
            workflow_tags=self.workflow_tags,
            workflow_metadata=self.workflow_metadata,
            overwrite=self.overwrite,
        )

        return self._bootstrap_result

    # ========================================================
    # ACCESSORS
    # ========================================================

    @property
    def bootstrap_result(
        self,
    ) -> WorkflowBootstrapResult:
        if self._bootstrap_result is None:
            raise RuntimeError("WorkflowModule has not been started.")

        return self._bootstrap_result

    @property
    def facade(
        self,
    ):
        return self.bootstrap_result.facade

    @property
    def event_bus_instance(
        self,
    ) -> EventBus:
        return self.bootstrap_result.event_bus

    @property
    def archive_instance(
        self,
    ) -> CompletedRunArchive:
        return self.bootstrap_result.archive

    # ========================================================
    # REGISTRATION AFTER STARTUP
    # ========================================================

    def register_workflow(
        self,
        workflow_definition: WorkflowGraphDefinition,
        tags: tuple[str, ...] = (),
        metadata: dict[str, Any] | None = None,
        overwrite: bool = False,
    ) -> None:
        """
        Register workflow after module startup.
        """

        self.facade.register_workflow(
            workflow_definition=workflow_definition,
            tags=tags,
            metadata=metadata,
            overwrite=overwrite,
        )

    # ========================================================
    # RESET
    # ========================================================

    def reset(
        self,
    ) -> None:
        """
        Reset bootstrapped runtime.

        Useful for tests.
        """

        self._bootstrap_result = None


# ============================================================
# CONVENIENCE FUNCTION
# ============================================================


def create_workflow_module(
    config: WorkflowModuleConfig | None = None,
    workflow_definitions: list[WorkflowGraphDefinition] | None = None,
    workflow_tags: dict[str, tuple[str, ...]] | None = None,
    workflow_metadata: dict[str, dict[str, Any]] | None = None,
    event_bus: EventBus | None = None,
    archive: CompletedRunArchive | None = None,
    overwrite: bool = False,
) -> WorkflowModule:
    """
    Convenience factory for app startup.
    """

    return WorkflowModule(
        config=config,
        workflow_definitions=workflow_definitions,
        workflow_tags=workflow_tags,
        workflow_metadata=workflow_metadata,
        event_bus=event_bus,
        archive=archive,
        overwrite=overwrite,
    )
