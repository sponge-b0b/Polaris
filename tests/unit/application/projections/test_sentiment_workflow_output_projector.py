from __future__ import annotations

from datetime import UTC
from datetime import datetime
from typing import cast

import pytest

from application.persistence.sentiment import SentimentPersistenceService
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
    SENTIMENT_SNAPSHOT_PROJECTOR_NAME,
)
from application.projections.workflow_outputs.projectors import (
    SentimentSnapshotWorkflowOutputProjector,
)
from application.projections.workflow_outputs.projectors import (
    build_sentiment_snapshot_projector_registration,
)
from core.storage.persistence.completed_run_archive import CompletedNodeOutputRecord
from core.storage.persistence.completed_run_archive import CompletedRunExecutionMode
from core.storage.persistence.completed_run_archive import CompletedRunRecord
from core.storage.persistence.completed_run_archive import JsonObject
from core.storage.persistence.sentiment import SentimentPersistenceBundle
from core.storage.persistence.sentiment import SentimentPersistenceRepository
from core.storage.persistence.sentiment import SentimentPersistenceResult
from domain.workflow_outputs import SENTIMENT_SNAPSHOT_OUTPUT_CONTRACT
from domain.workflow_outputs import WORKFLOW_OUTPUT_SCHEMA_VERSION_V1


@pytest.mark.asyncio
async def test_sentiment_projector_persists_snapshot_and_eligible_sources() -> None:
    repository = _FakeSentimentRepository()
    projector = SentimentSnapshotWorkflowOutputProjector(
        SentimentPersistenceService(cast(SentimentPersistenceRepository, repository)),
    )

    outcome = await projector.project(_projector_request())

    assert outcome.status is WorkflowOutputProjectionStatus.SUCCEEDED
    assert outcome.projector_name == SENTIMENT_SNAPSHOT_PROJECTOR_NAME
    assert outcome.records_written == 2
    assert len(repository.bundles) == 1

    bundle = repository.bundles[0]
    assert len(bundle.snapshots) == 1
    assert len(bundle.sources) == 1

    snapshot = bundle.snapshots[0]
    assert snapshot.timestamp == datetime(2026, 7, 10, 13, 30, tzinfo=UTC)
    assert snapshot.source == "SentimentService"
    assert snapshot.symbol == "SPY"
    assert snapshot.universe == "single_symbol"
    assert snapshot.market_regime == "bullish"
    assert snapshot.market_bias == "risk_on"
    assert snapshot.fear_greed_score == 0.64
    assert snapshot.news_sentiment_score == 0.4
    assert snapshot.social_sentiment_score == 0.2
    assert snapshot.composite_sentiment == 0.35
    assert snapshot.confidence == 0.72
    assert snapshot.directional_signal == 0.35
    assert snapshot.metadata["source_fingerprint"] == "fingerprint-1"
    assert snapshot.lineage.node_name == "sentiment_agent"

    source = bundle.sources[0]
    assert source.sentiment_snapshot_id == snapshot.sentiment_snapshot_id
    assert source.source == "fear_greed"
    assert source.source_type == "fear_greed"
    assert source.timestamp == datetime(2026, 7, 10, 12, 45, tzinfo=UTC)
    assert source.sentiment_score == 0.28
    assert source.confidence == 0.8
    assert source.weight == 0.5
    assert source.sample_size == 1


@pytest.mark.asyncio
async def test_sentiment_projector_persists_snapshot_without_unqualified_sources() -> (
    None
):
    repository = _FakeSentimentRepository()
    projector = SentimentSnapshotWorkflowOutputProjector(
        SentimentPersistenceService(cast(SentimentPersistenceRepository, repository)),
    )
    outputs: dict[str, object] = dict(_sentiment_outputs())
    source_data = dict(cast(dict[str, object], outputs["sentiment_source_data"]))
    source_data["providers"] = {"fear_greed": {"sentiment_score": 0.2}}
    outputs["sentiment_source_data"] = source_data

    outcome = await projector.project(
        _projector_request(outputs=cast(JsonObject, outputs))
    )

    assert outcome.status is WorkflowOutputProjectionStatus.SUCCEEDED
    assert outcome.records_written == 1
    assert len(repository.bundles[0].snapshots) == 1
    assert repository.bundles[0].sources == ()


