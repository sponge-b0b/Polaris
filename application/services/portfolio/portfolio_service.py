from __future__ import annotations

from typing import Any
from typing import TYPE_CHECKING
from datetime import datetime, timezone

from application.persistence.portfolio import PortfolioPersistenceService
from core.storage.persistence.lineage import PersistenceLineage

from core.utils.utils import (
    _get_value,
    _safe_bool,
    _safe_dict,
    _safe_float,
    _safe_int,
    _safe_str,
)

from application.services.base import ServiceRequest
from application.services.base import ServiceResult
from application.services.base.application_service import (
    ApplicationService,
    ValidatingApplicationService,
)

from application.services.portfolio import (
    portfolio_analysis,
)
from application.services.portfolio import (
    portfolio_positions,
)
from application.services.portfolio import (
    portfolio_equity,
)
from application.services.portfolio.portfolio_equity_history import (
    normalize_portfolio_equity_history,
)

from domain.portfolio.models.portfolio_state import (
    PortfolioState,
)

from application.services.portfolio.portfolio_request import (
    PortfolioAnalysisRequest,
)
from application.services.portfolio.portfolio_result import (
    PortfolioAnalysisResult,
)

if TYPE_CHECKING:
    from integration.providers.portfolio.portfolio_provider import (
        PortfolioProvider,
    )


