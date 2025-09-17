# backend/opensearch_index.py
"""
Index messages into OpenSearch for full-text search.

Usage:
    export OPENSEARCH_URL=http://localhost:9200
    python backend/opensearch_index.py --input ./output/CASE-001/parsed/messages.jsonl --index messages
"""

import argparse
import json
import logging
from pathlib import Path
from typing import Dict, Any, Generator, List

from opensearchpy import OpenSearch, helpers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("opensearch_index")


def get_client() -> OpenSearch:
    import os

    url = os.environ.get("OPENSEARCH_URL", "http://localhost:9200")
    logger.info("Connecting to OpenSearch at %s", url)
    client = OpenSearch(hosts=[url], timeout=30, max_retries=3, retry_on_timeout=True)
    return client


def create_index_if_missing(client: OpenSearch, index_name: str) -> None:
    if client.indices.exists(index=index_name):
        logger.info("Index '%s' already exists", index_name)
        return

    mapping = {
        "settings": {"index": {"number_of_shards": 1, "number_of_replicas": 0}},
        "mappings": {
            "properties": {
                "case_id": {"type": "keyword"},
                "body": {"type": "text"},
                "sender": {"type": "keyword"},
                "recipient": {"type": "keyword"},
                "timestamp_utc": {"type": "date"},
                "entities": {"type": "object"},
                "attachments": {"type": "object"},
            }
        },
    }
    client.indices.create(index=index_name, body=mapping)
    logger.info("Created index '%s' with mapping", index_name)


def read_messages_jsonl(path: Path) -> Generator[Dict[str, Any], None, None]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                doc = json.loads(line)
                yield doc
            except Exception as e:
                logger.error("Failed to parse line: %s", e)
                continue


def docs_to_bulk_actions(docs: List[Dict[str, Any]], index_name: str) -> List[Dict[str, Any]]:
    actions = []
    for d in docs:
        doc_id = d.get("id") or d.get("message_id")
        participants = d.get("participants", [])
        action = {
            "_op_type": "index",
            "_index": index_name,
            "_id": doc_id,
            "_source": {
                "id": doc_id,
                "case_id": d.get("case_id"),
                "body": d.get("body"),
                "sender": d.get("sender") or (participants[0] if participants else None),
                "recipient": d.get("recipient") or (participants[1] if len(participants) > 1 else None),
                "timestamp_utc": d.get("timestamp_utc") or d.get("timestamp"),
                "entities": d.get("entities"),
                "attachments": d.get("attachments"),
            },
        }
        actions.append(action)
    return actions


def bulk_index(client: OpenSearch, index_name: str, docs_gen) -> None:
    BATCH = 500
    batch = []
    for doc in docs_gen:
        batch.append(doc)
        if len(batch) >= BATCH:
            actions = docs_to_bulk_actions(batch, index_name)
            helpers.bulk(client, actions)
            logger.info("Indexed batch of %d documents", len(batch))
            batch = []
    if batch:
        actions = docs_to_bulk_actions(batch, index_name)
        helpers.bulk(client, actions)
        logger.info("Indexed final batch of %d documents", len(batch))


def main():
    parser = argparse.ArgumentParser(description="Index parsed messages into OpenSearch")
    parser.add_argument("--input", required=True, help="Path to messages.jsonl")
    parser.add_argument("--index", default="messages", help="OpenSearch index name")
    args = parser.parse_args()

    path = Path(args.input)
    if not path.exists():
        logger.error("Input file not found: %s", path)
        raise SystemExit(1)

    client = get_client()
    create_index_if_missing(client, args.index)

    docs_gen = read_messages_jsonl(path)
    bulk_index(client, args.index, docs_gen)
    logger.info("Indexing complete.")


if __name__ == "__main__":
    main()

def get_opensearch_client(url: str) -> OpenSearch:
    """
    Create and return OpenSearch client.
    
    Args:
        url: OpenSearch cluster URL
        
    Returns:
        OpenSearch client instance
    """
    logger.info(f"Connecting to OpenSearch at {url}")
    
    # Parse URL to extract host and port
    if url.startswith("http://") or url.startswith("https://"):
        # For development/demo with basic auth
        client = OpenSearch(
            hosts=[url],
            http_compress=True,  # Enable compression
            verify_certs=False,  # For development only
            ssl_assert_hostname=False,
            ssl_show_warn=False,
            timeout=30,
            max_retries=3,
            retry_on_timeout=True
        )
    else:
        # Fallback for custom configurations
        client = OpenSearch([url])
    
    return client

