# Phase 2B: Semantic Search & Memory Science

**Date**: November 10, 2025  
**Current Version**: 2.1.1 (moving to 2.1.2)  
**Prerequisites**: Phase 2A.5 ✅ COMPLETE  
**Timeline**: 1-2 weeks  
**Priority**: P1 - High (Product Differentiation)

---

## 🎯 Phase Overview

### **Objective**
Transform WhiteMagic from keyword-based search to **semantic understanding** using embeddings and vector search, enabling AI agents to find relevant memories by meaning, not just keywords.

### **Why This Matters**
- **Better Relevance**: Find "debugging race conditions" even if memory says "async timing issues"
- **Competitive Edge**: Most memory systems use simple keyword search
- **Privacy Options**: Local embeddings for privacy-conscious users
- **Enterprise Ready**: Optional managed vector DBs (Pinecone) for scale
- **Cost Effective**: Hybrid approach balances quality and cost

---

## 📋 Implementation Checklist

### **Day 1-2: Embedding Generation** (2 days)

#### **1.1 Embedding Service Architecture**
- [ ] Create `whitemagic/embeddings.py` module
- [ ] Define `EmbeddingProvider` abstract base class
- [ ] Implement `OpenAIEmbeddings` provider
- [ ] Implement `LocalEmbeddings` provider (sentence-transformers)
- [ ] Add configuration for provider selection
- [ ] Error handling and retry logic
- [ ] Rate limiting for API calls

**Files**:
```python
whitemagic/embeddings.py
whitemagic/api/embeddings.py  # API routes
tests/test_embeddings.py
```

**API Integration**:
```python
from whitemagic.embeddings import get_embedding_provider

# OpenAI provider
provider = get_embedding_provider("openai", api_key="sk-...")
embedding = await provider.embed("Debug async race conditions")

# Local provider
provider = get_embedding_provider("local", model="all-MiniLM-L6-v2")
embedding = await provider.embed("Debug async race conditions")
```

#### **1.2 Database Schema Updates**
- [ ] Create Alembic migration for embeddings table
- [ ] Add `memory_embeddings` table
- [ ] Add pgvector extension to PostgreSQL
- [ ] Create vector indices (IVFFlat or HNSW)
- [ ] Add embedding metadata columns

**Migration**:
```sql
-- migrations/versions/xxx_add_embeddings.py
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE memory_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    memory_id VARCHAR(255) UNIQUE NOT NULL,
    embedding vector(1536),  -- or 384 for local
    model VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_embedding_vector ON memory_embeddings 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

#### **1.3 Auto-Embedding on Create/Update**
- [ ] Update `create_memory` to auto-embed
- [ ] Update `update_memory` to re-embed
- [ ] Add `skip_embedding` flag for bulk operations
- [ ] Background task queue for embedding generation
- [ ] Handle embedding failures gracefully

---

### **Day 3-4: Vector Search** (2 days)

#### **2.1 Vector Search Implementation**
- [ ] Implement cosine similarity search
- [ ] Add distance thresholds
- [ ] Implement K-nearest neighbors (KNN)
- [ ] Add filtering by memory type
- [ ] Add filtering by tags
- [ ] Optimize query performance

**Search Function**:
```python
async def semantic_search(
    query: str,
    k: int = 10,
    threshold: float = 0.7,
    memory_type: Optional[str] = None,
    tags: Optional[List[str]] = None
) -> List[SearchResult]:
    # 1. Generate query embedding
    query_embedding = await embedder.embed(query)
    
    # 2. Search vector database
    results = await db.query("""
        SELECT 
            m.*,
            1 - (e.embedding <=> $1::vector) as similarity
        FROM memories m
        JOIN memory_embeddings e ON m.id = e.memory_id
        WHERE 1 - (e.embedding <=> $1::vector) > $2
        ORDER BY e.embedding <=> $1::vector
        LIMIT $3
    """, query_embedding, threshold, k)
    
    return results
