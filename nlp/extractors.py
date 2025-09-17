# nlp/extractors.py
"""
Entity Extraction Module for UFDR Investigator - Phase 3: NLP & Entity Extraction
Author: NLP Engineer
Python 3.11+

Extracts structured entities from message text using regex patterns.
Supports phones, crypto addresses, emails, and URLs.
"""

import re
import logging
from typing import Dict, List, Set

logger = logging.getLogger(__name__)

# Compiled regex patterns for better performance
PHONE_PATTERN = re.compile(r'\+?\d{7,15}')
EMAIL_PATTERN = re.compile(r'[\w\.-]+@[\w\.-]+\.\w+')
URL_PATTERN = re.compile(r'http[s]?://\S+')

# Cryptocurrency address patterns
ETHEREUM_PATTERN = re.compile(r'0x[a-fA-F0-9]{40}')
BITCOIN_PATTERN = re.compile(r'[13][a-km-zA-HJ-NP-Z1-9]{25,34}')


def extract_phones(text: str) -> List[str]:
    """
    Extract phone numbers from text using regex pattern.
    
    Args:
        text: Input text to search for phone numbers
        
    Returns:
        List of unique phone number strings found
    """
    if not text:
        return []
    
    matches = PHONE_PATTERN.findall(text)
    # Remove duplicates while preserving order
    seen: Set[str] = set()
    unique_matches = []
    for match in matches:
        if match not in seen:
            seen.add(match)
            unique_matches.append(match)
    
    return unique_matches


def extract_emails(text: str) -> List[str]:
    """
    Extract email addresses from text using regex pattern.
    
    Args:
        text: Input text to search for email addresses
        
    Returns:
        List of unique email address strings found
    """
    if not text:
        return []
    
    matches = EMAIL_PATTERN.findall(text)
    # Remove duplicates while preserving order
    seen: Set[str] = set()
    unique_matches = []
    for match in matches:
        if match not in seen:
            seen.add(match)
            unique_matches.append(match)
    
    return unique_matches


def extract_urls(text: str) -> List[str]:
    """
    Extract URLs from text using regex pattern.
    
    Args:
        text: Input text to search for URLs
        
    Returns:
        List of unique URL strings found
    """
    if not text:
        return []
    
    matches = URL_PATTERN.findall(text)
    # Remove duplicates while preserving order
    seen: Set[str] = set()
    unique_matches = []
    for match in matches:
        if match not in seen:
            seen.add(match)
            unique_matches.append(match)
    
    return unique_matches


def extract_crypto_addresses(text: str) -> List[str]:
    """
    Extract cryptocurrency addresses from text.
    Supports Ethereum and Bitcoin address formats.
    
    Args:
        text: Input text to search for crypto addresses
        
    Returns:
        List of unique cryptocurrency address strings found
    """
    if not text:
        return []
    
    crypto_addresses = []
    seen: Set[str] = set()
    
    # Extract Ethereum addresses (0x followed by 40 hex characters)
    eth_matches = ETHEREUM_PATTERN.findall(text)
    for match in eth_matches:
        if match not in seen:
            seen.add(match)
            crypto_addresses.append(match)
    
    # Extract Bitcoin addresses (base58 format starting with 1 or 3)
    btc_matches = BITCOIN_PATTERN.findall(text)
    for match in btc_matches:
        if match not in seen:
            seen.add(match)
            crypto_addresses.append(match)
    
    return crypto_addresses


def extract_entities(text: str) -> Dict[str, List[str]]:
    """
    Extract all supported entities from message text.
    
    Args:
        text: Input message text to analyze
        
    Returns:
        Dictionary with entity types as keys and lists of found entities as values:
        {
            "phones": ["list", "of", "phone", "numbers"],
            "crypto_addresses": ["list", "of", "crypto", "addresses"],
            "emails": ["list", "of", "email", "addresses"],
            "urls": ["list", "of", "urls"]
        }
    """
    if not text:
        # Return empty structure for empty/None input
        return {
            "phones": [],
            "crypto_addresses": [],
            "emails": [],
            "urls": []
        }
    
    logger.debug("Extracting entities from text: %s...", text[:100])
    
    # Extract each entity type
    phones = extract_phones(text)
    crypto_addresses = extract_crypto_addresses(text)
    emails = extract_emails(text)
    urls = extract_urls(text)
    
    entities = {
        "phones": phones,
        "crypto_addresses": crypto_addresses,
        "emails": emails,
        "urls": urls
    }
    
    # Log summary
    total_entities = sum(len(entity_list) for entity_list in entities.values())
    if total_entities > 0:
        logger.debug("Found %d entities: %s", total_entities, entities)
    
    return entities


def validate_bitcoin_address(address: str) -> bool:
    """
    Basic validation for Bitcoin addresses using regex pattern.
    Note: This is a simple format check, not a full cryptographic validation.
    
    Args:
        address: Bitcoin address string to validate
        
    Returns:
        True if address matches Bitcoin format pattern, False otherwise
    """
    if not address:
        return False
    
    return bool(BITCOIN_PATTERN.fullmatch(address))


def validate_ethereum_address(address: str) -> bool:
    """
    Basic validation for Ethereum addresses using regex pattern.
    Note: This is a simple format check, not a full checksum validation.
    
    Args:
        address: Ethereum address string to validate
        
    Returns:
        True if address matches Ethereum format pattern, False otherwise
    """
    if not address:
        return False
    
    return bool(ETHEREUM_PATTERN.fullmatch(address))


# Export main functions
__all__ = [
    "extract_entities",
    "extract_phones", 
    "extract_emails",
    "extract_urls",
    "extract_crypto_addresses",
    "validate_bitcoin_address",
    "validate_ethereum_address"
]