from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Final, cast

from application.persistence.market import MarketPersistenceService
from application.projections.workflow_outputs.projection_identity import (
    build_projected_record_id,
)
from application.projections.workflow_outputs.projection_models import (
    WorkflowOutputProjectionOutcome,
    WorkflowOutputProjectionStatus,
    WorkflowOutputProjectorRequest,
)
from application.projections.workflow_outputs.projection_registry import (
    WorkflowOutputProjectorRegistration,
)
from core.storage.persistence.lineage import JsonObject
from core.storage.persistence.market import (
    MarketBreadthSnapshotRecord,
    MarketContextSnapshotRecord,
    TechnicalAnalysisSnapshotRecord,
)
from domain.workflow_outputs import (
    TECHNICAL_ANALYSIS_OUTPUT_CONTRACT,
    WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
)

TECHNICAL_MARKET_PROJECTOR_NAME: Final = "technical_market_projector"
TECHNICAL_MARKET_PROJECTOR_NODE_NAMES: Final = ("technical_agent",)
TECHNICAL_MARKET_UNIVERSE_FIELD: Final = "market_universe"
TECHNICAL_MARKET_OBSERVED_AT_FIELD: Final = "observed_at"


class TechnicalMarketWorkflowOutputProjector:
    """Project technical-agent workflow evidence into curated market records."""

    def __init__(
        self,
        market_persistence_service: MarketPersistenceService,
    ) -> None:
        self._market_persistence_service = market_persistence_service

    @property
    def projector_name(self) -> str:
        return TECHNICAL_MARKET_PROJECTOR_NAME

    async def project(
        self,
        request: WorkflowOutputProjectorRequest,
    ) -> WorkflowOutputProjectionOutcome:
        outputs = _mapping(request.node_output.outputs)
        features = _mapping(outputs.get("features"))
        if not features:
            return _skipped(request, "Technical output has no typed features payload.")

        observed_at = _parse_timestamp(outputs.get(TECHNICAL_MARKET_OBSERVED_AT_FIELD))
        if observed_at is None:
            return _skipped(
                request,
                "Technical output is missing first-class observed_at timestamp.",
            )

        symbol = _optional_identifier(features.get("symbol"))
        if symbol is None:
            return _skipped(request, "Technical output is missing symbol.")

        universe = _optional_identifier(outputs.get(TECHNICAL_MARKET_UNIVERSE_FIELD))
        if universe is None:
            return _skipped(
                request,
                "Technical output is missing first-class market_universe.",
            )

        source = _optional_identifier(request.node_output.metadata.get("source"))
        metadata = _projection_metadata(request)

        snapshot = _mapping(features.get("snapshot"))
        market_context = _mapping(features.get("market_context"))
        micro_regime = _mapping(features.get("micro_regime"))
        trend = _mapping(features.get("trend"))
        volatility = _mapping(features.get("volatility"))
        breadth = _mapping(features.get("breadth"))
        raw_regime = _mapping(features.get("raw_regime"))
        regime = _mapping(features.get("regime"))

        technical_record = _build_technical_snapshot_record(
            request=request,
            symbol=symbol,
            observed_at=observed_at,
            source=source,
            metadata=metadata,
            outputs=outputs,
            features=features,
            snapshot=snapshot,
            market_context=market_context,
            micro_regime=micro_regime,
            trend=trend,
            volatility=volatility,
            breadth=breadth,
            raw_regime=raw_regime,
            regime=regime,
        )
        context_records: tuple[MarketContextSnapshotRecord, ...] = ()
        if market_context:
            context_records = (
                _build_market_context_snapshot_record(
                    request=request,
                    universe=universe,
                    observed_at=observed_at,
                    source=source,
                    metadata=metadata,
                    outputs=outputs,
                    market_context=market_context,
                    trend=trend,
                    volatility=volatility,
                    breadth=breadth,
                    regime=regime,
                ),
            )

        breadth_records: tuple[MarketBreadthSnapshotRecord, ...] = ()
        if breadth:
            breadth_records = (
                _build_breadth_snapshot_record(
                    request=request,
                    universe=universe,
                    observed_at=observed_at,
                    source=source,
                    metadata=metadata,
                    market_context=market_context,
                    breadth=breadth,
                ),
            )

        result = await self._market_persistence_service.persist_records(
            technical_snapshots=(technical_record,),
            context_snapshots=context_records,
            breadth_snapshots=breadth_records,
        )
        if not result.success:
            return _failed(request, result.error or "Market persistence failed.")

        return _outcome(
            request=request,
            status=WorkflowOutputProjectionStatus.SUCCEEDED,
            records_written=result.records_persisted,
            message="Technical market output projected into curated market records.",
        )


