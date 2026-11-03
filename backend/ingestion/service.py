"""Idempotent event-level MongoDB + Qdrant ingestion."""
import os
import uuid
from pathlib import Path
from langchain_core.documents import Document
from pymongo import MongoClient, UpdateOne
from rag.vector_store import get_vector_store

def ingest_file(path: str | Path) -> dict:
    from ingestion.parser import parse_text_file
    events = parse_text_file(path)
    mongo = MongoClient(os.getenv("MONGODB_URI", "mongodb://mongodb:27017"), serverSelectionTimeoutMS=10000)
    try:
        db = mongo[os.getenv("MONGODB_DATABASE", "cricket_rag")]
        collection = db[os.getenv("MONGODB_COLLECTION", "cricket_events")]
        collection.create_index("event_id", unique=True)
        for field in ("match_id", "player", "team", "event_type", "timestamp", "status", "over"):
            collection.create_index(field)
        operations = []
        for event in events:
            doc = dict(event)
            doc["timestamp"] = event["timestamp"]
            operations.append(UpdateOne({"event_id": event["event_id"]}, {"$set": doc}, upsert=True))
        result = collection.bulk_write(operations, ordered=False) if operations else None
        documents = []
        ids = []
        for event in events:
            metadata = {
                key: (value.isoformat() if hasattr(value, "isoformat") else value)
                for key, value in event.items()
                if key != "raw_line"
            }
            documents.append(Document(page_content=event["search_text"], metadata=metadata))
            ids.append(str(uuid.uuid5(uuid.NAMESPACE_URL, "cricket-event:" + event["event_id"])))
        # LangChain delegates idempotent upserts to Qdrant; IDs remain stable per event.
        get_vector_store().add_documents(documents, ids=ids)
        output = Path(os.getenv("OUTPUT_DIR", "/app/output"))
        output.mkdir(parents=True, exist_ok=True)
        import json
        (output / "parsed_events.json").write_text(
            json.dumps([{**e, "timestamp": e["timestamp"].isoformat()} for e in events], ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        return {
            "status": "ingested",
            "source_file": Path(path).name,
            "parsed_events": len(events),
            "mongo_upserted": getattr(result, "upserted_count", 0) if result else 0,
            "mongo_modified": getattr(result, "modified_count", 0) if result else 0,
            "qdrant_points_upserted": len(documents),
            "quality_flagged_events": sum(bool(e["quality_flags"]) for e in events),
            "output_json": str(output / "parsed_events.json"),
        }
    finally:
        mongo.close()
