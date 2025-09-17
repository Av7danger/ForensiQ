# ForensiQ - UFDR Forensic Investigation Platform

🔍 **Advanced forensic investigation platform for Cellebrite UFDR files with hybrid search and AI-powered analysis.**

ForensiQ is a comprehensive, offline-capable forensic investigation system that parses Cellebrite UFDR (Universal Forensic Data Report) files and provides powerful search, entity extraction, and analysis capabilities for digital forensic investigators.

## 🚀 Features

### Phase 1 — Ingest & Parser
- **UFDR File Processing**: Extract and parse Cellebrite UFDR ZIP archives
- **Message Extraction**: Parse SMS, chat messages, emails with full metadata
- **Contact & Call Data**: Extract phone contacts and call history  
- **Attachment Handling**: Process and catalog media files and documents
- **JSONL Output**: Structured data export for downstream processing

### Phase 2 — Storage & Indexing
- **Database Storage**: PostgreSQL/SQLite backend with SQLAlchemy ORM
- **Full-Text Search**: OpenSearch indexing for keyword queries
- **Efficient ETL**: Bulk loading with upsert capabilities
- **Data Integrity**: Robust error handling and validation

### Phase 3 — NLP & Entity Extraction
- **Entity Recognition**: Extract phones, emails, URLs, cryptocurrency addresses
- **Phone Normalization**: E.164 standardization with country detection
- **Semantic Embeddings**: sentence-transformers for message vectorization
- **FAISS Indexing**: Fast similarity search for large datasets

### Phase 4 — Retrieval (Hybrid) + Local Summarizer
- **Hybrid Search**: Combines keyword (OpenSearch) and semantic (FAISS) search
- **Local Summarization**: HuggingFace models for offline content summarization
- **REST API**: FastAPI endpoints for query and analysis
- **Score Fusion**: Intelligent ranking combining multiple search methods

## 🛠️ Installation

### Prerequisites
- Python 3.11+
- PostgreSQL (optional, SQLite fallback included)
- OpenSearch (for keyword search)

### Quick Setup

```bash
# Clone the repository
git clone https://github.com/Av7danger/ForensiQ.git
cd ForensiQ

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
python -c "from backend.db import init_db; init_db()"
```

### Dependencies

```bash
# Core dependencies
pip install sqlalchemy psycopg2-binary opensearch-py python-dotenv

# NLP and embeddings
pip install sentence-transformers faiss-cpu phonenumbers transformers

# API and web interface  
pip install fastapi pydantic uvicorn

# Optional: GPU acceleration
pip install faiss-gpu torch
```

## 📖 Usage

### 1. Parse UFDR Files

```bash
python parsers/ufdr_parser.py --input case_data.ufdr --output ./output/CASE-001/
```

### 2. Load Data into Database

```bash
python backend/etl_load.py --input ./output/CASE-001/parsed/ --case CASE-001
```

### 3. Index for Search

```bash
# Keyword indexing
python backend/opensearch_index.py --input ./output/CASE-001/parsed/messages.jsonl --index messages

# Semantic embeddings  
python nlp/embeddings_worker.py --input ./output/CASE-001/parsed/messages.jsonl --out ./vectors/
```

### 4. Start Query API

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Query the Data

```bash
# Hybrid search with summarization
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "q": "suspicious cryptocurrency transactions",
    "limit": 10,
    "summarize": true
  }'
```

## 🏗️ Architecture

```
ForensiQ/
├── parsers/           # Phase 1: UFDR parsing and extraction
├── backend/           # Phase 2: Storage, indexing, and API
├── nlp/              # Phase 3: Entity extraction and embeddings
└── output/           # Processed case data and artifacts
```

### Data Flow

1. **UFDR Input** → **Parser** → **JSONL Output**
2. **JSONL** → **ETL** → **PostgreSQL Database**  
3. **Messages** → **OpenSearch** → **Keyword Index**
4. **Messages** → **NLP** → **FAISS Embeddings**
5. **Query** → **Hybrid Search** → **Ranked Results** → **Summary**

