from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from decimal import InvalidOperation
from typing import TypeAlias


ReportScalar: TypeAlias = str | int | float | bool | None


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
