from __future__ import annotations

from tests.helpers.package_imports import inspect_package_import

_FORBIDDEN_RAG_ROOTS = {
    "crawl4ai",
    "httpx",
    "neo4j",
    "numpy",
    "ollama",
    "qdrant_client",
}


def test_application_rag_package_exports_only_domain_contracts() -> None:
    result = inspect_package_import(
        "application.rag",
        forbidden_roots=_FORBIDDEN_RAG_ROOTS,
    )

    assert result["exports"] == [
        "RagRequest",
        "RagResult",
        "RagRetrievedContext",
        "RagRetrievalFilters",
        "RagSource",
    ]
    assert result["loaded_forbidden_modules"] == []


def test_integration_rag_packages_do_not_eagerly_import_implementations() -> None:
    for package_name in (
        "integration.clients.rag",
        "integration.providers.rag",
    ):
        result = inspect_package_import(
            package_name,
            forbidden_roots=_FORBIDDEN_RAG_ROOTS,
        )

        assert result["exports"] == []
        assert result["loaded_package_children"] == []
        assert result["loaded_forbidden_modules"] == []
