from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, replace
from datetime import datetime

from .facts import (
    DecisionApplicability,
    DecisionApplicabilityContested,
    DecisionContinuity,
    DecisionDeferred,
    DecisionExternallyResolved,
    DecisionInitiated,
    DecisionInitiationContinuity,
    DecisionLifecycleCorrected,
    DecisionLifecycleCorrectionBasis,
    DecisionLifecycleCorrectionEffect,
    DecisionLifecycleDisposition,
    DecisionLifecycleFact,
    DecisionLifecycleFactId,
    DecisionLifecycleFactMetadata,
    DecisionLifecycleSequence,
    DecisionMutationContext,
    DecisionNeed,
    DecisionNeedAlreadyGrounded,
    DecisionNeedId,
    DecisionNotOperative,
    DecisionScope,
    DecisionScopeCompleteness,
    DecisionScopeEstablished,
    DecisionScopeRevised,
    DecisionSubject,
    DecisionSubjectRevised,
    DecisionSubstantivelyResolved,
    DecisionVersion,
    DecisionWorkControlBasis,
    DecisionWorkPosture,
    DecisionWorkResumed,
    DecisionWorkWithdrawn,
    ExternalResolutionBasis,
    HumanInvestmentDecisionEffect,
    IndependentChoiceRequiresNewDecision,
    InvalidDecisionBasis,
    InvalidDecisionHistory,
    InvalidDecisionLifecycleCorrection,
    InvalidDecisionNeed,
    InvalidDecisionTransition,
    InvestmentDecisionId,
    OperationId,
    TechnicalProvenance,
    TriggerProvenance,
    TrustedHumanInvestmentDecisionBasis,
    UnsupportedDecisionNeedBasis,
    _actor,
    _aware,
    _exact,
    _known_actor,
)
from .lifecycle import (
    ContestedDecisionLifecycleInterpretation,
    DecisionLifecycleInterpretation,
    _disposition,
    _interpret,
    _posture,
)


@dataclass(frozen=True, slots=True, init=False)
class InvestmentDecision:
    _history: tuple[DecisionLifecycleFact, ...]
    _subject: DecisionSubject
    _scope: DecisionScope
    _version: DecisionVersion
    lifecycle_interpretation: DecisionLifecycleInterpretation
    _applicability: DecisionApplicability
    _work_posture: DecisionWorkPosture | None

    def __init__(self) -> None:
        raise TypeError(
            "InvestmentDecision must be created by domain behavior or "
            "reconstruct_decision"
        )

    @classmethod
    def _from_validated(
        cls,
        history: tuple[DecisionLifecycleFact, ...],
        subject: DecisionSubject,
        scope: DecisionScope,
        version: DecisionVersion,
        interpretation: DecisionLifecycleInterpretation,
        applicability: DecisionApplicability,
        work_posture: DecisionWorkPosture | None,
    ) -> InvestmentDecision:
        instance = object.__new__(cls)
        object.__setattr__(instance, "_history", history)
        object.__setattr__(instance, "_subject", subject)
        object.__setattr__(instance, "_scope", scope)
        object.__setattr__(instance, "_version", version)
        object.__setattr__(instance, "lifecycle_interpretation", interpretation)
        object.__setattr__(instance, "_applicability", applicability)
        object.__setattr__(instance, "_work_posture", work_posture)
        return instance

    @property
    def decision_id(self) -> InvestmentDecisionId:
        return self._history[0].metadata.decision_id

    @property
    def need(self) -> DecisionNeed:
        fact = self._history[0]
        assert isinstance(fact, DecisionInitiated)
        return fact.need

    @property
    def need_id(self) -> DecisionNeedId:
        return self.need.need_id

    @property
    def subject(self) -> DecisionSubject:
        return self._subject

    @property
    def scope(self) -> DecisionScope:
        return self._scope

    @property
    def version(self) -> DecisionVersion:
        return self._version

    @property
    def disposition(self) -> DecisionLifecycleDisposition:
        return _disposition(self.lifecycle_interpretation)

    @property
    def work_posture(self) -> DecisionWorkPosture | None:
        return self._work_posture

    @property
    def created_at(self) -> datetime:
        return self._history[0].metadata.recorded_at

    @property
    def history(self) -> tuple[DecisionLifecycleFact, ...]:
        return tuple(
            f
            for f in self._history
            if f.metadata.recorded_at <= self.lifecycle_interpretation.known_at
        )

    def effective_at(
        self,
        effective_at: datetime,
        *,
        known_at: datetime,
        applicability: DecisionApplicability,
    ) -> InvestmentDecision:
        return _view(self._history, effective_at, known_at, applicability)

    def as_known_at(
        self,
        known_at: datetime,
        *,
        applicability: DecisionApplicability,
    ) -> InvestmentDecision:
        return self.effective_at(
            known_at, known_at=known_at, applicability=applicability
        )


