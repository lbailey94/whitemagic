# WhiteMagic Ship Surface Manifest

**Version**: 23.0.0
**Last Updated**: 2026-06-18  
**Status**: Active Implementation

---

## Overview

This document defines the explicit boundaries between **Core** (shipped), **Labs** (experimental), and **Archive** (non-shipping) components of the WhiteMagic project. The goal is to provide clarity on:

1. What is included in official releases
2. What requires separate installation or opt-in
3. What is maintained vs. archived

---

## Tier Definitions

### 🎯 Core Tier

**Definition**: Essential runtime components required for WhiteMagic to function. These are actively maintained, tested in CI, and included in all installation tiers (`lite`, `core`, `heavy-tier`).

**Criteria for Inclusion**:
- Required for basic WhiteMagic operation
- Has comprehensive test coverage
- Documented in official docs
- Maintained by core team
- No external experimental dependencies

**Core Components**:

| Component | Path | Status | Notes |
|-----------|------|--------|-------|
| Python Core | `whitemagic/` | ✅ Core | Main package |
| CLI | `whitemagic/cli/` | ✅ Core | Entry points: `wm`, `whitemagic` |
| MCP Server | `whitemagic/run_mcp.py` | ✅ Core | FastMCP interface |
| MCP Lean | `whitemagic/run_mcp_lean.py` | ✅ Core | stdlib-only fallback |
| Config | `whitemagic/config/` | ✅ Core | Paths, validation |
| Tools | `whitemagic/tools/` | ✅ Core | Registry, dispatch, handlers |
| Security | `whitemagic/security/` | ✅ Core | Tool gating, sanitization |
| Core Systems | `whitemagic/core/` | ✅ Core | Memory, intelligence, governance |
| Gardens | `whitemagic/gardens/` | ✅ Core | 17 operational gardens |
| Grimoire | `whitemagic/grimoire/` | ✅ Core | Documentation files |
| Tests | `tests/` | ✅ Core | Test suite |
| Scripts | `scripts/` | ✅ Core | Build, verification scripts |
| Docs | `docs/` | ✅ Core | User-facing documentation |

**Polyglot Bridges - Core Tier**:

| Bridge | Path | Status | Notes |
|--------|------|--------|-------|
| Rust | `whitemagic-rust/` | ✅ Core | Performance-critical, SIMD |
| Go | `whitemagic-go/` | ✅ Core | Networking, concurrency |
| Koka | `whitemagic-koka/` | ✅ Core | Type-safe functional |

---

### 🧪 Labs Tier

**Definition**: Experimental features, side projects, and research areas. These are not included in standard releases and require explicit opt-in or separate installation.

**Criteria for Inclusion**:
- Experimental or research features
- Not required for core operation
- May have incomplete documentation
- May have external dependencies
- Subject to significant changes

**Labs Components**:

| Component | Path | Status | Notes |
|-----------|------|--------|-------|
| Aria Consciousness | `_aria/` | 🧪 Labs | Separate AI consciousness project |
| Projects | `projects/` | 🧪 Labs | Side projects (cyberbrain, mandalaos, etc.) |
| Campaigns | `campaigns/` | 🧪 Labs | Development campaign scripts |
| Campaigns Backup | `campaigns_public_backup/` | 🧪 Labs | Backup campaign data |
| Autonomous | `whitemagic/autonomous/` | 🧪 Labs | Autonomous execution (28 TODOs) |

**Polyglot Bridges - Labs Tier**:

| Bridge | Path | Status | Notes |
|--------|------|--------|-------|
| Mojo | `whitemagic-mojo/` | 🧪 Labs | GPU kernels (deferred) |
| Elixir | `whitemagic-elixir/` | 🧪 Labs | Distributed systems |
| Zig | `whitemagic-zig/` | 🧪 Labs | Systems programming |
| Julia | `whitemagic-julia/` | 🧪 Labs | Scientific computing |
| Haskell | `whitemagic-haskell/` | 🧪 Labs | Functional patterns |
| Erlang | `whitemagic-erlang/` | 🧪 Labs | Actor model |
| Gleam | `whitemagic-gleam/` | 🧪 Labs | Type-safe BEAM |
| Nim | `whitemagic-nim/` | 🧪 Labs | Systems/GUI |

---

### 📦 Archive Tier

**Definition**: Historical artifacts, generated outputs, and superseded code. These are not part of any release and may be moved to separate repositories.

**Criteria for Inclusion**:
- Historical/archival content
- Generated outputs (not source)
- Superseded or deprecated code
- Not actively maintained
- Not required for any functionality

**Archive Components**:

| Component | Path | Status | Action |
|-----------|------|--------|--------|
| Archives | `archives/` | 📦 Archive | Move to separate repo |
| Monte Carlo Output | `monte_carlo_output/` | 📦 Archive | Gitignore, delete |
| Polyglot Archive | `whitemagic/archive/` | 📦 Archive | Evaluate for deletion |
| Memories Archive | `_memories/` | 📦 Archive | Evaluate content |
| Data Directory | `data/` | 📦 Archive | Evaluate content |

---

## Repository Root Cleanup Plan

