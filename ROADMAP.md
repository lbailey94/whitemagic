# WhiteMagic Development Roadmap

**Current Version**: 2.2.0 ✅ (Released Nov 15, 2025)  
**Next Version**: 2.3.0 (SDK Realignment & API Completion)  
**Status**: Core Stable, Addressing Integration Issues  
**Updated**: November 15, 2025

---

## 📖 Detailed Roadmap

**For comprehensive version-by-version roadmap (v2.1.4 → v3.0), see:**
**[ROADMAP_v2.1.4_to_v3.0.md](./ROADMAP_v2.1.4_to_v3.0.md)**

This document contains the strategic vision, release timeline, feature details, pricing strategy, and success metrics for the next 6 months of development.

---

## Project Vision (Updated)

WhiteMagic is **memory infrastructure for AI agents and developers**:
- ✅ Native Python API (importable library)
- ✅ REST API with auth, quotas, rate limits
- ✅ MCP server (IDE integration - Cursor, Windsurf, Claude)
- ✅ Semantic search with embeddings
- 🚧 Multi-tier monetization via Whop
- 🚧 Graph-based memory relationships
- 🚧 Team workspaces & collaboration
- 🚧 Multi-modal memory (images, PDFs, audio)

---

## Completed: v2.0.1 Foundation ✅

### Core Product (October-November 2025)
- ✅ Tiered prompt system (Tier 0/1/2)
- ✅ Memory management (short-term, long-term, archive)
- ✅ CLI with 10 commands (create, list, search, update, delete, restore, consolidate, list-tags, normalize-tags, context)
- ✅ Tag normalization and statistics
- ✅ Archive workflow (delete → restore)
- ✅ 18 comprehensive tests (100% pass rate)
- ✅ Complete documentation (90KB+ of design docs)

### Architecture Documents Created
1. **PYTHON_API_DESIGN.md** (27KB) - Package structure & performance
2. **REST_API_DESIGN.md** (24KB) - FastAPI architecture & deployment
3. **TOOL_WRAPPERS_GUIDE.md** (28KB) - Framework integrations
4. **API_BENEFITS_ANALYSIS.md** (14KB) - ROI & market analysis
5. **RELEASE_v2.0.1.md** (10KB) - Release notes & migration guide

### Strategic Insights (GPT-5 Recommendations)
- ✅ MCP (Model Context Protocol) identified as game-changer
- ✅ Whop platform for monetization & distribution
- ✅ Hybrid model (local-first + cloud sync optional)
- ✅ Realistic revenue projections ($60K Year 1 → $185K Year 2)

---

## Phase 1A: Python API + REST Foundation

**Timeline**: 7 days (focused work)  
**Status**: 🚧 IN PROGRESS  
**Quality Bar**: 100% test coverage maintained

### Objectives

1. **Importable Python Package**
   - Refactor `memory_manager.py` into `whitemagic/` package
   - Pydantic data models (type-safe)
   - Custom exceptions
   - PyPI-ready structure

2. **REST API**
   - FastAPI backend with GPT-5's endpoints
   - API key authentication
   - Rate limiting & quota enforcement
   - OpenAPI/Swagger documentation

3. **Docker Deployment**
   - Single-command deployment
   - Environment configuration
   - Health checks & monitoring

### Package Structure

```
whitemagic/
├── __init__.py              # Public API exports
├── core.py                  # MemoryManager (refactored from memory_manager.py)
├── models.py                # Pydantic data classes (Memory, Tag, Stats, etc.)
├── exceptions.py            # Custom exceptions (MemoryNotFoundError, etc.)
├── utils.py                 # Helper functions (_normalize_tags, etc.)
├── api/
│   ├── __init__.py
│   ├── main.py             # FastAPI application
│   ├── auth.py             # API key middleware
│   ├── routes/
│   │   ├── memories.py     # Memory CRUD endpoints
│   │   ├── search.py       # Search endpoints
│   │   ├── context.py      # Context generation
│   │   └── admin.py        # Key management
│   └── schemas.py          # Request/response models
├── cli.py                   # CLI wrapper (backward compatible)
└── constants.py             # Configuration constants
```

### REST API Endpoints (GPT-5 Spec)

**Base URL**: `http://localhost:8000/v1`  
**Auth**: `Authorization: Bearer <api_key>`

