"""LangChain Qdrant vector-store configuration."""

import os
from functools import lru_cache

from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient, models

from rag.embeddings import embedding_dimension, get_embeddings


def collection_name() -> str:
    return os.getenv("QDRANT_COLLECTION", "cricket_events")


@lru_cache(maxsize=1)
def get_qdrant_client() -> QdrantClient:
    """Provide the client used by LangChain and the Django health endpoint."""
    return QdrantClient(url=os.getenv("QDRANT_URL", "http://qdrant:6333"), timeout=30)


def ensure_collection(client: QdrantClient | None = None) -> QdrantClient:
    """Create the LangChain document collection once, using cosine distance."""
    client = client or get_qdrant_client()
    if not client.collection_exists(collection_name()):
        client.create_collection(
            collection_name=collection_name(),
            vectors_config=models.VectorParams(
                size=embedding_dimension(),
                distance=models.Distance.COSINE,
            ),
        )
    return client


@lru_cache(maxsize=1)
def get_vector_store() -> QdrantVectorStore:
    """Return the LangChain store backed by the configured Qdrant server."""
    return QdrantVectorStore(
        client=ensure_collection(),
        collection_name=collection_name(),
        embedding=get_embeddings(),
        content_payload_key="page_content",
        metadata_payload_key="metadata",
    )
