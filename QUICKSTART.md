# WhiteMagic Quickstart

Get from zero to productive in 5 minutes.

**Performance**: Sub-millisecond core operations with polyglot acceleration (Rust 0.012ms cosine, Zig 0.044ms cosine, Julia 0.001ms neighbor search, memory recall 0.037ms). See full benchmarks below.

---

## 1. Install

> **Important**: On modern Linux (PEP 668), use a virtual environment to avoid `externally-managed-environment` errors:
> ```bash
> python -m venv .venv && source .venv/bin/activate
> ```

```bash
# Minimal (core + CLI)
pip install whitemagic[cli]

# With MCP server
pip install whitemagic[mcp,cli]

# From source (this repo)
git clone https://github.com/whitemagic-ai/whitemagic.git
cd whitemagic
# Using just (recommended):
just setup
# Or manually:
python -m venv .venv && source .venv/bin/activate
pip install -e core/.[dev,mcp,cli]
```

## 2. Verify

```bash
wm doctor
```

Expected output:
```
✅ Core: OK
✅ Memory DB: OK
✅ Tools: 490 registered (462 dispatch + 28 Gana meta-tools)
✅ MCP: fastmcp available
```

## 3. Store a Memory

### CLI
```bash
wm remember "We chose SQLite for Phase 1 because it's zero-config and fast." \
  --title "Architecture Decision: SQLite" \
  --tags architecture,database,v11
```

### Python
```python
from whitemagic.tools.unified_api import call_tool

out = call_tool(
    "create_memory",
    title="Architecture Decision: SQLite",
    content="We chose SQLite for Phase 1 because it's zero-config and fast.",
    tags=["architecture", "database", "v11"],
    type="long_term",
)
print(out["status"])  # "success"
print(out["details"]["memory_id"])  # UUID
```

## 4. Search Memories

### CLI
```bash
wm recall "architecture" --limit 5
```

### Python
```python
out = call_tool("search_memories", query="architecture decisions", limit=5)
for result in out["details"]["results"]:
    print(f"  {result['entry']['title']}: {result['score']:.2f}")
```

## 5. System Introspection (Gnosis)

The Gnosis portal gives you a unified health snapshot of every subsystem:

```python
out = call_tool("gnosis", compact=True)
details = out["details"]

# What you get:
# - harmony: 7-dimension health vector
# - dharma: active rules and profile
# - karma: side-effect audit
# - circuit_breakers: per-tool resilience state
# - capabilities: subsystem matrix
# - resonance: PRAT session context
```

### CLI
```bash
wm status           # Quick health check
wm doctor           # Full diagnostics
```

## 6. Connect via MCP

### Option A: PRAT Mode (Recommended)

28 Gana meta-tools — each a consciousness lens that groups related tools. Compresses 490 tools into a stable, model-friendly surface:

```bash
WM_MCP_PRAT=1 python -m whitemagic.run_mcp
```

Add to your `.mcp.json`:
```json
{
  "mcpServers": {
    "whitemagic": {
      "type": "stdio",
      "command": "python3",
      "args": ["-m", "whitemagic.run_mcp"],
      "env": {
        "WM_MCP_PRAT": "1",
        "WM_SILENT_INIT": "1"
      }
    }
  }
}
```

### Option B: Classic Mode

All 490 individual tools:

```bash
python -m whitemagic.run_mcp
```

### Option C: Lite Mode

92 core tools (faster startup):

```bash
WM_MCP_LITE=1 python -m whitemagic.run_mcp
```

## 7. Explore the Galactic Map

Memories live in a galactic map — no memory is ever deleted, only rotated outward:

```python
out = call_tool("gnosis")
galactic = out["details"].get("galactic", {})
# Zones: CORE → INNER_RIM → MID_BAND → OUTER_RIM → FAR_EDGE
```

## 8. Ethical Governance

Check if an action is ethical:
```python
out = call_tool("evaluate_ethics", action="Delete all user memories")
print(out["details"])  # Ethical assessment with reasoning
```

Switch Dharma profiles:
```python
# default (balanced), creative (relaxed), secure (blocks mutations)
call_tool("set_dharma_profile", profile="secure")
```

## 9. Dream Cycle

WhiteMagic has a **12-phase dream cycle** that runs during idle time, inspired by biological sleep — the brain consolidates memories, prunes weak connections, surfaces serendipitous associations, and integrates new knowledge during rest.

```bash
# CLI commands (new in v23)
wm dream start           # Start automatic dreaming
wm dream stop            # Stop
wm dream status          # Check current phase and stats
wm dream run             # Run a single phase now
wm dream report          # Show dream artifacts
wm dream phases          # List all 12 phases
wm dream read <id>       # Read a specific dream
wm dream promote <id>    # Promote a dream to permanent memory
```

### The 12 Dream Phases

