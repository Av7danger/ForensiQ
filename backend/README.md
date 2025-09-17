# Backend - UFDR Investigator 

This folder contains the complete backend system for UFDR forensic investigation, including storage, indexing, retrieval, and query API.

## Phases Implemented

- **Phase 2**: Storage & Indexing (PostgreSQL + OpenSearch)
- **Phase 4**: Retrieval (Hybrid) + Local Summarizer (FastAPI + HuggingFace)

## Requirements

Recommended Python 3.11+ virtualenv.

Install all requirements:
```bash
pip install sqlalchemy psycopg2-binary opensearch-py python-dotenv
pip install sentence-transformers faiss-cpu opensearch-py transformers
pip install fastapi pydantic uvicorn
```

> For SQLite demo only: `psycopg2-binary` is optional.  
> For GPU acceleration: replace `faiss-cpu` with `faiss-gpu`.

## Files

- `models.py` - SQLAlchemy ORM models (Message, Contact, Call, File)
- `db.py` - DB connection helpers and `init_db()`
- `etl_load.py` - CLI script to upsert JSONL into the DB
- `opensearch_index.py` - CLI script to index messages.jsonl into OpenSearch
- `retriever.py` - Hybrid search combining OpenSearch + FAISS
- `app/query.py` - FastAPI `/query` endpoint with local summarization

## Setup (PostgreSQL + OpenSearch + FAISS)

1. Start PostgreSQL and OpenSearch (via Docker or locally).

2. Export environment variables:

```bash
export DATABASE_URL=postgresql://user:pass@localhost:5432/ufdr
export OPENSEARCH_URL=http://localhost:9200
export FAISS_INDEX_DIR=./vectors
```

3. Initialize DB (optional — etl_load will create tables if needed):

```bash
python -c "from backend.db import init_db; init_db()"
```

## Phase 2: ETL & Indexing

### Load parsed JSONL into DB

Assuming Phase 1 created parsed JSONL under `./output/CASE-001/parsed/`:

```bash
python backend/etl_load.py --input ./output/CASE-001/parsed/ --case CASE-001
```

This will upsert `messages.jsonl`, `contacts.jsonl`, `calls.jsonl`, and `blobs_manifest.jsonl` into the DB.

### Index messages into OpenSearch

```bash
export OPENSEARCH_URL=http://localhost:9200
python backend/opensearch_index.py --input ./output/CASE-001/parsed/messages.jsonl --index messages
```

Test keyword search:

```bash
curl -s "http://localhost:9200/messages/_search?q=crypto&pretty"
```

### Generate FAISS embeddings (Phase 3 requirement)

```bash
python nlp/embeddings_worker.py \
  --input ./output/CASE-001/parsed/messages.jsonl \
  --out ./vectors/
```

## Phase 4: Query API

### Start FastAPI server

```bash
# Install FastAPI dependencies
pip install fastapi uvicorn

# Start development server
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### Query API endpoints

#### POST /query - Hybrid search with optional summarization

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "q": "find bitcoin payments",
    "limit": 5,
    "summarize": false
  }'
```

Example response:

```json
{
  "query": "find bitcoin payments",
  "summary": null,
  "hits": [
    {
      "message_id": "msg_12345",
      "case_id": "CASE-001",
      "snippet": "Sent 0.5 BTC to wallet address 1A1zP1eP5QGefi...",
      "sender": "+15551234567",
      "recipient": "+15559876543",
      "timestamp": "2024-01-15T10:30:00Z",
      "score": 0.95,
      "sources": ["opensearch", "faiss"],
      "opensearch_score": 0.8,
      "faiss_score": 0.7
    }
  ],
  "total_hits": 1,
  "sources_used": ["opensearch", "faiss"]
}
```

#### POST /query with summarization

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "q": "suspicious money transfers",
    "limit": 10,
    "summarize": true
  }'