def create_messages_index(client: OpenSearch, index_name: str) -> bool:
    """
    Create messages index with optimized mapping for search.
    
    Args:
        client: OpenSearch client
        index_name: Name of the index to create
        
    Returns:
        True if index was created or already exists, False on error
    """
    # Define index mapping for optimal search performance
    mapping = {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0,  # For single-node development
            "analysis": {
                "analyzer": {
                    "message_analyzer": {
                        "tokenizer": "standard",
                        "filter": ["lowercase", "stop"]
                    }
                }
            }
        },
        "mappings": {
            "properties": {
                "id": {
                    "type": "keyword"
                },
                "case_id": {
                    "type": "keyword"
                },
                "timestamp_utc": {
                    "type": "date",
                    "format": "strict_date_optional_time||epoch_millis"
                },
                "sender": {
                    "type": "keyword",
                    "fields": {
                        "text": {
                            "type": "text",
                            "analyzer": "message_analyzer"
                        }
                    }
                },
                "recipient": {
                    "type": "keyword", 
                    "fields": {
                        "text": {
                            "type": "text",
                            "analyzer": "message_analyzer"
                        }
                    }
                },
                "body": {
                    "type": "text",
                    "analyzer": "message_analyzer",
                    "fields": {
                        "keyword": {
                            "type": "keyword",
                            "ignore_above": 256
                        }
                    }
                },
                "entities": {
                    "type": "object",
                    "properties": {
                        "phone_numbers": {
                            "type": "keyword"
                        },
                        "crypto_addresses": {
                            "type": "keyword"
                        },
                        "urls": {
                            "type": "keyword"
                        }
                    }
                },
                "attachments": {
                    "type": "keyword"
                },
                "direction": {
                    "type": "keyword"
                },
                "participants": {
                    "type": "keyword"
                },
                "raw_source": {
                    "type": "keyword"
                },
                "hash": {
                    "type": "keyword"
                }
            }
        }
    }
    
    try:
        # Check if index already exists
        if client.indices.exists(index=index_name):
            logger.info(f"Index '{index_name}' already exists")
            return True
        
        # Create the index
        logger.info(f"Creating index '{index_name}'...")
        response = client.indices.create(index=index_name, body=mapping)
        
        if response.get("acknowledged"):
            logger.info(f"Index '{index_name}' created successfully")
            return True
        else:
            logger.error(f"Failed to create index '{index_name}': {response}")
            return False
            
    except RequestError as e:
        logger.error(f"Error creating index '{index_name}': {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error creating index '{index_name}': {e}")
        return False

def parse_datetime_for_es(dt_str: str) -> str:
    """
    Parse and format datetime for Elasticsearch/OpenSearch.
    
    Args:
        dt_str: ISO format datetime string
        
    Returns:
        Formatted datetime string or original if parsing fails
    """
    if not dt_str:
        return dt_str
    
    try:
        # Handle Z suffix (UTC timezone)
        if dt_str.endswith('Z'):
            dt_str = dt_str[:-1] + '+00:00'
        dt = datetime.fromisoformat(dt_str)
        return dt.isoformat()
    except ValueError:
        logger.warning(f"Failed to parse datetime '{dt_str}', using as-is")
        return dt_str

