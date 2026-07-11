from __future__ import annotations

from application.reports import MorningReportAssembler


FULL_MACRO_LLM_RESPONSE = (
    "Macro desk full response line one.\n\n"
    "Macro desk full response line two with attribution context. "
    "END_OF_FULL_LLM_RESPONSE"
)


FULL_TECHNICAL_LLM_RESPONSE = (
    "Technical desk full response line one.\nTechnical desk full response line two."
)


FULL_STRATEGY_LLM_RESPONSE = (
    "Strategy synthesis full narrative line one.\n\n"
    "Strategy synthesis full narrative line two with complete rationale. "
    "END_OF_FULL_STRATEGY_LLM_RESPONSE"
)


def test_assembler_extracts_portfolio_intelligence_risk_and_action_sections() -> None:
    document = MorningReportAssembler().assemble(
        _complete_workflow_result(),
    )

    assert document.symbol == "QQQ"
    assert document.execution_id == "exec-report-1"
    assert document.status == "Succeeded"
    assert document.generated_at == "2026-05-26T13:30:00Z"

    assert (
        _metric_value(document.portfolio_snapshot, "Portfolio Value") == "$1,000,000.00"
    )
    assert _metric_value(document.portfolio_snapshot, "Cash Allocation") == "25.0%"
    assert _metric_value(document.portfolio_snapshot, "Leverage") == "1.21"
    assert _metric_value(document.portfolio_snapshot, "Margin Utilization") == "34.0%"
    assert _metric_value(document.portfolio_snapshot, "Portfolio Regime") == "Balanced"
    assert _metric_value(document.portfolio_snapshot, "Directional Bias") == "Long Bias"
    assert (
        _table_value(document.portfolio_snapshot, "Portfolio PnL", "Total PnL")
        == "6.1%"
    )
    assert (
        _table_value(document.portfolio_snapshot, "Portfolio PnL", "Realized PnL")
        == "3.7%"
    )
    assert (
        _table_value(
            document.portfolio_snapshot,
            "Portfolio PnL",
            "Intraday Unrealized PnL",
        )
        == "$1,250.55"
    )
    assert (
        _table_value(
            document.portfolio_snapshot,
            "Portfolio Exposure",
            "Long Market Value",
        )
        == "$720,000.00"
    )
    assert (
        _table_value(
            document.portfolio_snapshot, "Portfolio Exposure", "Short Exposure"
        )
        == "8.0%"
    )
    assert (
        _table_value(
            document.portfolio_snapshot,
            "Portfolio Risk & Constraints",
            "Largest Position",
        )
        == "18.0%"
    )
    assert (
        _table_value(
            document.portfolio_snapshot,
            "Portfolio Risk & Constraints",
            "Account Health",
        )
        == "Healthy"
    )
    assert (
        _table_value(
            document.portfolio_snapshot,
            "Portfolio Risk & Constraints",
            "Account Restrictions",
        )
        == "None Reported"
    )

    assert document.macro_backdrop.summary == FULL_MACRO_LLM_RESPONSE
    assert _metric_value(document.macro_backdrop, "Macro Regime") == "Constructive"
    assert _metric_value(document.macro_backdrop, "Fed Stance") == "Pause"

    assert document.technical_setup.summary == FULL_TECHNICAL_LLM_RESPONSE
    assert _metric_value(document.technical_setup, "Technical Regime") == "Bullish"
    assert _metric_value(document.technical_setup, "Execution Readiness") == "82.0%"
    assert (
        _metric_value(document.technical_setup, "Breadth Regime")
        == "Very Strong Breadth"
    )
    assert _metric_value(document.technical_setup, "Breadth Score") == "0.64"
    assert (
        _table_value(document.technical_setup, "Market Breadth", "% Above 50DMA")
        == "71.0%"
    )
    assert (
        _table_value(document.technical_setup, "Market Breadth", "McClellan Oscillator")
        == "18.25"
    )
    assert (
        _table_value(
            document.technical_setup, "Market Breadth", "Price / A-D Divergence"
        )
        == "No"
    )

    assert "News desk full response" in document.news_sentiment.summary
    assert "Sentiment desk full response" in document.news_sentiment.summary
    assert _metric_value(document.news_sentiment, "Headlines Reviewed") == "12"
    assert _metric_value(document.news_sentiment, "Sentiment Regime") == "Constructive"

    assert _metric_value(document.risk_assessment, "Composite Risk") == "0.62"
    assert _metric_value(document.risk_assessment, "Execution Guard") == "Review"
    assert "Volatility risk is 0.44" in document.risk_assessment.bullets[0].text

    assert "decision support only" in document.recommended_action_plan.summary
    assert (
        _metric_value(document.recommended_action_plan, "Strategy Posture")
        == "Selective Risk On"
    )
    assert (
        _metric_value(document.recommended_action_plan, "Selected Strategy") == "Bull"
    )
    assert (
        _metric_value(document.recommended_action_plan, "Synthesis Status")
        == "Selected"
    )
    assert (
        _metric_value(document.recommended_action_plan, "Synthesis Confidence")
        == "73.0%"
    )
    assert (
        _bullet_text(document.recommended_action_plan, "Selected thesis")
        == "Bull case thesis with broad confirmation."
    )
    assert (
        _bullet_text(document.recommended_action_plan, "Complete strategy narrative")
        == FULL_STRATEGY_LLM_RESPONSE
    )
    assert "Trend confirms upside" in _bullet_text(
        document.recommended_action_plan,
        "Decisive supporting evidence",
    )
    assert "Breadth is not yet decisive" in _bullet_text(
        document.recommended_action_plan,
        "Material contradictory evidence",
    )
    assert "Rates remain stable" in _bullet_text(
        document.recommended_action_plan,
        "Key assumptions",
    )
    assert "breadth_score stays above 0.35" in _bullet_text(
        document.recommended_action_plan,
        "Invalidation conditions",
    )
    assert "No unresolved synthesis conflicts" in _bullet_text(
        document.recommended_action_plan,
        "Unresolved conflicts",
    )
    assert (
        _table_value(
            document.recommended_action_plan,
            "Strategy Case Comparison",
            "Bull Case",
        )
        == "Synthesis 62.0% | Candidate 0.67 | Rank 1 | Status Selected"
    )
    assert "Synthesis 18.0%" in _table_value(
        document.recommended_action_plan,
        "Strategy Case Comparison",
        "Bear Case",
    )
    assert "Synthesis 20.0%" in _table_value(
        document.recommended_action_plan,
        "Strategy Case Comparison",
        "Sideways Case",
    )
    assert any(
        "human review" in bullet.text
        for bullet in document.recommended_action_plan.recommendations
    )


