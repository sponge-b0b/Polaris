from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from core.database.models.agent_intelligence import AgentReasoningModel
from core.database.models.agent_signals import AgentSignalModel
from core.database.models.macro import MacroRegimeSnapshotModel
from core.database.models.market import (
    MarketBreadthSnapshotModel,
    MarketContextSnapshotModel,
    MarketEventSnapshotModel,
    TechnicalAnalysisSnapshotModel,
)
from core.database.models.news import NewsAnalysisSnapshotModel
from core.database.models.portfolio import (
    PortfolioPositionHistoryModel,
    PortfolioRiskSnapshotModel,
)
from core.database.models.portfolio_state import PortfolioStateHistoryModel
from core.database.models.sentiment import SentimentSnapshotModel
from core.storage.persistence.agent_intelligence import AgentReasoningRecord
from core.storage.persistence.agent_signals import AgentSignalRecord
from core.storage.persistence.lineage import (
    PersistenceLineage,
    PersistenceRecordIdentity,
)
from core.storage.persistence.macro import MacroRegimeSnapshotRecord
from core.storage.persistence.market import (
    MarketBreadthSnapshotRecord,
    MarketContextSnapshotRecord,
    MarketEventSnapshotRecord,
    TechnicalAnalysisSnapshotRecord,
)
from core.storage.persistence.news import NewsAnalysisSnapshotRecord
from core.storage.persistence.portfolio import (
    PortfolioPositionHistoryRecord,
    PortfolioRiskSnapshotRecord,
)
from core.storage.persistence.sentiment import SentimentSnapshotRecord
from core.storage.persistence.serializers.agent_intelligence_persistence_serializer import (  # noqa: E501
    AgentIntelligencePersistenceSerializer,
)
from core.storage.persistence.serializers.agent_signal_persistence_serializer import (
    AgentSignalPersistenceSerializer,
)
from core.storage.persistence.serializers.macro_persistence_serializer import (
    MacroPersistenceSerializer,
)
from core.storage.persistence.serializers.market_persistence_serializer import (
    MarketPersistenceSerializer,
)
from core.storage.persistence.serializers.news_persistence_serializer import (
    NewsPersistenceSerializer,
)
from core.storage.persistence.serializers.portfolio_persistence_serializer import (
    PortfolioPersistenceSerializer,
)
from core.storage.persistence.serializers.portfolio_state_serializer import (
    PortfolioStateSerializer,
)
from core.storage.persistence.serializers.sentiment_persistence_serializer import (
    SentimentPersistenceSerializer,
)
from domain.portfolio.models.portfolio_state import PortfolioState


def test_market_service_outputs_round_trip_with_canonical_payload_columns() -> None:
    technical_record = _technical_analysis_output()
    context_record = _market_context_output()
    breadth_record = _breadth_output()
    event_record = _market_events_output()

    technical_model = TechnicalAnalysisSnapshotModel(
        **MarketPersistenceSerializer.technical_snapshot_values(technical_record),
    )
    context_model = MarketContextSnapshotModel(
        **MarketPersistenceSerializer.context_snapshot_values(context_record),
    )
    breadth_model = MarketBreadthSnapshotModel(
        **MarketPersistenceSerializer.breadth_snapshot_values(breadth_record),
    )
    event_model = MarketEventSnapshotModel(
        **MarketPersistenceSerializer.event_snapshot_values(event_record),
    )

    assert technical_model.directional_technical_score == 0.6789012345678901
    assert (
        technical_model.market_context_payload == context_record.market_context_payload
    )
    assert technical_model.breadth_payload == breadth_record.breadth_payload
    assert context_model.top_50_constituents_payload == {
        "symbols": ["AAPL", "MSFT", "NVDA"],
    }
    assert context_model.market_caps_payload == {
        "AAPL": 3_100_000_000_000.123,
        "MSFT": 2_900_000_000_000.456,
    }
    assert breadth_model.ad_line_trend_score == 0.4567890123456789
    assert event_model.volatility_forecast == "elevated"

    technical = MarketPersistenceSerializer.technical_snapshot_from_model(
        technical_model,
    )
    context = MarketPersistenceSerializer.context_snapshot_from_model(
        context_model,
    )
    breadth = MarketPersistenceSerializer.breadth_snapshot_from_model(
        breadth_model,
    )
    event = MarketPersistenceSerializer.event_snapshot_from_model(event_model)

    assert technical.snapshot_payload == technical_record.snapshot_payload
    assert technical.market_context_payload == technical_record.market_context_payload
    assert technical.breadth_payload == technical_record.breadth_payload
    assert technical.directional_technical_score == 0.6789012345678901
    assert context.market_context_payload == context_record.market_context_payload
    assert context.market_caps_payload == context_record.market_caps_payload
    assert context.ad_line_trend_score == 0.4123456789012345
    assert breadth.source_metrics_payload == breadth_record.source_metrics_payload
    assert breadth.breadth_payload == breadth_record.breadth_payload
    assert breadth.ad_line_trend_score == 0.4567890123456789
    assert event.events_payload == event_record.events_payload
    assert event.risk_projection_payload == event_record.risk_projection_payload

    _assert_physical_columns(
        TechnicalAnalysisSnapshotModel,
        include=("inputs_payload", "market_context_payload", "breadth_payload"),
        exclude=("inputs", "market_context", "breadth", "regime"),
    )
    _assert_physical_columns(
        MarketContextSnapshotModel,
        include=("top_50_constituents_payload", "market_caps_payload"),
        exclude=("top_50_constituents", "market_caps"),
    )


