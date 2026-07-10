from __future__ import annotations

from core.workflow.models.workflow_graph_definition import (
    WorkflowGraphDefinition,
)
from core.workflow.models.workflow_node_definition import (
    WorkflowNodeDefinition,
)

# ============================================================
# PORTFOLIO STATE
# ============================================================

from intelligence.portfolio.management.portfolio_state_builder import (
    PortfolioStateBuilder,
)

# ============================================================
# ANALYST TEAM
# ============================================================

from intelligence.analysts.fundamental.fundamental_agent import (
    FundamentalAgent,
)

from intelligence.analysts.technical.technical_agent import (
    TechnicalAgent,
)

# ============================================================
# RESEARCH TEAM
# ============================================================

from intelligence.research.news.news_agent import (
    NewsAgent,
)

from intelligence.research.sentiment.sentiment_agent import (
    SentimentAgent,
)

# ============================================================
# STRATEGY TEAM
# ============================================================

from intelligence.strategy.bull.bull_agent import (
    BullAgent,
)

from intelligence.strategy.bear.bear_agent import (
    BearAgent,
)

from intelligence.strategy.sideways.sideways_agent import (
    SidewaysAgent,
)

from intelligence.strategy.hypothesis.evidence_builder import (
    StrategyEvidenceBuilder,
)

from intelligence.strategy.synthesis.strategy_synthesis_agent import (
    StrategySynthesisAgent,
)

# ============================================================
# ATTRIBUTION ENGINE
# ============================================================

from intelligence.attribution.attribution_engine import (
    AttributionEngine,
)

# ============================================================
# ADAPTIVE WEIGHTING ENGINE
# ============================================================

from intelligence.strategy.weighting.adaptive_weighting_engine import (
    AdaptiveStrategyWeightingEngine,
)

# ============================================================
# RISK TEAM
# ============================================================

from intelligence.risk.drawdown.drawdown_risk_agent import (
    DrawdownRiskAgent,
)

from intelligence.risk.exposure.exposure_risk_agent import (
    ExposureRiskAgent,
)

from intelligence.risk.volatility.volatility_risk_agent import (
    VolatilityRiskAgent,
)

from intelligence.risk.aggregation.risk_signal_builder import (
    RiskSignalBuilder,
)

from intelligence.risk.aggregation.risk_aggregator_agent import (
    RiskAggregatorAgent,
)

# ============================================================
# PORTFOLIO MANAGEMENT
# ============================================================

from intelligence.portfolio.management.portfolio_manager_agent import (
    PortfolioManagerAgent,
)

# ============================================================
# EXECUTION
# ============================================================

from intelligence.execution.trade_packaging.trade_packager import (
    TradePackager,
)

from intelligence.execution.execution_risk.execution_risk_guard import (
    ExecutionRiskGuard,
)


