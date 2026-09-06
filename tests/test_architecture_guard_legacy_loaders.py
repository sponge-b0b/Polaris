from __future__ import annotations

from pathlib import Path
from textwrap import indent

import pytest

from tests.architecture_guard import check_repository
from tests.test_architecture_guard import _rules, _write

# Authority-derived from Spec #277 US-22 / ID-4 / TD-4 and Review #283 RB-3.
# This matrix is intentionally independent of architecture_guard.LOADERS.
LEGACY_LOADER_CASES = (
    (
        "dunder-import",
        "",
        "__import__({target})",
        "legacy.v0_1.core",
        "json",
    ),
    (
        "import-module",
        "from importlib import import_module\n",
        "import_module({target})",
        "legacy.v0_1.core",
        "json",
    ),
    (
        "source-file-loader",
        "from importlib.machinery import SourceFileLoader\n",
        'SourceFileLoader("current", {target})',
        "legacy/v0_1/core.py",
        "src/polaris/core.py",
    ),
    (
        "spec-from-file-location",
        "from importlib.util import spec_from_file_location\n",
        'spec_from_file_location("current", {target})',
        "legacy/v0_1/core.py",
        "src/polaris/core.py",
    ),
    (
        "run-module",
        "from runpy import run_module\n",
        "run_module({target})",
        "legacy.v0_1.core",
        "json",
    ),
    (
        "run-path",
        "from runpy import run_path\n",
        "run_path({target})",
        "legacy/v0_1/core.py",
        "tools/run.py",
    ),
)
TARGET_FORMS = ("direct-literal", "one-hop-bound-literal")
LEXICAL_SCOPES = ("module", "sync-function", "async-function", "class")
TARGET_KINDS = ("legacy", "non-legacy")


def _loader_source(
    prelude: str,
    call_template: str,
    target: str,
    target_form: str,
    scope: str,
) -> str:
    target_expression = repr(target)
    statements = ""
    if target_form == "one-hop-bound-literal":
        statements += f"TARGET = {target!r}\n"
        target_expression = "TARGET"
    statements += f"{call_template.format(target=target_expression)}\n"

    if scope == "module":
        body = statements
    elif scope == "sync-function":
        body = "def exercise():\n" + indent(statements, "    ")
    elif scope == "async-function":
        body = "async def exercise():\n" + indent(statements, "    ")
    elif scope == "class":
        body = "class Exercise:\n" + indent(statements, "    ")
    else:
        raise AssertionError(f"unknown lexical scope: {scope}")

    return prelude + body


@pytest.mark.parametrize(
    ("loader_name", "prelude", "call_template", "legacy_target", "safe_target"),
    LEGACY_LOADER_CASES,
)
@pytest.mark.parametrize("target_form", TARGET_FORMS)
@pytest.mark.parametrize("scope", LEXICAL_SCOPES)
@pytest.mark.parametrize("target_kind", TARGET_KINDS)
def test_root_complete_static_legacy_loader_matrix(
    tmp_path: Path,
    loader_name: str,
    prelude: str,
    call_template: str,
    legacy_target: str,
    safe_target: str,
    target_form: str,
    scope: str,
    target_kind: str,
) -> None:
    target = legacy_target if target_kind == "legacy" else safe_target
    source = _loader_source(prelude, call_template, target, target_form, scope)
    _write(tmp_path, "src/polaris/application/use_cases/run.py", source)

    rules = _rules(tmp_path)
    if target_kind == "legacy":
        assert "ARCH-LEGACY-DYNAMIC" in rules, (
            f"{loader_name}/{target_form}/{scope} did not reject {target!r}"
        )
    else:
        assert "ARCH-LEGACY-DYNAMIC" not in rules, (
            f"{loader_name}/{target_form}/{scope} rejected adjacent-valid {target!r}"
        )


@pytest.mark.parametrize("scope", ("module", "class"))
def test_later_import_shadow_does_not_hide_earlier_legacy_loader(
    tmp_path: Path,
    scope: str,
) -> None:
    statements = (
        'importlib.import_module("legacy.v0_1.core")\nimport json as importlib\n'
    )
    body = (
        statements
        if scope == "module"
        else "class Loader:\n" + indent(statements, "    ")
    )
    _write(
        tmp_path,
        "src/polaris/application/use_cases/run.py",
        "import importlib\n" + body,
    )
    assert "ARCH-LEGACY-DYNAMIC" in _rules(tmp_path)


