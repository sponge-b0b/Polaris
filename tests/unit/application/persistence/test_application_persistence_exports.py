from __future__ import annotations

import importlib
import inspect
import os
from collections.abc import Sequence
from typing import get_args, get_origin, get_type_hints

os.environ.setdefault(
    "POLARIS_DATABASE_URL", "postgresql+asyncpg://localhost/polaris_test"
)

import application.persistence as persistence
from core.storage.persistence.query import PersistenceListResult

_DOMAIN_MODULES = (
    "application.persistence.agent_intelligence",
    "application.persistence.attribution",
    "application.persistence.audit",
    "application.persistence.backtesting",
    "application.persistence.diagnostics",
    "application.persistence.export",
    "application.persistence.health",
    "application.persistence.lineage",
    "application.persistence.macro",
    "application.persistence.market",
    "application.persistence.news",
    "application.persistence.portfolio",
    "application.persistence.recommendations",
    "application.persistence.rag",
    "application.persistence.reports",
    "application.persistence.retention",
    "application.persistence.sentiment",
    "application.persistence.strategy",
    "application.persistence.telemetry",
    "application.persistence.validation",
    "application.persistence.workflow_audit",
)

_ROOT_EXPORT_SUFFIXES = (
    "Config",
    "Filters",
    "Service",
)

_DOMAIN_EXPORT_SUFFIXES = (
    "Config",
    "Filters",
    "Result",
    "Service",
    "Summary",
)

_SERVICES_WITHOUT_LIST_APIS = {
    "DiagnosticsPersistenceService",
    "HealthPersistenceService",
    "JsonPersistenceExportService",
    "RetentionPersistenceService",
    "TelemetryRetentionService",
    "ValidationPersistenceService",
}

_DOMAIN_SUPPORT_EXPORTS = {
    "application.persistence.backtesting": {
        "backtest_result_to_persistence_bundle",
    },
    "application.persistence.retention": {
        "DEFAULT_TELEMETRY_RETENTION_BATCH_SIZE",
        "DEFAULT_TELEMETRY_RETENTION_DAYS",
        "DEFAULT_TELEMETRY_RETENTION_MAX_BATCHES",
    },
}


def test_application_persistence_root_exports_all_domain_service_contracts() -> None:
    expected_exports: set[str] = set()
    for module_name in _DOMAIN_MODULES:
        module = importlib.import_module(module_name)
        expected_exports.update(
            export_name
            for export_name in module.__all__
            if export_name.endswith(_ROOT_EXPORT_SUFFIXES)
        )

    assert set(persistence.__all__) == expected_exports


def test_application_persistence_exports_are_sorted_and_bound() -> None:
    assert persistence.__all__ == sorted(persistence.__all__)
    for export_name in persistence.__all__:
        assert getattr(persistence, export_name) is not None


def test_application_persistence_exports_services_and_filters_only() -> None:
    for export_name in persistence.__all__:
        assert export_name.endswith(_ROOT_EXPORT_SUFFIXES)
        assert "Repository" not in export_name


def test_domain_persistence_modules_export_services_and_filters_only() -> None:
    for module_name in _DOMAIN_MODULES:
        module = importlib.import_module(module_name)
        assert module.__all__ == sorted(module.__all__)
        for export_name in module.__all__:
            assert _is_public_domain_export(
                module_name,
                export_name,
            )
            assert "Repository" not in export_name
            assert not export_name.endswith(
                (
                    "Record",
                    "Bundle",
                    "QueryService",
                )
            )


def test_application_persistence_root_does_not_export_infrastructure_types() -> None:
    forbidden_fragments = (
        "Repository",
        "Postgres",
        "Serializer",
        "Model",
        "Record",
        "Bundle",
        "Result",
        "QueryService",
    )

    for export_name in persistence.__all__:
        assert not any(fragment in export_name for fragment in forbidden_fragments)


def test_application_persistence_services_preserve_list_apis_and_add_result_envelopes() -> (  # noqa: E501
    None
):
    for module_name in _DOMAIN_MODULES:
        module = importlib.import_module(module_name)
        service_names = [
            export_name
            for export_name in module.__all__
            if export_name.endswith("Service")
        ]
        assert service_names

        for service_name in service_names:
            service_type = getattr(
                module,
                service_name,
            )

            list_methods = _public_list_methods(
                service_type,
                result_methods=False,
            )
            result_methods = _public_list_methods(
                service_type,
                result_methods=True,
            )

            if service_name in _SERVICES_WITHOUT_LIST_APIS:
                assert not list_methods
                assert not result_methods
                continue

            assert list_methods
            assert set(result_methods) == {
                f"{method_name}_result" for method_name in list_methods
            }

            for method_name in list_methods:
                hints = get_type_hints(
                    getattr(
                        service_type,
                        method_name,
                    )
                )
                assert get_origin(hints["return"]) is Sequence

            for method_name in result_methods:
                hints = get_type_hints(
                    getattr(
                        service_type,
                        method_name,
                    )
                )
                return_type = hints["return"]
                assert get_origin(return_type) is PersistenceListResult
                assert get_args(return_type)


def _is_public_domain_export(
    module_name: str,
    export_name: str,
) -> bool:
    if export_name.endswith(_DOMAIN_EXPORT_SUFFIXES):
        return True
    return export_name in _DOMAIN_SUPPORT_EXPORTS.get(
        module_name,
        set(),
    )


def _public_list_methods(
    service_type: type[object],
    *,
    result_methods: bool,
) -> list[str]:
    return sorted(
        name
        for name, member in inspect.getmembers(
            service_type,
            predicate=inspect.iscoroutinefunction,
        )
        if name.startswith("list_")
        and not name.startswith("list_rationales")
        and not name.startswith("list_outcomes")
        and name.endswith("_result") == result_methods
    )