def test_optional_market_and_sentiment_fields_can_round_trip_empty_payloads() -> None:
    minimal_context = MarketContextSnapshotRecord(
        context_snapshot_id="market-context-minimal",
        timestamp=_timestamp(),
        lineage=_lineage("market_context"),
    )
    minimal_sentiment = SentimentSnapshotRecord(
        sentiment_snapshot_id="sentiment-minimal",
        timestamp=_timestamp(),
        lineage=_lineage("sentiment_node"),
    )

    context_model = MarketContextSnapshotModel(
        **MarketPersistenceSerializer.context_snapshot_values(minimal_context),
    )
    sentiment_model = SentimentSnapshotModel(
        **SentimentPersistenceSerializer.snapshot_values(minimal_sentiment),
    )

    context = MarketPersistenceSerializer.context_snapshot_from_model(context_model)
    sentiment = SentimentPersistenceSerializer.snapshot_from_model(sentiment_model)

    assert context.market_regime is None
    assert context.market_context_payload == {}
    assert context.top_50_constituents_payload == {}
    assert sentiment.market_regime is None
    assert sentiment.fusion_components == {}
    assert sentiment.providers_payload == {}
    assert sentiment.sentiment_payload == {}


def test_portfolio_state_equity_and_positions_round_trip_with_precision() -> None:
    state_record = _portfolio_state_output()
    position_record = _position_output()
    risk_record = _portfolio_risk_output()

    state_model = PortfolioStateSerializer.to_history_model(state_record)
    position_model = PortfolioPositionHistoryModel(
        **PortfolioPersistenceSerializer.position_history_values(position_record),
    )
    risk_model = PortfolioRiskSnapshotModel(
        **PortfolioPersistenceSerializer.risk_snapshot_values(risk_record),
    )

    assert state_model.equity == 100_000.123456789
    assert state_model.cash_ratio == 0.15306122448979592
    assert state_model.sector_exposure == {"technology": 0.4234567891234568}
    assert position_model.weight == 0.4234567891234568
    assert position_model.market_value == 42_345.67891234568
    assert risk_model.equity_retention_ratio == 0.9800034567890123

    state = PortfolioStateSerializer.from_history_model(state_model)
    position = PortfolioPersistenceSerializer.position_history_from_model(
        position_model
    )
    risk = PortfolioPersistenceSerializer.risk_snapshot_from_model(risk_model)

    assert state == state_record
    assert state.cash_ratio == 0.15306122448979592
    assert state.risk_signals["drawdown"]["score"] == 0.06666888888888889
    assert position.weight == 0.4234567891234568
    assert position.metadata == position_record.metadata
    assert risk.risk_signals == risk_record.risk_signals
    assert risk.equity_retention_ratio == 0.9800034567890123

    _assert_physical_columns(
        PortfolioStateHistoryModel,
        include=("cash_pct", "risk_signals_payload", "equity_state_payload"),
        exclude=("cash_ratio", "risk_signals"),
    )
    _assert_physical_columns(
        PortfolioPositionHistoryModel,
        include=("exposure_weight", "position_payload"),
        exclude=("weight",),
    )


