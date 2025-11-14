# WhiteMagic Strategic Roadmap v2.1.4 → v3.0

**Last Updated**: November 12, 2025  
**Team**: 3 developers  
**Timeline**: November 2025 → May 2026 (6 months)  
**Status**: Foundation complete (v2.1.3 shipped ✅)

---

## Vision Statement

**WhiteMagic = Memory Infrastructure for AI Agents & Developers**

- **Core Value**: Drop-in memory system with zero-config setup
- **Business Model**: API-as-a-service with usage-based tiered pricing
- **Target Path**: AI Agents → Indie Devs → Teams → Enterprise
- **Differentiation**: Graph-based memory + MCP-native + provider flexibility + self-hostable

---

## Market Position

### Competitive Landscape
- **Mem.ai**: Personal AI ($30M funding) - No API, mobile-first
- **Reflect**: Note-taking + AI - Not agent-focused
- **Pinecone/Weaviate**: Vector DBs - Too low-level
- **LangChain/CrewAI**: Agent frameworks - No hosted memory layer

### WhiteMagic's Unique Position (Blue Ocean)
✅ **Agent-first** (not human note-taking)  
✅ **API-as-a-service** (not just SDK)  
✅ **Tiered memory** (short/long/context)  
✅ **MCP native** (Anthropic ecosystem)  
✅ **Self-hostable** (privacy/enterprise)

**No direct competitor** for "memory infrastructure for AI agents as a service"

---

## Release Schedule

```
Nov 2025  Dec 2025  Jan 2026  Feb 2026  Mar 2026  Apr 2026  May 2026
   |         |         |         |         |         |         |
   v2.1.3    v2.1.4    v2.2.0    v2.3.0    v2.4.0    v3.0.0
   (DONE)    ↓         ↓         ↓         ↓         ↓
           DX+SDK    Agent     GitHub   Teams    Multi-
                    Powers    +VSCode            modal
                    
           v2.1.5    v2.2.5
           ↓         ↓
         Money    Providers
```

---

## v2.1.4 - "Developer Experience & SDK" 
**Timeline**: 2-3 weeks (Nov 18 - Dec 6, 2025)  
**Theme**: Make integration effortless

### Features

#### 1. MCP CLI Auto-Setup Helper ⭐
**Goal**: One command to configure any MCP-compatible IDE

```bash
npx whitemagic-mcp setup
# Auto-detects: Cursor, Windsurf, Claude Desktop, Cline, any MCP client
# Prompts: API key, WM_BASE_PATH
# Writes: Config JSON to correct location
# Tests: Connection and validates setup
```

**Effort**: 1 week  
**Impact**: 10x faster onboarding, reduces support load  
**Files**: `whitemagic-mcp/src/cli/setup.ts`

#### 2. OpenAPI Client Generation (TypeScript + Python) ⭐
**Goal**: Official SDKs for both primary languages

**TypeScript**:
```bash
npm install @whitemagic/client
```

**Python**:
```bash
pip install whitemagic-client
```

Auto-generated from FastAPI schema, published to npm/PyPI.

**Effort**: 1 week  
**Impact**: Developer adoption, ecosystem growth  
**Files**: `scripts/generate_clients.py`, `clients/typescript/`, `clients/python/`

#### 3. Basic Usage Dashboard ⭐
**Goal**: Show users their quota/usage in real-time

- Dashboard page: `/dashboard/account`
- Display: API calls (RPM, daily), memory count, storage used
- Simple charts: Last 7 days usage
- Current plan display

**Effort**: 0.5 weeks  
**Impact**: Value visibility, upgrade awareness  
**Files**: `dashboard/account.html`, `dashboard/app.js`

#### 4. Post-Release Fixes (Already Done)
- Docker Compose V2 auto-detection
- MCP test noise suppression

### Success Metrics
- Setup time < 2 minutes
- 50% reduction in setup support tickets
- SDK downloads > 100/week

**Release Target**: December 6, 2025

---

## v2.1.5 - "Monetization Foundation"
**Timeline**: 2-3 weeks (Dec 9 - Dec 27, 2025)  
**Theme**: Get billing/usage infrastructure solid

### Features

