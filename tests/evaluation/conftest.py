from __future__ import annotations

import json
import os
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest

from config.settings import Settings

LoadJsonlFixture = Callable[[Path], tuple[dict[str, Any], ...]]

EVAL_REQUIRED_ENV = "POLARIS_EVAL_REQUIRED"
LIVE_EVAL_ENV = "POLARIS_RUN_LIVE_EVALS"
_REQUIRED_DEEPEVAL_ENV = (
    "POLARIS_DEEPEVAL_ENABLED",
    "POLARIS_DEEPEVAL_JUDGE_PROVIDER",
    "POLARIS_DEEPEVAL_JUDGE_MODEL",
)


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "evaluation: Polaris LLM-evaluation tests that may run in CI.",
    )
    config.addinivalue_line(
        "markers",
        "eval_smoke: quick deterministic evaluation smoke tests.",
    )
    config.addinivalue_line(
        "markers",
        "eval_rag_regression: RAG regression evaluation tests.",
    )
    config.addinivalue_line(
        "markers",
        "eval_prompt_regression: prompt and rubric regression evaluation tests.",
    )
    config.addinivalue_line(
        "markers",
        "eval_strategy_synthesis: strategy-synthesis evaluation tests.",
    )
    config.addinivalue_line(
        "markers",
        "eval_security: prompt-injection and safety evaluation tests.",
    )
    config.addinivalue_line(
        "markers",
        "live_deepeval: live DeepEval tests requiring an explicit judge model.",
    )


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        item_path = Path(str(item.path)).as_posix()
        if "/tests/evaluation/" in item_path or item_path.startswith(
            "tests/evaluation/"
        ):
            item.add_marker(pytest.mark.evaluation)


def _enabled(value: str | None) -> bool:
    return value is not None and value.strip().lower() in {"1", "true", "yes", "on"}


def _missing_live_deepeval_env() -> tuple[str, ...]:
    missing = []
    for name in _REQUIRED_DEEPEVAL_ENV:
        value = os.environ.get(name)
        if value is None or not value.strip():
            missing.append(name)
    return tuple(missing)


@pytest.fixture()
def evaluation_fixture_dir() -> Path:
    return Path(__file__).parent / "fixtures"


@pytest.fixture()
def evaluation_required() -> bool:
    return _enabled(os.environ.get(EVAL_REQUIRED_ENV))


@pytest.fixture()
def run_live_evaluations() -> bool:
    return _enabled(os.environ.get(LIVE_EVAL_ENV))


@pytest.fixture()
def live_deepeval_settings(
    evaluation_required: bool,
    run_live_evaluations: bool,
) -> Settings:
    """Return live judge settings or skip/fail with an explicit CI reason."""

    missing = _missing_live_deepeval_env()
    if not run_live_evaluations and not evaluation_required:
        pytest.skip(
            f"Set {LIVE_EVAL_ENV}=true and configure "
            f"{', '.join(_REQUIRED_DEEPEVAL_ENV)} "
            "to run live DeepEval evaluation tests."
        )
    if missing:
        reason = (
            "Live DeepEval evaluation tests require explicit judge configuration; "
            f"missing: {', '.join(missing)}."
        )
        if evaluation_required:
            pytest.fail(reason)
        pytest.skip(reason)

    settings = Settings()
    try:
        settings.validate_deepeval_evaluation(require_configured=True)
    except ValueError as exc:
        if evaluation_required:
            pytest.fail(str(exc))
        pytest.skip(str(exc))
    return settings


@pytest.fixture()
def load_jsonl_fixture() -> Iterator[LoadJsonlFixture]:
    def _load(path: Path) -> tuple[dict[str, Any], ...]:
        rows: list[dict[str, Any]] = []
        with path.open(encoding="utf-8") as handle:
            for line_number, raw_line in enumerate(handle, start=1):
                line = raw_line.strip()
                if not line:
                    continue
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise AssertionError(f"{path}:{line_number} is not a JSON object")
                rows.append(value)
        return tuple(rows)

    yield _load
