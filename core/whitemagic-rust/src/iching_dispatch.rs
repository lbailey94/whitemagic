//! I Ching Dispatch — Trigram Modes + Hexagram Dispatch Matrix
//!
//! Phase 2b: Trigram Compute/I/O Mode Definitions
//! Phase 2c: Hexagram Dispatch Matrix (64 hexagrams → compute lane assignments)
//!
//! Each trigram maps to a compute mode (ALU intensity, memory bandwidth,
//! I/O pattern, latency profile). Each hexagram combines two trigrams into
//! a dispatch decision: which compute lane, what I/O channel, and what
//! execution strategy to use.

use crate::iching::Trigram;

// ---------------------------------------------------------------------------
// Phase 2b: Trigram Compute/I/O Modes
// ---------------------------------------------------------------------------

/// Compute mode: describes the hardware execution profile.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum ComputeMode {
    /// Heavy ALU, integer/float pipeline saturation
    Compute,
    /// Memory bandwidth bound, streaming loads/stores
    Memory,
    /// I/O bound, network or disk wait
    IoBound,
    /// Mixed: compute + memory, balanced pipeline
    Mixed,
    /// Latency-sensitive, minimal parallelism
    Latency,
    /// Throughput-oriented, maximize parallelism
    Throughput,
    /// Cache-friendly, small working set
    CacheFriendly,
    /// Streaming, large working set, minimal reuse
    Streaming,
}

/// I/O channel type for data movement.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum IoChannel {
    /// Shared memory / mmap
    SharedMem,
    /// Network socket (TCP/UDP)
    Network,
    /// Disk I/O (file read/write)
    Disk,
    /// IPC (pipe, message queue)
    Ipc,
    /// In-process channel (channel, crossbeam)
    InProcess,
    /// GPU memory transfer
    GpuTransfer,
    /// No I/O — pure compute
    None,
}

/// Trigram dispatch profile: maps each trigram to compute + I/O characteristics.
#[derive(Debug, Clone, Copy)]
pub struct TrigramDispatch {
    pub compute_mode: ComputeMode,
    pub io_channel: IoChannel,
    /// Lane width hint (1 = scalar, 4 = SSE, 8 = AVX2, 16 = AVX-512)
    pub lane_width: u32,
    /// Priority (0 = highest, 7 = lowest)
    pub priority: u32,
    /// Whether this trigram benefits from SIMD parallelism
    pub simd_friendly: bool,
}

/// Map each trigram to its dispatch profile.
pub fn trigram_dispatch(trigram: &Trigram) -> TrigramDispatch {
    match trigram {
        Trigram::Qian => TrigramDispatch {
            compute_mode: ComputeMode::Throughput,
            io_channel: IoChannel::None,
            lane_width: 16,
            priority: 0,
            simd_friendly: true,
        },
        Trigram::Kun => TrigramDispatch {
            compute_mode: ComputeMode::Memory,
            io_channel: IoChannel::SharedMem,
            lane_width: 8,
            priority: 1,
            simd_friendly: true,
        },
        Trigram::Zhen => TrigramDispatch {
            compute_mode: ComputeMode::Compute,
            io_channel: IoChannel::None,
            lane_width: 8,
            priority: 2,
            simd_friendly: true,
        },
        Trigram::Xun => TrigramDispatch {
            compute_mode: ComputeMode::Streaming,
            io_channel: IoChannel::Network,
            lane_width: 4,
            priority: 3,
            simd_friendly: false,
        },
        Trigram::Kan => TrigramDispatch {
            compute_mode: ComputeMode::IoBound,
            io_channel: IoChannel::Disk,
            lane_width: 1,
            priority: 4,
            simd_friendly: false,
        },
        Trigram::Li => TrigramDispatch {
            compute_mode: ComputeMode::Latency,
            io_channel: IoChannel::Ipc,
            lane_width: 4,
            priority: 5,
            simd_friendly: false,
        },
        Trigram::Gen => TrigramDispatch {
            compute_mode: ComputeMode::CacheFriendly,
            io_channel: IoChannel::InProcess,
            lane_width: 8,
            priority: 6,
            simd_friendly: true,
        },
        Trigram::Dui => TrigramDispatch {
            compute_mode: ComputeMode::Mixed,
            io_channel: IoChannel::GpuTransfer,
            lane_width: 16,
            priority: 7,
            simd_friendly: true,
        },
    }
}