def test_assembler_degrades_missing_nodes_into_unavailable_sections() -> None:
    document = MorningReportAssembler().assemble(
        {
            "workflow_name": "morning_report",
            "execution_id": "exec-minimal",
            "status": "failed",
            "summary": {
                "symbol": "SPY",
            },
            "payload": {
                "workflow_inputs": {
                    "symbol": "SPY",
                },
                "node_outputs": {},
            },
            "error_message": "provider unavailable",
        }
    )

    assert document.symbol == "SPY"
    assert document.status == "Failed"
    assert document.run_errors == ("provider unavailable",)
    assert "not available" in document.macro_backdrop.summary
    assert "not available" in document.technical_setup.summary
    assert "not available" in document.news_sentiment.summary
    assert "not available" in document.risk_assessment.summary
    assert "not available" in document.recommended_action_plan.summary


def _metric_value(
    section: object,
    label: str,
) -> str:
    metrics = getattr(
        section,
        "metrics",
    )
    for metric in metrics:
        if metric.label == label:
            return metric.value

    raise AssertionError(f"missing metric: {label}")


def _bullet_text(
    section: object,
    label: str,
) -> str:
    bullets = getattr(
        section,
        "bullets",
    )
    for bullet in bullets:
        if bullet.label == label:
            return bullet.text

    raise AssertionError(f"missing bullet: {label}")