```

#### **2.2 Hybrid Search (Keyword + Semantic)**
- [ ] Combine keyword and semantic results
- [ ] Implement RRF (Reciprocal Rank Fusion) algorithm
- [ ] Configurable weighting (keyword vs semantic)
- [ ] Deduplicate results
- [ ] Add re-ranking layer

**Hybrid Algorithm**:
```python
def hybrid_search(
    query: str,
    k: int = 10,
    keyword_weight: float = 0.3,
    semantic_weight: float = 0.7
) -> List[SearchResult]:
    # Get both result sets
    keyword_results = keyword_search(query, k=k*2)
    semantic_results = semantic_search(query, k=k*2)
    
    # Apply RRF (Reciprocal Rank Fusion)
    scores = defaultdict(float)
    for rank, result in enumerate(keyword_results):
        scores[result.id] += keyword_weight / (rank + 60)
    
    for rank, result in enumerate(semantic_results):
        scores[result.id] += semantic_weight / (rank + 60)
    
    # Sort by combined score
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)[:k]
```

---

### **Day 5-6: API Endpoints & Migration** (2 days)

#### **3.1 New API Endpoints**
- [ ] `POST /api/v1/memories/search/semantic` - Semantic search
- [ ] `POST /api/v1/memories/search/hybrid` - Hybrid search
- [ ] `GET /api/v1/embeddings/status` - Status of embedding generation
- [ ] `POST /api/v1/embeddings/batch` - Batch process existing memories
- [ ] `GET /api/v1/embeddings/config` - Provider configuration
- [ ] Add OpenAPI schema updates

**Endpoint Examples**:
```python
# Semantic search
POST /api/v1/memories/search/semantic
{
  "query": "How do I debug async race conditions?",
  "k": 10,
  "threshold": 0.7,
  "filters": {
    "type": "long_term",
    "tags": ["python", "async"]
  }
}

# Response
{
  "items": [
    {
      "id": "mem_123",
      "title": "Async Debugging Techniques",
      "content": "...",
      "similarity": 0.92,
      "match_type": "semantic"
    }
  ],
  "metadata": {
    "query_embedding_time_ms": 45,
    "search_time_ms": 12,
    "total_time_ms": 57
  }
}

# Embedding status
GET /api/v1/embeddings/status
{
  "total_memories": 1000,
  "embedded": 950,
  "pending": 50,
  "provider": "openai",
  "model": "text-embedding-3-small",
  "last_batch_run": "2025-11-10T12:00:00Z"
}

# Batch processing
POST /api/v1/embeddings/batch
{
  "memory_type": "long_term",
  "limit": 100,
  "provider": "local"
}
```

#### **3.2 Migration Scripts**
- [ ] Create batch migration script for existing memories
- [ ] Add progress tracking
- [ ] Handle errors and retries
- [ ] Estimate costs for OpenAI embeddings
- [ ] Add dry-run mode
- [ ] Create verification script

**Migration Script**:
```bash
# CLI command
python cli.py embeddings migrate \
  --provider local \
  --batch-size 100 \
  --memory-type all \
  --dry-run

# Output
📊 Migration Plan:
  Provider: local (sentence-transformers/all-MiniLM-L6-v2)
  Total memories: 1,000
  Batch size: 100
  Estimated time: ~15 minutes
  Cost: $0.00 (local)
  
🔍 Dry run complete. Run without --dry-run to execute.
```

---

### **Day 7: Testing & Benchmarks** (1 day)

#### **4.1 Unit Tests**
- [ ] Test embedding generation (OpenAI + local)
- [ ] Test vector search
- [ ] Test hybrid search
- [ ] Test migration script
- [ ] Test API endpoints
- [ ] Test error handling

**Test Coverage**:
```python
tests/test_embeddings.py
  - test_openai_embedding_generation
  - test_local_embedding_generation
  - test_embedding_caching
  - test_embedding_error_handling