@pytest.mark.asyncio
async def test_sentiment_projector_skips_without_first_class_timestamp() -> None:
    repository = _FakeSentimentRepository()
    projector = SentimentSnapshotWorkflowOutputProjector(
        SentimentPersistenceService(cast(SentimentPersistenceRepository, repository)),
    )
    outputs = dict(_sentiment_outputs())
    outputs.pop("observed_at")

    outcome = await projector.project(
        _projector_request(outputs=cast(JsonObject, outputs))
    )

    assert outcome.status is WorkflowOutputProjectionStatus.SKIPPED
    assert outcome.records_written == 0
    assert repository.bundles == []
    assert "observed_at" in (outcome.message or "")


def test_build_sentiment_projector_registration_uses_canonical_contract() -> None:
    registration = build_sentiment_snapshot_projector_registration(
        SentimentPersistenceService(
            cast(SentimentPersistenceRepository, _FakeSentimentRepository())
        ),
    )

    assert registration.projector_name == SENTIMENT_SNAPSHOT_PROJECTOR_NAME
    assert registration.output_contract == SENTIMENT_SNAPSHOT_OUTPUT_CONTRACT
    assert registration.output_schema_version == WORKFLOW_OUTPUT_SCHEMA_VERSION_V1
    assert registration.supported_node_names == ("sentiment_agent",)


class _FakeSentimentRepository:
    def __init__(self) -> None:
        self.bundles: list[SentimentPersistenceBundle] = []

    async def persist_sentiment_bundle(
        self,
        bundle: SentimentPersistenceBundle,
    ) -> SentimentPersistenceResult:
        self.bundles.append(bundle)
        return SentimentPersistenceResult.succeeded(
            primary_record_id=bundle.snapshots[0].sentiment_snapshot_id,
            records_persisted=len(bundle.snapshots) + len(bundle.sources),
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
        node_name="sentiment_agent",
        node_type="market_sentiment",
        output_contract=SENTIMENT_SNAPSHOT_OUTPUT_CONTRACT,
        output_schema_version=WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
        status="succeeded",
        success=True,
        outputs=outputs or _sentiment_outputs(),
        metadata={"quality_status": "normal"},
        errors_json=(),
        started_at=datetime(2026, 7, 10, 13, 29, tzinfo=UTC),
        completed_at=datetime(2026, 7, 10, 13, 31, tzinfo=UTC),
        duration_seconds=120.0,
    )


def _sentiment_outputs() -> JsonObject:
    return {
        "observed_at": "2026-07-10T13:30:00+00:00",
        "sentiment_source": "SentimentService",
        "sentiment_universe": "single_symbol",
        "symbol": "SPY",
        "directional_score": 0.35,
        "confidence": 0.72,
        "regime": "bullish",
        "features": {
            "composite_sentiment": 0.35,
            "stability": 0.66,
            "momentum": 0.12,
            "divergence": 0.08,
            "components": {
                "news": 0.4,
                "social": 0.2,
                "fear_greed": 0.64,
            },
        },
        "sentiment_snapshot": {
            "composite_sentiment": 0.35,
            "confidence": 0.72,
            "regime": "bullish",
            "market_bias": "risk_on",
            "fusion_components": {"news": 0.4},
        },
        "sentiment_source_data": {
            "symbol": "SPY",
            "providers": {
                "fear_greed": {
                    "timestamp": "2026-07-10T12:45:00+00:00",
                    "normalized_sentiment": 0.28,
                    "confidence": 0.8,
                    "weight": 0.5,
                    "sample_size": 1,
                },
                "provider_without_timestamp": {
                    "sentiment_score": 0.1,
                },
            },
            "features": {"components": {"news": 0.4}},
            "sentiment": {"composite_sentiment": 0.35},
            "composite_sentiment": 0.35,
            "market_regime": "bullish",
            "market_bias": "risk_on",
            "confidence": 0.72,
        },
    }
