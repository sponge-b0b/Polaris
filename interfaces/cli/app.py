from __future__ import annotations

import typer

from interfaces.cli.commands.ai_command import ai_app
from interfaces.cli.commands.backtest_command import backtest_app
from interfaces.cli.commands.completed_runs_command import completed_runs_app
from interfaces.cli.commands.evaluation_command import evaluation_app
from interfaces.cli.commands.inspect_command import inspect_app
from interfaces.cli.commands.morning_report_command import morning_report
from interfaces.cli.commands.observability_command import observability_app
from interfaces.cli.commands.rag_command import rag_app
from interfaces.cli.commands.workflow_command import workflow_app


def create_app() -> typer.Typer:
    app = typer.Typer(
        name="polaris",
        help="Polaris Capital platform CLI.",
        no_args_is_help=True,
    )

    app.command(
        "morning-report",
        help=(
            "Run the morning report workflow. Terminal output, progress "
            "notifications, and interactive workflow control are enabled by "
            "default; --format writes an additional report file."
        ),
    )(
        morning_report,
    )
    app.add_typer(
        workflow_app,
        name="workflow",
    )
    app.add_typer(
        ai_app,
        name="ai",
    )
    app.add_typer(
        inspect_app,
        name="inspect",
    )
    app.add_typer(
        backtest_app,
        name="backtest",
    )
    app.add_typer(
        completed_runs_app,
        name="runs",
    )
    app.add_typer(
        completed_runs_app,
        name="completed-runs",
    )
    app.add_typer(
        rag_app,
        name="rag",
    )
    app.add_typer(
        observability_app,
        name="observability",
    )
    app.add_typer(
        evaluation_app,
        name="eval",
    )

    return app


app = create_app()
