# WhiteMagic Strategic Roadmap — v23.0.0

**Date**: 2026-05-26
**Current State**: v22.2.0 — 2,280 tests passing, 67 skipped, 0 failures
**Target**: v23.0.0 — Production-ready cognitive OS

---

## 1. Audit: 67 Skipped Tests

### Category Breakdown

| Category | Count | Reason | Action |
|----------|-------|--------|--------|
| **Polyglot bridges (Go, Koka, Mojo, Julia)** | 7 | Runtimes not installed | **Archive** — These are optional accelerators. Not critical path. |
| **Haskell FFI tests** | 9 | Haskell bridge not loaded | **Fix** — `LD_PRELOAD` not set in test env. Add to `conftest.py`. |
| **Zig SIMD tests** | 7 | Zig lib not found | **Fix** — Build Zig lib before tests, or skip with clear marker. |
| **Rust memory core tests** | 11 | `whitemagic_rs` not importable | **Fix** — Rust extension not built. Add to CI pipeline. |
| **Web search tests** | 3 | Require live internet | **Archive** — Mark as `@pytest.mark.network` and skip by default. |
| **Rust native module tests** | 4 | `whitemagic_rs` missing accelerators | **Fix** — Same as Rust memory core. |
| **Galactic improvements** | 5 | Missing v-column, search ordering | **Fix** — These test real features that should work. |
| **Dream cycle forced phase** | 1 | Dream cycle not running | **Fix** — Mock the dream cycle for testing. |
| **Salience homeostatic coupling** | 3 | Arbiter not initialized | **Fix** — Initialize arbiter in test fixtures. |
| **Gnosis schema compact** | 1 | Schema not built | **Fix** — Build schema in test setup. |
| **Fusion status** | 2 | Fusion registry not populated | **Fix** — Populate registry in conftest. |
| **Willow async health check** | 1 | Async fixture issue | **Fix** — Use `pytest-asyncio`. |
| **PRAT MCP integration** | 1 | MCP server not running | **Archive** — Requires external MCP server. |
| **Collection skips** | 14 | `.hypothesis` dir, missing deps | **Already handled** — pytest config. |
| **Other** | 3 | Various | **Investigate individually**. |

### Resolution Strategy

**Phase A — Quick Fixes (can resolve ~30 skips)**
1. Add `LD_PRELOAD` to test environment in `conftest.py`
2. Build Rust extension before test collection
3. Build Zig SIMD library before test collection
4. Initialize arbiter and fusion registry in fixtures
5. Fix async health check with `pytest-asyncio`

**Phase B — Archive (~20 skips)**
1. Go/Koka/Mojo/Julia bridges → move to `tests/archive_polyglot/`
2. Web search tests → mark `@pytest.mark.network`
3. PRAT MCP → mark `@pytest.mark.mcp`
4. Deepmind attribution → intentional skip (code quality check)

**Phase C — Investigate (~17 skips)**
1. Galactic improvement tests — verify v-column migration
2. Dream cycle forced phase — mock or implement
3. Gnosis schema compact — build or remove

---

## 2. Audit: Remaining Stubs

### Current Stubs Found

| Module | Stub | Severity | Action |
|--------|------|----------|--------|
| `cyberbrain/nervous_system.py` | `_check_homeostasis` — `NotImplementedError` | Medium | Implement or remove |
| `cyberbrain/nervous_system.py` | `_update_consciousness` — `NotImplementedError` | Medium | Implement or remove |
| `intelligence/hemisphere_agents.py` | `analyze` — `NotImplementedError` | Medium | Implement or remove |
| `intelligence/hemisphere_agents.py` | `synthesize` — `NotImplementedError` | Medium | Implement or remove |
| `tools/handlers/misc.py` | `_stub()` — returns "not yet implemented" | Low | **Intentional** — graceful degradation |
| `tools/gnosis.py` | Agent registry — "not yet initialized" | Low | Initialize on startup |
| `payments/ilp_manager.py` | All functions — informative stubs | Low | **Intentional** — payments require external service |
| `gratitude/ledger.py` | All functions — informative stubs | Low | **Intentional** — requires external service |
| `mesh/client.py` | gRPC stub — optional | Low | **Intentional** — mesh networking is optional |
| `economy/sovereign_market.py` | Cost estimation — placeholder | Low | Replace with real pricing API |

### Resolution Strategy

**Critical (4 stubs)**
1. `cyberbrain/nervous_system._check_homeostasis` — Implement with actual homeostatic check
2. `cyberbrain/nervous_system._update_consciousness` — Implement consciousness update loop
3. `intelligence/hemisphere_agents.analyze` — Implement analytical reasoning
4. `intelligence/hemisphere_agents.synthesize` — Implement synthesis pipeline

**Low Priority (6 stubs)**
5. `tools/gnosis.py` agent registry — Initialize on startup
6. `economy/sovereign_market.py` pricing — Connect to real API
7. `payments/ilp_manager.py` — Keep as stub, document clearly
8. `gratitude/ledger.py` — Keep as stub, document clearly
9. `mesh/client.py` — Keep as optional, document clearly
10. `tools/handlers/misc.py` — Keep as graceful degradation

---

## 3. Shortcomings Resolution Strategy

### 3.1 WASM Runtime — Partial → Ready

**Current**: 178KB module with EdgeEngine, cosine, batch, text search. No SQLite, no embeddings, no holographic coords.

**Target**: Full browser runtime with persistent storage and memory creation.