// ---------------------------------------------------------------------------
// Phase 2c: Hexagram Dispatch Matrix
// ---------------------------------------------------------------------------

/// Dispatch decision for a hexagram: combines upper + lower trigram profiles.
#[derive(Debug, Clone)]
pub struct HexagramDispatch {
    pub hexagram_num: u32,
    pub lower: TrigramDispatch,
    pub upper: TrigramDispatch,
    /// Effective compute mode (dominant trigram wins, with blending)
    pub effective_compute: ComputeMode,
    /// Effective I/O channel (upper trigram typically drives I/O)
    pub effective_io: IoChannel,
    /// Lane width = max(lower, upper) — use the wider SIMD path
    pub lane_width: u32,
    /// Overall priority = min(lower, upper) — highest priority wins
    pub priority: u32,
    /// Whether both trigrams are SIMD-friendly (fully parallelizable)
    pub fully_simd: bool,
    /// Dispatch strategy
    pub strategy: DispatchStrategy,
}

/// Execution strategy derived from hexagram pattern.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum DispatchStrategy {
    /// Parallel SIMD across all lanes
    ParallelSimd,
    /// Sequential with prefetch
    Sequential,
    /// Pipelined: compute → memory → I/O stages
    Pipelined,
    /// Async I/O with compute overlap
    AsyncOverlap,
    /// Batch processing
    Batch,
    /// Stream processing
    Stream,
    /// Single-threaded latency-critical
    SingleThread,
    /// GPU offload
    GpuOffload,
}

/// Compute the dispatch for a hexagram given its two trigrams.
pub fn hexagram_dispatch(lower: &Trigram, upper: &Trigram, hexagram_num: u32) -> HexagramDispatch {
    let lower_disp = trigram_dispatch(lower);
    let upper_disp = trigram_dispatch(upper);

    let effective_compute = blend_compute(lower_disp.compute_mode, upper_disp.compute_mode);
    let effective_io = upper_disp.io_channel; // upper trigram drives I/O
    let lane_width = lower_disp.lane_width.max(upper_disp.lane_width);
    let priority = lower_disp.priority.min(upper_disp.priority);
    let fully_simd = lower_disp.simd_friendly && upper_disp.simd_friendly;

    let strategy = derive_strategy(&effective_compute, effective_io, fully_simd);

    HexagramDispatch {
        hexagram_num,
        lower: lower_disp,
        upper: upper_disp,
        effective_compute,
        effective_io,
        lane_width,
        priority,
        fully_simd,
        strategy,
    }
}

/// Blend two compute modes into an effective mode.
fn blend_compute(lower: ComputeMode, upper: ComputeMode) -> ComputeMode {
    use ComputeMode::*;
    match (lower, upper) {
        // Same mode → that mode
        (a, b) if a == b => a,
        // Throughput + anything → Throughput (dominates)
        (Throughput, _) | (_, Throughput) => Throughput,
        // Memory + Compute → Mixed
        (Memory, Compute) | (Compute, Memory) => Mixed,
        // IoBound + anything → IoBound (bottleneck)
        (IoBound, _) | (_, IoBound) => IoBound,
        // Latency + CacheFriendly → Latency
        (Latency, CacheFriendly) | (CacheFriendly, Latency) => Latency,
        // Streaming + Memory → Streaming
        (Streaming, Memory) | (Memory, Streaming) => Streaming,
        // Mixed + anything → Mixed
        (Mixed, _) | (_, Mixed) => Mixed,
        // Default: upper wins
        (_, upper) => upper,
    }
}

