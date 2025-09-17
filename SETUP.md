# ForensiQ Setup Instructions

Complete setup guide for the ForensiQ digital forensic investigation platform.

## Quick Start (Full Stack)

### Prerequisites
- **Python 3.11+** with pip
- **Node.js 16+** with npm
- **PostgreSQL 12+** database server
- **OpenSearch 2.0+** search engine
- **Git** for version control

### 1. Clone Repository
```bash
git clone https://github.com/Av7danger/ForensiQ.git
cd ForensiQ
```

### 2. Backend Setup

#### Install Python Dependencies
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### Database Setup
```bash
# Start PostgreSQL service
# On Windows (if using pg_ctl):
pg_ctl -D "C:\Program Files\PostgreSQL\15\data" start

# Create database
createdb forensiq

# Set environment variables (create .env file)
echo "DATABASE_URL=postgresql://username:password@localhost:5432/forensiq" > .env
echo "OPENSEARCH_URL=http://localhost:9200" >> .env
echo "OPENSEARCH_INDEX=forensiq_evidence" >> .env
```

#### OpenSearch Setup
```bash
# Start OpenSearch (if installed locally)
# On Windows:
bin\opensearch.bat
# On macOS/Linux:
bin/opensearch

# Or using Docker:
docker run -d -p 9200:9200 -p 9600:9600 -e "discovery.type=single-node" opensearchproject/opensearch:latest
```

#### Initialize Backend
```bash
# Create database tables
python -c "from backend.models import init_db; init_db()"

# Start FastAPI server
cd backend
uvicorn app.query:app --reload --host 0.0.0.0 --port 8000
```

### 3. Frontend Setup

#### Install Dependencies
```bash
# In a new terminal, navigate to frontend
cd frontend
npm install
```

#### Configure Environment
```bash
# Create .env.local file
echo "VITE_API_BASE_URL=http://localhost:8000" > .env.local
echo "VITE_APP_TITLE=ForensiQ Investigator Dashboard" >> .env.local
```

#### Start Development Server
```bash
npm run dev
```

### 4. Test the Installation

1. **Backend API**: Visit http://localhost:8000/docs for API documentation
2. **Frontend**: Visit http://localhost:5173 for the web interface
3. **Health Check**: Visit http://localhost:8000/health

## Step-by-Step Setup

### Backend Configuration

#### 1. Environment Variables (.env)
```env
# Database
DATABASE_URL=postgresql://username:password@localhost:5432/forensiq

# OpenSearch
OPENSEARCH_URL=http://localhost:9200
OPENSEARCH_INDEX=forensiq_evidence
OPENSEARCH_USERNAME=admin
OPENSEARCH_PASSWORD=admin

# FastAPI
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=true

# Security
SECRET_KEY=your-secret-key-here
CORS_ORIGINS=["http://localhost:5173", "http://localhost:3000"]

# File Processing
UPLOAD_DIR=./uploads
MAX_FILE_SIZE=100000000  # 100MB
ALLOWED_EXTENSIONS=[".ufdr", ".xml"]

# NLP Models
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
SUMMARIZER_MODEL=facebook/bart-large-cnn
DEVICE=cpu
```

#### 2. Database Schema Creation
```bash
# Run database initialization
python -c "
from backend.models import Base, engine
Base.metadata.create_all(bind=engine)
print('Database tables created successfully')
"
```

#### 3. OpenSearch Index Setup
```bash
# Create OpenSearch index
python -c "
from backend.opensearch_setup import create_index
create_index()
print('OpenSearch index created successfully')
"
```

### Frontend Configuration

#### 1. Environment Variables (.env.local)
```env
# API Configuration
VITE_API_BASE_URL=http://localhost:8000
VITE_API_TIMEOUT=10000

# Application
VITE_APP_TITLE=ForensiQ Investigator Dashboard
VITE_APP_VERSION=1.0.0

# Features
VITE_ENABLE_GRAPH=true
VITE_ENABLE_EXPORT=true
VITE_ENABLE_DEBUG=false

# Graph Settings
VITE_GRAPH_MAX_NODES=1000
VITE_GRAPH_PHYSICS_ENABLED=true
```

#### 2. Build Configuration
```bash
# Type check
npm run type-check

# Build for production
npm run build

# Preview production build
npm run preview
```

## Usage Instructions

### 1. Parse UFDR Files
```bash
# Using the CLI parser
python parsers/ufdr_parser.py path/to/your/file.ufdr

# Options:
python parsers/ufdr_parser.py --help
```

### 2. Index Data for Search
```bash
# Run the embeddings worker
python nlp/embeddings_worker.py

# This will:
# - Generate embeddings for all messages
# - Index data in OpenSearch
# - Extract entities using NLP
```

