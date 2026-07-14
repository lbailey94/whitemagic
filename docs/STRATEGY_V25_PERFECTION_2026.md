# Strategy: WhiteMagic v25 Perfection — 5-Tier Packaging, Docker, Docs, Benchmarks, Adapters

**Version**: v25.0.0
**Created**: 2026-07-14
**Status**: Planning
**Goal**: Bring WhiteMagic to 100% — clean 5-tier installation topology, `whitemagic grow` unfold experience, Dockerfile with 3 targets (seed/core/heavy), per-tool docs, benchmarks, framework adapters — before registry listing and website update.

---

## Research Findings (2026-07-14)

### `uvx` is the standard for Python MCP servers
The MCP ecosystem has converged on `uvx` (uv tool run) as the primary way to distribute and run Python MCP servers. It's Python's `npx` — one command, no pip install, no venv setup:

```json
// Claude Desktop config
{
  "mcpServers": {
    "whitemagic": {
      "command": "uvx",
      "args": ["whitemagic-mcp"]
    }
  }
}
```

If we publish `whitemagic-mcp` to PyPI, `uvx whitemagic-mcp` becomes a **zero-setup, one-command install+run**. This is the distribution path the ecosystem expects.

### `uv` in Docker is the 2026 best practice
Modern Dockerfiles use `uv` instead of `pip` for multi-stage builds:
- Copy uv binary from `ghcr.io/astral-sh/uv:latest`
- `uv sync --frozen --no-install-project` for cached dependency layers
- Distroless runtime images reach ~130MB
- Non-root user, HEALTHCHECK, signal handling all standard

### Docker MCP Catalog
Docker has a curated MCP catalog at `hub.docker.com/mcp` with 300+ verified server images. This is a distribution channel to target alongside PyPI.

### DXT (Desktop Extensions)
Anthropic's one-click install for Claude Desktop. Bundles server + deps + config into a `.dxt` file. Currently Claude Desktop only. Future consideration.

### Tarball/zip on the website — not recommended
`pip install` can install from URLs (`pip install https://whitemagic.dev/downloads/whitemagic-25.0.0.tar.gz`), but this is strictly worse than `uvx whitemagic-mcp`:
- User still needs Python + pip installed
- User still needs to resolve dependencies
- No automatic updates, no version management
- The air-gapped/offline use case is better served by `wm-seed` (zero-dep Rust binary)

**Decision**: Skip tarball distribution. The three surfaces (wm-seed binary, `uvx whitemagic-mcp`, Docker) cover every use case.

---

## Installation Topology — 5 Tiers

WhiteMagic has 7 capability layers with different dependency profiles. The installation topology maps these into 5 strict-superset tiers:

```
Tier 0: wm-seed (Rust binary)
  ├── 30 tools, zero deps, single statically-compiled binary
  ├── curl https://whitemagic.dev/install.sh | sh
  ├── SQLite + FTS5 directly from Rust, no Python runtime
  └── For: minimal MCP memory, embedded systems, CI/CD, air-gapped envs

Tier 1: uvx whitemagic-mcp  (or: pip install whitemagic-mcp)
  ├── 759 tools (Python MCP server), ~50MB install
  ├── Dependencies: whitemagic core + mcp SDK + fastembed (50MB embeddings)
  ├── Semantic search out of the box via fastembed (no torch needed)
  ├── No CLI, no API server, no polyglot, no heavy ML
  ├── uvx = zero-setup one-command run (recommended for MCP clients)
  └── For: AI agent developers who want memory + governance via MCP

Tier 2: pip install whitemagic
  ├── 759 tools + CLI + API server + full tool surface
  ├── Adds: click, rich, fastapi, uvicorn, sqlalchemy, aiohttp
  ├── ~100MB install, includes `whitemagic grow` command
  └── For: developers building on WhiteMagic as a platform

Tier 3: pip install whitemagic[heavy]
  ├── Adds: torch, sentence-transformers, faiss, scipy, scikit-learn
  ├── ~2.5GB install, full ML-powered semantic search
  ├── Rust accelerator wheel (whitemagic-rust) auto-detected if present
  └── For: production deployments with heavy recall workloads

Tier 4: Full polyglot (manual install)
  ├── Rust: pip install whitemagic-rust (maturin wheel)
  ├── Julia/Elixir/Haskell/Koka/Zig: from source (polyglot/)
  ├── Each bridge auto-detected, falls back to Python if absent
  ├── WM_SKIP_POLYGLOT=1 to disable all bridges
  └── For: research, maximum performance, cognitive science experiments
```

