from __future__ import annotations

import ast
from dataclasses import fields
from pathlib import Path

from sqlalchemy.dialects.postgresql import UUID

from polaris.domain.portfolio import PortfolioState
from polaris.infrastructure.persistence.postgresql.schema import portfolio_states

ROOT = Path(__file__).resolve().parents[1]

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
        tree = ast.parse((ROOT / relative_path).read_text(encoding="utf-8"))
        classes = {node.name for node in tree.body if isinstance(node, ast.ClassDef)}
        assert classes == allowed

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
