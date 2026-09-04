from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol, cast

from neo4j import AsyncGraphDatabase, RoutingControl

from config.settings import Settings
from core.storage.persistence.rag import JsonObject

_NODE_LABELS = {
    "WorkflowRun": "WorkflowRun",
    "AgentSignal": "AgentSignal",
    "Report": "Report",
    "Recommendation": "Recommendation",
    "Risk": "Risk",
    "Strategy": "Strategy",
    "Symbol": "Symbol",
    "MacroRegime": "MacroRegime",
    "TechnicalRegime": "TechnicalRegime",
    "NewsTheme": "NewsTheme",
    "SentimentSnapshot": "SentimentSnapshot",
    "PortfolioSnapshot": "PortfolioSnapshot",
}
_RELATIONSHIP_TYPES = {
    "PRODUCED": "PRODUCED",
    "SUPPORTS": "SUPPORTS",
    "CONSTRAINS": "CONSTRAINS",
    "APPLIES_TO": "APPLIES_TO",
    "SUMMARIZES": "SUMMARIZES",
    "HAS_REGIME": "HAS_REGIME",
    "INFLUENCES": "INFLUENCES",
    "MENTIONS": "MENTIONS",
    "DECISION_EVALUATED_HYPOTHESIS": "DECISION_EVALUATED_HYPOTHESIS",
    "DECISION_SELECTED_HYPOTHESIS": "DECISION_SELECTED_HYPOTHESIS",
    "HYPOTHESIS_SUPPORTED_BY": "HYPOTHESIS_SUPPORTED_BY",
    "HYPOTHESIS_CONTRADICTED_BY": "HYPOTHESIS_CONTRADICTED_BY",
    "HYPOTHESIS_INVALIDATED_BY": "HYPOTHESIS_INVALIDATED_BY",
}


@dataclass(frozen=True, slots=True)
class Neo4jNode:
    node_id: str
    node_type: str
    properties: JsonObject


@dataclass(frozen=True, slots=True)
class Neo4jRelationship:
    start_node_id: str
    end_node_id: str
    relationship_type: str
    properties: JsonObject


@dataclass(frozen=True, slots=True)
class Neo4jSearchQuery:
    query: str
    top_k: int
    symbols: tuple[str, ...] = ()
    regimes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Neo4jSearchHit:
    document_id: str
    source_id: str
    source_type: str
    title: str
    score: float
    related_entities: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Neo4jGraphStatus:
    healthy: bool
    entity_count: int


class Neo4jDriverProtocol(Protocol):
    async def execute_query(
        self,
        query_: str,
        parameters_: Mapping[str, Any] | None = None,
        *,
        routing_: RoutingControl = RoutingControl.WRITE,
        database_: str | None = None,
    ) -> object: ...

    async def verify_connectivity(self, **config: Any) -> None: ...

    async def close(self) -> None: ...