class MorningReportWorkflow(WorkflowGraphDefinition):
    """
    Polaris Morning Report Workflow

    PURPOSE
    ------------------------------------------------------------
    Canonical daily intelligence workflow responsible for:

    - market analysis
    - portfolio state analysis
    - risk aggregation
    - strategy generation
    - synthesis
    - portfolio enforcement
    - execution packaging

    DESIGN PRINCIPLES
    ------------------------------------------------------------
    - deterministic orchestration
    - dependency injection driven
    - execution-mode agnostic
    - no hard-coded runtime state
    - no direct infrastructure coupling
    """

    @property
    def workflow_name(
        self,
    ) -> str:
        return "morning_report"

    @property
    def workflow_description(
        self,
    ) -> str:
        return (
            "Canonical daily portfolio intelligence workflow for portfolio "
            "state, market analysis, risk, strategy, packaging, and execution "
            "guardrails."
        )

    # ============================================================
    # BUILD GRAPH
    # ============================================================

    def build_graph(
        self,
    ) -> list[WorkflowNodeDefinition]:
        return [
            # ====================================================
            # PORTFOLIO STATE
            # ====================================================
            WorkflowNodeDefinition(
                name="portfolio_state_builder",
                node_type=PortfolioStateBuilder,
                tags=("morning_report", "portfolio"),
            ),
            # ====================================================
            # MARKET INTELLIGENCE
            # ====================================================
            WorkflowNodeDefinition(
                name="fundamental_agent",
                node_type=FundamentalAgent,
                dependencies=("portfolio_state_builder",),
                tags=("morning_report", "market_intelligence"),
            ),
            WorkflowNodeDefinition(
                name="technical_agent",
                node_type=TechnicalAgent,
                dependencies=("portfolio_state_builder",),
                tags=("morning_report", "market_intelligence"),
            ),
            WorkflowNodeDefinition(
                name="news_agent",
                node_type=NewsAgent,
                dependencies=("portfolio_state_builder",),
                tags=("morning_report", "market_intelligence"),
            ),
            WorkflowNodeDefinition(
                name="sentiment_agent",
                node_type=SentimentAgent,
                dependencies=("portfolio_state_builder",),
                tags=("morning_report", "market_intelligence"),
            ),
            # ====================================================
            # RISK ANALYSIS
            # ====================================================
            WorkflowNodeDefinition(
                name="drawdown_risk_agent",
                node_type=DrawdownRiskAgent,
                dependencies=(
                    "portfolio_state_builder",
                    "fundamental_agent",
                    "technical_agent",
                    "news_agent",
                    "sentiment_agent",
                ),
                tags=("morning_report", "risk"),
            ),
            WorkflowNodeDefinition(
                name="exposure_risk_agent",
                node_type=ExposureRiskAgent,
                dependencies=(
                    "portfolio_state_builder",
                    "fundamental_agent",
                    "technical_agent",
                    "news_agent",
                    "sentiment_agent",
                ),
                tags=("morning_report", "risk"),
            ),
            WorkflowNodeDefinition(
                name="volatility_risk_agent",
                node_type=VolatilityRiskAgent,
                dependencies=(
                    "portfolio_state_builder",
                    "fundamental_agent",
                    "technical_agent",
                    "news_agent",
                    "sentiment_agent",
                ),
                tags=("morning_report", "risk"),
            ),
            # ====================================================
            # RISK AGGREGATION
            # ====================================================
            WorkflowNodeDefinition(
                name="risk_signal_builder",
                node_type=RiskSignalBuilder,
                dependencies=(
                    "drawdown_risk_agent",
                    "exposure_risk_agent",
                    "volatility_risk_agent",
                ),
                tags=("morning_report", "risk"),
            ),
            WorkflowNodeDefinition(
                name="risk_aggregator_agent",
                node_type=RiskAggregatorAgent,
                dependencies=("risk_signal_builder",),
                tags=("morning_report", "risk"),
            ),
            # ====================================================
            # STRATEGY EVIDENCE
            # ====================================================
            WorkflowNodeDefinition(
                name="strategy_evidence_builder",
                node_type=StrategyEvidenceBuilder,
                dependencies=(
                    "portfolio_state_builder",
                    "fundamental_agent",
                    "technical_agent",
                    "news_agent",
                    "sentiment_agent",
                    "risk_aggregator_agent",
                ),
                tags=("morning_report", "strategy"),
            ),
            # ====================================================
            # ATTRIBUTION
            # ====================================================
            WorkflowNodeDefinition(
                name="attribution_engine",
                node_type=AttributionEngine,
                dependencies=(
                    "portfolio_state_builder",
                    "fundamental_agent",
                    "technical_agent",
                    "news_agent",
                    "sentiment_agent",
                    "risk_aggregator_agent",
                ),
                tags=("morning_report", "attribution"),
            ),
            # ====================================================
            # WEIGHTING
            # ====================================================
            WorkflowNodeDefinition(
                name="adaptive_weighting_engine",
                node_type=AdaptiveStrategyWeightingEngine,
                dependencies=(
                    "attribution_engine",
                    "risk_aggregator_agent",
                ),
                tags=("morning_report", "strategy"),
            ),
            # ====================================================
            # STRATEGY GENERATION
            # ====================================================
            WorkflowNodeDefinition(
                name="bull_agent",
                node_type=BullAgent,
                dependencies=(
                    "adaptive_weighting_engine",
                    "risk_aggregator_agent",
                    "strategy_evidence_builder",
                ),
                tags=("morning_report", "strategy"),
            ),
            WorkflowNodeDefinition(
                name="bear_agent",
                node_type=BearAgent,
                dependencies=(
                    "adaptive_weighting_engine",
                    "risk_aggregator_agent",
                    "strategy_evidence_builder",
                ),
                tags=("morning_report", "strategy"),
            ),
            WorkflowNodeDefinition(
                name="sideways_agent",
                node_type=SidewaysAgent,
                dependencies=(
                    "adaptive_weighting_engine",
                    "risk_aggregator_agent",
                    "strategy_evidence_builder",
                ),
                tags=("morning_report", "strategy"),
            ),
            # ====================================================
            # STRATEGY SYNTHESIS
            # ====================================================
            WorkflowNodeDefinition(
                name="strategy_synthesis_agent",
                node_type=StrategySynthesisAgent,
                dependencies=(
                    "adaptive_weighting_engine",
                    "bull_agent",
                    "bear_agent",
                    "sideways_agent",
                    "risk_aggregator_agent",
                    "portfolio_state_builder",
                    "technical_agent",
                ),
                tags=("morning_report", "strategy"),
            ),
            # ====================================================
            # PORTFOLIO MANAGEMENT
            # ====================================================
            WorkflowNodeDefinition(
                name="portfolio_manager_agent",
                node_type=PortfolioManagerAgent,
                dependencies=(
                    "portfolio_state_builder",
                    "strategy_synthesis_agent",
                    "risk_aggregator_agent",
                ),
                tags=("morning_report", "portfolio"),
            ),
            # ====================================================
            # EXECUTION PACKAGING
            # ====================================================
            WorkflowNodeDefinition(
                name="trade_packager",
                node_type=TradePackager,
                dependencies=("portfolio_manager_agent",),
                tags=("morning_report", "execution"),
            ),
            # ====================================================
            # EXECUTION RISK GUARD
            # ====================================================
            WorkflowNodeDefinition(
                name="execution_risk_guard",
                node_type=ExecutionRiskGuard,
                dependencies=(
                    "trade_packager",
                    "risk_aggregator_agent",
                ),
                tags=("morning_report", "execution"),
            ),
        ]
