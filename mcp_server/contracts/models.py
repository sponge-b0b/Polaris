"""Typed request and response contracts for the Polaris MCP tool catalog."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, JsonValue, StringConstraints
from pydantic import model_validator

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Score = Annotated[float, Field(ge=0.0, le=1.0)]


class McpBoundaryModel(BaseModel):
    """Strict base contract for data crossing the MCP serialization boundary."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class McpError(McpBoundaryModel):
    """Sanitized structured error safe for an MCP consumer."""

    code: NonEmptyString
    message: NonEmptyString
    retryable: bool = False


class RagAskRequest(McpBoundaryModel):
    """Input contract for ``polaris_rag_ask``."""

    query: NonEmptyString
    symbols: tuple[NonEmptyString, ...] = ()
    source_types: tuple[NonEmptyString, ...] = ()
    source_tables: tuple[NonEmptyString, ...] = ()
    agent_names: tuple[NonEmptyString, ...] = ()
    agent_types: tuple[NonEmptyString, ...] = ()
    report_types: tuple[NonEmptyString, ...] = ()
    regimes: tuple[NonEmptyString, ...] = ()
    workflow_name: NonEmptyString | None = None
    execution_id: NonEmptyString | None = None
    runtime_id: NonEmptyString | None = None
    as_of_start: datetime | None = None
    as_of_end: datetime | None = None
    top_k: int = Field(default=8, ge=1)
    allow_web: bool = False
    include_contexts: bool = False

    @model_validator(mode="after")
    def validate_time_window(self) -> RagAskRequest:
        if (
            self.as_of_start is not None
            and self.as_of_end is not None
            and self.as_of_start > self.as_of_end
        ):
            raise ValueError("as_of_start cannot be after as_of_end.")
        return self


class RagCitation(McpBoundaryModel):
    """Canonical source lineage returned with a RAG answer."""

    source_table: NonEmptyString
    source_id: NonEmptyString
    source_type: NonEmptyString
    document_id: NonEmptyString
    title: NonEmptyString
    chunk_id: NonEmptyString | None = None
    section_name: NonEmptyString | None = None
    generated_at: datetime | None = None
    workflow_name: NonEmptyString | None = None
    execution_id: NonEmptyString | None = None
    metadata: dict[str, JsonValue] = Field(default_factory=dict)


class RagRetrievedContext(McpBoundaryModel):
    """Optional complete retrieved context returned by ``polaris_rag_ask``."""

    context_id: NonEmptyString
    text: NonEmptyString
    source: RagCitation
    score: float
    rank: int = Field(ge=0)
    retrieval_route: NonEmptyString
    metadata: dict[str, JsonValue] = Field(default_factory=dict)


class RagReflectionScores(McpBoundaryModel):
    """Self-RAG quality scores returned with a generated answer."""

    retrieval_necessity: Score
    source_relevance: Score
    answer_support: Score
    usefulness: Score


class RagAskResponse(McpBoundaryModel):
    """Output contract for ``polaris_rag_ask``."""

    query_id: NonEmptyString
    answer_text: NonEmptyString
    status: NonEmptyString
    route: NonEmptyString
    citations: tuple[RagCitation, ...] = ()
    contexts: tuple[RagRetrievedContext, ...] | None = None
    confidence_score: Score | None = None
    grounding_score: Score | None = None
    utility_score: Score | None = None
    injection_detected: bool = False
    reflection_scores: RagReflectionScores | None = None
    corrective_actions: tuple[NonEmptyString, ...] = ()
    error: str | None = None
    generated_at: datetime


class RagStatusRequest(McpBoundaryModel):
    """Input contract for ``polaris_rag_status``."""

    include_details: bool = True


class RagCanonicalReadiness(McpBoundaryModel):
    available: bool
    document_count: int | None = Field(default=None, ge=0)
    chunk_count: int | None = Field(default=None, ge=0)
    embedding_job_count: int | None = Field(default=None, ge=0)
    graph_job_count: int | None = Field(default=None, ge=0)
    pending_embedding_jobs: int | None = Field(default=None, ge=0)
    retryable_embedding_jobs: int | None = Field(default=None, ge=0)
    failed_embedding_jobs: int | None = Field(default=None, ge=0)
    error: str | None = None


