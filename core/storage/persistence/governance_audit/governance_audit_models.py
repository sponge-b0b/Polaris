from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from hashlib import sha256
from uuid import uuid4

from domain.authority import RiskAuthorityContract, RiskTier

type JsonValue = object
type JsonObject = Mapping[str, object]


class AutomatedPolicyAuditOutcome(StrEnum):
    """First-class persisted automated policy decision states."""

    ALLOW = "allow"
    WARN = "warn"
    DENY = "deny"
    SKIP = "skip"


class AutomatedGovernanceAuditOutcome(StrEnum):
    """First-class persisted automated governance recommendation states."""

    ALLOW = "allow"
    WARN = "warn"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"
    SKIP = "skip"


class GovernanceReviewTaskStatus(StrEnum):
    """Durable states for human governance review work items."""

    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    DENIED = "denied"
    CONTESTED = "contested"
    CHANGES_REQUESTED = "changes_requested"
    OVERRIDDEN = "overridden"
    CANCELLED = "cancelled"


class GovernanceReviewDecisionOutcome(StrEnum):
    """Immutable human review outcomes for governance review tasks."""

    APPROVED = "approved"
    DENIED = "denied"
    CONTESTED = "contested"
    CHANGES_REQUESTED = "changes_requested"
    OVERRIDDEN = "overridden"


class GovernanceReviewerActorType(StrEnum):
    """Actor categories allowed to author human governance review records."""

    HUMAN_REVIEWER = "human_reviewer"
    ORGANIZATION_REVIEWER = "organization_reviewer"


@dataclass(frozen=True, slots=True)
class AutomatedDecisionSubject:
    """Stable subject identity for an automated audit decision."""

    subject_type: str
    subject_id: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "subject_type",
            _clean_identifier(self.subject_type, "subject_type"),
        )
        object.__setattr__(
            self,
            "subject_id",
            _clean_identifier(self.subject_id, "subject_id"),
        )


@dataclass(frozen=True, slots=True)
class AutomatedDecisionEvidenceReference:
    """Reference to the authoritative decision evidence packet/version."""

    packet_id: str
    packet_version: int

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "packet_id",
            _clean_identifier(self.packet_id, "packet_id"),
        )
        if self.packet_version < 1:
            raise ValueError("packet_version must be positive.")

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "packet_id": self.packet_id,
            "packet_version": self.packet_version,
        }


@dataclass(frozen=True, slots=True)
class AutomatedPolicyAuditRecord:
    """Authoritative PostgreSQL audit record for automated policy outcomes."""

    audit_record_id: str
    subject: AutomatedDecisionSubject
    risk_tier: RiskTier
    authority_metadata: JsonObject
    evidence: AutomatedDecisionEvidenceReference | None
    outcome: AutomatedPolicyAuditOutcome
    policy_name: str
    timestamp: datetime
    reason: str | None = None
    message: str = ""
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "audit_record_id",
            _clean_identifier(self.audit_record_id, "audit_record_id"),
        )
        object.__setattr__(self, "risk_tier", _coerce_risk_tier(self.risk_tier))
        object.__setattr__(
            self,
            "authority_metadata",
            _validate_authority_metadata(
                self.authority_metadata,
                risk_tier=self.risk_tier,
            ),
        )
        object.__setattr__(self, "outcome", _coerce_policy_outcome(self.outcome))
        object.__setattr__(
            self,
            "policy_name",
            _clean_identifier(self.policy_name, "policy_name"),
        )
        object.__setattr__(
            self,
            "reason",
            _clean_optional_text(self.reason, "reason"),
        )
        object.__setattr__(self, "message", self.message.strip())
        object.__setattr__(self, "metadata", _json_object(self.metadata))

    @property
    def subject_type(self) -> str:
        return self.subject.subject_type

    @property
    def subject_id(self) -> str:
        return self.subject.subject_id

    @property
    def evidence_packet_id(self) -> str | None:
        if self.evidence is None:
            return None
        return self.evidence.packet_id

    @property
    def evidence_packet_version(self) -> int | None:
        if self.evidence is None:
            return None
        return self.evidence.packet_version

    @property
    def outcome_value(self) -> str:
        return self.outcome.value


