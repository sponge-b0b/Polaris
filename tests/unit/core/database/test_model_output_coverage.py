from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, cast

from sqlalchemy import Table
from sqlalchemy.orm import DeclarativeBase

from core.database.models.agent_intelligence import (
    AgentReasoningModel,
    AgentRecommendationModel,
    AgentRiskAssessmentModel,
)
from core.database.models.agent_signals import AgentSignalModel
from core.database.models.macro import MacroRegimeSnapshotModel
from core.database.models.market import (
    MarketBreadthSnapshotModel,
    MarketContextSnapshotModel,
    MarketEventSnapshotModel,
    TechnicalAnalysisSnapshotModel,
)
from core.database.models.news import NewsAnalysisSnapshotModel, NewsArticleModel
from core.database.models.portfolio import (
    PortfolioPositionHistoryModel,
    PortfolioPositionLatestModel,
    PortfolioRiskSnapshotModel,
)
from core.database.models.portfolio_state import (
    PortfolioStateHistoryModel,
    PortfolioStateLatestModel,
)
from core.database.models.recommendations import (
    RecommendationModel,
    RecommendationOutcomeModel,
    RecommendationRationaleModel,
    TradeSetupModel,
    WatchlistItemModel,
)
from core.database.models.sentiment import SentimentSnapshotModel

CoverageKind = Literal["relational", "payload", "not_persisted"]


@dataclass(frozen=True, slots=True)
class OutputCoverageContract:
    name: str
    output_keys: frozenset[str]
    coverage: dict[str, CoverageKind]
    models: tuple[type[DeclarativeBase], ...]
    required_relational_columns: frozenset[str]
    required_payload_columns: frozenset[str]


TECHNICAL_RESULT_KEYS = frozenset(
    {
        "symbol",
        "technical_score",
        "snapshot",
        "market_context",
        "micro_regime",
        "trend",
        "volatility",
        "breadth",
        "raw_regime",
        "regime",
    }
)

MARKET_CONTEXT_KEYS = frozenset(
    {
        "vix",
        "vix_20",
        "vix_50",
        "vix_percentile_252",
        "vix_trend_ratio",
        "vix_change_5d",
        "vix_change_20d",
        "vvix",
        "vvix_20",
        "vvix_50",
        "vvix_percentile_252",
        "vvix_trend_ratio",
        "vvix_change_5d",
        "vvix_change_20d",
        "market_cap_index",
        "market_cap_index_20",
        "market_cap_index_50",
        "market_cap_index_change_5d",
        "market_cap_index_change_20d",
        "advances_count",
        "declines_count",
        "unchanged_count",
        "active_count",
        "net_breadth",
        "breadth_percent",
        "ad_ratio",
        "ad_line",
        "ad_line_ema_10",
        "ad_line_ema_20",
        "ad_line_ema_50",
        "ad_line_slope_5",
        "ad_line_slope_20",
        "ad_line_trend_ratio",
        "ad_line_trend_score",
        "price_ad_divergence",
        "pct_above_50dma",
        "pct_above_200dma",
        "new_highs",
        "new_lows",
        "new_high_low_diff",
        "new_high_low_ratio",
        "net_breadth_ema_19",
        "net_breadth_ema_39",
        "mcclellan_oscillator",
        "mcclellan_summation_index",
        "has_vix",
        "has_vvix",
        "has_sp500",
        "has_ad_line",
        "has_breadth",
        "top_50_constituents",
        "market_caps",
    }
)

BREADTH_RESULT_KEYS = frozenset(
    {
        "has_breadth_data",
        "breadth_score",
        "breadth_risk_score",
        "breadth_regime",
        "risk_regime",
        "strategy_environment",
        "trend_score",
        "slope_score",
        "confirmation_score",
        "participation_score",
        "leadership_score",
        "mcclellan_score",
        "divergence_score",
        "components",
        "source_metrics",
    }
)

MARKET_EVENTS_KEYS = frozenset(
    {
        "symbol",
        "market_pressure_score",
        "volatility_forecast",
        "regime_bias",
        "events",
        "high_impact_events",
        "event_count",
        "high_impact_count",
        "risk_projection",
    }
)

