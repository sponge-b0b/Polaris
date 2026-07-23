from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from core.storage.persistence.rag.rag_persistence_models import (
    JsonObject,
    JsonValue,
    RagSourceEligibilityRecord,
    new_rag_source_eligibility_id,
)

DEFAULT_RAG_ELIGIBILITY_RULE_VERSION = "2026-06-01.v1"
DEFAULT_RAG_ELIGIBILITY_REVIEWER = "default_rag_eligibility_rules"

_CURATED_REPORT_TABLES = frozenset(
    {
        "reports",
        "report_sections",
    }
)
_MEANINGFUL_AGENT_TABLES = frozenset(
    {
        "agent_signals",
        "agent_reasoning",
        "agent_recommendations",
        "agent_risk_assessments",
    }
)
_RECOMMENDATION_WITH_RATIONALE_TABLES = frozenset(
    {
        "recommendations",
        "trade_setups",
        "watchlist_items",
    }
)
_RECOMMENDATION_RATIONALE_TABLES = frozenset(
    {
        "recommendation_rationales",
    }
)
_SUMMARY_TABLES = frozenset(
    {
        "macro_regime_snapshots",
        "technical_analysis_snapshots",
        "market_context_snapshots",
        "market_breadth_snapshots",
        "portfolio_risk_snapshots",
        "portfolio_allocation_snapshots",
        "news_analysis_snapshots",
        "sentiment_snapshots",
        "backtest_runs",
        "backtest_steps",
        "backtest_portfolio_snapshots",
        "backtest_metrics",
        "backtest_artifacts",
    }
)
_RAW_RUNTIME_TABLES = frozenset(
    {
        "workflow_events",
        "workflow_node_runs",
        "workflow_runs",
        "workflow_state_snapshots",
    }
)
_RAW_TELEMETRY_TABLES = frozenset(
    {
        "telemetry_events",
        "telemetry_metrics",
        "telemetry_traces",
        "workflow_metrics",
        "agent_metrics",
        "provider_metrics",
    }
)
_RAW_PROVIDER_TABLES = frozenset(
    {
        "raw_provider_payloads",
        "provider_payloads",
        "provider_raw_payloads",
        "macro_observations",
        "economic_calendar_events",
        "market_ohlcv",
        "market_indicators",
        "news_articles",
        "sentiment_sources",
    }
)
_OPERATIONAL_ERROR_TABLES = frozenset(
    {
        "operational_error_logs",
        "runtime_error_logs",
        "error_logs",
    }
)
_ELIGIBLE_SOURCE_TYPES = frozenset(
    {
        "report",
        "report_section",
        "morning_report",
        "agent_signal",
        "agent_reasoning",
        "agent_intelligence",
        "recommendation_rationale",
        "macro_summary",
        "macro_snapshot",
        "technical_summary",
        "technical_snapshot",
        "market_context_summary",
        "market_breadth_summary",
        "portfolio_risk_summary",
        "portfolio_allocation_summary",
        "news_summary",
        "sentiment_summary",
        "sentiment_snapshot",
        "backtest_summary",
        "backtest_step_summary",
        "backtest_portfolio_summary",
        "backtest_metric_summary",
        "backtest_artifact",
    }
)
_RECOMMENDATION_SOURCE_TYPES = frozenset(
    {
        "recommendation",
        "trade_setup",
        "watchlist_item",
    }
)
_RAW_RUNTIME_SOURCE_TYPES = frozenset(
    {
        "runtime_event",
        "raw_runtime_event",
        "runtime_node_run",
        "runtime_run",
        "workflow_event",
        "workflow_run",
    }
)
_RAW_TELEMETRY_SOURCE_TYPES = frozenset(
    {
        "telemetry_event",
        "telemetry_metric",
        "telemetry_trace",
        "workflow_metric",
        "agent_metric",
        "provider_metric",
        "raw_telemetry",
    }
)
_RAW_PROVIDER_SOURCE_TYPES = frozenset(
    {
        "raw_provider_payload",
        "provider_payload",
        "provider_raw_payload",
        "raw_market_data",
        "raw_macro_data",
        "raw_news_article",
        "raw_sentiment_source",
    }
)
_OPERATIONAL_ERROR_SOURCE_TYPES = frozenset(
    {
        "operational_error_log",
        "runtime_error_log",
        "error_log",
    }
)


