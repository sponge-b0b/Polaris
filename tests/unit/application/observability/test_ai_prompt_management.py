from __future__ import annotations

import pytest

from application.observability import (
    APPROVED_LANGFUSE_PROMPT_SOURCE,
    DEFAULT_SOURCE_CONTROLLED_PROMPT_SOURCE,
    DEFAULT_STATIC_PROMPT_VERSION,
    AiGenerationObservation,
    AiObservabilityCapturePolicy,
    AiObservationType,
    AiPromptGovernanceError,
    AiPromptGovernancePolicy,
    AiPromptPromotionPolicy,
    AiPromptPromotionRequest,
    AiPromptPromotionStatus,
    AiPromptVersionReference,
    LangfuseObservationMapper,
    static_prompt_hash,
    static_prompt_reference,
)


def test_static_prompt_reference_records_deterministic_hash_and_source() -> None:
    reference = static_prompt_reference(
        prompt_name="rag.answer",
        prompt_text="Answer with citations.",
    )

    assert reference.prompt_name == "rag.answer"
    assert reference.prompt_version == DEFAULT_STATIC_PROMPT_VERSION
    assert reference.prompt_hash == static_prompt_hash("Answer with citations.")
    assert reference.source == DEFAULT_SOURCE_CONTROLLED_PROMPT_SOURCE


@pytest.mark.parametrize("version", ["latest", "draft", "dev", "mutable"])
def test_production_prompt_governance_rejects_mutable_versions(version: str) -> None:
    policy = AiPromptGovernancePolicy(environment="production")

    with pytest.raises(AiPromptGovernanceError, match="pinned version"):
        policy.validate_reference(
            AiPromptVersionReference(
                prompt_name="rag.answer",
                prompt_version=version,
                prompt_hash="hash-1",
                source=APPROVED_LANGFUSE_PROMPT_SOURCE,
            )
        )


@pytest.mark.parametrize(
    "reference",
    [
        AiPromptVersionReference(
            prompt_name="rag.answer",
            prompt_version="v1",
            source=APPROVED_LANGFUSE_PROMPT_SOURCE,
        ),
        AiPromptVersionReference(
            prompt_name="rag.answer",
            prompt_version="v1",
            prompt_hash="hash-1",
        ),
        AiPromptVersionReference(
            prompt_name="rag.answer",
            prompt_version="v1",
            prompt_hash="hash-1",
            source="not-approved",
        ),
    ],
)
def test_production_prompt_governance_requires_hash_and_approved_source(
    reference: AiPromptVersionReference,
) -> None:
    policy = AiPromptGovernancePolicy(environment="production")

    with pytest.raises(AiPromptGovernanceError):
        policy.validate_reference(reference)


def test_production_prompt_governance_accepts_pinned_source_controlled_reference() -> (
    None
):
    policy = AiPromptGovernancePolicy(environment="production")
    reference = AiPromptVersionReference(
        prompt_name="rag.answer",
        prompt_version="v1",
        prompt_hash="hash-1",
        source=DEFAULT_SOURCE_CONTROLLED_PROMPT_SOURCE,
    )

    policy.validate_reference(reference)


def test_production_mapper_rejects_generation_without_prompt_reference() -> None:
    mapper = LangfuseObservationMapper(
        capture_policy=AiObservabilityCapturePolicy(),
        environment="production",
    )
    observation = AiGenerationObservation(
        observation_type=AiObservationType.RAG_GENERATION,
        name="secure_generation",
    )

    with pytest.raises(AiPromptGovernanceError, match="require a prompt reference"):
        mapper.to_payload(observation)


def test_prompt_promotion_policy_requires_production_approved_reference() -> None:
    policy = AiPromptPromotionPolicy()
    approved = AiPromptVersionReference(
        prompt_name="rag.answer",
        prompt_version="v2",
        prompt_hash="hash-2",
        source=APPROVED_LANGFUSE_PROMPT_SOURCE,
    )
    request = AiPromptPromotionRequest(
        candidate_reference=approved,
        evaluation_run_id="eval-run-1",
        approved_by="platform-owner",
        approval_reason="quality gate passed",
    )

    decision = policy.decide(request)

    assert decision.status is AiPromptPromotionStatus.APPROVED
    assert decision.approved_reference == approved


def test_prompt_promotion_policy_rejects_unpinned_langfuse_candidate() -> None:
    policy = AiPromptPromotionPolicy()
    request = AiPromptPromotionRequest(
        candidate_reference=AiPromptVersionReference(
            prompt_name="rag.answer",
            prompt_version="latest",
            prompt_hash="hash-2",
            source=APPROVED_LANGFUSE_PROMPT_SOURCE,
        ),
        evaluation_run_id="eval-run-1",
        approved_by="platform-owner",
        approval_reason="quality gate passed",
    )

    decision = policy.decide(request)

    assert decision.status is AiPromptPromotionStatus.REJECTED
    assert decision.reason is not None