PORTFOLIO_STATE_KEYS = frozenset(
    {
        "portfolio_value",
        "equity",
        "cash",
        "cash_pct",
        "position_count",
        "gross_exposure",
        "net_exposure",
        "long_exposure",
        "short_exposure",
        "leverage",
        "largest_position_pct",
        "concentration_score",
        "diversification_score",
        "sector_exposure",
        "asset_class_exposure",
        "beta_exposure",
        "beta_risk",
        "portfolio_heat",
        "risk_intensity",
        "portfolio_regime",
        "directional_bias",
        "unrealized_pnl",
        "unrealized_pnl_pct",
        "unrealized_intraday_pnl",
        "unrealized_intraday_pnl_pct",
        "realized_pnl",
        "realized_pnl_pct",
        "pnl_total",
        "pnl_total_pct",
        "portfolio_history",
        "risk_signals",
    }
)

PORTFOLIO_EQUITY_KEYS = frozenset(
    {
        "account_number",
        "status",
        "currency",
        "equity",
        "cash",
        "buying_power",
        "regt_buying_power",
        "daytrading_buying_power",
        "non_marginable_buying_power",
        "options_buying_power",
        "multiplier",
        "accrued_fees",
        "pending_transfer_in",
        "pending_transfer_out",
        "options_approved_level",
        "options_trading_level",
        "account_health",
        "risk_signals",
    }
)

PORTFOLIO_POSITION_KEYS = frozenset(
    {
        "symbol",
        "side",
        "quantity",
        "qty_available",
        "entry_price",
        "current_price",
        "lastday_price",
        "change_today",
        "market_value",
        "signed_market_value",
        "cost_basis",
        "unrealized_pnl",
        "unrealized_pnl_pct",
        "unrealized_intraday_pnl",
        "unrealized_intraday_pnl_pct",
        "asset_id",
        "exchange",
        "asset_class",
        "asset_marginable",
        "sector",
        "beta",
        "swap_rate",
        "avg_entry_swap_rate",
        "exposure_weight",
    }
)

MACRO_RESULT_KEYS = frozenset(
    {
        "macro_data",
        "inflation_analysis",
        "fed_analysis",
        "liquidity_analysis",
        "yield_curve_analysis",
        "economic_regime",
        "inflation_regime",
        "fed_stance",
        "liquidity_regime",
        "yield_curve_regime",
        "market_bias",
        "summary",
        "macro_score",
    }
)

SENTIMENT_RESULT_KEYS = frozenset(
    {
        "symbol",
        "providers",
        "features",
        "sentiment",
        "composite_sentiment",
        "market_regime",
        "market_bias",
        "confidence",
        "directional_signal",
        "momentum",
        "stability",
        "divergence",
    }
)

NEWS_RESULT_KEYS = frozenset(
    {
        "id",
        "title",
        "summary",
        "source",
        "url",
        "published_at",
        "headline_score",
        "relevance_score",
        "raw",
        "analysis",
    }
)

AGENT_OUTPUT_KEYS = frozenset(
    {
        "agent_name",
        "agent_type",
        "symbol",
        "universe",
        "timestamp",
        "directional_score",
        "confidence",
        "regime",
        "signals",
        "risks",
        "recommendations",
        "features",
        "reasoning_text",
        "llm_response",
        "inputs",
        "outputs",
        "supporting_signals",
    }
)

GENERIC_AGENT_SIGNAL_COLUMNS = frozenset(
    {
        "agent_name",
        "agent_type",
        "symbol",
        "universe",
        "timestamp",
        "directional_score",
        "confidence",
        "regime",
    }
)

GENERIC_AGENT_SIGNAL_PAYLOAD_COLUMNS = frozenset(
    {
        "signals",
        "risks",
        "recommendations",
        "features",
    }
)

TECHNICAL_AGENT_OUTPUT_KEYS = AGENT_OUTPUT_KEYS | frozenset(
    {
        "technical_score",
        "market_context",
        "breadth",
        "trend",
        "volatility",
    }
)

STRATEGY_SYNTHESIS_OUTPUT_KEYS = AGENT_OUTPUT_KEYS | frozenset(
    {
        "strategy_weights",
        "allocation_vector",
        "event_context",
        "breadth_context",
        "risk_pressure",
    }
)

RISK_AGENT_OUTPUT_KEYS = AGENT_OUTPUT_KEYS | frozenset(
    {
        "risk_pressure",
        "risk_regime",
        "risk_bias",
        "drawdown_risk",
        "exposure_risk",
        "volatility_risk",
        "composite_risk",
        "execution_guard",
    }
)

