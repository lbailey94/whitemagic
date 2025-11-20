"""
WhiteMagic REST API

FastAPI-based REST API for WhiteMagic memory management.
Provides authenticated access to memory operations, search, and context generation.
"""

__version__ = "2.6.5"

from .app import app
from .auth import create_api_key, validate_api_key
from .database import APIKey, Database, Quota, User
from .rate_limit import PLAN_LIMITS, RateLimiter

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
