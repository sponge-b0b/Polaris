from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

from core.storage.persistence.lineage import (
    JsonObject,
    PersistenceLineage,
    clean_optional_identifier,
    require_non_empty_identifier,
)


@dataclass(
    frozen=True,
    slots=True,
)
class MarketOhlcvRecord:
    """
    Typed persistence-boundary record for curated market OHLCV facts.

    Provider payloads should be normalized before becoming this record. The
    record is suitable for PostgreSQL persistence and future curated RAG source
    material, but application/intelligence layers should continue to use their
    richer domain DTOs before crossing the persistence boundary.
    """

    ohlcv_id: str
    symbol: str
    timestamp: datetime
    source: str
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: float
    lineage: PersistenceLineage = field(default_factory=PersistenceLineage)
    adjusted_close: float | None = None
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "ohlcv_id",
            require_non_empty_identifier(
                self.ohlcv_id,
                "ohlcv_id",
            ),
        )
        _normalize_symbol_source_fields(self)
        _require_non_negative_float(
            self.open_price,
            "open_price",
        )
        _require_non_negative_float(
            self.high_price,
            "high_price",
        )
        _require_non_negative_float(
            self.low_price,
            "low_price",
        )
        _require_non_negative_float(
            self.close_price,
            "close_price",
        )
        _require_non_negative_float(
            self.volume,
            "volume",
        )
        _require_optional_non_negative_float(
            self.adjusted_close,
            "adjusted_close",
        )
        if self.high_price < self.low_price:
            raise ValueError("high_price must be greater than or equal to low_price.")


@dataclass(
    frozen=True,
    slots=True,
)
class MarketIndicatorRecord:
    """
    Typed persistence-boundary record for a normalized technical indicator.
    """

    indicator_id: str
    symbol: str
    timestamp: datetime
    source: str
    indicator_name: str
    indicator_value: float
    lineage: PersistenceLineage = field(default_factory=PersistenceLineage)
    timeframe: str | None = None
    parameters: JsonObject = field(default_factory=dict)
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "indicator_id",
            require_non_empty_identifier(
                self.indicator_id,
                "indicator_id",
            ),
        )
        _normalize_symbol_source_fields(self)
        object.__setattr__(
            self,
            "indicator_name",
            require_non_empty_identifier(
                self.indicator_name,
                "indicator_name",
            ),
        )
        object.__setattr__(
            self,
            "timeframe",
            clean_optional_identifier(
                self.timeframe,
                "timeframe",
            ),
        )