def build_technical_market_projector_registration(
    market_persistence_service: MarketPersistenceService,
) -> WorkflowOutputProjectorRegistration:
    """Build the canonical technical-agent market projector registration."""
    projector = TechnicalMarketWorkflowOutputProjector(market_persistence_service)
    return WorkflowOutputProjectorRegistration(
        projector_name=TECHNICAL_MARKET_PROJECTOR_NAME,
        output_contract=TECHNICAL_ANALYSIS_OUTPUT_CONTRACT,
        output_schema_version=WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
        projector=projector,
        supported_node_names=TECHNICAL_MARKET_PROJECTOR_NODE_NAMES,
    )


def _build_technical_snapshot_record(
    *,
    request: WorkflowOutputProjectorRequest,
    symbol: str,
    observed_at: datetime,
    source: str | None,
    metadata: JsonObject,
    outputs: Mapping[str, object],
    features: Mapping[str, object],
    snapshot: Mapping[str, object],
    market_context: Mapping[str, object],
    micro_regime: Mapping[str, object],
    trend: Mapping[str, object],
    volatility: Mapping[str, object],
    breadth: Mapping[str, object],
    raw_regime: Mapping[str, object],
    regime: Mapping[str, object],
) -> TechnicalAnalysisSnapshotRecord:
    return TechnicalAnalysisSnapshotRecord(
        technical_snapshot_id=build_projected_record_id(
            record_type="technical_analysis_snapshot",
            execution_id=request.lineage.execution_id or request.run.execution_id,
            node_name=request.lineage.node_name or request.node_output.node_name,
            domain_natural_key=symbol,
            source_timestamp=observed_at,
        ),
        symbol=symbol,
        timestamp=observed_at,
        lineage=request.lineage,
        source=source,
        technical_regime=_coalesce_identifier(
            outputs.get("regime"),
            regime.get("regime"),
        ),
        trend_regime=_coalesce_identifier(
            trend.get("trend_regime"),
            trend.get("primary_trend"),
        ),
        volatility_regime=_optional_identifier(volatility.get("volatility_regime")),
        breadth_regime=_optional_identifier(breadth.get("breadth_regime")),
        technical_score=_optional_float(features.get("technical_score")),
        directional_technical_score=_coalesce_float(
            regime.get("directional_technical_score"),
            outputs.get("directional_score"),
        ),
        bull_score=_optional_float(regime.get("bull_score")),
        bear_score=_optional_float(regime.get("bear_score")),
        sideways_score=_optional_float(regime.get("sideways_score")),
        trend_score=_optional_float(trend.get("trend_score")),
        trend_strength=_optional_float(trend.get("trend_strength")),
        trend_quality=_optional_float(trend.get("trend_quality")),
        volatility_score=_optional_float(volatility.get("volatility_score")),
        breadth_score=_coalesce_float(
            breadth.get("breadth_score"),
            regime.get("breadth_score"),
        ),
        risk_score=_optional_float(volatility.get("risk_score")),
        trend_risk_score=_optional_float(trend.get("trend_risk_score")),
        volatility_risk_score=_optional_float(volatility.get("volatility_risk_score")),
        breadth_risk_score=_optional_float(breadth.get("breadth_risk_score")),
        strategy_environment=_optional_identifier(regime.get("strategy_environment")),
        confidence=_coalesce_float(
            outputs.get("confidence"),
            regime.get("confidence"),
        ),
        inputs_payload=_json_mapping(regime.get("inputs")),
        snapshot_payload=_json_mapping(snapshot),
        market_context_payload=_json_mapping(market_context),
        micro_regime_payload=_json_mapping(micro_regime),
        trend_payload=_json_mapping(trend),
        volatility_payload=_json_mapping(volatility),
        breadth_payload=_json_mapping(breadth),
        raw_regime_payload=_json_mapping(raw_regime),
        regime_payload=_json_mapping(regime),
        metadata=metadata,
    )