PORTFOLIO_MANAGER_OUTPUT_KEYS = AGENT_OUTPUT_KEYS | frozenset(
    {
        "target_allocation",
        "drift",
        "total_drift",
        "execution_status",
        "scale_factor",
        "portfolio_regime",
    }
)

TRADE_PACKAGER_OUTPUT_KEYS = AGENT_OUTPUT_KEYS | frozenset(
    {
        "trade_intent",
        "risk_alignment",
        "trade_quality_score",
        "position_sizing_hint",
        "entry_context",
        "stop_context",
        "target_context",
    }
)

RECOMMENDATION_LAYER_KEYS = frozenset(
    {
        "recommendation_id",
        "symbol",
        "bias",
        "confidence",
        "setup_quality",
        "risk_score",
        "risk_level",
        "time_horizon",
        "status",
        "created_at",
        "entry_context",
        "stop_context",
        "target_context",
        "supporting_signals",
        "rationale_text",
        "outcome",
        "human_action",
        "setup_type",
        "risk_reward_ratio",
        "reason",
        "priority",
    }
)

ALL_COVERED_MODELS = (
    TechnicalAnalysisSnapshotModel,
    MarketContextSnapshotModel,
    MarketBreadthSnapshotModel,
    MarketEventSnapshotModel,
    PortfolioStateHistoryModel,
    PortfolioStateLatestModel,
    PortfolioRiskSnapshotModel,
    PortfolioPositionHistoryModel,
    PortfolioPositionLatestModel,
    MacroRegimeSnapshotModel,
    SentimentSnapshotModel,
    NewsArticleModel,
    NewsAnalysisSnapshotModel,
    AgentSignalModel,
    AgentReasoningModel,
    AgentRecommendationModel,
    AgentRiskAssessmentModel,
    RecommendationModel,
    RecommendationRationaleModel,
    RecommendationOutcomeModel,
    TradeSetupModel,
    WatchlistItemModel,
)

CANONICAL_COLUMN_RENAMES = {
    ("market_breadth_snapshots", "advancing_count"): "advances_count",
    ("market_breadth_snapshots", "declining_count"): "declines_count",
    ("market_breadth_snapshots", "advance_decline_line"): "ad_line",
    ("market_breadth_snapshots", "percent_above_50dma"): "pct_above_50dma",
    ("market_breadth_snapshots", "percent_above_200dma"): "pct_above_200dma",
    ("market_breadth_snapshots", "inputs"): "inputs_payload",
    ("market_breadth_snapshots", "outputs"): "breadth_payload",
    ("market_context_snapshots", "inputs"): "inputs_payload",
    ("market_context_snapshots", "outputs"): "market_context_payload",
    (
        "technical_analysis_snapshots",
        "directional_score",
    ): "directional_technical_score",
    ("technical_analysis_snapshots", "inputs"): "inputs_payload",
    ("technical_analysis_snapshots", "indicator_outputs"): "snapshot_payload",
    ("technical_analysis_snapshots", "analysis_outputs"): "regime_payload",
    ("macro_regime_snapshots", "inputs"): "macro_data_payload",
    ("macro_regime_snapshots", "outputs"): "economic_regime_payload",
    ("news_articles", "published_timestamp"): "published_at",
    ("news_articles", "metadata"): "metadata_payload",
    ("news_analysis_snapshots", "inputs"): "inputs_payload",
    ("news_analysis_snapshots", "outputs"): "analysis_payload",
    ("portfolio_state_history", "cash_ratio"): "cash_pct",
    ("portfolio_state_history", "risk_signals"): "risk_signals_payload",
    ("portfolio_state_latest", "cash_ratio"): "cash_pct",
    ("portfolio_state_latest", "risk_signals"): "risk_signals_payload",
    ("portfolio_positions_history", "weight"): "exposure_weight",
    ("portfolio_positions_latest", "weight"): "exposure_weight",
    ("agent_reasoning", "inputs"): "inputs_payload",
    ("agent_reasoning", "outputs"): "outputs_payload",
    ("agent_recommendations", "inputs"): "inputs_payload",
    ("agent_recommendations", "outputs"): "outputs_payload",
    ("agent_risk_assessments", "inputs"): "inputs_payload",
    ("agent_risk_assessments", "outputs"): "outputs_payload",
}

