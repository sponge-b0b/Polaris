from __future__ import annotations

from core.telemetry.emitters.integration_telemetry import IntegrationTelemetry
from integration.clients.rag.neo4j_rag_client import Neo4jNode
from integration.clients.rag.neo4j_rag_client import Neo4jRagClient
from integration.clients.rag.neo4j_rag_client import Neo4jRelationship
from integration.clients.rag.neo4j_rag_client import Neo4jSearchQuery
from integration.providers.provider_telemetry import record_provider_call
from integration.providers.rag.graph_projection_models import GraphProjection
from integration.providers.rag.graph_projection_models import GraphSearchQuery
from integration.providers.rag.graph_projection_models import GraphSearchResult
from integration.providers.rag.graph_projection_models import GraphStoreStatus
from integration.providers.rag.graph_projection_provider import GraphProjectionProvider


class Neo4jGraphProjectionProvider(GraphProjectionProvider):
    """Platform-facing graph projection provider backed by Neo4j."""

    def __init__(
        self,
        client: Neo4jRagClient,
        telemetry: IntegrationTelemetry | None = None,
    ) -> None:
        self._client = client
        self._telemetry = telemetry

    async def upsert_projection(self, projection: GraphProjection) -> None:
        await record_provider_call(
            self._telemetry,
            self.__class__.__name__,
            "upsert_projection",
            lambda: self._client.upsert_projection(
                nodes=tuple(
                    Neo4jNode(
                        node_id=node.node_id,
                        node_type=node.node_type.value,
                        properties=node.properties,
                    )
                    for node in projection.nodes
                ),
                relationships=tuple(
                    Neo4jRelationship(
                        start_node_id=relationship.start_node_id,
                        end_node_id=relationship.end_node_id,
                        relationship_type=relationship.relationship_type.value,
                        properties=relationship.properties,
                    )
                    for relationship in projection.relationships
                ),
            ),
            attributes={
                "document_id": projection.document_id,
                "node_count": len(projection.nodes),
                "relationship_count": len(projection.relationships),
            },
        )

    async def search(
        self,
        query: GraphSearchQuery,
    ) -> tuple[GraphSearchResult, ...]:
        hits = await record_provider_call(
            self._telemetry,
            self.__class__.__name__,
            "search",
            lambda: self._client.search(
                Neo4jSearchQuery(
                    query=query.query,
                    top_k=query.top_k,
                    symbols=query.symbols,
                    regimes=query.regimes,
                )
            ),
            attributes={"top_k": query.top_k},
        )
        return tuple(
            GraphSearchResult(
                document_id=hit.document_id,
                source_id=hit.source_id,
                source_type=hit.source_type,
                title=hit.title,
                score=hit.score,
                related_entities=hit.related_entities,
            )
            for hit in hits
        )

    async def clear_projection(self) -> int:
        return await record_provider_call(
            self._telemetry,
            self.__class__.__name__,
            "clear_projection",
            self._client.clear_projection,
        )

    async def status(self) -> GraphStoreStatus:
        status = await record_provider_call(
            self._telemetry,
            self.__class__.__name__,
            "status",
            self._client.status,
        )
        return GraphStoreStatus(
            healthy=status.healthy,
            entity_count=status.entity_count,
        )
