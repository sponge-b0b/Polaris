from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Final

from application.decision_evidence.claim_binding import (
    ClaimEvidenceBindingError,
    DecisionEvidenceClaimBindingService,
    RecommendationClaimEvidenceBindingTarget,
    ensure_material_claim_evidence_links_bound,
    has_material_claim_references,
)
from application.decision_evidence.persistence import (
    DecisionEvidencePacketReconstructionError,
)
from application.persistence.recommendations import RecommendationPersistenceService
from application.projections.workflow_outputs.projection_models import (
    WorkflowOutputProjectionOutcome,
    WorkflowOutputProjectionStatus,
    WorkflowOutputProjectorRequest,
)
from application.projections.workflow_outputs.projection_registry import (
    WorkflowOutputProjectorRegistration,
)
from core.storage.persistence.lineage import JsonObject
from core.storage.persistence.recommendations import (
    RecommendationClaimEvidenceLinkRecord,
    RecommendationPersistenceBundle,
    RecommendationRationaleRecord,
    RecommendationRecord,
    TradeSetupRecord,
    new_recommendation_child_id,
    new_recommendation_id,
)
from domain.authority import (
    RiskTier,
    authority_contract_metadata,
    model_authority_claims_from_payloads,
    recommendation_rationale_authority,
    recommendation_record_authority,
)
from domain.decision_evidence import (
    DECISION_EVIDENCE_CLAIM_REFERENCES_METADATA_KEY,
    DecisionEvidencePacketValidationError,
    EvidenceClaimReference,
    evidence_claim_references_from_metadata,
)
from domain.workflow_outputs import (
    PORTFOLIO_ALLOCATION_INTENT_OUTPUT_CONTRACT,
    TRADE_RECOMMENDATION_OUTPUT_CONTRACT,
    WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
)

PORTFOLIO_ALLOCATION_INTENT_PROJECTOR_NAME: Final = (
    "portfolio_allocation_intent_projector"
)
TRADE_RECOMMENDATION_PROJECTOR_NAME: Final = "trade_recommendation_projector"
_HIGH_RISK_RECOMMENDATION_CLAIM_PROVENANCE_TIERS: Final = frozenset(
    (RiskTier.ENHANCED.value, RiskTier.VIGILANT.value),
)