def test_macro_news_sentiment_and_agent_outputs_round_trip_without_truncation() -> None:
    macro_record = _macro_output()
    sentiment_record = _sentiment_output()
    news_record = _news_output()
    signal_record = _agent_signal_output()
    reasoning_record = _agent_reasoning_output()

    macro_model = MacroRegimeSnapshotModel(
        **MacroPersistenceSerializer.regime_snapshot_values(macro_record),
    )
    sentiment_model = SentimentSnapshotModel(
        **SentimentPersistenceSerializer.snapshot_values(sentiment_record),
    )
    news_model = NewsAnalysisSnapshotModel(
        **NewsPersistenceSerializer.analysis_snapshot_values(news_record),
    )
    signal_model = AgentSignalModel(
        **AgentSignalPersistenceSerializer.signal_values(signal_record),
    )
    reasoning_model = AgentReasoningModel(
        **AgentIntelligencePersistenceSerializer.reasoning_values(reasoning_record),
    )

    macro = MacroPersistenceSerializer.regime_snapshot_from_model(macro_model)
    sentiment = SentimentPersistenceSerializer.snapshot_from_model(sentiment_model)
    news = NewsPersistenceSerializer.analysis_snapshot_from_model(news_model)
    signal = AgentSignalPersistenceSerializer.signal_from_model(signal_model)
    reasoning = AgentIntelligencePersistenceSerializer.reasoning_from_model(
        reasoning_model,
    )

    assert macro.outputs == macro_record.outputs
    assert macro.macro_score == 0.1234567890123456
    assert sentiment.fusion_components == sentiment_record.fusion_components
    assert sentiment.composite_sentiment == 0.23456789012345678
    assert news.full_llm_response == news_record.full_llm_response
    assert len(news.full_llm_response or "") == len(news_record.full_llm_response or "")
    assert signal.signals == signal_record.signals
    assert signal.llm_response == signal_record.llm_response
    assert reasoning.reasoning_text == reasoning_record.reasoning_text
    assert reasoning.full_llm_response == reasoning_record.full_llm_response
    assert reasoning.outputs == reasoning_record.outputs

    _assert_physical_columns(
        AgentReasoningModel,
        include=("inputs_payload", "outputs_payload", "full_llm_response"),
        exclude=("inputs", "outputs"),
    )
    _assert_physical_columns(
        NewsAnalysisSnapshotModel,
        include=("full_llm_response",),
        exclude=("truncated_llm_response",),
    )


def _technical_analysis_output() -> TechnicalAnalysisSnapshotRecord:
    return TechnicalAnalysisSnapshotRecord(
        technical_snapshot_id="technical-realistic-1",
        symbol="spy",
        timestamp=_timestamp(),
        source="technical_analysis_service",
        technical_regime="bullish",
        trend_regime="uptrend",
        volatility_regime="normalizing",
        breadth_regime="constructive",
        technical_score=0.5890123456789012,
        directional_technical_score=0.6789012345678901,
        bull_score=0.7123456789012345,
        bear_score=0.1876543210987654,
        sideways_score=0.1,
        trend_score=0.6234567890123456,
        trend_strength=0.5345678901234567,
        trend_quality=0.6456789012345678,
        volatility_score=0.23456789012345678,
        breadth_score=0.4567890123456789,
        risk_score=0.267890123456789,
        trend_risk_score=0.19876543210987654,
        volatility_risk_score=0.31234567890123456,
        breadth_risk_score=0.28765432109876543,
        strategy_environment="risk_on",
        confidence=0.8123456789012345,
        inputs_payload={"symbol": "SPY", "lookback_days": 252},
        snapshot_payload={
            "close": 532.123456789,
            "rsi_14": 61.12345678901234,
        },
        market_context_payload=_market_context_payload(),
        micro_regime_payload={"micro_regime": "trend_continuation"},
        trend_payload={"trend_score": 0.6234567890123456},
        volatility_payload={"vix": 14.123456789012345},
        breadth_payload=_breadth_payload(),
        raw_regime_payload={"regime": "bullish", "score": 0.5890123456789012},
        regime_payload={
            "calibrated_regime": "bullish",
            "confidence": 0.8123456789012345,
        },
        lineage=_lineage("technical_analysis"),
        metadata={"service": "TechnicalAnalysisService"},
    )


