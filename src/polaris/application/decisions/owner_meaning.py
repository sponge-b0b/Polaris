"""R2 Decision Memory attestation for an exact R3 Evidence basis key."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from polaris.application.evidence.owner_meaning import (
    GoverningDecisionMeaning,
    OwnerCauseVerdict,
    OwnerHistoryRecord,
    OwnerMeaningCause,
    OwnerMeaningNoBasis,
    OwnerMeaningNoBasisReason,
    OwnerMeaningReadUnavailable,
    OwnerMeaningSubject,
    OwnerMeaningWitness,
)
from polaris.domain.decisions import (
    ContestedDecisionLifecycleInterpretation,
    DecisionApplicability,
    DecisionInitiated,
    DecisionLifecycleCorrected,
    DecisionLifecycleDisposition,
    DecisionLifecycleFactId,
    DecisionNeed,
    DecisionRelationshipBasisContribution,
    DecisionRelationshipCorrected,
    DecisionRelationshipFact,
    DecisionRelationshipFactId,
    DecisionRelationshipPositiveClaim,
    DecisionRelationshipState,
    DecisionRelationshipType,
    DecisionScope,
    DecisionSubject,
    DecisionWorkPosture,
    DeterminateDecisionLifecycleInterpretation,
    InvalidDecisionHistory,
    InvalidDecisionRelationshipHistory,
    InvalidDecisionTransition,
    InvestmentDecisionId,
    NotYetEffectiveDecisionLifecycleInterpretation,
    OperationId,
    derive_relationship_applicability,
    reconstruct_decision,
    relationship_version_changes_for_command,
    validate_decision_lifecycle_lineage,
)
from polaris.domain.decisions.facts import DecisionLifecycleFact
from polaris.domain.decisions.relationships import DecisionRelationshipHistoryFact
from polaris.domain.evidence.context_versions import BasisScopeKey

from .contracts import (
    LifecycleConflict,
    RelationshipHistoryIncomplete,
    RelationshipHistoryInvalidOrIncomplete,
)
from .memory import (
    DecisionLineageDirection,
    DecisionLineageView,
    DecisionMemoryCurrentState,
    DecisionMemoryQueryReader,
    DecisionVersionSupport,
    _lineage,
)


# duplicate-code: this as-of semantic projection excludes the domain interpreter's
# observation instants; sharing its value type would make clock passage look like drift.
# arid: disable
@dataclass(frozen=True, slots=True)
class DecisionRelationshipMeaning:
    source_decision_id: InvestmentDecisionId
    target_decision_id: InvestmentDecisionId
    relationship_type: DecisionRelationshipType
    direction: DecisionLineageDirection
    state: DecisionRelationshipState
    support_fact_ids: frozenset[DecisionRelationshipFactId]
    basis_contributions: frozenset[DecisionRelationshipBasisContribution]
    surviving_positive_claims: frozenset[DecisionRelationshipPositiveClaim]


# arid: enable
@dataclass(frozen=True, slots=True)
class DecisionRelationshipGuard:
    """Complete incident selection, including an empty selection."""

    key: BasisScopeKey
    selected: tuple[DecisionRelationshipMeaning, ...]


@dataclass(frozen=True, slots=True)
class DecisionOwnerMeaning:
    """Decision semantics without the observation instant used to derive them."""

    need: DecisionNeed
    subject: DecisionSubject
    scope: DecisionScope
    disposition: DecisionLifecycleDisposition
    lifecycle_support: frozenset[DecisionLifecycleFactId]
    work_posture: DecisionWorkPosture | None
    applicability: DecisionApplicability
    lineage: tuple[DecisionRelationshipMeaning, ...]


class DecisionMeaningProvenance(StrEnum):
    R2_DECISION_MEMORY = "r2_decision_memory"


type DecisionMeaningWitness = OwnerMeaningWitness[
    DecisionOwnerMeaning,
    DecisionMeaningProvenance,
    DecisionLifecycleFact | DecisionRelationshipHistoryFact | DecisionVersionSupport,
    DecisionLifecycleCorrected | DecisionRelationshipCorrected,
    DecisionRelationshipGuard,
]


class DecisionOwnerMeaningReader:
    """Attest and independently re-evaluate complete R2 history at (T, K)."""

    def __init__(self, reader: DecisionMemoryQueryReader) -> None:
        self._reader = reader

    async def read_at(
        self,
        key: BasisScopeKey,
        subject: OwnerMeaningSubject,
        *,
        effective_at: datetime,
        known_at: datetime,
        read_at: datetime,
    ) -> DecisionMeaningWitness | OwnerMeaningNoBasis:
        subject = _validate_request(key, subject, effective_at, known_at, read_at)
        identity = key, subject, effective_at, known_at, read_at
        try:
            snapshot = await self._reader.load_current_decision_state(
                key.decision_id, known_at=known_at
            )
        except RelationshipHistoryIncomplete as error:
            return _no_basis(
                *identity, OwnerMeaningNoBasisReason.INCOMPLETE, str(error)
            )
        except (LifecycleConflict, RelationshipHistoryInvalidOrIncomplete) as error:
            return _no_basis(
                *identity, OwnerMeaningNoBasisReason.INVALID_HISTORY, str(error)
            )
        except Exception as error:
            raise OwnerMeaningReadUnavailable(
                "Decision Memory snapshot is unavailable"
            ) from error
        if snapshot is None:
            return _no_basis(
                *identity,
                OwnerMeaningNoBasisReason.MISSING,
                "Decision is not known at K",
            )
        if type(snapshot) is not DecisionMemoryCurrentState:
            return _no_basis(
                *identity,
                OwnerMeaningNoBasisReason.INVALID_HISTORY,
                "Decision Memory returned an invalid snapshot",
            )
        if snapshot.version != subject.reference.revision:
            return _no_basis(
                *identity,
                OwnerMeaningNoBasisReason.CONTRADICTORY,
                "Decision version does not match the owner snapshot",
            )
        return _attest(snapshot, key, subject, effective_at, known_at, read_at)

    async def verify_cause(
        self, witness: DecisionMeaningWitness, *, validation_at: datetime
    ) -> OwnerCauseVerdict | OwnerMeaningNoBasisReason:
        if validation_at.tzinfo is None or validation_at.utcoffset() is None:
            raise ValueError("validation_at must be timezone-aware")
        if validation_at < witness.read_at:
            return OwnerMeaningNoBasisReason.INVALID_HISTORY
        result = await self.read_at(
            witness.key,
            witness.subject,
            effective_at=witness.effective_at,
            known_at=witness.known_at,
            read_at=witness.read_at,
        )
        if isinstance(result, OwnerMeaningNoBasis):
            return result.reason
        if result != witness:
            return OwnerMeaningNoBasisReason.INVALID_HISTORY
        return OwnerCauseVerdict.VALID


def _validate_request(
    key: BasisScopeKey,
    subject: OwnerMeaningSubject,
    effective_at: datetime,
    known_at: datetime,
    read_at: datetime,
) -> GoverningDecisionMeaning:
    if type(key) is not BasisScopeKey or type(subject) is not GoverningDecisionMeaning:
        raise TypeError("Decision owner requires a governing Decision subject")
    if subject.reference.root != key.decision_id:
        raise ValueError("Decision owner subject must match the exact key")
    for boundary in (effective_at, known_at, read_at):
        if boundary.tzinfo is None or boundary.utcoffset() is None:
            raise ValueError("Decision owner boundaries must be timezone-aware")
    if known_at > read_at:
        raise ValueError("read cannot precede its knowledge boundary")
    return subject


def _no_basis(
    key: BasisScopeKey,
    subject: GoverningDecisionMeaning,
    effective_at: datetime,
    known_at: datetime,
    read_at: datetime,
    reason: OwnerMeaningNoBasisReason,
    detail: str,
) -> OwnerMeaningNoBasis:
    return OwnerMeaningNoBasis(
        key, subject, effective_at, known_at, read_at, reason, detail
    )


def _relationship_meaning(view: DecisionLineageView) -> DecisionRelationshipMeaning:
    return DecisionRelationshipMeaning(
        view.source_decision_id,
        view.target_decision_id,
        view.relationship_type,
        view.direction,
        view.state,
        view.support_fact_ids,
        view.basis_contributions,
        view.surviving_positive_claims,
    )


def _attest(
    snapshot: DecisionMemoryCurrentState,
    key: BasisScopeKey,
    subject: GoverningDecisionMeaning,
    effective_at: datetime,
    known_at: datetime,
    read_at: datetime,
) -> DecisionMeaningWitness | OwnerMeaningNoBasis:
    identity = key, subject, effective_at, known_at, read_at
    lifecycle = tuple(
        fact
        for fact in snapshot.lifecycle_facts
        if fact.metadata.recorded_at <= known_at
    )
    relationships = tuple(
        fact
        for fact in snapshot.relationship_history
        if fact.metadata.recorded_at <= known_at
    )
    if not lifecycle:
        return _no_basis(
            *identity,
            OwnerMeaningNoBasisReason.INCOMPLETE,
            "Decision lifecycle history is incomplete",
        )
    if any(fact.metadata.decision_id != key.decision_id for fact in lifecycle):
        return _no_basis(
            *identity,
            OwnerMeaningNoBasisReason.INVALID_HISTORY,
            "Decision lifecycle history belongs to another Decision",
        )
    try:
        # This validates future-effective and non-incident relationship history too.
        _validate_recording_boundaries(lifecycle, relationships)
        validate_decision_lifecycle_lineage(relationships, known_at=known_at)
        applicability = derive_relationship_applicability(
            key.decision_id,
            relationships,
            effective_at=effective_at,
            known_at=known_at,
        )
        decision = reconstruct_decision(
            lifecycle,
            observed_at=known_at,
            applicability=applicability,
            decision_version=snapshot.version,
        ).effective_at(effective_at, known_at=known_at, applicability=applicability)
        lineage = _lineage(
            relationships,
            decision_id=key.decision_id,
            effective_at=effective_at,
            known_at=known_at,
        )
        _validate_version_support(
            snapshot, lifecycle, relationships, lineage, key, known_at
        )
    except (
        InvalidDecisionHistory,
        InvalidDecisionRelationshipHistory,
        InvalidDecisionTransition,
    ) as error:
        return _no_basis(
            *identity, OwnerMeaningNoBasisReason.INVALID_HISTORY, str(error)
        )
    except RelationshipHistoryIncomplete as error:
        return _no_basis(*identity, OwnerMeaningNoBasisReason.INCOMPLETE, str(error))
    interpretation = decision.lifecycle_interpretation
    if type(interpretation) is NotYetEffectiveDecisionLifecycleInterpretation:
        return _no_basis(
            *identity,
            OwnerMeaningNoBasisReason.NOT_YET_EFFECTIVE,
            "Decision lifecycle is not yet effective at T",
        )
    if (
        type(interpretation) is ContestedDecisionLifecycleInterpretation
        or applicability is DecisionApplicability.CONTESTED
        or any(item.state is DecisionRelationshipState.CONTESTED for item in lineage)
    ):
        return _no_basis(
            *identity,
            OwnerMeaningNoBasisReason.CONTESTED,
            "Decision lifecycle or applicability is contested",
        )
    assert type(interpretation) is DeterminateDecisionLifecycleInterpretation
    selected = tuple(
        _relationship_meaning(item)
        for item in lineage
        if item.state is DecisionRelationshipState.SUPPORTED
    )
    guard = DecisionRelationshipGuard(key, selected)
    facts = (
        tuple(
            OwnerHistoryRecord(
                fact, fact.metadata.effective_at, fact.metadata.recorded_at
            )
            for fact in lifecycle
            if not isinstance(fact, DecisionLifecycleCorrected)
        )
        + tuple(
            OwnerHistoryRecord(
                fact, fact.relationship_effective_at, fact.metadata.recorded_at
            )
            for fact in relationships
            if isinstance(fact, DecisionRelationshipFact)
        )
        + tuple(
            OwnerHistoryRecord(item, item.recorded_at, item.recorded_at)
            for item in snapshot.version_support
            if item.recorded_at <= known_at
        )
    )
    corrections = tuple(
        OwnerHistoryRecord(fact, fact.metadata.effective_at, fact.metadata.recorded_at)
        for fact in lifecycle
        if isinstance(fact, DecisionLifecycleCorrected)
    ) + tuple(
        OwnerHistoryRecord(
            fact, fact.correction_effective_at, fact.metadata.recorded_at
        )
        for fact in relationships
        if isinstance(fact, DecisionRelationshipCorrected)
    )
    return OwnerMeaningWitness(
        key,
        subject,
        effective_at,
        known_at,
        read_at,
        DecisionOwnerMeaning(
            decision.need,
            decision.subject,
            decision.scope,
            interpretation.disposition,
            interpretation.support_fact_ids,
            decision.work_posture,
            applicability,
            selected,
        ),
        DecisionMeaningProvenance.R2_DECISION_MEMORY,
        OwnerMeaningCause(facts, corrections, (guard,), True),
    )


def _validate_recording_boundaries(
    lifecycle: tuple[DecisionLifecycleFact, ...],
    relationships: tuple[DecisionRelationshipHistoryFact, ...],
) -> None:
    by_operation: dict[OperationId, datetime] = {}
    for fact in (*lifecycle, *relationships):
        operation = fact.metadata.operation_id
        recorded_at = fact.metadata.recorded_at
        if operation in by_operation and by_operation[operation] != recorded_at:
            raise InvalidDecisionHistory(
                "one Decision operation has conflicting recording boundaries"
            )
        by_operation[operation] = recorded_at


def _validate_version_support(
    snapshot: DecisionMemoryCurrentState,
    lifecycle: tuple[DecisionLifecycleFact, ...],
    relationships: tuple[DecisionRelationshipHistoryFact, ...],
    lineage: tuple[DecisionLineageView, ...],
    key: BasisScopeKey,
    known_at: datetime,
) -> None:
    incident_ids = {
        fact.metadata.relationship_fact_id for item in lineage for fact in item.history
    }
    incident_operations = {
        fact.metadata.operation_id for item in lineage for fact in item.history
    }
    operations = set()
    known_support = []
    for support in snapshot.version_support:
        if support.recorded_at > known_at:
            continue
        if support.decision_id != key.decision_id or support.operation_id in operations:
            raise InvalidDecisionHistory("Decision version support has wrong identity")
        operations.add(support.operation_id)
        matching = tuple(
            fact
            for fact in relationships
            if fact.metadata.operation_id == support.operation_id
        )
        if (
            not matching
            or support.relationship_fact_ids
            != frozenset(fact.metadata.relationship_fact_id for fact in matching)
            or not (support.relationship_fact_ids & incident_ids)
            or any(
                fact.metadata.recorded_at != support.recorded_at for fact in matching
            )
            or support.after.value
            not in (support.before.value, support.before.value + 1)
        ):
            raise InvalidDecisionHistory("Decision version support is not entailed")
        known_support.append(support)
    if operations != incident_operations:
        raise RelationshipHistoryIncomplete(
            "incident relationship history is missing version support"
        )
    order = _check_version_chain(
        snapshot.version.value, lifecycle, relationships, known_support
    )
    support_by_operation = {item.operation_id: item for item in known_support}
    lifecycle_by_operation = {fact.metadata.operation_id: fact for fact in lifecycle}
    prior_operations: set[OperationId] = set()
    for operation in order:
        receipt = support_by_operation.get(operation)
        if receipt is not None:
            before = tuple(
                fact
                for fact in relationships
                if fact.metadata.recorded_at < receipt.recorded_at
                or (
                    fact.metadata.recorded_at == receipt.recorded_at
                    and fact.metadata.operation_id in prior_operations
                )
            )
            proposed = tuple(
                fact
                for fact in relationships
                if fact.metadata.operation_id == operation
            )
            changed = key.decision_id in relationship_version_changes_for_command(
                before, proposed, recording_boundary=receipt.recorded_at
            )
            lifecycle_fact = lifecycle_by_operation.get(operation)
            if not (
                type(lifecycle_fact) is DecisionInitiated
                and receipt.before.value == receipt.after.value == 1
                and lifecycle_fact.metadata.decision_version.value == 1
            ):
                lifecycle_increment = (
                    lifecycle_fact is not None
                    and lifecycle_fact.metadata.decision_version.value
                    == receipt.before.value + 1
                )
                expected_after = receipt.before.value + (changed or lifecycle_increment)
                if receipt.after.value != expected_after:
                    raise InvalidDecisionHistory(
                        "Decision version support contradicts relationship effect"
                    )
        prior_operations.add(operation)


def _lifecycle_correction_effects(
    lifecycle: tuple[DecisionLifecycleFact, ...],
) -> dict[OperationId, bool]:
    effects = {}
    for index, fact in enumerate(lifecycle):
        if not isinstance(fact, DecisionLifecycleCorrected):
            continue
        boundary = fact.metadata.recorded_at
        before = reconstruct_decision(
            lifecycle[:index],
            observed_at=boundary,
            applicability=DecisionApplicability.OPERATIVE,
        ).lifecycle_interpretation
        after = reconstruct_decision(
            lifecycle[: index + 1],
            observed_at=boundary,
            applicability=DecisionApplicability.OPERATIVE,
        ).lifecycle_interpretation
        effects[fact.metadata.operation_id] = before != after
    return effects


def _relationship_operation_dependencies(
    relationships: tuple[DecisionRelationshipHistoryFact, ...],
) -> dict[OperationId, set[OperationId]]:
    relationships_by_id = {
        fact.metadata.relationship_fact_id: fact for fact in relationships
    }
    dependencies: dict[OperationId, set[OperationId]] = {}
    for fact in relationships:
        if not isinstance(fact, DecisionRelationshipCorrected):
            continue
        target = relationships_by_id[fact.target_relationship_fact_id]
        if (
            target.metadata.operation_id != fact.metadata.operation_id
            and target.metadata.recorded_at == fact.metadata.recorded_at
        ):
            dependencies.setdefault(fact.metadata.operation_id, set()).add(
                target.metadata.operation_id
            )
    return dependencies


def _check_version_chain(
    expected_version: int,
    lifecycle: tuple[DecisionLifecycleFact, ...],
    relationships: tuple[DecisionRelationshipHistoryFact, ...],
    support: list[DecisionVersionSupport],
) -> tuple[OperationId, ...]:
    lifecycle_by_operation = {fact.metadata.operation_id: fact for fact in lifecycle}
    if len(lifecycle_by_operation) != len(lifecycle):
        raise InvalidDecisionHistory(
            "one Decision operation has multiple lifecycle facts"
        )
    correction_effects = _lifecycle_correction_effects(lifecycle)
    support_by_operation = {item.operation_id: item for item in support}
    operations = lifecycle_by_operation.keys() | support_by_operation.keys()
    dependencies = _relationship_operation_dependencies(relationships)
    events_by_recording: dict[
        datetime,
        list[
            tuple[
                OperationId,
                DecisionLifecycleFact | None,
                DecisionVersionSupport | None,
            ]
        ],
    ] = {}
    for operation in operations:
        fact = lifecycle_by_operation.get(operation)
        receipt = support_by_operation.get(operation)
        recorded_at = (
            fact.metadata.recorded_at if fact is not None else receipt.recorded_at
        )
        events_by_recording.setdefault(recorded_at, []).append(
            (operation, fact, receipt)
        )
    version = 0
    order = []
    completed: set[OperationId] = set()
    for recorded_at in sorted(events_by_recording):
        pending = events_by_recording[recorded_at]
        while pending:
            eligible = [
                (index, after, fact, receipt)
                for index, (operation, fact, receipt) in enumerate(pending)
                if dependencies.get(operation, set()) <= completed
                and (
                    after := _operation_after(
                        version,
                        fact,
                        receipt,
                        correction_effects.get(operation),
                    )
                )
                is not None
            ]
            if not eligible:
                raise InvalidDecisionHistory(
                    "Decision version history has no causal ordering"
                )
            index, version, _, _ = min(
                eligible,
                key=lambda item: (
                    item[1] != version,
                    isinstance(item[2], DecisionLifecycleCorrected) and item[3] is None,
                ),
            )
            operation, _, _ = pending.pop(index)
            order.append(operation)
            completed.add(operation)
    if expected_version != version:
        raise InvalidDecisionHistory("Decision version has no authoritative cause")
    return tuple(order)


def _operation_after(
    version: int,
    fact: DecisionLifecycleFact | None,
    receipt: DecisionVersionSupport | None,
    correction_changes: bool | None,
) -> int | None:
    if fact is not None:
        expected_lifecycle_version = version + (
            correction_changes if isinstance(fact, DecisionLifecycleCorrected) else 1
        )
        if fact.metadata.decision_version.value != expected_lifecycle_version:
            return None
        lifecycle_version = fact.metadata.decision_version.value
    else:
        lifecycle_version = version
    if receipt is None:
        return lifecycle_version
    if receipt.before.value != version and not (
        version == 0
        and fact is not None
        and receipt.before.value == lifecycle_version == 1
    ):
        return None
    if receipt.after.value != lifecycle_version and not (
        lifecycle_version == version and receipt.after.value == version + 1
    ):
        return None
    return receipt.after.value