class PortfolioAllocationIntentWorkflowOutputProjector:
    """Project portfolio allocation intent into recommendation records."""

    def __init__(
        self,
        recommendation_persistence_service: RecommendationPersistenceService,
        *,
        claim_binding_service: DecisionEvidenceClaimBindingService | None = None,
    ) -> None:
        self._recommendation_persistence_service = recommendation_persistence_service
        self._claim_binding_service = claim_binding_service

    @property
    def projector_name(self) -> str:
        return PORTFOLIO_ALLOCATION_INTENT_PROJECTOR_NAME

    async def project(
        self,
        request: WorkflowOutputProjectorRequest,
    ) -> WorkflowOutputProjectionOutcome:
        outputs = _mapping(request.node_output.outputs)
        features = _mapping(outputs.get("features"))
        symbol = _symbol(request, outputs, features)
        if symbol is None:
            return _skipped(request, self.projector_name, "Allocation symbol missing.")
        recommendation_id = new_recommendation_id(
            symbol=symbol,
            execution_id=request.run.execution_id,
            recommendation_key="portfolio_allocation_intent",
        )
        confidence = _score(outputs.get("confidence")) or 0.0
        model_authority_claims = model_authority_claims_from_payloads(
            outputs,
            features,
        )
        try:
            claim_references = _claim_references_from_boundary_payloads(
                outputs, features
            )
            rationale = _rationale(
                recommendation_id=recommendation_id,
                request=request,
                rationale_type="portfolio_allocation_intent",
                rationale_text=_rationale_text(outputs, "Portfolio allocation intent."),
                confidence=confidence,
            )
            claim_evidence_links = await _bind_recommendation_claim_evidence(
                self._claim_binding_service,
                recommendation_id=recommendation_id,
                rationale=rationale,
                claim_references=claim_references,
            )
        except (
            ClaimEvidenceBindingError,
            DecisionEvidencePacketReconstructionError,
            DecisionEvidencePacketValidationError,
        ) as exc:
            return _failed(
                request,
                self.projector_name,
                str(exc),
                error_type=exc.__class__.__name__,
            )
        bundle = RecommendationPersistenceBundle(
            recommendation=RecommendationRecord(
                recommendation_id=recommendation_id,
                symbol=symbol,
                bias=_text(outputs.get("regime"), default="allocation_intent"),
                confidence=confidence,
                created_at=_timestamp(request),
                lineage=request.lineage,
                setup_quality=_score(features.get("scale_factor")),
                risk_score=_score(features.get("composite_risk")),
                risk_level=_risk_level(_score(features.get("composite_risk"))),
                time_horizon=_optional_text(request.run.inputs_json.get("horizon")),
                status="allocation_intent",
                metadata={
                    "execution_status": _optional_text(
                        features.get("execution_status")
                    ),
                    "portfolio_regime": _optional_text(
                        features.get("portfolio_regime")
                    ),
                    "selected_perspective": _optional_text(
                        features.get("selected_perspective")
                    ),
                    "selection_status": _optional_text(
                        features.get("selection_status")
                    ),
                    "source_fingerprint": request.source_fingerprint,
                    "node_output_id": request.node_output.node_output_id,
                    **authority_contract_metadata(
                        recommendation_record_authority(model_authority_claims)
                    ),
                },
            ),
            rationales=(rationale,),
            claim_evidence_links=claim_evidence_links,
        )
        result = await self._recommendation_persistence_service.persist_bundle(bundle)
        if not result.success:
            return _failed(
                request,
                self.projector_name,
                result.error or "Allocation intent persistence failed.",
            )
        return _outcome(
            request=request,
            projector_name=self.projector_name,
            status=WorkflowOutputProjectionStatus.SUCCEEDED,
            records_written=result.records_persisted,
            message=(
                "Portfolio allocation intent projected into recommendation records."
            ),
        )


