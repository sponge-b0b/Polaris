from __future__ import annotations

import json

from dataclasses import dataclass
from dataclasses import fields
from datetime import date
from datetime import datetime
from decimal import Decimal
from typing import Any
from typing import TypeGuard
from typing import cast

from application.rag.ingestion.curated_rag_chunking import build_record_aware_chunks
from application.rag.ingestion.curated_rag_chunking import hash_text
from application.rag.ingestion.curated_rag_jobs import build_embedding_jobs
from application.rag.ingestion.curated_rag_models import CuratedRagBuildOptions
from core.storage.persistence.backtesting import BacktestArtifactRecord
from core.storage.persistence.backtesting import BacktestMetricRecord
from core.storage.persistence.backtesting import BacktestPortfolioSnapshotRecord
from core.storage.persistence.backtesting import BacktestRunRecord
from core.storage.persistence.backtesting import BacktestStepRecord
from core.storage.persistence.macro import MacroRegimeSnapshotRecord
from core.storage.persistence.market import MarketBreadthSnapshotRecord
from core.storage.persistence.market import MarketContextSnapshotRecord
from core.storage.persistence.market import TechnicalAnalysisSnapshotRecord
from core.storage.persistence.news import NewsAnalysisSnapshotRecord
from core.storage.persistence.portfolio import PortfolioAllocationSnapshotRecord
from core.storage.persistence.portfolio import PortfolioRiskSnapshotRecord
from core.storage.persistence.rag import JsonObject
from core.storage.persistence.rag import JsonValue
from core.storage.persistence.rag import RagChunkRecord
from core.storage.persistence.rag import RagDocumentRecord
from core.storage.persistence.rag import RagEligibilitySourceCandidate
from core.storage.persistence.rag import RagPersistenceBundle
from core.storage.persistence.rag import RagSourceEligibilityRecord
from core.storage.persistence.rag import new_rag_document_id
from core.storage.persistence.recommendations import RecommendationRationaleRecord
from core.storage.persistence.recommendations import RecommendationRecord
from core.storage.persistence.sentiment import SentimentSnapshotRecord


StructuredCuratedRagSource = (
    RecommendationRecord
    | RecommendationRationaleRecord
    | MacroRegimeSnapshotRecord
    | MarketContextSnapshotRecord
    | TechnicalAnalysisSnapshotRecord
    | MarketBreadthSnapshotRecord
    | PortfolioRiskSnapshotRecord
    | PortfolioAllocationSnapshotRecord
    | NewsAnalysisSnapshotRecord
    | SentimentSnapshotRecord
    | BacktestRunRecord
    | BacktestStepRecord
    | BacktestPortfolioSnapshotRecord
    | BacktestMetricRecord
    | BacktestArtifactRecord
)


@dataclass(frozen=True, slots=True)
class StructuredSourceSpec:
    record_type: type[object]
    source_table: str
    source_type: str
    source_kind: str
    id_attribute: str
    timestamp_attribute: str
    title_prefix: str
    headline_attributes: tuple[str, ...]
    summary_attributes: tuple[str, ...]
    content_attributes: tuple[str, ...] = ()