def _build_market_context_snapshot_record(
    *,
    request: WorkflowOutputProjectorRequest,
    universe: str,
    observed_at: datetime,
    source: str | None,
    metadata: JsonObject,
    outputs: Mapping[str, object],
    market_context: Mapping[str, object],
    trend: Mapping[str, object],
    volatility: Mapping[str, object],
    breadth: Mapping[str, object],
    regime: Mapping[str, object],
) -> MarketContextSnapshotRecord:
    return MarketContextSnapshotRecord(
        context_snapshot_id=build_projected_record_id(
            record_type="market_context_snapshot",
            execution_id=request.lineage.execution_id or request.run.execution_id,
            node_name=request.lineage.node_name or request.node_output.node_name,
            domain_natural_key=universe,
            source_timestamp=observed_at,
        ),
        timestamp=observed_at,
        lineage=request.lineage,
        source=source,
        universe=universe,
        market_regime=_coalesce_identifier(
            outputs.get("regime"),
            regime.get("regime"),
        ),
        volatility_regime=_optional_identifier(volatility.get("volatility_regime")),
        breadth_regime=_optional_identifier(breadth.get("breadth_regime")),
        trend_score=_optional_float(trend.get("trend_score")),
        volatility_score=_optional_float(volatility.get("volatility_score")),
        breadth_score=_optional_float(breadth.get("breadth_score")),
        risk_score=_optional_float(volatility.get("risk_score")),
        vix=_optional_float(market_context.get("vix")),
        vix_20=_optional_float(market_context.get("vix_20")),
        vix_50=_optional_float(market_context.get("vix_50")),
        vix_percentile_252=_optional_float(market_context.get("vix_percentile_252")),
        vix_trend_ratio=_optional_float(market_context.get("vix_trend_ratio")),
        vix_change_5d=_optional_float(market_context.get("vix_change_5d")),
        vix_change_20d=_optional_float(market_context.get("vix_change_20d")),
        vvix=_optional_float(market_context.get("vvix")),
        vvix_20=_optional_float(market_context.get("vvix_20")),
        vvix_50=_optional_float(market_context.get("vvix_50")),
        vvix_percentile_252=_optional_float(market_context.get("vvix_percentile_252")),
        vvix_trend_ratio=_optional_float(market_context.get("vvix_trend_ratio")),
        vvix_change_5d=_optional_float(market_context.get("vvix_change_5d")),
        vvix_change_20d=_optional_float(market_context.get("vvix_change_20d")),
        market_cap_index=_optional_float(market_context.get("market_cap_index")),
        market_cap_index_20=_optional_float(market_context.get("market_cap_index_20")),
        market_cap_index_50=_optional_float(market_context.get("market_cap_index_50")),
        market_cap_index_change_5d=_optional_float(
            market_context.get("market_cap_index_change_5d")
        ),
        market_cap_index_change_20d=_optional_float(
            market_context.get("market_cap_index_change_20d")
        ),
        advances_count=_optional_int(market_context.get("advances_count")),
        declines_count=_optional_int(market_context.get("declines_count")),
        unchanged_count=_optional_int(market_context.get("unchanged_count")),
        active_count=_optional_int(market_context.get("active_count")),
        net_breadth=_optional_int(market_context.get("net_breadth")),
        breadth_percent=_optional_float(market_context.get("breadth_percent")),
        ad_ratio=_optional_float(market_context.get("ad_ratio")),
        ad_line=_optional_float(market_context.get("ad_line")),
        ad_line_ema_10=_optional_float(market_context.get("ad_line_ema_10")),
        ad_line_ema_20=_optional_float(market_context.get("ad_line_ema_20")),
        ad_line_ema_50=_optional_float(market_context.get("ad_line_ema_50")),
        ad_line_slope_5=_optional_float(market_context.get("ad_line_slope_5")),
        ad_line_slope_20=_optional_float(market_context.get("ad_line_slope_20")),
        ad_line_trend_ratio=_optional_float(market_context.get("ad_line_trend_ratio")),
        ad_line_trend_score=_optional_float(market_context.get("ad_line_trend_score")),
        price_ad_divergence=_optional_ratio_signal(
            market_context.get("price_ad_divergence")
        ),
        pct_above_50dma=_optional_float(market_context.get("pct_above_50dma")),
        pct_above_200dma=_optional_float(market_context.get("pct_above_200dma")),
        new_highs=_optional_int(market_context.get("new_highs")),
        new_lows=_optional_int(market_context.get("new_lows")),
        new_high_low_diff=_optional_int(market_context.get("new_high_low_diff")),
        new_high_low_ratio=_optional_float(market_context.get("new_high_low_ratio")),
        net_breadth_ema_19=_optional_float(market_context.get("net_breadth_ema_19")),
        net_breadth_ema_39=_optional_float(market_context.get("net_breadth_ema_39")),
        mcclellan_oscillator=_optional_float(
            market_context.get("mcclellan_oscillator")
        ),
        mcclellan_summation_index=_optional_float(
            market_context.get("mcclellan_summation_index")
        ),
        has_vix=_optional_bool(market_context.get("has_vix")),
        has_vvix=_optional_bool(market_context.get("has_vvix")),
        has_sp500=_optional_bool(market_context.get("has_sp500")),
        has_ad_line=_optional_bool(market_context.get("has_ad_line")),
        has_breadth=_optional_bool(market_context.get("has_breadth")),
        inputs_payload=_json_mapping(regime.get("inputs")),
        market_context_payload=_json_mapping(market_context),
        top_50_constituents_payload=_json_payload(
            "constituents",
            market_context.get("top_50_constituents"),
        ),
        market_caps_payload=_json_payload(
            "market_caps",
            market_context.get("market_caps"),
        ),
        metadata=metadata,
    )


