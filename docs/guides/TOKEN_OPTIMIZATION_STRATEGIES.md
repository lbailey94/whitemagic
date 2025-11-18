# Token Optimization Strategies - Order of Magnitude Improvements

**Date**: November 16, 2025
**Goal**: Reduce token burn by 10x through intelligent reading, caching, and context management
**Status**: Design Phase

---

## Strategy 1: Context-Aware Progressive Reading

### Current Approach (Baseline)

```python
# Read entire file (wasteful)
read_file("/path/to/file.py")  # 1000 lines = ~15K tokens

# Progressive (better)
read_file("/path/to/file.py", offset=1, limit=100)  # 100 lines = ~1.5K tokens
```

### Proposed: Pattern-Targeted Context Reading

**Concept**: Search for specific patterns, then read surrounding context (±100 lines).

#### Example Use Case

```python
# Find all instances of "def search_semantic" in codebase
grep_search("def search_semantic", IsRegex=True)
# Returns: Line 42, Line 156, Line 389

# Read context around each match
read_file_context(
    file="search/semantic.py",
    line=42,
    before=50,  # 50 lines before
    after=50    # 50 lines after
)
# Reads lines 1-92 (92 lines vs 500+ full file)
```

### Pros & Cons Analysis

#### Line-by-Line Sequential (Current)

**Pros**:

- Simple, predictable
- Good for thorough analysis
- No missed content

**Cons**:

- Wasteful for large files
- Reads irrelevant sections
- High token cost (15K per 1000-line file)

#### Pattern-Targeted Context (Proposed)

**Pros**:

- 70-90% token reduction for targeted searches
- Focuses on relevant code/content
- Maintains context (±N lines)

**Cons**:

- Might miss relationships outside window
- Requires good grep queries
- More complex orchestration

#### Hybrid Intelligent (Best of Both)

**Decision Tree**:

```
If file < 300 lines:
    → Read entire file (1.5-4.5K tokens)
    → Cost: Low, benefit: Complete context

Else if grep matches < 5 locations:
    → Read context windows (50 lines each)
    → Cost: 5 × 750 tokens = 3.75K vs 15K full
    → Savings: 75%

Else if grep matches >= 5 locations:
    → Summary read strategy:
        1. Read first 100 lines (headers, imports, docs)
        2. Read targeted context windows (top 5 matches)
        3. Read last 50 lines (often has main/exports)
    → Cost: ~5-7K vs 15K full
    → Savings: 50-65%

Else (no grep/exploratory):
    → Progressive reading (100 lines at a time)
    → Ask for continuation if needed
```

### Implementation Plan

**New Tool: `read_file_context`**

```python
def read_file_context(
    file_path: str,
    line: int,          # Target line
    before: int = 50,   # Lines before
    after: int = 50,    # Lines after
    include_full_if_small: int = 300  # Full read threshold
) -> str:
    """
    Read file with context around specific line.

    If file < include_full_if_small lines, reads entire file.
    Otherwise reads [line-before:line+after] range.

    Returns formatted output with line numbers.
    """
```

**Enhanced Workflow**:

```python
# Step 1: Grep first (cheap)
matches = grep_search("class SemanticSearch", file="search/")
# Returns: [(file1.py, line 42), (file2.py, line 156)]

# Step 2: Intelligent read
for file, line in matches[:5]:  # Top 5 matches
    if file_size(file) < 300:
        read_file(file)  # Full read
    else:
        read_file_context(file, line, before=50, after=50)
```

### Token Savings Projection

**Scenario**: Analyzing 10 files (avg 800 lines each)

| Approach | Tokens | Time |
|----------|--------|------|
| **Full read all** | 120K | 10s |
| **Progressive (100 lines)** | 15K | 8s |
| **Context-targeted (5 matches/file)** | 30K | 5s |
| **Hybrid intelligent** | 20-25K | 5s |

**Best case**: **80-85% token reduction** vs full reads

---

## Strategy 2: Summary Cache for Long-Term Memory

### Concept: Multi-Tier Memory Summaries

**Problem**: Loading 43 memories = ~50K tokens, but we often only need high-level context.

**Solution**: Hierarchical summaries

#### Cache Structure

```
.whitemagic/cache/summaries/
├── tier0/  # Ultra-compressed (titles + tags only)
│   └── all_memories.json  # 500 tokens for all 43
├── tier1/  # Short summaries (1-2 sentences each)
│   └── all_memories.json  # 3-5K tokens for all 43
├── tier2/  # Medium summaries (1 paragraph each)
│   └── all_memories.json  # 10-15K tokens for all 43
└── full/   # Original content (on-demand only)
    └── [individual files]
```

### Summary Generation

