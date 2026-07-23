from __future__ import annotations

from datetime import UTC, datetime

from core.database.models.attribution import (
    AttributionRecordModel,
    RecommendationAttributionModel,
    SignalAttributionModel,
)
from core.storage.persistence.attribution import (
    AttributionRecord,
    RecommendationAttributionRecord,
    SignalAttributionRecord,
)
from core.storage.persistence.lineage import (
    PersistenceLineage,
    PersistenceRecordIdentity,
)
from core.storage.persistence.serializers.attribution_persistence_serializer import (
    AttributionPersistenceSerializer,
)

_FULL_EXPLANATION = "Full attribution explanation must not be truncated. " * 200


def test_attribution_serializer_flattens_generic_attribution_record() -> None:
    record = _attribution()

    values = AttributionPersistenceSerializer.attribution_values(record)

    assert values["attribution_id"] == "attribution-1"
    assert values["target_record_type"] == "recommendation"
    assert values["target_record_id"] == "recommendation-1"
    assert values["contribution_score"] == 0.42
    assert values["confidence"] == 0.88
    assert values["explanation"] == _FULL_EXPLANATION.strip()
    assert values["source_records"] == [
        {"record_type": "agent_signal", "record_id": "agent-signal-1"},
    ]
    assert values["workflow_name"] == "morning_report"
    assert values["execution_id"] == "exec-1"
    assert values["metadata_payload"] == {"source": "unit-test"}


def test_attribution_serializer_round_trips_generic_attribution_record() -> None:
    model = AttributionRecordModel(
        **AttributionPersistenceSerializer.attribution_values(_attribution())
    )

    record = AttributionPersistenceSerializer.attribution_from_model(model)

    assert record.attribution_id == "attribution-1"
    assert record.target_record.record_type == "recommendation"
    assert record.target_record.record_id == "recommendation-1"
    assert record.explanation == _FULL_EXPLANATION.strip()
    assert record.source_records[0].record_type == "agent_signal"
    assert record.lineage.node_name == "attribution_node"
    assert record.metadata == {"source": "unit-test"}


def test_attribution_serializer_flattens_signal_attribution_record() -> None:
    record = _signal_attribution()

    values = AttributionPersistenceSerializer.signal_attribution_values(record)

    assert values["signal_attribution_id"] == "signal-attribution-1"
    assert values["signal_id"] == "agent-signal-1"
    assert values["signal_type"] == "technical"
    assert values["symbol"] == "SPY"
    assert values["universe"] == "us_equities"
    assert values["explanation"] == _FULL_EXPLANATION.strip()
    assert values["source_records"] == [
        {"record_type": "market_context_snapshot", "record_id": "market-1"},
    ]


def test_attribution_serializer_round_trips_signal_attribution_record() -> None:
    model = SignalAttributionModel(
        **AttributionPersistenceSerializer.signal_attribution_values(
            _signal_attribution()
        )
    )

    record = AttributionPersistenceSerializer.signal_attribution_from_model(model)

    assert record.signal_attribution_id == "signal-attribution-1"
    assert record.signal_id == "agent-signal-1"
    assert record.signal_type == "technical"
    assert record.symbol == "SPY"
    assert record.explanation == _FULL_EXPLANATION.strip()
    assert record.source_records[0].record_id == "market-1"
    assert record.lineage.workflow_name == "morning_report"


def test_attribution_serializer_flattens_recommendation_attribution_record() -> None:
    record = _recommendation_attribution()

    values = AttributionPersistenceSerializer.recommendation_attribution_values(record)

    assert values["recommendation_attribution_id"] == "recommendation-attribution-1"
    assert values["recommendation_id"] == "recommendation-1"
    assert values["signal_id"] == "agent-signal-1"
    assert values["symbol"] == "QQQ"
    assert values["explanation"] == _FULL_EXPLANATION.strip()
    assert values["source_records"] == [
        {"record_type": "agent_signal", "record_id": "agent-signal-1"},
    ]


def test_attribution_serializer_round_trips_recommendation_attribution_record() -> None:
    model = RecommendationAttributionModel(
        **AttributionPersistenceSerializer.recommendation_attribution_values(
            _recommendation_attribution()
        )
    )

    record = AttributionPersistenceSerializer.recommendation_attribution_from_model(
        model
    )

    assert record.recommendation_attribution_id == "recommendation-attribution-1"
    assert record.recommendation_id == "recommendation-1"
    assert record.signal_id == "agent-signal-1"
    assert record.symbol == "QQQ"
    assert record.explanation == _FULL_EXPLANATION.strip()
    assert record.source_records[0].record_type == "agent_signal"
    assert record.lineage.execution_id == "exec-1"


def _attribution() -> AttributionRecord:
    return AttributionRecord(
        attribution_id="attribution-1",
        target_record=PersistenceRecordIdentity(
            record_type="recommendation",
            record_id="recommendation-1",
        ),
        attribution_type="recommendation_support",
        contribution_type="positive",
        contribution_score=0.42,
        confidence=0.88,
        explanation=_FULL_EXPLANATION,
        timestamp=_timestamp(),
        lineage=_lineage(),
        agent_name="StrategySynthesisAgent",
        agent_type="strategy",
        source_records=(_agent_signal_identity(),),
        metadata={"source": "unit-test"},
    )


def _signal_attribution() -> SignalAttributionRecord:
    return SignalAttributionRecord(
        signal_attribution_id="signal-attribution-1",
        signal_id="agent-signal-1",
        attribution_type="signal_evidence",
        contribution_type="positive",
        contribution_score=0.55,
        confidence=0.86,
        explanation=_FULL_EXPLANATION,
        timestamp=_timestamp(),
        lineage=_lineage(),
        signal_type="technical",
        agent_name="TechnicalAgent",
        agent_type="technical",
        symbol="spy",
        universe="us_equities",
        source_records=(
            PersistenceRecordIdentity(
                record_type="market_context_snapshot",
                record_id="market-1",
            ),
        ),
        metadata={"source": "unit-test"},
    )


def _recommendation_attribution() -> RecommendationAttributionRecord:
    return RecommendationAttributionRecord(
        recommendation_attribution_id="recommendation-attribution-1",
        recommendation_id="recommendation-1",
        attribution_type="recommendation_evidence",
        contribution_type="positive",
        contribution_score=0.61,
        confidence=0.91,
        explanation=_FULL_EXPLANATION,
        timestamp=_timestamp(),
        lineage=_lineage(),
        signal_id="agent-signal-1",
        agent_name="PortfolioManagerAgent",
        agent_type="portfolio",
        symbol="qqq",
        universe="us_equities",
        source_records=(_agent_signal_identity(),),
        metadata={"source": "unit-test"},
    )


def _agent_signal_identity() -> PersistenceRecordIdentity:
    return PersistenceRecordIdentity(
        record_type="agent_signal",
        record_id="agent-signal-1",
    )


def _lineage() -> PersistenceLineage:
    return PersistenceLineage(
        workflow_name="morning_report",
        execution_id="exec-1",
        runtime_id="runtime-1",
        node_name="attribution_node",
    )


def _timestamp() -> datetime:
    return datetime(2026, 5, 31, 14, 0, tzinfo=UTC)
