from __future__ import annotations

from typing import Annotated

import typer

from config.provider_profiles import apply_provider_profile
from config.settings import Settings
from interfaces.cli.bootstrap.container import cli_runtime_scope
from interfaces.cli.formatters.console_formatter import format_mapping
from interfaces.cli.formatters.json_formatter import format_json
from interfaces.cli.services.async_runner import run_cli_async

inspect_app = typer.Typer(
    help="Inspect CLI/runtime configuration.",
    no_args_is_help=True,
)


@inspect_app.command("config")
def inspect_config(
    output_format: Annotated[
        str,
        typer.Option(
            "--format",
            "-f",
            help="Output format: console or json.",
        ),
    ] = "console",
) -> None:
    settings = Settings()
    settings = apply_provider_profile(
        settings,
        settings.PROVIDER_PROFILE,
    )
    values = {
        "provider_profile": settings.PROVIDER_PROFILE or "custom",
        "macro_provider": settings.MACRO_PROVIDER,
        "market_data_provider": settings.MARKET_DATA_PROVIDER,
        "market_events_provider": settings.MARKET_EVENTS_PROVIDER,
        "news_provider": settings.NEWS_PROVIDER,
        "portfolio_provider": settings.PORTFOLIO_PROVIDER,
        "sentiment_provider": settings.SENTIMENT_PROVIDER,
    }

    if output_format == "json":
        typer.echo(
            format_json(
                values,
            )
        )
        return

    if output_format != "console":
        raise typer.BadParameter("inspect config supports console or json output")

    typer.echo(
        format_mapping(
            "Provider configuration:",
            values,
        )
    )


@inspect_app.command("runtime")
def inspect_runtime(
    output_format: Annotated[
        str,
        typer.Option(
            "--format",
            "-f",
            help="Output format: console or json.",
        ),
    ] = "console",
) -> None:
    values = run_cli_async(
        _inspect_runtime_values(),
    )

    if output_format == "json":
        typer.echo(
            format_json(
                values,
            )
        )
        return

    if output_format != "console":
        raise typer.BadParameter("inspect runtime supports console or json output")

    typer.echo(
        format_mapping(
            "Runtime configuration:",
            values,
        )
    )


async def _inspect_runtime_values() -> dict[str, bool | int]:
    async with cli_runtime_scope() as scope:
        runtime = scope.runtime
        return {
            "workflow_count": len(runtime.facade.list_workflows()),
            "policy_engine": runtime.policy_engine is not None,
            "governance_engine": runtime.governance_engine is not None,
            "telemetry": runtime.telemetry is not None,
            "observability_manager": runtime.observability_manager is not None,
            "runtime_node_count": len(runtime.runtime_node_factory.list_nodes()),
        }
