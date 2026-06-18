# What's Next — Recommendation (2026-06-18)

**Source**: STRATEGIC_ROADMAP_V23.md + TACTICAL_PLAN_2026-06-08.md + current state audit
**Date**: 2026-06-18
**Author**: opencode (minimax-m3) on behalf of Lucas
**Goal**: Pick the v22.3 (incremental) vs v23.0 (production release) path

---

## Where we are today (post-session)

Test baseline: 1,470 passed, 2 skipped, 0 failed (was 1,024 at start of session)
- Fixed: 4 reverted docstring files (Phase 1)
- Fixed: 162 undocumented public classes → 0 (Phase 2)
- Added: `ipc_try_receive` API + 6 new IPC tests (Phase 3)
- Fixed: surprise_gate RuntimeError bug (+4 tests) (Phase 4)
- Fixed: 4 conftest collection errors (+34 tests) (Phase 5)
- Fixed: AI_PRIMARY drift label (Phase 6)
- Fixed: ship-check absolute path in test fixture (Phase 7)

Memory stress: PASS, 0 errors, p95 latencies all under 20ms
Omega test: 1,966/1,969 (1 pre-existing ship-check failure, 14 pre-existing
absolute_path hits in scripts/, not from this session)

---

## My recommendation: **Ship v22.3.0 next, then v23.0.0**

### Why v22.3 (not v23) right now

**v23.0.0 is a production release with mandatory quality gates** (STRATEGIC_ROADMAP §0):
- QG-01..QG-06 are all marked done in the roadmap, but
  * multi-user (Phase 4) and * real-time sync (Phase 4) are still "IN PROGRESS"
  * WASM SQLite + ONNX embeddings (Phase 2) are still in progress
  * WebSocket bidirectional sync (Phase 4) is not started
- v23 implies "production-ready cognitive OS" — that's not us yet
- Shipping v23 prematurely dilutes the "production" semantics

**v22.3 is the right vehicle for the wins from this session** because:
- Phase 1+2 docstring sweep is a quality win (5,317 functions + 1,342 classes
  now have docstrings, was 0.8% / 0% undocumented, now 0.8% / 0% of 5,317 + 1,342)
- Phase 3 IPC subscribe is a new capability (Python can now receive on
  wm/events, wm/memories, wm/commands, wm/harmony — even if cross-process
  use is constrained by iceoryx2 v0.8 Subscriber: !Send)
- Phase 4 surprise_gate fix is a real bug fix (4 tests previously failing
  due to too-narrow except clause)
- Phase 5 conftest extraction unblocked 34 tests
- Phase 6 AI_PRIMARY drift fix makes the doc-drift check fully green

### Concrete v22.3.0 release plan

1. **Tag v22.3.0** on the current main branch (this session's commits)
2. **Changelog entry** highlighting:
   - Documentation: 888 + 162 = 1,050 entities documented
   - IPC: new `ipc_try_receive` Python API
   - Bug fix: surprise_gate RuntimeError handling
   - Test infra: extract `tests/_envelope.py` for proper module imports
3. **Build new Rust .so** with the new ipc_try_receive
4. **Push to private repo** (already done in this session)
5. **No public release** — per user constraint "keep everything private"

### Concrete v23.0.0 release plan (post-v22.3, ~2-3 weeks)

1. **Finish Phase 4: Multi-User + Real-Time** (the big remaining work)
   - Per-user galaxies + API key auth (4 routes: create user, login,
     galaxy isolation, MCP integration)
   - WebSocket endpoint at `/ws/events`
   - Conflict resolution (last-write-wins is fine for v23.0)
   - Offline queue (LWW with replay log)
2. **Finish Phase 2: WASM Runtime**
   - SQLite WASM + OPFS
   - ONNX embedding model (INT8 quantized, ~23MB)
   - Resonance models in WASM
3. **Polish**
   - Static Haskell linking (or fall back to Rust iching — already exists)
   - Final docs pass
   - Tag v23.0.0

### What to do *this week* (Tactical Plan items still open)

- I-1: Exception scan re-baseline (220 auto-fixable blocks, 1-2 hr)
- I-2: Prescience claim updates (AGT v4, Anthropic Dreaming overtaken)
- I-3: External site competitive positioning
- New from this session: 14 pre-existing absolute_path hits in scripts/
  (out of scope for "polish to v22.3" but worth a quick pass)

### What to do *not* do

- **Don't** try to make the iceoryx2 v0.8 Subscriber thread-safe
  (it's a Rust design constraint, not a code defect — wait for
  iceoryx2 v0.9 if it becomes a problem)
- **Don't** add a Subscriber cache to whitemagic_rust unless
  cross-process consumers actually exist (the Nexus UI comment
  at AgentToolsPanel.tsx:18 is a placeholder, not active code)
- **Don't** chase v23.0 before v22.3 ships — the v22.3 wins are
  real and shippable now

---

## TL;DR

**Ship v22.3.0 with this session's wins.** Then start v23.0 work on
multi-user + WASM runtime per the strategic roadmap. The session's
1,470 passing tests and 0% undocumented public classes are a solid
v22.3 baseline.
