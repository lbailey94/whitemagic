# SIMD + FFT Optimization Pass — 2026-07-15

**Status**: Active — 5 items complete, 3 remaining
**Hardware**: Intel Core i5-8350U (Kaby Lake R, 4c/8t, AVX2+FMA, no AVX-512)

---

## Completed Work

### #1 HRR FFT Bind — O(n²) → O(n log n) ✅

**File**: `core/whitemagic-rust/src/inference/simd_ops.rs`

Replaced direct O(n²) circular convolution with FFT-based convolution using `rustfft` crate.
For dim=384: 147,456 ops → 6,912 ops (21.3x algorithmic reduction).

**Benchmark** (50 vectors × 384 dims, numpy zero-copy PyO3):
- Rust FFT: **4.7 μs/vector** (235.9 μs total)
- NumPy FFT: **200.1 μs/vector** (10,003.6 μs total)
- **Speedup: 42.4x**

Single bind: 38.5 μs (Rust) vs 58.1 μs (NumPy) → **1.51x**

**Python bridge**: `hrr.py` bind/unbind now uses Rust FFT as fast path.
Circular reversal for unbind: `np.roll(b[::-1], 1)` (conjugate FFT equivalence for real signals).
Roundtrip similarity verified: 0.7134 (matches NumPy exactly).

### #2 FMA + Horizontal Sum + L1 Tiling ✅

**File**: `core/whitemagic-rust/src/inference/simd_ops.rs`

Three improvements to batch cosine similarity:

1. **FMA** (`_mm256_fmadd_ps`): Fuses multiply+add into one instruction (~1.5-2x on dot products)
2. **Proper horizontal sum**: `_mm256_extractf128_ps` + `_mm_add_ps` + `_mm_movehdup_ps` + `_mm_movehl_ps` + `_mm_add_ss` — replaces scalar loop over 8 array elements
3. **L1 cache tiling**: 16-vector tiles (24KB) stay within 32KB L1d alongside query vector

**Benchmark** (16K vectors × 384 dims, numpy zero-copy):
- Rust FMA: 5,042 μs | NumPy (MKL BLAS): 3,657 μs | Ratio: 0.73x
- Note: NumPy uses multi-threaded MKL BLAS. Our single-thread Rust FMA is still valuable for GIL-released parallel workers and f32 (half bandwidth vs old f64 path).

**Python bridge**: `embedding_similarity.py` `batch_cosine_similarity_numpy` now tries Rust FMA path first for pre-normalized vectors.

### #3 PyO3 Numpy Zero-Copy Bindings ✅

**File**: `core/whitemagic-rust/src/inference_pymodule.rs`

Added `py_batch_cosine_numpy` and `py_batch_circular_convolution_numpy` using `PyReadonlyArray1/2` for zero-copy numpy → Rust. GIL released during computation via `py.allow_threads()`.

This eliminated the Python list serialization bottleneck that made the list-based path 10x slower than NumPy.

### Test Results ✅

- **7 Rust unit tests**: all pass (cosine, dot, euclidean, FFT conv, topk, 384-dim)
- **7,006 Python tests passed**, 9 pre-existing failures (unrelated: galaxy routing, path hygiene, bounty platforms)
- **Zero regressions** from our changes

---

## Remaining Work

### #4 Rust Hybrid Search (FTS5 + Cosine in one call) ✅

**File**: `core/whitemagic-rust/src/memory/sqlite_accel.rs`

Combined FTS5 full-text search + embedding cosine similarity + galactic weighting in one Rust call.
Eliminates Python N+1 pattern (FTS query → N embedding queries → Python cosine loop → score combine).

Added `open_db_readonly()` for read-only queries — skips expensive `PRAGMA journal_mode = WAL` roundtrip.

**Benchmark** (aria galaxy, 173 memories, 16 embeddings):
- Hybrid search: **1.5 ms/call** (readonly connection)
- FTS-only: **1.3 ms/call** (readonly connection)
- Embedding + cosine overhead: **162 μs** (batch IN query + scalar cosine)
- First call: 1.3 ms (connection warmup), subsequent: 1.5 ms

