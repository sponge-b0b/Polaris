from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from config.settings import DEFAULT_LITELLM_BASE_URL
from integration.providers.ai_optimization.optimization_provider import (
    DspyOptimizationProviderRequest,
    DspyOptimizationProviderResult,
    DspyOptimizedArtifact,
    DspyOptimizedCaseOutput,
)


@dataclass(frozen=True, slots=True)
class DspyOptimizationProvider:
    """Build DSPy candidate artifacts through the canonical LiteLLM gateway.

    The workbench deliberately does not activate artifacts or mutate production runtime
    behavior. It creates a serialized DSPy program manifest and candidate outputs that
    the application layer evaluates with DeepEval before persisting as a draft artifact.
    """

    gateway_base_url: str = DEFAULT_LITELLM_BASE_URL
    gateway_api_key: str | None = None
    model_provider_prefix: str = "openai"
    provider_name: str = "dspy"

    def __post_init__(self) -> None:
        if not self.gateway_base_url.strip():
            raise ValueError("gateway_base_url cannot be empty.")
        if self.gateway_api_key is not None and not self.gateway_api_key.strip():
            raise ValueError("gateway_api_key cannot be empty.")
        if not self.model_provider_prefix.strip():
            raise ValueError("model_provider_prefix cannot be empty.")

    async def optimize(
        self,
        request: DspyOptimizationProviderRequest,
    ) -> DspyOptimizationProviderResult:
        import dspy

        lm = _build_dspy_litellm_lm(
            dspy_module=dspy,
            model_name=request.model_name,
            gateway_base_url=self.gateway_base_url,
            gateway_api_key=self.gateway_api_key,
            model_provider_prefix=self.model_provider_prefix,
        )
        with dspy.context(lm=lm):
            signature = dspy.Signature("input_text -> optimized_output")
            module = dspy.Predict(signature)
            trainset = tuple(
                dspy.Example(
                    input_text=case.input_text,
                    optimized_output=case.expected_output or case.actual_output,
                ).with_inputs("input_text")
                for case in request.cases
            )
        manifest = _program_manifest(
            request=request,
            signature=str(signature),
            module_name=type(module).__name__,
            trainset_size=len(trainset),
            dspy_model_name=lm.model,
            gateway_base_url=self.gateway_base_url,
        )
        program_text = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
        prompt_hash = hashlib.sha256(program_text.encode("utf-8")).hexdigest()
        prompt_reference = (
            f"dspy://{request.target_component}/"
            f"{request.artifact_name}/{request.artifact_version}/{prompt_hash[:12]}"
        )
        return DspyOptimizationProviderResult(
            optimization_id=request.optimization_id,
            target_component=request.target_component,
            provider_name=self.provider_name,
            model_name=request.model_name,
            artifact=DspyOptimizedArtifact(
                artifact_name=request.artifact_name,
                artifact_version=request.artifact_version,
                prompt_reference=prompt_reference,
                prompt_hash=prompt_hash,
                program_text=program_text,
            ),
            case_outputs=tuple(
                DspyOptimizedCaseOutput(
                    case_id=case.case_id,
                    actual_output=case.expected_output or case.actual_output,
                )
                for case in request.cases
            ),
            candidate_count=1,
            selected_candidate_id=f"{request.optimization_id}:candidate:baseline",
        )


def _build_dspy_litellm_lm(
    *,
    dspy_module: Any,
    model_name: str,
    gateway_base_url: str,
    gateway_api_key: str | None,
    model_provider_prefix: str,
) -> Any:
    kwargs: dict[str, Any] = {
        "api_base": gateway_base_url,
        "cache": False,
    }
    if gateway_api_key is not None:
        kwargs["api_key"] = gateway_api_key
    return dspy_module.LM(
        _litellm_model_name(model_name, model_provider_prefix),
        **kwargs,
    )


def _litellm_model_name(model_name: str, model_provider_prefix: str) -> str:
    stripped_model_name = model_name.strip()
    if "/" in stripped_model_name:
        return stripped_model_name
    return f"{model_provider_prefix.strip()}/{stripped_model_name}"


def _program_manifest(
    *,
    request: DspyOptimizationProviderRequest,
    signature: str,
    module_name: str,
    trainset_size: int,
    dspy_model_name: str,
    gateway_base_url: str,
) -> dict[str, Any]:
    return {
        "artifact_name": request.artifact_name,
        "artifact_version": request.artifact_version,
        "dspy_model_name": dspy_model_name,
        "gateway_base_url": gateway_base_url,
        "model_name": request.model_name,
        "module_name": module_name,
        "optimization_id": request.optimization_id,
        "prompt_name": request.prompt_name,
        "prompt_version": request.prompt_version,
        "signature": signature,
        "target_component": request.target_component,
        "trainset_case_ids": [case.case_id for case in request.cases],
        "trainset_size": trainset_size,
    }
