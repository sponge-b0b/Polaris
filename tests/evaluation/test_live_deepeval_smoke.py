from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from config.settings import Settings
from domain.evaluation import EvaluationStatus
from integration.providers.llm_evaluation import (
    DeepEvalEvaluationProvider,
    EvaluationMetricSpec,
    EvaluationProviderRequest,
)
from tests.evaluation._helpers import evaluation_case_from_row

LoadJsonlFixture = Callable[[Path], tuple[dict[str, Any], ...]]

pytestmark = pytest.mark.live_deepeval


@pytest.mark.asyncio()
async def test_live_deepeval_provider_smoke_requires_explicit_judge_config(
    live_deepeval_settings: Settings,
    evaluation_fixture_dir: Path,
    load_jsonl_fixture: LoadJsonlFixture,
) -> None:
    row = load_jsonl_fixture(evaluation_fixture_dir / "golden_rag_questions.jsonl")[0]
    case = evaluation_case_from_row(row)
    provider = DeepEvalEvaluationProvider(
        judge_provider=live_deepeval_settings.DEEPEVAL_JUDGE_PROVIDER or "configured",
        judge_model=live_deepeval_settings.DEEPEVAL_JUDGE_MODEL or "configured",
        default_threshold=live_deepeval_settings.DEEPEVAL_DEFAULT_THRESHOLD,
        max_concurrency=1,
        timeout_seconds=min(live_deepeval_settings.DEEPEVAL_TIMEOUT_SECONDS, 30.0),
        telemetry_opt_out=live_deepeval_settings.DEEPEVAL_TELEMETRY_OPT_OUT,
    )

    result = await provider.evaluate(
        EvaluationProviderRequest(
            run_id="live-deepeval-smoke-001",
            cases=(case,),
            metrics=(EvaluationMetricSpec("answer_relevancy"),),
            timeout_seconds=min(live_deepeval_settings.DEEPEVAL_TIMEOUT_SECONDS, 30.0),
        )
    )

    assert result.run_id == "live-deepeval-smoke-001"
    assert result.metric_results
    assert result.status in {
        EvaluationStatus.PASSED,
        EvaluationStatus.FAILED,
        EvaluationStatus.ERRORED,
    }
