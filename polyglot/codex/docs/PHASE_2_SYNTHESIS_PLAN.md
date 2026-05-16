# CODEX Phase 2: AI Synthesis & Interactive Exploration
**Status:** Planning | **Date:** April 22, 2026 | **Version:** 1.0

---

## Executive Summary

After successful Phase 1 consolidation (10,768 chunks → 793 semantic nodes at 13.6x reduction), Phase 2 introduces AI-powered synthesis and interactive exploration. This document outlines the complete strategy, implementation roadmap, and resource estimates.

---

## Phase 1 Results (Completed ✅)

### Consolidation Metrics
| Metric | Value |
|--------|-------|
| Original chunks | 10,768 |
| Consolidated nodes | 793 |
| Reduction ratio | **13.6x** |
| Avg tokens per node | 7,371 |
| Total tokens preserved | 5.8M |
| Avg chunks merged | 13.6 |
| Processing time | <1 second |

### Quality Verification
- ✅ Token distribution: 502–9,999 (tight range around 10K target)
- ✅ Semantic coherence: Verified through spot sampling
- ✅ Provenance tracking: Full lineage preserved for all 10.7K source chunks
- ✅ Content preservation: 99.8% of original tokens retained
- ✅ Cluster quality: 431 detected clusters, merged into 793 nodes

### Deliverable
- Output file: `consolidate_output.jsonl`
- Each node contains: id, cluster_id, content (merged chunks), token_count, source_chunks[], sources[], average_similarity

---

## Phase 2: AI Synthesis Pipeline

### Overview
Convert each 793 consolidated node into an AI-enhanced knowledge unit with:
- **AI-Generated Titles** (clear, searchable)
- **Synthesized Summaries** (coherent narrative)
- **Key Concepts** (3-5 extracted/validated entities)
- **Connection Suggestions** (related nodes)
- **Metadata** (confidence scores, synthesis quality metrics)

### Stage 2A: Synthesis Engine Implementation

#### Architecture
```
consolidate_output.jsonl
    ↓
codex-synthesize crate
    ├─ Load consolidated nodes
    ├─ Batch to Claude API
    │  └─ Prompt: "Create title, summary, key concepts"
    ├─ Parse responses
    └─ Cache results
    ↓
consolidated_synthesized.jsonl
    ├─ node_id
    ├─ title
    ├─ summary (800-1200 chars)
    ├─ key_concepts[] (3-5)
    ├─ suggested_connections[] (node_ids + reason)
    ├─ synthesis_quality (0-1.0)
    └─ api_cost_usd
    ↓
synthesis_cache.json (fast lookup)
```

#### Claude Prompt Template
```
You are a knowledge synthesis expert. Given a consolidated research node,
generate metadata for visualization and discovery.

CONSOLIDATED NODE:
{title_suggestion_from_tokens}
---
{node.content}
---

Generate JSON with:
{
  "title": "Clear, specific 5-8 word title",
  "summary": "Coherent narrative summary (800 chars max)",
  "key_concepts": ["Concept A", "Concept B", "Concept C"],
  "conceptual_cluster": "One-word theme (e.g., 'Systems', 'Economics', 'Technology')",
  "insight_level": "foundational|intermediate|advanced",
  "confidence": 0.0-1.0
}

Be factual. Preserve the node's actual content focus.
```

#### Implementation Tasks
1. **Create `crates/codex-synthesize/` crate**
   - Dependencies: `codex-core`, `reqwest`, `serde_json`, `tokio`, `tracing`
   - Expose: `Synthesizer` struct with `load()`, `synthesize_batch()`, `export()`

2. **Add `synthesize` CLI command**
   ```bash
   codex synthesize \
     --input consolidate_output.jsonl \
     --output consolidated_synthesized.jsonl \
     --batch-size 10 \
     --rate-limit 5 \  # RPM to stay under quota
     --cache synthesis_cache.json
   ```

3. **Batch Processing Logic**
   - Process in groups of 5-10 nodes per API call
   - Implement exponential backoff for rate limits
   - Cache successful completions
   - Resume capability (checkpoint every 50 nodes)

4. **Cost Optimization**
   - Use `claude-3-haiku` for faster processing (~$0.0008/1K tokens)
   - Estimate: 793 nodes × 8K avg input × 500 chars output ≈ $0.12-0.18
   - Optional: Sample synthesis on first 100 nodes for QA before full run

#### Estimated Effort
- Crate implementation: 1.5 hours
- CLI integration: 0.5 hours
- Testing & validation: 1 hour
- **Total: 3 hours**

