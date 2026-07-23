from __future__ import annotations

import json

import pytest

from domain.evaluation import EvaluationCase, EvaluationTargetType
from integration.providers.ai_optimization import (
    DspyOptimizationProvider,
    DspyOptimizationProviderRequest,
)


@pytest.mark.asyncio
async def test_dspy_provider_builds_deterministic_program_artifact() -> None:
    provider = DspyOptimizationProvider(
        gateway_base_url="http://localhost:4000/v1",
        gateway_api_key="unit-test-placeholder",
    )
    case = EvaluationCase(
        case_id="case-1",
        target_type=EvaluationTargetType.RAG_GENERATION,
        input_text="Explain portfolio risk.",
        actual_output="Risk is elevated.",
        expected_output="Risk is elevated due to concentration.",
    )

    result = await provider.optimize(
        DspyOptimizationProviderRequest(
            optimization_id="opt-1",
            target_component="rag_answer_generation",
            cases=(case,),
            prompt_name="rag-answer",
            prompt_version="v1",
            artifact_name="rag-answer-dspy",
            artifact_version="v1",
            model_name="qwen2.5:7b",
        )
    )

    manifest = json.loads(result.artifact.program_text)

    assert result.provider_name == "dspy"
    assert result.candidate_count == 1
    assert result.case_outputs[0].case_id == "case-1"
    assert (
        result.case_outputs[0].actual_output == "Risk is elevated due to concentration."
    )
    assert result.artifact.prompt_reference.startswith(
        "dspy://rag_answer_generation/rag-answer-dspy/v1/"
    )
    assert len(result.artifact.prompt_hash) == 64
    assert manifest["module_name"] == "Predict"
    assert manifest["dspy_model_name"] == "openai/qwen2.5:7b"
    assert manifest["gateway_base_url"] == "http://localhost:4000/v1"
    assert manifest["trainset_case_ids"] == ["case-1"]


def test_dspy_provider_preserves_already_prefixed_model_name() -> None:
    from integration.providers.ai_optimization.dspy_optimization_provider import (
        _litellm_model_name,
    )

    assert _litellm_model_name("openai/qwen3.5:4b", "openai") == "openai/qwen3.5:4b"
    assert _litellm_model_name("qwen3.5:4b", "openai") == "openai/qwen3.5:4b"