@dataclass(
    frozen=True,
    slots=True,
)
class MarketContextSnapshotRecord:
    """
    Append-only market context snapshot with final synthesized market outputs.
    """

    context_snapshot_id: str
    timestamp: datetime
    lineage: PersistenceLineage = field(default_factory=PersistenceLineage)
    source: str | None = None
    universe: str | None = None
    market_regime: str | None = None
    volatility_regime: str | None = None
    breadth_regime: str | None = None
    trend_score: float | None = None
    volatility_score: float | None = None
    breadth_score: float | None = None
    risk_score: float | None = None
    vix: float | None = None
    vix_20: float | None = None
    vix_50: float | None = None
    vix_percentile_252: float | None = None
    vix_trend_ratio: float | None = None
    vix_change_5d: float | None = None
    vix_change_20d: float | None = None
    vvix: float | None = None
    vvix_20: float | None = None
    vvix_50: float | None = None
    vvix_percentile_252: float | None = None
    vvix_trend_ratio: float | None = None
    vvix_change_5d: float | None = None
    vvix_change_20d: float | None = None
    market_cap_index: float | None = None
    market_cap_index_20: float | None = None
    market_cap_index_50: float | None = None
    market_cap_index_change_5d: float | None = None
    market_cap_index_change_20d: float | None = None
    advances_count: int | None = None
    declines_count: int | None = None
    unchanged_count: int | None = None
    active_count: int | None = None
    net_breadth: int | None = None
    breadth_percent: float | None = None
    ad_ratio: float | None = None
    ad_line: float | None = None
    ad_line_ema_10: float | None = None
    ad_line_ema_20: float | None = None
    ad_line_ema_50: float | None = None
    ad_line_slope_5: float | None = None
    ad_line_slope_20: float | None = None
    ad_line_trend_ratio: float | None = None
    ad_line_trend_score: float | None = None
    price_ad_divergence: float | None = None
    pct_above_50dma: float | None = None
    pct_above_200dma: float | None = None
    new_highs: int | None = None
    new_lows: int | None = None
    new_high_low_diff: int | None = None
    new_high_low_ratio: float | None = None
    net_breadth_ema_19: float | None = None
    net_breadth_ema_39: float | None = None
    mcclellan_oscillator: float | None = None
    mcclellan_summation_index: float | None = None
    has_vix: bool | None = None
    has_vvix: bool | None = None
    has_sp500: bool | None = None
    has_ad_line: bool | None = None
    has_breadth: bool | None = None
    inputs_payload: JsonObject = field(default_factory=dict)
    market_context_payload: JsonObject = field(default_factory=dict)
    top_50_constituents_payload: JsonObject = field(default_factory=dict)
    market_caps_payload: JsonObject = field(default_factory=dict)
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "context_snapshot_id",
            require_non_empty_identifier(
                self.context_snapshot_id,
                "context_snapshot_id",
            ),
        )
        _normalize_optional_context_fields(self)
        for field_name in (
            "trend_score",
            "volatility_score",
            "breadth_score",
        ):
            _require_optional_stability_score(getattr(self, field_name), field_name)
        for field_name in (
            "risk_score",
            "vix_percentile_252",
            "vvix_percentile_252",
            "breadth_percent",
            "price_ad_divergence",
            "pct_above_50dma",
            "pct_above_200dma",
        ):
            _require_optional_ratio(getattr(self, field_name), field_name)
        for field_name in (
            "vix",
            "vix_20",
            "vix_50",
            "vvix",
            "vvix_20",
            "vvix_50",
            "market_cap_index",
            "market_cap_index_20",
            "market_cap_index_50",
        ):
            _require_optional_non_negative_float(getattr(self, field_name), field_name)
        for field_name in (
            "advances_count",
            "declines_count",
            "unchanged_count",
            "active_count",
            "new_highs",
            "new_lows",
        ):
            _require_optional_non_negative_int(getattr(self, field_name), field_name)


@dataclass(
    frozen=True,
    slots=True,
)
class TechnicalAnalysisSnapshotRecord:
    """
    Append-only final technical analysis snapshot for a symbol.
    """

    technical_snapshot_id: str
    symbol: str
    timestamp: datetime
    lineage: PersistenceLineage = field(default_factory=PersistenceLineage)
    source: str | None = None
    technical_regime: str | None = None
    trend_regime: str | None = None
    volatility_regime: str | None = None
    breadth_regime: str | None = None
    technical_score: float | None = None
    directional_technical_score: float | None = None
    bull_score: float | None = None
    bear_score: float | None = None
    sideways_score: float | None = None
    trend_score: float | None = None
    trend_strength: float | None = None
    trend_quality: float | None = None
    volatility_score: float | None = None
    breadth_score: float | None = None
    risk_score: float | None = None
    trend_risk_score: float | None = None
    volatility_risk_score: float | None = None
    breadth_risk_score: float | None = None
    strategy_environment: str | None = None
    confidence: float | None = None
    inputs_payload: JsonObject = field(default_factory=dict)
    snapshot_payload: JsonObject = field(default_factory=dict)
    market_context_payload: JsonObject = field(default_factory=dict)
    micro_regime_payload: JsonObject = field(default_factory=dict)
    trend_payload: JsonObject = field(default_factory=dict)
    volatility_payload: JsonObject = field(default_factory=dict)
    breadth_payload: JsonObject = field(default_factory=dict)
    raw_regime_payload: JsonObject = field(default_factory=dict)
    regime_payload: JsonObject = field(default_factory=dict)
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "technical_snapshot_id",
            require_non_empty_identifier(
                self.technical_snapshot_id,
                "technical_snapshot_id",
            ),
        )
        object.__setattr__(
            self,
            "symbol",
            require_non_empty_identifier(
                self.symbol,
                "symbol",
            ).upper(),
        )
        _normalize_optional_regime_fields(self)
        object.__setattr__(
            self,
            "strategy_environment",
            clean_optional_identifier(
                self.strategy_environment,
                "strategy_environment",
            ),
        )
        for field_name in (
            "technical_score",
            "directional_technical_score",
            "bull_score",
            "bear_score",
            "sideways_score",
            "trend_score",
            "trend_strength",
            "trend_quality",
            "volatility_score",
            "breadth_score",
        ):
            _require_optional_stability_score(getattr(self, field_name), field_name)
        for field_name in (
            "risk_score",
            "trend_risk_score",
            "volatility_risk_score",
            "breadth_risk_score",
            "confidence",
        ):
            _require_optional_ratio(getattr(self, field_name), field_name)