def _market_context_output() -> MarketContextSnapshotRecord:
    return MarketContextSnapshotRecord(
        context_snapshot_id="market-context-realistic-1",
        timestamp=_timestamp(),
        source="technical_analysis_service",
        universe="sp500",
        market_regime="constructive",
        volatility_regime="normalizing",
        breadth_regime="constructive",
        trend_score=0.6234567890123456,
        volatility_score=0.23456789012345678,
        breadth_score=0.4567890123456789,
        risk_score=0.267890123456789,
        vix=14.123456789012345,
        vix_20=15.234567890123456,
        vix_50=16.345678901234567,
        vix_percentile_252=0.28765432109876543,
        vix_trend_ratio=0.9234567890123456,
        vix_change_5d=-0.1234567890123456,
        vix_change_20d=-0.23456789012345678,
        vvix=82.12345678901235,
        vvix_20=84.23456789012345,
        vvix_50=86.34567890123457,
        vvix_percentile_252=0.3765432109876543,
        vvix_trend_ratio=0.9487654321098765,
        vvix_change_5d=-0.08765432109876543,
        vvix_change_20d=-0.1765432109876543,
        market_cap_index=100.12345678901235,
        market_cap_index_20=98.23456789012345,
        market_cap_index_50=96.34567890123457,
        market_cap_index_change_5d=0.019230769230769232,
        market_cap_index_change_20d=0.0392156862745098,
        advances_count=318,
        declines_count=174,
        unchanged_count=8,
        active_count=500,
        net_breadth=144,
        breadth_percent=0.636,
        ad_ratio=1.8275862068965518,
        ad_line=12_345.6789012345,
        ad_line_ema_10=12_200.123456789,
        ad_line_ema_20=12_050.23456789,
        ad_line_ema_50=11_800.345678901,
        ad_line_slope_5=0.03456789012345678,
        ad_line_slope_20=0.023456789012345678,
        ad_line_trend_ratio=1.0245678901234568,
        ad_line_trend_score=0.4123456789012345,
        price_ad_divergence=0.08765432109876543,
        pct_above_50dma=0.6434567890123457,
        pct_above_200dma=0.5765432109876543,
        new_highs=42,
        new_lows=7,
        new_high_low_diff=35,
        new_high_low_ratio=6.0,
        net_breadth_ema_19=128.123456789,
        net_breadth_ema_39=111.23456789,
        mcclellan_oscillator=16.888888899,
        mcclellan_summation_index=345.123456789,
        has_vix=True,
        has_vvix=True,
        has_sp500=True,
        has_ad_line=True,
        has_breadth=True,
        inputs_payload={"breadth_source": "get_sp500_data"},
        market_context_payload=_market_context_payload(),
        top_50_constituents_payload={"symbols": ["AAPL", "MSFT", "NVDA"]},
        market_caps_payload={
            "AAPL": 3_100_000_000_000.123,
            "MSFT": 2_900_000_000_000.456,
        },
        lineage=_lineage("market_context"),
        metadata={"service": "TechnicalAnalysisService"},
    )


