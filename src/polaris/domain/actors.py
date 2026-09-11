from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ActorId:
    """Opaque durable identity for a domain-recognized actor."""

    value: UUID

    def __post_init__(self) -> None:
        if type(self.value) is not UUID:
            raise TypeError("ActorId.value must be UUID")
        if self.value.version != 4:
            raise ValueError("ActorId.value must be UUIDv4")


@dataclass(frozen=True, slots=True)
class KnownActorAttribution:
    actor_id: ActorId

    def __post_init__(self) -> None:
        if type(self.actor_id) is not ActorId:
            raise TypeError("actor_id must be ActorId")


@dataclass(frozen=True, slots=True)
class UnknownActorAttribution:
    """Historical attribution whose actor cannot currently be established."""


@dataclass(frozen=True, slots=True)
class ContestedActorAttribution:
    candidate_actor_ids: frozenset[ActorId]

    def __post_init__(self) -> None:
        if type(self.candidate_actor_ids) is not frozenset:
            raise TypeError("candidate_actor_ids must be frozenset[ActorId]")
        if not self.candidate_actor_ids:
            raise ValueError(
                "contested attribution requires at least one candidate ActorId"
            )
        if any(type(actor_id) is not ActorId for actor_id in self.candidate_actor_ids):
            raise TypeError("candidate_actor_ids must contain only ActorId values")


ActorAttribution = (
    KnownActorAttribution | UnknownActorAttribution | ContestedActorAttribution
)
