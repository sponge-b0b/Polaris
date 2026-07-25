from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from application.rag.contracts.rag_context import RagRetrievedContext, RagSource
from application.rag.contracts.rag_quality_models import (
    RagCorrectiveAction,
    RagReflectionScores,
)
from application.rag.contracts.rag_request import RagRequest
from core.storage.persistence.rag import JsonObject
from domain.authority import (
    SourceOfTruthCategory,
    risk_authority_contract_from_metadata,
)
from domain.decision_evidence import (
    ClaimEvidenceBinding,
    DecisionEvidencePacket,
    EvidenceConstraint,
    EvidenceLimitation,
    EvidenceReference,
    EvidenceReferenceKind,
    EvidenceRetentionRequirement,
    EvidenceUncertainty,
    MaterialClaim,
    ReconstructionReference,
    ReconstructionReferenceKind,
)


@dataclass(
    frozen=True,
    slots=True,
)
class RagResult:
    """
    Canonical platform-facing RAG result.
    """

    query_id: str
    request: RagRequest
    answer_text: str
    status: str
    route: str
    contexts: tuple[RagRetrievedContext, ...] = ()
    citations: tuple[RagSource, ...] = ()
    confidence_score: float | None = None
    grounding_score: float | None = None
    utility_score: float | None = None
    injection_detected: bool = False
    reflection_scores: RagReflectionScores | None = None
    corrective_actions: tuple[RagCorrectiveAction, ...] = ()
    error: str | None = None
    evidence_packet: DecisionEvidencePacket | None = None
    generated_at: datetime = field(
        default_factory=lambda: datetime.now(UTC),
    )
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        for field_name in (
            "query_id",
            "answer_text",
            "status",
            "route",
        ):
            _require_non_empty(
                getattr(
                    self,
                    field_name,
                ),
                field_name,
            )
        if (
            self.confidence_score is not None
            and not 0.0 <= self.confidence_score <= 1.0
        ):
            raise ValueError("confidence_score must be between 0.0 and 1.0.")
        for field_name in ("grounding_score", "utility_score"):
            value = getattr(self, field_name)
            if value is not None and not 0.0 <= value <= 1.0:
                raise ValueError(f"{field_name} must be between 0.0 and 1.0.")
        if self.status == "failed":
            _require_non_empty(
                self.error,
                "error",
            )

    @classmethod
    def answered(
        cls,
        *,
        request: RagRequest,
        answer_text: str,
        contexts: tuple[RagRetrievedContext, ...],
        confidence_score: float | None = None,
        metadata: JsonObject | None = None,
    ) -> RagResult:
        return cls(
            query_id=request.request_id,
            request=request,
            answer_text=answer_text,
            status="answered",
            route=request.route,
            contexts=contexts,
            citations=_unique_citations(
                contexts,
            ),
            confidence_score=confidence_score,
            metadata=metadata or {},
        )

    @classmethod
    def no_results(
        cls,
        *,
        request: RagRequest,
        answer_text: str = "No relevant curated RAG context was found.",
    ) -> RagResult:
        return cls(
            query_id=request.request_id,
            request=request,
            answer_text=answer_text,
            status="no_results",
            route=request.route,
        )

    @classmethod
    def failed(
        cls,
        *,
        request: RagRequest,
        error: str,
    ) -> RagResult:
        return cls(
            query_id=request.request_id,
            request=request,
            answer_text=f"RAG request failed: {error}",
            status="failed",
            route=request.route,
            error=error,
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "query_id": self.query_id,
            "request": self.request.to_dict(),
            "answer_text": self.answer_text,
            "status": self.status,
            "route": self.route,
            "contexts": [context.to_dict() for context in self.contexts],
            "citations": [citation.to_dict() for citation in self.citations],
            "confidence_score": self.confidence_score,
            "grounding_score": self.grounding_score,
            "utility_score": self.utility_score,
            "injection_detected": self.injection_detected,
            "reflection_scores": (
                None
                if self.reflection_scores is None
                else self.reflection_scores.to_dict()
            ),
            "corrective_actions": [action.value for action in self.corrective_actions],
            "error": self.error,
            "evidence_packet": _evidence_packet_to_payload(self.evidence_packet),
            "generated_at": self.generated_at.isoformat(),
            "metadata": deepcopy(
                dict(self.metadata),
            ),
        }

    @classmethod
    def from_dict(
        cls,
        payload: Mapping[str, Any],
    ) -> RagResult:
        request_payload = payload.get(
            "request",
        )
        if not isinstance(
            request_payload,
            Mapping,
        ):
            raise TypeError("request must be an object.")

        return cls(
            query_id=_required_str(
                payload,
                "query_id",
            ),
            request=RagRequest.from_dict(
                request_payload,
            ),
            answer_text=_required_str(
                payload,
                "answer_text",
            ),
            status=_required_str(
                payload,
                "status",
            ),
            route=_required_str(
                payload,
                "route",
            ),
            contexts=_contexts_from_payload(
                payload.get(
                    "contexts",
                    (),
                )
            ),
            citations=_citations_from_payload(
                payload.get(
                    "citations",
                    (),
                )
            ),
            confidence_score=_optional_float(
                payload.get(
                    "confidence_score",
                )
            ),
            grounding_score=_optional_float(payload.get("grounding_score")),
            utility_score=_optional_float(payload.get("utility_score")),
            injection_detected=_bool_from_payload(
                payload.get("injection_detected", False),
                "injection_detected",
            ),
            reflection_scores=_reflection_scores_from_payload(
                payload.get("reflection_scores")
            ),
            corrective_actions=_corrective_actions_from_payload(
                payload.get("corrective_actions", ())
            ),
            error=_optional_str(
                payload.get(
                    "error",
                )
            ),
            evidence_packet=_evidence_packet_from_payload(
                payload.get(
                    "evidence_packet",
                )
            ),
            generated_at=_datetime_from_payload(
                payload.get(
                    "generated_at",
                )
            ),
            metadata=_metadata_from_payload(
                payload.get(
                    "metadata",
                )
            ),
        )


