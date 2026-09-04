from __future__ import annotations

from typing import Annotated, Any

import typer

from interfaces.cli.services.async_runner import run_cli_async
from interfaces.cli.services.evaluation_command_service import (
    EvaluationCommandService,
    render_evaluation_dataset_seed_result,
    render_evaluation_datasets,
    render_evaluation_results,
    render_evaluation_run_result,
    render_evaluation_status,
)

evaluation_app = typer.Typer(
    help="Run and inspect Polaris LLM evaluations.",
    no_args_is_help=True,
)
evaluation_datasets_app = typer.Typer(
    help="Inspect canonical evaluation datasets.",
    no_args_is_help=True,
)
evaluation_app.add_typer(evaluation_datasets_app, name="datasets")


@evaluation_app.callback()
def evaluation_callback() -> None:
    return None


@evaluation_app.command(
    "status",
    help="Show DeepEval and canonical evaluation dataset readiness.",
)
def evaluation_status() -> None:
    result = _run_cli_command(EvaluationCommandService().status())
    typer.echo(render_evaluation_status(result))


@evaluation_datasets_app.command(
    "list",
    help="List canonical evaluation datasets and persisted case counts.",
)
def list_datasets() -> None:
    result = _run_cli_command(EvaluationCommandService().list_datasets())
    typer.echo(render_evaluation_datasets(result))
    if not result.success:
        raise typer.Exit(1)


@evaluation_datasets_app.command(
    "seed",
    help="Seed canonical evaluation datasets from source-controlled fixtures.",
)
def seed_datasets(
    dataset: Annotated[
        str | None,
        typer.Option(
            "--dataset",
            help="Optional canonical dataset name, such as golden_rag_questions.",
        ),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Load and count fixture records without writing to PostgreSQL.",
        ),
    ] = False,
) -> None:
    result = _run_cli_command(
        EvaluationCommandService().seed_datasets(dataset, dry_run=dry_run)
    )
    typer.echo(render_evaluation_dataset_seed_result(result))
    if not result.success:
        raise typer.Exit(1)


@evaluation_app.command(
    "run",
    help="Run evaluation for a persisted canonical dataset.",
)
def run_dataset(
    dataset: Annotated[
        str,
        typer.Option(
            "--dataset",
            help="Canonical evaluation dataset name, such as golden_rag_questions.",
        ),
    ],
) -> None:
    result = _run_cli_command(EvaluationCommandService().run_dataset(dataset))
    typer.echo(render_evaluation_run_result(result))
    if not result.success:
        raise typer.Exit(1)


@evaluation_app.command(
    "run-rag",
    help="Run RAG evaluation for one persisted evaluation case.",
)
def run_rag_case(
    case_id: Annotated[
        str,
        typer.Option(
            "--case",
            help="Persisted RAG evaluation case id.",
        ),
    ],
) -> None:
    result = _run_cli_command(EvaluationCommandService().run_rag_case(case_id))
    typer.echo(render_evaluation_run_result(result))
    if not result.success:
        raise typer.Exit(1)


@evaluation_app.command(
    "run-latest-rag",
    help="Run evaluation for the latest persisted RAG evaluation case.",
)
def run_latest_rag() -> None:
    result = _run_cli_command(EvaluationCommandService().run_latest_rag())
    typer.echo(render_evaluation_run_result(result))
    if not result.success:
        raise typer.Exit(1)


@evaluation_app.command(
    "results",
    help="Show persisted evaluation results for one run.",
)
def evaluation_results(
    run_id: Annotated[
        str,
        typer.Option(
            "--run",
            help="Persisted evaluation run id.",
        ),
    ],
) -> None:
    result = _run_cli_command(EvaluationCommandService().results(run_id))
    typer.echo(render_evaluation_results(result))
    if not result.success:
        raise typer.Exit(1)


def _run_cli_command(awaitable: Any) -> Any:
    return run_cli_async(awaitable)
