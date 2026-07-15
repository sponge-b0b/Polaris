from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from integration.providers.ai_optimization.optimization_provider import (
    DspyOptimizedArtifact,
)
from integration.providers.ai_optimization.optimization_provider import (
    DspyOptimizedCaseOutput,
)
from integration.providers.ai_optimization.optimization_provider import (
    DspyOptimizationProviderRequest,
)
from integration.providers.ai_optimization.optimization_provider import (
    DspyOptimizationProviderResult,
)


@dataclass(frozen=True, slots=True)
class DspyOptimizationProvider:
    """Build deterministic DSPy candidate artifacts for offline optimization runs.

    The workbench deliberately does not activate artifacts or mutate production runtime
    behavior. It creates a serialized DSPy program manifest and candidate outputs that
    the application layer evaluates with DeepEval before persisting as a draft artifact.
    """

    provider_name: str = "dspy"

    async def optimize(
        self,
        request: DspyOptimizationProviderRequest,
    ) -> DspyOptimizationProviderResult:
        import dspy

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


def _program_manifest(
    *,
    request: DspyOptimizationProviderRequest,
    signature: str,
    module_name: str,
    trainset_size: int,
) -> dict[str, Any]:
    return {
        "artifact_name": request.artifact_name,
        "artifact_version": request.artifact_version,
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
