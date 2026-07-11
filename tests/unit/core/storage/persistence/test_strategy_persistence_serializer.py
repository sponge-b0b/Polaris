from __future__ import annotations

from core.database.models.strategy import StrategyHypothesisEvaluationModel
from core.database.models.strategy import StrategyHypothesisModel
from core.database.models.strategy import StrategySynthesisDecisionModel
from core.storage.persistence.serializers.strategy_persistence_serializer import (
    StrategyPersistenceSerializer,
)

from tests.unit.core.storage.persistence.strategy_fixtures import strategy_evaluation
from tests.unit.core.storage.persistence.strategy_fixtures import strategy_hypothesis
from tests.unit.core.storage.persistence.strategy_fixtures import (
    strategy_synthesis_decision,
)


def test_strategy_serializer_flattens_hypothesis_lineage_and_evidence() -> None:
    values = StrategyPersistenceSerializer.hypothesis_values(strategy_hypothesis())

    assert values["hypothesis_id"] == "hypothesis-1"
    assert values["symbol"] == "SPY"
    assert values["workflow_name"] == "morning_report"
    assert values["execution_id"] == "exec-1"
    assert values["supporting_evidence"] == [
        {
            "evidence_id": "e1",
            "source": "technical",
            "name": "trend",
            "observed_value": 0.712345678901,
        }
    ]
    assert values["metadata_payload"] == {"source_node_output_id": "node-output-1"}


def test_strategy_serializer_round_trips_complete_hypothesis_model() -> None:
    model = StrategyHypothesisModel(
        **StrategyPersistenceSerializer.hypothesis_values(strategy_hypothesis())
    )

    record = StrategyPersistenceSerializer.hypothesis_from_model(model)

    assert record.hypothesis_id == "hypothesis-1"
    assert record.symbol == "SPY"
    assert record.directional_bias == 0.612345678901
    assert record.supporting_evidence[0]["observed_value"] == 0.712345678901
    assert record.invalidation_conditions[0]["condition_id"] == "i1"
    assert record.lineage.node_name == "strategy_synthesis_agent"


def test_strategy_serializer_round_trips_decision_model_without_precision_loss() -> (
    None
):
    model = StrategySynthesisDecisionModel(
        **StrategyPersistenceSerializer.decision_values(strategy_synthesis_decision())
    )

    record = StrategyPersistenceSerializer.decision_from_model(model)

    assert record.decision_id == "decision-1"
    assert record.directional_score == 0.584567890123
    assert record.uncertainty == 0.235432109877
    assert record.signals == ("breadth_supportive", "trend_positive")
    assert record.metadata == {"decision_source": "strategy_synthesis"}


def test_strategy_serializer_round_trips_evaluation_lineage() -> None:
    model = StrategyHypothesisEvaluationModel(
        **StrategyPersistenceSerializer.evaluation_values(strategy_evaluation())
    )

    record = StrategyPersistenceSerializer.evaluation_from_model(model)

    assert record.evaluation_id == "decision-1:evaluation:bull"
    assert record.decision_id == "decision-1"
    assert record.hypothesis_id == "hypothesis-1"
    assert record.synthesis_weight == 0.684567890123
    assert record.degraded_reasons == ("market_events_partial",)
    assert record.lineage.execution_id == "exec-1"