def _metadata(
    decision: InvestmentDecision | None,
    decision_id: InvestmentDecisionId,
    context: DecisionMutationContext,
) -> DecisionLifecycleFactMetadata:
    sequence = (
        1 if decision is None else decision.history[-1].metadata.sequence.value + 1
    )
    version = 1 if decision is None else decision.version.value + 1
    return DecisionLifecycleFactMetadata(
        context.fact_id,
        decision_id,
        DecisionLifecycleSequence(sequence),
        DecisionVersion(version),
        context.operation_id,
        context.actor_attribution,
        context.trigger,
        context.technical_provenance,
        context.effective_at,
        context.recorded_at,
    )


def _same_choice(decision: InvestmentDecision, continuity: DecisionContinuity) -> None:
    if continuity is DecisionContinuity.INDEPENDENT_CHOICE:
        raise IndependentChoiceRequiresNewDecision(decision.decision_id)
    if continuity is not DecisionContinuity.SAME_COHERENT_CHOICE:
        raise InvalidDecisionTransition("requested change must classify continuity")


def _require_unresolved(decision: InvestmentDecision) -> None:
    if decision.disposition is not DecisionLifecycleDisposition.UNRESOLVED:
        raise InvalidDecisionTransition(
            "resolved Decision cannot receive ordinary work"
        )


def _require_operative(applicability: DecisionApplicability) -> None:
    if type(applicability) is not DecisionApplicability:
        raise InvalidDecisionTransition("Decision applicability is invalid")
    if applicability is DecisionApplicability.CONTESTED:
        raise DecisionApplicabilityContested(
            "ordinary Decision work requires determinate operative applicability"
        )
    if applicability is DecisionApplicability.NON_OPERATIVE:
        raise DecisionNotOperative("ordinary Decision work requires operative status")


def _require_human_effect(
    basis: TrustedHumanInvestmentDecisionBasis,
    expected: HumanInvestmentDecisionEffect,
) -> None:
    if type(basis) is not TrustedHumanInvestmentDecisionBasis:
        raise InvalidDecisionBasis(
            "operation requires a trusted Human Investment Decision basis"
        )
    if basis.effect is not expected:
        raise InvalidDecisionBasis(
            f"Human Investment Decision basis must have {expected.value} effect"
        )


def initiate_decision(
    *,
    decision_id: InvestmentDecisionId,
    need: DecisionNeed,
    subject: DecisionSubject,
    scope: DecisionScope,
    continuity: DecisionInitiationContinuity,
    mutation: DecisionMutationContext,
    existing_decision_for_need: InvestmentDecisionId | None = None,
) -> InvestmentDecision:
    _exact(decision_id, InvestmentDecisionId, "decision_id")
    if not isinstance(need, DecisionNeed):
        raise InvalidDecisionNeed("need must be DecisionNeed")
    _known_actor(need.actor_attribution)
    if existing_decision_for_need is not None:
        _exact(
            existing_decision_for_need,
            InvestmentDecisionId,
            "existing_decision_for_need",
        )
        raise DecisionNeedAlreadyGrounded(need.need_id, existing_decision_for_need)
    fact = DecisionInitiated(
        _metadata(None, decision_id, mutation), need, subject, scope, continuity
    )
    return reconstruct_decision(
        (fact,),
        observed_at=mutation.recorded_at,
        applicability=DecisionApplicability.OPERATIVE,
    )


