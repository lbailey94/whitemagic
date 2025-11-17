# WhiteMagic Best Practices v2.2.7

**Updated**: November 16, 2025  
**For**: Developers, AI agents, contributors  
**Version**: 2.2.7

---

## 🎯 Core Principles

### 1. **Parallel-First Execution**
Always use parallel operations when tasks are independent.

```python
# ❌ Sequential (slow)
for file in files:
    process(file)

# ✅ Parallel (40x faster)
from whitemagic.parallel import ParallelFileReader
reader = ParallelFileReader(max_workers=64)
results = await reader.read_batch(files)
```

### 2. **Tiered Context Loading**
Start with Tier 1, only escalate if needed.

```python
# ❌ Loading everything (40K+ tokens)
context = load_all_context()

# ✅ Tiered approach (3K tokens)
from whitemagic import get_context
context = get_context(tier=1)  # Balanced - use 90% of time
```

### 3. **Philosophy-Guided Development**
Use I Ching, Wu Xing, and Art of War systems actively.

```python
# Threading: I Ching-aligned
from whitemagic.parallel import ThreadingTier
tier = ThreadingTier.TIER_3  # 64 threads - hexagram optimal

# Workflow: Wu Xing phases
from whitemagic.wu_xing import WuXingPhase
phase = WuXingPhase.FIRE  # Execution mode

# Planning: Art of War terrain
from whitemagic.strategy import TaskTerrain
terrain = assess_terrain(task)  # Before executing
```

---

## 📚 Development Workflow

### Session Start
```python
# 1. Load context
context = mcp3_get_context(tier=1)

# 2. Create session
from whitemagic.sessions import SessionManager
manager = SessionManager()
session = await manager.create_session(
    name="feature-implementation",
    goals=["Build X", "Test Y"],
    auto_checkpoint=True
)

# 3. Create scratchpad for working memory
from whitemagic.scratchpad import ScratchpadManager
scratch_mgr = ScratchpadManager()
scratchpad = await scratch_mgr.create("task-name")
```

### During Work
```python
# Use parallel operations
from whitemagic.parallel import parallel_search
results = await parallel_search(["query1", "query2", "query3"])

# Track decisions in scratchpad
await scratch_mgr.update(
    scratchpad.id,
    "decisions",
    "Chose approach A because..."
)

# Track metrics
from whitemagic.metrics import track_metric
track_metric("velocity", "files_modified", 12)
```

### Session End
```python
# Finalize scratchpad
content = await scratch_mgr.finalize(scratchpad.id)

# Checkpoint session
await manager.checkpoint_session(session.id)

# Create summary memory
mcp3_create_memory(
    title="Session complete",
    content=content,
    type="short_term"
)
```

---

## 🔒 Security & Privacy

### Never Commit
- ❌ API keys, tokens, passwords
- ❌ `.env` files (except `.env.example`)
- ❌ `private/` directory
- ❌ Internal notes, TODOs with sensitive info
- ❌ Real user data, emails, credentials

### Always Check
```bash
# Before committing:
python scripts/audit_for_release.py

# Before releasing:
whitemagic audit --full  # (v2.2.8+)
```

### .gitignore Essentials
```gitignore
private/
.env
.env.*
!.env.example
*.key
secrets.json
```

---

## 🧪 Testing

### Write Tests First
```python
# tests/test_feature.py
def test_parallel_operations():
    reader = ParallelFileReader(max_workers=64)
    results = await reader.read_batch(files)
    assert len(results) == len(files)
    assert all(r.success for r in results)
```

### Run Tests
```bash
# All tests
pytest

# Specific module
pytest tests/test_parallel.py

# With coverage
pytest --cov=whitemagic --cov-report=html
```

---

## 📖 Documentation

### Update on Version Change
1. **VERSION file** - Source of truth
2. **pyproject.toml** - Python package
3. **whitemagic-mcp/package.json** - MCP server
4. **Client SDKs** - Python + TypeScript
5. **CHANGELOG.md** - Release history
6. **Release notes** - New features

### Use Version Tool (v2.2.8+)
```bash
whitemagic version bump 2.2.9
# Updates all files automatically
```

---

## 🚀 Performance Tips

### Token Efficiency
```python
# Instead of full file read:
read_file("huge_file.py")  # 10K+ tokens

# Use targeted search:
grep_search(
    Query="function_name",
    SearchPath="path/to/file.py",
    MatchPerLine=true
)  # ~100 tokens
```

### Parallel Thinking
```python
# Batch independent operations:
results = parallel([
    read_file("a.py"),
    read_file("b.py"),
    grep_search(...),
    mcp3_search_memories(...)
])
```

### Memory Management
```python
# Create memories often:
mcp3_create_memory(...)  # After insights

# Consolidate when needed:
mcp.call_tool('consolidate', {dry_run: false})

# Use scratchpads for working memory
# (Converted to permanent memories at end)
```

---

## 🎯 Code Quality

### Type Hints
```python
# Always use type hints
from typing import List, Dict, Optional

def process_memories(
    queries: List[str],
    tier: int = 1
) -> Dict[str, Any]:
    ...
```

### Docstrings
```python
def parallel_search(queries: List[str]) -> List[SearchResult]:
    """
    Search multiple queries in parallel.
    
    Args:
        queries: List of search strings
        
    Returns:
        List of search results (one per query)
        
    Example:
        >>> results = await parallel_search(["query1", "query2"])
        >>> len(results)
        2
    """
```