tests/test_vector_search.py
  - test_semantic_search_basic
  - test_semantic_search_with_filters
  - test_hybrid_search
  - test_search_performance

tests/test_embeddings_api.py
  - test_semantic_search_endpoint
  - test_batch_migration
  - test_embedding_status
```

#### **4.2 Performance Benchmarks**
- [ ] Benchmark embedding generation speed
- [ ] Benchmark search latency (target: <200ms)
- [ ] Benchmark at scale (1k, 10k, 100k memories)
- [ ] Compare keyword vs semantic vs hybrid relevance
- [ ] Document results

**Benchmark Script**:
```python
# CLI command
python cli.py embeddings benchmark

# Output
📊 Embedding Benchmark Results:

Provider Performance:
  OpenAI (text-embedding-3-small):
    - Generation: 45ms/doc
    - Cost: $0.02/1M tokens
    - Quality: High
  
  Local (all-MiniLM-L6-v2):
    - Generation: 12ms/doc
    - Cost: $0.00
    - Quality: Medium-High

Search Performance (10k memories):
  Semantic: 15ms avg
  Keyword: 8ms avg
  Hybrid: 23ms avg

Relevance (NDCG@10):
  Keyword: 0.65
  Semantic: 0.82
  Hybrid: 0.88
```

---

### **Day 8-10: Documentation & Polish** (3 days)

#### **5.1 Documentation**
- [ ] Update API documentation
- [ ] Add embedding guide
- [ ] Add migration guide
- [ ] Add cost analysis
- [ ] Add privacy considerations
- [ ] Update README with semantic search info

**Documents to Create**:
```
docs/SEMANTIC_SEARCH.md
docs/EMBEDDINGS_GUIDE.md
docs/MIGRATION_GUIDE.md
docs/COST_ANALYSIS.md
docs/DAY1-10_PHASE_2B_SUMMARY.md
```

#### **5.2 Configuration & Defaults**
- [ ] Add environment variables for embedding config
- [ ] Set sensible defaults (local embeddings)
- [ ] Add cost warnings for OpenAI
- [ ] Add provider selection logic
- [ ] Document configuration options

**Environment Variables**:
```bash
# Embedding provider
WM_EMBEDDING_PROVIDER=local  # or "openai"
WM_EMBEDDING_MODEL=all-MiniLM-L6-v2
OPENAI_API_KEY=sk-...

