from __future__ import annotations

from typing import Annotated
from typing import Any

import typer

from application.ai_optimization import AiOptimizationTarget
from core.storage.persistence.ai_artifacts import AiArtifactType
from interfaces.cli.services.ai_command_service import AiCommandService
from interfaces.cli.services.ai_command_service import render_ai_artifact_command_result
from interfaces.cli.services.ai_command_service import render_ai_artifacts
from interfaces.cli.services.ai_command_service import render_ai_optimize_result
from interfaces.cli.services.async_runner import run_cli_async

ai_app = typer.Typer(
    help="Run AI optimization workbench tasks and manage prompt/program artifacts.",
    no_args_is_help=True,
)
ai_artifacts_app = typer.Typer(
    help="Inspect, approve, activate, and deactivate AI prompt/program artifacts.",
    no_args_is_help=True,
)
ai_app.add_typer(ai_artifacts_app, name="artifacts")


@ai_app.callback()
def ai_callback() -> None:
    return None


@ai_app.command(
    "optimize",
    help="Run one explicit DSPy optimization workbench pass.",
)
def optimize(
    target: Annotated[
        AiOptimizationTarget,
        typer.Option(
            "--target",
            help="AI optimization target, such as rag_answer_generation.",
        ),
    ],
    dataset: Annotated[
        str,
        typer.Option(
            "--dataset",
            help="Canonical evaluation dataset name or persisted dataset id.",
        ),
    ],
    model: Annotated[
        str | None,
        typer.Option(
            "--model",
            help="Optional DSPy optimization model override.",
        ),
    ] = None,
    prompt_name: Annotated[
        str | None,
        typer.Option(
            "--prompt-name",
            help="Optional prompt name stored in the DSPy artifact manifest.",
        ),
    ] = None,
    prompt_version: Annotated[
        str,
        typer.Option(
            "--prompt-version",
            help="Prompt version stored in the DSPy artifact manifest.",
        ),
    ] = "v1",
    artifact_name: Annotated[
        str | None,
        typer.Option(
            "--artifact-name",
            help="Optional artifact name override.",
        ),
    ] = None,
    artifact_version: Annotated[
        str,
        typer.Option(
            "--artifact-version",
            help="Artifact version to persist for the generated artifact.",
        ),
    ] = "v1",
    max_cases: Annotated[
        int | None,
        typer.Option(
            "--max-cases",
            min=1,
            help="Optional maximum number of persisted evaluation cases to train on.",
        ),
    ] = None,
    timeout_seconds: Annotated[
        float | None,
        typer.Option(
            "--timeout-seconds",
            min=1.0,
            help="Optional DeepEval timeout override in seconds.",
        ),
    ] = None,
) -> None:
    result = _run_cli_command(
        AiCommandService().optimize(
            target=target.value,
            dataset=dataset,
            model=model,
            prompt_name=prompt_name,
            prompt_version=prompt_version,
            artifact_name=artifact_name,
            artifact_version=artifact_version,
            max_cases=max_cases,
            timeout_seconds=timeout_seconds,
        )
    )
    typer.echo(render_ai_optimize_result(result))
    if not result.success:
        raise typer.Exit(1)


@ai_artifacts_app.command(
    "list",
    help="List persisted AI prompt/program artifacts.",
)
def list_artifacts(
    target: Annotated[
        str | None,
        typer.Option(
            "--target",
            help="Optional target component filter.",
        ),
    ] = None,
    artifact_type: Annotated[
        AiArtifactType | None,
        typer.Option(
            "--type",
            help="Optional artifact type filter.",
        ),
    ] = None,
    active: Annotated[
        bool | None,
        typer.Option(
            "--active/--inactive",
            help="Optional active-state filter.",
        ),
    ] = None,
    limit: Annotated[
        int,
        typer.Option(
            "--limit",
            min=1,
            help="Maximum number of artifacts to display.",
        ),
    ] = 20,
) -> None:
    result = _run_cli_command(
        AiCommandService().list_artifacts(
            target_component=target,
            artifact_type=None if artifact_type is None else artifact_type.value,
            active=active,
            limit=limit,
        )
    )
    typer.echo(render_ai_artifacts(result))
    if not result.success:
        raise typer.Exit(1)


@ai_artifacts_app.command(
    "approve",
    help="Approve an artifact for possible later activation.",
)
def approve_artifact(
    artifact_id: Annotated[str, typer.Argument(help="AI artifact id to approve.")],
    approved_by: Annotated[
        str,
        typer.Option(
            "--approved-by",
            help="Reviewer identifier to persist in audit metadata.",
        ),
    ] = "cli",
) -> None:
    result = _run_cli_command(
        AiCommandService().approve_artifact(
            artifact_id,
            approved_by=approved_by,
        )
    )
    typer.echo(render_ai_artifact_command_result(result))
    if not result.success:
        raise typer.Exit(1)


@ai_artifacts_app.command(
    "activate",
    help="Activate one approved artifact for runtime discovery.",
)
def activate_artifact(
    artifact_id: Annotated[
        str, typer.Argument(help="Approved AI artifact id to activate.")
    ],
) -> None:
    result = _run_cli_command(AiCommandService().activate_artifact(artifact_id))
    typer.echo(render_ai_artifact_command_result(result))
    if not result.success:
        raise typer.Exit(1)


@ai_artifacts_app.command(
    "deactivate",
    help="Deactivate an active AI prompt/program artifact.",
)
def deactivate_artifact(
    artifact_id: Annotated[str, typer.Argument(help="AI artifact id to deactivate.")],
) -> None:
    result = _run_cli_command(AiCommandService().deactivate_artifact(artifact_id))
    typer.echo(render_ai_artifact_command_result(result))
    if not result.success:
        raise typer.Exit(1)


def _run_cli_command(awaitable: Any) -> Any:
    return run_cli_async(awaitable)
