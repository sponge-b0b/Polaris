"""Typed persistence codec for the PostgreSQL Decision foundation."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import datetime
from uuid import UUID

from sqlalchemy.engine import RowMapping

from polaris.application.decisions.contracts import (
    ContinuityDetermination,
    ContinuityDeterminationKind,
    ExpectedDecisionVersion,
    InitiationReceipt,
    InitiationResult,
    InitiationResultKind,
    InitiationSemanticRequest,
)
from polaris.domain.actors import (
    ActorAttribution,
    ActorId,
    ContestedActorAttribution,
    KnownActorAttribution,
    UnknownActorAttribution,
)
from polaris.domain.decisions import (
    DecisionInitiated,
    DecisionInitiationContinuity,
    DecisionInitiationDetermination,
    DecisionLifecycleFactId,
    DecisionLifecycleFactMetadata,
    DecisionLifecycleSequence,
    DecisionNeed,
    DecisionNeedId,
    DecisionScope,
    DecisionScopeCompleteness,
    DecisionSubject,
    DecisionVersion,
    InvestmentDecisionId,
    OperationId,
    PortfolioId,
    TechnicalProvenance,
    TechnicalReference,
    TechnicalReferenceKind,
    TriggerKind,
    TriggerProvenance,
)

type JsonObject = dict[str, object]
type RowLike = Mapping[str, object] | RowMapping


def actor_columns(actor: ActorAttribution) -> dict[str, object]:
    if isinstance(actor, KnownActorAttribution):
        return {
            "actor_attribution_kind": "known",
            "actor_id": actor.actor_id.value,
            "actor_candidate_ids": None,
        }
    if isinstance(actor, UnknownActorAttribution):
        return {
            "actor_attribution_kind": "unknown",
            "actor_id": None,
            "actor_candidate_ids": None,
        }
    return {
        "actor_attribution_kind": "contested",
        "actor_id": None,
        "actor_candidate_ids": sorted(
            (identity.value for identity in actor.candidate_actor_ids), key=str
        ),
    }


def actor_from_columns(row: RowLike) -> ActorAttribution:
    kind = _string(row["actor_attribution_kind"], "actor_attribution_kind")
    if kind == "known":
        return KnownActorAttribution(ActorId(_uuid(row["actor_id"], "actor_id")))
    if kind == "unknown":
        return UnknownActorAttribution()
    if kind == "contested":
        return ContestedActorAttribution(
            frozenset(
                ActorId(value)
                for value in _uuid_list(
                    row["actor_candidate_ids"], "actor_candidate_ids"
                )
            )
        )
    raise ValueError(f"unsupported Actor Attribution kind: {kind}")


def technical_payload(provenance: TechnicalProvenance) -> list[JsonObject]:
    return [
        {"kind": reference.kind.value, "reference": reference.reference}
        for reference in sorted(
            provenance.references,
            key=lambda item: (item.kind.value, item.reference),
        )
    ]


def technical_from_payload(value: object) -> TechnicalProvenance:
    if not isinstance(value, list):
        raise ValueError("technical_provenance must be a JSON list")
    references = []
    for item in value:
        payload = _mapping(item, "technical_provenance entry")
        references.append(
            TechnicalReference(
                TechnicalReferenceKind(_string(payload.get("kind"), "technical kind")),
                _string(payload.get("reference"), "technical reference"),
            )
        )
    return TechnicalProvenance(references)


def trigger_columns(trigger: TriggerProvenance) -> dict[str, object]:
    return {
        "trigger_kind": trigger.kind.value,
        "trigger_reference": trigger.reference,
    }


def trigger_from_columns(row: RowLike) -> TriggerProvenance:
    return TriggerProvenance(
        TriggerKind(_string(row["trigger_kind"], "trigger_kind")),
        _string(row["trigger_reference"], "trigger_reference"),
    )


def initiation_request_payload(request: InitiationSemanticRequest) -> JsonObject:
    continuity: JsonObject | None = None
    if request.continuity is not None:
        continuity = {
            "kind": request.continuity.kind.value,
            "decision_id": (
                str(request.continuity.decision_id.value)
                if request.continuity.decision_id is not None
                else None
            ),
            "rationale": request.continuity.rationale,
        }
    return {
        "actor_attribution": _actor_payload(request.actor_attribution),
        "trigger": {
            "kind": request.trigger.kind.value,
            "reference": request.trigger.reference,
        },
        "effective_at": request.effective_at.isoformat(),
        "expected_versions": [
            {
                "decision_id": str(item.decision_id.value),
                "version": item.version.value,
            }
            for item in sorted(
                request.expected_versions, key=lambda item: str(item.decision_id.value)
            )
        ],
        "need_statement": request.need_statement,
        "subject": request.subject.statement,
        "scope": _scope_payload(request.scope),
        "continuity": continuity,
    }


def initiation_result_payload(result: InitiationResult) -> JsonObject:
    return {
        "decision_id": str(result.decision_id.value),
        "need_id": str(result.need_id.value) if result.need_id is not None else None,
        "kind": result.kind.value,
    }


def initiation_receipt_from_row(row: RowMapping) -> InitiationReceipt:
    request = initiation_request_from_payload(row["request_payload"])
    result = initiation_result_from_payload(row["result_payload"])
    return InitiationReceipt(
        operation_id=OperationId(_uuid(row["operation_id"], "operation_id")),
        request=request,
        result=result,
    )


def initiation_request_from_payload(value: object) -> InitiationSemanticRequest:
    payload = _mapping(value, "initiation request")
    actor = _actor_from_payload(payload.get("actor_attribution"))
    if not isinstance(actor, KnownActorAttribution):
        raise ValueError("initiation receipt must contain known Actor Attribution")
    trigger = _mapping(payload.get("trigger"), "trigger")
    scope = _mapping(payload.get("scope"), "scope")
    raw_expected = payload.get("expected_versions")
    if not isinstance(raw_expected, list):
        raise ValueError("expected_versions must be a JSON list")
    expected = frozenset(
        _expected_version(_mapping(item, "expected version")) for item in raw_expected
    )
    raw_continuity = payload.get("continuity")
    continuity = None
    if raw_continuity is not None:
        continuity_payload = _mapping(raw_continuity, "continuity")
        raw_decision_id = continuity_payload.get("decision_id")
        continuity = ContinuityDetermination(
            kind=ContinuityDeterminationKind(
                _string(continuity_payload.get("kind"), "continuity kind")
            ),
            decision_id=(
                InvestmentDecisionId(_uuid(raw_decision_id, "continuity decision_id"))
                if raw_decision_id is not None
                else None
            ),
            rationale=_optional_string(continuity_payload.get("rationale")),
        )
    return InitiationSemanticRequest(
        actor_attribution=actor,
        trigger=TriggerProvenance(
            TriggerKind(_string(trigger.get("kind"), "trigger kind")),
            _string(trigger.get("reference"), "trigger reference"),
        ),
        effective_at=_datetime(payload.get("effective_at"), "effective_at"),
        expected_versions=expected,
        need_statement=_string(payload.get("need_statement"), "need_statement"),
        subject=DecisionSubject(_string(payload.get("subject"), "subject")),
        scope=DecisionScope(
            (
                PortfolioId(_uuid(item, "scope portfolio ID"))
                for item in _object_list(scope.get("portfolio_ids"), "portfolio_ids")
            ),
            DecisionScopeCompleteness(
                _string(scope.get("completeness"), "scope completeness")
            ),
        ),
        continuity=continuity,
    )


def initiation_result_from_payload(value: object) -> InitiationResult:
    payload = _mapping(value, "initiation result")
    raw_need_id = payload.get("need_id")
    return InitiationResult(
        decision_id=InvestmentDecisionId(
            _uuid(payload.get("decision_id"), "decision_id")
        ),
        need_id=(
            DecisionNeedId(_uuid(raw_need_id, "need_id"))
            if raw_need_id is not None
            else None
        ),
        kind=InitiationResultKind(_string(payload.get("kind"), "result kind")),
    )


def request_fingerprint(request: InitiationSemanticRequest) -> str:
    encoded = json.dumps(
        initiation_request_payload(request),
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def initiated_fact_from_rows(
    fact_row: RowMapping,
    need_row: RowMapping,
) -> DecisionInitiated:
    need = DecisionNeed(
        need_id=DecisionNeedId(_uuid(need_row["need_id"], "need_id")),
        statement=_string(need_row["statement"], "Need statement"),
        effective_at=_datetime(need_row["effective_at"], "Need effective_at"),
        recorded_at=_datetime(need_row["recorded_at"], "Need recorded_at"),
        operation_id=OperationId(_uuid(need_row["operation_id"], "Need operation_id")),
        actor_attribution=actor_from_columns(need_row),
        trigger=trigger_from_columns(need_row),
        technical_provenance=technical_from_payload(need_row["technical_provenance"]),
    )
    metadata = DecisionLifecycleFactMetadata(
        fact_id=DecisionLifecycleFactId(_uuid(fact_row["fact_id"], "fact_id")),
        decision_id=InvestmentDecisionId(_uuid(fact_row["decision_id"], "decision_id")),
        sequence=DecisionLifecycleSequence(
            _integer(fact_row["lifecycle_sequence"], "lifecycle_sequence")
        ),
        decision_version=DecisionVersion(
            _integer(fact_row["decision_version"], "decision_version")
        ),
        operation_id=OperationId(_uuid(fact_row["operation_id"], "operation_id")),
        actor_attribution=actor_from_columns(fact_row),
        trigger=trigger_from_columns(fact_row),
        technical_provenance=technical_from_payload(fact_row["technical_provenance"]),
        effective_at=_datetime(fact_row["effective_at"], "effective_at"),
        recorded_at=_datetime(fact_row["recorded_at"], "recorded_at"),
    )
    return DecisionInitiated(
        metadata=metadata,
        need=need,
        subject=DecisionSubject(
            _string(fact_row["subject_statement"], "subject_statement")
        ),
        scope=DecisionScope(
            (
                PortfolioId(value)
                for value in _uuid_list(
                    fact_row["scope_portfolio_ids"], "scope_portfolio_ids"
                )
            ),
            DecisionScopeCompleteness(
                _string(fact_row["scope_completeness"], "scope_completeness")
            ),
        ),
        continuity=DecisionInitiationContinuity(
            determination=DecisionInitiationDetermination(
                _string(
                    fact_row["continuity_determination"],
                    "continuity_determination",
                )
            ),
            candidate_decision_ids=(
                InvestmentDecisionId(value)
                for value in _uuid_list(
                    fact_row["continuity_candidate_ids"],
                    "continuity_candidate_ids",
                )
            ),
            known_at=_datetime(fact_row["continuity_known_at"], "continuity_known_at"),
            rationale=_optional_string(fact_row["continuity_rationale"]),
        ),
    )


def _actor_payload(actor: ActorAttribution) -> JsonObject:
    if isinstance(actor, KnownActorAttribution):
        return {"kind": "known", "actor_id": str(actor.actor_id.value)}
    if isinstance(actor, UnknownActorAttribution):
        return {"kind": "unknown"}
    return {
        "kind": "contested",
        "candidate_actor_ids": sorted(
            str(identity.value) for identity in actor.candidate_actor_ids
        ),
    }


def _actor_from_payload(value: object) -> ActorAttribution:
    payload = _mapping(value, "actor_attribution")
    kind = _string(payload.get("kind"), "actor attribution kind")
    if kind == "known":
        return KnownActorAttribution(
            ActorId(_uuid(payload.get("actor_id"), "actor_id"))
        )
    if kind == "unknown":
        return UnknownActorAttribution()
    if kind == "contested":
        return ContestedActorAttribution(
            frozenset(
                ActorId(_uuid(item, "candidate actor ID"))
                for item in _object_list(
                    payload.get("candidate_actor_ids"), "candidate_actor_ids"
                )
            )
        )
    raise ValueError(f"unsupported Actor Attribution kind: {kind}")


def _scope_payload(scope: DecisionScope) -> JsonObject:
    return {
        "completeness": scope.completeness.value,
        "portfolio_ids": sorted(
            str(identity.value) for identity in scope.portfolio_ids
        ),
    }


def _expected_version(payload: Mapping[str, object]) -> ExpectedDecisionVersion:
    return ExpectedDecisionVersion(
        InvestmentDecisionId(_uuid(payload.get("decision_id"), "decision_id")),
        DecisionVersion(_integer(payload.get("version"), "version")),
    )


def _mapping(value: object, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        raise ValueError(f"{field} must be a JSON object")
    return value


def _object_list(value: object, field: str) -> list[object]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a JSON list")
    return value


def _uuid_list(value: object, field: str) -> tuple[UUID, ...]:
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{field} must be a UUID collection")
    return tuple(_uuid(item, field) for item in value)


def _uuid(value: object, field: str) -> UUID:
    if type(value) is UUID:
        return value
    if isinstance(value, UUID):
        return UUID(str(value))
    if isinstance(value, str):
        return UUID(value)
    raise ValueError(f"{field} must be UUID-compatible")


def _datetime(value: object, field: str) -> datetime:
    if isinstance(value, datetime):
        result = value
    elif isinstance(value, str):
        result = datetime.fromisoformat(value)
    else:
        raise ValueError(f"{field} must be datetime-compatible")
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    return result


def _integer(value: object, field: str) -> int:
    if type(value) is not int:
        raise ValueError(f"{field} must be an integer")
    return value


def _string(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    return value


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    return _string(value, "optional string")
