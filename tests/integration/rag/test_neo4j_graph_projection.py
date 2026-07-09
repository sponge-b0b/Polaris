from __future__ import annotations

import pytest

from config.settings import Settings
from integration.clients.rag.neo4j_rag_client import Neo4jNode
from integration.clients.rag.neo4j_rag_client import Neo4jRagClient
from integration.clients.rag.neo4j_rag_client import Neo4jRelationship
from integration.clients.rag.neo4j_rag_client import Neo4jSearchQuery
from integration.providers.rag.graph_projection_models import GraphNodeType
from integration.providers.rag.graph_projection_models import GraphRelationshipType


@pytest.mark.asyncio
async def test_live_neo4j_projection_is_idempotent_and_retrievable() -> None:
    settings = Settings(RAG_GRAPH_PROJECTION_NAME="polaris_rag_integration_test")
    client = Neo4jRagClient(settings=settings)
    try:
        await client.clear_projection()
        nodes = (
            Neo4jNode(
                node_id="document:integration-report",
                node_type=GraphNodeType.REPORT.value,
                properties={
                    "document_id": "integration-report",
                    "source_id": "report-1",
                    "source_type": "morning_report",
                    "title": "Breadth Integration Report",
                    "generated_at": "2026-06-24T00:00:00+00:00",
                    "symbols": ["SPY"],
                    "search_text": "spy breadth risk on",
                },
            ),
            Neo4jNode(
                node_id="symbol:integration-SPY",
                node_type=GraphNodeType.SYMBOL.value,
                properties={"symbol": "SPY", "title": "SPY"},
            ),
        )
        relationships = (
            Neo4jRelationship(
                start_node_id="document:integration-report",
                end_node_id="symbol:integration-SPY",
                relationship_type=GraphRelationshipType.MENTIONS.value,
                properties={},
            ),
        )

        await client.upsert_projection(nodes=nodes, relationships=relationships)
        await client.upsert_projection(nodes=nodes, relationships=relationships)
        status = await client.status()
        hits = await client.search(
            Neo4jSearchQuery(
                query="SPY breadth",
                symbols=("SPY",),
                top_k=3,
            )
        )

        assert status.healthy is True
        assert status.entity_count == 2
        assert len(hits) == 1
        assert hits[0].document_id == "integration-report"
        assert hits[0].related_entities == ("SPY",)
    finally:
        await client.clear_projection()
        await client.close()
