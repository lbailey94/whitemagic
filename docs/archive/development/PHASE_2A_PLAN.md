# Phase 2A: Whop Integration & REST API

**Status**: 🚧 In Progress  
**Target**: Paid Beta Launch (90/100)  
**Timeline**: 7-10 days  
**Start Date**: November 2, 2025

---

## 🎯 Objectives

Transform WhiteMagic from open-source dev preview to commercial SaaS:

1. **Monetization**: Integrate Whop for licensing and payments
2. **API Access**: REST API for programmatic access
3. **Rate Limiting**: Prevent abuse, enforce quotas
4. **User Dashboard**: Key management and usage tracking
5. **Observability**: Logging, metrics, error tracking
6. **Legal Compliance**: ToS, Privacy Policy

---

## 📐 Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         User Layer                          │
├─────────────────────────────────────────────────────────────┤
│  IDE (MCP)    │  CLI/Python  │  REST API  │  Dashboard     │
└────────┬──────┴──────┬───────┴─────┬──────┴────────┬────────┘
         │             │             │               │
         └─────────────┴─────────────┴───────────────┘
                          │
         ┌────────────────▼────────────────┐
         │    FastAPI Application          │
         │  - Auth Middleware              │
         │  - Rate Limiting                │
         │  - Request Validation           │
         └────────┬───────────┬────────────┘
                  │           │
         ┌────────▼───────┐  ┌▼─────────────┐
         │  WhiteMagic    │  │  PostgreSQL  │
         │  Core Library  │  │  Database    │
         │  (unchanged)   │  │  - Users     │
         └────────────────┘  │  - API Keys  │
                             │  - Usage     │
                             └──────────────┘
                                    │
                       ┌────────────▼──────────────┐
                       │  Whop API                 │
                       │  - License validation     │
                       │  - Webhook handling       │
                       │  - Plan management        │
                       └───────────────────────────┘
```

---

## 🏗️ Implementation Phases

### **Week 1: Core Infrastructure (Days 1-5)**

#### Day 1: Database & API Keys
- PostgreSQL schema design
- User and API key models
- Key generation (secure random 32-byte)
- Key rotation functionality
- Basic CRUD operations

#### Day 2: REST API Foundation
- FastAPI application structure
- Core endpoints (/memory, /search, /context)
- Request/response models
- Error handling
- OpenAPI documentation

#### Day 3: Authentication & Rate Limiting
- API key middleware
- Rate limiting (Redis-backed)
- Quota enforcement
- Request logging
- Error responses

#### Day 4: Whop Integration
- Whop webhook handlers
- License validation
- Plan tier detection
- User provisioning flow
- Subscription updates

#### Day 5: User Dashboard MVP
- Simple web UI (React/Next.js)
- API key display/rotation
- Usage statistics
- Plan details
- Quick links to docs

### **Week 2: Polish & Launch (Days 6-7)**

#### Day 6: Observability & Legal
- Structured logging (JSON)
- Error tracking (Sentry)
- Basic metrics (Prometheus)
- ToS and Privacy Policy
- API documentation

#### Day 7: Testing & Launch
- End-to-end tests
- Load testing (100 concurrent users)
- Soft launch to beta users
- Monitor and iterate

---

## 💾 Database Schema

### Users Table
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    whop_user_id VARCHAR(255) UNIQUE,
    whop_membership_id VARCHAR(255),
    plan_tier VARCHAR(50) DEFAULT 'free',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_seen_at TIMESTAMP
);
```

### API Keys Table
```sql
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    key_hash VARCHAR(128) NOT NULL UNIQUE,
    key_prefix VARCHAR(16) NOT NULL,  -- For display (wm_abc123...)
    name VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    last_used_at TIMESTAMP,
    expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);
```

### Usage Table
```sql
CREATE TABLE usage_records (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    api_key_id UUID REFERENCES api_keys(id) ON DELETE SET NULL,
    endpoint VARCHAR(100) NOT NULL,
    method VARCHAR(10) NOT NULL,
    status_code INTEGER,
    response_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    date DATE GENERATED ALWAYS AS (created_at::date) STORED
);

CREATE INDEX idx_usage_user_date ON usage_records(user_id, date);
```

### Quotas Table
```sql
CREATE TABLE quotas (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    requests_today INTEGER DEFAULT 0,
    requests_this_month INTEGER DEFAULT 0,
    memories_count INTEGER DEFAULT 0,
    storage_bytes BIGINT DEFAULT 0,
    last_reset_daily DATE DEFAULT CURRENT_DATE,
    last_reset_monthly DATE DEFAULT DATE_TRUNC('month', CURRENT_DATE)
);
```

---

## 🔑 API Key System

### Format
```
wm_<env>_<32-char-base62>
Example: wm_prod_aB3xY9kL2mN4pQ7rS8tU5vW1xY2zA3bC
```

