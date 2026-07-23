"""
Application-layer persistence service exports.

This package exposes typed domain persistence services and their typed filter
contracts only. Repository implementations remain infrastructure concerns under
``core.storage.persistence`` and should not be exported from this boundary.
"""

from __future__ import annotations

from application.persistence.agent_intelligence import (
    AgentIntelligencePersistenceService,
    AgentReasoningPersistenceFilters,
    AgentRecommendationPersistenceFilters,
    AgentRiskAssessmentPersistenceFilters,
)
from application.persistence.attribution import (
    AttributionPersistenceFilters,
    AttributionPersistenceService,
    RecommendationAttributionPersistenceFilters,
    SignalAttributionPersistenceFilters,
)
from application.persistence.audit import (
    AuditPersistenceFilters,
    AuditPersistenceService,
)
from application.persistence.backtesting import (
    BacktestPersistenceService,
    BacktestRunPersistenceFilters,
)
from application.persistence.diagnostics import (
    DiagnosticsPersistenceFilters,
    DiagnosticsPersistenceService,
)
from application.persistence.export import JsonPersistenceExportService
from application.persistence.health import (
    HealthPersistenceFilters,
    HealthPersistenceService,
)
from application.persistence.lineage import LineagePersistenceService
from application.persistence.macro import (
    EconomicCalendarEventPersistenceFilters,
    MacroObservationPersistenceFilters,
    MacroPersistenceService,
    MacroRegimeSnapshotPersistenceFilters,
)
from application.persistence.market import (
    MarketBreadthSnapshotPersistenceFilters,
    MarketContextSnapshotPersistenceFilters,
    MarketEventSnapshotPersistenceFilters,
    MarketIndicatorPersistenceFilters,
    MarketOhlcvPersistenceFilters,
    MarketPersistenceService,
    TechnicalAnalysisSnapshotPersistenceFilters,
)
from application.persistence.news import (
    NewsAnalysisSnapshotPersistenceFilters,
    NewsArticlePersistenceFilters,
    NewsPersistenceService,
)
from application.persistence.portfolio import (
    PortfolioAllocationSnapshotPersistenceFilters,
    PortfolioEquityHistoryPersistenceFilters,
    PortfolioExposureSnapshotPersistenceFilters,
    PortfolioLatestPositionPersistenceFilters,
    PortfolioPersistenceService,
    PortfolioPositionHistoryPersistenceFilters,
    PortfolioRiskSnapshotPersistenceFilters,
)
from application.persistence.rag import (
    RagEligibilityPersistenceFilters,
    RagEligibilityPersistenceService,
)
from application.persistence.recommendations import (
    RecommendationPersistenceFilters,
    RecommendationPersistenceService,
    TradeSetupPersistenceFilters,
    WatchlistPersistenceFilters,
)
from application.persistence.reports import (
    ReportArtifactPersistenceFilters,
    ReportPersistenceService,
    ReportPublicationPersistenceFilters,
)
from application.persistence.retention import (
    RetentionPersistenceService,
    RetentionPlanningFilters,
    TelemetryRetentionConfig,
    TelemetryRetentionService,
)
from application.persistence.sentiment import (
    SentimentPersistenceService,
    SentimentSnapshotPersistenceFilters,
    SentimentSourcePersistenceFilters,
)
from application.persistence.strategy import (
    StrategyHypothesisEvaluationPersistenceFilters,
    StrategyHypothesisPersistenceFilters,
    StrategyPersistenceService,
    StrategySynthesisDecisionPersistenceFilters,
)
from application.persistence.telemetry import (
    AgentMetricPersistenceFilters,
    ProviderMetricPersistenceFilters,
    TelemetryEventPersistenceFilters,
    TelemetryMetricPersistenceFilters,
    TelemetryPersistenceService,
    TelemetryTracePersistenceFilters,
    WorkflowMetricPersistenceFilters,
)
from application.persistence.validation import ValidationPersistenceService
from application.persistence.workflow_audit import (
    WorkflowStateSnapshotPersistenceFilters,
    WorkflowStateSnapshotPersistenceService,
)

__all__ = [
    "AgentIntelligencePersistenceService",
    "AgentMetricPersistenceFilters",
    "AgentReasoningPersistenceFilters",
    "AgentRecommendationPersistenceFilters",
    "AgentRiskAssessmentPersistenceFilters",
    "AttributionPersistenceFilters",
    "AttributionPersistenceService",
    "AuditPersistenceFilters",
    "AuditPersistenceService",
    "BacktestPersistenceService",
    "BacktestRunPersistenceFilters",
    "DiagnosticsPersistenceFilters",
    "DiagnosticsPersistenceService",
    "EconomicCalendarEventPersistenceFilters",
    "HealthPersistenceFilters",
    "HealthPersistenceService",
    "JsonPersistenceExportService",
    "LineagePersistenceService",
    "MacroObservationPersistenceFilters",
    "MacroPersistenceService",
    "MacroRegimeSnapshotPersistenceFilters",
    "MarketBreadthSnapshotPersistenceFilters",
    "MarketContextSnapshotPersistenceFilters",
    "MarketEventSnapshotPersistenceFilters",
    "MarketIndicatorPersistenceFilters",
    "MarketOhlcvPersistenceFilters",
    "MarketPersistenceService",
    "NewsAnalysisSnapshotPersistenceFilters",
    "NewsArticlePersistenceFilters",
    "NewsPersistenceService",
    "PortfolioAllocationSnapshotPersistenceFilters",
    "PortfolioEquityHistoryPersistenceFilters",
    "PortfolioExposureSnapshotPersistenceFilters",
    "PortfolioLatestPositionPersistenceFilters",
    "PortfolioPersistenceService",
    "PortfolioPositionHistoryPersistenceFilters",
    "PortfolioRiskSnapshotPersistenceFilters",
    "ProviderMetricPersistenceFilters",
    "RagEligibilityPersistenceFilters",
    "RagEligibilityPersistenceService",
    "RecommendationAttributionPersistenceFilters",
    "RecommendationPersistenceFilters",
    "RecommendationPersistenceService",
    "ReportArtifactPersistenceFilters",
    "ReportPersistenceService",
    "ReportPublicationPersistenceFilters",
    "RetentionPersistenceService",
    "RetentionPlanningFilters",
    "SentimentPersistenceService",
    "SentimentSnapshotPersistenceFilters",
    "SentimentSourcePersistenceFilters",
    "SignalAttributionPersistenceFilters",
    "StrategyHypothesisEvaluationPersistenceFilters",
    "StrategyHypothesisPersistenceFilters",
    "StrategyPersistenceService",
    "StrategySynthesisDecisionPersistenceFilters",
    "TechnicalAnalysisSnapshotPersistenceFilters",
    "TelemetryEventPersistenceFilters",
    "TelemetryMetricPersistenceFilters",
    "TelemetryPersistenceService",
    "TelemetryRetentionConfig",
    "TelemetryRetentionService",
    "TelemetryTracePersistenceFilters",
    "TradeSetupPersistenceFilters",
    "ValidationPersistenceService",
    "WatchlistPersistenceFilters",
    "WorkflowMetricPersistenceFilters",
    "WorkflowStateSnapshotPersistenceFilters",
    "WorkflowStateSnapshotPersistenceService",
]
