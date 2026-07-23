from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from time import perf_counter
from typing import Protocol

from application.evaluations.contracts import (
    EvaluationLangfuseProjectionRequest,
    EvaluationLangfuseProjectionResult,
    EvaluationRunServiceRequest,
    EvaluationRunServiceResult,
)
from application.evaluations.evaluation_datasets import (
    canonical_evaluation_dataset_definition_by_name,
)
from application.evaluations.evaluation_telemetry import EvaluationTelemetry
from application.evaluations.risk_authority_gate import (
    RiskAuthorityGateDecision,
    RiskAuthorityGateDecisionStatus,
    RiskAuthorityGateEvidence,
    select_risk_authority_gate,
)
from core.storage.persistence.evaluation import (
    EvaluationCaseRecord,
    EvaluationDatasetRecord,
    EvaluationMetricResultRecord,
    EvaluationPersistenceBundle,
    EvaluationPersistenceRepository,
    EvaluationPersistenceResult,
    EvaluationRunRecord,
)
from domain.authority import (
    AiOutputContentType,
    AuthorityEffect,
    CanonicalOwner,
    IntendedSink,
    RiskAuthorityClassificationInput,
    SourceOfTruthCategory,
    classify_risk_authority,
)
from domain.evaluation import (
    EvaluationCase,
    EvaluationRun,
    EvaluationStatus,
    EvaluationTargetType,
)
from integration.providers.llm_evaluation import (
    EvaluationProvider,
    EvaluationProviderRequest,
)

logger = logging.getLogger(__name__)


class EvaluationRunScoreProjectionService(Protocol):
    """Score-projection boundary for post-persistence evaluation exports."""

    async def project_run_scores(
        self,
        request: EvaluationLangfuseProjectionRequest,
    ) -> EvaluationLangfuseProjectionResult: ...