### Generation
```python
import secrets
import hashlib

def generate_api_key(environment='prod'):
    """Generate a secure API key"""
    random_part = secrets.token_urlsafe(24)[:32]
    key = f"wm_{environment}_{random_part}"
    
    # Store hash, not raw key
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    key_prefix = key[:16]  # For display
    
    return key, key_hash, key_prefix
```

### Validation
```python
async def validate_api_key(key: str) -> User:
    """Validate API key and return user"""
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    
    api_key = await db.fetch_one(
        "SELECT * FROM api_keys WHERE key_hash = $1 AND is_active = true",
        key_hash
    )
    
    if not api_key or (api_key.expires_at and api_key.expires_at < datetime.now()):
        raise Unauthorized("Invalid or expired API key")
    
    user = await db.fetch_one("SELECT * FROM users WHERE id = $1", api_key.user_id)
    
    # Update last_used
    await db.execute(
        "UPDATE api_keys SET last_used_at = NOW() WHERE id = $1",
        api_key.id
    )
    
    return user
```

---

## 🚦 Rate Limiting

### Strategy: Token Bucket (Redis-backed)

```python
from fastapi import HTTPException
import redis.asyncio as redis

class RateLimiter:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
    
    async def check_rate_limit(self, user_id: str, plan_tier: str) -> bool:
        """Check if user is within rate limits"""
        limits = {
            'free': {'rpm': 10, 'daily': 100},
            'starter': {'rpm': 60, 'daily': 5000},
            'pro': {'rpm': 300, 'daily': 50000},
            'enterprise': {'rpm': 1000, 'daily': 1000000}
        }
        
        limit = limits.get(plan_tier, limits['free'])
        
        # Check per-minute rate
        rpm_key = f"ratelimit:rpm:{user_id}"
        rpm_count = await self.redis.incr(rpm_key)
        
        if rpm_count == 1:
            await self.redis.expire(rpm_key, 60)
        
        if rpm_count > limit['rpm']:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded: {limit['rpm']} requests/minute"
            )
        
        # Check daily quota
        daily_key = f"ratelimit:daily:{user_id}:{date.today()}"
        daily_count = await self.redis.incr(daily_key)
        
        if daily_count == 1:
            await self.redis.expire(daily_key, 86400)
        
        if daily_count > limit['daily']:
            raise HTTPException(
                status_code=429,
                detail=f"Daily quota exceeded: {limit['daily']} requests/day"
            )
        
        return True
```

---

## 🔗 Whop Integration

### Webhook Handler
```python
from fastapi import Request, HTTPException
import hmac
import hashlib

@app.post("/webhooks/whop")
async def whop_webhook(request: Request):
    """Handle Whop webhooks for subscription events"""
    
    # Verify signature
    signature = request.headers.get("X-Whop-Signature")
    body = await request.body()
    
    expected_sig = hmac.new(
        WHOP_WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(signature, expected_sig):
        raise HTTPException(403, "Invalid signature")
    
    event = await request.json()
    
    # Handle event types
    if event['type'] == 'membership:created':
        await handle_new_subscription(event['data'])
    elif event['type'] == 'membership:updated':
        await handle_subscription_update(event['data'])
    elif event['type'] == 'membership:cancelled':
        await handle_cancellation(event['data'])
    
    return {"status": "ok"}

async def handle_new_subscription(data):
    """Provision new user with API key"""
    user = await User.create(
        email=data['email'],
        whop_user_id=data['user_id'],
        whop_membership_id=data['membership_id'],
        plan_tier=get_plan_tier(data['plan_id'])
    )
    
    # Generate API key
    key, key_hash, key_prefix = generate_api_key()
    
    await APIKey.create(
        user_id=user.id,
        key_hash=key_hash,
        key_prefix=key_prefix,
        name="Default API Key"
    )
    
    # Send welcome email with API key
    await send_welcome_email(user.email, key)
```

---

## 🎨 REST API Endpoints

### Core Endpoints

```
POST   /api/v1/memories              Create memory
GET    /api/v1/memories              List memories
GET    /api/v1/memories/{id}         Get memory
PUT    /api/v1/memories/{id}         Update memory
DELETE /api/v1/memories/{id}         Delete memory

POST   /api/v1/search                Search memories
POST   /api/v1/context               Generate context
POST   /api/v1/consolidate           Run consolidation

GET    /api/v1/tags                  List all tags
GET    /api/v1/stats                 Get statistics

GET    /api/v1/user/me               Get current user
GET    /api/v1/user/usage            Get usage stats
POST   /api/v1/user/keys             Create API key
DELETE /api/v1/user/keys/{id}        Revoke API key
```

