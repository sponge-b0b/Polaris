from __future__ import annotations

import ast
from pathlib import Path

import pytest


@pytest.mark.parametrize(
    "module_path",
    (
        Path("application/decision_evidence/completed_workflow_assembly.py"),
        Path("application/decision_evidence/persistence.py"),
        Path(
            "core/storage/persistence/repositories/"
            "postgres_decision_evidence_persistence_repository.py"
        ),
    ),
)
def test_decision_evidence_telemetry_paths_do_not_catch_generic_exception(
    module_path: Path,
) -> None:
    tree = ast.parse(module_path.read_text())

    generic_exception_handlers = [
        handler
        for handler in ast.walk(tree)
        if isinstance(handler, ast.ExceptHandler)
        and isinstance(handler.type, ast.Name)
        and handler.type.id == "Exception"
    ]

    assert generic_exception_handlers == []
