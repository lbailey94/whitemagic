"""
Tests for WhiteMagic API database models.

Tests database models, relationships, and basic CRUD operations.
Uses SQLite in-memory database for speed.
"""

import pytest
from datetime import datetime, date
from uuid import uuid4

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select

from whitemagic.api.database import Base, User, APIKey, UsageRecord, Quota, Database


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
        whop_user_id="whop_123",
        whop_membership_id="mem_456",
        plan_tier="pro",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


class TestUserModel:
    """Tests for User model."""
    
    @pytest.mark.asyncio
    async def test_create_user(self, db_session):
        """Test creating a user."""
        user = User(
            email="newuser@example.com",
            plan_tier="free",
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        assert user.id is not None
        assert user.email == "newuser@example.com"
        assert user.plan_tier == "free"
        assert user.whop_user_id is None
        assert user.created_at is not None
        assert user.updated_at is not None
    
    @pytest.mark.asyncio
    async def test_user_with_whop_data(self, db_session):
        """Test creating a user with Whop data."""
        user = User(
            email="whopuser@example.com",
            whop_user_id="whop_789",
            whop_membership_id="mem_012",
            plan_tier="enterprise",
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        assert user.whop_user_id == "whop_789"
        assert user.whop_membership_id == "mem_012"
        assert user.plan_tier == "enterprise"
    
    @pytest.mark.asyncio
    async def test_user_email_unique(self, db_session, sample_user):
        """Test that email must be unique."""
        duplicate_user = User(
            email=sample_user.email,  # Same email
            plan_tier="free",
        )
        db_session.add(duplicate_user)
        
        with pytest.raises(Exception):  # IntegrityError
            await db_session.commit()
    
    @pytest.mark.asyncio
    async def test_user_repr(self, sample_user):
        """Test user string representation."""
        repr_str = repr(sample_user)
        assert "User" in repr_str
        assert sample_user.email in repr_str
        assert sample_user.plan_tier in repr_str


class TestAPIKeyModel:
    """Tests for APIKey model."""
    
    @pytest.mark.asyncio
    async def test_create_api_key(self, db_session, sample_user):
        """Test creating an API key."""
        api_key = APIKey(
            user_id=sample_user.id,
            key_hash="abc123hash",
            key_prefix="wm_prod_abc...",
            name="Production Key",
        )
        db_session.add(api_key)
        await db_session.commit()
        await db_session.refresh(api_key)
        
        assert api_key.id is not None
        assert api_key.user_id == sample_user.id
        assert api_key.key_hash == "abc123hash"
        assert api_key.key_prefix == "wm_prod_abc..."
        assert api_key.name == "Production Key"
        assert api_key.is_active is True
        assert api_key.created_at is not None
    
    @pytest.mark.asyncio
    async def test_api_key_user_relationship(self, db_session, sample_user):
        """Test relationship between API key and user."""
        api_key = APIKey(
            user_id=sample_user.id,
            key_hash="xyz789hash",
            key_prefix="wm_dev_xyz...",
        )
        db_session.add(api_key)
        await db_session.commit()
        
        # Refresh to load relationships
        await db_session.refresh(sample_user, ["api_keys"])
        
        assert len(sample_user.api_keys) == 1
        assert sample_user.api_keys[0].key_hash == "xyz789hash"
    
    @pytest.mark.asyncio
    async def test_api_key_cascade_delete(self, db_session, sample_user):
        """Test that API keys are deleted when user is deleted."""
        api_key = APIKey(
            user_id=sample_user.id,
            key_hash="delete_test",
            key_prefix="wm_test...",
        )
        db_session.add(api_key)
        await db_session.commit()
        
        api_key_id = api_key.id
        
        # Delete user
        await db_session.delete(sample_user)
        await db_session.commit()
        
        # Check API key was deleted
        result = await db_session.execute(
            select(APIKey).where(APIKey.id == api_key_id)
        )
        assert result.scalar_one_or_none() is None


class TestUsageRecordModel:
    """Tests for UsageRecord model."""
    
    @pytest.mark.asyncio
    async def test_create_usage_record(self, db_session, sample_user):
        """Test creating a usage record."""
        usage = UsageRecord(
            user_id=sample_user.id,
            endpoint="/api/v1/memories",
            method="POST",
            status_code=201,
            response_time_ms=45,
        )
        db_session.add(usage)
        await db_session.commit()
        await db_session.refresh(usage)
        
        assert usage.id is not None
        assert usage.user_id == sample_user.id
        assert usage.endpoint == "/api/v1/memories"
        assert usage.method == "POST"
        assert usage.status_code == 201
        assert usage.response_time_ms == 45
        assert usage.date == date.today()
    
    @pytest.mark.asyncio
    async def test_usage_record_with_api_key(self, db_session, sample_user):
        """Test usage record with associated API key."""
        api_key = APIKey(
            user_id=sample_user.id,
            key_hash="usage_test",
            key_prefix="wm_test...",
        )
        db_session.add(api_key)
        await db_session.commit()
        
        usage = UsageRecord(
            user_id=sample_user.id,
            api_key_id=api_key.id,
            endpoint="/api/v1/search",
            method="POST",
            status_code=200,
        )
        db_session.add(usage)
        await db_session.commit()
        await db_session.refresh(usage, ["api_key"])
        
        assert usage.api_key_id == api_key.id
        assert usage.api_key.key_hash == "usage_test"


class TestQuotaModel:
    """Tests for Quota model."""
    
    @pytest.mark.asyncio
    async def test_create_quota(self, db_session, sample_user):
        """Test creating a quota record."""
        quota = Quota(
            user_id=sample_user.id,
            requests_today=100,
            requests_this_month=5000,
            memories_count=50,
            storage_bytes=1024 * 1024,  # 1MB
        )
        db_session.add(quota)
        await db_session.commit()
        await db_session.refresh(quota)
        
        assert quota.user_id == sample_user.id
        assert quota.requests_today == 100
        assert quota.requests_this_month == 5000
        assert quota.memories_count == 50
        assert quota.storage_bytes == 1024 * 1024
        assert quota.last_reset_daily == date.today()
    
    @pytest.mark.asyncio
    async def test_quota_user_relationship(self, db_session, sample_user):
        """Test one-to-one relationship between quota and user."""
        quota = Quota(
            user_id=sample_user.id,
            requests_today=10,
        )
        db_session.add(quota)
        await db_session.commit()
        
        await db_session.refresh(sample_user, ["quota"])
        
        assert sample_user.quota is not None
        assert sample_user.quota.requests_today == 10


class TestDatabase:
    """Tests for Database connection manager."""
    
    @pytest.mark.asyncio
    async def test_database_initialization(self):
        """Test Database class initialization."""
        db = Database(
            "sqlite+aiosqlite:///:memory:",
            echo=False,
        )
        
        assert db.engine is not None
        assert db.async_session is not None
        
        await db.close()
    
    @pytest.mark.asyncio
    async def test_create_tables(self):
        """Test creating all tables."""
        db = Database("sqlite+aiosqlite:///:memory:")
        
        await db.create_tables()
        
        # Verify tables exist by creating a user
        async with db.get_session() as session:
            user = User(email="tabletest@example.com")
            session.add(user)
            await session.commit()
            await session.refresh(user)
            
            assert user.id is not None
        
        await db.close()
    
    @pytest.mark.asyncio
    async def test_get_session(self):
        """Test getting a database session."""
        db = Database("sqlite+aiosqlite:///:memory:")
        await db.create_tables()
        
        session = db.get_session()
        assert isinstance(session, AsyncSession)
        
        await session.close()
        await db.close()
