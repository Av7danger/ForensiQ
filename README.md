```
███████╗ ██████╗ ██████╗ ███████╗███╗   ██╗███████╗██╗ ██████╗
██╔════╝██╔═══██╗██╔══██╗██╔════╝████╗  ██║██╔════╝██║██╔═══██╗
███████╗██║   ██║██████╔╝█████╗  ██╔██╗ ██║███████╗██║██║   ██║
╚════██║██║   ██║██╔══██╗██╔══╝  ██║╚██╗██║╚════██║██║██║   ██║
███████║╚██████╔╝██║  ██║███████╗██║ ╚████║███████║██║╚██████╔╝
╚══════╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝╚═╝  ╚═══╝╚══════╝╚═╝ ╚═════╝
```

<p align="center">
  <b>UFDR Forensic Investigation Platform — Hybrid Search & AI-Powered Analysis</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="MIT License">
  <img src="https://img.shields.io/badge/Python-3.11+-yellow.svg" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/Database-PostgreSQL-lightblue.svg" alt="Postgres">
  <img src="https://img.shields.io/badge/Search-OpenSearch-orange.svg" alt="OpenSearch">
  <img src="https://img.shields.io/badge/AI-SentenceTransformers-green.svg" alt="SentenceTransformers">
  <img src="https://img.shields.io/badge/Vector-FAISS-red.svg" alt="FAISS">
</p>

---

# 🔍 ForensiQ — UFDR Forensic Investigation Platform

**ForensiQ** is an advanced, offline-capable forensic investigation system for **Cellebrite UFDR (Universal Forensic Data Report)** files.  
It empowers investigators with **hybrid search, entity extraction, and AI-powered analysis** while ensuring **data privacy and legal compliance**.

---

## ✨ Features

### 🗂️ Phase 1 — Ingest & Parsing

- Parse Cellebrite UFDR ZIP archives
- Extract **messages** (SMS, chats, emails) with metadata
- Parse **contacts & call history**
- Catalog **attachments & media**
- Export structured **JSONL** for downstream processing

### 💾 Phase 2 — Storage & Indexing

- Store data in **PostgreSQL** (or SQLite for demo) with SQLAlchemy ORM
- Index messages in **OpenSearch** for full-text search
- Robust ETL with **idempotent upserts**
- Integrity checks & error handling

### 🧠 Phase 3 — NLP & Entity Extraction

- Detect **phone numbers, emails, URLs, crypto addresses**
- Normalize phones into **E.164 international format**
- Generate **semantic embeddings** using sentence-transformers
- Build **FAISS index** for similarity search

### 🔎 Phase 4 — Hybrid Retrieval & Summarization

- Combine **keyword search (OpenSearch)** + **semantic search (FAISS)**
- Provide **FastAPI REST API** for querying evidence
- Local **summarization** with HuggingFace (BART/T5)  
- Score fusion & relevance ranking

### 🖥️ Phase 5 — Web Interface

- **React + TypeScript** investigator dashboard
- **Interactive search** with entity highlighting
- **Network graph visualization** of relationships
- **Export capabilities** (PDF, HTML, JSON)
- **Responsive design** for all devices

---

## 🛠️ Installation

### Prerequisites

- Python 3.11+
- Node.js 16+ (for frontend)
- PostgreSQL (optional, SQLite fallback works)
- OpenSearch (for keyword search)
- FAISS (CPU or GPU)

### Quick Setup

```bash
# Clone repo
git clone https://github.com/Av7danger/ForensiQ.git
cd ForensiQ

# Backend setup
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python -c "from backend.db import init_db; init_db()"

# Frontend setup
cd frontend
npm install
npm run dev
```

### Core Dependencies

```bash
# Database & ETL
pip install sqlalchemy psycopg2-binary opensearch-py python-dotenv

# NLP & embeddings
pip install sentence-transformers faiss-cpu phonenumbers transformers

# API
pip install fastapi uvicorn pydantic

# Optional (GPU acceleration)
pip install faiss-gpu torch
```

---

## 📖 Usage

### 1️⃣ Parse UFDR Files

```bash
python parsers/ufdr_parser.py --input case.ufdr --output ./output/CASE-001/
```

### 2️⃣ Load Data into DB

```bash
python backend/etl_load.py --input ./output/CASE-001/parsed/ --case CASE-001
```

### 3️⃣ Build Search Indexes

```bash
# Keyword search (OpenSearch)
python backend/opensearch_index.py --input ./output/CASE-001/parsed/messages.jsonl --index messages

# Semantic search (FAISS)
python nlp/embeddings_worker.py --input ./output/CASE-001/parsed/messages.jsonl --out ./vectors/
```

### 4️⃣ Start Services

```bash
# Backend API
uvicorn backend.app.query:app --reload --host 0.0.0.0 --port 8000

# Frontend (new terminal)
cd frontend && npm run dev
```

### 5️⃣ Access Interface

- **Web Dashboard**: http://localhost:5173
- **API Documentation**: http://localhost:8000/docs