#### 1. Full Usage Dashboard
- Real-time quota meters (RPM, daily quota, storage, embeddings)
- Historical usage charts (7/30/90 days)
- Plan comparison widget with upgrade CTAs
- Export usage data (CSV)

**Effort**: 1.5 weeks

#### 2. Tiered Feature Toggles
```python
PLAN_FEATURES = {
    "free": ["basic_memory"],
    "starter": ["basic_memory", "semantic_search"],
    "pro": ["basic_memory", "semantic_search", "exec_api", "webhooks"],
    "enterprise": ["all"]
}
```

- Backend enforcement in middleware
- Whop metadata → feature flags
- Graceful degradation with upgrade prompts

**Effort**: 1 week

#### 3. Whop Integration
- Sync plans from Whop API
- Webhook handlers for plan changes
- User portal link for billing management

**Effort**: 0.5 weeks

#### 4. Usage Alerts
- Email when 80% quota used
- Webhook support for custom alerting
- Dashboard notifications

**Effort**: 0.5 weeks

### Success Metrics
- Free → Paid conversion rate
- Average Revenue Per User (ARPU)
- Upgrade rate after hitting limits

**Release Target**: December 27, 2025

---

## v2.2.0 - "Agent Superpowers"
**Timeline**: 3-4 weeks (Jan 6 - Jan 31, 2026)  
**Theme**: Features that make AI agents dramatically more capable

### Features

#### 1. Memory Relationships/Graph ⭐⭐
**Goal**: Transform from storage to knowledge system

```python
POST /api/v1/memories/{id}/relationships
{
  "target_id": "uuid",
  "type": "references|contradicts|follows_up|related",
  "strength": 0.85  # Auto-calculated from embeddings
}

GET /api/v1/memories/{id}/graph?depth=2
# Returns memory + related memories up to 2 hops
```

- Auto-detect relationships via embedding similarity
- Manual relationship creation
- Graph visualization in dashboard
- Graph-based context generation

**Effort**: 2 weeks  
**Impact**: Unique differentiator, "AI reasoning" foundation

#### 2. Semantic Collections
**Goal**: Isolated memory contexts per project/client

```python
POST /api/v1/collections
{
  "name": "Project Apollo",
  "description": "Client work for Apollo Inc",
  "tags": ["client", "apollo"]
}

GET /api/v1/search?collection_id={id}&query="authentication"
# Scoped search within collection only
```

- Named collections with metadata
- Collection-level permissions
- Scoped search and context generation
- Perfect for agencies/multi-project teams

**Effort**: 1.5 weeks  
**Impact**: Enterprise use case, agent isolation

#### 3. Smart Consolidation
**Goal**: Auto-pilot memory management

- Auto-summarize old short-term → long-term
- Detect duplicates via embeddings → merge
- Archive low-value memories (never accessed)
- Weekly memory health reports

**Effort**: 1 week  
**Impact**: Reduces cognitive load, shows intelligence

#### 4. Automation Hooks (Webhooks)
**Goal**: Integration ecosystem

```python
POST /api/v1/webhooks
{
  "url": "https://your-app.com/webhook",
  "events": ["memory.created", "memory.consolidated"],
  "secret": "signing_key"
}
```

- Outbound webhooks for events
- Zapier integration template
- Webhook signing for security

**Effort**: 1 week  
**Impact**: Enterprise integrations, ecosystem

### Success Metrics
- Agent retention (7-day, 30-day)
- Graph query usage
- Collection adoption rate
- Webhook integrations

**Release Target**: January 31, 2026

---

## v2.2.5 - "Self-Hosting & Providers"
**Timeline**: 2 weeks (Feb 3 - Feb 14, 2026)  
**Theme**: Flexibility for privacy and cost optimization

### Features

#### 1. Embeddings Provider Matrix
- Support: OpenAI, Cohere, Ollama, local models
- Per-provider caching
- Dashboard UI to switch providers
- Cost comparison dashboard

**Effort**: 1.5 weeks

#### 2. Self-Hosted Improvements
- Improved Docker setup docs
- Kubernetes Helm chart
- Air-gapped mode (no external API calls)
- Migration tools (cloud → self-hosted)