## 🔍 Search Capabilities

### Keyword Search (OpenSearch)
- Exact term matching
- Fuzzy search with typo tolerance
- Field-specific queries (sender, recipient, content)
- Boolean operators and phrase queries

### Semantic Search (FAISS)
- Conceptual similarity matching
- Cross-lingual understanding
- Context-aware results
- Vector similarity scoring

### Hybrid Fusion
- Weighted score combination
- Multi-source result boosting
- Intelligent deduplication
- Relevance ranking optimization

## 🤖 AI Features

### Entity Extraction
- **Phone Numbers**: International format normalization
- **Email Addresses**: Contact identification  
- **URLs**: Web link discovery
- **Cryptocurrency**: Bitcoin/Ethereum address detection

### Local Summarization
- **Offline Models**: HuggingFace transformers (BART, T5)
- **Context-Aware**: Multi-document summarization
- **Configurable**: Adjustable summary length and style
- **Privacy-Preserving**: No external API calls

## 📊 API Reference

### POST /query
Hybrid search with optional summarization

**Request:**
```json
{
  "q": "search query",
  "limit": 10,
  "summarize": false
}
```

**Response:**
```json
{
  "query": "search query",
  "summary": "Generated summary...",
  "hits": [
    {
      "message_id": "msg_12345",
      "case_id": "CASE-001",
      "snippet": "Message content preview...",
      "sender": "+15551234567",
      "recipient": "+15559876543", 
      "timestamp": "2024-01-15T10:30:00Z",
      "score": 0.95,
      "sources": ["opensearch", "faiss"]
    }
  ],
  "total_hits": 1,
  "sources_used": ["opensearch", "faiss"]
}
```

### GET /status
System health and component availability

### GET /health  
Simple health check endpoint

## 🔧 Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/ufdr

# Search
OPENSEARCH_URL=http://localhost:9200
FAISS_INDEX_DIR=./vectors

# Models
EMBEDDING_MODEL=all-MiniLM-L6-v2
```

### Docker Support (Future)

```yaml
# docker-compose.yml (planned)
services:
  forensiq:
    build: .
    ports:
      - "8000:8000"
  postgres:
    image: postgres:15
  opensearch:
    image: opensearchproject/opensearch:2.8.0
```

## 🧪 Testing

```bash
# Run entity extraction tests
python -c "
from nlp.extractors import extract_entities
assert extract_entities('Call +1-555-123-4567')['phones']
print('Entity extraction: PASS')
"

# Test phone normalization
python -c "
from nlp.normalize_phone import normalize_phone  
assert normalize_phone('(555) 123-4567') == '+15551234567'
print('Phone normalization: PASS')
"

# Test API health
curl http://localhost:8000/health
```

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 🔒 Security & Privacy

ForensiQ is designed with forensic investigation requirements in mind:

- **Offline Operation**: No external API dependencies
- **Local Processing**: All analysis happens on your infrastructure
- **Data Isolation**: Complete control over sensitive forensic data
- **Audit Trail**: Comprehensive logging for legal compliance

## 📚 Documentation

- [Parser Documentation](parsers/README.md)
- [Backend API Guide](backend/README.md)  
- [NLP Module Documentation](nlp/README.md)

## 🚧 Roadmap

- [ ] Web-based investigation dashboard
- [ ] Advanced timeline analysis
- [ ] Network graph visualization
- [ ] Multi-case correlation analysis
- [ ] Export to standard forensic formats
- [ ] Docker containerization
- [ ] Kubernetes deployment

## 📞 Support

For questions, issues, or feature requests:

- **Issues**: [GitHub Issues](https://github.com/Av7danger/ForensiQ/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Av7danger/ForensiQ/discussions)

## 🏆 Acknowledgments

- Cellebrite for UFDR format specifications
- HuggingFace for transformer models
- OpenSearch community for search capabilities
- FAISS team for efficient similarity search

---

**ForensiQ** - Empowering digital forensic investigators with AI-enhanced analysis capabilities.