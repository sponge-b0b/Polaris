from __future__ import annotations

from datetime import UTC, datetime
from time import perf_counter
from typing import Any

from application.observability import AiObservationStatus, static_prompt_hash
from application.services.base import ServiceRequest, ServiceRunner
from application.services.news.news_request import NewsRequest
from application.services.news.news_service import (
    NewsService,
)
from core.llm.llm_service import LLMService
from core.runtime.contracts.runtime_node import RuntimeNode
from core.runtime.state.runtime_context import RuntimeContext
from core.runtime.state.runtime_node_output import RuntimeNodeOutput
from core.telemetry.emitters.intelligence_telemetry import IntelligenceTelemetry
from domain.workflow_outputs import (
    NEWS_ANALYSIS_OUTPUT_CONTRACT,
    WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
)
from intelligence.observability import (
    IntelligenceAiObservabilityProjectorPort,
    IntelligenceAiObservabilityRecorder,
    llm_model_name,
    record_intelligence_generation_observation,
)
from intelligence.prompts.system.news_agent_prompt import (
    NEWS_AGENT_SYSTEM_PROMPT,
)
from intelligence.telemetry import telemetry_context_from_runtime

NEWS_AGENT_SYSTEM_PROMPT_HASH = static_prompt_hash(NEWS_AGENT_SYSTEM_PROMPT)


