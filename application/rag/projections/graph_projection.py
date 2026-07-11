from __future__ import annotations

from collections.abc import Mapping
from collections.abc import Sequence
from dataclasses import dataclass
from dataclasses import replace
from datetime import UTC
from datetime import datetime
from time import perf_counter

from application.rag.contracts.rag_context import RagRetrievedContext
from application.rag.contracts.rag_context import RagSource
from application.rag.contracts.rag_request import RagRequest
from core.storage.persistence.rag import JsonObject
from core.storage.persistence.rag import JsonValue
from core.storage.persistence.rag import RagDocumentRecord
from core.storage.persistence.rag import RagGraphJobRecord
from core.storage.persistence.rag import RagPersistenceRepository
from core.storage.persistence.rag import new_rag_graph_job_id
from core.telemetry.emitters.application_rag_telemetry import ApplicationRagTelemetry
from integration.providers.rag.graph_projection_models import GraphNode
from integration.providers.rag.graph_projection_models import GraphNodeType
from integration.providers.rag.graph_projection_models import GraphProjection
from integration.providers.rag.graph_projection_models import GraphRelationship
from integration.providers.rag.graph_projection_models import GraphRelationshipType
from integration.providers.rag.graph_projection_models import GraphSearchQuery
from integration.providers.rag.graph_projection_provider import GraphProjectionProvider


NEO4J_TARGET_STORE = "neo4j"
DEFAULT_GRAPH_MODEL = "polaris-rag-graph-v1"


@dataclass(frozen=True, slots=True)
class GraphJobProcessingResult:
    processed_count: int
    completed_count: int
    failed_count: int
    failed_job_ids: tuple[str, ...] = ()
    cleared_entity_count: int = 0


