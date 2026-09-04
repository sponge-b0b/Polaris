from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from application.decision_evidence.claim_binding import (
    DecisionEvidenceClaimBindingService,
)
from application.decision_evidence.persistence import (
    DecisionEvidencePacketPersistenceService,
)
from application.governance import (
    AutomatedDecisionAuditService,
    GovernedWorkflowExecutionService,
)
from application.governance.baseline_runtime_evidence import (
    BaselineRuntimeEvidencePersistenceService,
)
from application.governance.governed_execution_evidence_resolver import (
    CanonicalGovernedExecutionEvidenceLifecycle,
    GovernedExecutionEvidenceResolver,
)
from application.persistence.agent_signals import AgentSignalPersistenceService
from application.persistence.backtesting import BacktestPersistenceService
from application.persistence.diagnostics import DiagnosticsPersistenceService
from application.persistence.health import HealthPersistenceService
from application.persistence.lineage import LineagePersistenceService
from application.persistence.macro import MacroPersistenceService
from application.persistence.market import MarketPersistenceService
from application.persistence.news import NewsPersistenceService
from application.persistence.portfolio import PortfolioPersistenceService
from application.persistence.recommendations import RecommendationPersistenceService
from application.persistence.sentiment import SentimentPersistenceService
from application.persistence.strategy import StrategyPersistenceService
from application.presentation.sink_decision import PresentationSinkDecisionService
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
    PostgresBaselineRuntimeEvidenceRepository,
    PostgresDecisionEvidencePacketRepository,
    PostgresEvaluationPersistenceRepository,
    PostgresGovernedExecutionEvidenceSelectionRepository,
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
from core.workflow.execution.workflow_facade import WorkflowFacade


class ApplicationPersistenceDIProvider(Provider):
    """Request-scoped application persistence orchestration."""

    scope = Scope.REQUEST

    @provide
    def provide_health_persistence_service(
        self,
    ) -> HealthPersistenceService:
        return HealthPersistenceService()

    @provide
    def provide_diagnostics_persistence_service(
        self,
        health_service: HealthPersistenceService,
    ) -> DiagnosticsPersistenceService:
        return DiagnosticsPersistenceService(
            health_service=health_service,
        )

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
    def provide_baseline_runtime_evidence_repository(
        self,
        session: AsyncSession,
    ) -> PostgresBaselineRuntimeEvidenceRepository:
        return PostgresBaselineRuntimeEvidenceRepository(session)

    @provide
    def provide_baseline_runtime_evidence_persistence_service(
        self,
        repository: PostgresBaselineRuntimeEvidenceRepository,
    ) -> BaselineRuntimeEvidencePersistenceService:
        return BaselineRuntimeEvidencePersistenceService(repository)

    @provide
    def provide_governed_execution_evidence_selection_repository(
        self,
        session: AsyncSession,
    ) -> PostgresGovernedExecutionEvidenceSelectionRepository:
        return PostgresGovernedExecutionEvidenceSelectionRepository(session)

    @provide
    def provide_canonical_governed_execution_evidence_lifecycle(
        self,
        workflow_facade: WorkflowFacade,
        selection_repository: PostgresGovernedExecutionEvidenceSelectionRepository,
        baseline_runtime_evidence_persistence_service: (
            BaselineRuntimeEvidencePersistenceService
        ),
        decision_evidence_packet_persistence_service: (
            DecisionEvidencePacketPersistenceService
        ),
    ) -> CanonicalGovernedExecutionEvidenceLifecycle:
        return CanonicalGovernedExecutionEvidenceLifecycle(
            workflow_registry=workflow_facade.registry,
            selection_repository=selection_repository,
            baseline_evidence_service=baseline_runtime_evidence_persistence_service,
            packet_persistence_service=decision_evidence_packet_persistence_service,
        )

    @provide
    def provide_governed_execution_evidence_resolver(
        self,
        workflow_facade: WorkflowFacade,
        selection_repository: PostgresGovernedExecutionEvidenceSelectionRepository,
        baseline_runtime_evidence_persistence_service: (
            BaselineRuntimeEvidencePersistenceService
        ),
        decision_evidence_packet_persistence_service: (
            DecisionEvidencePacketPersistenceService
        ),
    ) -> GovernedExecutionEvidenceResolver:
        return GovernedExecutionEvidenceResolver(
            workflow_registry=workflow_facade.registry,
            selection_repository=selection_repository,
            baseline_evidence_service=baseline_runtime_evidence_persistence_service,
            packet_persistence_service=decision_evidence_packet_persistence_service,
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
        observability_manager: ObservabilityManager,
    ) -> AutomatedDecisionAuditService:
        return AutomatedDecisionAuditService(
            repository,
            observability_manager=observability_manager,
        )

    @provide
    def provide_governed_workflow_execution_service(
        self,
        workflow_facade: WorkflowFacade,
        automated_decision_audit_service: AutomatedDecisionAuditService,
        decision_evidence_packet_persistence_service: (
            DecisionEvidencePacketPersistenceService
        ),
        baseline_runtime_evidence_persistence_service: (
            BaselineRuntimeEvidencePersistenceService
        ),
        evidence_lifecycle: CanonicalGovernedExecutionEvidenceLifecycle,
        evidence_resolver: GovernedExecutionEvidenceResolver,
    ) -> GovernedWorkflowExecutionService:
        return GovernedWorkflowExecutionService(
            workflow_facade=workflow_facade,
            automated_decision_audit_service=automated_decision_audit_service,
            decision_evidence_packet_persistence_service=(
                decision_evidence_packet_persistence_service
            ),
            baseline_runtime_evidence_persistence_service=(
                baseline_runtime_evidence_persistence_service
            ),
            evidence_lifecycle=evidence_lifecycle,
            evidence_resolver=evidence_resolver,
        )

    @provide
    def provide_morning_report_persistence_service(
        self,
        repository: PostgresReportPersistenceRepository,
        claim_binding_service: DecisionEvidenceClaimBindingService,
        automated_decision_audit_service: AutomatedDecisionAuditService,
        observability_manager: ObservabilityManager,
    ) -> MorningReportPersistenceService:
        return MorningReportPersistenceService(
            repository,
            claim_binding_service=claim_binding_service,
            governed_output_release_service=automated_decision_audit_service,
            presentation_sink_decision_service=PresentationSinkDecisionService(
                observability_manager
            ),
        )
