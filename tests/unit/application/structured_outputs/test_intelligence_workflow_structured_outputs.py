from __future__ import annotations

from datetime import UTC
from datetime import datetime

import pytest
from pydantic import ValidationError

from application.structured_outputs import StructuredMorningReportSection
from application.structured_outputs import StructuredRecommendationExplanation
from application.structured_outputs import StructuredStrategyHypothesisEvaluation
from application.structured_outputs import StructuredStrategySynthesisOutput
from intelligence.strategy.hypothesis.contracts import StrategyPerspective
from intelligence.strategy.synthesis.contracts import StrategySynthesisSelectionStatus


def test_strategy_synthesis_structured_output_maps_to_canonical_decision() -> None:
    output = StructuredStrategySynthesisOutput(
        selected_perspective="bull",
        selection_status=StrategySynthesisSelectionStatus.SELECTED,
        directional_score=0.42,
        confidence=0.81,
        regime="constructive",
        uncertainty=0.19,
        evaluations=(
            StructuredStrategyHypothesisEvaluation(
                perspective="bull",
                perspective_weight=0.5,
                contradiction_burden=0.1,
                assumption_support=0.9,
                invalidated=False,
                candidate_score=0.88,
                synthesis_weight=0.7,
                rank=1,
                selection_status=StrategySynthesisSelectionStatus.SELECTED,
            ),
            StructuredStrategyHypothesisEvaluation(
                perspective="bear",
                perspective_weight=0.25,
                contradiction_burden=0.6,
                assumption_support=0.4,
                invalidated=False,
                candidate_score=0.4,
                synthesis_weight=0.2,
                rank=2,
                selection_status=StrategySynthesisSelectionStatus.REJECTED,
            ),
            StructuredStrategyHypothesisEvaluation(
                perspective="sideways",
                perspective_weight=0.25,
                contradiction_burden=0.4,
                assumption_support=0.5,
                invalidated=False,
                candidate_score=0.35,
                synthesis_weight=0.1,
                rank=3,
                selection_status=StrategySynthesisSelectionStatus.REJECTED,
            ),
        ),
        thesis="Bullish hypothesis has the best evidence-adjusted support.",
        signals=("breadth_support",),
        risks=("event_risk",),
        recommendations=("Maintain disciplined upside exposure.",),
    )

    decision = output.to_domain_decision()

    assert decision.selected_perspective is StrategyPerspective.BULL
    assert decision.selection_status is StrategySynthesisSelectionStatus.SELECTED
    assert decision.thesis == output.thesis
    assert decision.recommendations == output.recommendations
    assert len(decision.evaluations) == 3


def test_strategy_synthesis_structured_output_rejects_ambiguous_selection() -> None:
    with pytest.raises(ValidationError, match="exactly one selected evaluation"):
        StructuredStrategySynthesisOutput(
            selected_perspective="bull",
            selection_status=StrategySynthesisSelectionStatus.SELECTED,
            directional_score=0.2,
            confidence=0.7,
            regime="constructive",
            uncertainty=0.3,
            evaluations=(
                StructuredStrategyHypothesisEvaluation(
                    perspective="bull",
                    perspective_weight=1.0,
                    contradiction_burden=0.1,
                    assumption_support=0.9,
                    invalidated=False,
                    candidate_score=0.9,
                    synthesis_weight=1.0,
                    rank=1,
                    selection_status=StrategySynthesisSelectionStatus.REJECTED,
                ),
            ),
            thesis="Ambiguous selection should fail schema validation.",
        )


def test_recommendation_explanation_maps_to_attributable_rationale_record() -> None:
    explanation = StructuredRecommendationExplanation(
        rationale_type="trade_recommendation",
        explanation_text="The setup is attractive because trend and risk agree.",
        supporting_source_ids=("strategy-record-1", "risk-record-2"),
        confidence=0.77,
        limitations=("Monitor liquidity.",),
    )

    record = explanation.to_rationale_record(
        rationale_id="rationale-1",
        recommendation_id="recommendation-1",
        created_at=datetime(2026, 7, 15, tzinfo=UTC),
    )

    assert record.rationale_type == "trade_recommendation"
    assert record.rationale_text == explanation.explanation_text
    assert record.confidence == explanation.confidence
    assert record.metadata["supporting_source_ids"] == [
        "strategy-record-1",
        "risk-record-2",
    ]
    assert record.metadata["limitations"] == ["Monitor liquidity."]


def test_morning_report_structured_section_maps_to_report_section() -> None:
    structured = StructuredMorningReportSection(
        title="Technical Setup",
        summary="Trend is constructive but breadth is mixed.",
        bullets=("Price remains above the primary moving average.",),
        risks=("Breadth divergence remains a risk.",),
        recommendations=("Use staged entries.",),
    )

    section = structured.to_report_section()

    assert section.title == "Technical Setup"
    assert section.summary == structured.summary
    assert tuple(bullet.text for bullet in section.bullets) == structured.bullets
    assert tuple(risk.text for risk in section.risks) == structured.risks
    assert (
        tuple(item.text for item in section.recommendations)
        == structured.recommendations
    )


def test_workflow_structured_outputs_reject_generic_extra_payloads() -> None:
    with pytest.raises(ValidationError, match="Extra inputs"):
        StructuredMorningReportSection.model_validate(
            {
                "title": "Executive Summary",
                "summary": "Summary text.",
                "legacy_payload": {"freeform": True},
            }
        )