class TradeRecommendationWorkflowOutputProjector:
    """Project broker-agnostic trade recommendations into recommendation records."""

    def __init__(
        self,
        recommendation_persistence_service: RecommendationPersistenceService,
        *,
        claim_binding_service: DecisionEvidenceClaimBindingService | None = None,
    ) -> None:
        self._recommendation_persistence_service = recommendation_persistence_service
        self._claim_binding_service = claim_binding_service

    @property
    def projector_name(self) -> str:
        return TRADE_RECOMMENDATION_PROJECTOR_NAME

    async def project(
        self,
        request: WorkflowOutputProjectorRequest,
    ) -> WorkflowOutputProjectionOutcome:
        outputs = _mapping(request.node_output.outputs)
        features = _mapping(outputs.get("features"))
        trade_intent = _mapping(features.get("trade_intent"))
        symbol = _symbol(request, outputs, features)
        if symbol is None:
            return _skipped(request, self.projector_name, "Trade symbol missing.")
        recommendation_id = new_recommendation_id(
            symbol=symbol,
            execution_id=request.run.execution_id,
            recommendation_key="trade_recommendation",
        )
        created_at = _timestamp(request)
        confidence = (
            _score(outputs.get("confidence"))
            or _score(trade_intent.get("confidence"))
            or 0.0
        )
        direction = _text(
            outputs.get("regime"),
            default=_text(trade_intent.get("direction"), default="flat"),
        )
        entry_context: JsonObject = {
            "entry_bias": _json_scalar(trade_intent.get("entry_bias")),
            "position_sizing_hint": _json_scalar(
                trade_intent.get("position_sizing_hint")
            ),
        }
        stop_context: JsonObject = {
            "stop_distance": _json_scalar(trade_intent.get("stop_distance")),
        }
        target_context: JsonObject = {
            "take_profit_distance": _json_scalar(
                trade_intent.get("take_profit_distance")
            ),
        }
        model_authority_claims = model_authority_claims_from_payloads(
            outputs,
            features,
            trade_intent,
        )
        recommendation = RecommendationRecord(
            recommendation_id=recommendation_id,
            symbol=symbol,
            bias=direction,
            confidence=confidence,
            created_at=created_at,
            lineage=request.lineage,
            setup_quality=_score(features.get("trade_quality_score")),
            risk_score=_score(features.get("risk_pressure")),
            risk_level=_risk_level(_score(features.get("risk_pressure"))),
            time_horizon=_optional_text(request.run.inputs_json.get("horizon")),
            status="trade_proposal",
            entry_context=entry_context,
            stop_context=stop_context,
            target_context=target_context,
            metadata={
                "risk_alignment": _json_scalar(features.get("risk_alignment")),
                "technical_regime": _optional_text(features.get("technical_regime")),
                "source_fingerprint": request.source_fingerprint,
                "node_output_id": request.node_output.node_output_id,
                **authority_contract_metadata(
                    recommendation_record_authority(model_authority_claims)
                ),
            },
        )
        trade_setup = TradeSetupRecord(
            setup_id=new_recommendation_child_id(
                recommendation_id=recommendation_id,
                child_type="trade_setup",
                child_key="primary",
            ),
            recommendation_id=recommendation_id,
            symbol=symbol,
            setup_type="trade_recommendation",
            bias=direction,
            created_at=created_at,
            lineage=request.lineage,
            setup_quality=_score(features.get("trade_quality_score")),
            confidence=confidence,
            risk_score=_score(features.get("risk_pressure")),
            risk_reward_ratio=_risk_reward_ratio(features),
            time_horizon=_optional_text(request.run.inputs_json.get("horizon")),
            entry_context=entry_context,
            stop_context=stop_context,
            target_context=target_context,
            metadata={
                "trade_intent_reasoning": _optional_text(trade_intent.get("reasoning")),
                **authority_contract_metadata(
                    recommendation_record_authority(model_authority_claims)
                ),
            },
        )
        try:
            claim_references = _claim_references_from_boundary_payloads(
                outputs,
                features,
                trade_intent,
            )
            rationale = _rationale(
                recommendation_id=recommendation_id,
                request=request,
                rationale_type="trade_recommendation",
                rationale_text=_rationale_text(outputs, "Trade recommendation."),
                confidence=confidence,
            )
            claim_evidence_links = await _bind_recommendation_claim_evidence(
                self._claim_binding_service,
                recommendation_id=recommendation_id,
                rationale=rationale,
                claim_references=claim_references,
            )
        except (
            ClaimEvidenceBindingError,
            DecisionEvidencePacketReconstructionError,
            DecisionEvidencePacketValidationError,
        ) as exc:
            return _failed(
                request,
                self.projector_name,
                str(exc),
                error_type=exc.__class__.__name__,
            )
        bundle = RecommendationPersistenceBundle(
            recommendation=recommendation,
            rationales=(rationale,),
            trade_setups=(trade_setup,),
            claim_evidence_links=claim_evidence_links,
        )
        result = await self._recommendation_persistence_service.persist_bundle(bundle)
        if not result.success:
            return _failed(
                request,
                self.projector_name,
                result.error or "Trade recommendation persistence failed.",
            )
        return _outcome(
            request=request,
            projector_name=self.projector_name,
            status=WorkflowOutputProjectionStatus.SUCCEEDED,
            records_written=result.records_persisted,
            message="Trade recommendation projected into recommendation records.",
        )


