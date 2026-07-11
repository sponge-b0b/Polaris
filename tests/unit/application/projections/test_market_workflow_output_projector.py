from __future__ import annotations

from datetime import UTC
from datetime import datetime
from typing import cast

import pytest

from application.persistence.market import MarketPersistenceService
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
    TECHNICAL_MARKET_PROJECTOR_NAME,
)
from application.projections.workflow_outputs.projectors import (
    TechnicalMarketWorkflowOutputProjector,
)
from application.projections.workflow_outputs.projectors import (
    build_technical_market_projector_registration,
)
from core.storage.persistence.completed_run_archive import CompletedNodeOutputRecord
from core.storage.persistence.completed_run_archive import CompletedRunExecutionMode
from core.storage.persistence.completed_run_archive import CompletedRunRecord
from core.storage.persistence.completed_run_archive import JsonObject
from core.storage.persistence.market import MarketPersistenceBundle
from core.storage.persistence.market import MarketPersistenceRepository
from core.storage.persistence.market import MarketPersistenceResult
from domain.workflow_outputs import TECHNICAL_ANALYSIS_OUTPUT_CONTRACT
from domain.workflow_outputs import WORKFLOW_OUTPUT_SCHEMA_VERSION_V1


@pytest.mark.asyncio
async def test_technical_market_projector_persists_typed_market_records() -> None:
    repository = _FakeMarketRepository()
    projector = TechnicalMarketWorkflowOutputProjector(
        MarketPersistenceService(cast(MarketPersistenceRepository, repository)),
    )
    request = _projector_request()

    outcome = await projector.project(request)

    assert outcome.status is WorkflowOutputProjectionStatus.SUCCEEDED
    assert outcome.projector_name == TECHNICAL_MARKET_PROJECTOR_NAME
    assert outcome.records_written == 3
    assert len(repository.bundles) == 1

    bundle = repository.bundles[0]
    assert len(bundle.technical_snapshots) == 1
    assert len(bundle.context_snapshots) == 1
    assert len(bundle.breadth_snapshots) == 1
    assert bundle.ohlcv == ()
    assert bundle.indicators == ()
    assert bundle.event_snapshots == ()

    technical = bundle.technical_snapshots[0]
    assert technical.symbol == "SPY"
    assert technical.timestamp == datetime(2026, 7, 10, 13, 30, tzinfo=UTC)
    assert technical.source == "TechnicalService"
    assert technical.technical_regime == "constructive"
    assert technical.trend_regime == "uptrend"
    assert technical.volatility_regime == "normal"
    assert technical.breadth_regime == "weak_breadth"
    assert technical.directional_technical_score == 0.31
    assert technical.confidence == 0.58
    assert technical.metadata["source_fingerprint"] == "fingerprint-1"
    assert technical.lineage.node_name == "technical_agent"

    context = bundle.context_snapshots[0]
    assert context.universe == "sp500"
    assert context.advances_count == 180
    assert context.declines_count == 310
    assert context.price_ad_divergence == 1.0
    assert context.top_50_constituents_payload == {
        "constituents": ["AAPL", "MSFT"],
    }
    assert context.market_caps_payload == {
        "AAPL": 3_000_000_000_000.0,
        "MSFT": 2_800_000_000_000.0,
    }

    breadth = bundle.breadth_snapshots[0]
    assert breadth.universe == "sp500"
    assert breadth.breadth_score == -0.52
    assert breadth.breadth_risk_score == 0.76
    assert breadth.price_ad_divergence == 1.0
    assert breadth.new_high_low_diff == -36
    assert breadth.breadth_regime == "weak_breadth"
    assert breadth.source_metrics_payload["mcclellan_oscillator"] == -32.5


@pytest.mark.asyncio
async def test_technical_market_projector_uses_deterministic_record_ids() -> None:
    first_repository = _FakeMarketRepository()
    second_repository = _FakeMarketRepository()
    request = _projector_request()

    await TechnicalMarketWorkflowOutputProjector(
        MarketPersistenceService(cast(MarketPersistenceRepository, first_repository)),
    ).project(request)
    await TechnicalMarketWorkflowOutputProjector(
        MarketPersistenceService(cast(MarketPersistenceRepository, second_repository)),
    ).project(request)

    first_bundle = first_repository.bundles[0]
    second_bundle = second_repository.bundles[0]
    assert (
        first_bundle.technical_snapshots[0].technical_snapshot_id
        == second_bundle.technical_snapshots[0].technical_snapshot_id
    )
    assert (
        first_bundle.context_snapshots[0].context_snapshot_id
        == second_bundle.context_snapshots[0].context_snapshot_id
    )
    assert (
        first_bundle.breadth_snapshots[0].breadth_snapshot_id
        == second_bundle.breadth_snapshots[0].breadth_snapshot_id
    )


