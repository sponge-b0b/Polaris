"""Typed PostgreSQL boundary codec for Decision relationship persistence."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import datetime

from sqlalchemy.engine import RowMapping

from polaris.application.decisions.contracts import (
    ContinuityDetermination,
    ContinuityDeterminationKind,
)
from polaris.application.decisions.relationships import (
    DecisionRelationshipCommandKind,
    DecisionRelationshipReceipt,
    DecisionRelationshipResult,
    DecisionRelationshipSemanticRequest,
    OmittedRenewalLineagePayload,
    RelationshipCorrectionPayload,
    RelationshipCorrectionSetMemberPayload,
    RelationshipCorrectionSetPayload,
    RenewalPayload,
    RenewalPredecessor,
    SupersessionPayload,
    SupersessionTarget,
)
from polaris.domain.actors import KnownActorAttribution
from polaris.domain.decisions import (
    DecisionRelationshipBasis,
    DecisionRelationshipCorrected,
    DecisionRelationshipCorrectionBasis,
    DecisionRelationshipCorrectionEffect,
    DecisionRelationshipFact,
    DecisionRelationshipFactId,
    DecisionRelationshipFactMetadata,
    DecisionRelationshipHistoryFact,
    DecisionRelationshipType,
    DecisionScope,
    DecisionScopeCompleteness,
    DecisionSubject,
    DecisionVersion,
    InvestmentDecisionId,
    OperationId,
    PortfolioId,
    RenewedFromRelationshipBasis,
    SupersedesRelationshipBasis,
)

from .codec import (
    actor_columns,
    actor_from_columns,
    technical_from_payload,
    technical_payload,
    trigger_columns,
    trigger_from_columns,
)

type JsonObject = dict[str, object]


def relationship_request_payload(
    request: DecisionRelationshipSemanticRequest,
) -> JsonObject:
    return {
        "kind": request.kind.value,
        "actor_attribution": _actor_payload(request.actor_attribution),
        "trigger": {
            "kind": request.trigger.kind.value,
            "reference": request.trigger.reference,
        },
        "effective_at": request.effective_at.isoformat(),
        "expected_versions": [
            {"decision_id": str(identity.value), "version": version.value}
            for identity, version in sorted(
                request.expected_versions, key=lambda item: str(item[0].value)
            )
        ],
        "payload": _request_body(request.payload),
    }


def relationship_result_payload(result: DecisionRelationshipResult) -> JsonObject:
    return {
        "relationship_fact_ids": [
            str(identity.value) for identity in result.relationship_fact_ids
        ],
        "versioned_decision_ids": [
            str(identity.value)
            for identity in sorted(
                result.versioned_decision_ids, key=lambda item: str(item.value)
            )
        ],
        "new_decision_id": (
            str(result.new_decision_id.value)
            if result.new_decision_id is not None
            else None
        ),
        "need_id": str(result.need_id.value) if result.need_id is not None else None,
    }


def relationship_receipt_from_row(row: RowMapping) -> DecisionRelationshipReceipt:
    return DecisionRelationshipReceipt(
        operation_id=OperationId(_uuid(row["operation_id"], "operation_id")),
        request=relationship_request_from_payload(row["request_payload"]),
        result=relationship_result_from_payload(row["result_payload"]),
    )


def relationship_request_from_payload(
    value: object,
) -> DecisionRelationshipSemanticRequest:
    payload = _mapping(value, "relationship request")
    actor = _actor_from_payload(payload.get("actor_attribution"))
    trigger = _mapping(payload.get("trigger"), "trigger")
    expected = frozenset(
        (
            InvestmentDecisionId(
                _uuid(item.get("decision_id"), "expected decision_id")
            ),
            DecisionVersion(_integer(item.get("version"), "expected version")),
        )
        for raw_item in _object_list(
            payload.get("expected_versions"), "expected_versions"
        )
        for item in (_mapping(raw_item, "expected version"),)
    )
    kind = DecisionRelationshipCommandKind(
        _string(payload.get("kind"), "relationship command kind")
    )
    return DecisionRelationshipSemanticRequest(
        kind=kind,
        actor_attribution=actor,
        trigger=trigger_from_columns(
            {
                "trigger_kind": _string(trigger.get("kind"), "trigger kind"),
                "trigger_reference": _string(
                    trigger.get("reference"), "trigger reference"
                ),
            }
        ),
        effective_at=_datetime(payload.get("effective_at"), "effective_at"),
        expected_versions=expected,
        payload=_request_body_from(kind, payload.get("payload")),
    )


def relationship_result_from_payload(value: object) -> DecisionRelationshipResult:
    payload = _mapping(value, "relationship result")
    raw_new_decision_id = payload.get("new_decision_id")
    raw_need_id = payload.get("need_id")
    from polaris.domain.decisions import DecisionNeedId

    return DecisionRelationshipResult(
        relationship_fact_ids=tuple(
            DecisionRelationshipFactId(_uuid(item, "relationship_fact_id"))
            for item in _object_list(
                payload.get("relationship_fact_ids"), "relationship_fact_ids"
            )
        ),
        versioned_decision_ids=frozenset(
            InvestmentDecisionId(_uuid(item, "versioned_decision_id"))
            for item in _object_list(
                payload.get("versioned_decision_ids"), "versioned_decision_ids"
            )
        ),
        new_decision_id=(
            InvestmentDecisionId(_uuid(raw_new_decision_id, "new_decision_id"))
            if raw_new_decision_id is not None
            else None
        ),
        need_id=(
            DecisionNeedId(_uuid(raw_need_id, "need_id"))
            if raw_need_id is not None
            else None
        ),
    )


def relationship_request_fingerprint(
    request: DecisionRelationshipSemanticRequest,
) -> str:
    encoded = json.dumps(
        relationship_request_payload(request), sort_keys=True, separators=(",", ":")
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def relationship_fact_values(
    fact: DecisionRelationshipHistoryFact,
    *,
    group: tuple[
        InvestmentDecisionId,
        DecisionRelationshipType,
        InvestmentDecisionId,
    ],
    admission_evidence: JsonObject | None,
) -> dict[str, object]:
    metadata = fact.metadata
    common = {
        "relationship_fact_id": metadata.relationship_fact_id.value,
        "source_decision_id": group[0].value,
        "relationship_type": group[1].value,
        "target_decision_id": group[2].value,
        "operation_id": metadata.operation_id.value,
        **actor_columns(metadata.actor_attribution),
        **trigger_columns(metadata.trigger),
        "technical_provenance": technical_payload(metadata.technical_provenance),
        "recorded_at": metadata.recorded_at,
        "admission_evidence": admission_evidence,
    }
    if isinstance(fact, DecisionRelationshipFact):
        return {
            **common,
            "fact_kind": "base",
            "target_relationship_fact_id": None,
            "effective_at": fact.relationship_effective_at,
            "correction_effect": None,
            "positive_claim_effective_at": None,
            "positive_basis": _basis_payload(fact.relationship_basis),
            "correction_basis": None,
        }
    return {
        **common,
        "fact_kind": "correction",
        "target_relationship_fact_id": fact.target_relationship_fact_id.value,
        "effective_at": fact.correction_effective_at,
        "correction_effect": fact.effect.value,
        "positive_claim_effective_at": fact.replacement_relationship_effective_at,
        "positive_basis": (
            _basis_payload(fact.replacement_relationship_basis)
            if fact.replacement_relationship_basis is not None
            else None
        ),
        "correction_basis": _correction_basis_payload(fact.correction_basis),
    }


def relationship_fact_from_row(row: RowMapping) -> DecisionRelationshipHistoryFact:
    metadata = DecisionRelationshipFactMetadata(
        relationship_fact_id=DecisionRelationshipFactId(
            _uuid(row["relationship_fact_id"], "relationship_fact_id")
        ),
        operation_id=OperationId(_uuid(row["operation_id"], "operation_id")),
        actor_attribution=actor_from_columns(row),
        trigger=trigger_from_columns(row),
        technical_provenance=technical_from_payload(row["technical_provenance"]),
        recorded_at=_datetime(row["recorded_at"], "recorded_at"),
    )
    relationship_type = DecisionRelationshipType(
        _string(row["relationship_type"], "relationship_type")
    )
    if row["fact_kind"] == "base":
        return DecisionRelationshipFact(
            metadata=metadata,
            source_decision_id=InvestmentDecisionId(
                _uuid(row["source_decision_id"], "source_decision_id")
            ),
            target_decision_id=InvestmentDecisionId(
                _uuid(row["target_decision_id"], "target_decision_id")
            ),
            relationship_type=relationship_type,
            relationship_effective_at=_datetime(row["effective_at"], "effective_at"),
            relationship_basis=_basis_from_payload(
                relationship_type, row["positive_basis"]
            ),
        )
    raw_replacement_at = row["positive_claim_effective_at"]
    return DecisionRelationshipCorrected(
        metadata=metadata,
        target_relationship_fact_id=DecisionRelationshipFactId(
            _uuid(row["target_relationship_fact_id"], "target_relationship_fact_id")
        ),
        effect=DecisionRelationshipCorrectionEffect(
            _string(row["correction_effect"], "correction_effect")
        ),
        correction_effective_at=_datetime(row["effective_at"], "effective_at"),
        correction_basis=_correction_basis_from_payload(row["correction_basis"]),
        replacement_relationship_effective_at=(
            _datetime(raw_replacement_at, "positive_claim_effective_at")
            if raw_replacement_at is not None
            else None
        ),
        replacement_relationship_basis=(
            _basis_from_payload(relationship_type, row["positive_basis"])
            if row["positive_basis"] is not None
            else None
        ),
    )


def _request_body(value: object) -> JsonObject:
    if isinstance(value, RenewalPayload):
        return {
            "need_statement": value.need_statement,
            "subject": value.subject.statement,
            "scope": _scope_payload(value.scope),
            "predecessors": [_predecessor_payload(item) for item in value.predecessors],
            "continuity": _continuity_payload(value.continuity),
        }
    if isinstance(value, OmittedRenewalLineagePayload):
        return {
            "source_decision_id": str(value.source_decision_id.value),
            "predecessors": [_predecessor_payload(item) for item in value.predecessors],
        }
    if isinstance(value, SupersessionPayload):
        return {
            "source_decision_id": str(value.source_decision_id.value),
            "targets": [
                {
                    "decision_id": str(item.decision_id.value),
                    "basis": _basis_payload(item.basis),
                    "effective_at": item.effective_at.isoformat(),
                }
                for item in value.targets
            ],
        }
    if isinstance(value, RelationshipCorrectionPayload):
        return _correction_payload(
            value.target_relationship_fact_id,
            value.effect,
            value.correction_effective_at,
            value.correction_basis,
            value.replacement_relationship_effective_at,
            value.replacement_relationship_basis,
        )
    if isinstance(value, RelationshipCorrectionSetPayload):
        return {
            "members": [
                _correction_payload(
                    item.target,
                    item.effect,
                    item.correction_effective_at,
                    item.correction_basis,
                    item.replacement_relationship_effective_at,
                    item.replacement_relationship_basis,
                )
                for item in value.members
            ]
        }
    raise ValueError("unsupported Decision relationship request payload")


def _request_body_from(
    kind: DecisionRelationshipCommandKind, value: object
) -> (
    RenewalPayload
    | OmittedRenewalLineagePayload
    | SupersessionPayload
    | RelationshipCorrectionPayload
    | RelationshipCorrectionSetPayload
):
    payload = _mapping(value, "relationship request payload")
    if kind is DecisionRelationshipCommandKind.RENEW:
        return RenewalPayload(
            need_statement=_string(payload.get("need_statement"), "need_statement"),
            subject=DecisionSubject(_string(payload.get("subject"), "subject")),
            scope=_scope_from_payload(payload.get("scope")),
            predecessors=tuple(
                _predecessor_from_payload(item)
                for item in _object_list(payload.get("predecessors"), "predecessors")
            ),
            continuity=_continuity_from_payload(payload.get("continuity")),
        )
    if kind is DecisionRelationshipCommandKind.ATTACH_OMITTED_RENEWAL_LINEAGE:
        return OmittedRenewalLineagePayload(
            source_decision_id=InvestmentDecisionId(
                _uuid(payload.get("source_decision_id"), "source_decision_id")
            ),
            predecessors=tuple(
                _predecessor_from_payload(item)
                for item in _object_list(payload.get("predecessors"), "predecessors")
            ),
        )
    if kind is DecisionRelationshipCommandKind.ESTABLISH_SUPERSESSION:
        return SupersessionPayload(
            source_decision_id=InvestmentDecisionId(
                _uuid(payload.get("source_decision_id"), "source_decision_id")
            ),
            targets=tuple(
                _supersession_target_from_payload(item)
                for item in _object_list(payload.get("targets"), "targets")
            ),
        )
    if "members" in payload:
        return RelationshipCorrectionSetPayload(
            tuple(
                _correction_member_from_payload(item)
                for item in _object_list(payload.get("members"), "members")
            )
        )
    correction = _correction_values(payload)
    target = correction[0]
    if not isinstance(target, DecisionRelationshipFactId):
        raise ValueError("single relationship correction target must be a fact ID")
    return RelationshipCorrectionPayload(target, *correction[1:])


def _predecessor_payload(value: RenewalPredecessor) -> JsonObject:
    return {
        "decision_id": str(value.decision_id.value),
        "basis": _basis_payload(value.basis),
    }


def _predecessor_from_payload(value: object) -> RenewalPredecessor:
    payload = _mapping(value, "renewal predecessor")
    return RenewalPredecessor(
        InvestmentDecisionId(_uuid(payload.get("decision_id"), "decision_id")),
        _renewed_basis_from_payload(payload.get("basis")),
    )


def _supersession_target_from_payload(value: object) -> SupersessionTarget:
    payload = _mapping(value, "supersession target")
    return SupersessionTarget(
        InvestmentDecisionId(_uuid(payload.get("decision_id"), "decision_id")),
        _supersedes_basis_from_payload(payload.get("basis")),
        _datetime(payload.get("effective_at"), "effective_at"),
    )


def _correction_payload(
    target: DecisionRelationshipFactId | int,
    effect: DecisionRelationshipCorrectionEffect,
    correction_effective_at: datetime,
    correction_basis: DecisionRelationshipCorrectionBasis,
    replacement_effective_at: datetime | None,
    replacement_basis: DecisionRelationshipBasis | None,
) -> JsonObject:
    return {
        "target": (
            {"fact_id": str(target.value)}
            if isinstance(target, DecisionRelationshipFactId)
            else {"member_index": target}
        ),
        "effect": effect.value,
        "correction_effective_at": correction_effective_at.isoformat(),
        "correction_basis": _correction_basis_payload(correction_basis),
        "replacement_effective_at": (
            replacement_effective_at.isoformat()
            if replacement_effective_at is not None
            else None
        ),
        "replacement_basis": (
            _basis_payload(replacement_basis) if replacement_basis is not None else None
        ),
    }


def _correction_values(
    payload: Mapping[str, object],
) -> tuple[
    DecisionRelationshipFactId | int,
    DecisionRelationshipCorrectionEffect,
    datetime,
    DecisionRelationshipCorrectionBasis,
    datetime | None,
    DecisionRelationshipBasis | None,
]:
    target_payload = _mapping(payload.get("target"), "correction target")
    if target_payload.get("fact_id") is not None:
        target: DecisionRelationshipFactId | int = DecisionRelationshipFactId(
            _uuid(target_payload.get("fact_id"), "target fact_id")
        )
    else:
        target = _integer(target_payload.get("member_index"), "target member_index")
    raw_replacement_at = payload.get("replacement_effective_at")
    raw_replacement_basis = payload.get("replacement_basis")
    return (
        target,
        DecisionRelationshipCorrectionEffect(
            _string(payload.get("effect"), "correction effect")
        ),
        _datetime(payload.get("correction_effective_at"), "correction_effective_at"),
        _correction_basis_from_payload(payload.get("correction_basis")),
        (
            _datetime(raw_replacement_at, "replacement_effective_at")
            if raw_replacement_at is not None
            else None
        ),
        (
            _untyped_basis_from_payload(raw_replacement_basis)
            if raw_replacement_basis is not None
            else None
        ),
    )


def _correction_member_from_payload(
    value: object,
) -> RelationshipCorrectionSetMemberPayload:
    payload = _mapping(value, "correction set member")
    return RelationshipCorrectionSetMemberPayload(*_correction_values(payload))


def _basis_payload(value: DecisionRelationshipBasis) -> JsonObject:
    kind = (
        DecisionRelationshipType.RENEWED_FROM
        if isinstance(value, RenewedFromRelationshipBasis)
        else DecisionRelationshipType.SUPERSEDES
    )
    return {"kind": kind.value, "references": sorted(value.references)}


def _basis_from_payload(
    relationship_type: DecisionRelationshipType, value: object
) -> DecisionRelationshipBasis:
    payload = _mapping(value, "relationship basis")
    kind = DecisionRelationshipType(_string(payload.get("kind"), "basis kind"))
    if kind is not relationship_type:
        raise ValueError("relationship basis kind does not match relationship type")
    return _untyped_basis_from_payload(payload)


def _untyped_basis_from_payload(value: object) -> DecisionRelationshipBasis:
    payload = _mapping(value, "relationship basis")
    references = tuple(
        _string(item, "basis reference")
        for item in _object_list(payload.get("references"), "basis references")
    )
    kind = DecisionRelationshipType(_string(payload.get("kind"), "basis kind"))
    if kind is DecisionRelationshipType.RENEWED_FROM:
        return RenewedFromRelationshipBasis(references)
    return SupersedesRelationshipBasis(references)


def _renewed_basis_from_payload(value: object) -> RenewedFromRelationshipBasis:
    basis = _untyped_basis_from_payload(value)
    if not isinstance(basis, RenewedFromRelationshipBasis):
        raise ValueError("renewal predecessor requires renewed-from basis")
    return basis


def _supersedes_basis_from_payload(value: object) -> SupersedesRelationshipBasis:
    basis = _untyped_basis_from_payload(value)
    if not isinstance(basis, SupersedesRelationshipBasis):
        raise ValueError("supersession target requires supersedes basis")
    return basis


def _correction_basis_payload(
    value: DecisionRelationshipCorrectionBasis,
) -> JsonObject:
    return {"references": sorted(value.references)}


def _correction_basis_from_payload(
    value: object,
) -> DecisionRelationshipCorrectionBasis:
    payload = _mapping(value, "correction basis")
    return DecisionRelationshipCorrectionBasis(
        _string(item, "correction basis reference")
        for item in _object_list(payload.get("references"), "correction references")
    )


def _scope_payload(value: DecisionScope) -> JsonObject:
    return {
        "portfolio_ids": [
            str(identity.value)
            for identity in sorted(
                value.portfolio_ids, key=lambda item: str(item.value)
            )
        ],
        "completeness": value.completeness.value,
    }


def _scope_from_payload(value: object) -> DecisionScope:
    payload = _mapping(value, "scope")
    return DecisionScope(
        (
            PortfolioId(_uuid(item, "portfolio_id"))
            for item in _object_list(payload.get("portfolio_ids"), "portfolio_ids")
        ),
        DecisionScopeCompleteness(
            _string(payload.get("completeness"), "scope completeness")
        ),
    )


def _continuity_payload(value: ContinuityDetermination | None) -> JsonObject | None:
    if value is None:
        return None
    return {
        "kind": value.kind.value,
        "decision_id": (
            str(value.decision_id.value) if value.decision_id is not None else None
        ),
        "rationale": value.rationale,
    }


def _continuity_from_payload(value: object) -> ContinuityDetermination | None:
    if value is None:
        return None
    payload = _mapping(value, "continuity")
    raw_decision_id = payload.get("decision_id")
    return ContinuityDetermination(
        kind=ContinuityDeterminationKind(
            _string(payload.get("kind"), "continuity kind")
        ),
        decision_id=(
            InvestmentDecisionId(_uuid(raw_decision_id, "continuity decision_id"))
            if raw_decision_id is not None
            else None
        ),
        rationale=_optional_string(payload.get("rationale")),
    )


def _actor_payload(value: KnownActorAttribution) -> JsonObject:
    return {"kind": "known", "actor_id": str(value.actor_id.value)}


def _actor_from_payload(value: object) -> KnownActorAttribution:
    payload = _mapping(value, "actor attribution")
    from polaris.domain.actors import ActorId

    if _string(payload.get("kind"), "actor attribution kind") != "known":
        raise ValueError("relationship request requires known Actor Attribution")
    return KnownActorAttribution(ActorId(_uuid(payload.get("actor_id"), "actor_id")))


def _mapping(value: object, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} must be a JSON object")
    return value


def _object_list(value: object, field: str) -> list[object]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a JSON list")
    return value


def _uuid(value: object, field: str):
    from uuid import UUID

    if type(value) is UUID:
        return value
    if isinstance(value, UUID):
        return UUID(str(value))
    if isinstance(value, str):
        return UUID(value)
    raise ValueError(f"{field} must be a UUID")


def _datetime(value: object, field: str) -> datetime:
    if isinstance(value, datetime):
        result = value
    elif isinstance(value, str):
        result = datetime.fromisoformat(value)
    else:
        raise ValueError(f"{field} must be a datetime")
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    return result


def _integer(value: object, field: str) -> int:
    if type(value) is not int:
        raise ValueError(f"{field} must be an integer")
    return value


def _string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a non-empty string")
    return value


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    return _string(value, "optional string")
