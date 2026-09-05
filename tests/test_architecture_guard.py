from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from tests.architecture_guard import check_repository

REPO_ROOT = Path(__file__).resolve().parents[1]


def _write(root: Path, relative: str, source: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(source).lstrip(), encoding="utf-8")


def _rules(root: Path) -> set[str]:
    return {violation.rule for violation in check_repository(root)}


def test_current_greenfield_repository_satisfies_architecture_rules() -> None:
    violations = check_repository(REPO_ROOT)
    assert not violations, "\n".join(item.render() for item in violations)


@pytest.mark.parametrize(
    ("path", "dependency"),
    [
        ("src/polaris/domain/decisions/model.py", "polaris.application.use_cases"),
        ("src/polaris/domain/decisions/model.py", "polaris.infrastructure.persistence"),
        ("src/polaris/domain/decisions/model.py", "polaris.interfaces.cli"),
        (
            "src/polaris/application/use_cases/run.py",
            "polaris.infrastructure.persistence",
        ),
        ("src/polaris/application/use_cases/run.py", "polaris.interfaces.cli"),
        ("src/polaris/interfaces/cli.py", "polaris.infrastructure.persistence"),
        ("src/polaris/infrastructure/persistence/store.py", "polaris.interfaces.cli"),
    ],
)
def test_forbidden_layer_dependencies_fail(
    tmp_path: Path,
    path: str,
    dependency: str,
) -> None:
    _write(tmp_path, path, f"from {dependency} import Example\n")
    assert "ARCH-LAYER" in _rules(tmp_path)


@pytest.mark.parametrize(
    ("path", "dependency"),
    [
        ("src/polaris/application/use_cases/run.py", "polaris.domain.decisions"),
        ("src/polaris/interfaces/cli.py", "polaris.application.use_cases"),
        (
            "src/polaris/infrastructure/persistence/store.py",
            "polaris.application.ports",
        ),
        ("src/polaris/infrastructure/persistence/store.py", "polaris.domain.decisions"),
    ],
)
def test_valid_inward_dependencies_pass(
    tmp_path: Path,
    path: str,
    dependency: str,
) -> None:
    _write(tmp_path, path, f"from {dependency} import Example\n")
    assert check_repository(tmp_path) == ()


@pytest.mark.parametrize("module", ["fastapi", "typer"])
def test_application_cannot_depend_on_interface_framework(
    tmp_path: Path,
    module: str,
) -> None:
    _write(
        tmp_path,
        "src/polaris/application/use_cases/run.py",
        f"import {module}\n",
    )
    assert "ARCH-LAYER" in _rules(tmp_path)


@pytest.mark.parametrize(
    "path",
    [
        "src/polaris/application/use_cases/run.py",
        "tests/test_no_legacy.py",
    ],
)
def test_direct_legacy_imports_fail(tmp_path: Path, path: str) -> None:
    _write(tmp_path, path, "import legacy.v0_1.core\n")
    assert "ARCH-LEGACY" in _rules(tmp_path)


@pytest.mark.parametrize(
    "source",
    [
        'import importlib\nimportlib.import_module("legacy.v0_1.core")\n',
        'from importlib import import_module\nimport_module("legacy.v0_1.core")\n',
        '__import__("legacy.v0_1.core")\n',
        (
            "import importlib.util\n"
            'importlib.util.spec_from_file_location("x", "legacy/v0_1/x.py")\n'
        ),
        (
            "from importlib import import_module\n"
            "load_module = import_module\n"
            'load_module("legacy.v0_1.core")\n'
        ),
        (
            "from importlib import import_module\n"
            "load_module = import_module\n"
            "load_module_again = load_module\n"
            'load_module_again("legacy.v0_1.core")\n'
        ),
        (
            "from collections.abc import Callable\n"
            "from importlib import import_module\n"
            "load_module: Callable[[str], object] = import_module\n"
            'load_module("legacy.v0_1.core")\n'
        ),
        (
            "from importlib import import_module\n\n"
            "def load():\n"
            "    loader = import_module\n"
            '    return loader("legacy.v0_1.core")\n'
        ),
        'import runpy\nrunpy.run_module("legacy.v0_1.core")\n',
        'import runpy\nrunpy.run_path("legacy/v0_1/core.py")\n',
        (
            "from importlib.machinery import SourceFileLoader\n"
            'SourceFileLoader("legacy", "legacy/v0_1/core.py")\n'
        ),
    ],
)
def test_static_dynamic_legacy_loads_fail(tmp_path: Path, source: str) -> None:
    _write(tmp_path, "src/polaris/application/use_cases/run.py", source)
    assert "ARCH-LEGACY-DYNAMIC" in _rules(tmp_path)