### Distribution Channels by Tier

| Tier | PyPI | uvx | Docker | GitHub Releases | MCP Registry |
|------|------|-----|--------|-----------------|-------------|
| 0 (seed) | — | — | `seed` target | ✅ binary assets | ✅ |
| 1 (mcp) | ✅ `whitemagic-mcp` | ✅ `uvx whitemagic-mcp` | `core` target | — | ✅ |
| 2 (full) | ✅ `whitemagic` | — | `core` target | — | ✅ |
| 3 (heavy) | ✅ `whitemagic[heavy]` | — | `heavy` target | — | — |
| 4 (polyglot) | `whitemagic-rust` on PyPI | — | `heavy` target | source | — |

### The "Unfold" Experience — `whitemagic grow`

First run of Tier 1 or Tier 2 prints:

```
$ whitemagic-mcp
  WhiteMagic MCP Server v25.0.0 — Seed Mode
  759 tools available | Embeddings: fastembed (lightweight)

  ℹ  Optional upgrades available:
     • whitemagic[heavy]    — Full ML embeddings (2.5GB, better recall)
     • whitemagic-rust      — Rust SIMD acceleration (3-10x faster search)
     • Polyglot bridges     — Julia/Elixir/Haskell/Koka/Zig (advanced cognition)

  Run `whitemagic grow` to install recommended upgrades.
  Or set WM_SILENT_INIT=1 to suppress this message.
```

The `whitemagic grow` command:
1. Detects installed capabilities (fastembed, sentence-transformers, Rust, polyglot)
2. Detects hardware (GPU, AVX2/AVX-512, disk space)
3. Recommends upgrades based on hardware profile
4. Prompts for confirmation, installs via pip subprocess
5. Re-initializes and prints summary of unlocked capabilities

### Graceful Degradation Matrix

| Layer | With It | Without It (Fallback) |
|-------|---------|----------------------|
| **fastembed** (Tier 1) | Semantic search via 50MB ONNX model | FTS5 keyword-only search |
| **sentence-transformers** (Tier 3) | Higher-quality embeddings, multilingual | fastembed or FTS5 fallback |
| **Rust bridge** (Tier 3/4) | 3-10x faster cosine/HNSW/ternary | Python numpy/scipy equivalents |
| **Julia bridge** (Tier 4) | Neuromodulation dynamics | Python dict-lookup fallback |
| **Elixir bridge** (Tier 4) | Ripple tagging (temporal propagation) | Python sequential fallback |
| **Haskell bridge** (Tier 4) | Replay simulation (consolidation) | Python loop fallback |
| **Koka bridge** (Tier 4) | Compile-time effect enforcement | Python runtime effect checking |
| **Zig bridge** (Tier 4) | SIMD-accelerated batch ops | Python numpy fallback |

**Key principle**: Every polyglot bridge checks `WM_SKIP_POLYGLOT` and falls back to Python. No bridge is required for core functionality.

---

## Current State Assessment

### What Works
- **MCP server**: `run_mcp_lean.py` — 1,737 lines, stdio + HTTP, lazy init, 28 Gana meta-tools, `wm` seed mode
- **wm-seed Rust binary**: 725 lines in `core/whitemagic-rust/src/bin/wm_seed.rs` — 30 tools (create/search/read memory, gnosis, dharma, karma, harmony, health, manifest, capabilities), SQLite + FTS5 from Rust, zero Python deps
- **pyproject.toml**: Dynamic version from `core/VERSION`, tiered extras, console scripts (`wm`, `whitemagic`)
- **Dockerfile**: Multi-stage but stale (v24.1.0, wrong paths, `run_mcp` instead of `run_mcp_lean`)
- **server.json / mcp-registry.json**: Registry manifests at v25.0.0
- **Tool registry**: 51 registry_defs files, `ToolDefinition` dataclass
- **generate_tool_docs.py**: Script exists (266 lines), not yet run for production docs
- **Polyglot graceful degradation**: All bridges check `WM_SKIP_POLYGLOT`, fall back to Python
- **Tool count**: 759 callable tools, 756 dispatch entries, 28 Gana meta-tools