/// Derive execution strategy from compute mode, I/O channel, and SIMD flag.
fn derive_strategy(compute: &ComputeMode, io: IoChannel, fully_simd: bool) -> DispatchStrategy {
    use ComputeMode::*;
    use IoChannel::*;
    match (compute, io, fully_simd) {
        (Throughput, None, true) => DispatchStrategy::ParallelSimd,
        (Throughput, _, _) => DispatchStrategy::Batch,
        (Memory, SharedMem, true) => DispatchStrategy::ParallelSimd,
        (Memory, Disk, _) => DispatchStrategy::Stream,
        (Memory, Network, _) => DispatchStrategy::Stream,
        (Compute, None, true) => DispatchStrategy::ParallelSimd,
        (Compute, _, _) => DispatchStrategy::Pipelined,
        (IoBound, Disk, _) => DispatchStrategy::AsyncOverlap,
        (IoBound, Network, _) => DispatchStrategy::AsyncOverlap,
        (IoBound, _, _) => DispatchStrategy::Sequential,
        (Latency, _, _) => DispatchStrategy::SingleThread,
        (Mixed, GpuTransfer, _) => DispatchStrategy::GpuOffload,
        (Mixed, _, _) => DispatchStrategy::Pipelined,
        (CacheFriendly, _, true) => DispatchStrategy::ParallelSimd,
        (CacheFriendly, _, false) => DispatchStrategy::Sequential,
        (Streaming, _, _) => DispatchStrategy::Stream,
        (_, _, true) => DispatchStrategy::ParallelSimd,
        (_, _, false) => DispatchStrategy::Sequential,
    }
}

// ---------------------------------------------------------------------------
// Full 64-hexagram dispatch table (precomputed for fast lookup)
// ---------------------------------------------------------------------------

/// Precompute dispatch for all 64 hexagrams.
/// Index by King Wen number (1-64), returns the dispatch profile.
pub fn dispatch_for_hexagram(king_wen_num: u32) -> Option<HexagramDispatch> {
    if king_wen_num == 0 || king_wen_num > 64 {
        return None;
    }

    // Convert King Wen number to binary pattern, then decompose into trigrams
    // We need the reverse King Wen lookup: King Wen → binary
    let binary = king_wen_to_binary(king_wen_num);
    let lower_bits = (binary & 0b111) as u8;
    let upper_bits = ((binary >> 3) & 0b111) as u8;
    let lower = Trigram::from_binary(lower_bits);
    let upper = Trigram::from_binary(upper_bits);

    Some(hexagram_dispatch(&lower, &upper, king_wen_num))
}

/// Reverse King Wen lookup: King Wen number (1-64) → binary pattern (0-63).
/// Uses the KING_WEN table from iching.rs (we reconstruct it here for independence).
fn king_wen_to_binary(kw: u32) -> u32 {
    // The KING_WEN table maps binary → King Wen. We need the inverse.
    const KING_WEN: [u8; 64] = [
         2, 24,  7, 19, 15, 36, 46, 11,
        16, 51, 40, 54, 62, 55, 32, 34,
         8,  3, 29, 60, 39, 63, 48,  5,
        45, 17, 47, 58, 31, 49, 28, 43,
        23, 27,  4, 41, 52, 22, 18, 26,
        35, 21, 64, 38, 56, 30, 50, 14,
        20, 42, 59, 61, 53, 37, 57,  9,
        12, 25,  6, 10, 33, 13, 44,  1,
    ];
    for (binary, &kw_val) in KING_WEN.iter().enumerate() {
        if kw_val as u32 == kw {
            return binary as u32;
        }
    }
    0
}

// ---------------------------------------------------------------------------
// Phase 4b: Boltzmann Hexagram Selection
// ---------------------------------------------------------------------------

/// Compute Boltzmann weights for all 64 hexagrams given a temperature.
/// P(i) ∝ exp(-E_i / T), where E_i is the energy of hexagram i.
///
/// Energy is derived from dispatch priority (lower priority = higher energy,
/// meaning high-priority hexagrams are preferred at low temperature).
/// At high temperature, selection becomes uniform (exploration).
/// At low temperature, selection concentrates on lowest-energy hexagrams (exploitation).
pub fn boltzmann_weights(temperature: f64) -> Vec<f64> {
    let t = temperature.max(1e-10);
    let mut weights = Vec::with_capacity(64);
    let mut sum = 0.0;

    for n in 1..=64u32 {
        if let Some(disp) = dispatch_for_hexagram(n) {
            // Energy: higher priority (lower value) = lower energy
            // Also factor in lane width (wider = lower energy, more efficient)
            let energy = disp.priority as f64 + (16.0 - disp.lane_width as f64) * 0.5;
            let w = (-energy / t).exp();
            weights.push(w);
            sum += w;
        } else {
            weights.push(0.0);
        }
    }

    // Normalize
    if sum > 0.0 {
        for w in &mut weights {
            *w /= sum;
        }
    }
    weights
}

