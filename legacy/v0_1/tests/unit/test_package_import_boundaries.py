from __future__ import annotations

import pytest

from tests.helpers.package_imports import inspect_package_import

_FORBIDDEN_INFRASTRUCTURE_ROOTS = {
    "asyncpg",
    "dishka",
    "httpx",
    "numpy",
    "opentelemetry",
    "pandas",
    "prometheus_client",
    "requests",
    "rich",
    "sqlalchemy",
    "typer",
}


@pytest.mark.parametrize(
    "package_name",
    [
        "core.storage",
        "integration.providers.backtesting.market_data",
        "interfaces.cli",
        "interfaces.cli.services",
    ],
)
def test_infrastructure_packages_do_not_eagerly_import_implementations(
    package_name: str,
) -> None:
    result = inspect_package_import(
        package_name,
        forbidden_roots=_FORBIDDEN_INFRASTRUCTURE_ROOTS,
    )

    assert result["exports"] == []
    assert result["loaded_package_children"] == []
    assert result["loaded_forbidden_modules"] == []