class NewsAgent(RuntimeNode):
    """
    Polaris News Agent

    RESPONSIBILITIES:
    -----------------
    - collect macro + market news
    - summarize relevant SPY drivers
    - extract market-moving themes
    - identify informational risk events
    - produce structured news intelligence

    IMPORTANT:
    ----------
    This agent:
    - DOES NOT perform execution decisions
    - DOES NOT produce trade recommendations
    - DOES produce structured RuntimeNodeOutput
    """

    node_name = "news_agent"
    node_type = "market_news"

    def __init__(
        self,
        news_service: NewsService,
        llm_service: LLMService,
        service_runner: ServiceRunner[Any, Any],
        intelligence_telemetry: IntelligenceTelemetry,
        ai_observability_projector: IntelligenceAiObservabilityProjectorPort
        | None = None,
    ) -> None:

        self.news_service = news_service
        self.llm_service = llm_service
        self.service_runner = service_runner
        self.intelligence_telemetry = intelligence_telemetry
        self.ai_observability = IntelligenceAiObservabilityRecorder(
            ai_observability_projector
        )

    # ============================================================
    # MAIN EXECUTION
    # ============================================================

    async def _execute(
        self,
        context: RuntimeContext,
    ) -> RuntimeNodeOutput:
        """
        Fetch + analyze news for SPY / macro environment.
        """

        # ========================================================
        # INPUTS
        # ========================================================

        symbol = context.workflow_inputs.get(
            "symbol",
            "SPY",
        )

        query = context.workflow_inputs.get(
            "query",
            ("SPY OR S&P 500 OR inflation OR Fed OR rates"),
        )

        # ========================================================
        # FETCH NEWS
        # ========================================================

        news_result = await self.service_runner.run(
            service=self.news_service,
            request=ServiceRequest(
                payload=NewsRequest(
                    query=str(query),
                    symbol=str(symbol),
                    limit=5,
                ),
                telemetry_context=telemetry_context_from_runtime(
                    context,
                    node_name=self.node_name,
                ),
            ),
        )
        news_result.raise_if_failed()

        if news_result.result is None:
            raise RuntimeError("News service returned no result data.")

        articles = news_result.result.to_list()
        observed_at = datetime.now(UTC)

        # ========================================================
        # LLM CONTEXT
        # ========================================================

        llm_context = self._build_llm_context(articles)

        # ========================================================
        # LLM INFERENCE
        # ========================================================

        llm_started_at = perf_counter()
        llm_status = AiObservationStatus.SUCCESS
        try:
            llm_response = await self.llm_service.chat(
                system_prompt=NEWS_AGENT_SYSTEM_PROMPT,
                response_format="json",
                messages=[
                    {
                        "role": "user",
                        "content": llm_context,
                    }
                ],
            )
        except Exception as error:
            llm_status = AiObservationStatus.FAILED
            await self.intelligence_telemetry.emit_agent_degraded(
                agent_name=self.node_name,
                reason="llm_inference_failure",
                error=error,
                context=telemetry_context_from_runtime(
                    context,
                    node_name=self.node_name,
                ),
            )
            llm_response = {
                "error": "llm_inference_failure",
                "message": str(error),
            }

        # ========================================================
        # LLM FAILURE HANDLING
        # ========================================================

        if not isinstance(llm_response, dict) or "error" in llm_response:
            await record_intelligence_generation_observation(
                self.ai_observability,
                context=context,
                node_name=self.node_name,
                component_name="news_llm_reasoning",
                status=AiObservationStatus.DEGRADED,
                latency_seconds=perf_counter() - llm_started_at,
                model_name=llm_model_name(self.llm_service),
                provider_name="LLMService",
                prompt_name="news_agent_system_prompt",
                prompt_version="static-v1",
                prompt_hash=NEWS_AGENT_SYSTEM_PROMPT_HASH,
                input_shape=(
                    f"context_characters={len(llm_context)};"
                    f"article_count={len(articles)}"
                ),
                output_shape="fallback=true",
                metadata={
                    "symbol": str(symbol),
                    "query": str(query),
                    "article_count": len(articles),
                    "fallback": True,
                    "llm_failed": llm_status is AiObservationStatus.FAILED,
                },
            )
            return RuntimeNodeOutput.success_output(
                outputs=dict(
                    observed_at=observed_at.isoformat(),
                    news_source="NewsService",
                    symbol=str(symbol),
                    query=str(query),
                    news_articles=articles,
                    directional_score=0.0,
                    confidence=0.0,
                    regime="llm_inference_failure",
                    signals=[
                        "llm_inference_failure",
                    ],
                    risks=[
                        "llm_inference_failure",
                    ],
                    recommendations=[
                        "llm_inference_failure",
                    ],
                    features={
                        "error": "llm_inference_failure",
                    },
                    llm_response=llm_response,
                ),
                execution_metadata={
                    "node_name": self.node_name,
                    "node_type": self.node_type,
                    "confidence": (0.0),
                    **(
                        {
                            "query": query,
                            "articles_retrieved": len(articles),
                            "failure": True,
                            "quality_status": "degraded",
                        }
                    ),
                },
                output_contract=NEWS_ANALYSIS_OUTPUT_CONTRACT,
                output_schema_version=WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
            )

        # ========================================================
        # MARKET RELEVANCE
        # ========================================================

        market_relevance = str(
            llm_response.get(
                "market_relevance",
                "neutral",
            )
        ).lower()

        directional_score = self._determine_directional_score(market_relevance)

        # ========================================================
        # CONFIDENCE
        # ========================================================

        confidence = self._calculate_confidence(
            articles=articles,
            llm_response=llm_response,
        )

        await record_intelligence_generation_observation(
            self.ai_observability,
            context=context,
            node_name=self.node_name,
            component_name="news_llm_reasoning",
            status=llm_status,
            latency_seconds=perf_counter() - llm_started_at,
            model_name=llm_model_name(self.llm_service),
            provider_name="LLMService",
            prompt_name="news_agent_system_prompt",
            prompt_version="static-v1",
            prompt_hash=NEWS_AGENT_SYSTEM_PROMPT_HASH,
            input_shape=(
                f"context_characters={len(llm_context)};article_count={len(articles)}"
            ),
            output_shape=f"response_keys={len(llm_response)}",
            metadata={
                "symbol": str(symbol),
                "query": str(query),
                "article_count": len(articles),
                "market_relevance": market_relevance,
                "confidence": confidence,
                "fallback": False,
            },
        )

        # ========================================================
        # SIGNALS
        # ========================================================

        signals = llm_response.get("signals", [])

        themes = llm_response.get(
            "themes",
            [],
        )
        for theme in themes:
            signals.append(f"theme:{theme}")

        # ========================================================
        # RISKS
        # ========================================================

        risks = llm_response.get("risks", [])

        # ========================================================
        # RECOMMENDATIONS
        # ========================================================

        recommendations = llm_response.get("recommendations", [])

        # ========================================================
        # FEATURES
        # ========================================================

        features = {
            "headline_count": len(articles),
            "market_relevance": market_relevance,
            "primary_themes": themes,
            "articles": articles,
            "query": query,
        }

        # ========================================================
        # RUNTIME RESULT
        # ========================================================

        result = dict(
            observed_at=observed_at.isoformat(),
            news_source="NewsService",
            symbol=str(symbol),
            query=str(query),
            news_articles=articles,
            directional_score=directional_score,
            confidence=confidence,
            regime=market_relevance,
            signals=signals,
            risks=risks,
            recommendations=recommendations,
            features=features,
            llm_response=llm_response,
        )

        await self.intelligence_telemetry.emit_agent_signal(
            agent_name=self.node_name,
            signal_name="news.market_signal",
            confidence=confidence,
            context=telemetry_context_from_runtime(
                context,
                node_name=self.node_name,
            ),
            payload={
                "directional_score": directional_score,
                "market_relevance": market_relevance,
                "articles_retrieved": len(articles),
            },
        )

        # ========================================================
        # FINAL OUTPUT
        # ========================================================

        return RuntimeNodeOutput.success_output(
            outputs=result,
            execution_metadata={
                "node_name": self.node_name,
                "node_type": self.node_type,
                "confidence": (confidence),
                **(
                    {
                        "symbol": symbol,
                        "query": query,
                        "articles_retrieved": len(articles),
                        "quality_status": "normal",
                    }
                ),
            },
            output_contract=NEWS_ANALYSIS_OUTPUT_CONTRACT,
            output_schema_version=WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
        )

    # ============================================================
    # DIRECTIONAL SCORE
    # ============================================================

    def _determine_directional_score(
        self,
        relevance: str,
    ) -> float:
        """
        Canonical directional mapping.

        RANGE:
        ------
        +1.0 = strongly bullish
         0.0 = neutral
        -1.0 = strongly bearish
        """

        mapping = {
            "strong_bullish": 0.90,
            "bullish": 0.60,
            "neutral": 0.00,
            "bearish": -0.60,
            "strong_bearish": -0.90,
        }

        return float(
            mapping.get(
                relevance,
                0.0,
            )
        )

    # ============================================================
    # CONFIDENCE MODEL
    # ============================================================

    def _calculate_confidence(
        self,
        articles: list[dict],
        llm_response: dict[str, Any],
    ) -> float:
        """
        Deterministic confidence model.
        """

        confidence = 0.45

        # ========================================================
        # ARTICLE COUNT
        # ========================================================

        article_count = len(articles)

        if article_count >= 5:
            confidence += 0.20

        elif article_count >= 3:
            confidence += 0.10

        # ========================================================
        # THEMATIC CONSISTENCY
        # ========================================================

        themes = llm_response.get(
            "themes",
            [],
        )

        if len(themes) >= 3:
            confidence += 0.10

        # ========================================================
        # MARKET RELEVANCE
        # ========================================================

        relevance = str(
            llm_response.get(
                "market_relevance",
                "neutral",
            )
        ).lower()

        if relevance != "neutral":
            confidence += 0.10

        # ========================================================
        # HARD CLAMP
        # ========================================================

        confidence = max(
            0.0,
            min(confidence, 1.0),
        )

        return confidence

    # ============================================================
    # BUILD LLM CONTEXT
    # ============================================================

    def _build_llm_context(
        self,
        articles: list[dict],
    ) -> str:
        """
        Convert articles into structured
        LLM-readable market context.
        """

        # ============================================================
        # EMPTY STATE
        # ============================================================

        if not articles:
            return """
    NEWS SYSTEM STATE
    ======================

    No relevant market news articles were retrieved.

    ========================================================

    TASK

    Analyze current macro and market news conditions for SPY.

    Focus on:
    - macroeconomic developments
    - Fed policy implications
    - inflation narratives
    - liquidity conditions
    - geopolitical risks
    - earnings/macro spillover risk
    - market-moving catalysts

    Return structured JSON only.
    """

        # ============================================================
        # ARTICLE BLOCKS
        # ============================================================

        text_blocks = []

        for idx, article in enumerate(
            articles,
            start=1,
        ):
            title = article.get(
                "title",
                "",
            )

            description = article.get(
                "description",
                "",
            )

            source_name = article.get(
                "source",
                "unknown",
            )

            published_at = article.get(
                "published_at",
                "",
            )

            text_blocks.append(
                f"""
    ARTICLE {idx}
    ======================

    Source:
    {source_name}

    Published:
    {published_at}

    Title:
    {title}

    Description:
    {description}
    """
            )

        # ============================================================
        # FINAL CONTEXT
        # ============================================================

        article_context = "\n".join(text_blocks)

        return f"""
    NEWS SYSTEM STATE
    ======================

    Retrieved Articles:
    {len(articles)}

    ========================================================

    ARTICLE FLOW

    {article_context}

    ========================================================

    TASK

    Analyze the current macro and market news environment for SPY.

    Focus on:
    - Fed policy developments
    - inflation narratives
    - interest rate expectations
    - liquidity conditions
    - macroeconomic risks
    - geopolitical instability
    - earnings spillover effects
    - broad market catalysts
    - systemic market risks

    Evaluate:
    - whether headlines are risk-on or risk-off
    - whether macro conditions are stabilizing or deteriorating
    - whether market-moving narratives are strengthening
    - whether event clustering increases volatility risk

    Do NOT:
    - generate trade recommendations
    - exaggerate headlines
    - use sensational language
    - provide certainty statements

    Return structured JSON only.
    """