def _breadth_output() -> MarketBreadthSnapshotRecord:
    return MarketBreadthSnapshotRecord(
        breadth_snapshot_id="breadth-realistic-1",
        timestamp=_timestamp(),
        universe="sp500",
        source="technical_analysis_service",
        has_breadth_data=True,
        advances_count=318,
        declines_count=174,
        unchanged_count=8,
        new_highs=42,
        new_lows=7,
        ad_line=12_345.6789012345,
        ad_line_ema_10=12_200.123456789,
        ad_line_ema_20=12_050.23456789,
        ad_line_ema_50=11_800.345678901,
        ad_line_slope_5=0.03456789012345678,
        ad_line_slope_20=0.023456789012345678,
        ad_line_trend_ratio=1.0245678901234568,
        ad_line_trend_score=0.4567890123456789,
        price_ad_divergence=0.08765432109876543,
        pct_above_50dma=0.6434567890123457,
        pct_above_200dma=0.5765432109876543,
        new_high_low_diff=35,
        new_high_low_ratio=6.0,
        net_breadth_ema_19=128.123456789,
        net_breadth_ema_39=111.23456789,
        mcclellan_oscillator=16.888888899,
        mcclellan_summation_index=345.123456789,
        breadth_score=0.4567890123456789,
        breadth_risk_score=0.28765432109876543,
        trend_score=0.4123456789012345,
        slope_score=0.3987654321098765,
        confirmation_score=0.5345678901234567,
        participation_score=0.4567890123456789,
        leadership_score=0.3765432109876543,
        mcclellan_score=0.28765432109876543,
        divergence_score=0.08765432109876543,
        breadth_regime="constructive",
        risk_regime="moderate",
        strategy_environment="risk_on",
        inputs_payload={"universe": "sp500"},
        components_payload={"participation": 0.4567890123456789},
        source_metrics_payload={"active_count": 500, "has_breadth": True},
        breadth_payload=_breadth_payload(),
        lineage=_lineage("market_breadth"),
        metadata={"service": "TechnicalAnalysisService"},
    )


def _market_events_output() -> MarketEventSnapshotRecord:
    return MarketEventSnapshotRecord(
        event_snapshot_id="market-events-realistic-1",
        symbol="spy",
        timestamp=_timestamp(),
        source="market_events_service",
        market_pressure_score=0.3456789012345679,
        volatility_forecast="elevated",
        regime_bias="risk_on_with_event_risk",
        event_count=3,
        high_impact_count=1,
        events_payload={"events": [{"name": "CPI", "impact": "high"}]},
        high_impact_events_payload={"events": ["FOMC"]},
        risk_projection_payload={"volatility_forecast": "elevated"},
        lineage=_lineage("market_events"),
        metadata={"service": "MarketEventsService"},
    )


def _portfolio_state_output() -> PortfolioState:
    return PortfolioState(
        snapshot_id="portfolio-state-realistic-1",
        account_id="account-1",
        timestamp=_timestamp(),
        schema_version=2,
        equity=100_000.123456789,
        peak_equity=105_000.234567891,
        portfolio_value=98_000.345678912,
        cash=15_000.456789123,
        buying_power=20_000.567891234,
        last_equity=99_000.678912345,
        cash_ratio=0.15306122448979592,
        buying_power_ratio=0.20408163265306123,
        realized_pnl=1_250.789123456,
        realized_pnl_pct=0.01250789123456,
        unrealized_pnl=-500.891234567,
        unrealized_pnl_pct=-0.00500891234567,
        unrealized_intraday_pnl=125.912345678,
        unrealized_intraday_pnl_pct=0.00125912345678,
        pnl_total=750.123456789,
        pnl_total_pct=0.00750123456789,
        drawdown_absolute=7_000.234567891,
        drawdown_percent=0.06666888888888889,
        capital_base=100_000.0,
        equity_retention_ratio=0.9800034567890123,
        long_market_value=80_000.111111111,
        short_market_value=-12_000.222222222,
        gross_market_value=92_000.333333333,
        net_market_value=68_000.444444444,
        gross_exposure=0.9387789123456789,
        net_exposure=0.6938812345678901,
        long_exposure=0.8163288888888889,
        short_exposure=0.12244777777777778,
        leverage=0.9387799999999999,
        largest_position_pct=0.2145678912345679,
        concentration_score=0.3656789123456789,
        diversification_score=0.7345678912345678,
        beta_exposure=1.0876543210987654,
        beta_risk=0.18765432109876543,
        portfolio_heat=0.2765432198765432,
        risk_intensity=0.3234567890123457,
        initial_margin=10_000.111111111,
        maintenance_margin=8_000.222222222,
        last_maintenance_margin=7_500.333333333,
        margin_utilization_ratio=0.16666777777777778,
        initial_margin_ratio=0.1020401234567901,
        daytrade_count=2,
        pattern_day_trader=True,
        trading_blocked=False,
        transfers_blocked=False,
        account_blocked=False,
        trade_suspended_by_user=False,
        shorting_enabled=True,
        position_count=7,
        portfolio_regime="risk_on",
        directional_bias="bullish",
        account_health="healthy",
        sector_exposure={"technology": 0.4234567891234568},
        asset_class_exposure={"us_equity": 0.8123456789012345},
        risk_signals={"drawdown": {"score": 0.06666888888888889}},
    )


