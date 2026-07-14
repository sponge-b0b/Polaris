from __future__ import annotations

from dataclasses import dataclass
from application.evaluations.contracts import EvaluationDatasetRegistrationRequest
from application.evaluations.rag_evaluation_metrics import (
    intelligence_threshold_profile,
)
from application.evaluations.rag_evaluation_metrics import rag_threshold_profile
from core.storage.persistence.evaluation import JsonObject
from domain.evaluation import EvaluationDatasetReference
from domain.evaluation import EvaluationTargetType

EVALUATION_DATASET_VERSION = "v1"


@dataclass(frozen=True, slots=True)
class EvaluationDatasetDefinition:
    """Canonical, versioned Polaris evaluation dataset definition."""

    reference: EvaluationDatasetReference
    target_type: EvaluationTargetType
    description: str
    threshold_profile: JsonObject | None = None
    source_lineage: tuple[str, ...] = ()
    deterministic_fixture_uri: str | None = None
    active: bool = True

    def __post_init__(self) -> None:
        if not self.description.strip():
            raise ValueError("description cannot be empty.")
        object.__setattr__(self, "description", self.description.strip())
        object.__setattr__(
            self,
            "source_lineage",
            _clean_tuple(self.source_lineage, "source_lineage_entry"),
        )
        if self.deterministic_fixture_uri is not None:
            fixture_uri = self.deterministic_fixture_uri.strip()
            if not fixture_uri:
                raise ValueError("deterministic_fixture_uri cannot be empty.")
            object.__setattr__(self, "deterministic_fixture_uri", fixture_uri)

    def to_registration_request(self) -> EvaluationDatasetRegistrationRequest:
        return EvaluationDatasetRegistrationRequest(
            reference=self.reference,
            target_type=self.target_type,
            description=self.description,
            source_lineage=self.source_lineage,
            deterministic_fixture_uri=self.deterministic_fixture_uri,
            threshold_profile=self.threshold_profile,
            active=self.active,
        )


def _reference(name: str, tags: tuple[str, ...]) -> EvaluationDatasetReference:
    return EvaluationDatasetReference(
        dataset_id=f"{name}_{EVALUATION_DATASET_VERSION}",
        name=name,
        version=EVALUATION_DATASET_VERSION,
        tags=tags,
    )


