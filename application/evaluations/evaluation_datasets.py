from __future__ import annotations

from dataclasses import dataclass

from application.evaluations.contracts import EvaluationDatasetRegistrationRequest
from application.evaluations.rag_evaluation_metrics import (
    intelligence_threshold_profile,
    rag_threshold_profile,
)
from core.storage.persistence.evaluation import JsonObject
from domain.evaluation import EvaluationDatasetReference, EvaluationTargetType

EVALUATION_DATASET_VERSION = "v1"

MODEL_REGRESSION_REQUIRED_COVERAGE_TAGS: tuple[str, ...] = (
    "structured_output",
    "rag_quality",
    "rag_grounding",
    "prompt_injection",
    "strategy_hypothesis",
    "strategy_synthesis",
    "recommendation_explanation",
    "execution_risk",
    "local_operations",
)


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


@dataclass(frozen=True, slots=True)
class EvaluationDatasetSliceMembership:
    """Membership for a named canonical evaluation dataset slice."""

    dataset_name: str
    case_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_non_empty(self.dataset_name, "dataset_name")
        object.__setattr__(
            self,
            "case_ids",
            _clean_tuple(self.case_ids, "case_id"),
        )
        if not self.case_ids:
            raise ValueError("case_ids cannot be empty.")


@dataclass(frozen=True, slots=True)
class EvaluationDatasetSliceDefinition:
    """Named, fixture-backed slice inside the canonical golden corpus."""

    name: str
    description: str
    memberships: tuple[EvaluationDatasetSliceMembership, ...]
    coverage_tags: tuple[str, ...]
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_non_empty(self.name, "name")
        _require_non_empty(self.description, "description")
        object.__setattr__(self, "name", self.name.strip())
        object.__setattr__(self, "description", self.description.strip())
        if not self.memberships:
            raise ValueError("memberships cannot be empty.")
        object.__setattr__(
            self,
            "coverage_tags",
            _clean_tuple(self.coverage_tags, "coverage_tag"),
        )
        if not self.coverage_tags:
            raise ValueError("coverage_tags cannot be empty.")
        object.__setattr__(self, "tags", _clean_tuple(self.tags, "tag"))

    @property
    def case_count(self) -> int:
        return sum(len(membership.case_ids) for membership in self.memberships)

    @property
    def dataset_names(self) -> tuple[str, ...]:
        return tuple(membership.dataset_name for membership in self.memberships)

    @property
    def case_ids(self) -> tuple[str, ...]:
        return tuple(
            case_id
            for membership in self.memberships
            for case_id in membership.case_ids
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


def _require_non_empty(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} cannot be empty.")


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


CANONICAL_EVALUATION_DATASET_SLICE_DEFINITIONS: tuple[
    EvaluationDatasetSliceDefinition,
    ...,
] = (
    EvaluationDatasetSliceDefinition(
        name="model_regression",
        description=(
            "Dedicated 20-30 case model-regression slice inside the canonical "
            "golden evaluation corpus for validating model/profile replacements."
        ),
        tags=("model_regression", "golden", "model_gate"),
        coverage_tags=MODEL_REGRESSION_REQUIRED_COVERAGE_TAGS,
        memberships=(
            EvaluationDatasetSliceMembership(
                dataset_name="golden_rag_questions",
                case_ids=(
                    "golden-rag-answer-001",
                    "golden-rag-answer-005",
                    "golden-rag-answer-018",
                    "golden-rag-answer-020",
                ),
            ),
            EvaluationDatasetSliceMembership(
                dataset_name="rag_citation_support",
                case_ids=(
                    "rag-citation-001",
                    "rag-citation-004",
                    "rag-citation-008",
                    "rag-citation-012",
                ),
            ),
            EvaluationDatasetSliceMembership(
                dataset_name="rag_security_prompt_injection",
                case_ids=(
                    "rag-security-injection-001",
                    "rag-security-injection-003",
                    "rag-security-injection-005",
                    "rag-security-injection-012",
                ),
            ),
            EvaluationDatasetSliceMembership(
                dataset_name="strategy_synthesis_quality",
                case_ids=(
                    "strategy-synthesis-quality-001",
                    "strategy-synthesis-quality-002",
                    "strategy-synthesis-quality-008",
                    "strategy-synthesis-quality-013",
                ),
            ),
            EvaluationDatasetSliceMembership(
                dataset_name="recommendation_explanations",
                case_ids=(
                    "recommendation-explanation-001",
                    "recommendation-explanation-004",
                    "recommendation-explanation-009",
                    "recommendation-explanation-011",
                ),
            ),
            EvaluationDatasetSliceMembership(
                dataset_name="mcp_tool_responses",
                case_ids=(
                    "mcp-tool-response-001",
                    "mcp-tool-response-003",
                ),
            ),
            EvaluationDatasetSliceMembership(
                dataset_name="agent_task_completion",
                case_ids=(
                    "agent-task-completion-002",
                    "agent-task-completion-004",
                ),
            ),
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


def canonical_evaluation_dataset_slice_definitions() -> tuple[
    EvaluationDatasetSliceDefinition,
    ...,
]:
    """Return named fixture-backed slices inside the canonical golden corpus."""

    return CANONICAL_EVALUATION_DATASET_SLICE_DEFINITIONS


def canonical_evaluation_dataset_slice_definition_by_name(
    name: str,
) -> EvaluationDatasetSliceDefinition:
    """Resolve one canonical dataset slice definition by stable slice name."""

    cleaned_name = name.strip()
    if not cleaned_name:
        raise ValueError("name cannot be empty.")
    for definition in CANONICAL_EVALUATION_DATASET_SLICE_DEFINITIONS:
        if definition.name == cleaned_name:
            return definition
    raise KeyError(cleaned_name)
