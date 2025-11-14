#!/usr/bin/env python3
import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

from whitemagic.api.database import User
from whitemagic.api.auth import create_api_key
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

async def main():
    db_url = os.getenv("DATABASE_URL")
    engine = create_async_engine(db_url, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession)
    
    async with async_session() as session:
        # Create test user
        user = User(email="test@whitemagic.dev", plan_tier="pro")
        session.add(user)
        await session.commit()
        await session.refresh(user)
        
        # Generate API key
        raw_key, api_key = await create_api_key(session, user.id, "Test Key")
        
        print(f"\n✅ Test API Key Created!")
        print(f"API Key: {raw_key}")
        print(f"User: {user.email}")
        print(f"Plan: {user.plan_tier}\n")
        
        # Save to file
        with open(".test_api_key", "w") as f:
            f.write(raw_key)
        print("💾 Saved to .test_api_key\n")

if __name__ == "__main__":
    asyncio.run(main())
