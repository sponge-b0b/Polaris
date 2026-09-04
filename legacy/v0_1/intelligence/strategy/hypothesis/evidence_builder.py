from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from application.services.base import ServiceRequest, ServiceRunner
from application.services.market_events.market_events_request import MarketEventsRequest
from application.services.market_events.market_events_result import MarketEventsResult
from application.services.market_events.market_events_service import MarketEventsService
from core.runtime.contracts.runtime_node import RuntimeNode
from core.runtime.state.runtime_context import RuntimeContext
from core.runtime.state.runtime_node_output import RuntimeNodeOutput
from core.telemetry.emitters.intelligence_telemetry import IntelligenceTelemetry
from domain.workflow_outputs import (
    STRATEGY_EVIDENCE_CONTEXT_OUTPUT_CONTRACT,
    WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
)
from intelligence.strategy.hypothesis.context import (
    StrategyEvidenceContext,
    StrategyEvidenceInputStatus,
)
from intelligence.strategy.hypothesis.normalization import (
    normalize_strategy_evidence_context,
)
from intelligence.strategy.market_context import extract_symbol_constituents
from intelligence.telemetry import telemetry_context_from_runtime


class StrategyEvidenceBuilder(RuntimeNode):
    """Build the shared strategy evidence context from canonical runtime evidence."""

    node_name = "strategy_evidence_builder"
    node_type = "strategy_evidence_builder"
    node_version = "1.0.0"

    def __init__(
        self,
        *,
        events_service: MarketEventsService,
        service_runner: ServiceRunner[Any, Any],
        intelligence_telemetry: IntelligenceTelemetry,
    ) -> None:
        self.events_service = events_service
        self.service_runner = service_runner
        self.intelligence_telemetry = intelligence_telemetry

    async def _execute(
        self,
        context: RuntimeContext,
    ) -> RuntimeNodeOutput:
        symbol = _string_value(context.workflow_inputs.get("symbol"), default="SPY")
        as_of = _optional_string(context.workflow_inputs.get("as_of"))
        node_outputs = dict(context.node_outputs)

        market_events_output, market_events_status = await self._market_events_output(
            context=context,
            symbol=symbol,
        )
        node_outputs["market_events"] = market_events_output

        evidence_context = normalize_strategy_evidence_context(
            node_outputs,
            symbol=symbol,
            as_of=as_of,
        )
        evidence_fingerprint = evidence_context.evidence_fingerprint()

        if _has_evidence_degradation(
            evidence_context=evidence_context,
            market_events_status=market_events_status,
        ):
            await self._emit_evidence_degradation_telemetry(
                context=context,
                evidence_context=evidence_context,
                evidence_fingerprint=evidence_fingerprint,
                market_events_status=market_events_status,
            )

        return RuntimeNodeOutput.success_output(
            outputs={
                "strategy_evidence_context": evidence_context.to_dict(),
                "evidence_fingerprint": evidence_fingerprint,
                "symbol": evidence_context.symbol,
                "market_events_status": market_events_status,
                "missing_required_inputs": evidence_context.has_missing_required_inputs,
                "degraded_required_inputs": (
                    evidence_context.has_degraded_required_inputs
                ),
            },
            execution_metadata={
                "evidence_fingerprint": evidence_fingerprint,
                "required_evidence_count": len(evidence_context.required_evidence),
                "optional_evidence_count": len(evidence_context.optional_evidence),
                "market_events_status": market_events_status,
            },
            output_contract=STRATEGY_EVIDENCE_CONTEXT_OUTPUT_CONTRACT,
            output_schema_version=WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
        )

    async def _market_events_output(
        self,
        *,
        context: RuntimeContext,
        symbol: str,
    ) -> tuple[dict[str, object], str]:
        request = ServiceRequest(
            payload=MarketEventsRequest(
                symbol=symbol,
                lookahead_days=_int_value(
                    context.workflow_inputs.get("event_lookahead_days"),
                    default=10,
                ),
                horizon=_string_value(
                    context.workflow_inputs.get("horizon"),
                    default="3month",
                ),
                symbol_constituents=_symbol_constituents(context.node_outputs),
            ),
            telemetry_context=telemetry_context_from_runtime(
                context,
                node_name=self.node_name,
            ),
        )
        try:
            service_result = await self.service_runner.run(
                service=self.events_service,
                request=request,
            )
            service_result.raise_if_failed()
        except Exception as exc:
            return _degraded_market_events_output(
                symbol=symbol,
                reason=str(exc) or type(exc).__name__,
            ), "degraded"

        if service_result.result is None:
            return _degraded_market_events_output(
                symbol=symbol,
                reason="market events service returned no result",
            ), "degraded"

        return _available_market_events_output(service_result.result), "available"

    async def _emit_evidence_degradation_telemetry(
        self,
        *,
        context: RuntimeContext,
        evidence_context: StrategyEvidenceContext,
        evidence_fingerprint: str,
        market_events_status: str,
    ) -> None:
        degraded_inputs = tuple(
            quality
            for quality in evidence_context.input_quality
            if quality.status is not StrategyEvidenceInputStatus.AVAILABLE
        )
        await self.intelligence_telemetry.emit_agent_signal(
            agent_name=self.node_name,
            signal_name="strategy_evidence_context.degraded",
            confidence=(0.0 if evidence_context.has_missing_required_inputs else 0.25),
            context=telemetry_context_from_runtime(
                context,
                node_name=self.node_name,
                attributes={"telemetry_reason": "evidence_context_degraded"},
            ),
            payload={
                "symbol": evidence_context.symbol,
                "evidence_fingerprint": evidence_fingerprint,
                "market_events_status": market_events_status,
                "missing_required_inputs": (
                    evidence_context.has_missing_required_inputs
                ),
                "degraded_required_inputs": (
                    evidence_context.has_degraded_required_inputs
                ),
                "required_evidence_count": len(evidence_context.required_evidence),
                "optional_evidence_count": len(evidence_context.optional_evidence),
                "input_quality": [quality.to_dict() for quality in degraded_inputs],
            },
        )