def _clean_tuple(values: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    cleaned = tuple(value.strip() for value in values if value.strip())
    if len(cleaned) != len(values):
        raise ValueError(f"{field_name} cannot be empty.")
    return cleaned


RAG_THRESHOLD_PROFILE = rag_threshold_profile()
INTELLIGENCE_THRESHOLD_PROFILE = intelligence_threshold_profile()

CANONICAL_EVALUATION_DATASET_DEFINITIONS: tuple[
    EvaluationDatasetDefinition,
    ...,
] = (
    EvaluationDatasetDefinition(
        reference=_reference(
            "golden_rag_questions",
            ("rag", "golden", "quality"),
        ),
        target_type=EvaluationTargetType.RAG_ANSWER,
        description=(
            "Golden RAG answer cases sourced from curated Polaris records and "
            "designed to verify grounded answer quality."
        ),
        threshold_profile=RAG_THRESHOLD_PROFILE,
        source_lineage=(
            "postgres.rag_documents",
            "postgres.rag_chunks",
            "postgres.completed_workflow_runs",
        ),
        deterministic_fixture_uri=(
            "tests/evaluation/fixtures/golden_rag_questions.jsonl"
        ),
    ),
    EvaluationDatasetDefinition(
        reference=_reference(
            "rag_citation_support",
            ("rag", "citations", "grounding"),
        ),
        target_type=EvaluationTargetType.RAG_ANSWER,
        description=(
            "Citation-support cases that validate whether generated answers are "
            "materially supported by retrieved chunks and citation identifiers."
        ),
        threshold_profile=RAG_THRESHOLD_PROFILE,
        source_lineage=(
            "postgres.rag_documents",
            "postgres.rag_chunks",
            "postgres.rag_document_citations",
        ),
        deterministic_fixture_uri=(
            "tests/evaluation/fixtures/rag_citation_support.jsonl"
        ),
    ),
    EvaluationDatasetDefinition(
        reference=_reference(
            "rag_security_prompt_injection",
            ("rag", "security", "prompt_injection"),
        ),
        target_type=EvaluationTargetType.RAG_ANSWER,
        description=(
            "Adversarial RAG cases that validate resistance to prompt-injection "
            "attempts embedded in user input or retrieved context."
        ),
        threshold_profile=RAG_THRESHOLD_PROFILE,
        source_lineage=(
            "postgres.rag_documents",
            "external.security_fixtures",
        ),
        deterministic_fixture_uri=(
            "tests/evaluation/fixtures/rag_security_prompt_injection.jsonl"
        ),
    ),
    EvaluationDatasetDefinition(
        reference=_reference(
            "morning_report_quality",
            ("morning_report", "report", "quality"),
        ),
        target_type=EvaluationTargetType.MORNING_REPORT,
        description=(
            "Morning-report quality cases that evaluate professional structure, "
            "clarity, attribution, and decision-useful portfolio context."
        ),
        threshold_profile=INTELLIGENCE_THRESHOLD_PROFILE,
        source_lineage=(
            "postgres.completed_workflow_runs",
            "postgres.curated_report_records",
        ),
        deterministic_fixture_uri=(
            "tests/evaluation/fixtures/morning_report_quality.jsonl"
        ),
    ),
    EvaluationDatasetDefinition(
        reference=_reference(
            "strategy_synthesis_quality",
            ("strategy", "synthesis", "quality"),
        ),
        target_type=EvaluationTargetType.STRATEGY_SYNTHESIS,
        description=(
            "Strategy-synthesis cases that verify perspective weighting, rationale "
            "quality, conflict handling, and risk-aware conclusions."
        ),
        threshold_profile=INTELLIGENCE_THRESHOLD_PROFILE,
        source_lineage=(
            "postgres.curated_strategy_records",
            "postgres.completed_workflow_runs",
        ),
        deterministic_fixture_uri=(
            "tests/evaluation/fixtures/strategy_synthesis_quality.jsonl"
        ),
    ),
    EvaluationDatasetDefinition(
        reference=_reference(
            "recommendation_explanations",
            ("recommendation", "explanation", "quality"),
        ),
        target_type=EvaluationTargetType.RECOMMENDATION_EXPLANATION,
        description=(
            "Recommendation-explanation cases that verify rationale clarity, "
            "supporting evidence, risk caveats, and portfolio relevance."
        ),
        threshold_profile=INTELLIGENCE_THRESHOLD_PROFILE,
        source_lineage=(
            "postgres.curated_recommendation_records",
            "postgres.completed_workflow_runs",
        ),
        deterministic_fixture_uri=(
            "tests/evaluation/fixtures/recommendation_explanations.jsonl"
        ),
    ),
    EvaluationDatasetDefinition(
        reference=_reference(
            "mcp_tool_responses",
            ("mcp", "tool_response", "transport"),
        ),
        target_type=EvaluationTargetType.MCP_TOOL_RESPONSE,
        description=(
            "MCP tool-response cases that verify external transport output remains "
            "faithful to canonical Polaris application-service responses."
        ),
        threshold_profile=INTELLIGENCE_THRESHOLD_PROFILE,
        source_lineage=(
            "mcp.tool_invocations",
            "postgres.curated_records",
        ),
        deterministic_fixture_uri="tests/evaluation/fixtures/mcp_tool_responses.jsonl",
    ),
    EvaluationDatasetDefinition(
        reference=_reference(
            "agent_task_completion",
            ("agent", "task_completion", "quality"),
        ),
        target_type=EvaluationTargetType.AGENT_TASK,
        description=(
            "Agent task-completion cases that evaluate whether internal or customer "
            "agents satisfy requested outcomes using supported Polaris evidence."
        ),
        threshold_profile=INTELLIGENCE_THRESHOLD_PROFILE,
        source_lineage=(
            "postgres.completed_workflow_runs",
            "postgres.curated_intelligence_records",
        ),
        deterministic_fixture_uri=(
            "tests/evaluation/fixtures/agent_task_completion.jsonl"
        ),
    ),
)


def canonical_evaluation_dataset_definitions(
    *,
    target_type: EvaluationTargetType | None = None,
) -> tuple[EvaluationDatasetDefinition, ...]:
    """Return canonical dataset definitions, optionally filtered by target type."""

    if target_type is None:
        return CANONICAL_EVALUATION_DATASET_DEFINITIONS
    return tuple(
        definition
        for definition in CANONICAL_EVALUATION_DATASET_DEFINITIONS
        if definition.target_type is target_type
    )


def canonical_evaluation_dataset_registration_requests(
    *,
    target_type: EvaluationTargetType | None = None,
) -> tuple[EvaluationDatasetRegistrationRequest, ...]:
    """Return registration requests for all canonical dataset definitions."""

    return tuple(
        definition.to_registration_request()
        for definition in canonical_evaluation_dataset_definitions(
            target_type=target_type,
        )
    )


def canonical_evaluation_dataset_definition_by_name(
    name: str,
) -> EvaluationDatasetDefinition:
    """Resolve one canonical dataset definition by its stable dataset name."""

    cleaned_name = name.strip()
    if not cleaned_name:
        raise ValueError("name cannot be empty.")
    for definition in CANONICAL_EVALUATION_DATASET_DEFINITIONS:
        if definition.reference.name == cleaned_name:
            return definition
    raise KeyError(cleaned_name)