class RagGraphEntityExtractor:
    """Build deterministic graph entities from canonical PostgreSQL documents."""

    def extract(self, document: RagDocumentRecord) -> GraphProjection:
        primary_type = _primary_node_type(document)
        primary_id = _primary_node_id(document, primary_type)
        symbols = _metadata_strings(document.metadata, "symbols")
        symbol = _metadata_string(document.metadata, "symbol")
        if symbol is not None:
            symbols = _unique(symbols + (symbol.upper(),))
        regimes = _regimes(document.metadata)
        themes = _metadata_strings(document.metadata, "themes")

        nodes: list[GraphNode] = [
            GraphNode(
                node_id=primary_id,
                node_type=primary_type,
                properties={
                    "document_id": document.document_id,
                    "source_id": document.source_id,
                    "source_table": document.source_table,
                    "source_type": document.source_type,
                    "title": document.title,
                    "generated_at": document.generated_at.isoformat(),
                    "symbols": list(symbols),
                    "search_text": " ".join(
                        (
                            document.title,
                            document.source_type,
                            *symbols,
                            *regimes,
                            *themes,
                        )
                    ).lower(),
                },
            )
        ]
        relationships: list[GraphRelationship] = []

        workflow_id = _workflow_node_id(document)
        if workflow_id is not None:
            nodes.append(
                GraphNode(
                    node_id=workflow_id,
                    node_type=GraphNodeType.WORKFLOW_RUN,
                    properties={
                        "workflow_name": document.workflow_name,
                        "execution_id": document.execution_id,
                        "title": f"{document.workflow_name}:{document.execution_id}",
                    },
                )
            )
            relationships.append(
                GraphRelationship(
                    start_node_id=workflow_id,
                    end_node_id=primary_id,
                    relationship_type=GraphRelationshipType.PRODUCED,
                )
            )

        for value in symbols:
            symbol_id = f"symbol:{value.upper()}"
            nodes.append(
                GraphNode(
                    node_id=symbol_id,
                    node_type=GraphNodeType.SYMBOL,
                    properties={"symbol": value.upper(), "title": value.upper()},
                )
            )
            relationships.append(
                GraphRelationship(
                    start_node_id=primary_id,
                    end_node_id=symbol_id,
                    relationship_type=(
                        GraphRelationshipType.APPLIES_TO
                        if primary_type is GraphNodeType.RECOMMENDATION
                        else GraphRelationshipType.MENTIONS
                    ),
                )
            )

        for value in regimes:
            regime_type = _regime_node_type(document)
            regime_id = f"regime:{regime_type.value.lower()}:{_slug(value)}"
            nodes.append(
                GraphNode(
                    node_id=regime_id,
                    node_type=regime_type,
                    properties={"regime": value.lower(), "title": value},
                )
            )
            relationships.append(
                GraphRelationship(
                    start_node_id=primary_id,
                    end_node_id=regime_id,
                    relationship_type=GraphRelationshipType.HAS_REGIME,
                )
            )

        for value in themes:
            theme_id = f"news_theme:{_slug(value)}"
            nodes.append(
                GraphNode(
                    node_id=theme_id,
                    node_type=GraphNodeType.NEWS_THEME,
                    properties={"theme": value, "title": value},
                )
            )
            relationships.append(
                GraphRelationship(
                    start_node_id=primary_id,
                    end_node_id=theme_id,
                    relationship_type=GraphRelationshipType.MENTIONS,
                )
            )

        recommendation_id = _metadata_string(document.metadata, "recommendation_id")
        if recommendation_id and primary_type is not GraphNodeType.RECOMMENDATION:
            recommendation_node_id = f"recommendation:{recommendation_id}"
            nodes.append(
                GraphNode(
                    node_id=recommendation_node_id,
                    node_type=GraphNodeType.RECOMMENDATION,
                    properties={
                        "source_id": recommendation_id,
                        "title": f"Recommendation {recommendation_id}",
                    },
                )
            )
            relationship_type = _recommendation_relationship(primary_type)
            if relationship_type is not None:
                relationships.append(
                    GraphRelationship(
                        start_node_id=primary_id,
                        end_node_id=recommendation_node_id,
                        relationship_type=relationship_type,
                    )
                )

        _append_strategy_relationships(
            document=document,
            primary_id=primary_id,
            nodes=nodes,
            relationships=relationships,
        )

        return GraphProjection(
            document_id=document.document_id,
            nodes=_deduplicate_nodes(nodes),
            relationships=_deduplicate_relationships(relationships),
        )


