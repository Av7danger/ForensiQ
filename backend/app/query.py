# backend/app/query.py
"""
Query API Endpoint for UFDR Investigator - Phase 4: Retrieval (Hybrid) + Local Summarizer
Author: Backend Engineer  
Python 3.11+

FastAPI endpoint for natural language queries with hybrid search and local summarization.

Requires:
    pip install fastapi pydantic transformers torch
"""

import logging
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

# Optional imports with graceful degradation
try:
    from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM
except ImportError:
    pipeline = None
    AutoTokenizer = None
    AutoModelForSeq2SeqLM = None

from retriever import get_retriever

logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter()

# Summarization model configuration
DEFAULT_SUMMARIZER_MODEL = "facebook/bart-large-cnn"  # High quality
FALLBACK_SUMMARIZER_MODEL = "t5-small"  # Lightweight fallback
MAX_SUMMARY_TOKENS = 512
MAX_SUMMARY_LENGTH = 150  # Max summary length in tokens


class QueryRequest(BaseModel):
    """Request model for query endpoint."""
    q: str = Field(..., description="Search query string", min_length=1, max_length=500)
    limit: int = Field(default=10, description="Maximum number of results", ge=1, le=50)
    summarize: bool = Field(default=False, description="Generate summary of top results")


class SearchHit(BaseModel):
    """Individual search result."""
    message_id: str = Field(..., description="Unique message identifier")
    case_id: str = Field(..., description="Case identifier")
    snippet: str = Field(..., description="Content snippet (first 200 chars)")
    sender: Optional[str] = Field(default=None, description="Message sender")
    recipient: Optional[str] = Field(default=None, description="Message recipient")
    timestamp: Optional[str] = Field(default=None, description="Message timestamp (ISO format)")
    score: float = Field(..., description="Relevance score (0-1)", ge=0.0, le=1.0)
    sources: List[str] = Field(..., description="Search sources (opensearch, faiss)")
    opensearch_score: float = Field(default=0.0, description="OpenSearch keyword score")
    faiss_score: float = Field(default=0.0, description="FAISS semantic score")


class QueryResponse(BaseModel):
    """Response model for query endpoint."""
    query: str = Field(..., description="Original search query")
    summary: Optional[str] = Field(default=None, description="Generated summary (if requested)")
    hits: List[SearchHit] = Field(..., description="Search results")
    total_hits: int = Field(..., description="Number of results returned")
    sources_used: List[str] = Field(..., description="Search sources that returned results")


class LocalSummarizer:
    """
    Local HuggingFace summarization model wrapper.
    Provides offline summarization without external APIs.
    """
    
    def __init__(self, model_name: str = DEFAULT_SUMMARIZER_MODEL):
        """
        Initialize local summarizer.
        
        Args:
            model_name: HuggingFace model name for summarization
        """
        self.model_name = model_name
        self.summarizer = None
        self.tokenizer = None
        self._initialized = False
        
        logger.info("Initialized LocalSummarizer with model: %s", model_name)
    
    def _load_model(self) -> bool:
        """Load the summarization model on first use."""
        if self._initialized or pipeline is None:
            return self._initialized
        
        try:
            logger.info("Loading summarization model: %s", self.model_name)
            
            # Try to load the primary model
            try:
                self.summarizer = pipeline(
                    "summarization",
                    model=self.model_name,
                    tokenizer=self.model_name,
                    device=-1,  # CPU only for offline use
                    framework="pt"  # PyTorch
                )
                logger.info("Successfully loaded model: %s", self.model_name)
                
            except Exception as e:
                logger.warning("Failed to load primary model %s: %s", self.model_name, str(e))
                
                # Fallback to smaller model
                logger.info("Attempting fallback model: %s", FALLBACK_SUMMARIZER_MODEL)
                self.summarizer = pipeline(
                    "summarization",
                    model=FALLBACK_SUMMARIZER_MODEL,
                    tokenizer=FALLBACK_SUMMARIZER_MODEL,
                    device=-1,
                    framework="pt"
                )
                self.model_name = FALLBACK_SUMMARIZER_MODEL
                logger.info("Successfully loaded fallback model: %s", FALLBACK_SUMMARIZER_MODEL)
            
            self._initialized = True
            return True
            
        except Exception as e:
            logger.error("Failed to load any summarization model: %s", str(e))
            self._initialized = False
            return False
    
    def summarize(self, texts: List[str], max_length: int = MAX_SUMMARY_LENGTH) -> Optional[str]:
        """
        Generate summary from list of text snippets.
        
        Args:
            texts: List of text snippets to summarize
            max_length: Maximum summary length in tokens
            
        Returns:
            Generated summary text or None if failed
        """
        if not texts or not self._load_model():
            return None
        
        try:
            # Combine and truncate input texts
            combined_text = " ".join(texts)
            
            # Truncate to model's token limit (rough estimation)
            if len(combined_text) > MAX_SUMMARY_TOKENS * 4:  # ~4 chars per token
                combined_text = combined_text[:MAX_SUMMARY_TOKENS * 4]
                combined_text += "..."
            
            # Generate summary
            logger.debug("Generating summary for %d characters of text", len(combined_text))
            
            summary_result = self.summarizer(
                combined_text,
                max_length=max_length,
                min_length=30,
                do_sample=False,  # Deterministic output
                truncation=True
            )
            
            if summary_result and isinstance(summary_result, list) and len(summary_result) > 0:
                summary_text = summary_result[0].get('summary_text', '').strip()
                logger.debug("Generated summary: %s", summary_text[:100])
                return summary_text
            else:
                logger.warning("Unexpected summarizer output format")
                return None
                
        except Exception as e:
            logger.error("Summarization failed: %s", str(e))
            return None
    
    def is_available(self) -> bool:
        """Check if summarizer is available."""
        return self._load_model()