@dataclass(frozen=True, slots=True)
class AutomatedGovernanceAuditRecord:
    """Authoritative PostgreSQL audit record for automated governance outcomes."""

    audit_record_id: str
    subject: AutomatedDecisionSubject
    risk_tier: RiskTier
    authority_metadata: JsonObject
    evidence: AutomatedDecisionEvidenceReference | None
    outcome: AutomatedGovernanceAuditOutcome
    rule_name: str
    timestamp: datetime
    reason: str | None = None
    message: str = ""
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "audit_record_id",
            _clean_identifier(self.audit_record_id, "audit_record_id"),
        )
        object.__setattr__(self, "risk_tier", _coerce_risk_tier(self.risk_tier))
        object.__setattr__(
            self,
            "authority_metadata",
            _validate_authority_metadata(
                self.authority_metadata,
                risk_tier=self.risk_tier,
            ),
        )
        object.__setattr__(
            self,
            "outcome",
            _coerce_governance_outcome(self.outcome),
        )
        object.__setattr__(
            self,
            "rule_name",
            _clean_identifier(self.rule_name, "rule_name"),
        )
        object.__setattr__(
            self,
            "reason",
            _clean_optional_text(self.reason, "reason"),
        )
        object.__setattr__(self, "message", self.message.strip())
        object.__setattr__(self, "metadata", _json_object(self.metadata))

    @property
    def subject_type(self) -> str:
        return self.subject.subject_type

    @property
    def subject_id(self) -> str:
        return self.subject.subject_id

    @property
    def evidence_packet_id(self) -> str | None:
        if self.evidence is None:
            return None
        return self.evidence.packet_id

    @property
    def evidence_packet_version(self) -> int | None:
        if self.evidence is None:
            return None
        return self.evidence.packet_version

    @property
    def outcome_value(self) -> str:
        return self.outcome.value


@dataclass(frozen=True, slots=True)
class GovernanceReviewTaskRecord:
    """Durable human review work item for governance approval requirements."""

    review_task_id: str
    automated_governance_audit_record_id: str
    subject: AutomatedDecisionSubject
    risk_tier: RiskTier
    authority_metadata: JsonObject
    review_scope: str
    intended_sink: str
    requested_action: str
    status: GovernanceReviewTaskStatus
    evidence: AutomatedDecisionEvidenceReference
    evidence_references: JsonObject
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "review_task_id",
            _clean_identifier(self.review_task_id, "review_task_id"),
        )
        object.__setattr__(
            self,
            "automated_governance_audit_record_id",
            _clean_identifier(
                self.automated_governance_audit_record_id,
                "automated_governance_audit_record_id",
            ),
        )
        object.__setattr__(self, "risk_tier", _coerce_risk_tier(self.risk_tier))
        object.__setattr__(
            self,
            "authority_metadata",
            _validate_authority_metadata(
                self.authority_metadata,
                risk_tier=self.risk_tier,
            ),
        )
        object.__setattr__(
            self,
            "review_scope",
            _clean_identifier(self.review_scope, "review_scope"),
        )
        object.__setattr__(
            self,
            "intended_sink",
            _clean_identifier(self.intended_sink, "intended_sink"),
        )
        object.__setattr__(
            self,
            "requested_action",
            _clean_identifier(self.requested_action, "requested_action"),
        )
        object.__setattr__(
            self,
            "status",
            _coerce_review_task_status(self.status),
        )
        object.__setattr__(
            self,
            "evidence_references",
            _json_object(self.evidence_references),
        )

    @property
    def subject_type(self) -> str:
        return self.subject.subject_type

    @property
    def subject_id(self) -> str:
        return self.subject.subject_id

    @property
    def evidence_packet_id(self) -> str:
        return self.evidence.packet_id

    @property
    def evidence_packet_version(self) -> int:
        return self.evidence.packet_version

    @property
    def status_value(self) -> str:
        return self.status.value


@dataclass(frozen=True, slots=True)
class GovernanceReviewerIdentity:
    """Attributable reviewer identity for a human governance action."""

    reviewer_id: str
    actor_type: GovernanceReviewerActorType
    display_name: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "reviewer_id",
            _clean_identifier(self.reviewer_id, "reviewer_id"),
        )
        object.__setattr__(
            self,
            "actor_type",
            _coerce_reviewer_actor_type(self.actor_type),
        )
        object.__setattr__(
            self,
            "display_name",
            _clean_optional_text(self.display_name, "display_name"),
        )

    @property
    def actor_type_value(self) -> str:
        return self.actor_type.value