class RagVectorReadiness(McpBoundaryModel):
    collection_name: NonEmptyString
    exists: bool
    healthy: bool
    dense_vector_present: bool
    sparse_vector_present: bool
    configured_vector_size: int = Field(gt=0)
    actual_vector_size: int | None = Field(default=None, gt=0)
    vector_size_compatible: bool
    points_count: int = Field(ge=0)
    status: str | None = None
    error: str | None = None


class RagGraphReadiness(McpBoundaryModel):
    connected: bool
    healthy: bool
    entity_count: int | None = Field(default=None, ge=0)
    error: str | None = None


class RagModelReadiness(McpBoundaryModel):
    component: NonEmptyString
    model: NonEmptyString
    ready: bool
    dimensions: int | None = Field(default=None, gt=0)
    error: str | None = None


class RagStatusResponse(McpBoundaryModel):
    """Output contract for ``polaris_rag_status``."""

    status: NonEmptyString
    message: NonEmptyString
    ready: bool
    canonical: RagCanonicalReadiness | None = None
    vector: RagVectorReadiness | None = None
    graph: RagGraphReadiness | None = None
    embedding: RagModelReadiness | None = None
    reranker: RagModelReadiness | None = None


class WorkflowsListRequest(McpBoundaryModel):
    """Input contract for ``polaris_workflows_list``."""

    tag: NonEmptyString | None = None
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=50, ge=1)


class WorkflowSummary(McpBoundaryModel):
    workflow_name: NonEmptyString
    description: str = ""
    tags: tuple[NonEmptyString, ...] = ()
    metadata: dict[str, JsonValue] = Field(default_factory=dict)


class WorkflowsListResponse(McpBoundaryModel):
    """Output contract for ``polaris_workflows_list``."""

    workflows: tuple[WorkflowSummary, ...]
    total_count: int = Field(ge=0)
    offset: int = Field(ge=0)
    limit: int = Field(ge=1)
    has_more: bool
    next_offset: int | None = Field(default=None, ge=0)


class WorkflowDescribeRequest(McpBoundaryModel):
    """Input contract for ``polaris_workflow_describe``."""

    workflow_name: NonEmptyString


class WorkflowNodeDescription(McpBoundaryModel):
    name: NonEmptyString
    node_type: NonEmptyString
    dependencies: tuple[NonEmptyString, ...] = ()
    enabled: bool
    max_retries: int = Field(ge=0)
    retry_backoff_seconds: float = Field(ge=0.0)
    fail_fast: bool
    timeout_seconds: float | None = Field(default=None, gt=0.0)
    tags: tuple[NonEmptyString, ...] = ()
    metadata: dict[str, JsonValue] = Field(default_factory=dict)


class WorkflowGraphDescription(McpBoundaryModel):
    workflow_name: NonEmptyString
    workflow_description: str
    nodes: tuple[WorkflowNodeDescription, ...]


class WorkflowDescribeResponse(McpBoundaryModel):
    """Output contract for ``polaris_workflow_describe``."""

    found: bool
    workflow_name: NonEmptyString
    description: str = ""
    tags: tuple[NonEmptyString, ...] = ()
    metadata: dict[str, JsonValue] = Field(default_factory=dict)
    definition: WorkflowGraphDescription | None = None
    error: McpError | None = None

    @model_validator(mode="after")
    def validate_found_payload(self) -> WorkflowDescribeResponse:
        if self.found and self.definition is None:
            raise ValueError("definition is required when found is true.")
        if not self.found and self.error is None:
            raise ValueError("error is required when found is false.")
        return self


class CompletedRunsListRequest(McpBoundaryModel):
    """Input contract for ``polaris_completed_runs_list``."""

    workflow_name: NonEmptyString
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1)


