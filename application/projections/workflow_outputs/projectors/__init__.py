from __future__ import annotations

from application.projections.workflow_outputs.projectors.macro import (
    ECONOMIC_CALENDAR_EVENTS_FIELD,
)
from application.projections.workflow_outputs.projectors.macro import (
    MACRO_ANALYSIS_FIELD,
)
from application.projections.workflow_outputs.projectors.macro import (
    MACRO_ANALYSIS_OBSERVED_AT_FIELD,
)
from application.projections.workflow_outputs.projectors.macro import (
    MACRO_ANALYSIS_PROJECTOR_NAME,
)
from application.projections.workflow_outputs.projectors.macro import (
    MACRO_ANALYSIS_PROJECTOR_NODE_NAMES,
)
from application.projections.workflow_outputs.projectors.macro import (
    MACRO_ANALYSIS_REGION_FIELD,
)
from application.projections.workflow_outputs.projectors.macro import (
    MACRO_ANALYSIS_SOURCE_FIELD,
)
from application.projections.workflow_outputs.projectors.macro import (
    MacroAnalysisWorkflowOutputProjector,
)
from application.projections.workflow_outputs.projectors.macro import (
    build_macro_analysis_projector_registration,
)
from application.projections.workflow_outputs.projectors.market import (
    TECHNICAL_MARKET_OBSERVED_AT_FIELD,
)
from application.projections.workflow_outputs.projectors.market import (
    TECHNICAL_MARKET_PROJECTOR_NAME,
)
from application.projections.workflow_outputs.projectors.market import (
    TECHNICAL_MARKET_PROJECTOR_NODE_NAMES,
)
from application.projections.workflow_outputs.projectors.market import (
    TECHNICAL_MARKET_UNIVERSE_FIELD,
)
from application.projections.workflow_outputs.projectors.market import (
    TechnicalMarketWorkflowOutputProjector,
)
from application.projections.workflow_outputs.projectors.market import (
    build_technical_market_projector_registration,
)
from application.projections.workflow_outputs.projectors.news import (
    NEWS_ANALYSIS_ARTICLES_FIELD,
)
from application.projections.workflow_outputs.projectors.news import (
    NEWS_ANALYSIS_OBSERVED_AT_FIELD,
)
from application.projections.workflow_outputs.projectors.news import (
    NEWS_ANALYSIS_PROJECTOR_NAME,
)
from application.projections.workflow_outputs.projectors.news import (
    NEWS_ANALYSIS_PROJECTOR_NODE_NAMES,
)
from application.projections.workflow_outputs.projectors.news import (
    NEWS_ANALYSIS_SOURCE_FIELD,
)
from application.projections.workflow_outputs.projectors.news import (
    NewsAnalysisWorkflowOutputProjector,
)
from application.projections.workflow_outputs.projectors.news import (
    build_news_analysis_projector_registration,
)
from application.projections.workflow_outputs.projectors.sentiment import (
    SENTIMENT_SNAPSHOT_FIELD,
)
from application.projections.workflow_outputs.projectors.sentiment import (
    SENTIMENT_SNAPSHOT_OBSERVED_AT_FIELD,
)
from application.projections.workflow_outputs.projectors.sentiment import (
    SENTIMENT_SNAPSHOT_PROJECTOR_NAME,
)
from application.projections.workflow_outputs.projectors.sentiment import (
    SENTIMENT_SNAPSHOT_PROJECTOR_NODE_NAMES,
)
from application.projections.workflow_outputs.projectors.sentiment import (
    SENTIMENT_SNAPSHOT_SOURCE_FIELD,
)
from application.projections.workflow_outputs.projectors.sentiment import (
    SENTIMENT_SNAPSHOT_UNIVERSE_FIELD,
)
from application.projections.workflow_outputs.projectors.sentiment import (
    SENTIMENT_SOURCE_DATA_FIELD,
)
from application.projections.workflow_outputs.projectors.sentiment import (
    SentimentSnapshotWorkflowOutputProjector,
)
from application.projections.workflow_outputs.projectors.sentiment import (
    build_sentiment_snapshot_projector_registration,
)

