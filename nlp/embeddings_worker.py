# nlp/embeddings_worker.py
"""
Embeddings Generation Worker for UFDR Investigator - Phase 3: NLP & Entity Extraction
Author: NLP Engineer
Python 3.11+

Generates semantic embeddings for messages using sentence-transformers.
Creates FAISS index for efficient similarity search.

Requires:
    pip install sentence-transformers
    pip install faiss-cpu  # or faiss-gpu for GPU acceleration
"""

import argparse
import json
import logging
import os
import pickle
from pathlib import Path
from typing import List, Dict, Any, Optional

import numpy as np

try:
    import faiss
except ImportError:
    faiss = None

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

logger = logging.getLogger(__name__)

# Default model for text embeddings
DEFAULT_MODEL = "all-MiniLM-L6-v2"  # Fast, good quality general-purpose model
# Alternative models:
# "all-mpnet-base-v2"  # Higher quality but slower
# "multi-qa-MiniLM-L6-cos-v1"  # Optimized for Q&A/search


class EmbeddingsWorker:
    """
    Worker class for generating and managing message embeddings.
    """
    
    def __init__(self, model_name: str = DEFAULT_MODEL):
        """
        Initialize the embeddings worker with a sentence transformer model.
        
        Args:
            model_name: Name of the sentence-transformers model to use
        """
        if SentenceTransformer is None:
            raise ImportError("sentence-transformers is required. Install with: pip install sentence-transformers")
        
        self.model_name = model_name
        self.model = None
        self.embedding_dim = None
        
        logger.info("Initializing EmbeddingsWorker with model: %s", model_name)
    
    def load_model(self):
        """Load the sentence transformer model."""
        if self.model is None:
            logger.info("Loading sentence transformer model: %s", self.model_name)
            self.model = SentenceTransformer(self.model_name)
            
            # Get embedding dimension
            test_embedding = self.model.encode(["test"])
            self.embedding_dim = len(test_embedding[0])
            logger.info("Model loaded. Embedding dimension: %d", self.embedding_dim)
    
    def generate_embeddings(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """
        Generate embeddings for a list of texts.
        
        Args:
            texts: List of text strings to embed
            batch_size: Batch size for encoding (default: 32)
            
        Returns:
            NumPy array of embeddings with shape (len(texts), embedding_dim)
        """
        if not texts:
            return np.array([])
        
        self.load_model()
        
        logger.info("Generating embeddings for %d texts", len(texts))
        
        # Generate embeddings in batches
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=True,
            convert_to_numpy=True,
            normalize_embeddings=True  # L2 normalization for cosine similarity
        )
        
        logger.info("Generated embeddings with shape: %s", embeddings.shape)
        return embeddings
    
    def process_jsonl_file(self, input_file: Path, output_dir: Path, text_field: str = "content") -> Dict[str, Any]:
        """
        Process a JSONL file to generate embeddings for message content.
        
        Args:
            input_file: Path to input JSONL file containing messages
            output_dir: Directory to save output files
            text_field: Field name containing text to embed (default: "content")
            
        Returns:
            Dictionary with processing statistics
        """
        if not input_file.exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Read messages from JSONL
        messages = []
        texts = []
        message_ids = []
        
        logger.info("Reading messages from: %s", input_file)
        
        with open(input_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    message = json.loads(line.strip())
                    text_content = message.get(text_field, "")
                    
                    if text_content and isinstance(text_content, str):
                        messages.append(message)
                        texts.append(text_content)
                        message_ids.append(message.get("id", f"msg_{line_num}"))
                    
                except json.JSONDecodeError as e:
                    logger.warning("Failed to parse JSON on line %d: %s", line_num, str(e))
                    continue
        
        if not texts:
            logger.warning("No valid text content found in %s", input_file)
            return {"processed": 0, "skipped": 0}
        
        logger.info("Found %d messages with text content", len(texts))
        
        # Generate embeddings
        embeddings = self.generate_embeddings(texts)
        
        # Save embeddings and metadata
        embeddings_file = output_dir / "embeddings.npy"
        metadata_file = output_dir / "metadata.json"
        
        # Save embeddings as NumPy array
        np.save(embeddings_file, embeddings)
        logger.info("Saved embeddings to: %s", embeddings_file)
        
        # Save metadata
        metadata = {
            "model_name": self.model_name,
            "embedding_dim": self.embedding_dim,
            "num_embeddings": len(embeddings),
            "message_ids": message_ids,
            "text_field": text_field,
            "input_file": str(input_file)
        }
        
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        logger.info("Saved metadata to: %s", metadata_file)
        
        # Create FAISS index if available
        if faiss is not None:
            self.create_faiss_index(embeddings, output_dir)
        else:
            logger.warning("FAISS not available. Skipping index creation. Install with: pip install faiss-cpu")
        
        return {
            "processed": len(texts),
            "skipped": 0,
            "embedding_dim": self.embedding_dim,
            "output_dir": str(output_dir)
        }
    
    def create_faiss_index(self, embeddings: np.ndarray, output_dir: Path):
        """
        Create a FAISS index for efficient similarity search.
        
        Args:
            embeddings: NumPy array of embeddings
            output_dir: Directory to save the FAISS index
        """
        if faiss is None:
            logger.warning("FAISS not available. Cannot create index.")
            return
        
        if len(embeddings) == 0:
            logger.warning("No embeddings to index")
            return
        
        logger.info("Creating FAISS index for %d embeddings", len(embeddings))
        
        # Create FAISS index (using IndexFlatIP for cosine similarity with normalized vectors)
        dimension = embeddings.shape[1]
        index = faiss.IndexFlatIP(dimension)  # Inner product (cosine similarity for normalized vectors)
        
        # Add embeddings to index
        index.add(embeddings.astype(np.float32))
        
        # Save index
        index_file = output_dir / "faiss.index"
        faiss.write_index(index, str(index_file))
        logger.info("Saved FAISS index to: %s", index_file)
    
    def search_similar(self, query_text: str, embeddings_dir: Path, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Search for similar messages given a query text.
        
        Args:
            query_text: Text to search for similar messages
            embeddings_dir: Directory containing embeddings and FAISS index
            top_k: Number of top similar results to return
            
        Returns:
            List of dictionaries with similarity results
        """
        # Load metadata
        metadata_file = embeddings_dir / "metadata.json"
        if not metadata_file.exists():
            raise FileNotFoundError(f"Metadata file not found: {metadata_file}")
        
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        # Load FAISS index
        index_file = embeddings_dir / "faiss.index"
        if not index_file.exists():
            raise FileNotFoundError(f"FAISS index not found: {index_file}")
        
        if faiss is None:
            raise ImportError("FAISS is required for similarity search. Install with: pip install faiss-cpu")
        
        index = faiss.read_index(str(index_file))
        
        # Generate query embedding
        self.load_model()
        query_embedding = self.model.encode([query_text], normalize_embeddings=True)
        
        # Search for similar embeddings
        scores, indices = index.search(query_embedding.astype(np.float32), top_k)
        
        # Format results
        results = []
        message_ids = metadata["message_ids"]
        
        for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
            if idx < len(message_ids):
                results.append({
                    "rank": i + 1,
                    "message_id": message_ids[idx],
                    "similarity_score": float(score),
                    "index": int(idx)
                })
        
        return results


def main():
    """
    CLI entry point for embeddings generation.
    """
    parser = argparse.ArgumentParser(description="Generate semantic embeddings for UFDR message data")
    parser.add_argument("--input", required=True, help="Input JSONL file with messages")
    parser.add_argument("--out", required=True, help="Output directory for embeddings")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Sentence transformer model (default: {DEFAULT_MODEL})")
    parser.add_argument("--text-field", default="content", help="Field containing text to embed (default: content)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Validate inputs
    input_file = Path(args.input)
    output_dir = Path(args.out)
    
    if not input_file.exists():
        logger.error("Input file not found: %s", input_file)
        return 1
    
    try:
        # Initialize worker and process file
        worker = EmbeddingsWorker(model_name=args.model)
        result = worker.process_jsonl_file(input_file, output_dir, args.text_field)
        
        logger.info("Processing complete: %s", result)
        print(f"Successfully processed {result['processed']} messages")
        print(f"Output saved to: {result['output_dir']}")
        
        return 0
        
    except Exception as e:
        logger.error("Processing failed: %s", str(e))
        return 1


if __name__ == "__main__":
    exit(main())