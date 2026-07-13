from __future__ import annotations

from datetime import UTC
from datetime import datetime
from time import perf_counter
from typing import Any, Dict

from application.observability import AiObservationStatus
from application.observability import static_prompt_hash
from core.llm.llm_service import LLMService

from core.runtime.contracts.runtime_node import RuntimeNode
from core.runtime.state.runtime_context import RuntimeContext
from core.runtime.state.runtime_node_output import RuntimeNodeOutput

from intelligence.prompts.system.sentiment_agent_prompt import (
    SENTIMENT_AGENT_SYSTEM_PROMPT,
)

from intelligence.observability import IntelligenceAiObservabilityProjectorPort
from intelligence.observability import IntelligenceAiObservabilityRecorder
from intelligence.observability import llm_model_name
from intelligence.observability import record_intelligence_generation_observation
from intelligence.telemetry import telemetry_context_from_runtime

from application.services.sentiment.sentiment_service import (
    SentimentService,
)
from application.services.base import ServiceRequest
from application.services.base import ServiceRunner
from application.services.sentiment.sentiment_request import (
    SentimentSnapshotRequest,
)
from core.telemetry.emitters.intelligence_telemetry import IntelligenceTelemetry
from domain.workflow_outputs import (
    SENTIMENT_SNAPSHOT_OUTPUT_CONTRACT,
    WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
)


SENTIMENT_AGENT_SYSTEM_PROMPT_HASH = static_prompt_hash(SENTIMENT_AGENT_SYSTEM_PROMPT)


