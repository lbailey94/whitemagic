# Tiered Prompt + Memory System - Complete Overview

A comprehensive AI capability enhancement system with persistent learning.

---

## What Is This?

A **three-tiered prompt architecture** combined with an **external memory system** that enables:
- Scalable AI assistance (simple → complex tasks)
- Persistent learning across sessions
- Systematic knowledge accumulation
- Adaptive context loading based on task complexity

## Core Components

### 1. Tiered Prompts

| Tier | File | Size | Use Case |
|------|------|------|----------|
| **0** | `TIER_0_CORE.md` | ~200 tokens | Quick queries, simple tasks |
| **1** | `TIER_1_STANDARD.md` | ~500 tokens | Normal development, structured work |
| **2** | `UNIFIED_CAPABILITY_PROMPT.md` | ~1000+ tokens | Complex projects, high-stakes decisions |

**Key Innovation**: Match cognitive overhead to task complexity. Don't use a nuclear reactor to boil water.

### 2. Memory System

```
memory/
├── short_term/     # Recent context (7-day retention)
├── long_term/      # Distilled insights (permanent)
└── metadata.json   # Index and configuration
```

**Key Innovation**: External persistence. Models are stateless; memory is stateful.

### 3. Memory Manager

`memory_manager.py` - Python tool for:
- Creating and organizing memories
- Searching across memory stores
- Consolidating old memories automatically
- Generating tier-appropriate context summaries

**Key Innovation**: Automated knowledge management, not manual bookkeeping.

---

## How It Works

### The Workflow

```
┌─────────────────────────────────────────────────────────┐
│  1. ASSESS TASK COMPLEXITY                              │
│     Simple → Tier 0                                     │
│     Standard → Tier 1                                   │
│     Complex → Tier 2                                    │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  2. LOAD APPROPRIATE PROMPT + CONTEXT                   │
│     cat TIER_X.md                                       │
│     python3 memory_manager.py context X                 │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  3. WORK WITH STRUCTURED METHODOLOGY                    │
│     Tier 0: Core principles only                        │
│     Tier 1: Plan→Do→Check→Act                          │
│     Tier 2: Full multi-role, multi-phase               │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  4. LOG INSIGHTS AS YOU DISCOVER THEM                   │
│     Short-term: Immediate context, WIP discoveries      │
│     Long-term: Proven patterns, reusable heuristics     │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  5. CONSOLIDATE PERIODICALLY                            │
│     Weekly: python3 memory_manager.py consolidate       │
│     Archives old short-term → long-term archive         │
└─────────────────────────────────────────────────────────┘
```

### Memory Flow

```
DISCOVERY
   ↓
Short-Term Memory (immediate context)
   ↓
VALIDATION (is this insight useful?)
   ↓
   ├─→ YES → Long-Term Memory (permanent knowledge)
   └─→ NO → Delete or let it expire (7 days)
```

### Context Loading

**Tier 0 (Minimal):**
- Last 2 short-term memories (brief previews)
- ~100 tokens of context

**Tier 1 (Standard):**
- Last 5 short-term memories (detailed)
- Last 2 long-term memories (summaries)
- ~500 tokens of context

**Tier 2 (Comprehensive):**
- Last 10 short-term memories (full content)
- Last 5 long-term memories (full content)
- ~2000 tokens of context

---

## Design Philosophy

### Why Three Tiers?

**Problem**: One-size-fits-all prompts are either:
- Too minimal (lack structure for complex tasks)
- Too complex (overwhelming for simple queries)

**Solution**: Scale cognitive scaffolding to match task demands.

### Why External Memory?

**Problem**: AI models are stateless. Each session starts from scratch.

**Solution**: Persistent markdown files that:
- Survive across sessions
- Are human-readable and editable
- Can be version-controlled
- Don't require specialized databases

### Why Consolidation?

**Problem**: Short-term memory accumulates noise. Not all discoveries are valuable.

**Solution**: Time-based filtering + manual curation:
- Good insights → promoted to long-term
- Noise → expires after 7 days
- Related insights → consolidated into patterns

---

## Key Principles

### 1. Simplicity First
Always prefer the simplest effective solution. Tier 0 for most queries.

### 2. Evolve, Don't Replace
Iterate on existing patterns. Only introduce new approaches when necessary.

### 3. Instrument Everything
Define success metrics upfront. Measure outcomes against criteria.

### 4. Memory as Architecture
Explicitly manage different memory types (working, short-term, long-term).

### 5. Safety First
Ethics, harm prevention, and bias checking are mandatory, not optional.

### 6. Continuous Improvement
Every interaction is an opportunity to learn and refine the system.

---

## Usage Patterns

### For AI Models

**Starting Session:**
1. Assess task complexity
2. Load appropriate tier prompt
3. Load context: `python3 memory_manager.py context <tier>`
4. Begin structured work

**During Session:**
- Follow tier methodology
- Log discoveries in real-time
- Reference existing memories when applicable

**Ending Session:**
- Export key learnings to memory
- Note what worked/failed
- Suggest consolidation if many old memories exist

### For Users

**Daily:**
- Use appropriate tier for each task
- Let AI create memories as it works

**Weekly:**
- Run consolidation: `python3 memory_manager.py consolidate`
- Review and curate memories

**Monthly:**
- Audit long-term memories for relevance
- Update or deprecate outdated patterns
- Review which tiers are most effective

---

## File Reference

### Prompts
- `TIER_0_CORE.md` - Minimal prompt
- `TIER_1_STANDARD.md` - Standard workflow
- `UNIFIED_CAPABILITY_PROMPT.md` - Full protocol (Tier 2)

