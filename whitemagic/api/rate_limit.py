"""
WhiteMagic API - Rate Limiting

Redis-backed rate limiting using token bucket algorithm.
Enforces per-user quotas based on plan tier.
"""

import time
from typing import Optional
from datetime import datetime, date

from fastapi import HTTPException, Request
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

try:
    import redis.asyncio as redis
except ImportError:
    redis = None

from .database import User, Quota


# Plan tier limits
PLAN_LIMITS = {
    "free": {
        "rpm": 10,  # Requests per minute
        "daily": 100,  # Requests per day
        "monthly": 1000,  # Requests per month
        "memories": 50,  # Max memories
        "storage_mb": 10,  # Max storage in MB
    },
    "starter": {
        "rpm": 60,
        "daily": 5000,
        "monthly": 100000,
        "memories": 500,
        "storage_mb": 100,
    },
    "pro": {
        "rpm": 300,
        "daily": 50000,
        "monthly": 1000000,
        "memories": 5000,
        "storage_mb": 1000,
    },
    "enterprise": {
        "rpm": 1000,
        "daily": 1000000,
        "monthly": 10000000,
        "memories": 50000,
        "storage_mb": 10000,
    },
}


class RateLimitExceeded(HTTPException):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        limit_type: str,
        limit: int,
        reset_at: Optional[int] = None,
    ):
        detail = f"Rate limit exceeded: {limit} {limit_type}"

        headers = {
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": "0",
        }

        if reset_at:
            headers["X-RateLimit-Reset"] = str(reset_at)
            detail += f". Resets at {datetime.fromtimestamp(reset_at).isoformat()}"

        super().__init__(
            status_code=429,
            detail=detail,
            headers=headers,
        )


class RateLimiter:
    """Redis-backed rate limiter with token bucket algorithm."""

    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize rate limiter.

        Args:
            redis_url: Redis connection URL. If None, rate limiting is disabled.
        """
        self.redis_client: Optional[redis.Redis] = None
        self.enabled = False

        if redis_url and redis:
            try:
                self.redis_client = redis.from_url(
                    redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                )
                self.enabled = True
            except Exception as e:
                print(f"Warning: Failed to connect to Redis: {e}")
                print("Rate limiting will be disabled.")

    async def close(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()

    async def check_rate_limit(
        self,
        user: User,
        request: Request,
    ) -> dict:
        """
        Check if request is within rate limits.

        Uses token bucket algorithm for smooth rate limiting.

        Args:
            user: Authenticated user
            request: FastAPI request object

        Returns:
            Dict with rate limit info

        Raises:
            RateLimitExceeded: If any rate limit is exceeded
        """
        limits = PLAN_LIMITS.get(user.plan_tier, PLAN_LIMITS["free"])
        user_id = str(user.id)

        # Add rate limit headers to response
        rate_limit_info = {
            "limit": limits["rpm"],
            "remaining": limits["rpm"],
            "reset": int(time.time()) + 60,
        }

        if not self.enabled:
            # Rate limiting disabled (development mode)
            return rate_limit_info

        # Check per-minute rate (token bucket)
        rpm_key = f"ratelimit:rpm:{user_id}"
        rpm_count = await self._increment_counter(rpm_key, ttl=60)

        if rpm_count > limits["rpm"]:
            reset_at = int(time.time()) + 60
            raise RateLimitExceeded("requests/minute", limits["rpm"], reset_at)

        rate_limit_info["remaining"] = limits["rpm"] - rpm_count

        # Check daily quota
        today = date.today().isoformat()
        daily_key = f"ratelimit:daily:{user_id}:{today}"
        daily_count = await self._increment_counter(daily_key, ttl=86400)

        if daily_count > limits["daily"]:
            # Reset at midnight
            tomorrow = int(time.mktime((date.today()).timetuple())) + 86400
            raise RateLimitExceeded("requests/day", limits["daily"], tomorrow)

        return rate_limit_info

    async def _increment_counter(self, key: str, ttl: int) -> int:
        """
        Increment a counter with automatic expiration.

        Args:
            key: Redis key
            ttl: Time to live in seconds

        Returns:
            New counter value
        """
        if not self.redis_client:
            return 0

        # Increment counter
        count = await self.redis_client.incr(key)

        # Set expiration on first increment
        if count == 1:
            await self.redis_client.expire(key, ttl)

        return count

    async def get_user_stats(self, user: User) -> dict:
        """
        Get current usage stats for a user.

        Args:
            user: User to get stats for

        Returns:
            Dict with current usage
        """
        if not self.enabled:
            return {
                "rpm_used": 0,
                "daily_used": 0,
                "rpm_limit": PLAN_LIMITS[user.plan_tier]["rpm"],
                "daily_limit": PLAN_LIMITS[user.plan_tier]["daily"],
            }

        user_id = str(user.id)
        today = date.today().isoformat()

        # Get counters
        rpm_key = f"ratelimit:rpm:{user_id}"
        daily_key = f"ratelimit:daily:{user_id}:{today}"

        rpm_used = await self.redis_client.get(rpm_key) or 0
        daily_used = await self.redis_client.get(daily_key) or 0

        limits = PLAN_LIMITS[user.plan_tier]

        return {
            "rpm_used": int(rpm_used),
            "daily_used": int(daily_used),
            "rpm_limit": limits["rpm"],
            "daily_limit": limits["daily"],
            "rpm_remaining": limits["rpm"] - int(rpm_used),
            "daily_remaining": limits["daily"] - int(daily_used),
        }


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


def set_rate_limiter(limiter: RateLimiter):
    """Set the global rate limiter instance."""
    global _rate_limiter
    _rate_limiter = limiter


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance."""
    if _rate_limiter is None:
        raise RuntimeError("Rate limiter not initialized")
    return _rate_limiter