class GraphProjectionJobProcessor:
    """Queue and execute PostgreSQL-backed Neo4j projection jobs."""

    def __init__(
        self,
        *,
        repository: RagPersistenceRepository,
        provider: GraphProjectionProvider,
        extractor: RagGraphEntityExtractor | None = None,
        telemetry: ApplicationRagTelemetry | None = None,
        graph_model: str = DEFAULT_GRAPH_MODEL,
    ) -> None:
        self._repository = repository
        self._provider = provider
        self._extractor = extractor or RagGraphEntityExtractor()
        self._telemetry = telemetry
        self._graph_model = graph_model

    async def queue_document(self, document_id: str) -> bool:
        existing_jobs = await self._repository.list_graph_jobs()
        if any(
            job.document_id == document_id
            and job.target_store == NEO4J_TARGET_STORE
            and job.graph_model == self._graph_model
            for job in existing_jobs
        ):
            return False
        job = RagGraphJobRecord(
            job_id=new_rag_graph_job_id(
                document_id=document_id,
                target_store=NEO4J_TARGET_STORE,
                graph_model=self._graph_model,
            ),
            document_id=document_id,
            target_store=NEO4J_TARGET_STORE,
            graph_model=self._graph_model,
            status="queued",
            queued_at=datetime.now(UTC),
            metadata={"projection": NEO4J_TARGET_STORE},
        )
        result = await self._repository.persist_graph_job(job)
        if not result.success:
            raise RuntimeError(
                result.error or f"Failed to queue graph job {job.job_id}."
            )
        return True

    async def process_queued_jobs(
        self,
        *,
        batch_size: int | None = None,
    ) -> GraphJobProcessingResult:
        operation = "rag.graph.process"
        started_at = perf_counter()
        await self._emit_started(
            operation,
            attributes={"batch_size": batch_size},
        )
        try:
            jobs = tuple(
                job
                for job in await self._repository.list_graph_jobs(status="queued")
                if job.target_store == NEO4J_TARGET_STORE
            )
            if batch_size is not None:
                jobs = jobs[:batch_size]
            completed = 0
            failed_ids: list[str] = []
            for job in jobs:
                if await self._process_job(job):
                    completed += 1
                else:
                    failed_ids.append(job.job_id)
            result = GraphJobProcessingResult(
                processed_count=len(jobs),
                completed_count=completed,
                failed_count=len(failed_ids),
                failed_job_ids=tuple(failed_ids),
            )
        except Exception as exc:
            await self._emit_failed(
                operation,
                error=exc,
                duration_seconds=perf_counter() - started_at,
            )
            raise
        await self._emit_completed(
            operation,
            duration_seconds=perf_counter() - started_at,
            attributes={
                "processed_count": result.processed_count,
                "completed_count": result.completed_count,
                "failed_count": result.failed_count,
            },
        )
        return result

    async def rebuild(self) -> GraphJobProcessingResult:
        cleared = await self._provider.clear_projection()
        jobs = tuple(
            job
            for job in await self._repository.list_graph_jobs()
            if job.target_store == NEO4J_TARGET_STORE
        )
        by_document: dict[str, RagGraphJobRecord] = {}
        for job in jobs:
            by_document.setdefault(job.document_id, job)
        for job in by_document.values():
            queued = replace(
                job,
                graph_model=self._graph_model,
                status="queued",
                queued_at=datetime.now(UTC),
                started_at=None,
                completed_at=None,
                attempts=0,
                error=None,
                metadata={**dict(job.metadata), "rebuild_requeued": True},
            )
            result = await self._repository.persist_graph_job(queued)
            if not result.success:
                raise RuntimeError(result.error or f"Failed to requeue {job.job_id}.")
        processed = await self.process_queued_jobs()
        return replace(processed, cleared_entity_count=cleared)

    async def _process_job(self, job: RagGraphJobRecord) -> bool:
        operation = "rag.graph.job"
        started_at = perf_counter()
        await self._emit_started(
            operation,
            correlation_id=job.job_id,
            attributes={
                "document_id": job.document_id,
                "graph_model": job.graph_model,
            },
        )
        processing = replace(
            job,
            status="processing",
            started_at=datetime.now(UTC),
            completed_at=None,
            attempts=job.attempts + 1,
            error=None,
        )
        try:
            await self._persist_job(processing)
            document = await self._repository.get_document(job.document_id)
            if document is None:
                raise LookupError(f"RAG document not found: {job.document_id}")
            projection = self._extractor.extract(document)
            await self._provider.upsert_projection(projection)
            await self._persist_job(
                replace(
                    processing,
                    status="completed",
                    completed_at=datetime.now(UTC),
                )
            )
        except Exception as exc:
            try:
                await self._persist_job(
                    replace(
                        processing,
                        status="failed",
                        completed_at=datetime.now(UTC),
                        error=str(exc),
                    )
                )
            finally:
                await self._emit_failed(
                    operation,
                    error=exc,
                    duration_seconds=perf_counter() - started_at,
                    correlation_id=job.job_id,
                    attributes={"document_id": job.document_id},
                )
            return False
        await self._emit_completed(
            operation,
            duration_seconds=perf_counter() - started_at,
            correlation_id=job.job_id,
            attributes={
                "document_id": job.document_id,
                "node_count": len(projection.nodes),
                "relationship_count": len(projection.relationships),
            },
        )
        return True

    async def _persist_job(self, job: RagGraphJobRecord) -> None:
        result = await self._repository.persist_graph_job(job)
        if not result.success:
            raise RuntimeError(
                result.error or f"Failed to persist graph job {job.job_id}."
            )

    async def _emit_started(
        self,
        operation: str,
        *,
        correlation_id: str | None = None,
        attributes: dict[str, JsonValue] | None = None,
    ) -> None:
        if self._telemetry is None:
            return
        await self._telemetry.emit_operation_started(
            self.__class__.__name__,
            operation,
            correlation_id=correlation_id,
            attributes=attributes,
        )

    async def _emit_completed(
        self,
        operation: str,
        *,
        duration_seconds: float,
        correlation_id: str | None = None,
        attributes: dict[str, JsonValue],
    ) -> None:
        if self._telemetry is None:
            return
        await self._telemetry.emit_operation_completed(
            self.__class__.__name__,
            operation,
            duration_seconds=duration_seconds,
            correlation_id=correlation_id,
            attributes=attributes,
        )

    async def _emit_failed(
        self,
        operation: str,
        *,
        error: Exception,
        duration_seconds: float,
        correlation_id: str | None = None,
        attributes: dict[str, JsonValue] | None = None,
    ) -> None:
        if self._telemetry is None:
            return
        await self._telemetry.emit_operation_failed(
            self.__class__.__name__,
            operation,
            error=error,
            duration_seconds=duration_seconds,
            correlation_id=correlation_id,
            attributes=attributes,
        )