def _has_evidence_degradation(
    *,
    evidence_context: StrategyEvidenceContext,
    market_events_status: str,
) -> bool:
    return (
        market_events_status == "degraded"
        or evidence_context.has_missing_required_inputs
        or evidence_context.has_degraded_required_inputs
    )


def _available_market_events_output(
    result: MarketEventsResult,
) -> dict[str, object]:
    confidence = 1.0 if result.event_count else 0.5
    return {
        "symbol": result.symbol,
        "confidence": confidence,
        "features": {
            "event_pressure": result.market_pressure_score,
            "event_bias": result.regime_bias,
            "event_volatility": result.volatility_pressure,
            "volatility_forecast": result.volatility_forecast,
            "event_count": result.event_count,
            "high_impact_count": result.high_impact_count,
        },
        "market_events": result.to_dict(),
    }


def _degraded_market_events_output(
    *,
    symbol: str,
    reason: str,
) -> dict[str, object]:
    return {
        "symbol": symbol,
        "event_error": reason,
        "features": {
            "event_error": reason,
        },
    }


def _symbol_constituents(
    node_outputs: Mapping[str, object],
) -> frozenset[str]:
    technical_output = _unwrap_outputs(node_outputs.get("technical_agent"))
    technical_features = _mapping(technical_output.get("features"))
    return extract_symbol_constituents(technical_features.get("market_context"))


def _unwrap_outputs(raw_output: object) -> Mapping[str, object]:
    object_outputs = getattr(raw_output, "outputs", None)
    if isinstance(object_outputs, Mapping):
        return object_outputs
    if isinstance(raw_output, Mapping):
        nested_outputs = raw_output.get("outputs")
        if isinstance(nested_outputs, Mapping):
            return nested_outputs
        return raw_output
    return {}


def _mapping(value: object) -> Mapping[str, object]:
    if isinstance(value, Mapping):
        return value
    return {}


def _string_value(value: object, *, default: str) -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _int_value(value: object, *, default: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default
    return default
