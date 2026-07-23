from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import StrEnum

from application.observability.ai_observability_contracts import (
    AiGenerationObservation,
    AiObservation,
    AiPromptVersionReference,
)

DEFAULT_STATIC_PROMPT_VERSION = "static-v1"
DEFAULT_SOURCE_CONTROLLED_PROMPT_SOURCE = "polaris.source_controlled"
APPROVED_LANGFUSE_PROMPT_SOURCE = "langfuse.approved"


class AiPromptPromotionStatus(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"


class AiPromptGovernanceError(ValueError):
    """Raised when a prompt reference violates Polaris prompt governance."""


@dataclass(frozen=True, slots=True)
class AiPromptGovernancePolicy:
    """Validate prompt references before AI observations are exported.

    Polaris owns production prompt governance. Langfuse may be used for prompt
    authoring and evaluation, but production observations must reference pinned,
    approved prompt versions rather than mutable labels such as ``latest``.
    """

    environment: str = "development"
    require_pinned_production_prompts: bool = True
    production_environments: tuple[str, ...] = ("production", "prod")
    mutable_versions: tuple[str, ...] = ("latest", "draft", "dev", "mutable")
    approved_source_prefixes: tuple[str, ...] = (
        "polaris",
        APPROVED_LANGFUSE_PROMPT_SOURCE,
    )

    @property
    def is_production(self) -> bool:
        return self.environment.strip().lower() in self.production_environments

    def validate_observation(self, observation: AiObservation) -> None:
        reference = observation.prompt_reference
        if reference is not None:
            self.validate_reference(reference)
            return
        if self.is_production and isinstance(observation, AiGenerationObservation):
            raise AiPromptGovernanceError(
                "Production AI generation observations require a prompt reference."
            )

    def validate_reference(self, reference: AiPromptVersionReference) -> None:
        if not self.is_production or not self.require_pinned_production_prompts:
            return
        version = reference.prompt_version.strip().lower()
        if version in self.mutable_versions:
            raise AiPromptGovernanceError(
                "Production prompt references must use a pinned version, "
                f"not {reference.prompt_version!r}."
            )
        if reference.prompt_hash is None:
            raise AiPromptGovernanceError(
                "Production prompt references must include a prompt hash."
            )
        source = (reference.source or "").strip()
        if not source:
            raise AiPromptGovernanceError(
                "Production prompt references must include an approved source."
            )
        if not any(
            source.startswith(prefix) for prefix in self.approved_source_prefixes
        ):
            raise AiPromptGovernanceError(
                f"Prompt source {source!r} is not approved for production use."
            )


@dataclass(frozen=True, slots=True)
class AiPromptPromotionRequest:
    """Request to promote an evaluated Langfuse prompt into Polaris governance."""

    candidate_reference: AiPromptVersionReference
    evaluation_run_id: str
    approved_by: str
    approval_reason: str

    def __post_init__(self) -> None:
        _require_non_empty(self.evaluation_run_id, "evaluation_run_id")
        _require_non_empty(self.approved_by, "approved_by")
        _require_non_empty(self.approval_reason, "approval_reason")


@dataclass(frozen=True, slots=True)
class AiPromptPromotionDecision:
    status: AiPromptPromotionStatus
    approved_reference: AiPromptVersionReference | None = None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class AiPromptPromotionPolicy:
    """Canonical policy for approving Langfuse-authored prompts for production."""

    governance_policy: AiPromptGovernancePolicy = AiPromptGovernancePolicy(
        environment="production"
    )

    def decide(self, request: AiPromptPromotionRequest) -> AiPromptPromotionDecision:
        try:
            self.governance_policy.validate_reference(request.candidate_reference)
        except AiPromptGovernanceError as exc:
            return AiPromptPromotionDecision(
                status=AiPromptPromotionStatus.REJECTED,
                reason=str(exc),
            )
        return AiPromptPromotionDecision(
            status=AiPromptPromotionStatus.APPROVED,
            approved_reference=request.candidate_reference,
            reason=request.approval_reason,
        )


def static_prompt_hash(prompt_text: str) -> str:
    _require_non_empty(prompt_text, "prompt_text")
    return hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()


def static_prompt_reference(
    *,
    prompt_name: str,
    prompt_text: str,
    prompt_version: str = DEFAULT_STATIC_PROMPT_VERSION,
    source: str = DEFAULT_SOURCE_CONTROLLED_PROMPT_SOURCE,
) -> AiPromptVersionReference:
    return AiPromptVersionReference(
        prompt_name=prompt_name,
        prompt_version=prompt_version,
        prompt_hash=static_prompt_hash(prompt_text),
        source=source,
    )


def _require_non_empty(value: str | None, field_name: str) -> None:
    if value is None or not value.strip():
        raise ValueError(f"{field_name} cannot be empty.")
