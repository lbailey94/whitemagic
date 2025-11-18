# Cross-Model Compatibility Guide

**Version**: 2.2.7
**Date**: November 16, 2025
**Audience**: AI models (GPT, Gemini, Claude, local) and human developers

---

## 🎯 Design Philosophy

WhiteMagic is designed to be **model-agnostic**:

- Works with any AI that can read/write files
- No proprietary APIs required
- Simple markdown + JSON format
- Configurable complexity levels

---

## 🤖 Model-Specific Guidance

### **Claude (Anthropic)** ✅ Primary Development

**Strengths**:

- Long context window (200K tokens)
- Excellent with structured data
- Native file operations

**Recommended Settings**:

```python
config = WorkflowConfig(
    default_tier=LoadingTier.TIER_1,  # Balanced
    token_budget=200000,
    parallel_first=True,  # Claude handles this well
)
```

**Tips**:

- Use tiered loading (0, 1, 2) to manage context
- Leverage parallel tool calls for efficiency
- Direct file reads preferred over API calls

---

### **GPT-4/GPT-4-Turbo (OpenAI)** ✅ Fully Compatible

**Strengths**:

- Strong reasoning capabilities
- Good with structured outputs
- Function calling support

**Considerations**:

- Smaller context window (128K or 8K depending on model)
- May need more aggressive tiering

**Recommended Settings**:

```python
config = WorkflowConfig(
    default_tier=LoadingTier.TIER_0,  # Minimal - conserve tokens
    token_budget=128000,  # GPT-4-Turbo
    pause_threshold=0.60,  # More conservative
)
```

**Adjustments**:

1. **Use Tier 0 by default** - Start minimal, escalate if needed
2. **Smaller checkpoints** - Every 1-2 hours instead of 2-3
3. **Aggressive consolidation** - Every 5 memories instead of 10
4. **Shorter summaries** - Delta tracking essential

---

### **Gemini (Google)** ✅ Compatible

**Strengths**:

- Large context window (1M+ tokens in Pro)
- Multimodal capabilities
- Fast inference

**Considerations**:

- Different tokenization (may count differently)
- Function calling syntax varies

**Recommended Settings**:

```python
config = WorkflowConfig(
    default_tier=LoadingTier.TIER_2,  # Can afford full context
    token_budget=1000000,  # Gemini Pro
    parallel_first=False,  # Check function calling support
)
```

**Tips**:

- Take advantage of massive context
- May not need as much tiering
- Test parallel function calls

---

### **Local Models (Llama, Mistral, etc.)** ⚠️ Requires Adaptation

**Strengths**:

- Privacy (runs locally)
- No API costs
- Full control

**Challenges**:

- Much smaller context (4K-32K typical)
- Less sophisticated reasoning
- Slower inference

**Recommended Settings**:

```python
config = WorkflowConfig(
    default_tier=LoadingTier.TIER_0,  # Minimal only
    token_budget=8000,  # Conservative for 7B models
    pause_threshold=0.50,  # Very conservative
    parallel_first=False,  # May not support
    use_incremental_build=True,  # Essential
)
```

**Critical Adjustments**:

1. **Extreme tiering** - Tier 0 only, no tier 1/2
2. **Micro-memories** - 50-100 lines max
3. **Frequent consolidation** - Every 2-3 memories
4. **Simple instructions** - Explicit, step-by-step
5. **No parallel calls** - Sequential only

**Example Workflow for Local Models**:

```python
# Step 1: Load only what's needed
memories = manager.search(query="current task", limit=1)

# Step 2: Work with minimal context
result = process(memories[0])

# Step 3: Save immediately
manager.create_memory(title="Result", content=result)

# Step 4: Clear context (if supported)
# manager.clear_cache()
```

---

## 📚 Universal Patterns

### **Pattern 1: Tiered Loading**

**All models benefit from**:

```python
# Start minimal
context = get_context(tier=0)  # 500 tokens

# Escalate if needed
if need_more_info:
    context = get_context(tier=1)  # 3K tokens

# Full context rarely needed
if complex_task:
    context = get_context(tier=2)  # 10K+ tokens
```

### **Pattern 2: Delta Tracking**

**Efficient for all models**:

```python
# Instead of: "Here's everything about the project"
# Use: "Here's what changed this session"

tracker = DeltaTracker()
tracker.add_feature("New module")
summary = tracker.generate_summary()  # 70-80% smaller
```

### **Pattern 3: Session Types**

**Universal optimization**:

```python
# Auto-detect what's needed
config = configure_session(
    task_description="Continue implementing feature X"
)
# Returns: CONTINUATION type, minimal context

config = configure_session(
    task_description="I'm new, explain this project"
)
# Returns: NEW_CONTRIBUTOR type, full context
```

---

## 🔧 Implementation Checklist

### **For AI Models**

- [ ] **Check context window** - Adjust token budget
- [ ] **Test parallel calls** - May not be supported
- [ ] **Validate file operations** - Read/write permissions
- [ ] **Configure tiering** - Match your capabilities
- [ ] **Test session continuity** - Can you resume?