### What's Broken or Missing
1. **No `whitemagic-mcp` standalone package** — `pip install whitemagic-mcp` doesn't exist
2. **No `whitemagic grow` command** — no guided upgrade experience
3. **No `wm-seed` binary distribution** — builds locally but no `curl | sh` or GitHub Releases binary
4. **Dockerfile is stale** — wrong paths, wrong entry point, wrong version, no `seed` target
5. **No per-tool docs generated** — `docs/api/` doesn't exist
6. **No benchmarks** — no comparison against Mem0, Zep, LangChain
7. **No framework adapters** — no LangChain/CrewAI/AutoGen integration
8. **`fastembed` not in default deps** — should be in `whitemagic-mcp` base for out-of-box semantic search

---

## Phase 1: Three Distribution Surfaces — `whitemagic-mcp` + `whitemagic grow` + `wm-seed`

### Goal
Create three distribution surfaces: (a) `whitemagic-mcp` PyPI package with fastembed by default, (b) `whitemagic grow` guided upgrade command, (c) `wm-seed` binary distribution via curl | sh and GitHub Releases.

### 1a: `whitemagic-mcp` Package (Tier 1)

```
mcp-package/
├── pyproject.toml          # name="whitemagic-mcp", depends on whitemagic + mcp + fastembed
├── src/
│   └── whitemagic_mcp/
│       ├── __init__.py     # re-exports run_mcp_lean.main
│       ├── __main__.py     # python -m whitemagic_mcp → launches MCP server
│       └── grow.py         # `whitemagic grow` implementation
├── .github/
│   └── workflows/
│       └── publish.yml     # Auto-publish to PyPI on tag push
└── README.md               # Quick start, Claude Desktop config, env vars, upgrade guide
```

### Tasks
- [ ] Create `mcp-package/pyproject.toml`:
  - name=`whitemagic-mcp`, version=25.0.0
  - dependencies: `whitemagic>=25.0.0`, `mcp>=1.0.0`, `fastembed>=0.2.0`
  - console scripts: `whitemagic-mcp = whitemagic_mcp:main`, `whitemagic-grow = whitemagic_mcp.grow:main`
  - Use `src/` layout per 2026 PyPI best practices
- [ ] Create `mcp-package/src/whitemagic_mcp/__init__.py` — thin wrapper importing `whitemagic.run_mcp_lean.main`
- [ ] Create `mcp-package/src/whitemagic_mcp/__main__.py` — `from whitemagic_mcp import main; main()`
- [ ] Create `mcp-package/README.md` — MCP-only quick start, **uvx config** for Claude Desktop, env vars, upgrade guide
- [ ] Add GitHub Actions workflow for auto-publish to PyPI on tag push
- [ ] Verify `pip install -e mcp-package/` works and `whitemagic-mcp` launches the server
- [ ] Verify `uvx whitemagic-mcp` works (the primary recommended install method)
- [ ] Verify `python -m whitemagic_mcp` works as alternative invocation
- [ ] Verify `whitemagic-mcp --http --port 8770` launches HTTP server
- [ ] Update `server.json` — add `uvx` as recommended command in packages section
- [ ] Update `mcp-registry.json` — add `uvx` to installation section

### 1b: `whitemagic grow` Command

