""Logging configuration for the application."""
import json
import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel

from ..config.settings import get_settings


class LogRecordFactory:
    """Custom log record factory that adds request_id to log records."""
    
    def __init__(self, original_factory):
        self.original_factory = original_factory
    
    def __call__(self, *args, **kwargs):
        record = self.original_factory(*args, **kwargs)
        if not hasattr(record, 'request_id'):
            record.request_id = 'system'
        return record


class JsonFormatter(logging.Formatter):
    ""
    Custom JSON formatter for structured logging.
    
    Converts log records to JSON format with additional context.
    """
    
    def format(self, record):
        log_record = {
            'timestamp': self.formatTime(record, self.datefmt),
            'level': record.levelname,
            'name': record.name,
            'message': record.getMessage(),
            'request_id': getattr(record, 'request_id', 'system'),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'process': record.process,
            'thread': record.thread,
            'thread_name': record.threadName,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_record['exception'] = self.formatException(record.exc_info)
        
        # Add any extra attributes
        if hasattr(record, 'props') and isinstance(record.props, dict):
            log_record.update(record.props)
        
        return json.dumps(log_record, ensure_ascii=False)


def configure_logging() -> None:
    """
    Configure logging for the application.
    
    Sets up console and file handlers with appropriate formatters.
    Configures log levels and propagation settings.
    """
    settings = get_settings()
    
    # Create logs directory if it doesn't exist
    log_dir = os.path.dirname(settings.LOG_FILE)
    if log_dir:
        Path(log_dir).mkdir(parents=True, exist_ok=True)
    
    # Set up the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.LOG_LEVEL)
    
    # Clear any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Set up console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(settings.LOG_LEVEL)
    
    # Set up file handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        settings.LOG_FILE,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(settings.LOG_LEVEL)
    
    # Create formatters
    if settings.ENVIRONMENT == 'production':
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(settings.LOG_FORMAT)
    
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    
    # Add handlers to root logger
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Set log levels for specific loggers
    logging.getLogger('uvicorn').setLevel(logging.WARNING)
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.orm').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    
    # Set up custom log record factory
    logging.setLogRecordFactory(LogRecordFactory(logging.getLogRecordFactory()))
    
    # Disable propagation for uvicorn loggers
    for logger_name in ('uvicorn', 'uvicorn.error', 'uvicorn.access'):
        logging.getLogger(logger_name).propagate = False


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.
    
    Args:
        name: Name of the logger
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)