### 6️⃣ Run a Query

```bash
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "q": "suspicious cryptocurrency transactions",
    "limit": 5,
    "page": 1
  }'
```

---

## 🏗️ Architecture

```
ForensiQ/
├── parsers/        # Phase 1: UFDR parsing
├── backend/        # Phase 2: DB, indexing, API
├── nlp/            # Phase 3: Entity extraction & embeddings
├── frontend/       # Phase 5: React dashboard
├── vectors/        # FAISS index
└── output/         # Parsed case data
```

**Data Flow:**

1. **UFDR → Parser → JSONL**
2. **JSONL → ETL → PostgreSQL**
3. **Messages → OpenSearch (keywords)**
4. **Messages → NLP → FAISS (embeddings)**
5. **Query → Hybrid Retrieval → Web Interface → Results**

---

## 🔍 Search Modes

### Keyword Search (OpenSearch)

* Exact / fuzzy search
* Field-specific (sender, recipient, body)
* Boolean queries

### Semantic Search (FAISS)

* Conceptual similarity
* Context-aware results
* Cross-lingual support

### Hybrid Fusion

* Weighted score combination
* Deduplication & boosting
* Optimized ranking

---

## 🤖 AI Features

* **Entity Extraction**: Phones, emails, URLs, crypto
* **Phone Normalization**: International (E.164)
* **Summarization**: Local HuggingFace models
* **Privacy First**: No external API calls

---

## 📊 API Reference

### POST `/api/search`

Hybrid search with pagination.

**Request**

```json
{
  "q": "search query",
  "limit": 10,
  "page": 1,
  "type": "messages"
}
```

**Response**

```json
{
  "results": [
    {
      "id": "msg_123",
      "type": "message",
      "content": "Message text...",
      "score": 0.92,
      "entities": {
        "phones": ["+15551234567"],
        "emails": ["user@example.com"]
      },
      "timestamp": "2024-01-15T10:30:00Z"
    }
  ],
  "total": 42,
  "page": 1,
  "per_page": 10
}
```

### GET `/api/evidence/{id}`

Get detailed evidence information.

### GET `/api/graph`

Get network graph data for visualization.

### GET `/health`

Simple health check.

---

## ⚙️ Configuration

Set environment variables in `.env`:

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/ufdr

# Search
OPENSEARCH_URL=http://localhost:9200
FAISS_INDEX_DIR=./vectors

# Models
EMBEDDING_MODEL=all-MiniLM-L6-v2

# API
API_HOST=0.0.0.0
API_PORT=8000
```

Frontend configuration in `frontend/.env.local`:

```bash
VITE_API_BASE_URL=http://localhost:8000
VITE_APP_TITLE=ForensiQ Investigator Dashboard
```

---

## 🚧 Roadmap

* [x] ~~UFDR parsing & data extraction~~
* [x] ~~Hybrid search (keyword + semantic)~~
* [x] ~~Entity extraction & phone normalization~~
* [x] ~~REST API with FastAPI~~
* [x] ~~React investigator dashboard~~
* [x] ~~Network graph visualization~~
* [ ] File upload interface
* [ ] Timeline analysis view
* [ ] Advanced case management
* [ ] Multi-case correlation
* [ ] Docker & K8s deployment

---

## 🔒 Security & Privacy

* 100% **offline-capable**
* **No external APIs**
* Local processing of sensitive forensic data
* Audit logs for legal compliance
* Secure file handling with integrity checks

---

## 🧪 Testing

Run the test suite:

```bash
# Backend tests
python -m pytest tests/

# Entity extraction test
python -c "
from nlp.extractors import extract_entities
result = extract_entities('Call +1-555-123-4567')
assert result['phones']
print('✅ Entity extraction: PASS')
"

# Phone normalization test  
python -c "
from nlp.normalize_phone import normalize_phone
assert normalize_phone('(555) 123-4567') == '+15551234567'
print('✅ Phone normalization: PASS')
"

# Frontend tests
cd frontend && npm test
```

---

## 📝 License

MIT License — see [LICENSE](LICENSE)

---

## 🤝 Contributing

1. Fork repo
2. Create feature branch (`git checkout -b feature/my-feature`)
3. Commit changes (`git commit -m 'Add feature'`)
4. Push (`git push origin feature/my-feature`)
5. Open PR

---

## 📚 Documentation

* [Setup Instructions](SETUP.md) - Complete installation guide
* [Parser Docs](parsers/README.md) - UFDR parsing details
* [Backend API Guide](backend/README.md) - API documentation
* [Frontend Guide](frontend/README.md) - Web interface setup
* [NLP Module](nlp/README.md) - Entity extraction & embeddings

---

## 🏆 Acknowledgments

* **Cellebrite** for UFDR specs
* **HuggingFace** for NLP models
* **OpenSearch** community
* **FAISS** team
* **React** & **TypeScript** communities

---

🚀 **ForensiQ** — Empowering forensic investigators with **offline, AI-powered evidence analysis**.