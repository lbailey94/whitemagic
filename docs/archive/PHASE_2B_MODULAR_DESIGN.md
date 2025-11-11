# Phase 2B: Modular Semantic Search Design

**Philosophy**: "Start local and small, add as you go"

---

## 🎯 **Design Principles**

1. **Optional by Default**: Semantic search is an add-on, not required
2. **Progressive Enhancement**: Start simple, add complexity as needed
3. **Pay-as-you-go**: Only install/configure what you use
4. **Zero Breaking Changes**: Existing code continues to work

---

## 📊 **Three Tiers of Usage**

### **Tier 1: Ephemeral (Minimal Setup)**
**For**: Quick prototyping, low-commitment testing

**What you get**:
- OpenAI embeddings API
- Semantic search (no caching)
- No database changes
- No local models

**Setup**:
```bash
pip install whitemagic[embeddings-openai]
export OPENAI_API_KEY=sk-...
```

**Usage**:
```python
from whitemagic.embeddings import get_embedding_provider, EmbeddingConfig

config = EmbeddingConfig(provider="openai", openai_api_key="sk-...")
provider = get_embedding_provider(config)

# Generate on-demand (not stored)
embedding = await provider.embed("Find debugging tips")
```

**Pros**:
- ✅ Zero database changes
- ✅ Works with SQLite/PostgreSQL equally
- ✅ Fast setup (<5 minutes)

**Cons**:
- ❌ No embedding caching (re-generates each time)
- ❌ Higher API costs over time
- ❌ Slower for repeated queries

---

### **Tier 2: Cached (Standard Setup)**
**For**: Production use, cost optimization

**What you get**:
- OpenAI embeddings API
- pgvector storage (caching)
- Persistent embeddings
- Faster repeated queries

**Setup**:
```bash
pip install whitemagic[embeddings-openai]
export OPENAI_API_KEY=sk-...

# Enable pgvector extension in PostgreSQL
psql -d whitemagic -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Run migration
alembic upgrade head
```

**Usage**:
```python
# Same API, but embeddings are cached
embedding = await provider.embed("Find debugging tips")  # Stored in DB
embedding = await provider.embed("Find debugging tips")  # Retrieved from cache
```

**Pros**:
- ✅ Embeddings cached in database
- ✅ Lower API costs (only generate once)
- ✅ Faster repeated queries
- ✅ Supports batch migration

**Cons**:
- ❌ Requires PostgreSQL with pgvector
- ❌ Additional DB storage
- ❌ Migration needed

---

### **Tier 3: Full Stack (Maximum Features)**
**For**: Privacy-focused, cost-sensitive, or offline use

**What you get**:
- OpenAI + local embeddings
- pgvector storage
- Hybrid search
- No external API dependency
- Full privacy

**Setup**:
```bash
pip install whitemagic[embeddings-all]  # When deps fixed
export OPENAI_API_KEY=sk-...  # Optional

# Enable pgvector
psql -d whitemagic -c "CREATE EXTENSION IF NOT EXISTS vector;"
alembic upgrade head
```

**Usage**:
```python
# Use local provider (private, free)
config = EmbeddingConfig(provider="local", model="all-MiniLM-L6-v2")
provider = get_embedding_provider(config)

embedding = await provider.embed("Find debugging tips")  # 100% local
```

**Pros**:
- ✅ No external API calls
- ✅ Free (no ongoing costs)
- ✅ Full privacy (no data leaves server)
- ✅ Works offline

**Cons**:
- ❌ ~500MB additional dependencies
- ❌ Slightly lower quality than OpenAI
- ❌ Currently blocked by dep conflicts

---

## 🏗️ **Implementation Strategy**

### **Phase 1: Ephemeral (This Week)**
- [x] Embedding provider interface
- [x] OpenAI provider
- [x] Configuration
- [ ] API endpoints (generate on-demand)
- [ ] Basic tests

**Deliverable**: Can use semantic search without DB changes

### **Phase 2: Cached (Next Week)**
- [ ] Database schema (optional)
- [ ] pgvector migration
- [ ] Caching layer
- [ ] Batch migration script
- [ ] Auto-embed on create/update

**Deliverable**: Production-ready with caching

### **Phase 3: Full Stack (Week 3+)**
- [ ] Fix sentence-transformers deps
- [ ] Local provider implementation
- [ ] Hybrid search
- [ ] Performance benchmarks

**Deliverable**: Complete feature set

---

## 📦 **Package Structure**

```toml
[project.optional-dependencies]
# Tier 1: Minimal
embeddings-openai = [
    "openai>=1.0.0"
]

# Tier 2: Standard (adds PostgreSQL vector support)
embeddings-cached = [
    "openai>=1.0.0",
    "pgvector>=0.2.0",
    "numpy>=1.24.0",
    "scipy>=1.10.0"
]

# Tier 3: Full (adds local models - when fixed)
embeddings-local = [
    "sentence-transformers>=2.2.0"
]

# All features
embeddings-all = [
    "openai>=1.0.0",
    "pgvector>=0.2.0",
    "numpy>=1.24.0",
    "scipy>=1.10.0",
    # "sentence-transformers>=2.2.0"  # When deps resolved
]
```