ALLOWED_CANONICAL_PAYLOAD_COLUMNS_WITHOUT_SUFFIX = frozenset(
    {
        "asset_class_exposure",
        "entry_context",
        "features",
        "recommendations",
        "risks",
        "sector_exposure",
        "signals",
        "stop_context",
        "supporting_signals",
        "target_context",
    }
)

CANONICAL_SCORE_SUFFIXES = (
    "_score",
    "_risk",
    "_confidence",
    "confidence",
    "score",
)

CANONICAL_METRIC_SUFFIX_EXCEPTIONS = frozenset({"risk_intensity", "risk_reward_ratio"})
CANONICAL_RISK_FIELD_SUFFIXES = CANONICAL_SCORE_SUFFIXES + ("_regime", "_level")


CONTRACTS = (
    OutputCoverageContract(
        name="technical_analysis_result",
        output_keys=TECHNICAL_RESULT_KEYS,
        coverage={
            "symbol": "relational",
            "technical_score": "relational",
            "snapshot": "payload",
            "market_context": "payload",
            "micro_regime": "payload",
            "trend": "payload",
            "volatility": "payload",
            "breadth": "payload",
            "raw_regime": "payload",
            "regime": "payload",
        },
        models=(TechnicalAnalysisSnapshotModel,),
        required_relational_columns=frozenset({"symbol", "technical_score"}),
        required_payload_columns=frozenset(
            {
                "snapshot_payload",
                "market_context_payload",
                "micro_regime_payload",
                "trend_payload",
                "volatility_payload",
                "breadth_payload",
                "raw_regime_payload",
                "regime_payload",
            }
        ),
    ),
    OutputCoverageContract(
        name="market_context",
        output_keys=MARKET_CONTEXT_KEYS,
        coverage={
            **{key: "relational" for key in MARKET_CONTEXT_KEYS},
            "top_50_constituents": "payload",
            "market_caps": "payload",
        },
        models=(MarketContextSnapshotModel,),
        required_relational_columns=MARKET_CONTEXT_KEYS
        - frozenset({"top_50_constituents", "market_caps"}),
        required_payload_columns=frozenset(
            {
                "top_50_constituents_payload",
                "market_caps_payload",
                "market_context_payload",
            }
        ),
    ),
    OutputCoverageContract(
        name="breadth_result",
        output_keys=BREADTH_RESULT_KEYS,
        coverage={
            **{key: "relational" for key in BREADTH_RESULT_KEYS},
            "components": "payload",
            "source_metrics": "payload",
        },
        models=(MarketBreadthSnapshotModel,),
        required_relational_columns=BREADTH_RESULT_KEYS
        - frozenset({"components", "source_metrics"}),
        required_payload_columns=frozenset(
            {"components_payload", "source_metrics_payload", "breadth_payload"}
        ),
    ),
    OutputCoverageContract(
        name="market_events",
        output_keys=MARKET_EVENTS_KEYS,
        coverage={
            "symbol": "relational",
            "market_pressure_score": "relational",
            "volatility_forecast": "relational",
            "regime_bias": "relational",
            "event_count": "relational",
            "high_impact_count": "relational",
            "events": "payload",
            "high_impact_events": "payload",
            "risk_projection": "payload",
        },
        models=(MarketEventSnapshotModel,),
        required_relational_columns=frozenset(
            {
                "symbol",
                "market_pressure_score",
                "volatility_forecast",
                "regime_bias",
                "event_count",
                "high_impact_count",
            }
        ),
        required_payload_columns=frozenset(
            {"events_payload", "high_impact_events_payload", "risk_projection_payload"}
        ),
    ),
    OutputCoverageContract(
        name="portfolio_state",
        output_keys=PORTFOLIO_STATE_KEYS,
        coverage={
            **{key: "relational" for key in PORTFOLIO_STATE_KEYS},
            "sector_exposure": "payload",
            "asset_class_exposure": "payload",
            "portfolio_history": "payload",
            "risk_signals": "payload",
        },
        models=(
            PortfolioStateHistoryModel,
            PortfolioStateLatestModel,
            PortfolioRiskSnapshotModel,
        ),
        required_relational_columns=PORTFOLIO_STATE_KEYS
        - frozenset(
            {
                "sector_exposure",
                "asset_class_exposure",
                "portfolio_history",
                "risk_signals",
            }
        ),
        required_payload_columns=frozenset(
            {
                "sector_exposure",
                "asset_class_exposure",
                "portfolio_history_payload",
                "risk_signals_payload",
                "portfolio_state_payload",
            }
        ),
    ),
    OutputCoverageContract(
        name="portfolio_equity",
        output_keys=PORTFOLIO_EQUITY_KEYS,
        coverage={
            **{key: "relational" for key in PORTFOLIO_EQUITY_KEYS},
            "risk_signals": "payload",
        },
        models=(PortfolioStateHistoryModel, PortfolioStateLatestModel),
        required_relational_columns=PORTFOLIO_EQUITY_KEYS - frozenset({"risk_signals"}),
        required_payload_columns=frozenset(
            {"risk_signals_payload", "equity_state_payload"}
        ),
    ),
    OutputCoverageContract(
        name="portfolio_position",
        output_keys=PORTFOLIO_POSITION_KEYS,
        coverage={key: "relational" for key in PORTFOLIO_POSITION_KEYS},
        models=(PortfolioPositionHistoryModel, PortfolioPositionLatestModel),
        required_relational_columns=PORTFOLIO_POSITION_KEYS,
        required_payload_columns=frozenset(
            {"position_payload", "position_risk_payload"}
        ),
    ),
    OutputCoverageContract(
        name="macro_result",
        output_keys=MACRO_RESULT_KEYS,
        coverage={
            "macro_data": "payload",
            "inflation_analysis": "payload",
            "fed_analysis": "payload",
            "liquidity_analysis": "payload",
            "yield_curve_analysis": "payload",
            "economic_regime": "payload",
            "inflation_regime": "relational",
            "fed_stance": "relational",
            "liquidity_regime": "relational",
            "yield_curve_regime": "relational",
            "market_bias": "relational",
            "summary": "relational",
            "macro_score": "relational",
        },
        models=(MacroRegimeSnapshotModel,),
        required_relational_columns=frozenset(
            {
                "inflation_regime",
                "fed_stance",
                "liquidity_regime",
                "yield_curve_regime",
                "market_bias",
                "summary",
                "macro_score",
            }
        ),
        required_payload_columns=frozenset(
            {
                "macro_data_payload",
                "inflation_analysis_payload",
                "fed_analysis_payload",
                "liquidity_analysis_payload",
                "yield_curve_analysis_payload",
                "economic_regime_payload",
                "components_payload",
            }
        ),
    ),
    OutputCoverageContract(
        name="sentiment_result",
        output_keys=SENTIMENT_RESULT_KEYS,
        coverage={
            "symbol": "relational",
            "providers": "payload",
            "features": "payload",
            "sentiment": "payload",
            "composite_sentiment": "relational",
            "market_regime": "relational",
            "market_bias": "relational",
            "confidence": "relational",
            "directional_signal": "relational",
            "momentum": "relational",
            "stability": "relational",
            "divergence": "relational",
        },
        models=(SentimentSnapshotModel,),
        required_relational_columns=frozenset(
            {
                "symbol",
                "composite_sentiment",
                "market_regime",
                "market_bias",
                "confidence",
                "directional_signal",
                "momentum",
                "stability",
                "divergence",
            }
        ),
        required_payload_columns=frozenset(
            {
                "providers_payload",
                "features_payload",
                "sentiment_payload",
                "fusion_components_payload",
                "raw_payload",
            }
        ),
    ),
    OutputCoverageContract(
        name="news_result",
        output_keys=NEWS_RESULT_KEYS,
        coverage={
            "id": "relational",
            "title": "relational",
            "summary": "relational",
            "source": "relational",
            "url": "relational",
            "published_at": "relational",
            "headline_score": "relational",
            "relevance_score": "relational",
            "raw": "payload",
            "analysis": "payload",
        },
        models=(NewsArticleModel, NewsAnalysisSnapshotModel),
        required_relational_columns=frozenset(
            {
                "title",
                "summary",
                "source",
                "url",
                "published_at",
                "headline_score",
                "relevance_score",
            }
        ),
        required_payload_columns=frozenset(
            {"normalized_article_payload", "raw_payload", "analysis_payload"}
        ),
    ),
    OutputCoverageContract(
        name="agent_output",
        output_keys=AGENT_OUTPUT_KEYS,
        coverage={
            "agent_name": "relational",
            "agent_type": "relational",
            "symbol": "relational",
            "universe": "relational",
            "timestamp": "relational",
            "directional_score": "relational",
            "confidence": "relational",
            "regime": "relational",
            "signals": "payload",
            "risks": "payload",
            "recommendations": "payload",
            "features": "payload",
            "reasoning_text": "relational",
            "llm_response": "relational",
            "inputs": "payload",
            "outputs": "payload",
            "supporting_signals": "payload",
        },
        models=(
            AgentSignalModel,
            AgentReasoningModel,
            AgentRecommendationModel,
            AgentRiskAssessmentModel,
        ),
        required_relational_columns=frozenset(
            {
                "agent_name",
                "agent_type",
                "symbol",
                "universe",
                "timestamp",
                "directional_score",
                "confidence",
                "regime",
                "reasoning_text",
                "llm_response",
            }
        ),
        required_payload_columns=GENERIC_AGENT_SIGNAL_PAYLOAD_COLUMNS
        | frozenset({"inputs_payload", "outputs_payload", "supporting_signals"}),
    ),
    OutputCoverageContract(
        name="technical_agent_output",
        output_keys=TECHNICAL_AGENT_OUTPUT_KEYS,
        coverage={
            **{key: "payload" for key in TECHNICAL_AGENT_OUTPUT_KEYS},
            **{key: "relational" for key in GENERIC_AGENT_SIGNAL_COLUMNS},
        },
        models=(AgentSignalModel,),
        required_relational_columns=GENERIC_AGENT_SIGNAL_COLUMNS,
        required_payload_columns=GENERIC_AGENT_SIGNAL_PAYLOAD_COLUMNS,
    ),
    OutputCoverageContract(
        name="strategy_synthesis_output",
        output_keys=STRATEGY_SYNTHESIS_OUTPUT_KEYS,
        coverage={
            **{key: "payload" for key in STRATEGY_SYNTHESIS_OUTPUT_KEYS},
            **{key: "relational" for key in GENERIC_AGENT_SIGNAL_COLUMNS},
        },
        models=(AgentSignalModel,),
        required_relational_columns=GENERIC_AGENT_SIGNAL_COLUMNS,
        required_payload_columns=GENERIC_AGENT_SIGNAL_PAYLOAD_COLUMNS,
    ),
    OutputCoverageContract(
        name="risk_agent_output",
        output_keys=RISK_AGENT_OUTPUT_KEYS,
        coverage={
            **{key: "payload" for key in RISK_AGENT_OUTPUT_KEYS},
            **{key: "relational" for key in GENERIC_AGENT_SIGNAL_COLUMNS},
        },
        models=(AgentSignalModel,),
        required_relational_columns=GENERIC_AGENT_SIGNAL_COLUMNS,
        required_payload_columns=GENERIC_AGENT_SIGNAL_PAYLOAD_COLUMNS,
    ),
    OutputCoverageContract(
        name="portfolio_manager_output",
        output_keys=PORTFOLIO_MANAGER_OUTPUT_KEYS,
        coverage={
            **{key: "payload" for key in PORTFOLIO_MANAGER_OUTPUT_KEYS},
            **{key: "relational" for key in GENERIC_AGENT_SIGNAL_COLUMNS},
        },
        models=(AgentSignalModel,),
        required_relational_columns=GENERIC_AGENT_SIGNAL_COLUMNS,
        required_payload_columns=GENERIC_AGENT_SIGNAL_PAYLOAD_COLUMNS,
    ),
    OutputCoverageContract(
        name="trade_packager_output",
        output_keys=TRADE_PACKAGER_OUTPUT_KEYS,
        coverage={
            **{key: "payload" for key in TRADE_PACKAGER_OUTPUT_KEYS},
            **{key: "relational" for key in GENERIC_AGENT_SIGNAL_COLUMNS},
        },
        models=(AgentSignalModel, RecommendationModel, TradeSetupModel),
        required_relational_columns=GENERIC_AGENT_SIGNAL_COLUMNS
        | frozenset(
            {
                "symbol",
                "bias",
                "confidence",
                "setup_quality",
                "risk_score",
                "risk_reward_ratio",
            }
        ),
        required_payload_columns=GENERIC_AGENT_SIGNAL_PAYLOAD_COLUMNS
        | frozenset({"entry_context", "stop_context", "target_context"}),
    ),
    OutputCoverageContract(
        name="recommendation_layer",
        output_keys=RECOMMENDATION_LAYER_KEYS,
        coverage={
            **{key: "relational" for key in RECOMMENDATION_LAYER_KEYS},
            "entry_context": "payload",
            "stop_context": "payload",
            "target_context": "payload",
            "supporting_signals": "payload",
        },
        models=(
            RecommendationModel,
            RecommendationRationaleModel,
            RecommendationOutcomeModel,
            TradeSetupModel,
            WatchlistItemModel,
        ),
        required_relational_columns=frozenset(
            {
                "recommendation_id",
                "symbol",
                "bias",
                "confidence",
                "setup_quality",
                "risk_score",
                "risk_level",
                "time_horizon",
                "status",
                "created_at",
                "rationale_text",
                "outcome",
                "human_action",
                "setup_type",
                "risk_reward_ratio",
                "reason",
                "priority",
            }
        ),
        required_payload_columns=frozenset(
            {
                "entry_context",
                "stop_context",
                "target_context",
                "supporting_signals",
            }
        ),
    ),
)