def revise_subject(
    decision: InvestmentDecision,
    *,
    subject: DecisionSubject,
    continuity: DecisionContinuity,
    applicability: DecisionApplicability,
    mutation: DecisionMutationContext,
) -> InvestmentDecision:
    decision = _at_recording(decision, mutation, applicability)
    if subject == decision.subject:
        return decision
    _require_unresolved(decision)
    _require_operative(applicability)
    _same_choice(decision, continuity)
    fact = DecisionSubjectRevised(
        _metadata(decision, decision.decision_id, mutation), subject
    )
    return _append_ordinary(decision, fact, mutation)


def establish_or_revise_scope(
    decision: InvestmentDecision,
    *,
    scope: DecisionScope,
    continuity: DecisionContinuity,
    applicability: DecisionApplicability,
    mutation: DecisionMutationContext,
) -> InvestmentDecision:
    decision = _at_recording(decision, mutation, applicability)
    if scope == decision.scope:
        return decision
    _require_unresolved(decision)
    _require_operative(applicability)
    _same_choice(decision, continuity)
    if _established_to_unresolved(decision.scope, scope):
        raise InvalidDecisionTransition(
            "Established Decision Scope cannot become unresolved through ordinary "
            "revision"
        )
    meta = _metadata(decision, decision.decision_id, mutation)
    fact: DecisionLifecycleFact
    if _unresolved_to_established(decision.scope, scope):
        fact = DecisionScopeEstablished(meta, scope)
    else:
        fact = DecisionScopeRevised(meta, scope)
    return _append_ordinary(decision, fact, mutation)


def defer_decision(
    decision: InvestmentDecision,
    *,
    basis: TrustedHumanInvestmentDecisionBasis,
    applicability: DecisionApplicability,
    mutation: DecisionMutationContext,
) -> InvestmentDecision:
    decision = _at_recording(decision, mutation, applicability)
    _require_unresolved(decision)
    _require_operative(applicability)
    _require_human_effect(basis, HumanInvestmentDecisionEffect.DEFERRING)
    fact = DecisionDeferred(
        _metadata(decision, decision.decision_id, mutation),
        basis,
    )
    return _append_ordinary(decision, fact, mutation)


def withdraw_decision_work(
    decision: InvestmentDecision,
    *,
    basis: DecisionWorkControlBasis,
    applicability: DecisionApplicability,
    mutation: DecisionMutationContext,
) -> InvestmentDecision:
    decision = _at_recording(decision, mutation, applicability)
    _require_unresolved(decision)
    _require_operative(applicability)
    if type(basis) is not DecisionWorkControlBasis:
        raise InvalidDecisionBasis("work withdrawal requires a work-control basis")
    if decision.work_posture is DecisionWorkPosture.WITHDRAWN:
        raise InvalidDecisionTransition("Decision work is already withdrawn")
    fact = DecisionWorkWithdrawn(
        _metadata(decision, decision.decision_id, mutation),
        basis,
    )
    return _append_ordinary(decision, fact, mutation)


def resume_decision_work(
    decision: InvestmentDecision,
    *,
    basis: DecisionWorkControlBasis,
    continuity: DecisionContinuity,
    applicability: DecisionApplicability,
    mutation: DecisionMutationContext,
) -> InvestmentDecision:
    decision = _at_recording(decision, mutation, applicability)
    _require_unresolved(decision)
    _require_operative(applicability)
    _same_choice(decision, continuity)
    if type(basis) is not DecisionWorkControlBasis:
        raise InvalidDecisionBasis("work resumption requires a work-control basis")
    if decision.work_posture not in (
        DecisionWorkPosture.DEFERRED,
        DecisionWorkPosture.WITHDRAWN,
    ):
        raise InvalidDecisionTransition("only deferred or withdrawn work may resume")
    fact = DecisionWorkResumed(
        _metadata(decision, decision.decision_id, mutation),
        basis,
    )
    return _append_ordinary(decision, fact, mutation)