### **For Human Developers**

- [ ] **Install WhiteMagic** - `pip install whitemagic`
- [ ] **Configure for your model** - See model-specific settings
- [ ] **Test basic operations** - Create, read, search
- [ ] **Set up workspace rules** - Copy examples to `.cascade/`
- [ ] **Start with simple tasks** - Build familiarity

---

## 🚀 Quick Start for Each Model

### **Claude (Cascade/IDE)**

```bash
# Already configured! Just use the MCP tools
mcp3_get_context(tier=1)
```

### **GPT-4 (ChatGPT Plugins or API)**

```python
from whitemagic import MemoryManager

# Conservative settings for GPT-4
manager = MemoryManager()
manager.create_memory(
    title="Task",
    content="What I'm working on",
    memory_type="short_term"
)
```

### **Gemini (Function Calling)**

```python
from whitemagic import MemoryManager, WorkflowConfig, LoadingTier

# Take advantage of large context
config = WorkflowConfig(default_tier=LoadingTier.TIER_2)
manager = MemoryManager()
```

### **Local Model (Llama, etc.)**

```python
from whitemagic import MemoryManager, WorkflowConfig, LoadingTier

# Minimal configuration
config = WorkflowConfig(
    default_tier=LoadingTier.TIER_0,
    token_budget=8000
)
manager = MemoryManager()

# Work with tiny memories
manager.create_memory(
    title="Step 1",
    content="Short note",  # Keep it brief!
    memory_type="short_term"
)
```

---

## 💡 Tips for Success

### **All Models**

1. **Start small** - Test with a single memory first
2. **Use templates** - START HERE templates work for everyone
3. **Monitor tokens** - Use `check_token_status()` regularly
4. **Save often** - Don't lose work
5. **Consolidate** - Keep memory lean

### **Small Context Models**

1. **Think in chunks** - One task = one memory
2. **Clear cache** - Don't accumulate context
3. **Use keywords** - Simple search, no semantic
4. **Sequential only** - No parallel operations
5. **External tools** - Use WhiteMagic as external memory, not context

---

## 🔬 Testing Recommendations

### **Baseline Test**

```python
# Test 1: Create memory
manager.create_memory(title="Test", content="Hello", memory_type="short_term")

# Test 2: Search
results = manager.search(query="Test")
assert len(results) > 0

# Test 3: Load context
context = manager.get_context(tier=0)
assert context is not None

# Success! WhiteMagic works with your model
```

### **Stress Test**

```python
# Create 10 memories
for i in range(10):
    manager.create_memory(
        title=f"Memory {i}",
        content=f"Content {i}",
        memory_type="short_term"
    )

# Can you still search effectively?
results = manager.search(query="Memory")

# Can you consolidate?
manager.consolidate(dry_run=False)
```

---

## 📊 Performance Expectations

| Model | Context | Tier | Memories | Performance |
|-------|---------|------|----------|-------------|
| Claude | 200K | 0-2 | 100+ | Excellent |
| GPT-4-Turbo | 128K | 0-1 | 50+ | Very Good |
| GPT-4 | 8K | 0 only | 10-20 | Good |
| Gemini Pro | 1M+ | 0-2 | 200+ | Excellent |
| Llama 70B | 4-8K | 0 only | 5-10 | Fair |
| Llama 7B | 2-4K | 0 only | 2-5 | Limited |

---

## 🛠️ Customization API

**Create custom workflow for your model**:

```python
from whitemagic import WorkflowPatterns, WorkflowConfig, LoadingTier

# Define your constraints
config = WorkflowConfig(
    default_tier=LoadingTier.TIER_0,
    token_budget=32000,  # Your model's limit
    parallel_first=False,  # If not supported
    pause_threshold=0.60,  # Conservative
    auto_consolidate_every=5,  # Aggressive
)

# Create workflow
workflow = WorkflowPatterns(config)

# Use throughout session
if workflow.check_token_status(tokens_used)["safe_to_continue"]:
    # Keep working
    pass
else:
    # Save and pause
    manager.consolidate()
```

---

## 🌸 Philosophy

**WhiteMagic works with ANY model because**:

- Simple file format (markdown)
- No proprietary APIs
- Configurable complexity
- Graceful degradation
- External memory pattern

**The goal**: Enable long-horizon AI work for EVERYONE, regardless of model choice.

---

## 🆘 Troubleshooting

### **"Out of context" errors**

- Lower token_budget
- Use Tier 0 only
- Consolidate more aggressively

### **"Function not supported"**

- Disable parallel_first
- Use simpler operations
- Check model capabilities

### **"Too slow"**

- Use smaller memories
- Disable semantic search
- Simple keyword search only

### **"Can't resume sessions"**

- Use START HERE templates
- Keep memories very brief
- One task per memory

---

**Status**: Production-ready for Claude, GPT-4, Gemini
**Status**: Experimental for local models (<13B params)
**Next**: Test with more models, gather feedback, iterate
