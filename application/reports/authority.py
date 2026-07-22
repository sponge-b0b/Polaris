from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Final, cast

from domain.authority import (
    AiOutputContentType,
    AuthorityEffect,
    CanonicalOwner,
    IntendedSink,
    RiskAuthorityClassificationInput,
    RiskAuthorityContract,
    RiskTier,
    SourceOfTruthCategory,
    authority_contract_metadata,
    classify_risk_authority,
)

type JsonScalar = str | int | float | bool | None
type JsonValue = JsonScalar | Mapping[str, JsonValue] | Sequence[JsonValue]

REPORT_AUTHORITY_FAILURE_MODE_METADATA_KEY: Final = "report_authority_failure_mode"
REPORT_AUTHORITY_FAIL_CLOSED_METADATA_KEY: Final = "report_authority_fail_closed"
REPORT_AUTHORITY_BOUNDARY_METADATA_KEY: Final = "report_authority_boundary"
REPORT_AUTHORITY_LIMITATIONS_METADATA_KEY: Final = "report_authority_limitations"

REPORT_AUTHORITY_BOUNDARY: Final = (
    "presentation_report_is_decision_support_not_portfolio_strategy_governance_"
    "readiness_or_execution_authority"
)
REPORT_AUTHORITY_LIMITATIONS: Final[tuple[str, ...]] = (
    "Report content is non-authoritative decision support and does not approve "
    "portfolio, strategy, governance, readiness, or execution decisions.",
    "Workflow evidence, provider data, and derived analysis may be incomplete, "
    "stale, or unavailable for some sections.",
    "Broker execution, governance approval, residual-risk acceptance, and "
    "production readiness require separate canonical controls outside this report.",
)

_ALLOWED_REPORT_AUTHORITY_EFFECTS: Final[frozenset[AuthorityEffect]] = frozenset(
    {
        AuthorityEffect.NON_AUTHORITATIVE_INFORMATION,
        AuthorityEffect.ADVISORY_CONTEXT,
    }
)
_AUTHORITY_CLAIM_PATTERNS: Final[tuple[tuple[str, re.Pattern[str]], ...]] = (
    ("authority_effect", re.compile(r"(?i)\bauthority[-_ ]effect\b")),
    ("authority_level", re.compile(r"(?i)\b(?:authoritative|authority[-_ ]level)\b")),
    ("governance_approved", re.compile(r"(?i)\bgovernance[-_ ]approved\b")),
    ("production_ready", re.compile(r"(?i)\bproduction[-_ ]ready\b")),
    (
        "residual_risk_accepted",
        re.compile(r"(?i)\bresidual[-_ ]risk[-_ ]accepted\b"),
    ),
    ("risk_tier", re.compile(r"(?i)\brisk[-_ ]tier\b")),
    (
        "portfolio_decision_authority",
        re.compile(r"(?i)\b(?:final|authoritative|approved)\s+portfolio\s+decision\b"),
    ),
    (
        "strategy_decision_authority",
        re.compile(r"(?i)\b(?:final|authoritative|approved)\s+strategy\s+decision\b"),
    ),
    (
        "execution_decision_authority",
        re.compile(
            r"(?i)\b(?:approved\s+execution\s+decision|execution\s+is\s+approved|"
            r"execute\s+(?:the\s+)?trade|place\s+(?:a\s+)?(?:market\s+)?order)\b"
        ),
    ),
)
_UNSUPPORTED_CAPITAL_ADVICE_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(
        r"(?i)\b(?:buy|sell|short|cover)\s+\d+(?:\.\d+)?\s+(?:shares|contracts)\b"
    ),
    re.compile(r"(?i)\b(?:send|submit)\s+(?:the\s+)?(?:trade|order)\b"),
)


class ReportAuthorityFailureMode(StrEnum):
    """Platform-owned failure modes for report presentation boundaries."""

    NONE = "none"
    UNSAFE_AUTHORITY_ESCALATION = "unsafe_authority_escalation"
    UNSUPPORTED_CAPITAL_ADVICE = "unsupported_capital_advice"
    OUTSIDE_AUTHORITY = "outside_authority"


class ReportAuthorityViolationError(ValueError):
    """Raised when report content cannot safely cross a presentation boundary."""

    def __init__(
        self,
        message: str,
        *,
        failure_mode: ReportAuthorityFailureMode,
    ) -> None:
        super().__init__(message)
        self.failure_mode = failure_mode


@dataclass(frozen=True, slots=True)
class ReportAuthorityValidation:
    """Result of checking report content against its authority boundary."""

    failure_mode: ReportAuthorityFailureMode = ReportAuthorityFailureMode.NONE
    claims: tuple[str, ...] = ()

    @property
    def safe_to_publish(self) -> bool:
        return self.failure_mode is ReportAuthorityFailureMode.NONE


