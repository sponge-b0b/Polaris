from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from interfaces.cli.output import WorkflowOutputArtifact, output_path_for_format


def test_output_path_for_format_uses_safe_utc_timestamp_and_extension() -> None:
    path = output_path_for_format(
        "morning report",
        "markdown",
        now=datetime(
            2026,
            5,
            27,
            8,
            30,
            12,
            tzinfo=UTC,
        ),
        directory=Path(
            "/tmp/reports",
        ),
    )

    assert path == Path("/tmp/reports/morning_report_20260527T083012Z.md")


def test_output_path_for_format_sanitizes_workflow_name() -> None:
    path = output_path_for_format(
        "../bad workflow/name",
        "json",
        now=datetime(
            2026,
            5,
            27,
            8,
            30,
            12,
            tzinfo=UTC,
        ),
        directory=Path(
            "/tmp/reports",
        ),
    )

    assert path == Path("/tmp/reports/bad_workflow_name_20260527T083012Z.json")


def test_workflow_output_artifact_detects_binary_content() -> None:
    text_artifact = WorkflowOutputArtifact(
        output_format="markdown",
        path=Path(
            "report.md",
        ),
        content="# Report",
    )
    binary_artifact = WorkflowOutputArtifact(
        output_format="pdf",
        path=Path(
            "report.pdf",
        ),
        content=b"%PDF",
    )

    assert text_artifact.is_binary is False
    assert binary_artifact.is_binary is True


def test_emit_workflow_output_bundle_writes_text_artifact_and_stdout(
    tmp_path,
) -> None:
    from interfaces.cli.output import WorkflowOutputBundle, emit_workflow_output_bundle

    stdout_lines: list[str] = []
    status_lines: list[str] = []
    artifact = WorkflowOutputArtifact(
        output_format="markdown",
        path=tmp_path / "report.md",
        content="# Report",
    )
    bundle = WorkflowOutputBundle(
        stdout="# Report",
        artifact=artifact,
    )

    written_path = emit_workflow_output_bundle(
        bundle,
        stdout_emitter=stdout_lines.append,
        status_emitter=status_lines.append,
    )

    assert written_path == tmp_path / "report.md"
    assert stdout_lines == [
        "# Report",
    ]
    assert status_lines == [
        f"[output] wrote {tmp_path / 'report.md'}",
    ]
    assert (tmp_path / "report.md").read_text(
        encoding="utf-8",
    ) == "# Report"


def test_emit_workflow_output_bundle_writes_binary_artifact(
    tmp_path,
) -> None:
    from interfaces.cli.output import WorkflowOutputBundle, emit_workflow_output_bundle

    artifact = WorkflowOutputArtifact(
        output_format="pdf",
        path=tmp_path / "report.pdf",
        content=b"%PDF-test",
    )
    bundle = WorkflowOutputBundle(
        stdout="# Report",
        artifact=artifact,
    )

    emit_workflow_output_bundle(
        bundle,
        stdout_emitter=lambda _: None,
    )

    assert (tmp_path / "report.pdf").read_bytes() == b"%PDF-test"


def test_emit_workflow_output_bundle_writes_explicit_output_without_artifact(
    tmp_path,
) -> None:
    from interfaces.cli.output import WorkflowOutputBundle, emit_workflow_output_bundle

    bundle = WorkflowOutputBundle(
        stdout="plain stdout",
    )

    written_path = emit_workflow_output_bundle(
        bundle,
        explicit_output_path=tmp_path / "stdout.txt",
        stdout_emitter=lambda _: None,
    )

    assert written_path == tmp_path / "stdout.txt"
    assert (tmp_path / "stdout.txt").read_text(
        encoding="utf-8",
    ) == "plain stdout"