@dataclass(frozen=True, slots=True)
class GovernanceReviewDecisionRecord:
    """Immutable audit entry for attributable human review outcomes."""

    review_decision_id: str
    review_task_id: str
    automated_governance_audit_record_id: str
    subject: AutomatedDecisionSubject
    risk_tier: RiskTier
    outcome: GovernanceReviewDecisionOutcome
    reviewer: GovernanceReviewerIdentity
    rationale: str
    review_scope: str
    evidence: AutomatedDecisionEvidenceReference
    decided_at: datetime
    resulting_task_status: GovernanceReviewTaskStatus | None = None
    requested_remediation: str | None = None
    residual_risk_acceptance_required: bool = False
    residual_risk_acceptance_id: str | None = None
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "review_decision_id",
            _clean_identifier(self.review_decision_id, "review_decision_id"),
        )
        object.__setattr__(
            self,
            "review_task_id",
            _clean_identifier(self.review_task_id, "review_task_id"),
        )
        object.__setattr__(
            self,
            "automated_governance_audit_record_id",
            _clean_identifier(
                self.automated_governance_audit_record_id,
                "automated_governance_audit_record_id",
            ),
        )
        object.__setattr__(self, "risk_tier", _coerce_risk_tier(self.risk_tier))
        object.__setattr__(
            self,
            "outcome",
            _coerce_review_decision_outcome(self.outcome),
        )
        object.__setattr__(
            self,
            "rationale",
            _clean_identifier(self.rationale, "rationale"),
        )
        object.__setattr__(
            self,
            "review_scope",
            _clean_identifier(self.review_scope, "review_scope"),
        )
        expected_status = _review_task_status_for_decision_outcome(self.outcome)
        resulting_status = _coerce_review_task_status(
            self.resulting_task_status or expected_status,
        )
        if resulting_status is not expected_status:
            raise ValueError(
                "resulting_task_status must match the human review outcome.",
            )
        object.__setattr__(
            self,
            "resulting_task_status",
            resulting_status,
        )
        object.__setattr__(
            self,
            "requested_remediation",
            _clean_optional_text(
                self.requested_remediation,
                "requested_remediation",
            ),
        )
        object.__setattr__(
            self,
            "residual_risk_acceptance_id",
            _clean_optional_text(
                self.residual_risk_acceptance_id,
                "residual_risk_acceptance_id",
            ),
        )
        object.__setattr__(self, "metadata", _validated_review_metadata(self.metadata))
        if (
            self.residual_risk_acceptance_required
            and self.outcome
            in {
                GovernanceReviewDecisionOutcome.APPROVED,
                GovernanceReviewDecisionOutcome.OVERRIDDEN,
            }
            and self.residual_risk_acceptance_id is None
        ):
            raise ValueError(
                "approved or overridden vigilant review decisions with remaining "
                "residual risk require explicit residual-risk acceptance."
            )
        if (
            self.outcome
            in {
                GovernanceReviewDecisionOutcome.CONTESTED,
                GovernanceReviewDecisionOutcome.CHANGES_REQUESTED,
            }
            and self.requested_remediation is None
        ):
            raise ValueError(
                "contested and request-changes outcomes require requested remediation."
            )

    @property
    def subject_type(self) -> str:
        return self.subject.subject_type

    @property
    def subject_id(self) -> str:
        return self.subject.subject_id

    @property
    def evidence_packet_id(self) -> str:
        return self.evidence.packet_id

    @property
    def evidence_packet_version(self) -> int:
        return self.evidence.packet_version

    @property
    def outcome_value(self) -> str:
        return self.outcome.value

    @property
    def resulting_task_status_value(self) -> str:
        status = self.resulting_task_status
        if status is None:
            raise ValueError("resulting_task_status was not resolved.")
        return status.value


@dataclass(frozen=True, slots=True)
class GovernanceResidualRiskAcceptanceRecord:
    """Explicit scoped human acceptance of residual risk for one evidence version."""

    acceptance_id: str
    review_task_id: str
    subject: AutomatedDecisionSubject
    risk_tier: RiskTier
    reviewer: GovernanceReviewerIdentity
    rationale: str
    review_scope: str
    residual_risk_scope: str
    evidence: AutomatedDecisionEvidenceReference
    accepted_at: datetime
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "acceptance_id",
            _clean_identifier(self.acceptance_id, "acceptance_id"),
        )
        object.__setattr__(
            self,
            "review_task_id",
            _clean_identifier(self.review_task_id, "review_task_id"),
        )
        object.__setattr__(self, "risk_tier", _coerce_risk_tier(self.risk_tier))
        if self.risk_tier is not RiskTier.VIGILANT:
            raise ValueError(
                "residual-risk acceptance is only valid for vigilant reviews."
            )
        object.__setattr__(
            self,
            "rationale",
            _clean_identifier(self.rationale, "rationale"),
        )
        object.__setattr__(
            self,
            "review_scope",
            _clean_identifier(self.review_scope, "review_scope"),
        )
        object.__setattr__(
            self,
            "residual_risk_scope",
            _clean_identifier(self.residual_risk_scope, "residual_risk_scope"),
        )
        object.__setattr__(self, "metadata", _validated_review_metadata(self.metadata))

    @property
    def subject_type(self) -> str:
        return self.subject.subject_type

    @property
    def subject_id(self) -> str:
        return self.subject.subject_id

    @property
    def evidence_packet_id(self) -> str:
        return self.evidence.packet_id

    @property
    def evidence_packet_version(self) -> int:
        return self.evidence.packet_version


