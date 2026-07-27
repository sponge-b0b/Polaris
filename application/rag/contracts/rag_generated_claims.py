from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, cast

from core.storage.persistence.rag import JsonObject
from domain.decision_evidence import ClaimMaterialityTier


@dataclass(frozen=True, slots=True)
class RagGeneratedClaim:
    """Typed claim emitted by a RAG answer-generation provider.

    This contract is the provenance-bearing source of truth for material RAG
    answer claims. Rendered answer text remains presentation output; packet
    assembly consumes these typed claims instead of inferring support from the
    rendered string.
    """

    claim_id: str
    text: str
    citation_ids: tuple[str, ...] = ()
    supporting_citation_ids: tuple[str, ...] = ()
    materiality: ClaimMaterialityTier = ClaimMaterialityTier.READINESS_GATING
    sanitized_context_ids: tuple[str, ...] = ()
    rejected_context_ids: tuple[str, ...] = ()
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "claim_id",
            _clean_required_str(self.claim_id, "claim_id"),
        )
        object.__setattr__(self, "text", _clean_required_str(self.text, "text"))
        object.__setattr__(
            self,
            "citation_ids",
            _clean_string_tuple(self.citation_ids, "citation_ids"),
        )
        object.__setattr__(
            self,
            "supporting_citation_ids",
            _clean_string_tuple(
                self.supporting_citation_ids,
                "supporting_citation_ids",
            ),
        )
        object.__setattr__(
            self,
            "sanitized_context_ids",
            _clean_string_tuple(self.sanitized_context_ids, "sanitized_context_ids"),
        )
        object.__setattr__(
            self,
            "rejected_context_ids",
            _clean_string_tuple(self.rejected_context_ids, "rejected_context_ids"),
        )
        object.__setattr__(
            self,
            "materiality",
            _claim_materiality_from_payload(self.materiality),
        )
        if not isinstance(self.metadata, Mapping):
            raise TypeError("metadata must be an object.")
        object.__setattr__(self, "metadata", deepcopy(dict(self.metadata)))

    @property
    def gates_readiness(self) -> bool:
        """Whether the claim requires supporting evidence for readiness."""

        return self.materiality is ClaimMaterialityTier.READINESS_GATING

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "text": self.text,
            "citation_ids": list(self.citation_ids),
            "supporting_citation_ids": list(self.supporting_citation_ids),
            "materiality": self.materiality.value,
            "sanitized_context_ids": list(self.sanitized_context_ids),
            "rejected_context_ids": list(self.rejected_context_ids),
            "metadata": deepcopy(dict(self.metadata)),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> RagGeneratedClaim:
        return cls(
            claim_id=_required_payload_str(payload, "claim_id"),
            text=_required_payload_str(payload, "text"),
            citation_ids=_string_tuple_from_payload(
                payload.get("citation_ids", ()),
                "citation_ids",
            ),
            supporting_citation_ids=_string_tuple_from_payload(
                payload.get("supporting_citation_ids", ()),
                "supporting_citation_ids",
            ),
            materiality=_claim_materiality_from_payload(
                payload.get("materiality", ClaimMaterialityTier.READINESS_GATING.value)
            ),
            sanitized_context_ids=_string_tuple_from_payload(
                payload.get("sanitized_context_ids", ()),
                "sanitized_context_ids",
            ),
            rejected_context_ids=_string_tuple_from_payload(
                payload.get("rejected_context_ids", ()),
                "rejected_context_ids",
            ),
            metadata=cast(
                JsonObject,
                deepcopy(dict(_mapping_payload(payload.get("metadata", {})))),
            ),
        )


def generated_claims_from_payload(value: object) -> tuple[RagGeneratedClaim, ...]:
    if value is None:
        return ()
    if not isinstance(value, Sequence) or isinstance(value, str | bytes | bytearray):
        raise TypeError("generated_claims must be a sequence.")
    claims: list[RagGeneratedClaim] = []
    for item in value:
        if isinstance(item, RagGeneratedClaim):
            claims.append(item)
            continue
        if not isinstance(item, Mapping):
            raise TypeError("generated_claims items must be objects.")
        claims.append(RagGeneratedClaim.from_dict(cast(Mapping[str, Any], item)))
    return tuple(claims)


def _clean_required_str(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string.")
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{field_name} cannot be empty.")
    return stripped


def _clean_string_tuple(value: object, field_name: str) -> tuple[str, ...]:
    values = _string_tuple_from_payload(value, field_name)
    return tuple(dict.fromkeys(values))


def _string_tuple_from_payload(value: object, field_name: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        stripped = value.strip()
        return (stripped,) if stripped else ()
    if not isinstance(value, Sequence) or isinstance(value, bytes | bytearray):
        raise TypeError(f"{field_name} must be a sequence of strings.")
    items: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise TypeError(f"{field_name} must contain only strings.")
        stripped = item.strip()
        if stripped:
            items.append(stripped)
    return tuple(items)


def _claim_materiality_from_payload(value: object) -> ClaimMaterialityTier:
    if isinstance(value, ClaimMaterialityTier):
        return value
    if isinstance(value, str) and value.strip():
        return ClaimMaterialityTier(value.strip())
    raise TypeError("materiality must be a ClaimMaterialityTier value.")


def _mapping_payload(value: object) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError("metadata must be an object.")
    return cast(Mapping[str, Any], value)


def _required_payload_str(payload: Mapping[str, Any], field_name: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} cannot be empty.")
    return value


__all__ = [
    "RagGeneratedClaim",
    "generated_claims_from_payload",
]
