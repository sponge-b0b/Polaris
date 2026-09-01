from __future__ import annotations

from dataclasses import dataclass, field

from application.presentation.sink_decision import PresentationSinkDecision


@dataclass(frozen=True, slots=True)
class GovernedPresentationProjection:
    """Externally safe projection of one canonical presentation decision."""

    disposition: str
    may_present: bool
    authority_metadata: dict[str, object]
    gate_failure_mode: str
    risk_tier: str | None
    gate_profile: str | None
    limitations: tuple[str, ...]
    provenance_record_ids: tuple[str, ...]
    decision_evidence_packet_ids: tuple[str, ...]
    governance_approval_states: tuple[str, ...]

    @classmethod
    def from_decision(
        cls,
        decision: PresentationSinkDecision,
    ) -> GovernedPresentationProjection:
        return cls(
            disposition=decision.disposition.value,
            may_present=decision.may_present,
            authority_metadata=(
                {}
                if decision.authority_metadata is None
                else dict(decision.authority_metadata)
            ),
            gate_failure_mode=decision.gate_failure_mode.value,
            risk_tier=(
                None if decision.risk_tier is None else decision.risk_tier.value
            ),
            gate_profile=(
                None if decision.gate_profile is None else decision.gate_profile.value
            ),
            limitations=decision.limitations,
            provenance_record_ids=decision.provenance_record_ids,
            decision_evidence_packet_ids=decision.decision_evidence_packet_ids,
            governance_approval_states=tuple(
                state.value for state in decision.governance_approval_states
            ),
        )


@dataclass(frozen=True, slots=True)
class GovernedPresentationResult[T]:
    """Application-owned payload bound to canonical presentation governance."""

    payload: T | None
    decision: PresentationSinkDecision
    projection: GovernedPresentationProjection = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "projection",
            GovernedPresentationProjection.from_decision(self.decision),
        )

    def require_payload(self) -> T:
        """Return the application-owned payload when one was emitted."""

        payload = self.payload
        if payload is None:
            raise ValueError("governed presentation result contains no payload.")
        return payload

    def require_presentable_payload(self) -> T:
        """Return payload only when the canonical decision permits presentation."""

        if not self.decision.may_present:
            raise ValueError(
                "governed presentation result is not eligible for presentation."
            )
        return self.require_payload()


__all__ = [
    "GovernedPresentationProjection",
    "GovernedPresentationResult",
]
