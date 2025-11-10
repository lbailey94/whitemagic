"""
WhiteMagic API - Middleware

Request/response middleware for logging, timing, and request tracking.
"""

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from .database import UsageRecord, User
from .dependencies import get_db_session
from .version import get_version
from .structured_logging import get_logger, set_correlation_id

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log requests and track usage.

    Adds:
    - Request ID to all requests
    - Response time tracking
    - Usage record creation
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate or extract correlation ID
        correlation_id = request.headers.get("x-correlation-id") or str(uuid.uuid4())
        request.state.request_id = correlation_id
        set_correlation_id(correlation_id)

        # Start timer
        start_time = time.time()

        user = getattr(request.state, "user", None)

        # Log incoming request
        logger.info(
            "request_started",
            extra={
                "method": request.method,
                "path": request.url.path,
                "user_id": str(user.id) if user else None,
            }
        )

        # Ensure quotas are enforced before processing request
        if user:
            await self._enforce_quota_limits(user)

        try:
            response = await call_next(request)
        except Exception as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            logger.error(
                "request_failed",
                exc_info=True,
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "response_time_ms": response_time_ms,
                    "user_id": str(user.id) if user else None,
                }
            )
            raise

        # Calculate response time
        response_time_ms = int((time.time() - start_time) * 1000)

        # Log successful request
        logger.info(
            "request_completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "response_time_ms": response_time_ms,
                "user_id": str(user.id) if user else None,
            }
        )

        # Add headers
        response.headers["X-Request-ID"] = correlation_id
        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-Response-Time"] = f"{response_time_ms}ms"
        response.headers["X-WhiteMagic-Revision"] = get_version()

        if user:
            try:
                await self._log_usage(
                    user=user,
                    endpoint=request.url.path,
                    method=request.method,
                    status_code=response.status_code,
                    response_time_ms=response_time_ms,
                )

                if 200 <= response.status_code < 300:
                    await self._update_request_counters(user)
            except Exception as e:
                logger.error(
                    "usage_logging_failed",
                    exc_info=True,
                    extra={"user_id": str(user.id)}
                )

        return response

    async def _log_usage(
        self,
        user: User,
        endpoint: str,
        method: str,
        status_code: int,
        response_time_ms: int,
    ):
        """Create a usage record in the database."""
        from .dependencies import get_database
        from .database import UsageRecord

        try:
            db = get_database()
            async with db.get_session() as session:
                usage = UsageRecord(
                    user_id=user.id,
                    endpoint=endpoint,
                    method=method,
                    status_code=status_code,
                    response_time_ms=response_time_ms,
                )
                session.add(usage)
                await session.commit()
        except Exception as e:
            # Don't fail request if logging fails
            logger.warning(
                "usage_record_creation_failed",
                exc_info=True,
                extra={"user_id": str(user.id)}
            )

    async def _enforce_quota_limits(self, user: User) -> None:
        """Ensure the user is within quota limits before fulfilling the request."""
        from .dependencies import get_database
        from .rate_limit import check_quota_limits

        db = get_database()
        async with db.get_session() as session:
            await check_quota_limits(session, user)

    async def _update_request_counters(self, user: User) -> None:
        """Increment per-user request counters after a successful response."""
        from .dependencies import get_database
        from .rate_limit import update_quota_in_db

        db = get_database()
        async with db.get_session() as session:
            await update_quota_in_db(session, user)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce rate limits.

    Must be applied after authentication middleware.
    Gets rate_limiter from dependencies on each request.
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health check and docs
        if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)

        # Check if user is authenticated
        if hasattr(request.state, "user"):
            user = request.state.user

            try:
                # Get rate limiter from global
                from .rate_limit import get_rate_limiter

                rate_limiter = get_rate_limiter()

                # Check rate limit
                rate_limit_info = await rate_limiter.check_rate_limit(
                    user=user,
                    request=request,
                )

                # Process request
                response = await call_next(request)

                # Add rate limit headers
                response.headers["X-RateLimit-Limit"] = str(rate_limit_info["limit"])
                response.headers["X-RateLimit-Remaining"] = str(rate_limit_info["remaining"])
                response.headers["X-RateLimit-Reset"] = str(rate_limit_info["reset"])

                return response

            except Exception as e:
                # Re-raise rate limit exceptions
                raise
        else:
            # No user authenticated, skip rate limiting
            # (will fail later in auth dependency)
            return await call_next(request)


class CORSHeadersMiddleware(BaseHTTPMiddleware):
    """
    Custom CORS middleware for additional headers.

    Adds security headers to all responses.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # API version header
        response.headers["X-API-Version"] = "2.1.0"

        return response
