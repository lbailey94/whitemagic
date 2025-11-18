"""
WhiteMagic API - FastAPI Dependencies

Dependency injection for authentication, database sessions, etc.
"""

from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from .auth import AuthenticationError, validate_api_key
from .database import Database, User

# Global database instance (will be initialized in main app)
_database: Database = None


def set_database(database: Database):
    """Set the global database instance."""
    global _database
    _database = database


def get_database() -> Database:
    """Get the global database instance."""
    if _database is None:
        raise RuntimeError("Database not initialized. Call set_database() first.")
    return _database


async def get_db_session() -> AsyncSession:
    """
    FastAPI dependency to get a database session.

    Usage:
        @app.get("/endpoint")
        async def my_endpoint(session: AsyncSession = Depends(get_db_session)):
            ...
    """
    if _database is None:
        raise RuntimeError("Database not initialized. Call set_database() first.")

    async with _database.get_session() as session:
        try:
            yield session
        finally:
            await session.close()


# HTTP Bearer security scheme (for Swagger UI)
security = HTTPBearer(
    scheme_name="API Key",
    description="Enter your API key in format: wm_prod_xxxxx...",
    auto_error=False,  # We'll handle errors manually
)


async def get_api_key_from_header(
    authorization: Annotated[str | None, Header()] = None,
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> str:
    """
    Extract API key from headers.

    Supports three formats (in order of preference):
    1. Authorization: Bearer wm_prod_xxxxx...
    2. Authorization: wm_prod_xxxxx...
    3. X-API-Key: wm_prod_xxxxx... (legacy SDK support)

    Args:
        authorization: Raw Authorization header
        x_api_key: X-API-Key header (deprecated, for SDK compatibility)
        credentials: Parsed Bearer token from HTTPBearer

    Returns:
        API key string

    Raises:
        HTTPException: If no API key provided
    """
    # Try Bearer token first (from HTTPBearer)
    if credentials:
        return credentials.credentials

    # Try raw Authorization header
    if authorization:
        # Remove "Bearer " prefix if present
        if authorization.startswith("Bearer "):
            return authorization[7:]
        return authorization

    # Try X-API-Key header (legacy SDK support)
    if x_api_key:
        import warnings

        warnings.warn(
            "X-API-Key header is deprecated. Please use Authorization: Bearer <key>",
            DeprecationWarning,
            stacklevel=2,
        )
        return x_api_key

    # No API key provided
    raise HTTPException(
        status_code=401,
        detail="API key required. Include in Authorization header: 'Bearer wm_prod_xxxxx...' or X-API-Key header",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    request: Request,
    api_key: Annotated[str, Depends(get_api_key_from_header)],
    session: AsyncSession = Depends(get_db_session),
) -> User:
    """
    FastAPI dependency to get the current authenticated user.

    Sets request.state.user for middleware access (rate limiting, logging).

    Usage:
        @app.get("/api/v1/memories")
        async def list_memories(
            user: User = Depends(get_current_user)
        ):
            # user is automatically authenticated
            ...

    Args:
        request: FastAPI request object (auto-injected)
        api_key: API key from Authorization header (auto-injected)
        session: Database session (auto-injected)

    Returns:
        Authenticated User object

    Raises:
        HTTPException: If authentication fails
    """
    try:
        result = await validate_api_key(session, api_key, update_last_used=True)

        if not result:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired API key",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user, _ = result

        # Set user on request state for middleware access
        request.state.user = user

        return user

    except AuthenticationError as e:
        raise HTTPException(
            status_code=401,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        # Log the error (will add proper logging later)
        print(f"Authentication error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Authentication service error",
        )


# Type alias for dependency injection
CurrentUser = Annotated[User, Depends(get_current_user)]
DBSession = Annotated[AsyncSession, Depends(get_db_session)]
