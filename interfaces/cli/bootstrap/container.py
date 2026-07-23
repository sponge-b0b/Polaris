from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar

from dishka import Container

from application.projections.workflow_outputs import (
    subscribe_default_workflow_output_projection,
)
from config.provider_profiles import apply_provider_profile
from config.settings import Settings
from core.bootstrap.di_providers import application_sync_request_scope
from core.telemetry.emitters.bootstrap_configuration_telemetry import (
    configuration_setting_names,
    emergency_log_configuration_failure,
)
from core.workflow.bootstrap.workflow_bootstrap import (
    WorkflowBootstrapConfig,
    WorkflowBootstrapResult,
)
from interfaces.cli.bootstrap.settings import CliSettings
from workflows.catalog import get_builtin_workflows

DependencyT = TypeVar("DependencyT")


@dataclass(
    frozen=True,
    slots=True,
)
class CliRuntimeScope:
    """Dependencies owned by one CLI invocation."""

    runtime: WorkflowBootstrapResult
    request_container: Container

    def get(
        self,
        dependency_type: type[DependencyT],
    ) -> DependencyT:
        return self.request_container.get(dependency_type)


@asynccontextmanager
async def cli_runtime_scope(
    *,
    plugin_dirs: tuple[Path, ...] = (),
    autoload_plugins: bool = False,
    provider_profile: str | None = None,
) -> AsyncIterator[CliRuntimeScope]:
    """Open one canonical Dishka request scope for a CLI invocation."""

    try:
        cli_settings = CliSettings.from_env(
            plugin_dirs=plugin_dirs,
            autoload_plugins=autoload_plugins,
        )
        base_settings = Settings()
    except Exception as error:
        emergency_log_configuration_failure(
            component="cli_bootstrap",
            invalid_setting_names=configuration_setting_names(
                error,
                fallback=("environment",),
            ),
            error=error,
            details={"configuration_source": "environment"},
        )
        raise

    try:
        settings = apply_provider_profile(
            base_settings,
            provider_profile or base_settings.PROVIDER_PROFILE,
        )
    except Exception as error:
        emergency_log_configuration_failure(
            component="provider_profile",
            invalid_setting_names=("PROVIDER_PROFILE",),
            error=error,
            details={"configuration_source": "provider_profile"},
        )
        raise
    with application_sync_request_scope(
        settings,
        workflow_config=_workflow_bootstrap_config(cli_settings),
    ) as request_container:
        runtime = request_container.get(WorkflowBootstrapResult)
        subscribe_default_workflow_output_projection(
            event_bus=runtime.event_bus,
            observability_manager=runtime.observability_manager,
        )
        for workflow in get_builtin_workflows():
            await runtime.facade.register_workflow_async(
                workflow_definition=workflow,
                tags=("builtin",),
                metadata={"source": "workflows.catalog"},
                overwrite=True,
            )
        await _autoload_cli_plugins(runtime)
        yield CliRuntimeScope(
            runtime=runtime,
            request_container=request_container,
        )


async def _autoload_cli_plugins(runtime: WorkflowBootstrapResult) -> None:
    if not runtime.config.autoload_plugins:
        return
    for plugin_dir in runtime.config.plugin_dirs:
        await runtime.facade.load_plugins_from_dir(
            plugin_dir=plugin_dir,
            recursive=runtime.config.autoload_plugins_recursive,
            overwrite=runtime.config.autoload_plugin_overwrite,
            register_workflows=runtime.config.autoload_register_workflows,
        )


def _workflow_bootstrap_config(
    settings: CliSettings,
) -> WorkflowBootstrapConfig:
    return WorkflowBootstrapConfig(
        completed_run_retention_max_age_days=settings.completed_run_retention_max_age_days,
        completed_run_retention_max_count=settings.completed_run_retention_max_count,
        checkpoint_dir=settings.checkpoint_dir,
        artifact_dir=settings.artifact_dir,
        telemetry_jsonl_path=settings.telemetry_jsonl_path,
        autoload_plugins=settings.autoload_plugins,
        plugin_dirs=settings.plugin_dirs,
        enable_observability=settings.enable_observability,
        enable_opentelemetry=settings.enable_opentelemetry,
        enable_prometheus_metrics=settings.enable_prometheus_metrics,
        prometheus_metrics_host=settings.prometheus_metrics_host,
        prometheus_metrics_port=settings.prometheus_metrics_port,
        prometheus_metrics_path=settings.prometheus_metrics_path,
    )