@pytest.mark.asyncio
async def test_technical_market_projector_skips_without_first_class_timestamp() -> None:
    repository = _FakeMarketRepository()
    projector = TechnicalMarketWorkflowOutputProjector(
        MarketPersistenceService(cast(MarketPersistenceRepository, repository)),
    )
    outputs = dict(_technical_outputs())
    outputs.pop("observed_at")

    outcome = await projector.project(
        _projector_request(outputs=cast(JsonObject, outputs))
    )

    assert outcome.status is WorkflowOutputProjectionStatus.SKIPPED
    assert outcome.records_written == 0
    assert repository.bundles == []
    assert "observed_at" in (outcome.message or "")


def test_build_technical_market_projector_registration_uses_canonical_contract() -> (
    None
):
    registration = build_technical_market_projector_registration(
        MarketPersistenceService(
            cast(MarketPersistenceRepository, _FakeMarketRepository())
        ),
    )

    assert registration.projector_name == TECHNICAL_MARKET_PROJECTOR_NAME
    assert registration.output_contract == TECHNICAL_ANALYSIS_OUTPUT_CONTRACT
    assert registration.output_schema_version == WORKFLOW_OUTPUT_SCHEMA_VERSION_V1
    assert registration.supported_node_names == ("technical_agent",)


class _FakeMarketRepository:
    def __init__(self) -> None:
        self.bundles: list[MarketPersistenceBundle] = []

    async def persist_market_bundle(
        self,
        bundle: MarketPersistenceBundle,
    ) -> MarketPersistenceResult:
        self.bundles.append(bundle)
        return MarketPersistenceResult.succeeded(
            primary_record_id=bundle.technical_snapshots[0].technical_snapshot_id,
            records_persisted=(
                len(bundle.technical_snapshots)
                + len(bundle.context_snapshots)
                + len(bundle.breadth_snapshots)
            ),
        )


def _projector_request(
    *,
    outputs: JsonObject | None = None,
) -> WorkflowOutputProjectorRequest:
    run = _run()
    node_output = _node(outputs=outputs)
    return WorkflowOutputProjectorRequest(
        run=run,
        node_output=node_output,
        source_fingerprint="fingerprint-1",
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
        node_output_id="node-output-1",
        run_id="run-1",
        workflow_name="morning_report",
        execution_id="exec-1",
        node_name="technical_agent",
        node_type="technical_analysis",
        output_contract=TECHNICAL_ANALYSIS_OUTPUT_CONTRACT,
        output_schema_version=WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
        status="succeeded",
        success=True,
        outputs=outputs or _technical_outputs(),
        metadata={
            "source": "TechnicalService",
            "quality_status": "normal",
        },
        errors_json=(),
        started_at=datetime(2026, 7, 10, 13, 29, tzinfo=UTC),
        completed_at=datetime(2026, 7, 10, 13, 31, tzinfo=UTC),
        duration_seconds=120.0,
    )


def _technical_outputs() -> JsonObject:
    return {
        "observed_at": "2026-07-10T13:30:00+00:00",
        "market_universe": "sp500",
        "directional_score": 0.31,
        "confidence": 0.58,
        "regime": "constructive",
        "features": {
            "symbol": "SPY",
            "technical_score": 0.31,
            "snapshot": {
                "close": 450.0,
                "rsi_14": 61.0,
            },
            "trend": {
                "primary_trend": "uptrend",
                "trend_regime": "uptrend",
                "trend_score": 0.72,
                "trend_strength": 0.72,
                "trend_quality": 0.66,
                "trend_risk_score": 0.24,
            },
            "volatility": {
                "volatility_regime": "normal",
                "volatility_score": 0.44,
                "volatility_risk_score": 0.31,
            },
            "market_context": {
                "has_breadth": True,
                "advances_count": 180,
                "declines_count": 310,
                "breadth_percent": 0.37,
                "pct_above_50dma": 0.42,
                "pct_above_200dma": 0.48,
                "new_highs": 8,
                "new_lows": 44,
                "new_high_low_diff": -36,
                "mcclellan_oscillator": -32.5,
                "price_ad_divergence": 1.0,
                "top_50_constituents": ["AAPL", "MSFT"],
                "market_caps": {
                    "AAPL": 3_000_000_000_000.0,
                    "MSFT": 2_800_000_000_000.0,
                },
            },
            "breadth": {
                "has_breadth_data": True,
                "breadth_regime": "weak_breadth",
                "risk_regime": "elevated",
                "breadth_score": -0.52,
                "breadth_risk_score": 0.76,
                "participation_score": -0.41,
                "leadership_score": -0.38,
                "mcclellan_score": -0.45,
                "divergence_score": -0.60,
                "price_ad_divergence": True,
                "new_high_low_diff": -36,
                "source_metrics": {
                    "mcclellan_oscillator": -32.5,
                },
            },
            "raw_regime": {
                "inputs": {
                    "breadth_regime": "weak_breadth",
                },
            },
            "regime": {
                "directional_technical_score": 0.31,
                "confidence": 0.58,
                "regime": "constructive",
                "bull_score": 0.62,
                "bear_score": 0.20,
                "sideways_score": 0.18,
                "inputs": {
                    "breadth_regime": "weak_breadth",
                },
            },
        },
    }
