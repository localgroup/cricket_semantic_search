"""LangChain semantic retrieval plus exact MongoDB event queries."""

import os

from langchain_core.documents import Document
from pymongo import MongoClient
from qdrant_client.models import FieldCondition, Filter, MatchValue

from rag.vector_store import get_vector_store

FILTER_FIELDS = ("match_id", "player", "team", "event_type", "status")


def _qdrant_filter(filters: dict | None) -> Filter | None:
    conditions = []
    for field in FILTER_FIELDS:
        value = (filters or {}).get(field)
        if value:
            conditions.append(
                FieldCondition(key=f"metadata.{field}", match=MatchValue(value=value))
            )
    return Filter(must=conditions) if conditions else None


def _event_from_document(document: Document, score: float) -> dict:
    metadata = document.metadata
    return {
        "event_id": str(metadata.get("event_id", "")),
        "score": float(score),
        "match_id": metadata.get("match_id"),
        "team": metadata.get("team"),
        "player": metadata.get("player"),
        "event_type": metadata.get("event_type"),
        "runs": metadata.get("runs"),
        "over": metadata.get("over"),
        "status": metadata.get("status"),
        "timestamp": metadata.get("timestamp"),
        "commentary": metadata.get("commentary"),
        "role": metadata.get("role"),
        "venue": metadata.get("venue"),
        "weather": metadata.get("weather"),
        "quality_flags": metadata.get("quality_flags", []),
        "search_text": metadata.get("search_text", document.page_content),
    }


def search_events(query: str, top_k: int = 5, filters: dict | None = None) -> list[dict]:
    """Retrieve semantically similar event documents through LangChain Qdrant."""
    if not query or not query.strip():
        raise ValueError("query cannot be empty")

    matches = get_vector_store().similarity_search_with_score(
        query.strip(),
        k=max(1, min(top_k, 20)),
        filter=_qdrant_filter(filters),
    )
    return [_event_from_document(document, score) for document, score in matches]


def get_stats() -> dict:
    mongo = MongoClient(
        os.getenv("MONGODB_URI", "mongodb://mongodb:27017"),
        serverSelectionTimeoutMS=5000,
    )
    try:
        collection = mongo[os.getenv("MONGODB_DATABASE", "cricket_rag")][
            os.getenv("MONGODB_COLLECTION", "cricket_events")
        ]
        return {
            "total_events": collection.count_documents({}),
            "matches": list(collection.distinct("match_id")),
            "event_types": list(
                collection.aggregate(
                    [
                        {"$group": {"_id": "$event_type", "count": {"$sum": 1}}},
                        {"$sort": {"count": -1}},
                    ]
                )
            ),
            "statuses": list(
                collection.aggregate(
                    [
                        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
                        {"$sort": {"count": -1}},
                    ]
                )
            ),
            "quality_flagged_events": collection.count_documents(
                {"quality_flags.0": {"$exists": True}}
            ),
        }
    finally:
        mongo.close()


def exact_events(params: dict) -> list[dict]:
    """MongoDB-backed exact filters for non-semantic API queries."""
    mongo = MongoClient(
        os.getenv("MONGODB_URI", "mongodb://mongodb:27017"),
        serverSelectionTimeoutMS=5000,
    )
    try:
        collection = mongo[os.getenv("MONGODB_DATABASE", "cricket_rag")][
            os.getenv("MONGODB_COLLECTION", "cricket_events")
        ]
        query = {key: value for key, value in params.items() if key in FILTER_FIELDS and value}
        documents = list(
            collection.find(query, {"_id": 0, "raw_line": 0}).sort("timestamp", 1).limit(100)
        )
        for document in documents:
            if document.get("timestamp"):
                document["timestamp"] = document["timestamp"].isoformat()
        return documents
    finally:
        mongo.close()