def substantively_resolve_decision(
    decision: InvestmentDecision,
    *,
    basis: TrustedHumanInvestmentDecisionBasis,
    applicability: DecisionApplicability,
    mutation: DecisionMutationContext,
) -> InvestmentDecision:
    decision = _at_recording(decision, mutation, applicability)
    _require_unresolved(decision)
    _require_operative(applicability)
    _require_human_effect(
        basis,
        HumanInvestmentDecisionEffect.SUBSTANTIVELY_RESOLVING,
    )
    fact = DecisionSubstantivelyResolved(
        _metadata(decision, decision.decision_id, mutation),
        basis,
    )
    return _append_ordinary(decision, fact, mutation)


def externally_resolve_decision(
    decision: InvestmentDecision,
    *,
    basis: ExternalResolutionBasis,
    mutation: DecisionMutationContext,
) -> InvestmentDecision:
    decision = _at_recording(decision, mutation, decision._applicability)
    _require_unresolved(decision)
    if type(basis) is not ExternalResolutionBasis:
        raise InvalidDecisionBasis(
            "External Resolution requires an attributable external basis"
        )
    fact = DecisionExternallyResolved(
        _metadata(decision, decision.decision_id, mutation),
        basis,
    )
    return _append_ordinary(decision, fact, mutation)


def reconstruct_decision(
    history: Iterable[DecisionLifecycleFact],
    *,
    observed_at: datetime,
    applicability: DecisionApplicability,
) -> InvestmentDecision:
    """Validate immutable admission history, then observe it at supplied T=K."""
    facts = tuple(history)
    initiation = _history_start(facts)
    _validate_metadata(facts, initiation.metadata.decision_id)
    _validate_initiation(initiation)
    for index, fact in enumerate(facts[1:], 1):
        prefix = facts[:index]
        if isinstance(fact, DecisionLifecycleCorrected):
            _validate_correction(prefix, fact)
        else:
            try:
                _admit_ordinary(prefix, fact)
            except InvalidDecisionTransition as error:
                raise InvalidDecisionHistory(str(error)) from error
    return _view(facts, observed_at, observed_at, applicability)


def _view(
    facts: tuple[DecisionLifecycleFact, ...],
    effective_at: datetime,
    known_at: datetime,
    applicability: DecisionApplicability,
) -> InvestmentDecision:
    if type(applicability) is not DecisionApplicability:
        raise InvalidDecisionTransition("Decision applicability is invalid")
    interpretation = _interpret(facts, effective_at, known_at)
    first = facts[0]
    assert isinstance(first, DecisionInitiated)
    subject, scope = first.subject, first.scope
    known = tuple(f for f in facts if f.metadata.recorded_at <= known_at)
    for fact in sorted(
        known, key=lambda f: (f.metadata.effective_at, f.metadata.sequence)
    ):
        if fact.metadata.effective_at > effective_at:
            continue
        if isinstance(fact, DecisionSubjectRevised):
            subject = fact.subject
        elif isinstance(fact, (DecisionScopeEstablished, DecisionScopeRevised)):
            scope = fact.scope
    posture = (
        _posture(known, interpretation)
        if applicability is DecisionApplicability.OPERATIVE
        else None
    )
    return InvestmentDecision._from_validated(
        facts,
        subject,
        scope,
        known[-1].metadata.decision_version,
        interpretation,
        applicability,
        posture,
    )