#### Core Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/memories` | Create memory |
| `GET` | `/memories/:id` | Get memory by ID |
| `PUT` | `/memories/:id` | Update memory |
| `DELETE` | `/memories/:id` | Delete/archive memory |
| `POST` | `/memories/search` | Search memories |
| `POST` | `/memories/:id/restore` | Restore archived memory |

#### System Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/context` | Generate tiered context |
| `POST` | `/consolidate` | Consolidate short-term memories |
| `GET` | `/stats` | Get system statistics |
| `GET` | `/tags` | List all tags with stats |

#### Admin Endpoints (for Phase 2A)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/keys` | Create API key |
| `DELETE` | `/keys/:id` | Revoke API key |
| `GET` | `/keys` | List API keys |

### Deliverables

- [x] Python package (`whitemagic/`)
- [x] REST API with all endpoints
- [x] Docker deployment (`Dockerfile`, `docker-compose.yml`)
- [x] API documentation (Swagger UI at `/docs`)
- [x] 30+ tests (23 core + 11 new API tests)
- [x] Migration guide for v2.0.1 users
- [ ] Performance benchmarks (API vs CLI)

### Success Criteria

- ✅ All existing CLI functionality available via API
- ✅ <1ms response time for memory operations (vs 100-200ms CLI)
- ✅ 100% test coverage maintained
- ✅ Backward compatible (existing CLI still works)
- ✅ Docker deployment works out-of-box
- ✅ API documentation complete

---

## Phase 1B: MCP Server

**Timeline**: 3-4 days  
**Status**: ✅ COMPLETE  
**Quality Bar**: 100% test coverage

### Objectives

1. **MCP Protocol Implementation**
   - Node.js MCP server
   - Resources: `memory://short_term`, `memory://long_term`
   - Tools: `create_memory`, `search`, `context`, `consolidate`
   - Events: `memory.updated`, `consolidation.completed`

2. **IDE Integration**
   - Works with Cursor
   - Works with Windsurf
   - Works with Claude Desktop
   - One-command installation

3. **Docker Packaging**
   - MCP server container
   - Auto-connects to REST API
   - Environment-based configuration

### Package Structure

```
whitemagic-mcp/
├── package.json
├── mcp.json                # MCP manifest
├── src/
│   ├── server.ts          # MCP server implementation
│   ├── client.ts          # REST API client
│   └── types.ts           # TypeScript types
├── Dockerfile
├── docker-compose.yml
└── README.md              # Installation guide
```

### MCP Manifest (mcp.json)

```json
{
  "name": "white-magic-memory",
  "version": "1.0.0",
  "description": "Tiered prompt + external memory for AI agents",
  "resources": [
    {"uri": "memory://short_term", "mimeType": "application/json"},
    {"uri": "memory://long_term", "mimeType": "application/json"}
  ],
  "tools": [
    {
      "name": "create_memory",
      "description": "Create a new memory entry",
      "inputSchema": {
        "type": "object",
        "properties": {
          "title": {"type": "string"},
          "content": {"type": "string"},
          "type": {"type": "string", "enum": ["short_term", "long_term"]},
          "tags": {"type": "array", "items": {"type": "string"}}
        },
        "required": ["title", "content", "type"]
      }
    },
    {
      "name": "search",
      "description": "Search memories by query and filters",
      "inputSchema": {
        "type": "object",
        "properties": {
          "query": {"type": "string"},
          "type": {"type": "string"},
          "tags": {"type": "array", "items": {"type": "string"}},
          "limit": {"type": "number"}
        },
        "required": ["query"]
      }
    },
    {
      "name": "context",
      "description": "Generate tiered context for AI agents",
      "inputSchema": {
        "type": "object",
        "properties": {
          "tier": {"type": "number", "enum": [0, 1, 2]}
        },
        "required": ["tier"]
      }
    },
    {
      "name": "consolidate",
      "description": "Consolidate and archive old short-term memories",
      "inputSchema": {
        "type": "object",
        "properties": {
          "dry_run": {"type": "boolean"}
        }
      }
    }
  ],
  "env": ["WM_API_URL", "WM_API_KEY"]
}
```

### Deliverables

- [x] MCP server (Node.js/TypeScript)
- [x] Works with Cursor/Windsurf/Claude Desktop
- [ ] Docker deployment
- [x] Installation guide with screenshots
- [x] Integration tests
- [ ] Demo video

### Success Criteria

