# WMgen3 — Dependency Manifest (Phase 1)

**Purpose:** make the contamination boundary mechanical. The Phase-2 A/B is only meaningful
if the Gen3 arm is genuinely minimal — so the allowed surface is an explicit allowlist with
rationales, and the forbidden surface is enforced by a cargo-tree check.

---

## 1. The single hard rule

**No `wm-*` crate may appear in any `wm-gen3-*` dependency tree.** The only Gen2 artifact any
Gen3 code may touch is the **frozen control binary**, and only in the control arm (never
linked into the candidate).

Enforcement (CI / pre-run check):

```bash
cargo tree -p wm-gen3-core  | grep -E '^[│├└ ]*wm-' && exit 1 || true
cargo tree -p wm-gen3-harness | grep -E '^[│├└ ]*wm-' && exit 1 || true
```

A canary test additionally asserts the absence of the forbidden crate list below.

---

## 2. Allowed — infrastructure (each line earns its place)

| Dependency | Rationale |
|---|---|
| Rust toolchain 1.85+, edition 2024 | Same toolchain family as Gen2; workspace familiarity without code reuse |
| `tokio` | Async runtime; required for any server/harness process |
| `rayon` | Data-parallel scoring/propagation loops (opt-in; not needed at Phase 1 start) |
| `serde`, `serde_json`, `rmp-serde` | Serialization for stores, receipts, and harness IO |
| LMDB bindings (same crate family as Gen2; exact crate + version pinned at scaffold) | Durable store engine; comparability with the control's storage physics |
| `tantivy` (lexical only) | Stock full-text engine; **may not** port Gen2 query planners, filters, or scoring policy |
| `clap` | CLI harness surface |
| `anyhow`, `thiserror` | Error handling |
| `tempfile` | Test isolation |
| `sha2` | Hashes for receipts and corpus pinning |
| `proptest` | Property tests for closures and selection contracts (Phase 1 gates) |
| `criterion` | Benchmarks (only when a metric needs it) |

**Deferred, not allowed yet:** embeddings/ONNX/fastembed (vector similarity); arrow
(working sets); julia/ffi; network clients; web tooling; anything whose presence increases
the variables under test.

## 3. Forbidden — behavioral machinery (contamination surface)

| Forbidden | Why |
|---|---|
| Any `wm-*` crate (`wm-core`, `wm-memory`, `wm-dispatch`, `wm-cognitive`, `wm-governance`, `wm-tools`, `wm-mcp`, …) | Behavioral reuse would invalidate the A/B |
| Gen2 conflict/supersession/evidence-bundle logic (as code or as copied translation) | Directly under test |
| Gen2 episodic retrieval scoring, typology write-gates, dedup thresholds | Adjacent scoring policy; would leak Gen2's tuned behavior |
| Gen2 query planners/filters on top of Tantivy | Retrieval policy is part of the substrate under test |
| Claims ledger / importance / recency scoring implementations | Same reason |
| Verbatim type ports from Gen2 | Allowed only if re-expressed as Gen3 primitives with their own tests — never copied |

## 4. Borderline decisions (recorded here, receipts in `receipts/`)

| Item | Call | Rationale |
|---|---|---|
| Tantivy lexical index | **Allow** | Stock engine, not Gen2 behavior; used by both arms' data preparation equally |
| LMDB engine | **Allow** | Storage physics must match the control for a fair comparison |
| Embeddings | **Defer** | Lexical-only reduces variables; revisit only if kill-criteria demand it |
| Gen2 corpus generation scripts (memorastrict_gen.py) | **Allow for corpus only** | Corpus is frozen by hash before either arm runs; generation is not part of the tested pipeline |
| Harness scoring functions (eval_protocol.py) | **Allow** | Identical scoring for both arms is required; scoring is not the system under test |

## 5. Change process

Any addition to §2 or §4 requires a **contamination-boundary exception receipt**
(`receipts/`) naming the dependency, the need, the alternative considered, and the expected
effect on the experiment. Statute-tier change: external/operator authorized, never adaptive.