@dataclass(
    frozen=True,
    slots=True,
)
class RagEligibilitySourceCandidate:
    """
    Typed candidate for applying default curated RAG eligibility rules.

    The candidate references an existing canonical PostgreSQL record. It is not
    a RAG document, chunk, embedding job, vector-store payload, or graph-store
    payload.
    """

    source_table: str
    source_id: str
    source_type: str
    has_meaningful_content: bool = True
    has_rationale: bool = False
    quality_score: float | None = None
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "source_table",
            _clean_identifier(
                self.source_table,
                "source_table",
            ).lower(),
        )
        object.__setattr__(
            self,
            "source_id",
            _clean_identifier(
                self.source_id,
                "source_id",
            ),
        )
        object.__setattr__(
            self,
            "source_type",
            _clean_identifier(
                self.source_type,
                "source_type",
            ).lower(),
        )
        if self.quality_score is not None:
            _require_ratio(
                self.quality_score,
                "quality_score",
            )
        object.__setattr__(
            self,
            "metadata",
            dict(
                self.metadata,
            ),
        )


class DefaultRagEligibilityRules:
    """
    Default metadata-only rules for curated RAG source eligibility.

    These rules intentionally stop at eligibility metadata. They do not build
    RAG documents, chunks, embedding jobs, vector-store writes, graph-store
    writes, or ingestion workflows.
    """

    def evaluate(  # noqa: C901
        self,
        candidate: RagEligibilitySourceCandidate,
        *,
        reviewed_timestamp: datetime | None = None,
    ) -> RagSourceEligibilityRecord:
        reviewed_at = reviewed_timestamp or datetime.now(
            UTC,
        )
        table = candidate.source_table
        source_type = candidate.source_type

        if table in _RAW_RUNTIME_TABLES or source_type in _RAW_RUNTIME_SOURCE_TYPES:
            return _build_record(
                candidate,
                eligible=False,
                reason="Raw runtime records are operational state and are not curated RAG sources.",  # noqa: E501
                quality_score=0.0,
                rule_name="raw_runtime_ineligible",
                reviewed_timestamp=reviewed_at,
            )

        if table in _RAW_TELEMETRY_TABLES or source_type in _RAW_TELEMETRY_SOURCE_TYPES:
            return _build_record(
                candidate,
                eligible=False,
                reason="Raw telemetry records are observability data and are not curated RAG sources.",  # noqa: E501
                quality_score=0.0,
                rule_name="raw_telemetry_ineligible",
                reviewed_timestamp=reviewed_at,
            )

        if table in _RAW_PROVIDER_TABLES or source_type in _RAW_PROVIDER_SOURCE_TYPES:
            return _build_record(
                candidate,
                eligible=False,
                reason="Raw provider payloads and facts are not curated RAG sources.",
                quality_score=0.0,
                rule_name="raw_provider_ineligible",
                reviewed_timestamp=reviewed_at,
            )

        if (
            table in _OPERATIONAL_ERROR_TABLES
            or source_type in _OPERATIONAL_ERROR_SOURCE_TYPES
        ):
            return _build_record(
                candidate,
                eligible=False,
                reason="Operational error logs are not curated RAG sources.",
                quality_score=0.0,
                rule_name="operational_error_log_ineligible",
                reviewed_timestamp=reviewed_at,
            )

        if not candidate.has_meaningful_content:
            return _build_record(
                candidate,
                eligible=False,
                reason="Source lacks meaningful curated text for RAG retrieval.",
                quality_score=0.0,
                rule_name="missing_meaningful_content_ineligible",
                reviewed_timestamp=reviewed_at,
            )

        if table in _CURATED_REPORT_TABLES:
            return _build_record(
                candidate,
                eligible=True,
                reason="Curated human-readable reports are eligible RAG sources.",
                quality_score=_quality_score(candidate, 0.92),
                rule_name="curated_report_eligible",
                reviewed_timestamp=reviewed_at,
            )

        if table in _MEANINGFUL_AGENT_TABLES:
            return _build_record(
                candidate,
                eligible=True,
                reason="Meaningful agent signals and reasoning are eligible RAG sources.",  # noqa: E501
                quality_score=_quality_score(candidate, 0.86),
                rule_name="meaningful_agent_intelligence_eligible",
                reviewed_timestamp=reviewed_at,
            )

        if table in _RECOMMENDATION_RATIONALE_TABLES:
            return _build_record(
                candidate,
                eligible=True,
                reason="Recommendation rationales are eligible RAG sources.",
                quality_score=_quality_score(candidate, 0.9),
                rule_name="recommendation_rationale_eligible",
                reviewed_timestamp=reviewed_at,
            )

        if (
            table in _RECOMMENDATION_WITH_RATIONALE_TABLES
            or source_type in _RECOMMENDATION_SOURCE_TYPES
        ):
            if candidate.has_rationale:
                return _build_record(
                    candidate,
                    eligible=True,
                    reason="Recommendations with rationales are eligible RAG sources.",
                    quality_score=_quality_score(candidate, 0.88),
                    rule_name="recommendation_with_rationale_eligible",
                    reviewed_timestamp=reviewed_at,
                )
            return _build_record(
                candidate,
                eligible=False,
                reason="Recommendations without rationales are not curated RAG sources by default.",  # noqa: E501
                quality_score=0.0,
                rule_name="recommendation_without_rationale_ineligible",
                reviewed_timestamp=reviewed_at,
            )

        if table in _SUMMARY_TABLES:
            return _build_record(
                candidate,
                eligible=True,
                reason="Curated analytical summaries are eligible RAG sources.",
                quality_score=_quality_score(candidate, 0.84),
                rule_name="curated_summary_eligible",
                reviewed_timestamp=reviewed_at,
            )

        if source_type in _ELIGIBLE_SOURCE_TYPES:
            return _build_record(
                candidate,
                eligible=True,
                reason="Curated source type is eligible for RAG retrieval by default.",
                quality_score=_quality_score(candidate, 0.8),
                rule_name="curated_source_type_eligible",
                reviewed_timestamp=reviewed_at,
            )

        return _build_record(
            candidate,
            eligible=False,
            reason="No default curated RAG eligibility rule matched this source.",
            quality_score=0.0,
            rule_name="unknown_source_ineligible",
            reviewed_timestamp=reviewed_at,
        )


