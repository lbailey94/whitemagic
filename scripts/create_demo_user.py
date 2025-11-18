#!/usr/bin/env python3
"""
Create a demo user and API key for testing the dashboard.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from whitemagic.api.auth import create_api_key
from whitemagic.api.database import Database, Quota, User


async def create_demo_user():
    """Create a demo user with API key."""

    # Get database URL from environment or use SQLite default
    database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./users/whitemagic.db")
    print(f"📊 Using database: {database_url.split('://')[0]}://...")

    # Initialize database
    db = Database(database_url=database_url)
    await db.create_tables()

    try:
        async with db.get_session() as session:
            # Check if demo user already exists
            result = await session.execute(select(User).where(User.email == "demo@whitemagic.dev"))
            user = result.scalar_one_or_none()

            if user:
                print(f"✅ Demo user already exists: {user.email}")
                print(f"   User ID: {user.id}")
                print(f"   Plan: {user.plan_tier}")
            else:
                # Create new demo user
                user = User(
                    email="demo@whitemagic.dev",
                    plan_tier="starter",
                )
                session.add(user)
                await session.flush()

                # Create quota
                quota = Quota(user_id=user.id)
                session.add(quota)

                await session.commit()
                await session.refresh(user)

                print(f"✅ Created new demo user: {user.email}")
                print(f"   User ID: {user.id}")
                print(f"   Plan: {user.plan_tier}")

            # Generate API key
            raw_key, api_key_obj = await create_api_key(
                session,
                user.id,
                name="Dashboard Test Key",
            )

            print("\n🔑 API Key Generated:")
            print(f"   {raw_key}")
            print("\n⚠️  SAVE THIS KEY - It won't be shown again!")
            print("\n📋 Use this key in the dashboard login form.")

            return raw_key

    finally:
        await db.close()


if __name__ == "__main__":
    try:
        api_key = asyncio.run(create_demo_user())
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
