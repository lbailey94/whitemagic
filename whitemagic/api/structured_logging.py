"""
Structured JSON logging for WhiteMagic API

Provides:
- JSON formatted logs
- Correlation ID tracking
- Log levels (DEBUG, INFO, WARNING, ERROR)
- Context-aware logging
"""

import logging
import json
import sys
from datetime import datetime
from typing import Any, Dict, Optional
from contextvars import ContextVar


# Thread-safe correlation ID storage
correlation_id_var: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)


def get_correlation_id() -> Optional[str]:
    """Get current correlation ID from context"""
    return correlation_id_var.get()


def set_correlation_id(correlation_id: str) -> None:
    """Set correlation ID in context"""
    correlation_id_var.set(correlation_id)


class JSONFormatter(logging.Formatter):
    """
    Format logs as JSON for structured logging.
    
    Output format:
    {
        "timestamp": "2025-11-10T17:30:00.123Z",
        "level": "INFO",
        "logger": "whitemagic.api",
        "message": "User created",
        "correlation_id": "abc-123",
        "user_id": "user_456",
        ...extra fields...
    }
    """
    
    def format(self, record: logging.LogRecord) -> str:
        log_obj: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add correlation_id if present
        correlation_id = get_correlation_id()
        if correlation_id:
            log_obj["correlation_id"] = correlation_id
        
        # Add user_id if present in record
        if hasattr(record, 'user_id'):
            log_obj["user_id"] = record.user_id
        
        # Add extra fields from record
        if hasattr(record, 'extra') and isinstance(record.extra, dict):
            log_obj.update(record.extra)
        
        # Add exception info if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        
        # Add location info in debug mode
        if record.levelno >= logging.WARNING:
            log_obj["location"] = {
                "file": record.pathname,
                "line": record.lineno,
                "function": record.funcName
            }
        
        return json.dumps(log_obj)


def setup_logging(level: str = "INFO", json_logs: bool = True):
    """
    Configure structured logging for WhiteMagic.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_logs: If True, use JSON formatting. If False, use standard formatting.
    """
    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    
    # Set formatter
    if json_logs:
        handler.setFormatter(JSONFormatter())
    else:
        # Standard format for development
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.handlers.clear()  # Remove existing handlers
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Silence noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the given name.
    
    Usage:
        logger = get_logger(__name__)
        logger.info("Something happened", extra={"user_id": "123"})
    """
    return logging.getLogger(name)
