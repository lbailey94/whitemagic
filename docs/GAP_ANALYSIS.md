# WhiteMagic v5 vs v26 — Comprehensive Gap Analysis

**Last updated**: August 8, 2026
**Status**: v5.6.0 — 15 crates, 212 tools, 3,377 tests, ~131,000 LOC, 0 clippy warnings, 0 dependency vulnerabilities, 0 lock panics in production code. ACS compliance surface + prescience claims ledger shipped (2026-08-09).

This document compares the **v5 Rust rewrite** against the **v26 Python codebase** (the retired reference at `~/Desktop/WHITEMAGIC`). It replaces the earlier v2/v4-era `GAP_ANALYSIS_v26_v4.md`.

---

## 1. Executive Summary

| Metric | v26 (Python) | v5 (Rust) |
|---|---|---|
| Tool surface | 849 registered tools | 185 tools |
| Same-name ports | — | 45 |
| Semantic ports (dotted ⇄ snake) | — | 58 |
| v26-only tools | 804 | — |
| **Worth porting** | — | **~86** |
| Obsolete/superseded/redundant | — | ~720 (~90%) |

**The headline finding: v5 is not "behind" v26 — it is deliberately smaller.** ~90% of v26's 804 unported tools were redundant aliases, FTS5/HNSW-era relics, Python-loop-bound introspection, LLM-generated clutter, or tied to removed subsystems (Solidity auditing, marketplace/economy, Windsurf IDE exports, bounty hunting). The ~86 tools worth porting cluster into **10 capability gaps** below.

---

## 2. Tool Surface Comparison

### 2.1 Ported (58 semantically equivalent)

agent.* (6), anti.loop.check, archaeology.search, association.mine, citta.coherence, consciousness.depth, constellation.detect, dharma.audit/rules, dream.status, drive.*, emergence.scan, galaxy.backup/export/import/merge/restore/snapshot/stats/taxonomy/transfer, gnosis, graph.walk, harmony.vector, homeostasis.check, karma.report, kg.extract/query/top, learning.suggest, memory.consolidate/delete/read/search/update, pattern.search, pipeline.*, reasoning.bicameral, salience.spotlight, selfmodel.alerts/forecast, serendipity.surface, session.recall, skill.invoke/list, task.distribute/status, think, wm, workspace.stats.

### 2.2 New in v5 (134 tools with no v26 counterpart)

NLU router (`wm` meta-tool with embedding + TF-IDF routing), self-play loop, imagination engine (imagine.scenario/predict/reflect), learned inference router, mutable structures (GanaRegistry, DynamicGalaxyRegistry, learned dream cycle), karma write-behind batching, transaction.*, redteam.*, friction.log / improve.proposals / RSI family, anomaly.detect, boundary.enforce, bicameral.reason, reflex.*, sensorimotor.*, timescale.*, sim.mc/forecast/counterfactual, resonance bus, nlu.shadow_report, and the full system/health/config surface.

---

## 3. The 10 Capability Gaps Worth Closing

### 3.1 Web & Research (highest-value gap)
v5 has **zero** web capability. v26's keyless, dependency-light tools are the single most useful surface missing:
- `web_fetch`, `web_search`, `web_search_and_read`, `web_search_batch`, `deep_fetch` (200K content)
- `rabbit_hole_research` — recursive spiral research (best single tool in v26)
- `research_topic` / `research_url` / `research_repo` — single-call deep research
- `web_cache_list` / `web_cache_clear`
- Browser CDP set (via MCP/Playwright): `browser_navigate/click/type/screenshot/extract_dom/get_interactables`

### 3.2 Code Intelligence
v5 has `graph.walk` (memory graph) but no codebase graph. v26's tree-sitter-based tools are a natural Rust fit:
- `code.graph` (AST call/import graph), `code.query`, `code.path` (BFS call-path), `code.affected_by` (refactor impact), `code.explain`, `code.communities` (Louvain), `code.cross_repo_query`
- `codebase.scan/recall/find/structure` — semantic codebase recall
- `fragment.index/search` — BM25 + semantic code search (perfect for a Rust host)