@dataclass(
    frozen=True,
    slots=True,
)
class MarketBreadthSnapshotRecord:
    """
    Append-only market breadth snapshot for a market universe.
    """

    breadth_snapshot_id: str
    timestamp: datetime
    universe: str
    lineage: PersistenceLineage = field(default_factory=PersistenceLineage)
    source: str | None = None
    has_breadth_data: bool | None = None
    advances_count: int | None = None
    declines_count: int | None = None
    unchanged_count: int | None = None
    new_highs: int | None = None
    new_lows: int | None = None
    ad_line: float | None = None
    ad_line_ema_10: float | None = None
    ad_line_ema_20: float | None = None
    ad_line_ema_50: float | None = None
    ad_line_slope_5: float | None = None
    ad_line_slope_20: float | None = None
    ad_line_trend_ratio: float | None = None
    ad_line_trend_score: float | None = None
    price_ad_divergence: float | None = None
    pct_above_50dma: float | None = None
    pct_above_200dma: float | None = None
    new_high_low_diff: int | None = None
    new_high_low_ratio: float | None = None
    net_breadth_ema_19: float | None = None
    net_breadth_ema_39: float | None = None
    mcclellan_oscillator: float | None = None
    mcclellan_summation_index: float | None = None
    breadth_score: float | None = None
    breadth_risk_score: float | None = None
    trend_score: float | None = None
    slope_score: float | None = None
    confirmation_score: float | None = None
    participation_score: float | None = None
    leadership_score: float | None = None
    mcclellan_score: float | None = None
    divergence_score: float | None = None
    breadth_regime: str | None = None
    risk_regime: str | None = None
    strategy_environment: str | None = None
    inputs_payload: JsonObject = field(default_factory=dict)
    components_payload: JsonObject = field(default_factory=dict)
    source_metrics_payload: JsonObject = field(default_factory=dict)
    breadth_payload: JsonObject = field(default_factory=dict)
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "breadth_snapshot_id",
            require_non_empty_identifier(
                self.breadth_snapshot_id,
                "breadth_snapshot_id",
            ),
        )
        object.__setattr__(
            self,
            "universe",
            require_non_empty_identifier(
                self.universe,
                "universe",
            ),
        )
        for field_name in (
            "source",
            "breadth_regime",
            "risk_regime",
            "strategy_environment",
        ):
            object.__setattr__(
                self,
                field_name,
                clean_optional_identifier(getattr(self, field_name), field_name),
            )
        for field_name in (
            "advances_count",
            "declines_count",
            "unchanged_count",
            "new_highs",
            "new_lows",
        ):
            _require_optional_non_negative_int(getattr(self, field_name), field_name)
        for field_name in (
            "pct_above_50dma",
            "pct_above_200dma",
            "price_ad_divergence",
            "breadth_risk_score",
        ):
            _require_optional_ratio(getattr(self, field_name), field_name)
        for field_name in (
            "breadth_score",
            "trend_score",
            "slope_score",
            "confirmation_score",
            "participation_score",
            "leadership_score",
            "mcclellan_score",
            "divergence_score",
        ):
            _require_optional_stability_score(getattr(self, field_name), field_name)


@dataclass(
    frozen=True,
    slots=True,
)
class MarketEventSnapshotRecord:
    """
    Append-only market event snapshot for market-events service outputs.
    """

    event_snapshot_id: str
    symbol: str
    timestamp: datetime
    lineage: PersistenceLineage = field(default_factory=PersistenceLineage)
    source: str | None = None
    market_pressure_score: float | None = None
    volatility_forecast: str | None = None
    regime_bias: str | None = None
    event_count: int | None = None
    high_impact_count: int | None = None
    events_payload: JsonObject = field(default_factory=dict)
    high_impact_events_payload: JsonObject = field(default_factory=dict)
    risk_projection_payload: JsonObject = field(default_factory=dict)
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "event_snapshot_id",
            require_non_empty_identifier(
                self.event_snapshot_id,
                "event_snapshot_id",
            ),
        )
        object.__setattr__(
            self,
            "symbol",
            require_non_empty_identifier(
                self.symbol,
                "symbol",
            ).upper(),
        )
        object.__setattr__(
            self,
            "source",
            clean_optional_identifier(
                self.source,
                "source",
            ),
        )
        object.__setattr__(
            self,
            "volatility_forecast",
            clean_optional_identifier(
                self.volatility_forecast,
                "volatility_forecast",
            ),
        )
        object.__setattr__(
            self,
            "regime_bias",
            clean_optional_identifier(
                self.regime_bias,
                "regime_bias",
            ),
        )
        _require_optional_stability_score(
            self.market_pressure_score,
            "market_pressure_score",
        )
        _require_optional_non_negative_int(
            self.event_count,
            "event_count",
        )
        _require_optional_non_negative_int(
            self.high_impact_count,
            "high_impact_count",
        )