### Tasks
- [ ] Create `mcp-package/src/whitemagic_mcp/grow.py`:
  - `detect_capabilities()` — check for fastembed, sentence-transformers, whitemagic-rust, polyglot bridges
  - `detect_hardware()` — GPU (nvidia-smi), AVX2/AVX-512 (cpuinfo), disk space, RAM
  - `recommend_upgrades()` — map hardware profile to recommended tiers
  - `install_upgrade()` — pip subprocess with confirmation prompt
  - `main()` — CLI entry: print current state, recommend, prompt, install, re-init
- [ ] Add startup message to `run_mcp_lean.py` — print upgrade hints when not `WM_SILENT_INIT`
- [ ] Verify `whitemagic grow` detects current capabilities and recommends correct upgrades
- [ ] Verify `WM_SILENT_INIT=1` suppresses the startup message

### 1c: `wm-seed` Binary Distribution (Tier 0)

### Tasks
- [ ] Create `scripts/install_seed.sh` — curl | sh installer:
  - Detect OS (linux/macOS) and architecture (x86_64/aarch64)
  - Download from GitHub Releases (`https://github.com/lbailey94/whitemagic/releases/latest`)
  - Verify checksum, install to `/usr/local/bin/wm-seed`
  - Print quick start: `wm-seed serve` or `wm-seed init`
- [ ] Add GitHub Actions workflow to build and publish `wm-seed` binaries:
  - Build for linux-x86_64, linux-aarch64, macos-x86_64, macos-aarch64
  - Upload as release assets on tag push
  - Generate checksums file
- [ ] Add `wm-seed` documentation to `mcp-package/README.md` and website
- [ ] Verify `wm-seed serve` launches MCP stdio server with 30 tools
- [ ] Verify `wm-seed init` scaffolds state directory with seed memories

### Acceptance Criteria
- `pip install whitemagic-mcp` installs MCP server + fastembed, <50MB
- `whitemagic-mcp` command launches stdio MCP server with 759 tools
- `whitemagic grow` detects capabilities, recommends upgrades, installs with confirmation
- `curl https://whitemagic.dev/install.sh | sh` installs `wm-seed` binary
- `wm-seed serve` launches MCP stdio server with 30 tools, zero Python deps
- Startup message shows upgrade hints, `WM_SILENT_INIT=1` suppresses it

---

## Phase 2: Dockerfile Modernization — 3 Targets (seed/core/heavy)

### Goal
Update the Dockerfile to v25.0.0 with 3 targets: `seed` (Rust binary only, ~20MB), `core` (Tier 1 Python + fastembed, ~200MB), `heavy` (Tier 3 with ML + polyglot, ~1GB). Use `uv` for dependency management per 2026 best practices.

### Tasks
- [ ] Add `seed` target — Rust-only, no Python:
  - `FROM rust:1.75-slim AS seed-builder` → build `wm-seed` binary
  - `FROM debian:bookworm-slim AS seed` → copy binary, ~20MB image
  - `CMD ["wm-seed", "serve"]`
- [ ] Update `core` target (was `slim`):
  - Use `uv` for dependency installation: `COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/`
  - `uv sync --frozen --no-install-project` for cached deps, then `uv sync --frozen` for final
  - Fix source paths: `COPY core/whitemagic-rust/`, `COPY core/whitemagic/`
  - Fix entry point: `CMD ["python", "-m", "whitemagic.run_mcp_lean"]`
  - Add `fastembed` to core install
  - Set `WM_MCP_PRAT=2` (Seed mode) as default env var
  - Update labels: tool count 759, version 25.0.0, correct GitHub URL
  - Non-root user, HEALTHCHECK, `PYTHONUNBUFFERED=1`, `PYTHONDONTWRITEBYTECODE=1`
  - Remove stale `whitemagic-mojo` reference (removed in v23.2.0)
- [ ] Update `heavy` target:
  - Install `.[heavy]` extras via uv
  - Copy polyglot source trees (no Mojo)
  - Install Rust accelerator wheel from builder stage