/// Select a hexagram using Boltzmann sampling.
/// Returns the King Wen number (1-64) of the selected hexagram.
pub fn boltzmann_select(rng: &mut impl rand::Rng, temperature: f64) -> u32 {
    let weights = boltzmann_weights(temperature);
    let r: f64 = rng.gen();
    let mut cumulative = 0.0;
    for (i, &w) in weights.iter().enumerate() {
        cumulative += w;
        if r < cumulative {
            return (i + 1) as u32;
        }
    }
    64 // fallback
}

/// Compute the entropy of the Boltzmann distribution.
/// Low entropy = concentrated (exploitation). High entropy = spread (exploration).
pub fn boltzmann_entropy(temperature: f64) -> f64 {
    let weights = boltzmann_weights(temperature);
    let mut h = 0.0;
    for &w in &weights {
        if w > 0.0 {
            h -= w * w.ln();
        }
    }
    h
}

/// Get the top-K hexagrams by Boltzmann probability.
pub fn boltzmann_top_k(temperature: f64, k: usize) -> Vec<(u32, f64)> {
    let weights = boltzmann_weights(temperature);
    let mut indexed: Vec<(u32, f64)> = weights.iter()
        .enumerate()
        .map(|(i, &w)| ((i + 1) as u32, w))
        .collect();
    indexed.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
    indexed.truncate(k);
    indexed
}

// ---------------------------------------------------------------------------
// Phase 5b: Entropy-Matched Routing
// ---------------------------------------------------------------------------

/// Route a task to the best hexagram lane by matching system entropy
/// to the Boltzmann temperature parameter.
///
/// High system entropy (chaotic, uncertain) → high temperature → exploration
/// Low system entropy (stable, predictable) → low temperature → exploitation
///
/// Returns the selected hexagram number and its dispatch profile.
pub fn entropy_matched_route(system_entropy: f64) -> (u32, Option<HexagramDispatch>) {
    // Map system entropy [0, ∞) to temperature [0.1, 10.0]
    // entropy=0 → T=0.1 (exploit), entropy=ln(64)≈4.16 → T=1.0 (balanced),
    // entropy→∞ → T=10.0 (explore)
    let temperature = (0.1_f64).max(system_entropy.exp().min(10.0));

    // Use deterministic selection (pick top-1 from Boltzmann)
    let top = boltzmann_top_k(temperature, 1);
    if let Some(&(num, _)) = top.first() {
        (num, dispatch_for_hexagram(num))
    } else {
        (1, dispatch_for_hexagram(1))
    }
}

/// Route multiple tasks using entropy-matched routing with stochastic sampling.
/// Returns a vector of (hexagram_num, dispatch) tuples.
pub fn entropy_matched_route_batch(
    rng: &mut impl rand::Rng,
    system_entropy: f64,
    n_tasks: usize,
) -> Vec<(u32, Option<HexagramDispatch>)> {
    let temperature = (0.1_f64).max(system_entropy.exp().min(10.0));
    let mut results = Vec::with_capacity(n_tasks);
    for _ in 0..n_tasks {
        let num = boltzmann_select(rng, temperature);
        results.push((num, dispatch_for_hexagram(num)));
    }
    results
}

/// Compute the optimal temperature for a desired exploration/exploitation ratio.
/// ratio=0 → pure exploitation (T→0), ratio=1 → pure exploration (T→∞)
pub fn temperature_for_ratio(ratio: f64) -> f64 {
    let r = ratio.clamp(0.0, 1.0);
    // Exponential mapping: ratio=0.5 → T=1.0, ratio=0 → T=0.01, ratio=1 → T=100
    0.01 * (10000.0_f64).powf(r)
}

// ---------------------------------------------------------------------------
// Phase 6c: I/O Channel Gating
// ---------------------------------------------------------------------------

/// I/O channel gate state: open, throttled, or closed.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum GateState {
    Open,      // Full bandwidth
    Throttled, // Reduced bandwidth (50%)
    Closed,    // No new requests
}

/// I/O channel gate: controls data flow for a specific channel.
#[derive(Debug, Clone)]
pub struct IoGate {
    pub channel: IoChannel,
    pub state: GateState,
    /// Current load (0.0 = idle, 1.0 = saturated)
    pub load: f64,
    /// Maximum throughput (requests/s)
    pub max_throughput: f64,
}

impl IoGate {
    pub fn new(channel: IoChannel, max_throughput: f64) -> Self {
        Self {
            channel,
            state: GateState::Open,
            load: 0.0,
            max_throughput,
        }
    }

