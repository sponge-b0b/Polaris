from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime
from datetime import timezone

import pytest

from core.storage.persistence.attribution import AttributionPersistenceBundle
from core.storage.persistence.attribution import AttributionPersistenceResult
from core.storage.persistence.attribution import AttributionRecord
from core.storage.persistence.attribution import RecommendationAttributionRecord
from core.storage.persistence.attribution import SignalAttributionRecord
from core.storage.persistence.attribution import new_attribution_record_id
from core.storage.persistence.attribution import new_recommendation_attribution_id
from core.storage.persistence.attribution import new_signal_attribution_id
from core.storage.persistence.lineage import PersistenceLineage
from core.storage.persistence.lineage import PersistenceRecordIdentity

_TIMESTAMP = datetime(2026, 5, 31, 14, 0, tzinfo=timezone.utc)
_SIGNAL_ID = "agent-signal-1"
_RECOMMENDATION_ID = "recommendation-1"
_FULL_EXPLANATION = "Full attribution explanation must not be truncated. " * 200


def test_attribution_record_is_typed_immutable_and_preserves_full_explanation() -> None:
    record = AttributionRecord(
        attribution_id="attribution-1",
        target_record=PersistenceRecordIdentity(
            record_type="recommendation",
            record_id=_RECOMMENDATION_ID,
        ),
        attribution_type="source_contribution",
        contribution_type="positive_driver",
        contribution_score=0.72,
        confidence=0.84,
        explanation=_FULL_EXPLANATION,
        timestamp=_TIMESTAMP,
        lineage=_lineage(),
        agent_name=" StrategySynthesisAgent ",
        agent_type=" strategy ",
        source_records=(_source_record(),),
        metadata={"source": "unit-test"},
    )

    assert record.attribution_id == "attribution-1"
    assert record.agent_name == "StrategySynthesisAgent"
    assert record.agent_type == "strategy"
    assert record.explanation == _FULL_EXPLANATION.strip()
    assert len(record.explanation) == len(_FULL_EXPLANATION.strip())
    assert record.source_records == (_source_record(),)
    assert record.lineage.execution_id == "exec-1"

    with pytest.raises(FrozenInstanceError):
        record.contribution_score = 0.1  # type: ignore[misc]


def test_signal_attribution_record_normalizes_scope_and_source_links() -> None:
    record = SignalAttributionRecord(
        signal_attribution_id="signal-attribution-1",
        signal_id=f" {_SIGNAL_ID} ",
        attribution_type="input_driver",
        contribution_type="technical_momentum",
        contribution_score=0.64,
        confidence=0.79,
        explanation=" Momentum signal drove the bullish score. ",
        timestamp=_TIMESTAMP,
        lineage=_lineage(),
        signal_type=" technical ",
        agent_name=" TechnicalAgent ",
        agent_type=" technical ",
        symbol=" spy ",
        universe=" us_equities ",
        source_records=(_source_record(),),
    )

    assert record.signal_id == _SIGNAL_ID
    assert record.signal_type == "technical"
    assert record.agent_name == "TechnicalAgent"
    assert record.agent_type == "technical"
    assert record.symbol == "SPY"
    assert record.universe == "us_equities"
    assert record.explanation == "Momentum signal drove the bullish score."


def test_recommendation_attribution_record_normalizes_signal_and_scope() -> None:
    record = RecommendationAttributionRecord(
        recommendation_attribution_id="recommendation-attribution-1",
        recommendation_id=f" {_RECOMMENDATION_ID} ",
        attribution_type="signal_driver",
        contribution_type="risk_adjusted_support",
        contribution_score=0.45,
        confidence=0.81,
        explanation=_FULL_EXPLANATION,
        timestamp=_TIMESTAMP,
        lineage=_lineage(),
        signal_id=f" {_SIGNAL_ID} ",
        agent_name=" PortfolioManagerAgent ",
        agent_type=" portfolio ",
        symbol=" qqq ",
        universe=" nasdaq100 ",
        source_records=(_signal_record(), _source_record()),
    )

    assert record.recommendation_id == _RECOMMENDATION_ID
    assert record.signal_id == _SIGNAL_ID
    assert record.agent_name == "PortfolioManagerAgent"
    assert record.agent_type == "portfolio"
    assert record.symbol == "QQQ"
    assert record.universe == "nasdaq100"
    assert len(record.source_records) == 2
    assert record.explanation == _FULL_EXPLANATION.strip()