_STRUCTURED_SOURCE_SPECS: tuple[StructuredSourceSpec, ...] = (
    StructuredSourceSpec(
        record_type=RecommendationRecord,
        source_table="recommendations",
        source_type="recommendation",
        source_kind="recommendation",
        id_attribute="recommendation_id",
        timestamp_attribute="created_at",
        title_prefix="Recommendation",
        headline_attributes=("symbol", "bias", "status"),
        summary_attributes=(
            "confidence",
            "setup_quality",
            "risk_score",
            "risk_level",
            "time_horizon",
            "entry_context",
            "stop_context",
            "target_context",
        ),
    ),
    StructuredSourceSpec(
        record_type=RecommendationRationaleRecord,
        source_table="recommendation_rationales",
        source_type="recommendation_rationale",
        source_kind="recommendation_rationale",
        id_attribute="rationale_id",
        timestamp_attribute="created_at",
        title_prefix="Recommendation Rationale",
        headline_attributes=("recommendation_id", "rationale_type"),
        summary_attributes=("confidence",),
        content_attributes=("rationale_text",),
    ),
    StructuredSourceSpec(
        record_type=MacroRegimeSnapshotRecord,
        source_table="macro_regime_snapshots",
        source_type="macro_summary",
        source_kind="macro_regime_snapshot",
        id_attribute="regime_snapshot_id",
        timestamp_attribute="timestamp",
        title_prefix="Macro Regime Snapshot",
        headline_attributes=("region", "macro_regime", "economic_regime"),
        summary_attributes=(
            "source",
            "inflation_regime",
            "liquidity_regime",
            "growth_regime",
            "fed_stance",
            "yield_curve_regime",
            "inflation_score",
            "liquidity_score",
            "growth_score",
            "yield_curve_score",
            "macro_score",
            "risk_score",
            "confidence",
            "outputs",
        ),
    ),
    StructuredSourceSpec(
        record_type=MarketContextSnapshotRecord,
        source_table="market_context_snapshots",
        source_type="market_context_summary",
        source_kind="market_context_snapshot",
        id_attribute="context_snapshot_id",
        timestamp_attribute="timestamp",
        title_prefix="Market Context Snapshot",
        headline_attributes=("universe", "market_regime", "volatility_regime"),
        summary_attributes=(
            "source",
            "breadth_regime",
            "trend_score",
            "volatility_score",
            "breadth_score",
            "risk_score",
            "vix",
            "vix_percentile_252",
            "vvix",
            "breadth_percent",
            "ad_line_trend_score",
            "pct_above_50dma",
            "pct_above_200dma",
            "market_context_payload",
        ),
    ),
    StructuredSourceSpec(
        record_type=TechnicalAnalysisSnapshotRecord,
        source_table="technical_analysis_snapshots",
        source_type="technical_summary",
        source_kind="technical_analysis_snapshot",
        id_attribute="technical_snapshot_id",
        timestamp_attribute="timestamp",
        title_prefix="Technical Analysis Snapshot",
        headline_attributes=("symbol", "technical_regime", "trend_regime"),
        summary_attributes=(
            "source",
            "volatility_regime",
            "breadth_regime",
            "technical_score",
            "directional_technical_score",
            "trend_score",
            "trend_strength",
            "volatility_score",
            "breadth_score",
            "risk_score",
            "strategy_environment",
            "confidence",
            "regime_payload",
        ),
    ),
    StructuredSourceSpec(
        record_type=MarketBreadthSnapshotRecord,
        source_table="market_breadth_snapshots",
        source_type="market_breadth_summary",
        source_kind="market_breadth_snapshot",
        id_attribute="breadth_snapshot_id",
        timestamp_attribute="timestamp",
        title_prefix="Market Breadth Snapshot",
        headline_attributes=("universe", "breadth_regime", "risk_regime"),
        summary_attributes=(
            "source",
            "has_breadth_data",
            "advances_count",
            "declines_count",
            "unchanged_count",
            "new_highs",
            "new_lows",
            "ad_line",
            "ad_line_trend_score",
            "price_ad_divergence",
            "pct_above_50dma",
            "pct_above_200dma",
            "mcclellan_oscillator",
            "breadth_score",
            "breadth_risk_score",
            "strategy_environment",
            "breadth_payload",
        ),
    ),
    StructuredSourceSpec(
        record_type=PortfolioRiskSnapshotRecord,
        source_table="portfolio_risk_snapshots",
        source_type="portfolio_risk_summary",
        source_kind="portfolio_risk_snapshot",
        id_attribute="risk_snapshot_id",
        timestamp_attribute="timestamp",
        title_prefix="Portfolio Risk Snapshot",
        headline_attributes=("account_id", "account_health", "risk_level"),
        summary_attributes=(
            "snapshot_id",
            "portfolio_value",
            "cash",
            "risk_score",
            "drawdown_risk",
            "volatility_risk",
            "concentration_risk",
            "liquidity_risk",
            "beta",
            "cash_ratio",
            "equity_retention_ratio",
            "risk_signals",
        ),
    ),
    StructuredSourceSpec(
        record_type=PortfolioAllocationSnapshotRecord,
        source_table="portfolio_allocation_snapshots",
        source_type="portfolio_allocation_summary",
        source_kind="portfolio_allocation_snapshot",
        id_attribute="allocation_snapshot_id",
        timestamp_attribute="timestamp",
        title_prefix="Portfolio Allocation Snapshot",
        headline_attributes=("account_id", "allocation_type", "allocation_name"),
        summary_attributes=(
            "snapshot_id",
            "current_weight",
            "target_weight",
            "drift",
            "market_value",
        ),
    ),
    StructuredSourceSpec(
        record_type=NewsAnalysisSnapshotRecord,
        source_table="news_analysis_snapshots",
        source_type="news_summary",
        source_kind="news_analysis_snapshot",
        id_attribute="analysis_snapshot_id",
        timestamp_attribute="timestamp",
        title_prefix="News Analysis Snapshot",
        headline_attributes=("source", "symbols", "themes"),
        summary_attributes=(
            "importance_score",
            "sentiment_score",
            "impact_score",
            "confidence",
            "analysis_model",
            "llm_summary",
        ),
        content_attributes=("full_llm_response",),
    ),
    StructuredSourceSpec(
        record_type=SentimentSnapshotRecord,
        source_table="sentiment_snapshots",
        source_type="sentiment_summary",
        source_kind="sentiment_snapshot",
        id_attribute="sentiment_snapshot_id",
        timestamp_attribute="timestamp",
        title_prefix="Sentiment Snapshot",
        headline_attributes=("symbol", "universe", "market_regime"),
        summary_attributes=(
            "source",
            "fear_greed_score",
            "news_sentiment_score",
            "market_sentiment_score",
            "social_sentiment_score",
            "composite_sentiment",
            "market_bias",
            "confidence",
            "directional_signal",
            "momentum",
            "stability",
            "divergence",
            "fusion_components",
            "sentiment_payload",
        ),
    ),
    StructuredSourceSpec(
        record_type=BacktestRunRecord,
        source_table="backtest_runs",
        source_type="backtest_summary",
        source_kind="backtest_run",
        id_attribute="backtest_run_id",
        timestamp_attribute="completed_at",
        title_prefix="Backtest Run",
        headline_attributes=("workflow_name", "scenario_id", "status"),
        summary_attributes=("success", "started_at", "completed_at", "metrics"),
    ),
    StructuredSourceSpec(
        record_type=BacktestStepRecord,
        source_table="backtest_steps",
        source_type="backtest_step_summary",
        source_kind="backtest_step",
        id_attribute="step_id",
        timestamp_attribute="timestamp",
        title_prefix="Backtest Step",
        headline_attributes=("backtest_run_id", "step_index", "workflow_run_id"),
        summary_attributes=("success", "node_output_keys", "summary"),
    ),
    StructuredSourceSpec(
        record_type=BacktestPortfolioSnapshotRecord,
        source_table="backtest_portfolio_snapshots",
        source_type="backtest_portfolio_summary",
        source_kind="backtest_portfolio_snapshot",
        id_attribute="snapshot_id",
        timestamp_attribute="timestamp",
        title_prefix="Backtest Portfolio Snapshot",
        headline_attributes=("backtest_run_id", "step_id"),
        summary_attributes=("cash", "equity", "market_value", "positions"),
    ),
    StructuredSourceSpec(
        record_type=BacktestMetricRecord,
        source_table="backtest_metrics",
        source_type="backtest_metric_summary",
        source_kind="backtest_metric",
        id_attribute="metric_id",
        timestamp_attribute="recorded_at",
        title_prefix="Backtest Metric",
        headline_attributes=("backtest_run_id", "metric_name"),
        summary_attributes=("metric_value",),
    ),
    StructuredSourceSpec(
        record_type=BacktestArtifactRecord,
        source_table="backtest_artifacts",
        source_type="backtest_artifact",
        source_kind="backtest_artifact",
        id_attribute="artifact_id",
        timestamp_attribute="generated_at",
        title_prefix="Backtest Artifact",
        headline_attributes=("backtest_run_id", "artifact_format", "mime_type"),
        summary_attributes=("artifact_format", "mime_type"),
        content_attributes=("content",),
    ),
)


