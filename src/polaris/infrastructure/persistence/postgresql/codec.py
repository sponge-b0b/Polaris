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
from polaris.application.decisions.ordinary_work import (
    DecisionMutationKind,
    DecisionMutationReceipt,
    DecisionMutationResult,
    DecisionMutationResultKind,
    DecisionMutationSemanticRequest,
    ExternalResolutionPayload,
    HumanDeferralPayload,
    LifecycleCorrectionPayload,
    ScopeMutationPayload,
    SubjectRevisionPayload,
    SubstantiveResolutionPayload,
    UnsupportedNeedRetractionPayload,
    WorkResumptionPayload,
    WorkWithdrawalPayload,
)
from polaris.domain.actors import (
    ActorAttribution,
    ActorId,
    ContestedActorAttribution,
    KnownActorAttribution,
    UnknownActorAttribution,
)
from polaris.domain.decisions import (
    DecisionContinuity,
    DecisionDeferred,
    DecisionExternallyResolved,
    DecisionInitiated,
    DecisionInitiationContinuity,
    DecisionInitiationDetermination,
    DecisionLifecycleCorrected,
    DecisionLifecycleCorrectionBasis,
    DecisionLifecycleCorrectionEffect,
    DecisionLifecycleDisposition,
    DecisionLifecycleFactId,
    DecisionLifecycleFactMetadata,
    DecisionLifecycleSequence,
    DecisionNeed,
    DecisionNeedId,
    DecisionScope,
    DecisionScopeCompleteness,
    DecisionScopeEstablished,
    DecisionScopeRevised,
    DecisionSubject,
    DecisionSubjectRevised,
    DecisionSubstantivelyResolved,
    DecisionVersion,
    DecisionWorkControlBasis,
    DecisionWorkResumed,
    DecisionWorkWithdrawn,
    ExternalResolutionBasis,
    HumanInvestmentDecisionEffect,
    InvestmentDecisionId,
    OperationId,
    PortfolioId,
    TechnicalProvenance,
    TechnicalReference,
    TechnicalReferenceKind,
    TriggerKind,
    TriggerProvenance,
    TrustedHumanInvestmentDecisionBasis,
    UnsupportedDecisionNeedBasis,
)
from polaris.domain.decisions.facts import DecisionLifecycleFact

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


def mutation_request_payload(request: DecisionMutationSemanticRequest) -> JsonObject:
    return {
        "kind": request.kind.value,
        "decision_id": str(request.decision_id.value),
        # duplicate-code: variants require independent field validation.
        # arid: disable
        "actor_attribution": _actor_payload(request.actor_attribution),
        "trigger": {
            "kind": request.trigger.kind.value,
            "reference": request.trigger.reference,
        },
        "effective_at": request.effective_at.isoformat(),
        # arid: enable
        "expected_version": request.expected_version.value,
        "payload": _mutation_payload(request.payload),
    }


def mutation_result_payload(result: DecisionMutationResult) -> JsonObject:
    return {
        "decision_id": str(result.decision_id.value),
        "version": result.version.value,
        "kind": result.kind.value,
    }


def mutation_receipt_from_row(row: RowMapping) -> DecisionMutationReceipt:
    return DecisionMutationReceipt(
        operation_id=OperationId(_uuid(row["operation_id"], "operation_id")),
        request=mutation_request_from_payload(row["request_payload"]),
        result=mutation_result_from_payload(row["result_payload"]),
    )


def mutation_request_from_payload(value: object) -> DecisionMutationSemanticRequest:
    payload = _mapping(value, "Decision mutation request")
    kind = DecisionMutationKind(_string(payload.get("kind"), "mutation kind"))
    actor = _actor_from_payload(payload.get("actor_attribution"))
    if not isinstance(actor, KnownActorAttribution):
        raise ValueError(
            "Decision mutation receipt must contain known Actor Attribution"
        )
    trigger = _mapping(payload.get("trigger"), "trigger")
    mutation_payload = _mapping(payload.get("payload"), "mutation payload")
    return DecisionMutationSemanticRequest(
        kind=kind,
        decision_id=InvestmentDecisionId(
            _uuid(payload.get("decision_id"), "decision_id")
        ),
        # duplicate-code: variants require independent field validation.
        # arid: disable
        actor_attribution=actor,
        trigger=TriggerProvenance(
            TriggerKind(_string(trigger.get("kind"), "trigger kind")),
            _string(trigger.get("reference"), "trigger reference"),
        ),
        effective_at=_datetime(payload.get("effective_at"), "effective_at"),
        # arid: enable
        expected_version=DecisionVersion(
            _integer(payload.get("expected_version"), "expected_version")
        ),
        payload=_mutation_payload_from(kind, mutation_payload),
    )