- [ ] Add `.dockerignore` to exclude node_modules, .git, WindsurfRips, test exports, archives
- [ ] Update `docker-compose.yml` to use `run_mcp_lean` and v25 env vars
- [ ] Test: `docker build --target seed -t whitemagic:seed .` succeeds (~20MB)
- [ ] Test: `docker build --target core -t whitemagic:core .` succeeds (~200MB)
- [ ] Test: `docker run --rm -i whitemagic:seed` launches MCP server (30 tools, no Python)
- [ ] Test: `docker run --rm -i whitemagic:core` launches MCP server (759 tools)
- [ ] Submit to Docker MCP Catalog (`hub.docker.com/mcp`) after build verification

### Acceptance Criteria
- `docker build --target seed -t whitemagic:seed .` — image <30MB, launches `wm-seed serve`
- `docker build --target core -t whitemagic:core .` — image <300MB, launches `run_mcp_lean` with fastembed
- `docker build -t whitemagic:heavy .` — image <1.2GB, full ML + Rust + polyglot
- `docker run --rm -p 8770:8770 whitemagic:core python -m whitemagic.run_mcp_lean --http --port 8770` works
- Non-root user, HEALTHCHECK, signal handling all present

---

## Phase 3: Per-Tool Documentation Generation

### Goal
Generate comprehensive per-tool documentation for all 759 tools — markdown reference, OpenAPI spec, and machine-readable JSON catalog. Deploy to `docs/api/`.

### Tasks
- [ ] Update `scripts/generate_tool_docs.py`:
  - Fix OpenAPI info version (1.0.0 → 25.0.0) and description ("490+ tools" → actual count)
  - Add Gana mapping to each tool doc (which Gana routes to this tool)
  - Add example responses from `SAFE_DEFAULTS` or dispatch table
  - Add `--format json` option for machine-readable catalog
  - Add category index pages (one per ToolCategory)
  - Add Gana index page (28 chapters, each listing its nested tools)
- [ ] Run `python scripts/generate_tool_docs.py --output docs/api/ --openapi docs/openapi.json`
- [ ] Verify all 759 tool markdown files generated
- [ ] Verify `docs/api/README.md` index page lists all tools
- [ ] Verify `docs/openapi.json` is valid OpenAPI 3.0
- [ ] Add `docs/api/` to `.gitignore` exclusions (generated, but tracked for registry)
- [ ] Create `docs/api/QUICKSTART.md` — how to use WhiteMagic tools from Python, from MCP client, from HTTP

### Documentation Structure
```
docs/api/
├── README.md                    # Master index (all 759 tools)
├── QUICKSTART.md                # Getting started guide
├── openapi.json                 # OpenAPI 3.0 spec
├── catalog.json                 # Machine-readable tool catalog
├── categories/                  # Per-category indexes
│   ├── memory.md
│   ├── governance.md
│   ├── security.md
│   ├── system.md
│   ├── gana.md
│   ├── session.md
│   └── ...
├── gana/                        # Per-Gana indexes (28 chapters)
│   ├── gana_horn.md
│   ├── gana_neck.md
│   └── ...
└── tools/                       # Per-tool pages (759 files)
    ├── search_memories.md
    ├── create_memory.md
    └── ...
```

### Acceptance Criteria
- `docs/api/` contains 759+ tool markdown files
- `docs/api/README.md` lists all tools with category, safety, description
- `docs/openapi.json` validates with `swagger-cli validate`
- `docs/api/catalog.json` contains all tool definitions in machine-readable format
- Every tool doc includes: name, description, category, safety, input schema, example invocation, example output, Gana routing

---

## Phase 4: Benchmarks and Evals

### Goal
Create a standardized benchmark suite comparing WhiteMagic against Mem0, Zep, and raw LangChain memory. Produce publishable numbers.

### Tasks
- [ ] Create `benchmarks/` directory at repo root
- [ ] Create `benchmarks/dataset.py` — generates/loads test datasets:
  - 100 conversations × 20 turns (2,000 memories)
  - 1,000 memories with known semantic relationships
  - 10 query templates × 100 variations (1,000 queries)
- [ ] Create `benchmarks/mem0_benchmark.py` — Mem0 comparison:
  - Install: `pip install mem0ai`
  - Operations: add memory, search memory, get all, update, delete
  - Metrics: latency (p50/p95/p99), throughput (ops/sec), memory usage, recall quality