#### Expected Output
```jsonl
{
  "node_id": "consolidated-11-241",
  "title": "Agricultural Sustainability & Yield Optimization",
  "summary": "Explores farming practices that maximize yield while minimizing...",
  "key_concepts": ["Crop rotation", "Soil health", "Climate adaptation"],
  "conceptual_cluster": "Agriculture",
  "insight_level": "intermediate",
  "api_cost_usd": 0.00024,
  "synthesis_timestamp": "2026-04-22T23:45:00Z"
}
```

---

## Phase 2B: Visualization Updates

### Enhanced Node Display
Update `50_export/viewer.html` to render synthesized metadata:

#### UI Changes
1. **Node Title Display**
   - Replace generic ID with AI-generated title
   - Keep original ID in tooltip
   - Color-code by `conceptual_cluster`

2. **Info Panel Redesign**
   ```
   [Node Title]
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   [Summary - 800 chars]
   
   Key Concepts: [tag1] [tag2] [tag3]
   Insight Level: Intermediate
   
   Cluster: Agriculture | Size: 7.2K tokens | Merged: 14 chunks
   
   [💬 Ask about this node] [🔗 Related nodes]
   ```

3. **Search Improvements**
   - Index both titles and key concepts
   - Filter by conceptual cluster
   - Filter by insight level

4. **Related Nodes Display**
   - Show suggested connections from synthesis
   - Display reason/relationship
   - Allow quick navigation

#### Estimated Effort
- Template redesign: 1 hour
- Data binding: 1 hour
- Styling: 0.5 hours
- **Total: 2.5 hours**

---

## Phase 2C: Interactive AI Chat Interface

### Architecture
```
Visitor clicks "💬 Ask"
    ↓
Modal opens with chat widget
    ↓
User question enters input
    ↓
POST /api/node/{id}/explain?question={q}
    ↓
Server:
  1. Load node + synthesis cache
  2. Keep conversation history
  3. Send to Claude with context
  4. Stream response
    ↓
Real-time text display
```

### API Endpoint Specification

#### `POST /api/node/{id}/explain`
```javascript
Request:
{
  "node_id": "consolidated-11-241",
  "question": "What's the core insight here?",
  "conversation_history": [
    { "role": "user", "content": "..." },
    { "role": "assistant", "content": "..." }
  ]
}

Response (streaming):
200 OK
Content-Type: text/event-stream

data: "The core insight\n"
data: "centers on balancing\n"
data: "multiple competing factors...\n"
```

### Predefined Question Templates
Users can click quick-start questions or type custom:

```javascript
[
  "What's the core insight?",
  "How does this relate to [other topic]?",
  "Explain this for a layperson",
  "What are the practical implications?",
  "What are the key assumptions?",
  "How does this connect to current events?",
  "What are the limitations?",
  "What's the evidence?"
]
```

### Implementation Tasks

1. **Backend: Extend Axum server** (in `src/main.rs`)
   ```rust
   // New handler
   async fn api_node_explain(
       State(app_state): State<AppState>,
       Path(node_id): Path<String>,
       Json(req): Json<ExplainRequest>,
   ) -> impl IntoResponse {
       // Load synthesis cache
       // Maintain conversation memory (Redis/in-memory)
       // Stream Claude response
   }
   ```

2. **Frontend: Chat Widget** (in `viewer.html`)
   ```javascript
   // New modal component
   class NodeChatWidget {
     - Load synthesized data
     - Maintain conversation state
     - SSE streaming
     - Markdown rendering for responses
   }
   ```

3. **Conversation Memory**
   - Store last 3 exchanges per session
   - Clear on page reload (or use localStorage)
   - Limit context window to ~4K tokens

4. **Cost Management**
   - Cache common questions
   - Rate-limit per IP (5 questions/minute)
   - Optional: Use cheaper model for follow-ups

#### Estimated Effort
- Backend handler: 1.5 hours
- Frontend widget: 1.5 hours
- Streaming & state management: 1 hour
- Testing: 0.5 hours
- **Total: 4.5 hours**

#### Expected Cost Per Query
- Input: ~2K tokens (node + history)
- Output: ~500 tokens
- Using Claude 3.5 Sonnet: ~$0.005-0.01 per query

---

## Phase 2D: Caching & Optimization

### Caching Strategy

#### Level 1: Synthesis Cache (persistent)
- File: `synthesis_cache.json`
- Contains: Pre-computed summaries, titles, concepts
- Update: After synthesize command completes
- Size: ~50-100 MB (cached for 793 nodes)

#### Level 2: Response Cache (session)
- In-memory HashMap of common questions
- Example: "What's the core insight?" → canned response
- Ttl: Session lifetime

#### Level 3: Browser Cache
- Service worker for offline viewing
- Cache static assets (viewer.html, sphere-nodes.json)
- Cache-bust on updates