def test_loader_alias_does_not_leak_between_function_scopes(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path,
        "src/polaris/application/use_cases/run.py",
        (
            "def first():\n"
            "    from importlib import import_module as loader\n"
            '    return loader("json")\n\n'
            "def second():\n"
            "    loader = print\n"
            '    loader("legacy.v0_1.core")\n'
        ),
    )
    assert check_repository(tmp_path) == ()


def test_legacy_convenience_wrapper_cannot_hide_dependency(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "src/polaris/application/legacy_bridge.py",
        "import legacy.v0_1.core\n",
    )
    _write(
        tmp_path,
        "src/polaris/application/use_cases/run.py",
        "from polaris.application.legacy_bridge import load\n",
    )

    violations = check_repository(tmp_path)
    assert any(
        item.rule == "ARCH-LEGACY"
        and item.source == "src/polaris/application/legacy_bridge.py"
        for item in violations
    )


def test_quarantined_legacy_files_are_not_scanned(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "legacy/v0_1/core/example.py",
        "from polaris.infrastructure.persistence import Store\n",
    )
    assert check_repository(tmp_path) == ()


@pytest.mark.parametrize(
    ("module", "family"),
    [
        ("sqlalchemy.orm", "persistence"),
        ("openai", "model-provider"),
        ("yfinance", "external-source"),
        ("auth0.authentication", "identity"),
        ("opentelemetry.trace", "observability"),
    ],
)
def test_inward_vendor_dependencies_fail(
    tmp_path: Path,
    module: str,
    family: str,
) -> None:
    _write(
        tmp_path,
        "src/polaris/application/ports/example.py",
        f"from {module} import NativeType\n",
    )
    violations = check_repository(tmp_path)
    assert any(
        item.rule == "ARCH-INWARD-VENDOR" and family in item.detail
        for item in violations
    )


@pytest.mark.parametrize(
    ("module", "family"),
    [
        ("sqlalchemy.orm", "persistence"),
        ("openai", "model-provider"),
        ("yfinance", "external-source"),
        ("auth0.authentication", "identity"),
        ("opentelemetry.trace", "observability"),
    ],
)
def test_interface_cannot_bypass_application_through_infrastructure_vendor(
    tmp_path: Path,
    module: str,
    family: str,
) -> None:
    _write(
        tmp_path,
        "src/polaris/interfaces/api.py",
        f"from {module} import NativeType\n",
    )

    violations = check_repository(tmp_path)
    assert any(
        item.rule == "ARCH-INTERFACE-INFRASTRUCTURE"
        and family in item.detail
        and module in item.detail
        for item in violations
    )


def test_standard_library_and_internal_semantic_types_pass(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "src/polaris/application/ports/query.py",
        """
        from datetime import datetime
        from polaris.domain.decisions import InvestmentDecisionId

        def load(
            decision_id: InvestmentDecisionId,
            known_at: datetime,
        ) -> None:
            pass
        """,
    )
    assert check_repository(tmp_path) == ()


@pytest.mark.parametrize(
    "source",
    [
        "class JobId: pass\nInvestmentDecisionId = JobId\n",
        "class ReportId: pass\ndecision_id: ReportId\n",
        ("class RunId: pass\n\ndef load(decision_id: RunId) -> None:\n    pass\n"),
        ("class RuntimeIdentifier: pass\nInvestmentDecisionId = RuntimeIdentifier\n"),
        (
            "from typing import TypeAlias\n"
            "class WorkflowId: pass\n"
            "InvestmentDecisionId: TypeAlias = WorkflowId\n"
        ),
    ],
)
def test_technical_identity_cannot_substitute_for_decision_identity(
    tmp_path: Path,
    source: str,
) -> None:
    _write(tmp_path, "src/polaris/domain/decisions/identity.py", source)
    assert "ARCH-DECISION-IDENTITY" in _rules(tmp_path)