def mutation_result_from_payload(value: object) -> DecisionMutationResult:
    payload = _mapping(value, "Decision mutation result")
    return DecisionMutationResult(
        decision_id=InvestmentDecisionId(
            _uuid(payload.get("decision_id"), "decision_id")
        ),
        version=DecisionVersion(_integer(payload.get("version"), "version")),
        kind=DecisionMutationResultKind(_string(payload.get("kind"), "result kind")),
    )


def mutation_request_fingerprint(request: DecisionMutationSemanticRequest) -> str:
    encoded = json.dumps(
        mutation_request_payload(request),
        # duplicate-code: variants require independent field validation.
        # arid: disable
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(encoded).hexdigest()
    # arid: enable


def _mutation_payload(value: object) -> JsonObject:
    if isinstance(value, SubjectRevisionPayload):
        return {
            "subject": value.subject.statement,
            "continuity": value.continuity.value,
        }
    if isinstance(value, ScopeMutationPayload):
        return {
            "scope": _scope_payload(value.scope),
            "continuity": value.continuity.value,
        }
    if isinstance(value, HumanDeferralPayload):
        return {"basis": _human_basis_payload(value.basis)}
    if isinstance(value, SubstantiveResolutionPayload):
        return {"basis": _human_basis_payload(value.basis)}
    if isinstance(value, ExternalResolutionPayload):
        return {"basis_reference": value.basis.reference}
    if isinstance(value, WorkWithdrawalPayload):
        return {"basis_reference": value.basis.reference}
    if isinstance(value, WorkResumptionPayload):
        return {
            "basis_reference": value.basis.reference,
            "continuity": value.continuity.value,
        }
    if isinstance(value, LifecycleCorrectionPayload):
        return {
            "target_fact_id": str(value.target_fact_id.value),
            "effect": value.effect.value,
            "correction_basis_reference": value.correction_basis.reference,
            "replacement_disposition": (
                value.replacement_disposition.value
                if value.replacement_disposition is not None
                else None
            ),
            "replacement_basis": _replacement_basis_payload(value.replacement_basis),
        }
    if isinstance(value, UnsupportedNeedRetractionPayload):
        return {
            "correction_basis_reference": value.correction_basis.reference,
            "unsupported_need_basis_reference": value.unsupported_need_basis.reference,
        }
    raise ValueError("unsupported Decision mutation receipt payload")


def _mutation_payload_from(
    kind: DecisionMutationKind,
    payload: Mapping[str, object],
) -> (
    SubjectRevisionPayload
    | ScopeMutationPayload
    | HumanDeferralPayload
    | SubstantiveResolutionPayload
    | ExternalResolutionPayload
    | WorkWithdrawalPayload
    | WorkResumptionPayload
    | LifecycleCorrectionPayload
    | UnsupportedNeedRetractionPayload
):
    if kind is DecisionMutationKind.REVISE_SUBJECT:
        return SubjectRevisionPayload(
            DecisionSubject(_string(payload.get("subject"), "subject")),
            DecisionContinuity(_string(payload.get("continuity"), "continuity")),
        )
    if kind is DecisionMutationKind.ESTABLISH_OR_REVISE_SCOPE:
        return ScopeMutationPayload(
            _scope_from_payload(payload.get("scope")),
            DecisionContinuity(_string(payload.get("continuity"), "continuity")),
        )
    if kind is DecisionMutationKind.APPLY_HUMAN_DEFERRAL:
        return HumanDeferralPayload(_human_basis_from_payload(payload.get("basis")))
    if kind is DecisionMutationKind.APPLY_SUBSTANTIVE_RESOLUTION:
        return SubstantiveResolutionPayload(
            _human_basis_from_payload(payload.get("basis"))
        )
    if kind is DecisionMutationKind.APPLY_EXTERNAL_RESOLUTION:
        return ExternalResolutionPayload(
            ExternalResolutionBasis(
                _string(payload.get("basis_reference"), "basis reference")
            )
        )
    if kind is DecisionMutationKind.WITHDRAW_WORK:
        return WorkWithdrawalPayload(
            DecisionWorkControlBasis(
                _string(payload.get("basis_reference"), "basis reference")
            )
        )
    if kind is DecisionMutationKind.RESUME_WORK:
        return WorkResumptionPayload(
            DecisionWorkControlBasis(
                _string(payload.get("basis_reference"), "basis reference")
            ),
            DecisionContinuity(_string(payload.get("continuity"), "continuity")),
        )
    if kind is DecisionMutationKind.RECORD_LIFECYCLE_CORRECTION:
        raw_disposition = payload.get("replacement_disposition")
        return LifecycleCorrectionPayload(
            target_fact_id=DecisionLifecycleFactId(
                _uuid(payload.get("target_fact_id"), "target_fact_id")
            ),
            effect=DecisionLifecycleCorrectionEffect(
                _string(payload.get("effect"), "correction effect")
            ),
            correction_basis=DecisionLifecycleCorrectionBasis(
                _string(
                    payload.get("correction_basis_reference"),
                    "correction basis reference",
                )
            ),
            replacement_disposition=(
                DecisionLifecycleDisposition(_string(raw_disposition, "disposition"))
                if raw_disposition is not None
                else None
            ),
            replacement_basis=_replacement_basis_from_payload(
                payload.get("replacement_basis")
            ),
        )
    if kind is DecisionMutationKind.RETRACT_UNSUPPORTED_DECISION_NEED:
        return UnsupportedNeedRetractionPayload(
            DecisionLifecycleCorrectionBasis(
                _string(
                    payload.get("correction_basis_reference"),
                    "correction basis reference",
                )
            ),
            UnsupportedDecisionNeedBasis(
                _string(
                    payload.get("unsupported_need_basis_reference"),
                    "unsupported Need basis reference",
                )
            ),
        )
    raise ValueError(f"unsupported Decision mutation kind: {kind}")


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


def mutation_fact_values(fact: DecisionLifecycleFact) -> dict[str, object]:
    metadata = fact.metadata
    values: dict[str, object] = {
        "fact_id": metadata.fact_id.value,
        "decision_id": metadata.decision_id.value,
        "lifecycle_sequence": metadata.sequence.value,
        "decision_version": metadata.decision_version.value,
        "operation_id": metadata.operation_id.value,
        **actor_columns(metadata.actor_attribution),
        **trigger_columns(metadata.trigger),
        "technical_provenance": technical_payload(metadata.technical_provenance),
        "effective_at": metadata.effective_at,
        "recorded_at": metadata.recorded_at,
    }
    if isinstance(fact, DecisionSubjectRevised):
        values.update(
            fact_kind="decision_subject_revised",
            subject_statement=fact.subject.statement,
        )
    elif isinstance(fact, (DecisionScopeEstablished, DecisionScopeRevised)):
        values.update(
            fact_kind=(
                "decision_scope_established"
                if isinstance(fact, DecisionScopeEstablished)
                else "decision_scope_revised"
            ),
            scope_completeness=fact.scope.completeness.value,
            scope_portfolio_ids=sorted(
                (identity.value for identity in fact.scope.portfolio_ids), key=str
            ),
        )
    elif isinstance(fact, (DecisionDeferred, DecisionSubstantivelyResolved)):
        values.update(
            fact_kind=(
                "decision_deferred"
                if isinstance(fact, DecisionDeferred)
                else "decision_substantively_resolved"
            ),
            human_decision_reference=fact.basis.decision_reference,
            human_decision_effect=fact.basis.effect.value,
        )
    elif isinstance(fact, (DecisionWorkWithdrawn, DecisionWorkResumed)):
        values.update(
            fact_kind=(
                "decision_work_withdrawn"
                if isinstance(fact, DecisionWorkWithdrawn)
                else "decision_work_resumed"
            ),
            work_control_reference=fact.basis.reference,
        )
    elif isinstance(fact, DecisionExternallyResolved):
        values.update(
            fact_kind="decision_externally_resolved",
            external_resolution_reference=fact.basis.reference,
        )
    elif isinstance(fact, DecisionLifecycleCorrected):
        basis_kind, basis_reference = _replacement_basis_columns(fact.replacement_basis)
        values.update(
            fact_kind="decision_lifecycle_corrected",
            correction_target_fact_id=fact.target_fact_id.value,
            correction_effect=fact.effect.value,
            correction_basis_reference=fact.correction_basis.reference,
            replacement_disposition=(
                fact.replacement_disposition.value
                if fact.replacement_disposition is not None
                else None
            ),
            replacement_basis_kind=basis_kind,
            replacement_basis_reference=basis_reference,
        )
    else:
        raise ValueError("unsupported Decision mutation fact")
    return values


def mutation_fact_from_row(row: RowMapping) -> DecisionLifecycleFact:
    metadata = _metadata_from_row(row)
    kind = _string(row["fact_kind"], "fact_kind")
    if kind == "decision_subject_revised":
        return DecisionSubjectRevised(
            metadata,
            DecisionSubject(_string(row["subject_statement"], "subject_statement")),
        )
    if kind in {"decision_scope_established", "decision_scope_revised"}:
        scope = DecisionScope(
            (
                PortfolioId(value)
                for value in _uuid_list(
                    row["scope_portfolio_ids"], "scope_portfolio_ids"
                )
            ),
            DecisionScopeCompleteness(
                _string(row["scope_completeness"], "scope_completeness")
            ),
        )
        return (
            DecisionScopeEstablished(metadata, scope)
            if kind == "decision_scope_established"
            else DecisionScopeRevised(metadata, scope)
        )
    if kind in {"decision_deferred", "decision_substantively_resolved"}:
        human_basis = TrustedHumanInvestmentDecisionBasis(
            _string(row["human_decision_reference"], "human_decision_reference"),
            HumanInvestmentDecisionEffect(
                _string(row["human_decision_effect"], "human_decision_effect")
            ),
        )
        return (
            DecisionDeferred(metadata, human_basis)
            if kind == "decision_deferred"
            else DecisionSubstantivelyResolved(metadata, human_basis)
        )
    if kind in {"decision_work_withdrawn", "decision_work_resumed"}:
        work_basis = DecisionWorkControlBasis(
            _string(row["work_control_reference"], "work_control_reference")
        )
        return (
            DecisionWorkWithdrawn(metadata, work_basis)
            if kind == "decision_work_withdrawn"
            else DecisionWorkResumed(metadata, work_basis)
        )
    if kind == "decision_externally_resolved":
        return DecisionExternallyResolved(
            metadata,
            ExternalResolutionBasis(
                _string(
                    row["external_resolution_reference"],
                    "external_resolution_reference",
                )
            ),
        )
    if kind == "decision_lifecycle_corrected":
        raw_disposition = row["replacement_disposition"]
        return DecisionLifecycleCorrected(
            metadata=metadata,
            target_fact_id=DecisionLifecycleFactId(
                _uuid(row["correction_target_fact_id"], "correction_target_fact_id")
            ),
            effect=DecisionLifecycleCorrectionEffect(
                _string(row["correction_effect"], "correction_effect")
            ),
            correction_basis=DecisionLifecycleCorrectionBasis(
                _string(
                    row["correction_basis_reference"],
                    "correction_basis_reference",
                )
            ),
            replacement_disposition=(
                DecisionLifecycleDisposition(
                    _string(raw_disposition, "replacement_disposition")
                )
                if raw_disposition is not None
                else None
            ),
            replacement_basis=_replacement_basis_from_columns(row),
        )
    raise ValueError(f"unsupported persisted lifecycle fact kind: {kind}")


def _replacement_basis_columns(value: object) -> tuple[str | None, str | None]:
    if value is None:
        return None, None
    if isinstance(value, TrustedHumanInvestmentDecisionBasis):
        return "human", value.decision_reference
    if isinstance(value, ExternalResolutionBasis):
        return "external", value.reference
    if isinstance(value, UnsupportedDecisionNeedBasis):
        return "unsupported_need", value.reference
    raise ValueError("unsupported lifecycle replacement basis")


def _replacement_basis_from_columns(
    row: RowLike,
) -> (
    TrustedHumanInvestmentDecisionBasis
    | ExternalResolutionBasis
    | UnsupportedDecisionNeedBasis
    | None
):
    raw_kind = row["replacement_basis_kind"]
    raw_reference = row["replacement_basis_reference"]
    if raw_kind is None and raw_reference is None:
        return None
    kind = _string(raw_kind, "replacement_basis_kind")
    reference = _string(raw_reference, "replacement_basis_reference")
    if kind == "human":
        return TrustedHumanInvestmentDecisionBasis(
            reference,
            HumanInvestmentDecisionEffect.SUBSTANTIVELY_RESOLVING,
        )
    if kind == "external":
        return ExternalResolutionBasis(reference)
    if kind == "unsupported_need":
        return UnsupportedDecisionNeedBasis(reference)
    raise ValueError(f"unsupported replacement basis kind: {kind}")


def _metadata_from_row(row: RowMapping) -> DecisionLifecycleFactMetadata:
    return DecisionLifecycleFactMetadata(
        fact_id=DecisionLifecycleFactId(_uuid(row["fact_id"], "fact_id")),
        decision_id=InvestmentDecisionId(_uuid(row["decision_id"], "decision_id")),
        sequence=DecisionLifecycleSequence(
            _integer(row["lifecycle_sequence"], "lifecycle_sequence")
        ),
        decision_version=DecisionVersion(
            _integer(row["decision_version"], "decision_version")
        ),
        operation_id=OperationId(_uuid(row["operation_id"], "operation_id")),
        actor_attribution=actor_from_columns(row),
        trigger=trigger_from_columns(row),
        technical_provenance=technical_from_payload(row["technical_provenance"]),
        effective_at=_datetime(row["effective_at"], "effective_at"),
        recorded_at=_datetime(row["recorded_at"], "recorded_at"),
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
    # duplicate-code: variants require independent field validation.
    # arid: disable
    if kind == "unknown":
        return UnknownActorAttribution()
    if kind == "contested":
        return ContestedActorAttribution(
            frozenset(
                # arid: enable
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


def _scope_from_payload(value: object) -> DecisionScope:
    payload = _mapping(value, "scope")
    return DecisionScope(
        (
            PortfolioId(_uuid(item, "scope portfolio ID"))
            for item in _object_list(payload.get("portfolio_ids"), "portfolio_ids")
        ),
        DecisionScopeCompleteness(
            _string(payload.get("completeness"), "scope completeness")
        ),
    )


def _human_basis_payload(value: TrustedHumanInvestmentDecisionBasis) -> JsonObject:
    return {
        "decision_reference": value.decision_reference,
        "effect": value.effect.value,
    }


def _human_basis_from_payload(value: object) -> TrustedHumanInvestmentDecisionBasis:
    payload = _mapping(value, "Human Investment Decision basis")
    return TrustedHumanInvestmentDecisionBasis(
        _string(payload.get("decision_reference"), "decision reference"),
        HumanInvestmentDecisionEffect(_string(payload.get("effect"), "effect")),
    )


def _replacement_basis_payload(value: object) -> JsonObject | None:
    if value is None:
        return None
    if isinstance(value, TrustedHumanInvestmentDecisionBasis):
        return {"kind": "human", **_human_basis_payload(value)}
    if isinstance(value, ExternalResolutionBasis):
        return {"kind": "external", "reference": value.reference}
    if isinstance(value, UnsupportedDecisionNeedBasis):
        return {"kind": "unsupported_need", "reference": value.reference}
    raise ValueError("unsupported lifecycle replacement basis")


def _replacement_basis_from_payload(
    value: object,
) -> (
    TrustedHumanInvestmentDecisionBasis
    | ExternalResolutionBasis
    | UnsupportedDecisionNeedBasis
    | None
):
    if value is None:
        return None
    payload = _mapping(value, "replacement basis")
    kind = _string(payload.get("kind"), "replacement basis kind")
    if kind == "human":
        return _human_basis_from_payload(payload)
    reference = _string(payload.get("reference"), "replacement basis reference")
    # duplicate-code: variants require independent field validation.
    # arid: disable
    if kind == "external":
        return ExternalResolutionBasis(reference)
    if kind == "unsupported_need":
        return UnsupportedDecisionNeedBasis(reference)
    raise ValueError(f"unsupported replacement basis kind: {kind}")
    # arid: enable


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