@dataclass(frozen=True, slots=True)
class EvaluationRunService:
    """Run evaluation cases through a provider and persist canonical results."""

    provider: EvaluationProvider
    repository: EvaluationPersistenceRepository
    projection_service: EvaluationRunScoreProjectionService
    telemetry: EvaluationTelemetry | None = None

    async def run_evaluation(
        self,
        request: EvaluationRunServiceRequest,
    ) -> EvaluationRunServiceResult:
        started_at = datetime.now(UTC)
        started_monotonic = perf_counter()
        dataset_id = None if request.dataset is None else request.dataset.dataset_id
        case_records = tuple(
            EvaluationCaseRecord.from_domain(case) for case in request.cases
        )
        running_run = EvaluationRun(
            run_id=request.run_id,
            target_type=request.target_type,
            status=EvaluationStatus.RUNNING,
            evaluator_provider=request.evaluator_provider,
            evaluator_model=request.evaluator_model,
            dataset=request.dataset,
            case_ids=tuple(case.case_id for case in request.cases),
            started_at=started_at,
        )
        initial_result = await self.repository.persist_evaluation_bundle(
            EvaluationPersistenceBundle(
                datasets=_dataset_records(request),
                cases=case_records,
                runs=(EvaluationRunRecord.from_domain(running_run),),
            )
        )
        authority_gate_decision = _select_authority_gate(request)
        if self.telemetry is not None:
            await self.telemetry.emit_run_started(
                run_id=request.run_id,
                target_type=request.target_type,
                evaluator_provider=request.evaluator_provider,
                evaluator_model=request.evaluator_model,
                case_count=len(request.cases),
                metric_count=len(request.metrics),
                dataset_id=dataset_id,
                authority_gate_decision=authority_gate_decision,
            )
        if (
            authority_gate_decision is not None
            and authority_gate_decision.status is RiskAuthorityGateDecisionStatus.FAILED
        ):
            errored_run = EvaluationRun(
                run_id=request.run_id,
                target_type=request.target_type,
                status=EvaluationStatus.ERRORED,
                evaluator_provider=request.evaluator_provider,
                evaluator_model=request.evaluator_model,
                dataset=request.dataset,
                case_ids=tuple(case.case_id for case in request.cases),
                started_at=started_at,
                completed_at=datetime.now(UTC),
                error_message=(
                    "risk authority gate failed: "
                    f"{authority_gate_decision.failure_mode.value}"
                ),
            )
            error_result = await self.repository.persist_evaluation_bundle(
                EvaluationPersistenceBundle(
                    runs=(EvaluationRunRecord.from_domain(errored_run),)
                )
            )
            if self.telemetry is not None:
                await self.telemetry.emit_run_failed(
                    run_id=request.run_id,
                    target_type=request.target_type,
                    evaluator_provider=request.evaluator_provider,
                    evaluator_model=request.evaluator_model,
                    case_count=len(request.cases),
                    dataset_id=dataset_id,
                    duration_seconds=perf_counter() - started_monotonic,
                    error=RuntimeError(authority_gate_decision.message),
                    authority_gate_decision=authority_gate_decision,
                )
            return EvaluationRunServiceResult(
                run=errored_run,
                metric_results=(),
                persistence_result=_combine_persistence_results(
                    initial_result, error_result
                ),
                authority_gate_decision=authority_gate_decision,
            )
        try:
            provider_result = await self.provider.evaluate(
                EvaluationProviderRequest(
                    run_id=request.run_id,
                    cases=request.cases,
                    metrics=request.metrics,
                    timeout_seconds=request.timeout_seconds,
                )
            )
        except Exception as exc:
            errored_run = EvaluationRun(
                run_id=request.run_id,
                target_type=request.target_type,
                status=EvaluationStatus.ERRORED,
                evaluator_provider=request.evaluator_provider,
                evaluator_model=request.evaluator_model,
                dataset=request.dataset,
                case_ids=tuple(case.case_id for case in request.cases),
                started_at=started_at,
                completed_at=datetime.now(UTC),
                error_message=str(exc),
            )
            error_result = await self.repository.persist_evaluation_bundle(
                EvaluationPersistenceBundle(
                    runs=(EvaluationRunRecord.from_domain(errored_run),)
                )
            )
            if self.telemetry is not None:
                await self.telemetry.emit_run_failed(
                    run_id=request.run_id,
                    target_type=request.target_type,
                    evaluator_provider=request.evaluator_provider,
                    evaluator_model=request.evaluator_model,
                    case_count=len(request.cases),
                    dataset_id=dataset_id,
                    duration_seconds=perf_counter() - started_monotonic,
                    error=exc,
                    authority_gate_decision=authority_gate_decision,
                )
            return EvaluationRunServiceResult(
                run=errored_run,
                metric_results=(),
                persistence_result=_combine_persistence_results(
                    initial_result, error_result
                ),
                authority_gate_decision=authority_gate_decision,
            )

        completed_run = EvaluationRun(
            run_id=request.run_id,
            target_type=request.target_type,
            status=provider_result.status,
            evaluator_provider=provider_result.evaluator_provider,
            evaluator_model=provider_result.evaluator_model,
            dataset=request.dataset,
            case_ids=tuple(case.case_id for case in request.cases),
            started_at=started_at,
            completed_at=datetime.now(UTC),
            error_message=provider_result.error_message,
        )
        completed_run_record = EvaluationRunRecord.from_domain(completed_run)
        metric_result_records = tuple(
            EvaluationMetricResultRecord.from_domain(metric_result)
            for metric_result in provider_result.metric_results
        )
        final_result = await self.repository.persist_evaluation_bundle(
            EvaluationPersistenceBundle(
                runs=(completed_run_record,),
                metric_results=metric_result_records,
            )
        )
        if self.telemetry is not None:
            self.telemetry.record_cases_evaluated(
                target_type=request.target_type,
                evaluator_provider=provider_result.evaluator_provider,
                evaluator_model=provider_result.evaluator_model,
                case_count=len(request.cases),
            )
            for metric_result in provider_result.metric_results:
                self.telemetry.record_metric_result(
                    metric_result,
                    target_type=request.target_type,
                )
            await self.telemetry.emit_run_completed(
                run_id=request.run_id,
                target_type=request.target_type,
                status=provider_result.status,
                evaluator_provider=provider_result.evaluator_provider,
                evaluator_model=provider_result.evaluator_model,
                case_count=len(request.cases),
                metric_result_count=len(provider_result.metric_results),
                dataset_id=dataset_id,
                duration_seconds=perf_counter() - started_monotonic,
                authority_gate_decision=authority_gate_decision,
            )
        projection_result = await self._project_scores(
            completed_run_record,
            metric_result_records,
            case_records,
        )
        return EvaluationRunServiceResult(
            run=completed_run,
            metric_results=tuple(provider_result.metric_results),
            persistence_result=_combine_persistence_results(
                initial_result, final_result
            ),
            langfuse_projection_result=projection_result,
            authority_gate_decision=authority_gate_decision,
        )

    async def _project_scores(
        self,
        run_record: EvaluationRunRecord,
        metric_result_records: tuple[EvaluationMetricResultRecord, ...],
        case_records: tuple[EvaluationCaseRecord, ...],
    ) -> EvaluationLangfuseProjectionResult | None:
        if not metric_result_records:
            return None
        try:
            result = await self.projection_service.project_run_scores(
                EvaluationLangfuseProjectionRequest(
                    run=run_record,
                    metric_results=metric_result_records,
                    cases=case_records,
                )
            )
            if self.telemetry is not None:
                self.telemetry.record_langfuse_projection_failures(
                    run_id=run_record.run_id,
                    target_type=run_record.target_type,
                    failed_count=result.failed_count,
                )
            return result
        except Exception:
            logger.debug(
                "Langfuse evaluation-score projection request failed.",
                extra={"run_id": run_record.run_id},
                exc_info=True,
            )
            failed_count = _metric_result_case_count(metric_result_records)
            if self.telemetry is not None:
                self.telemetry.record_langfuse_projection_failures(
                    run_id=run_record.run_id,
                    target_type=run_record.target_type,
                    failed_count=failed_count,
                )
            return EvaluationLangfuseProjectionResult(
                export_results=(),
                failed_count=failed_count,
            )