def _at_recording(
    decision: InvestmentDecision,
    mutation: DecisionMutationContext,
    applicability: DecisionApplicability,
) -> InvestmentDecision:
    if mutation.recorded_at < decision._history[-1].metadata.recorded_at:
        raise InvalidDecisionHistory("recorded_at must be non-decreasing")
    view = _view(
        decision._history, mutation.recorded_at, mutation.recorded_at, applicability
    )
    if view.version.value >= decision.version.value:
        return view
    return InvestmentDecision._from_validated(
        view._history,
        view._subject,
        view._scope,
        decision.version,
        view.lifecycle_interpretation,
        view._applicability,
        view._work_posture,
    )


def _append_ordinary(
    decision: InvestmentDecision,
    fact: DecisionLifecycleFact,
    mutation: DecisionMutationContext,
) -> InvestmentDecision:
    _admit_ordinary(decision._history, fact)
    return reconstruct_decision(
        (*decision._history, fact),
        observed_at=mutation.recorded_at,
        applicability=decision._applicability,
    )


def _admit_ordinary(
    prefix: tuple[DecisionLifecycleFact, ...],
    fact: DecisionLifecycleFact,
) -> None:
    """Strict sequence prefix, even when recorded timestamps are equal."""
    meta = fact.metadata
    for instant in {meta.recorded_at, meta.effective_at}:
        view = _view(prefix, instant, meta.recorded_at, DecisionApplicability.OPERATIVE)
        _require_unresolved(view)
        _validate_ordinary_payload(fact, view)
    # Piecewise-constant lifecycle interpretation changes only at known effective
    # boundaries. Test each affected interval, including already-known futures.
    appended = (*prefix, fact)
    boundaries = {f.metadata.effective_at for f in appended}
    for instant in boundaries:
        if instant < meta.effective_at:
            continue
        after = _interpret(appended, instant, meta.recorded_at)
        if isinstance(after, ContestedDecisionLifecycleInterpretation) and (
            after != _interpret(prefix, instant, meta.recorded_at)
        ):
            raise InvalidDecisionTransition(
                "ordinary act introduces incompatible lifecycle"
            )


def _validate_ordinary_payload(
    fact: DecisionLifecycleFact, view: InvestmentDecision
) -> None:
    if isinstance(fact, DecisionSubjectRevised):
        if type(fact.subject) is not DecisionSubject or fact.subject == view.subject:
            raise InvalidDecisionHistory("invalid or no-op Subject revision")
    elif isinstance(fact, DecisionScopeEstablished):
        _replay_establishment(view.scope, fact)
    elif isinstance(fact, DecisionScopeRevised):
        _replay_scope_revision(view.scope, fact)
    else:
        _replay_lifecycle_fact(fact, view.disposition, view.work_posture)


def correct_decision_lifecycle(
    decision: InvestmentDecision,
    *,
    target_fact_id: DecisionLifecycleFactId,
    effect: DecisionLifecycleCorrectionEffect,
    correction_basis: DecisionLifecycleCorrectionBasis,
    mutation: DecisionMutationContext,
    applicability: DecisionApplicability,
    replacement_disposition: DecisionLifecycleDisposition | None = None,
    replacement_basis: (
        TrustedHumanInvestmentDecisionBasis
        | ExternalResolutionBasis
        | UnsupportedDecisionNeedBasis
        | None
    ) = None,
) -> InvestmentDecision:
    """Append a distinct correction act; Application owns exact replay receipts.

    Corrections bypass ordinary lifecycle/applicability gates. Support changes at
    this one recording boundary determine the committed version consequence.
    """
    decision = _at_recording(decision, mutation, applicability)
    meta = _metadata(decision, decision.decision_id, mutation)
    fact = DecisionLifecycleCorrected(
        meta,
        target_fact_id,
        effect,
        correction_basis,
        replacement_disposition,
        replacement_basis,
    )
    _validate_correction_target(decision._history, fact)
    before = decision.lifecycle_interpretation
    after = _interpret(
        (*decision._history, fact), mutation.recorded_at, mutation.recorded_at
    )
    version = DecisionVersion(decision.version.value + (before != after))
    fact = replace(fact, metadata=replace(meta, decision_version=version))
    return reconstruct_decision(
        (*decision._history, fact),
        observed_at=mutation.recorded_at,
        applicability=applicability,
    )


