from __future__ import annotations

from typing import Final

WORKFLOW_OUTPUT_SCHEMA_VERSION_V1: Final[int] = 1

ATTRIBUTION_EXPLANATION_OUTPUT_CONTRACT: Final[str] = "polaris.attribution.explanation"
EXECUTION_RISK_DECISION_OUTPUT_CONTRACT: Final[str] = "polaris.execution.risk_decision"
FUNDAMENTAL_SIGNAL_OUTPUT_CONTRACT: Final[str] = "polaris.agent.fundamental_signal"
MACRO_ANALYSIS_OUTPUT_CONTRACT: Final[str] = "polaris.macro.analysis"
NEWS_ANALYSIS_OUTPUT_CONTRACT: Final[str] = "polaris.news.analysis"
PORTFOLIO_ALLOCATION_INTENT_OUTPUT_CONTRACT: Final[str] = (
    "polaris.portfolio.allocation_intent"
)
PORTFOLIO_STATE_OUTPUT_CONTRACT: Final[str] = "polaris.portfolio.state"
RISK_AGGREGATE_INPUT_SIGNAL_OUTPUT_CONTRACT: Final[str] = (
    "polaris.risk.aggregate_input_signal"
)
RISK_AGGREGATE_SIGNAL_OUTPUT_CONTRACT: Final[str] = "polaris.risk.aggregate_signal"
RISK_DRAWDOWN_SIGNAL_OUTPUT_CONTRACT: Final[str] = "polaris.risk.drawdown_signal"
RISK_EXPOSURE_SIGNAL_OUTPUT_CONTRACT: Final[str] = "polaris.risk.exposure_signal"
RISK_VOLATILITY_SIGNAL_OUTPUT_CONTRACT: Final[str] = "polaris.risk.volatility_signal"
SENTIMENT_SNAPSHOT_OUTPUT_CONTRACT: Final[str] = "polaris.sentiment.snapshot"
STRATEGY_BEAR_HYPOTHESIS_OUTPUT_CONTRACT: Final[str] = (
    "polaris.strategy.hypothesis.bear"
)
STRATEGY_BULL_HYPOTHESIS_OUTPUT_CONTRACT: Final[str] = (
    "polaris.strategy.hypothesis.bull"
)
STRATEGY_EVIDENCE_CONTEXT_OUTPUT_CONTRACT: Final[str] = (
    "polaris.strategy.evidence_context"
)
STRATEGY_PERSPECTIVE_WEIGHTS_OUTPUT_CONTRACT: Final[str] = (
    "polaris.strategy.perspective_weights"
)
STRATEGY_SIDEWAYS_HYPOTHESIS_OUTPUT_CONTRACT: Final[str] = (
    "polaris.strategy.hypothesis.sideways"
)
STRATEGY_SYNTHESIS_OUTPUT_CONTRACT: Final[str] = "polaris.strategy.synthesis"
TECHNICAL_ANALYSIS_OUTPUT_CONTRACT: Final[str] = "polaris.market.technical_analysis"
TRADE_RECOMMENDATION_OUTPUT_CONTRACT: Final[str] = "polaris.trade.recommendation"