class Neo4jGraphRetriever:
    """Retrieve Neo4j-linked documents and rehydrate them from PostgreSQL."""

    def __init__(
        self,
        *,
        repository: RagPersistenceRepository,
        provider: GraphProjectionProvider,
        telemetry: ApplicationRagTelemetry | None = None,
    ) -> None:
        self._repository = repository
        self._provider = provider
        self._telemetry = telemetry

    async def retrieve(self, request: RagRequest) -> tuple[RagRetrievedContext, ...]:
        hits = await self._provider.search(
            GraphSearchQuery(
                query=request.normalized_query,
                top_k=request.top_k,
                symbols=request.filters.symbols,
                regimes=request.filters.regimes,
            )
        )
        contexts: list[RagRetrievedContext] = []
        missing_document_count = 0
        for rank, hit in enumerate(hits, start=1):
            document = await self._repository.get_document(hit.document_id)
            if document is None:
                missing_document_count += 1
                continue
            contexts.append(
                RagRetrievedContext(
                    context_id=f"graph:{document.document_id}",
                    text=document.content_text,
                    source=RagSource(
                        source_table=document.source_table,
                        source_id=document.source_id,
                        source_type=document.source_type,
                        document_id=document.document_id,
                        title=document.title,
                        generated_at=document.generated_at,
                        workflow_name=document.workflow_name,
                        execution_id=document.execution_id,
                        metadata=document.metadata,
                    ),
                    score=hit.score,
                    rank=rank,
                    retrieval_route="graph",
                    metadata={
                        "related_entities": list(hit.related_entities),
                        "projection": NEO4J_TARGET_STORE,
                    },
                )
            )
        if missing_document_count and self._telemetry is not None:
            await self._telemetry.emit_operation_degraded(
                self.__class__.__name__,
                "rag.retrieval.graph.rehydrate",
                correlation_id=request.request_id,
                attributes={
                    "graph_hit_count": len(hits),
                    "rehydrated_document_count": len(contexts),
                    "missing_document_count": missing_document_count,
                },
            )
        return tuple(contexts)


def _append_strategy_relationships(
    *,
    document: RagDocumentRecord,
    primary_id: str,
    nodes: list[GraphNode],
    relationships: list[GraphRelationship],
) -> None:
    if document.source_table == "strategy_synthesis_decisions":
        _append_strategy_decision_relationships(
            document=document,
            primary_id=primary_id,
            nodes=nodes,
            relationships=relationships,
        )
        return
    if document.source_table == "strategy_hypotheses":
        _append_strategy_hypothesis_evidence_relationships(
            hypothesis_node_id=primary_id,
            metadata=document.metadata,
            source_id=document.source_id,
            nodes=nodes,
            relationships=relationships,
        )


