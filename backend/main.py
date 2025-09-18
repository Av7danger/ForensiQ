# backend/main.py
"""
FastAPI Main Application for ForensiQ - UFDR Forensic Investigation Platform
Author: Backend Engineering Team
Python 3.11+

Comprehensive forensic investigation API with hybrid search, entity extraction, and AI analysis.
"""

import logging
import os
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from fastapi.responses import JSONResponse, FileResponse
from contextlib import asynccontextmanager

# Import routers (to be created)
from app.upload import router as upload_router
from app.search import router as search_router  
from app.entities import router as entities_router
from app.cases import router as cases_router
from app.analysis import router as analysis_router

# Import database and services
from db import get_database
from models import Base, engine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/forensiq.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Ensure directories exist
os.makedirs('uploads', exist_ok=True)
os.makedirs('models', exist_ok=True)
os.makedirs('logs', exist_ok=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting ForensiQ API...")
    
    # Create database tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")
    
    # Initialize OpenSearch indices
    try:
        from opensearch_index import initialize_indices
        await initialize_indices()
        logger.info("OpenSearch indices initialized")
    except Exception as e:
        logger.warning(f"OpenSearch initialization failed: {e}")
    
    # Download ML models if needed
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("ML models loaded successfully")
    except Exception as e:
        logger.warning(f"ML model loading failed: {e}")
    
    yield
    
    logger.info("Shutting down ForensiQ API...")

# Create FastAPI application
app = FastAPI(
    title="ForensiQ API",
    description="UFDR Forensic Investigation Platform - Hybrid Search & AI-Powered Analysis",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Security
security = HTTPBearer()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Include routers
app.include_router(upload_router, prefix="/api/upload", tags=["upload"])
app.include_router(search_router, prefix="/api/search", tags=["search"])
app.include_router(entities_router, prefix="/api/entities", tags=["entities"])
app.include_router(cases_router, prefix="/api/cases", tags=["cases"])
app.include_router(analysis_router, prefix="/api/analysis", tags=["analysis"])

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "service": "ForensiQ API",
        "version": "1.0.0",
        "description": "UFDR Forensic Investigation Platform",
        "features": [
            "UFDR file processing",
            "Hybrid search (keyword + semantic)",
            "Entity extraction",
            "AI-powered analysis",
            "Network visualization data"
        ],
        "endpoints": {
            "upload": "/api/upload",
            "search": "/api/search", 
            "entities": "/api/entities",
            "cases": "/api/cases",
            "analysis": "/api/analysis",
            "health": "/health",
            "docs": "/docs"
        }
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    """Comprehensive health check."""
    health_status = {
        "status": "healthy",
        "timestamp": "2024-01-01T00:00:00Z",
        "services": {}
    }
    
    # Check database
    try:
        db = next(get_database())
        db.execute("SELECT 1")
        health_status["services"]["database"] = "healthy"
    except Exception as e:
        health_status["services"]["database"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check OpenSearch
    try:
        from opensearch import OpenSearch
        client = OpenSearch([os.getenv("OPENSEARCH_URL", "http://localhost:9200")])
        cluster_health = client.cluster.health()
        health_status["services"]["opensearch"] = cluster_health["status"]
    except Exception as e:
        health_status["services"]["opensearch"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check file system
    upload_dir = Path("uploads")
    if upload_dir.exists() and upload_dir.is_dir():
        health_status["services"]["filesystem"] = "healthy"
    else:
        health_status["services"]["filesystem"] = "unhealthy: upload directory missing"
        health_status["status"] = "degraded"
    
    return health_status

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)