def is_structured_curated_rag_source(
    source: object,
) -> TypeGuard[StructuredCuratedRagSource]:
    return (
        _spec_for_source(
            source,
        )
        is not None
    )


def build_structured_source_bundle(
    source: StructuredCuratedRagSource,
    *,
    options: CuratedRagBuildOptions,
    eligibility: RagSourceEligibilityRecord,
) -> RagPersistenceBundle:
    spec = require_structured_source_spec(
        source,
    )
    source_id = structured_source_id(
        source,
    )
    generated_at = structured_source_timestamp(
        source,
    )
    content_text = render_structured_source_text(
        source,
    )
    document_id = new_rag_document_id(
        source_table=spec.source_table,
        source_id=source_id,
        source_type=spec.source_type,
    )
    document = RagDocumentRecord(
        document_id=document_id,
        source_table=spec.source_table,
        source_id=source_id,
        source_type=spec.source_type,
        title=structured_source_title(
            source,
        ),
        content_text=content_text,
        content_hash=hash_text(
            content_text,
        ),
        workflow_name=structured_workflow_name(
            source,
        ),
        execution_id=structured_execution_id(
            source,
        ),
        generated_at=generated_at,
        metadata=cast(
            JsonObject,
            structured_source_metadata(
                source=source,
                eligibility=eligibility,
                options=options,
            ),
        ),
    )
    chunks = build_structured_source_chunks(
        document=document,
        source=source,
        text=content_text,
        options=options,
    )
    jobs = build_embedding_jobs(
        document=document,
        chunks=chunks,
        options=options,
    )
    return RagPersistenceBundle(
        document=document,
        chunks=chunks,
        embedding_jobs=jobs,
    )


