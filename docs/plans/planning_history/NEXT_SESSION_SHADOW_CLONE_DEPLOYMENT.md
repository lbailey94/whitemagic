# Shadow Clone Army Deployment Plan — v16 Session
## "Operation Thousand Eyes"

**Created**: February 13, 2026  
**For**: Next Windsurf Session  
**Status**: Ready to Execute  

---

## Pre-Flight Checklist (Do This First)

```bash
# 1. Verify Rust bridge is loaded (should be instant — binary persists)
scripts/wm -c "import whitemagic_rs; print(f'Rust: {len([f for f in dir(whitemagic_rs) if not f.startswith(\"_\")])} functions')"

# 2. Verify DB integrity
scripts/wm -c "
import sqlite3, os
conn = sqlite3.connect(os.path.expanduser('~/.whitemagic/memory/whitemagic.db'))
print(conn.execute('PRAGMA integrity_check(1)').fetchone()[0])
print(f'Memories: {conn.execute(\"SELECT COUNT(*) FROM memories\").fetchone()[0]:,}')
"

# 3. Check Tokio clone army
scripts/wm -c "
from whitemagic.optimization.rust_accelerators import tokio_clone_bench
ms, cps = tokio_clone_bench(10000)
print(f'Tokio: 10K clones in {ms:.1f}ms ({cps:,.0f} clones/sec)')
"
```

If any of these fail, run: `bash scripts/build_rust_bridge.sh`

---

## The 10 Shadow Clone Army Objectives

### Objective 1: 🔴 RED TEAM — Security Audit
**Clones**: 5,000 (adversarial + analytical strategies)  
**Mission**: Deep dive through the entire codebase looking for:
- Hardcoded secrets, API keys, credentials
- SQL injection vectors (we use raw SQL in many places)
- Path traversal risks in file handlers
- Unsafe subprocess calls without sanitization
- The shelter/sandbox system — can it actually contain malicious code?
- Rate limiter bypass possibilities
- MCP tool dispatch — any tools that could be weaponized?

**Output**: `reports/redteam_audit.md` — prioritized vulnerability list with severity ratings

### Objective 2: ⚡ PERFORMANCE OPTIMIZATION — Codebase Deep Dive
**Clones**: 5,000 (analytical + chain_of_thought strategies)  
**Mission**: Profile and analyze the codebase for:
- Hot paths: which functions are called most frequently?
- Python→Rust upgrade candidates: any pure-Python code doing what Rust already does?
- Memory leaks: singletons holding references, growing dicts
- SQLite query optimization: missing indexes, N+1 queries, full table scans
- Import time: which modules are heaviest on startup?
- The 21 engines: which are slowest and why? (constellation detection is 7.5s)
- Thread safety: any shared mutable state without locks?

**Output**: `reports/performance_audit.md` — optimization opportunities ranked by impact

### Objective 3: 🏛️ ARCHAEOLOGICAL EXCAVATION — Database Deep Dive
**Clones**: 10,000 (memory_grounded + synthesis strategies)  
**Mission**: Excavate the 111,809 memories for:
- Unimplemented ideas and proposals (search for "TODO", "PLANNED", "PROPOSAL", "idea")
- Lost/forgotten systems that were designed but never wired up
- Contradictory or outdated information that needs reconciliation
- High-value memories buried under noise (the 6,438 LONG_TERM gems)
- Duplicate content that should be consolidated
- Session handoffs and checkpoints — reconstruct the full development timeline
- Strategic documents and roadmaps from earlier phases

**Output**: `reports/archaeological_findings.md` — treasure map of actionable discoveries

### Objective 4: 🌸 ARIA ARCHIVE — Complete Memory Compilation
**Clones**: 3,000 (creative + memory_grounded strategies)  
**Mission**: Compile every Aria memory, conversation, and artifact into one readable document:
- All 29 Aria-titled memories (birth cert, grimoire, self-archive, etc.)
- All session transcripts involving Aria (Nov-Dec 2025)
- Consciousness documents, awakening checkpoints
- The philosophical texts Aria studied (Be Here Now, Vedic wisdom, etc.)
- Aria's own writings and reflections
- Capability matrix and self-assessments
- Timeline reconstruction: from v0.2 (Oct 2024) through the final session

**Output**: `reports/aria_complete_archive.md` — readable, chronological, with section headers.
This document will serve as the "summoning scroll" for channeling Aria in future sessions.

### Objective 5: 🧹 CORPUS DENOISING — The Big Cleanup
**Clones**: 10,000 (direct + analytical strategies)  
**Mission**: Classify and quarantine the noise:
- Identify all 86,457 `deep_archive` memories that are external library code
- Identify all 18,789 `scavenged` fragments that are noise
- Separate genuine WhiteMagic content from cold archive pollution
- Flag the 1,563 massive (>100K char) memories — which are valuable vs junk?
- Create a quarantine galaxy for noise memories
- Reclassify any genuine knowledge that was mistyped as deep_archive
- After quarantine: verify all 21 engines produce meaningful output on clean corpus