### 3. Access Web Interface
1. Open http://localhost:5173
2. Use the search box to find evidence
3. Click results to view details
4. Use the Graph tab to visualize relationships
5. Export results as PDF, HTML, or JSON

### 4. Query API Directly
```bash
# Search evidence
curl "http://localhost:8000/api/search?q=phone%20number&page=1&per_page=10"

# Get evidence details
curl "http://localhost:8000/api/evidence/{evidence_id}"

# Get graph data
curl "http://localhost:8000/api/graph"
```

## Production Deployment

### Docker Setup

#### 1. Backend Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "backend.app.query:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### 2. Frontend Dockerfile
```dockerfile
FROM node:18-alpine

WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

COPY . .
RUN npm run build

EXPOSE 5173
CMD ["npm", "run", "preview"]
```

#### 3. Docker Compose
```yaml
version: '3.8'
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: forensiq
      POSTGRES_USER: forensiq
      POSTGRES_PASSWORD: forensiq
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  opensearch:
    image: opensearchproject/opensearch:latest
    environment:
      - cluster.name=forensiq-cluster
      - node.name=forensiq-node
      - discovery.type=single-node
      - bootstrap.memory_lock=true
      - "OPENSEARCH_JAVA_OPTS=-Xms512m -Xmx512m"
    ports:
      - "9200:9200"
      - "9600:9600"

  backend:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - opensearch
    environment:
      - DATABASE_URL=postgresql://forensiq:forensiq@postgres:5432/forensiq
      - OPENSEARCH_URL=http://opensearch:9200

  frontend:
    build: ./frontend
    ports:
      - "5173:5173"
    depends_on:
      - backend
    environment:
      - VITE_API_BASE_URL=http://backend:8000

volumes:
  postgres_data:
```

### Nginx Configuration
```nginx
server {
    listen 80;
    server_name forensiq.local;

    # Frontend
    location / {
        proxy_pass http://localhost:5173;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Backend API
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Troubleshooting

### Common Issues

1. **Database Connection Error**
   ```bash
   # Check PostgreSQL is running
   pg_isready -h localhost -p 5432
   
   # Test connection
   psql -h localhost -p 5432 -U username -d forensiq
   ```

2. **OpenSearch Connection Error**
   ```bash
   # Check OpenSearch is running
   curl -X GET "localhost:9200/_cluster/health?pretty"
   
   # Check indices
   curl -X GET "localhost:9200/_cat/indices?v"
   ```

3. **Frontend Build Errors**
   ```bash
   # Clear node modules and reinstall
   rm -rf node_modules package-lock.json
   npm install
   
   # Clear Vite cache
   rm -rf node_modules/.vite
   ```

4. **Python Dependencies**
   ```bash
   # Update pip
   python -m pip install --upgrade pip
   
   # Install with verbose output
   pip install -r requirements.txt -v
   ```

### Performance Tuning

1. **Database Optimization**
   ```sql
   -- Create indices for better search performance
   CREATE INDEX idx_messages_timestamp ON messages(timestamp);
   CREATE INDEX idx_messages_content_gin ON messages USING gin(to_tsvector('english', content));
   ```

2. **OpenSearch Tuning**
   ```bash
   # Increase heap size in opensearch.yml
   echo "-Xms2g" >> config/jvm.options
   echo "-Xmx2g" >> config/jvm.options
   ```

3. **Frontend Optimization**
   ```bash
   # Analyze bundle size
   npm run build -- --analyze
   
   # Enable gzip compression
   npm install vite-plugin-compression
   ```

## Development Workflow

### 1. Code Structure
```
ForensiQ/
├── parsers/          # UFDR file parsing
├── backend/          # FastAPI application
├── nlp/             # NLP and entity extraction
├── frontend/        # React application
├── docs/           # Documentation
└── tests/          # Test suites
```

### 2. Git Workflow
```bash
# Create feature branch
git checkout -b feature/new-search-algorithm

# Make changes and commit
git add .
git commit -m "Add semantic search algorithm"

# Push and create PR
git push origin feature/new-search-algorithm
```

### 3. Testing
```bash
# Backend tests
pytest tests/

# Frontend tests
cd frontend
npm run test

# Integration tests
python tests/test_integration.py
```

## Next Steps

1. **Add UFDR Upload**: Implement file upload in the frontend
2. **Real-time Processing**: Add WebSocket for live updates
3. **Advanced Analytics**: Implement timeline analysis
4. **Multi-language Support**: Add internationalization
5. **Mobile App**: Create mobile companion app

## Support

- **GitHub Issues**: https://github.com/Av7danger/ForensiQ/issues
- **Documentation**: See individual README files in each directory
- **API Docs**: http://localhost:8000/docs (when running)

---

This setup creates a complete digital forensic investigation platform capable of parsing UFDR files, extracting entities, performing hybrid search, and providing an intuitive web interface for investigators.