def test_output_coverage_contract_classifies_every_service_key() -> None:
    for contract in CONTRACTS:
        assert set(contract.coverage) == set(contract.output_keys), contract.name
        assert set(contract.coverage.values()) <= {
            "relational",
            "payload",
            "not_persisted",
        }


def test_output_coverage_contracts_have_explicit_persistence_targets() -> None:
    for contract in CONTRACTS:
        assert (
            contract.required_relational_columns or contract.required_payload_columns
        ), contract.name
        for column_name in contract.required_payload_columns:
            assert column_name.endswith("_payload") or column_name in {
                "asset_class_exposure",
                "component_scores",
                "entry_context",
                "features",
                "recommendations",
                "risk_signals",
                "risks",
                "sector_exposure",
                "signals",
                "stop_context",
                "supporting_signals",
                "target_context",
            }


def test_canonical_database_naming_rules_are_encoded() -> None:
    """Document naming rules used by the destructive cleanup plan."""
    for contract in CONTRACTS:
        for column_name in contract.required_payload_columns:
            if column_name in ALLOWED_CANONICAL_PAYLOAD_COLUMNS_WITHOUT_SUFFIX:
                continue
            assert column_name.endswith("_payload"), column_name

        legacy_names_for_contract_models = {
            legacy_name
            for table_name, legacy_name in CANONICAL_COLUMN_RENAMES
            if table_name in _model_table_names(contract.models)
        }
        for column_name in contract.required_relational_columns:
            assert not column_name.endswith("_payload"), column_name
            assert column_name not in legacy_names_for_contract_models, column_name


