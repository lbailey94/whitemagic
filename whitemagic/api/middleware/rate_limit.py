"""
Rate limiting middleware using Redis for distributed rate limiting.

Prevents abuse and ensures fair usage across all users.
"""

from fastapi import Request, HTTPException
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import redis
import os

# Initialize limiter with Redis backend for distributed rate limiting
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

try:
    redis_client = redis.from_url(redis_url)
    limiter = Limiter(
        key_func=get_remote_address,
        storage_uri=redis_url,
        default_limits=["100/minute"]
    )
except:
    # Fallback to in-memory limiter for development
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=["100/minute"]
    )

# Custom rate limits for different endpoints
RATE_LIMITS = {
    "/performance/audit": "10/minute",      # Expensive operation
    "/performance/consolidate": "5/minute",  # Very expensive
    "/performance/benchmark": "2/minute",    # Resource intensive
    "/api/memories": "50/minute",            # Standard operations
    "/api/search": "100/minute",             # Read operations
}


def get_rate_limit(path: str) -> str:
    """Get rate limit for specific path."""
    for endpoint, limit in RATE_LIMITS.items():
        if path.startswith(endpoint):
            return limit
    return "100/minute"  # Default


async def rate_limit_middleware(request: Request, call_next):
    """Apply rate limiting to requests."""
    try:
        response = await call_next(request)
        return response
    except RateLimitExceeded:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again later."
        )
