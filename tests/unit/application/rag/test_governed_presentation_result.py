from __future__ import annotations

from typing import Any, cast

import pytest

from application.evaluations.risk_authority_gate import (
    RiskAuthorityGateDecision,
    RiskAuthorityGateDecisionStatus,
    RiskAuthorityGateEvidence,
    RiskAuthorityGateFailureMode,
)
from application.presentation.governed_result import GovernedPresentationResult
from application.presentation.sink_decision import (
    PresentationSinkDecision,
    PresentationSinkDecisionService,
    PresentationSinkDisposition,
)
from application.rag.contracts.rag_quality_models import (
    RagCorrectiveAction,
    RagReflectionScores,
)
from application.rag.contracts.rag_request import RagRequest
from application.rag.contracts.rag_result import RagResult
from application.rag.generation import RagAnswerGenerator
from application.rag.rag_service import RagService
from core.storage.persistence.rag import RagPersistenceRepository
from core.workflow.registry.workflow_registry import WorkflowRegistry
from domain.authority import GateProfile, RiskTier
from integration.providers.rag.answer_generation_provider import (
    RagAnswerGenerationResult,
)
from tests.unit.application.rag.test_rag_service import (
    FakeAnswerProvider,
    FakePipeline,
    FakeRagRepository,
    FakeRetriever,
    _context,
    _generated_claim,
    _packet_persistence,
    _workflow_registry,
)


class _FixedPresentationDecisionService:
    def __init__(self, decision: PresentationSinkDecision) -> None:
        self.decision = decision

    async def evaluate(
        self,
        *args: object,
        **kwargs: object,
    ) -> PresentationSinkDecision:
        return self.decision


@pytest.mark.asyncio
async def test_rag_service_run_returns_application_owned_governed_result() -> None:
    request = RagRequest(
        query="Summarize SPY breadth.",
        requester="unit-test",
        workflow_name="morning_report",
        execution_id="exec-1",
        request_id="rag_query:governed-service-run",
    )
    context = _context(
        context_id="chunk-1",
        text="SPY breadth improved with broad participation.",
    )
    repository = FakeRagRepository()
    service = RagService(
        pipeline=FakePipeline(
            retriever=FakeRetriever(contexts=(context,)),
            answer_generator=RagAnswerGenerator(
                answer_provider=FakeAnswerProvider(
                    result=RagAnswerGenerationResult(
                        answer_text=(
                            "SPY breadth improved with broad participation [C1]."
                        ),
                        model="unit-test-model",
                        provider_name="unit-test-provider",
                        confidence_score=0.88,
                        generated_claims=(_generated_claim(),),
                    )
                )
            ),
        ),
        repository=cast(RagPersistenceRepository, repository),
        decision_evidence_packet_persistence_service=_packet_persistence(),
        workflow_registry=cast(WorkflowRegistry, _workflow_registry()),
    )

    governed = await service.run(request)
    payload = governed.require_presentable_payload()

    assert isinstance(governed, GovernedPresentationResult)
    assert governed.decision.may_present is True
    assert governed.projection.disposition in {"eligible", "degraded"}
    assert payload.status == "answered"
    assert payload.citations == (context.source,)
    assert repository.answer_logs[0].status == "answered"


@pytest.mark.asyncio
async def test_rag_service_strips_claim_state_before_blocked_result() -> None:
    request = RagRequest(query="Explain SPY risk")
    context = _context(
        context_id="chunk-1",
        text="Claim-bearing retrieved evidence.",
    )
    result = RagResult(
        query_id=request.request_id,
        request=request,
        answer_text="Claim-bearing answer [C1].",
        status="answered",
        route=request.route,
        contexts=(context,),
        citations=(context.source,),
        confidence_score=0.91,
        grounding_score=0.92,
        utility_score=0.93,
        reflection_scores=RagReflectionScores(
            retrieval_necessity=0.8,
            source_relevance=0.9,
            answer_support=0.95,
            usefulness=0.85,
        ),
        corrective_actions=(RagCorrectiveAction.DISCARD_WEAK_CONTEXT,),
        generated_claims=(_generated_claim(),),
    )
    service = _service(
        _FixedPresentationDecisionService(
            PresentationSinkDecision(
                disposition=PresentationSinkDisposition.BLOCKED,
                gate_decision=RiskAuthorityGateDecision(
                    status=RiskAuthorityGateDecisionStatus.FAILED,
                    failure_mode=RiskAuthorityGateFailureMode.PROHIBITED_BOUNDARY,
                    message="outside authority",
                    risk_tier=RiskTier.PROHIBITED_OUTSIDE_AUTHORITY,
                    gate_profile=GateProfile.PROHIBITED_BOUNDARY,
                    authority_metadata=None,
                    evidence=RiskAuthorityGateEvidence(),
                ),
                reasons=("outside authority",),
            )
        )
    )

    governed = await service._apply_presentation_decision(result)
    payload = governed.require_payload()

    assert governed.decision.may_present is False
    assert payload.status == "no_results"
    assert "Claim-bearing answer" not in payload.answer_text
    assert payload.contexts == ()
    assert payload.citations == ()
    assert payload.confidence_score is None
    assert payload.grounding_score is None
    assert payload.utility_score is None
    assert payload.reflection_scores is None
    assert payload.corrective_actions == ()
    assert payload.evidence_packet is None
    assert payload.generated_claims == ()


@pytest.mark.asyncio
async def test_rag_service_fails_closed_when_authority_is_missing() -> None:
    request = RagRequest(query="Explain SPY risk")
    context = _context(
        context_id="chunk-1",
        text="Claim-bearing retrieved evidence.",
    )
    result = RagResult.answered(
        request=request,
        answer_text="Claim-bearing answer [C1].",
        contexts=(context,),
        confidence_score=0.91,
    )
    service = _service(PresentationSinkDecisionService())

    governed = await service._apply_presentation_decision(result)
    payload = governed.require_payload()

    assert governed.decision.may_present is False
    assert governed.projection.disposition == "withheld"
    assert governed.projection.gate_failure_mode == "metadata_missing"
    assert payload.status == "no_results"
    assert payload.contexts == ()
    assert payload.citations == ()
    assert payload.confidence_score is None


def _service(presentation_service: object) -> RagService:
    return RagService(
        pipeline=cast(Any, object()),
        repository=cast(Any, object()),
        decision_evidence_packet_persistence_service=cast(Any, object()),
        presentation_sink_decision_service=cast(Any, presentation_service),
    )
