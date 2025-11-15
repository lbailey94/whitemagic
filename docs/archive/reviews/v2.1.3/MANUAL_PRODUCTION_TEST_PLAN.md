# Manual Production Testing Plan - WhiteMagic v2.1.3

**Date**: November 12, 2025, 11:25am EST  
**Purpose**: Verify all functionality in production-like environment with Redis

---

## Test Environment Setup

### Prerequisites
- [x] All unit tests passing (196/196)
- [x] MCP tests passing (27/27)
- [ ] Redis running
- [ ] PostgreSQL running (optional, can use SQLite)
- [ ] API server started
- [ ] Test database initialized

### Environment Variables

```bash
# Required
export DATABASE_URL="sqlite:///./whitemagic_test.db"
export REDIS_URL="redis://localhost:6379"

# Optional for full testing
export ENABLE_RATE_LIMITING="true"
export WM_LOG_LEVEL="DEBUG"
export WM_ENABLE_EXEC_API="false"  # Keep disabled for security
```

---

## Test Plan

### Phase 1: Infrastructure (5 min)

#### 1.1 Start Redis
```bash
# Check if Redis is running
redis-cli ping
# Expected: PONG

# If not running, start it
docker run -d --name whitemagic-redis -p 6379:6379 redis:7-alpine
```

#### 1.2 Start API Server
```bash
cd /home/lucas/Desktop/whitemagic
export DATABASE_URL="sqlite:///./whitemagic_test.db"
export REDIS_URL="redis://localhost:6379"
export ENABLE_RATE_LIMITING="true"

# Start server
python3 -m uvicorn whitemagic.api.app:app --reload --port 8000
```

#### 1.3 Verify Startup
```bash
# Check health endpoint
curl http://localhost:8000/health
# Expected: {"status": "healthy", "version": "2.1.3"}

# Check ready endpoint  
curl http://localhost:8000/ready
# Expected: {"status": "ready"}

# Check version endpoint
curl http://localhost:8000/version
# Expected: {"version": "2.1.3", ...}
```

**✅ Pass Criteria**: All public endpoints return 200

---

### Phase 2: Authentication & Rate Limiting (10 min)

#### 2.1 Create Test User & API Key
```bash
# Create user via Python
python3 << 'EOF'
import asyncio
from whitemagic.api.database import Database
from whitemagic.api.auth import create_api_key

async def setup():
    db = Database("sqlite:///./whitemagic_test.db")
    await db.create_tables()
    
    async with db.get_session() as session:
        from whitemagic.api.database import User
        user = User(email="test@whitemagic.dev", plan_tier="pro")
        session.add(user)
        await session.commit()
        await session.refresh(user)
        
        api_key, _ = await create_api_key(session, user.id, "Test Key")
        print(f"API Key: {api_key}")
        print(f"User ID: {user.id}")
        
    await db.close()

asyncio.run(setup())
EOF
```

#### 2.2 Test Unauthenticated Access
```bash
# Should fail with 401
curl -X POST http://localhost:8000/api/v1/memories \
  -H "Content-Type: application/json" \
  -d '{"title": "Test", "content": "Test", "type": "short_term"}'
# Expected: 401 Unauthorized
```

#### 2.3 Test Authenticated Access
```bash
# Replace YOUR_API_KEY with actual key from step 2.1
export API_KEY="YOUR_API_KEY"

curl -X POST http://localhost:8000/api/v1/memories \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{"title": "Test Memory", "content": "Production test", "type": "short_term", "tags": ["test"]}'
# Expected: 200 OK with memory details
```

#### 2.4 Test Rate Limiting
```bash
# Make 10 requests quickly
for i in {1..10}; do
  curl -s -w "\nStatus: %{http_code}\n" \
    -X POST http://localhost:8000/api/v1/memories \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $API_KEY" \
    -d "{\"title\": \"Test $i\", \"content\": \"Test\", \"type\": \"short_term\"}"
done
# Expected: All should succeed (pro plan has high limits)

# Check rate limit headers
curl -I -X GET http://localhost:8000/api/v1/memories \
  -H "Authorization: Bearer $API_KEY"
# Expected: X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset headers
```