---

## 🔌 **API Design (Modular)**

### **Configuration Detection**

```python
class EmbeddingConfig(BaseModel):
    provider: str = "openai"
    
    # Storage configuration (optional)
    enable_caching: bool = Field(
        default=False,
        description="Enable database caching of embeddings"
    )
    
    cache_backend: str = Field(
        default="postgres",
        description="Cache backend: 'postgres' or 'redis'"
    )
```

### **Auto-Detection**

```python
def get_embedding_provider(config: EmbeddingConfig):
    provider = create_provider(config)
    
    # Wrap with caching if enabled
    if config.enable_caching:
        if has_pgvector():
            provider = CachedProvider(provider, backend="postgres")
        else:
            logger.warning("Caching requested but pgvector not available. Using ephemeral mode.")
    
    return provider
```

### **Graceful Degradation**

```python
try:
    # Try to use cached embeddings
    embedding = await cache.get(text_hash)
except Exception:
    # Fall back to generating on-demand
    embedding = await provider.embed(text)
```

---

## 🎯 **Migration Path**

### **From Tier 1 → Tier 2**

```bash
# User starts with Tier 1 (ephemeral)
pip install whitemagic[embeddings-openai]

# Later, wants caching:
pip install whitemagic[embeddings-cached]
alembic upgrade head  # Adds embeddings table

# Config change:
export WM_EMBEDDING_CACHING=true

# Batch migrate existing memories:
wm embeddings migrate --batch-size 100
```

### **From Tier 2 → Tier 3**

```bash
# Add local embeddings
pip install whitemagic[embeddings-local]  # When available

# Switch provider:
export WM_EMBEDDING_PROVIDER=local

# Re-embed with local model:
wm embeddings migrate --provider local --batch-size 100
```

---

## ✅ **Success Criteria**

### **Tier 1 (This Week)**
- [ ] Can use semantic search with zero DB changes
- [ ] Works with SQLite and PostgreSQL equally
- [ ] Setup time <5 minutes

### **Tier 2 (Next Week)**
- [ ] pgvector optional, not required
- [ ] Graceful fallback if pgvector missing
- [ ] Migration script handles 10k+ memories

### **Tier 3 (Future)**
- [ ] Local embeddings working
- [ ] Hybrid search implemented
- [ ] Performance benchmarks published

---

## 📝 **Documentation Strategy**

### **Quick Start (Tier 1)**
```markdown
# Quick Start: Semantic Search

1. Install: `pip install whitemagic[embeddings-openai]`
2. Set API key: `export OPENAI_API_KEY=sk-...`
3. Use: 
   ```python
   from whitemagic.search import semantic_search
   results = semantic_search("debugging async code")
   ```

That's it! No database changes needed.
```

### **Production Setup (Tier 2)**
```markdown
# Production: Cached Embeddings

For production use, enable caching to reduce API costs:

1. Install: `pip install whitemagic[embeddings-cached]`
2. Enable pgvector: `CREATE EXTENSION vector;`
3. Run migration: `alembic upgrade head`
4. Enable caching: `export WM_EMBEDDING_CACHING=true`
5. Migrate existing: `wm embeddings migrate`
```

### **Self-Hosted (Tier 3)**
```markdown
# Self-Hosted: Local Embeddings

For privacy or cost savings, use local models:

1. Install: `pip install whitemagic[embeddings-all]`
2. Set provider: `export WM_EMBEDDING_PROVIDER=local`
3. First use downloads model (~80MB)
4. 100% local, no API calls

Cost: $0/month | Privacy: 100% local
```

---

## 🎨 **User Experience**

### **Tier 1 User**
```
$ pip install whitemagic[embeddings-openai]
$ export OPENAI_API_KEY=sk-xxx
$ python
>>> from whitemagic.search import semantic_search
>>> results = semantic_search("async debugging")
>>> print(results)

✓ Works immediately, no DB setup needed
✓ Perfect for prototyping
⚠ Generates embeddings on-demand (slower, costs more)
```

### **Tier 2 User**
```
$ pip install whitemagic[embeddings-cached]
$ psql -c "CREATE EXTENSION vector;"
$ alembic upgrade head
$ export WM_EMBEDDING_CACHING=true
$ wm embeddings migrate

Migrating 1,000 memories...
[████████████████████] 100% (1000/1000)
✓ Migration complete (45 seconds, $0.02)

✓ Embeddings cached in database
✓ Future queries are instant and free
✓ Production-ready setup
```

### **Tier 3 User**
```
$ pip install whitemagic[embeddings-all]
$ export WM_EMBEDDING_PROVIDER=local
$ python

Downloading model: all-MiniLM-L6-v2... [80MB]
Model loaded in 2.3 seconds.

>>> results = semantic_search("async debugging")

✓ 100% local, no external API
✓ Free forever
✓ Full privacy
⚠ ~500MB dependencies
```

---

**Status**: Design approved, starting implementation  
**Timeline**: Tier 1 this week, Tier 2 next week, Tier 3 when deps fixed  
**Philosophy**: Start small, grow as needed
