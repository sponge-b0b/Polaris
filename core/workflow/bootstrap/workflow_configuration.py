from __future__ import annotations

from core.workflow.bootstrap.workflow_runtime_components import WorkflowBootstrapConfig


class WorkflowBootstrapConfigurationError(ValueError):
    """Required workflow bootstrap configuration is invalid."""

    def __init__(
        self,
        invalid_setting_names: tuple[str, ...],
    ) -> None:
        self.invalid_setting_names = invalid_setting_names
        super().__init__(
            "Invalid required workflow bootstrap settings: "
            f"{', '.join(invalid_setting_names)}."
        )


def validate_required_workflow_configuration(
    config: WorkflowBootstrapConfig,
) -> None:
    invalid_setting_names: list[str] = []

    if (
        config.completed_run_retention_max_age_days is not None
        and config.completed_run_retention_max_age_days < 0
    ):
        invalid_setting_names.append("completed_run_retention_max_age_days")

    if (
        config.completed_run_retention_max_count is not None
        and config.completed_run_retention_max_count < 0
    ):
        invalid_setting_names.append("completed_run_retention_max_count")

    if config.enable_checkpoints and not config.checkpoint_dir.strip():
        invalid_setting_names.append("checkpoint_dir")

    if config.enable_artifacts and not config.artifact_dir.strip():
        invalid_setting_names.append("artifact_dir")

    if config.autoload_plugins and any(not path.strip() for path in config.plugin_dirs):
        invalid_setting_names.append("plugin_dirs")

    if invalid_setting_names:
        raise WorkflowBootstrapConfigurationError(
            tuple(invalid_setting_names),
        )


__all__ = [
    "WorkflowBootstrapConfigurationError",
    "validate_required_workflow_configuration",
]