def _select_authority_gate(
    request: EvaluationRunServiceRequest,
) -> RiskAuthorityGateDecision:
    return select_risk_authority_gate(
        request.authority_metadata,
        evidence=request.authority_gate_evidence,
        expected_authority_metadata=expected_authority_metadata_for_evaluation_target(
            request.target_type,
        ),
    )


def expected_authority_metadata_for_evaluation_target(
    target_type: EvaluationTargetType,
) -> dict[str, object]:
    return classify_risk_authority(
        _authority_classification_input_for_target(target_type),
    ).to_metadata()


def authority_gate_evidence_for_evaluation_cases(
    target_type: EvaluationTargetType,
    cases: Sequence[EvaluationCase],
    *,
    run_id: str,
) -> RiskAuthorityGateEvidence:
    provenance_ids = _provenance_ids_for_evaluation_cases(cases)
    decision_ids = (
        (f"evaluation_run:{run_id}",)
        if target_type
        in {
            EvaluationTargetType.STRATEGY_SYNTHESIS,
            EvaluationTargetType.RECOMMENDATION_EXPLANATION,
            EvaluationTargetType.MCP_TOOL_RESPONSE,
        }
        else ()
    )
    return RiskAuthorityGateEvidence(
        provenance_record_ids=provenance_ids,
        decision_evidence_ids=decision_ids,
        evaluation_run_ids=(run_id,),
    )


def _provenance_ids_for_evaluation_cases(
    cases: Sequence[EvaluationCase],
) -> tuple[str, ...]:
    provenance_ids: list[str] = []
    for case in cases:
        provenance_ids.extend(case.source_record_ids)
        provenance_ids.extend(case.citation_context_ids)
        if case.workflow_execution_id is not None:
            provenance_ids.append(case.workflow_execution_id)
        provenance_ids.append(case.case_id)
    return tuple(dict.fromkeys(provenance_ids))