@dataclass(
    frozen=True,
    slots=True,
)
class MarketPersistenceBundle:
    """
    Atomic market/technical persistence payload.
    """

    ohlcv: tuple[MarketOhlcvRecord, ...] = ()
    indicators: tuple[MarketIndicatorRecord, ...] = ()
    context_snapshots: tuple[MarketContextSnapshotRecord, ...] = ()
    technical_snapshots: tuple[TechnicalAnalysisSnapshotRecord, ...] = ()
    breadth_snapshots: tuple[MarketBreadthSnapshotRecord, ...] = ()
    event_snapshots: tuple[MarketEventSnapshotRecord, ...] = ()


@dataclass(
    frozen=True,
    slots=True,
)
class MarketPersistenceResult:
    """
    Typed result returned by market persistence adapters.
    """

    success: bool
    records_persisted: int = 0
    primary_record_id: str | None = None
    error: str | None = None

    def __post_init__(
        self,
    ) -> None:
        if self.records_persisted < 0:
            raise ValueError("records_persisted cannot be negative.")

        if self.success and self.error is not None:
            raise ValueError("successful persistence results cannot include an error.")

        if self.success:
            require_non_empty_identifier(
                self.primary_record_id,
                "primary_record_id",
            )

        if not self.success:
            require_non_empty_identifier(
                self.error,
                "error",
            )

    @classmethod
    def succeeded(
        cls,
        *,
        primary_record_id: str,
        records_persisted: int = 1,
    ) -> MarketPersistenceResult:
        return cls(
            success=True,
            records_persisted=records_persisted,
            primary_record_id=primary_record_id,
        )

    @classmethod
    def failed(
        cls,
        error: str,
    ) -> MarketPersistenceResult:
        return cls(
            success=False,
            records_persisted=0,
            error=error,
        )


def new_market_ohlcv_id(
    *,
    symbol: str,
    timestamp: datetime,
    source: str,
) -> str:
    return _stable_market_id(
        "market_ohlcv",
        timestamp,
        require_non_empty_identifier(
            symbol,
            "symbol",
        ).upper(),
        require_non_empty_identifier(
            source,
            "source",
        ),
    )


def new_market_indicator_id(
    *,
    symbol: str,
    timestamp: datetime,
    indicator_name: str,
    source: str,
    timeframe: str | None = None,
) -> str:
    parts = [
        require_non_empty_identifier(
            symbol,
            "symbol",
        ).upper(),
        require_non_empty_identifier(
            indicator_name,
            "indicator_name",
        ),
        require_non_empty_identifier(
            source,
            "source",
        ),
    ]
    clean_timeframe = clean_optional_identifier(
        timeframe,
        "timeframe",
    )
    if clean_timeframe is not None:
        parts.append(clean_timeframe)

    return _stable_market_id(
        "market_indicator",
        timestamp,
        *parts,
    )


def new_market_context_snapshot_id(
    *,
    timestamp: datetime,
    execution_id: str | None = None,
    context_key: str | None = None,
) -> str:
    return _snapshot_market_id(
        record_type="market_context_snapshot",
        timestamp=timestamp,
        execution_id=execution_id,
        key=context_key,
    )


def new_technical_analysis_snapshot_id(
    *,
    symbol: str,
    timestamp: datetime,
    execution_id: str | None = None,
    snapshot_key: str | None = None,
) -> str:
    clean_symbol = require_non_empty_identifier(
        symbol,
        "symbol",
    ).upper()
    return _snapshot_market_id(
        record_type="technical_analysis_snapshot",
        timestamp=timestamp,
        execution_id=execution_id,
        key=snapshot_key,
        parts=(clean_symbol,),
    )