**Auto-generate on memory create/update**:

```python
def create_memory(title, content, ...):
    # ... create memory file ...

    # Auto-generate summaries (async/background)
    summaries = {
        "tier0": f"{title} | {tags}",  # 20 tokens
        "tier1": generate_summary(content, max_tokens=50),  # 50 tokens
        "tier2": generate_summary(content, max_tokens=200), # 200 tokens
    }

    cache.set(f"summary/{filename}", summaries)
```

### Intelligent Loading Strategy

**Tiered Context Loading**:

```python
class MemoryLoader:
    def get_context(self, tier: int = 1, query: Optional[str] = None):
        if tier == 0:
            # Ultra-fast scan: All titles + tags
            return load_tier0_summaries()  # 500 tokens

        elif tier == 1:
            # Balanced: Summaries + relevant full content
            if query:
                # 1. Load all tier1 summaries (3-5K)
                summaries = load_tier1_summaries()

                # 2. Find top 5 most relevant (semantic/keyword)
                relevant = search_summaries(query, summaries, limit=5)

                # 3. Load FULL content for top 5 only
                full_content = [load_full(mem) for mem in relevant]

                return summaries + full_content  # 3K + (5 × 2K) = 13K
            else:
                # No query: all tier1 summaries
                return load_tier1_summaries()  # 3-5K

        elif tier == 2:
            # Deep dive: All medium summaries + targeted full
            summaries = load_tier2_summaries()  # 10-15K
            if query:
                relevant = search_summaries(query, summaries, limit=10)
                full_content = [load_full(mem) for mem in relevant]
                return summaries + full_content  # 15K + (10 × 2K) = 35K
            return summaries

        else:  # tier == 3 (exhaustive)
            # Load everything (rare)
            return load_all_full_memories()  # 50K+
```

### Summary Quality

**Use LLM for high-quality summaries**:

```python
def generate_summary(content: str, max_tokens: int) -> str:
    """
    Generate summary using local LLM or GPT-3.5-turbo.

    Cache summaries permanently (regenerate only if content changes).
    """
    prompt = f"""Summarize this memory in {max_tokens} tokens or less.
    Focus on: key decisions, insights, version info, status.

    Content:
    {content[:2000]}  # Truncate for summary generation
    """

    summary = llm.generate(prompt, max_tokens=max_tokens)
    return summary
```

### Token Savings Projection

**Scenario**: Loading context for AI session

| Approach | Tokens | Coverage |
|----------|--------|----------|
| **Current (load all full)** | 50K | 100% |
| **Tier 0 (scan only)** | 500 | Titles + tags |
| **Tier 1 (smart load)** | 3-13K | Summaries + top 5 full |
| **Tier 2 (deep)** | 15-35K | All summaries + top 10 full |
| **Tier 3 (exhaustive)** | 50K+ | Everything |

**Best case**: **90-95% token reduction** for most queries (Tier 1)

---

## Strategy 3: Batch Summarization After Parallel Reads

### Concept: Read → Synthesize → Cache

**Current Problem**: 10 parallel reads = 30K tokens, often need to reference them multiple times.

**Solution**: Generate consolidated summary after batch operations.

#### Workflow

```python
# Step 1: Parallel batch read (one-time cost)
results = parallel_read([
    grep_search("v2.2.7", docs/),
    grep_search("missing features", roadmap/),
    read_file(vision.md),
    read_file(v2.2.7_plan.md),
])  # 30K tokens

# Step 2: Generate consolidated summary (500-1K tokens)
summary = generate_batch_summary(results, focus=[
    "missing features",
    "v2.2.7 scope",
    "implementation timeline"
])

# Step 3: Cache summary for session
cache.set("session/v2.2.7_context", summary)

# Step 4: Future references use summary (95% savings)
# Instead of re-reading 30K, reference 500-token summary
```

### Summary Prompt

```python
BATCH_SUMMARY_PROMPT = """
You performed {n_operations} operations in parallel:
{operation_list}

Synthesize findings into a concise summary:
1. Key insights (bullet points)
2. Relevant data points
3. Decisions/conclusions

Focus on: {focus_areas}

Max length: 500 tokens.
"""
```

### Token Savings Projection

**Scenario**: Multi-turn conversation referencing same context

| Turn | Without Summary | With Summary | Savings |
|------|----------------|--------------|---------|
| **Initial load** | 30K | 30K + 500 = 30.5K | -500 (overhead) |
| **2nd reference** | 30K | 500 | 29.5K (98%) |
| **3rd reference** | 30K | 500 | 29.5K (98%) |
| **4th reference** | 30K | 500 | 29.5K (98%) |
| **Total (4 turns)** | 120K | 32K | **88K (73%)** |

