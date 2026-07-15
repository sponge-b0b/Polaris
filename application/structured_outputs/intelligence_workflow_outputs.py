from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import StringConstraints
from pydantic import field_validator
from pydantic import model_validator

from application.reports.morning_report_models import ReportBullet
from application.reports.morning_report_models import ReportSection
from core.storage.persistence.lineage import JsonObject
from core.storage.persistence.lineage import PersistenceLineage
from core.storage.persistence.recommendations import RecommendationRationaleRecord
from intelligence.strategy.hypothesis.contracts import StrategyPerspective
from intelligence.strategy.hypothesis.contracts import parse_strategy_perspective
from intelligence.strategy.synthesis.contracts import StrategyHypothesisEvaluation
from intelligence.strategy.synthesis.contracts import StrategySynthesisDecision
from intelligence.strategy.synthesis.contracts import StrategySynthesisDegradedReason
from intelligence.strategy.synthesis.contracts import StrategySynthesisSelectionStatus

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Score = Annotated[float, Field(ge=0.0, le=1.0)]
DirectionalScore = Annotated[float, Field(ge=-1.0, le=1.0)]


class StructuredWorkflowOutputModel(BaseModel):
    """Strict base schema for Instructor-backed intelligence workflow output."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class StructuredStrategyHypothesisEvaluation(StructuredWorkflowOutputModel):
    """Schema-enforced synthesis evaluation for one strategy perspective."""

    perspective: NonEmptyString
    perspective_weight: Score
    contradiction_burden: Score
    assumption_support: Score
    invalidated: bool
    candidate_score: Score
    synthesis_weight: Score
    rank: int = Field(ge=1)
    selection_status: StrategySynthesisSelectionStatus
    degraded_reasons: tuple[StrategySynthesisDegradedReason, ...] = ()

    @field_validator("perspective")
    @classmethod
    def _validate_perspective(cls, value: str) -> str:
        return parse_strategy_perspective(value).value

    def to_domain(self) -> StrategyHypothesisEvaluation:
        """Map the structured LLM payload into the canonical domain object."""

        return StrategyHypothesisEvaluation(
            perspective=parse_strategy_perspective(self.perspective),
            perspective_weight=self.perspective_weight,
            contradiction_burden=self.contradiction_burden,
            assumption_support=self.assumption_support,
            invalidated=self.invalidated,
            candidate_score=self.candidate_score,
            synthesis_weight=self.synthesis_weight,
            rank=self.rank,
            selection_status=self.selection_status,
            degraded_reasons=self.degraded_reasons,
        )


class StructuredStrategySynthesisOutput(StructuredWorkflowOutputModel):
    """Instructor target schema for strategy synthesis narrative output."""

    selected_perspective: NonEmptyString | None = None
    selection_status: StrategySynthesisSelectionStatus
    directional_score: DirectionalScore
    confidence: Score
    regime: NonEmptyString
    uncertainty: Score
    evaluations: tuple[StructuredStrategyHypothesisEvaluation, ...]
    degraded_reasons: tuple[StrategySynthesisDegradedReason, ...] = ()
    thesis: NonEmptyString
    signals: tuple[NonEmptyString, ...] = ()
    risks: tuple[NonEmptyString, ...] = ()
    recommendations: tuple[NonEmptyString, ...] = ()

    @field_validator("selected_perspective")
    @classmethod
    def _validate_selected_perspective(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return parse_strategy_perspective(value).value

    @model_validator(mode="after")
    def validate_selected_evaluation(self) -> StructuredStrategySynthesisOutput:
        if self.selection_status is StrategySynthesisSelectionStatus.SELECTED:
            if self.selected_perspective is None:
                raise ValueError(
                    "selected_perspective is required for selected output."
                )
            selected = tuple(
                evaluation
                for evaluation in self.evaluations
                if evaluation.selection_status
                is StrategySynthesisSelectionStatus.SELECTED
            )
            if len(selected) != 1:
                raise ValueError("exactly one selected evaluation is required.")
            if selected[0].perspective != self.selected_perspective:
                raise ValueError(
                    "selected_perspective must match the selected evaluation."
                )
        return self

    def to_domain_decision(self) -> StrategySynthesisDecision:
        """Map the structured payload into the canonical synthesis decision."""

        selected_perspective: StrategyPerspective | None = None
        if self.selected_perspective is not None:
            selected_perspective = parse_strategy_perspective(self.selected_perspective)
        return StrategySynthesisDecision(
            selected_perspective=selected_perspective,
            selection_status=self.selection_status,
            directional_score=self.directional_score,
            confidence=self.confidence,
            regime=self.regime,
            uncertainty=self.uncertainty,
            evaluations=tuple(
                evaluation.to_domain() for evaluation in self.evaluations
            ),
            degraded_reasons=self.degraded_reasons,
            thesis=self.thesis,
            signals=self.signals,
            risks=self.risks,
            recommendations=self.recommendations,
        )


class StructuredRecommendationExplanation(StructuredWorkflowOutputModel):
    """Instructor target schema for attributable recommendation explanations."""

    rationale_type: NonEmptyString
    explanation_text: NonEmptyString
    supporting_source_ids: tuple[NonEmptyString, ...] = ()
    confidence: Score
    limitations: tuple[NonEmptyString, ...] = ()

    def to_rationale_record(
        self,
        *,
        rationale_id: str,
        recommendation_id: str,
        created_at: datetime,
        lineage: PersistenceLineage | None = None,
    ) -> RecommendationRationaleRecord:
        """Map the structured explanation into the canonical rationale record."""

        metadata: JsonObject = {
            "supporting_source_ids": list(self.supporting_source_ids),
            "limitations": list(self.limitations),
        }
        return RecommendationRationaleRecord(
            rationale_id=rationale_id,
            recommendation_id=recommendation_id,
            rationale_type=self.rationale_type,
            rationale_text=self.explanation_text,
            created_at=created_at,
            lineage=PersistenceLineage() if lineage is None else lineage,
            confidence=self.confidence,
            metadata=metadata,
        )


class StructuredMorningReportSection(StructuredWorkflowOutputModel):
    """Instructor target schema for one generated morning-report section."""

    title: NonEmptyString
    summary: NonEmptyString
    bullets: tuple[NonEmptyString, ...] = ()
    risks: tuple[NonEmptyString, ...] = ()
    recommendations: tuple[NonEmptyString, ...] = ()

    def to_report_section(self) -> ReportSection:
        """Map the structured payload into the existing report section model."""

        return ReportSection(
            title=self.title,
            summary=self.summary,
            bullets=tuple(ReportBullet(text=bullet) for bullet in self.bullets),
            risks=tuple(ReportBullet(text=risk) for risk in self.risks),
            recommendations=tuple(
                ReportBullet(text=recommendation)
                for recommendation in self.recommendations
            ),
        )