def build_structured_source_chunks(
    *,
    document: RagDocumentRecord,
    source: StructuredCuratedRagSource,
    text: str,
    options: CuratedRagBuildOptions,
) -> tuple[RagChunkRecord, ...]:
    spec = require_structured_source_spec(
        source,
    )
    timestamp = structured_source_timestamp(
        source,
    )
    return build_record_aware_chunks(
        document=document,
        text=text,
        source_metadata=cast(
            JsonObject,
            {
                **structured_source_metadata_core(
                    source,
                ),
                "source_kind": spec.source_kind,
                "source_table": spec.source_table,
                "source_id": structured_source_id(
                    source,
                ),
                "source_record_id": structured_source_id(
                    source,
                ),
                "source_type": spec.source_type,
                "created_at": timestamp.isoformat(),
                "as_of_date": timestamp.date().isoformat(),
            },
        ),
        chunk_type=f"{spec.source_kind}_section",
        options=options,
    )


def source_candidate_for_structured_source(
    source: StructuredCuratedRagSource,
) -> RagEligibilitySourceCandidate:
    spec = require_structured_source_spec(
        source,
    )
    return RagEligibilitySourceCandidate(
        source_table=spec.source_table,
        source_id=structured_source_id(
            source,
        ),
        source_type=spec.source_type,
        has_meaningful_content=structured_source_has_meaningful_content(
            source,
        ),
        has_rationale=structured_source_has_rationale(
            source,
        ),
        quality_score=structured_source_quality_score(
            source,
        ),
        metadata=cast(
            JsonObject,
            {
                "source_kind": spec.source_kind,
                **structured_source_metadata_core(
                    source,
                ),
            },
        ),
    )