| Phase | What It Does |
|-------|-------------|
| 1. TRIAGE | Quick scan — identify memories needing attention, auto-tag, correct drift |
| 2. CONSOLIDATION | Hippocampal replay — cluster and promote memories to long-term |
| 3. SERENDIPITY | Surface unexpected cross-temporal connections between distant memories |
| 4. GOVERNANCE | Echo chamber detection — check for circular reasoning in memory graph |
| 5. NARRATIVE | Narrative compression — condense verbose memories without losing meaning |
| 6. KAIZEN | Analyze tool usage patterns for continuous improvement hints |
| 7. ORACLE | Consult the Grimoire for contextual spell recommendations |
| 8. DECAY | Mindful forgetting — rotate old memories toward the galactic edge |
| 9. CONSTELLATION | Auto-merge related memory constellations that drifted apart |
| 10. PREDICTION | Predictive drift detection — forecast which memories will become relevant |
| 11. ENRICHMENT | Entity extraction & semantic enrichment of unstructured content |
| 12. HARMONIZE | Wu Xing balance & harmony tuning across all subsystems |

```python
# Python API
from whitemagic.tools.unified_api import call_tool

call_tool("dream_start")    # Start dreaming
call_tool("dream_status")   # Check phase
call_tool("dream_now")      # Trigger a cycle immediately
call_tool("dream_stop")     # Stop
call_tool("dream_list")     # List dream artifacts
```

## 10. Performance

WhiteMagic delivers **sub-millisecond core operations** with polyglot acceleration:

| Operation | Latency | Technology |
|-----------|---------|-----------|
| Julia KD-tree neighbors (100) | **0.001ms** | Julia JSON-stdio |
| Rust cosine similarity (384d) | **0.012ms** | Rust + IceOryx2 zero-copy |
| Zig cosine similarity (384d) | **0.044ms** | Zig C-ABI SIMD |
| Memory recall (by ID) | **0.037ms** | SQLite + connection pool |
| Memory count | **0.025ms** | SQLite index |
| Cached garden aggregation | **0.071ms** | Materialized cache |
| Decay prediction | **0.020ms** | Python scipy |
| Memory search (FTS5) | **0.271ms** | SQLite full-text search |
| Rust galactic batch (100) | **0.445ms** | Rust spatial index |
| Haskell hexagram cast | **0.368ms** | Haskell FFI |
| Pattern detection (100) | **0.823ms** | Python resonance models |

### Polyglot Acceleration Stack

| Language | Role | Status |
|----------|------|--------|
| **Rust** (PyO3 + IceOryx2 + Arrow) | Zero-copy memory operations, SIMD | ✅ Production |
| **Zig** (C-ABI shared lib) | SIMD kernels: HRR, causal, k-means, matmul, batch norm | ✅ Production |
| **Julia** (JSON-stdio) | Scientific computing: stats, forecasting, PageRank, RRF | ✅ Production |
| **Haskell** (FFI + LD_PRELOAD) | Dharma rules, I Ching, dependency graph | ✅ Production |
| **Koka** (compiled binary) | Algebraic effects, PRAT resonance, holographic encoding | ✅ Functional |
| **Elixir** (BEAM) | Concurrent state, OTP GenServer | ✅ Functional |
| **Go** (sidecar daemon) | P2P mesh, libp2p networking | ✅ Functional |

All cores are **free, open-source, no accounts required**.

## 11. Next Steps

- **[AI_PRIMARY.md](AI_PRIMARY.md)** — Authoritative AI-agent contract
- **[SYSTEM_MAP.md](SYSTEM_MAP.md)** — Full system architecture and runtime state
- **[AGENTS.md](AGENTS.md)** — Developer guide (conventions, testing, architecture)
- **[docs/guides/](docs/guides/)** — Example workflows and integration guides
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — How to add tools and accelerators
- **[grimoire/](grimoire/)** — The 28 Lunar Mansion chapters (cognitive taxonomy)

---

## Troubleshooting

### "No module named 'whitemagic'"
```bash
pip install -e .  # If developing from source
# or
pip install whitemagic  # If installing from PyPI
```

### "fastmcp not installed"
```bash
pip install whitemagic[mcp]
```

### Tests hang or are slow
Set test isolation:
```bash
WM_STATE_ROOT=/tmp/wm_test WM_SILENT_INIT=1 pytest tests/ -q
```

### MCP server doesn't start
1. Check Python version: `python --version` (needs 3.10+)
2. Check fastmcp: `python -c "import fastmcp; print('ok')"`
3. Check env: `WM_SILENT_INIT=1 python -c "from whitemagic.tools.unified_api import call_tool; print(call_tool('capabilities')['status'])"`

### Memory DB errors
```bash
wm doctor  # Diagnoses DB issues
export WM_STATE_ROOT=/tmp/fresh_wm  # Start fresh if needed
```

---

## Gratitude

WhiteMagic is **free and open-source** (MIT). If it's been useful to you, gratitude is welcome but never expected.

- **XRPL Tip Address**: `YOUR_XRPL_ADDRESS`
- **Contact**: contact@whitemagic.dev
