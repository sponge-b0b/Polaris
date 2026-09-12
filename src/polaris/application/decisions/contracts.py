from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol

from polaris.domain.actors import ActorAttribution, KnownActorAttribution
from polaris.domain.decisions import (
    DecisionNeedId,
    DecisionScope,
    DecisionSubject,
    DecisionVersion,
    InvestmentDecision,
    InvestmentDecisionId,
    OperationId,
    TechnicalProvenance,
    TriggerProvenance,
)


class DecisionApplicationError(Exception):
    """Base class for Investment Decision application-boundary failures."""


class InvalidDecisionCommand(DecisionApplicationError):
    pass


@dataclass(slots=True)
class ContinuityAmbiguous(DecisionApplicationError):
    candidate_decision_ids: frozenset[InvestmentDecisionId]


@dataclass(slots=True)
class ContinuityConflict(DecisionApplicationError):
    candidate_decision_ids: frozenset[InvestmentDecisionId]


@dataclass(slots=True)
class IdempotencyConflict(DecisionApplicationError):
    operation_id: OperationId


@dataclass(slots=True)
class DecisionNeedGroundingConflict(DecisionApplicationError):
    existing_decision_id: InvestmentDecisionId


class ConcurrencyConflict(DecisionApplicationError):
    pass


class LifecycleConflict(DecisionApplicationError):
    pass


class RelationshipConflict(DecisionApplicationError):
    pass


class RelationshipCycle(RelationshipConflict):
    pass


class RelationshipCycleSafetyIndeterminate(RelationshipConflict):
    pass


class RelationshipHistoryInvalidOrIncomplete(RelationshipConflict):
    pass


class PersistenceUnavailable(DecisionApplicationError):
    pass


@dataclass(frozen=True, slots=True)
class ExpectedDecisionVersion:
    decision_id: InvestmentDecisionId
    version: DecisionVersion

    def __post_init__(self) -> None:
        if type(self.decision_id) is not InvestmentDecisionId:
            raise TypeError("decision_id must be InvestmentDecisionId")
        if type(self.version) is not DecisionVersion:
            raise TypeError("version must be DecisionVersion")


@dataclass(frozen=True, slots=True)
class DecisionCommandEnvelope:
    operation_id: OperationId
    actor_attribution: ActorAttribution
    trigger: TriggerProvenance
    effective_at: datetime
    technical_provenance: TechnicalProvenance
    expected_versions: frozenset[ExpectedDecisionVersion] = frozenset()

    def __post_init__(self) -> None:
        if type(self.operation_id) is not OperationId:
            raise TypeError("operation_id must be OperationId")
        if not isinstance(self.actor_attribution, ActorAttribution):
            raise TypeError("actor_attribution must be ActorAttribution")
        if type(self.trigger) is not TriggerProvenance:
            raise TypeError("trigger must be TriggerProvenance")
        if type(self.technical_provenance) is not TechnicalProvenance:
            raise TypeError("technical_provenance must be TechnicalProvenance")
        if (
            not isinstance(self.effective_at, datetime)
            or self.effective_at.tzinfo is None
            or self.effective_at.utcoffset() is None
        ):
            raise ValueError("effective_at must be timezone-aware")
        if type(self.expected_versions) is not frozenset or any(
            type(item) is not ExpectedDecisionVersion for item in self.expected_versions
        ):
            raise TypeError(
                "expected_versions must be frozenset[ExpectedDecisionVersion]"
            )


class ContinuityDeterminationKind(StrEnum):
    CONTINUE_EXISTING = "continue_existing"
    CREATE_NEW = "create_new"


@dataclass(frozen=True, slots=True)
class ContinuityDetermination:
    kind: ContinuityDeterminationKind
    decision_id: InvestmentDecisionId | None = None
    rationale: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, ContinuityDeterminationKind):
            raise TypeError("kind must be ContinuityDeterminationKind")
        clean = self.rationale.strip() if isinstance(self.rationale, str) else None
        if self.kind is ContinuityDeterminationKind.CONTINUE_EXISTING:
            if type(self.decision_id) is not InvestmentDecisionId:
                raise InvalidDecisionCommand(
                    "CONTINUE_EXISTING requires an InvestmentDecisionId"
                )
            if clean is not None:
                raise InvalidDecisionCommand(
                    "CONTINUE_EXISTING does not accept a create-new rationale"
                )
        else:
            if self.decision_id is not None:
                raise InvalidDecisionCommand(
                    "CREATE_NEW cannot carry an existing Decision identity"
                )
            if self.rationale is not None and not clean:
                raise InvalidDecisionCommand("create-new rationale cannot be empty")
        object.__setattr__(self, "rationale", clean)

    @classmethod
    def continue_existing(
        cls, decision_id: InvestmentDecisionId
    ) -> ContinuityDetermination:
        return cls(ContinuityDeterminationKind.CONTINUE_EXISTING, decision_id)

    @classmethod
    def create_new(cls, rationale: str | None = None) -> ContinuityDetermination:
        return cls(ContinuityDeterminationKind.CREATE_NEW, rationale=rationale)