def _append_strategy_decision_relationships(
    *,
    document: RagDocumentRecord,
    primary_id: str,
    nodes: list[GraphNode],
    relationships: list[GraphRelationship],
) -> None:
    selected_hypothesis_id = _metadata_string(
        document.metadata,
        "selected_hypothesis_id",
    )
    evaluations_by_hypothesis = {
        hypothesis_id: evaluation
        for evaluation in _metadata_objects(document.metadata, "related_evaluations")
        if (hypothesis_id := _metadata_object_string(evaluation, "hypothesis_id"))
    }
    for hypothesis in _metadata_objects(document.metadata, "related_hypotheses"):
        hypothesis_id = _metadata_object_string(hypothesis, "hypothesis_id")
        if hypothesis_id is None:
            continue
        hypothesis_node_id = f"strategy_hypothesis:{hypothesis_id}"
        nodes.append(
            GraphNode(
                node_id=hypothesis_node_id,
                node_type=GraphNodeType.STRATEGY,
                properties=_strategy_hypothesis_node_properties(hypothesis),
            )
        )
        evaluation = evaluations_by_hypothesis.get(hypothesis_id, {})
        relationships.append(
            GraphRelationship(
                start_node_id=primary_id,
                end_node_id=hypothesis_node_id,
                relationship_type=GraphRelationshipType.DECISION_EVALUATED_HYPOTHESIS,
                properties=_strategy_relationship_properties(evaluation),
            )
        )
        if hypothesis_id == selected_hypothesis_id:
            relationships.append(
                GraphRelationship(
                    start_node_id=primary_id,
                    end_node_id=hypothesis_node_id,
                    relationship_type=(
                        GraphRelationshipType.DECISION_SELECTED_HYPOTHESIS
                    ),
                    properties=_strategy_relationship_properties(evaluation),
                )
            )
        _append_strategy_hypothesis_evidence_relationships(
            hypothesis_node_id=hypothesis_node_id,
            metadata=hypothesis,
            source_id=hypothesis_id,
            nodes=nodes,
            relationships=relationships,
        )


def _append_strategy_hypothesis_evidence_relationships(
    *,
    hypothesis_node_id: str,
    metadata: JsonObject,
    source_id: str,
    nodes: list[GraphNode],
    relationships: list[GraphRelationship],
) -> None:
    for index, evidence in enumerate(
        _metadata_objects(metadata, "supporting_evidence"),
        start=1,
    ):
        node_id = _strategy_evidence_node_id(source_id, "supporting", index)
        nodes.append(_strategy_evidence_node(node_id, evidence, "supporting_evidence"))
        relationships.append(
            GraphRelationship(
                start_node_id=hypothesis_node_id,
                end_node_id=node_id,
                relationship_type=GraphRelationshipType.HYPOTHESIS_SUPPORTED_BY,
            )
        )
    for index, evidence in enumerate(
        _metadata_objects(metadata, "contradicting_evidence"),
        start=1,
    ):
        node_id = _strategy_evidence_node_id(source_id, "contradicting", index)
        nodes.append(
            _strategy_evidence_node(node_id, evidence, "contradicting_evidence")
        )
        relationships.append(
            GraphRelationship(
                start_node_id=hypothesis_node_id,
                end_node_id=node_id,
                relationship_type=GraphRelationshipType.HYPOTHESIS_CONTRADICTED_BY,
            )
        )
    for index, condition in enumerate(
        _metadata_objects(metadata, "invalidation_conditions"),
        start=1,
    ):
        node_id = _strategy_evidence_node_id(source_id, "invalidation", index)
        nodes.append(
            _strategy_evidence_node(node_id, condition, "invalidation_condition")
        )
        relationships.append(
            GraphRelationship(
                start_node_id=hypothesis_node_id,
                end_node_id=node_id,
                relationship_type=GraphRelationshipType.HYPOTHESIS_INVALIDATED_BY,
            )
        )


