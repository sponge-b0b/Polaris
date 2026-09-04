from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from interfaces.cli.output.workflow_output import WorkflowOutputBundle

TextEmitter = Callable[
    [str],
    None,
]


def emit_workflow_output_bundle(
    bundle: WorkflowOutputBundle,
    *,
    explicit_output_path: Path | None = None,
    stdout_emitter: TextEmitter,
    status_emitter: TextEmitter | None = None,
) -> Path | None:
    """
    Emit mandatory CLI stdout and write any selected file artifact.

    If an explicit output format produced an artifact, write that artifact. If no
    explicit format was selected but --output was supplied, persist the same
    stdout text while still rendering stdout to the terminal.
    """

    stdout_emitter(
        bundle.stdout,
    )

    if bundle.artifact is not None:
        path = bundle.artifact.path
        _write_content(
            path,
            bundle.artifact.content,
        )
        _emit_status(
            status_emitter,
            path,
        )
        return path

    if explicit_output_path is not None:
        _write_content(
            explicit_output_path,
            bundle.stdout,
        )
        _emit_status(
            status_emitter,
            explicit_output_path,
        )
        return explicit_output_path

    return None


def _write_content(
    path: Path,
    content: str | bytes,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if isinstance(
        content,
        bytes,
    ):
        path.write_bytes(
            content,
        )
        return

    path.write_text(
        content,
        encoding="utf-8",
    )


def _emit_status(
    status_emitter: TextEmitter | None,
    path: Path,
) -> None:
    if status_emitter is None:
        return

    status_emitter(
        f"[output] wrote {path}",
    )