def _evidence_packet_to_payload(
    packet: DecisionEvidencePacket | None,
) -> dict[str, Any] | None:
    if packet is None:
        return None
    return {
        "packet_id": packet.packet_id,
        "output_id": packet.output_id,
        "schema_version": packet.schema_version,
        "authority": packet.authority.to_metadata(),
        "claims": [_claim_to_payload(claim) for claim in packet.claims],
        "evidence": [_evidence_to_payload(evidence) for evidence in packet.evidence],
        "reconstruction_references": [
            _reconstruction_reference_to_payload(reference)
            for reference in packet.reconstruction_references
        ],
        "retention": {
            "retain_until": packet.retention.retain_until,
            "policy_id": packet.retention.policy_id,
            "legal_hold": packet.retention.legal_hold,
        },
        "constraints": [
            _constraint_to_payload(constraint) for constraint in packet.constraints
        ],
        "uncertainties": [
            _uncertainty_to_payload(uncertainty) for uncertainty in packet.uncertainties
        ],
        "limitations": [
            _limitation_to_payload(limitation) for limitation in packet.limitations
        ],
    }


def _evidence_packet_from_payload(
    value: object,
) -> DecisionEvidencePacket | None:
    if value is None:
        return None
    payload = _require_mapping(value)
    authority_payload = payload.get("authority")
    if not isinstance(authority_payload, Mapping):
        raise TypeError("evidence_packet.authority must be an object.")
    retention_payload = _require_mapping(payload.get("retention"))
    return DecisionEvidencePacket(
        packet_id=_required_str(payload, "packet_id"),
        output_id=_required_str(payload, "output_id"),
        authority=risk_authority_contract_from_metadata(authority_payload),
        claims=tuple(
            _claim_from_payload(item)
            for item in _sequence_payload(
                payload.get("claims"), "evidence_packet.claims"
            )
        ),
        evidence=tuple(
            _evidence_from_payload(item)
            for item in _sequence_payload(
                payload.get("evidence"), "evidence_packet.evidence"
            )
        ),
        reconstruction_references=tuple(
            _reconstruction_reference_from_payload(item)
            for item in _sequence_payload(
                payload.get("reconstruction_references"),
                "evidence_packet.reconstruction_references",
            )
        ),
        retention=EvidenceRetentionRequirement(
            retain_until=_required_str(retention_payload, "retain_until"),
            policy_id=_required_str(retention_payload, "policy_id"),
            legal_hold=_optional_bool(
                retention_payload.get("legal_hold", False), "legal_hold"
            ),
        ),
        constraints=tuple(
            _constraint_from_payload(item)
            for item in _sequence_payload(
                payload.get("constraints", ()),
                "evidence_packet.constraints",
            )
        ),
        uncertainties=tuple(
            _uncertainty_from_payload(item)
            for item in _sequence_payload(
                payload.get("uncertainties", ()),
                "evidence_packet.uncertainties",
            )
        ),
        limitations=tuple(
            _limitation_from_payload(item)
            for item in _sequence_payload(
                payload.get("limitations", ()),
                "evidence_packet.limitations",
            )
        ),
        schema_version=_optional_int(
            payload.get("schema_version", 1), "schema_version"
        ),
    )