def test_investment_decision_id_field_cannot_use_runtime_identity(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path,
        "src/polaris/domain/decisions/model.py",
        ("class RunId: pass\n\nclass InvestmentDecision:\n    id: RunId\n"),
    )
    assert "ARCH-DECISION-IDENTITY" in _rules(tmp_path)


def test_investment_decision_local_alias_cannot_hide_runtime_identity(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path,
        "src/polaris/domain/decisions/model.py",
        (
            "class RunId: pass\n\n"
            "class InvestmentDecision:\n"
            "    RuntimeIdentity = RunId\n"
            "    id: RuntimeIdentity\n"
        ),
    )
    assert "ARCH-DECISION-IDENTITY" in _rules(tmp_path)


def test_decision_identity_alias_chain_cannot_hide_runtime_identity(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path,
        "src/polaris/domain/decisions/identity.py",
        (
            "class RunId: pass\n"
            "RuntimeIdentity = RunId\n"
            "InvestmentDecisionId = RuntimeIdentity\n"
        ),
    )
    assert "ARCH-DECISION-IDENTITY" in _rules(tmp_path)


def test_python_312_type_alias_cannot_use_runtime_identity(tmp_path: Path) -> None:
    if not hasattr(__import__("ast"), "TypeAlias"):
        pytest.skip("requires Python 3.12 AST type-alias support")

    _write(
        tmp_path,
        "src/polaris/domain/decisions/identity.py",
        "class RunId: pass\ntype InvestmentDecisionId = RunId\n",
    )
    assert "ARCH-DECISION-IDENTITY" in _rules(tmp_path)


def test_current_migration_cannot_import_legacy_lineage(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "db/migrations/0001_initial.py",
        "from legacy.v0_1.core.database import metadata\n",
    )
    rules = _rules(tmp_path)
    assert "ARCH-LEGACY" in rules
    assert "ARCH-MIGRATION-LEGACY" in rules


def test_current_migration_cannot_runtime_load_legacy_lineage(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "db/migrations/0001_initial.py",
        (
            "from importlib import import_module\n"
            'legacy_schema = import_module("legacy.v0_1.schema")\n'
        ),
    )
    rules = _rules(tmp_path)
    assert "ARCH-LEGACY-DYNAMIC" in rules
    assert "ARCH-MIGRATION-LEGACY" in rules


def test_migration_legacy_object_definition_alone_is_not_reuse(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path,
        "db/migrations/0001_initial.py",
        "legacy_metadata = object()\n",
    )
    assert check_repository(tmp_path) == ()


def test_current_migration_cannot_reuse_legacy_schema_object(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "db/migrations/0001_initial.py",
        "legacy_metadata = object()\ncurrent_metadata = legacy_metadata\n",
    )
    assert "ARCH-MIGRATION-LEGACY-SCHEMA" in _rules(tmp_path)


def test_fresh_current_migration_and_quarantined_history_pass(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "db/migrations/0001_initial.py",
        'TABLE_NAME = "investment_decisions"\n',
    )
    _write(
        tmp_path,
        "legacy/v0_1/migrations/0001_old.py",
        "legacy_metadata = object()\n",
    )
    assert check_repository(tmp_path) == ()


def test_scan_failure_is_reported_as_architecture_violation(tmp_path: Path) -> None:
    path = tmp_path / "src/polaris/domain/broken.py"
    path.parent.mkdir(parents=True)
    path.write_text("def broken(:\n", encoding="utf-8")

    violations = check_repository(tmp_path)
    assert len(violations) == 1
    assert violations[0].rule == "ARCH-SCAN"
    assert violations[0].source == "src/polaris/domain/broken.py"


def test_diagnostic_names_source_dependency_and_rule(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "src/polaris/domain/decisions/model.py",
        "from polaris.application.use_cases import Run\n",
    )

    rendered = check_repository(tmp_path)[0].render()
    assert "src/polaris/domain/decisions/model.py:1" in rendered
    assert "ARCH-LAYER" in rendered
    assert "domain may not depend on application" in rendered