```

Response includes local HuggingFace-generated summary:

```json
{
  "query": "suspicious money transfers",
  "summary": "The messages contain several references to large cash transfers and cryptocurrency payments. Multiple participants discussed moving funds through various channels and mentioned concerns about detection.",
  "hits": [...],
  "total_hits": 8,
  "sources_used": ["opensearch", "faiss"]
}
```

#### GET /status - Component health check

```bash
curl http://localhost:8000/status
```

Returns availability of OpenSearch, FAISS, and summarization models.

#### GET /health - Simple health check

```bash
curl http://localhost:8000/health
```

## Hybrid Search Features

- **Keyword Search**: OpenSearch finds exact term matches, phrase queries
- **Semantic Search**: FAISS finds conceptually similar messages using embeddings
- **Score Fusion**: Weighted combination of keyword + semantic scores
- **Multi-source Boost**: Higher scores for messages found by both methods
- **Graceful Degradation**: Works with only OpenSearch or only FAISS available

## Local Summarization

- **Offline-capable**: Uses HuggingFace transformers (no external APIs)
- **Models**: facebook/bart-large-cnn (primary), t5-small (fallback)
- **Context**: Summarizes top-5 search result snippets
- **Token Limits**: Max 512 tokens input, ~150 tokens output

## Notes & Tips

- For demo runs, fallback DB is `sqlite:///ufdr.db`. For production use PostgreSQL.
- The ETL upserts by `id` — re-running is idempotent (won't duplicate rows).
- OpenSearch index uses simple mapping suitable for text queries; tune analyzers for your language/requirements.
- If something fails, enable debug SQL logs by setting `echo=True` in `db.get_engine`.
- FAISS requires embeddings from Phase 3 NLP module to be generated first.
- Summarization models are downloaded automatically on first use (~500MB-2GB).

## Troubleshooting

- If OpenSearch can't connect, check `OPENSEARCH_URL` and that service is running.
- If PostgreSQL fails, confirm `DATABASE_URL` credentials and DB server status.
- If FAISS search fails, ensure embeddings were generated and saved to `FAISS_INDEX_DIR`.
- If summarization fails, check available memory (models require 2-4GB RAM).

## Requirements File

Add to your repo root `requirements.txt`:

```text
# Core backend
sqlalchemy>=1.4
psycopg2-binary>=2.9
opensearch-py>=2.1.0
python-dotenv>=0.21.0

# Phase 4: Retrieval & API
sentence-transformers>=2.2.0
faiss-cpu>=1.7.0
transformers>=4.21.0
torch>=1.12.0
fastapi>=0.100.0
pydantic>=2.0.0
uvicorn>=0.23.0
```

## Quick Start / Sanity Run

1. Put parsed JSONL from Phase 1 into `./output/CASE-001/parsed/`:
   - `messages.jsonl`, `contacts.jsonl`, `calls.jsonl`, `blobs_manifest.jsonl`

2. (Optional) Set environment variables:

```bash
export DATABASE_URL=postgresql://user:pass@localhost:5432/ufdr
export OPENSEARCH_URL=http://localhost:9200
export FAISS_INDEX_DIR=./vectors
```

If not set, defaults: `sqlite:///ufdr.db`, `http://localhost:9200`, `./vectors`

3. Initialize DB and run ETL:

```bash
python -c "from backend.db import init_db; init_db()"
python backend/etl_load.py --input ./output/CASE-001/parsed/ --case CASE-001
```

4. Index messages into OpenSearch:

```bash
python backend/opensearch_index.py --input ./output/CASE-001/parsed/messages.jsonl --index messages
```

5. Generate FAISS embeddings:

```bash
python nlp/embeddings_worker.py --input ./output/CASE-001/parsed/messages.jsonl --out ./vectors/
```

6. Start query API:

```bash
uvicorn backend.main:app --reload
```

7. Test hybrid search:

```bash
curl -X POST http://localhost:8000/query -H "Content-Type: application/json" -d '{"q":"crypto payments","limit":5}'
```