### Error Handling
```python
# Graceful degradation
try:
    result = await parallel_operation()
except Exception as e:
    logger.error(f"Parallel failed, falling back: {e}")
    result = await sequential_operation()
```

---

## 🔄 Version Control

### Commit Messages
```bash
# Format: <type>: <description>

feat: Add parallel search MCP tool
fix: TypeScript type assertion in batch_create
docs: Update v2.2.7 release notes
test: Add parallel infrastructure tests
chore: Bump version to 2.2.7
```

### Branch Naming
```
feature/v2.2.7-parallel-sessions
fix/railway-port-interpolation
docs/update-quickstart
```

### Before Push
```bash
# Check status
git status

# Run tests
pytest

# Audit (if releasing)
python scripts/audit_for_release.py

# Push
git push origin branch-name
```

---

## 📊 Metrics & Monitoring

### Track Important Metrics
```python
from whitemagic.metrics import track_metric

# Token efficiency
track_metric("token_efficiency", "usage_percent", 67.5)

# Velocity
track_metric("velocity", "features_per_day", 3)

# Quality
track_metric("quality", "tests_passing", 194)
```

### Wu Xing Phases
```python
from whitemagic.wu_xing import WuXingPhase

# Track current phase
phase = WuXingPhase.FIRE  # Execution
# Affects: metrics categorization, workflow suggestions
```

---

## 🛠️ Tools & Utilities

### MCP Tools (24 total)
```typescript
// Core operations
mcp.call_tool('search_memories', {query: "..."})
mcp.call_tool('create_memory', {title: "...", content: "..."})
mcp.call_tool('get_context', {tier: 1})

// Parallel operations (P0 - v2.2.7)
mcp.call_tool('parallel_search', {queries: [...]})
mcp.call_tool('batch_create_memories', {memories: [...]})

// Session management (P0 - v2.2.7)
mcp.call_tool('create_session', {name: "..."})
mcp.call_tool('checkpoint_session', {session_id: "..."})

// Scratchpad (P0 - v2.2.7)
mcp.call_tool('create_scratchpad', {name: "..."})
mcp.call_tool('update_scratchpad', {...})
```

### CLI Commands
```bash
# Memory operations
whitemagic create "title" "content"
whitemagic search "query"
whitemagic list

# Context
whitemagic context --tier 1

# Metrics
whitemagic track velocity files_modified 12

# AI initialization
whitemagic ai-init

# Automation (v2.2.8+)
whitemagic audit --full
whitemagic docs-check --fix
whitemagic exec plan --commands <json>
```

---

## 🚫 Anti-Patterns

### Don't Do This
```python
# ❌ Sequential when can be parallel
for query in queries:
    search(query)

# ❌ Loading full context always
get_context(tier=2)  # 10K tokens!

# ❌ No error handling
result = risky_operation()  # Crash!

# ❌ Magic numbers
pool = ThreadPool(workers=73)  # Why 73?

# ❌ No type hints
def process(data):  # What type?
    ...
```

### Do This Instead
```python
# ✅ Parallel operations
results = await parallel_search(queries)

# ✅ Tiered loading
context = get_context(tier=1)  # 3K tokens

# ✅ Error handling
try:
    result = risky_operation()
except SpecificError as e:
    handle(e)

# ✅ I Ching-aligned constants
from whitemagic.parallel import ThreadingTier
pool = ThreadPool(workers=ThreadingTier.TIER_3.value)  # 64

# ✅ Type hints
def process(data: Dict[str, Any]) -> List[Result]:
    ...
```

---

## 📚 Learning Resources

### Documentation
- [USER_GUIDE.md](USER_GUIDE.md) - Complete guide
- [PARALLEL_OPERATIONS.md](guides/PARALLEL_OPERATIONS.md) - Parallel infrastructure
- [SESSION_MANAGEMENT.md](guides/SESSION_MANAGEMENT.md) - Sessions & scratchpads
- [AI_QUICKSTART.md](AI_QUICKSTART.md) - For AI agents

### Examples
- `examples/parallel_example.py` - Parallel operations
- `examples/session_example.py` - Session management
- `examples/wu_xing_example.py` - Philosophy integration

### Terminal Helper
```bash
source .whitemagic/terminal_helper.sh
wm_help  # Show all commands
```

---

## ✅ Checklist for New Contributors

Before your first PR:
- [ ] Read USER_GUIDE.md
- [ ] Install dev dependencies: `pip install -e .[dev]`
- [ ] Run tests: `pytest`
- [ ] Check code style: `black . && isort .`
- [ ] Try terminal helper: `source .whitemagic/terminal_helper.sh`
- [ ] Read CONTRIBUTING.md
- [ ] Check .gitignore (don't commit private/)

---

## 🎯 Summary

**Key takeaways**:
1. **Parallel-first** - 40x speedup
2. **Tiered loading** - 87% token savings
3. **Philosophy-guided** - I Ching, Wu Xing, Art of War
4. **Session management** - Continuity across work
5. **Security-conscious** - Never commit secrets
6. **Test-driven** - Write tests first
7. **Well-documented** - Update docs with code

**WhiteMagic best practices = faster, safer, smarter development!** 🪄

---

For questions: See [USER_GUIDE.md](USER_GUIDE.md) or [GitHub Discussions](https://github.com/lbailey94/whitemagic/discussions)