def test_loader_alias_rebinding_to_nonloader_clears_loader_identity(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path,
        "src/polaris/application/use_cases/run.py",
        (
            "from importlib import import_module\n"
            "loader = import_module\n"
            "loader = print\n"
            'loader("legacy.v0_1.core")\n'
        ),
    )
    assert check_repository(tmp_path) == ()


def test_function_local_import_shadow_still_masks_outer_loader(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path,
        "src/polaris/application/use_cases/run.py",
        (
            "import importlib\n\n"
            "def load():\n"
            '    importlib.import_module("legacy.v0_1.core")\n'
            "    import json as importlib\n"
        ),
    )
    assert check_repository(tmp_path) == ()


def test_bound_legacy_target_survives_loader_alias_chain(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "src/polaris/application/use_cases/run.py",
        (
            "from importlib import import_module\n"
            "loader = import_module\n"
            "loader_again = loader\n"
            'TARGET = "legacy.v0_1.core"\n'
            "loader_again(TARGET)\n"
        ),
    )
    assert "ARCH-LEGACY-DYNAMIC" in _rules(tmp_path)


def test_bound_legacy_target_in_migration_emits_both_violations(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path,
        "db/migrations/0001_initial.py",
        (
            "from importlib import import_module\n"
            'TARGET = "legacy.v0_1.schema"\n'
            "schema = import_module(TARGET)\n"
        ),
    )
    rules = _rules(tmp_path)
    assert "ARCH-LEGACY-DYNAMIC" in rules
    assert "ARCH-MIGRATION-LEGACY" in rules


def test_bound_target_rebinding_to_nonlegacy_is_allowed(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "src/polaris/application/use_cases/run.py",
        (
            "from importlib import import_module\n"
            'TARGET = "legacy.v0_1.core"\n'
            'TARGET = "json"\n'
            "import_module(TARGET)\n"
        ),
    )
    assert check_repository(tmp_path) == ()


def test_function_parameter_shadows_outer_legacy_binding(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "src/polaris/application/use_cases/run.py",
        (
            "from importlib import import_module\n"
            'TARGET = "legacy.v0_1.core"\n\n'
            "def load(TARGET: str):\n"
            "    return import_module(TARGET)\n"
        ),
    )
    assert check_repository(tmp_path) == ()


def test_function_local_binding_masks_outer_legacy_before_assignment(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path,
        "src/polaris/application/use_cases/run.py",
        (
            "from importlib import import_module\n"
            'TARGET = "legacy.v0_1.core"\n\n'
            "def load():\n"
            "    import_module(TARGET)\n"
            '    TARGET = "json"\n'
        ),
    )
    assert check_repository(tmp_path) == ()


def test_global_declaration_preserves_outer_legacy_binding(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "src/polaris/application/use_cases/run.py",
        (
            "from importlib import import_module\n"
            'TARGET = "legacy.v0_1.core"\n\n'
            "def load():\n"
            "    global TARGET\n"
            "    return import_module(TARGET)\n"
        ),
    )
    assert "ARCH-LEGACY-DYNAMIC" in _rules(tmp_path)


def test_class_binding_shadows_outer_legacy_binding(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "src/polaris/application/use_cases/run.py",
        (
            "from importlib import import_module\n"
            'TARGET = "legacy.v0_1.core"\n\n'
            "class Loader:\n"
            '    TARGET = "json"\n'
            "    import_module(TARGET)\n"
        ),
    )
    assert check_repository(tmp_path) == ()


def test_method_does_not_inherit_class_literal_binding(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "src/polaris/application/use_cases/run.py",
        (
            "from importlib import import_module\n"
            'TARGET = "json"\n\n'
            "class Loader:\n"
            '    TARGET = "legacy.v0_1.core"\n\n'
            "    def load(self):\n"
            "        return import_module(TARGET)\n"
        ),
    )
    assert check_repository(tmp_path) == ()