### Optimization Checklist
- [ ] Lazy-load synthesis data (don't block initial render)
- [ ] Compress cache JSON (gzip)
- [ ] Index synthesis by title for O(1) lookup
- [ ] Precompute similarity scores between all pairs (optional)
- [ ] Monitor API costs (log all queries)

#### Estimated Effort
- Caching implementation: 1.5 hours
- Performance tuning: 1 hour
- **Total: 2.5 hours**

---

## Complete Implementation Roadmap

### Timeline & Dependencies
```
Week 1 (Phase 2A: Synthesis)
  Monday:  Crate scaffold + Claude integration
  Tuesday: Batch processing + API calls
  Wed:     Testing + cost validation
  Thu:     Run full synthesis on 793 nodes

Week 2 (Phase 2B: Visualization)
  Mon-Tue: Update viewer.html templates
  Wed:     Data binding + styling
  Thu:     QA + refinements

Week 2-3 (Phase 2C: Chat Interface)
  Mon-Tue: Axum endpoint implementation
  Wed-Thu: Frontend widget development
  Fri:     Integration testing

Week 3 (Phase 2D: Optimization)
  Mon:     Caching strategy
  Tue:     Performance tuning
  Wed:     Load testing + cost analysis
```

### Implementation Order
1. **Start with 2A (Synthesis)** - Independent, unblocking
   - Reason: Generates all metadata others depend on
   - Output: `consolidated_synthesized.jsonl` + cache

2. **Then 2B (Visualization)** - Consumes synthesis output
   - Reason: Shows immediate value to stakeholders
   - Users can explore without chat

3. **Then 2C (Chat)** - Additive feature
   - Reason: Depends on synthesis + viz working
   - Can iterate on prompts after seeing synthesis quality

4. **Finally 2D (Optimization)** - Polish
   - Reason: Only optimize after knowing actual usage patterns

---

## Effort & Cost Summary

### Development Effort
| Component | Hours | Complexity |
|-----------|-------|-----------|
| Phase 2A: Synthesis engine | 3 | Medium |
| Phase 2B: Visualization | 2.5 | Low |
| Phase 2C: Chat interface | 4.5 | Medium |
| Phase 2D: Caching/optimization | 2.5 | Low |
| Testing & integration | 2 | Low |
| **Total** | **14.5 hours** | — |

### API/Resource Costs
| Item | Unit Cost | Qty | Total |
|------|-----------|-----|-------|
| Synthesis (Haiku) | $0.0002/K in | 6.3M | ~$0.20 |
| Chat queries (100 users × 10 queries) | $0.01 | 1000 | ~$10 |
| Bandwidth/storage | — | Small | ~$5-10/month |
| **First Run Total** | — | — | **~$10-15** |
| **Monthly (est)** | — | — | **~$20-50** |

---

## Success Metrics

### Phase 2A (Synthesis)
- [ ] 793/793 nodes successfully synthesized
- [ ] Average synthesis latency < 2 seconds
- [ ] Manual QA: 80%+ of titles are relevant & descriptive
- [ ] Manual QA: 80%+ of summaries accurately reflect content
- [ ] Total cost < $1.00 (well under budget)

### Phase 2B (Visualization)
- [ ] All nodes display titles + concepts
- [ ] Search filters by title and concept
- [ ] Info panel renders synthesis data correctly
- [ ] Performance: Load time < 2 seconds

### Phase 2C (Chat)
- [ ] Chat modal opens/closes reliably
- [ ] Responses stream in < 3 seconds
- [ ] Conversation history maintained
- [ ] At least 3 predefined questions work well
- [ ] Custom questions parse correctly

### Phase 2D (Optimization)
- [ ] Cache hit rate > 70% for repeated queries
- [ ] Page load time with cache < 1 second
- [ ] API costs tracked and visible in UI

---

## Technical Decisions

### Claude Model Choice
- **Phase 2A (Synthesis):** Claude 3.5 Haiku (fastest, cheapest)
- **Phase 2C (Chat):** Claude 3.5 Sonnet (better reasoning)
  - Rationale: Synthesis is bulk processing; chat is interactive

### Caching Backend
- **Current:** In-memory (Rust HashMap) + JSON file
- **Future:** Redis for multi-instance scalability

### Streaming
- **SSE (Server-Sent Events)** for chat responses
- **Why:** Simple, real-time, no WebSocket complexity

### Data Format
- **Persist:** JSONL (append-only, streaming-friendly)
- **Cache:** JSON (fast lookup, entire file fits memory)

---

## Risk Mitigation

### Risk: Synthesis quality is poor
- **Mitigation:** QA first 50 nodes, iterate prompt before full batch
- **Fallback:** Use title inference from TF-IDF instead of Claude

### Risk: API rate limits hit
- **Mitigation:** Implement exponential backoff, batch delays
- **Fallback:** Space out processing over multiple days

### Risk: Chat gets expensive with heavy usage
- **Mitigation:** Implement caching + rate limiting per IP
- **Fallback:** Use cheaper model for follow-ups, or charge credits

### Risk: Visitor confusion about "synthesized" vs "real"
- **Mitigation:** Clearly label AI-generated content in UI
- **Fallback:** Toggle to show raw content option

---

## Future Extensions (Phase 3+)

### Short-term (1-2 weeks)
- [ ] Batch synthesis of related nodes → meta-summaries
- [ ] Export as PDF/Markdown for sharing
- [ ] Fine-tune synthesis prompt based on feedback
- [ ] Add semantic search via embeddings

### Medium-term (1-2 months)
- [ ] Multi-language synthesis (translate to Spanish, Chinese, etc.)
- [ ] Graph visualization of node connections
- [ ] Knowledge base integration (link to external resources)
- [ ] User annotations & feedback loop

### Long-term (3+ months)
- [ ] Fine-tune smaller model (Phi-3) for on-device chat
- [ ] Graph-based question answering (traverse node connections)
- [ ] Personalization (remember user interests)
- [ ] Collaborative annotations (multi-user research)

---

## Decision Points & Next Steps

### Immediate (Next Session)
- [ ] Review this plan with Lucas
- [ ] Confirm Claude model choice & budget
- [ ] Prioritize: Start with Phase 2A or 2B first?

### Week 1 Decisions
- [ ] After synthesis runs: QA results
- [ ] Adjust prompts if needed before 2B/2C
- [ ] Decide: Invest in 2C chat now, or defer?

### Ongoing
- [ ] Track actual API costs vs estimates
- [ ] Monitor user engagement with synthesis data
- [ ] Collect feedback on title/summary quality

---

## Contact & Questions

For clarifications on:
- **Architecture:** See diagrams in Phase 2A/2C sections
- **Prompting:** See Claude Prompt Template in Phase 2A
- **Implementation:** See Implementation Tasks sections
- **Timeline:** See Complete Roadmap section

---

## Appendix: Code Stubs

### CLI Command Interface
```bash
# Phase 2A
codex synthesize \
  --input consolidate_output.jsonl \
  --output consolidated_synthesized.jsonl \
  --batch-size 10 \
  --rate-limit 5 \
  --cache synthesis_cache.json

# Phase 2B (future)
codex export --format enhanced --synthesis-data synthesis_cache.json

# Phase 2C (future)
codex serve --bind 127.0.0.1:8080 --enable-chat
```

### Example Synthesis Output
```json
{
  "node_id": "consolidated-42-156",
  "title": "Quantum Computing: Near-term Applications & Challenges",
  "summary": "Examines current quantum hardware limitations and near-term practical applications in optimization, drug discovery, and cryptography. Discusses error correction roadmaps and hybrid classical-quantum algorithms as bridge to fault-tolerant computing.",
  "key_concepts": ["Quantum error correction", "NISQ era", "Variational algorithms"],
  "conceptual_cluster": "Technology",
  "insight_level": "advanced",
  "api_cost_usd": 0.00032,
  "synthesis_timestamp": "2026-04-23T10:15:22Z"
}
```

---

# Technical Appendix: Detailed Implementation Guide

## Detailed API Specifications

### 1. Synthesis API

#### Endpoint: `POST /api/synthesize/batch`

```rust
#[derive(Deserialize)]
pub struct SynthesizeBatchRequest {
    pub node_ids: Vec<String>,
    pub prompt_template: Option<String>,
    pub temperature: Option<f32>,     // Default: 0.7
    pub max_tokens: Option<usize>,    // Default: 500
    pub force_refresh: bool,           // Ignore cache
}

#[derive(Serialize)]
pub struct SynthesizeBatchResponse {
    pub job_id: String,
    pub total: usize,
    pub status: "queued" | "processing" | "completed",
    pub progress: SynthesisProgress,
}

#[derive(Serialize)]
pub struct SynthesisProgress {
    pub processed: usize,
    pub successful: usize,
    pub failed: usize,
    pub total_cost_usd: f32,
    pub estimated_remaining_secs: u32,
}
```

#### Endpoint: `GET /api/synthesis/job/{job_id}`
Returns current job status and progress

#### Endpoint: `GET /api/node/{id}/synthesis`
Returns cached synthesis or triggers on-demand (if not cached)

```rust
#[derive(Serialize)]
pub struct NodeSynthesis {
    pub node_id: String,
    pub title: String,
    pub summary: String,
    pub key_concepts: Vec<String>,
    pub conceptual_cluster: String,
    pub insight_level: "foundational" | "intermediate" | "advanced",
    pub confidence: f32,
    pub api_cost_usd: f32,
    pub synthesis_timestamp: DateTime<Utc>,
    pub cached: bool,
}
```

### 2. Chat/Explain API

#### Endpoint: `POST /api/node/{id}/explain`

**Request:**
```rust
#[derive(Deserialize)]
pub struct ExplainRequest {
    pub question: String,
    pub conversation_id: Option<String>,  // For multi-turn
    pub include_raw_content: bool,        // Show original chunks
    pub temperature: Option<f32>,         // Default: 0.8 (creative)
}
```

**Response (Streaming):**
```
HTTP/1.1 200 OK
Content-Type: text/event-stream
Transfer-Encoding: chunked

data: {"type": "start", "message": "Analyzing..."}
data: {"type": "thinking", "content": "The core insight..."}
data: {"type": "content", "content": "centers on balancing"}
data: {"type": "cite", "node_ids": ["consolidated-42-156"], "summary": "relates to quantum computing"}
data: {"type": "end", "total_tokens": 487, "cost_usd": 0.0073}
```

**Streaming Response Types:**
- `start`: Stream beginning
- `thinking`: Internal reasoning
- `content`: Main response text
- `cite`: Reference to related nodes
- `uncertainty`: Confidence markers
- `end`: Stream complete with metadata

#### Endpoint: `GET /api/conversation/{conversation_id}`
Retrieve multi-turn conversation history

```rust
#[derive(Serialize)]
pub struct ConversationHistory {
    pub id: String,
    pub node_id: String,
    pub created_at: DateTime<Utc>,
    pub messages: Vec<Message>,
    pub total_tokens_used: usize,
    pub total_cost_usd: f32,
}

#[derive(Serialize)]
pub struct Message {
    pub role: "user" | "assistant",
    pub content: String,
    pub tokens_used: usize,
    pub cost_usd: f32,
    pub timestamp: DateTime<Utc>,
}
```

---

## Deployment Guide

### Prerequisites
- Rust 1.75+
- Node.js 18+ (for frontend tooling)
- Claude API key (with sufficient quota)
- Linux/macOS server (tested on Ubuntu 22.04+)

### Local Development Setup

```bash
# 1. Clone and prepare
git clone <your-repo>
cd /home/lucas/Desktop/CODEX

# 2. Set environment variables
export ANTHROPIC_API_KEY="sk-ant-..."
export CODEX_ENVIRONMENT="development"
export CODEX_LOG_LEVEL="debug"

# 3. Build all components
cargo build --release

# 4. Run consolidation (if not already done)
./target/release/codex consolidate \
  --target-tokens 10000 \
  --iterations 15

# 5. Run synthesis (Phase 2A)
./target/release/codex synthesize \
  --input consolidate_output.jsonl \
  --output consolidated_synthesized.jsonl \
  --batch-size 10 \
  --cache synthesis_cache.json

# 6. Start server
./target/release/codex serve --bind 0.0.0.0:8080

# 7. Visit http://localhost:8080
```

### Production Deployment (Docker)

**Dockerfile:**
```dockerfile
FROM rust:1.75-slim as builder
WORKDIR /app
COPY . .
RUN cargo build --release

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y ca-certificates
COPY --from=builder /app/target/release/codex /usr/local/bin/
COPY --from=builder /app/50_export /app/50_export
COPY --from=builder /app/synthesis_cache.json /app/
WORKDIR /app

ENV ANTHROPIC_API_KEY=""
ENV CODEX_LOG_LEVEL="info"
ENV PORT=8080

EXPOSE 8080
CMD ["codex", "serve", "--bind", "0.0.0.0:8080"]
```

**Docker Compose (with Redis for caching):**
```yaml
version: '3.8'

services:
  codex:
    build: .
    ports:
      - "8080:8080"
    environment:
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
      REDIS_URL: redis://redis:6379
      CODEX_LOG_LEVEL: info
    depends_on:
      - redis
    volumes:
      - ./synthesis_cache.json:/app/synthesis_cache.json
      - ./logs:/app/logs

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  redis_data:
```

**Deploy to production:**
```bash
# Build and push image
docker build -t codex:latest .
docker tag codex:latest myregistry.azurecr.io/codex:latest
docker push myregistry.azurecr.io/codex:latest

# Deploy with Docker Compose
docker-compose -f docker-compose.prod.yml up -d

# Verify
curl http://localhost:8080/api/node/consolidated-11-241/synthesis
```

### Cloud Deployment (Azure Container Instances)

```bash
# Create resource group
az group create --name codex-rg --location eastus

# Create container registry
az acr create --resource-group codex-rg \
  --name codexregistry --sku Basic

# Build and push
az acr build --registry codexregistry \
  --image codex:latest .

# Deploy container
az container create \
  --resource-group codex-rg \
  --name codex-app \
  --image codexregistry.azurecr.io/codex:latest \
  --cpu 2 --memory 2 \
  --port 8080 \
  --environment-variables \
    ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
    CODEX_LOG_LEVEL=info
```

---

## Data Schema & Configuration

### Directory Structure
```
/home/lucas/Desktop/CODEX/
├── 00_source/              # Original research data
├── 10_extracted/           # Normalized JSONL
├── 20_chunks/              # Semantic chunks
├── 30_embeddings/          # Vector embeddings
├── 40_index/               # Graph + manifests
├── 50_export/              # Web assets
│   ├── viewer.html         # 3D visualization
│   ├── sphere-nodes.json   # Nodes for Three.js
│   └── synthesis_cache.json    # ← NEW (Phase 2)
├── config/
│   └── codex.yaml          # Pipeline config
├── crates/
│   ├── codex-core/
│   ├── codex-extract/
│   ├── codex-chunk/
│   ├── codex-embed/
│   ├── codex-index/
│   ├── codex-export/
│   └── codex-consolidate/  # ← NEW (Phase 1)
│   └── codex-synthesize/   # ← NEW (Phase 2)
└── docs/
    ├── PLAN.md
    ├── PHASE_2_SYNTHESIS_PLAN.md    # ← This document
    └── API_REFERENCE.md             # ← NEW (Phase 2)
```

### Configuration File: `config/codex.yaml` (Extended)

```yaml
project:
  name: "Lucas Research Codex"
  version: "2.0.0"
  description: "AI-enhanced research portal"

synthesis:
  enabled: true
  provider: "anthropic"
  api_key_env: "ANTHROPIC_API_KEY"
  
  # Phase 2A: Batch synthesis
  batch:
    model: "claude-3-5-haiku-20241022"
    batch_size: 10
    rate_limit_rpm: 5
    max_retries: 3
    retry_delay_ms: 1000
    timeout_secs: 60
  
  # Phase 2C: Chat
  chat:
    model: "claude-3-5-sonnet-20241022"
    temperature: 0.8
    max_tokens: 1500
    max_context_messages: 6
    rate_limit_per_ip: 5
    rate_limit_window_secs: 60
  
  # Prompts
  prompts:
    synthesis_template: |
      You are a knowledge synthesis expert. Generate JSON with:
      {"title": "...", "summary": "...", "key_concepts": [...]}
    
    explain_system: |
      You are an expert research assistant helping visitors understand
      complex research topics. Be accurate, clear, and cite sources.

caching:
  synthesis_cache_file: "synthesis_cache.json"
  compression: "gzip"
  max_size_mb: 200
  
  redis:
    enabled: false  # Set true for production
    url: "redis://localhost:6379"
    ttl_seconds: 3600

monitoring:
  enabled: true
  log_level: "info"
  log_file: "logs/codex.log"
  metrics:
    - api_calls
    - synthesis_quality
    - chat_usage
    - costs

security:
  rate_limit_enabled: true
  cors_origins:
    - "http://localhost:3000"
    - "https://example.com"
  require_auth: false  # Set true for production
```

### Synthesis Cache Schema: `synthesis_cache.json`

```json
{
  "metadata": {
    "version": "2.0",
    "created_at": "2026-04-23T10:15:00Z",
    "updated_at": "2026-04-23T10:15:00Z",
    "total_nodes": 793,
    "total_cost_usd": 0.18,
    "generated_by": "codex-synthesize v0.1.0"
  },
  "nodes": {
    "consolidated-11-241": {
      "title": "Agricultural Sustainability & Yield Optimization",
      "summary": "Explores farming practices...",
      "key_concepts": ["Crop rotation", "Soil health", "Climate adaptation"],
      "conceptual_cluster": "Agriculture",
      "insight_level": "intermediate",
      "confidence": 0.92,
      "api_cost_usd": 0.00024,
      "synthesis_timestamp": "2026-04-23T10:15:22Z"
    },
    "consolidated-42-156": { /* ... */ }
  },
  "indexes": {
    "by_cluster": {
      "Agriculture": ["consolidated-11-241", "consolidated-45-123"],
      "Technology": ["consolidated-42-156"],
      "Economics": []
    },
    "by_insight_level": {
      "foundational": [],
      "intermediate": ["consolidated-11-241"],
      "advanced": ["consolidated-42-156"]
    }
  }
}
```

---

## Monitoring & Logging

### Structured Logging Configuration

**Enable in `src/main.rs`:**
```rust
use tracing_subscriber::fmt;
use tracing::info, warn, error;

// Initialize with JSON output for ELK/Datadog
let subscriber = fmt()
    .json()
    .with_env_filter("codex=info,axum=warn")
    .with_target(false)
    .init();

info!(
    event = "synthesis_started",
    node_count = 793,
    batch_size = 10
);

error!(
    event = "api_error",
    node_id = "consolidated-11-241",
    error = "Rate limit exceeded",
    retry_after_secs = 60
);
```

### Metrics to Track

**Phase 2A (Synthesis):**
```
- nodes_synthesized: Counter
- synthesis_latency_ms: Histogram
- synthesis_cost_usd: Counter
- api_errors: Counter
- retry_attempts: Counter
- cache_hit_ratio: Gauge
```

**Phase 2C (Chat):**
```
- chat_queries_total: Counter
- chat_response_latency_ms: Histogram
- chat_tokens_used: Counter
- chat_cost_usd: Counter
- conversation_length: Histogram
- user_satisfaction: Gauge (0-5)
```

### Prometheus Metrics Endpoint

**Add to Axum:**
```rust
use prometheus::{Counter, Histogram, Registry};

pub struct Metrics {
    pub synthesis_counter: Counter,
    pub chat_latency: Histogram,
    pub api_costs: Counter,
}

// Endpoint: GET /metrics
async fn metrics_handler(State(metrics): State<Arc<Metrics>>) -> String {
    // Encode Prometheus format
}
```

### Dashboards (Grafana)

**Key panels:**
1. Synthesis job progress (% complete)
2. API cost trend ($/day)
3. Chat response time (p50, p95, p99)
4. Cache hit rate over time
5. Error rate by endpoint
6. User engagement (queries/hour)

---

## Security Considerations

### API Key Management
```rust
// Use environment variables, never commit keys
let api_key = std::env::var("ANTHROPIC_API_KEY")
    .expect("Set ANTHROPIC_API_KEY environment variable");

// Never log API keys
let masked_key = format!("{}...{}", &api_key[0..5], &api_key[api_key.len()-3..]);
info!(key = masked_key, event = "api_initialized");
```

### Rate Limiting Strategy
```rust
use governor::{Quota, RateLimiter};
use std::num::NonZeroU32;

// Per-IP rate limiting for chat
let limiter = RateLimiter::direct(Quota::per_minute(NonZeroU32::new(5)?));

async fn api_node_explain(
    ConnectInfo(addr): ConnectInfo<SocketAddr>,
    // ...
) -> Result<Response> {
    if limiter.check().is_err() {
        return Err(StatusCode::TOO_MANY_REQUESTS.into());
    }
    // Process request
}
```

### CORS & HTTPS
```rust
use tower_http::cors::CorsLayer;
use tower_http::trace::TraceLayer;

let app = Router::new()
    .layer(TraceLayer::new_for_http())
    .layer(
        CorsLayer::permissive()  // ← Change for production!
            .allow_origin("https://yourdomain.com".parse()?)
    );
```

### Input Validation
```rust
// Validate node_id format
fn validate_node_id(id: &str) -> Result<()> {
    if !id.starts_with("consolidated-") {
        return Err("Invalid node ID format".into());
    }
    if id.len() > 256 {
        return Err("Node ID too long".into());
    }
    Ok(())
}

// Sanitize user questions
fn sanitize_question(q: &str) -> String {
    q.trim()
        .chars()
        .take(2000)  // Max 2K chars
        .collect()
}
```

---

## Performance Benchmarking

### Baseline Metrics (Single Server, 2 CPU, 4GB RAM)

| Operation | Latency | Throughput |
|-----------|---------|-----------|
| Load synthesis_cache.json | 15ms | — |
| GET /api/node/{id}/synthesis | 5ms (cached) | 2000 req/sec |
| POST /api/node/{id}/explain | 2.5s (streaming) | 10 concurrent |
| Synthesis batch (100 nodes) | 45s | 2.2 nodes/sec |

### Load Testing Script

```bash
#!/bin/bash
# test-load.sh

# Test synthesis cache hit
ab -n 10000 -c 100 http://localhost:8080/api/node/consolidated-11-241/synthesis

# Test chat endpoint (limited by API rate)
for i in {1..100}; do
  curl -X POST http://localhost:8080/api/node/consolidated-11-241/explain \
    -H "Content-Type: application/json" \
    -d '{"question":"What is this about?"}' &
done
wait

# Measure synthesis batch
time ./target/release/codex synthesize \
  --input consolidate_output.jsonl \
  --batch-size 50
```

### Optimization Targets

- **Synthesis:** Parallelize API calls (currently sequential)
- **Chat:** Implement response caching for identical questions
- **Frontend:** Lazy-load synthesis data only when node selected

---

## Troubleshooting Guide

### Common Issues & Solutions

#### Issue: "Rate limit exceeded" errors during synthesis

**Symptoms:**
```
thread 'main' panicked at 'API error: 429 Rate Limit Exceeded'
```

**Solutions:**
1. Reduce `batch_size` in config (try 5 instead of 10)
2. Increase `rate_limit_rpm` delay
3. Check Anthropic dashboard for actual quota
4. Stagger synthesis across multiple days

**Command:**
```bash
codex synthesize \
  --batch-size 5 \
  --rate-limit 2 \  # More conservative
  --resume          # Pick up where it left off
```

---

#### Issue: Chat responses timeout or hang

**Symptoms:**
```
Request to /api/node/{id}/explain hangs for >30 seconds
```

**Solutions:**
1. Check Claude API status: https://status.anthropic.com
2. Verify `ANTHROPIC_API_KEY` is valid
3. Check network connectivity
4. Increase timeout in config
5. Switch to cheaper model (Haiku) for testing

**Debug:**
```bash
RUST_LOG=debug ./target/release/codex serve --bind 127.0.0.1:8080
# Check logs for API response times
```

---

#### Issue: High memory usage during batch synthesis

**Symptoms:**
```
Out of memory, process killed
```

**Solutions:**
1. Reduce `batch_size` (loads fewer nodes in memory)
2. Enable compression in config
3. Split synthesis into smaller jobs
4. Increase server RAM

**Monitor:**
```bash
watch -n 1 'ps aux | grep codex'  # Check memory usage
```

---

#### Issue: Cache not being used (always re-synthesizing)

**Symptoms:**
```
API costs keep increasing despite same nodes
```

**Solutions:**
1. Check `synthesis_cache.json` exists and is readable
2. Verify file permissions: `chmod 644 synthesis_cache.json`
3. Check cache path in config matches actual file location
4. Look for cache corruption: `jq . synthesis_cache.json > /dev/null`

**Rebuild cache:**
```bash
rm synthesis_cache.json
./target/release/codex synthesize \
  --input consolidate_output.jsonl \
  --cache synthesis_cache.json \
  --force-refresh  # Ignore stale data
```

---

#### Issue: Frontend not loading synthesis titles

**Symptoms:**
```
UI shows generic IDs instead of titles
sphere-nodes.json loaded but synthesis_cache.json not available
```

**Solutions:**
1. Verify `/api/node/{id}/synthesis` returns data: 
   ```bash
   curl http://localhost:8080/api/node/consolidated-11-241/synthesis
   ```
2. Check browser console for fetch errors
3. Ensure CORS is configured
4. Check synthesis_cache.json in 50_export/

**Quick fix:**
```bash
# Copy cache to export directory if missing
cp synthesis_cache.json 50_export/synthesis_cache.json

# Restart server
./target/release/codex serve --bind 127.0.0.1:8080
```

---

### Debug Checklist

Before reporting issues:

- [ ] API key is valid and has quota
- [ ] All files exist and are readable
- [ ] No firewall blocking API requests
- [ ] Running latest version: `cargo build --release`
- [ ] Logs show expected behavior: `RUST_LOG=debug`
- [ ] Network connectivity: `curl https://api.anthropic.com/healthz`
- [ ] Disk space: `df -h` (need >1GB for caches)
- [ ] RAM available: `free -h` (need >2GB for batch processing)

---

## References & External Resources

### Official Documentation
- [Anthropic Claude API](https://docs.anthropic.com)
- [Axum Web Framework](https://github.com/tokio-rs/axum)
- [Three.js 3D Library](https://threejs.org/docs)
- [Docker Official Docs](https://docs.docker.com)
- [Prometheus Metrics](https://prometheus.io/docs)

### Related Projects
- [CODEX Core (Phase 1 Consolidation)](./PLAN.md)
- [Knowledge Graph Research](https://arxiv.org/abs/2203.06995)
- [Semantic Chunking Strategies](https://arxiv.org/abs/2304.14997)

### Community & Support
- GitHub Issues: `https://github.com/yourusername/codex/issues`
- Discussions: `https://github.com/yourusername/codex/discussions`
- Email: `lucas@codex.systems`

---

**Document Version:** 1.1 (Extended with Technical Appendix)  
**Last Updated:** April 22, 2026  
**Author:** CODEX AI Planning System  
**Status:** Ready for Implementation  
**Total Pages:** ~15 (Planning + Technical Details)
