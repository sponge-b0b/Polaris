from __future__ import annotations

from datetime import datetime
from typing import Annotated
from typing import Any

import typer

from interfaces.cli.services.async_runner import run_cli_async
from application.rag.contracts.rag_operation_models import RagIngestOperationRequest
from application.rag.contracts.rag_operation_models import (
    RagProcessEmbeddingsOperationRequest,
)
from application.rag.contracts.rag_operation_models import (
    RagProcessGraphOperationRequest,
)
from application.rag.contracts.rag_operation_models import (
    RagRebuildProjectionOperationRequest,
)
from interfaces.cli.services.rag_command_service import RagAskCommandRequest
from interfaces.cli.services.rag_command_service import RagCommandService
from interfaces.cli.services.rag_command_service import render_rag_ask_result
from interfaces.cli.services.rag_command_service import render_rag_operation_result
from interfaces.cli.services.rag_command_service import render_rag_projection_readiness

rag_app = typer.Typer(
    help="Query the platform-native RAG pipeline.",
    no_args_is_help=True,
)


@rag_app.callback()
def rag_callback() -> None:
    return None


@rag_app.command(
    "ask",
    help="Ask a question against curated platform RAG records.",
)
def ask_rag(
    query: Annotated[
        str,
        typer.Argument(
            help="Question to answer from curated platform RAG context.",
        ),
    ],
    symbols: Annotated[
        list[str],
        typer.Option(
            "--symbol",
            "-s",
            help="Limit retrieval to one symbol. Repeat for multiple symbols.",
        ),
    ] = [],
    source_types: Annotated[
        list[str],
        typer.Option(
            "--source-type",
            help="Limit retrieval to one source type. Repeat for multiple types.",
        ),
    ] = [],
    source_tables: Annotated[
        list[str],
        typer.Option(
            "--source-table",
            help="Limit retrieval to one source table. Repeat for multiple tables.",
        ),
    ] = [],
    agent_names: Annotated[
        list[str],
        typer.Option(
            "--agent-name",
            help="Limit retrieval to one agent name. Repeat for multiple agents.",
        ),
    ] = [],
    report_types: Annotated[
        list[str],
        typer.Option(
            "--report-type",
            help="Limit retrieval to one report type. Repeat for multiple reports.",
        ),
    ] = [],
    workflow_name: Annotated[
        str | None,
        typer.Option(
            "--workflow-name",
            help="Limit retrieval to one workflow name.",
        ),
    ] = None,
    execution_id: Annotated[
        str | None,
        typer.Option(
            "--execution-id",
            help="Limit retrieval to one workflow execution id.",
        ),
    ] = None,
    runtime_id: Annotated[
        str | None,
        typer.Option(
            "--runtime-id",
            help="Limit retrieval to one runtime id.",
        ),
    ] = None,
    as_of_start: Annotated[
        str | None,
        typer.Option(
            "--as-of-start",
            help="Inclusive ISO datetime lower bound for source generated time.",
        ),
    ] = None,
    as_of_end: Annotated[
        str | None,
        typer.Option(
            "--as-of-end",
            help="Inclusive ISO datetime upper bound for source generated time.",
        ),
    ] = None,
    route: Annotated[
        str,
        typer.Option(
            "--route",
            help="Retrieval route to use.",
        ),
    ] = "hybrid",
    top_k: Annotated[
        int,
        typer.Option(
            "--top-k",
            min=1,
            help="Maximum number of retrieved contexts to use.",
        ),
    ] = 8,
    allow_web: Annotated[
        bool,
        typer.Option(
            "--web/--no-web",
            help="Permit transient open-source web fallback when curated context is insufficient.",
        ),
    ] = False,
) -> None:
    result = _run_cli_command(
        RagCommandService().ask(
            RagAskCommandRequest(
                query=query,
                symbols=tuple(symbols),
                source_types=tuple(source_types),
                source_tables=tuple(source_tables),
                agent_names=tuple(agent_names),
                report_types=tuple(report_types),
                workflow_name=workflow_name,
                execution_id=execution_id,
                runtime_id=runtime_id,
                as_of_start=_parse_datetime_option(
                    as_of_start,
                    "as_of_start",
                ),
                as_of_end=_parse_datetime_option(
                    as_of_end,
                    "as_of_end",
                ),
                route=route,
                top_k=top_k,
                allow_web=allow_web,
            )
        )
    )
    typer.echo(
        render_rag_ask_result(
            result,
        )
    )
    if not result.success:
        raise typer.Exit(
            code=1,
        )


