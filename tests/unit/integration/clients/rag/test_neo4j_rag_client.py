from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from typing import Mapping

import pytest
from neo4j import RoutingControl

from config.settings import Settings
from integration.clients.rag.neo4j_rag_client import Neo4jNode
from integration.clients.rag.neo4j_rag_client import Neo4jRagClient
from integration.clients.rag.neo4j_rag_client import Neo4jRelationship
from integration.clients.rag.neo4j_rag_client import Neo4jSearchQuery
from integration.clients.rag.neo4j_rag_client import _GRAPH_SEARCH_QUERY
from integration.clients.rag.neo4j_rag_client import node_upsert_query
from integration.clients.rag.neo4j_rag_client import relationship_upsert_query
from integration.providers.rag.graph_projection_models import GraphNodeType
from integration.providers.rag.graph_projection_models import GraphRelationshipType


@dataclass(frozen=True)
class FakeResult:
    records: tuple[Mapping[str, object], ...] = ()


class FakeDriver:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Mapping[str, Any], RoutingControl, str | None]] = []
        self.closed = False
        self.verified = False

    async def execute_query(
        self,
        query_: str,
        parameters_: Mapping[str, Any] | None = None,
        *,
        routing_: RoutingControl = RoutingControl.WRITE,
        database_: str | None = None,
    ) -> object:
        self.calls.append((query_, parameters_ or {}, routing_, database_))
        if "RETURN document.document_id" in query_:
            return FakeResult(
                records=(
                    {
                        "document_id": "document-1",
                        "source_id": "report-1",
                        "source_type": "morning_report",
                        "title": "Morning Report",
                        "score": 2.01,
                        "related_entities": ["SPY", "risk_on"],
                    },
                )
            )
        return FakeResult()

    async def verify_connectivity(self, **config: Any) -> None:
        self.verified = True

    async def close(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_neo4j_client_builds_whitelisted_idempotent_cypher_payloads() -> None:
    driver = FakeDriver()
    client = Neo4jRagClient(settings=Settings(), driver=driver)

    await client.upsert_projection(
        nodes=(
            Neo4jNode(
                node_id="document:1",
                node_type=GraphNodeType.REPORT.value,
                properties={"title": "Morning Report", "nested": {"ignored": True}},
            ),
            Neo4jNode(
                node_id="symbol:SPY",
                node_type=GraphNodeType.SYMBOL.value,
                properties={"symbol": "SPY"},
            ),
        ),
        relationships=(
            Neo4jRelationship(
                start_node_id="document:1",
                end_node_id="symbol:SPY",
                relationship_type=GraphRelationshipType.MENTIONS.value,
                properties={},
            ),
        ),
    )

    assert len(driver.calls) == 3
    report_query, report_parameters, _, database = driver.calls[0]
    assert (
        "MERGE (node:RagEntity:Report {projection: $projection, node_id: row.node_id})"
    ) in report_query
    assert report_parameters["projection"] == "polaris_rag"
    assert report_parameters["rows"][0]["properties"] == {
        "title": "Morning Report",
        "projection": "polaris_rag",
    }
    assert database == "neo4j"
    relationship_query = driver.calls[2][0]
    assert "MATCH (start:RagEntity {projection: $projection" in relationship_query
    assert "MATCH (end:RagEntity {projection: $projection" in relationship_query
    assert "MERGE (start)-[relationship:MENTIONS]->(end)" in relationship_query


@pytest.mark.asyncio
async def test_neo4j_client_search_normalizes_graph_hits() -> None:
    driver = FakeDriver()
    client = Neo4jRagClient(settings=Settings(), driver=driver)

    hits = await client.search(
        Neo4jSearchQuery(
            query="SPY breadth",
            symbols=("spy",),
            regimes=("Risk_On",),
            top_k=3,
        )
    )

    assert hits[0].document_id == "document-1"
    assert hits[0].related_entities == ("SPY", "risk_on")
    _, parameters, routing, _ = driver.calls[0]
    assert parameters["symbols"] == ["SPY"]
    assert parameters["regimes"] == ["risk_on"]
    assert parameters["query_terms"] == ["spy", "breadth"]
    assert routing is RoutingControl.READ


def test_cypher_templates_only_accept_typed_graph_enums() -> None:
    assert "RagEntity:AgentSignal" in node_upsert_query(
        GraphNodeType.AGENT_SIGNAL.value
    )
    assert "relationship:SUPPORTS" in relationship_upsert_query(
        GraphRelationshipType.SUPPORTS.value
    )
    assert "relationship:DECISION_SELECTED_HYPOTHESIS" in relationship_upsert_query(
        GraphRelationshipType.DECISION_SELECTED_HYPOTHESIS.value
    )


def test_graph_search_query_uses_dynamic_optional_related_properties() -> None:
    assert "related.regime" not in _GRAPH_SEARCH_QUERY
    assert "related.theme" not in _GRAPH_SEARCH_QUERY
    assert 'properties(related)["regime"]' in _GRAPH_SEARCH_QUERY
    assert 'properties(related)["theme"]' in _GRAPH_SEARCH_QUERY