def test_legacy_schema_names_have_canonical_cleanup_targets() -> None:
    """Ensure known legacy columns are explicit migration cleanup targets."""
    existing_columns = _existing_table_columns(ALL_COVERED_MODELS)

    for legacy_column, canonical_name in CANONICAL_COLUMN_RENAMES.items():
        assert canonical_name != legacy_column[1]
        assert _is_canonical_column_name(canonical_name), canonical_name
        if legacy_column in existing_columns:
            assert legacy_column in CANONICAL_COLUMN_RENAMES


def test_canonical_metric_names_use_consistent_suffixes() -> None:
    metric_columns = frozenset(
        column_name
        for contract in CONTRACTS
        for column_name in contract.required_relational_columns
        if any(token in column_name for token in ("score", "risk", "confidence"))
    )

    for column_name in metric_columns:
        if column_name in CANONICAL_METRIC_SUFFIX_EXCEPTIONS:
            continue
        assert column_name.endswith(CANONICAL_RISK_FIELD_SUFFIXES), column_name


def test_current_schema_gap_report_matches_revised_plan() -> None:
    """Pin current model-output gaps before schema cleanup begins.

    Later plan steps should reduce these expected gaps as models, migrations, and
    mappers are updated. This test intentionally passes today while documenting
    exactly what remains uncovered by canonical columns or payload targets.
    """
    assert EXPECTED_CURRENT_SCHEMA_GAPS == {
        "technical_analysis_result": {
            "missing_relational_columns": frozenset(),
            "missing_payload_columns": frozenset(),
            "missing_model": False,
        },
        "market_context": {
            "missing_relational_columns": frozenset(),
            "missing_payload_columns": frozenset(),
            "missing_model": False,
        },
        "breadth_result": {
            "missing_relational_columns": frozenset(),
            "missing_payload_columns": frozenset(),
            "missing_model": False,
        },
        "market_events": {
            "missing_relational_columns": frozenset(),
            "missing_payload_columns": frozenset(),
            "missing_model": False,
        },
        "portfolio_state": {
            "missing_relational_columns": frozenset(),
            "missing_payload_columns": frozenset(
                {
                    "portfolio_history_payload",
                }
            ),
            "missing_model": False,
        },
        "portfolio_equity": {
            "missing_relational_columns": frozenset(),
            "missing_payload_columns": frozenset(),
            "missing_model": False,
        },
        "portfolio_position": {
            "missing_relational_columns": frozenset(),
            "missing_payload_columns": frozenset(),
            "missing_model": False,
        },
        "macro_result": {
            "missing_relational_columns": frozenset(),
            "missing_payload_columns": frozenset(),
            "missing_model": False,
        },
        "sentiment_result": {
            "missing_relational_columns": frozenset(),
            "missing_payload_columns": frozenset(),
            "missing_model": False,
        },
        "news_result": {
            "missing_relational_columns": frozenset(),
            "missing_payload_columns": frozenset(),
            "missing_model": False,
        },
        "agent_output": {
            "missing_relational_columns": frozenset(),
            "missing_payload_columns": frozenset(),
            "missing_model": False,
        },
        "technical_agent_output": {
            "missing_relational_columns": frozenset(),
            "missing_payload_columns": frozenset(),
            "missing_model": False,
        },
        "strategy_synthesis_output": {
            "missing_relational_columns": frozenset(),
            "missing_payload_columns": frozenset(),
            "missing_model": False,
        },
        "risk_agent_output": {
            "missing_relational_columns": frozenset(),
            "missing_payload_columns": frozenset(),
            "missing_model": False,
        },
        "portfolio_manager_output": {
            "missing_relational_columns": frozenset(),
            "missing_payload_columns": frozenset(),
            "missing_model": False,
        },
        "trade_packager_output": {
            "missing_relational_columns": frozenset(),
            "missing_payload_columns": frozenset(),
            "missing_model": False,
        },
        "recommendation_layer": {
            "missing_relational_columns": frozenset(),
            "missing_payload_columns": frozenset(),
            "missing_model": False,
        },
    }