class Neo4jRagClient:
    """Vendor-specific async Neo4j boundary for the rebuildable RAG graph."""

    def __init__(
        self,
        *,
        settings: Settings,
        driver: Neo4jDriverProtocol | None = None,
    ) -> None:
        auth = None
        if settings.NEO4J_USER and settings.NEO4J_PASSWORD:
            auth = (settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        self._driver = driver or cast(
            Neo4jDriverProtocol,
            AsyncGraphDatabase.driver(settings.NEO4J_URI, auth=auth),
        )
        self._database = settings.NEO4J_DATABASE
        self._projection_name = settings.RAG_GRAPH_PROJECTION_NAME

    async def upsert_projection(
        self,
        *,
        nodes: tuple[Neo4jNode, ...],
        relationships: tuple[Neo4jRelationship, ...],
    ) -> None:
        for node_type in _NODE_LABELS:
            grouped = tuple(node for node in nodes if node.node_type == node_type)
            if not grouped:
                continue
            await self._execute_write(
                node_upsert_query(node_type),
                {
                    "projection": self._projection_name,
                    "rows": [
                        {
                            "node_id": node.node_id,
                            "properties": _neo4j_properties(
                                node.properties, self._projection_name
                            ),
                        }
                        for node in grouped
                    ],
                },
            )
        for relationship_type in _RELATIONSHIP_TYPES:
            grouped_relationships = tuple(
                relationship
                for relationship in relationships
                if relationship.relationship_type == relationship_type
            )
            if not grouped_relationships:
                continue
            await self._execute_write(
                relationship_upsert_query(relationship_type),
                {
                    "projection": self._projection_name,
                    "rows": [
                        {
                            "start_node_id": relationship.start_node_id,
                            "end_node_id": relationship.end_node_id,
                            "properties": _neo4j_properties(
                                relationship.properties, self._projection_name
                            ),
                        }
                        for relationship in grouped_relationships
                    ],
                },
            )

    async def search(
        self,
        query: Neo4jSearchQuery,
    ) -> tuple[Neo4jSearchHit, ...]:
        result = await self._driver.execute_query(
            _GRAPH_SEARCH_QUERY,
            parameters_={
                "projection": self._projection_name,
                "query_terms": _query_terms(query.query),
                "symbols": [symbol.upper() for symbol in query.symbols],
                "regimes": [regime.lower() for regime in query.regimes],
                "limit": query.top_k,
            },
            routing_=RoutingControl.READ,
            database_=self._database,
        )
        return tuple(_search_hit(record) for record in _records(result))

    async def clear_projection(self) -> int:
        result = await self._execute_write(
            "MATCH (node:RagEntity {projection: $projection}) "
            "WITH collect(node) AS nodes, count(node) AS deleted_count "
            "FOREACH (node IN nodes | DETACH DELETE node) "
            "RETURN deleted_count",
            {"projection": self._projection_name},
        )
        records = _records(result)
        return _as_int(_record_value(records[0], "deleted_count", 0)) if records else 0

    async def status(self) -> Neo4jGraphStatus:
        await self._driver.verify_connectivity()
        result = await self._driver.execute_query(
            "MATCH (node:RagEntity {projection: $projection}) "
            "RETURN count(node) AS entity_count",
            parameters_={"projection": self._projection_name},
            routing_=RoutingControl.READ,
            database_=self._database,
        )
        records = _records(result)
        count = _as_int(_record_value(records[0], "entity_count", 0)) if records else 0
        return Neo4jGraphStatus(healthy=True, entity_count=count)

    async def close(self) -> None:
        await self._driver.close()

    async def _execute_write(
        self,
        query: str,
        parameters: Mapping[str, Any],
    ) -> object:
        return await self._driver.execute_query(
            query,
            parameters_=parameters,
            routing_=RoutingControl.WRITE,
            database_=self._database,
        )


def node_upsert_query(node_type: str) -> str:
    return (
        f"UNWIND $rows AS row MERGE (node:RagEntity:{_NODE_LABELS[node_type]} "
        "{projection: $projection, node_id: row.node_id}) "
        "SET node += row.properties "
        "RETURN count(node) AS upserted_count"
    )


def relationship_upsert_query(
    relationship_type: str,
) -> str:
    return (
        "UNWIND $rows AS row "
        "MATCH (start:RagEntity {projection: $projection, node_id: row.start_node_id}) "
        "MATCH (end:RagEntity {projection: $projection, node_id: row.end_node_id}) "
        f"MERGE (start)-[relationship:{_RELATIONSHIP_TYPES[relationship_type]}]->(end) "
        "SET relationship += row.properties "
        "RETURN count(relationship) AS upserted_count"
    )


def _neo4j_properties(
    properties: JsonObject,
    projection_name: str,
) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in properties.items():
        if value is None or isinstance(value, (str, int, float, bool)):
            normalized[key] = value
        elif isinstance(value, (list, tuple)):
            normalized[key] = [
                item for item in value if isinstance(item, (str, int, float, bool))
            ]
    normalized["projection"] = projection_name
    return normalized


def _query_terms(query: str) -> list[str]:
    return [term.lower() for term in query.split() if len(term.strip()) >= 3]


def _records(result: object) -> tuple[object, ...]:
    records = getattr(result, "records", ())
    return tuple(records) if records is not None else ()


def _record_value(record: object, key: str, default: object) -> object:
    if isinstance(record, Mapping):
        return record.get(key, default)
    if hasattr(record, "get"):
        getter = record.get
        return getter(key, default)
    return default


def _as_int(value: object) -> int:
    if isinstance(value, (str, int, float)):
        return int(value)
    return 0


def _as_float(value: object) -> float:
    if isinstance(value, (str, int, float)):
        return float(value)
    return 0.0


def _search_hit(record: object) -> Neo4jSearchHit:
    entities = _record_value(record, "related_entities", ())
    related = (
        tuple(str(value) for value in entities) if isinstance(entities, list) else ()
    )
    return Neo4jSearchHit(
        document_id=str(_record_value(record, "document_id", "")),
        source_id=str(_record_value(record, "source_id", "")),
        source_type=str(_record_value(record, "source_type", "")),
        title=str(_record_value(record, "title", "")),
        score=_as_float(_record_value(record, "score", 0.0)),
        related_entities=related,
    )


_GRAPH_SEARCH_QUERY = """
MATCH (document:RagEntity {projection: $projection})
WHERE document.document_id IS NOT NULL
OPTIONAL MATCH (document)-[]-(related:RagEntity {projection: $projection})
WITH document,
     [value IN collect(DISTINCT coalesce(
         properties(related)["symbol"],
         properties(related)["regime"],
         properties(related)["theme"],
         properties(related)["title"]
     )) WHERE value IS NOT NULL] AS related_entities
WITH document, related_entities,
     size([term IN $query_terms WHERE
         toLower(coalesce(document.search_text, '')) CONTAINS term OR
         any(entity IN related_entities WHERE
             toLower(toString(entity)) CONTAINS term)]) AS matched_terms
WHERE (size($query_terms) = 0 OR matched_terms > 0)
  AND (size($symbols) = 0 OR any(symbol IN $symbols WHERE
       symbol IN coalesce(document.symbols, []) OR symbol IN related_entities))
  AND (size($regimes) = 0 OR any(regime IN $regimes WHERE
       any(entity IN related_entities WHERE toLower(toString(entity)) = regime)))
RETURN document.document_id AS document_id,
       document.source_id AS source_id,
       document.source_type AS source_type,
       document.title AS title,
       toFloat(matched_terms + size(related_entities) * 0.01) AS score,
       related_entities
ORDER BY score DESC, document.generated_at DESC, document.document_id
LIMIT $limit
"""
