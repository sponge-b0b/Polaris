from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC
from datetime import datetime
from typing import cast

import pytest

from application.persistence.macro import MacroPersistenceService
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
    MACRO_ANALYSIS_PROJECTOR_NAME,
)
from application.projections.workflow_outputs.projectors import (
    MacroAnalysisWorkflowOutputProjector,
)
from application.projections.workflow_outputs.projectors import (
    build_macro_analysis_projector_registration,
)
from core.storage.persistence.completed_run_archive import CompletedNodeOutputRecord
from core.storage.persistence.completed_run_archive import CompletedRunExecutionMode
from core.storage.persistence.completed_run_archive import CompletedRunRecord
from core.storage.persistence.completed_run_archive import JsonObject
from core.storage.persistence.macro import MacroPersistenceBundle
from core.storage.persistence.macro import MacroPersistenceRepository
from core.storage.persistence.macro import MacroPersistenceResult
from domain.workflow_outputs import MACRO_ANALYSIS_OUTPUT_CONTRACT
from domain.workflow_outputs import WORKFLOW_OUTPUT_SCHEMA_VERSION_V1


@pytest.mark.asyncio
async def test_macro_projector_persists_typed_macro_records() -> None:
    repository = _FakeMacroRepository()
    projector = MacroAnalysisWorkflowOutputProjector(
        MacroPersistenceService(cast(MacroPersistenceRepository, repository)),
    )

    outcome = await projector.project(_projector_request())

    assert outcome.status is WorkflowOutputProjectionStatus.SUCCEEDED
    assert outcome.projector_name == MACRO_ANALYSIS_PROJECTOR_NAME
    assert outcome.records_written == 3
    assert len(repository.bundles) == 1

    bundle = repository.bundles[0]
    assert len(bundle.observations) == 1
    assert len(bundle.regime_snapshots) == 1
    assert len(bundle.calendar_events) == 1

    observation = bundle.observations[0]
    assert observation.indicator_name == "cpi"
    assert observation.value == 3.2
    assert observation.source == "fred"
    assert observation.region == "US"
    assert observation.indicator_category == "inflation"
    assert observation.observation_timestamp == datetime(2026, 6, 1, tzinfo=UTC)
    assert observation.metadata["source_fingerprint"] == "fingerprint-1"
    assert observation.lineage.node_name == "fundamental_agent"

    regime = bundle.regime_snapshots[0]
    assert regime.timestamp == datetime(2026, 7, 10, 13, 30, tzinfo=UTC)
    assert regime.source == "MacroService"
    assert regime.region == "US"
    assert regime.inflation_regime == "disinflationary"
    assert regime.liquidity_regime == "high_liquidity"
    assert regime.fed_stance == "dovish"
    assert regime.yield_curve_regime == "normal_curve"
    assert regime.macro_regime == "risk_on_expansion"
    assert regime.economic_regime == "risk_on_expansion"
    assert regime.macro_score == 0.75
    assert regime.confidence == 0.85
    macro_inputs = cast(Mapping[str, object], regime.inputs["macro_data"])
    regime_outputs = cast(Mapping[str, object], regime.outputs["economic_regime"])
    assert macro_inputs["cpi"] == 3.2
    assert regime_outputs["market_bias"] == "bullish_bias"

    calendar_event = bundle.calendar_events[0]
    assert calendar_event.event_name == "CPI Release"
    assert calendar_event.source == "fred"
    assert calendar_event.event_timestamp == datetime(2026, 7, 11, 12, 30, tzinfo=UTC)
    assert calendar_event.region == "US"
    assert calendar_event.importance_score == 0.9


@pytest.mark.asyncio
async def test_macro_projector_uses_deterministic_record_ids() -> None:
    first_repository = _FakeMacroRepository()
    second_repository = _FakeMacroRepository()
    request = _projector_request()

    await MacroAnalysisWorkflowOutputProjector(
        MacroPersistenceService(cast(MacroPersistenceRepository, first_repository)),
    ).project(request)
    await MacroAnalysisWorkflowOutputProjector(
        MacroPersistenceService(cast(MacroPersistenceRepository, second_repository)),
    ).project(request)

    first_bundle = first_repository.bundles[0]
    second_bundle = second_repository.bundles[0]
    assert (
        first_bundle.observations[0].observation_id
        == second_bundle.observations[0].observation_id
    )
    assert (
        first_bundle.regime_snapshots[0].regime_snapshot_id
        == second_bundle.regime_snapshots[0].regime_snapshot_id
    )
    assert (
        first_bundle.calendar_events[0].event_id
        == second_bundle.calendar_events[0].event_id
    )