### Example: Create Memory
```python
@app.post("/api/v1/memories", response_model=MemoryResponse)
async def create_memory(
    request: CreateMemoryRequest,
    user: User = Depends(get_current_user)
):
    """Create a new memory"""
    
    # Check quotas
    await check_quota(user.id)
    
    # Create memory using core library
    manager = MemoryManager(base_dir=get_user_dir(user.id))
    
    path = manager.create_memory(
        title=request.title,
        content=request.content,
        memory_type=request.type,
        tags=request.tags
    )
    
    # Log usage
    await log_usage(user.id, "create_memory")
    
    return MemoryResponse(
        success=True,
        path=str(path),
        message="Memory created successfully"
    )
```

---

## 📊 Plan Tiers

| Tier | Price/mo | RPM | Daily Quota | Storage | Features |
|------|----------|-----|-------------|---------|----------|
| **Free** | $0 | 10 | 100 | 10MB | Basic features, MCP only |
| **Starter** | $10 | 60 | 5,000 | 100MB | REST API, email support |
| **Pro** | $30 | 300 | 50,000 | 1GB | Priority support, webhooks |
| **Enterprise** | Custom | 1000 | 1M | 10GB | SLA, dedicated support |

---

## 🔐 Security Considerations

1. **API Keys**: SHA-256 hashed, never stored in plaintext
2. **Rate Limiting**: Redis-backed token bucket
3. **Input Validation**: Pydantic models for all requests
4. **SQL Injection**: Parameterized queries only
5. **CORS**: Whitelist specific domains
6. **HTTPS**: Enforce TLS 1.2+
7. **Secrets**: Environment variables, never committed

---

## 📈 Observability

### Logging (Structured JSON)
```python
import structlog

logger = structlog.get_logger()

logger.info(
    "memory_created",
    user_id=user.id,
    memory_type="long_term",
    tags=["api", "pattern"],
    duration_ms=12
)
```

### Metrics (Prometheus)
- `whitemagic_requests_total` - Total API requests
- `whitemagic_request_duration_seconds` - Request latency
- `whitemagic_rate_limit_hits_total` - Rate limit violations
- `whitemagic_memories_total` - Total memories by type
- `whitemagic_active_users` - Active users (24h)

### Error Tracking (Sentry)
- Automatic exception capture
- User context attached
- Performance monitoring
- Release tracking

---

## 📜 Legal Documents

### Terms of Service (key points)
- Service description
- User obligations
- Payment terms
- Refund policy (pro-rated)
- Data retention (30 days post-cancellation)
- Liability limitations
- Termination conditions

### Privacy Policy (GDPR-compliant)
- Data collected (email, usage, memories)
- Purpose (service delivery, billing)
- Third parties (Whop, hosting provider)
- User rights (access, deletion, export)
- Data retention periods
- Security measures

---

## 🧪 Testing Strategy

### Unit Tests
- API endpoint tests
- Rate limiter tests
- Auth middleware tests
- Whop webhook tests

### Integration Tests
- End-to-end API flows
- Database transactions
- Redis rate limiting
- Whop API mocking

### Load Tests (Locust)
- 100 concurrent users
- 1000 requests/minute
- Various endpoints
- Success rate >99.9%

---

## 🚀 Deployment

### Infrastructure
- **App**: Railway/Fly.io/Render
- **Database**: Neon/Supabase (PostgreSQL)
- **Cache**: Upstash Redis
- **Monitoring**: Better Stack/Axiom

### Environment Variables
```bash
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
WHOP_API_KEY=whop_...
WHOP_WEBHOOK_SECRET=whsec_...
SENTRY_DSN=https://...
ALLOWED_ORIGINS=https://app.whitemagic.dev
```

---

## 📝 Success Criteria

- [ ] New user can purchase → receive key → make API call in <5 minutes
- [ ] Rate limits actually block when exceeded
- [ ] All endpoints return proper error codes
- [ ] 23/23 existing tests still pass
- [ ] 50+ new tests added for Phase 2A
- [ ] Load test: 100 concurrent users, 99.9% success
- [ ] Documentation complete (API docs, quickstart)
- [ ] Legal docs published (ToS, Privacy)
- [ ] Monitoring dashboard operational

---

## 🎯 Definition of Done

**Phase 2A is complete when:**

1. ✅ User can buy on Whop and get API key
2. ✅ REST API with 10+ endpoints functional
3. ✅ Rate limiting enforced per plan tier
4. ✅ Dashboard shows usage and allows key rotation
5. ✅ Whop webhooks handle subscription events
6. ✅ Logging and error tracking operational
7. ✅ ToS and Privacy Policy published
8. ✅ Documentation complete
9. ✅ All tests passing (>70 total)
10. ✅ Soft launch to 10 beta users successful

---

**Next**: Begin Day 1 - Database Schema & API Key System

Ready to start? 🚀
