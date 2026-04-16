# WhiteMagic v15.10 & v16 Planning
## Based on Extended Activation Sequence Results (Feb 13, 2026)

---

## Activation Summary

| Metric | Value | Notes |
|--------|-------|-------|
| **Engines Run** | 21/21 ✅ | All pass after bug fixes |
| **Memories** | 111,691 | 2,013.5 MB |
| **Associations** | 2,248,830 | 29,090 typed (1.3%) |
| **Embeddings** | 5,577 | **5.0% coverage** ⚠️ |
| **Holographic Coords** | 6,486 | **5.8% coverage** ⚠️ |
| **Constellations** | 13 | Largest: 4,950 (noise) |
| **KG Entities** | 13 | All from constellation detector |
| **Emergence Insights** | 8 | 3 convergence, 5 hotspots |
| **Causal Edges Mined** | 0 | Needs embeddings |
| **Bridge Nodes** | 0 | Needs networkx |
| **Tools** | 375 | 28 Ganas, 0 orphans |
| **Total Time** | 80s | Full 21-step sequence |

### Zone Distribution
```
        core:    219 ( 0.2%)
   inner_rim:    137 ( 0.1%)
    mid_band: 100,728 (90.2%) ← nearly everything
   outer_rim:  10,615 ( 9.5%)
    far_edge:      0 ( 0.0%)
```

### Bugs Fixed During Activation
1. **6 handler import errors** — wrong module paths, missing factory functions, wrong API signatures
2. **datetime naive/aware mismatch** — `days_since_recall` crashed on timezone-aware DB timestamps
3. **Circular import** in `pattern_consciousness` — `resonance_cascade` ↔ `__init__` cycle
4. **Satkona fusion missing `agg` param** — handler and script both fixed
5. **KG `get_status()` → `status()`** — method name mismatch

---

## v15.10 — Pre-Release Polish (P0)

### 1. Batch Embedding Coverage (5% → 50%+)
**Why**: Semantic mining, causal mining, novelty detection, and bridge synthesis all fall back or return empty without embeddings. This is the single biggest blocker to meaningful analysis.

**Action**: Run `scripts/batch_embed.py` with a local model (all-MiniLM-L6-v2 via sentence-transformers). Target at least 50K embedded.

**Acceptance**: `SELECT COUNT(*) FROM memory_embeddings` > 50,000

### 2. Batch Holographic Coordinate Assignment (5.8% → 50%+)
**Why**: Constellation detection only scans 6,486 of 111K memories. Most of the corpus is invisible to the clustering engine.

**Action**: Run `scripts/batch_holographic_coords.py`. Depends on #1 (embeddings feed coordinate projection).

**Acceptance**: `SELECT COUNT(*) FROM holographic_coords` > 50,000

### 3. Install networkx (0 → full graph engine)
**Why**: Graph topology, bridge nodes, community detection, and PageRank all return 0 without it. Bridge synthesis depends on bridges existing. 4 engines are dead weight.

**Action**: `pip install networkx` and add to `requirements-lock.txt`

**Acceptance**: Graph rebuild returns >1000 nodes, bridge_nodes >5, communities >10

### 4. Noise Filter for Narrative Compressor
**Why**: Dream narrative phase is compressing benchmark junk ("Benchmark memory 0, 1, 2...") into permanent narratives. Wastes storage and pollutes insights.

**Action**: Apply the same `_build_noise_exclusion_set()` logic from `graph_engine.py` to `narrative_compressor.py` before cluster selection.

**Acceptance**: No narratives with `_bench` tags or benchmark content

### 5. Multi-Spectral Reasoner: Enable All Lenses
**Why**: Only Wu Xing lens is producing perspectives. I Ching, Art of War, and Zodiac lenses return nothing. The "multi-spectral" system is effectively mono-spectral.

**Action**: Investigate why `IChingLens`, `ArtOfWarLens`, and `ZodiacLens` don't produce output. Likely missing initialization or data files.

**Acceptance**: All 3 questions produce perspectives from ≥3 different lenses

### 6. Causal Miner: Fix Zero Sampling
**Why**: `mine()` returns `memories_sampled=0`. The miner likely requires embeddings or has a query threshold issue. Temporal proximity mining should work without embeddings.

**Action**: Add fallback temporal-proximity causal mining (memories created within N minutes of each other by same session → `preceded` edge). Don't require embeddings.

**Acceptance**: Causal mining returns >0 edges on 111K corpus

---

## v16.0 — Major Release

### Architecture Improvements

