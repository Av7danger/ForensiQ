# ForensiQ Development Guide

## 🚀 Quick Setup

### Prerequisites
- **Python 3.11+**
- **Node.js 18+** 
- **Docker & Docker Compose**
- **Git**

### 1. Clone and Setup
```bash
git clone https://github.com/Av7danger/ForensiQ.git
cd ForensiQ

# Copy environment file
cp .env.example .env
# Edit .env with your configuration
```

### 2. Start with Docker (Recommended)
```bash
# Start all services
docker-compose up -d

# Check service health
docker-compose ps
curl http://localhost/health
```

### 3. Development Setup (Local)
```bash
# Backend setup
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Frontend setup  
cd ../frontend
npm install

# Start services
cd ../backend && uvicorn main:app --reload
cd ../frontend && npm start
```

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React Frontend │    │  FastAPI Backend │    │   PostgreSQL    │
│   (TypeScript)   │◄──►│    (Python)     │◄──►│   Database      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                       ┌────────┴────────┐
                       │                 │
                ┌─────────────┐   ┌─────────────┐
                │ OpenSearch  │   │    FAISS    │
                │ (Full-text) │   │ (Semantic)  │
                └─────────────┘   └─────────────┘
```

## 📁 Project Structure

```
ForensiQ/
├── backend/                 # Python FastAPI backend
│   ├── app/                # API routes and business logic
│   │   ├── upload.py       # File upload endpoints
│   │   ├── search.py       # Search endpoints
│   │   ├── entities.py     # Entity extraction
│   │   ├── cases.py        # Case management
│   │   └── analysis.py     # AI analysis
│   ├── models.py           # SQLAlchemy database models
│   ├── db.py              # Database configuration
│   ├── schema.sql         # Database schema
│   ├── main.py            # FastAPI application
│   └── requirements.txt   # Python dependencies
├── frontend/               # React TypeScript frontend
│   ├── src/
│   │   ├── components/    # Reusable UI components
│   │   ├── pages/         # Page components
│   │   ├── services/      # API clients
│   │   └── types/         # TypeScript definitions
│   └── package.json
├── parsers/               # UFDR parsing logic
├── nlp/                   # NLP and AI modules
├── tests/                 # Test suites
├── nginx/                 # Reverse proxy config
├── assets/                # Visual assets
├── docker-compose.yml     # Container orchestration
└── README.md             # Documentation
```

## 🔌 API Endpoints

### Upload & Processing
- `POST /api/upload` - Upload UFDR file
- `GET /api/upload/status/{job_id}` - Check processing status

### Search & Retrieval  
- `GET /api/search` - Keyword search
- `POST /api/search/semantic` - Semantic search
- `POST /api/search/hybrid` - Combined search

### Entity Management
- `GET /api/entities` - List extracted entities
- `GET /api/entities/{entity_id}` - Entity details
- `GET /api/entities/network` - Entity network graph

### Case Management
- `GET /api/cases` - List cases
- `POST /api/cases` - Create case
- `GET /api/cases/{case_id}` - Case details

### Analysis & Reports
- `POST /api/analysis/summarize` - Generate case summary
- `GET /api/analysis/timeline` - Evidence timeline
- `POST /api/analysis/export` - Export report

## 🧪 Testing

### Backend Tests
```bash
cd backend
pytest tests/ -v
pytest tests/test_upload.py::test_ufdr_upload -v
```

### Frontend Tests
```bash
cd frontend
npm test
npm run test:coverage
```

### Integration Tests
```bash
# Full end-to-end testing
pytest tests/integration/ -v
```

## 🛠️ Development Workflow

### 1. Feature Development
```bash
# Create feature branch
git checkout -b feature/entity-timeline

# Make changes
# Run tests
pytest tests/

# Commit and push
git add .
git commit -m "Add entity timeline visualization"
git push origin feature/entity-timeline
```

### 2. Code Quality
```bash
# Format code
black backend/
isort backend/

# Lint frontend
cd frontend && npm run lint
```

### 3. Database Migrations
```bash
cd backend
alembic revision --autogenerate -m "Add entity relationships"
alembic upgrade head
```

## 🐛 Debugging

### Backend Debugging
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
uvicorn main:app --reload --log-level debug

# Debug specific modules
export PYTHONPATH=/app
python -c "from parsers.ufdr_parser import UFDRParser; parser = UFDRParser(); print('Parser loaded')"
```

### Frontend Debugging
```bash
# Start with debug info
REACT_APP_DEBUG=true npm start

# Check network requests
# Open Chrome DevTools > Network tab
```

### Database Debugging
```bash
# Connect to database
docker exec -it forensiq_postgres psql -U forensiq_user -d forensiq_db

# Check OpenSearch
curl "http://localhost:9200/_cat/indices?v"
curl "http://localhost:9200/messages/_search?pretty"
```

## 📊 Performance Monitoring

### Backend Metrics
- API response times: `/docs` FastAPI metrics
- Database queries: PostgreSQL slow query log
- Search performance: OpenSearch `_stats` endpoint

### Frontend Metrics
- Bundle size: `npm run analyze`
- Runtime performance: Chrome DevTools > Performance

## 🔒 Security Considerations

### Development Security
- Never commit `.env` files
- Use strong passwords in docker-compose
- Enable CORS only for trusted origins
- Validate all file uploads
- Sanitize user inputs

### Production Security
- Use HTTPS everywhere
- Implement proper authentication
- Set up WAF (Web Application Firewall)
- Regular security updates
- Database encryption at rest

## 📚 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [OpenSearch Documentation](https://opensearch.org/docs/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Make changes with tests
4. Submit pull request
5. Code review and merge

## 🆘 Troubleshooting

### Common Issues

**Database Connection Failed**
```bash
# Check if PostgreSQL is running
docker-compose logs postgres
# Verify connection string in .env
```

**OpenSearch Index Issues**
```bash
# Reset indices
curl -X DELETE "localhost:9200/messages"
curl -X DELETE "localhost:9200/entities"
# Restart backend to recreate
```

**Frontend Build Errors**
```bash
# Clear node modules
rm -rf node_modules package-lock.json
npm install
```

**Large File Upload Timeout**
```bash
# Increase nginx timeout in nginx.conf
proxy_read_timeout 600s;
```