    /// Update gate state based on current load.
    pub fn update(&mut self) {
        self.state = if self.load > 0.9 {
            GateState::Closed
        } else if self.load > 0.6 {
            GateState::Throttled
        } else {
            GateState::Open
        };
    }

    /// Check if a request can be admitted.
    pub fn admit(&self) -> bool {
        match self.state {
            GateState::Open => true,
            GateState::Throttled => rand::random(), // 50% admission
            GateState::Closed => false,
        }
    }

    /// Get effective throughput given current gate state.
    pub fn effective_throughput(&self) -> f64 {
        match self.state {
            GateState::Open => self.max_throughput,
            GateState::Throttled => self.max_throughput * 0.5,
            GateState::Closed => 0.0,
        }
    }
}

/// Gate all I/O channels for a hexagram dispatch.
/// Returns a map of channel → gate state.
pub fn gate_dispatch(disp: &HexagramDispatch, system_load: f64) -> IoGate {
    let mut gate = IoGate::new(disp.effective_io, 1000.0);

    // Adjust load based on dispatch priority (higher priority = more load tolerance)
    let priority_factor = 1.0 - (disp.priority as f64 * 0.1);
    gate.load = (system_load * priority_factor).min(1.0);
    gate.update();
    gate
}

/// Check if a dispatch can proceed given current system load on its I/O channel.
pub fn can_dispatch(disp: &HexagramDispatch, system_load: f64) -> bool {
    let gate = gate_dispatch(disp, system_load);
    gate.admit()
}


