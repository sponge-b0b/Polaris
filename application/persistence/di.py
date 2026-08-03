from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from application.decision_evidence.claim_binding import (
    DecisionEvidenceClaimBindingService,
)
from application.decision_evidence.persistence import (
    DecisionEvidencePacketPersistenceService,
)
from application.governance import AutomatedDecisionAuditService
from application.persistence.agent_signals import AgentSignalPersistenceService
from application.persistence.backtesting import BacktestPersistenceService
from application.persistence.lineage import LineagePersistenceService
from application.persistence.macro import MacroPersistenceService
from application.persistence.market import MarketPersistenceService
from application.persistence.news import NewsPersistenceService
from application.persistence.portfolio import PortfolioPersistenceService
from application.persistence.recommendations import RecommendationPersistenceService
from application.persistence.sentiment import SentimentPersistenceService
from application.persistence.strategy import StrategyPersistenceService
from application.reports import MorningReportPersistenceService
from core.storage.persistence.completed_run_archive import CompletedRunArchive
from core.storage.persistence.portfolio import (
    PortfolioExpansionPersistenceRepository,
)
from core.storage.persistence.portfolio.portfolio_state_repository import (
    PortfolioStateRepository,
)
from core.storage.persistence.repositories import (
    PostgresAgentSignalPersistenceRepository,
    PostgresAutomatedDecisionAuditRepository,
    PostgresBacktestPersistenceRepository,
    PostgresDecisionEvidencePacketRepository,
    PostgresEvaluationPersistenceRepository,
    PostgresMacroPersistenceRepository,
    PostgresMarketPersistenceRepository,
    PostgresNewsPersistenceRepository,
    PostgresPersistenceLineageLinkRepository,
    PostgresRagPersistenceRepository,
    PostgresRecommendationPersistenceRepository,
    PostgresReportPersistenceRepository,
    PostgresSentimentPersistenceRepository,
    PostgresStrategyPersistenceRepository,
    PostgresTelemetryPersistenceRepository,
)
from core.telemetry.emitters.application_service_telemetry import (
    ApplicationServiceTelemetry,
)
from core.telemetry.observability import ObservabilityManager


