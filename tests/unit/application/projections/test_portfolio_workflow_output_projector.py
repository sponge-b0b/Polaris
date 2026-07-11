from __future__ import annotations

from datetime import UTC
from datetime import datetime
from typing import cast

import pytest

from application.persistence.portfolio import PortfolioPersistenceService
from application.projections.workflow_outputs.projection_identity import (
    build_workflow_output_projection_lineage,
)
from application.projections.workflow_outputs.projection_models import (
    WorkflowOutputProjectionStatus,
)
from application.projections.workflow_outputs.projection_models import (
    WorkflowOutputProjectorRequest,
)
from application.projections.workflow_outputs.projectors import (
    PORTFOLIO_STATE_PROJECTOR_NAME,
)
from application.projections.workflow_outputs.projectors import (
    PortfolioStateWorkflowOutputProjector,
)
from application.projections.workflow_outputs.projectors import (
    build_portfolio_state_projector_registration,
)
from core.storage.persistence.completed_run_archive import CompletedNodeOutputRecord
from core.storage.persistence.completed_run_archive import CompletedRunExecutionMode
from core.storage.persistence.completed_run_archive import CompletedRunRecord
from core.storage.persistence.completed_run_archive import JsonObject
from core.storage.persistence.portfolio import (
    InMemoryPortfolioExpansionPersistenceRepository,
)
from core.storage.persistence.portfolio.in_memory_portfolio_state_repository import (
    InMemoryPortfolioStateRepository,
)
from domain.workflow_outputs import PORTFOLIO_STATE_OUTPUT_CONTRACT
from domain.workflow_outputs import WORKFLOW_OUTPUT_SCHEMA_VERSION_V1


@pytest.mark.asyncio
async def test_portfolio_projector_persists_curated_portfolio_records() -> None:
    expansion_repository = InMemoryPortfolioExpansionPersistenceRepository()
    state_repository = InMemoryPortfolioStateRepository()
    projector = PortfolioStateWorkflowOutputProjector(
        PortfolioPersistenceService(expansion_repository, state_repository),
    )

    outcome = await projector.project(_projector_request())

    assert outcome.status is WorkflowOutputProjectionStatus.SUCCEEDED
    assert outcome.projector_name == PORTFOLIO_STATE_PROJECTOR_NAME
    assert outcome.records_written == 25

    latest_state = await state_repository.get_latest("account-1")
    assert latest_state is not None
    assert latest_state.account_id == "account-1"
    assert latest_state.equity == 100_000.0
    assert latest_state.snapshot_id.startswith("portfolio_state_snapshot:")

    equity_points = await expansion_repository.list_equity_history_points(
        account_id="account-1",
        source="alpaca",
        timeframe="1D",
    )
    assert len(equity_points) == 2
    assert equity_points[0].observed_at == datetime(2026, 7, 9, tzinfo=UTC)
    assert equity_points[1].equity == 100_000.0

    position_history = await expansion_repository.list_position_history(
        account_id="account-1",
    )
    latest_positions = await expansion_repository.list_latest_positions(
        account_id="account-1",
    )
    assert [record.symbol for record in position_history] == ["AAPL", "SPY"]
    assert [record.symbol for record in latest_positions] == ["AAPL", "SPY"]
    assert latest_positions[1].weight == 0.70
    assert latest_positions[1].sector == "ETF"

    exposure_snapshots = await expansion_repository.list_exposure_snapshots(
        account_id="account-1",
    )
    assert len(exposure_snapshots) == 12
    sector_exposures = {
        record.exposure_name: record.exposure_value
        for record in exposure_snapshots
        if record.exposure_type == "sector"
    }
    assert sector_exposures == {"ETF": 0.70, "Technology": 0.15}

    risk_snapshots = await expansion_repository.list_risk_snapshots(
        account_id="account-1",
    )
    assert len(risk_snapshots) == 1
    assert risk_snapshots[0].risk_score == 0.33
    assert risk_snapshots[0].risk_level == "low"
    assert risk_snapshots[0].drawdown_risk == 0.05

    allocation_snapshots = await expansion_repository.list_allocation_snapshots(
        account_id="account-1",
    )
    assert len(allocation_snapshots) == 5
    position_allocations = {
        record.allocation_name: record.current_weight
        for record in allocation_snapshots
        if record.allocation_type == "position"
    }
    assert position_allocations == {"AAPL": 0.15, "SPY": 0.70}