class PortfolioService(ApplicationService, ValidatingApplicationService):
    """
    Polaris Portfolio Service

    ============================================================
    PURPOSE
    ============================================================
    Canonical portfolio normalization + analytics node.

    SINGLE SOURCE OF TRUTH FOR:
        - portfolio state
        - equity state
        - normalized positions
        - exposure metrics
        - risk features

    ============================================================
    ARCHITECTURE
    ============================================================
    PROVIDER LAYER:
        Handles ALL external data access.

    SERVICES:
        Pure deterministic compute only.

    THIS NODE:
        Orchestrates provider -> services -> normalized state.

    ============================================================
    IMPORTANT
    ============================================================
    Polaris DOES NOT execute trades.

    Polaris ONLY:
        - consumes broker portfolio state
        - consumes market data
        - generates intelligence

    This node is fully compatible with:
        - live trading intelligence
        - historical simulation
        - backtesting
        - replay systems
    """

    service_name = "portfolio_service"

    # ============================================================
    # INIT
    # ============================================================

    def __init__(
        self,
        portfolio_provider: PortfolioProvider,
        portfolio_persistence_service: PortfolioPersistenceService,
    ) -> None:

        # ========================================================
        # PROVIDER LAYER
        # ========================================================

        self.portfolio_provider = portfolio_provider
        self.portfolio_persistence_service = portfolio_persistence_service

    async def run(
        self,
        request: ServiceRequest[PortfolioAnalysisRequest],
    ) -> ServiceResult[PortfolioAnalysisResult]:
        result = await self._execute(
            request.payload,
            lineage=_persistence_lineage(request),
        )

        return ServiceResult.ok(
            request_id=request.request_id,
            request_name=request.request_name,
            result=result,
        )

    async def validate_request(
        self,
        request: ServiceRequest[PortfolioAnalysisRequest],
    ) -> tuple[str, ...]:
        errors: list[str] = []

        if not isinstance(request.payload, PortfolioAnalysisRequest):
            return (f"Unsupported service request: {request.request_name}",)

        if not request.payload.symbol.strip():
            errors.append(
                "symbol is required.",
            )

        return tuple(errors)

    # ============================================================
    # EXECUTE
    # ============================================================

    async def _execute(
        self,
        request: PortfolioAnalysisRequest,
        *,
        lineage: PersistenceLineage = PersistenceLineage(),
    ) -> PortfolioAnalysisResult:

        symbol = request.symbol

        # ========================================================
        # RAW PROVIDER DATA
        # ========================================================

        raw_account = await self.portfolio_provider.get_account()

        raw_positions = await self.portfolio_provider.get_positions()

        raw_portfolio_history = await self.portfolio_provider.get_portfolio_history()

        # ========================================================
        # NORMALIZED POSITION STATE
        # ========================================================

        positions_response = portfolio_positions.execute_positions_analysis(
            raw_positions=raw_positions,
            symbol=symbol,
        )

        # ========================================================
        # LOAD LATEST PORTFOLIO STATE
        # ========================================================

        account_id = _safe_str(
            _get_value(raw_account, "id"),
        )

        portfolio_state = await self.portfolio_persistence_service.get_latest_state(
            account_id=account_id
        )

        peak_equity = 0.0
        if portfolio_state:
            peak_equity = portfolio_state.peak_equity

        # ========================================================
        # EQUITY STATE
        # ========================================================

        equity_response = portfolio_equity.execute_equity_analysis(
            raw_peak_equity=peak_equity,
            raw_account=raw_account,
        )

        # ========================================================
        # PORTFOLIO ANALYTICS
        # ========================================================

        portfolio_response = portfolio_analysis.execute_portfolio_analysis(
            positions_state=positions_response,
            equity_state=equity_response,
            portfolio_history=raw_portfolio_history,
        )

        equity_history_points = normalize_portfolio_equity_history(
            account_id=account_id,
            source=self.portfolio_provider.source,
            history=raw_portfolio_history,
            lineage=lineage,
        )

        # ========================================================
        # SAVE PORTFOLIO STATE
        # ========================================================

        await self.portfolio_persistence_service.persist_state_snapshot(
            self.to_portfolio_state(
                account_id=account_id,
                positions_state=positions_response,
                equity_state=equity_response,
                portfolio_state=portfolio_response,
            )
        )

        equity_history_result = (
            await self.portfolio_persistence_service.persist_expansion_records(
                equity_history_points=equity_history_points,
            )
        )
        if not equity_history_result.success:
            raise RuntimeError(
                "Portfolio equity history persistence failed: "
                f"{equity_history_result.error}"
            )

        return PortfolioAnalysisResult(
            portfolio_state=portfolio_response,
            positions_state=positions_response,
            equity_state=equity_response,
        )

    # ============================================================
    # SERIALIZE PORTFOLIO STATE
    # ============================================================

    def to_portfolio_state(
        self,
        account_id: str,
        positions_state: dict[str, Any],
        equity_state: dict[str, Any],
        portfolio_state: dict[str, Any],
    ) -> PortfolioState:
        return PortfolioState(
            account_id=account_id,
            timestamp=datetime.now(timezone.utc),
            equity=_safe_float(equity_state.get("equity")),
            peak_equity=_safe_float(equity_state.get("peak_equity")),
            portfolio_value=_safe_float(equity_state.get("portfolio_value")),
            cash=_safe_float(equity_state.get("cash")),
            buying_power=_safe_float(equity_state.get("buying_power")),
            last_equity=_safe_float(equity_state.get("last_equity")),
            cash_ratio=_safe_float(equity_state.get("cash_ratio")),
            buying_power_ratio=_safe_float(
                equity_state.get("buying_power_ratio"),
            ),
            realized_pnl=_safe_float(portfolio_state.get("realized_pnl")),
            realized_pnl_pct=_safe_float(
                portfolio_state.get("realized_pnl_pct"),
            ),
            unrealized_pnl=_safe_float(
                portfolio_state.get("unrealized_pnl"),
            ),
            unrealized_pnl_pct=_safe_float(
                portfolio_state.get("unrealized_pnl_pct"),
            ),
            unrealized_intraday_pnl=_safe_float(
                portfolio_state.get("unrealized_intraday_pnl"),
            ),
            unrealized_intraday_pnl_pct=_safe_float(
                portfolio_state.get("unrealized_intraday_pnl_pct"),
                default=_sum_position_value(
                    positions_state=positions_state,
                    key="unrealized_intraday_pnl_pct",
                ),
            ),
            pnl_total=_safe_float(portfolio_state.get("pnl_total")),
            pnl_total_pct=_safe_float(portfolio_state.get("pnl_total_pct")),
            drawdown_absolute=_safe_float(
                equity_state.get("drawdown_absolute"),
            ),
            drawdown_percent=_safe_float(
                equity_state.get("drawdown_percent"),
            ),
            capital_base=_safe_float(equity_state.get("capital_base")),
            equity_retention_ratio=_safe_float(
                equity_state.get("equity_retention_ratio"),
            ),
            long_market_value=_safe_float(
                equity_state.get("long_market_value"),
            ),
            short_market_value=_safe_float(
                equity_state.get("short_market_value"),
            ),
            gross_market_value=_safe_float(
                equity_state.get("gross_market_value"),
            ),
            net_market_value=_safe_float(
                equity_state.get("net_market_value"),
            ),
            gross_exposure=_safe_float(
                portfolio_state.get("gross_exposure"),
            ),
            net_exposure=_safe_float(portfolio_state.get("net_exposure")),
            long_exposure=_safe_float(
                portfolio_state.get("long_exposure"),
            ),
            short_exposure=_safe_float(
                portfolio_state.get("short_exposure"),
            ),
            leverage=_safe_float(portfolio_state.get("leverage")),
            largest_position_pct=_safe_float(
                portfolio_state.get("largest_position_pct"),
            ),
            concentration_score=_safe_float(
                portfolio_state.get("concentration_score"),
            ),
            diversification_score=_safe_float(
                portfolio_state.get("diversification_score"),
                default=1.0,
            ),
            beta_exposure=_safe_float(
                portfolio_state.get("beta_exposure"),
            ),
            beta_risk=_safe_float(portfolio_state.get("beta_risk")),
            portfolio_heat=_safe_float(
                portfolio_state.get("portfolio_heat"),
            ),
            risk_intensity=_safe_float(
                portfolio_state.get("risk_intensity"),
            ),
            initial_margin=_safe_float(equity_state.get("initial_margin")),
            maintenance_margin=_safe_float(
                equity_state.get("maintenance_margin"),
            ),
            last_maintenance_margin=_safe_float(
                equity_state.get("last_maintenance_margin"),
            ),
            margin_utilization_ratio=_safe_float(
                equity_state.get("margin_utilization_ratio"),
            ),
            initial_margin_ratio=_safe_float(
                equity_state.get("initial_margin_ratio"),
            ),
            daytrade_count=_safe_int(equity_state.get("daytrade_count")),
            pattern_day_trader=_safe_bool(
                equity_state.get("pattern_day_trader"),
            ),
            trading_blocked=_safe_bool(
                equity_state.get("trading_blocked"),
            ),
            transfers_blocked=_safe_bool(
                equity_state.get("transfers_blocked"),
            ),
            account_blocked=_safe_bool(
                equity_state.get("account_blocked"),
            ),
            trade_suspended_by_user=_safe_bool(
                equity_state.get("trade_suspended_by_user"),
            ),
            shorting_enabled=_safe_bool(
                equity_state.get("shorting_enabled"),
            ),
            position_count=_safe_int(portfolio_state.get("position_count")),
            portfolio_regime=_safe_str(
                portfolio_state.get("portfolio_regime"),
                default="unknown",
            ),
            directional_bias=_safe_str(
                portfolio_state.get("directional_bias"),
                default="neutral",
            ),
            account_health=_safe_str(
                equity_state.get("account_health"),
                default="unknown",
            ),
            sector_exposure=portfolio_state.get("sector_exposure", {}) or {},
            asset_class_exposure=(
                portfolio_state.get("asset_class_exposure", {}) or {}
            ),
            risk_signals=_merge_risk_signals(
                equity_state=equity_state,
                positions_state=positions_state,
                portfolio_state=portfolio_state,
            ),
        )


def _merge_risk_signals(
    *,
    equity_state: dict[str, Any],
    positions_state: dict[str, Any],
    portfolio_state: dict[str, Any],
) -> dict[str, Any]:
    return {
        **_safe_dict(equity_state.get("risk_signals")),
        **_safe_dict(positions_state.get("risk_signals")),
        **_safe_dict(portfolio_state.get("risk_signals")),
    }


def _sum_position_value(
    *,
    positions_state: dict[str, Any],
    key: str,
) -> float:
    positions = positions_state.get("positions", [])

    if not isinstance(positions, list):
        return 0.0

    return sum(
        _safe_float(position.get(key))
        for position in positions
        if isinstance(position, dict)
    )


def _persistence_lineage(
    request: ServiceRequest[PortfolioAnalysisRequest],
) -> PersistenceLineage:
    context = request.telemetry_context
    workflow_name = request.metadata.get("workflow_name")
    return PersistenceLineage(
        workflow_name=(workflow_name if isinstance(workflow_name, str) else None),
        execution_id=context.execution_id if context is not None else None,
        runtime_id=context.runtime_id if context is not None else None,
        node_name=context.node_name if context is not None else None,
    )
