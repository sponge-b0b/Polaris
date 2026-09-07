from __future__ import annotations

import ast
from pathlib import Path

DOMAIN_ROOT = Path(__file__).parents[3] / "src" / "polaris" / "domain"


def test_decisions_domain_has_no_outward_or_legacy_imports() -> None:
    forbidden = (
        "polaris.application",
        "polaris.infrastructure",
        "polaris.interfaces",
        "legacy",
        "sqlalchemy",
        "psycopg",
    )
    for path in (DOMAIN_ROOT / "decisions").glob("*.py"):
        tree = ast.parse(path.read_text())
        modules: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules.append(node.module)
        assert not any(
            module == blocked or module.startswith(f"{blocked}.")
            for module in modules
            for blocked in forbidden
        )


def test_old_investment_decisions_package_is_not_part_of_current_domain() -> None:
    assert not (DOMAIN_ROOT / "investment_decisions").exists()