- ✅ Cursor can install and use WhiteMagic MCP
- ✅ All tools function correctly
- ✅ Resources return valid data
- ✅ <100ms latency for tool calls
- ✅ Documentation with step-by-step setup

---

## Phase 2A: Whop Integration & Monetization

**Timeline**: 1 week  
**Status**: ⏳ PENDING (after Phase 1B)  
**Quality Bar**: 100% test coverage

### Objectives

1. **Whop Webhook Integration**
   - Handle subscription lifecycle events
   - Provision/deprovision API keys
   - Manage seat allocations
   - Grace period handling

2. **License System**
   - API key generation with plans/limits
   - CLI activation (`wm activate <key>`)
   - Offline license validation
   - Usage tracking & enforcement

3. **Dashboard (Whop Experience View)**
   - API key management (create/rotate/revoke)
   - Usage statistics (memories, storage, API calls)
   - Toggle: local-only vs cloud-sync
   - Plan upgrade/downgrade

### Package Structure

```
whitemagic-dashboard/
├── app/                    # Next.js App Router
│   ├── api/
│   │   └── whop/
│   │       └── webhook/
│   │           └── route.ts
│   └── dashboard/
│       ├── page.tsx       # Main dashboard
│       ├── keys/
│       │   └── page.tsx   # API key management
│       └── usage/
│           └── page.tsx   # Usage statistics
├── lib/
│   ├── db.ts              # Database client (Prisma)
│   ├── license.ts         # License generation/validation
│   └── whop.ts            # Whop API client
├── prisma/
│   └── schema.prisma      # Database schema
└── public/
```

### Database Schema

```prisma
model User {
  id            String   @id @default(cuid())
  whopUserId    String   @unique
  email         String
  plan          String   // "free", "pro", "team", "enterprise"
  planExpiry    DateTime?
  createdAt     DateTime @default(now())
  updatedAt     DateTime @updatedAt
  
  apiKeys       ApiKey[]
  usage         Usage[]
}

model ApiKey {
  id            String   @id @default(cuid())
  key           String   @unique
  userId        String
  label         String?
  plan          String
  rateLimit     Int      // requests per minute
  quota         Int      // memories per month
  status        String   // "active", "grace", "revoked"
  createdAt     DateTime @default(now())
  expiresAt     DateTime?
  
  user          User     @relation(fields: [userId], references: [id])
  usage         Usage[]
}

model Usage {
  id            String   @id @default(cuid())
  userId        String
  apiKeyId      String
  endpoint      String
  timestamp     DateTime @default(now())
  
  user          User     @relation(fields: [userId], references: [id])
  apiKey        ApiKey   @relation(fields: [apiKeyId], references: [id])
}
```

### Pricing Tiers

| Tier | Price | Memories | Storage | API Calls | Features |
|------|-------|----------|---------|-----------|----------|
| **Free** | $0 | 10,000 | 100MB | 1,000/mo | Local-only |
| **Pro** | $15/mo | Unlimited | 10GB | 100k/mo | Cloud sync, embeddings, hosted MCP |
| **Team** | $79/mo | Unlimited | 100GB | 1M/mo | 5 seats, shared workspace, RBAC |
| **Enterprise** | Custom | Unlimited | Custom | Unlimited | SSO, on-prem, SLA, audit logs |

### Deliverables

- [ ] Whop webhook handlers
- [ ] License system (generation, validation, activation)
- [ ] Dashboard UI (Next.js)
- [ ] CLI activation command
- [ ] Database schema & migrations
- [ ] Rate limiting & quota enforcement in API
- [ ] Documentation (setup, activation, dashboard usage)

### Success Criteria

- ✅ Whop purchases auto-provision API keys
- ✅ Cancellations handle gracefully
- ✅ CLI activation works offline
- ✅ Dashboard shows real-time usage
- ✅ Rate limits enforced correctly
- ✅ Plan upgrades/downgrades work seamlessly

---

## Phase 2B: Semantic Search & Embeddings

**Timeline**: 1 week  
**Status**: ⏳ PENDING (after Phase 2A)  
**Quality Bar**: 100% test coverage

### Objectives

1. **Embedding Generation**
   - OpenAI embeddings (cloud)
   - Local embeddings (sentence-transformers)
   - Batch processing for existing memories
   - Automatic embedding on create/update

2. **Vector Storage**
   - pgvector for self-hosted (Pro+)
   - Pinecone/Weaviate optional (Enterprise)
   - Migration script for existing data

