# nlp/normalize_phone.py
"""
Phone Number Normalization Module for UFDR Investigator - Phase 3: NLP & Entity Extraction
Author: NLP Engineer
Python 3.11+

Normalizes phone numbers to E.164 format with country detection.
Requires: pip install phonenumbers
"""

import re
import logging
from typing import Optional, Dict, Any
import phonenumbers
from phonenumbers import geocoder, carrier, timezone
from phonenumbers.phonenumberutil import NumberParseException

logger = logging.getLogger(__name__)

# Default country code for phone numbers without country code
DEFAULT_COUNTRY = "US"

# Common country codes for context-aware normalization
COMMON_COUNTRIES = ["US", "GB", "CA", "AU", "DE", "FR", "IT", "ES", "NL", "BE"]


def normalize_phone(phone_str: str, default_country: str = DEFAULT_COUNTRY) -> Optional[str]:
    """
    Normalize a phone number string to E.164 format.
    
    Args:
        phone_str: Raw phone number string to normalize
        default_country: Default country code to use if none detected (default: "US")
        
    Returns:
        E.164 formatted phone number string (e.g., "+12345678901") or None if invalid
    """
    if not phone_str:
        return None
    
    # Clean input - remove common non-digit characters but preserve +
    cleaned = re.sub(r'[^\d+]', '', phone_str.strip())
    
    if not cleaned:
        return None
    
    try:
        # Try parsing with default country first
        parsed_number = phonenumbers.parse(cleaned, default_country)
        
        # Validate the parsed number
        if phonenumbers.is_valid_number(parsed_number):
            # Format to E.164 international format
            normalized = phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)
            logger.debug("Normalized %s to %s", phone_str, normalized)
            return normalized
            
        else:
            logger.debug("Invalid phone number: %s", phone_str)
            return None
            
    except NumberParseException as e:
        # Try with different country codes if default fails
        for country in COMMON_COUNTRIES:
            if country == default_country:
                continue  # Already tried
                
            try:
                parsed_number = phonenumbers.parse(cleaned, country)
                if phonenumbers.is_valid_number(parsed_number):
                    normalized = phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)
                    logger.debug("Normalized %s to %s (country: %s)", phone_str, normalized, country)
                    return normalized
            except NumberParseException:
                continue
        
        logger.debug("Failed to parse phone number: %s (error: %s)", phone_str, str(e))
        return None


def get_phone_metadata(phone_str: str, default_country: str = DEFAULT_COUNTRY) -> Dict[str, Any]:
    """
    Extract metadata for a phone number including country, carrier, timezone.
    
    Args:
        phone_str: Phone number string to analyze
        default_country: Default country code to use if none detected
        
    Returns:
        Dictionary with phone metadata:
        {
            "normalized": "+12345678901",
            "country_code": "US", 
            "region": "United States",
            "carrier": "Verizon",
            "timezones": ["America/New_York"],
            "is_valid": True
        }
    """
    metadata = {
        "normalized": None,
        "country_code": None,
        "region": None,
        "carrier": None,
        "timezones": [],
        "is_valid": False
    }
    
    if not phone_str:
        return metadata
    
    # Clean input
    cleaned = re.sub(r'[^\d+]', '', phone_str.strip())
    
    if not cleaned:
        return metadata
    
    try:
        # Parse the number
        parsed_number = phonenumbers.parse(cleaned, default_country)
        
        # Check if valid
        is_valid = phonenumbers.is_valid_number(parsed_number)
        metadata["is_valid"] = is_valid
        
        if is_valid:
            # Get normalized E.164 format
            metadata["normalized"] = phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)
            
            # Get country code
            metadata["country_code"] = phonenumbers.region_code_for_number(parsed_number)
            
            # Get region/country name
            try:
                region = geocoder.description_for_number(parsed_number, "en")
                metadata["region"] = region if region else None
            except Exception:
                metadata["region"] = None
            
            # Get carrier information
            try:
                carrier_name = carrier.name_for_number(parsed_number, "en")
                metadata["carrier"] = carrier_name if carrier_name else None
            except Exception:
                metadata["carrier"] = None
            
            # Get timezone information
            try:
                timezones_list = timezone.time_zones_for_number(parsed_number)
                metadata["timezones"] = list(timezones_list) if timezones_list else []
            except Exception:
                metadata["timezones"] = []
        
        logger.debug("Phone metadata for %s: %s", phone_str, metadata)
        return metadata
        
    except NumberParseException as e:
        logger.debug("Failed to parse phone number for metadata: %s (error: %s)", phone_str, str(e))
        return metadata


def batch_normalize_phones(phone_list: list, default_country: str = DEFAULT_COUNTRY) -> Dict[str, Optional[str]]:
    """
    Normalize a batch of phone numbers to E.164 format.
    
    Args:
        phone_list: List of phone number strings to normalize
        default_country: Default country code to use if none detected
        
    Returns:
        Dictionary mapping original phone strings to normalized E.164 format (or None if invalid)
    """
    if not phone_list:
        return {}
    
    results = {}
    
    for phone_str in phone_list:
        normalized = normalize_phone(phone_str, default_country)
        results[phone_str] = normalized
    
    # Log summary
    valid_count = sum(1 for v in results.values() if v is not None)
    logger.info("Normalized %d/%d phone numbers successfully", valid_count, len(phone_list))
    
    return results


def is_valid_phone(phone_str: str, default_country: str = DEFAULT_COUNTRY) -> bool:
    """
    Check if a phone number string is valid.
    
    Args:
        phone_str: Phone number string to validate
        default_country: Default country code to use if none detected
        
    Returns:
        True if the phone number is valid, False otherwise
    """
    if not phone_str:
        return False
    
    cleaned = re.sub(r'[^\d+]', '', phone_str.strip())
    
    if not cleaned:
        return False
    
    try:
        parsed_number = phonenumbers.parse(cleaned, default_country)
        return phonenumbers.is_valid_number(parsed_number)
    except NumberParseException:
        return False


# Export main functions
__all__ = [
    "normalize_phone",
    "get_phone_metadata", 
    "batch_normalize_phones",
    "is_valid_phone"
]