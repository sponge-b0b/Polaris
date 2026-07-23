from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

import pytest

from application.persistence.news import NewsPersistenceService
from application.projections.workflow_outputs.projection_identity import (
    build_workflow_output_projection_lineage,
)
from application.projections.workflow_outputs.projection_models import (
    WorkflowOutputProjectionStatus,
    WorkflowOutputProjectorRequest,
)
from application.projections.workflow_outputs.projectors import (
    NEWS_ANALYSIS_PROJECTOR_NAME,
    NewsAnalysisWorkflowOutputProjector,
    build_news_analysis_projector_registration,
)
from core.storage.persistence.completed_run_archive import (
    CompletedNodeOutputRecord,
    CompletedRunExecutionMode,
    CompletedRunRecord,
    JsonObject,
)
from core.storage.persistence.news import (
    NewsPersistenceBundle,
    NewsPersistenceRepository,
    NewsPersistenceResult,
)
from domain.workflow_outputs import (
    NEWS_ANALYSIS_OUTPUT_CONTRACT,
    WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
)


@pytest.mark.asyncio
async def test_news_projector_persists_snapshot_and_eligible_articles() -> None:
    repository = _FakeNewsRepository()
    projector = NewsAnalysisWorkflowOutputProjector(
        NewsPersistenceService(cast(NewsPersistenceRepository, repository)),
    )

    outcome = await projector.project(_projector_request())

    assert outcome.status is WorkflowOutputProjectionStatus.SUCCEEDED
    assert outcome.projector_name == NEWS_ANALYSIS_PROJECTOR_NAME
    assert outcome.records_written == 2
    assert len(repository.bundles) == 1

    bundle = repository.bundles[0]
    assert len(bundle.articles) == 1
    assert len(bundle.analysis_snapshots) == 1

    article = bundle.articles[0]
    assert article.source == "Reuters"
    assert article.external_id == "article-1"
    assert article.title == "Fed signals policy patience"
    assert article.published_timestamp == datetime(2026, 7, 10, 12, tzinfo=UTC)
    assert article.symbols == ("SPY",)
    assert article.themes == ("fed_policy", "rates")
    assert article.headline_score == 0.8
    assert article.relevance_score == 0.9
    assert article.sentiment_score == 0.25
    assert article.metadata["source_fingerprint"] == "fingerprint-1"
    assert article.lineage.node_name == "news_agent"

    snapshot = bundle.analysis_snapshots[0]
    assert snapshot.timestamp == datetime(2026, 7, 10, 13, 30, tzinfo=UTC)
    assert snapshot.source == "NewsService"
    assert snapshot.article_ids == (article.article_id,)
    assert snapshot.symbols == ("SPY",)
    assert snapshot.themes == ("fed_policy", "rates")
    assert snapshot.sentiment_score == 0.6
    assert snapshot.impact_score == 0.6
    assert snapshot.confidence == 0.75
    assert snapshot.llm_summary == "Policy expectations remain constructive."
    assert snapshot.full_llm_response is not None
    assert "Policy expectations" in snapshot.full_llm_response


@pytest.mark.asyncio
async def test_news_projector_persists_snapshot_without_unqualified_articles() -> None:
    repository = _FakeNewsRepository()
    projector = NewsAnalysisWorkflowOutputProjector(
        NewsPersistenceService(cast(NewsPersistenceRepository, repository)),
    )
    outputs = dict(_news_outputs())
    outputs["news_articles"] = [
        {
            "title": "Missing identity",
            "source": "Reuters",
            "published_at": "2026-07-10T12:00:00+00:00",
        }
    ]

    outcome = await projector.project(
        _projector_request(outputs=cast(JsonObject, outputs))
    )

    assert outcome.status is WorkflowOutputProjectionStatus.SUCCEEDED
    assert outcome.records_written == 1
    assert repository.bundles[0].articles == ()
    assert len(repository.bundles[0].analysis_snapshots) == 1


@pytest.mark.asyncio
async def test_news_projector_skips_snapshot_for_degraded_output_but_persists_articles() -> (  # noqa: E501
    None
):
    repository = _FakeNewsRepository()
    projector = NewsAnalysisWorkflowOutputProjector(
        NewsPersistenceService(cast(NewsPersistenceRepository, repository)),
    )

    outcome = await projector.project(_projector_request(quality_status="degraded"))

    assert outcome.status is WorkflowOutputProjectionStatus.SUCCEEDED
    assert outcome.records_written == 1
    assert len(repository.bundles[0].articles) == 1
    assert repository.bundles[0].analysis_snapshots == ()