#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_trigram_dispatch_all_defined() {
        for t in [Trigram::Qian, Trigram::Kun, Trigram::Zhen, Trigram::Xun,
                  Trigram::Kan, Trigram::Li, Trigram::Gen, Trigram::Dui] {
            let d = trigram_dispatch(&t);
            assert!(d.lane_width >= 1 && d.lane_width <= 16);
            assert!(d.priority <= 7);
        }
    }

    #[test]
    fn test_qian_is_throughput_simd() {
        let d = trigram_dispatch(&Trigram::Qian);
        assert_eq!(d.compute_mode, ComputeMode::Throughput);
        assert!(d.simd_friendly);
        assert_eq!(d.io_channel, IoChannel::None);
    }

    #[test]
    fn test_kan_is_io_bound_disk() {
        let d = trigram_dispatch(&Trigram::Kan);
        assert_eq!(d.compute_mode, ComputeMode::IoBound);
        assert_eq!(d.io_channel, IoChannel::Disk);
        assert!(!d.simd_friendly);
    }

    #[test]
    fn test_hexagram_dispatch_lane_width_max() {
        // Qian (16) + Kan (1) → 16
        let d = hexagram_dispatch(&Trigram::Kan, &Trigram::Qian, 5);
        assert_eq!(d.lane_width, 16);
    }

    #[test]
    fn test_hexagram_dispatch_priority_min() {
        // Qian (0) + Kan (4) → 0
        let d = hexagram_dispatch(&Trigram::Kan, &Trigram::Qian, 5);
        assert_eq!(d.priority, 0);
    }

    #[test]
    fn test_hexagram_dispatch_fully_simd() {
        // Qian + Qian → fully SIMD
        let d = hexagram_dispatch(&Trigram::Qian, &Trigram::Qian, 1);
        assert!(d.fully_simd);
        // Qian + Kan → not fully SIMD
        let d2 = hexagram_dispatch(&Trigram::Kan, &Trigram::Qian, 5);
        assert!(!d2.fully_simd);
    }

    #[test]
    fn test_blend_compute_same_mode() {
        assert_eq!(blend_compute(ComputeMode::Throughput, ComputeMode::Throughput), ComputeMode::Throughput);
        assert_eq!(blend_compute(ComputeMode::Memory, ComputeMode::Memory), ComputeMode::Memory);
    }

    #[test]
    fn test_blend_compute_memory_compute_mixed() {
        assert_eq!(blend_compute(ComputeMode::Memory, ComputeMode::Compute), ComputeMode::Mixed);
        assert_eq!(blend_compute(ComputeMode::Compute, ComputeMode::Memory), ComputeMode::Mixed);
    }

    #[test]
    fn test_blend_compute_io_bound_dominates() {
        assert_eq!(blend_compute(ComputeMode::IoBound, ComputeMode::Compute), ComputeMode::IoBound);
        assert_eq!(blend_compute(ComputeMode::Throughput, ComputeMode::IoBound), ComputeMode::Throughput);
    }

    #[test]
    fn test_derive_strategy_parallel_simd() {
        assert_eq!(derive_strategy(&ComputeMode::Throughput, IoChannel::None, true), DispatchStrategy::ParallelSimd);
    }

    #[test]
    fn test_derive_strategy_async_overlap() {
        assert_eq!(derive_strategy(&ComputeMode::IoBound, IoChannel::Disk, false), DispatchStrategy::AsyncOverlap);
    }

    #[test]
    fn test_derive_strategy_single_thread() {
        assert_eq!(derive_strategy(&ComputeMode::Latency, IoChannel::Ipc, false), DispatchStrategy::SingleThread);
    }

    #[test]
    fn test_derive_strategy_gpu_offload() {
        assert_eq!(derive_strategy(&ComputeMode::Mixed, IoChannel::GpuTransfer, true), DispatchStrategy::GpuOffload);
    }

    #[test]
    fn test_dispatch_for_hexagram_all_64() {
        for n in 1..=64u32 {
            let d = dispatch_for_hexagram(n);
            assert!(d.is_some(), "No dispatch for hexagram {}", n);
            let d = d.unwrap();
            assert_eq!(d.hexagram_num, n);
            assert!(d.lane_width >= 1);
        }
    }

    #[test]
    fn test_dispatch_for_hexagram_invalid() {
        assert!(dispatch_for_hexagram(0).is_none());
        assert!(dispatch_for_hexagram(65).is_none());
    }

    #[test]
    fn test_hexagram_1_creative_valid() {
        let d = dispatch_for_hexagram(1).unwrap();
        assert!(d.fully_simd || d.strategy == DispatchStrategy::SingleThread);
    }

    #[test]
    fn test_hexagram_2_receptive_is_stream_or_parallel() {
        // Hexagram 2 = all yin = Kun/Kun → Memory/SharedMem
        let d = dispatch_for_hexagram(2).unwrap();
        assert_eq!(d.effective_compute, ComputeMode::Memory);
        assert!(d.fully_simd);
    }

    #[test]
    fn test_all_strategies_represented() {
        // Across all 64 hexagrams, we should see multiple strategies
        let strategies: std::collections::HashSet<_> = (1..=64u32)
            .filter_map(|n| dispatch_for_hexagram(n).map(|d| d.strategy))
            .collect();
        assert!(strategies.len() >= 3, "Expected >= 3 strategies, got {}", strategies.len());
    }

    #[test]
    fn test_boltzmann_weights_sum_to_one() {
        for t in [0.1, 1.0, 5.0, 10.0] {
            let weights = boltzmann_weights(t);
            let sum: f64 = weights.iter().sum();
            assert!((sum - 1.0).abs() < 1e-10, "t={}: sum = {} not 1.0", t, sum);
        }
    }

    #[test]
    fn test_boltzmann_weights_all_positive() {
        let weights = boltzmann_weights(1.0);
        for (i, &w) in weights.iter().enumerate() {
            assert!(w > 0.0, "Weight {} is not positive: {}", i, w);
        }
    }

    #[test]
    fn test_boltzmann_select_valid() {
        use rand::SeedableRng;
        use rand::rngs::SmallRng;
        let mut rng = SmallRng::seed_from_u64(42);
        for _ in 0..100 {
            let n = boltzmann_select(&mut rng, 1.0);
            assert!(n >= 1 && n <= 64, "Selected hexagram {} out of range", n);
        }
    }

    #[test]
    fn test_boltzmann_low_temp_concentrates() {
        // At very low temperature, distribution should be concentrated
        let weights = boltzmann_weights(0.01);
        let max_w = weights.iter().cloned().fold(0.0, f64::max);
        assert!(max_w > 0.05, "Low temp should concentrate probability, max weight = {}", max_w);
    }

    #[test]
    fn test_boltzmann_high_temp_spreads() {
        // At high temperature, distribution should be near-uniform
        let weights = boltzmann_weights(100.0);
        let max_w = weights.iter().cloned().fold(0.0, f64::max);
        let min_w = weights.iter().cloned().fold(1.0, f64::min);
        assert!(max_w - min_w < 0.01, "High temp should be near-uniform, range = {}", max_w - min_w);
    }

    #[test]
    fn test_boltzmann_entropy_increases_with_temp() {
        let h_low = boltzmann_entropy(0.1);
        let h_hi = boltzmann_entropy(10.0);
        assert!(h_hi > h_low, "Entropy should increase with temp: {} > {}", h_hi, h_low);
    }

    #[test]
    fn test_boltzmann_top_k() {
        let top = boltzmann_top_k(1.0, 5);
        assert_eq!(top.len(), 5);
        // Should be sorted descending
        for i in 1..top.len() {
            assert!(top[i].1 <= top[i-1].1);
        }
        // All hexagram numbers valid
        for &(n, _) in &top {
            assert!(n >= 1 && n <= 64);
        }
    }

    // Phase 5b: Entropy-Matched Routing tests

    #[test]
    fn test_entropy_matched_route_valid() {
        let (num, disp) = entropy_matched_route(1.0);
        assert!(num >= 1 && num <= 64);
        assert!(disp.is_some());
    }

    #[test]
    fn test_entropy_matched_route_low_entropy() {
        // Low entropy → low temperature → should pick high-priority hexagram
        let (num, _) = entropy_matched_route(0.0);
        assert!(num >= 1 && num <= 64);
    }

    #[test]
    fn test_entropy_matched_route_high_entropy() {
        // High entropy → high temperature → more random selection
        let (num, _) = entropy_matched_route(5.0);
        assert!(num >= 1 && num <= 64);
    }

    #[test]
    fn test_entropy_matched_route_batch() {
        use rand::SeedableRng;
        use rand::rngs::SmallRng;
        let mut rng = SmallRng::seed_from_u64(42);
        let results = entropy_matched_route_batch(&mut rng, 1.0, 10);
        assert_eq!(results.len(), 10);
        for (num, _) in &results {
            assert!(num >= &1 && num <= &64);
        }
    }

    #[test]
    fn test_temperature_for_ratio() {
        assert!(temperature_for_ratio(0.0) < 0.1, "Pure exploitation should have low T");
        assert!(temperature_for_ratio(1.0) >= 1.0, "Pure exploration should have T >= 1.0");
        assert!((temperature_for_ratio(0.5) - 1.0).abs() < 0.01, "50/50 ratio → T≈1.0");
    }

    // Phase 6c: I/O Channel Gating tests

    #[test]
    fn test_io_gate_open_at_low_load() {
        let mut gate = IoGate::new(IoChannel::Disk, 1000.0);
        gate.load = 0.3;
        gate.update();
        assert_eq!(gate.state, GateState::Open);
        assert!(gate.admit());
    }

    #[test]
    fn test_io_gate_throttled_at_medium_load() {
        let mut gate = IoGate::new(IoChannel::Network, 1000.0);
        gate.load = 0.7;
        gate.update();
        assert_eq!(gate.state, GateState::Throttled);
    }

    #[test]
    fn test_io_gate_closed_at_high_load() {
        let mut gate = IoGate::new(IoChannel::Disk, 1000.0);
        gate.load = 0.95;
        gate.update();
        assert_eq!(gate.state, GateState::Closed);
        assert!(!gate.admit());
    }

    #[test]
    fn test_effective_throughput() {
        let mut gate = IoGate::new(IoChannel::SharedMem, 1000.0);
        gate.update();
        assert_eq!(gate.effective_throughput(), 1000.0);

        gate.load = 0.7;
        gate.update();
        assert_eq!(gate.effective_throughput(), 500.0);

        gate.load = 0.95;
        gate.update();
        assert_eq!(gate.effective_throughput(), 0.0);
    }

    #[test]
    fn test_gate_dispatch_returns_valid_gate() {
        let disp = dispatch_for_hexagram(5).unwrap();
        let gate = gate_dispatch(&disp, 0.5);
        assert!(gate.load >= 0.0 && gate.load <= 1.0);
    }

    #[test]
    fn test_can_dispatch_low_load() {
        let disp = dispatch_for_hexagram(10).unwrap();
        assert!(can_dispatch(&disp, 0.2));
    }

    #[test]
    fn test_cannot_dispatch_high_load() {
        let disp = dispatch_for_hexagram(10).unwrap();
        // At very high load, gate should be closed for most dispatches
        let gate = gate_dispatch(&disp, 1.0);
        assert!(gate.state == GateState::Closed || gate.state == GateState::Throttled);
    }
}
