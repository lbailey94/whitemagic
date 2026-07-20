# Inference Acceleration Strategy — 2026

**Version**: v25.1.0
**Updated**: 2026-07-20
**Status**: Research → Implementation Planning

---

## 1. Current State

WhiteMagic already has substantial inference infrastructure:

### Ternary LUT Kernels (Rust, AVX2)
**File**: `core/whitemagic-rust/src/inference/ternary_kernel.rs`

3-tier dispatch based on dimension size:
- **k < 64**: T-MAC LUT approach — `blendv_ps` for multiplication-free selection (best precision)
- **k >= 64**: Integer SIMD via `_mm256_madd_epi16` — single instruction for 16 int16 multiplies
- **k >= 128**: I2_S kernel via `_mm256_maddubs_epi16` — highest throughput, int8 activations

Features:
- 16x data compression (2 bits per weight vs 32 for fp32)
- Zero FP multiplications in inner loop
- PyO3 bindings (`py_ternary_gemv`) exposed to Python
- Streaming engine with layer-by-layer loading (92x RAM reduction)
- Quantized KV cache (q8_0 default, 50% reduction)

### Speculative Decoding Pipeline
**Files**: `speculative_decoder.py`, `speculative_wiring.py`, `llama_cpp.py`

Architecture:
- **Draft models**: BitMamba-2 255M (ternary SSM), SmolLM2-360M
- **Verify models**: llama.cpp (Qwen3-4B, Phi4-mini), bitnet.cpp (BitNet b1.58 2B4T, Falcon3-1B-1.58)
- **Adaptive K**: Adjusts draft token count (1-8) based on acceptance rate
- **Pipelined mode**: Core-pinned draft/verify via ring buffers (☰ Qián → ☲ Lí)
- **ngram-mod**: Built into llama.cpp config (no draft model needed, ~16MB hash pool)
- **Stats tracking**: Acceptance rate, speedup, draft/verify latency

### llama.cpp Integration
**File**: `llama_cpp.py`

- KV cache quantization (q8_0 default, q4_0 available)
- Flash attention
- Parallel slots (continuous batching, default 4)
- JSON schema / GBNF grammar constraints
- Dual-model manager (background + foreground)
- ngram-mod speculative decoding with configurable n-match/n-min/n-max

---

## 2. Research Findings — What's New (2026)

### 2a. Vec-LUT (MobiSys 2026) — **Highest Priority**

**Paper**: "Vec-LUT: Vector Table Lookup for Parallel Ultra-Low-Bit LLM Inference on Edge Devices"
**Code**: https://github.com/lgs001elite/vlut.cpp

**Problem**: T-MAC's scalar LUT paradigm (1→1 lookup) underutilizes memory bandwidth (<40%) during parallel inference. Each token requires an independent table, causing N× repetitive table loading.

**Solution**: Vector LUT paradigm — 1→N lookup that turns random lookup into contiguous vector addition.
- Vector LUT-centric tensor layout
- Cache-aware streamed lookup
- Reduces lookup cost from ~50% of kernel time to <1%
- Lossless ternary packings: I1 (b1.60) and I2 (b2.00)

**Results**:
- 4.2× speedup over T-MAC (I1 packing)
- 2.6× speedup over T-MAC (I2 packing)
- 273.5 tokens/s on $0.50/h AWS CPU server (continuous batching)
- 2 CPU cores on Snapdragon 8 Elite outperforms NPU-based solution by 1.1×

**Relevance to WhiteMagic**: Our `ternary_kernel.rs` uses the scalar T-MAC LUT approach. Upgrading to Vec-LUT would directly improve parallel inference throughput (multiple concurrent sessions, citta heartbeats + user chat).

### 2b. AVX-512 VNNI Support

**Current gap**: Our kernels only target AVX2 (256-bit). AVX-512 (512-bit) offers 2x vector width.

**Key instructions**:
- `_mm512_dpbusd_epi32` (VNNI): 64 INT8 muls + 16 INT32 adds per cycle — 2x AVX2 throughput
- `_mm512_fmadd_ps`: 16 FP32 fused multiply-adds per cycle
- AMX `_tile_dpbf16ps`: 16×16 tile BF16 matrix multiply (Sapphire Rapids+)

