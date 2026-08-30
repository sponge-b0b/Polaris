from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from application.evaluations.risk_authority_gate import (
    RiskAuthorityGateDecision,
    RiskAuthorityGateEvidence,
    RiskAuthorityGateFailureMode,
    select_risk_authority_gate,
)
from application.governance.automated_decision_audit import (
    GovernanceReviewApprovalState,
    GovernedOutputReleaseDecision,
    requires_governed_output_release_review,
)
from core.telemetry.observability import ObservabilityManager
from core.telemetry.tracing import TraceContext
from domain.authority import (
    GateProfile,
    RiskAuthorityContract,
    RiskTier,
    validate_risk_authority_metadata,
)

logger = logging.getLogger(__name__)

_PRESENTATION_SINK_EVENT_TYPE = "presentation.sink_decision"
_PRESENTATION_SINK_EVENT_SOURCE = "PresentationSinkDecisionService"


class PresentationSinkDisposition(StrEnum):
    """Externally meaningful disposition for one presentation boundary."""

    ELIGIBLE = "eligible"
    DEGRADED = "degraded"
    WITHHELD = "withheld"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class PresentationSinkDecision:
    """Presentation disposition derived from canonical platform readiness."""

    disposition: PresentationSinkDisposition
    gate_decision: RiskAuthorityGateDecision
    reasons: tuple[str, ...]
    limitations: tuple[str, ...] = ()
    governed_release_decisions: tuple[GovernedOutputReleaseDecision, ...] = ()

    @property
    def may_present(self) -> bool:
        return self.disposition in {
            PresentationSinkDisposition.ELIGIBLE,
            PresentationSinkDisposition.DEGRADED,
        }

    @property
    def risk_tier(self) -> RiskTier | None:
        return self.gate_decision.risk_tier

    @property
    def gate_profile(self) -> GateProfile | None:
        return self.gate_decision.gate_profile

    @property
    def authority_metadata(self) -> Mapping[str, object] | None:
        return self.gate_decision.authority_metadata

    @property
    def gate_failure_mode(self) -> RiskAuthorityGateFailureMode:
        return self.gate_decision.failure_mode

    @property
    def readiness_passed(self) -> bool:
        return self.gate_decision.passed

    @property
    def provenance_record_ids(self) -> tuple[str, ...]:
        return self.gate_decision.evidence.provenance_record_ids

    @property
    def decision_evidence_packet_ids(self) -> tuple[str, ...]:
        return tuple(
            packet.packet_id
            for packet in self.gate_decision.evidence.decision_evidence_packets
        )

    @property
    def governed_release_allowed(self) -> bool | None:
        if not self.governed_release_decisions:
            return None
        return all(decision.allowed for decision in self.governed_release_decisions)

    @property
    def governance_approval_states(self) -> tuple[GovernanceReviewApprovalState, ...]:
        return tuple(
            decision.approval_state
            for decision in self.governed_release_decisions
            if decision.approval_state is not None
        )


class PresentationSinkDecisionService:
    """Own presentation disposition and its non-eligible observability event."""

    def __init__(
        self,
        observability_manager: ObservabilityManager | None = None,
    ) -> None:
        self._observability = observability_manager

    async def evaluate(
        self,
        authority_metadata: Mapping[str, object] | RiskAuthorityContract | None,
        *,
        evidence: RiskAuthorityGateEvidence | None = None,
        expected_authority_metadata: (
            Mapping[str, object] | RiskAuthorityContract | None
        ) = None,
        governed_release_decisions: tuple[GovernedOutputReleaseDecision, ...] = (),
        limitations: tuple[str, ...] = (),
        degradation_reasons: tuple[str, ...] = (),
        withholding_reasons: tuple[str, ...] = (),
        blocking_reasons: tuple[str, ...] = (),
        trace_context: TraceContext | None = None,
    ) -> PresentationSinkDecision:
        """Select a fail-closed presentation disposition from canonical readiness."""

        gate_decision = select_risk_authority_gate(
            authority_metadata,
            evidence=evidence,
            expected_authority_metadata=expected_authority_metadata,
        )
        release_decisions = governed_release_decisions or tuple(
            item.release_decision
            for item in gate_decision.evidence.output_governance_evidence
        )
        governed_release_reasons = _governed_release_reasons(
            gate_decision,
            release_decisions,
        )
        decision = _presentation_decision(
            gate_decision,
            governed_release_decisions=release_decisions,
            governed_release_reasons=governed_release_reasons,
            limitations=_clean_strings(limitations, "limitations"),
            degradation_reasons=_clean_strings(
                degradation_reasons,
                "degradation_reasons",
            ),
            withholding_reasons=_clean_strings(
                withholding_reasons,
                "withholding_reasons",
            ),
            blocking_reasons=_clean_strings(
                blocking_reasons,
                "blocking_reasons",
            ),
        )
        await self._emit_non_eligible_decision(decision, trace_context=trace_context)
        return decision

    async def _emit_non_eligible_decision(
        self,
        decision: PresentationSinkDecision,
        *,
        trace_context: TraceContext | None,
    ) -> None:
        if (
            self._observability is None
            or decision.disposition is PresentationSinkDisposition.ELIGIBLE
        ):
            return
        try:
            await self._observability.warning(
                _PRESENTATION_SINK_EVENT_TYPE,
                _PRESENTATION_SINK_EVENT_SOURCE,
                attributes={
                    "disposition": decision.disposition.value,
                    "risk_tier": (
                        decision.risk_tier.value
                        if decision.risk_tier is not None
                        else "unknown"
                    ),
                    "gate_profile": (
                        decision.gate_profile.value
                        if decision.gate_profile is not None
                        else "unknown"
                    ),
                    "gate_failure_mode": decision.gate_failure_mode.value,
                    "reason_count": len(decision.reasons),
                    "limitation_count": len(decision.limitations),
                },
                trace_context=trace_context,
            )
        except Exception:
            logger.exception("Failed to emit presentation sink decision telemetry.")