@pytest.mark.asyncio
async def test_portfolio_projector_uses_deterministic_record_ids() -> None:
    first_expansion = InMemoryPortfolioExpansionPersistenceRepository()
    first_state = InMemoryPortfolioStateRepository()
    second_expansion = InMemoryPortfolioExpansionPersistenceRepository()
    second_state = InMemoryPortfolioStateRepository()
    request = _projector_request()

    await PortfolioStateWorkflowOutputProjector(
        PortfolioPersistenceService(first_expansion, first_state),
    ).project(request)
    await PortfolioStateWorkflowOutputProjector(
        PortfolioPersistenceService(second_expansion, second_state),
    ).project(request)

    first_latest_state = await first_state.get_latest("account-1")
    second_latest_state = await second_state.get_latest("account-1")
    assert first_latest_state is not None
    assert second_latest_state is not None
    assert first_latest_state.snapshot_id == second_latest_state.snapshot_id

    first_positions = await first_expansion.list_position_history(
        account_id="account-1"
    )
    second_positions = await second_expansion.list_position_history(
        account_id="account-1"
    )
    assert [record.position_history_id for record in first_positions] == [
        record.position_history_id for record in second_positions
    ]


@pytest.mark.asyncio
async def test_portfolio_projector_skips_without_canonical_state() -> None:
    expansion_repository = InMemoryPortfolioExpansionPersistenceRepository()
    state_repository = InMemoryPortfolioStateRepository()
    projector = PortfolioStateWorkflowOutputProjector(
        PortfolioPersistenceService(expansion_repository, state_repository),
    )
    outputs = dict(_portfolio_outputs())
    outputs.pop("canonical_portfolio_state")

    outcome = await projector.project(
        _projector_request(outputs=cast(JsonObject, outputs)),
    )

    assert outcome.status is WorkflowOutputProjectionStatus.SKIPPED
    assert outcome.records_written == 0
    assert await state_repository.get_latest("account-1") is None
    assert "canonical_portfolio_state" in (outcome.message or "")


def test_build_portfolio_state_projector_registration_uses_canonical_contract() -> None:
    registration = build_portfolio_state_projector_registration(
        PortfolioPersistenceService(
            InMemoryPortfolioExpansionPersistenceRepository(),
            InMemoryPortfolioStateRepository(),
        ),
    )

    assert registration.projector_name == PORTFOLIO_STATE_PROJECTOR_NAME
    assert registration.output_contract == PORTFOLIO_STATE_OUTPUT_CONTRACT
    assert registration.output_schema_version == WORKFLOW_OUTPUT_SCHEMA_VERSION_V1
    assert registration.supported_node_names == ("portfolio_state_builder",)


def _projector_request(
    *,
    outputs: JsonObject | None = None,
) -> WorkflowOutputProjectorRequest:
    run = _run()
    node_output = _node(outputs=outputs)
    return WorkflowOutputProjectorRequest(
        run=run,
        node_output=node_output,
        source_fingerprint="fingerprint-portfolio-1",
        lineage=build_workflow_output_projection_lineage(
            run=run,
            node_output=node_output,
        ),
        requested_at=datetime(2026, 7, 10, 13, 31, tzinfo=UTC),
    )


def _run() -> CompletedRunRecord:
    return CompletedRunRecord(
        run_id="run-1",
        workflow_name="morning_report",
        workflow_id="workflow-1",
        execution_id="exec-1",
        runtime_id="runtime-1",
        status="succeeded",
        success=True,
        context_json={},
        inputs_json={},
        outputs_json={},
        metadata={},
        errors_json=(),
        started_at=datetime(2026, 7, 10, 13, tzinfo=UTC),
        completed_at=datetime(2026, 7, 10, 13, 35, tzinfo=UTC),
        duration_seconds=300.0,
        node_count=1,
        completed_node_count=1,
        failed_node_count=0,
        execution_mode=CompletedRunExecutionMode.NORMAL,
    )


def _node(
    *,
    outputs: JsonObject | None = None,
) -> CompletedNodeOutputRecord:
    return CompletedNodeOutputRecord(
        node_output_id="node-output-portfolio-1",
        run_id="run-1",
        workflow_name="morning_report",
        execution_id="exec-1",
        node_name="portfolio_state_builder",
        node_type="portfolio_state",
        output_contract=PORTFOLIO_STATE_OUTPUT_CONTRACT,
        output_schema_version=WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
        status="succeeded",
        success=True,
        outputs=outputs or _portfolio_outputs(),
        metadata={"quality_status": "normal"},
        errors_json=(),
        started_at=datetime(2026, 7, 10, 13, 29, tzinfo=UTC),
        completed_at=datetime(2026, 7, 10, 13, 31, tzinfo=UTC),
        duration_seconds=120.0,
    )


