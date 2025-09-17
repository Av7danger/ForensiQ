# backend/etl_load.py
"""
ETL loader: reads parsed JSONL files and upserts into the database.

Usage:
    export DATABASE_URL=postgresql://user:pass@localhost:5432/ufdr
    python backend/etl_load.py --input ./output/CASE-001/parsed/ --case CASE-001
"""

import argparse
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from .db import SessionLocal, init_db, get_engine
from .models import Message, Contact, Call, File

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("etl")


def parse_iso_or_none(value: Optional[str]) -> Optional[datetime]:
    if value is None:
        return None
    # Try ISO first
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        pass
    # Try numeric epoch
    try:
        n = int(value)
        if n > 1_000_000_000_000:  # milliseconds
            n = n // 1000
        return datetime.utcfromtimestamp(n)
    except Exception:
        return None


def upsert_message(session: Session, obj: Dict[str, Any]) -> None:
    msg_id = obj.get("id")
    if not msg_id:
        logger.warning("Skipping message without id: %s", obj)
        return
    existing = session.get(Message, msg_id)
    ts = parse_iso_or_none(obj.get("timestamp_utc") or obj.get("timestamp"))
    if existing:
        # update fields
        existing.case_id = obj.get("case_id", existing.case_id)
        existing.device_id = obj.get("device_id", existing.device_id)
        existing.timestamp_utc = ts or existing.timestamp_utc
        existing.direction = obj.get("direction", existing.direction)
        existing.sender = obj.get("sender", existing.sender)
        existing.recipient = obj.get("recipient", existing.recipient)
        existing.body = obj.get("body", existing.body)
        existing.entities = obj.get("entities", existing.entities)
        existing.attachments = obj.get("attachments", existing.attachments)
        existing.raw_source = obj.get("raw_source", existing.raw_source)
        existing.hash = obj.get("hash", existing.hash)
    else:
        participants = obj.get("participants", [])
        new = Message(
            id=msg_id,
            case_id=obj.get("case_id"),
            device_id=obj.get("device_id"),
            timestamp_utc=ts,
            direction=obj.get("direction"),
            sender=participants[0] if participants else obj.get("sender"),
            recipient=participants[1] if len(participants) > 1 else obj.get("recipient"),
            body=obj.get("body"),
            entities=obj.get("entities"),
            attachments=obj.get("attachments"),
            raw_source=obj.get("raw_source"),
            hash=obj.get("hash"),
        )
        session.add(new)


def upsert_contact(session: Session, obj: Dict[str, Any]) -> None:
    cid = obj.get("id")
    if not cid:
        logger.warning("Skipping contact without id: %s", obj)
        return
    existing = session.get(Contact, cid)
    if existing:
        existing.case_id = obj.get("case_id", existing.case_id)
        existing.name = obj.get("name", existing.name)
        existing.phones = obj.get("phones", existing.phones)
        existing.raw = obj.get("raw", existing.raw)
    else:
        new = Contact(
            id=cid,
            case_id=obj.get("case_id"),
            name=obj.get("name"),
            phones=obj.get("phones"),
            raw=obj.get("raw"),
        )
        session.add(new)


def upsert_call(session: Session, obj: Dict[str, Any]) -> None:
    cid = obj.get("id")
    if not cid:
        logger.warning("Skipping call without id: %s", obj)
        return
    existing = session.get(Call, cid)
    ts = parse_iso_or_none(obj.get("timestamp_utc") or obj.get("timestamp"))
    if existing:
        existing.case_id = obj.get("case_id", existing.case_id)
        existing.timestamp_utc = ts or existing.timestamp_utc
        existing.caller = obj.get("caller", existing.caller)
        existing.callee = obj.get("callee", existing.callee)
        existing.duration = obj.get("duration", existing.duration)
        existing.raw = obj.get("raw", existing.raw)
    else:
        new = Call(
            id=cid,
            case_id=obj.get("case_id"),
            timestamp_utc=ts,
            caller=obj.get("caller"),
            callee=obj.get("callee"),
            duration=obj.get("duration"),
            raw=obj.get("raw"),
        )
        session.add(new)