@pytest.mark.asyncio
async def test_macro_projector_skips_without_first_class_timestamp() -> None:
    repository = _FakeMacroRepository()
    projector = MacroAnalysisWorkflowOutputProjector(
        MacroPersistenceService(cast(MacroPersistenceRepository, repository)),
    )
    outputs = dict(_macro_outputs())
    outputs.pop("observed_at")

    outcome = await projector.project(
        _projector_request(outputs=cast(JsonObject, outputs))
    )

    assert outcome.status is WorkflowOutputProjectionStatus.SKIPPED
    assert outcome.records_written == 0
    assert repository.bundles == []
    assert "observed_at" in (outcome.message or "")


def test_build_macro_projector_registration_uses_canonical_contract() -> None:
    registration = build_macro_analysis_projector_registration(
        MacroPersistenceService(
            cast(MacroPersistenceRepository, _FakeMacroRepository())
        ),
    )

    assert registration.projector_name == MACRO_ANALYSIS_PROJECTOR_NAME
    assert registration.output_contract == MACRO_ANALYSIS_OUTPUT_CONTRACT
    assert registration.output_schema_version == WORKFLOW_OUTPUT_SCHEMA_VERSION_V1
    assert registration.supported_node_names == ("fundamental_agent",)


class _FakeMacroRepository:
    def __init__(self) -> None:
        self.bundles: list[MacroPersistenceBundle] = []

    async def persist_macro_bundle(
        self,
        bundle: MacroPersistenceBundle,
    ) -> MacroPersistenceResult:
        self.bundles.append(bundle)
        primary_record_id = bundle.regime_snapshots[0].regime_snapshot_id
        return MacroPersistenceResult.succeeded(
            primary_record_id=primary_record_id,
            records_persisted=(
                len(bundle.observations)
                + len(bundle.regime_snapshots)
                + len(bundle.calendar_events)
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
        node_name="fundamental_agent",
        node_type="macro_fundamental",
        output_contract=MACRO_ANALYSIS_OUTPUT_CONTRACT,
        output_schema_version=WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
        status="succeeded",
        success=True,
        outputs=outputs or _macro_outputs(),
        metadata={"quality_status": "normal"},
        errors_json=(),
        started_at=datetime(2026, 7, 10, 13, 29, tzinfo=UTC),
        completed_at=datetime(2026, 7, 10, 13, 31, tzinfo=UTC),
        duration_seconds=120.0,
    )


def _macro_outputs() -> JsonObject:
    return {
        "observed_at": "2026-07-10T13:30:00+00:00",
        "macro_source": "MacroService",
        "macro_region": "US",
        "confidence": 0.85,
        "regime": "risk_on_expansion",
        "macro_analysis": {
            "macro_data": {
                "cpi": 3.2,
                "core_cpi": 2.9,
                "pce": 2.4,
                "fed_funds_rate": 4.5,
                "treasury_2y": 4.2,
                "treasury_10y": 4.8,
                "unemployment_rate": 3.9,
                "m2_money_supply": 21_500_000.0,
                "vix": 14.0,
                "observations": [
                    {
                        "indicator_name": "cpi",
                        "value": 3.2,
                        "observation_timestamp": "2026-06-01T00:00:00+00:00",
                        "source": "fred",
                        "indicator_category": "inflation",
                        "region": "US",
                    }
                ],
            },
            "inflation_analysis": {
                "inflation_regime": "disinflationary",
            },
            "fed_analysis": {"fed_stance": "dovish"},
            "liquidity_analysis": {
                "liquidity_regime": "high_liquidity",
            },
            "yield_curve_analysis": {
                "curve_regime": "normal_curve",
            },
            "economic_regime": {
                "economic_regime": "risk_on_expansion",
                "market_bias": "bullish_bias",
                "macro_score": 0.75,
            },
            "inflation_regime": "disinflationary",
            "fed_stance": "dovish",
            "liquidity_regime": "high_liquidity",
            "yield_curve_regime": "normal_curve",
        },
        "economic_calendar_events": [
            {
                "event_name": "CPI Release",
                "event_timestamp": "2026-07-11T12:30:00+00:00",
                "source": "fred",
                "region": "US",
                "event_type": "inflation",
                "importance_score": 0.9,
            }
        ],
    }
