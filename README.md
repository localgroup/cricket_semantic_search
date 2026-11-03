# Cricket Log Semantic Search

A local-first semantic search and RAG application for the supplied cricket match logs. It parses each log line into a structured event, stores event records in MongoDB, indexes event embeddings in Qdrant, exposes a Django REST API, serves a Dash browser UI, and includes an MCP adapter for AI clients.

## Architecture: exactly one container

This project follows a single-container deployment: **one container runs the application, MongoDB, and Qdrant**. Supervisor manages the application and database processes; `tini` handles container signals. Dash serves the browser UI on port 8050 and communicates with the Django REST API on port 8000.

```text
Browser / API client
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│ ONE CONTAINER: cricket-search                           │
│                                                         │
│  Dash UI → Django API ─── MongoDB (localhost:27017)     │
│          │                                              │
│          ├── Embeddings + RAG ─ Qdrant (localhost:6333) │
│          │                                              │
│          └── MCP stdio adapter (launched on demand)     │
└─────────────────────────────────────────────────────────┘
        │
        ├── ./state/combined/mongodb  (persistent MongoDB data)
        ├── ./state/combined/qdrant   (persistent vector data)
        ├── ./output         (parsed event export)
        └── model_cache      (downloaded embedding model)
```


## Included dataset and parser

`data/cricket_log.txt` is the source file. It contains 500 event lines across 10 matches. The parser creates one structured record per non-blank line and preserves the source values. Optional role, or fields are populated only when clearly present in commentary; otherwise they remain null.

Each record contains:
- `event_id`, `line_number`, `timestamp`
- `match_id`, `team`, `player`, `event_type`
- `runs`, `over`, `status`, `commentary`
- optional `role`, `venue`, `weather`
- `quality_flags`, `raw_line`, and a combined `search_text`

Potential data issues are flagged rather than silently corrected (for example, a `six hit` with zero runs or an `LBW given` with positive runs). The parser does not assume the source values are correct cricket scoring.

## Requirements

- Docker Engine with Compose, or Podman with a compatible `podman compose` provider
- Internet access for the first image build and embedding-model download
- Optional Groq API key for LLM-generated chat answers. Without it, semantic retrieval still works and chat returns retrieved evidence.

## Build and run

### Docker

```bash
cp .env.example .env
# GROQ_API_KEY is optional and enables LLM-generated chat answers.
docker compose up --build -d
docker compose ps
docker compose logs -f cricket-search
```

Open the Dash frontend at **http://localhost:8050**. The Django REST API is available at **http://localhost:8000**.

### Podman

```bash
cp .env.example .env
podman compose up --build -d
podman compose ps
podman compose logs -f cricket-search
```

Open the Dash frontend at **http://localhost:8050**. The Django REST API is available at **http://localhost:8000**.

The first build downloads Python packages plus pinned MongoDB and Qdrant binaries. The application installs the CPU-only PyTorch wheel and uses Sentence Transformers locally. The selected embedding-model weights are downloaded into the persistent `model_cache` volume on first ingestion; no event text or search query is sent to Hugging Face for embedding.

The default embedding model is `sentence-transformers/all-MiniLM-L6-v2` unless `EMBEDDING_MODEL` is set. After changing the model, re-ingest the dataset so all stored vectors are regenerated with the same model:

```bash
docker compose exec cricket-search python manage.py ingest_logs
```


### If a previous build filled disk space (Podman on Windows)

Stop an in-progress build with `Ctrl+C`. To remove only dangling images left by an interrupted build, run:

```cmd
podman image prune -f
podman system df
```

Do **not** use `podman system prune --volumes`: it can delete persisted database data. `podman image prune -f` only removes dangling images.

## Ingest the logs (manual command, not a public endpoint)

Ingestion is deliberately an offline/manual command; the public REST API does not include an ingestion route.

```bash
docker compose exec cricket-search python manage.py ingest_logs
# Podman:
podman compose exec cricket-search python manage.py ingest_logs
```

The command parses `data/cricket_log.txt`, upserts event records into MongoDB, embeds each event, upserts vectors into Qdrant, and writes `output/parsed_events.json` for inspection. Rerunning the command is safe for the same source file.

To ingest a different file, copy it into `data/` and run:

```bash
docker compose exec cricket-search python manage.py ingest_logs --file /app/data/another_log.txt
```

## Persistence and migration safety

The combined application uses only `./state/combined/mongodb` and
`./state/combined/qdrant`. Those paths are intentionally different from the
standalone `cricket-mongodb` and `cricket-qdrant` containers' storage. Do not
mount a storage directory into two running MongoDB or Qdrant processes.

The existing standalone services are preserved as the rollback copy. The
audited Qdrant collection currently has zero points, while the canonical
`data/cricket_log.txt` contains 500 events. For this supplied dataset, the safe
transition is an isolated re-index rather than a raw database-file copy:

1. Leave `cricket-mongodb` and `cricket-qdrant` running and unchanged.
2. Build and start the combined application only after approving the build.
   It will use the new `state/combined` directories and cannot contend with the
   standalone services' storage.
3. Confirm `GET /api/health/` succeeds, then explicitly run the manual
   ingestion command above. This creates MongoDB records and Qdrant vectors in
   the new, isolated stores.
4. Verify `GET /api/stats/` reports 500 events and run a semantic search. Keep
   the standalone containers as the rollback copy until those checks pass.

If the standalone MongoDB contains records that are not reproducible from
`data/cricket_log.txt`, stop here and perform an approved logical export/import
instead. Never copy live WiredTiger or Qdrant storage files between running
containers.

## REST API

All API responses are JSON.

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/health/` | MongoDB/Qdrant health |
| `GET` | `/api/stats/` | Event total, matches, event-type/status breakdowns, quality flags |
| `POST` | `/api/search/` | Qdrant semantic similarity search with optional exact metadata filters |
| `POST` | `/api/chat/` | Retrieve evidence and optionally generate a grounded answer using Groq |
| `GET` | `/api/events/` | MongoDB exact metadata filters |

Example semantic search:

```bash
curl -X POST http://localhost:8000/api/search/ \
  -H 'Content-Type: application/json' \
  -d '{"query":"disputed wicket decisions","top_k":5,"filters":{"match_id":"MATCH001"}}'
```

Example chat:

```bash
curl -X POST http://localhost:8000/api/chat/ \
  -H 'Content-Type: application/json' \
  -d '{"question":"Find events related to disputed decisions","top_k":5}'
```

Example exact MongoDB query:

```bash
curl 'http://localhost:8000/api/events/?match_id=MATCH001&status=disputed'
```

Use MongoDB for exact filters/counts and Qdrant for semantic similarity.

## MCP integration

The MCP adapter uses the REST API, keeping search and chat logic in one place. It exposes:
- `cricket_stats`
- `search_cricket_events`
- `ask_cricket_logs`
- `list_cricket_events`

MCP uses stdio, so the server is launched on demand by an MCP-capable client rather than exposed as a separate network service. With the app running, test the server interactively in a terminal:

```bash
docker compose exec cricket-search python /app/mcp_server/server.py
# Podman:
podman compose exec cricket-search python /app/mcp_server/server.py
```

This command will wait for MCP protocol messages on stdin.

## Tests and validation

The project includes parser tests and a dataset validation script.

```bash
# Quick parser/dataset validation (does not require databases or external services)
python scripts/validate_dataset.py

# In a Python 3.11 virtual environment:
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cd backend
python manage.py test api rag
python manage.py check
```

The parser validation should report 500 parsed events, 10 matches, and 10 event types.