def upsert_file(session: Session, obj: Dict[str, Any]) -> None:
    blob_id = obj.get("blob_id")
    if not blob_id:
        logger.warning("Skipping file without blob_id: %s", obj)
        return
    existing = session.get(File, blob_id)
    mtime = parse_iso_or_none(obj.get("mtime_utc"))
    related_msg_ids = obj.get("related_message_ids", [])
    if existing:
        existing.case_id = obj.get("case_id", existing.case_id)
        existing.blob_path = obj.get("blob_path", existing.blob_path)
        existing.sha256 = obj.get("sha256", existing.sha256)
        existing.size_bytes = obj.get("size_bytes", existing.size_bytes)
        existing.mtime_utc = mtime or existing.mtime_utc
        existing.related_message_id = related_msg_ids[0] if related_msg_ids else None
    else:
        new = File(
            blob_id=blob_id,
            case_id=obj.get("case_id"),
            blob_path=obj.get("blob_path"),
            sha256=obj.get("sha256"),
            size_bytes=obj.get("size_bytes"),
            mtime_utc=mtime,
            related_message_id=related_msg_ids[0] if related_msg_ids else None,
        )
        session.add(new)


def process_jsonl_file(session: Session, file_path: Path, record_type: str) -> int:
    """
    Process a JSONL file and upsert records.
    returns number of processed records.
    """
    logger.info("Processing %s -> %s", record_type, file_path)
    count = 0
    if not file_path.exists():
        logger.warning("File not found: %s", file_path)
        return 0
    with file_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception as e:
                logger.error("Failed to parse JSON line: %s - %s", e, line[:200])
                continue
            try:
                if record_type == "messages":
                    upsert_message(session, obj)
                elif record_type == "contacts":
                    upsert_contact(session, obj)
                elif record_type == "calls":
                    upsert_call(session, obj)
                elif record_type == "files":
                    upsert_file(session, obj)
                else:
                    logger.warning("Unknown record type: %s", record_type)
                    continue
                count += 1
            except Exception as e:
                logger.exception("Error upserting record: %s", e)
    session.commit()
    logger.info("Finished %s: %d records", record_type, count)
    return count


def main():
    parser = argparse.ArgumentParser(description="ETL loader for UFDR parsed JSONL")
    parser.add_argument("--input", required=True, help="Path to parsed/ directory")
    parser.add_argument("--case", required=True, help="Case ID to assign if missing")
    parser.add_argument("--database-url", default=None, help="Optional DATABASE_URL override")
    args = parser.parse_args()

    input_dir = Path(args.input)
    if not input_dir.exists():
        logger.error("Input path does not exist: %s", input_dir)
        raise SystemExit(1)

    # Initialize DB
    init_db(args.database_url)
    engine = get_engine(args.database_url)
    Session = SessionLocal
    session = Session()

    try:
        counts = {}
        counts["messages"] = process_jsonl_file(session, input_dir / "messages.jsonl", "messages")
        counts["contacts"] = process_jsonl_file(session, input_dir / "contacts.jsonl", "contacts")
        counts["calls"] = process_jsonl_file(session, input_dir / "calls.jsonl", "calls")
        counts["files"] = process_jsonl_file(session, input_dir / "blobs_manifest.jsonl", "files")
        logger.info("ETL completed. counts: %s", counts)
    finally:
        session.close()


if __name__ == "__main__":
    main()


def parse_datetime(dt_str: str) -> Optional[datetime]:
    """
    Parse datetime string to datetime object.
    
    Args:
        dt_str: ISO format datetime string
        
    Returns:
        datetime object or None if parsing fails
    """
    if not dt_str:
        return None
    
    try:
        # Handle Z suffix (UTC timezone)
        if dt_str.endswith('Z'):
            dt_str = dt_str[:-1] + '+00:00'
        return datetime.fromisoformat(dt_str)
    except ValueError as e:
        logger.warning(f"Failed to parse datetime '{dt_str}': {e}")
        return None