**✅ Pass Criteria**: 
- Unauthenticated requests → 401
- Authenticated requests → 200
- Rate limit headers present

---

### Phase 3: Core Memory Operations (15 min)

#### 3.1 Create Memory
```bash
curl -X POST http://localhost:8000/api/v1/memories \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{
    "title": "Production Test Memory",
    "content": "This is a production test of the memory system",
    "type": "short_term",
    "tags": ["production", "test", "v2.1.3"]
  }'
# Save the returned ID
```

#### 3.2 List Memories
```bash
curl http://localhost:8000/api/v1/memories \
  -H "Authorization: Bearer $API_KEY"
# Expected: Array with our test memory
```

#### 3.3 Get Single Memory
```bash
# Replace MEMORY_ID with ID from step 3.1
curl http://localhost:8000/api/v1/memories/MEMORY_ID \
  -H "Authorization: Bearer $API_KEY"
# Expected: Full memory details
```

#### 3.4 Update Memory
```bash
curl -X PATCH http://localhost:8000/api/v1/memories/MEMORY_ID \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{
    "content": "Updated content for production test",
    "add_tags": ["updated"]
  }'
# Expected: Updated memory
```

#### 3.5 Search Memories
```bash
curl "http://localhost:8000/api/v1/search?q=production&type=short_term" \
  -H "Authorization: Bearer $API_KEY"
# Expected: Results including our test memory
```

#### 3.6 Delete Memory
```bash
curl -X DELETE http://localhost:8000/api/v1/memories/MEMORY_ID \
  -H "Authorization: Bearer $API_KEY"
# Expected: 200 OK

# Verify deleted (should return empty or not found)
curl http://localhost:8000/api/v1/memories \
  -H "Authorization: Bearer $API_KEY"
```

**✅ Pass Criteria**: All CRUD operations work correctly

---

### Phase 4: Advanced Features (10 min)

#### 4.1 Context Generation
```bash
curl "http://localhost:8000/api/v1/context?tier=1" \
  -H "Authorization: Bearer $API_KEY"
# Expected: Context summary with memories
```

#### 4.2 Get Stats
```bash
curl http://localhost:8000/api/v1/stats \
  -H "Authorization: Bearer $API_KEY"
# Expected: Memory counts and statistics
```

#### 4.3 Get Tags
```bash
curl http://localhost:8000/api/v1/tags \
  -H "Authorization: Bearer $API_KEY"
# Expected: List of tags with counts
```

#### 4.4 Consolidation (Dry Run)
```bash
curl -X POST "http://localhost:8000/api/v1/consolidate?dry_run=true" \
  -H "Authorization: Bearer $API_KEY"
# Expected: Consolidation report without changes
```

**✅ Pass Criteria**: All advanced endpoints return valid data

---

### Phase 5: Public Endpoints (5 min)

#### 5.1 Static Files (if dashboard deployed)
```bash
curl -I http://localhost:8000/static/index.html
# Expected: 200 OK (or 404 if no static files)
```

#### 5.2 Documentation
```bash
curl http://localhost:8000/docs
# Expected: OpenAPI documentation page
```

#### 5.3 OpenAPI JSON
```bash
curl http://localhost:8000/openapi.json
# Expected: OpenAPI specification JSON
```

**✅ Pass Criteria**: Public endpoints accessible without auth

---

### Phase 6: Error Handling (5 min)

#### 6.1 Invalid JSON
```bash
curl -X POST http://localhost:8000/api/v1/memories \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d 'invalid json'
# Expected: 422 Unprocessable Entity
```

#### 6.2 Missing Required Fields
```bash
curl -X POST http://localhost:8000/api/v1/memories \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{"title": "No content field"}'
# Expected: 422 with validation error
```