**More turns = Higher savings**

---

## Strategy 4: Smart Deduplication

### Concept: Don't Re-Read What We Already Have

**Current Problem**: Often grep same patterns multiple times or re-read files.

**Solution**: Context-aware deduplication

#### Session Context Cache

```python
class SessionContext:
    """Track what we've already read this session."""

    def __init__(self):
        self.read_files = {}  # {path: (content, timestamp)}
        self.grep_results = {}  # {(query, path): results}
        self.summaries = {}  # {key: summary}

    def has_file(self, path: str, max_age_seconds: int = 300) -> bool:
        """Check if we've read this file recently (5 min window)."""
        if path not in self.read_files:
            return False

        _, timestamp = self.read_files[path]
        age = time.time() - timestamp
        return age < max_age_seconds

    def get_file(self, path: str) -> Optional[str]:
        """Get cached file content."""
        if self.has_file(path):
            content, _ = self.read_files[path]
            return content
        return None

    def cache_file(self, path: str, content: str):
        """Cache file content with timestamp."""
        self.read_files[path] = (content, time.time())
```

#### Intelligent Tool Wrapper

```python
def smart_read_file(path: str, session_ctx: SessionContext) -> str:
    """Read file with session-aware caching."""

    # Check session cache first
    cached = session_ctx.get_file(path)
    if cached:
        print(f"[Cache HIT] Using cached content for {path}")
        return cached

    # Not cached, read from disk
    content = read_file(path)
    session_ctx.cache_file(path, content)

    return content
```

### Token Savings Projection

**Scenario**: Multi-turn session with some repeated file accesses

| Without Deduplication | With Deduplication | Savings |
|----------------------|-------------------|---------|
| Read file 3 times: 45K | Read once + 2 cache hits: 15K | 30K (67%) |

**Compound with summaries**: Read once (15K) → Summarize (500) → Reference 2× (1K) = **16.5K vs 45K (63% savings)**

---

## Combined Impact: Order of Magnitude Improvement

### Token Cost Comparison (Full Session)

**Typical session without optimizations**:

```
- Load memories: 50K
- Read 10 files: 150K
- Re-read references: 60K
- Exploratory searches: 40K
Total: 300K tokens
```

**Same session with ALL optimizations**:

```
- Load memories (Tier 1): 5-13K (90% reduction)
- Read 10 files (context-targeted): 20-30K (80% reduction)
- Re-read references (cached summaries): 5K (92% reduction)
- Exploratory searches (smart dedup): 15K (62% reduction)
Total: 45-63K tokens (79-85% reduction)
```

**Improvement**: **5-7x more efficient** per session

### Reasoning Depth vs Token Cost

**Tier System Design**:

| Tier | Description | Token Budget | Use Case |
|------|-------------|--------------|----------|
| **0** | Quick scan | 500-2K | "What memories do I have?" |
| **1** | Balanced | 5-15K | "Find missing features in v2.2.7" |
| **2** | Deep | 20-40K | "Full audit of all documentation" |
| **3** | Exhaustive | 50-100K | "Complete codebase analysis" |

**Intelligence**: AI selects appropriate tier based on task complexity.

---

## Implementation Priority

### Phase 1: Quick Wins (1-2 days)

1. **Session context cache** (deduplication)
2. **Summary generation** (tier 1 summaries)
3. **Smart file size check** (< 300 lines = full read)

**Impact**: 40-50% token reduction

### Phase 2: Medium (3-4 days)

1. **read_file_context tool** (pattern-targeted reading)
2. **Batch summarization** (after parallel ops)
3. **Tiered memory loading** (0/1/2/3)

**Impact**: 70-80% token reduction

### Phase 3: Polish (5-7 days)

1. **LLM-powered summaries** (quality improvement)
2. **Auto-tier selection** (AI chooses tier)
3. **Cache management** (TTL, cleanup, stats)

**Impact**: 85-90% token reduction + better quality

---

## Success Metrics

### Quantitative

- **Token reduction**: 79-85% per session
- **Speed improvement**: 2-3x faster (less waiting)
- **Cache hit rate**: >60% for repeated accesses

### Qualitative

- **Reasoning quality**: Maintained or improved (focused context)
- **Completeness**: No missed critical information
- **UX**: Faster responses, less "thinking..." time

---

## Next Steps

1. **Implement Phase 1** (session cache + summaries)
2. **Test with v2.2.7 work** (real-world validation)
3. **Measure token savings** (before/after comparison)
4. **Iterate based on results**
5. **Document patterns** for future optimization

---

**Status**: Ready to implement
**Owner**: WhiteMagic Core Team
**Next Review**: After Phase 1 completion
