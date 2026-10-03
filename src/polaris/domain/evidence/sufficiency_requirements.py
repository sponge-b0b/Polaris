from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .bindings import EvidenceRole


class InvalidEvidenceSufficiencyPredicate(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class MinimumEligibleEvidence:
    """Closed R3 readiness predicate over distinct eligible observations."""

    minimum_distinct_observations: int
    qualifying_roles: frozenset[EvidenceRole]

    def __post_init__(self) -> None:
        from .bindings import EvidenceRole

        readiness_roles = frozenset(
            {
                EvidenceRole.SUPPORTING,
                EvidenceRole.CONFLICTING,
                EvidenceRole.CONSTRAINING,
                EvidenceRole.QUALIFYING,
            }
        )
        if (
            not isinstance(self.minimum_distinct_observations, int)
            or isinstance(self.minimum_distinct_observations, bool)
            or self.minimum_distinct_observations <= 0
        ):
            raise InvalidEvidenceSufficiencyPredicate(
                "minimum_distinct_observations must be a positive integer"
            )
        if not isinstance(self.qualifying_roles, frozenset):
            raise TypeError("qualifying_roles must be a frozenset of EvidenceRole")
        if not self.qualifying_roles:
            raise InvalidEvidenceSufficiencyPredicate(
                "qualifying_roles must not be empty"
            )
        if any(type(role) is not EvidenceRole for role in self.qualifying_roles):
            raise TypeError("qualifying_roles must contain only EvidenceRole values")
        if not self.qualifying_roles <= readiness_roles:
            raise InvalidEvidenceSufficiencyPredicate(
                "qualifying_roles may contain only readiness-gating Evidence roles"
            )


__all__ = [
    "InvalidEvidenceSufficiencyPredicate",
    "MinimumEligibleEvidence",
]
