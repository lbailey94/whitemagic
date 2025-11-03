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


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log requests and track usage.
    
    Adds:
    - Request ID to all requests
    - Response time tracking
    - Usage record creation
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Start timer
        start_time = time.time()
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate response time
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # Add headers
            response.headers['X-Request-ID'] = request_id
            response.headers['X-Response-Time'] = f"{response_time_ms}ms"
            
            # Log usage and update quota (async, don't wait)
            if hasattr(request.state, 'user'):
                # User was authenticated, log usage and update quotas
                try:
                    await self._log_usage(
                        user=request.state.user,
                        endpoint=request.url.path,
                        method=request.method,
                        status_code=response.status_code,
                        response_time_ms=response_time_ms,
                    )
                    
                    # Update quota if request was successful
                    if 200 <= response.status_code < 300:
                        from .rate_limit import update_quota_in_db
                        from .dependencies import get_database
                        
                        db = get_database()
                        async with db.get_session() as session:
                            await update_quota_in_db(session, request.state.user.id)
                except Exception as e:
                    # Don't fail request if logging fails
                    print(f"Failed to log usage/update quota: {e}")
            
            return response
            
        except Exception as e:
            # Log error and re-raise
            response_time_ms = int((time.time() - start_time) * 1000)
            print(f"Request {request_id} failed after {response_time_ms}ms: {e}")
            raise
    
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
            print(f"Failed to create usage record: {e}")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce rate limits.
    
    Must be applied after authentication middleware.
    """
    
    def __init__(self, app: ASGIApp, rate_limiter):
        super().__init__(app)
        self.rate_limiter = rate_limiter
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health check and docs
        if request.url.path in ['/health', '/docs', '/redoc', '/openapi.json']:
            return await call_next(request)
        
        # Check if user is authenticated
        if hasattr(request.state, 'user'):
            user = request.state.user
            
            try:
                # Check rate limit
                rate_limit_info = await self.rate_limiter.check_rate_limit(
                    user=user,
                    request=request,
                )
                
                # Process request
                response = await call_next(request)
                
                # Add rate limit headers
                response.headers['X-RateLimit-Limit'] = str(rate_limit_info['limit'])
                response.headers['X-RateLimit-Remaining'] = str(rate_limit_info['remaining'])
                response.headers['X-RateLimit-Reset'] = str(rate_limit_info['reset'])
                
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
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # API version header
        response.headers['X-API-Version'] = '0.2.0'
        
        return response