@dataclass(frozen=True, slots=True)
class InitiateDecisionCommand:
    envelope: DecisionCommandEnvelope
    need_statement: str
    subject: DecisionSubject
    scope: DecisionScope
    continuity: ContinuityDetermination | None = None

    def __post_init__(self) -> None:
        if type(self.envelope) is not DecisionCommandEnvelope:
            raise TypeError("envelope must be DecisionCommandEnvelope")
        if type(self.envelope.actor_attribution) is not KnownActorAttribution:
            raise InvalidDecisionCommand(
                "Decision initiation requires known Actor Attribution"
            )
        if not isinstance(self.need_statement, str) or not self.need_statement.strip():
            raise InvalidDecisionCommand("need_statement must be a non-empty string")
        if type(self.subject) is not DecisionSubject:
            raise TypeError("subject must be DecisionSubject")
        if type(self.scope) is not DecisionScope:
            raise TypeError("scope must be DecisionScope")
        if (
            self.continuity is not None
            and type(self.continuity) is not ContinuityDetermination
        ):
            raise TypeError("continuity must be ContinuityDetermination or None")
        object.__setattr__(self, "need_statement", self.need_statement.strip())


@dataclass(frozen=True, slots=True)
class InitiationSemanticRequest:
    actor_attribution: KnownActorAttribution
    trigger: TriggerProvenance
    effective_at: datetime
    expected_versions: frozenset[ExpectedDecisionVersion]
    need_statement: str
    subject: DecisionSubject
    scope: DecisionScope
    continuity: ContinuityDetermination | None

    @classmethod
    def from_command(
        cls, command: InitiateDecisionCommand
    ) -> InitiationSemanticRequest:
        envelope = command.envelope
        assert type(envelope.actor_attribution) is KnownActorAttribution
        return cls(
            actor_attribution=envelope.actor_attribution,
            trigger=envelope.trigger,
            effective_at=envelope.effective_at,
            expected_versions=envelope.expected_versions,
            need_statement=command.need_statement,
            subject=command.subject,
            scope=command.scope,
            continuity=command.continuity,
        )


@dataclass(frozen=True, slots=True)
class ContinuityCandidateBasis:
    candidate_decision_ids: frozenset[InvestmentDecisionId]
    known_at: datetime

    def __post_init__(self) -> None:
        if type(self.candidate_decision_ids) is not frozenset or any(
            type(value) is not InvestmentDecisionId
            for value in self.candidate_decision_ids
        ):
            raise TypeError(
                "candidate_decision_ids must be frozenset[InvestmentDecisionId]"
            )
        if (
            not isinstance(self.known_at, datetime)
            or self.known_at.tzinfo is None
            or self.known_at.utcoffset() is None
        ):
            raise ValueError("known_at must be timezone-aware")


class InitiationResultKind(StrEnum):
    CREATED = "created"
    CONTINUED = "continued"


@dataclass(frozen=True, slots=True)
class InitiationResult:
    decision_id: InvestmentDecisionId
    need_id: DecisionNeedId | None
    kind: InitiationResultKind
    replayed: bool = False


@dataclass(frozen=True, slots=True)
class InitiationReceipt:
    operation_id: OperationId
    request: InitiationSemanticRequest
    result: InitiationResult


@dataclass(frozen=True, slots=True)
class InitiationCommit:
    operation_id: OperationId
    request: InitiationSemanticRequest
    candidate_basis: ContinuityCandidateBasis
    result: InitiationResult
    decision: InvestmentDecision | None


@dataclass(frozen=True, slots=True)
class InitiationCommitted:
    receipt: InitiationReceipt


@dataclass(frozen=True, slots=True)
class InitiationReplayed:
    receipt: InitiationReceipt


@dataclass(frozen=True, slots=True)
class InitiationIdempotencyConflict:
    operation_id: OperationId


@dataclass(frozen=True, slots=True)
class InitiationContinuityConflict:
    candidate_decision_ids: frozenset[InvestmentDecisionId]


@dataclass(frozen=True, slots=True)
class InitiationNeedAlreadyGrounded:
    existing_decision_id: InvestmentDecisionId


@dataclass(frozen=True, slots=True)
class InitiationUnavailable:
    reason: str


InitiationCommitOutcome = (
    InitiationCommitted
    | InitiationReplayed
    | InitiationIdempotencyConflict
    | InitiationContinuityConflict
    | InitiationNeedAlreadyGrounded
    | InitiationUnavailable
)


class DecisionMemoryReader(Protocol):
    async def find_unresolved_continuity_candidates(
        self, *, known_at: datetime
    ) -> tuple[InvestmentDecisionId, ...]: ...


class DecisionCommandStore(Protocol):
    async def get_initiation_receipt(
        self, operation_id: OperationId
    ) -> InitiationReceipt | None: ...

    async def commit_initiation(
        self, commit: InitiationCommit
    ) -> InitiationCommitOutcome: ...