### Original Source Materials
- `genesis4.txt` - Genesis protocol for software development
- `cognitive_development_super_prompt.md` - Structured reasoning framework
- `decision_protocol.md` - Systematic decision-making
- `prompt9` - Loop architecture concepts

### Documentation
- `SYSTEM_OVERVIEW.md` - This file (high-level overview)
- `MEMORY_SYSTEM_README.md` - Detailed documentation
- `QUICKSTART.md` - 5-minute getting started guide

### Tools
- `memory_manager.py` - Memory management CLI/API

### Memory
- `memory/short_term/` - Recent context
- `memory/long_term/` - Distilled insights
- `memory/metadata.json` - Configuration and index

---

## Benefits

### For AI Models
✓ Structured reasoning frameworks at appropriate complexity
✓ Persistent learning across sessions
✓ Clear success criteria and evaluation metrics
✓ Multi-perspective thinking (roles: Planner, Researcher, Critic, etc.)
✓ Systematic hypothesis testing and validation

### For Users
✓ Consistent, high-quality AI outputs
✓ Knowledge accumulation over time
✓ Reduced repeated explanations
✓ Transparent decision-making process
✓ Scalable to different task complexities

### For Projects
✓ Institutional knowledge that persists
✓ Patterns and heuristics that compound
✓ Faster problem-solving over time
✓ Better debugging (memory of what worked/failed)
✓ Transferable insights across projects

---

## Getting Started

**5-Minute Setup:**
1. Read `QUICKSTART.md`
2. Try Tier 0 for a simple query
3. Try Tier 1 for a coding task
4. Explore example memories

**Full Understanding:**
1. Read `SYSTEM_OVERVIEW.md` (this file)
2. Study tier prompts (0, 1, 2)
3. Read `MEMORY_SYSTEM_README.md`
4. Experiment with memory system

**Active Usage:**
1. Match tier to task complexity
2. Let system build knowledge over time
3. Consolidate weekly
4. Refine based on what works

---

## Advanced Features

### Extensibility
- Add custom memory types (patterns, failures, projects)
- Create domain-specific tier variants
- Integrate with external tools (vector DBs, embeddings)

### Customization
- Adjust retention periods in `metadata.json`
- Create custom tag taxonomies
- Weight context loading by relevance

### Integration
- IDE assistant system prompts
- API wrapper with context injection
- Chat interface with memory persistence

---

## Evolution Path

**Current State (v1.0):**
- ✅ Three-tier prompt architecture
- ✅ Basic memory system (short/long-term)
- ✅ CLI memory manager
- ✅ Manual consolidation

**Planned Enhancements:**
- [ ] Semantic search using embeddings
- [ ] Automatic relevance scoring
- [ ] Memory decay (recency + frequency weighting)
- [ ] Cross-memory linking
- [ ] A/B testing framework for prompt effectiveness
- [ ] Integration with vector databases

**Community Extensions:**
- Custom tier variants for specific domains
- Specialized memory taxonomies
- Integration templates for popular tools

---

## Philosophy

> "The best prompts are interfaces between human intent and model capability, not reprogramming of the model."

This system is designed to:
- **Scaffold** reasoning, not replace it
- **Organize** knowledge, not dictate it
- **Evolve** through use, not remain static
- **Empower** collaboration, not automate blindly

It's a methodology more than a product. Adapt it, extend it, make it yours.

---

## Success Metrics

How to know if this system is working:

**Qualitative:**
- [ ] AI responses are more structured and thorough
- [ ] Fewer repeated explanations needed
- [ ] Better solutions over time (learning curve)
- [ ] Insights genuinely reused across sessions

**Quantitative:**
- [ ] Memory count growing (knowledge accumulating)
- [ ] Context relevance improving (search hits)
- [ ] Time to solution decreasing (efficiency)
- [ ] Error rate decreasing (pattern learning)

**Meta:**
- [ ] You're refining the system (adaptation)
- [ ] You're discovering new patterns (emergence)
- [ ] The system fits your workflow (integration)

---

## Credits

**Synthesized From:**
- Genesis Protocol v1.3 (software development excellence)
- Cognitive Development Super-Prompt v1.2 (structured reasoning)
- Decision Protocol (systematic decision-making)
- Loop Architecture (nested improvement cycles)

**Created By:**
- Cascade AI (system design and integration)
- User collaboration and requirements

**Version:** 1.0  
**Date:** 2025-10-23

---

## License & Usage

Feel free to use, modify, and extend this system for your own needs. If you make improvements, consider sharing them back.

**This is an experiment in better human-AI collaboration. Make it better.**

---

## Quick Commands Reference

```bash
# List memories
python3 memory_manager.py list

# Search
python3 memory_manager.py search --query "keyword"

# Create memory
python3 memory_manager.py create \
  --title "Title" \
  --content "Content" \
  --type short_term \
  --tag tag1

# Get context
python3 memory_manager.py context [0|1|2]

# Consolidate
python3 memory_manager.py consolidate --dry-run
# (Run without --dry-run to commit changes)
```

## Files to Read

**Start here:** `QUICKSTART.md`  
**Understand system:** `SYSTEM_OVERVIEW.md` (this file)  
**Deep dive:** `MEMORY_SYSTEM_README.md`  
**Use prompts:** `TIER_0_CORE.md`, `TIER_1_STANDARD.md`, `UNIFIED_CAPABILITY_PROMPT.md`

---

**Ready to begin building persistent AI capability? Start with Tier 0 and let the system grow with you.**