def _portfolio_outputs() -> JsonObject:
    return {
        "canonical_portfolio_state": {
            "account_id": "account-1",
            "timestamp": "2026-07-10T13:30:00+00:00",
            "equity": 100_000.0,
            "peak_equity": 105_000.0,
            "portfolio_value": 100_000.0,
            "cash": 15_000.0,
            "buying_power": 40_000.0,
            "last_equity": 99_000.0,
            "cash_ratio": 0.15,
            "buying_power_ratio": 0.40,
            "drawdown_absolute": 5_000.0,
            "drawdown_percent": 0.05,
            "capital_base": 95_000.0,
            "equity_retention_ratio": 1.0,
            "long_market_value": 85_000.0,
            "short_market_value": 0.0,
            "gross_market_value": 85_000.0,
            "net_market_value": 85_000.0,
            "gross_exposure": 0.85,
            "net_exposure": 0.85,
            "long_exposure": 0.85,
            "short_exposure": 0.0,
            "leverage": 1.0,
            "largest_position_pct": 0.70,
            "concentration_score": 0.40,
            "diversification_score": 0.60,
            "beta_exposure": 1.05,
            "beta_risk": 0.18,
            "portfolio_heat": 0.22,
            "risk_intensity": 0.33,
            "position_count": 2,
            "portfolio_regime": "balanced",
            "directional_bias": "long",
            "account_health": "healthy",
            "sector_exposure": {"ETF": 0.70, "Technology": 0.15},
            "asset_class_exposure": {"equity": 0.85},
            "risk_signals": {"portfolio_risk_normal": True},
            "schema_version": 2,
        },
        "positions": [
            {
                "symbol": "SPY",
                "quantity": 100.0,
                "market_value": 70_000.0,
                "cost_basis": 60_000.0,
                "exposure_weight": 0.70,
                "sector": "ETF",
                "theme": "index",
                "beta": 1.0,
            },
            {
                "symbol": "AAPL",
                "quantity": 50.0,
                "market_value": 15_000.0,
                "cost_basis": 12_000.0,
                "exposure_weight": 0.15,
                "sector": "Technology",
                "theme": "mega_cap",
                "beta": 1.2,
            },
        ],
        "exposures": {
            "gross_exposure": 0.85,
            "net_exposure": 0.85,
            "long_exposure": 0.85,
            "short_exposure": 0.0,
            "leverage": 1.0,
            "gross_market_value": 85_000.0,
            "net_market_value": 85_000.0,
            "long_market_value": 85_000.0,
            "short_market_value": 0.0,
            "sector_exposure": {"ETF": 0.70, "Technology": 0.15},
            "asset_class_exposure": {"equity": 0.85},
        },
        "risk_metrics": {
            "drawdown_percent": 0.05,
            "concentration_score": 0.40,
            "risk_intensity": 0.33,
            "beta_exposure": 1.05,
            "account_health": "healthy",
        },
        "allocation_data": {
            "positions": [
                {"symbol": "SPY", "current_weight": 0.70, "market_value": 70_000.0},
                {"symbol": "AAPL", "current_weight": 0.15, "market_value": 15_000.0},
            ],
            "sector_exposure": {"ETF": 0.70, "Technology": 0.15},
            "asset_class_exposure": {"equity": 0.85},
        },
        "equity_history_points": [
            {
                "account_id": "account-1",
                "source": "alpaca",
                "timeframe": "1D",
                "observed_at": "2026-07-09T00:00:00+00:00",
                "equity": 99_000.0,
                "profit_loss": 1_000.0,
                "profit_loss_pct": 0.0102,
                "base_value": 98_000.0,
            },
            {
                "account_id": "account-1",
                "source": "alpaca",
                "timeframe": "1D",
                "observed_at": "2026-07-10T00:00:00+00:00",
                "equity": 100_000.0,
                "profit_loss": 2_000.0,
                "profit_loss_pct": 0.0204,
                "base_value": 98_000.0,
            },
        ],
        "provider_source": "alpaca",
        "history_period": "1A",
        "history_timeframe": "1D",
    }