@pytest.mark.parametrize(
    ("kwargs", "field_name"),
    [
        ({"attribution_id": " "}, "attribution_id"),
        ({"attribution_type": " "}, "attribution_type"),
        ({"contribution_type": " "}, "contribution_type"),
        ({"contribution_score": -1.1}, "contribution_score"),
        ({"confidence": 1.1}, "confidence"),
        ({"explanation": " "}, "explanation"),
        ({"source_records": ()}, "source_records"),
    ],
)
def test_attribution_record_validates_required_fields_and_scores(
    kwargs: dict[str, object],
    field_name: str,
) -> None:
    values: dict[str, object] = {
        "attribution_id": "attribution-1",
        "target_record": PersistenceRecordIdentity(
            record_type="recommendation",
            record_id=_RECOMMENDATION_ID,
        ),
        "attribution_type": "source_contribution",
        "contribution_type": "positive_driver",
        "contribution_score": 0.72,
        "confidence": 0.84,
        "explanation": "Attribution explanation.",
        "timestamp": _TIMESTAMP,
        "source_records": (_source_record(),),
    }
    values.update(kwargs)

    with pytest.raises(ValueError, match=field_name):
        AttributionRecord(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("record_type", "kwargs", "field_name"),
    [
        (
            SignalAttributionRecord,
            {"signal_attribution_id": " "},
            "signal_attribution_id",
        ),
        (
            SignalAttributionRecord,
            {"signal_id": " "},
            "signal_id",
        ),
        (
            SignalAttributionRecord,
            {"contribution_score": 1.1},
            "contribution_score",
        ),
        (
            RecommendationAttributionRecord,
            {"recommendation_attribution_id": " "},
            "recommendation_attribution_id",
        ),
        (
            RecommendationAttributionRecord,
            {"recommendation_id": " "},
            "recommendation_id",
        ),
        (
            RecommendationAttributionRecord,
            {"confidence": -0.1},
            "confidence",
        ),
    ],
)
def test_specific_attribution_records_validate_required_fields_and_scores(
    record_type: type[SignalAttributionRecord | RecommendationAttributionRecord],
    kwargs: dict[str, object],
    field_name: str,
) -> None:
    values = _specific_attribution_values(
        record_type,
    )
    values.update(kwargs)

    with pytest.raises(ValueError, match=field_name):
        record_type(**values)  # type: ignore[arg-type]


def test_attribution_bundle_groups_atomic_persistence_payload() -> None:
    bundle = AttributionPersistenceBundle(
        attribution_records=(_attribution_record(),),
        signal_attributions=(_signal_attribution(),),
        recommendation_attributions=(_recommendation_attribution(),),
    )

    assert len(bundle.attribution_records) == 1
    assert len(bundle.signal_attributions) == 1
    assert len(bundle.recommendation_attributions) == 1


def test_attribution_persistence_result_validates_state() -> None:
    success = AttributionPersistenceResult.succeeded(
        primary_record_id="attribution-1",
        records_persisted=3,
    )
    failure = AttributionPersistenceResult.failed(
        "database unavailable",
    )

    assert success.success is True
    assert success.records_persisted == 3
    assert success.primary_record_id == "attribution-1"
    assert failure.success is False
    assert failure.error == "database unavailable"

    with pytest.raises(ValueError, match="records_persisted"):
        AttributionPersistenceResult(
            success=True,
            primary_record_id="attribution-1",
            records_persisted=-1,
        )

    with pytest.raises(ValueError, match="successful"):
        AttributionPersistenceResult(
            success=True,
            primary_record_id="attribution-1",
            error="unexpected",
        )

    with pytest.raises(ValueError, match="primary_record_id"):
        AttributionPersistenceResult(
            success=True,
        )

    with pytest.raises(ValueError, match="error"):
        AttributionPersistenceResult.failed(
            " ",
        )