def _validate_correction_target(
    prefix: tuple[DecisionLifecycleFact, ...],
    fact: DecisionLifecycleCorrected,
) -> None:
    eligible = (
        DecisionInitiated,
        DecisionSubstantivelyResolved,
        DecisionExternallyResolved,
        DecisionLifecycleCorrected,
    )
    by_id = {f.metadata.fact_id: f for f in prefix}
    target = by_id.get(fact.target_fact_id)
    if not isinstance(target, eligible):
        raise InvalidDecisionLifecycleCorrection(
            "target must be an earlier same-Decision eligible fact"
        )
    if (
        isinstance(target, DecisionInitiated)
        and fact.effect is DecisionLifecycleCorrectionEffect.DISCONFIRM
    ):
        raise InvalidDecisionLifecycleCorrection(
            "cannot directly disconfirm initiation"
        )
    root: DecisionLifecycleFact = target
    while isinstance(root, DecisionLifecycleCorrected):
        root = by_id[root.target_fact_id]
    if (
        fact.replacement_disposition
        is DecisionLifecycleDisposition.NEED_RETRACTED_UNSUPPORTED
        and not isinstance(root, DecisionInitiated)
    ):
        raise InvalidDecisionLifecycleCorrection(
            "unsupported Need correction requires initiation lineage"
        )


def _validate_correction(
    prefix: tuple[DecisionLifecycleFact, ...],
    fact: DecisionLifecycleCorrected,
) -> None:
    _validate_correction_target(prefix, fact)
    instant = fact.metadata.recorded_at
    before = _interpret(prefix, instant, instant)
    after = _interpret((*prefix, fact), instant, instant)
    minimum = prefix[-1].metadata.decision_version.value + (before != after)
    if fact.metadata.decision_version.value < minimum:
        raise InvalidDecisionHistory(
            "correction version must preserve aggregate DecisionVersion and "
            "advance when current interpretation changes"
        )


def _history_start(facts: tuple[DecisionLifecycleFact, ...]) -> DecisionInitiated:
    if not facts or type(facts[0]) is not DecisionInitiated:
        raise InvalidDecisionHistory(
            "Decision history must start with DecisionInitiated"
        )
    supported = (
        DecisionInitiated,
        DecisionSubjectRevised,
        DecisionScopeEstablished,
        DecisionScopeRevised,
        DecisionDeferred,
        DecisionWorkWithdrawn,
        DecisionWorkResumed,
        DecisionSubstantivelyResolved,
        DecisionExternallyResolved,
        DecisionLifecycleCorrected,
    )
    if any(not isinstance(fact, supported) for fact in facts):
        raise InvalidDecisionHistory("Decision history contains unsupported fact type")
    initiation = facts[0]
    assert isinstance(initiation, DecisionInitiated)
    return initiation


def _validate_metadata(
    facts: tuple[DecisionLifecycleFact, ...],
    decision_id: InvestmentDecisionId,
) -> None:
    ids: set[DecisionLifecycleFactId] = set()
    previous_version = 0
    for index, fact in enumerate(facts):
        meta = fact.metadata
        _validate_meta_types(meta)
        if meta.decision_id != decision_id:
            raise InvalidDecisionHistory(
                "All lifecycle facts must reference the same Investment Decision"
            )
        if meta.fact_id in ids:
            raise InvalidDecisionHistory("Lifecycle fact IDs must be unique")
        ids.add(meta.fact_id)
        if meta.sequence.value != index + 1:
            raise InvalidDecisionHistory(
                "Lifecycle fact sequence must remain contiguous"
            )
        if index == 0 and meta.decision_version.value != 1:
            raise InvalidDecisionHistory("Decision initiation version must be 1")
        if index and meta.decision_version.value < previous_version:
            raise InvalidDecisionHistory("Decision versions must be non-decreasing")
        if index and type(fact) is DecisionInitiated:
            raise InvalidDecisionHistory("Decision history may contain one initiation")
        if index and meta.recorded_at < facts[index - 1].metadata.recorded_at:
            raise InvalidDecisionHistory("recorded_at must be non-decreasing")
        previous_version = meta.decision_version.value


