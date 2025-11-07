"""
WhiteMagic REST API

FastAPI-based REST API for WhiteMagic memory management.
Provides authenticated access to memory operations, search, and context generation.
"""

__version__ = "2.1.0"

from .app import app
from .database import Database, User, APIKey, Quota
from .auth import create_api_key, validate_api_key
from .rate_limit import RateLimiter, PLAN_LIMITS

__all__ = [
    "__version__",
    "app",
    "Database",
    "User",
    "APIKey",
    "Quota",
    "create_api_key",
    "validate_api_key",
    "RateLimiter",
    "PLAN_LIMITS",
]