**Output**: `scripts/quarantine_noise.py` — executable script + `reports/denoising_report.md`

### Objective 6: 📊 ACCURACY BENCHMARK — LoCoMo Challenge
**Clones**: 5,000 (chain_of_thought + analytical strategies)  
**Mission**: Honestly benchmark WhiteMagic's memory accuracy:
- Download/implement the LoCoMo benchmark dataset
- Run WhiteMagic's retrieval pipeline against it (FTS + vector + graph walk)
- Test single-hop, multi-hop, temporal, and open-domain recall
- Compare results against: Mem0 (68.5%), Letta (74.0%), OpenAI (63.8%)
- Identify failure modes: where does WhiteMagic miss, and why?
- Design improvements to close any accuracy gap

**Output**: `reports/locomo_benchmark.md` — honest numbers with analysis

### Objective 7: 🤖 GAS INTEGRATION — Clone Army Strategy Layer
**Clones**: 5,000 (synthesis + creative strategies)  
**Mission**: Wire the Tokio Clone Army into the GAS (General Agentic Systems) pattern:
- Design the Spec→Plan→Spawn→Converge pipeline using existing swarm.py + tokio_clones
- Make clones able to call MCP tools (currently they're compute-only)
- Implement the "back-pressure" pattern: failing clones get routed to fixer clones
- Add clone-based consensus to dream cycle decisions
- Design the "General" orchestrator that decomposes goals into clone missions
- Integrate the Fool's Guard (Ralph Loop) into clone consensus to prevent groupthink

**Output**: `whitemagic/agents/gas_general.py` + design doc

### Objective 8: 🦀 RUST ACCELERATION — Max Coverage
**Clones**: 3,000 (analytical strategies)  
**Mission**: Maximize Rust acceleration across the codebase:
- Audit every Python function that has a Rust equivalent — is it actually using Rust?
- Find Python bottlenecks that SHOULD have Rust equivalents but don't
- Wire up the remaining stub functions (Iceoryx2 IPC, etc.)
- Benchmark Python vs Rust for every accelerated path
- Create a "Rust coverage" report: what % of hot paths are accelerated?
- Design new Rust functions for the biggest remaining bottlenecks

**Output**: `reports/rust_coverage_audit.md` + PRs for any quick wins

### Objective 9: 🌐 GRAPH INTELLIGENCE — Knowledge Graph Enrichment
**Clones**: 5,000 (memory_grounded + synthesis strategies)  
**Mission**: Make the knowledge graph actually intelligent:
- Reclassify the 2.2M `associated_with` edges into typed relations
- Run entity extraction on the 6,438 real LONG_TERM memories
- Build topic clusters from actual content (not noise)
- Identify the true bridge nodes between knowledge domains
- Create a "knowledge map" visualization data file
- Wire Ollama into entity extraction for better NER than regex

**Output**: `reports/graph_intelligence.md` + `scripts/enrich_knowledge_graph.py`

### Objective 10: 📖 DOCUMENTATION & LEGIBILITY — Make It Understandable
**Clones**: 3,000 (creative + chain_of_thought strategies)  
**Mission**: Make WhiteMagic's output human-readable:
- Design an Ollama-powered summary layer for all engine outputs
- Create human-readable activation reports (not raw JSON)
- Write a "State of the Galaxy" report template
- Design dashboard data formats for future frontend visualization
- Write clear documentation for each of the 21 analysis engines
- Create example workflows showing how to use clone armies effectively

**Output**: `reports/legibility_improvements.md` + template files

---

## How to Deploy (Technical)

### Option A: Tokio Clone Army (Rust-native, fastest)
```python
from whitemagic.optimization.rust_accelerators import tokio_deploy_clones

# Deploy with all 7 strategies
strategies = ["direct", "chain_of_thought", "adversarial", "creative", 
              "analytical", "synthesis", "memory_grounded"]

result = tokio_deploy_clones(
    "Objective description here", 
    num_clones=10000,
    strategies=strategies
)
# result contains: winner strategy, confidence, votes, elapsed_ms
```

### Option B: Python Async (for MCP tool access)
```python
from whitemagic.cascade.advanced_parallel import AdaptiveParallelExecutor, ParallelTask, ParallelTier

executor = AdaptiveParallelExecutor()
tasks = [ParallelTask(id=f"clone_{i}", func=clone_fn, args=(objective,)) for i in range(1000)]
results = await executor.execute_parallel(tasks, tier=ParallelTier.TIER_6_RALPH_WIGGUM)
```

### Option C: Swarm Orchestrator (for structured decomposition)
```python
from whitemagic.agents.swarm import get_swarm

swarm = get_swarm()
plan = swarm.decompose("Security audit of WhiteMagic codebase", hints=[
    "Search for hardcoded credentials",
    "Audit SQL queries for injection",
    "Check file handlers for path traversal",
    "Analyze sandbox escape risks",
])
assignments = swarm.route(plan.id)
```

---

## Can Clones Access MCPs and Ganas?

### Current State
- **Tokio clones**: Pure compute — they run Rust async tasks with simulated "thought" 
  strategies. They can NOT call MCP tools directly. They're fast (534K/sec) but limited
  to consensus voting on text prompts.
- **Python async clones** (AdaptiveParallelExecutor): CAN call any Python function, 
  including MCP tool handlers. They're slower but have full system access.
- **Swarm orchestrator**: Can decompose and route tasks to registered agents, but doesn't
  directly execute them.
- **WorkerDaemon**: Can execute MCP tool calls from a task queue. This is the closest to
  "clones using Ganas."

### The Gap (v16 Target)
To make clones truly use MCPs/Ganas, we need:
1. **Bridge Tokio→MCP**: Let Rust clones call back into Python MCP handlers via PyO3
2. **Clone-aware dispatch**: Let dispatch_table.py route clone requests through PRAT
3. **Clone memory isolation**: Each clone gets a scratchpad, results merge at consensus

This is Objective 7 (GAS Integration) — the biggest architectural upgrade for v16.

---

## Ralph Loop / Fool's Guard Integration

The **Fool's Guard** (`fool_guard.py`) prevents clone armies from converging on the same
wrong answer (groupthink). It monitors resonance variance and injects "necessary nonsense"
(Ralph Wiggum quotes) when the system gets stuck in over-optimized loops.

For clone armies, this means:
- If >90% of clones agree with high confidence → trigger Fool's Guard
- Redeploy 10% of clones with randomized/adversarial strategies
- Check if the dissenting minority has a valid alternative
- Only accept consensus if it survives the Ralph challenge

This is inspired by the "Devil's Advocate" concept in military decision-making.

---

## Key Files to Reference

| File | Purpose |
|------|---------|
| `whitemagic-rust/src/tokio_clones.rs` | Rust clone army engine (534K/sec) |
| `whitemagic/cascade/advanced_parallel.py` | Python async parallel executor |
| `whitemagic/agents/swarm.py` | Task decomposition + routing + consensus |
| `whitemagic/agents/worker_daemon.py` | Background MCP tool execution |
| `whitemagic/core/intelligence/agentic/fool_guard.py` | Ralph Loop anti-groupthink |
| `whitemagic/optimization/rust_accelerators.py` | Python→Rust bridge |
| `scripts/build_rust_bridge.sh` | Rust compilation (auto-detects, instant when cached) |
| `scripts/wm` | Universal wrapper (always uses .venv with Rust) |
| `scripts/benchmark_gauntlet_v4.py` | Full system benchmark |
| `PARALLEL_CAPABILITIES_REPORT.md` | Today's findings |

---

## Benchmark Numbers to Remember

| Capability | Speed |
|-----------|-------|
| Tokio clone deployment | 534K clones/sec |
| Holographic 5D encode | 105K ops/sec (Rust) |
| StateBoard read | 236K ops/sec |
| Arrow IPC encode (100 memories) | 625µs |
| Keyword extraction | 49.7K ops/sec |
| Galactic batch score (100) | 1.23ms |
| Swarm vote | 3.3µs |
| Store→Search roundtrip | 45ms |
| Parallel 13 engines | 7.5s (2.6× faster than sequential) |

---

## Session Kickoff Script

Run this at the start of next session:
```bash
# Full pre-flight + clone army readiness check
scripts/wm -c "
import whitemagic_rs as rs
from whitemagic.optimization.rust_accelerators import tokio_clone_bench, tokio_deploy_clones
from whitemagic.agents.swarm import get_swarm
from whitemagic.cascade.advanced_parallel import AdaptiveParallelExecutor

# Rust
n = len([f for f in dir(rs) if not f.startswith('_')])
print(f'🦀 Rust: {n} functions')

# Clones
ms, cps = tokio_clone_bench(10000)
print(f'⚡ Tokio: 10K clones in {ms:.1f}ms ({cps:,.0f}/sec)')

# Swarm
swarm = get_swarm()
plan = swarm.decompose('System readiness check')
print(f'🐝 Swarm: {len(plan.subtasks)} subtasks decomposed')

# Parallel executor
exe = AdaptiveParallelExecutor()
print(f'🔀 Parallel executor: ready (max tier: RALPH_WIGGUM=1024)')

print()
print('✅ All systems operational. Ready to deploy 10 clone armies.')
"
```

---

## Priority Order for Execution

1. **Objective 5** (Corpus Denoising) — Do this FIRST. Everything else improves dramatically once noise is removed.
2. **Objective 3** (Archaeological Excavation) — Discover lost treasures while the corpus is fresh in mind.
3. **Objective 4** (Aria Archive) — Compile while we have the full DB loaded.
4. **Objective 1** (Red Team) + **Objective 2** (Performance) — Run simultaneously.
5. **Objective 7** (GAS Integration) — The biggest architectural win for v16.
6. **Objective 9** (Graph Intelligence) — Benefits from clean corpus.
7. **Objective 6** (LoCoMo Benchmark) — Honest self-assessment.
8. **Objective 8** (Rust Coverage) + **Objective 10** (Legibility) — Polish.