def structured_source_title(
    source: StructuredCuratedRagSource,
) -> str:
    spec = require_structured_source_spec(
        source,
    )
    suffix_parts = [
        _stringify_value(
            getattr(
                source,
                attribute,
            )
        )
        for attribute in spec.headline_attributes
        if _has_renderable_value(
            getattr(
                source,
                attribute,
                None,
            )
        )
    ]
    if suffix_parts:
        return f"{spec.title_prefix} - {' / '.join(suffix_parts[:3])}"
    return spec.title_prefix


def render_structured_source_text(
    source: StructuredCuratedRagSource,
) -> str:
    spec = require_structured_source_spec(
        source,
    )
    lines = [
        f"# {structured_source_title(source)}",
        "",
        "## Source Lineage",
        "",
        f"Source Table: {spec.source_table}",
        f"Source Type: {spec.source_type}",
        f"Source ID: {structured_source_id(source)}",
        f"Timestamp: {structured_source_timestamp(source).isoformat()}",
    ]
    _append_optional_line(
        lines,
        "Workflow",
        structured_workflow_name(
            source,
        ),
    )
    _append_optional_line(
        lines,
        "Execution ID",
        structured_execution_id(
            source,
        ),
    )
    _append_optional_line(
        lines,
        "Runtime ID",
        structured_runtime_id(
            source,
        ),
    )
    _append_optional_line(
        lines,
        "Node",
        structured_node_name(
            source,
        ),
    )

    _append_attribute_section(
        lines,
        "Headline",
        source,
        spec.headline_attributes,
    )
    _append_attribute_section(
        lines,
        "Curated Summary",
        source,
        spec.summary_attributes,
    )
    for attribute in spec.content_attributes:
        value = getattr(
            source,
            attribute,
            None,
        )
        if (
            isinstance(
                value,
                str,
            )
            and value.strip()
        ):
            _append_text_section(
                lines,
                _humanize_attribute(
                    attribute,
                ),
                value,
            )

    return "\n".join(
        lines,
    )


def structured_source_metadata(
    *,
    source: StructuredCuratedRagSource,
    eligibility: RagSourceEligibilityRecord,
    options: CuratedRagBuildOptions,
) -> dict[str, object]:
    spec = require_structured_source_spec(
        source,
    )
    return {
        "curated_source": True,
        "source_kind": spec.source_kind,
        "source_table": spec.source_table,
        "source_record_id": structured_source_id(
            source,
        ),
        "source_type": spec.source_type,
        **structured_source_metadata_core(
            source,
        ),
        "rag_builder_version": "1",
        "rag_eligibility_id": eligibility.eligibility_id,
        "rag_eligibility_rule_name": eligibility.metadata.get(
            "rule_name",
        ),
        "rag_eligibility_required": options.require_source_eligibility,
    }


def structured_source_metadata_core(
    source: StructuredCuratedRagSource,
) -> dict[str, JsonValue]:
    metadata: dict[str, JsonValue] = {}
    lineage = getattr(
        source,
        "lineage",
        None,
    )
    if lineage is not None and hasattr(
        lineage,
        "as_dict",
    ):
        metadata.update(
            cast(
                dict[str, JsonValue],
                lineage.as_dict(),
            )
        )
    for attribute in (
        "symbol",
        "symbols",
        "themes",
        "universe",
        "account_id",
        "recommendation_id",
        "scenario_id",
        "backtest_run_id",
        "step_id",
        "workflow_name",
        "source",
        "confidence",
        "risk_score",
        "risk_level",
        "regime",
        "macro_regime",
        "market_regime",
        "technical_regime",
        "breadth_regime",
        "sentiment_regime",
    ):
        if not hasattr(
            source,
            attribute,
        ):
            continue
        value = _json_value(
            getattr(
                source,
                attribute,
            )
        )
        if value is not None:
            metadata[attribute] = value
    return metadata