**Effort**: 0.5 weeks

### Success Metrics
- Self-hosted installations
- Ollama/local model adoption
- Provider diversity

**Release Target**: February 14, 2026

---

## v2.3.0 - "GitHub & Developer Ecosystem"
**Timeline**: 3-4 weeks (Feb 17 - Mar 14, 2026)  
**Theme**: Tap into developer market, viral distribution

### Features

#### 1. GitHub Integration ⭐⭐
**Goal**: Auto-create memories from development workflow

- GitHub App: Auto-memory from PRs, commits, issues
- Link memories to specific code/files
- "Memory this PR" button
- Search memories by repo/branch

**Effort**: 2 weeks  
**Impact**: Developer market, viral potential

#### 2. VS Code Extension
**Goal**: Daily usage in developer's IDE

- Sidebar memory browser (CRUD operations)
- Inline memory suggestions (context-aware)
- Right-click "Save as memory"
- Auto-tag by file/project
- Search memories without leaving IDE

**Effort**: 2 weeks  
**Impact**: Distribution channel, daily engagement

#### 3. Official SDKs (Enhanced)
- Feature-complete Python/TypeScript SDKs
- Framework integrations (LangChain, CrewAI, AutoGPT)
- Streaming API support
- Comprehensive examples

**Effort**: 1 week  
**Impact**: Ecosystem lock-in

### Success Metrics
- GitHub App installs
- VS Code extension downloads
- SDK package downloads
- Developer community growth

**Release Target**: March 14, 2026

---

## v2.4.0 - "Team Collaboration"
**Timeline**: 4-5 weeks (Mar 17 - Apr 18, 2026)  
**Theme**: Enterprise features, 10x revenue potential

### Features

#### 1. Team Workspaces ⭐⭐
**Goal**: Shared memory for teams

- Shared memory pools per workspace
- Role-based access (viewer, editor, admin, owner)
- Team-wide context generation
- Workspace-level quotas
- Member management UI

**Effort**: 3 weeks  
**Impact**: 10x revenue per customer (team vs individual)

#### 2. Audit Logs
**Goal**: Compliance and security

- Who accessed/modified what
- Exportable audit trail
- GDPR compliance features
- SOC2 preparation

**Effort**: 1 week  
**Impact**: Enterprise sales requirement

#### 3. Usage-Based Billing (Enterprise)
- Pay-per-API-call option
- Storage pricing ($/GB/month)
- Custom contracts
- Invoice generation

**Effort**: 1 week  
**Impact**: Enterprise revenue scale

### Success Metrics
- Team signups
- Average seats per team
- Enterprise deal size
- Multi-seat revenue

**Release Target**: April 18, 2026

---

## v3.0.0 - "Multi-Modal & Intelligence"
**Timeline**: 6-8 weeks (Apr 21 - Jun 6, 2026)  
**Theme**: Next-generation capabilities, market leadership

### Features

#### 1. Multi-Modal Memory ⭐⭐⭐
**Goal**: Beyond text - images, PDFs, audio

- Image upload → OCR + embeddings (screenshots, diagrams)
- PDF ingestion → chunk + embed
- Audio transcription → memory (meeting recordings)
- Visual memory browser with thumbnails
- Multi-modal search (find image by text description)

**Effort**: 3 weeks  
**Impact**: New use cases, premium pricing

#### 2. Advanced Memory Intelligence
**Goal**: AI-powered memory management

- Auto-tagging via LLM (analyze content, suggest tags)
- Memory quality scoring (completeness, clarity)
- Conflict detection (contradicting memories)
- Smart recommendations ("You should link these memories")

**Effort**: 2 weeks  
**Impact**: Shows true AI intelligence

#### 3. Memory Analytics Dashboard
- Most/least accessed memories
- Orphaned memories (no relationships)
- Growth trends over time
- Memory health score
- Embedding visualization (t-SNE/UMAP plot)

**Effort**: 1.5 weeks  
**Impact**: User engagement, insights

#### 4. Chrome Extension
- Save web research as memories
- Inline memory search on any page
- Highlight text → "Save as memory"
- Research assistant mode

