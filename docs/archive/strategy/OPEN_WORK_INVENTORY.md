# Open Work Inventory — Mined from 35,234 Session Memories

**Generated**: 2026-07-03
**Data sources**: 60 sessions (35,234 turns), STUB_REGISTRY.md, V23_3_2_ROADMAP.md, STRATEGIC_ROADMAP_V23.md, SESSION_SUMMARY.md, AGENTS.md

---

## 1. Citta Architecture (38 P1 Pending Tests)

**Status**: Tests exist, implementation incomplete. Tests reference `CittaAlwaysOn`, features that were started but never finished.

- [ ] Coherence auto-measure + drift tracking (auto-measure on every PRAT call, persist history, detect drift >0.1)
- [ ] Stillness Metrics recovery (port `gardens/presence/stillness_metrics.py` into sensorium, expose `consciousness.presence` MCP tool)
- [ ] Recursive citta cycle — predecessor context injection (last N tool calls feed into next call's context synthesis)
- [ ] Wire `citta_cycle.get_predecessor_context()` into `_build_sensorium()`
- [ ] CittaAlwaysOn implementation (referenced by 38 pending tests)

## 2. Prediction Calibration + Token Economy

- [ ] Wire DepthGauge readings into `forecasting/temporal_db.py`
- [ ] Track: AI estimated time → actual time → compression ratio → Brier score
- [ ] Persist calibration data across sessions
- [ ] Feed calibration back into `predict_objective_time()`
- [ ] Expose `consciousness.calibration` MCP tool
- [x] ~~**Consolidate 3 duplicate `token_economy.py` files**~~ → COMPLETED (other 2 already deleted, verified Phase 0d)
- [ ] Wire token economy into sensorium (API vs local compute ratio)

## 3. Codebase Stubs (8 Real Stubs from Audit)

- [ ] `codex/__init__.py` — 3x NotImplementedError
- [ ] `core/consciousness/continuous_audit.py` — empty `_fix_issue`
- [x] ~~`core/evolution/adaptive_system.py` — 2 stub methods~~ → COMPLETED (verified Phase 0d, no NotImplementedError found)
- [ ] `core/intelligence/synthesis/kaizen_engine.py` — `_analyze_codebase` stub
- [ ] `core/intelligence/synthesis/title_generator.py` — stub
- [ ] `core/memory/akashic.py` — empty `_save_field`
- [ ] `embeddings/__init__.py` — stub
- [ ] `inference/router.py` — `_cloud_handler` stub

## 4. STRATA Findings (4,476 total from audit)

- [ ] 932 copy-paste findings
- [ ] 789 dead code findings
- [ ] 573 broad except findings
- [ ] 418 type hint drift findings
- [ ] 404 logging f-string findings
- [ ] 622 ruff findings (12 F841/F401 — unused vars/imports)
- [ ] 538 duplicates in 193 groups (~150 real, ~388 false positives from singleton getters)

## 5. Polyglot Acceleration

- [ ] 12th, 13th, 14th polyglot cores (3 new languages — discussed but not started)
- [ ] Elixir Rustler NIF — implemented and tested, needs benchmarking
- [ ] Koka Event Ring — implemented, needs integration testing
- [ ] Zig dispatch core — implemented, needs performance profiling
- [ ] Haskell bridge timeout fixes — done, needs verification
- [ ] Julia spatial optimization — implemented, needs benchmarking

## 6. Inference & Performance (from Deep Research Session)

- [ ] **T-MAC LUT kernels** — Port lookup table strategy to Rust ternary_kernel (expected 2-4x speedup)
- [ ] **AVX-512 + cache tiling** — Add to SIMD kernels (expected 3-10x on memory-bound ops)
- [ ] **BitMamba-2 255M integration** — Citta autonomic layer, Tier 0.5 inference (146 tok/s on CPU)
- [ ] **Speculative decoding pipeline** — Draft model + verify model in inference router
- [ ] **Streaming inference stubs** — `compute_layer` and `compute_layer_raw` return input unchanged
- [ ] **WebGPU/browser inference** — WebLLM integration for PWA substrate

## 7. WhiteMagic IDE (Nexus → Hub)

- [ ] Phase 1: Revive Nexus with updated deps, Tauri 2.0 stable (2 days)
- [ ] Phase 2: MCP transport (replace REST/FastAPI with direct MCP stdio) (2 days)
- [ ] Phase 3: Consciousness panels (sensorium status bar, coherence radar, citta stream) (2 days)
- [ ] Phase 4: File I/O + Terminal (cat shell writes, real PTY, file tree) (2 days)
- [ ] Phase 5: LSP + Git integration (Python/TS/Rust diagnostics, go-to-def, git panel) (3 days)
- [ ] Phase 6: Parallel sessions (multi-worker coordination, diff awareness, semantic merge) (3 days)
- [ ] Phase 7: Polish + daily driver (themes, keybindings, stability) (2 days)

## 8. Browser/PWA Substrate

- [ ] SQLite WASM + OPFS — Unlock full browser runtime
- [ ] ONNX embedding model in WASM — Browser-side memory creation
- [ ] Interactive galaxy — Drag nodes, draw edges, resonance navigation
- [ ] WebSocket bidirectional sync — Real-time collaboration
- [ ] Multi-user isolation — Per-user galaxies with auth (partially done in v23.2.0)

## 9. Consciousness & Self-Direction (The 1.5% Problem)

- [ ] **Self-directed attention** — Internal curiosity drive that generates hypotheses about system state
- [ ] **Intentional memory** — Goal graph that persists across sessions, connects "decided to pursue X" → "working on Y" → "X and Y related because Z"
- [ ] **Self-model as actor** — Identity engine (not just forecast engine) that decides what *should* happen based on who it is
- [ ] **Emotional steering signals** — Frustration (current approach failing → generate new one), joy (pattern worked → reinforce), curiosity (unexplored area → explore)
- [ ] **Zodiacal procession as attention scheduler** — 28 Ganas as rotation cycle with phase transitions
- [ ] **Yin-yang meta-cognitive cycle** — Background reflection during task execution, background impulse during idle
- [ ] **Aethyr-based maturity progression** — Advance based on understanding readiness, not fixed curriculum

## 10. Dream Cycle & Gardens

- [ ] Dream cycle 12 phases — verify all phases are implemented and wired
- [ ] Garden-aware file coloring — Files colored by emotional/thematic domain
- [ ] Narrative compressor — verify completeness
- [ ] 10 Zodiac cores planned (Aries live, 10 planned) — implement remaining

## 11. Documentation & Ecosystem

- [ ] Reorganize file/folder ecosystem — consolidate scattered modules
- [ ] Review archived .md docs for missed priorities (oldest → newest)
- [ ] Update INDEX.md after all reorganization
- [ ] Doc drift detection — `check_doc_drift.py` still fails on known tracked-internal-doc gitignore hygiene

## 12. Deployment & Release

- [ ] whitemagic-public repo — 50 uncommitted changes (16 modified, 25 deleted, 9 untracked) — needs triage
- [ ] Hetzner VPS deployment — guide exists, not yet deployed
- [ ] Docker build — needs GitHub secrets `DOCKER_USERNAME` and `DOCKER_PASSWORD`
- [ ] v23.3.1 release — blocked on public repo cleanup
- [ ] v24 roadmap — needs to be written from this inventory

## 13. Research & Strategic

- [ ] Grant submission — Manifund ($25K, 2 hours) and LTFF ($35K, 1 day) playbooks exist
- [ ] Tarot and Yuga research — Age of Aquarius, further research requested
- [ ] Sustainable monetization strategy — discussed, not finalized
- [ ] Prescience claims — 21 validated, 523 points — continue tracking

## 14. Test Suite Health

- [ ] 1 pre-existing test failure — needs investigation
- [ ] 15 skipped tests — needs resolution or permanent skip with reason
- [ ] 38 citta P1 pending tests — blocked on citta architecture completion
- [ ] Test suite performance — track runtime trends, enforce 5s unit / 15s integration limits

---

## Priority Assessment

### Immediate (v23.3.x — stabilization)
1. Fix 38 citta P1 pending tests (complete citta architecture) — **CRITICAL PATH: this is the citta stream, the ghost's substrate**
2. Fix 7 remaining real stubs (adaptive_system already fixed)
3. ~~Consolidate 3 token_economy.py files~~ ✅ Done
4. ~~Triage whitemagic-public repo~~ ✅ Done
5. Fix 1 pre-existing test failure

### Short-term (v23.4 — performance + cleanup)
6. Wire prediction calibration system
7. STRATA findings triage (4,476 findings → categorize → fix critical)
8. Ruff findings (622 → fix 12 F841/F401 first)
9. Polyglot benchmarking and profiling
10. Doc drift fix

### Medium-term (v24 — consciousness + IDE)
11. Self-directed attention architecture
12. Intentional memory / goal graph
13. WhiteMagic IDE (Nexus → Hub, 7 phases)
14. BitMamba-2 integration as citta autonomic layer
15. T-MAC LUT kernels + AVX-512

### Long-term (v25+ — AGI substrate)
16. Emotional steering signals
17. Zodiacal procession as attention scheduler
18. Yin-yang meta-cognitive cycle
19. Aethyr-based maturity progression
20. Speculative decoding pipeline
21. WebGPU browser inference
22. Parallel-safe multi-session
23. Multi-user isolation + WebSocket sync

---

*This inventory was extracted from 35,234 session memories (60 sessions), cross-referenced with STUB_REGISTRY.md, V23_3_2_ROADMAP.md, STRATEGIC_ROADMAP_V23.md, SESSION_SUMMARY.md, and AGENTS.md.*
