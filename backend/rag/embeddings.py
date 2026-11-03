"""LangChain embedding configuration for local CPU inference."""

import os
from functools import lru_cache

from langchain_huggingface import HuggingFaceEmbeddings

DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
BATCH_SIZE = 32


@lru_cache(maxsize=1)
def get_embeddings() -> HuggingFaceEmbeddings:
    """Create one CPU-only LangChain embedding provider for the process."""
    return HuggingFaceEmbeddings(
        model_name=os.getenv("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL),
        model_kwargs={"device": "cpu"},
        encode_kwargs={"batch_size": BATCH_SIZE, "normalize_embeddings": True},
    )


def embedding_dimension() -> int:
    """Derive the configured model's vector size before creating a collection."""
    return len(get_embeddings().embed_query("cricket embedding dimension probe"))
