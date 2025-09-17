# backend/db.py
"""
Database connection helpers for UFDR Investigator.

- Uses DATABASE_URL environment variable if present.
- Falls back to sqlite:///ufdr.db for demo.
- Exposes get_engine, SessionLocal, and init_db to create tables.
"""

import os
import logging
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import Engine

from .models import Base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_database_url() -> str:
    return os.environ.get("DATABASE_URL", "sqlite:///ufdr.db")


def get_engine(database_url: Optional[str] = None) -> Engine:
    if database_url is None:
        database_url = get_database_url()
    logger.info("Using database URL: %s", database_url)
    # echo=False to avoid verbose SQL in demo; set True for debugging
    engine = create_engine(database_url, echo=False, future=True)
    return engine


# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())


def init_db(database_url: Optional[str] = None) -> None:
    """
    Create tables based on models.Base metadata.
    """
    engine = get_engine(database_url)
    logger.info("Creating tables (if not exist)...")
    Base.metadata.create_all(bind=engine)
    logger.info("Tables created/verified.")