#### A. Embedding Pipeline Overhaul
- Local embedding model always available (bundled or auto-downloaded)
- Incremental embedding on `store()` — never accumulate backlog
- GPU acceleration path for batch operations
- Target: 100% embedding coverage maintained automatically

#### B. Knowledge Graph Entity Extraction Without spaCy
- Current KG has only 13 entities (all from constellation detector)
- Implement lightweight regex/rule-based NER for titles, tags, content
- Extract: people, tools, concepts, version numbers, dates, file paths
- Feed extracted entities into KG on every `store()`
- Target: 1000+ entities, 5000+ relations

#### C. Novelty Detector Baseline Corpus
- Cold start always scores 1.0 — no discrimination
- Build TF-IDF or MinHash baseline from existing memories on first dream cycle
- Auto-calibrate threshold so only genuinely novel content scores >0.7
- Target: "Hello world" scores <0.3, genuinely new concepts score >0.7

#### D. Graph Engine: Incremental Updates
- Currently rebuilds entire graph from scratch each time
- Maintain persistent graph structure in DB
- Add/remove edges incrementally on store/delete
- Target: Graph rebuild <1s for incremental updates

#### E. Constellation Quality: Noise-Aware Clustering
- Largest cluster is 4,950 Golang ecosystem files — noise dominates
- Apply quality filter (noise exclusion set) BEFORE clustering, not just in graph analysis
- Better zone distribution — 90% mid_band suggests retention scoring needs tuning
- Target: No noise-dominated constellations, more meaningful zone spread

### Feature Additions

#### F. First-Time Experience
- `whitemagic init` CLI command (interactive setup wizard)
- Seed content: 10-15 guide memories auto-created
- Quieter defaults: reduce INFO logging noise for new users
- Better error messages for missing optional dependencies
- Progressive disclosure: basic tools first, advanced tools after first dream cycle

#### G. Association Type Evolution
- Only 1.3% of 2.2M associations are typed (29,090 of 2,248,830)
- Batch reclassification pipeline using tag heuristics + LLM classification
- Run `scripts/batch_classify_associations.py` at scale
- Target: 50%+ typed edges

#### H. Harmony Vector Cold Start Fix
- `error_rate=1.0`, `karma_debt=0.9` on first run are misleading
- Use sane warm-start defaults until 100+ tool calls accumulate
- Distinguish "no data" from "bad data" in all harmony dimensions

#### I. Dream Cycle Scheduling
- `scripts/dream_overnight.py` exists but isn't wired to MCP
- Add `dream.schedule`, `dream.status` tools
- Support cron-style scheduling: "run every night at 2am"
- Persist dream journal across sessions

#### J. Public Website / Dashboard
- Knowledge Sphere 3D visualization (Three.js)
- Galaxy map with constellation overlays
- System health dashboard (harmony vector, wu xing, dream status)
- Memory search + browse UI
- Agent marketplace directory

---

## Emergence Insights from Activation

The activation sequence itself revealed these patterns:

1. **Constellation Convergence**: "Corona Synthetic Insight" and "Corona Migrated Aria-Era III" are 0.30 apart in 5D space with shared `migrated` tag — actively merging domain

2. **Association Hotspots**: `session_handoff.meta.json` has 20,056 associations (avg strength 0.63) — it's a mega-hub. Consider whether this is meaningful or an artifact of import

3. **Go Ecosystem Dominance**: The cold DB ingestion brought in ~100K Golang ecosystem memories that dominate the corpus. These should probably be in their own galaxy or filtered from core analysis

4. **Aria-Era Memories**: 689 members in "Corona Migrated Aria-Era" constellation at core zone — these are working correctly as protected, high-importance memories

5. **Dream Kaizen Hints**: "High error rate", "Low energy", "Karma debt" — all cold-start artifacts, but the hint system itself works. Needs warm-start logic

---

## Priority Order

### Ship-blocking (do before public release):
1. Install networkx → 4 engines come alive
2. Noise filter for narrative compressor
3. Harmony cold-start fix (don't show error_rate=1.0 to new users)
4. First-time experience (`whitemagic init`)

### High-value (dramatically improves quality):
5. Batch embeddings (50K+)
6. Batch holographic coords (50K+)
7. Multi-spectral reasoner all lenses
8. Causal miner temporal fallback

### v16 architecture:
9. Incremental embedding on store()
10. Lightweight NER for KG
11. Novelty baseline calibration
12. Graph incremental updates
13. Association batch reclassification
14. Dream scheduling
15. Public dashboard

---

*Generated from activation report: `reports/activation_extended_20260213_162919.json`*
*21/21 engines, 0 errors, 80s total runtime on 111K corpus*