def evaluate_default_rag_source_eligibility(
    candidate: RagEligibilitySourceCandidate,
    *,
    reviewed_timestamp: datetime | None = None,
) -> RagSourceEligibilityRecord:
    return DefaultRagEligibilityRules().evaluate(
        candidate,
        reviewed_timestamp=reviewed_timestamp,
    )


def _build_record(
    candidate: RagEligibilitySourceCandidate,
    *,
    eligible: bool,
    reason: str,
    quality_score: float,
    rule_name: str,
    reviewed_timestamp: datetime,
) -> RagSourceEligibilityRecord:
    metadata: dict[str, JsonValue] = dict(
        candidate.metadata,
    )
    metadata.update(
        {
            "reviewer": DEFAULT_RAG_ELIGIBILITY_REVIEWER,
            "rule_name": rule_name,
            "rule_version": DEFAULT_RAG_ELIGIBILITY_RULE_VERSION,
        }
    )
    return RagSourceEligibilityRecord(
        eligibility_id=new_rag_source_eligibility_id(
            source_table=candidate.source_table,
            source_id=candidate.source_id,
            source_type=candidate.source_type,
        ),
        source_table=candidate.source_table,
        source_id=candidate.source_id,
        source_type=candidate.source_type,
        eligible=eligible,
        reason=reason,
        quality_score=quality_score,
        reviewed_timestamp=reviewed_timestamp,
        metadata=metadata,
    )


def _quality_score(
    candidate: RagEligibilitySourceCandidate,
    default_score: float,
) -> float:
    if candidate.quality_score is None:
        return default_score
    return candidate.quality_score


def _clean_identifier(
    value: str | None,
    field_name: str,
) -> str:
    if value is None or not value.strip():
        raise ValueError(f"{field_name} cannot be empty.")
    return value.strip()


def _require_ratio(
    value: float,
    field_name: str,
) -> None:
    if value < 0.0 or value > 1.0:
        raise ValueError(f"{field_name} must be between 0.0 and 1.0.")