def _table_value(
    section: object,
    title: str,
    label: str,
) -> str:
    tables = getattr(
        section,
        "tables",
    )
    for table in tables:
        if table.title != title:
            continue

        for row in table.rows:
            if row.label == label:
                return row.value

    raise AssertionError(f"missing table value: {title} / {label}")


def _complete_workflow_result() -> dict[str, object]:
    return {
        "workflow_name": "morning_report",
        "execution_id": "exec-report-1",
        "success": True,
        "status": "succeeded",
        "summary": {
            "symbol": "QQQ",
            "completed_at": "2026-05-26T13:30:00Z",
        },
        "payload": {
            "workflow_inputs": {
                "symbol": "QQQ",
            },
            "node_outputs": {
                "portfolio_state_builder": {
                    "success": True,
                    "outputs": {
                        "confidence": 0.77,
                        "regime": "balanced",
                        "features": {
                            "portfolio_state": {
                                "portfolio_value": 1_000_000,
                                "cash": 250_000,
                                "cash_ratio": 0.25,
                                "cash_pct": 0.25,
                                "realized_pnl_pct": 0.037,
                                "unrealized_pnl_pct": 0.024,
                                "unrealized_intraday_pnl": 1250.55,
                                "unrealized_intraday_pnl_pct": 0.0013,
                                "pnl_total_pct": 0.061,
                                "long_market_value": 720_000,
                                "short_market_value": 80_000,
                                "gross_market_value": 800_000,
                                "net_market_value": 640_000,
                                "gross_exposure": 0.72,
                                "net_exposure": 0.64,
                                "long_exposure": 0.72,
                                "short_exposure": 0.08,
                                "leverage": 1.21,
                                "largest_position_pct": 0.18,
                                "concentration_score": 0.31,
                                "diversification_score": 0.69,
                                "beta_exposure": 1.08,
                                "beta_risk": 0.42,
                                "portfolio_heat": 0.46,
                                "risk_intensity": 0.41,
                                "margin_utilization_ratio": 0.34,
                                "account_health": "healthy",
                                "trading_blocked": False,
                                "transfers_blocked": False,
                                "account_blocked": False,
                                "trade_suspended_by_user": False,
                                "pattern_day_trader": False,
                                "portfolio_regime": "balanced",
                                "directional_bias": "long_bias",
                            },
                            "equity_state": {
                                "drawdown_percent": 0.035,
                            },
                            "positions_state": {
                                "position_count": 8,
                            },
                            "risk_features": {
                                "concentration": 0.31,
                            },
                        },
                    },
                },
                "fundamental_agent": {
                    "success": True,
                    "outputs": {
                        "directional_score": 0.58,
                        "confidence": 0.74,
                        "regime": "constructive",
                        "llm_response": FULL_MACRO_LLM_RESPONSE,
                        "features": {
                            "macro_state": {
                                "fed_stance": "pause",
                                "liquidity_regime": "neutral",
                                "inflation_regime": "cooling",
                                "growth_regime": "resilient",
                            },
                        },
                        "signals": [
                            "earnings_quality_improving",
                        ],
                    },
                },
                "technical_agent": {
                    "success": True,
                    "execution_metadata": {
                        "raw_debug_marker": "SECRET_RAW_RUNTIME_VALUE",
                    },
                    "outputs": {
                        "directional_score": 0.67,
                        "confidence": 0.79,
                        "regime": "bullish",
                        "llm_response": FULL_TECHNICAL_LLM_RESPONSE,
                        "features": {
                            "regime": {
                                "execution_readiness": 0.82,
                                "signal_quality": 0.76,
                                "calibration": {
                                    "breadth_score": 0.64,
                                    "breadth_risk_score": 0.18,
                                    "participation_score": 0.52,
                                },
                            },
                            "technical_state": {
                                "trend_direction": "uptrend",
                                "momentum_state": "positive",
                            },
                            "volatility": {
                                "volatility_regime": "normal",
                            },
                            "snapshot": {
                                "close": 450.25,
                                "rsi_14": 58.4,
                                "atr_14": 4.2,
                            },
                            "breadth": {
                                "has_breadth_data": True,
                                "breadth_regime": "very_strong_breadth",
                                "breadth_score": 0.64,
                                "breadth_risk_score": 0.18,
                                "participation_score": 0.52,
                                "leadership_score": 0.48,
                                "mcclellan_score": 0.31,
                                "price_ad_divergence": False,
                                "breadth_percent": 0.63,
                                "pct_above_50dma": 0.71,
                                "pct_above_200dma": 0.66,
                                "new_highs": 42,
                                "new_lows": 9,
                                "mcclellan_oscillator": 18.25,
                            },
                            "market_context": {
                                "advances_count": 312,
                                "declines_count": 183,
                                "breadth_percent": 0.63,
                                "pct_above_50dma": 0.71,
                                "pct_above_200dma": 0.66,
                                "new_highs": 42,
                                "new_lows": 9,
                                "mcclellan_oscillator": 18.25,
                                "price_ad_divergence": 0.0,
                            },
                            "raw_regime": {
                                "inputs": {
                                    "breadth_regime": "very_strong_breadth",
                                    "price_ad_divergence": False,
                                },
                            },
                        },
                    },
                },
                "news_agent": {
                    "success": True,
                    "outputs": {
                        "regime": "high_relevance",
                        "llm_response": "News desk full response. NEWS_LLM_END",
                        "features": {
                            "headline_count": 12,
                            "market_relevance": "high_relevance",
                            "primary_themes": [
                                "ai_capex",
                                "rates",
                            ],
                            "articles": [
                                {
                                    "title": "Mega-cap earnings support futures",
                                    "source": {
                                        "name": "Market Wire",
                                    },
                                    "description": "Short article description.",
                                }
                            ],
                        },
                    },
                },
                "sentiment_agent": {
                    "success": True,
                    "outputs": {
                        "directional_score": 0.54,
                        "confidence": 0.68,
                        "regime": "constructive",
                        "llm_response": "Sentiment desk full response. SENTIMENT_LLM_END",
                        "features": {
                            "composite_sentiment": 0.57,
                            "fear_greed_state": "neutral",
                            "positioning_state": "balanced",
                            "stability": 0.7,
                            "momentum": 0.52,
                        },
                    },
                },
                "risk_signal_builder": {
                    "success": True,
                    "outputs": {
                        "features": {
                            "primitive_sources": {
                                "volatility": 0.44,
                                "drawdown": 0.22,
                                "exposure": 0.36,
                            },
                        },
                    },
                },
                "risk_aggregator_agent": {
                    "success": True,
                    "outputs": {
                        "confidence": 0.71,
                        "regime": "moderate",
                        "features": {
                            "adjusted_composite_risk": 0.62,
                            "adjusted_risk_pressure": 0.48,
                            "stability_score": 0.55,
                            "risk_regime": "moderate",
                            "risk_bias": "balanced",
                        },
                        "risks": [
                            "volatility_breakout",
                        ],
                        "recommendations": [
                            "keep_position_sizes_moderate",
                        ],
                    },
                },
                "strategy_synthesis_agent": {
                    "success": True,
                    "outputs": {
                        "confidence": 0.73,
                        "regime": "selective_risk_on",
                        "llm_response": FULL_STRATEGY_LLM_RESPONSE,
                        "features": {
                            "posture": "selective_risk_on",
                            "execution_readiness": 0.69,
                            "portfolio_scale_factor": 0.6,
                            "selected_perspective": "bull",
                            "selection_status": "selected",
                            "hypothesis_candidate_scores": {
                                "bull": 0.67,
                                "bear": 0.19,
                                "sideways": 0.22,
                            },
                            "hypothesis_synthesis_weights": {
                                "bull": 0.62,
                                "bear": 0.18,
                                "sideways": 0.20,
                            },
                            "selected_hypothesis": {
                                "perspective": "bull",
                                "thesis": "Bull case thesis with broad confirmation.",
                                "supporting_evidence": [
                                    {
                                        "name": "technical_trend",
                                        "explanation": "Trend confirms upside",
                                        "strength": 0.81,
                                    },
                                ],
                                "contradicting_evidence": [
                                    {
                                        "name": "breadth_confirmation",
                                        "explanation": "Breadth is not yet decisive",
                                        "strength": 0.37,
                                    },
                                ],
                                "key_assumptions": [
                                    {
                                        "description": "Rates remain stable",
                                        "confidence": 0.72,
                                    },
                                ],
                                "invalidation_conditions": [
                                    {
                                        "description": "breadth_score stays above 0.35",
                                        "observed_value": 0.64,
                                        "operator": "<",
                                        "threshold": 0.35,
                                        "invalidated": False,
                                    },
                                ],
                                "risks": [
                                    "chasing_extended_prices",
                                ],
                            },
                            "strategy_synthesis_decision": {
                                "selected_perspective": "bull",
                                "selection_status": "selected",
                                "directional_score": 0.58,
                                "confidence": 0.73,
                                "regime": "selective_risk_on",
                                "uncertainty": 0.27,
                                "evaluations": [
                                    {
                                        "perspective": "bull",
                                        "perspective_weight": 0.60,
                                        "contradiction_burden": 0.10,
                                        "assumption_support": 0.90,
                                        "invalidated": False,
                                        "candidate_score": 0.67,
                                        "synthesis_weight": 0.62,
                                        "rank": 1,
                                        "selection_status": "selected",
                                        "degraded_reasons": [],
                                    },
                                    {
                                        "perspective": "bear",
                                        "perspective_weight": 0.20,
                                        "contradiction_burden": 0.35,
                                        "assumption_support": 0.55,
                                        "invalidated": False,
                                        "candidate_score": 0.19,
                                        "synthesis_weight": 0.18,
                                        "rank": 3,
                                        "selection_status": "rejected",
                                        "degraded_reasons": [],
                                    },
                                    {
                                        "perspective": "sideways",
                                        "perspective_weight": 0.20,
                                        "contradiction_burden": 0.25,
                                        "assumption_support": 0.65,
                                        "invalidated": False,
                                        "candidate_score": 0.22,
                                        "synthesis_weight": 0.20,
                                        "rank": 2,
                                        "selection_status": "rejected",
                                        "degraded_reasons": [],
                                    },
                                ],
                                "degraded_reasons": [],
                                "thesis": "Bull case thesis with broad confirmation.",
                                "signals": [
                                    "risk_on",
                                ],
                                "risks": [
                                    "late_cycle_momentum",
                                ],
                                "recommendations": [
                                    "add_exposure_selectively",
                                ],
                            },
                        },
                        "recommendations": [
                            "add_exposure_selectively",
                        ],
                    },
                },
                "portfolio_manager_agent": {
                    "success": True,
                    "outputs": {
                        "regime": "ready_for_review",
                        "features": {
                            "execution_status": "ready_for_review",
                            "scale_factor": 0.6,
                        },
                        "recommendations": [
                            "rebalance_toward_quality",
                        ],
                    },
                },
                "trade_packager": {
                    "success": True,
                    "outputs": {
                        "regime": "long_bias",
                        "features": {
                            "trade_intent": {
                                "direction": "long_bias",
                                "position_sizing_hint": 0.35,
                                "trade_quality_score": 0.72,
                                "entry_bias": 0.61,
                                "stop_distance": 0.04,
                                "take_profit_distance": 0.08,
                            },
                        },
                        "recommendations": [
                            "stage_entries",
                        ],
                    },
                },
                "execution_risk_guard": {
                    "success": True,
                    "outputs": {
                        "features": {
                            "execution_guard": {
                                "mode": "review",
                                "adjusted_position_size": 0.3,
                                "flags": [
                                    "requires_human_review",
                                ],
                            },
                        },
                        "recommendations": [
                            "confirm_liquidity_before_action",
                        ],
                    },
                },
            },
        },
    }
