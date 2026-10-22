from __future__ import annotations

import ast
from dataclasses import fields
from pathlib import Path

from sqlalchemy.dialects.postgresql import UUID

from polaris.domain.portfolio import PortfolioState
from polaris.domain.portfolio_risk import PortfolioRiskAssessment
from polaris.infrastructure.persistence.postgresql.schema import (
    metadata,
    portfolio_states,
)

ROOT = Path(__file__).resolve().parents[1]


def _top_level_classes(relative_path: str) -> set[str]:
    tree = ast.parse((ROOT / relative_path).read_text(encoding="utf-8"))
    return {node.name for node in tree.body if isinstance(node, ast.ClassDef)}


EXPECTED_STATE_FIELDS = frozenset(
    {"state_id", "portfolio_id", "as_of", "source", "instrument_id"}
    | {"currency", "capital_basis", "cash", "position_quantity", "position_value"}
    | {"exposure_value", "allocation_fraction", "interpretation_basis", "uncertainty"}
)
EXPECTED_STORAGE_COLUMNS = (EXPECTED_STATE_FIELDS - {"source"}) | {
    "known_at",
    "source_system",
    "source_record_reference",
    "source_observed_at",
}


def test_portfolio_fact_remains_typed_and_domain_owned() -> None:
    assert {field.name for field in fields(PortfolioState)} == EXPECTED_STATE_FIELDS
    assert set(portfolio_states.c.keys()) == EXPECTED_STORAGE_COLUMNS
    assert isinstance(portfolio_states.c.state_id.type, UUID)
    assert isinstance(portfolio_states.c.instrument_id.type, UUID)


def test_portfolio_scope_has_no_generic_simulation_or_authority_writer() -> None:
    expected_classes = {
        "src/polaris/domain/portfolio.py": {
            "PortfolioId",
            "FinancialInstrumentId",
            "PortfolioStateId",
            "PortfolioSource",
            "PortfolioState",
            "RecordedPortfolioState",
        },
        "src/polaris/application/portfolio.py": {
            "PortfolioStateConflict",
            "PortfolioStateStoreFailure",
            "PortfolioStateStore",
        },
        "src/polaris/infrastructure/persistence/postgresql/portfolio_states.py": {
            "PostgresPortfolioStateStore",
        },
    }
    for relative_path, allowed in expected_classes.items():
        assert _top_level_classes(relative_path) == allowed

    migration = ast.parse(
        (ROOT / "migrations/versions/0009_portfolio_states.py").read_text(
            encoding="utf-8"
        )
    )
    created_tables = [
        node
        for node in ast.walk(migration)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "op"
        and node.func.attr == "create_table"
    ]
    assert len(created_tables) == 1
    assert isinstance(created_tables[0].args[0], ast.Constant)
    assert created_tables[0].args[0].value == "portfolio_states"
    migration_columns = {
        column.args[0].value
        for column in created_tables[0].args[1:]
        if isinstance(column, ast.Call)
        and isinstance(column.func, ast.Attribute)
        and column.func.attr == "Column"
        and isinstance(column.args[0], ast.Constant)
    }
    assert migration_columns == set(portfolio_states.c.keys())


def test_r3_risk_and_consequence_authorities_remain_bounded() -> None:
    expected_classes = {
        "src/polaris/domain/portfolio_consequences.py": {
            "ProjectedChange",
            "ProjectedPortfolioConsequence",
            "RecordedProjectedPortfolioConsequence",
        },
        "src/polaris/domain/portfolio_risk.py": {
            "RiskDimensionKind",
            "RiskDimension",
            "RiskSupport",
            "PortfolioRiskAssessment",
            "RecordedPortfolioRiskAssessment",
        },
        "src/polaris/application/portfolio_risk.py": {
            "PortfolioRiskConflict",
            "PortfolioRiskStoreFailure",
            "PortfolioRiskStore",
            "PortfolioStateReader",
            "PortfolioConsequenceReader",
            "PortfolioRiskService",
        },
        "src/polaris/infrastructure/persistence/postgresql/portfolio_risk.py": {
            "PostgresPortfolioRiskStore",
        },
    }
    for relative_path, allowed in expected_classes.items():
        assert _top_level_classes(relative_path) == allowed

    # Distinct typed dimensions remain authoritative; an optional score may coexist.
    assert "dimensions" in {field.name for field in fields(PortfolioRiskAssessment)}
    risk_tree = ast.parse(
        (ROOT / "src/polaris/domain/portfolio_risk.py").read_text(encoding="utf-8")
    )
    public_producers = {
        node.name
        for node in risk_tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    }
    assert public_producers == {"assess_portfolio_risk"}


def test_r3_portfolio_modules_exclude_later_and_generic_authorities() -> None:
    forbidden = (
        "decisionrecord",
        "claimgraph",
        "evidencegraph",
        "formalconstraint",
        "admissibility",
        "approval",
        "broker",
        "execution",
        "simulation",
        "simulate",
        "simulator",
    )
    source_root = ROOT / "src/polaris"
    paths = [
        *source_root.glob("domain/portfolio*.py"),
        *source_root.glob("application/portfolio*.py"),
        *source_root.glob("infrastructure/persistence/postgresql/portfolio*.py"),
        source_root / "domain/investment_intelligence.py",
        source_root / "application/investment_intelligence.py",
        source_root
        / "infrastructure/persistence/postgresql/investment_intelligence.py",
    ]
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        declarations = [
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        declarations.extend(
            node.target.id
            for node in ast.walk(tree)
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
        )
        declarations.extend(
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        )
        declarations.extend(
            node.module or ""
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        )
        assert all(
            not any(term in name.replace("_", "").lower() for term in forbidden)
            for name in declarations
        ), path.relative_to(ROOT)
    assert all(
        not any(term in name.replace("_", "").lower() for term in forbidden)
        for name in metadata.tables
    )