def governance_review_task_id(
    *,
    subject: AutomatedDecisionSubject,
    evidence: AutomatedDecisionEvidenceReference,
    review_scope: str,
    requested_action: str,
) -> str:
    """Build a stable idempotency key for one scoped evidence review."""

    fingerprint = "|".join(
        (
            subject.subject_type,
            subject.subject_id,
            evidence.packet_id,
            str(evidence.packet_version),
            _clean_identifier(review_scope, "review_scope"),
            _clean_identifier(requested_action, "requested_action"),
        )
    )
    digest = sha256(fingerprint.encode("utf-8")).hexdigest()[:32]
    return f"governance_review_task:{digest}"


@dataclass(frozen=True, slots=True)
class AutomatedDecisionAuditPersistenceResult:
    """Result of writing an automated decision audit record."""

    success: bool
    audit_record_id: str | None = None
    records_persisted: int = 0
    errors: tuple[str, ...] = ()
    review_task_id: str | None = None

    def __post_init__(self) -> None:
        if self.records_persisted < 0:
            raise ValueError("records_persisted must be non-negative.")
        if self.success and self.audit_record_id is None:
            raise ValueError("audit_record_id is required when success is true.")
        if not self.success and not self.errors:
            raise ValueError("errors are required when success is false.")

    @classmethod
    def succeeded(
        cls,
        audit_record_id: str,
        *,
        records_persisted: int = 1,
        review_task_id: str | None = None,
    ) -> AutomatedDecisionAuditPersistenceResult:
        return cls(
            success=True,
            audit_record_id=_clean_identifier(audit_record_id, "audit_record_id"),
            records_persisted=records_persisted,
            review_task_id=_clean_optional_text(review_task_id, "review_task_id"),
        )

    @classmethod
    def failed(
        cls,
        error: str,
        *,
        audit_record_id: str | None = None,
    ) -> AutomatedDecisionAuditPersistenceResult:
        return cls(
            success=False,
            audit_record_id=_clean_optional_text(audit_record_id, "audit_record_id"),
            errors=(_clean_identifier(error, "error"),),
        )


def new_automated_policy_audit_record_id() -> str:
    return f"automated_policy_audit:{uuid4().hex}"


def new_automated_governance_audit_record_id() -> str:
    return f"automated_governance_audit:{uuid4().hex}"


def new_governance_review_decision_id() -> str:
    return f"governance_review_decision:{uuid4().hex}"


def new_governance_residual_risk_acceptance_id() -> str:
    return f"governance_residual_risk_acceptance:{uuid4().hex}"


def _review_task_status_for_decision_outcome(
    outcome: GovernanceReviewDecisionOutcome,
) -> GovernanceReviewTaskStatus:
    return {
        GovernanceReviewDecisionOutcome.APPROVED: GovernanceReviewTaskStatus.APPROVED,
        GovernanceReviewDecisionOutcome.DENIED: GovernanceReviewTaskStatus.DENIED,
        GovernanceReviewDecisionOutcome.CONTESTED: GovernanceReviewTaskStatus.CONTESTED,
        GovernanceReviewDecisionOutcome.CHANGES_REQUESTED: (
            GovernanceReviewTaskStatus.CHANGES_REQUESTED
        ),
        GovernanceReviewDecisionOutcome.OVERRIDDEN: (
            GovernanceReviewTaskStatus.OVERRIDDEN
        ),
    }[outcome]


def authority_metadata_from_contract(
    contract: RiskAuthorityContract,
) -> JsonObject:
    return _json_object(contract.to_metadata())


def _coerce_policy_outcome(value: object) -> AutomatedPolicyAuditOutcome:
    if isinstance(value, AutomatedPolicyAuditOutcome):
        return value
    if isinstance(value, str):
        return AutomatedPolicyAuditOutcome(value.strip().lower())
    raise ValueError("policy outcome must be an automated policy audit outcome.")


