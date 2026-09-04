from __future__ import annotations

import subprocess
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[4]
_EXCLUDED_PATHS = {"NOTES.md"}
_RETIRED_PLATFORM_NAME = "".join(("ti", "tan"))


def test_project_owned_files_use_current_platform_branding() -> None:
    retired_name = _RETIRED_PLATFORM_NAME.casefold()
    path_findings: list[str] = []
    content_findings: list[str] = []

    for relative_name in _project_owned_paths():
        if retired_name in relative_name.casefold():
            path_findings.append(relative_name)

        path = _PROJECT_ROOT / relative_name
        if not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if retired_name in content.casefold():
            content_findings.append(relative_name)

    assert path_findings == []
    assert content_findings == []


def _project_owned_paths() -> tuple[str, ...]:
    result = subprocess.run(
        (
            "git",
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
            "-z",
        ),
        cwd=_PROJECT_ROOT,
        check=True,
        capture_output=True,
    )
    return tuple(
        relative_name
        for relative_name in result.stdout.decode().split("\0")
        if relative_name and relative_name not in _EXCLUDED_PATHS
    )