3. **Hybrid Search**
   - Combine keyword + semantic search
   - Configurable weighting
   - Re-ranking algorithms

### API Extensions

```python
# New endpoint: POST /memories/search/semantic
{
  "query": "How do I debug async race conditions?",
  "k": 10,
  "filters": {"type": "long_term"},
  "mode": "hybrid"  # "keyword", "semantic", "hybrid"
}

# Response includes relevance scores
{
  "items": [
    {
      "id": "mem_123",
      "title": "Async Debugging Heuristics",
      "content": "...",
      "score": 0.92,
      "match_type": "semantic"
    }
  ]
}
```

### Deliverables

- [ ] Embedding generation (OpenAI + local models)
- [ ] Vector storage (pgvector integration)
- [ ] Hybrid search algorithm
- [ ] Batch migration script
- [ ] Performance benchmarks (keyword vs semantic vs hybrid)
- [ ] Documentation (configuration, migration, tuning)
- [ ] Cost analysis (embedding costs vs local)

### Success Criteria

- ✅ Semantic search returns relevant results
- ✅ Hybrid search outperforms keyword-only
- ✅ <200ms query latency
- ✅ Migration script handles 10k+ memories
- ✅ Local embeddings option for privacy
- ✅ Cost-effective at scale

---

## Phase 3: Extensions & Integrations

**Timeline**: 2 weeks  
**Status**: ⏳ PENDING (after Phase 2B)

### VS Code Extension

- Sidebar: Browse memories
- Commands: Create/search from editor
- Auto-context injection
- Whop login integration

### Cursor/Windsurf Deep Integration

- Native MCP installation
- Context injection on demand
- Memory creation shortcuts
- Team workspace sync

### Alternative Framework Adapters (if needed)

- LangChain adapter
- LlamaIndex integration
- Direct OpenAI/Anthropic wrappers

### Mobile Apps (Stretch Goal)

- iOS/Android for memory creation
- Voice-to-memory
- Photo/document ingestion

---

## Success Metrics

### Technical Metrics

| Metric | Current (v2.0.1) | Target (Phase 1A) | Target (Phase 2B) |
|--------|------------------|-------------------|-------------------|
| Test Coverage | 100% (18 tests) | 100% (30+ tests) | 100% (50+ tests) |
| API Response Time | 100-200ms (CLI) | <1ms (Python) | <1ms (Python) |
| Search Latency | ~50ms (keyword) | ~50ms (keyword) | <200ms (hybrid) |
| Docker Deploy Time | N/A | <60s | <60s |

### Business Metrics (Post-Phase 2A)

| Metric | Month 3 | Month 6 | Month 12 |
|--------|---------|---------|----------|
| Free Users | 200 | 500 | 2,000 |
| Pro Users | 10 | 50 | 200 |
| Team Users | 2 | 5 | 25 |
| MRR | $350 | $1,375 | $4,975 |
| Churn Rate | <10% | <5% | <5% |

### Market Metrics

- GitHub stars: 500 (6 months), 2,000 (12 months)
- MCP installs: 1,000 (6 months), 5,000 (12 months)
- PyPI downloads: 5k/mo (6 months), 20k/mo (12 months)

---

## Risk Mitigation

### Technical Risks

| Risk | Mitigation |
|------|-----------|
| Breaking existing users | Maintain CLI backward compatibility, thorough testing |
| Performance degradation | Benchmark all changes, optimize hot paths |
| Vector search costs | Offer local embeddings, batch processing |
| MCP adoption slow | Maintain REST API + tool wrappers as alternatives |

### Business Risks

| Risk | Mitigation |
|------|-----------|
| Low conversion to paid | Generous free tier, clear value prop, testimonials |
| Whop platform issues | Build license system that can run standalone |
| Competition | Speed to market, quality focus, community building |
| Pricing too high/low | A/B testing, user feedback, competitor analysis |

---

## Dependencies

### External Services (Phase 2A+)

- **Whop**: Payment processing, webhooks
- **OpenAI** (optional): Embeddings (Phase 2B)
- **Vercel/Railway**: Hosting for dashboard & API
- **PostgreSQL**: Production database
- **GitHub Actions**: CI/CD pipeline

### Technology Stack

- **Backend**: Python 3.10+, FastAPI, Pydantic, SQLAlchemy
- **MCP Server**: Node.js 18+, TypeScript
- **Dashboard**: Next.js 14+, React, Tailwind CSS
- **Database**: SQLite (dev), PostgreSQL (prod), pgvector (Phase 2B)
- **Deployment**: Docker, docker-compose
- **Testing**: pytest, unittest, jest
- **Monitoring**: Sentry (errors), Posthog (analytics)