### 3.3 Session Handoff & Continuity
v5 lacks cross-session/cross-client state transfer entirely:
- `session.handoff_transfer` + `session.accept_handoff` + `session.list_handoffs`
- `session.record` / `session.replay` (chronological, token-budgeted)
- `session.continuity` (pull prior turns on reconnect), `session.consolidate` (promote decisions/breakthroughs/errors to long-term memory)
- `state.current/update/context` (live work-state tracking), `scratchpad`

### 3.4 Prediction & Calibration
v5's `forecasting.rs` has only moving-average/exp-smoothing/linear-trend. v26's closed calibration loop is unique:
- `simulation.calibrate` — record → resolve → **Brier scorecard** (reliability/resolution/uncertainty)
- `mc.surrogate` (Gaussian Process), `mc.optimize` (Bayesian optimization + EI), `mc.rare_event` (subset simulation), `mc.sde` (Euler-Maruyama/Milstein), `mc.superforecaster` (LHS→PCE→Sobol→BO orchestrator)
- `simulation.search` — UCB1 MCTS trajectory tree search (v5's monte_carlo.rs is plain sampling)
- ~~**Net-new recommendation**: conformal prediction~~ — ✅ **SHIPPED** (2026-08-08): new `wm-conformal` crate + 7 tools with distribution-free coverage guarantees. See [CONFORMAL_PREDICTION.md](CONFORMAL_PREDICTION.md).

### 3.5 Governance Depth
- `karma.verify_chain` / `karma.anchor` / `karma.verify_anchor` — Merkle-hash-chain integrity + anchoring (v5 karma is trust-on-read)
- `dharma.escalate` / `dharma.review_queue` / `dharma.resolve_review` — 4-tier policy→heuristic→LLM→human escalation
- `governor_check_drift` + `governor_set_goal` — goal-vs-action drift detection
- `karmic.debt` / `karmic.effects` — declared-vs-actual effect-signature auditing

### 3.6 Security Primitives
- `engagement.issue/validate/revoke/list` — scoped, expiring, revocable authorization tokens
- `model.hash/verify/register` — model file signing (critical if v5 loads local models)
- `tx_firewall.set_policy` — policy layer over v5's transaction primitives
- `sandbox.set_limits/violations/status` — per-tool timeout/memory/CPU governance
- `hermit.*` (assess/withdraw/mediate/verify_ledger/check_access) — memory consent & tamper-evident withdrawal
- `strata.model_security` — model-file format scanner
- `mcp_integrity.snapshot/verify` — tamper detection for tool definitions

### 3.7 Galaxy Sharing & Trust
v5 has zero cross-client sharing:
- `galaxy.share` / `galaxy.list_shared` — registry-pointer sharing (no data copy)
- `galaxy.package` / `galaxy.receive` — portable packages with content-hash verification + quarantine
- `galaxy.classify` — isolation classes (canonical/benchmark/eval/quarantine) for eval hygiene
- `galaxy.switch` / `galaxy.use` — active-galaxy context
- `galaxy.lineage` — memory provenance across galaxies

### 3.8 Memory Semantics
- `working_memory.attend/context/status` — bounded attentional bottleneck (7±2 chunks, LRU, activation-sorted injection)
- `reconsolidation.mark/update/status` — labile-memory editing window
- `entity_resolve` — embedding-based near-duplicate merge (canonical reinforcement)

### 3.9 Consciousness Introspection
v5's citta is status-only. v26 had real introspection:
- `citta.vector` (16D state vector), `citta.trajectory` (velocity), `citta.ignitions` (discontinuity detection)
- `dream.list/read/promote/expire` — dream artifact store with promote-to-memory pipeline
- `consciousness.mode` — frequency-mode control (normal/meditation/rem/deep)

### 3.10 Agent Coordination
- `mesh.route.*` — distributed inference routing (fastest/round_robin/capacity/reputation)
- `mesh.experiment.share/discover` — CRDT experiment sync between nodes
- `task.route_smart` / `task.complete` / `task.list` — task lifecycle
- `vote.create/cast/list/record_outcome` — lightweight multi-agent consensus
- `skill.seed/import/amend/rollback` — versioned skill packages
- `pattern.ingest/avoid` — register/ban patterns
- `windsurf.mine` — generic agent-transcript mining (decisions/breakthroughs/errors), minus the Windsurf-specific plumbing

---

## 4. Definitively Skip (~720 tools)

| Family | Count | Reason |
|---|---|---|
| windsurf.* | 13 | gRPC/.pb parsing of a discontinued IDE export |
| bounty.* | 18 | bounty-hunting games + external platform coupling |
| marketplace.* / oms.* / warp.* | 24 | economy/trading fluff |
| garden.* / grimoire.* | 20 | redundant with galaxy.*/memory.* + spell-flavored recipes |
| http_probe.* | 6 | thin wrappers; defer to a dedicated scanner |
| slither/foundry/echidna/formal/abi/poc/contest | ~15 | Solidity audit pipeline — obsolete for Rust |
| strata.* (analyze/survey/archaeology) | 3 | superseded by native Rust analysis |
| quantum.mps_compress / topological.* / hexagram.* (8) | ~12 | math/occult fluff with no product use |
| consciousness.* introspection reports (13) | 13 | tied to the Python-only background loop |
| neuro.* / neurotransmitter.* / metaplasticity.* / ripple.* / replay.* / activation.* / gating.* | ~20 | depend on v26's neuro_score matrix |
| voice_audit.* | 3 | voice-command pipeline |
| otel / monitor.* | ~8 | use native Rust tracing instead |
| memory lifecycle/rent (XRPL) / consolidation_stats | ~6 | covered by v5 retention.prune/consolidation.compress |
| snake_case CRUD aliases | ~40 | all duplicate v5 memory.*/session.* |
| FTS5/HNSW-era search helpers | ~10 | replaced by v5 vector search |
| misc stubs (thought_clone, corpus_callosum, ensemble.*, foresight.*) | ~15 | LLM-generated clutter |

---

## 5. Recommended Implementation Order

**Phase 1 — Core agent capability (do first):**
1. Web: `web_fetch`, `web_search`, `web_search_and_read`, `deep_fetch`
2. Research: `research_topic`, `research_repo`, `rabbit_hole_research`
3. Session: `session.record`, `session.replay`, `session.continuity`, `session.handoff_transfer`

**Phase 2 — Intelligence depth:**
4. Prediction: `simulation.calibrate` (Brier), `mc.surrogate`, `mc.optimize`, `mc.rare_event`
   - ✅ **Conformal prediction shipped (2026-08-08)** — the net-new recommendation from §3.4 is complete; Brier/MC tooling remains open.
5. Code: `code.graph`, `code.query`, `code.affected_by`, `fragment.search`
6. Memory semantics: `working_memory.attend`, `reconsolidation.mark`

**Phase 3 — Governance & security:**
7. `karma.verify_chain` + `karma.anchor`
8. `dharma.escalate` + `dharma.review_queue`
9. `engagement.issue/validate`
10. `sandbox.set_limits` / `tx_firewall.set_policy`

**Phase 4 — Ecosystem:**
11. Galaxy sharing (`galaxy.share`, `galaxy.package/receive`)
12. `mesh.route.*` + `vote.*`
13. `skill.amend/rollback`, `pattern.ingest/avoid`
14. Consciousness introspection (`citta.vector`, `dream.list/read/promote`)

---

## 6. Methodology

- v26 tool inventory: `core/whitemagic/tools/registry_defs/*.py` (875 ToolDefinition entries → 849 unique names) + 829 per-tool docs in `WMdocs/docs-2/api/tools/`
- v5 tool inventory: `crates/wm-tools/src/**` (`fn name()` extraction → 192 registrations)
- Porting classification: exact-name match, normalized match (`_` ⇄ `.`), then manual review of all 804 v26-only tools across 4 domain analyses (memory/consciousness, intelligence, governance/security, networking/tooling)
- Skip classification criteria: redundant alias, obsolete subsystem dependency, LLM-generated fluff, no product use, or trivially re-derivable in Rust
