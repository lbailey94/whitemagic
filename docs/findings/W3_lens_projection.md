# Phase 4 — Wave-3 findings: lenses (projection / alternate views)
**Status: findings · 2026-09-17 · read-only research; assigns no verdicts. Companion to
PHASE4_WAVE1_FINDINGS.md / PHASE4_WAVE2_FINDINGS.md.**
Per-row format as in the wave masters: observed behavior · selection history · candidate
expression/manifest · adversarial cases · ablation. Gen1 = `og_whitemagic` v26, Gen2 = `WMv9`,
S = the semantic-projection primitive (WMgen3-side `projection.rs`, τ = 0.694). Counts are
command-stated; UNVERIFIED items are marked.

## Observed behavior (cites)

### Gen1 v26 — lens ancestors
- **Two coordinate organs (the known E/C1 conflation):** `CoordinateEncoder` builds 6D
  `[x,y,z,w,v,u]` (`core/intelligence/hologram/encoder.py:5,111`); qFHRR is separate
  (`core/memory/qfhrr.py:1-17`; class default `bits=4` `:51`; retrieve path 8-bit LUT per
  `findings/W1_retrieval.md:65-74`). HRR circular convolution is write-side only
  (`core/memory/hrr.py:100-165`; consumer cache module absent — `W1_retrieval.md:65-70`).
- **Embeddings-as-projection is item-side, not query-side:** `_calculate_semantic_bias`
  returns 0.0 unless the encoded dict carries an id with a cached embedding
  (`encoder.py:216-222`; called from `_calculate_x` `:727` and the Rust blend `:361-365`).
  `HolographicMemory.query_nearest` encodes `{"content": query}` (`holographic.py:127-171`),
  so query coords come out heuristic-only (bias 0.0). PCA path expects centered MiniLM
  vectors, amplified ×6.0 (`encoder.py:258-265`).
- **Storage + index:** 6D `holographic_coords(x,y,z,w,v,u)` SQLite (per `W1_retrieval.md:75-78`);
  precomputed-coord insert `holographic.py:110-124`, `query_by_vector` `:173-197`.
- **Retrieval coupling is a *stage*, not a caller view:** planner stage `SPATIAL_RANKING`,
  RRF weight 0.5 default (`retrieval_plan.py:11,91`; `search_planner.py:139-161,205-209`),
  silently skipped if the index is absent or `WM_SKIP_SPATIAL_SEARCH=1`
  (`search_planner.py:142`), recorded only in `degraded_stages` (`:156`); legacy inline path
  identical (`unified.py:854-868`). Default hybrid runs the planner (`unified.py:736-757`).
- **Caller-declared views live in `wm_read`:** auto-detect coords→spatial, no-query+time_window→
  temporal (`tools/handlers/wm_read.py:75-102`); spatial takes caller-supplied 5D coords →
  `core_access.query_holographic_neighbors` (`:446-470`); temporal returns time-bucketed
  **activity metrics + velocity**, not memories (`:495-513`). Mode enum/descriptions:
  `tools/registry_defs/unified_read.py:19-55`.

### Gen2 (WMv9) — the S analogue and the vector story
- **S itself (WMgen3-side):** pinned model `Qdrant/bge-small-en-v1.5-onnx-Q`
  (`crates/wm-gen3-core/src/projection.rs:21`), `TAU_GATE = 0.694` (`:28`), τ-floor
  `semantic_support` (`:109-117`); two declared attach points — recall candidate expansion and
  `think` pair gating (`:4-5`); enabled by `WM_GEN3_PROJECTION`/`WM_GEN3_EMBED_CACHE` and gated
  by `WM_GEN3_PROJECTION_GATED` (`wm-gen3-harness/src/main.rs:41-56`; `"count"` selects the
  count criterion). τ pinned at the battery midpoint; margin advisory 0.0116 < 0.05
  (`receipts/P2B_IMPLEMENTATION_FREEZE_2026-09-16.md:23-25`).
- **Gen2's own coords:** `HolographicCoords` (6D, galaxy+temporal key; `crates/wm-core/src/coords.rs:16-68`)
  and `Coordinate5D` whose x/y/z are SHA-256 hash bytes, w/v 0.5 (`:212-225`); the struct's own
  doc calls the hash "semantically meaningless" (`:229-232`). `from_semantic` (`:234-248`) is
  reached only via `SemanticEncoder::encode_coordinate` (`crates/wm-memory/src/semantic.rs:252-259`),
  a Tantivy anchor-TF projection with three named axes (`semantic.rs:1-60`).