def _position_output() -> PortfolioPositionHistoryRecord:
    return PortfolioPositionHistoryRecord(
        position_history_id="position-realistic-1",
        account_id="account-1",
        symbol="aapl",
        snapshot_id="portfolio-state-realistic-1",
        timestamp=_timestamp(),
        quantity=123.45678912345678,
        market_value=42_345.67891234568,
        cost_basis=40_000.123456789,
        weight=0.4234567891234568,
        sector="technology",
        theme="ai_infrastructure",
        beta=1.1876543210987654,
        risk_weight=0.3656789123456789,
        lineage=_lineage("portfolio_state"),
        metadata={"provider": "alpaca"},
    )


def _portfolio_risk_output() -> PortfolioRiskSnapshotRecord:
    return PortfolioRiskSnapshotRecord(
        risk_snapshot_id="portfolio-risk-realistic-1",
        account_id="account-1",
        snapshot_id="portfolio-state-realistic-1",
        timestamp=_timestamp(),
        portfolio_value=98_000.345678912,
        cash=15_000.456789123,
        account_health="healthy",
        risk_score=0.3234567890123457,
        risk_level="moderate",
        drawdown_risk=0.06666888888888889,
        volatility_risk=0.28765432109876543,
        concentration_risk=0.3656789123456789,
        liquidity_risk=0.08765432109876543,
        beta=1.0876543210987654,
        cash_ratio=0.15306122448979592,
        equity_retention_ratio=0.9800034567890123,
        risk_signals={"drawdown": {"score": 0.06666888888888889}},
        lineage=_lineage("portfolio_state"),
        metadata={"provider": "alpaca"},
    )


def _macro_output() -> MacroRegimeSnapshotRecord:
    return MacroRegimeSnapshotRecord(
        regime_snapshot_id="macro-realistic-1",
        timestamp=_timestamp(),
        source="macro_service",
        region="US",
        inflation_regime="disinflation",
        liquidity_regime="tight",
        growth_regime="resilient",
        fed_stance="restrictive",
        yield_curve_regime="inverted",
        macro_regime="late_cycle",
        economic_regime="expansion",
        inflation_score=0.21234567890123456,
        liquidity_score=-0.28765432109876543,
        growth_score=0.5123456789012346,
        yield_curve_score=-0.6234567890123457,
        macro_score=0.1234567890123456,
        risk_score=0.4123456789012346,
        confidence=0.8234567890123457,
        inputs={"series": ["CPI", "DGS10", "DGS2"]},
        outputs={"macro_regime": "late_cycle", "score": 0.1234567890123456},
        lineage=_lineage("macro_analysis"),
        metadata={"service": "MacroService"},
    )


def _sentiment_output() -> SentimentSnapshotRecord:
    return SentimentSnapshotRecord(
        sentiment_snapshot_id="sentiment-realistic-1",
        timestamp=_timestamp(),
        source="sentiment_service",
        symbol="spy",
        universe="us_equities",
        market_regime="neutral_positive",
        fear_greed_score=0.6234567890123457,
        news_sentiment_score=0.1234567890123456,
        market_sentiment_score=0.3456789012345679,
        social_sentiment_score=-0.08765432109876543,
        composite_sentiment=0.23456789012345678,
        confidence=0.7456789012345678,
        fusion_components={"news": 0.1234567890123456, "market": 0.3456789012345679},
        providers_payload={"article_count": 47},
        sentiment_payload={"sentiment_regime": "neutral_positive"},
        lineage=_lineage("sentiment_node"),
        metadata={"service": "SentimentService"},
    )