def test_attribution_ids_are_stable() -> None:
    target = PersistenceRecordIdentity(
        record_type="recommendation",
        record_id=_RECOMMENDATION_ID,
    )

    assert new_attribution_record_id(
        target_record=target,
        timestamp=_TIMESTAMP,
        attribution_key="primary",
    ) == (
        "attribution_record:recommendation:recommendation-1:"
        "2026-05-31T14:00:00+00:00:primary"
    )
    assert new_signal_attribution_id(
        signal_id=_SIGNAL_ID,
        timestamp=_TIMESTAMP,
        attribution_key="technical",
    ) == ("signal_attribution:agent-signal-1:2026-05-31T14:00:00+00:00:technical")
    assert new_recommendation_attribution_id(
        recommendation_id=_RECOMMENDATION_ID,
        signal_id=_SIGNAL_ID,
        timestamp=_TIMESTAMP,
        attribution_key="risk-adjusted",
    ) == (
        "recommendation_attribution:recommendation-1:agent-signal-1:"
        "2026-05-31T14:00:00+00:00:risk-adjusted"
    )

    with pytest.raises(ValueError, match="signal_id"):
        new_signal_attribution_id(
            signal_id=" ",
            timestamp=_TIMESTAMP,
        )


def _specific_attribution_values(
    record_type: type[SignalAttributionRecord | RecommendationAttributionRecord],
) -> dict[str, object]:
    common: dict[str, object] = {
        "attribution_type": "source_contribution",
        "contribution_type": "positive_driver",
        "contribution_score": 0.4,
        "confidence": 0.8,
        "explanation": "Attribution explanation.",
        "timestamp": _TIMESTAMP,
        "source_records": (_source_record(),),
    }
    if record_type is SignalAttributionRecord:
        return {
            **common,
            "signal_attribution_id": "signal-attribution-1",
            "signal_id": _SIGNAL_ID,
        }

    return {
        **common,
        "recommendation_attribution_id": "recommendation-attribution-1",
        "recommendation_id": _RECOMMENDATION_ID,
    }


def _attribution_record() -> AttributionRecord:
    return AttributionRecord(
        attribution_id="attribution-1",
        target_record=PersistenceRecordIdentity(
            record_type="recommendation",
            record_id=_RECOMMENDATION_ID,
        ),
        attribution_type="source_contribution",
        contribution_type="positive_driver",
        contribution_score=0.72,
        confidence=0.84,
        explanation=_FULL_EXPLANATION,
        timestamp=_TIMESTAMP,
        lineage=_lineage(),
        agent_name="StrategySynthesisAgent",
        agent_type="strategy",
        source_records=(_source_record(),),
    )


def _signal_attribution() -> SignalAttributionRecord:
    return SignalAttributionRecord(
        signal_attribution_id="signal-attribution-1",
        signal_id=_SIGNAL_ID,
        attribution_type="source_contribution",
        contribution_type="technical_momentum",
        contribution_score=0.64,
        confidence=0.79,
        explanation="Momentum signal drove the bullish score.",
        timestamp=_TIMESTAMP,
        lineage=_lineage(),
        source_records=(_source_record(),),
    )


def _recommendation_attribution() -> RecommendationAttributionRecord:
    return RecommendationAttributionRecord(
        recommendation_attribution_id="recommendation-attribution-1",
        recommendation_id=_RECOMMENDATION_ID,
        attribution_type="signal_contribution",
        contribution_type="risk_adjusted_support",
        contribution_score=0.45,
        confidence=0.81,
        explanation=_FULL_EXPLANATION,
        timestamp=_TIMESTAMP,
        lineage=_lineage(),
        signal_id=_SIGNAL_ID,
        source_records=(_signal_record(), _source_record()),
    )


def _source_record() -> PersistenceRecordIdentity:
    return PersistenceRecordIdentity(
        record_type="market_context_snapshot",
        record_id="market-context-1",
    )


def _signal_record() -> PersistenceRecordIdentity:
    return PersistenceRecordIdentity(
        record_type="agent_signal",
        record_id=_SIGNAL_ID,
    )


def _lineage() -> PersistenceLineage:
    return PersistenceLineage(
        workflow_name="morning_report",
        execution_id="exec-1",
        runtime_id="runtime-1",
        node_name="attribution_node",
    )
