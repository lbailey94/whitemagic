"""
WhiteMagic API - Authentication

API key generation, validation, and authentication middleware.
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .database import APIKey, User


# API Key Format: wm_<env>_<32-char-base62>
# Example: wm_prod_aB3xY9kL2mN4pQ7rS8tU5vW1xY2zA3bC


def generate_api_key(environment: str = "prod") -> Tuple[str, str, str]:
    """
    Generate a secure API key.

    Args:
        environment: Environment prefix (prod, dev, test)

    Returns:
        Tuple of (full_key, key_hash, key_prefix)
        - full_key: The actual key to give to user (SHOW ONCE!)
        - key_hash: SHA-256 hash to store in database
        - key_prefix: First 16 chars for display purposes

    Example:
        >>> key, hash, prefix = generate_api_key("prod")
        >>> key
        'wm_prod_aB3xY9kL2mN4pQ7rS8tU5vW1xY2zA3bC'
        >>> prefix
        'wm_prod_aB3xY9kL'
    """
    # Generate cryptographically secure random string (alphanumeric only, no underscores)
    # Use secrets.choice to avoid underscores and hyphens from token_urlsafe
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    random_part = ''.join(secrets.choice(alphabet) for _ in range(32))

    # Construct full key
    full_key = f"wm_{environment}_{random_part}"

    # Hash for storage (never store raw keys!)
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()

    # Prefix for display (first 16 chars, no ellipsis to fit DB column)
    # UI can add "..." when displaying
    key_prefix = full_key[:16]

    return full_key, key_hash, key_prefix


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key for storage/comparison.

    Args:
        api_key: Raw API key string

    Returns:
        SHA-256 hex digest of the key
    """
    return hashlib.sha256(api_key.encode()).hexdigest()


async def create_api_key(
    session: AsyncSession,
    user_id: UUID,
    name: Optional[str] = None,
    environment: str = "prod",
    expires_in_days: Optional[int] = None,
) -> Tuple[str, APIKey]:
    """
    Create a new API key for a user.

    Args:
        session: Database session
        user_id: User ID to create key for
        name: Optional name for the key
        environment: Environment (prod/dev/test)
        expires_in_days: Optional expiration in days

    Returns:
        Tuple of (raw_key, api_key_model)
        WARNING: raw_key is only returned here - must be shown to user immediately!

    Example:
        >>> raw_key, api_key = await create_api_key(
        ...     session, user.id, name="Production Key"
        ... )
        >>> print(f"Your API key: {raw_key}")
        >>> # raw_key is now lost forever after this function returns!
    """
    # Generate key
    raw_key, key_hash, key_prefix = generate_api_key(environment)

    # Calculate expiration
    expires_at = None
    if expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

    # Create database record
    api_key = APIKey(
        user_id=user_id,
        key_hash=key_hash,
        key_prefix=key_prefix,
        name=name,
        expires_at=expires_at,
        is_active=True,
    )

    session.add(api_key)
    await session.commit()
    await session.refresh(api_key)

    return raw_key, api_key


async def validate_api_key(
    session: AsyncSession,
    raw_key: str,
    update_last_used: bool = True,
) -> Optional[Tuple[User, APIKey]]:
    """
    Validate an API key and return the associated user.

    Args:
        session: Database session
        raw_key: Raw API key from request
        update_last_used: Whether to update last_used timestamp

    Returns:
        Tuple of (User, APIKey) if valid, None if invalid

    Validation checks:
        1. Key format is correct
        2. Key hash exists in database
        3. Key is_active = True
        4. Key has not expired
        5. Associated user exists
    """
    # Validate format
    if not raw_key.startswith("wm_"):
        return None

    # Split with maxsplit=2 to handle underscores in random part
    # e.g., "wm_prod_aB3x_Y9kL" -> ["wm", "prod", "aB3x_Y9kL"]
    parts = raw_key.split("_", 2)
    if len(parts) != 3:
        return None

    # Hash the key
    key_hash = hash_api_key(raw_key)

    # Query database
    result = await session.execute(
        select(APIKey, User)
        .join(User, APIKey.user_id == User.id)
        .where(APIKey.key_hash == key_hash)
        .where(APIKey.is_active == True)
    )

    row = result.first()
    if not row:
        return None

    api_key, user = row

    # Check expiration
    if api_key.expires_at and api_key.expires_at < datetime.utcnow():
        return None

    # Update last_used timestamp
    if update_last_used:
        api_key.last_used_at = datetime.utcnow()
        user.last_seen_at = datetime.utcnow()
        await session.commit()

    return user, api_key


async def revoke_api_key(session: AsyncSession, api_key_id: UUID) -> bool:
    """
    Revoke (deactivate) an API key.

    Args:
        session: Database session
        api_key_id: ID of key to revoke

    Returns:
        True if key was revoked, False if not found
    """
    result = await session.execute(select(APIKey).where(APIKey.id == api_key_id))
    api_key = result.scalar_one_or_none()

    if not api_key:
        return False

    api_key.is_active = False
    await session.commit()
    return True


async def list_user_api_keys(
    session: AsyncSession,
    user_id: UUID,
    include_inactive: bool = False,
) -> list[APIKey]:
    """
    List all API keys for a user.

    Args:
        session: Database session
        user_id: User ID
        include_inactive: Whether to include revoked keys

    Returns:
        List of APIKey objects (WITHOUT raw keys!)
    """
    query = select(APIKey).where(APIKey.user_id == user_id)

    if not include_inactive:
        query = query.where(APIKey.is_active == True)

    query = query.order_by(APIKey.created_at.desc())

    result = await session.execute(query)
    return list(result.scalars().all())


async def rotate_api_key(
    session: AsyncSession,
    old_key_id: UUID,
    name: Optional[str] = None,
    environment: str = "prod",
) -> Optional[Tuple[str, APIKey]]:
    """
    Rotate an API key (revoke old, create new).

    Args:
        session: Database session
        old_key_id: ID of key to rotate
        name: Optional name for new key
        environment: Environment for new key

    Returns:
        Tuple of (raw_key, new_api_key) if successful, None if old key not found
    """
    # Get old key
    result = await session.execute(select(APIKey).where(APIKey.id == old_key_id))
    old_key = result.scalar_one_or_none()

    if not old_key:
        return None

    # Revoke old key
    old_key.is_active = False

    # Create new key
    raw_key, new_key = await create_api_key(
        session,
        user_id=old_key.user_id,
        name=name or old_key.name,
        environment=environment,
    )

    await session.commit()

    return raw_key, new_key


# Helpers for FastAPI dependency injection


class AuthenticationError(Exception):
    """Raised when authentication fails."""

    pass


class RateLimitError(Exception):
    """Raised when rate limit is exceeded."""

    pass


async def get_current_user_from_api_key(
    session: AsyncSession,
    api_key: str,
) -> User:
    """
    FastAPI dependency to get current user from API key.

    Usage:
        @app.get("/api/v1/memories")
        async def list_memories(
            user: User = Depends(get_current_user)
        ):
            ...

    Args:
        session: Database session (injected)
        api_key: API key from Authorization header (injected)

    Returns:
        User object if authenticated

    Raises:
        AuthenticationError: If authentication fails
    """
    result = await validate_api_key(session, api_key)

    if not result:
        raise AuthenticationError("Invalid or expired API key")

    user, _ = result
    return user