- [ ] Create `benchmarks/zep_benchmark.py` — Zep comparison (if available):
  - Install: `pip install zep-python`
  - Same operations and metrics
- [ ] Create `benchmarks/langchain_benchmark.py` — LangChain ConversationBufferMemory comparison:
  - Install: `pip install langchain`
  - Same operations and metrics
- [ ] Create `benchmarks/whitemagic_benchmark.py` — WhiteMagic benchmark:
  - Uses `call_tool("search_memories", ...)` and `call_tool("create_memory", ...)`
  - Same operations and metrics
  - Test with both fastembed (lightweight) and sentence-transformers (heavy) embeddings
- [ ] Create `benchmarks/eval_recall.py` — recall quality evaluation:
  - Known-answer queries (queries with known correct memory IDs)
  - Metrics: recall@1, recall@5, recall@10, MRR (mean reciprocal rank)
  - Compare WhiteMagic HNSW + FTS5 vs Mem0 vs Zep vs LangChain
- [ ] Create `benchmarks/run_all.py` — orchestrates all benchmarks, generates report
- [ ] Create `benchmarks/REPORT.md` — template for results (filled after running)
- [ ] Run benchmarks and record results

### Benchmark Matrix
| Operation | WhiteMagic | Mem0 | Zep | LangChain |
|-----------|-----------|------|-----|-----------|
| Add memory (1K) | ?ms | ?ms | ?ms | ?ms |
| Search (1K memories) | ?ms | ?ms | ?ms | ?ms |
| Recall@1 | ?% | ?% | ?% | ?% |
| Recall@5 | ?% | ?% | ?% | ?% |
| Memory usage | ?MB | ?MB | ?MB | ?MB |

### Acceptance Criteria
- `python benchmarks/run_all.py` executes all benchmarks and generates report
- Results table comparing WhiteMagic vs at least 1 alternative (Mem0)
- Numbers are reproducible (deterministic dataset, fixed seed)
- Report includes: latency, throughput, recall quality, memory usage

---

## Phase 5: Framework Adapters

### Goal
Create adapters that let users plug WhiteMagic into popular AI frameworks with 2-3 lines of code.

### Tasks
- [ ] Create `core/whitemagic/adapters/` directory
- [ ] Create `core/whitemagic/adapters/__init__.py` — exports all adapters

### LangChain Adapter
- [ ] Create `core/whitemagic/adapters/langchain.py`:
  - `WhiteMagicMemory` class — extends `BaseChatMemory` from LangChain
  - Methods: `save_context()`, `load_memory_variables()`, `clear()`
  - Uses `call_tool("create_memory", ...)` for saves
  - Uses `call_tool("search_memories", ...)` for loads
  - Configurable galaxy, user_id, search limit
- [ ] Create `core/whitemagic/adapters/langchain_tools.py`:
  - `WhiteMagicTool` class — wraps any WhiteMagic tool as a LangChain `Tool`
  - `WhiteMagicToolkit` class — exposes search/create/health as a toolkit
  - `from_langchain_agent()` factory — creates tools from an existing LangChain agent
- [ ] Test: LangChain agent can use WhiteMagic for memory and tool execution

### CrewAI Adapter
- [ ] Create `core/whitemagic/adapters/crewai.py`:
  - `WhiteMemory` class — CrewAI memory backend
  - `WhiteMagicCrewTools` — CrewAI tool collection
  - Uses same `call_tool` interface

### AutoGen Adapter
- [ ] Create `core/whitemagic/adapters/autogen.py`:
  - `WhiteMagicAgent` — AutoGen agent with WhiteMagic memory
  - `register_whitemagic_tools()` — registers WM tools with AutoGen registry

### PydanticAI Adapter
- [ ] Create `core/whitemagic/adapters/pydantic_ai.py`:
  - `WhiteMagicToolset` — PydanticAI toolset
  - Uses `ToolDefinition.to_openai_function()` for schema conversion