@rag_app.command(
    "ingest",
    help="Ingest eligible curated PostgreSQL records into canonical RAG documents.",
)
def ingest_rag(
    source: Annotated[
        str,
        typer.Option(
            "--source",
            help="Curated source to ingest: reports, agent-signals, recommendations, market, macro, news, sentiment, portfolio, or backtests.",
        ),
    ],
    limit: Annotated[
        int | None,
        typer.Option(
            "--limit",
            min=1,
            help="Maximum number of eligible source records to ingest.",
        ),
    ] = None,
    queue_embedding_jobs: Annotated[
        bool,
        typer.Option(
            "--queue-embedding-jobs/--no-queue-embedding-jobs",
            help="Queue embedding projection jobs for generated chunks.",
        ),
    ] = True,
    queue_graph_jobs: Annotated[
        bool,
        typer.Option(
            "--queue-graph-jobs/--no-queue-graph-jobs",
            help="Queue Neo4j graph projection jobs for generated documents.",
        ),
    ] = True,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Show eligible records without persisting RAG documents.",
        ),
    ] = False,
) -> None:
    result = _run_cli_command(
        RagCommandService().ingest(
            RagIngestOperationRequest(
                source=source,
                limit=limit,
                queue_embedding_jobs=queue_embedding_jobs,
                queue_graph_jobs=queue_graph_jobs,
                dry_run=dry_run,
            )
        )
    )
    _render_operation_and_exit(
        result,
    )


@rag_app.command(
    "process-embeddings",
    help="Process queued PostgreSQL RAG embedding jobs into Qdrant projections.",
)
def process_rag_embeddings(
    batch_size: Annotated[
        int | None,
        typer.Option(
            "--batch-size",
            min=1,
            help="Maximum queued embedding jobs to process.",
        ),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Count queued embedding jobs without processing them.",
        ),
    ] = False,
) -> None:
    result = _run_cli_command(
        RagCommandService().process_embeddings(
            RagProcessEmbeddingsOperationRequest(
                batch_size=batch_size,
                dry_run=dry_run,
            )
        )
    )
    _render_operation_and_exit(
        result,
    )


@rag_app.command(
    "process-graph",
    help="Process queued PostgreSQL RAG graph projection jobs.",
)
def process_rag_graph(
    execute: Annotated[
        bool,
        typer.Option(
            "--execute",
            help="Execute graph projection processing. Without this flag, performs a dry run.",
        ),
    ] = False,
) -> None:
    result = _run_cli_command(
        RagCommandService().process_graph(
            RagProcessGraphOperationRequest(
                dry_run=not execute,
            )
        )
    )
    _render_operation_and_exit(
        result,
    )


@rag_app.command(
    "rebuild",
    help="Rebuild a derived RAG projection from PostgreSQL canonical records.",
)
def rebuild_rag_projection(
    projection: Annotated[
        str,
        typer.Option(
            "--projection",
            help="Projection to rebuild: qdrant or neo4j.",
        ),
    ],
    confirm_delete: Annotated[
        bool,
        typer.Option(
            "--confirm-delete",
            help="Confirm destructive projection cleanup. Without this flag, performs a dry run.",
        ),
    ] = False,
) -> None:
    result = _run_cli_command(
        RagCommandService().rebuild(
            RagRebuildProjectionOperationRequest(
                projection=projection,
                dry_run=not confirm_delete,
                confirm_delete=confirm_delete,
            )
        )
    )
    _render_operation_and_exit(
        result,
    )


@rag_app.command(
    "status",
    help="Show PostgreSQL, Qdrant, Neo4j, embedding, and reranker readiness.",
)
def rag_status() -> None:
    result = _run_cli_command(RagCommandService().status())
    typer.echo(render_rag_projection_readiness(result))
    if not result.ready:
        raise typer.Exit(code=1)


def _parse_datetime_option(
    value: str | None,
    field_name: str,
) -> datetime | None:
    if value is None:
        return None
    try:
        return datetime.fromisoformat(
            value.replace(
                "Z",
                "+00:00",
            )
        )
    except ValueError as exc:
        raise typer.BadParameter(
            f"{field_name} must be an ISO datetime.",
        ) from exc


def _render_operation_and_exit(
    result: Any,
) -> None:
    typer.echo(
        render_rag_operation_result(
            result,
        )
    )
    if not result.success:
        raise typer.Exit(
            code=1,
        )


def _run_cli_command(
    awaitable: Any,
) -> Any:
    return run_cli_async(
        awaitable,
    )
