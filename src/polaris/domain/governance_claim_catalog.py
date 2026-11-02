"""Complete Human Decision claim declarations owned by Governance."""

from __future__ import annotations

from dataclasses import dataclass

from polaris.domain.evidence.judgments import ClaimId
from polaris.domain.evidence.observations import EvidenceFactRef, is_evidence_fact_ref


# duplicate-code: Governance and Portfolio own separate complete claim declarations;
# sharing a claim class would couple distinct target histories.
# arid: disable
# jscpd:ignore-start
@dataclass(frozen=True, slots=True)
class GovernanceClaim:
    claim_id: ClaimId
    proposition: str
    surviving_support: frozenset[EvidenceFactRef]

    def __post_init__(self) -> None:
        if type(self.claim_id) is not ClaimId:
            raise TypeError("claim_id must be ClaimId")
        if not isinstance(self.proposition, str) or not self.proposition.strip():
            raise ValueError("claim proposition must be substantive")
        if type(self.surviving_support) is not frozenset or any(
            not is_evidence_fact_ref(item) for item in self.surviving_support
        ):
            raise TypeError("surviving_support must contain typed Evidence facts")


# jscpd:ignore-end
# arid: enable


@dataclass(frozen=True, slots=True)
class GovernanceClaimCatalog:
    """One explicitly complete target-owned catalog, including an empty one."""

    claims: tuple[GovernanceClaim, ...]

    def __post_init__(self) -> None:
        if type(self.claims) is not tuple or any(
            type(claim) is not GovernanceClaim for claim in self.claims
        ):
            raise TypeError("claims must be a tuple of GovernanceClaim")
        if len({claim.claim_id for claim in self.claims}) != len(self.claims):
            # duplicate-code: Governance catalog ordering and Portfolio catalog ordering
            # remain local to their distinct claim identities.
            # arid: disable
            raise ValueError("claim identities must be distinct")
        object.__setattr__(
            self,
            "claims",
            # arid: enable
            tuple(sorted(self.claims, key=lambda claim: str(claim.claim_id.value))),
        )

    @property
    def claim_ids(self) -> frozenset[ClaimId]:
        return frozenset(claim.claim_id for claim in self.claims)

    def validate_successor(
        self, successor: GovernanceClaimCatalog, historical_ids: frozenset[ClaimId]
    ) -> None:
        if type(successor) is not GovernanceClaimCatalog:
            raise TypeError("successor must be a complete GovernanceClaimCatalog")
        old = {claim.claim_id: claim for claim in self.claims}
        new = {claim.claim_id: claim for claim in successor.claims}
        if any(
            claim_id in old and old[claim_id].proposition != claim.proposition
            for claim_id, claim in new.items()
        ):
            raise ValueError("material proposition change requires a fresh ClaimId")
        if (set(new) - set(old)) & historical_ids:
            raise ValueError("retired ClaimId cannot be reused as a new proposition")