def build_recommendation_projector_registrations(
    recommendation_persistence_service: RecommendationPersistenceService,
    *,
    claim_binding_service: DecisionEvidenceClaimBindingService | None = None,
) -> tuple[WorkflowOutputProjectorRegistration, ...]:
    """Build canonical recommendation projector registrations."""
    expected_record_authority = recommendation_record_authority()
    allocation_projector = PortfolioAllocationIntentWorkflowOutputProjector(
        recommendation_persistence_service,
        claim_binding_service=claim_binding_service,
    )
    trade_projector = TradeRecommendationWorkflowOutputProjector(
        recommendation_persistence_service,
        claim_binding_service=claim_binding_service,
    )
    return (
        WorkflowOutputProjectorRegistration(
            projector_name=PORTFOLIO_ALLOCATION_INTENT_PROJECTOR_NAME,
            output_contract=PORTFOLIO_ALLOCATION_INTENT_OUTPUT_CONTRACT,
            output_schema_version=WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
            projector=allocation_projector,
            supported_node_names=("portfolio_manager_agent",),
            expected_authority_contract=expected_record_authority,
        ),
        WorkflowOutputProjectorRegistration(
            projector_name=TRADE_RECOMMENDATION_PROJECTOR_NAME,
            output_contract=TRADE_RECOMMENDATION_OUTPUT_CONTRACT,
            output_schema_version=WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
            projector=trade_projector,
            supported_node_names=("trade_packager",),
            expected_authority_contract=expected_record_authority,
        ),
    )


async def _bind_recommendation_claim_evidence(
    claim_binding_service: DecisionEvidenceClaimBindingService | None,
    *,
    recommendation_id: str,
    rationale: RecommendationRationaleRecord,
    claim_references: tuple[EvidenceClaimReference, ...],
) -> tuple[RecommendationClaimEvidenceLinkRecord, ...]:
    if not claim_references:
        _ensure_recommendation_claim_audit_treatment_present(rationale)
        return ()
    targets = tuple(
        RecommendationClaimEvidenceBindingTarget(
            rationale_id=rationale.rationale_id,
            claim_target_id=f"{rationale.rationale_id}:claim:{reference.claim_id}",
            claim_references=(reference,),
        )
        for reference in claim_references
    )
    if claim_binding_service is None:
        if has_material_claim_references(targets):
            raise ClaimEvidenceBindingError(
                "canonical claim evidence binding service is required for "
                "material recommendation claim references."
            )
        return ()
    links = await claim_binding_service.bind_recommendation_claims(
        recommendation_id=recommendation_id,
        targets=targets,
    )
    ensure_material_claim_evidence_links_bound(
        targets=targets,
        links=links,
        boundary_name="recommendation projection",
    )
    return links


def _ensure_recommendation_claim_audit_treatment_present(
    rationale: RecommendationRationaleRecord,
) -> None:
    risk_authority = rationale.metadata.get("risk_authority")
    if not isinstance(risk_authority, Mapping):
        return
    risk_tier = risk_authority.get("risk_tier")
    if risk_tier not in _HIGH_RISK_RECOMMENDATION_CLAIM_PROVENANCE_TIERS:
        return

    raise ClaimEvidenceBindingError(
        "recommendation projection "
        f"{risk_tier} rationale has no explicit decision-evidence claim audit "
        "treatment from workflow output or feature metadata; material "
        "recommendation records and rationales require canonical "
        "decision-evidence packet provenance before persistence."
    )


def _rationale(
    *,
    recommendation_id: str,
    request: WorkflowOutputProjectorRequest,
    rationale_type: str,
    rationale_text: str,
    confidence: float,
) -> RecommendationRationaleRecord:
    outputs = _mapping(request.node_output.outputs)
    features = _mapping(outputs.get("features"))
    return RecommendationRationaleRecord(
        rationale_id=new_recommendation_child_id(
            recommendation_id=recommendation_id,
            child_type="rationale",
            child_key=rationale_type,
        ),
        recommendation_id=recommendation_id,
        rationale_type=rationale_type,
        rationale_text=rationale_text,
        created_at=_timestamp(request),
        lineage=request.lineage,
        confidence=confidence,
        metadata={
            "source_fingerprint": request.source_fingerprint,
            **authority_contract_metadata(
                recommendation_rationale_authority(
                    model_authority_claims_from_payloads(
                        outputs,
                        features,
                    )
                )
            ),
        },
    )


def _claim_references_from_boundary_payloads(
    *payloads: Mapping[str, object],
) -> tuple[EvidenceClaimReference, ...]:
    """Read boundary-serialized claim refs before durable rationale persistence."""

    for payload in payloads:
        value = payload.get(DECISION_EVIDENCE_CLAIM_REFERENCES_METADATA_KEY)
        if value is None:
            continue
        return evidence_claim_references_from_metadata(value).claim_references
    return ()


