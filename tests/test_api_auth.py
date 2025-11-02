"""
Tests for WhiteMagic API authentication.

Tests API key generation, validation, and management.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from whitemagic.api.database import Base, User, APIKey
from whitemagic.api.auth import (
    generate_api_key,
    hash_api_key,
    create_api_key,
    validate_api_key,
    revoke_api_key,
    list_user_api_keys,
    rotate_api_key,
    AuthenticationError,
)


@pytest.fixture
async def db_engine():
    """Create in-memory SQLite database for testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine):
    """Create a database session for testing."""
    async_session = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def sample_user(db_session):
    """Create a sample user for testing."""
    user = User(
        email="test@example.com",
        plan_tier="pro",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


class TestAPIKeyGeneration:
    """Tests for API key generation."""
    
    def test_generate_api_key_format(self):
        """Test that generated key has correct format."""
        key, key_hash, prefix = generate_api_key("prod")
        
        # Check format: wm_<env>_<random>
        assert key.startswith("wm_prod_")
        parts = key.split("_")
        assert len(parts) == 3
        assert parts[0] == "wm"
        assert parts[1] == "prod"
        assert len(parts[2]) == 32  # 32 random characters
    
    def test_generate_api_key_hash(self):
        """Test that key hash is SHA-256."""
        key, key_hash, prefix = generate_api_key()
        
        # SHA-256 produces 64 hex characters
        assert len(key_hash) == 64
        assert all(c in "0123456789abcdef" for c in key_hash)
    
    def test_generate_api_key_prefix(self):
        """Test that prefix is correctly extracted."""
        key, key_hash, prefix = generate_api_key("dev")
        
        assert prefix.startswith("wm_dev_")
        assert prefix.endswith("...")
        assert len(prefix) == 19  # "wm_dev_" + 8 chars + "..."
    
    def test_generate_api_key_uniqueness(self):
        """Test that multiple calls generate different keys."""
        key1, _, _ = generate_api_key()
        key2, _, _ = generate_api_key()
        key3, _, _ = generate_api_key()
        
        assert key1 != key2
        assert key2 != key3
        assert key1 != key3
    
    def test_generate_api_key_environments(self):
        """Test different environment prefixes."""
        prod_key, _, _ = generate_api_key("prod")
        dev_key, _, _ = generate_api_key("dev")
        test_key, _, _ = generate_api_key("test")
        
        assert "prod" in prod_key
        assert "dev" in dev_key
        assert "test" in test_key


class TestAPIKeyHashing:
    """Tests for API key hashing."""
    
    def test_hash_api_key_deterministic(self):
        """Test that same key produces same hash."""
        key = "wm_prod_test123"
        hash1 = hash_api_key(key)
        hash2 = hash_api_key(key)
        
        assert hash1 == hash2
    
    def test_hash_api_key_different_keys(self):
        """Test that different keys produce different hashes."""
        hash1 = hash_api_key("wm_prod_key1")
        hash2 = hash_api_key("wm_prod_key2")
        
        assert hash1 != hash2
    
    def test_hash_api_key_length(self):
        """Test that hash is SHA-256 (64 hex chars)."""
        key_hash = hash_api_key("wm_prod_any_key")
        
        assert len(key_hash) == 64
        assert all(c in "0123456789abcdef" for c in key_hash)


class TestCreateAPIKey:
    """Tests for creating API keys."""
    
    @pytest.mark.asyncio
    async def test_create_api_key_basic(self, db_session, sample_user):
        """Test creating a basic API key."""
        raw_key, api_key = await create_api_key(
            db_session,
            sample_user.id,
            name="Test Key",
        )
        
        # Check raw key format
        assert raw_key.startswith("wm_prod_")
        
        # Check database record
        assert api_key.id is not None
        assert api_key.user_id == sample_user.id
        assert api_key.name == "Test Key"
        assert api_key.is_active is True
        assert api_key.key_prefix.startswith("wm_prod_")
        
        # Verify hash matches
        assert api_key.key_hash == hash_api_key(raw_key)
    
    @pytest.mark.asyncio
    async def test_create_api_key_with_expiration(self, db_session, sample_user):
        """Test creating an API key with expiration."""
        raw_key, api_key = await create_api_key(
            db_session,
            sample_user.id,
            expires_in_days=30,
        )
        
        assert api_key.expires_at is not None
        
        # Should expire in approximately 30 days
        expected_expiry = datetime.utcnow() + timedelta(days=30)
        diff = abs((api_key.expires_at - expected_expiry).total_seconds())
        assert diff < 5  # Within 5 seconds
    
    @pytest.mark.asyncio
    async def test_create_api_key_different_environments(self, db_session, sample_user):
        """Test creating keys for different environments."""
        prod_key, prod_api_key = await create_api_key(
            db_session,
            sample_user.id,
            environment="prod",
        )
        
        dev_key, dev_api_key = await create_api_key(
            db_session,
            sample_user.id,
            environment="dev",
        )
        
        assert "prod" in prod_key
        assert "dev" in dev_key
        assert prod_api_key.key_hash != dev_api_key.key_hash


class TestValidateAPIKey:
    """Tests for validating API keys."""
    
    @pytest.mark.asyncio
    async def test_validate_valid_key(self, db_session, sample_user):
        """Test validating a valid API key."""
        raw_key, _ = await create_api_key(db_session, sample_user.id)
        
        result = await validate_api_key(db_session, raw_key)
        
        assert result is not None
        user, api_key = result
        assert user.id == sample_user.id
        assert api_key.key_hash == hash_api_key(raw_key)
    
    @pytest.mark.asyncio
    async def test_validate_invalid_key(self, db_session):
        """Test validating an invalid API key."""
        result = await validate_api_key(db_session, "wm_prod_invalid_key_12345678901234")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_validate_malformed_key(self, db_session):
        """Test validating keys with wrong format."""
        # Missing prefix
        assert await validate_api_key(db_session, "prod_abc123") is None
        
        # Wrong prefix
        assert await validate_api_key(db_session, "api_prod_abc123") is None
        
        # Too few parts
        assert await validate_api_key(db_session, "wm_abc123") is None
    
    @pytest.mark.asyncio
    async def test_validate_inactive_key(self, db_session, sample_user):
        """Test that inactive keys are rejected."""
        raw_key, api_key = await create_api_key(db_session, sample_user.id)
        
        # Deactivate key
        api_key.is_active = False
        await db_session.commit()
        
        result = await validate_api_key(db_session, raw_key)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_validate_expired_key(self, db_session, sample_user):
        """Test that expired keys are rejected."""
        raw_key, api_key = await create_api_key(
            db_session,
            sample_user.id,
            expires_in_days=1,
        )
        
        # Manually expire the key
        api_key.expires_at = datetime.utcnow() - timedelta(days=1)
        await db_session.commit()
        
        result = await validate_api_key(db_session, raw_key)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_validate_updates_last_used(self, db_session, sample_user):
        """Test that validation updates last_used timestamp."""
        raw_key, api_key = await create_api_key(db_session, sample_user.id)
        
        original_last_used = api_key.last_used_at
        assert original_last_used is None
        
        # Wait a moment
        await validate_api_key(db_session, raw_key, update_last_used=True)
        
        # Refresh from database
        await db_session.refresh(api_key)
        
        assert api_key.last_used_at is not None
        assert api_key.last_used_at != original_last_used


class TestRevokeAPIKey:
    """Tests for revoking API keys."""
    
    @pytest.mark.asyncio
    async def test_revoke_existing_key(self, db_session, sample_user):
        """Test revoking an existing API key."""
        raw_key, api_key = await create_api_key(db_session, sample_user.id)
        
        result = await revoke_api_key(db_session, api_key.id)
        
        assert result is True
        
        # Refresh and verify
        await db_session.refresh(api_key)
        assert api_key.is_active is False
        
        # Key should no longer validate
        validation = await validate_api_key(db_session, raw_key)
        assert validation is None
    
    @pytest.mark.asyncio
    async def test_revoke_nonexistent_key(self, db_session):
        """Test revoking a non-existent key."""
        fake_id = uuid4()
        result = await revoke_api_key(db_session, fake_id)
        
        assert result is False


class TestListUserAPIKeys:
    """Tests for listing user API keys."""
    
    @pytest.mark.asyncio
    async def test_list_active_keys(self, db_session, sample_user):
        """Test listing active API keys."""
        # Create multiple keys
        await create_api_key(db_session, sample_user.id, name="Key 1")
        await create_api_key(db_session, sample_user.id, name="Key 2")
        await create_api_key(db_session, sample_user.id, name="Key 3")
        
        keys = await list_user_api_keys(db_session, sample_user.id)
        
        assert len(keys) == 3
        assert all(key.is_active for key in keys)
    
    @pytest.mark.asyncio
    async def test_list_excludes_inactive(self, db_session, sample_user):
        """Test that inactive keys are excluded by default."""
        _, key1 = await create_api_key(db_session, sample_user.id, name="Active")
        _, key2 = await create_api_key(db_session, sample_user.id, name="Inactive")
        
        # Revoke key2
        await revoke_api_key(db_session, key2.id)
        
        keys = await list_user_api_keys(db_session, sample_user.id)
        
        assert len(keys) == 1
        assert keys[0].name == "Active"
    
    @pytest.mark.asyncio
    async def test_list_includes_inactive_when_requested(self, db_session, sample_user):
        """Test that inactive keys can be included."""
        await create_api_key(db_session, sample_user.id, name="Active")
        _, inactive_key = await create_api_key(db_session, sample_user.id, name="Inactive")
        await revoke_api_key(db_session, inactive_key.id)
        
        keys = await list_user_api_keys(db_session, sample_user.id, include_inactive=True)
        
        assert len(keys) == 2
        assert any(not key.is_active for key in keys)


class TestRotateAPIKey:
    """Tests for rotating API keys."""
    
    @pytest.mark.asyncio
    async def test_rotate_key_success(self, db_session, sample_user):
        """Test successfully rotating an API key."""
        old_raw_key, old_api_key = await create_api_key(
            db_session,
            sample_user.id,
            name="Old Key",
        )
        
        result = await rotate_api_key(db_session, old_api_key.id, name="New Key")
        
        assert result is not None
        new_raw_key, new_api_key = result
        
        # Old key should be inactive
        await db_session.refresh(old_api_key)
        assert old_api_key.is_active is False
        
        # New key should be active
        assert new_api_key.is_active is True
        assert new_api_key.name == "New Key"
        
        # Keys should be different
        assert old_raw_key != new_raw_key
        assert old_api_key.key_hash != new_api_key.key_hash
    
    @pytest.mark.asyncio
    async def test_rotate_preserves_name(self, db_session, sample_user):
        """Test that rotation preserves name if not specified."""
        _, old_api_key = await create_api_key(
            db_session,
            sample_user.id,
            name="Production Key",
        )
        
        new_raw_key, new_api_key = await rotate_api_key(db_session, old_api_key.id)
        
        assert new_api_key.name == "Production Key"
    
    @pytest.mark.asyncio
    async def test_rotate_nonexistent_key(self, db_session):
        """Test rotating a non-existent key."""
        fake_id = uuid4()
        result = await rotate_api_key(db_session, fake_id)
        
        assert result is None
