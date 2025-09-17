# nlp/README.md
# Phase 3 — NLP & Entity Extraction

Advanced entity extraction and semantic analysis module for UFDR forensic investigation.

## Features

- **Entity Extraction**: Extract phones, emails, URLs, and cryptocurrency addresses from message text
- **Phone Normalization**: Convert phone numbers to standardized E.164 format with country detection
- **Semantic Embeddings**: Generate vector embeddings for message content with similarity search
- **FAISS Indexing**: Fast approximate nearest neighbor search for large message datasets

## Installation

Install required dependencies:

```bash
pip install phonenumbers sentence-transformers faiss-cpu
```

For GPU acceleration (optional):
```bash
pip install faiss-gpu
```

## Usage

### Entity Extraction

```python
from nlp.extractors import extract_entities

text = "Call me at +1-555-123-4567 or email user@example.com"
entities = extract_entities(text)
print(entities)
# {
#     "phones": ["+1-555-123-4567"],
#     "emails": ["user@example.com"],
#     "urls": [],
#     "crypto_addresses": []
# }
```

### Phone Normalization

```python
from nlp.normalize_phone import normalize_phone, get_phone_metadata

# Normalize to E.164 format
normalized = normalize_phone("(555) 123-4567", default_country="US")
print(normalized)  # "+15551234567"

# Get detailed metadata
metadata = get_phone_metadata("+15551234567")
print(metadata)
# {
#     "normalized": "+15551234567",
#     "country_code": "US",
#     "region": "United States",
#     "carrier": "Verizon",
#     "timezones": ["America/New_York"],
#     "is_valid": True
# }
```

### Semantic Embeddings

Generate embeddings for message content:

```bash
python nlp/embeddings_worker.py \
  --input ./output/CASE-001/parsed/messages.jsonl \
  --out ./vectors/ \
  --model all-MiniLM-L6-v2
```

Search for similar messages:

```python
from nlp.embeddings_worker import EmbeddingsWorker

worker = EmbeddingsWorker()
results = worker.search_similar(
    query_text="suspicious transaction", 
    embeddings_dir="./vectors/",
    top_k=5
)

for result in results:
    print(f"Rank {result['rank']}: {result['message_id']} (score: {result['similarity_score']:.3f})")
```

## Command Line Tools

### Extract Entities from JSONL

```python
import json
from nlp.extractors import extract_entities

# Process messages.jsonl file
with open("messages.jsonl", "r") as f:
    for line in f:
        message = json.loads(line)
        if message.get("content"):
            entities = extract_entities(message["content"])
            message["entities"] = entities
            print(json.dumps(message))
```

### Batch Phone Normalization

```python
from nlp.normalize_phone import batch_normalize_phones

phones = ["(555) 123-4567", "+44 20 7946 0958", "invalid"]
normalized = batch_normalize_phones(phones, default_country="US")

for original, norm in normalized.items():
    print(f"{original} -> {norm}")
```

## Integration with Backend

The NLP modules integrate with the backend storage system:

```python
from backend.models import Message
from backend.db import get_session
from nlp.extractors import extract_entities
from nlp.normalize_phone import normalize_phone

# Process stored messages
with get_session() as session:
    messages = session.query(Message).filter(Message.entities.is_(None)).limit(100)
    
    for message in messages:
        if message.content:
            # Extract entities
            entities = extract_entities(message.content)
            
            # Normalize phone numbers in entities
            if entities["phones"]:
                normalized_phones = []
                for phone in entities["phones"]:
                    normalized = normalize_phone(phone)
                    if normalized:
                        normalized_phones.append(normalized)
                entities["phones_normalized"] = normalized_phones
            
            # Store entities back to message
            message.entities = entities
    
    session.commit()
```

## Models and Performance

### Embedding Models

- **all-MiniLM-L6-v2** (default): Fast, good quality, 384 dimensions
- **all-mpnet-base-v2**: Higher quality, slower, 768 dimensions  
- **multi-qa-MiniLM-L6-cos-v1**: Optimized for Q&A and search tasks

### Performance Guidelines

- **Entity Extraction**: ~1000 messages/second (regex-based)
- **Phone Normalization**: ~500 phones/second (with country detection)
- **Embeddings Generation**: ~100-500 messages/second (depends on model and hardware)
- **FAISS Search**: <1ms for top-K queries on 1M+ embeddings

## Output Formats

### Entity Extraction Output

```json
{
  "phones": ["+15551234567", "+441234567890"],
  "emails": ["user@domain.com"],
  "urls": ["https://example.com"],
  "crypto_addresses": ["0x742f35Cc8E7gB42B1a68d7a9a..."]
}
```

### Embeddings Output Structure

```
vectors/
├── embeddings.npy          # NumPy array of embeddings
├── metadata.json           # Model info, message IDs, dimensions
└── faiss.index            # FAISS index for similarity search
```

### Phone Metadata Output

```json
{
  "normalized": "+15551234567",
  "country_code": "US",
  "region": "New York, NY",
  "carrier": "Verizon Wireless",
  "timezones": ["America/New_York"],
  "is_valid": true
}
```

## Error Handling

The modules include comprehensive error handling:

- **Invalid phone numbers**: Return `None` or `False` for validation
- **Missing dependencies**: Clear error messages with installation instructions
- **Malformed input**: Graceful degradation with logging
- **File I/O errors**: Detailed error messages with file paths

## Logging

All modules use Python's standard logging framework:

```python
import logging
logging.basicConfig(level=logging.INFO)

# Enable debug logging for detailed output
logging.getLogger('nlp').setLevel(logging.DEBUG)
```

## Testing

Run tests for the NLP modules:

```bash
# Entity extraction tests
python -c "
from nlp.extractors import extract_entities
assert extract_entities('Call +1-555-123-4567')['phones'] == ['+1-555-123-4567']
print('Entity extraction: PASS')
"

# Phone normalization tests  
python -c "
from nlp.normalize_phone import normalize_phone
assert normalize_phone('(555) 123-4567') == '+15551234567'
print('Phone normalization: PASS')
"
```