def _build_breadth_snapshot_record(
    *,
    request: WorkflowOutputProjectorRequest,
    universe: str,
    observed_at: datetime,
    source: str | None,
    metadata: JsonObject,
    market_context: Mapping[str, object],
    breadth: Mapping[str, object],
) -> MarketBreadthSnapshotRecord:
    return MarketBreadthSnapshotRecord(
        breadth_snapshot_id=build_projected_record_id(
            record_type="market_breadth_snapshot",
            execution_id=request.lineage.execution_id or request.run.execution_id,
            node_name=request.lineage.node_name or request.node_output.node_name,
            domain_natural_key=universe,
            source_timestamp=observed_at,
        ),
        timestamp=observed_at,
        universe=universe,
        lineage=request.lineage,
        source=source,
        has_breadth_data=_optional_bool(breadth.get("has_breadth_data")),
        advances_count=_first_int("advances_count", breadth, market_context),
        declines_count=_first_int("declines_count", breadth, market_context),
        unchanged_count=_first_int("unchanged_count", breadth, market_context),
        new_highs=_first_int("new_highs", breadth, market_context),
        new_lows=_first_int("new_lows", breadth, market_context),
        ad_line=_first_float("ad_line", breadth, market_context),
        ad_line_ema_10=_first_float("ad_line_ema_10", breadth, market_context),
        ad_line_ema_20=_first_float("ad_line_ema_20", breadth, market_context),
        ad_line_ema_50=_first_float("ad_line_ema_50", breadth, market_context),
        ad_line_slope_5=_first_float("ad_line_slope_5", breadth, market_context),
        ad_line_slope_20=_first_float("ad_line_slope_20", breadth, market_context),
        ad_line_trend_ratio=_first_float(
            "ad_line_trend_ratio",
            breadth,
            market_context,
        ),
        ad_line_trend_score=_first_float(
            "ad_line_trend_score",
            breadth,
            market_context,
        ),
        price_ad_divergence=_first_ratio_signal(
            "price_ad_divergence",
            breadth,
            market_context,
        ),
        pct_above_50dma=_first_float("pct_above_50dma", breadth, market_context),
        pct_above_200dma=_first_float("pct_above_200dma", breadth, market_context),
        new_high_low_diff=_first_int("new_high_low_diff", breadth, market_context),
        new_high_low_ratio=_first_float("new_high_low_ratio", breadth, market_context),
        net_breadth_ema_19=_first_float(
            "net_breadth_ema_19",
            breadth,
            market_context,
        ),
        net_breadth_ema_39=_first_float(
            "net_breadth_ema_39",
            breadth,
            market_context,
        ),
        mcclellan_oscillator=_first_float(
            "mcclellan_oscillator",
            breadth,
            market_context,
        ),
        mcclellan_summation_index=_first_float(
            "mcclellan_summation_index",
            breadth,
            market_context,
        ),
        breadth_score=_optional_float(breadth.get("breadth_score")),
        breadth_risk_score=_optional_float(breadth.get("breadth_risk_score")),
        trend_score=_optional_float(breadth.get("trend_score")),
        slope_score=_optional_float(breadth.get("slope_score")),
        confirmation_score=_optional_float(breadth.get("confirmation_score")),
        participation_score=_optional_float(breadth.get("participation_score")),
        leadership_score=_optional_float(breadth.get("leadership_score")),
        mcclellan_score=_optional_float(breadth.get("mcclellan_score")),
        divergence_score=_optional_float(breadth.get("divergence_score")),
        breadth_regime=_optional_identifier(breadth.get("breadth_regime")),
        risk_regime=_optional_identifier(breadth.get("risk_regime")),
        strategy_environment=_optional_identifier(breadth.get("strategy_environment")),
        inputs_payload=_json_mapping(breadth.get("inputs")),
        components_payload=_json_mapping(breadth.get("components")),
        source_metrics_payload=_json_mapping(breadth.get("source_metrics")),
        breadth_payload=_json_mapping(breadth),
        metadata=metadata,
    )