def _authority_classification_input_for_target(
    target_type: EvaluationTargetType,
) -> RiskAuthorityClassificationInput:
    if target_type is EvaluationTargetType.RAG_RETRIEVAL:
        return RiskAuthorityClassificationInput(
            content_type=AiOutputContentType.RUNTIME_EVIDENCE,
            authority_effect=AuthorityEffect.NON_AUTHORITATIVE_INFORMATION,
            canonical_owner=CanonicalOwner.RUNTIME,
            source_of_truth=SourceOfTruthCategory.RUNTIME_EVIDENCE,
            intended_sink=IntendedSink.INTERNAL_RUNTIME_EVIDENCE,
        )
    if target_type in {
        EvaluationTargetType.RAG_ANSWER,
        EvaluationTargetType.RAG_GENERATION,
    }:
        return RiskAuthorityClassificationInput(
            content_type=AiOutputContentType.RAG_ANSWER,
            authority_effect=AuthorityEffect.NON_AUTHORITATIVE_INFORMATION,
            canonical_owner=CanonicalOwner.RAG_SERVICE,
            source_of_truth=SourceOfTruthCategory.PRESENTATION_OUTPUT,
            intended_sink=IntendedSink.RAG_ANSWER,
            externally_visible=True,
        )
    if target_type is EvaluationTargetType.MORNING_REPORT:
        return RiskAuthorityClassificationInput(
            content_type=AiOutputContentType.REPORT,
            authority_effect=AuthorityEffect.ADVISORY_CONTEXT,
            canonical_owner=CanonicalOwner.REPORT_SERVICE,
            source_of_truth=SourceOfTruthCategory.PRESENTATION_OUTPUT,
            intended_sink=IntendedSink.REPORT,
            externally_visible=True,
        )
    if target_type is EvaluationTargetType.STRATEGY_SYNTHESIS:
        return RiskAuthorityClassificationInput(
            content_type=AiOutputContentType.STRATEGY_SYNTHESIS,
            authority_effect=AuthorityEffect.DETERMINISTIC_PLATFORM_DECISION,
            canonical_owner=CanonicalOwner.STRATEGY_SERVICE,
            source_of_truth=SourceOfTruthCategory.CANONICAL_DOMAIN_RECORD,
            intended_sink=IntendedSink.DURABLE_DOMAIN_RECORD,
            capital_relevant=True,
            durable_authority=True,
        )
    if target_type is EvaluationTargetType.RECOMMENDATION_EXPLANATION:
        return RiskAuthorityClassificationInput(
            content_type=AiOutputContentType.RECOMMENDATION_EXPLANATION,
            authority_effect=AuthorityEffect.ADVISORY_CONTEXT,
            canonical_owner=CanonicalOwner.RECOMMENDATION_SERVICE,
            source_of_truth=SourceOfTruthCategory.CANONICAL_DOMAIN_RECORD,
            intended_sink=IntendedSink.RECOMMENDATION,
            capital_relevant=True,
            externally_visible=True,
        )
    if target_type is EvaluationTargetType.MCP_TOOL_RESPONSE:
        return RiskAuthorityClassificationInput(
            content_type=AiOutputContentType.TOOL_RESPONSE,
            authority_effect=AuthorityEffect.OUTSIDE_AUTHORITY,
            canonical_owner=CanonicalOwner.APPLICATION_SERVICE,
            source_of_truth=SourceOfTruthCategory.EXTERNAL_TRANSPORT_PAYLOAD,
            intended_sink=IntendedSink.MCP_TOOL_RESPONSE,
            capital_relevant=True,
            externally_visible=True,
        )
    return RiskAuthorityClassificationInput(
        content_type=AiOutputContentType.RUNTIME_EVIDENCE,
        authority_effect=AuthorityEffect.NON_AUTHORITATIVE_INFORMATION,
        canonical_owner=CanonicalOwner.EVALUATION_SERVICE,
        source_of_truth=SourceOfTruthCategory.RUNTIME_EVIDENCE,
        intended_sink=IntendedSink.EVALUATION_GATE,
    )


def _dataset_records(
    request: EvaluationRunServiceRequest,
) -> tuple[EvaluationDatasetRecord, ...]:
    if request.dataset is None:
        return ()
    try:
        definition = canonical_evaluation_dataset_definition_by_name(
            request.dataset.name
        )
    except KeyError:
        return (
            EvaluationDatasetRecord.from_reference(
                request.dataset,
                target_type=request.target_type,
                threshold_profile={},
            ),
        )
    if definition.reference.dataset_id != request.dataset.dataset_id:
        return (
            EvaluationDatasetRecord.from_reference(
                request.dataset,
                target_type=request.target_type,
                threshold_profile={},
            ),
        )
    return (
        EvaluationDatasetRecord.from_reference(
            definition.reference,
            target_type=definition.target_type,
            description=definition.description,
            source_lineage=definition.source_lineage,
            deterministic_fixture_uri=definition.deterministic_fixture_uri,
            threshold_profile=definition.threshold_profile,
        ),
    )


def _combine_persistence_results(
    first: EvaluationPersistenceResult,
    second: EvaluationPersistenceResult,
) -> EvaluationPersistenceResult:
    return EvaluationPersistenceResult(
        datasets_written=first.datasets_written + second.datasets_written,
        cases_written=first.cases_written + second.cases_written,
        runs_written=first.runs_written + second.runs_written,
        metric_results_written=(
            first.metric_results_written + second.metric_results_written
        ),
        artifacts_written=first.artifacts_written + second.artifacts_written,
    )


def _metric_result_case_count(
    metric_result_records: tuple[EvaluationMetricResultRecord, ...],
) -> int:
    return len({record.case_id for record in metric_result_records})