def _claim_to_payload(claim: MaterialClaim) -> dict[str, Any]:
    return {
        "claim_id": claim.claim_id,
        "text": claim.text,
        "material": claim.material,
        "evidence": {
            "supporting_evidence_ids": list(claim.evidence.supporting_evidence_ids),
            "conflicting_evidence_ids": list(claim.evidence.conflicting_evidence_ids),
            "constraint_ids": list(claim.evidence.constraint_ids),
            "uncertainty_ids": list(claim.evidence.uncertainty_ids),
            "limitation_ids": list(claim.evidence.limitation_ids),
        },
    }


def _claim_from_payload(value: object) -> MaterialClaim:
    payload = _require_mapping(value)
    evidence_payload = _require_mapping(payload.get("evidence"))
    return MaterialClaim(
        claim_id=_required_str(payload, "claim_id"),
        text=_required_str(payload, "text"),
        material=_optional_bool(payload.get("material", True), "material"),
        evidence=ClaimEvidenceBinding(
            supporting_evidence_ids=_string_tuple(
                evidence_payload.get("supporting_evidence_ids", ()),
                "supporting_evidence_ids",
            ),
            conflicting_evidence_ids=_string_tuple(
                evidence_payload.get("conflicting_evidence_ids", ()),
                "conflicting_evidence_ids",
            ),
            constraint_ids=_string_tuple(
                evidence_payload.get("constraint_ids", ()),
                "constraint_ids",
            ),
            uncertainty_ids=_string_tuple(
                evidence_payload.get("uncertainty_ids", ()),
                "uncertainty_ids",
            ),
            limitation_ids=_string_tuple(
                evidence_payload.get("limitation_ids", ()),
                "limitation_ids",
            ),
        ),
    )


def _evidence_to_payload(evidence: EvidenceReference) -> dict[str, Any]:
    return {
        "evidence_id": evidence.evidence_id,
        "kind": evidence.kind.value,
        "reconstruction_reference_ids": list(evidence.reconstruction_reference_ids),
        "summary": evidence.summary,
        "source_of_truth": _optional_enum_value(evidence.source_of_truth),
    }