def _coerce_governance_outcome(value: object) -> AutomatedGovernanceAuditOutcome:
    if isinstance(value, AutomatedGovernanceAuditOutcome):
        return value
    if isinstance(value, str):
        return AutomatedGovernanceAuditOutcome(value.strip().lower())
    raise ValueError(
        "governance outcome must be an automated governance audit outcome."
    )


def _coerce_review_task_status(value: object) -> GovernanceReviewTaskStatus:
    if isinstance(value, GovernanceReviewTaskStatus):
        return value
    if isinstance(value, str):
        return GovernanceReviewTaskStatus(value.strip().lower())
    raise ValueError("review task status must be a governance review task status.")


def _coerce_review_decision_outcome(
    value: object,
) -> GovernanceReviewDecisionOutcome:
    if isinstance(value, GovernanceReviewDecisionOutcome):
        return value
    if isinstance(value, str):
        return GovernanceReviewDecisionOutcome(value.strip().lower())
    raise ValueError("review decision outcome must identify a human review result.")


def _coerce_reviewer_actor_type(value: object) -> GovernanceReviewerActorType:
    if isinstance(value, GovernanceReviewerActorType):
        return value
    if isinstance(value, str):
        return GovernanceReviewerActorType(value.strip().lower())
    raise ValueError("reviewer actor type must identify a human reviewer.")


def _coerce_risk_tier(value: object) -> RiskTier:
    if isinstance(value, RiskTier):
        return value
    if isinstance(value, str):
        return RiskTier(value.strip().lower())
    raise ValueError("risk_tier must be a RiskTier.")


def _validate_authority_metadata(
    value: JsonObject,
    *,
    risk_tier: RiskTier,
) -> dict[str, JsonValue]:
    metadata = _json_object(value)
    observed_tier = metadata.get("risk_tier")
    if observed_tier != risk_tier.value:
        raise ValueError(
            "authority_metadata risk_tier must match the platform risk_tier."
        )
    _reject_model_authority_assertions(metadata)
    return metadata


def _reject_model_authority_assertions(metadata: Mapping[str, object]) -> None:
    forbidden_keys = {
        "approved",
        "approval_status",
        "governance_approved",
        "policy_approved",
        "production_ready",
        "residual_risk_accepted",
        "risk_tier_override",
    }
    for key, value in metadata.items():
        normalized_key = key.strip().lower()
        if normalized_key in forbidden_keys:
            raise ValueError(f"model-provided authority metadata cannot set {key!r}.")
        if isinstance(value, Mapping):
            _reject_model_authority_assertions(value)
            continue
        if isinstance(value, Sequence) and not isinstance(
            value, str | bytes | bytearray
        ):
            for item in value:
                if isinstance(item, Mapping):
                    _reject_model_authority_assertions(item)


def _validated_review_metadata(value: Mapping[str, object]) -> dict[str, object]:
    metadata = _json_object(value)
    _reject_model_authority_assertions(metadata)
    _reject_nonhuman_review_assertions(metadata)
    return metadata


def _reject_nonhuman_review_assertions(metadata: Mapping[str, object]) -> None:
    forbidden_keys = {
        "model_output",
        "workflow_metadata",
        "changes_requested",
        "clear_review_task",
        "contest",
        "contested",
        "evaluator_score",
        "generated_text",
        "override",
        "overridden",
        "policy_outcome_override",
        "request_changes",
        "requested_changes_satisfied",
        "review_satisfied",
        "satisfy_review_task",
    }
    for key, value in metadata.items():
        normalized_key = key.strip().lower()
        if normalized_key in forbidden_keys:
            raise ValueError(
                f"non-human governance review metadata cannot set {key!r}."
            )
        if isinstance(value, Mapping):
            _reject_nonhuman_review_assertions(value)
            continue
        if isinstance(value, Sequence) and not isinstance(
            value, str | bytes | bytearray
        ):
            for item in value:
                if isinstance(item, Mapping):
                    _reject_nonhuman_review_assertions(item)


def _json_object(value: Mapping[str, object]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError("JSON metadata keys must be non-empty strings.")
        result[key] = _json_value(item)
    return result


def _json_value(value: object) -> object:
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, Mapping):
        return _json_object(value)
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return [_json_value(item) for item in value]
    raise ValueError("metadata values must be JSON serializable.")


def _clean_identifier(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a string.")
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{label} cannot be empty.")
    return cleaned


def _clean_optional_text(value: object | None, label: str) -> str | None:
    if value is None:
        return None
    return _clean_identifier(value, label)
