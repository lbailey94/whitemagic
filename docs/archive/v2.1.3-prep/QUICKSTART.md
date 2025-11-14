# WhiteMagic Quick Start Guide

Get WhiteMagic running in 5 minutes!

---

## Prerequisites

- Python 3.11+
- PostgreSQL
- Redis (optional, for rate limiting)

---

## 1. Install

```bash
cd /home/lucas/Desktop/whitemagic
pip install -e .[api]
```

---

## 2. Set Environment

```bash
export DATABASE_URL="sqlite+aiosqlite:///./whitemagic.db"
export REDIS_URL="redis://localhost:6379"  # Optional
```

---

## 3. Start API

```bash
uvicorn whitemagic.api.app:app --reload
```

---

## 4. Open Dashboard

Visit: http://localhost:8000/

---

## 5. Create API Key

### Option A: Via CLI (coming soon)
```bash
python -m whitemagic.api.cli create-key --email test@example.com
```

### Option B: Via Python

```python
import asyncio
from whitemagic.api.database import Database, User
from whitemagic.api.auth import create_api_key

async def main():
    db = Database("sqlite+aiosqlite:///./whitemagic.db")
    await db.create_tables()
    
    async with db.get_session() as session:
        user = User(email="test@example.com", plan_tier="pro")
        session.add(user)
        await session.commit()
        await session.refresh(user)
        
        raw_key, _ = await create_api_key(session, user.id, name="Test Key")
        print(f"API Key: {raw_key}")

asyncio.run(main())
```

---

## 6. Test API

```bash
# Health check
curl http://localhost:8000/health

# Create memory
curl -X POST http://localhost:8000/api/v1/memories \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"title": "Test", "content": "Hello World", "type": "short_term"}'
```

---

## 7. View API Docs

http://localhost:8000/docs

---

## Production Deploy

See [DEPLOYMENT.md](DEPLOYMENT.md) for production setup with Railway, Render, or Fly.io.

---

**That's it! You're running WhiteMagic!** 🎉