def _existing_column_names(contract: OutputCoverageContract) -> frozenset[str]:
    return frozenset(
        column.name for model in contract.models for column in model.__table__.columns
    )


def _missing_relational_columns(contract: OutputCoverageContract) -> frozenset[str]:
    return contract.required_relational_columns - _existing_column_names(contract)


def _missing_payload_columns(contract: OutputCoverageContract) -> frozenset[str]:
    return contract.required_payload_columns - _existing_column_names(contract)


def _model_table_names(models: tuple[type[DeclarativeBase], ...]) -> frozenset[str]:
    return frozenset(_sqlalchemy_table(model).name for model in models)


def _existing_table_columns(
    models: tuple[type[DeclarativeBase], ...],
) -> frozenset[tuple[str, str]]:
    return frozenset(
        (table.name, column.name)
        for model in models
        for table in (_sqlalchemy_table(model),)
        for column in table.columns
    )


def _sqlalchemy_table(model: type[DeclarativeBase]) -> Table:
    return cast(Table, model.__table__)


def _is_canonical_column_name(column_name: str) -> bool:
    if column_name in ALLOWED_CANONICAL_PAYLOAD_COLUMNS_WITHOUT_SUFFIX:
        return True
    if column_name in {"inputs", "outputs", "metadata"}:
        return False
    if column_name.endswith("_payload"):
        return True
    return not column_name.endswith(("_outputs", "_timestamp"))


EXPECTED_CURRENT_SCHEMA_GAPS = {
    contract.name: {
        "missing_relational_columns": _missing_relational_columns(contract),
        "missing_payload_columns": _missing_payload_columns(contract),
        "missing_model": not contract.models,
    }
    for contract in CONTRACTS
}
