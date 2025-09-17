# backend/main.py
"""
FastAPI Main Application for UFDR Investigator - Phase 4: Retrieval (Hybrid) + Local Summarizer
Author: Backend Engineer
Python 3.11+

Main FastAPI application entry point with query endpoints.
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .app.query import router as query_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="UFDR Investigator Query API",
    description="Hybrid search and summarization API for UFDR forensic investigation",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include query router
app.include_router(query_router, prefix="", tags=["query"])

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "service": "UFDR Investigator Query API",
        "version": "1.0.0",
        "endpoints": {
            "query": "/query",
            "status": "/status", 
            "health": "/health",
            "docs": "/docs"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)