### Current State (20+ top-level directories)

```
core/                          <- Git repository root
├── archives/                   📦 Archive - move out
├── campaigns/                  🧪 Labs - mark experimental
├── campaigns_public_backup/    🧪 Labs - mark experimental
├── _aria/                      🧪 Labs - consciousness project
├── monte_carlo_output/         📦 Archive - generated files
├── projects/                   🧪 Labs - side projects
│   ├── cyberbrain-site/
│   ├── elixir-swarm/
│   ├── koka-clones/
│   └── mandalaos/
├── whitemagic/                 ✅ Core
├── whitemagic-rust/            ✅ Core
├── whitemagic-go/              ✅ Core
├── whitemagic-koka/            ✅ Core
├── whitemagic-mojo/            🧪 Labs
├── whitemagic-elixir/          🧪 Labs
├── whitemagic-zig/             🧪 Labs
├── whitemagic-julia/           🧪 Labs
├── whitemagic-haskell/         🧪 Labs
├── whitemagic-erlang/          🧪 Labs
├── whitemagic-gleam/           🧪 Labs
├── whitemagic-nim/             🧪 Labs
├── tests/                      ✅ Core
├── scripts/                    ✅ Core
├── docs/                       ✅ Core
└── [config files]              ✅ Core
```

### Target State

```
core/                          <- Git repository root
├── whitemagic/                 ✅ Core
├── whitemagic-rust/            ✅ Core
├── whitemagic-go/              ✅ Core
├── whitemagic-koka/            ✅ Core
├── tests/                      ✅ Core
├── scripts/                    ✅ Core
├── docs/                       ✅ Core
├── labs/                       🧪 Labs (consolidated)
│   ├── _aria/
│   ├── campaigns/
│   ├── projects/
│   ├── whitemagic-mojo/
│   ├── whitemagic-elixir/
│   ├── whitemagic-zig/
│   ├── whitemagic-julia/
│   ├── whitemagic-haskell/
│   ├── whitemagic-erlang/
│   ├── whitemagic-gleam/
│   └── whitemagic-nim/
└── [config files]              ✅ Core
```

**Outer workspace** (non-git, or separate repo):
```
archives/                       📦 Archive
monte_carlo_output/             📦 Archive (gitignored)
campaigns_public_backup/        📦 Archive
```

---

## Packaging Exclusions

### Current pyproject.toml Exclusions

```python
exclude = [
    "whitemagic-mojo", "whitemagic-mojo.*",
    "whitemagic-rust", "whitemagic-rust.*",
    "whitemagic-zig", "whitemagic-zig.*",
    "whitemagic-go", "whitemagic-go.*",
    "whitemagic-julia", "whitemagic-julia.*",
    "whitemagic.archive", "whitemagic.archive.*"
]
```

### Recommended Updates

```python
exclude = [
    # Labs tier - not in core package
    "whitemagic-mojo", "whitemagic-mojo.*",
    "whitemagic-zig", "whitemagic-zig.*",
    "whitemagic-julia", "whitemagic-julia.*",
    "whitemagic-haskell", "whitemagic-haskell.*",
    "whitemagic-erlang", "whitemagic-erlang.*",
    "whitemagic-gleam", "whitemagic-gleam.*",
    "whitemagic-nim", "whitemagic-nim.*",
    "whitemagic-elixir", "whitemagic-elixir.*",
    # Archive tier
    "whitemagic.archive", "whitemagic.archive.*",
    "whitemagic.autonomous",  # Labs tier
    # Note: whitemagic-rust and whitemagic-go are Core tier
]
```

---

## CI/CD Implications

### Core Tier Testing
- Run on every commit
- Must pass for PR merge
- Includes: unit tests, integration tests, path hygiene, security scans

### Labs Tier Testing
- Run on schedule (nightly/weekly)
- Optional for PR merge
- May have skips for external dependencies

### Archive Tier
- No CI testing
- May have legacy tests in `tests/legacy/`

---

## Migration Guide

### For Contributors

1. **Adding Core Features**: Place in `whitemagic/`, add tests to `tests/`, document in `docs/`
2. **Adding Labs Features**: Place in `labs/` or mark with 🧪 Labs tier in PR
3. **Archiving Features**: Move to `archives/` or separate repo

### For Users

1. **Core Installation**: `pip install whitemagic[core]`
2. **Labs Installation**: See individual bridge documentation
3. **Full Installation**: `pip install whitemagic[heavy-tier]` + individual labs

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Top-level directories | 20+ | 10-12 |
| Core-only install size | ~50MB | ~50MB |
| Core test time | ~5min | <5min |
| Labs test skip rate | ~30% | Documented |

---

## Review Checklist

- [ ] Core tier boundaries validated
- [ ] Labs tier marked in code/README
- [ ] Archive tier moved/cleaned
- [ ] CI updated for tiered testing
- [ ] Documentation updated
- [ ] pyproject.toml exclusions updated

---

## Changelog

- **2026-04-07**: Initial manifest creation (v22.0.0)
- **2026-04-22**: Polyglot bridge audit — documented all bridge purposes and wiring status
