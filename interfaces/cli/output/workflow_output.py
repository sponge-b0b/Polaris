from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Literal

CliOutputFormat = Literal[
    "html",
    "json",
    "markdown",
    "pdf",
]

_OUTPUT_EXTENSIONS: dict[CliOutputFormat, str] = {
    "html": ".html",
    "json": ".json",
    "markdown": ".md",
    "pdf": ".pdf",
}


@dataclass(frozen=True, slots=True)
class WorkflowOutputArtifact:
    """
    CLI-boundary file artifact selected by an explicit output format.
    """

    output_format: CliOutputFormat
    path: Path
    content: str | bytes

    @property
    def is_binary(
        self,
    ) -> bool:
        return isinstance(
            self.content,
            bytes,
        )


@dataclass(frozen=True, slots=True)
class WorkflowOutputBundle:
    """
    CLI-boundary render result containing mandatory stdout and optional file output.
    """

    stdout: str
    artifact: WorkflowOutputArtifact | None = None


def output_path_for_format(
    workflow_name: str,
    output_format: CliOutputFormat,
    *,
    now: datetime | None = None,
    directory: Path | None = None,
) -> Path:
    """
    Build the default timestamped output path for an explicit CLI output format.
    """

    timestamp = _format_timestamp(
        now
        or datetime.now(
            UTC,
        )
    )
    safe_workflow_name = _safe_filename_component(
        workflow_name,
    )

    return (directory or Path.cwd()) / (
        f"{safe_workflow_name}_{timestamp}{_OUTPUT_EXTENSIONS[output_format]}"
    )


def _format_timestamp(
    value: datetime,
) -> str:
    if value.tzinfo is None:
        value = value.replace(
            tzinfo=UTC,
        )

    return value.astimezone(
        UTC,
    ).strftime(
        "%Y%m%dT%H%M%SZ",
    )


def _safe_filename_component(
    value: str,
) -> str:
    normalized = value.strip().replace(
        " ",
        "_",
    )
    safe = "".join(
        character if character.isalnum() or character in {"-", "_", "."} else "_"
        for character in normalized
    ).strip("._")

    return safe or "workflow"
