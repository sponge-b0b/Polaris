from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
READINESS_DOC = REPO_ROOT / "docs" / "model_allocation_readiness.md"

SERVICE_FREE_READINESS_PATHS = (
    "tests/unit/config/test_litellm_model_alias_config.py",
    "tests/unit/config/test_ai_structured_output_settings.py",
    "tests/unit/config/test_rag_model_config.py",
    "tests/unit/config/test_strategy_model_config.py",
    "tests/unit/config/test_model_allocation_readiness.py",
    "tests/unit/domain/test_reasoning_trace_safety.py",
    "tests/unit/integration/clients/test_non_rag_client_stabilization.py",
    "tests/unit/integration/providers/llm_structured_output",
    "tests/unit/application/structured_outputs/test_intelligence_workflow_structured_outputs.py",
    "tests/unit/application/rag/test_rag_security.py",
    "tests/unit/application/rag/test_secure_rag_generation.py",
    "tests/unit/integration/providers/rag/test_litellm_query_routing_provider.py",
    "tests/unit/integration/providers/rag/test_litellm_quality_evaluation_provider.py",
    "tests/unit/integration/providers/rag/test_structured_answer_generation_provider.py",
    "tests/unit/intelligence/strategy/test_strategy_model_alias_behavior.py",
    "tests/evaluation/test_strategy_synthesis_evals.py",
    "tests/evaluation/test_structured_rag_output_evals.py",
    "tests/evaluation/test_rag_regression_evals.py",
    "tests/evaluation/test_golden_dataset_fixtures.py",
    "tests/unit/application/evaluations/test_evaluation_datasets.py",
    "tests/unit/application/evaluations/test_model_replacement_gate.py",
)

ACCEPTANCE_PHRASES = (
    "approved aliases configured and discoverable",
    "no concrete local model names in architectural defaults",
    "reasoning-trace safety",
    "structured-output",
    "strategy",
    "RAG",
    "evaluation gate",
    "documentation current",
    "live-service requirements",
    "full pytest suite was not run",
)

LIVE_SERVICE_NAMES = (
    "LiteLLM",
    "Ollama",
    "PostgreSQL",
    "Qdrant",
    "Neo4j",
    "BGE reranker",
    "Langfuse",
    "Prometheus",
    "Jaeger",
    "Grafana",
)


def _readiness_text() -> str:
    return READINESS_DOC.read_text()


def test_readiness_runbook_points_to_existing_service_free_checks() -> None:
    text = _readiness_text()

    for relative_path in SERVICE_FREE_READINESS_PATHS:
        assert (REPO_ROOT / relative_path).exists(), relative_path
        assert relative_path in text


def test_readiness_runbook_covers_issue_24_acceptance_matrix() -> None:
    text = _readiness_text()

    for phrase in ACCEPTANCE_PHRASES:
        assert phrase in text


def test_readiness_runbook_declares_live_service_requirements() -> None:
    text = _readiness_text()
    live_heading = "## Optional live validation requirements"
    live_section = text.split(live_heading, maxsplit=1)[-1]

    for service_name in LIVE_SERVICE_NAMES:
        assert service_name in live_section

    required_warning = (
        "Do not run these checks until the required services are confirmed healthy"
    )
    assert required_warning in live_section