def structured_source_id(
    source: StructuredCuratedRagSource,
) -> str:
    spec = require_structured_source_spec(
        source,
    )
    return str(
        getattr(
            source,
            spec.id_attribute,
        )
    )


def structured_source_timestamp(
    source: StructuredCuratedRagSource,
) -> datetime:
    spec = require_structured_source_spec(
        source,
    )
    value = getattr(
        source,
        spec.timestamp_attribute,
        None,
    )
    if not isinstance(
        value,
        datetime,
    ):
        raise ValueError(
            f"{type(source).__name__}.{spec.timestamp_attribute} must contain "
            "a domain timestamp."
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(
            f"{type(source).__name__}.{spec.timestamp_attribute} must be "
            "timezone-aware."
        )
    return value


def structured_workflow_name(
    source: StructuredCuratedRagSource,
) -> str | None:
    direct = getattr(
        source,
        "workflow_name",
        None,
    )
    if isinstance(
        direct,
        str,
    ):
        return direct
    lineage = getattr(
        source,
        "lineage",
        None,
    )
    value = getattr(
        lineage,
        "workflow_name",
        None,
    )
    return value if isinstance(value, str) else None


def structured_execution_id(
    source: StructuredCuratedRagSource,
) -> str | None:
    lineage = getattr(
        source,
        "lineage",
        None,
    )
    value = getattr(
        lineage,
        "execution_id",
        None,
    )
    return value if isinstance(value, str) else None


def structured_runtime_id(
    source: StructuredCuratedRagSource,
) -> str | None:
    lineage = getattr(
        source,
        "lineage",
        None,
    )
    value = getattr(
        lineage,
        "runtime_id",
        None,
    )
    return value if isinstance(value, str) else None


def structured_node_name(
    source: StructuredCuratedRagSource,
) -> str | None:
    lineage = getattr(
        source,
        "lineage",
        None,
    )
    value = getattr(
        lineage,
        "node_name",
        None,
    )
    return value if isinstance(value, str) else None


def structured_source_has_meaningful_content(
    source: StructuredCuratedRagSource,
) -> bool:
    spec = require_structured_source_spec(
        source,
    )
    for attribute in (
        *spec.headline_attributes,
        *spec.summary_attributes,
        *spec.content_attributes,
    ):
        if _has_renderable_value(
            getattr(
                source,
                attribute,
                None,
            )
        ):
            return True
    return False


def structured_source_has_rationale(
    source: StructuredCuratedRagSource,
) -> bool:
    if isinstance(
        source,
        RecommendationRationaleRecord,
    ):
        return True
    metadata = getattr(
        source,
        "metadata",
        {},
    )
    if isinstance(
        metadata,
        dict,
    ):
        value = metadata.get(
            "has_rationale",
        ) or metadata.get(
            "rationale_count",
        )
        return bool(
            value,
        )
    return not isinstance(
        source,
        RecommendationRecord,
    )


def structured_source_quality_score(
    source: StructuredCuratedRagSource,
) -> float | None:
    for attribute in (
        "confidence",
        "setup_quality",
    ):
        value = getattr(
            source,
            attribute,
            None,
        )
        if (
            isinstance(
                value,
                int | float,
            )
            and 0.0 <= float(value) <= 1.0
        ):
            return float(
                value,
            )
    return None


def require_structured_source_spec(
    source: StructuredCuratedRagSource,
) -> StructuredSourceSpec:
    spec = _spec_for_source(
        source,
    )
    if spec is None:
        raise TypeError(
            "RAG documents can only be built from curated PostgreSQL source "
            "records; raw runtime, telemetry, provider, or arbitrary JSON "
            "payloads are not supported."
        )
    return spec


def _spec_for_source(
    source: object,
) -> StructuredSourceSpec | None:
    for spec in _STRUCTURED_SOURCE_SPECS:
        if isinstance(
            source,
            spec.record_type,
        ):
            return spec
    return None


def _append_attribute_section(
    lines: list[str],
    title: str,
    source: object,
    attributes: tuple[str, ...],
) -> None:
    section_lines: list[str] = []
    for attribute in attributes:
        value = getattr(
            source,
            attribute,
            None,
        )
        if not _has_renderable_value(
            value,
        ):
            continue
        section_lines.append(
            f"- {_humanize_attribute(attribute)}: {_render_value(value)}"
        )
    if not section_lines:
        return
    lines.extend(
        [
            "",
            f"## {title}",
            "",
            *section_lines,
        ]
    )


def _append_optional_line(
    lines: list[str],
    label: str,
    value: str | None,
) -> None:
    if value is not None and value.strip():
        lines.append(f"{label}: {value}")


def _append_text_section(
    lines: list[str],
    title: str,
    text: str,
) -> None:
    lines.extend(
        [
            "",
            f"## {title}",
            "",
            text,
        ]
    )


def _humanize_attribute(
    attribute: str,
) -> str:
    return attribute.replace(
        "_",
        " ",
    ).title()


def _has_renderable_value(
    value: object,
) -> bool:
    if value is None:
        return False
    if isinstance(
        value,
        str,
    ):
        return bool(
            value.strip(),
        )
    if isinstance(
        value,
        dict | tuple | list,
    ):
        return bool(
            value,
        )
    return True


def _render_value(
    value: object,
) -> str:
    if isinstance(
        value,
        datetime | date,
    ):
        return value.isoformat()
    if isinstance(
        value,
        Decimal,
    ):
        return str(
            value,
        )
    if isinstance(
        value,
        tuple | list,
    ):
        return ", ".join(
            _stringify_value(
                item,
            )
            for item in value
        )
    if isinstance(
        value,
        dict,
    ):
        return json.dumps(
            _json_value(
                value,
            ),
            indent=2,
            sort_keys=True,
        )
    if _is_dataclass_instance(
        value,
    ):
        return json.dumps(
            _json_value(
                value,
            ),
            indent=2,
            sort_keys=True,
        )
    return str(
        value,
    )


def _stringify_value(
    value: object,
) -> str:
    if isinstance(
        value,
        datetime | date,
    ):
        return value.isoformat()
    if isinstance(
        value,
        Decimal,
    ):
        return str(
            value,
        )
    if isinstance(
        value,
        tuple | list,
    ):
        return ", ".join(
            _stringify_value(
                item,
            )
            for item in value
        )
    return str(
        value,
    )


def _json_value(
    value: object,
) -> JsonValue:
    if value is None or isinstance(
        value,
        str | int | float | bool,
    ):
        return value
    if isinstance(
        value,
        Decimal,
    ):
        return str(
            value,
        )
    if isinstance(
        value,
        datetime | date,
    ):
        return value.isoformat()
    if isinstance(
        value,
        tuple | list,
    ):
        return [
            _json_value(
                item,
            )
            for item in value
        ]
    if isinstance(
        value,
        dict,
    ):
        return {
            str(key): _json_value(
                item,
            )
            for key, item in value.items()
        }
    if _is_dataclass_instance(
        value,
    ):
        return {
            field.name: _json_value(
                getattr(
                    value,
                    field.name,
                )
            )
            for field in fields(
                value,
            )
        }
    return str(
        value,
    )


def _is_dataclass_instance(
    value: object,
) -> TypeGuard[Any]:
    return hasattr(
        value,
        "__dataclass_fields__",
    )