class ApplicationPersistenceDIProvider(Provider):
    """Request-scoped application persistence orchestration."""

    scope = Scope.REQUEST

    @provide
    def provide_portfolio_persistence_service(
        self,
        expansion_repository: PortfolioExpansionPersistenceRepository,
        state_repository: PortfolioStateRepository,
    ) -> PortfolioPersistenceService:
        return PortfolioPersistenceService(
            expansion_repository,
            state_repository,
        )

    @provide
    def provide_market_persistence_repository(
        self,
        session: AsyncSession,
    ) -> PostgresMarketPersistenceRepository:
        return PostgresMarketPersistenceRepository(session)

    @provide
    def provide_market_persistence_service(
        self,
        repository: PostgresMarketPersistenceRepository,
    ) -> MarketPersistenceService:
        return MarketPersistenceService(repository)

    @provide
    def provide_macro_persistence_repository(
        self,
        session: AsyncSession,
    ) -> PostgresMacroPersistenceRepository:
        return PostgresMacroPersistenceRepository(session)

    @provide
    def provide_macro_persistence_service(
        self,
        repository: PostgresMacroPersistenceRepository,
    ) -> MacroPersistenceService:
        return MacroPersistenceService(repository)

    @provide
    def provide_news_persistence_repository(
        self,
        session: AsyncSession,
    ) -> PostgresNewsPersistenceRepository:
        return PostgresNewsPersistenceRepository(session)

    @provide
    def provide_news_persistence_service(
        self,
        repository: PostgresNewsPersistenceRepository,
    ) -> NewsPersistenceService:
        return NewsPersistenceService(repository)

    @provide
    def provide_sentiment_persistence_repository(
        self,
        session: AsyncSession,
    ) -> PostgresSentimentPersistenceRepository:
        return PostgresSentimentPersistenceRepository(session)

    @provide
    def provide_sentiment_persistence_service(
        self,
        repository: PostgresSentimentPersistenceRepository,
    ) -> SentimentPersistenceService:
        return SentimentPersistenceService(repository)

    @provide
    def provide_agent_signal_persistence_repository(
        self,
        session: AsyncSession,
    ) -> PostgresAgentSignalPersistenceRepository:
        return PostgresAgentSignalPersistenceRepository(session)

    @provide
    def provide_agent_signal_persistence_service(
        self,
        repository: PostgresAgentSignalPersistenceRepository,
    ) -> AgentSignalPersistenceService:
        return AgentSignalPersistenceService(repository)

    @provide
    def provide_strategy_persistence_repository(
        self,
        session: AsyncSession,
    ) -> PostgresStrategyPersistenceRepository:
        return PostgresStrategyPersistenceRepository(session)

    @provide
    def provide_strategy_persistence_service(
        self,
        repository: PostgresStrategyPersistenceRepository,
    ) -> StrategyPersistenceService:
        return StrategyPersistenceService(repository)

    @provide
    def provide_decision_evidence_packet_repository(
        self,
        session: AsyncSession,
        observability_manager: ObservabilityManager,
    ) -> PostgresDecisionEvidencePacketRepository:
        return PostgresDecisionEvidencePacketRepository(
            session,
            observability_manager=observability_manager,
        )

    @provide
    def provide_decision_evidence_rag_repository(
        self,
        session: AsyncSession,
    ) -> PostgresRagPersistenceRepository:
        return PostgresRagPersistenceRepository(session)

    @provide
    def provide_decision_evidence_evaluation_repository(
        self,
        session: AsyncSession,
    ) -> PostgresEvaluationPersistenceRepository:
        return PostgresEvaluationPersistenceRepository(session)

    @provide
    def provide_decision_evidence_trace_repository(
        self,
        session: AsyncSession,
    ) -> PostgresTelemetryPersistenceRepository:
        return PostgresTelemetryPersistenceRepository(session)

    @provide
    def provide_decision_evidence_packet_persistence_service(
        self,
        repository: PostgresDecisionEvidencePacketRepository,
        completed_run_archive: CompletedRunArchive,
        rag_repository: PostgresRagPersistenceRepository,
        evaluation_repository: PostgresEvaluationPersistenceRepository,
        trace_repository: PostgresTelemetryPersistenceRepository,
        application_service_telemetry: ApplicationServiceTelemetry,
    ) -> DecisionEvidencePacketPersistenceService:
        return DecisionEvidencePacketPersistenceService(
            repository=repository,
            completed_run_archive=completed_run_archive,
            evaluation_repository=evaluation_repository,
            rag_repository=rag_repository,
            trace_repository=trace_repository,
            telemetry=application_service_telemetry,
        )

    @provide
    def provide_decision_evidence_claim_binding_service(
        self,
        packet_persistence_service: DecisionEvidencePacketPersistenceService,
    ) -> DecisionEvidenceClaimBindingService:
        return DecisionEvidenceClaimBindingService(packet_persistence_service)

    @provide
    def provide_lineage_persistence_repository(
        self,
        session: AsyncSession,
    ) -> PostgresPersistenceLineageLinkRepository:
        return PostgresPersistenceLineageLinkRepository(session)

    @provide
    def provide_lineage_persistence_service(
        self,
        repository: PostgresPersistenceLineageLinkRepository,
    ) -> LineagePersistenceService:
        return LineagePersistenceService(repository)

    @provide
    def provide_recommendation_persistence_repository(
        self,
        session: AsyncSession,
        observability_manager: ObservabilityManager,
    ) -> PostgresRecommendationPersistenceRepository:
        return PostgresRecommendationPersistenceRepository(
            session,
            observability_manager=observability_manager,
        )

    @provide
    def provide_recommendation_persistence_service(
        self,
        repository: PostgresRecommendationPersistenceRepository,
    ) -> RecommendationPersistenceService:
        return RecommendationPersistenceService(repository)

    @provide
    def provide_backtest_persistence_service(
        self,
        repository: PostgresBacktestPersistenceRepository,
    ) -> BacktestPersistenceService:
        return BacktestPersistenceService(repository)

    @provide
    def provide_automated_decision_audit_repository(
        self,
        session: AsyncSession,
    ) -> PostgresAutomatedDecisionAuditRepository:
        return PostgresAutomatedDecisionAuditRepository(session)

    @provide
    def provide_automated_decision_audit_service(
        self,
        repository: PostgresAutomatedDecisionAuditRepository,
    ) -> AutomatedDecisionAuditService:
        return AutomatedDecisionAuditService(repository)

    @provide
    def provide_morning_report_persistence_service(
        self,
        repository: PostgresReportPersistenceRepository,
        claim_binding_service: DecisionEvidenceClaimBindingService,
        automated_decision_audit_service: AutomatedDecisionAuditService,
    ) -> MorningReportPersistenceService:
        return MorningReportPersistenceService(
            repository,
            claim_binding_service=claim_binding_service,
            governed_output_release_service=automated_decision_audit_service,
        )