def _strategy_hypothesis_node_properties(metadata: JsonObject) -> JsonObject:
    hypothesis_id = _metadata_object_string(metadata, "hypothesis_id") or "unknown"
    perspective = _metadata_object_string(metadata, "perspective")
    symbol = _metadata_object_string(metadata, "symbol")
    return {
        "strategy_entity_type": "hypothesis",
        "source_table": "strategy_hypotheses",
        "source_id": hypothesis_id,
        "title": f"Strategy Hypothesis {hypothesis_id}",
        "symbol": symbol,
        "perspective": perspective,
        "confidence": _metadata_object_scalar(metadata, "confidence"),
        "hypothesis_strength": _metadata_object_scalar(
            metadata,
            "hypothesis_strength",
        ),
        "directional_bias": _metadata_object_scalar(metadata, "directional_bias"),
        "invalidated": _metadata_object_scalar(metadata, "invalidated"),
        "search_text": " ".join(
            part
            for part in (
                "strategy hypothesis",
                symbol,
                perspective,
                hypothesis_id,
            )
            if part
        ).lower(),
    }


def _strategy_evidence_node(
    node_id: str,
    metadata: JsonObject,
    entity_type: str,
) -> GraphNode:
    title = _strategy_evidence_title(metadata, entity_type)
    return GraphNode(
        node_id=node_id,
        node_type=GraphNodeType.STRATEGY,
        properties={
            "strategy_entity_type": entity_type,
            "title": title,
            "source": _metadata_object_string(metadata, "source"),
            "name": _metadata_object_string(metadata, "name"),
            "description": _metadata_object_string(metadata, "description"),
            "claim": _metadata_object_string(metadata, "claim"),
            "condition": _metadata_object_string(metadata, "condition"),
            "operator": _metadata_object_string(metadata, "operator"),
            "observed_value": _metadata_object_scalar(metadata, "observed_value"),
            "threshold": _metadata_object_scalar(metadata, "threshold"),
            "search_text": f"{entity_type} {title}".lower(),
        },
    )


def _strategy_evidence_title(metadata: JsonObject, fallback: str) -> str:
    for key in ("name", "description", "claim", "condition"):
        value = _metadata_object_string(metadata, key)
        if value is not None:
            return value
    return fallback.replace("_", " ").title()


def _strategy_evidence_node_id(
    source_id: str,
    kind: str,
    index: int,
) -> str:
    return f"strategy_evidence:{_slug(source_id)}:{kind}:{index}"


def _strategy_relationship_properties(metadata: JsonObject) -> JsonObject:
    return {
        key: value
        for key in (
            "evaluation_id",
            "perspective",
            "perspective_weight",
            "synthesis_weight",
            "candidate_score",
            "contradiction_burden",
            "assumption_support",
            "rank",
            "selection_status",
            "invalidated",
        )
        if (value := _metadata_object_scalar(metadata, key)) is not None
    }


def _metadata_objects(metadata: JsonObject, key: str) -> tuple[JsonObject, ...]:
    value = metadata.get(key)
    if not isinstance(value, Sequence) or isinstance(value, str | bytes):
        return ()
    return tuple(item for item in value if isinstance(item, Mapping))


def _metadata_object_string(metadata: JsonObject, key: str) -> str | None:
    value = metadata.get(key)
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _metadata_object_scalar(metadata: JsonObject, key: str) -> JsonValue:
    value = metadata.get(key)
    if value is None or isinstance(value, str | int | float | bool):
        return value
    return None