**Performance hierarchy** (INT8 dot product throughput per cycle):
| ISA | Width | Throughput |
|-----|-------|-----------|
| AVX2 maddubs | 256-bit | 64 ops |
| AVX-512 VNNI | 512-bit | 256 ops (4x) |
| AMX tiles | 16×16 | 512+ ops |

**Genesis kernel project** (https://github.com/Anuar81/genesis-kernel):
- AVX-512 NF4 dequantization + matmul for MoE CPU offload
- Q4_K kernel beats ggml stock by 1.5% (found via brute-force instruction injection)
- Runtime x86-64 machine code generation (no compiler needed)
- Zen 4 microarchitectural optimizations (cache-line-aligned NOPs, prefetch hints)

**Relevance**: Our consumer laptop (Dell Inspiron 3582) may not have AVX-512, but server deployments and newer AMD Zen 4+ / Intel Ice Lake+ systems do. Adding AVX-512 path with runtime detection is a straightforward 2x win for capable hardware.

### 2c. Speculative Decoding Advances

#### LK Losses (arXiv 2602.23881)
- **Direct acceptance rate optimization** instead of KL divergence proxy
- 8-10% improvement in average acceptance length
- Zero computational overhead, drop-in replacement for draft training
- **Relevance**: Could improve our BitMamba draft model training

#### MARS — Margin-Aware Speculative Verification (ACL 2026)
- **Training-free** verification strategy
- Adaptive tie-breaking: accepts draft tokens when target model has weak preference
- Logit margin analysis: relaxes verification only when strict checking provides minimal benefit
- Consistent speedup across 8B-235B models, chat/coding/reasoning benchmarks
- **Relevance**: Drop-in improvement to our `_accept_reject()` method in `speculative_decoder.py`

#### UniVer — Unified Multi-step + Multi-draft (arXiv 2605.04543)
- Tree-based verification as conditional Optimal Transport
- 4.2-8.5% acceptance length improvement over recursive rejection sampling
- Lossless — maintains exact distributional alignment
- **Relevance**: Next-gen verification for tree-based speculative decoding

#### VSD — Variational Speculative Decoding (arXiv 2602.05774)
- Sequence-level acceptance optimization (not just token-level)
- 9.6% speedup over EAGLE-3
- EM procedure with adaptive rejection weighting
- **Relevance**: Future draft model training improvement

### 2d. CPU Inference Architecture

#### Cache-Resident Inference (arXiv 2606.25353)
- GB-scale last-level caches (3D-stacked) can hold model weights on-chip
- Weight-attention decoupled architecture
- 2.04x-11.51x TPOT speedup over llama.cpp
- **Relevance**: Future optimization for server-class CPUs with large L3 caches

#### LiLo — IAA + AMX + AVX Orchestration (HPCA 2026)
- Intel IAA (In-memory Analytics Accelerator) for compressed weight decompression
- AMX for compute, IAA for decompression, AVX for bridging
- 4.9x latency reduction for Llama3-405B under memory constraints
- **Relevance**: Intel Sapphire Rapids+ server optimization path

---

## 3. Implementation Plan

### Phase 1: Vec-LUT Kernel Upgrade (2-3 sessions)
**Priority**: HIGH — Direct improvement to existing ternary kernels

1. **Study vlut.cpp** I1/I2 packing format and vector LUT paradigm
2. **Implement Vec-LUT in Rust** alongside existing AVX2 kernels:
   - New packing format: I1 (1.60 BPW) and I2 (2.00 BPW) 
   - Vector LUT-centric tensor layout (axis reordering + tiling)
   - Cache-aware streamed lookup (contiguous vector addition)
   - 1→N lookup replacing 1→1 scalar LUT
3. **Add 4th dispatch tier** in `ternary_gemv()`:
   - k >= 128 + parallel batch > 1: Vec-LUT kernel
   - k >= 128 + single token: existing I2_S kernel
4. **Benchmark** against existing kernels (single-token and parallel)
5. **Expose via PyO3** with new packing functions

**Expected result**: 2-4x throughput improvement for parallel inference (multiple concurrent sessions)

### Phase 2: AVX-512 VNNI Path (1-2 sessions)
**Priority**: MEDIUM — 2x throughput on capable hardware

1. **Add runtime detection**: `is_x86_feature_detected!("avx512f")` + `avx512vnni`
2. **Implement `ternary_gemv_avx512_vnni`**:
   - Use `_mm512_dpbusd_epi32` for INT8 dot product (256 ops/cycle)
   - ZMM registers (512-bit) for 2x vector width
   - Cache-aware tiling for ZMM register pressure
3. **Add 5th dispatch tier**: AVX-512 path when available, fallback to AVX2
4. **Test on Zen 4+ / Ice Lake+** if available

**Expected result**: 2x throughput on AVX-512 VNNI hardware, zero impact on non-AVX-512 systems

### Phase 3: MARS Verification (1 session)
**Priority**: HIGH — Training-free, immediate improvement

1. **Study MARS paper** — logit margin ratio `r_t = z_{(1)} / z_{(2)}`
2. **Modify `_accept_reject()`** in `speculative_decoder.py`:
   - Add margin threshold `θ` (default 0.9)
   - When draft token matches verify's top-1: accept (existing behavior)
   - When draft token matches verify's top-2 AND `r_t > θ`: accept (new — adaptive tie-breaking)
   - When draft token doesn't match top-2: reject (existing behavior)
3. **Add margin config** to `SpeculativeDecoder.__init__()`
4. **Benchmark** acceptance rate improvement

**Expected result**: 5-15% acceptance rate improvement with zero quality loss

### Phase 4: ngram-mod Tuning (0.5 session)
**Priority**: MEDIUM — Quick wins from parameter tuning

1. **Benchmark current ngram-mod params**: n-match=24, n-min=48, n-max=64
2. **Sweep parameter space**: n-match ∈ {16, 20, 24, 32}, n-min ∈ {32, 48, 64}, n-max ∈ {48, 64, 96}
3. **Find optimal for typical WhiteMagic workloads** (citta heartbeats, tool dispatch, chat)
4. **Auto-tune** based on workload type (short responses vs long generation)

**Expected result**: 10-30% speculative decoding improvement from parameter tuning alone

### Phase 5: Future Directions (Research)

- **LK Loss draft training**: Retrain BitMamba-2 with LK loss objective for 8-10% acceptance improvement
- **UniVer tree verification**: Implement conditional OT for multi-draft speculative decoding
- **Cache-resident inference**: Weight-attention decoupled architecture for server-class CPUs
- **AMX tile operations**: For batch > 1 on Sapphire Rapids+ (16×16 tile matrix multiply)
- **FP8 KV cache**: Following vLLM's CPU FP8 attention implementation (AVX-512 / AMX paths)

---

## 4. Benchmarking Plan

All benchmarks should be measured on:
1. **Dell Inspiron 3582** (consumer, AVX2 only) — baseline
2. **AWS c7i.metal** or equivalent (AVX-512 VNNI) — if available
3. **Raspberry Pi 5** (ARM NEON) — edge deployment

Metrics:
- Tokens/s (single-token decode)
- Tokens/s (parallel batch, N=4, N=16, N=32)
- Memory bandwidth utilization (% of theoretical)
- Acceptance rate (speculative decoding)
- End-to-end latency (prompt + generation)
- Energy consumption (if measurable)

---

## 5. References

| Paper/Project | Venue | Key Contribution |
|---------------|-------|-----------------|
| T-MAC (arXiv 2407.00088) | 2024 | LUT-based mpGEMM for CPU |
| Vec-LUT (arXiv 2512.06443) | MobiSys 2026 | Vector LUT paradigm, 4.2x over T-MAC |
| LK Losses (arXiv 2602.23881) | 2026 | Direct acceptance rate optimization |
| MARS | ACL 2026 Findings | Margin-aware verification, training-free |
| UniVer (arXiv 2605.04543) | 2026 | Unified multi-step + multi-draft OT |
| VSD (arXiv 2602.05774) | 2026 | Variational sequence-level acceptance |
| genesis-kernel | GitHub | AVX-512 NF4/Q4_K runtime codegen |
| Cache-Resident (arXiv 2606.25353) | 2026 | GB-scale LLC cache-resident inference |
| LiLo | HPCA 2026 | IAA + AMX + AVX orchestration |
| vLLm CPU FP8 (PR #39445) | 2026 | AVX-512 / AMX FP8 KV cache |