async def update_quota_in_db(
    session: AsyncSession,
    user: User,
):
    """
    Update quota counters in database.

    Called after successful request to track usage.

    Args:
        session: Database session
        user: Authenticated user
    """
    # Get or create quota
    result = await session.execute(select(Quota).where(Quota.user_id == user.id))
    quota = result.scalar_one_or_none()

    if not quota:
        quota = Quota(user_id=user.id)
        session.add(quota)

    # Reset daily counter if needed
    today = date.today()
    if quota.last_reset_daily < today:
        quota.requests_today = 0
        quota.last_reset_daily = today

    # Reset monthly counter if needed
    first_of_month = today.replace(day=1)
    if quota.last_reset_monthly < first_of_month:
        quota.requests_this_month = 0
        quota.last_reset_monthly = first_of_month

    # Increment counters
    quota.requests_today += 1
    quota.requests_this_month += 1

    await session.commit()


async def check_quota_limits(
    session: AsyncSession,
    user: User,
) -> None:
    """
    Check if user is within quota limits.

    Checks database quotas (memories count, storage).

    Args:
        session: Database session
        user: Authenticated user

    Raises:
        RateLimitExceeded: If quota is exceeded
    """
    limits = PLAN_LIMITS.get(user.plan_tier, PLAN_LIMITS["free"])

    # Get quota
    result = await session.execute(select(Quota).where(Quota.user_id == user.id))
    quota = result.scalar_one_or_none()

    if not quota:
        return  # No quota record yet, allow request

    # Check memory count limit
    if quota.memories_count >= limits["memories"]:
        raise RateLimitExceeded(
            f'memories (max {limits["memories"]})',
            limits["memories"],
        )

    # Check storage limit
    storage_limit_bytes = limits["storage_mb"] * 1024 * 1024
    if quota.storage_bytes >= storage_limit_bytes:
        raise RateLimitExceeded(
            f'storage (max {limits["storage_mb"]}MB)',
            limits["storage_mb"],
        )
