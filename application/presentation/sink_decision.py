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
)
from core.telemetry.observability import ObservabilityManager
from core.telemetry.tracing import TraceContext
from domain.authority import GateProfile, RiskAuthorityContract, RiskTier

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
    def provenance_record_ids(self) -> tuple[str, ...]:
        return self.gate_decision.evidence.provenance_record_ids

    @property
    def decision_evidence_packet_ids(self) -> tuple[str, ...]:
        return tuple(
            packet.packet_id
            for packet in self.gate_decision.evidence.decision_evidence_packets
        )

    @property
    def governance_approval_states(self) -> tuple[GovernanceReviewApprovalState, ...]:
        return tuple(
            evidence.approval_state
            for evidence in self.gate_decision.evidence.output_governance_evidence
            if evidence.approval_state is not None
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
        decision = _presentation_decision(
            gate_decision,
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


def _presentation_decision(
    gate_decision: RiskAuthorityGateDecision,
    *,
    limitations: tuple[str, ...],
    degradation_reasons: tuple[str, ...],
    withholding_reasons: tuple[str, ...],
    blocking_reasons: tuple[str, ...],
) -> PresentationSinkDecision:
    gate_disposition = _gate_disposition(gate_decision)
    boundary_disposition = _boundary_disposition(
        degradation_reasons=degradation_reasons,
        withholding_reasons=withholding_reasons,
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
            *withholding_reasons,
            *blocking_reasons,
        ),
        limitations=limitations,
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