**Python bridge**: `rust_accelerators.py` `sqlite_hybrid_search()` wrapper added.
Also exposed 5 pre-existing sqlite_accel functions that were previously unregistered:
`sqlite_fts_search`, `sqlite_batch_update_galactic`, `sqlite_decay_drift`, `sqlite_zone_stats`, `sqlite_export_for_mining`.

### #5 Embedding Batch Pack/Unpack in Rust (PyO3) ✅

**File**: `core/whitemagic-rust/src/inference_pymodule.rs`

Added `py_batch_pack_embeddings` (numpy → Vec<Vec<u8>> blobs) and `py_batch_unpack_embeddings` (blobs → numpy array + ids).

**Benchmark** (100 embeddings × 384 dims):
- Pack: Rust **1.0 ms** vs Python struct.pack **3.5 ms** → **2.1x**
- Unpack: Rust **2.7 ms** vs Python struct.unpack **4.1 ms** → **1.5x**
- Unpack vs numpy.frombuffer: 2.7 ms vs 2.5 ms (parity — Rust returns proper numpy array)

### #6 Dispatch Pipeline Import Hoisting ✅

**File**: `core/whitemagic/tools/middleware.py`

Hoisted 6 inline imports from `mw_semantic_cache` hot path to module-level lazy singletons via `_ensure_semantic_cache_cached()`:
- `json`, `get_unified_cache`, `get_prefetcher`, `QueryCache`, `CACHE_DIR`, `TOOL_TO_GANA`

Uses lambda wrappers that call through the module so test patches (`mock.patch`) still work correctly.

**Expected speedup**: Eliminates 6 `import` statement lookups per cache-hit call (microseconds → nanoseconds for dict check on `_semantic_cache_cached` flag).

### Test Results ✅

- **7,004 passed**, 5 pre-existing failures (citta introspection, bounty platforms, galaxy wiring)
- **Zero new regressions** from all 6 optimization items

---

## Hardware Constraints (Intel i5-8350U)

| Feature | Available | Impact |
|---------|-----------|--------|
| AVX2 | ✅ | 256-bit, 8×f32 per instruction |
| FMA | ✅ | Fused multiply+add |
| AVX-512 | ❌ | Kaby Lake max is 256-bit |
| L1d | 32 KB | 16-vector tiles for 384-dim |
| L2 | 256 KB | ~170 vectors |
| L3 | 6 MB | ~4,000 vectors (shared) |
| Turbo | 3.6 GHz | Thermal throttle ~2.0 GHz sustained |
| /dev/shm | 7.8 GB | Ring buffer SHM (227 MB used) |

---

## Files Changed

| File | Change |
|------|--------|
| `core/whitemagic-rust/src/inference/simd_ops.rs` | **New** — FMA+tiling cosine, FFT convolution, dot, euclidean, topk (440 lines) |
| `core/whitemagic-rust/src/inference/mod.rs` | Added `simd_ops` module |
| `core/whitemagic-rust/src/inference_pymodule.rs` | 10 PyO3 functions (SIMD + numpy + pack/unpack) |
| `core/whitemagic-rust/src/memory/sqlite_accel.rs` | `open_db_readonly()`, `sqlite_hybrid_search()` |
| `core/whitemagic-rust/src/memory/mod.rs` | Uncommented `sqlite_accel` module |
| `core/whitemagic-rust/src/lib.rs` | Registered 6 sqlite_accel PyO3 functions |
| `core/whitemagic-rust/Cargo.toml` | Added `rustfft = "6.2"` |
| `core/whitemagic/core/memory/hrr.py` | Rust FFT fast path for bind/unbind |
| `core/whitemagic/core/memory/embedding_similarity.py` | Rust FMA fast path for batch cosine |
| `core/whitemagic/optimization/rust_accelerators.py` | `sqlite_hybrid_search()` Python bridge |
| `core/whitemagic/tools/middleware.py` | Hoisted 6 inline imports in `mw_semantic_cache` |