def _evidence_from_payload(value: object) -> EvidenceReference:
    payload = _require_mapping(value)
    return EvidenceReference(
        evidence_id=_required_str(payload, "evidence_id"),
        kind=EvidenceReferenceKind(_required_str(payload, "kind")),
        reconstruction_reference_ids=_string_tuple(
            payload.get("reconstruction_reference_ids", ()),
            "reconstruction_reference_ids",
        ),
        summary=_optional_str(payload.get("summary")) or "",
        source_of_truth=_optional_source_of_truth(payload.get("source_of_truth")),
    )


def _reconstruction_reference_to_payload(
    reference: ReconstructionReference,
) -> dict[str, Any]:
    return {
        "reference_id": reference.reference_id,
        "kind": reference.kind.value,
        "record_id": reference.record_id,
        "source_of_truth": _optional_enum_value(reference.source_of_truth),
        "snapshot_id": reference.snapshot_id,
        "content_digest": reference.content_digest,
    }


def _reconstruction_reference_from_payload(value: object) -> ReconstructionReference:
    payload = _require_mapping(value)
    return ReconstructionReference(
        reference_id=_required_str(payload, "reference_id"),
        kind=ReconstructionReferenceKind(_required_str(payload, "kind")),
        record_id=_required_str(payload, "record_id"),
        source_of_truth=_optional_source_of_truth(payload.get("source_of_truth")),
        snapshot_id=_optional_str(payload.get("snapshot_id")),
        content_digest=_optional_str(payload.get("content_digest")),
    )


def _constraint_to_payload(constraint: EvidenceConstraint) -> dict[str, Any]:
    return {
        "constraint_id": constraint.constraint_id,
        "summary": constraint.summary,
        "evidence_ids": list(constraint.evidence_ids),
    }


def _constraint_from_payload(value: object) -> EvidenceConstraint:
    payload = _require_mapping(value)
    return EvidenceConstraint(
        constraint_id=_required_str(payload, "constraint_id"),
        summary=_required_str(payload, "summary"),
        evidence_ids=_string_tuple(payload.get("evidence_ids", ()), "evidence_ids"),
    )


def _uncertainty_to_payload(uncertainty: EvidenceUncertainty) -> dict[str, Any]:
    return {
        "uncertainty_id": uncertainty.uncertainty_id,
        "summary": uncertainty.summary,
        "evidence_ids": list(uncertainty.evidence_ids),
    }


def _uncertainty_from_payload(value: object) -> EvidenceUncertainty:
    payload = _require_mapping(value)
    return EvidenceUncertainty(
        uncertainty_id=_required_str(payload, "uncertainty_id"),
        summary=_required_str(payload, "summary"),
        evidence_ids=_string_tuple(payload.get("evidence_ids", ()), "evidence_ids"),
    )


def _limitation_to_payload(limitation: EvidenceLimitation) -> dict[str, Any]:
    return {
        "limitation_id": limitation.limitation_id,
        "summary": limitation.summary,
        "evidence_ids": list(limitation.evidence_ids),
    }


def _limitation_from_payload(value: object) -> EvidenceLimitation:
    payload = _require_mapping(value)
    return EvidenceLimitation(
        limitation_id=_required_str(payload, "limitation_id"),
        summary=_required_str(payload, "summary"),
        evidence_ids=_string_tuple(payload.get("evidence_ids", ()), "evidence_ids"),
    )


def _sequence_payload(value: object, field_name: str) -> tuple[object, ...]:
    if value is None:
        return ()
    if not isinstance(value, Sequence) or isinstance(value, str | bytes | bytearray):
        raise TypeError(f"{field_name} must be a sequence.")
    return tuple(value)


def _string_tuple(value: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, str | bytes | bytearray):
        raise TypeError(f"{field_name} must be a sequence of strings.")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise TypeError(f"{field_name} must be a sequence of strings.")
        result.append(item)
    return tuple(result)


