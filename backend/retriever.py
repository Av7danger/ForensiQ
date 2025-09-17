# backend/retriever.py
"""
Hybrid Retrieval Module for UFDR Investigator - Phase 4: Retrieval (Hybrid) + Local Summarizer
Author: Backend Engineer
Python 3.11+

Combines OpenSearch (keyword search) and FAISS (semantic embeddings) for hybrid retrieval.
Provides offline-capable search with score fusion and result ranking.

Requires:
    pip install opensearch-py sentence-transformers faiss-cpu numpy
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

import numpy as np

# Optional imports with graceful degradation
try:
    import faiss
except ImportError:
    faiss = None

try:
    from opensearchpy import OpenSearch
except ImportError:
    OpenSearch = None

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

from .db import get_session
from .models import Message

logger = logging.getLogger(__name__)

# Default embedding model (same as Phase 3)
DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# Default paths for indices
DEFAULT_FAISS_DIR = "./vectors"
DEFAULT_OPENSEARCH_HOST = "localhost:9200"


class HybridRetriever:
    """
    Hybrid retrieval system combining OpenSearch and FAISS for comprehensive search.
    """
    
    def __init__(
        self,
        opensearch_host: str = DEFAULT_OPENSEARCH_HOST,
        faiss_index_dir: str = DEFAULT_FAISS_DIR,
        embedding_model: str = DEFAULT_EMBEDDING_MODEL
    ):
        """
        Initialize the hybrid retriever.
        
        Args:
            opensearch_host: OpenSearch host and port (default: localhost:9200)
            faiss_index_dir: Directory containing FAISS index files
            embedding_model: Sentence transformer model for query embeddings
        """
        self.opensearch_host = opensearch_host
        self.faiss_index_dir = Path(faiss_index_dir)
        self.embedding_model_name = embedding_model
        
        # Initialize components
        self.opensearch_client = None
        self.faiss_index = None
        self.faiss_metadata = None
        self.embedding_model = None
        
        # Initialize on first use
        self._opensearch_available = False
        self._faiss_available = False
        
        logger.info("Initialized HybridRetriever with OpenSearch: %s, FAISS: %s", 
                   opensearch_host, faiss_index_dir)
    
    def _init_opensearch(self) -> bool:
        """Initialize OpenSearch client if available."""
        if self._opensearch_available or OpenSearch is None:
            return self._opensearch_available
        
        try:
            self.opensearch_client = OpenSearch(
                hosts=[{'host': self.opensearch_host.split(':')[0], 
                       'port': int(self.opensearch_host.split(':')[1])}],
                http_compress=True,
                use_ssl=False,
                verify_certs=False,
                timeout=30
            )
            
            # Test connection
            info = self.opensearch_client.info()
            logger.info("Connected to OpenSearch: %s", info.get('version', {}).get('number', 'unknown'))
            self._opensearch_available = True
            
        except Exception as e:
            logger.warning("OpenSearch not available: %s", str(e))
            self._opensearch_available = False
        
        return self._opensearch_available
    
    def _init_faiss(self) -> bool:
        """Initialize FAISS index if available."""
        if self._faiss_available or faiss is None:
            return self._faiss_available
        
        try:
            # Load FAISS index
            index_file = self.faiss_index_dir / "faiss.index"
            metadata_file = self.faiss_index_dir / "metadata.json"
            
            if not index_file.exists() or not metadata_file.exists():
                logger.warning("FAISS index files not found at %s", self.faiss_index_dir)
                return False
            
            # Load index
            self.faiss_index = faiss.read_index(str(index_file))
            
            # Load metadata
            with open(metadata_file, 'r', encoding='utf-8') as f:
                self.faiss_metadata = json.load(f)
            
            logger.info("Loaded FAISS index with %d embeddings, dimension: %d", 
                       self.faiss_metadata.get('num_embeddings', 0),
                       self.faiss_metadata.get('embedding_dim', 0))
            
            self._faiss_available = True
            
        except Exception as e:
            logger.warning("FAISS index not available: %s", str(e))
            self._faiss_available = False
        
        return self._faiss_available
    
    def _init_embedding_model(self) -> bool:
        """Initialize sentence transformer model for query embeddings."""
        if self.embedding_model is not None or SentenceTransformer is None:
            return self.embedding_model is not None
        
        try:
            logger.info("Loading embedding model: %s", self.embedding_model_name)
            self.embedding_model = SentenceTransformer(self.embedding_model_name)
            return True
            
        except Exception as e:
            logger.warning("Failed to load embedding model: %s", str(e))
            return False
    
    def _opensearch_search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Perform keyword search using OpenSearch.
        
        Args:
            query: Search query string
            limit: Maximum number of results
            
        Returns:
            List of search results with scores and metadata
        """
        if not self._init_opensearch():
            logger.warning("OpenSearch not available for keyword search")
            return []
        
        try:
            # Build OpenSearch query
            search_body = {
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": ["content^2", "sender", "recipient"],  # Boost content field
                        "type": "best_fields",
                        "fuzziness": "AUTO"
                    }
                },
                "size": limit,
                "_source": ["message_id", "case_id", "content", "sender", "recipient", "timestamp"]
            }
            
            # Execute search
            response = self.opensearch_client.search(
                index="messages",  # From Phase 2 opensearch_index.py
                body=search_body
            )
            
            results = []
            for hit in response.get('hits', {}).get('hits', []):
                source = hit.get('_source', {})
                score = hit.get('_score', 0.0)
                
                # Normalize OpenSearch score (roughly 0-1 range)
                normalized_score = min(score / 10.0, 1.0)  # Adjust scaling as needed
                
                results.append({
                    'message_id': source.get('message_id'),
                    'case_id': source.get('case_id'),
                    'content': source.get('content', ''),
                    'sender': source.get('sender'),
                    'recipient': source.get('recipient'), 
                    'timestamp': source.get('timestamp'),
                    'score': normalized_score,
                    'source': 'opensearch'
                })
            
            logger.debug("OpenSearch returned %d results for query: %s", len(results), query)
            return results
            
        except Exception as e:
            logger.error("OpenSearch search failed: %s", str(e))
            return []
    
    def _faiss_search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Perform semantic search using FAISS.
        
        Args:
            query: Search query string
            limit: Maximum number of results
            
        Returns:
            List of search results with similarity scores and metadata
        """
        if not self._init_faiss() or not self._init_embedding_model():
            logger.warning("FAISS or embedding model not available for semantic search")
            return []
        
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode([query], normalize_embeddings=True)
            
            # Search FAISS index
            scores, indices = self.faiss_index.search(query_embedding.astype(np.float32), limit)
            
            results = []
            message_ids = self.faiss_metadata.get('message_ids', [])
            
            for score, idx in zip(scores[0], indices[0]):
                if idx >= 0 and idx < len(message_ids):  # Valid index
                    message_id = message_ids[idx]
                    
                    # Fetch message details from database
                    message_data = self._get_message_by_id(message_id)
                    if message_data:
                        results.append({
                            'message_id': message_id,
                            'case_id': message_data.get('case_id'),
                            'content': message_data.get('content', ''),
                            'sender': message_data.get('sender'),
                            'recipient': message_data.get('recipient'),
                            'timestamp': message_data.get('timestamp'),
                            'score': float(score),  # FAISS similarity score (0-1)
                            'source': 'faiss'
                        })
            
            logger.debug("FAISS returned %d results for query: %s", len(results), query)
            return results
            
        except Exception as e:
            logger.error("FAISS search failed: %s", str(e))
            return []
    
    def _get_message_by_id(self, message_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch message details from database by ID.
        
        Args:
            message_id: Message identifier
            
        Returns:
            Dictionary with message data or None if not found
        """
        try:
            with get_session() as session:
                message = session.query(Message).filter(Message.id == message_id).first()
                
                if message:
                    return {
                        'case_id': message.case_id,
                        'content': message.content,
                        'sender': message.sender,
                        'recipient': message.recipient,
                        'timestamp': message.timestamp.isoformat() if message.timestamp else None
                    }
                else:
                    logger.warning("Message not found in database: %s", message_id)
                    return None
                    
        except Exception as e:
            logger.error("Database query failed for message %s: %s", message_id, str(e))
            return None
    
    def _merge_results(self, opensearch_results: List[Dict], faiss_results: List[Dict]) -> List[Dict[str, Any]]:
        """
        Merge and rank results from OpenSearch and FAISS.
        
        Args:
            opensearch_results: Results from keyword search
            faiss_results: Results from semantic search
            
        Returns:
            Merged and ranked list of results with boosted scores for duplicates
        """
        # Create lookup for deduplication and score boosting
        message_scores = {}
        
        # Process OpenSearch results
        for result in opensearch_results:
            message_id = result.get('message_id')
            if message_id:
                message_scores[message_id] = {
                    'data': result,
                    'opensearch_score': result.get('score', 0.0),
                    'faiss_score': 0.0,
                    'sources': ['opensearch']
                }
        
        # Process FAISS results
        for result in faiss_results:
            message_id = result.get('message_id')
            if message_id:
                if message_id in message_scores:
                    # Message found in both sources - boost score
                    message_scores[message_id]['faiss_score'] = result.get('score', 0.0)
                    message_scores[message_id]['sources'].append('faiss')
                else:
                    # Message only in FAISS
                    message_scores[message_id] = {
                        'data': result,
                        'opensearch_score': 0.0,
                        'faiss_score': result.get('score', 0.0),
                        'sources': ['faiss']
                    }
        
        # Calculate final scores and create merged results
        merged_results = []
        for message_id, scores in message_scores.items():
            # Hybrid scoring: weighted combination with boost for multi-source
            opensearch_weight = 0.6  # Slightly favor keyword relevance
            faiss_weight = 0.4
            multi_source_boost = 0.2
            
            base_score = (opensearch_weight * scores['opensearch_score'] + 
                         faiss_weight * scores['faiss_score'])
            
            # Boost if found in both sources
            if len(scores['sources']) > 1:
                final_score = min(base_score + multi_source_boost, 1.0)
            else:
                final_score = base_score
            
            # Create merged result
            result = scores['data'].copy()
            result['score'] = final_score
            result['sources'] = scores['sources']
            result['opensearch_score'] = scores['opensearch_score']
            result['faiss_score'] = scores['faiss_score']
            
            merged_results.append(result)
        
        # Sort by final score (descending)
        merged_results.sort(key=lambda x: x['score'], reverse=True)
        
        logger.debug("Merged %d unique results from %d OpenSearch + %d FAISS results",
                    len(merged_results), len(opensearch_results), len(faiss_results))
        
        return merged_results
    
    def _add_snippets(self, results: List[Dict[str, Any]], snippet_length: int = 200) -> List[Dict[str, Any]]:
        """
        Add content snippets to search results.
        
        Args:
            results: List of search results
            snippet_length: Maximum length of content snippet
            
        Returns:
            Results with added snippet field
        """
        for result in results:
            content = result.get('content', '')
            if content:
                # Create snippet (first N characters)
                snippet = content[:snippet_length]
                if len(content) > snippet_length:
                    snippet += "..."
                result['snippet'] = snippet
            else:
                result['snippet'] = ""
        
        return results
    
    def hybrid_search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining OpenSearch and FAISS.
        
        Args:
            query: Natural language search query
            limit: Maximum number of results to return
            
        Returns:
            List of ranked search results with metadata and snippets
        """
        if not query or not query.strip():
            logger.warning("Empty query provided")
            return []
        
        query = query.strip()
        logger.info("Performing hybrid search for query: %s (limit: %d)", query, limit)
        
        # Perform searches in parallel conceptually
        # In practice, these are sequential but could be made parallel with threading
        opensearch_results = self._opensearch_search(query, limit)
        faiss_results = self._faiss_search(query, limit)
        
        # Check if any results found
        if not opensearch_results and not faiss_results:
            logger.warning("No results found for query: %s", query)
            return []
        
        # Merge and rank results
        merged_results = self._merge_results(opensearch_results, faiss_results)
        
        # Limit results
        if len(merged_results) > limit:
            merged_results = merged_results[:limit]
        
        # Add content snippets
        final_results = self._add_snippets(merged_results)
        
        logger.info("Hybrid search returned %d results for query: %s", len(final_results), query)
        return final_results
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get status of retrieval components.
        
        Returns:
            Dictionary with component availability status
        """
        opensearch_available = self._init_opensearch()
        faiss_available = self._init_faiss()
        embedding_available = self._init_embedding_model()
        
        return {
            'opensearch': {
                'available': opensearch_available,
                'host': self.opensearch_host
            },
            'faiss': {
                'available': faiss_available,
                'index_dir': str(self.faiss_index_dir),
                'num_embeddings': self.faiss_metadata.get('num_embeddings', 0) if self.faiss_metadata else 0
            },
            'embeddings': {
                'available': embedding_available,
                'model': self.embedding_model_name
            }
        }


# Global retriever instance (initialized on first use)
_retriever_instance = None


def get_retriever() -> HybridRetriever:
    """
    Get or create global retriever instance.
    
    Returns:
        HybridRetriever instance
    """
    global _retriever_instance
    
    if _retriever_instance is None:
        # Use environment variables for configuration if available
        opensearch_host = os.environ.get('OPENSEARCH_HOST', DEFAULT_OPENSEARCH_HOST)
        faiss_dir = os.environ.get('FAISS_INDEX_DIR', DEFAULT_FAISS_DIR)
        embedding_model = os.environ.get('EMBEDDING_MODEL', DEFAULT_EMBEDDING_MODEL)
        
        _retriever_instance = HybridRetriever(
            opensearch_host=opensearch_host,
            faiss_index_dir=faiss_dir,
            embedding_model=embedding_model
        )
    
    return _retriever_instance


# Convenience function for direct use
def hybrid_search(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Convenience function for hybrid search.
    
    Args:
        query: Search query string
        limit: Maximum number of results
        
    Returns:
        List of search results
    """
    retriever = get_retriever()
    return retriever.hybrid_search(query, limit)


# Export main functions
__all__ = [
    "HybridRetriever",
    "get_retriever", 
    "hybrid_search"
]