def new_market_breadth_snapshot_id(
    *,
    universe: str,
    timestamp: datetime,
    execution_id: str | None = None,
    snapshot_key: str | None = None,
) -> str:
    clean_universe = require_non_empty_identifier(
        universe,
        "universe",
    )
    return _snapshot_market_id(
        record_type="market_breadth_snapshot",
        timestamp=timestamp,
        execution_id=execution_id,
        key=snapshot_key,
        parts=(clean_universe,),
    )


def new_market_event_snapshot_id(
    *,
    symbol: str,
    timestamp: datetime,
    execution_id: str | None = None,
    snapshot_key: str | None = None,
) -> str:
    clean_symbol = require_non_empty_identifier(
        symbol,
        "symbol",
    ).upper()
    return _snapshot_market_id(
        record_type="market_event_snapshot",
        timestamp=timestamp,
        execution_id=execution_id,
        key=snapshot_key,
        parts=(clean_symbol,),
    )


def _stable_market_id(
    record_type: str,
    timestamp: datetime,
    *parts: str,
) -> str:
    clean_record_type = require_non_empty_identifier(
        record_type,
        "record_type",
    )
    clean_parts = tuple(
        require_non_empty_identifier(
            part,
            "id_part",
        )
        for part in parts
    )

    return ":".join(
        (
            clean_record_type,
            timestamp.isoformat(),
            *clean_parts,
        )
    )


def _snapshot_market_id(
    *,
    record_type: str,
    timestamp: datetime,
    execution_id: str | None,
    key: str | None,
    parts: tuple[str, ...] = (),
) -> str:
    clean_record_type = require_non_empty_identifier(
        record_type,
        "record_type",
    )
    clean_execution_id = clean_optional_identifier(
        execution_id,
        "execution_id",
    )
    clean_key = clean_optional_identifier(
        key,
        "snapshot_key",
    )

    if clean_execution_id is None:
        return f"{clean_record_type}:{uuid4().hex}"

    id_parts = [
        clean_record_type,
        clean_execution_id,
        timestamp.isoformat(),
        *parts,
    ]
    if clean_key is not None:
        id_parts.append(clean_key)

    return ":".join(id_parts)


def _normalize_symbol_source_fields(
    record: MarketOhlcvRecord | MarketIndicatorRecord,
) -> None:
    object.__setattr__(
        record,
        "symbol",
        require_non_empty_identifier(
            record.symbol,
            "symbol",
        ).upper(),
    )
    object.__setattr__(
        record,
        "source",
        require_non_empty_identifier(
            record.source,
            "source",
        ),
    )


def _normalize_optional_context_fields(
    record: MarketContextSnapshotRecord,
) -> None:
    for field_name in (
        "source",
        "universe",
        "market_regime",
        "volatility_regime",
        "breadth_regime",
    ):
        object.__setattr__(
            record,
            field_name,
            clean_optional_identifier(
                getattr(
                    record,
                    field_name,
                ),
                field_name,
            ),
        )


def _normalize_optional_regime_fields(
    record: TechnicalAnalysisSnapshotRecord,
) -> None:
    for field_name in (
        "source",
        "technical_regime",
        "trend_regime",
        "volatility_regime",
        "breadth_regime",
    ):
        object.__setattr__(
            record,
            field_name,
            clean_optional_identifier(
                getattr(
                    record,
                    field_name,
                ),
                field_name,
            ),
        )


def _require_non_negative_float(
    value: float,
    field_name: str,
) -> None:
    if value < 0.0:
        raise ValueError(f"{field_name} cannot be negative.")


def _require_optional_non_negative_float(
    value: float | None,
    field_name: str,
) -> None:
    if value is None:
        return

    _require_non_negative_float(
        value,
        field_name,
    )


def _require_optional_non_negative_int(
    value: int | None,
    field_name: str,
) -> None:
    if value is None:
        return

    if value < 0:
        raise ValueError(f"{field_name} cannot be negative.")


def _require_optional_ratio(
    value: float | None,
    field_name: str,
) -> None:
    if value is None:
        return

    if value < 0.0 or value > 1.0:
        raise ValueError(f"{field_name} must be between 0.0 and 1.0.")


def _require_optional_stability_score(
    value: float | None,
    field_name: str,
) -> None:
    if value is None:
        return

    if value < -1.0 or value > 1.0:
        raise ValueError(f"{field_name} must be between -1.0 and 1.0.")