def _optional_bool(value: object, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{field_name} must be a boolean.")
    return value


def _optional_int(value: object, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{field_name} must be an integer.")
    return value


def _optional_source_of_truth(value: object) -> SourceOfTruthCategory | None:
    value = _optional_str(value)
    if value is None:
        return None
    return SourceOfTruthCategory(value)


def _optional_enum_value(value: SourceOfTruthCategory | None) -> str | None:
    if value is None:
        return None
    return value.value


def _unique_citations(
    contexts: tuple[RagRetrievedContext, ...],
) -> tuple[RagSource, ...]:
    seen: set[tuple[str, str, str | None]] = set()
    citations: list[RagSource] = []
    for context in contexts:
        key = (
            context.source.document_id,
            context.source.source_id,
            context.source.chunk_id,
        )
        if key in seen:
            continue
        seen.add(
            key,
        )
        citations.append(
            context.source,
        )
    return tuple(citations)


def _contexts_from_payload(
    value: object,
) -> tuple[RagRetrievedContext, ...]:
    if value is None:
        return ()
    if not isinstance(
        value,
        Sequence,
    ) or isinstance(
        value,
        str,
    ):
        raise TypeError("contexts must be a sequence of objects.")
    return tuple(
        RagRetrievedContext.from_dict(
            _require_mapping(
                item,
            )
        )
        for item in value
    )


def _citations_from_payload(
    value: object,
) -> tuple[RagSource, ...]:
    if value is None:
        return ()
    if not isinstance(
        value,
        Sequence,
    ) or isinstance(
        value,
        str,
    ):
        raise TypeError("citations must be a sequence of objects.")
    return tuple(
        RagSource.from_dict(
            _require_mapping(
                item,
            )
        )
        for item in value
    )


def _reflection_scores_from_payload(
    value: object,
) -> RagReflectionScores | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise TypeError("reflection_scores must be an object or None.")
    return RagReflectionScores.from_dict(value)


def _corrective_actions_from_payload(
    value: object,
) -> tuple[RagCorrectiveAction, ...]:
    if not isinstance(value, Sequence) or isinstance(value, str):
        raise TypeError("corrective_actions must be a sequence of strings.")
    result: list[RagCorrectiveAction] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise TypeError("corrective_actions must contain non-empty strings.")
        result.append(RagCorrectiveAction(item))
    return tuple(result)


def _bool_from_payload(
    value: object,
    field_name: str,
) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{field_name} must be a boolean.")
    return value


def _datetime_from_payload(
    value: object,
) -> datetime:
    if value is None:
        return datetime.now(UTC)
    if isinstance(
        value,
        datetime,
    ):
        return value
    if isinstance(
        value,
        str,
    ):
        return datetime.fromisoformat(
            value,
        )
    raise TypeError("generated_at must be an ISO datetime string or datetime object.")


def _metadata_from_payload(
    value: object,
) -> JsonObject:
    if value is None:
        return {}
    if not isinstance(
        value,
        Mapping,
    ):
        raise TypeError("metadata must be an object.")
    return dict(value)


def _optional_float(
    value: object,
) -> float | None:
    if value is None:
        return None
    if isinstance(
        value,
        int | float | str,
    ):
        return float(value)
    raise TypeError("optional float payload values must be numeric or strings.")


def _optional_str(
    value: object,
) -> str | None:
    if value is None:
        return None
    if not isinstance(
        value,
        str,
    ):
        raise TypeError("optional string payload values must be strings or None.")
    if not value.strip():
        return None
    return value


def _required_str(
    payload: Mapping[str, Any],
    key: str,
) -> str:
    value = payload.get(
        key,
    )
    if not isinstance(
        value,
        str,
    ):
        raise TypeError(f"{key} must be a string.")
    _require_non_empty(
        value,
        key,
    )
    return value


def _require_mapping(
    value: object,
) -> Mapping[str, Any]:
    if not isinstance(
        value,
        Mapping,
    ):
        raise TypeError("sequence values must be objects.")
    return value


def _require_non_empty(
    value: str | None,
    field_name: str,
) -> None:
    if value is None or not value.strip():
        raise ValueError(f"{field_name} cannot be empty.")