### Tasks (continued)
- [ ] Add `adapters` extra to `pyproject.toml`: `adapters = ["langchain>=0.1.0", "crewai>=0.1.0", "pydantic-ai>=0.0.1"]`
- [ ] Create `core/whitemagic/adapters/README.md` — adapter usage examples
- [ ] Create tests: `core/tests/unit/test_adapters.py` — mock-based tests for each adapter
- [ ] Verify each adapter can be imported independently (no hard deps)

### Acceptance Criteria
- `pip install whitemagic[adapters]` installs adapter dependencies
- `from whitemagic.adapters.langchain import WhiteMagicMemory` works
- LangChain agent with WhiteMagic memory completes a conversation
- Each adapter has tests and documentation
- Adapters gracefully degrade if framework not installed

---

## Phase 6: Final Polish (Pre-Registry)

### Goal
Clean up remaining issues before listing on registries.

### Tasks
- [ ] Run full test suite: `cd core && python -m pytest tests/ --ignore=tests/archive_v14 --ignore=tests/archive_v11 --ignore=tests/archive --ignore=tests/archive_polyglot --ignore=tests/legacy --ignore=tests/adhoc --ignore=tests/verify -q --timeout=30`
- [ ] Run `python scripts/check_doc_drift.py` and fix any drift
- [ ] Verify `pip install whitemagic-mcp` works from clean venv and launches server
- [ ] Verify `uvx whitemagic-mcp` works (primary recommended method)
- [ ] Verify `pip install whitemagic` works from clean venv with CLI
- [ ] Verify `whitemagic grow` detects capabilities and recommends upgrades
- [ ] Verify `curl https://whitemagic.dev/install.sh | sh` installs `wm-seed`
- [ ] Verify `docker build --target seed -t whitemagic:seed .` succeeds
- [ ] Verify `docker build --target core -t whitemagic:core .` succeeds
- [ ] Verify `python scripts/generate_tool_docs.py --output docs/api/ --openapi docs/openapi.json` generates complete docs
- [ ] Update `llms.txt` with v25.0.0 tool count, 5-tier topology, new package info
- [ ] Update `AI_PRIMARY.md` with v25.0.0 changes
- [ ] Update `core/.well-known/agent.json` tool count
- [ ] Update `public/.well-known/ai-agent.json` tool count
- [ ] Run benchmarks and record results in `benchmarks/REPORT.md`
- [ ] Commit all changes with scoped commits
- [ ] Push to all three remotes

