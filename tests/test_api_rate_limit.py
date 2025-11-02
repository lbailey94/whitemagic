"""
Tests for WhiteMagic API rate limiting.

Tests rate limiting logic and quota enforcement.
"""

import pytest
from datetime import date

from whitemagic.api.rate_limit import (
    RateLimiter,
    RateLimitExceeded,
    PLAN_LIMITS,
    update_quota_in_db,
    check_quota_limits,
)
from whitemagic.api.database import User, Quota
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from whitemagic.api.database import Base


@pytest.fixture
async def db_session():
    """Create test database session."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        yield session
        await session.rollback()
    
    await engine.dispose()


@pytest.fixture
async def test_user(db_session):
    """Create a test user."""
    user = User(
        email="test@example.com",
        plan_tier="free",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


class TestPlanLimits:
    """Tests for plan limit configurations."""
    
    def test_all_plans_have_limits(self):
        """Test that all plan tiers have defined limits."""
        required_plans = ['free', 'starter', 'pro', 'enterprise']
        
        for plan in required_plans:
            assert plan in PLAN_LIMITS, f"Missing limits for {plan} plan"
    
    def test_limits_have_required_fields(self):
        """Test that all plans have required limit fields."""
        required_fields = ['rpm', 'daily', 'monthly', 'memories', 'storage_mb']
        
        for plan, limits in PLAN_LIMITS.items():
            for field in required_fields:
                assert field in limits, f"{plan} plan missing {field} limit"
    
    def test_limits_are_progressive(self):
        """Test that higher tiers have higher limits."""
        plans = ['free', 'starter', 'pro', 'enterprise']
        
        for i in range(len(plans) - 1):
            current_plan = plans[i]
            next_plan = plans[i + 1]
            
            # Each tier should have higher limits
            assert PLAN_LIMITS[next_plan]['rpm'] >= PLAN_LIMITS[current_plan]['rpm']
            assert PLAN_LIMITS[next_plan]['daily'] >= PLAN_LIMITS[current_plan]['daily']
            assert PLAN_LIMITS[next_plan]['memories'] >= PLAN_LIMITS[current_plan]['memories']


class TestRateLimiter:
    """Tests for RateLimiter class."""
    
    def test_rate_limiter_initialization_without_redis(self):
        """Test rate limiter works without Redis (disabled mode)."""
        limiter = RateLimiter(redis_url=None)
        
        assert limiter.enabled is False
        assert limiter.redis_client is None
    
    @pytest.mark.asyncio
    async def test_rate_limiter_disabled_mode(self, test_user):
        """Test that disabled rate limiter allows all requests."""
        limiter = RateLimiter(redis_url=None)
        
        # Mock request
        class MockRequest:
            pass
        
        request = MockRequest()
        
        # Should not raise error
        info = await limiter.check_rate_limit(test_user, request)
        
        assert 'limit' in info
        assert 'remaining' in info
        assert 'reset' in info
    
    @pytest.mark.asyncio
    async def test_get_user_stats_disabled(self, test_user):
        """Test getting user stats when rate limiter is disabled."""
        limiter = RateLimiter(redis_url=None)
        
        stats = await limiter.get_user_stats(test_user)
        
        assert stats['rpm_used'] == 0
        assert stats['daily_used'] == 0
        assert 'rpm_limit' in stats
        assert 'daily_limit' in stats


class TestRateLimitExceeded:
    """Tests for RateLimitExceeded exception."""
    
    def test_rate_limit_exception_format(self):
        """Test rate limit exception has correct format."""
        exc = RateLimitExceeded('requests/minute', 10, 1234567890)
        
        assert exc.status_code == 429
        assert '10' in exc.detail
        assert 'requests/minute' in exc.detail
        assert 'X-RateLimit-Limit' in exc.headers
        assert 'X-RateLimit-Remaining' in exc.headers
        assert 'X-RateLimit-Reset' in exc.headers
    
    def test_rate_limit_exception_without_reset(self):
        """Test rate limit exception without reset time."""
        exc = RateLimitExceeded('requests', 100)
        
        assert exc.status_code == 429
        assert 'X-RateLimit-Reset' not in exc.headers


class TestQuotaManagement:
    """Tests for quota tracking in database."""
    
    @pytest.mark.asyncio
    async def test_update_quota_creates_new(self, db_session, test_user):
        """Test that update_quota creates new quota if none exists."""
        await update_quota_in_db(db_session, test_user)
        
        # Refresh to get quota
        await db_session.refresh(test_user, ["quota"])
        
        assert test_user.quota is not None
        assert test_user.quota.requests_today == 1
        assert test_user.quota.requests_this_month == 1
    
    @pytest.mark.asyncio
    async def test_update_quota_increments(self, db_session, test_user):
        """Test that update_quota increments existing quota."""
        # Create initial quota
        quota = Quota(
            user_id=test_user.id,
            requests_today=5,
            requests_this_month=100,
        )
        db_session.add(quota)
        await db_session.commit()
        
        # Update quota
        await update_quota_in_db(db_session, test_user)
        
        # Check incremented
        await db_session.refresh(quota)
        assert quota.requests_today == 6
        assert quota.requests_this_month == 101
    
    @pytest.mark.asyncio
    async def test_update_quota_resets_daily(self, db_session, test_user):
        """Test that daily quota resets on new day."""
        # Create quota from yesterday
        from datetime import timedelta
        yesterday = date.today() - timedelta(days=1)
        
        quota = Quota(
            user_id=test_user.id,
            requests_today=100,
            last_reset_daily=yesterday,
        )
        db_session.add(quota)
        await db_session.commit()
        
        # Update quota (should reset)
        await update_quota_in_db(db_session, test_user)
        
        await db_session.refresh(quota)
        assert quota.requests_today == 1  # Reset to 1
        assert quota.last_reset_daily == date.today()
    
    @pytest.mark.asyncio
    async def test_check_quota_limits_memory_count(self, db_session, test_user):
        """Test quota check fails when memory limit exceeded."""
        # Set user to free plan
        test_user.plan_tier = 'free'
        await db_session.commit()
        
        # Create quota at limit
        quota = Quota(
            user_id=test_user.id,
            memories_count=PLAN_LIMITS['free']['memories'],  # At limit
        )
        db_session.add(quota)
        await db_session.commit()
        
        # Should raise rate limit exceeded
        with pytest.raises(RateLimitExceeded) as exc_info:
            await check_quota_limits(db_session, test_user)
        
        assert 'memories' in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_check_quota_limits_storage(self, db_session, test_user):
        """Test quota check fails when storage limit exceeded."""
        test_user.plan_tier = 'free'
        await db_session.commit()
        
        # Create quota at storage limit
        storage_limit_bytes = PLAN_LIMITS['free']['storage_mb'] * 1024 * 1024
        quota = Quota(
            user_id=test_user.id,
            storage_bytes=storage_limit_bytes,  # At limit
        )
        db_session.add(quota)
        await db_session.commit()
        
        # Should raise rate limit exceeded
        with pytest.raises(RateLimitExceeded) as exc_info:
            await check_quota_limits(db_session, test_user)
        
        assert 'storage' in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_check_quota_limits_passes_under_limit(self, db_session, test_user):
        """Test quota check passes when under limits."""
        test_user.plan_tier = 'pro'
        await db_session.commit()
        
        # Create quota well under limits
        quota = Quota(
            user_id=test_user.id,
            memories_count=10,  # Way under pro limit
            storage_bytes=1024 * 1024,  # 1MB (way under)
        )
        db_session.add(quota)
        await db_session.commit()
        
        # Should not raise
        await check_quota_limits(db_session, test_user)  # No exception = pass


class TestPlanTierDifferences:
    """Tests to verify plan tier differences."""
    
    def test_free_vs_pro_limits(self):
        """Test that pro plan has significantly higher limits than free."""
        free_limits = PLAN_LIMITS['free']
        pro_limits = PLAN_LIMITS['pro']
        
        # Pro should have at least 10x the limits
        assert pro_limits['rpm'] >= free_limits['rpm'] * 10
        assert pro_limits['daily'] >= free_limits['daily'] * 10
        assert pro_limits['memories'] >= free_limits['memories'] * 10
    
    def test_enterprise_highest_limits(self):
        """Test that enterprise has the highest limits."""
        enterprise_limits = PLAN_LIMITS['enterprise']
        
        for plan in ['free', 'starter', 'pro']:
            plan_limits = PLAN_LIMITS[plan]
            assert enterprise_limits['rpm'] >= plan_limits['rpm']
            assert enterprise_limits['daily'] >= plan_limits['daily']
            assert enterprise_limits['memories'] >= plan_limits['memories']