def _validate_meta_types(meta: object) -> None:
    if type(meta) is not DecisionLifecycleFactMetadata:
        raise InvalidDecisionHistory("fact metadata is invalid")
    _exact(meta.fact_id, DecisionLifecycleFactId, "fact_id")
    _exact(meta.decision_id, InvestmentDecisionId, "decision_id")
    _exact(meta.operation_id, OperationId, "operation_id")
    if type(meta.sequence) is not DecisionLifecycleSequence:
        raise InvalidDecisionHistory("sequence must be DecisionLifecycleSequence")
    if type(meta.decision_version) is not DecisionVersion:
        raise InvalidDecisionHistory("decision_version must be DecisionVersion")
    _actor(meta.actor_attribution)
    if type(meta.trigger) is not TriggerProvenance:
        raise InvalidDecisionHistory("trigger must be TriggerProvenance")
    if type(meta.technical_provenance) is not TechnicalProvenance:
        raise InvalidDecisionHistory("technical_provenance must be TechnicalProvenance")
    _aware(meta.effective_at, "effective_at")
    _aware(meta.recorded_at, "recorded_at")


def _replay_lifecycle_fact(
    fact: DecisionLifecycleFact,
    disposition: DecisionLifecycleDisposition,
    work_posture: DecisionWorkPosture | None,
) -> tuple[DecisionLifecycleDisposition, DecisionWorkPosture | None]:
    if disposition is not DecisionLifecycleDisposition.UNRESOLVED:
        raise InvalidDecisionHistory("resolved Decision cannot receive ordinary work")
    if isinstance(fact, DecisionDeferred):
        _validate_deferred_fact(fact)
        return disposition, DecisionWorkPosture.DEFERRED
    if isinstance(fact, DecisionWorkWithdrawn):
        _validate_work_withdrawn_fact(fact, work_posture)
        return disposition, DecisionWorkPosture.WITHDRAWN
    if isinstance(fact, DecisionWorkResumed):
        _validate_work_resumed_fact(fact, work_posture)
        return disposition, DecisionWorkPosture.ACTIVE
    if isinstance(fact, DecisionSubstantivelyResolved):
        _validate_substantive_resolution_fact(fact)
        return DecisionLifecycleDisposition.SUBSTANTIVELY_RESOLVED, None
    if isinstance(fact, DecisionExternallyResolved):
        _validate_external_resolution_fact(fact)
        return DecisionLifecycleDisposition.EXTERNALLY_RESOLVED, None
    raise InvalidDecisionHistory("unsupported lifecycle fact")


def _validate_deferred_fact(fact: DecisionDeferred) -> None:
    try:
        _require_human_effect(fact.basis, HumanInvestmentDecisionEffect.DEFERRING)
    except InvalidDecisionBasis as error:
        raise InvalidDecisionHistory(str(error)) from error


def _validate_work_withdrawn_fact(
    fact: DecisionWorkWithdrawn,
    work_posture: DecisionWorkPosture | None,
) -> None:
    if type(fact.basis) is not DecisionWorkControlBasis:
        raise InvalidDecisionHistory("work withdrawal basis is invalid")
    if work_posture is DecisionWorkPosture.WITHDRAWN:
        raise InvalidDecisionHistory("Decision work is already withdrawn")