- **`put_semantic` / `find_similar`:** store-side semantic coords + distance scan
  (`crates/wm-memory/src/store.rs:1354-1392`; weights `coords.rs:274-281`). Caller audit
  (`rg -n "put_semantic" crates`): **production callers = 0** — all hits are `#[cfg(test)]`
  (`wm-cognitive/src/constellation.rs:365,388`; `autonomous.rs:2338+`). `find_similar` **is**
  called by the Connect cycle (`autonomous.rs:822,910`; `similarity_threshold` 0.7 `:125,143`),
  so that pass compares an anchor-TF query coord against hash-derived stored coords unless
  ingestion called `put_semantic`. Live-store coordinate provenance: UNVERIFIED.
- **`memory.nearby`:** hashes the query (`Coordinate5D::encode`, `wm-tools/src/expansion/additional.rs:405`)
  and scans stored `coord5d` (`wm-memory/src/memory.rs:129-130,343`); registered only in the
  expansion surface (`expansion/mod.rs`). Render/diagnostic, not recall.
- **Serving path has no lens:** hybrid recall fuses BM25 0.5 / vector 0.3 / importance 0.2
  (`wm-memory/src/recall.rs:26-28,164-174`) behind a real-embedder gate (Http/Stub
  `wm-memory/src/embedder.rs:3-17`; ONNX default `BAAI/bge-small-en-v1.5` per WMv9 `AGENTS.md`)
  — a weighted blend, i.e. a stage. `rg -i "hrr" crates` finds no HRR operator in Gen2 (only
  `hologram*` tool naming) — functional detail under erratum C1.

### WMgen3 experimental record (cite only)
- **S solo null:** consolidation matrix `docs/ARCHITECTURE_CONSOLIDATION.md:32`; claim-0001
  falsified (P2B, `receipts/PHASE2B_RESULTS_2026-09-16.md`).
- **Conditional reach in interaction** (+ up to +8 top-5), plus rank-1 displacement risk:
  matrix `:33,42-44,57-69`.
- **Gated series:** 001 floor behaviorally safe, cost-bar fail, |O| = 0 (`:48-55,154-160`);
  002 transport PASS / discrimination FAIL / ordering FAIL / pass-scoped cost PASS (`:57-69`);
  003 `count < 2` confirmed gate-scoped — O₀/O₁ 10/10, O₊₂ MissedOpportunity 1.000,
  CostEfficiency 0.381, claim-0007 validated (`:71-83,161-167`).
- **S as optional lens:** conditional tier `:127`; layer 4 "optional projections/lenses …
  ~60× cost argues for earned activation" `:144-146`; earned activation policy `:188-197`;
  "lenses are slots, not stages" `NUCLEUS_FREEZE_CRITERIA.md:87-90`; re-entry rule
  `PHASE3_ENTRY_DECISION.md:37-42`.
- **Multi-view notes:** five falsifications converge on selection among imperfect signals;
  projection-agreement gated out (10/12); "no blended score, no fitted weights"
  (`RESEARCH_NOTES_MULTI_VIEW_SELECTION.md:10-19,34-52`); seeds 1–20/101–106/201–202/301–310
  burned, 401–410 reserved (`experiments/testbed_ii/a/PRE_REGISTRATION_GATED_S.md:66`).

## Selection history
v26 accreted one ranking organ per feature wave; the 5D channel was fused as an always-on
planner stage (v15.1 addition) and never ablated or disclosed, while the caller-facing view
grammar lived in `wm_read` modes. Gen3's projection primitive was built the opposite way:
switch-off default, pinned model/τ, and it entered the record only through falsification
(solo null → 0.01-floor gate falsified as a zero-support detector → `count < 2` confirmed
gate-scoped). The consolidation matrix demoted S to the conditional tier; nucleus/entry
decision froze it as a slot with scoped activation.

## Candidate Gen3 expression / manifest notes
What the record already establishes for "declared optional lens" vs "mandatory stage":
- **Activation:** a declared condition or explicit caller mode — confirmed rule is
  `lexical_candidates < 2`, scoped to state-resolution questions, "not a general
  semantic-insufficiency detector" (matrix `:80-82`); always-on is the falsified alternative.