def _outcome(
    *,
    request: WorkflowOutputProjectorRequest,
    status: WorkflowOutputProjectionStatus,
    records_written: int = 0,
    message: str | None = None,
    error_type: str | None = None,
    error_message: str | None = None,
) -> WorkflowOutputProjectionOutcome:
    completed_at = datetime.now(UTC)
    return WorkflowOutputProjectionOutcome(
        status=status,
        projector_name=TECHNICAL_MARKET_PROJECTOR_NAME,
        node_name=request.node_output.node_name,
        output_contract=request.node_output.output_contract
        or TECHNICAL_ANALYSIS_OUTPUT_CONTRACT,
        output_schema_version=request.node_output.output_schema_version
        or WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
        source_fingerprint=request.source_fingerprint,
        records_written=records_written,
        message=message,
        error_type=error_type,
        error_message=error_message,
        completed_at=completed_at,
    )


def _skipped(
    request: WorkflowOutputProjectorRequest,
    message: str,
) -> WorkflowOutputProjectionOutcome:
    return _outcome(
        request=request,
        status=WorkflowOutputProjectionStatus.SKIPPED,
        message=message,
    )


def _failed(
    request: WorkflowOutputProjectorRequest,
    error: str,
) -> WorkflowOutputProjectionOutcome:
    return _outcome(
        request=request,
        status=WorkflowOutputProjectionStatus.FAILED,
        error_type="market_persistence_failed",
        error_message=error,
        message="Technical market projection failed during persistence.",
    )


def _projection_metadata(request: WorkflowOutputProjectorRequest) -> JsonObject:
    quality_status = _optional_identifier(
        request.node_output.metadata.get("quality_status")
    )
    return _compact_json_object(
        {
            "source_fingerprint": request.source_fingerprint,
            "quality_status": quality_status,
            "projector_name": TECHNICAL_MARKET_PROJECTOR_NAME,
            "node_output_id": request.node_output.node_output_id,
        }
    )


def _parse_timestamp(value: object) -> datetime | None:
    if isinstance(value, datetime):
        timestamp = value
    elif isinstance(value, str):
        raw_value = value.strip()
        if not raw_value:
            return None
        if raw_value.endswith("Z"):
            raw_value = f"{raw_value[:-1]}+00:00"
        try:
            timestamp = datetime.fromisoformat(raw_value)
        except ValueError:
            return None
    else:
        return None

    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=UTC)
    return timestamp


def _mapping(value: object) -> Mapping[str, object]:
    if isinstance(value, Mapping):
        return cast(Mapping[str, object], value)
    return {}


def _json_mapping(value: object) -> JsonObject:
    if isinstance(value, Mapping):
        return cast(JsonObject, dict(value))
    return {}


def _json_payload(key: str, value: object) -> JsonObject:
    if isinstance(value, Mapping):
        return cast(JsonObject, dict(value))
    if _is_json_value(value):
        return cast(JsonObject, {key: value})
    return {}


def _compact_json_object(payload: Mapping[str, object | None]) -> JsonObject:
    return cast(
        JsonObject,
        {key: value for key, value in payload.items() if value is not None},
    )


def _is_json_value(value: object) -> bool:
    if value is None or isinstance(value, str | int | float | bool):
        return True
    if isinstance(value, Mapping):
        return all(
            isinstance(key, str) and _is_json_value(item) for key, item in value.items()
        )
    if isinstance(value, list | tuple):
        return all(_is_json_value(item) for item in value)
    return False


def _optional_identifier(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _coalesce_identifier(*values: object) -> str | None:
    for value in values:
        cleaned = _optional_identifier(value)
        if cleaned is not None:
            return cleaned
    return None


def _coalesce_float(*values: object) -> float | None:
    for value in values:
        cleaned = _optional_float(value)
        if cleaned is not None:
            return cleaned
    return None


def _optional_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    return None


def _optional_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None


def _optional_bool(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    return None


def _optional_ratio_signal(value: object) -> float | None:
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    return _optional_float(value)


def _first_float(
    key: str,
    first: Mapping[str, object],
    second: Mapping[str, object],
) -> float | None:
    value = _optional_float(first.get(key))
    if value is not None:
        return value
    return _optional_float(second.get(key))


def _first_int(
    key: str,
    first: Mapping[str, object],
    second: Mapping[str, object],
) -> int | None:
    value = _optional_int(first.get(key))
    if value is not None:
        return value
    return _optional_int(second.get(key))


def _first_ratio_signal(
    key: str,
    first: Mapping[str, object],
    second: Mapping[str, object],
) -> float | None:
    value = _optional_ratio_signal(first.get(key))
    if value is not None:
        return value
    return _optional_ratio_signal(second.get(key))
