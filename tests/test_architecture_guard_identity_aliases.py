from __future__ import annotations

import ast
from pathlib import Path
from textwrap import dedent

import pytest

from tests.architecture_guard import TECHNICAL_IDS, check_repository


def _write(root: Path, relative: str, source: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(source).lstrip(), encoding="utf-8")


def _rules(root: Path) -> set[str]:
    return {violation.rule for violation in check_repository(root)}


def _technical_type_name(normalized: str) -> str:
    suffix = "Identifier" if normalized.endswith("identifier") else "Id"
    stem = normalized.removesuffix(suffix.lower())
    return f"{stem.capitalize()}{suffix}"


TECHNICAL_TYPES = tuple(sorted(_technical_type_name(name) for name in TECHNICAL_IDS))

SUBSTITUTION_FORMS = (
    "direct",
    "local-assignment",
    "class-local",
    "type-alias",
    "import-alias",
)


def _substitution_source(technical_type: str, form: str) -> str:
    if form == "direct":
        return (
            f"class {technical_type}: pass\nInvestmentDecisionId = {technical_type}\n"
        )

    if form == "local-assignment":
        return (
            f"class {technical_type}: pass\n"
            f"TechnicalAlias = {technical_type}\n"
            "InvestmentDecisionId = TechnicalAlias\n"
        )

    if form == "class-local":
        return (
            f"class {technical_type}: pass\n\n"
            "class InvestmentDecision:\n"
            f"    TechnicalAlias = {technical_type}\n"
            "    id: TechnicalAlias\n"
        )

    if form == "type-alias":
        return (
            f"class {technical_type}: pass\n"
            f"type InvestmentDecisionId = {technical_type}\n"
        )

    if form == "import-alias":
        return (
            "from polaris.domain.runtime import "
            f"{technical_type} as InvestmentDecisionId\n"
        )

    raise AssertionError(f"unknown substitution form: {form}")


@pytest.mark.parametrize("technical_type", TECHNICAL_TYPES)
@pytest.mark.parametrize("form", SUBSTITUTION_FORMS)
def test_root_complete_identity_substitution_matrix(
    tmp_path: Path,
    technical_type: str,
    form: str,
) -> None:
    if form == "type-alias" and not hasattr(ast, "TypeAlias"):
        pytest.skip("requires Python 3.12 AST type-alias support")

    _write(
        tmp_path,
        "src/polaris/domain/decisions/identity.py",
        _substitution_source(technical_type, form),
    )

    assert "ARCH-DECISION-IDENTITY" in _rules(tmp_path)


def test_imported_technical_decision_id_parameter_is_rejected(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path,
        "src/polaris/domain/decisions/query.py",
        """
        from polaris.domain.runtime import RunId as DecisionId

        def load(decision_id: DecisionId) -> None:
            pass
        """,
    )
    assert "ARCH-DECISION-IDENTITY" in _rules(tmp_path)


def test_imported_technical_alias_cannot_type_investment_decision_id(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path,
        "src/polaris/domain/decisions/model.py",
        """
        from polaris.domain.runtime import RunId as RuntimeIdentity

        class InvestmentDecision:
            id: RuntimeIdentity
        """,
    )
    assert "ARCH-DECISION-IDENTITY" in _rules(tmp_path)


def test_function_local_import_alias_chain_is_rejected(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path,
        "src/polaris/domain/decisions/query.py",
        """
        def load() -> None:
            from polaris.domain.runtime import RunId as RuntimeIdentity

            Alias = RuntimeIdentity
            decision_id: Alias
        """,
    )
    assert "ARCH-DECISION-IDENTITY" in _rules(tmp_path)


def test_class_scope_import_can_bind_investment_decision_id(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path,
        "src/polaris/domain/decisions/model.py",
        """
        class InvestmentDecision:
            from polaris.domain.runtime import RunId as id
        """,
    )
    assert "ARCH-DECISION-IDENTITY" in _rules(tmp_path)


def test_class_scope_type_alias_id_rejects_imported_technical_alias(
    tmp_path: Path,
) -> None:
    if not hasattr(ast, "TypeAlias"):
        pytest.skip("requires Python 3.12 AST type-alias support")

    _write(
        tmp_path,
        "src/polaris/domain/decisions/model.py",
        """
        class InvestmentDecision:
            from polaris.domain.runtime import RunId as RuntimeIdentity
            type id = RuntimeIdentity
        """,
    )
    assert "ARCH-DECISION-IDENTITY" in _rules(tmp_path)


