from __future__ import annotations

from dataclasses import dataclass

from config.settings import Settings
from integration.providers.rag.quality_evaluation_provider import RagQualityModelConfig
from integration.providers.rag.query_routing_provider import RagQueryModelConfig


@dataclass(
    frozen=True,
    slots=True,
)
class RagModelConfig:
    query_rewrite_model: str
    adaptive_triage_model: str
    route_selection_model: str
    hyde_model: str
    hybrid_embedding_model: str
    reranker_model: str
    reranker_endpoint: str
    crag_grader_model: str
    crag_query_rewrite_model: str
    self_reflection_model: str
    synthesis_model: str
    structured_max_tokens: int
    hyde_max_tokens: int
    synthesis_max_tokens: int

    def __post_init__(self) -> None:
        for field_name in self.__dataclass_fields__:
            value = getattr(self, field_name)
            if isinstance(value, str) and not value.strip():
                raise ValueError(f"{field_name} cannot be empty.")
            if isinstance(value, int) and value <= 0:
                raise ValueError(f"{field_name} must be greater than 0.")

    @classmethod
    def from_settings(cls, settings: Settings) -> RagModelConfig:
        return cls(
            query_rewrite_model=settings.RAG_QUERY_REWRITE_MODEL,
            adaptive_triage_model=settings.RAG_ADAPTIVE_TRIAGE_MODEL,
            route_selection_model=settings.RAG_ROUTE_SELECTION_MODEL,
            hyde_model=settings.RAG_HYDE_MODEL,
            hybrid_embedding_model=settings.RAG_HYBRID_EMBEDDING_MODEL,
            reranker_model=settings.RAG_RERANKER_MODEL,
            reranker_endpoint=settings.RAG_RERANKER_ENDPOINT,
            crag_grader_model=settings.RAG_CRAG_GRADER_MODEL,
            crag_query_rewrite_model=settings.RAG_CRAG_QUERY_REWRITE_MODEL,
            self_reflection_model=settings.RAG_SELF_REFLECTION_MODEL,
            synthesis_model=settings.RAG_SYNTHESIS_MODEL,
            structured_max_tokens=settings.RAG_STRUCTURED_MAX_TOKENS,
            hyde_max_tokens=settings.RAG_HYDE_MAX_TOKENS,
            synthesis_max_tokens=settings.RAG_SYNTHESIS_MAX_TOKENS,
        )

    @property
    def query_routing(self) -> RagQueryModelConfig:
        return RagQueryModelConfig(
            query_rewrite_model=self.query_rewrite_model,
            adaptive_triage_model=self.adaptive_triage_model,
            route_selection_model=self.route_selection_model,
            hyde_model=self.hyde_model,
            structured_max_tokens=self.structured_max_tokens,
            hyde_max_tokens=self.hyde_max_tokens,
        )

    @property
    def quality_evaluation(self) -> RagQualityModelConfig:
        return RagQualityModelConfig(
            crag_grader_model=self.crag_grader_model,
            crag_query_rewrite_model=self.crag_query_rewrite_model,
            self_reflection_model=self.self_reflection_model,
            structured_max_tokens=self.structured_max_tokens,
        )