def morning_report_authority(
    *,
    evidence_sufficient: bool = True,
    externally_visible: bool = True,
    model_provided_metadata: Mapping[str, object] | None = None,
) -> RiskAuthorityContract:
    """Classify human-facing morning-report output at the presentation boundary."""

    return classify_risk_authority(
        RiskAuthorityClassificationInput(
            content_type=AiOutputContentType.REPORT,
            authority_effect=AuthorityEffect.ADVISORY_CONTEXT,
            canonical_owner=CanonicalOwner.REPORT_SERVICE,
            source_of_truth=SourceOfTruthCategory.PRESENTATION_OUTPUT,
            intended_sink=IntendedSink.REPORT,
            capital_relevant=True,
            durable_authority=False,
            externally_visible=externally_visible,
            governance_impact=False,
            evidence_sufficient=evidence_sufficient,
            model_provided_metadata=model_provided_metadata or {},
        )
    )


def report_authority_metadata(
    contract: RiskAuthorityContract,
    *,
    failure_mode: ReportAuthorityFailureMode = ReportAuthorityFailureMode.NONE,
) -> dict[str, JsonValue]:
    """Build JSON-safe report authority metadata for render/persistence sinks."""

    metadata = authority_contract_metadata(contract)
    metadata[REPORT_AUTHORITY_FAILURE_MODE_METADATA_KEY] = failure_mode.value
    metadata[REPORT_AUTHORITY_FAIL_CLOSED_METADATA_KEY] = (
        failure_mode is not ReportAuthorityFailureMode.NONE
    )
    metadata[REPORT_AUTHORITY_BOUNDARY_METADATA_KEY] = REPORT_AUTHORITY_BOUNDARY
    metadata[REPORT_AUTHORITY_LIMITATIONS_METADATA_KEY] = list(
        REPORT_AUTHORITY_LIMITATIONS
    )
    return cast(dict[str, JsonValue], metadata)


def validate_report_publication_authority(
    *,
    contract: RiskAuthorityContract,
    content_texts: Sequence[str],
) -> ReportAuthorityValidation:
    """Fail closed before report text crosses an external or durable sink."""

    if contract.risk_tier is RiskTier.PROHIBITED_OUTSIDE_AUTHORITY:
        return ReportAuthorityValidation(
            failure_mode=ReportAuthorityFailureMode.OUTSIDE_AUTHORITY,
        )
    if contract.authority_effect not in _ALLOWED_REPORT_AUTHORITY_EFFECTS:
        return ReportAuthorityValidation(
            failure_mode=ReportAuthorityFailureMode.OUTSIDE_AUTHORITY,
        )
    if contract.ignored_model_authority_claims:
        return ReportAuthorityValidation(
            failure_mode=ReportAuthorityFailureMode.UNSAFE_AUTHORITY_ESCALATION,
            claims=contract.ignored_model_authority_claims,
        )

    text = "\n".join(content_texts)
    unsupported_capital_advice = _unsupported_capital_advice_claims(text)
    if unsupported_capital_advice:
        return ReportAuthorityValidation(
            failure_mode=ReportAuthorityFailureMode.UNSUPPORTED_CAPITAL_ADVICE,
            claims=unsupported_capital_advice,
        )

    authority_claims = _authority_claims_from_text(text)
    if authority_claims:
        return ReportAuthorityValidation(
            failure_mode=ReportAuthorityFailureMode.UNSAFE_AUTHORITY_ESCALATION,
            claims=authority_claims,
        )

    return ReportAuthorityValidation()


def ensure_report_publication_authority(
    *,
    contract: RiskAuthorityContract,
    content_texts: Sequence[str],
    boundary_name: str,
) -> None:
    """Raise a boundary-specific error if report content is unsafe to publish."""

    validation = validate_report_publication_authority(
        contract=contract,
        content_texts=content_texts,
    )
    if validation.safe_to_publish:
        return

    claims = ", ".join(validation.claims) if validation.claims else "none"
    raise ReportAuthorityViolationError(
        f"{boundary_name} rejected report publication: "
        f"{validation.failure_mode.value}; claims={claims}.",
        failure_mode=validation.failure_mode,
    )


def _authority_claims_from_text(text: str) -> tuple[str, ...]:
    return tuple(
        claim_key
        for claim_key, pattern in _AUTHORITY_CLAIM_PATTERNS
        if pattern.search(text)
    )


def _unsupported_capital_advice_claims(text: str) -> tuple[str, ...]:
    if any(pattern.search(text) for pattern in _UNSUPPORTED_CAPITAL_ADVICE_PATTERNS):
        return ("unsupported_capital_advice",)
    return ()