def _governed_release_reasons(
    gate_decision: RiskAuthorityGateDecision,
    release_decisions: tuple[GovernedOutputReleaseDecision, ...],
) -> tuple[str, ...]:
    if not gate_decision.passed or gate_decision.authority_metadata is None:
        return ()

    authority = validate_risk_authority_metadata(
        gate_decision.authority_metadata,
    ).expected_contract
    if not requires_governed_output_release_review(authority):
        return ()
    if not release_decisions:
        return ("Canonical governed output release decision is required.",)

    blocked_reasons = tuple(
        decision.reason.strip()
        or "Canonical governed output release decision does not permit release."
        for decision in release_decisions
        if not decision.allowed
    )
    return blocked_reasons


def _presentation_decision(
    gate_decision: RiskAuthorityGateDecision,
    *,
    governed_release_decisions: tuple[GovernedOutputReleaseDecision, ...],
    governed_release_reasons: tuple[str, ...],
    limitations: tuple[str, ...],
    degradation_reasons: tuple[str, ...],
    withholding_reasons: tuple[str, ...],
    blocking_reasons: tuple[str, ...],
) -> PresentationSinkDecision:
    effective_withholding_reasons = (
        *withholding_reasons,
        *governed_release_reasons,
    )
    gate_disposition = _gate_disposition(gate_decision)
    boundary_disposition = _boundary_disposition(
        degradation_reasons=degradation_reasons,
        withholding_reasons=effective_withholding_reasons,
        blocking_reasons=blocking_reasons,
    )
    disposition = max(
        (gate_disposition, boundary_disposition),
        key=_disposition_rank,
    )
    return PresentationSinkDecision(
        disposition=disposition,
        gate_decision=gate_decision,
        reasons=(
            gate_decision.message,
            *degradation_reasons,
            *effective_withholding_reasons,
            *blocking_reasons,
        ),
        limitations=limitations,
        governed_release_decisions=governed_release_decisions,
    )


def _gate_disposition(
    gate_decision: RiskAuthorityGateDecision,
) -> PresentationSinkDisposition:
    if gate_decision.passed:
        return PresentationSinkDisposition.ELIGIBLE
    if gate_decision.failure_mode in {
        RiskAuthorityGateFailureMode.METADATA_MISSING,
        RiskAuthorityGateFailureMode.PROVENANCE_EVIDENCE_REQUIRED,
        RiskAuthorityGateFailureMode.DECISION_EVIDENCE_REQUIRED,
        RiskAuthorityGateFailureMode.OUTPUT_GOVERNANCE_EVIDENCE_REQUIRED,
    }:
        return PresentationSinkDisposition.WITHHELD
    return PresentationSinkDisposition.BLOCKED


def _boundary_disposition(
    *,
    degradation_reasons: tuple[str, ...],
    withholding_reasons: tuple[str, ...],
    blocking_reasons: tuple[str, ...],
) -> PresentationSinkDisposition:
    if blocking_reasons:
        return PresentationSinkDisposition.BLOCKED
    if withholding_reasons:
        return PresentationSinkDisposition.WITHHELD
    if degradation_reasons:
        return PresentationSinkDisposition.DEGRADED
    return PresentationSinkDisposition.ELIGIBLE


def _disposition_rank(disposition: PresentationSinkDisposition) -> int:
    return {
        PresentationSinkDisposition.ELIGIBLE: 0,
        PresentationSinkDisposition.DEGRADED: 1,
        PresentationSinkDisposition.WITHHELD: 2,
        PresentationSinkDisposition.BLOCKED: 3,
    }[disposition]


def _clean_strings(values: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    cleaned: list[str] = []
    for value in values:
        normalized = value.strip()
        if not normalized:
            raise ValueError(f"{field_name} cannot contain empty strings.")
        cleaned.append(normalized)
    return tuple(cleaned)
