#!/usr/bin/env python3
"""
Create a test user and API key for dashboard testing
"""
import asyncio
import sys
from sqlalchemy import select

# Add parent directory to path
sys.path.insert(0, '/home/lucas/Desktop/whitemagic')

from whitemagic.api.database import Database, User, Quota
from whitemagic.api.auth import create_api_key


async def create_test_user():
    """Create test user with API key."""
    
    # Initialize database
    database_url = "sqlite+aiosqlite:///./whitemagic.db"
    db = Database(database_url, echo=False)
    await db.create_tables()
    
    async with db.get_session() as session:
        # Check if test user exists
        result = await session.execute(
            select(User).where(User.email == "test@whitemagic.dev")
        )
        user = result.scalar_one_or_none()
        
        if not user:
            # Create test user
            user = User(
                email="test@whitemagic.dev",
                plan_tier="free",  # Start with free tier to see upgrade banner
            )
            session.add(user)
            await session.flush()
            
            # Create quota
            quota = Quota(user_id=user.id)
            session.add(quota)
            
            await session.commit()
            await session.refresh(user)
            
            print(f"✅ Created test user: {user.email}")
        else:
            print(f"✅ Test user already exists: {user.email}")
        
        # Create API key
        raw_key, api_key = await create_api_key(
            session,
            user.id,
            name="Dashboard Test Key",
        )
        
        print(f"\n🔑 API Key Created!")
        print(f"━" * 60)
        print(f"Copy this key to log in:")
        print(f"\n{raw_key}\n")
        print(f"━" * 60)
        print(f"Key Prefix: {api_key.key_prefix}")
        print(f"User Email: {user.email}")
        print(f"Plan Tier: {user.plan_tier}")
        print(f"\n📍 Dashboard: http://localhost:3000")
        print(f"📍 API Docs: http://localhost:8000/docs")
    
    await db.close()


if __name__ == "__main__":
    asyncio.run(create_test_user())