#### 6.3 Invalid Memory Type
```bash
curl -X POST http://localhost:8000/api/v1/memories \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{"title": "Test", "content": "Test", "type": "invalid_type"}'
# Expected: 422 with validation error
```

#### 6.4 Not Found
```bash
curl http://localhost:8000/api/v1/memories/nonexistent \
  -H "Authorization: Bearer $API_KEY"
# Expected: 404 Not Found
```

**✅ Pass Criteria**: All error conditions return appropriate status codes

---

### Phase 7: Middleware & Logging (5 min)

#### 7.1 Check Server Logs
```bash
# Review server output for:
# - Structured JSON logs
# - Request logging with user_id
# - Rate limit checks
# - No errors or warnings

# Look for log entries like:
# {"timestamp": "...", "level": "INFO", "message": "request_started", "user_id": "...", ...}
```

#### 7.2 Verify Rate Limiter Initialization
```bash
# Check startup logs for:
# "Rate limiter initialized with Redis"
# "Redis connection successful"
```

#### 7.3 Check Redis Data
```bash
redis-cli
> KEYS whitemagic:*
# Expected: Keys for rate limiting, user data, etc.
```

**✅ Pass Criteria**: 
- Logs are structured and complete
- Rate limiter working
- Redis populated

---

## Test Results Checklist

### Infrastructure ✅
- [ ] Redis running
- [ ] API server started
- [ ] Health endpoints working
- [ ] No startup errors

### Authentication & Rate Limiting ✅
- [ ] Unauthenticated requests blocked
- [ ] Authenticated requests work
- [ ] Rate limit headers present
- [ ] Rate limiter initialized

### Core Operations ✅
- [ ] Create memory works
- [ ] List memories works
- [ ] Get memory works
- [ ] Update memory works
- [ ] Search works
- [ ] Delete memory works

### Advanced Features ✅
- [ ] Context generation works
- [ ] Stats endpoint works
- [ ] Tags endpoint works
- [ ] Consolidation works

### Public Endpoints ✅
- [ ] /health works
- [ ] /ready works
- [ ] /version works
- [ ] /docs works
- [ ] Static files work (if applicable)

### Error Handling ✅
- [ ] Invalid JSON handled
- [ ] Missing fields validated
- [ ] Invalid types rejected
- [ ] 404 errors work

### Middleware & Logging ✅
- [ ] Structured logging working
- [ ] Request logging includes user_id
- [ ] Rate limiter logs present
- [ ] No unexpected errors

---

## Final Verification

### All Critical Fixes Verified in Production
- [ ] Rate limiter doesn't crash on None user
- [ ] PUBLIC_PATHS accessible without auth
- [ ] Backup paths point to memory/ (test via CLI if time permits)
- [ ] Structured logging captures context
- [ ] Version reporting correct (2.1.3)

### Performance Check
- [ ] Response times < 200ms for simple operations
- [ ] No memory leaks after 100+ requests
- [ ] Redis connections properly pooled

### Security Check
- [ ] Unauthenticated requests blocked
- [ ] Rate limiting enforced
- [ ] Exec API disabled by default
- [ ] No sensitive data in logs

---

## Cleanup

```bash
# Stop API server (Ctrl+C)

# Stop Redis
docker stop whitemagic-redis
docker rm whitemagic-redis

# Remove test database
rm whitemagic_test.db

# Clear test data
rm -rf memory/
```

---

## Expected Duration
- Setup: 5 min
- Testing: 45 min
- Verification: 10 min
**Total**: ~60 minutes

---

## Success Criteria

✅ **PASS**: All checklist items completed without errors  
⚠️ **PARTIAL**: Minor issues found but core functionality works  
❌ **FAIL**: Critical functionality broken or errors present

---

## Notes

- Document any unexpected behavior
- Save full logs for review
- Screenshot any errors
- Note performance metrics

---

**Ready to execute? Let's ensure everything works perfectly! 🚀**