**Steps**:
1. **SQLite WASM + OPFS** — Use `@sqlite.org/sqlite-wasm` or `wa-sqlite`. Persistent storage survives browser restarts.
2. **ONNX embedding model** — Use `onnxruntime-web` with a lightweight embedding model (e.g., `all-MiniLM-L6-v2` quantized to INT8, ~23MB).
3. **Holographic coordinate computation** — Port `holographic_encoder_5d` from Rust to WASM (already in `wasm.rs` via `whitemagic-math`).
4. **Resonance models in WASM** — Port decay prediction, pattern detection, garden harmony.
5. **Sync layer** — When online, sync local DB with server via REST API. When offline, work locally.

**Estimated effort**: 2-3 weeks

### 3.2 Haskell FFI — Fragile → Robust

**Current**: Requires `LD_PRELOAD` of GHC RTS. Breaks on different GHC versions.

**Target**: Self-contained shared library with bundled RTS.

**Steps**:
1. **Static linking** — Build Haskell library with `-optl-static` or use `ghc -dynamic-too` with bundled RTS.
2. **Alternative**: Use `c2hs` or `inline-c` to generate a pure C wrapper that doesn't depend on GHC runtime.
3. **Alternative**: Replace Haskell hexagram with Rust implementation (already have `iching.rs`).
4. **Deployment**: Bundle the correct GHC RTS libraries in the deployment package.

**Estimated effort**: 3-5 days

### 3.3 Galaxy Visualization — Read-Only → Interactive

**Current**: Beautiful 3D visualization but users can only look, not interact.

**Target**: Interactive galaxy where users can navigate, create associations, and explore by resonance.

**Steps**:
1. **Drag nodes** — Reposition memories in 3D space, update holographic coordinates.
2. **Draw edges** — Click two nodes to create an association, adjust strength.
3. **Resonance navigation** — Click a node, see strongest resonance paths, follow them.
4. **Zone filtering** — Toggle zones on/off, focus on specific galactic regions.
5. **Search overlay** — Type to search, highlight matching nodes, zoom to results.
6. **Memory creation** — Click empty space to create a new memory at that position.

**Estimated effort**: 1-2 weeks

### 3.4 Multi-User Isolation — Not Ready → Ready

**Current**: Single database, no auth, no tenant isolation.

**Target**: Per-user galaxies with authentication and API key management.

**Steps**:
1. **User model** — Add `users` table with auth tokens.
2. **Galaxy isolation** — Each user gets a separate SQLite file or schema.
3. **API key management** — Generate/revoke API keys per user.
4. **Rate limiting** — Per-user rate limits on REST API.
5. **MCP integration** — Expose per-user memory to MCP clients.

**Estimated effort**: 1-2 weeks

### 3.5 Real-Time Bidirectional Sync — Not Ready → Partial

**Current**: SSE is one-way (server → client). No WebSocket.

**Target**: Bidirectional sync for collaborative features.

**Steps**:
1. **WebSocket endpoint** — Add `/ws/events` to REST API.
2. **Client sync** — PWA connects via WebSocket, receives real-time updates.
3. **Conflict resolution** — Last-write-wins or operational transforms.
4. **Offline queue** — Queue mutations when offline, sync when online.

**Estimated effort**: 1 week

---

## 4. Execution Priority

### Phase 1: Foundation (Week 1-2)
- [ ] Resolve 30 skipped tests (LD_PRELOAD, Rust/Zig builds, fixtures)
- [ ] Archive 20 skipped tests (polyglot bridges, network tests)
- [ ] Implement 4 critical stubs (homeostasis, consciousness, hemisphere agents)
- [ ] Initialize agent registry on startup

### Phase 2: WASM Runtime (Week 2-4)
- [ ] SQLite WASM + OPFS integration
- [ ] ONNX embedding model in browser
- [ ] Holographic coordinate computation in WASM
- [ ] Resonance models ported to WASM
- [ ] Sync layer (online/offline)

### Phase 3: Interactive Galaxy (Week 4-5)
- [ ] Drag nodes, update coordinates
- [ ] Draw edges, create associations
- [ ] Resonance navigation
- [ ] Search overlay
- [ ] Memory creation in 3D space

### Phase 4: Multi-User + Real-Time (Week 5-7)
- [ ] User model + auth
- [ ] Galaxy isolation
- [ ] API key management
- [ ] WebSocket endpoint
- [ ] Conflict resolution
- [ ] Offline queue

### Phase 5: Polish + Deploy (Week 7-8)
- [ ] Static Haskell linking (or Rust replacement)
- [ ] Hetzner VPS deployment
- [ ] Load testing
- [ ] Documentation
- [ ] v23.0.0 release

---

## 5. Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Tests passing | 2,280 | 2,310+ (resolve 30 skips) |
| Tests skipped | 67 | 20 (archive 47) |
| Stubs | 4 critical + 6 low | 0 critical + 6 documented |
| WASM features | 4 (EdgeEngine, cosine, batch, text) | 10+ (add SQLite, embeddings, holographic, resonance) |
| Galaxy interactivity | Read-only | Full interactive (drag, draw, navigate) |
| Multi-user | None | Per-user galaxies + auth |
| Real-time | SSE one-way | WebSocket bidirectional |
| Deployment | Local only | Hetzner VPS production |

---

## 6. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| ONNX model too large for WASM | Medium | High | Use INT8 quantization, lazy load |
| SQLite WASM performance poor | Low | Medium | Use OPFS, WAL mode, indexed queries |
| Haskell static linking fails | Medium | Low | Fall back to Rust iching implementation |
| Multi-user auth complexity | Low | Medium | Start simple (API keys), add OAuth later |
| WebSocket scaling issues | Low | Low | Start with single-server, add Redis pub/sub later |

---

*This roadmap is a living document. Update as priorities shift.*
