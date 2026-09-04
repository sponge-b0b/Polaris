from dishka import Provider, Scope, provide

from application.services.base import ServiceRunner
from application.services.news.news_service import NewsService
from application.services.sentiment.sentiment_service import SentimentService
from core.llm.llm_service import LLMService
from core.telemetry.emitters.intelligence_telemetry import IntelligenceTelemetry
from intelligence.research.news.news_agent import NewsAgent
from intelligence.research.sentiment.sentiment_agent import SentimentAgent


class IntelligenceResearchDIProvider(Provider):
    # This class provides components for the entire lifetime of the app
    scope = Scope.APP

    # News Agent
    @provide
    def provide_news_agent(
        self,
        llm_service: LLMService,
        news_service: NewsService,
        service_runner: ServiceRunner,
        intelligence_telemetry: IntelligenceTelemetry,
    ) -> NewsAgent:

        return NewsAgent(
            llm_service=llm_service,
            news_service=news_service,
            service_runner=service_runner,
            intelligence_telemetry=intelligence_telemetry,
        )

    # Sentiment Agent
    @provide
    def provide_sentiment_agent(
        self,
        llm_service: LLMService,
        sentiment_service: SentimentService,
        service_runner: ServiceRunner,
        intelligence_telemetry: IntelligenceTelemetry,
    ) -> SentimentAgent:

        return SentimentAgent(
            llm_service=llm_service,
            sentiment_service=sentiment_service,
            service_runner=service_runner,
            intelligence_telemetry=intelligence_telemetry,
        )