class SentimentAgent(RuntimeNode):
    """
    Polaris Sentiment Agent

    PURPOSE:
    --------
    - consume deterministic sentiment regime engine
    - enrich interpretation via LLM
    - normalize sentiment into RuntimeNodeOutput.outputs
    - provide behavioral/risk context
    - NEVER generate trade signals directly

    ARCHITECTURE:
    -------------
    Deterministic Layer:
        SentimentService

    Interpretive Layer:
        LLM synthesis

    Canonical Output:
        RuntimeNodeOutput.outputs sentiment payload
    """

    node_name = "sentiment_agent"
    node_type = "market_sentiment"

    def __init__(
        self,
        sentiment_service: SentimentService,
        llm_service: LLMService,
        service_runner: ServiceRunner[Any, Any],
        intelligence_telemetry: IntelligenceTelemetry,
        ai_observability_projector: IntelligenceAiObservabilityProjectorPort
        | None = None,
    ) -> None:

        self.sentiment_service = sentiment_service
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

        # ========================================================
        # INPUTS
        # ========================================================

        symbol = context.workflow_inputs.get(
            "symbol",
            "SPY",
        )

        # ========================================================
        # DETERMINISTIC SENTIMENT PIPELINE
        # ========================================================

        sentiment_result = await self.service_runner.run(
            service=self.sentiment_service,
            request=ServiceRequest(
                payload=SentimentSnapshotRequest(
                    symbol=str(symbol),
                ),
                telemetry_context=telemetry_context_from_runtime(
                    context,
                    node_name=self.node_name,
                ),
            ),
        )
        sentiment_result.raise_if_failed()

        if sentiment_result.result is None:
            raise RuntimeError("Sentiment service returned no result data.")

        sentiment_data = sentiment_result.result
        observed_at = datetime.now(UTC)

        sentiment = sentiment_data.sentiment
        features = sentiment_data.features

        # ========================================================
        # CORE DETERMINISTIC SIGNALS
        # ========================================================

        composite_sentiment = float(
            sentiment.get(
                "composite_sentiment",
                0.5,
            )
        )

        # ========================================================
        # NORMALIZE:
        #
        # Service and runtime ranges are both -1 → +1.
        # ========================================================

        directional_score = max(
            -1.0,
            min(1.0, composite_sentiment),
        )

        deterministic_confidence = float(
            sentiment.get(
                "confidence",
                0.5,
            )
        )

        regime = sentiment.get(
            "regime",
            "neutral",
        )

        # ========================================================
        # BUILD LLM CONTEXT
        # ========================================================

        llm_context = self._build_llm_context(sentiment_data.to_dict())

        # ========================================================
        # LLM INFERENCE
        # ========================================================

        llm_started_at = perf_counter()
        llm_status = AiObservationStatus.SUCCESS
        try:
            llm_response = self.llm_service.chat(
                system_prompt=(SENTIMENT_AGENT_SYSTEM_PROMPT),
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
        # LLM FAILURE SAFETY
        # ========================================================

        if not isinstance(llm_response, Dict) or "error" in llm_response:
            llm_status = AiObservationStatus.DEGRADED
            llm_response = {
                "summary": ("Sentiment interpretation unavailable."),
                "sentiment_bias": regime,
                "fear_greed_state": "neutral",
                "positioning_state": "balanced",
                "sentiment_score": directional_score,
                "confidence": deterministic_confidence,
                "signals": [],
                "risks": [
                    "llm_inference_failure",
                ],
                "recommendations": [
                    "fallback_to_deterministic_sentiment",
                ],
            }

        # ========================================================
        # FINAL CONFIDENCE
        # ========================================================

        llm_confidence = float(
            llm_response.get(
                "confidence",
                deterministic_confidence,
            )
        )

        confidence = deterministic_confidence * 0.75 + llm_confidence * 0.25

        confidence = max(
            0.0,
            min(1.0, confidence),
        )

        await record_intelligence_generation_observation(
            self.ai_observability,
            context=context,
            node_name=self.node_name,
            component_name="sentiment_llm_reasoning",
            status=llm_status,
            latency_seconds=perf_counter() - llm_started_at,
            model_name=llm_model_name(self.llm_service),
            provider_name="LLMService",
            prompt_name="sentiment_agent_system_prompt",
            prompt_version="static-v1",
            prompt_hash=SENTIMENT_AGENT_SYSTEM_PROMPT_HASH,
            input_shape=(
                f"context_characters={len(llm_context)};"
                f"sentiment_fields={len(sentiment)};"
                f"feature_fields={len(features)}"
            ),
            output_shape=f"response_keys={len(llm_response)}",
            metadata={
                "symbol": str(symbol),
                "regime": str(regime),
                "confidence": confidence,
                "fallback": llm_status is not AiObservationStatus.SUCCESS,
            },
        )

        # ========================================================
        # SIGNALS
        # ========================================================

        signals = [
            regime,
            llm_response.get(
                "sentiment_bias",
                "neutral",
            ),
            llm_response.get(
                "fear_greed_state",
                "neutral",
            ),
            llm_response.get(
                "positioning_state",
                "balanced",
            ),
            "sentiment_fusion",
        ]

        momentum = features.get("momentum")

        if momentum is not None:
            signals.append(f"momentum_{momentum}")

        # ========================================================
        # RISKS
        # ========================================================

        risks = list(
            llm_response.get(
                "risks",
                [],
            )
        )

        deterministic_risks = [
            "sentiment_regime_shift_risk",
            "macro_event_repricing_risk",
            "crowd_positioning_instability",
        ]

        for risk in deterministic_risks:
            if risk not in risks:
                risks.append(risk)

        # ========================================================
        # RECOMMENDATIONS
        # ========================================================

        recommendations = list(
            llm_response.get(
                "recommendations",
                [],
            )
        )

        deterministic_recommendations = [
            ("Use sentiment as contextual confirmation not primary signal generation"),
            ("Cross-check sentiment with technical and macro structure"),
            ("Reduce aggression during unstable sentiment transitions"),
        ]

        for recommendation in deterministic_recommendations:
            if recommendation not in recommendations:
                recommendations.append(recommendation)

        # ========================================================
        # FEATURES
        # ========================================================

        result_features = {
            "composite_sentiment": composite_sentiment,
            "stability": features.get("stability"),
            "momentum": features.get("momentum"),
            "divergence": features.get("divergence"),
            "risk_multiplier": features.get("risk_multiplier"),
            "components": features.get(
                "components",
                {},
            ),
            "fear_greed_state": llm_response.get("fear_greed_state"),
            "positioning_state": llm_response.get("positioning_state"),
            "sentiment_bias": llm_response.get("sentiment_bias"),
        }

        # ========================================================
        # BUILD RUNTIME RESULT
        # ========================================================

        result = dict(
            observed_at=observed_at.isoformat(),
            sentiment_source="SentimentService",
            sentiment_universe="single_symbol",
            symbol=str(symbol),
            directional_score=directional_score,
            confidence=confidence,
            regime=regime,
            signals=signals,
            risks=risks,
            recommendations=recommendations,
            features=result_features,
            sentiment_snapshot=sentiment,
            sentiment_source_data=sentiment_data.to_dict(),
            llm_response={
                "summary": llm_response.get("summary", ""),
                "sentiment_bias": llm_response.get(
                    "sentiment_bias",
                    "neutral",
                ),
                "fear_greed_state": llm_response.get(
                    "fear_greed_state",
                    "neutral",
                ),
                "positioning_state": llm_response.get(
                    "positioning_state",
                    "balanced",
                ),
            },
        )

        await self.intelligence_telemetry.emit_agent_signal(
            agent_name=self.node_name,
            signal_name="sentiment.market_signal",
            confidence=confidence,
            context=telemetry_context_from_runtime(
                context,
                node_name=self.node_name,
            ),
            payload={
                "directional_score": directional_score,
                "regime": regime,
                "composite_sentiment": composite_sentiment,
            },
        )

        # ========================================================
        # RETURN CANONICAL OUTPUT
        # ========================================================

        return RuntimeNodeOutput.success_output(
            outputs=result,
            execution_metadata={
                "node_name": self.node_name,
                "node_type": self.node_type,
                "confidence": confidence,
                **(
                    {
                        "symbol": symbol,
                        "deterministic_regime": regime,
                        "sentiment_snapshot": sentiment,
                        "quality_status": "normal",
                    }
                ),
            },
            output_contract=SENTIMENT_SNAPSHOT_OUTPUT_CONTRACT,
            output_schema_version=WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
        )

    # ============================================================
    # BUILD LLM CONTEXT
    # ============================================================

    def _build_llm_context(
        self,
        sentiment_data: Dict[str, Any],
    ) -> str:

        sentiment = sentiment_data.get(
            "sentiment",
            {},
        )

        features = sentiment_data.get(
            "features",
            {},
        )

        components = features.get(
            "components",
            {},
        )

        return f"""
SENTIMENT SYSTEM STATE
======================

Composite Sentiment:
{sentiment.get("composite_sentiment")}

Regime:
{sentiment.get("regime")}

Confidence:
{sentiment.get("confidence")}

Momentum:
{features.get("momentum")}

Stability:
{features.get("stability")}

Divergence:
{features.get("divergence")}

Risk Multiplier:
{features.get("risk_multiplier")}

========================================================

COMPONENT BREAKDOWN

News:
{components.get("news")}

Social:
{components.get("social")}

Insider:
{components.get("insider")}

Fear & Greed:
{components.get("fear_greed")}

========================================================

TASK

Analyze current market psychology for SPY.

Focus on:
- fear vs greed
- positioning risk
- emotional extremes
- sentiment instability
- behavioral risk conditions

Return structured JSON only.
"""
