from __future__ import annotations

from typing import Any

from application.reports.morning_report_models import MorningReportDocument
from application.reports.morning_report_models import ReportBullet
from application.reports.morning_report_models import ReportMetric
from application.reports.morning_report_models import ReportSection
from application.reports.morning_report_models import ReportTable
from application.reports.morning_report_models import ReportTableRow
from application.reports.morning_report_models import format_confidence
from application.reports.morning_report_models import format_currency
from application.reports.morning_report_models import format_percent
from application.reports.morning_report_models import format_regime
from application.reports.morning_report_models import format_score
from application.reports.morning_report_sections import BoundaryMapping
from application.reports.morning_report_sections import first_score
from application.reports.morning_report_sections import first_text
from application.reports.morning_report_sections import get_execution_id
from application.reports.morning_report_sections import get_node_outputs
from application.reports.morning_report_sections import get_path
from application.reports.morning_report_sections import get_symbol
from application.reports.morning_report_sections import get_workflow_status
from application.reports.morning_report_sections import safe_list
from application.reports.morning_report_sections import safe_mapping
from application.reports.morning_report_sections import summarize_long_text


class MorningReportAssembler:
    """
    Assemble a typed, human-facing morning report from workflow boundary data.

    The assembler reads dictionaries only at the workflow rendering boundary.
    Internally it produces typed report objects and display-ready strings so raw
    RuntimeNodeOutput JSON is not leaked into professional report sections.
    """

    def assemble(
        self,
        workflow_result: BoundaryMapping,
    ) -> MorningReportDocument:
        symbol = get_symbol(
            workflow_result,
        )
        execution_id = get_execution_id(
            workflow_result,
        )
        status = format_regime(
            get_workflow_status(
                workflow_result,
            ),
            fallback="Unknown",
        )

        portfolio_snapshot = self._build_portfolio_snapshot(
            workflow_result,
        )
        executive_summary = self._build_executive_summary(
            workflow_result,
            portfolio_snapshot=portfolio_snapshot,
        )

        return MorningReportDocument(
            title="Polaris Morning Financial Report",
            subtitle=f"Pre-market intelligence summary for {symbol}",
            symbol=symbol,
            execution_id=execution_id,
            generated_at=self._report_generated_at(
                workflow_result,
            ),
            status=status,
            executive_summary=executive_summary,
            portfolio_snapshot=portfolio_snapshot,
            macro_backdrop=self._build_macro_backdrop(
                workflow_result,
            ),
            technical_setup=self._build_technical_setup(
                workflow_result,
            ),
            news_sentiment=self._build_news_sentiment(
                workflow_result,
            ),
            risk_assessment=self._build_risk_assessment(
                workflow_result,
            ),
            recommended_action_plan=self._build_recommended_action_plan(
                workflow_result,
            ),
            run_errors=self._run_errors(
                workflow_result,
            ),
        )

    def _build_executive_summary(
        self,
        workflow_result: BoundaryMapping,
        *,
        portfolio_snapshot: ReportSection,
    ) -> ReportSection:
        portfolio = self._portfolio_outputs(
            workflow_result,
        )
        strategy = get_node_outputs(
            workflow_result,
            "strategy_synthesis_agent",
        )
        risk = self._risk_outputs(
            workflow_result,
        )
        guard = self._execution_guard_outputs(
            workflow_result,
        )

        strategy_features = safe_mapping(
            strategy.get(
                "features",
            )
        )
        risk_features = safe_mapping(
            risk.get(
                "features",
            )
        )
        guard_features = safe_mapping(
            guard.get(
                "features",
            )
        )
        execution_guard = safe_mapping(
            guard_features.get(
                "execution_guard",
            )
        )

        market_bias = format_regime(
            first_text(
                strategy_features.get(
                    "posture",
                ),
                strategy.get(
                    "regime",
                ),
                strategy_features.get(
                    "technical_regime",
                ),
                fallback="Neutral / Unconfirmed",
            ),
            fallback="Neutral / Unconfirmed",
        )
        risk_posture = format_regime(
            first_text(
                risk_features.get(
                    "risk_regime",
                ),
                risk.get(
                    "regime",
                ),
                risk_features.get(
                    "risk_bias",
                ),
                fallback="Unknown",
            ),
            fallback="Unknown",
        )
        portfolio_posture = self._portfolio_posture(
            portfolio,
        )
        execution_posture = format_regime(
            first_text(
                execution_guard.get(
                    "mode",
                ),
                guard.get(
                    "regime",
                ),
                fallback="Not Evaluated",
            ),
            fallback="Not Evaluated",
        )
        confidence = first_score(
            strategy.get(
                "confidence",
            ),
            risk.get(
                "confidence",
            ),
            portfolio.get(
                "confidence",
            ),
        )
        composite_risk = first_score(
            risk_features.get(
                "adjusted_composite_risk",
            ),
            risk_features.get(
                "composite_risk",
            ),
            strategy_features.get(
                "composite_risk",
            ),
        )

        metrics = (
            ReportMetric(
                label="Market Bias",
                value=market_bias,
            ),
            ReportMetric(
                label="Risk Posture",
                value=risk_posture,
            ),
            ReportMetric(
                label="Portfolio Posture",
                value=portfolio_posture,
            ),
            ReportMetric(
                label="Execution Posture",
                value=execution_posture,
            ),
            ReportMetric(
                label="Strategy Confidence",
                value=format_confidence(
                    confidence,
                ),
                raw_value=confidence,
            ),
            ReportMetric(
                label="Composite Risk",
                value=format_score(
                    composite_risk,
                ),
                raw_value=composite_risk,
            ),
        )

        summary = (
            f"Polaris completed the morning workflow with a {market_bias} market bias, "
            f"{risk_posture} risk posture, and {execution_posture} execution posture. "
            f"Portfolio positioning is currently characterized as {portfolio_posture.lower()}."
        )

        interpretation = self._strategy_interpretation(
            strategy=strategy,
            risk=risk,
            execution_posture=execution_posture,
        )
        bullets = (
            ReportBullet(
                label="Read-through",
                text=interpretation,
            ),
            ReportBullet(
                label="Portfolio context",
                text=portfolio_snapshot.summary,
            ),
        )

        return ReportSection(
            title="Executive Summary",
            summary=summarize_long_text(
                summary,
                max_chars=700,
            ),
            metrics=metrics,
            bullets=bullets,
            risks=self._humanized_bullets(
                risk.get(
                    "risks",
                ),
                limit=3,
            ),
            recommendations=self._executive_recommendations(
                strategy=strategy,
                risk=risk,
                guard=guard,
            ),
        )

    def _build_portfolio_snapshot(
        self,
        workflow_result: BoundaryMapping,
    ) -> ReportSection:
        portfolio = self._portfolio_outputs(
            workflow_result,
        )
        features = safe_mapping(
            portfolio.get(
                "features",
            )
        )
        portfolio_state = safe_mapping(
            features.get(
                "portfolio_state",
            )
        )
        equity_state = safe_mapping(
            features.get(
                "equity_state",
            )
        )
        positions_state = safe_mapping(
            features.get(
                "positions_state",
            )
        )
        risk_features = safe_mapping(
            features.get(
                "risk_features",
            )
        )

        portfolio_value = first_score(
            portfolio_state.get(
                "portfolio_value",
            ),
            portfolio_state.get(
                "total_value",
            ),
            equity_state.get(
                "portfolio_value",
            ),
            equity_state.get(
                "equity",
            ),
        )
        cash = first_score(
            portfolio_state.get(
                "cash",
            ),
            equity_state.get(
                "cash",
            ),
        )
        cash_allocation = first_score(
            portfolio_state.get(
                "cash_ratio",
            ),
            portfolio_state.get(
                "cash_pct",
            ),
            portfolio_state.get(
                "cash_percent",
            ),
            risk_features.get(
                "cash_buffer",
            ),
            risk_features.get(
                "cash_allocation",
            ),
            self._safe_ratio(
                cash,
                portfolio_value,
            ),
        )
        realized_pnl_pct = first_score(
            portfolio_state.get(
                "realized_pnl_pct",
            ),
            equity_state.get(
                "realized_pnl_pct",
            ),
        )
        unrealized_pnl_pct = first_score(
            portfolio_state.get(
                "unrealized_pnl_pct",
            ),
            equity_state.get(
                "unrealized_pnl_pct",
            ),
        )
        unrealized_intraday_pnl = first_score(
            portfolio_state.get(
                "unrealized_intraday_pnl",
            ),
            equity_state.get(
                "unrealized_intraday_pnl",
            ),
        )
        unrealized_intraday_pnl_pct = first_score(
            portfolio_state.get(
                "unrealized_intraday_pnl_pct",
            ),
            equity_state.get(
                "unrealized_intraday_pnl_pct",
            ),
        )
        pnl_total_pct = first_score(
            portfolio_state.get(
                "pnl_total_pct",
            ),
            equity_state.get(
                "pnl_total_pct",
            ),
        )
        long_market_value = first_score(
            portfolio_state.get(
                "long_market_value",
            ),
            equity_state.get(
                "long_market_value",
            ),
        )
        short_market_value = first_score(
            portfolio_state.get(
                "short_market_value",
            ),
            equity_state.get(
                "short_market_value",
            ),
        )
        gross_market_value = first_score(
            portfolio_state.get(
                "gross_market_value",
            ),
            equity_state.get(
                "gross_market_value",
            ),
        )
        net_market_value = first_score(
            portfolio_state.get(
                "net_market_value",
            ),
            equity_state.get(
                "net_market_value",
            ),
        )
        gross_exposure = first_score(
            portfolio_state.get(
                "gross_exposure",
            ),
            risk_features.get(
                "capital_utilization",
            ),
        )
        net_exposure = first_score(
            portfolio_state.get(
                "net_exposure",
            ),
            risk_features.get(
                "net_exposure",
            ),
        )
        long_exposure = first_score(
            portfolio_state.get(
                "long_exposure",
            ),
            risk_features.get(
                "long_exposure",
            ),
        )
        short_exposure = first_score(
            portfolio_state.get(
                "short_exposure",
            ),
            risk_features.get(
                "short_exposure",
            ),
        )
        leverage = first_score(
            portfolio_state.get(
                "leverage",
            ),
            risk_features.get(
                "leverage",
            ),
        )
        margin_utilization = first_score(
            portfolio_state.get(
                "margin_utilization_ratio",
            ),
            equity_state.get(
                "margin_utilization_ratio",
            ),
            risk_features.get(
                "margin_utilization_ratio",
            ),
        )
        position_count = first_score(
            positions_state.get(
                "position_count",
            ),
            portfolio_state.get(
                "position_count",
            ),
        )
        largest_position = first_score(
            portfolio_state.get(
                "largest_position_pct",
            ),
            positions_state.get(
                "largest_position_pct",
            ),
            risk_features.get(
                "largest_position_pct",
            ),
        )
        concentration = first_score(
            portfolio_state.get(
                "concentration_score",
            ),
            risk_features.get(
                "concentration_score",
            ),
            risk_features.get(
                "concentration",
            ),
        )
        diversification = first_score(
            portfolio_state.get(
                "diversification_score",
            ),
            risk_features.get(
                "diversification_score",
            ),
        )
        portfolio_heat = first_score(
            portfolio_state.get(
                "portfolio_heat",
            ),
            risk_features.get(
                "portfolio_heat",
            ),
        )
        risk_intensity = first_score(
            portfolio_state.get(
                "risk_intensity",
            ),
            risk_features.get(
                "risk_intensity",
            ),
        )
        drawdown = first_score(
            equity_state.get(
                "drawdown_percent",
            ),
            portfolio_state.get(
                "drawdown_percent",
            ),
            risk_features.get(
                "portfolio_stress",
            ),
        )
        beta_exposure = first_score(
            portfolio_state.get(
                "beta_exposure",
            ),
            risk_features.get(
                "beta_exposure",
            ),
        )
        beta_risk = first_score(
            portfolio_state.get(
                "beta_risk",
            ),
            risk_features.get(
                "beta_risk",
            ),
        )
        account_health = format_regime(
            first_text(
                portfolio_state.get(
                    "account_health",
                ),
                equity_state.get(
                    "account_health",
                ),
                risk_features.get(
                    "account_health",
                ),
                fallback="Unknown",
            ),
            fallback="Unknown",
        )
        trading_blocked = self._first_bool(
            portfolio_state.get(
                "trading_blocked",
            ),
            equity_state.get(
                "trading_blocked",
            ),
            risk_features.get(
                "trading_blocked",
            ),
        )
        transfers_blocked = self._first_bool(
            portfolio_state.get(
                "transfers_blocked",
            ),
            equity_state.get(
                "transfers_blocked",
            ),
            risk_features.get(
                "transfers_blocked",
            ),
        )
        account_blocked = self._first_bool(
            portfolio_state.get(
                "account_blocked",
            ),
            equity_state.get(
                "account_blocked",
            ),
            risk_features.get(
                "account_blocked",
            ),
        )
        trade_suspended_by_user = self._first_bool(
            portfolio_state.get(
                "trade_suspended_by_user",
            ),
            equity_state.get(
                "trade_suspended_by_user",
            ),
            risk_features.get(
                "trade_suspended_by_user",
            ),
        )
        pattern_day_trader = self._first_bool(
            portfolio_state.get(
                "pattern_day_trader",
            ),
            equity_state.get(
                "pattern_day_trader",
            ),
        )
        account_restrictions = self._account_restriction_text(
            trading_blocked=trading_blocked,
            transfers_blocked=transfers_blocked,
            account_blocked=account_blocked,
            trade_suspended_by_user=trade_suspended_by_user,
            pattern_day_trader=pattern_day_trader,
        )
        regime = format_regime(
            first_text(
                portfolio.get(
                    "regime",
                ),
                portfolio_state.get(
                    "portfolio_regime",
                ),
                portfolio_state.get(
                    "regime",
                ),
                fallback="Unknown",
            ),
            fallback="Unknown",
        )
        directional_bias = format_regime(
            first_text(
                portfolio_state.get(
                    "directional_bias",
                ),
                risk_features.get(
                    "directional_bias",
                ),
                fallback="Unknown",
            ),
            fallback="Unknown",
        )

        metrics = (
            ReportMetric(
                label="Portfolio Value",
                value=format_currency(
                    portfolio_value,
                ),
                raw_value=portfolio_value,
            ),
            ReportMetric(
                label="Cash",
                value=format_currency(
                    cash,
                ),
                raw_value=cash,
            ),
            ReportMetric(
                label="Cash Allocation",
                value=format_percent(
                    cash_allocation,
                ),
                raw_value=cash_allocation,
            ),
            ReportMetric(
                label="Gross Exposure",
                value=format_percent(
                    gross_exposure,
                ),
                raw_value=gross_exposure,
            ),
            ReportMetric(
                label="Net Exposure",
                value=format_percent(
                    net_exposure,
                ),
                raw_value=net_exposure,
            ),
            ReportMetric(
                label="Leverage",
                value=format_score(
                    leverage,
                ),
                raw_value=leverage,
            ),
            ReportMetric(
                label="Margin Utilization",
                value=format_percent(
                    margin_utilization,
                ),
                raw_value=margin_utilization,
            ),
            ReportMetric(
                label="Portfolio Regime",
                value=regime,
            ),
            ReportMetric(
                label="Directional Bias",
                value=directional_bias,
            ),
        )
        pnl_table = ReportTable(
            title="Portfolio PnL",
            rows=(
                ReportTableRow(
                    label="Total PnL",
                    value=format_percent(
                        pnl_total_pct,
                    ),
                ),
                ReportTableRow(
                    label="Realized PnL",
                    value=format_percent(
                        realized_pnl_pct,
                    ),
                ),
                ReportTableRow(
                    label="Unrealized PnL",
                    value=format_percent(
                        unrealized_pnl_pct,
                    ),
                ),
                ReportTableRow(
                    label="Intraday Unrealized PnL",
                    value=format_currency(
                        unrealized_intraday_pnl,
                    ),
                ),
                ReportTableRow(
                    label="Intraday Unrealized PnL %",
                    value=format_percent(
                        unrealized_intraday_pnl_pct,
                    ),
                ),
            ),
        )
        exposure_table = ReportTable(
            title="Portfolio Exposure",
            rows=(
                ReportTableRow(
                    label="Gross Market Value",
                    value=format_currency(
                        gross_market_value,
                    ),
                ),
                ReportTableRow(
                    label="Net Market Value",
                    value=format_currency(
                        net_market_value,
                    ),
                ),
                ReportTableRow(
                    label="Long Market Value",
                    value=format_currency(
                        long_market_value,
                    ),
                ),
                ReportTableRow(
                    label="Short Market Value",
                    value=format_currency(
                        short_market_value,
                    ),
                ),
                ReportTableRow(
                    label="Long Exposure",
                    value=format_percent(
                        long_exposure,
                    ),
                ),
                ReportTableRow(
                    label="Short Exposure",
                    value=format_percent(
                        short_exposure,
                    ),
                ),
                ReportTableRow(
                    label="Leverage",
                    value=format_score(
                        leverage,
                    ),
                ),
            ),
        )
        risk_table = ReportTable(
            title="Portfolio Risk & Constraints",
            rows=(
                ReportTableRow(
                    label="Positions",
                    value=self._format_count(
                        position_count,
                    ),
                ),
                ReportTableRow(
                    label="Largest Position",
                    value=format_percent(
                        largest_position,
                    ),
                ),
                ReportTableRow(
                    label="Concentration",
                    value=format_score(
                        concentration,
                    ),
                ),
                ReportTableRow(
                    label="Diversification",
                    value=format_score(
                        diversification,
                    ),
                ),
                ReportTableRow(
                    label="Portfolio Heat",
                    value=format_score(
                        portfolio_heat,
                    ),
                ),
                ReportTableRow(
                    label="Risk Intensity",
                    value=format_score(
                        risk_intensity,
                    ),
                ),
                ReportTableRow(
                    label="Drawdown",
                    value=format_percent(
                        drawdown,
                    ),
                ),
                ReportTableRow(
                    label="Beta Exposure",
                    value=format_score(
                        beta_exposure,
                    ),
                ),
                ReportTableRow(
                    label="Beta Risk",
                    value=format_score(
                        beta_risk,
                    ),
                ),
                ReportTableRow(
                    label="Margin Utilization",
                    value=format_percent(
                        margin_utilization,
                    ),
                ),
                ReportTableRow(
                    label="Account Health",
                    value=account_health,
                ),
                ReportTableRow(
                    label="Account Restrictions",
                    value=account_restrictions,
                ),
            ),
        )

        summary = self._portfolio_snapshot_summary(
            portfolio_value=portfolio_value,
            cash_allocation=cash_allocation,
            gross_exposure=gross_exposure,
            net_exposure=net_exposure,
            leverage=leverage,
            margin_utilization=margin_utilization,
            account_restrictions=account_restrictions,
            regime=regime,
            directional_bias=directional_bias,
        )

        return ReportSection(
            title="Portfolio Snapshot",
            summary=summary,
            metrics=metrics,
            bullets=self._humanized_bullets(
                portfolio.get(
                    "signals",
                ),
                limit=3,
            ),
            risks=self._humanized_bullets(
                portfolio.get(
                    "risks",
                ),
                limit=3,
            ),
            recommendations=self._humanized_bullets(
                portfolio.get(
                    "recommendations",
                ),
                limit=3,
            ),
            tables=(
                pnl_table,
                exposure_table,
                risk_table,
            ),
        )

    def _build_macro_backdrop(
        self,
        workflow_result: BoundaryMapping,
    ) -> ReportSection:
        fundamental = get_node_outputs(
            workflow_result,
            "fundamental_agent",
        )
        if not fundamental:
            return ReportSection.unavailable(
                "Macro / Fundamental Backdrop",
                reason="Macro and fundamental data was not available for this run.",
            )

        features = safe_mapping(
            fundamental.get(
                "features",
            )
        )
        macro_state = safe_mapping(
            features.get(
                "macro_state",
            )
        )
        fundamental_summary = safe_mapping(
            features.get(
                "fundamental_summary",
            )
        )

        regime = format_regime(
            first_text(
                fundamental.get(
                    "regime",
                ),
                macro_state.get(
                    "macro_regime",
                ),
                fallback="Neutral",
            ),
            fallback="Neutral",
        )
        fed_stance = format_regime(
            first_text(
                macro_state.get(
                    "fed_stance",
                ),
                fallback="Unknown",
            ),
            fallback="Unknown",
        )
        liquidity = format_regime(
            first_text(
                macro_state.get(
                    "liquidity_regime",
                ),
                fundamental_summary.get(
                    "liquidity",
                ),
                fallback="Unknown",
            ),
            fallback="Unknown",
        )
        inflation = format_regime(
            first_text(
                macro_state.get(
                    "inflation_regime",
                ),
                fundamental_summary.get(
                    "inflation",
                ),
                fallback="Unknown",
            ),
            fallback="Unknown",
        )
        growth = format_regime(
            first_text(
                macro_state.get(
                    "growth_regime",
                ),
                fundamental_summary.get(
                    "growth",
                ),
                fallback="Unknown",
            ),
            fallback="Unknown",
        )
        directional_score = first_score(
            fundamental.get(
                "directional_score",
            ),
        )
        confidence = first_score(
            fundamental.get(
                "confidence",
            ),
        )

        summary = self._summary_from_node(
            fundamental,
            fallback=(
                f"The macro backdrop is {regime.lower()} with {fed_stance.lower()} Fed posture, "
                f"{liquidity.lower()} liquidity, and {inflation.lower()} inflation conditions."
            ),
        )

        return ReportSection(
            title="Macro / Fundamental Backdrop",
            summary=summary,
            metrics=(
                ReportMetric(
                    label="Macro Regime",
                    value=regime,
                ),
                ReportMetric(
                    label="Directional Score",
                    value=format_score(
                        directional_score,
                    ),
                    raw_value=directional_score,
                ),
                ReportMetric(
                    label="Confidence",
                    value=format_confidence(
                        confidence,
                    ),
                    raw_value=confidence,
                ),
                ReportMetric(
                    label="Fed Stance",
                    value=fed_stance,
                ),
            ),
            bullets=self._humanized_bullets(
                fundamental.get(
                    "signals",
                ),
                limit=4,
            ),
            risks=self._humanized_bullets(
                fundamental.get(
                    "risks",
                ),
                limit=4,
            ),
            recommendations=self._humanized_bullets(
                fundamental.get(
                    "recommendations",
                ),
                limit=4,
            ),
            tables=(
                ReportTable(
                    title="Macro Drivers",
                    rows=(
                        ReportTableRow(
                            label="Liquidity",
                            value=liquidity,
                        ),
                        ReportTableRow(
                            label="Inflation",
                            value=inflation,
                        ),
                        ReportTableRow(
                            label="Growth",
                            value=growth,
                        ),
                    ),
                ),
            ),
        )

    def _build_technical_setup(
        self,
        workflow_result: BoundaryMapping,
    ) -> ReportSection:
        technical = get_node_outputs(
            workflow_result,
            "technical_agent",
        )
        if not technical:
            return ReportSection.unavailable(
                "Technical Setup",
                reason="Technical analysis data was not available for this run.",
            )

        features = safe_mapping(
            technical.get(
                "features",
            )
        )
        regime_features = safe_mapping(
            features.get(
                "regime",
            )
        )
        technical_state = safe_mapping(
            features.get(
                "technical_state",
            )
        )
        volatility = safe_mapping(
            features.get(
                "volatility",
            )
        )
        breadth = safe_mapping(
            features.get(
                "breadth",
            )
        )
        breadth_state = safe_mapping(
            features.get(
                "breadth_state",
            )
        )
        market_context = safe_mapping(
            features.get(
                "market_context",
            )
        )
        snapshot = safe_mapping(
            features.get(
                "snapshot",
            )
        )
        calibration = safe_mapping(
            regime_features.get(
                "calibration",
            )
        )
        raw_regime = safe_mapping(
            features.get(
                "raw_regime",
            )
        )
        raw_inputs = safe_mapping(
            raw_regime.get(
                "inputs",
            )
        )

        regime = format_regime(
            first_text(
                technical.get(
                    "regime",
                ),
                regime_features.get(
                    "regime",
                ),
                fallback="Neutral",
            ),
            fallback="Neutral",
        )
        trend = format_regime(
            first_text(
                technical_state.get(
                    "trend_direction",
                ),
                fallback="Unknown",
            ),
            fallback="Unknown",
        )
        momentum = format_regime(
            first_text(
                technical_state.get(
                    "momentum_state",
                ),
                fallback="Unknown",
            ),
            fallback="Unknown",
        )
        volatility_regime = format_regime(
            first_text(
                volatility.get(
                    "volatility_regime",
                ),
                fallback="Unknown",
            ),
            fallback="Unknown",
        )
        breadth_regime = format_regime(
            first_text(
                breadth.get(
                    "breadth_regime",
                ),
                breadth_state.get(
                    "breadth_regime",
                ),
                raw_inputs.get(
                    "breadth_regime",
                ),
                fallback="Unavailable",
            ),
            fallback="Unavailable",
        )
        directional_score = first_score(
            technical.get(
                "directional_score",
            ),
            features.get(
                "technical_score",
            ),
            regime_features.get(
                "directional_technical_score",
            ),
        )
        confidence = first_score(
            technical.get(
                "confidence",
            ),
            regime_features.get(
                "confidence",
            ),
        )
        execution_readiness = first_score(
            regime_features.get(
                "execution_readiness",
            ),
        )
        signal_quality = first_score(
            regime_features.get(
                "signal_quality",
            ),
        )
        breadth_score = first_score(
            breadth.get(
                "breadth_score",
            ),
            breadth_state.get(
                "breadth_score",
            ),
            calibration.get(
                "breadth_score",
            ),
        )
        breadth_risk_score = first_score(
            breadth.get(
                "breadth_risk_score",
            ),
            breadth_state.get(
                "breadth_risk_score",
            ),
            calibration.get(
                "breadth_risk_score",
            ),
        )
        participation_score = first_score(
            breadth.get(
                "participation_score",
            ),
            breadth_state.get(
                "participation_score",
            ),
            calibration.get(
                "participation_score",
            ),
        )
        leadership_score = first_score(
            breadth.get(
                "leadership_score",
            ),
            breadth_state.get(
                "leadership_score",
            ),
            calibration.get(
                "leadership_score",
            ),
        )
        mcclellan_score = first_score(
            breadth.get(
                "mcclellan_score",
            ),
            breadth_state.get(
                "mcclellan_score",
            ),
            calibration.get(
                "mcclellan_score",
            ),
        )
        price_ad_divergence = self._first_bool(
            breadth.get(
                "price_ad_divergence",
            ),
            breadth_state.get(
                "price_ad_divergence",
            ),
            market_context.get(
                "price_ad_divergence",
            ),
            raw_inputs.get(
                "price_ad_divergence",
            ),
        )

        summary = self._summary_from_node(
            technical,
            fallback=(
                f"The technical setup is {regime.lower()} with {trend.lower()} trend, "
                f"{momentum.lower()} momentum, {volatility_regime.lower()} volatility, "
                f"and {breadth_regime.lower()} market breadth."
            ),
        )

        return ReportSection(
            title="Technical Setup",
            summary=summary,
            metrics=(
                ReportMetric(
                    label="Technical Regime",
                    value=regime,
                ),
                ReportMetric(
                    label="Directional Score",
                    value=format_score(
                        directional_score,
                    ),
                    raw_value=directional_score,
                ),
                ReportMetric(
                    label="Confidence",
                    value=format_confidence(
                        confidence,
                    ),
                    raw_value=confidence,
                ),
                ReportMetric(
                    label="Execution Readiness",
                    value=format_confidence(
                        execution_readiness,
                    ),
                    raw_value=execution_readiness,
                ),
                ReportMetric(
                    label="Signal Quality",
                    value=format_confidence(
                        signal_quality,
                    ),
                    raw_value=signal_quality,
                ),
                ReportMetric(
                    label="Breadth Regime",
                    value=breadth_regime,
                ),
                ReportMetric(
                    label="Breadth Score",
                    value=format_score(
                        breadth_score,
                    ),
                    raw_value=breadth_score,
                ),
                ReportMetric(
                    label="Breadth Risk",
                    value=format_score(
                        breadth_risk_score,
                    ),
                    raw_value=breadth_risk_score,
                ),
                ReportMetric(
                    label="Participation",
                    value=format_score(
                        participation_score,
                    ),
                    raw_value=participation_score,
                ),
                ReportMetric(
                    label="Leadership",
                    value=format_score(
                        leadership_score,
                    ),
                    raw_value=leadership_score,
                ),
                ReportMetric(
                    label="McClellan Score",
                    value=format_score(
                        mcclellan_score,
                    ),
                    raw_value=mcclellan_score,
                ),
            ),
            bullets=self._technical_bullets(
                technical=technical,
                trend=trend,
                momentum=momentum,
                volatility_regime=volatility_regime,
                breadth_regime=breadth_regime,
                breadth_score=breadth_score,
                price_ad_divergence=price_ad_divergence,
            ),
            risks=self._humanized_bullets(
                technical.get(
                    "risks",
                ),
                limit=4,
            ),
            recommendations=self._humanized_bullets(
                technical.get(
                    "recommendations",
                ),
                limit=4,
            ),
            tables=(
                ReportTable(
                    title="Technical Levels",
                    rows=(
                        ReportTableRow(
                            label="Last Close",
                            value=format_currency(
                                first_score(
                                    snapshot.get(
                                        "close",
                                    ),
                                ),
                            ),
                        ),
                        ReportTableRow(
                            label="RSI 14",
                            value=format_score(
                                first_score(
                                    snapshot.get(
                                        "rsi_14",
                                    ),
                                ),
                            ),
                        ),
                        ReportTableRow(
                            label="ATR 14",
                            value=format_score(
                                first_score(
                                    snapshot.get(
                                        "atr_14",
                                    ),
                                ),
                            ),
                        ),
                    ),
                ),
                ReportTable(
                    title="Market Breadth",
                    rows=(
                        ReportTableRow(
                            label="Advances",
                            value=self._format_count(
                                first_score(
                                    breadth.get(
                                        "advances_count",
                                    ),
                                    market_context.get(
                                        "advances_count",
                                    ),
                                ),
                            ),
                        ),
                        ReportTableRow(
                            label="Declines",
                            value=self._format_count(
                                first_score(
                                    breadth.get(
                                        "declines_count",
                                    ),
                                    market_context.get(
                                        "declines_count",
                                    ),
                                ),
                            ),
                        ),
                        ReportTableRow(
                            label="Breadth %",
                            value=format_percent(
                                first_score(
                                    breadth.get(
                                        "breadth_percent",
                                    ),
                                    breadth_state.get(
                                        "breadth_percent",
                                    ),
                                    market_context.get(
                                        "breadth_percent",
                                    ),
                                ),
                            ),
                        ),
                        ReportTableRow(
                            label="% Above 50DMA",
                            value=format_percent(
                                first_score(
                                    breadth.get(
                                        "pct_above_50dma",
                                    ),
                                    breadth_state.get(
                                        "pct_above_50dma",
                                    ),
                                    market_context.get(
                                        "pct_above_50dma",
                                    ),
                                ),
                            ),
                        ),
                        ReportTableRow(
                            label="% Above 200DMA",
                            value=format_percent(
                                first_score(
                                    breadth.get(
                                        "pct_above_200dma",
                                    ),
                                    breadth_state.get(
                                        "pct_above_200dma",
                                    ),
                                    market_context.get(
                                        "pct_above_200dma",
                                    ),
                                ),
                            ),
                        ),
                        ReportTableRow(
                            label="New Highs",
                            value=self._format_count(
                                first_score(
                                    breadth.get(
                                        "new_highs",
                                    ),
                                    market_context.get(
                                        "new_highs",
                                    ),
                                ),
                            ),
                        ),
                        ReportTableRow(
                            label="New Lows",
                            value=self._format_count(
                                first_score(
                                    breadth.get(
                                        "new_lows",
                                    ),
                                    market_context.get(
                                        "new_lows",
                                    ),
                                ),
                            ),
                        ),
                        ReportTableRow(
                            label="McClellan Oscillator",
                            value=format_score(
                                first_score(
                                    breadth.get(
                                        "mcclellan_oscillator",
                                    ),
                                    breadth_state.get(
                                        "mcclellan_oscillator",
                                    ),
                                    market_context.get(
                                        "mcclellan_oscillator",
                                    ),
                                ),
                            ),
                        ),
                        ReportTableRow(
                            label="Price / A-D Divergence",
                            value=self._format_bool(
                                price_ad_divergence,
                            ),
                        ),
                    ),
                ),
            ),
        )

    def _build_news_sentiment(
        self,
        workflow_result: BoundaryMapping,
    ) -> ReportSection:
        news = get_node_outputs(
            workflow_result,
            "news_agent",
        )
        sentiment = get_node_outputs(
            workflow_result,
            "sentiment_agent",
        )
        if not news and not sentiment:
            return ReportSection.unavailable(
                "News & Sentiment",
                reason="News and sentiment data was not available for this run.",
            )

        news_features = safe_mapping(
            news.get(
                "features",
            )
        )
        sentiment_features = safe_mapping(
            sentiment.get(
                "features",
            )
        )
        headline_count = first_score(
            news_features.get(
                "headline_count",
            ),
        )
        market_relevance = format_regime(
            first_text(
                news_features.get(
                    "market_relevance",
                ),
                news.get(
                    "regime",
                ),
                fallback="Neutral",
            ),
            fallback="Neutral",
        )
        sentiment_regime = format_regime(
            first_text(
                sentiment.get(
                    "regime",
                ),
                sentiment_features.get(
                    "sentiment_bias",
                ),
                fallback="Neutral",
            ),
            fallback="Neutral",
        )
        sentiment_score = first_score(
            sentiment.get(
                "directional_score",
            ),
        )
        composite_sentiment = first_score(
            sentiment_features.get(
                "composite_sentiment",
            ),
        )
        sentiment_confidence = first_score(
            sentiment.get(
                "confidence",
            ),
        )
        fear_greed = format_regime(
            first_text(
                sentiment_features.get(
                    "fear_greed_state",
                ),
                fallback="Neutral",
            ),
            fallback="Neutral",
        )
        positioning = format_regime(
            first_text(
                sentiment_features.get(
                    "positioning_state",
                ),
                fallback="Balanced",
            ),
            fallback="Balanced",
        )

        news_summary = self._summary_from_node(
            news,
            fallback=(
                f"News relevance is {market_relevance.lower()} across "
                f"{self._format_count(headline_count)} reviewed headlines."
            ),
        )
        sentiment_summary = self._summary_from_node(
            sentiment,
            fallback=(
                f"Sentiment is {sentiment_regime.lower()} with {fear_greed.lower()} "
                f"fear/greed conditions and {positioning.lower()} positioning."
            ),
        )
        summary = f"{news_summary} {sentiment_summary}".strip()

        return ReportSection(
            title="News & Sentiment",
            summary=summary,
            metrics=(
                ReportMetric(
                    label="News Relevance",
                    value=market_relevance,
                ),
                ReportMetric(
                    label="Headlines Reviewed",
                    value=self._format_count(
                        headline_count,
                    ),
                    raw_value=headline_count,
                ),
                ReportMetric(
                    label="Sentiment Regime",
                    value=sentiment_regime,
                ),
                ReportMetric(
                    label="Sentiment Score",
                    value=format_score(
                        sentiment_score,
                    ),
                    raw_value=sentiment_score,
                ),
                ReportMetric(
                    label="Composite Sentiment",
                    value=format_score(
                        composite_sentiment,
                    ),
                    raw_value=composite_sentiment,
                ),
                ReportMetric(
                    label="Sentiment Confidence",
                    value=format_confidence(
                        sentiment_confidence,
                    ),
                    raw_value=sentiment_confidence,
                ),
            ),
            bullets=self._news_sentiment_bullets(
                news=news,
                sentiment=sentiment,
            ),
            risks=self._combined_humanized_bullets(
                news.get(
                    "risks",
                ),
                sentiment.get(
                    "risks",
                ),
                limit=5,
            ),
            recommendations=self._combined_humanized_bullets(
                news.get(
                    "recommendations",
                ),
                sentiment.get(
                    "recommendations",
                ),
                limit=5,
            ),
            tables=(
                ReportTable(
                    title="Sentiment Context",
                    rows=(
                        ReportTableRow(
                            label="Fear / Greed",
                            value=fear_greed,
                        ),
                        ReportTableRow(
                            label="Positioning",
                            value=positioning,
                        ),
                    ),
                ),
            ),
        )

    def _build_risk_assessment(
        self,
        workflow_result: BoundaryMapping,
    ) -> ReportSection:
        risk = self._risk_outputs(
            workflow_result,
        )
        risk_builder = get_node_outputs(
            workflow_result,
            "risk_signal_builder",
        )
        guard = self._execution_guard_outputs(
            workflow_result,
        )
        if not risk and not risk_builder and not guard:
            return ReportSection.unavailable(
                "Risk Assessment",
                reason="Risk assessment data was not available for this run.",
            )

        features = safe_mapping(
            risk.get(
                "features",
            )
        )
        builder_features = safe_mapping(
            risk_builder.get(
                "features",
            )
        )
        primitive_sources = safe_mapping(
            builder_features.get(
                "primitive_sources",
            )
        )
        guard_features = safe_mapping(
            guard.get(
                "features",
            )
        )
        execution_guard = safe_mapping(
            guard_features.get(
                "execution_guard",
            )
        )

        composite_risk = first_score(
            features.get(
                "adjusted_composite_risk",
            ),
            features.get(
                "composite_risk",
            ),
            risk_builder.get(
                "composite_risk",
            ),
        )
        risk_pressure = first_score(
            features.get(
                "adjusted_risk_pressure",
            ),
            features.get(
                "risk_pressure",
            ),
            risk_builder.get(
                "risk_pressure",
            ),
        )
        stability_score = first_score(
            features.get(
                "stability_score",
            ),
            risk_builder.get(
                "stability_score",
            ),
        )
        volatility_risk = first_score(
            features.get(
                "volatility_risk",
            ),
            primitive_sources.get(
                "volatility",
            ),
        )
        drawdown_risk = first_score(
            features.get(
                "drawdown_risk",
            ),
            primitive_sources.get(
                "drawdown",
            ),
        )
        exposure_risk = first_score(
            features.get(
                "exposure_risk",
            ),
            primitive_sources.get(
                "exposure",
            ),
        )
        risk_regime = format_regime(
            first_text(
                features.get(
                    "risk_regime",
                ),
                risk.get(
                    "regime",
                ),
                fallback="Neutral",
            ),
            fallback="Neutral",
        )
        risk_bias = format_regime(
            first_text(
                features.get(
                    "risk_bias",
                ),
                fallback="Neutral",
            ),
            fallback="Neutral",
        )
        guard_mode = format_regime(
            first_text(
                execution_guard.get(
                    "mode",
                ),
                fallback="Not Evaluated",
            ),
            fallback="Not Evaluated",
        )

        summary = (
            f"Portfolio risk is classified as {risk_regime.lower()} with "
            f"composite risk at {format_score(composite_risk)}, risk pressure at "
            f"{format_score(risk_pressure)}, and stability at {format_score(stability_score)}. "
            f"The execution guard is {guard_mode.lower()}."
        )

        flags = self._humanized_bullets(
            execution_guard.get(
                "flags",
            ),
            limit=5,
        )

        return ReportSection(
            title="Risk Assessment",
            summary=summary,
            metrics=(
                ReportMetric(
                    label="Risk Regime",
                    value=risk_regime,
                ),
                ReportMetric(
                    label="Risk Bias",
                    value=risk_bias,
                ),
                ReportMetric(
                    label="Composite Risk",
                    value=format_score(
                        composite_risk,
                    ),
                    raw_value=composite_risk,
                ),
                ReportMetric(
                    label="Risk Pressure",
                    value=format_score(
                        risk_pressure,
                    ),
                    raw_value=risk_pressure,
                ),
                ReportMetric(
                    label="Stability Score",
                    value=format_score(
                        stability_score,
                    ),
                    raw_value=stability_score,
                ),
                ReportMetric(
                    label="Execution Guard",
                    value=guard_mode,
                ),
            ),
            bullets=(
                ReportBullet(
                    label="Risk posture",
                    text=(
                        f"Volatility risk is {format_score(volatility_risk)}, "
                        f"drawdown risk is {format_score(drawdown_risk)}, and "
                        f"exposure risk is {format_score(exposure_risk)}."
                    ),
                ),
            ),
            risks=self._combined_humanized_bullets(
                risk.get(
                    "risks",
                ),
                guard.get(
                    "risks",
                ),
                limit=5,
            )
            or flags,
            recommendations=self._decision_support_bullets(
                self._combined_humanized_bullets(
                    risk.get(
                        "recommendations",
                    ),
                    guard.get(
                        "recommendations",
                    ),
                    limit=5,
                ),
                limit=5,
            ),
            tables=(
                ReportTable(
                    title="Primitive Risk Components",
                    rows=(
                        ReportTableRow(
                            label="Volatility",
                            value=format_score(
                                volatility_risk,
                            ),
                        ),
                        ReportTableRow(
                            label="Drawdown",
                            value=format_score(
                                drawdown_risk,
                            ),
                        ),
                        ReportTableRow(
                            label="Exposure",
                            value=format_score(
                                exposure_risk,
                            ),
                        ),
                    ),
                ),
            ),
        )

    def _build_recommended_action_plan(
        self,
        workflow_result: BoundaryMapping,
    ) -> ReportSection:
        strategy = get_node_outputs(
            workflow_result,
            "strategy_synthesis_agent",
        )
        portfolio_manager = get_node_outputs(
            workflow_result,
            "portfolio_manager_agent",
        )
        trade = get_node_outputs(
            workflow_result,
            "trade_packager",
        )
        guard = self._execution_guard_outputs(
            workflow_result,
        )
        risk = self._risk_outputs(
            workflow_result,
        )
        if not strategy and not portfolio_manager and not trade and not guard:
            return ReportSection.unavailable(
                "Recommended Action Plan",
                reason="Action-plan data was not available for this run.",
            )

        strategy_features = safe_mapping(
            strategy.get(
                "features",
            )
        )
        portfolio_features = safe_mapping(
            portfolio_manager.get(
                "features",
            )
        )
        trade_features = safe_mapping(
            trade.get(
                "features",
            )
        )
        trade_intent = safe_mapping(
            trade_features.get(
                "trade_intent",
            )
        )
        guard_features = safe_mapping(
            guard.get(
                "features",
            )
        )
        execution_guard = safe_mapping(
            guard_features.get(
                "execution_guard",
            )
        )

        strategy_posture = format_regime(
            first_text(
                strategy_features.get(
                    "posture",
                ),
                strategy.get(
                    "regime",
                ),
                fallback="Neutral",
            ),
            fallback="Neutral",
        )
        portfolio_status = format_regime(
            first_text(
                portfolio_features.get(
                    "execution_status",
                ),
                portfolio_manager.get(
                    "regime",
                ),
                fallback="Not Evaluated",
            ),
            fallback="Not Evaluated",
        )
        direction = format_regime(
            first_text(
                trade_intent.get(
                    "direction",
                ),
                trade.get(
                    "regime",
                ),
                fallback="Flat",
            ),
            fallback="Flat",
        )
        guard_mode = format_regime(
            first_text(
                execution_guard.get(
                    "mode",
                ),
                fallback="Not Evaluated",
            ),
            fallback="Not Evaluated",
        )
        scale_factor = first_score(
            portfolio_features.get(
                "scale_factor",
            ),
            strategy_features.get(
                "portfolio_scale_factor",
            ),
        )
        position_size = first_score(
            execution_guard.get(
                "adjusted_position_size",
            ),
            trade_intent.get(
                "position_sizing_hint",
            ),
            trade_features.get(
                "position_sizing_hint",
            ),
        )
        trade_quality = first_score(
            trade_intent.get(
                "trade_quality_score",
            ),
            trade_features.get(
                "trade_quality_score",
            ),
        )
        execution_readiness = first_score(
            strategy_features.get(
                "execution_readiness",
            ),
        )
        strategy_decision = safe_mapping(
            strategy_features.get(
                "strategy_synthesis_decision",
            )
        )
        selected_hypothesis = safe_mapping(
            strategy_features.get(
                "selected_hypothesis",
            )
        )
        selected_strategy = format_regime(
            first_text(
                strategy_decision.get(
                    "selected_perspective",
                ),
                strategy_features.get(
                    "selected_perspective",
                ),
                selected_hypothesis.get(
                    "perspective",
                ),
                fallback="Unresolved",
            ),
            fallback="Unresolved",
        )
        selection_status = format_regime(
            first_text(
                strategy_decision.get(
                    "selection_status",
                ),
                strategy_features.get(
                    "selection_status",
                ),
                fallback="Not Evaluated",
            ),
            fallback="Not Evaluated",
        )
        synthesis_confidence = first_score(
            strategy_decision.get(
                "confidence",
            ),
            strategy.get(
                "confidence",
            ),
        )

        summary = (
            "This action plan is decision support only. It does not authorize or execute trades. "
            f"Current synthesis posture is {strategy_posture.lower()}, portfolio status is "
            f"{portfolio_status.lower()}, trade-package direction is {direction.lower()}, and "
            f"execution guard mode is {guard_mode.lower()}."
        )

        recommendations = self._decision_support_bullets(
            self._combined_humanized_bullets(
                strategy.get(
                    "recommendations",
                ),
                portfolio_manager.get(
                    "recommendations",
                ),
                limit=4,
            )
            + self._combined_humanized_bullets(
                trade.get(
                    "recommendations",
                ),
                guard.get(
                    "recommendations",
                ),
                limit=4,
            ),
            limit=6,
        )
        if not recommendations:
            recommendations = (
                ReportBullet(
                    text="Maintain current review posture until stronger signal alignment is available.",
                ),
                ReportBullet(
                    text="Confirm any portfolio changes with human review, policy, and governance checks.",
                ),
            )

        strategy_case_rows = self._strategy_case_comparison_rows(
            strategy_features=strategy_features,
            strategy_decision=strategy_decision,
        )
        tables: list[ReportTable] = []
        if strategy_case_rows:
            tables.append(
                ReportTable(
                    title="Strategy Case Comparison",
                    rows=strategy_case_rows,
                )
            )
        tables.append(
            ReportTable(
                title="Action Inputs",
                rows=(
                    ReportTableRow(
                        label="Entry Bias",
                        value=format_score(
                            first_score(
                                trade.get(
                                    "directional_score",
                                ),
                                trade_intent.get(
                                    "entry_bias",
                                ),
                            ),
                        ),
                    ),
                    ReportTableRow(
                        label="Stop Distance",
                        value=format_score(
                            first_score(
                                trade_intent.get(
                                    "stop_distance",
                                ),
                                trade_features.get(
                                    "stop_distance",
                                ),
                            ),
                        ),
                    ),
                    ReportTableRow(
                        label="Take-Profit Distance",
                        value=format_score(
                            first_score(
                                trade_intent.get(
                                    "take_profit_distance",
                                ),
                                trade_features.get(
                                    "take_profit_distance",
                                ),
                            ),
                        ),
                    ),
                ),
            )
        )

        return ReportSection(
            title="Recommended Action Plan",
            summary=summary,
            metrics=(
                ReportMetric(
                    label="Strategy Posture",
                    value=strategy_posture,
                ),
                ReportMetric(
                    label="Selected Strategy",
                    value=selected_strategy,
                ),
                ReportMetric(
                    label="Synthesis Status",
                    value=selection_status,
                ),
                ReportMetric(
                    label="Synthesis Confidence",
                    value=format_confidence(
                        synthesis_confidence,
                    ),
                    raw_value=synthesis_confidence,
                ),
                ReportMetric(
                    label="Portfolio Status",
                    value=portfolio_status,
                ),
                ReportMetric(
                    label="Trade-Package Direction",
                    value=direction,
                ),
                ReportMetric(
                    label="Execution Guard",
                    value=guard_mode,
                ),
                ReportMetric(
                    label="Capital Scale Factor",
                    value=format_confidence(
                        scale_factor,
                    ),
                    raw_value=scale_factor,
                ),
                ReportMetric(
                    label="Position Size Hint",
                    value=format_confidence(
                        position_size,
                    ),
                    raw_value=position_size,
                ),
                ReportMetric(
                    label="Trade Quality",
                    value=format_confidence(
                        trade_quality,
                    ),
                    raw_value=trade_quality,
                ),
                ReportMetric(
                    label="Execution Readiness",
                    value=format_confidence(
                        execution_readiness,
                    ),
                    raw_value=execution_readiness,
                ),
            ),
            bullets=(
                ReportBullet(
                    label="Primary decision frame",
                    text=(
                        f"Evaluate {strategy_posture.lower()} positioning with a "
                        f"{portfolio_status.lower()} portfolio gate before changing exposure."
                    ),
                ),
                ReportBullet(
                    label="Capital discipline",
                    text=(
                        f"Use the {format_confidence(scale_factor)} capital scale factor and "
                        f"{format_confidence(position_size)} position-size hint as review inputs, "
                        "not execution instructions."
                    ),
                ),
                ReportBullet(
                    label="Governance",
                    text="Human approval remains required before any trading or allocation action.",
                ),
                *self._strategy_rationale_bullets(
                    strategy=strategy,
                    strategy_features=strategy_features,
                    strategy_decision=strategy_decision,
                    selected_hypothesis=selected_hypothesis,
                    selected_strategy=selected_strategy,
                    selection_status=selection_status,
                    synthesis_confidence=synthesis_confidence,
                    execution_readiness=execution_readiness,
                ),
            ),
            risks=self._combined_humanized_bullets(
                trade.get(
                    "risks",
                ),
                risk.get(
                    "risks",
                ),
                limit=5,
            ),
            recommendations=recommendations,
            tables=tuple(
                tables,
            ),
        )

    def _strategy_case_comparison_rows(
        self,
        *,
        strategy_features: dict[str, Any],
        strategy_decision: dict[str, Any],
    ) -> tuple[ReportTableRow, ...]:
        evaluations = self._mapping_sequence(
            strategy_decision.get(
                "evaluations",
            )
        ) or self._mapping_sequence(
            strategy_features.get(
                "strategy_hypothesis_evaluations",
            )
        )
        if not evaluations:
            return ()

        posterior_weights = safe_mapping(
            strategy_features.get(
                "hypothesis_posterior_weights",
            )
        )
        candidate_scores = safe_mapping(
            strategy_features.get(
                "hypothesis_candidate_scores",
            )
        )
        evaluations_by_perspective = {
            first_text(
                evaluation.get(
                    "perspective",
                )
            ).lower(): evaluation
            for evaluation in evaluations
        }

        rows: list[ReportTableRow] = []
        for perspective in (
            "bull",
            "bear",
            "sideways",
        ):
            evaluation = evaluations_by_perspective.get(
                perspective,
                {},
            )
            posterior_weight = first_score(
                evaluation.get(
                    "posterior_weight",
                ),
                posterior_weights.get(
                    perspective,
                ),
            )
            candidate_score = first_score(
                evaluation.get(
                    "candidate_score",
                ),
                candidate_scores.get(
                    perspective,
                ),
            )
            status = format_regime(
                first_text(
                    evaluation.get(
                        "selection_status",
                    ),
                    fallback="not_available",
                ),
                fallback="Not Available",
            )
            rank = first_score(
                evaluation.get(
                    "rank",
                )
            )
            rank_text = (
                "N/A"
                if rank is None
                else str(
                    int(
                        rank,
                    )
                )
            )
            rows.append(
                ReportTableRow(
                    label=f"{format_regime(perspective)} Case",
                    value=(
                        f"Posterior {format_confidence(posterior_weight)} | "
                        f"Candidate {format_score(candidate_score)} | "
                        f"Rank {rank_text} | Status {status}"
                    ),
                )
            )

        return tuple(
            rows,
        )

    def _strategy_rationale_bullets(
        self,
        *,
        strategy: dict[str, Any],
        strategy_features: dict[str, Any],
        strategy_decision: dict[str, Any],
        selected_hypothesis: dict[str, Any],
        selected_strategy: str,
        selection_status: str,
        synthesis_confidence: float | None,
        execution_readiness: float | None,
    ) -> tuple[ReportBullet, ...]:
        thesis = first_text(
            selected_hypothesis.get(
                "thesis",
            ),
            strategy_decision.get(
                "thesis",
            ),
            strategy_features.get(
                "thesis",
            ),
            fallback="No selected thesis was available from the strategy synthesis output.",
        )
        narrative = first_text(
            strategy.get(
                "llm_response",
            ),
            strategy_features.get(
                "llm_response",
            ),
            strategy_features.get(
                "narrative",
            ),
        )
        degraded_reasons = safe_list(
            strategy_decision.get(
                "degraded_reasons",
            )
        ) or safe_list(
            strategy_features.get(
                "degraded_reasons",
            )
        )
        unresolved_conflicts = (
            self._strategy_items_text(
                degraded_reasons,
                fallback="No unresolved synthesis conflicts were reported.",
            )
            if degraded_reasons
            else "No unresolved synthesis conflicts were reported."
        )

        risks_text = self._strategy_items_text(
            selected_hypothesis.get(
                "risks",
            ),
            strategy_decision.get(
                "risks",
            ),
            strategy.get(
                "risks",
            ),
            fallback="No strategy-specific risks were provided.",
        )

        bullets = [
            ReportBullet(
                label="Selected thesis",
                text=thesis,
            ),
            ReportBullet(
                label="Posture and confidence",
                text=(
                    f"Selected strategy is {selected_strategy.lower()} with "
                    f"{selection_status.lower()} synthesis status, "
                    f"{format_confidence(synthesis_confidence)} synthesis confidence, "
                    f"and {format_confidence(execution_readiness)} execution readiness."
                ),
            ),
            ReportBullet(
                label="Decisive supporting evidence",
                text=self._strategy_items_text(
                    selected_hypothesis.get(
                        "supporting_evidence",
                    ),
                    fallback="No decisive supporting evidence was provided.",
                ),
            ),
            ReportBullet(
                label="Material contradictory evidence",
                text=self._strategy_items_text(
                    selected_hypothesis.get(
                        "contradicting_evidence",
                    ),
                    fallback="No material contradictory evidence was provided.",
                ),
            ),
            ReportBullet(
                label="Key assumptions",
                text=self._strategy_items_text(
                    selected_hypothesis.get(
                        "key_assumptions",
                    ),
                    fallback="No explicit key assumptions were provided.",
                ),
            ),
            ReportBullet(
                label="Invalidation conditions",
                text=self._strategy_items_text(
                    selected_hypothesis.get(
                        "invalidation_conditions",
                    ),
                    fallback="No explicit invalidation conditions were provided.",
                ),
            ),
            ReportBullet(
                label="Unresolved conflicts",
                text=unresolved_conflicts,
            ),
            ReportBullet(
                label="Risks and execution readiness",
                text=(
                    f"Execution readiness is {format_confidence(execution_readiness)}. "
                    f"Material risks: {risks_text}"
                ),
            ),
        ]
        if narrative:
            bullets.append(
                ReportBullet(
                    label="Complete strategy narrative",
                    text=narrative,
                )
            )

        return tuple(
            bullets,
        )

    def _strategy_items_text(
        self,
        *values: Any,
        fallback: str,
    ) -> str:
        items: list[str] = []
        for value in values:
            items.extend(
                self._strategy_item_text(
                    item,
                )
                for item in self._strategy_item_values(
                    value,
                )
            )

        cleaned = tuple(dict.fromkeys(item for item in items if item))
        if not cleaned:
            return fallback

        return "; ".join(
            cleaned,
        )

    def _strategy_item_values(
        self,
        value: Any,
    ) -> tuple[Any, ...]:
        if value is None:
            return ()
        if isinstance(
            value,
            (list, tuple),
        ):
            return tuple(
                value,
            )
        return (value,)

    def _strategy_item_text(
        self,
        value: Any,
    ) -> str:
        mapping = safe_mapping(
            value,
        )
        if mapping:
            description = first_text(
                mapping.get(
                    "description",
                ),
                mapping.get(
                    "explanation",
                ),
                mapping.get(
                    "name",
                ),
                mapping.get(
                    "source",
                ),
            )
            score = first_score(
                mapping.get(
                    "strength",
                ),
                mapping.get(
                    "confidence",
                ),
                mapping.get(
                    "reliability",
                ),
            )
            qualifier = f" ({format_confidence(score)})" if score is not None else ""
            if {
                "observed_value",
                "operator",
                "threshold",
            }.issubset(mapping):
                invalidated = self._format_bool(
                    self._first_bool(
                        mapping.get(
                            "invalidated",
                        )
                    )
                )
                return (
                    f"{description or 'Condition'}: observed "
                    f"{mapping.get('observed_value')} {mapping.get('operator')} "
                    f"{mapping.get('threshold')} | invalidated {invalidated}"
                )
            if description:
                return f"{description}{qualifier}"
            return str(
                mapping,
            )

        text = str(
            value,
        ).strip()
        return self._humanize_token(
            text,
        )

    def _mapping_sequence(
        self,
        value: Any,
    ) -> tuple[dict[str, Any], ...]:
        if not isinstance(
            value,
            (list, tuple),
        ):
            return ()
        return tuple(
            mapping for mapping in (safe_mapping(item) for item in value) if mapping
        )

    def _run_errors(
        self,
        workflow_result: BoundaryMapping,
    ) -> tuple[str, ...]:
        errors: list[str] = []
        self._append_error_text(
            errors,
            workflow_result.get(
                "error_message",
            ),
        )

        raw_result = safe_mapping(
            workflow_result.get(
                "raw_result",
            )
        )
        raw_exception = safe_mapping(
            raw_result.get(
                "exception",
            )
        )
        self._append_error_text(
            errors,
            raw_exception.get(
                "message",
            ),
        )

        for item in safe_list(
            workflow_result.get(
                "errors",
            )
        ):
            self._append_error_text(
                errors,
                item,
            )

        return tuple(
            dict.fromkeys(
                errors,
            )
        )

    def _append_error_text(
        self,
        errors: list[str],
        value: Any,
    ) -> None:
        if value is None:
            return

        mapping = safe_mapping(
            value,
        )
        if mapping:
            text = first_text(
                mapping.get(
                    "message",
                ),
                mapping.get(
                    "error",
                ),
                mapping.get(
                    "reason",
                ),
                mapping.get(
                    "detail",
                ),
            )
            node_name = first_text(
                mapping.get(
                    "node_name",
                ),
                mapping.get(
                    "node",
                ),
            )
            error_type = first_text(
                mapping.get(
                    "error_type",
                ),
                mapping.get(
                    "type",
                ),
            )
            if text and node_name:
                text = f"{node_name}: {text}"
            if text and error_type:
                text = f"{text} ({error_type})"
            if text:
                errors.append(
                    text,
                )
            return

        text = first_text(
            value,
        )
        if text:
            errors.append(
                text,
            )

    def _portfolio_outputs(
        self,
        workflow_result: BoundaryMapping,
    ) -> dict[str, Any]:
        return get_node_outputs(
            workflow_result,
            "portfolio_state_builder",
        )

    def _risk_outputs(
        self,
        workflow_result: BoundaryMapping,
    ) -> dict[str, Any]:
        return get_node_outputs(
            workflow_result,
            "risk_aggregator_agent",
        )

    def _execution_guard_outputs(
        self,
        workflow_result: BoundaryMapping,
    ) -> dict[str, Any]:
        execution_guard = get_node_outputs(
            workflow_result,
            "execution_risk_guard",
        )
        if execution_guard:
            return execution_guard

        return get_node_outputs(
            workflow_result,
            "risk_guard",
        )

    def _report_generated_at(
        self,
        workflow_result: BoundaryMapping,
    ) -> str:
        summary = safe_mapping(
            workflow_result.get(
                "summary",
            )
        )
        raw_result = safe_mapping(
            workflow_result.get(
                "raw_result",
            )
        )
        raw_execution_result = safe_mapping(
            raw_result.get(
                "execution_result",
            )
        )
        execution_result = safe_mapping(
            workflow_result.get(
                "execution_result",
            )
        )

        return first_text(
            summary.get(
                "completed_at",
            ),
            summary.get(
                "started_at",
            ),
            execution_result.get(
                "completed_at",
            ),
            raw_execution_result.get(
                "completed_at",
            ),
            raw_execution_result.get(
                "started_at",
            ),
            fallback="Unknown",
        )

    def _portfolio_posture(
        self,
        portfolio: BoundaryMapping,
    ) -> str:
        cash_allocation = first_score(
            get_path(
                portfolio,
                "features",
                "portfolio_state",
                "cash_pct",
            ),
            get_path(
                portfolio,
                "features",
                "risk_features",
                "cash_buffer",
            ),
        )
        risk_intensity = first_score(
            get_path(
                portfolio,
                "features",
                "portfolio_state",
                "risk_intensity",
            ),
            get_path(
                portfolio,
                "features",
                "risk_features",
                "risk_intensity",
            ),
        )

        if cash_allocation is not None and cash_allocation >= 0.5:
            return "Defensive / High Cash"
        if risk_intensity is not None and risk_intensity >= 0.7:
            return "Elevated Risk"
        if cash_allocation is not None and cash_allocation <= 0.1:
            return "Invested / Low Cash"

        return "Balanced"

    def _portfolio_snapshot_summary(
        self,
        *,
        portfolio_value: float | None,
        cash_allocation: float | None,
        gross_exposure: float | None,
        net_exposure: float | None,
        leverage: float | None,
        margin_utilization: float | None,
        account_restrictions: str,
        regime: str,
        directional_bias: str,
    ) -> str:
        value_text = format_currency(
            portfolio_value,
        )
        cash_text = format_percent(
            cash_allocation,
        )
        gross_text = format_percent(
            gross_exposure,
        )
        net_text = format_percent(
            net_exposure,
        )
        leverage_text = format_score(
            leverage,
        )
        margin_text = format_percent(
            margin_utilization,
        )

        return (
            f"The portfolio is reported at {value_text} with {cash_text} cash, "
            f"{gross_text} gross exposure, {net_text} net exposure, "
            f"{leverage_text} leverage, and {margin_text} margin utilization. "
            f"The portfolio regime is {regime} with a {directional_bias.lower()} "
            f"directional bias. Account restrictions: {account_restrictions}."
        )

    def _strategy_interpretation(
        self,
        *,
        strategy: BoundaryMapping,
        risk: BoundaryMapping,
        execution_posture: str,
    ) -> str:
        recommendations = safe_list(
            strategy.get(
                "recommendations",
            )
        )
        risk_recommendations = safe_list(
            risk.get(
                "recommendations",
            )
        )
        if recommendations:
            primary = self._humanize_token(
                recommendations[0],
            )
            return (
                f"Primary synthesis guidance is to {primary.lower()}. "
                f"Execution posture is {execution_posture.lower()}, so changes should remain "
                "risk-aware and subject to human review."
            )
        if risk_recommendations:
            primary_risk = self._humanize_token(
                risk_recommendations[0],
            )
            return (
                f"Risk guidance emphasizes {primary_risk.lower()}. "
                "Positioning changes should be evaluated against current constraints."
            )

        return (
            "No high-conviction strategy directive was produced. Maintain a review posture "
            "until market, portfolio, and risk signals are more clearly aligned."
        )

    def _executive_recommendations(
        self,
        *,
        strategy: BoundaryMapping,
        risk: BoundaryMapping,
        guard: BoundaryMapping,
    ) -> tuple[ReportBullet, ...]:
        recommendations: list[ReportBullet] = []

        for source in (
            strategy,
            risk,
            guard,
        ):
            for item in safe_list(
                source.get(
                    "recommendations",
                )
            ):
                text = self._humanize_token(
                    item,
                )
                if not text:
                    continue
                recommendations.append(
                    ReportBullet(
                        text=text,
                    )
                )
                if (
                    len(
                        recommendations,
                    )
                    >= 3
                ):
                    return tuple(
                        recommendations,
                    )

        return (
            ReportBullet(
                text="Review the portfolio posture before changing risk exposure.",
            ),
            ReportBullet(
                text="Treat this report as decision support; human approval remains required for action.",
            ),
        )

    def _summary_from_node(
        self,
        node_output: BoundaryMapping,
        *,
        fallback: str,
    ) -> str:
        features = safe_mapping(
            node_output.get(
                "features",
            )
        )
        llm_response = node_output.get(
            "llm_response",
        )
        llm_mapping = safe_mapping(
            llm_response,
        )

        summary = first_text(
            features.get(
                "summary",
            ),
            features.get(
                "outlook",
            ),
            llm_mapping.get(
                "summary",
            ),
            llm_mapping.get(
                "outlook",
            ),
            llm_response if isinstance(llm_response, str) else None,
            fallback=fallback,
        )

        return summary

    def _technical_bullets(
        self,
        *,
        technical: BoundaryMapping,
        trend: str,
        momentum: str,
        volatility_regime: str,
        breadth_regime: str,
        breadth_score: float | None,
        price_ad_divergence: bool | None,
    ) -> tuple[ReportBullet, ...]:
        bullets: list[ReportBullet] = [
            ReportBullet(
                label="Structure",
                text=(
                    f"Trend is {trend.lower()}, momentum is {momentum.lower()}, "
                    f"and volatility is {volatility_regime.lower()}."
                ),
            )
        ]

        bullets.append(
            ReportBullet(
                label="Breadth",
                text=(
                    f"Market breadth is {breadth_regime.lower()} with a "
                    f"breadth score of {format_score(breadth_score)} and "
                    f"price / A-D divergence marked {self._format_bool(price_ad_divergence).lower()}."
                ),
            )
        )
        features = safe_mapping(
            technical.get(
                "features",
            )
        )
        for item in safe_list(
            features.get(
                "key_points",
            )
        )[:3]:
            text = self._humanize_token(
                item,
            )
            if text:
                bullets.append(
                    ReportBullet(
                        text=text,
                    )
                )

        if (
            len(
                bullets,
            )
            == 2
        ):
            bullets.extend(
                self._humanized_bullets(
                    technical.get(
                        "signals",
                    ),
                    limit=3,
                )
            )

        return tuple(
            bullets[:4],
        )

    def _news_sentiment_bullets(
        self,
        *,
        news: BoundaryMapping,
        sentiment: BoundaryMapping,
    ) -> tuple[ReportBullet, ...]:
        bullets: list[ReportBullet] = []
        news_features = safe_mapping(
            news.get(
                "features",
            )
        )
        sentiment_features = safe_mapping(
            sentiment.get(
                "features",
            )
        )

        themes = safe_list(
            news_features.get(
                "primary_themes",
            )
        )
        if themes:
            bullets.append(
                ReportBullet(
                    label="Themes",
                    text=", ".join(
                        self._humanize_token(
                            theme,
                        )
                        for theme in themes[:4]
                    ),
                )
            )

        for article in self._article_bullets(
            news_features.get(
                "articles",
            ),
            limit=3,
        ):
            bullets.append(
                article,
            )

        if sentiment_features:
            stability = format_score(
                first_score(
                    sentiment_features.get(
                        "stability",
                    ),
                )
            )
            momentum = format_score(
                first_score(
                    sentiment_features.get(
                        "momentum",
                    ),
                )
            )
            bullets.append(
                ReportBullet(
                    label="Sentiment quality",
                    text=f"Stability is {stability}; momentum is {momentum}.",
                )
            )

        if not bullets:
            bullets.extend(
                self._combined_humanized_bullets(
                    news.get(
                        "signals",
                    ),
                    sentiment.get(
                        "signals",
                    ),
                    limit=4,
                )
            )

        return tuple(
            bullets[:5],
        )

    def _article_bullets(
        self,
        value: Any,
        *,
        limit: int,
    ) -> tuple[ReportBullet, ...]:
        articles = []
        if isinstance(
            value,
            list,
        ):
            articles = value
        elif isinstance(
            value,
            tuple,
        ):
            articles = list(
                value,
            )

        bullets: list[ReportBullet] = []
        for article in articles[:limit]:
            article_mapping = safe_mapping(
                article,
            )
            title = first_text(
                article_mapping.get(
                    "title",
                ),
                article_mapping.get(
                    "headline",
                ),
                fallback="Untitled market update",
            )
            source_mapping = safe_mapping(
                article_mapping.get(
                    "source",
                )
            )
            source = first_text(
                source_mapping.get(
                    "name",
                ),
                source_mapping.get(
                    "title",
                ),
                article_mapping.get(
                    "source_name",
                ),
                article_mapping.get(
                    "publisher",
                ),
                article_mapping.get(
                    "source",
                )
                if not source_mapping
                else None,
                fallback="Unknown source",
            )
            description = summarize_long_text(
                first_text(
                    article_mapping.get(
                        "description",
                    ),
                    article_mapping.get(
                        "summary",
                    ),
                    fallback="",
                ),
                max_chars=180,
            )
            text = f"{title} ({source})"
            if description:
                text = f"{text}: {description}"
            bullets.append(
                ReportBullet(
                    label="Headline",
                    text=text,
                )
            )

        return tuple(
            bullets,
        )

    def _combined_humanized_bullets(
        self,
        first_value: Any,
        second_value: Any,
        *,
        limit: int,
    ) -> tuple[ReportBullet, ...]:
        bullets: list[ReportBullet] = []
        seen: set[str] = set()
        for value in (
            first_value,
            second_value,
        ):
            for item in safe_list(
                value,
            ):
                text = self._humanize_token(
                    item,
                )
                if not text or text in seen:
                    continue
                seen.add(
                    text,
                )
                bullets.append(
                    ReportBullet(
                        text=text,
                    )
                )
                if (
                    len(
                        bullets,
                    )
                    >= limit
                ):
                    return tuple(
                        bullets,
                    )

        return tuple(
            bullets,
        )

    def _decision_support_bullets(
        self,
        bullets: tuple[ReportBullet, ...],
        *,
        limit: int,
    ) -> tuple[ReportBullet, ...]:
        decision_bullets: list[ReportBullet] = []
        seen: set[str] = set()
        for bullet in bullets:
            base_text = bullet.text.strip()
            if not base_text:
                continue
            normalized = base_text[0].lower() + base_text[1:]
            text = f"Consider {normalized} only after human review and portfolio constraint checks."
            if text in seen:
                continue
            seen.add(
                text,
            )
            decision_bullets.append(
                ReportBullet(
                    label=bullet.label,
                    text=text,
                )
            )
            if (
                len(
                    decision_bullets,
                )
                >= limit
            ):
                break

        return tuple(
            decision_bullets,
        )

    def _humanized_bullets(
        self,
        value: Any,
        *,
        limit: int,
    ) -> tuple[ReportBullet, ...]:
        bullets: list[ReportBullet] = []
        for item in safe_list(
            value,
        )[:limit]:
            text = self._humanize_token(
                item,
            )
            if text:
                bullets.append(
                    ReportBullet(
                        text=text,
                    )
                )

        return tuple(
            bullets,
        )

    def _humanize_token(
        self,
        value: str,
    ) -> str:
        text = value.strip()
        if not text:
            return ""

        normalized = " ".join(
            text.replace(
                "_",
                " ",
            )
            .replace(
                "-",
                " ",
            )
            .split()
        )
        if not normalized:
            return ""

        return normalized[0].upper() + normalized[1:]

    def _account_restriction_text(
        self,
        *,
        trading_blocked: bool | None,
        transfers_blocked: bool | None,
        account_blocked: bool | None,
        trade_suspended_by_user: bool | None,
        pattern_day_trader: bool | None,
    ) -> str:
        flags = (
            ("Trading Blocked", trading_blocked),
            ("Transfers Blocked", transfers_blocked),
            ("Account Blocked", account_blocked),
            ("Trading Suspended By User", trade_suspended_by_user),
            ("Pattern Day Trader Flag", pattern_day_trader),
        )
        active = tuple(label for label, value in flags if value is True)
        if active:
            return "; ".join(
                active,
            )

        if any(value is not None for _, value in flags):
            return "None Reported"

        return "Unknown"

    def _safe_ratio(
        self,
        numerator: float | None,
        denominator: float | None,
    ) -> float | None:
        if numerator is None or denominator is None or denominator == 0.0:
            return None

        return numerator / denominator

    def _format_count(
        self,
        value: float | None,
    ) -> str:
        if value is None:
            return "N/A"

        return str(
            int(
                value,
            )
        )

    def _format_bool(
        self,
        value: bool | None,
    ) -> str:
        if value is None:
            return "N/A"

        return "Yes" if value else "No"

    def _first_bool(
        self,
        *values: Any,
    ) -> bool | None:
        for value in values:
            if isinstance(
                value,
                bool,
            ):
                return value

            if isinstance(
                value,
                (int, float),
            ):
                return value != 0

            if isinstance(
                value,
                str,
            ):
                text = value.strip().lower()
                if text in {
                    "true",
                    "yes",
                    "1",
                }:
                    return True
                if text in {
                    "false",
                    "no",
                    "0",
                }:
                    return False

        return None
