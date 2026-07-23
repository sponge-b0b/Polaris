from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from core.storage.persistence.rag import JsonObject


class GraphNodeType(StrEnum):
    WORKFLOW_RUN = "WorkflowRun"
    AGENT_SIGNAL = "AgentSignal"
    REPORT = "Report"
    RECOMMENDATION = "Recommendation"
    RISK = "Risk"
    STRATEGY = "Strategy"
    SYMBOL = "Symbol"
    MACRO_REGIME = "MacroRegime"
    TECHNICAL_REGIME = "TechnicalRegime"
    NEWS_THEME = "NewsTheme"
    SENTIMENT_SNAPSHOT = "SentimentSnapshot"
    PORTFOLIO_SNAPSHOT = "PortfolioSnapshot"


class GraphRelationshipType(StrEnum):
    PRODUCED = "PRODUCED"
    SUPPORTS = "SUPPORTS"
    CONSTRAINS = "CONSTRAINS"
    APPLIES_TO = "APPLIES_TO"
    SUMMARIZES = "SUMMARIZES"
    HAS_REGIME = "HAS_REGIME"
    INFLUENCES = "INFLUENCES"
    MENTIONS = "MENTIONS"
    DECISION_EVALUATED_HYPOTHESIS = "DECISION_EVALUATED_HYPOTHESIS"
    DECISION_SELECTED_HYPOTHESIS = "DECISION_SELECTED_HYPOTHESIS"
    HYPOTHESIS_SUPPORTED_BY = "HYPOTHESIS_SUPPORTED_BY"
    HYPOTHESIS_CONTRADICTED_BY = "HYPOTHESIS_CONTRADICTED_BY"
    HYPOTHESIS_INVALIDATED_BY = "HYPOTHESIS_INVALIDATED_BY"


@dataclass(frozen=True, slots=True)
class GraphNode:
    node_id: str
    node_type: GraphNodeType
    properties: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.node_id.strip():
            raise ValueError("node_id cannot be empty.")


@dataclass(frozen=True, slots=True)
class GraphRelationship:
    start_node_id: str
    end_node_id: str
    relationship_type: GraphRelationshipType
    properties: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.start_node_id.strip() or not self.end_node_id.strip():
            raise ValueError("relationship node identifiers cannot be empty.")


@dataclass(frozen=True, slots=True)
class GraphProjection:
    document_id: str
    nodes: tuple[GraphNode, ...]
    relationships: tuple[GraphRelationship, ...]

    def __post_init__(self) -> None:
        if not self.document_id.strip():
            raise ValueError("document_id cannot be empty.")


@dataclass(frozen=True, slots=True)
class GraphSearchQuery:
    query: str
    top_k: int
    symbols: tuple[str, ...] = ()
    regimes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.query.strip():
            raise ValueError("query cannot be empty.")
        if self.top_k <= 0:
            raise ValueError("top_k must be positive.")


@dataclass(frozen=True, slots=True)
class GraphSearchResult:
    document_id: str
    source_id: str
    source_type: str
    title: str
    score: float
    related_entities: tuple[str, ...] = ()
    metadata: JsonObject = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class GraphStoreStatus:
    healthy: bool
    entity_count: int
