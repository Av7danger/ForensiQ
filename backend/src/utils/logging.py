""Logging configuration and utilities."""
import logging
import logging.config
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from ..config.settings import get_settings

settings = get_settings()

class RequestIdFilter(logging.Filter):
    ""Log filter to add request_id to log records."""
    
    def filter(self, record):
        ""Add request_id to log record if it exists in the context."""
        if not hasattr(record, 'request_id'):
            record.request_id = 'system'
        return True

def configure_logging() -> None:
    ""Configure logging for the application."""
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Define log format
    log_format = (
        "%(asctime)s - %(name)s - %(levelname)s - "
        "[%(request_id)s] - %(message)s"
    )
    
    # Configure logging
    logging_config: Dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "request_id": {
                "()": RequestIdFilter,
            },
        },
        "formatters": {
            "default": {
                "format": log_format,
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "json": {
                "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                "format": "%(asctime)s %(name)s %(levelname)s %(request_id)s %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": settings.LOG_LEVEL,
                "formatter": "default",
                "filters": ["request_id"],
                "stream": sys.stdout,
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": settings.LOG_LEVEL,
                "formatter": "default",
                "filters": ["request_id"],
                "filename": "logs/forensiq.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "encoding": "utf8",
            },
        },
        "loggers": {
            "": {  # root logger
                "level": settings.LOG_LEVEL,
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "sqlalchemy.engine": {
                "level": "WARNING",
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "uvicorn": {
                "level": "WARNING",
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "uvicorn.access": {
                "level": "WARNING",
                "handlers": ["console", "file"],
                "propagate": False,
            },
        },
    }
    
    # Apply the configuration
    logging.config.dictConfig(logging_config)
    
    # Set log level for uvicorn loggers
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

def get_logger(name: Optional[str] = None) -> logging.Logger:
    ""Get a logger instance with the given name.
    
    Args:
        name: The name of the logger. If None, returns the root logger.
        
    Returns:
        A configured logger instance.
    """
    logger = logging.getLogger(name)
    return logger