def _validate_work_resumed_fact(
    fact: DecisionWorkResumed,
    work_posture: DecisionWorkPosture | None,
) -> None:
    if type(fact.basis) is not DecisionWorkControlBasis:
        raise InvalidDecisionHistory("work resumption basis is invalid")
    if work_posture not in (
        DecisionWorkPosture.DEFERRED,
        DecisionWorkPosture.WITHDRAWN,
    ):
        raise InvalidDecisionHistory("only deferred or withdrawn work may resume")


def _validate_substantive_resolution_fact(
    fact: DecisionSubstantivelyResolved,
) -> None:
    try:
        _require_human_effect(
            fact.basis,
            HumanInvestmentDecisionEffect.SUBSTANTIVELY_RESOLVING,
        )
    except InvalidDecisionBasis as error:
        raise InvalidDecisionHistory(str(error)) from error


def _validate_external_resolution_fact(fact: DecisionExternallyResolved) -> None:
    if type(fact.basis) is not ExternalResolutionBasis:
        raise InvalidDecisionHistory("External Resolution basis is invalid")


def _validate_initiation(fact: DecisionInitiated) -> None:
    if type(fact.need) is not DecisionNeed:
        raise InvalidDecisionHistory("initiation need is invalid")
    if type(fact.subject) is not DecisionSubject:
        raise InvalidDecisionHistory("initiation subject is invalid")
    if type(fact.scope) is not DecisionScope:
        raise InvalidDecisionHistory("initiation scope is invalid")
    if type(fact.continuity) is not DecisionInitiationContinuity:
        raise InvalidDecisionHistory("initiation continuity is invalid")


def _replay_establishment(
    current: DecisionScope, fact: DecisionScopeEstablished
) -> DecisionScope:
    if type(fact.scope) is not DecisionScope:
        raise InvalidDecisionHistory("Scope establishment is invalid")
    if current.completeness is not DecisionScopeCompleteness.UNRESOLVED:
        raise InvalidDecisionHistory("Scope can be established only once")
    if fact.scope.completeness is not DecisionScopeCompleteness.ESTABLISHED:
        raise InvalidDecisionHistory(
            "DecisionScopeEstablished requires ESTABLISHED Scope"
        )
    return fact.scope


def _replay_scope_revision(
    current: DecisionScope, fact: DecisionScopeRevised
) -> DecisionScope:
    if type(fact.scope) is not DecisionScope or fact.scope == current:
        raise InvalidDecisionHistory("invalid or no-op Scope revision")
    if _established_to_unresolved(current, fact.scope):
        raise InvalidDecisionHistory("Established Scope cannot become unresolved")
    if _unresolved_to_established(current, fact.scope):
        raise InvalidDecisionHistory(
            "First Scope establishment must use DecisionScopeEstablished"
        )
    return fact.scope


def _established_to_unresolved(current: DecisionScope, new: DecisionScope) -> bool:
    return (
        current.completeness is DecisionScopeCompleteness.ESTABLISHED
        and new.completeness is DecisionScopeCompleteness.UNRESOLVED
    )


def _unresolved_to_established(current: DecisionScope, new: DecisionScope) -> bool:
    return (
        current.completeness is DecisionScopeCompleteness.UNRESOLVED
        and new.completeness is DecisionScopeCompleteness.ESTABLISHED
    )


@dataclass(frozen=True, slots=True)
class DecisionReconciliationRequired:
    need_id: DecisionNeedId
    decision_ids: frozenset[InvestmentDecisionId]


def find_reconciliation_requirements(
    decisions: Iterable[InvestmentDecision],
) -> tuple[DecisionReconciliationRequired, ...]:
    by_need: dict[DecisionNeedId, set[InvestmentDecisionId]] = {}
    for decision in decisions:
        by_need.setdefault(decision.need_id, set()).add(decision.decision_id)
    conflicts = (
        DecisionReconciliationRequired(need_id, frozenset(ids))
        for need_id, ids in by_need.items()
        if len(ids) > 1
    )
    return tuple(sorted(conflicts, key=lambda item: item.need_id.value.int))
