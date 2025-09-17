# nlp/__init__.py
"""
NLP & Entity Extraction Module for UFDR Investigator - Phase 3
Author: NLP Engineer
Python 3.11+

Advanced entity extraction and semantic analysis for forensic investigation.
"""

__version__ = "1.0.0"
__author__ = "NLP Engineer"

# Import main functions for easy access
from .extractors import extract_entities, extract_phones, extract_emails, extract_urls, extract_crypto_addresses
from .normalize_phone import normalize_phone, get_phone_metadata, batch_normalize_phones, is_valid_phone

# Conditionally import embeddings worker if dependencies are available
try:
    from .embeddings_worker import EmbeddingsWorker
    __all__ = [
        "extract_entities",
        "extract_phones", 
        "extract_emails",
        "extract_urls",
        "extract_crypto_addresses",
        "normalize_phone",
        "get_phone_metadata",
        "batch_normalize_phones", 
        "is_valid_phone",
        "EmbeddingsWorker"
    ]
except ImportError:
    # embeddings_worker requires sentence-transformers and faiss
    __all__ = [
        "extract_entities",
        "extract_phones",
        "extract_emails", 
        "extract_urls",
        "extract_crypto_addresses",
        "normalize_phone",
        "get_phone_metadata",
        "batch_normalize_phones",
        "is_valid_phone"
    ]