- **Cost:** pre-registered cost bars and per-query accounting (gated pre-reg §3/§5,
  `PRE_REGISTRATION_GATED_S.md:60`); dormancy has a measured but *non-pre-registered* dividend
  (gated 0/20 stale-label vs always-on 3/20 — research note only, matrix `:130-134`).
- **Disclosure:** per-query gate events (`projection.gate`: lex_support_max/gated/fired) and
  result-level floors; contrast Gen1's silent stage skip, visible only in `degraded_stages`.
- **Scoping:** falsification conclusions attach to the gate, never to the lens class
  (`PRE_REGISTRATION_GATED_S.md:16-19`).
- Registration toll: ancestor · wire · acceptance · owner (`PHYLOGENETIC_FRAMING.md:83-85`);
  wave-3 gate = new registration + fresh holdout (`PHASE4_GEN1_TREE.md:33`); "rejected stays
  rejected" re-entry = registration + fresh holdout + ledger (`NUCLEUS_FREEZE_CRITERIA.md:84-90,123`);
  no tuned thresholds (multi-view §3 constraint).

## Adversarial cases
1. **Query/stored projection asymmetry** — Gen1 query coords drop the embedding bias
   (`encoder.py:216-222`); Gen2 `find_similar` compares anchor-TF query coords to SHA-256
   stored coords. A lens must be query-consistent or declare which side is projected.
2. **Silent dormancy** — Gen1's spatial stage can be skipped with no caller-visible signal
   (`search_planner.py:142,156`); a declared lens requires journaled firing decisions.
3. **Non-pre-registered dividends** — the stale-label dormancy benefit was never an endpoint
   (matrix `:130-134`), nor was the τ margin advisory (0.0116 < 0.05, P2B receipt `:25`);
   separation is the frozen requirement — such observations are recorded, not promoted.
4. **Harness-bound cost verdicts** — 001's cost failure came from per-query model reload in
   both cells (matrix `:48-51`); registrations must pin the cost model/amortization or the
   verdict is an artifact.
5. **Mixed coordinate provenance** — one `coord5d` field carries hash or anchor-TF coords
   depending on write path (`store.rs:2949-2966`); a coord-reading lens must disclose
   provenance (legacy stores may hold both).

## Ablation ideas
- Switch-level lens ablation is the established pattern: `WM_GEN3_PROJECTION` ×
  `WM_GEN3_PROJECTION_GATED` (`"1"` floor / `"count"` criterion) in the harness
  (`main.rs:41-56`). Gen1 stage ablations exist but were never run as an A/B:
  `WM_SKIP_SPATIAL_SEARCH`, `use_planner=False`, `axis_weights` (`search_planner.py:142`;
  `unified.py:693,698`). Gen2 has a de-facto S-on/off probe (stub vs real embedder gates the
  hybrid channel).
- Expected signature from the record: lens off/on moves reach, not R ordering
  (`ARCHITECTURE_CONSOLIDATION.md:91-100`); firing must be logged so dormancy is auditable.

## Open questions
- Was v26's spatial RRF channel ever load-bearing? No A/B, ablation, or telemetry attestation
  found; it fails soft, and its headline counts are docs-sourced (`W1_retrieval.md:21-25`). UNVERIFIED.
- Do live Gen2 stores hold any `put_semantic`-written coords? No production caller in source;
  needs a live-store provenance check.
- Is "temporal" a lens at all? v26 temporal mode is an activity-metrics view, not a memory
  projection (`wm_read.py:495-513`).
- Per-result view disclosure (support/disagreement) remains dormant per multi-view notes §3.1;
  no registered mechanism.
- Wave-3 owner and fresh holdout are unset (`PHASE4_GEN1_TREE.md:33`); projection-agreement
  ordering stays dormant (matrix `:167,197`).
- **Errata candidates (checked against `PHASE4_ERRATA.md`):** matrix §2.3 "HRR math distilled
  into coords" is already covered by C1 (HRR/coords conflation) — additive functional detail
  only: `rg -i "hrr" crates` finds no HRR operator in Gen2. Not raised before: the W1 spatial
  row could note query-side encoding bypasses embeddings and the temporal view is metrics-only.
  Neither is verdict-changing.