### Registry Submission Checklist (after polish)
- [ ] Submit to MCP Registry (registry.modelcontextprotocol.io) — `server.json` ready
- [ ] Submit to Docker MCP Catalog (hub.docker.com/mcp) — after Docker build verified
- [ ] Submit to MCPize (https://mcpize.com)
- [ ] Submit to MCPFind (https://mcpfind.com)
- [ ] Submit to MCP Marketplace (https://mcpmarketplace.com)
- [ ] Consider DXT packaging for Claude Desktop one-click install (future)
- [ ] Update website with v25.0.0 content, benchmark results, adapter examples
- [ ] Publish blog post: "WhiteMagic v25: 5-Tier Installation, 759 MCP Tools, Zero-Dep Binary, Framework Adapters"

---

## Execution Order

```
Phase 1 (3 distribution surfaces)    ──┐
Phase 2 (Dockerfile 3 targets)       ──┼── can run in parallel
Phase 3 (per-tool docs)              ──┘
         │
         ▼
Phase 4 (benchmarks)                 ──── depends on Phase 3 for tool catalog
         │
         ▼
Phase 5 (framework adapters)         ──── depends on Phase 1 for package structure
         │
         ▼
Phase 6 (final polish)               ──── depends on all above
         │
         ▼
Registry submission + website update
```

## Time Estimates (per Time Dilation Bias rules — actual will be 3-5x faster)

| Phase | Estimated | Likely Actual |
|-------|-----------|---------------|
| 1: whitemagic-mcp + grow + wm-seed | 45 min | ~15 min |
| 2: Dockerfile (3 targets) | 25 min | ~8 min |
| 3: Per-tool docs | 15 min | ~5 min |
| 4: Benchmarks | 45 min | ~15 min |
| 5: Framework adapters | 60 min | ~20 min |
| 6: Final polish | 30 min | ~10 min |
| **Total** | **3.7 hr** | **~73 min** |

---

## Key Decisions

1. **5-tier installation topology**: Tier 0 (wm-seed binary) → Tier 1 (whitemagic-mcp) → Tier 2 (whitemagic) → Tier 3 (heavy) → Tier 4 (polyglot). Each tier is a strict superset of the previous.

2. **`fastembed` in Tier 1 by default**: 50MB ONNX model gives real semantic search out of the box. Without it, search falls back to FTS5 keyword-only. The 50MB cost is worth it for usable search.

3. **`whitemagic grow` guided unfold**: Users start at Tier 1 and grow upward. The command detects hardware (GPU, AVX2) and recommends appropriate upgrades. Suppressible via `WM_SILENT_INIT=1`.

4. **`wm-seed` as independent binary**: Zero Python deps, statically compiled Rust, 30 essential tools. Distributed via `curl | sh` and GitHub Releases. The only MCP server with a zero-dependency binary distribution.

5. **Docker 3 targets**: `seed` (~20MB, Rust only), `core` (~200MB, Python + fastembed), `heavy` (~1GB, full ML + polyglot). `core` is the default `docker build` target.

6. **Two PyPI packages, one codebase**: `whitemagic` (full, Tier 2+) and `whitemagic-mcp` (MCP-only, Tier 1). The MCP package depends on `whitemagic` — it's a convenience wrapper, not a fork.

7. **Generated docs, not hand-written**: `docs/api/` is generated by `generate_tool_docs.py` and tracked in git. Regenerate on version bumps.

8. **Benchmarks use deterministic datasets**: Fixed seed, known answers. Results are reproducible and publishable.

9. **Adapters are optional extras**: `pip install whitemagic[adapters]` installs LangChain/CrewAI/AutoGen deps. Adapters gracefully degrade if framework not installed.

10. **No new MCP tools in this phase**: This is polish and packaging, not feature development. The 759 tools are the product.

11. **TypeScript SDK / PWA stays separate**: The browser/PWA/WASM surface was a side project and remains in `sdk/typescript/` and `lib/`. Not part of the pip/Docker distribution pipeline.

12. **`uvx` as primary recommended install**: The MCP ecosystem has converged on `uvx` for Python MCP servers. `uvx whitemagic-mcp` is the one-command zero-setup path. `pip install` remains as fallback.

13. **No tarball/zip distribution**: Strictly worse than `uvx`/pip for online users, and `wm-seed` binary is better for offline/air-gapped. Three distribution surfaces cover all use cases.

14. **`uv` in Docker**: Modern best practice — faster installs, better caching, smaller images. Use `ghcr.io/astral-sh/uv:latest` binary in multi-stage builds.

15. **Docker MCP Catalog as distribution channel**: Submit verified images to `hub.docker.com/mcp` alongside PyPI for Docker-native discovery.

---

## Risk Mitigation

- **PyPI namespace conflict**: Check `whitemagic-mcp` availability on PyPI before creating package. Fallback: `whitemagic-mcp-server`.
- **Docker build failures**: Test `seed` target first (fewest dependencies), then `core`, then `heavy`.
- **Benchmark fairness**: Use identical datasets and operations across all systems. Document hardware specs. Run all benchmarks on same machine.
- **Adapter breakage**: Framework APIs change frequently. Pin minimum versions, test against latest. Use duck typing where possible.
- **Doc generation timeouts**: `generate_tool_docs.py` loads full registry. If slow, add `--limit` flag for testing.
- **GitHub Releases binary size**: `wm-seed` statically compiled Rust binary should be <10MB. If larger, strip debug symbols.
- **Cross-platform `wm-seed`**: Test on linux-x86_64, linux-aarch64, macos-x86_64, macos-aarch64. Use `cross` tool for cross-compilation if needed.