@pytest.mark.asyncio
async def test_news_projector_skips_without_first_class_timestamp() -> None:
    repository = _FakeNewsRepository()
    projector = NewsAnalysisWorkflowOutputProjector(
        NewsPersistenceService(cast(NewsPersistenceRepository, repository)),
    )
    outputs = dict(_news_outputs())
    outputs.pop("observed_at")

    outcome = await projector.project(
        _projector_request(outputs=cast(JsonObject, outputs))
    )

    assert outcome.status is WorkflowOutputProjectionStatus.SKIPPED
    assert outcome.records_written == 0
    assert repository.bundles == []
    assert "observed_at" in (outcome.message or "")


def test_build_news_projector_registration_uses_canonical_contract() -> None:
    registration = build_news_analysis_projector_registration(
        NewsPersistenceService(cast(NewsPersistenceRepository, _FakeNewsRepository())),
    )

    assert registration.projector_name == NEWS_ANALYSIS_PROJECTOR_NAME
    assert registration.output_contract == NEWS_ANALYSIS_OUTPUT_CONTRACT
    assert registration.output_schema_version == WORKFLOW_OUTPUT_SCHEMA_VERSION_V1
    assert registration.supported_node_names == ("news_agent",)


class _FakeNewsRepository:
    def __init__(self) -> None:
        self.bundles: list[NewsPersistenceBundle] = []

    async def persist_news_bundle(
        self,
        bundle: NewsPersistenceBundle,
    ) -> NewsPersistenceResult:
        self.bundles.append(bundle)
        primary_record_id = (
            bundle.analysis_snapshots[0].analysis_snapshot_id
            if bundle.analysis_snapshots
            else bundle.articles[0].article_id
        )
        return NewsPersistenceResult.succeeded(
            primary_record_id=primary_record_id,
            records_persisted=len(bundle.articles) + len(bundle.analysis_snapshots),
        )


def _projector_request(
    *,
    outputs: JsonObject | None = None,
    quality_status: str = "normal",
) -> WorkflowOutputProjectorRequest:
    run = _run()
    node_output = _node(outputs=outputs, quality_status=quality_status)
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
    quality_status: str = "normal",
) -> CompletedNodeOutputRecord:
    return CompletedNodeOutputRecord(
        node_output_id="node-output-1",
        run_id="run-1",
        workflow_name="morning_report",
        execution_id="exec-1",
        node_name="news_agent",
        node_type="market_news",
        output_contract=NEWS_ANALYSIS_OUTPUT_CONTRACT,
        output_schema_version=WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
        status="succeeded",
        success=True,
        outputs=outputs or _news_outputs(),
        metadata={"quality_status": quality_status},
        errors_json=(),
        started_at=datetime(2026, 7, 10, 13, 29, tzinfo=UTC),
        completed_at=datetime(2026, 7, 10, 13, 31, tzinfo=UTC),
        duration_seconds=120.0,
    )


def _news_outputs() -> JsonObject:
    return {
        "observed_at": "2026-07-10T13:30:00+00:00",
        "news_source": "NewsService",
        "symbol": "SPY",
        "query": "SPY OR Fed",
        "news_articles": [
            {
                "id": "article-1",
                "title": "Fed signals policy patience",
                "summary": "Officials emphasized data dependence.",
                "source": "Reuters",
                "url": "https://example.test/fed-policy",
                "published_at": "2026-07-10T12:00:00+00:00",
                "headline_score": 0.8,
                "relevance_score": 0.9,
                "sentiment_hint": 0.25,
                "raw": {"vendor_id": "article-1"},
            },
            {
                "id": "article-2",
                "title": "Missing timestamp",
                "source": "Reuters",
            },
        ],
        "directional_score": 0.6,
        "confidence": 0.75,
        "regime": "bullish",
        "signals": ["liquidity_support"],
        "risks": ["event_risk"],
        "recommendations": ["monitor_rates"],
        "features": {
            "headline_count": 2,
            "market_relevance": "bullish",
            "primary_themes": ["fed_policy", "rates"],
            "query": "SPY OR Fed",
        },
        "llm_response": {
            "summary": "Policy expectations remain constructive.",
            "themes": ["fed_policy", "rates"],
            "market_relevance": "bullish",
        },
    }
