from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from config.rag_model_config import RagModelConfig
from config.settings import Settings

_RAG_SETTING_NAMES = (
    "RAG_QUERY_REWRITE_MODEL",
    "RAG_ADAPTIVE_TRIAGE_MODEL",
    "RAG_ROUTE_SELECTION_MODEL",
    "RAG_HYDE_MODEL",
    "RAG_HYBRID_EMBEDDING_MODEL",
    "RAG_RERANKER_MODEL",
    "RAG_RERANKER_ENDPOINT",
    "RAG_CRAG_GRADER_MODEL",
    "RAG_CRAG_QUERY_REWRITE_MODEL",
    "RAG_SELF_REFLECTION_MODEL",
    "RAG_SYNTHESIS_MODEL",
    "RAG_WEB_FALLBACK_ENABLED",
    "RAG_WEB_FALLBACK_MAX_RESULTS",
    "SEARXNG_BASE_URL",
    "SEARXNG_TIMEOUT_SECONDS",
    "SEARXNG_SAFE_SEARCH",
    "SEARXNG_LANGUAGE",
    "SEARXNG_CATEGORIES",
    "CRAWL4AI_TIMEOUT_SECONDS",
    "CRAWL4AI_HEADLESS",
    "CRAWL4AI_CACHE_ENABLED",
    "CRAWL4AI_MAX_CONCURRENCY",
    "CRAWL4AI_USER_AGENT",
)


def _settings(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    overrides: dict[str, str] | None = None,
) -> Settings:
    monkeypatch.chdir(tmp_path)
    for name in _RAG_SETTING_NAMES:
        monkeypatch.delenv(name, raising=False)
    for name, value in (overrides or {}).items():
        monkeypatch.setenv(name, value)
    return Settings()


def test_rag_model_config_maps_default_settings_by_semantic_operation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config = RagModelConfig.from_settings(_settings(monkeypatch, tmp_path))

    assert config.query_rewrite_model == "qwen2.5:7b"
    assert config.adaptive_triage_model == "qwen2.5:7b"
    assert config.route_selection_model == "qwen3.5:4b"
    assert config.hyde_model == "qwen3.5:4b"
    assert config.hybrid_embedding_model == "BAAI/bge-m3"
    assert config.reranker_model == "BAAI/bge-reranker-large"
    assert config.reranker_endpoint == "http://localhost:8080/rerank"
    assert config.crag_grader_model == "qwen3.5:4b"
    assert config.crag_query_rewrite_model == "qwen3.5:4b"
    assert config.self_reflection_model == "qwen3.5:4b"
    assert config.synthesis_model == "qwen3.5:4b"


def test_rag_model_config_preserves_independent_environment_overrides(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    overrides = {
        "RAG_QUERY_REWRITE_MODEL": "rewrite-override",
        "RAG_ADAPTIVE_TRIAGE_MODEL": "triage-override",
        "RAG_ROUTE_SELECTION_MODEL": "route-override",
        "RAG_HYDE_MODEL": "hyde-override",
        "RAG_HYBRID_EMBEDDING_MODEL": "embedding-override",
        "RAG_RERANKER_MODEL": "reranker-override",
        "RAG_RERANKER_ENDPOINT": "http://reranker.test/rerank",
        "RAG_CRAG_GRADER_MODEL": "grader-override",
        "RAG_CRAG_QUERY_REWRITE_MODEL": "crag-rewrite-override",
        "RAG_SELF_REFLECTION_MODEL": "reflection-override",
        "RAG_SYNTHESIS_MODEL": "synthesis-override",
    }

    config = RagModelConfig.from_settings(
        _settings(monkeypatch, tmp_path, overrides=overrides)
    )

    assert config.query_rewrite_model == overrides["RAG_QUERY_REWRITE_MODEL"]
    assert config.adaptive_triage_model == overrides["RAG_ADAPTIVE_TRIAGE_MODEL"]
    assert config.route_selection_model == overrides["RAG_ROUTE_SELECTION_MODEL"]
    assert config.hyde_model == overrides["RAG_HYDE_MODEL"]
    assert config.hybrid_embedding_model == overrides["RAG_HYBRID_EMBEDDING_MODEL"]
    assert config.reranker_model == overrides["RAG_RERANKER_MODEL"]
    assert config.reranker_endpoint == overrides["RAG_RERANKER_ENDPOINT"]
    assert config.crag_grader_model == overrides["RAG_CRAG_GRADER_MODEL"]
    assert config.crag_query_rewrite_model == overrides["RAG_CRAG_QUERY_REWRITE_MODEL"]
    assert config.self_reflection_model == overrides["RAG_SELF_REFLECTION_MODEL"]
    assert config.synthesis_model == overrides["RAG_SYNTHESIS_MODEL"]


def test_rag_model_config_exposes_query_routing_subset(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config = RagModelConfig.from_settings(_settings(monkeypatch, tmp_path))

    assert config.query_routing.query_rewrite_model == config.query_rewrite_model
    assert config.query_routing.adaptive_triage_model == config.adaptive_triage_model
    assert config.query_routing.route_selection_model == config.route_selection_model
    assert config.query_routing.hyde_model == config.hyde_model


def test_rag_model_config_is_immutable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config = RagModelConfig.from_settings(_settings(monkeypatch, tmp_path))

    with pytest.raises(FrozenInstanceError):
        setattr(config, "synthesis_model", "replacement")


def test_settings_keep_general_embedding_but_remove_legacy_rag_aliases(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = _settings(monkeypatch, tmp_path)

    assert settings.EMBEDDING_MODEL == "bge-m3:567m"
    assert not hasattr(settings, "BGE_RERANKER_ENDPOINT")


def test_rag_model_config_exposes_quality_evaluation_subset(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config = RagModelConfig.from_settings(_settings(monkeypatch, tmp_path))

    assert config.quality_evaluation.crag_grader_model == config.crag_grader_model
    assert (
        config.quality_evaluation.crag_query_rewrite_model
        == config.crag_query_rewrite_model
    )
    assert (
        config.quality_evaluation.self_reflection_model == config.self_reflection_model
    )


def test_open_source_web_fallback_is_disabled_by_default(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = _settings(monkeypatch, tmp_path)

    assert settings.RAG_WEB_FALLBACK_ENABLED is False
    assert settings.RAG_WEB_FALLBACK_MAX_RESULTS == 5
    assert settings.SEARXNG_BASE_URL == "http://localhost:8888"
    assert settings.SEARXNG_TIMEOUT_SECONDS == 15.0
    assert settings.SEARXNG_SAFE_SEARCH == 1
    assert settings.SEARXNG_LANGUAGE == "en"
    assert settings.SEARXNG_CATEGORIES == "general"
    assert settings.CRAWL4AI_TIMEOUT_SECONDS == 30.0
    assert settings.CRAWL4AI_HEADLESS is True
    assert settings.CRAWL4AI_CACHE_ENABLED is True
    assert settings.CRAWL4AI_MAX_CONCURRENCY == 4
    assert settings.CRAWL4AI_USER_AGENT is None
