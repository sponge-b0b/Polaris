from __future__ import annotations

from core.database.models.agent_intelligence import (
    AgentReasoningModel,
    AgentRecommendationModel,
    AgentRiskAssessmentModel,
)
from core.database.models.agent_signals import AgentSignalModel
from core.database.models.ai_artifacts import AiPromptProgramArtifactModel
from core.database.models.ai_observability import AiObservabilityExportJobModel
from core.database.models.attribution import (
    AttributionRecordModel,
    RecommendationAttributionModel,
    SignalAttributionModel,
)
from core.database.models.audit import PersistenceAuditEventModel
from core.database.models.backtesting import (
    BacktestArtifactModel,
    BacktestFillModel,
    BacktestMetricModel,
    BacktestPortfolioSnapshotModel,
    BacktestRunModel,
    BacktestScenarioModel,
    BacktestStepModel,
)
from core.database.models.completed_runs import (
    CompletedRunArtifactModel,
    CompletedWorkflowNodeOutputModel,
    CompletedWorkflowRunModel,
)
from core.database.models.evaluation import (
    EvaluationArtifactModel,
    EvaluationCaseModel,
    EvaluationDatasetModel,
    EvaluationMetricResultModel,
    EvaluationRunModel,
)
from core.database.models.lineage import PersistenceLineageLinkModel
from core.database.models.macro import (
    EconomicCalendarEventModel,
    MacroObservationModel,
    MacroRegimeSnapshotModel,
)
from core.database.models.market import (
    MarketBreadthSnapshotModel,
    MarketContextSnapshotModel,
    MarketEventSnapshotModel,
    MarketIndicatorModel,
    MarketOhlcvModel,
    TechnicalAnalysisSnapshotModel,
)
from core.database.models.news import NewsAnalysisSnapshotModel, NewsArticleModel
from core.database.models.portfolio import (
    PortfolioAllocationSnapshotModel,
    PortfolioEquityHistoryPointModel,
    PortfolioExposureSnapshotModel,
    PortfolioPositionHistoryModel,
    PortfolioPositionLatestModel,
    PortfolioRiskSnapshotModel,
)
from core.database.models.portfolio_state import (
    PortfolioStateHistoryModel,
    PortfolioStateLatestModel,
)
from core.database.models.projections import WorkflowOutputProjectionJobModel
from core.database.models.rag import (
    RagAnswerLogModel,
    RagChunkModel,
    RagDocumentModel,
    RagEmbeddingJobModel,
    RagGraphJobModel,
    RagQueryLogModel,
    RagSourceEligibilityModel,
)
from core.database.models.recommendations import (
    RecommendationModel,
    RecommendationOutcomeModel,
    RecommendationRationaleModel,
    TradeSetupModel,
    WatchlistItemModel,
)
from core.database.models.reports import (
    ReportArtifactModel,
    ReportModel,
    ReportPublicationModel,
    ReportSectionModel,
    ReportVersionModel,
)
from core.database.models.retention import PersistenceRetentionPolicyModel
from core.database.models.runtime import (
    WorkflowEventModel,
    WorkflowNodeRunModel,
    WorkflowRunModel,
    WorkflowStateSnapshotModel,
)
from core.database.models.sentiment import SentimentSnapshotModel, SentimentSourceModel
from core.database.models.strategy import (
    StrategyHypothesisEvaluationModel,
    StrategyHypothesisModel,
    StrategySynthesisDecisionModel,
)
from core.database.models.telemetry import (
    AgentMetricModel,
    ProviderMetricModel,
    TelemetryEventModel,
    TelemetryMetricModel,
    TelemetryTraceModel,
    WorkflowMetricModel,
)

__all__ = [
    "AiObservabilityExportJobModel",
    "AiPromptProgramArtifactModel",
    "EvaluationArtifactModel",
    "EvaluationCaseModel",
    "EvaluationDatasetModel",
    "EvaluationMetricResultModel",
    "EvaluationRunModel",
    "BacktestArtifactModel",
    "BacktestFillModel",
    "BacktestMetricModel",
    "BacktestPortfolioSnapshotModel",
    "BacktestRunModel",
    "BacktestScenarioModel",
    "BacktestStepModel",
    "PersistenceAuditEventModel",
    "CompletedWorkflowRunModel",
    "CompletedWorkflowNodeOutputModel",
    "CompletedRunArtifactModel",
    "NewsArticleModel",
    "NewsAnalysisSnapshotModel",
    "SentimentSnapshotModel",
    "SentimentSourceModel",
    "StrategySynthesisDecisionModel",
    "StrategyHypothesisModel",
    "StrategyHypothesisEvaluationModel",
    "MarketBreadthSnapshotModel",
    "MarketContextSnapshotModel",
    "MarketEventSnapshotModel",
    "MarketIndicatorModel",
    "MarketOhlcvModel",
    "TechnicalAnalysisSnapshotModel",
    "WatchlistItemModel",
    "TradeSetupModel",
    "RecommendationRationaleModel",
    "RecommendationOutcomeModel",
    "RecommendationModel",
    "PersistenceLineageLinkModel",
    "EconomicCalendarEventModel",
    "MacroObservationModel",
    "MacroRegimeSnapshotModel",
    "PortfolioAllocationSnapshotModel",
    "PortfolioEquityHistoryPointModel",
    "PortfolioExposureSnapshotModel",
    "PortfolioPositionHistoryModel",
    "PortfolioPositionLatestModel",
    "PortfolioRiskSnapshotModel",
    "RagEmbeddingJobModel",
    "RagQueryLogModel",
    "RagGraphJobModel",
    "RagAnswerLogModel",
    "RagSourceEligibilityModel",
    "RagDocumentModel",
    "RagChunkModel",
    "AgentReasoningModel",
    "AgentRecommendationModel",
    "AgentRiskAssessmentModel",
    "RecommendationAttributionModel",
    "SignalAttributionModel",
    "AttributionRecordModel",
    "AgentSignalModel",
    "PortfolioStateHistoryModel",
    "PortfolioStateLatestModel",
    "WorkflowOutputProjectionJobModel",
    "ReportSectionModel",
    "ReportPublicationModel",
    "ReportModel",
    "ReportArtifactModel",
    "ReportVersionModel",
    "PersistenceRetentionPolicyModel",
    "AgentMetricModel",
    "ProviderMetricModel",
    "TelemetryEventModel",
    "TelemetryMetricModel",
    "TelemetryTraceModel",
    "WorkflowMetricModel",
    "WorkflowEventModel",
    "WorkflowNodeRunModel",
    "WorkflowRunModel",
    "WorkflowStateSnapshotModel",
]
