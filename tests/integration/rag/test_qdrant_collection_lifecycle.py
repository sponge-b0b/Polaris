from __future__ import annotations

from typing import cast
from uuid import uuid4

import pytest
from qdrant_client import AsyncQdrantClient

from config.settings import Settings
from integration.clients.rag.qdrant_rag_client import QdrantRagClient
from integration.clients.rag.qdrant_rag_client import QdrantClientProtocol


@pytest.mark.asyncio
async def test_live_qdrant_collection_lifecycle_when_available() -> None:
    settings = Settings()
    raw_client = AsyncQdrantClient(
        url=settings.qdrant_url,
        timeout=2,
        check_compatibility=False,
    )
    available = False
    collection_name = f"polaris_rag_lifecycle_test_{uuid4().hex}"

    try:
        try:
            await raw_client.get_collections()
            available = True
        except Exception as exc:
            pytest.skip(f"Qdrant is not available at {settings.qdrant_url}: {exc}")

        client = QdrantRagClient(
            settings=settings,
            client=cast(QdrantClientProtocol, raw_client),
        )
        ensured = await client.ensure_collection(
            collection_name=collection_name,
            vector_size=3,
        )
        recreated = await client.recreate_collection(
            collection_name=collection_name,
            vector_size=3,
        )

        assert ensured.created is True
        assert ensured.healthy is True
        assert ensured.vector_size == 3
        assert recreated.created is True
        assert recreated.healthy is True
        assert recreated.vector_size == 3
    finally:
        try:
            if available and await raw_client.collection_exists(collection_name):
                await raw_client.delete_collection(collection_name)
        finally:
            await raw_client.close()