def _rationale_text(outputs: Mapping[str, object], fallback: str) -> str:
    features = _mapping(outputs.get("features"))
    for value in (
        features.get("thesis"),
        outputs.get("thesis"),
        features.get("reasoning"),
    ):
        text = _optional_text(value)
        if text is not None:
            return text
    recommendations = outputs.get("recommendations")
    if isinstance(recommendations, list) and recommendations:
        return "; ".join(str(item) for item in recommendations if item is not None)
    return fallback


def _timestamp(request: WorkflowOutputProjectorRequest) -> datetime:
    return (
        request.node_output.completed_at
        or request.node_output.started_at
        or request.run.completed_at
        or request.run.started_at
        or request.requested_at
        or datetime.now(UTC)
    )


def _symbol(
    request: WorkflowOutputProjectorRequest,
    outputs: Mapping[str, object],
    features: Mapping[str, object],
) -> str | None:
    trade_intent = _mapping(features.get("trade_intent"))
    for value in (
        outputs.get("symbol"),
        features.get("symbol"),
        trade_intent.get("symbol"),
        request.run.inputs_json.get("symbol"),
        request.node_output.metadata.get("symbol"),
    ):
        text = _optional_text(value)
        if text is not None:
            return text.upper()
    return None


def _risk_reward_ratio(features: Mapping[str, object]) -> float | None:
    stop = _positive_float(features.get("stop_distance"))
    target = _positive_float(features.get("take_profit_distance"))
    if stop is None or target is None or stop == 0.0:
        return None
    return target / stop


def _risk_level(risk_score: float | None) -> str | None:
    if risk_score is None:
        return None
    if risk_score >= 0.7:
        return "high"
    if risk_score >= 0.4:
        return "medium"
    return "low"


def _mapping(value: object) -> Mapping[str, object]:
    if isinstance(value, Mapping):
        return {str(key): item for key, item in value.items()}
    return {}


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _text(value: object, *, default: str) -> str:
    return _optional_text(value) or default


def _score(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    numeric = float(value)
    if 0.0 <= numeric <= 1.0:
        return numeric
    return None


def _positive_float(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    numeric = float(value)
    if numeric > 0.0:
        return numeric
    return None


def _json_scalar(value: object) -> str | int | float | bool | None:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _outcome(
    *,
    request: WorkflowOutputProjectorRequest,
    projector_name: str,
    status: WorkflowOutputProjectionStatus,
    records_written: int,
    message: str,
) -> WorkflowOutputProjectionOutcome:
    return WorkflowOutputProjectionOutcome(
        status=status,
        projector_name=projector_name,
        node_name=request.node_output.node_name,
        output_contract=request.node_output.output_contract or "unknown",
        output_schema_version=request.node_output.output_schema_version or 1,
        source_fingerprint=request.source_fingerprint,
        records_written=records_written,
        message=message,
    )


def _skipped(
    request: WorkflowOutputProjectorRequest,
    projector_name: str,
    message: str,
) -> WorkflowOutputProjectionOutcome:
    return _outcome(
        request=request,
        projector_name=projector_name,
        status=WorkflowOutputProjectionStatus.SKIPPED,
        records_written=0,
        message=message,
    )


def _failed(
    request: WorkflowOutputProjectorRequest,
    projector_name: str,
    error: str,
    *,
    error_type: str = "PersistenceError",
) -> WorkflowOutputProjectionOutcome:
    return WorkflowOutputProjectionOutcome(
        status=WorkflowOutputProjectionStatus.FAILED,
        projector_name=projector_name,
        node_name=request.node_output.node_name,
        output_contract=request.node_output.output_contract or "unknown",
        output_schema_version=request.node_output.output_schema_version or 1,
        source_fingerprint=request.source_fingerprint,
        error_type=error_type,
        error_message=error,
        message="Recommendation projection failed.",
    )