---

## Open Questions

### For Phase 1A

- [ ] Should we use SQLite or PostgreSQL for API persistence?
  - **Recommendation**: SQLite for Phase 1A (simplicity), PostgreSQL for Phase 2A (production)
- [ ] Should API keys be in database or separate key-value store?
  - **Recommendation**: Database for Phase 1A, Redis for Phase 2A (caching)
- [ ] How to handle API versioning?
  - **Recommendation**: `/v1/` prefix, maintain backward compatibility

### For Phase 1B

- [ ] Which MCP SDK version to use?
  - **Recommendation**: Latest stable from @modelcontextprotocol/sdk
- [ ] Should MCP server be in same repo or separate?
  - **Recommendation**: Separate repo for independent versioning

### For Phase 2A

- [ ] Self-host Whop dashboard or use Whop's built-in?
  - **Recommendation**: Self-host for max control, use Whop iframe for payments
- [ ] How to handle offline license validation?
  - **Recommendation**: Signed JWT tokens with 30-day offline grace period

---

## Communication Plan

### Documentation Updates

- Update `README.md` after each phase
- Create migration guides for breaking changes
- Maintain CHANGELOG.md
- Update all design docs to reflect implementation

### Community Engagement

- Tweet progress updates
- Write blog posts for each phase
- Create demo videos
- Engage in Reddit/HN discussions
- Build Discord community

### User Onboarding

- Quick start guide for each interface (CLI, API, MCP)
- Video tutorials
- Example projects
- Migration guides from v2.0.1

---

## Timeline Summary

| Phase | Duration | Start | End | Status |
|-------|----------|-------|-----|--------|
| **Foundation** | 4 weeks | Oct 1 | Nov 1 | ✅ COMPLETE |
| **Phase 1A** | 1 week | Nov 1 | Nov 8 | 🚧 IN PROGRESS |
| **Phase 1B** | 4 days | Nov 8 | Nov 12 | ⏳ PENDING |
| **Phase 2A** | 1 week | Nov 12 | Nov 19 | ⏳ PENDING |
| **Phase 2B** | 1 week | Nov 19 | Nov 26 | ⏳ PENDING |
| **Phase 3** | 2 weeks | Nov 26 | Dec 10 | ⏳ PENDING |

**Total**: ~6 weeks from v2.0.1 to full product launch

---

## ✅ v2.1.3 Complete (November 12, 2025)

**Major Achievements**:
- ✅ Production REST API with auth, quotas, rate limits
- ✅ MCP server with 27 tests passing
- ✅ 196 Python tests passing
- ✅ Docker Compose setup
- ✅ Security hardening (exec API, version management)
- ✅ Documentation cleanup
- ✅ Independent review fixes applied

**Release Notes**: See `INDEPENDENT_REVIEW_FIXES_v2.1.3.md`

---

## 🚧 v2.1.4 In Progress (Target: December 6, 2025)

**Theme**: Developer Experience & SDK

### Week 1 (Nov 18-22)
- [ ] MCP CLI auto-setup helper (all IDE support)
- [ ] OpenAPI TypeScript client generation
- [ ] Commit post-release fixes (Docker V2, MCP noise)

### Week 2 (Nov 25-29)
- [ ] OpenAPI Python client generation
- [ ] Publish `@whitemagic/client` to npm
- [ ] Publish `whitemagic-client` to PyPI
- [ ] Basic usage dashboard in `/dashboard/account`

### Week 3 (Dec 2-6)
- [ ] Testing & bug fixes
- [ ] Documentation updates
- [ ] Release notes
- [ ] Tag v2.1.4 and deploy

**See**: `ROADMAP_v2.1.4_to_v3.0.md` for complete release plan through v3.0

---

## Next Immediate Actions

1. ✅ Create comprehensive roadmap (`ROADMAP_v2.1.4_to_v3.0.md`)
2. ⏳ Commit post-release fixes to v2.1.4 branch
3. ⏳ Start MCP CLI auto-setup implementation
4. ⏳ Set up client generation pipeline

---

**Maintained by**: WhiteMagic Team (3 developers)  
**Last Updated**: November 12, 2025  
**Review Cadence**: Weekly during active development