# Search defaults
WM_SEARCH_MODE=hybrid  # "keyword", "semantic", "hybrid"
WM_HYBRID_KEYWORD_WEIGHT=0.3
WM_HYBRID_SEMANTIC_WEIGHT=0.7
```

---

## 📊 Technical Specifications

### **Embedding Providers**

#### **OpenAI** (Cloud, High Quality)
- **Model**: `text-embedding-3-small`
- **Dimensions**: 1536
- **Cost**: $0.02 per 1M tokens (~$0.00002 per memory)
- **Speed**: ~45ms per embedding
- **Quality**: High
- **Privacy**: Sends to OpenAI API

#### **Local** (Free, Privacy-Friendly)
- **Model**: `sentence-transformers/all-MiniLM-L6-v2`
- **Dimensions**: 384
- **Cost**: $0.00
- **Speed**: ~12ms per embedding
- **Quality**: Medium-High
- **Privacy**: 100% local, no external calls

### **Vector Database**

#### **pgvector** (Primary)
- Extension for PostgreSQL
- Supports cosine, L2, inner product distances
- IVFFlat and HNSW indices
- Free and open-source
- Self-hosted

#### **Pinecone** (Optional, Enterprise)
- Managed vector database
- Serverless or pod-based
- High performance at scale
- ~$70/month for 10M vectors
- Automatic scaling

### **Search Algorithms**

#### **Cosine Similarity**
```python
similarity = 1 - cosine_distance(query_embedding, memory_embedding)
```

#### **Reciprocal Rank Fusion (RRF)**
```python
rrf_score = sum(1 / (k + rank_i)) for rank_i in ranks
```

---

## 🎯 Success Criteria

### **Functional Requirements**
- ✅ Semantic search finds relevant memories by meaning
- ✅ Hybrid search combines best of both approaches
- ✅ Migration script handles existing memories
- ✅ Both OpenAI and local providers work
- ✅ API endpoints fully documented

### **Performance Requirements**
- ✅ Embedding generation: <50ms (OpenAI), <20ms (local)
- ✅ Search latency: <200ms end-to-end
- ✅ Handles 10,000+ memories efficiently
- ✅ Batch migration: >100 memories/minute

### **Quality Requirements**
- ✅ Hybrid search beats keyword-only (benchmark)
- ✅ Semantic search finds related concepts
- ✅ Re-ranking improves top-10 results
- ✅ Privacy-friendly local option available

### **Cost Requirements**
- ✅ Local option is $0/month (free)
- ✅ OpenAI cost <$0.50 for 10k memories
- ✅ Transparent cost calculator
- ✅ Cost warnings before expensive operations

---

## 📦 Deliverables

### **Code**
- [ ] `whitemagic/embeddings.py` - Embedding service
- [ ] `whitemagic/vector_search.py` - Vector search logic
- [ ] `whitemagic/api/embeddings.py` - API endpoints
- [ ] Migration scripts
- [ ] Database migrations (Alembic)
- [ ] 20+ new tests

### **Documentation**
- [ ] `docs/SEMANTIC_SEARCH.md`
- [ ] `docs/EMBEDDINGS_GUIDE.md`
- [ ] `docs/MIGRATION_GUIDE.md`
- [ ] `docs/COST_ANALYSIS.md`
- [ ] Updated API docs
- [ ] Updated README

### **Infrastructure**
- [ ] pgvector setup instructions
- [ ] Embedding provider configs
- [ ] Performance benchmarks
- [ ] Cost calculator

---

## 🚀 Getting Started

### **Prerequisites**
- ✅ Phase 2A.5 complete
- ✅ PostgreSQL with pgvector extension
- ✅ OpenAI API key (optional, for cloud embeddings)
- ✅ Python 3.10+
- ✅ At least 2GB RAM (for local embeddings)

### **First Steps**
1. Install dependencies: `pip install sentence-transformers pgvector`
2. Enable pgvector: `CREATE EXTENSION vector;`
3. Run migration: `alembic upgrade head`
4. Configure provider: Set `WM_EMBEDDING_PROVIDER=local`
5. Test embedding: `python cli.py embeddings test`

---

## 📈 Timeline

| Days | Phase | Status |
|------|-------|--------|
| 1-2 | Embedding generation | ⏳ Next |
| 3-4 | Vector search | ⏳ Pending |
| 5-6 | API & migration | ⏳ Pending |
| 7 | Testing & benchmarks | ⏳ Pending |
| 8-10 | Documentation & polish | ⏳ Pending |

**Total**: 8-10 days  
**Target Completion**: November 20, 2025

---

## 🎯 Next Steps

1. **Review this plan** - Approve timeline and approach
2. **Install dependencies** - pgvector, sentence-transformers
3. **Set up pgvector** - Enable extension in PostgreSQL
4. **Day 1: Start embedding service** - Create base classes
5. **Day 2: Implement providers** - OpenAI + local
6. **Day 3-4: Vector search** - Cosine similarity + hybrid
7. **Day 5-6: API + migration** - Endpoints + batch script
8. **Day 7: Testing** - 20+ tests + benchmarks
9. **Day 8-10: Docs** - Complete documentation

---

**Status**: ✅ **READY TO START**  
**Blocking Issues**: None  
**Dependencies**: pgvector, sentence-transformers (install on Day 1)

**Let's build semantic search! 🚀**
