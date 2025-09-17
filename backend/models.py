# backend/models.py
"""
SQLAlchemy ORM models for UFDR Investigator (Phase 2).
- Message, Contact, Call, File models.
- Beginner-friendly with type hints and __repr__ helpers.

Usage:
    from backend.db import init_db, SessionLocal
    init_db()
"""

from datetime import datetime
from typing import Any
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Text,
    ForeignKey,
    BigInteger,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.types import JSON

Base = declarative_base()


def JSON_TYPE():
    # Use JSONB on Postgres, fallback to generic JSON on SQLite/dev
    try:
        # If running on PostgreSQL, JSONB type will be used when engine binds
        return JSONB
    except Exception:
        return JSON

class Message(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True, index=True)  # message id from parser
    case_id = Column(String, index=True, nullable=False)
    device_id = Column(String, nullable=True)
    timestamp_utc = Column(DateTime, index=True, nullable=True)
    direction = Column(String, nullable=True)
    sender = Column(String, nullable=True)
    recipient = Column(String, nullable=True)
    body = Column(Text, nullable=True)
    entities = Column(JSON_TYPE(), nullable=True)  # phones, crypto, urls
    attachments = Column(JSON_TYPE(), nullable=True)  # list of blob ids
    raw_source = Column(Text, nullable=True)  # xml path hint
    hash = Column(String, nullable=True)  # SHA256 of message body

    def __repr__(self) -> str:
        ts = self.timestamp_utc.isoformat() if self.timestamp_utc else None
        return f"<Message id={self.id} case={self.case_id} ts={ts} sender={self.sender}>"


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(String, primary_key=True, index=True)
    case_id = Column(String, index=True, nullable=False)
    name = Column(String, nullable=True)
    phones = Column(JSON_TYPE(), nullable=True)  # list
    raw = Column(JSON_TYPE(), nullable=True)

    def __repr__(self) -> str:
        return f"<Contact id={self.id} name={self.name}>"


class Call(Base):
    __tablename__ = "calls"

    id = Column(String, primary_key=True, index=True)
    case_id = Column(String, index=True, nullable=False)
    timestamp_utc = Column(DateTime, nullable=True)
    caller = Column(String, nullable=True)
    callee = Column(String, nullable=True)
    duration = Column(Integer, nullable=True)
    raw = Column(JSON_TYPE(), nullable=True)

    def __repr__(self) -> str:
        return f"<Call id={self.id} caller={self.caller} callee={self.callee}>"


class File(Base):
    __tablename__ = "files"

    blob_id = Column(String, primary_key=True, index=True)  # sha256 hex
    case_id = Column(String, index=True, nullable=False)
    blob_path = Column(String, nullable=False)
    sha256 = Column(String, nullable=False)
    size_bytes = Column(BigInteger, nullable=True)
    mtime_utc = Column(DateTime, nullable=True)
    related_message_id = Column(String, ForeignKey("messages.id"), nullable=True)

    message = relationship("Message", backref="files", foreign_keys=[related_message_id])

    def __repr__(self) -> str:
        return f"<File blob_id={self.blob_id} case={self.case_id} size={self.size_bytes}>"