def test_semantic_import_as_investment_decision_id_is_allowed(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path,
        "src/polaris/domain/decisions/query.py",
        """
        from polaris.domain.decisions.identity import (
            SemanticIdentity as InvestmentDecisionId,
        )

        decision_id: InvestmentDecisionId
        """,
    )
    assert _rules(tmp_path) == set()


def test_semantic_import_can_shadow_technical_import_before_use(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path,
        "src/polaris/domain/decisions/query.py",
        """
        from polaris.domain.runtime import RunId as Identity
        from polaris.domain.decisions.identity import (
            InvestmentDecisionId as Identity,
        )

        decision_id: Identity
        """,
    )
    assert _rules(tmp_path) == set()


def test_later_technical_import_does_not_taint_earlier_semantic_use(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path,
        "src/polaris/domain/decisions/query.py",
        """
        from polaris.domain.decisions.identity import (
            InvestmentDecisionId as Identity,
        )

        decision_id: Identity

        from polaris.domain.runtime import RunId as Identity
        """,
    )
    assert _rules(tmp_path) == set()


def test_semantic_assignment_can_shadow_imported_technical_alias(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path,
        "src/polaris/domain/decisions/query.py",
        """
        from polaris.domain.decisions.identity import InvestmentDecisionId
        from polaris.domain.runtime import RunId as Identity

        Identity = InvestmentDecisionId
        decision_id: Identity
        """,
    )
    assert _rules(tmp_path) == set()


def test_method_local_import_named_id_is_not_class_identity_by_itself(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path,
        "src/polaris/domain/decisions/model.py",
        """
        class InvestmentDecision:
            def correlate(self) -> None:
                from polaris.domain.runtime import RunId as id
                reveal = id
        """,
    )
    assert _rules(tmp_path) == set()


@pytest.mark.parametrize(
    "statement",
    [
        "id = RuntimeIdentity",
        "id: RuntimeIdentity",
    ],
)
def test_method_local_id_can_remain_technical_provenance(
    tmp_path: Path,
    statement: str,
) -> None:
    _write(
        tmp_path,
        "src/polaris/domain/decisions/model.py",
        (
            "from polaris.domain.runtime import RunId as RuntimeIdentity\n\n"
            "class InvestmentDecision:\n"
            "    def correlate(self) -> None:\n"
            f"        {statement}\n"
        ),
    )

    assert _rules(tmp_path) == set()


@pytest.mark.parametrize(
    "decision_class",
    [
        "InvestmentDecisionId",
        "DecisionId",
    ],
)
def test_decision_identity_class_cannot_inherit_technical_identity(
    tmp_path: Path,
    decision_class: str,
) -> None:
    _write(
        tmp_path,
        "src/polaris/domain/decisions/identity.py",
        (f"class RunId: pass\nclass {decision_class}(RunId): pass\n"),
    )
    assert "ARCH-DECISION-IDENTITY" in _rules(tmp_path)


def test_decision_id_class_cannot_inherit_imported_technical_alias(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path,
        "src/polaris/domain/decisions/identity.py",
        """
        from polaris.domain.runtime import RunId as RuntimeIdentity

        class DecisionId(RuntimeIdentity):
            pass
        """,
    )
    assert "ARCH-DECISION-IDENTITY" in _rules(tmp_path)


def test_investment_decision_id_annotated_initializer_rejects_technical_alias(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path,
        "src/polaris/domain/decisions/model.py",
        """
        from polaris.domain.decisions.identity import InvestmentDecisionId
        from polaris.domain.runtime import RunId as RuntimeIdentity

        class InvestmentDecision:
            id: InvestmentDecisionId = RuntimeIdentity
        """,
    )
    assert "ARCH-DECISION-IDENTITY" in _rules(tmp_path)


@pytest.mark.parametrize(
    "target",
    [
        "InvestmentDecisionId",
        "DecisionId",
        "decision_id",
    ],
)
def test_decision_annotated_binding_rejects_technical_initializer(
    tmp_path: Path,
    target: str,
) -> None:
    _write(
        tmp_path,
        "src/polaris/domain/decisions/identity.py",
        (
            "from polaris.domain.decisions.identity import "
            "SemanticIdentity\n"
            "from polaris.domain.runtime import "
            "RunId as RuntimeIdentity\n\n"
            f"{target}: SemanticIdentity = RuntimeIdentity\n"
        ),
    )
    assert "ARCH-DECISION-IDENTITY" in _rules(tmp_path)


def test_semantic_annotated_initializer_remains_allowed(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path,
        "src/polaris/domain/decisions/model.py",
        """
        from polaris.domain.decisions.identity import (
            InvestmentDecisionId as SemanticIdentity,
        )

        class InvestmentDecision:
            id: SemanticIdentity = SemanticIdentity
        """,
    )
    assert _rules(tmp_path) == set()