class CompletedRunsListResponse(McpBoundaryModel):
    """Output contract for ``polaris_completed_runs_list``."""

    workflow_name: NonEmptyString
    execution_ids: tuple[NonEmptyString, ...]
    total_count: int = Field(ge=0)
    offset: int = Field(ge=0)
    limit: int = Field(ge=1)
    has_more: bool
    next_offset: int | None = Field(default=None, ge=0)


class CompletedRunSection(StrEnum):
    WORKFLOW_INPUTS = "workflow_inputs"
    NODE_OUTPUTS = "node_outputs"
    ERRORS = "errors"
    ARTIFACT_REFS = "artifact_refs"
    TRACE_CONTEXT = "trace_context"


class CompletedRunGetRequest(McpBoundaryModel):
    """Input contract for ``polaris_completed_run_get``."""

    workflow_name: NonEmptyString
    execution_id: NonEmptyString
    include: frozenset[CompletedRunSection] = frozenset()
    node_names: tuple[NonEmptyString, ...] = ()

    @model_validator(mode="after")
    def validate_node_selector(self) -> CompletedRunGetRequest:
        if self.node_names and CompletedRunSection.NODE_OUTPUTS not in self.include:
            raise ValueError("node_names requires node_outputs in include.")
        return self


class CompletedNodeOutput(McpBoundaryModel):
    node_name: NonEmptyString
    success: bool | None = None
    skipped: bool | None = None
    stop_propagation: bool | None = None
    outputs: dict[str, JsonValue] = Field(default_factory=dict)
    artifacts: dict[str, JsonValue] = Field(default_factory=dict)
    emitted_events: tuple[dict[str, JsonValue], ...] = ()
    errors: tuple[dict[str, JsonValue], ...] = ()
    execution_metadata: dict[str, JsonValue] = Field(default_factory=dict)


class TraceContextResponse(McpBoundaryModel):
    trace_id: NonEmptyString
    span_id: NonEmptyString
    parent_span_id: NonEmptyString | None = None
    correlation_id: NonEmptyString | None = None
    workflow_id: NonEmptyString | None = None
    execution_id: NonEmptyString | None = None
    runtime_id: NonEmptyString | None = None
    node_name: NonEmptyString | None = None
    created_at: datetime
    attributes: dict[str, JsonValue] = Field(default_factory=dict)


class CompletedRunGetResponse(McpBoundaryModel):
    """Output contract for ``polaris_completed_run_get``."""

    found: bool
    workflow_id: str | None = None
    execution_id: NonEmptyString
    runtime_id: str | None = None
    mode: str | None = None
    created_at: datetime | None = None
    simulation_time: datetime | None = None
    context_version: int | None = Field(default=None, ge=0)
    node_output_count: int = Field(default=0, ge=0)
    error_count: int = Field(default=0, ge=0)
    artifact_count: int = Field(default=0, ge=0)
    workflow_inputs: dict[str, JsonValue] | None = None
    node_outputs: tuple[CompletedNodeOutput, ...] | None = None
    errors: tuple[dict[str, JsonValue], ...] | None = None
    artifact_refs: dict[str, JsonValue] | None = None
    trace_context: TraceContextResponse | None = None
    error: McpError | None = None


TOOL_INPUT_MODELS: dict[str, type[McpBoundaryModel]] = {
    "polaris_rag_ask": RagAskRequest,
    "polaris_rag_status": RagStatusRequest,
    "polaris_workflows_list": WorkflowsListRequest,
    "polaris_workflow_describe": WorkflowDescribeRequest,
    "polaris_completed_runs_list": CompletedRunsListRequest,
    "polaris_completed_run_get": CompletedRunGetRequest,
}

TOOL_OUTPUT_MODELS: dict[str, type[McpBoundaryModel]] = {
    "polaris_rag_ask": RagAskResponse,
    "polaris_rag_status": RagStatusResponse,
    "polaris_workflows_list": WorkflowsListResponse,
    "polaris_workflow_describe": WorkflowDescribeResponse,
    "polaris_completed_runs_list": CompletedRunsListResponse,
    "polaris_completed_run_get": CompletedRunGetResponse,
}