# Global summarizer instance
_summarizer_instance = None


def get_summarizer() -> LocalSummarizer:
    """Get or create global summarizer instance."""
    global _summarizer_instance
    
    if _summarizer_instance is None:
        _summarizer_instance = LocalSummarizer()
    
    return _summarizer_instance


@router.post("/query", response_model=QueryResponse)
async def query_messages(request: QueryRequest) -> QueryResponse:
    """
    Query messages using hybrid search with optional local summarization.
    
    Combines OpenSearch (keyword) and FAISS (semantic) search for comprehensive results.
    Optionally generates a summary using local HuggingFace models.
    
    Args:
        request: Query request with search parameters
        
    Returns:
        Query response with search results and optional summary
        
    Raises:
        HTTPException: If query processing fails
    """
    try:
        logger.info("Processing query: %s (limit: %d, summarize: %s)", 
                   request.q, request.limit, request.summarize)
        
        # Get retriever and perform hybrid search
        retriever = get_retriever()
        search_results = retriever.hybrid_search(request.q, request.limit)
        
        # Convert to response format
        hits = []
        sources_used = set()
        
        for result in search_results:
            hit = SearchHit(
                message_id=result.get('message_id', ''),
                case_id=result.get('case_id', ''),
                snippet=result.get('snippet', ''),
                sender=result.get('sender'),
                recipient=result.get('recipient'),
                timestamp=result.get('timestamp'),
                score=result.get('score', 0.0),
                sources=result.get('sources', []),
                opensearch_score=result.get('opensearch_score', 0.0),
                faiss_score=result.get('faiss_score', 0.0)
            )
            hits.append(hit)
            sources_used.update(result.get('sources', []))
        
        # Generate summary if requested
        summary = None
        if request.summarize and hits:
            try:
                summarizer = get_summarizer()
                if summarizer.is_available():
                    # Use top 5 snippets for summary
                    top_snippets = [hit.snippet for hit in hits[:5] if hit.snippet]
                    if top_snippets:
                        summary = summarizer.summarize(top_snippets)
                        if summary:
                            logger.info("Generated summary: %s", summary[:100])
                        else:
                            logger.warning("Summarization returned empty result")
                    else:
                        logger.warning("No content snippets available for summarization")
                else:
                    logger.warning("Summarizer not available")
            except Exception as e:
                logger.error("Summarization failed: %s", str(e))
                # Don't fail the whole request if summarization fails
                summary = None
        
        response = QueryResponse(
            query=request.q,
            summary=summary,
            hits=hits,
            total_hits=len(hits),
            sources_used=list(sources_used)
        )
        
        logger.info("Query completed: %d hits, sources: %s", len(hits), list(sources_used))
        return response
        
    except Exception as e:
        logger.error("Query processing failed: %s", str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Query processing failed: {str(e)}"
        )


@router.get("/status")
async def get_query_status() -> Dict[str, Any]:
    """
    Get status of query system components.
    
    Returns:
        Dictionary with component availability and configuration
    """
    try:
        # Get retriever status
        retriever = get_retriever()
        retriever_status = retriever.get_status()
        
        # Get summarizer status
        summarizer = get_summarizer()
        summarizer_available = summarizer.is_available()
        
        return {
            "retrieval": retriever_status,
            "summarization": {
                "available": summarizer_available,
                "model": summarizer.model_name if summarizer_available else None
            },
            "endpoints": {
                "query": "/query",
                "status": "/status"
            }
        }
        
    except Exception as e:
        logger.error("Status check failed: %s", str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Status check failed: {str(e)}"
        )


# Health check endpoint
@router.get("/health")
async def health_check() -> Dict[str, str]:
    """Simple health check endpoint."""
    return {"status": "healthy", "service": "ufdr-query-api"}


# Export router
__all__ = ["router"]