from application.projections.workflow_outputs.projectors.agent_signals import (
    AgentSignalWorkflowOutputProjector,
)
from application.projections.workflow_outputs.projectors.agent_signals import (
    build_risk_signal_projector_registrations,
)
from application.projections.workflow_outputs.projectors.portfolio import (
    PORTFOLIO_STATE_PROJECTOR_NAME,
)
from application.projections.workflow_outputs.projectors.portfolio import (
    PORTFOLIO_STATE_PROJECTOR_NODE_NAMES,
)
from application.projections.workflow_outputs.projectors.portfolio import (
    PortfolioStateWorkflowOutputProjector,
)
from application.projections.workflow_outputs.projectors.portfolio import (
    build_portfolio_state_projector_registration,
)
from application.projections.workflow_outputs.projectors.recommendations import (
    PortfolioAllocationIntentWorkflowOutputProjector,
)
from application.projections.workflow_outputs.projectors.recommendations import (
    TradeRecommendationWorkflowOutputProjector,
)
from application.projections.workflow_outputs.projectors.recommendations import (
    build_recommendation_projector_registrations,
)
from application.projections.workflow_outputs.projectors.strategy import (
    StrategyHypothesisWorkflowOutputProjector,
)
from application.projections.workflow_outputs.projectors.strategy import (
    StrategySynthesisWorkflowOutputProjector,
)
from application.projections.workflow_outputs.projectors.strategy import (
    build_strategy_projector_registrations,
)

__all__ = [
    "AgentSignalWorkflowOutputProjector",
    "PORTFOLIO_STATE_PROJECTOR_NAME",
    "PORTFOLIO_STATE_PROJECTOR_NODE_NAMES",
    "PortfolioAllocationIntentWorkflowOutputProjector",
    "PortfolioStateWorkflowOutputProjector",
    "StrategyHypothesisWorkflowOutputProjector",
    "StrategySynthesisWorkflowOutputProjector",
    "TradeRecommendationWorkflowOutputProjector",
    "build_portfolio_state_projector_registration",
    "build_recommendation_projector_registrations",
    "build_risk_signal_projector_registrations",
    "build_strategy_projector_registrations",
    "build_sentiment_snapshot_projector_registration",
    "build_news_analysis_projector_registration",
    "SentimentSnapshotWorkflowOutputProjector",
    "NewsAnalysisWorkflowOutputProjector",
    "SENTIMENT_SOURCE_DATA_FIELD",
    "SENTIMENT_SNAPSHOT_UNIVERSE_FIELD",
    "SENTIMENT_SNAPSHOT_SOURCE_FIELD",
    "SENTIMENT_SNAPSHOT_PROJECTOR_NODE_NAMES",
    "SENTIMENT_SNAPSHOT_PROJECTOR_NAME",
    "SENTIMENT_SNAPSHOT_OBSERVED_AT_FIELD",
    "SENTIMENT_SNAPSHOT_FIELD",
    "NEWS_ANALYSIS_SOURCE_FIELD",
    "NEWS_ANALYSIS_PROJECTOR_NODE_NAMES",
    "NEWS_ANALYSIS_PROJECTOR_NAME",
    "NEWS_ANALYSIS_OBSERVED_AT_FIELD",
    "NEWS_ANALYSIS_ARTICLES_FIELD",
    "ECONOMIC_CALENDAR_EVENTS_FIELD",
    "MACRO_ANALYSIS_FIELD",
    "MACRO_ANALYSIS_OBSERVED_AT_FIELD",
    "MACRO_ANALYSIS_PROJECTOR_NAME",
    "MACRO_ANALYSIS_PROJECTOR_NODE_NAMES",
    "MACRO_ANALYSIS_REGION_FIELD",
    "MACRO_ANALYSIS_SOURCE_FIELD",
    "TECHNICAL_MARKET_OBSERVED_AT_FIELD",
    "TECHNICAL_MARKET_PROJECTOR_NAME",
    "TECHNICAL_MARKET_PROJECTOR_NODE_NAMES",
    "TECHNICAL_MARKET_UNIVERSE_FIELD",
    "MacroAnalysisWorkflowOutputProjector",
    "TechnicalMarketWorkflowOutputProjector",
    "build_macro_analysis_projector_registration",
    "build_technical_market_projector_registration",
]