**Effort**: 1.5 weeks  
**Impact**: Daily usage, research workflows

### Success Metrics
- Multi-modal adoption rate
- Premium feature usage
- User engagement time
- Market leadership recognition

**Release Target**: June 6, 2026

---

## Pricing Strategy (Launch with v2.1.5)

### Proposed Tiers

**Free** (Developers/Testing)
- 1,000 API calls/month
- 100 memories max
- OpenAI embeddings only
- Community support (Discord/GitHub)

**Starter** ($9/mo)
- 10,000 API calls/month
- 1,000 memories
- Semantic search
- Basic collections (3 max)
- Email support

**Pro** ($29/mo) ⭐ Target
- 100,000 API calls/month
- 10,000 memories
- All embedding providers
- Unlimited collections
- Webhooks (5 max)
- Graph relationships
- Priority support

**Team** ($99/mo)
- 500,000 API calls/month
- Unlimited memories
- Team workspace (5 seats)
- Exec API access
- Advanced analytics
- Unlimited webhooks
- Dedicated support

**Enterprise** (Custom pricing)
- Unlimited everything
- Custom SLA
- Self-hosted option
- White-label
- Custom integrations
- Account manager

**Overages**: 
- $0.01 per 100 API calls
- $1/GB storage/month
- $5/additional team seat

---

## Success Metrics by Phase

### Phase 1: Foundation (v2.1.4 - v2.2.0)
- Monthly Active Users (MAU): 1,000+
- Setup time: < 2 minutes
- Free → Starter conversion: 5%
- Starter → Pro conversion: 10%

### Phase 2: Ecosystem (v2.2.5 - v2.3.0)
- MAU: 5,000+
- GitHub App installs: 500+
- VS Code downloads: 1,000+
- SDK downloads: 5,000+/month

### Phase 3: Enterprise (v2.4.0)
- MAU: 10,000+
- Team accounts: 100+
- Average deal size: $500/mo
- MRR: $50,000+

### Phase 4: Innovation (v3.0.0)
- MAU: 25,000+
- Premium features adoption: 60%
- Multi-modal usage: 40%
- Market leadership position

---

## Technical Architecture Evolution

### v2.1.4 Additions
- CLI tooling (setup wizard)
- Client generators (OpenAPI → SDKs)
- Basic dashboard enhancements

### v2.2.0 Additions
- Graph database (memory relationships)
- Collection scoping (namespace isolation)
- Webhook infrastructure

### v2.3.0 Additions
- GitHub OAuth & webhooks
- VS Code extension backend APIs
- Enhanced SDK features

### v2.4.0 Additions
- Multi-tenancy (workspaces)
- RBAC (role-based access control)
- Audit logging system

### v3.0.0 Additions
- Multi-modal storage (S3/blob)
- OCR pipeline
- Transcription service
- Advanced analytics backend

---

## Risk Mitigation

### Technical Risks
- **Embedding costs**: Mitigate with local providers (Ollama)
- **Storage scaling**: Implement tiered storage, compression
- **API latency**: Add caching, CDN, read replicas

### Business Risks
- **Competitor launch**: First-mover advantage, build moat with features
- **Low conversion**: Free tier limits, clear upgrade path, value demos
- **Churn**: Engagement features, integrations, team lock-in

### Resource Risks
- **3-person team**: Prioritize ruthlessly, automate testing, clear scope
- **Timeline slips**: Buffer weeks, MVP mindset, ship iteratively

---

## Next Steps (This Week)

1. ✅ Commit post-release fixes (Docker V2, MCP noise)
2. ✅ Create this roadmap document
3. ✅ Update main ROADMAP.md to reference this
4. 🚧 Branch for v2.1.4 development
5. 🚧 Start MCP CLI auto-setup helper

---

## Document Updates

This roadmap should be reviewed and updated:
- **Weekly**: Progress tracking, blockers
- **End of each release**: Retrospective, metrics review
- **Quarterly**: Strategy adjustment based on market

**Next Review**: December 6, 2025 (v2.1.4 release)

---

**Prepared by**: AI Strategy Team  
**Approved by**: Lucas Bailey  
**Version**: 1.0  
**Date**: November 12, 2025
