from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from application.reports.authority import (
    REPORT_AUTHORITY_LIMITATIONS,
    morning_report_authority,
)
from core.storage.persistence.governance_audit import (
    AutomatedDecisionEvidenceReference,
    AutomatedDecisionSubject,
)
from domain.authority import RiskAuthorityContract
from domain.decision_evidence import EvidenceClaimReference

type ReportScalar = str | int | float | bool | None


@dataclass(frozen=True, slots=True)
class PreparedReportClaimEvidenceBinding:
    """Prepared claim references to attach to a generated report target."""

    section_key: str
    claim_references: tuple[EvidenceClaimReference, ...]
    bullet_label: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "section_key",
            _clean_binding_text(self.section_key, "section_key"),
        )
        if self.bullet_label is not None:
            object.__setattr__(
                self,
                "bullet_label",
                _clean_binding_text(self.bullet_label, "bullet_label"),
            )
        object.__setattr__(
            self,
            "claim_references",
            tuple(self.claim_references),
        )
        if not self.claim_references:
            raise ValueError(
                "prepared report claim evidence bindings require at least one "
                "claim reference."
            )
        for reference in self.claim_references:
            if not isinstance(reference, EvidenceClaimReference):
                raise TypeError(
                    "prepared report claim evidence bindings require "
                    "EvidenceClaimReference entries."
                )


@dataclass(frozen=True, slots=True)
class ReportMetric:
    """
    Human-facing metric for a financial report section.
    """

    label: str
    value: str
    raw_value: ReportScalar = None
    note: str | None = None


@dataclass(frozen=True, slots=True)
class ReportTableRow:
    """
    Human-facing table row with display-ready text.
    """

    label: str
    value: str
    note: str | None = None


@dataclass(frozen=True, slots=True)
class ReportTable:
    """
    Small markdown-friendly table for report metrics.
    """

    title: str
    rows: tuple[ReportTableRow, ...] = ()


@dataclass(frozen=True, slots=True)
class ReportBullet:
    """
    Concise human-readable report bullet.
    """

    text: str
    label: str | None = None
    claim_references: tuple[EvidenceClaimReference, ...] = ()


@dataclass(frozen=True, slots=True)
class ReportSection:
    """
    Human report section assembled from runtime outputs.
    """

    title: str
    summary: str
    metrics: tuple[ReportMetric, ...] = ()
    bullets: tuple[ReportBullet, ...] = ()
    risks: tuple[ReportBullet, ...] = ()
    recommendations: tuple[ReportBullet, ...] = ()
    tables: tuple[ReportTable, ...] = ()
    claim_references: tuple[EvidenceClaimReference, ...] = ()

    @classmethod
    def unavailable(
        cls,
        title: str,
        *,
        reason: str = "This section was not available in this run.",
    ) -> ReportSection:
        return cls(
            title=title,
            summary=reason,
        )


@dataclass(frozen=True, slots=True)
class ReportPublicationReview:
    """Scoped governance review metadata required before report publication."""

    subject: AutomatedDecisionSubject
    evidence: AutomatedDecisionEvidenceReference
    review_scope: str
    requested_action: str
    residual_risk_acceptance_required: bool = False


@dataclass(frozen=True, slots=True)
class MorningReportDocument:
    """
    Typed human-facing document for the morning-report workflow.
    """

    title: str
    subtitle: str
    symbol: str
    execution_id: str
    generated_at: str
    status: str
    executive_summary: ReportSection
    portfolio_snapshot: ReportSection
    macro_backdrop: ReportSection
    technical_setup: ReportSection
    news_sentiment: ReportSection
    risk_assessment: ReportSection
    recommended_action_plan: ReportSection
    run_errors: tuple[str, ...] = ()
    appendix: ReportSection | None = None
    authority: RiskAuthorityContract = field(
        default_factory=morning_report_authority,
    )
    authority_limitations: tuple[str, ...] = REPORT_AUTHORITY_LIMITATIONS
    publication_review: ReportPublicationReview | None = None


# ============================================================
# DISPLAY FORMAT HELPERS
# ============================================================


def format_currency(
    value: ReportScalar,
    *,
    fallback: str = "N/A",
) -> str:
    numeric = _as_decimal(
        value,
    )
    if numeric is None:
        return fallback

    sign = "-" if numeric < 0 else ""
    absolute = abs(
        numeric,
    )
    return f"{sign}${absolute:,.2f}"


def format_percent(
    value: ReportScalar,
    *,
    fallback: str = "N/A",
) -> str:
    numeric = _as_decimal(
        value,
    )
    if numeric is None:
        return fallback

    percent = numeric * Decimal("100") if abs(numeric) <= 1 else numeric
    return f"{percent:.1f}%"


def format_score(
    value: ReportScalar,
    *,
    fallback: str = "N/A",
) -> str:
    numeric = _as_decimal(
        value,
    )
    if numeric is None:
        return fallback

    return f"{numeric:.2f}"


def format_confidence(
    value: ReportScalar,
    *,
    fallback: str = "N/A",
) -> str:
    return format_percent(
        value,
        fallback=fallback,
    )


def format_regime(
    value: ReportScalar,
    *,
    fallback: str = "N/A",
) -> str:
    if value is None:
        return fallback

    text = str(
        value,
    ).strip()
    if not text:
        return fallback

    return " ".join(
        part.capitalize()
        for part in text.replace(
            "-",
            "_",
        ).split(
            "_",
        )
        if part
    )


def _clean_binding_text(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{label} must be a string.")
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{label} cannot be empty.")
    return cleaned


def _as_decimal(
    value: ReportScalar,
) -> Decimal | None:
    if value is None or isinstance(
        value,
        bool,
    ):
        return None

    if isinstance(
        value,
        Decimal,
    ):
        return value

    try:
        return Decimal(
            str(
                value,
            )
        )
    except (InvalidOperation, ValueError):
        return None