def load_messages(session: Session, jsonl_path: Path, case_id: str) -> Dict[str, int]:
    """
    Load messages from JSONL file into database.
    
    Args:
        session: Database session
        jsonl_path: Path to messages.jsonl file
        case_id: Case identifier
        
    Returns:
        Dictionary with 'inserted' and 'updated' counts
    """
    if not jsonl_path.exists():
        logger.warning(f"Messages file not found: {jsonl_path}")
        return {"inserted": 0, "updated": 0}
    
    inserted = 0
    updated = 0
    
    logger.info(f"Loading messages from {jsonl_path}")
    
    with jsonl_path.open('r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            try:
                data = json.loads(line.strip())
                
                # Check if message already exists
                existing = session.query(Message).filter_by(id=data['id']).first()
                
                if existing:
                    # Update existing message
                    existing.case_id = data.get('case_id', case_id)
                    existing.timestamp_utc = parse_datetime(data.get('timestamp_utc'))
                    existing.sender = data.get('sender')
                    existing.recipient = data.get('recipient')
                    existing.body = data.get('body')
                    existing.entities = data.get('entities')
                    existing.attachments = data.get('attachments')
                    existing.raw_source = data.get('raw_source')
                    existing.hash = data.get('hash')
                    updated += 1
                else:
                    # Insert new message
                    message = Message(
                        id=data['id'],
                        case_id=data.get('case_id', case_id),
                        timestamp_utc=parse_datetime(data.get('timestamp_utc')),
                        sender=data.get('sender'),
                        recipient=data.get('recipient'),
                        body=data.get('body'),
                        entities=data.get('entities'),
                        attachments=data.get('attachments'),
                        raw_source=data.get('raw_source'),
                        hash=data.get('hash')
                    )
                    session.add(message)
                    inserted += 1
                    
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON at line {line_num}: {e}")
            except Exception as e:
                logger.error(f"Error processing message at line {line_num}: {e}")
    
    logger.info(f"Messages: {inserted} inserted, {updated} updated")
    return {"inserted": inserted, "updated": updated}

def load_contacts(session: Session, jsonl_path: Path, case_id: str) -> Dict[str, int]:
    """
    Load contacts from JSONL file into database.
    
    Args:
        session: Database session
        jsonl_path: Path to contacts.jsonl file
        case_id: Case identifier
        
    Returns:
        Dictionary with 'inserted' and 'updated' counts
    """
    if not jsonl_path.exists():
        logger.warning(f"Contacts file not found: {jsonl_path}")
        return {"inserted": 0, "updated": 0}
    
    inserted = 0
    updated = 0
    
    logger.info(f"Loading contacts from {jsonl_path}")
    
    with jsonl_path.open('r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            try:
                data = json.loads(line.strip())
                
                # Check if contact already exists
                existing = session.query(Contact).filter_by(id=data['id']).first()
                
                if existing:
                    # Update existing contact
                    existing.case_id = data.get('case_id', case_id)
                    existing.name = data.get('name')
                    existing.phones = [data.get('phone')] if data.get('phone') else None
                    existing.raw = data
                    updated += 1
                else:
                    # Insert new contact
                    contact = Contact(
                        id=data['id'],
                        case_id=data.get('case_id', case_id),
                        name=data.get('name'),
                        phones=[data.get('phone')] if data.get('phone') else None,
                        raw=data
                    )
                    session.add(contact)
                    inserted += 1
                    
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON at line {line_num}: {e}")
            except Exception as e:
                logger.error(f"Error processing contact at line {line_num}: {e}")
    
    logger.info(f"Contacts: {inserted} inserted, {updated} updated")
    return {"inserted": inserted, "updated": updated}

def load_calls(session: Session, jsonl_path: Path, case_id: str) -> Dict[str, int]:
    """
    Load calls from JSONL file into database.
    
    Args:
        session: Database session
        jsonl_path: Path to calls.jsonl file
        case_id: Case identifier
        
    Returns:
        Dictionary with 'inserted' and 'updated' counts
    """
    if not jsonl_path.exists():
        logger.warning(f"Calls file not found: {jsonl_path}")
        return {"inserted": 0, "updated": 0}
    
    inserted = 0
    updated = 0
    
    logger.info(f"Loading calls from {jsonl_path}")
    
    with jsonl_path.open('r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            try:
                data = json.loads(line.strip())
                
                # Check if call already exists
                existing = session.query(Call).filter_by(id=data['id']).first()
                
                if existing:
                    # Update existing call
                    existing.case_id = data.get('case_id', case_id)
                    existing.timestamp_utc = parse_datetime(data.get('timestamp_utc'))
                    existing.caller = data.get('caller')
                    existing.callee = data.get('callee')
                    existing.duration = int(data.get('duration', 0)) if data.get('duration') else None
                    existing.raw = data
                    updated += 1
                else:
                    # Insert new call
                    call = Call(
                        id=data['id'],
                        case_id=data.get('case_id', case_id),
                        timestamp_utc=parse_datetime(data.get('timestamp_utc')),
                        caller=data.get('caller'),
                        callee=data.get('callee'),
                        duration=int(data.get('duration', 0)) if data.get('duration') else None,
                        raw=data
                    )
                    session.add(call)
                    inserted += 1
                    
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON at line {line_num}: {e}")
            except Exception as e:
                logger.error(f"Error processing call at line {line_num}: {e}")
    
    logger.info(f"Calls: {inserted} inserted, {updated} updated")
    return {"inserted": inserted, "updated": updated}

def load_files(session: Session, jsonl_path: Path, case_id: str) -> Dict[str, int]:
    """
    Load file metadata from blobs_manifest.jsonl into database.
    
    Args:
        session: Database session
        jsonl_path: Path to blobs_manifest.jsonl file
        case_id: Case identifier
        
    Returns:
        Dictionary with 'inserted' and 'updated' counts
    """
    if not jsonl_path.exists():
        logger.warning(f"Blobs manifest file not found: {jsonl_path}")
        return {"inserted": 0, "updated": 0}
    
    inserted = 0
    updated = 0
    
    logger.info(f"Loading file metadata from {jsonl_path}")
    
    with jsonl_path.open('r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            try:
                data = json.loads(line.strip())
                
                # Check if file already exists
                existing = session.query(File).filter_by(blob_id=data['blob_id']).first()
                
                # Get related message ID if exists
                related_msg_ids = data.get('related_message_ids', [])
                related_msg_id = related_msg_ids[0] if related_msg_ids else None
                
                if existing:
                    # Update existing file
                    existing.case_id = data.get('case_id', case_id)
                    existing.blob_path = data.get('blob_path')
                    existing.sha256 = data.get('sha256')
                    existing.size_bytes = data.get('size_bytes')
                    existing.mtime_utc = parse_datetime(data.get('mtime_utc'))
                    existing.related_message_id = related_msg_id
                    existing.orig_path = data.get('orig_path')
                    updated += 1
                else:
                    # Insert new file
                    file_obj = File(
                        blob_id=data['blob_id'],
                        case_id=data.get('case_id', case_id),
                        blob_path=data.get('blob_path'),
                        sha256=data.get('sha256'),
                        size_bytes=data.get('size_bytes'),
                        mtime_utc=parse_datetime(data.get('mtime_utc')),
                        related_message_id=related_msg_id,
                        orig_path=data.get('orig_path')
                    )
                    session.add(file_obj)
                    inserted += 1
                    
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON at line {line_num}: {e}")
            except Exception as e:
                logger.error(f"Error processing file at line {line_num}: {e}")
    
    logger.info(f"Files: {inserted} inserted, {updated} updated")
    return {"inserted": inserted, "updated": updated}


if __name__ == "__main__":
    main()

def parse_datetime(dt_str: str) -> Optional[datetime]:
    """
    Parse datetime string to datetime object.
    
    Args:
        dt_str: ISO format datetime string
        
    Returns:
        datetime object or None if parsing fails
    """
    if not dt_str:
        return None
    
    try:
        # Handle Z suffix (UTC timezone)
        if dt_str.endswith('Z'):
            dt_str = dt_str[:-1] + '+00:00'
        return datetime.fromisoformat(dt_str)
    except ValueError as e:
        logger.warning(f"Failed to parse datetime '{dt_str}': {e}")
        return None

def load_messages(session: Session, jsonl_path: Path, case_id: str) -> Dict[str, int]:
    """
    Load messages from JSONL file into database.
    
    Args:
        session: Database session
        jsonl_path: Path to messages.jsonl file
        case_id: Case identifier
        
    Returns:
        Dictionary with 'inserted' and 'updated' counts
    """
    if not jsonl_path.exists():
        logger.warning(f"Messages file not found: {jsonl_path}")
        return {"inserted": 0, "updated": 0}
    
    inserted = 0
    updated = 0
    
    logger.info(f"Loading messages from {jsonl_path}")
    
    with jsonl_path.open('r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            try:
                data = json.loads(line.strip())
                
                # Check if message already exists
                existing = session.query(Message).filter_by(id=data['id']).first()
                
                if existing:
                    # Update existing message
                    existing.case_id = data.get('case_id', case_id)
                    existing.timestamp_utc = parse_datetime(data.get('timestamp_utc'))
                    existing.sender = data.get('sender')
                    existing.recipient = data.get('recipient')
                    existing.body = data.get('body')
                    existing.entities = data.get('entities')
                    existing.attachments = data.get('attachments')
                    existing.raw_source = data.get('raw_source')
                    existing.hash = data.get('hash')
                    updated += 1
                else:
                    # Insert new message
                    message = Message(
                        id=data['id'],
                        case_id=data.get('case_id', case_id),
                        timestamp_utc=parse_datetime(data.get('timestamp_utc')),
                        sender=data.get('sender'),
                        recipient=data.get('recipient'),
                        body=data.get('body'),
                        entities=data.get('entities'),
                        attachments=data.get('attachments'),
                        raw_source=data.get('raw_source'),
                        hash=data.get('hash')
                    )
                    session.add(message)
                    inserted += 1
                    
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON at line {line_num}: {e}")
            except Exception as e:
                logger.error(f"Error processing message at line {line_num}: {e}")
    
    logger.info(f"Messages: {inserted} inserted, {updated} updated")
    return {"inserted": inserted, "updated": updated}

def load_contacts(session: Session, jsonl_path: Path, case_id: str) -> Dict[str, int]:
    """
    Load contacts from JSONL file into database.
    
    Args:
        session: Database session
        jsonl_path: Path to contacts.jsonl file
        case_id: Case identifier
        
    Returns:
        Dictionary with 'inserted' and 'updated' counts
    """
    if not jsonl_path.exists():
        logger.warning(f"Contacts file not found: {jsonl_path}")
        return {"inserted": 0, "updated": 0}
    
    inserted = 0
    updated = 0
    
    logger.info(f"Loading contacts from {jsonl_path}")
    
    with jsonl_path.open('r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            try:
                data = json.loads(line.strip())
                
                # Check if contact already exists
                existing = session.query(Contact).filter_by(id=data['id']).first()
                
                if existing:
                    # Update existing contact
                    existing.case_id = data.get('case_id', case_id)
                    existing.name = data.get('name')
                    existing.phones = [data.get('phone')] if data.get('phone') else None
                    existing.raw = data
                    updated += 1
                else:
                    # Insert new contact
                    contact = Contact(
                        id=data['id'],
                        case_id=data.get('case_id', case_id),
                        name=data.get('name'),
                        phones=[data.get('phone')] if data.get('phone') else None,
                        raw=data
                    )
                    session.add(contact)
                    inserted += 1
                    
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON at line {line_num}: {e}")
            except Exception as e:
                logger.error(f"Error processing contact at line {line_num}: {e}")
    
    logger.info(f"Contacts: {inserted} inserted, {updated} updated")
    return {"inserted": inserted, "updated": updated}

def load_calls(session: Session, jsonl_path: Path, case_id: str) -> Dict[str, int]:
    """
    Load calls from JSONL file into database.
    
    Args:
        session: Database session
        jsonl_path: Path to calls.jsonl file
        case_id: Case identifier
        
    Returns:
        Dictionary with 'inserted' and 'updated' counts
    """
    if not jsonl_path.exists():
        logger.warning(f"Calls file not found: {jsonl_path}")
        return {"inserted": 0, "updated": 0}
    
    inserted = 0
    updated = 0
    
    logger.info(f"Loading calls from {jsonl_path}")
    
    with jsonl_path.open('r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            try:
                data = json.loads(line.strip())
                
                # Check if call already exists
                existing = session.query(Call).filter_by(id=data['id']).first()
                
                if existing:
                    # Update existing call
                    existing.case_id = data.get('case_id', case_id)
                    existing.timestamp_utc = parse_datetime(data.get('timestamp_utc'))
                    existing.caller = data.get('caller')
                    existing.callee = data.get('callee')
                    existing.duration = int(data.get('duration', 0)) if data.get('duration') else None
                    existing.raw = data
                    updated += 1
                else:
                    # Insert new call
                    call = Call(
                        id=data['id'],
                        case_id=data.get('case_id', case_id),
                        timestamp_utc=parse_datetime(data.get('timestamp_utc')),
                        caller=data.get('caller'),
                        callee=data.get('callee'),
                        duration=int(data.get('duration', 0)) if data.get('duration') else None,
                        raw=data
                    )
                    session.add(call)
                    inserted += 1
                    
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON at line {line_num}: {e}")
            except Exception as e:
                logger.error(f"Error processing call at line {line_num}: {e}")
    
    logger.info(f"Calls: {inserted} inserted, {updated} updated")
    return {"inserted": inserted, "updated": updated}

def load_files(session: Session, jsonl_path: Path, case_id: str) -> Dict[str, int]:
    """
    Load file metadata from blobs_manifest.jsonl into database.
    
    Args:
        session: Database session
        jsonl_path: Path to blobs_manifest.jsonl file
        case_id: Case identifier
        
    Returns:
        Dictionary with 'inserted' and 'updated' counts
    """
    if not jsonl_path.exists():
        logger.warning(f"Blobs manifest file not found: {jsonl_path}")
        return {"inserted": 0, "updated": 0}
    
    inserted = 0
    updated = 0
    
    logger.info(f"Loading file metadata from {jsonl_path}")
    
    with jsonl_path.open('r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            try:
                data = json.loads(line.strip())
                
                # Check if file already exists
                existing = session.query(File).filter_by(blob_id=data['blob_id']).first()
                
                # Get related message ID if exists
                related_msg_ids = data.get('related_message_ids', [])
                related_msg_id = related_msg_ids[0] if related_msg_ids else None
                
                if existing:
                    # Update existing file
                    existing.case_id = data.get('case_id', case_id)
                    existing.blob_path = data.get('blob_path')
                    existing.sha256 = data.get('sha256')
                    existing.size_bytes = data.get('size_bytes')
                    existing.mtime_utc = parse_datetime(data.get('mtime_utc'))
                    existing.related_message_id = related_msg_id
                    existing.orig_path = data.get('orig_path')
                    updated += 1
                else:
                    # Insert new file
                    file_obj = File(
                        blob_id=data['blob_id'],
                        case_id=data.get('case_id', case_id),
                        blob_path=data.get('blob_path'),
                        sha256=data.get('sha256'),
                        size_bytes=data.get('size_bytes'),
                        mtime_utc=parse_datetime(data.get('mtime_utc')),
                        related_message_id=related_msg_id,
                        orig_path=data.get('orig_path')
                    )
                    session.add(file_obj)
                    inserted += 1
                    
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON at line {line_num}: {e}")
            except Exception as e:
                logger.error(f"Error processing file at line {line_num}: {e}")
    
    logger.info(f"Files: {inserted} inserted, {updated} updated")
    return {"inserted": inserted, "updated": updated}

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Load parsed UFDR JSONL data into PostgreSQL database"
    )
    parser.add_argument(
        "--input", 
        required=True, 
        help="Path to directory containing parsed JSONL files"
    )
    parser.add_argument(
        "--case", 
        required=True, 
        help="Case ID"
    )
    parser.add_argument(
        "--db-url",
        help="Database URL (overrides DATABASE_URL env var)"
    )
    
    args = parser.parse_args()
    
    input_dir = Path(args.input)
    if not input_dir.exists():
        logger.error(f"Input directory does not exist: {input_dir}")
        sys.exit(1)
    
    try:
        # Initialize database
        logger.info("Initializing database connection...")
        init_db(args.db_url)
        
        # Load data
        with get_db_session() as session:
            total_stats = {
                "messages": {"inserted": 0, "updated": 0},
                "contacts": {"inserted": 0, "updated": 0},
                "calls": {"inserted": 0, "updated": 0},
                "files": {"inserted": 0, "updated": 0}
            }
            
            # Load each data type
            total_stats["messages"] = load_messages(session, input_dir / "messages.jsonl", args.case)
            total_stats["contacts"] = load_contacts(session, input_dir / "contacts.jsonl", args.case)
            total_stats["calls"] = load_calls(session, input_dir / "calls.jsonl", args.case)
            total_stats["files"] = load_files(session, input_dir / "blobs_manifest.jsonl", args.case)
            
            # Print summary
            logger.info("ETL Load Summary:")
            for data_type, stats in total_stats.items():
                logger.info(f"  {data_type.capitalize()}: {stats['inserted']} inserted, {stats['updated']} updated")
            
            total_inserted = sum(stats["inserted"] for stats in total_stats.values())
            total_updated = sum(stats["updated"] for stats in total_stats.values())
            logger.info(f"  Total: {total_inserted} inserted, {total_updated} updated")
        
        logger.info("ETL load completed successfully")
        
    except SQLAlchemyError as e:
        logger.error(f"Database error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()