def generate_message_docs(jsonl_path: Path) -> Generator[Dict[str, Any], None, None]:
    """
    Generator that yields message documents for bulk indexing.
    
    Args:
        jsonl_path: Path to messages.jsonl file
        
    Yields:
        Document dictionaries for OpenSearch indexing
    """
    logger.info(f"Reading messages from {jsonl_path}")
    
    with jsonl_path.open('r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            try:
                data = json.loads(line.strip())
                
                # Prepare document for indexing
                doc = {
                    "_index": "messages",  # Will be overridden by caller
                    "_id": data.get('id'),
                    "_source": {
                        "id": data.get('id'),
                        "case_id": data.get('case_id'),
                        "timestamp_utc": parse_datetime_for_es(data.get('timestamp_utc', '')),
                        "sender": data.get('sender'),
                        "recipient": data.get('recipient'),
                        "body": data.get('body', ''),
                        "entities": data.get('entities', {}),
                        "attachments": data.get('attachments', []),
                        "direction": data.get('direction'),
                        "participants": data.get('participants', []),
                        "raw_source": data.get('raw_source'),
                        "hash": data.get('hash')
                    }
                }
                
                yield doc
                
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON at line {line_num}: {e}")
            except Exception as e:
                logger.error(f"Error processing message at line {line_num}: {e}")

def bulk_index_messages(client: OpenSearch, jsonl_path: Path, index_name: str) -> Dict[str, int]:
    """
    Bulk index messages from JSONL file into OpenSearch.
    
    Args:
        client: OpenSearch client
        jsonl_path: Path to messages.jsonl file
        index_name: Name of the index
        
    Returns:
        Dictionary with indexing statistics
    """
    if not jsonl_path.exists():
        logger.warning(f"Messages file not found: {jsonl_path}")
        return {"indexed": 0, "errors": 0}
    
    indexed = 0
    errors = 0
    
    try:
        # Generate documents and perform bulk indexing
        docs = generate_message_docs(jsonl_path)
        
        # Update index name in documents
        def update_index(doc_gen):
            for doc in doc_gen:
                doc["_index"] = index_name
                yield doc
        
        logger.info(f"Starting bulk indexing to '{index_name}'...")
        
        # Perform bulk indexing with error handling
        for success, info in bulk(
            client,
            update_index(docs),
            chunk_size=100,  # Process in batches of 100
            request_timeout=60,
            max_retries=3,
            initial_backoff=2,
            max_backoff=600
        ):
            if success:
                indexed += 1
            else:
                errors += 1
                logger.error(f"Indexing error: {info}")
        
        logger.info(f"Bulk indexing completed: {indexed} indexed, {errors} errors")
        
    except Exception as e:
        logger.error(f"Error during bulk indexing: {e}")
        errors += 1
    
    return {"indexed": indexed, "errors": errors}

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Index messages into OpenSearch for fast keyword search"
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to messages.jsonl file"
    )
    parser.add_argument(
        "--index",
        default="messages",
        help="OpenSearch index name (default: messages)"
    )
    parser.add_argument(
        "--opensearch-url",
        help="OpenSearch URL (overrides OPENSEARCH_URL env var)"
    )
    parser.add_argument(
        "--recreate-index",
        action="store_true",
        help="Delete and recreate the index"
    )
    
    args = parser.parse_args()
    
    # Get OpenSearch URL
    opensearch_url = args.opensearch_url or os.getenv("OPENSEARCH_URL", "http://localhost:9200")
    
    # Validate input file
    jsonl_path = Path(args.input)
    if not jsonl_path.exists():
        logger.error(f"Input file does not exist: {jsonl_path}")
        sys.exit(1)
    
    try:
        # Create OpenSearch client
        client = get_opensearch_client(opensearch_url)
        
        # Test connection
        info = client.info()
        logger.info(f"Connected to OpenSearch: {info['version']['distribution']} {info['version']['number']}")
        
        # Handle index recreation
        if args.recreate_index:
            if client.indices.exists(index=args.index):
                logger.info(f"Deleting existing index '{args.index}'...")
                client.indices.delete(index=args.index)
        
        # Create index
        if not create_messages_index(client, args.index):
            logger.error("Failed to create index")
            sys.exit(1)
        
        # Index messages
        stats = bulk_index_messages(client, jsonl_path, args.index)
        
        # Print summary
        logger.info("Indexing Summary:")
        logger.info(f"  Documents indexed: {stats['indexed']}")
        logger.info(f"  Errors: {stats['errors']}")
        
        if stats['errors'] > 0:
            logger.warning("Some documents failed to index. Check logs for details.")
            sys.exit(1)
        
        logger.info("Indexing completed successfully")
        
    except ConnectionError as e:
        logger.error(f"Failed to connect to OpenSearch: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()