def _primary_node_type(document: RagDocumentRecord) -> GraphNodeType:
    table = document.source_table
    if table == "agent_signals":
        return GraphNodeType.AGENT_SIGNAL
    if table == "reports":
        return GraphNodeType.REPORT
    if table in {"recommendations", "recommendation_rationales"}:
        return GraphNodeType.RECOMMENDATION
    if table == "portfolio_risk_snapshots":
        return GraphNodeType.RISK
    if table in {"portfolio_allocation_snapshots", "backtest_portfolio_snapshots"}:
        return GraphNodeType.PORTFOLIO_SNAPSHOT
    if table == "macro_regime_snapshots":
        return GraphNodeType.MACRO_REGIME
    if table in {
        "market_context_snapshots",
        "technical_analysis_snapshots",
        "market_breadth_snapshots",
    }:
        return GraphNodeType.TECHNICAL_REGIME
    if table == "news_analysis_snapshots":
        return GraphNodeType.NEWS_THEME
    if table == "sentiment_snapshots":
        return GraphNodeType.SENTIMENT_SNAPSHOT
    if table in {"strategy_synthesis_decisions", "strategy_hypotheses"}:
        return GraphNodeType.STRATEGY
    if table.startswith("backtest_"):
        return GraphNodeType.STRATEGY
    return GraphNodeType.REPORT


def _primary_node_id(
    document: RagDocumentRecord,
    node_type: GraphNodeType,
) -> str:
    if node_type is GraphNodeType.RECOMMENDATION:
        recommendation_id = _metadata_string(document.metadata, "recommendation_id")
        return f"recommendation:{recommendation_id or document.source_id}"
    return f"document:{document.document_id}"


def _workflow_node_id(document: RagDocumentRecord) -> str | None:
    if not document.workflow_name or not document.execution_id:
        return None
    return f"workflow:{document.workflow_name}:{document.execution_id}"


def _regime_node_type(document: RagDocumentRecord) -> GraphNodeType:
    if document.source_table == "macro_regime_snapshots":
        return GraphNodeType.MACRO_REGIME
    return GraphNodeType.TECHNICAL_REGIME


def _recommendation_relationship(
    source_type: GraphNodeType,
) -> GraphRelationshipType | None:
    if source_type is GraphNodeType.AGENT_SIGNAL:
        return GraphRelationshipType.SUPPORTS
    if source_type is GraphNodeType.RISK:
        return GraphRelationshipType.CONSTRAINS
    if source_type is GraphNodeType.NEWS_THEME:
        return GraphRelationshipType.INFLUENCES
    return None


def _regimes(metadata: JsonObject) -> tuple[str, ...]:
    values: tuple[str, ...] = ()
    for key in (
        "regime",
        "macro_regime",
        "market_regime",
        "technical_regime",
        "breadth_regime",
        "sentiment_regime",
    ):
        value = _metadata_string(metadata, key)
        if value is not None:
            values += (value,)
    return _unique(values)


def _metadata_string(metadata: JsonObject, key: str) -> str | None:
    value = metadata.get(key)
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _metadata_strings(metadata: JsonObject, key: str) -> tuple[str, ...]:
    value = metadata.get(key)
    if isinstance(value, str):
        return (value.strip(),) if value.strip() else ()
    if not isinstance(value, Sequence):
        return ()
    return _unique(tuple(str(item).strip() for item in value if str(item).strip()))


def _unique(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


def _slug(value: str) -> str:
    return "-".join(value.strip().lower().replace("_", "-").split())


def _deduplicate_nodes(nodes: list[GraphNode]) -> tuple[GraphNode, ...]:
    return tuple({node.node_id: node for node in nodes}.values())


def _deduplicate_relationships(
    relationships: list[GraphRelationship],
) -> tuple[GraphRelationship, ...]:
    return tuple(
        {
            (
                relationship.start_node_id,
                relationship.end_node_id,
                relationship.relationship_type,
            ): relationship
            for relationship in relationships
        }.values()
    )