def _news_output() -> NewsAnalysisSnapshotRecord:
    full_response = "\n".join(
        f"Paragraph {index}: complete analyst response retained."
        for index in range(200)
    )
    return NewsAnalysisSnapshotRecord(
        analysis_snapshot_id="news-realistic-1",
        timestamp=_timestamp(),
        source="news_service",
        article_ids=("article-1", "article-2"),
        symbols=("SPY", "QQQ"),
        themes=("macro", "earnings"),
        importance_score=0.8123456789012345,
        sentiment_score=0.1234567890123456,
        impact_score=0.4345678901234568,
        confidence=0.8567890123456789,
        llm_summary="Policy and earnings risks remain balanced.",
        full_llm_response=full_response,
        analysis_model="gpt-test",
        inputs={"article_count": 2},
        outputs={"market_impact": "balanced"},
        lineage=_lineage("news_node"),
        metadata={"service": "NewsService"},
    )


def _agent_signal_output() -> AgentSignalRecord:
    full_response = "Strategy synthesis retained response. " * 120
    return AgentSignalRecord(
        signal_id="agent-signal-realistic-1",
        agent_name="StrategySynthesisAgent",
        agent_type="strategy",
        workflow_name="morning_report",
        execution_id="exec-realistic-1",
        runtime_id="runtime-realistic-1",
        node_name="strategy_synthesis",
        symbol="SPY",
        universe=("SPY", "QQQ"),
        timestamp=_timestamp(),
        directional_score=0.4567890123456789,
        confidence=0.8234567890123457,
        regime="risk_on",
        signals={"technical": {"directional_score": 0.6789012345678901}},
        risks={"drawdown": {"score": 0.06666888888888889}},
        recommendations={"posture": "moderate_risk_on"},
        features={"top_50_constituents": ["AAPL", "MSFT", "NVDA"]},
        reasoning_text="Full strategy reasoning.",
        llm_response=full_response,
        metadata={"node": "strategy_synthesis"},
    )


def _agent_reasoning_output() -> AgentReasoningRecord:
    full_text = "Detailed reasoning is preserved. " * 150
    full_response = "Complete LLM response is preserved. " * 160
    return AgentReasoningRecord(
        reasoning_id="agent-reasoning-realistic-1",
        agent_signal_id="agent-signal-realistic-1",
        agent_name="StrategySynthesisAgent",
        agent_type="strategy",
        timestamp=_timestamp(),
        reasoning_text=full_text,
        reasoning_type="strategy_synthesis",
        model_name="gpt-test",
        prompt_version="strategy-v1",
        symbol="SPY",
        universe="us_equities",
        full_llm_response=full_response,
        inputs={"signals": ["technical", "macro", "sentiment"]},
        outputs={"recommendation": "moderate_risk_on"},
        linked_records=(
            PersistenceRecordIdentity(
                record_type="agent_signal",
                record_id="agent-signal-realistic-1",
            ),
        ),
        lineage=_lineage("strategy_synthesis"),
        metadata={"node": "strategy_synthesis"},
    )


def _market_context_payload() -> dict[str, Any]:
    return {
        "market_regime": "constructive",
        "vix": 14.123456789012345,
        "top_50_constituents": ["AAPL", "MSFT", "NVDA"],
    }


def _breadth_payload() -> dict[str, Any]:
    return {
        "advances": 318,
        "declines": 174,
        "ad_line_trend_score": 0.4567890123456789,
    }


def _assert_physical_columns(
    model: type[Any],
    *,
    include: tuple[str, ...],
    exclude: tuple[str, ...],
) -> None:
    column_names = {column.name for column in model.__table__.columns}
    for column in include:
        assert column in column_names
    for column in exclude:
        assert column not in column_names


def _lineage(node_name: str) -> PersistenceLineage:
    return PersistenceLineage(
        workflow_name="morning_report",
        execution_id="exec-realistic-1",
        runtime_id="runtime-realistic-1",
        node_name=node_name,
    )


def _timestamp() -> datetime:
    return datetime(2026, 6, 13, 13, 30, tzinfo=UTC)
