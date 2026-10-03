//! wm-gen3-core — Symbolic Spectroscopy & the 22 Dynamical Motifs (Milestone 4A, PEB-7).
//!
//! # The Non-Dispatching Law (Charter §3.10)
//! > *"Symbols may render; symbols may never dispatch."*
//!
//! No symbolic system (Sefer Yetzirah, Suarèsian letter-numbers, Tarot trumps,
//! Tree of Life paths, Ganas, Gardens) may branch execution, mutate state, or
//! dispatch operations. The [`Spectrometer`] trait is strictly an observational
//! lens possessing **zero capability tokens**.
//!
//! # Epistemic Line of Demarcation
//! - **Above the line (Historical / Symbolic Inspiration):**
//!   Hebrew alphabet (22 characters in Sefer Yetzirah) -> Carlo Suarès dynamical
//!   reinterpretation (*The Cipher of Genesis*) -> 19th-century Hermetic Tarot/Tree
//!   correspondences. These represent distinct historical attempts to construct a
//!   finite symbolic vocabulary of transformation. None of this counts as evidence.
//! - **Below the line (Preregistered Empirical Transfer Functions):**
//!   22 pure mathematical transfer functions $\phi_1 \dots \phi_{22}: \mathbb{R}^M \to [0, 1]$
//!   defined strictly on runtime engine telemetry prior to PEB-7 benchmarking.

#![forbid(unsafe_code)]

use serde::{Deserialize, Serialize};

/// The 22 preregistered dynamical motifs of symbolic spectroscopy.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[repr(u8)]
pub enum DynamicalMotif {
    /// 1. Aleph (א): Fluctuation / Superposition (Select beat)
    Aleph1 = 1,
    /// 2. Bayt (ב): Containment / Bounding (Select beat)
    Bayt2 = 2,
    /// 3. Ghimel (ג): Directed Canalization (Transform beat)
    Ghimel3 = 3,
    /// 4. Dallet (ד): Resistance / Gating Barrier (Evaluate beat)
    Dallet4 = 4,
    /// 5. He (ה): Respiration / Aperture (Select beat)
    He5 = 5,
    /// 6. Waw (ו): Relational Binding (Transform beat)
    Waw6 = 6,
    /// 7. Zayn (ז): Query Bifurcation (Select/Transform beat)
    Zayn7 = 7,
    /// 8. Het (ח): Intermediate Reservoir (Commit beat)
    Het8 = 8,
    /// 9. Tayt (ט): Structuration / Clustering (Transform beat)
    Tayt9 = 9,
    /// 10. Yod (י): Discrete Actuation Spark (Transform beat)
    Yod10 = 10,
    /// 20. Kaph (כ): Storage Assimilation (Commit beat)
    Kaph20 = 11,
    /// 30. Lamed (ל): Causal Trajectory Extrapolation (Transform beat)
    Lamed30 = 12,
    /// 40. Mem (מ): Continuous Fluid Diffusion (Transform beat)
    Mem40 = 13,
    /// 50. Nun (נ): Stochastic Novelty Mutation (Transform beat)
    Nun50 = 14,
    /// 60. Samekh (ס): Constitutional Scaffolding (Evaluate beat)
    Samekh60 = 15,
    /// 70. Ayin (ע): Evidential Apperception (Select beat)
    Ayin70 = 16,
    /// 80. Pe (פ): Telemetry / Output Emission (Commit beat)
    Pe80 = 17,
    /// 90. Tsade (צ): Objective Convergence (Evaluate beat)
    Tsade90 = 18,
    /// 100. Qof (ק): Global Resonance Cascade (Commit beat)
    Qof100 = 19,
    /// 200. Resh (ר): Autonomous Executive Handoff (Commit->Select beat)
    Resh200 = 20,
    /// 300. Shin (ש): Thermal Annealing / Purge (Transform/Eval beat)
    Shin300 = 21,
    /// 400. Taw (ת): Immutable Journal Seal (Commit beat)
    Taw400 = 22,
}

impl DynamicalMotif {
    /// All 22 motifs in canonical sequence.
    pub const ALL: [Self; 22] = [
        Self::Aleph1,
        Self::Bayt2,
        Self::Ghimel3,
        Self::Dallet4,
        Self::He5,
        Self::Waw6,
        Self::Zayn7,
        Self::Het8,
        Self::Tayt9,
        Self::Yod10,
        Self::Kaph20,
        Self::Lamed30,
        Self::Mem40,
        Self::Nun50,
        Self::Samekh60,
        Self::Ayin70,
        Self::Pe80,
        Self::Tsade90,
        Self::Qof100,
        Self::Resh200,
        Self::Shin300,
        Self::Taw400,
    ];

    /// Index in canonical 22D array [0..21].
    pub fn index(self) -> usize {
        (self as usize) - 1
    }

    /// Descriptive name of the motif.
    pub fn name(self) -> &'static str {
        match self {
            Self::Aleph1 => "Aleph_Fluctuation",
            Self::Bayt2 => "Bayt_Containment",
            Self::Ghimel3 => "Ghimel_Canalization",
            Self::Dallet4 => "Dallet_Resistance",
            Self::He5 => "He_Respiration",
            Self::Waw6 => "Waw_Binding",
            Self::Zayn7 => "Zayn_Bifurcation",
            Self::Het8 => "Het_Reservoir",
            Self::Tayt9 => "Tayt_Structuration",
            Self::Yod10 => "Yod_Actuation",
            Self::Kaph20 => "Kaph_Assimilation",
            Self::Lamed30 => "Lamed_Extrapolation",
            Self::Mem40 => "Mem_Diffusion",
            Self::Nun50 => "Nun_Mutation",
            Self::Samekh60 => "Samekh_Scaffolding",
            Self::Ayin70 => "Ayin_Apperception",
            Self::Pe80 => "Pe_Emission",
            Self::Tsade90 => "Tsade_Convergence",
            Self::Qof100 => "Qof_Cascade",
            Self::Resh200 => "Resh_ExecutiveHandoff",
            Self::Shin300 => "Shin_Annealing",
            Self::Taw400 => "Taw_Seal",
        }
    }
}

/// Comprehensive engine telemetry sampled during the [Select -> Transform -> Evaluate -> Commit] cycle.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct RuntimeTelemetry {
    // --- Select Phase Telemetry ---
    /// Candidate selection variance $\sigma^2_a \ge 0$.
    pub candidate_variance: f32,
    /// Normalized candidate entropy $H / H_{\max} \in [0.0, 1.0]$.
    pub candidate_entropy_ratio: f32,
    /// Active commit flag $I_{\text{commit}} \in \{0.0, 1.0\}$.
    pub commit_active: bool,
    /// Working set boundary leakage / pass fraction $\rho_{\text{pass}} \in [0.0, 1.0]$.
    pub boundary_leakage_rate: f32,
    /// Whether the active working set was strictly bounded.
    pub working_set_bounded: bool,
    /// Elapsed time in current respiratory cycle $\Delta t$ in ms.
    pub elapsed_cycle_ms: f32,
    /// Respiratory epoch duration $\tau_{\text{breath}}$ in ms.
    pub breath_epoch_ms: f32,
    /// Provenance chain density across selected inputs $\in [0.0, 1.0]$.
    pub provenance_chain_density: f32,

    // --- Transform Phase Telemetry ---
    /// Hop distance traversed $\|\vec{v}_{\text{hop}}\|$.
    pub hop_distance: f32,
    /// Maximum reachable hop distance $\|\vec{v}\|_{\max}$.
    pub max_hop_distance: f32,
    /// Homeostatic friction / resistance $\in [0.0, 1.0]$.
    pub homeostatic_friction: f32,
    /// Edge mutation delta $\Delta |E_{\text{hyper}}| + \Delta |E_{\text{assoc}}|$.
    pub edge_mutation_delta: f32,
    /// Branching fan-out factor $b_{\text{fan-out}} \ge 0$.
    pub fan_out_factor: f32,
    /// Graph community modularity $Q_{\text{communities}} \in [0.0, 1.0]$.
    pub community_modularity: f32,
    /// Whether an explicit discrete hypothesis was emitted.
    pub hypothesis_emitted: bool,
    /// Causal chain depth ratio $\text{depth} / \text{depth}_{\max} \in [0.0, 1.0]$.
    pub causal_chain_depth_ratio: f32,
    /// Embedding activation density $(1.0 - \text{sparsity}) \in [0.0, 1.0]$.
    pub activation_density: f32,
    /// Stochastic novelty exploration rate $\in [0.0, 1.0]$.
    pub random_walk_rate: f32,

    // --- Evaluate Phase Telemetry ---
    /// Gating refusal coefficient $\kappa_{\text{refusal}} \in [0.0, 1.0]$.
    pub refusal_factor: f32,
    /// Constitutional / homeostatic tension $\Phi \ge 0$.
    pub potential_tension: f32,
    /// Whether all formal constitutional closures verified.
    pub closures_verified: bool,
    /// Magnitude of closure violations $\Phi_{\text{violation}} \in [0.0, 1.0]$.
    pub closure_violation_mag: f32,
    /// Predictive Brier score loss $\in [0.0, 1.0]$.
    pub brier_score: f32,

    // --- Commit Phase Telemetry ---
    /// Staging buffer item count $|\mathcal{S}_{\text{staging}}|$.
    pub staging_buffer_count: usize,
    /// Pages allocated in persistent storage.
    pub pages_allocated: f32,
    /// Telemetry bytes streamed.
    pub bytes_streamed: f32,
    /// Global effective resonance delta $\Delta \|\vec{R}_{\text{effective}}\|$.
    pub resonance_delta: f32,
    /// Whether an autonomous executive phase switch occurred.
    pub phase_switch: bool,
    /// Executive coherence score $\in [0.0, 1.0]$.
    pub executive_coherence: f32,
    /// Current cognitive temperature $T \ge 0$.
    pub temperature: f32,
    /// Ratio of superseded/pruned edges to total edges $\in [0.0, 1.0]$.
    pub pruned_edge_ratio: f32,
    /// Uncommitted pending operations in buffer.
    pub uncommitted_ops: usize,
}

impl Default for RuntimeTelemetry {
    fn default() -> Self {
        Self {
            candidate_variance: 0.15,
            candidate_entropy_ratio: 0.40,
            commit_active: false,
            boundary_leakage_rate: 0.05,
            working_set_bounded: true,
            elapsed_cycle_ms: 12.0,
            breath_epoch_ms: 50.0,
            provenance_chain_density: 0.85,
            hop_distance: 1.5,
            max_hop_distance: 5.0,
            homeostatic_friction: 0.10,
            edge_mutation_delta: 2.0,
            fan_out_factor: 2.5,
            community_modularity: 0.65,
            hypothesis_emitted: true,
            causal_chain_depth_ratio: 0.50,
            activation_density: 0.70,
            random_walk_rate: 0.08,
            refusal_factor: 0.0,
            potential_tension: 0.10,
            closures_verified: true,
            closure_violation_mag: 0.0,
            brier_score: 0.12,
            staging_buffer_count: 5,
            pages_allocated: 4.0,
            bytes_streamed: 256.0,
            resonance_delta: 0.35,
            phase_switch: false,
            executive_coherence: 0.90,
            temperature: 0.35,
            pruned_edge_ratio: 0.05,
            uncommitted_ops: 0,
        }
    }
}

impl RuntimeTelemetry {
    /// Flattens raw telemetry into a continuous 24-dimensional feature vector.
    pub fn to_raw_vector(&self) -> [f32; 24] {
        [
            self.candidate_variance,
            self.candidate_entropy_ratio,
            if self.commit_active { 1.0 } else { 0.0 },
            self.boundary_leakage_rate,
            if self.working_set_bounded { 1.0 } else { 0.0 },
            self.elapsed_cycle_ms / self.breath_epoch_ms.max(1.0),
            self.provenance_chain_density,
            self.hop_distance / self.max_hop_distance.max(0.001),
            self.homeostatic_friction,
            self.edge_mutation_delta,
            self.fan_out_factor,
            self.community_modularity,
            if self.hypothesis_emitted { 1.0 } else { 0.0 },
            self.causal_chain_depth_ratio,
            self.activation_density,
            self.random_walk_rate,
            self.refusal_factor,
            self.potential_tension,
            if self.closures_verified { 1.0 } else { 0.0 },
            self.closure_violation_mag,
            self.brier_score,
            self.staging_buffer_count as f32,
            self.pages_allocated,
            self.temperature,
        ]
    }
}

/// 22-dimensional spectral signature emitted by the spectrometer.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SpectralSignature {
    /// Continuous activation intensities $\phi_k \in [0.0, 1.0]$ for each of the 22 motifs.
    pub activations: [f32; 22],
}

impl SpectralSignature {
    /// Retrieve activation intensity for a given motif.
    pub fn get(&self, motif: DynamicalMotif) -> f32 {
        self.activations[motif.index()]
    }

    /// Total spectral energy $\sum_k \phi_k^2$.
    pub fn energy(&self) -> f32 {
        self.activations.iter().map(|&x| x * x).sum()
    }

    /// Normalized spectral entropy across motifs.
    pub fn entropy(&self) -> f32 {
        let sum: f32 = self.activations.iter().sum();
        if sum <= 1e-7 {
            return 0.0;
        }
        let mut ent = 0.0f32;
        for &val in &self.activations {
            let p = val / sum;
            if p > 1e-7 {
                ent -= p * p.ln();
            }
        }
        ent / (22.0f32.ln())
    }

    /// Identifies the dominant motif with maximal activation.
    pub fn dominant_motif(&self) -> DynamicalMotif {
        let mut best_idx = 0;
        let mut best_val = -1.0f32;
        for (i, &val) in self.activations.iter().enumerate() {
            if val > best_val {
                best_val = val;
                best_idx = i;
            }
        }
        DynamicalMotif::ALL[best_idx]
    }

    /// Returns the raw 22D slice.
    pub fn as_slice(&self) -> &[f32; 22] {
        &self.activations
    }
}

/// Pure observational spectrometer contract.
///
/// **The Non-Dispatching Law (Charter §3.10):**
/// *"Symbols may render; symbols may never dispatch."*
///
/// Implementations of this trait must hold ZERO capability tokens, execute no
/// mutations, and branch no control paths.
pub trait Spectrometer: Send + Sync {
    /// Observe engine telemetry and compute the 22-dimensional spectral signature.
    fn observe(&self, telemetry: &RuntimeTelemetry) -> SpectralSignature;
}

/// Canonical implementation of the 22 preregistered transfer functions $\phi_1 \dots \phi_{400}$.
#[derive(Debug, Clone, Default)]
pub struct CanonicalSpectrometer;

impl CanonicalSpectrometer {
    pub fn new() -> Self {
        Self
    }

    #[inline]
    fn sigmoid(x: f32) -> f32 {
        1.0 / (1.0 + (-x).exp())
    }
}

impl Spectrometer for CanonicalSpectrometer {
    fn observe(&self, t: &RuntimeTelemetry) -> SpectralSignature {
        let mut phi = [0.0f32; 22];

        let commit_flag = if t.commit_active { 1.0 } else { 0.0 };
        let bounded_flag = if t.working_set_bounded { 1.0 } else { 0.0 };
        let hyp_flag = if t.hypothesis_emitted { 1.0 } else { 0.0 };
        let closures_flag = if t.closures_verified { 1.0 } else { 0.0 };
        let switch_flag = if t.phase_switch { 1.0 } else { 0.0 };

        // 1. Aleph (א): Fluctuation / Superposition
        // phi_1 = tanh(sigma^2_a) * (H / H_max) * (1 - I_commit)
        phi[0] = t.candidate_variance.tanh()
            * t.candidate_entropy_ratio.clamp(0.0, 1.0)
            * (1.0 - commit_flag);

        // 2. Bayt (ב): Containment / Bounding
        // phi_2 = (1 - rho_pass) * I(working_set_bounded)
        phi[1] = (1.0 - t.boundary_leakage_rate.clamp(0.0, 1.0)) * bounded_flag;

        // 3. Ghimel (ג): Directed Canalization
        // phi_3 = (||v_hop|| / ||v||_max) * (1 - friction)
        let hop_ratio = (t.hop_distance / t.max_hop_distance.max(0.001)).clamp(0.0, 1.0);
        phi[2] = hop_ratio * (1.0 - t.homeostatic_friction.clamp(0.0, 1.0));

        // 4. Dallet (ד): Resistance / Gating Barrier
        // phi_4 = kappa_refusal * tanh(Phi + 0.5)
        phi[3] =
            t.refusal_factor.clamp(0.0, 1.0) * (t.potential_tension + 0.5).tanh().clamp(0.0, 1.0);

        // 5. He (ה): Respiration / Aperture
        // phi_5 = 0.5 * (1 + sin(2 * pi * Delta t / tau_breath))
        let breath_arg =
            2.0 * std::f32::consts::PI * (t.elapsed_cycle_ms / t.breath_epoch_ms.max(0.001));
        phi[4] = 0.5 * (1.0 + breath_arg.sin()).clamp(0.0, 1.0);

        // 6. Waw (ו): Relational Binding
        // phi_6 = tanh(Delta |E_hyper| + Delta |E_assoc|)
        phi[5] = t.edge_mutation_delta.max(0.0).tanh().clamp(0.0, 1.0);

        // 7. Zayn (ז): Query Bifurcation
        // phi_7 = sigmoid(b_fan-out - 2.0)
        phi[6] = Self::sigmoid(t.fan_out_factor - 2.0).clamp(0.0, 1.0);

        // 8. Het (ח): Intermediate Reservoir
        // phi_8 = |S_staging| / (|S_staging| + 10.0)
        let staging_f = t.staging_buffer_count as f32;
        phi[7] = (staging_f / (staging_f + 10.0)).clamp(0.0, 1.0);

        // 9. Tayt (ט): Structuration / Clustering
        // phi_9 = Modularity(Q_communities)
        phi[8] = t.community_modularity.clamp(0.0, 1.0);

        // 10. Yod (י): Discrete Actuation Spark
        // phi_10 = I(hypothesis_emitted) * (1 - entropy)
        phi[9] = hyp_flag * (1.0 - t.candidate_entropy_ratio.clamp(0.0, 1.0));

        // 20. Kaph (כ): Storage Assimilation
        // phi_20 = tanh(pages_allocated / 10.0)
        phi[10] = (t.pages_allocated.max(0.0) / 10.0).tanh().clamp(0.0, 1.0);

        // 30. Lamed (ל): Causal Trajectory Extrapolation
        // phi_30 = depth(causal_chain) / depth_max
        phi[11] = t.causal_chain_depth_ratio.clamp(0.0, 1.0);

        // 40. Mem (מ): Continuous Fluid Diffusion
        // phi_40 = 1.0 - sparsity(embedding_activation) = activation_density
        phi[12] = t.activation_density.clamp(0.0, 1.0);

        // 50. Nun (נ): Stochastic Novelty Mutation
        // phi_50 = rate(random_walk_hops)
        phi[13] = t.random_walk_rate.clamp(0.0, 1.0);

        // 60. Samekh (ס): Constitutional Scaffolding
        // phi_60 = I(closures_verified) * (1 - Phi_violation)
        phi[14] = closures_flag * (1.0 - t.closure_violation_mag.clamp(0.0, 1.0));

        // 70. Ayin (ע): Evidential Apperception
        // phi_70 = density(provenance_chains)
        phi[15] = t.provenance_chain_density.clamp(0.0, 1.0);

        // 80. Pe (פ): Telemetry / Output Emission
        // phi_80 = tanh(bytes_streamed / 512.0)
        phi[16] = (t.bytes_streamed.max(0.0) / 512.0).tanh().clamp(0.0, 1.0);

        // 90. Tsade (צ): Objective Convergence
        // phi_90 = 1.0 - BrierScore
        phi[17] = (1.0 - t.brier_score.clamp(0.0, 1.0)).clamp(0.0, 1.0);

        // 100. Qof (ק): Global Resonance Cascade
        // phi_100 = tanh(Delta ||R_effective||)
        phi[18] = t.resonance_delta.max(0.0).tanh().clamp(0.0, 1.0);

        // 200. Resh (ר): Autonomous Executive Handoff
        // phi_200 = I(phase_switch) * executive_coherence
        phi[19] = switch_flag * t.executive_coherence.clamp(0.0, 1.0);

        // 300. Shin (ש): Thermal Annealing / Purge
        // phi_300 = tanh(T) * (pruned_ratio)
        phi[20] = t.temperature.max(0.0).tanh() * t.pruned_edge_ratio.clamp(0.0, 1.0);

        // 400. Taw (ת): Immutable Journal Seal
        // phi_400 = I_commit * exp(-uncommitted_ops)
        let uncommitted_penalty = (-(t.uncommitted_ops as f32)).exp();
        phi[21] = commit_flag * uncommitted_penalty;

        // Ensure all values are strictly non-NaN and bounded in [0.0, 1.0]
        for val in phi.iter_mut() {
            if val.is_nan() || val.is_infinite() {
                *val = 0.0;
            } else {
                *val = val.clamp(0.0, 1.0);
            }
        }

        SpectralSignature { activations: phi }
    }
}

/// The 8 distinct physical cognitive regimes evaluated in PEB-7.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum CognitiveRegime {
    /// 1. Low I/O, elevated temperature, fluid diffusion, high annealing.
    QuiescentDream = 0,
    /// 2. Active memory consolidation, community structuration, staging commits.
    DeepConsolidation = 1,
    /// 3. High streaming output, storage assimilation, immutable journal seals.
    HighChurnWaking = 2,
    /// 4. Elevated friction, gating refusal, tension resistance, bounded working set.
    StressedGating = 3,
    /// 5. High selection variance, high entropy, wide query branching, novelty mutation.
    DivergentExploration = 4,
    /// 6. Deep causal chains, discrete hypothesis sparks, low Brier loss, verified closures.
    AnalyticalConvergence = 5,
    /// 7. Closure violation isolated, high provenance scrutiny, gated quarantine.
    ConstitutionalQuarantine = 6,
    /// 8. Global resonance cascade, executive handoff, macro phase transition.
    ResonantPhaseShift = 7,
}

impl CognitiveRegime {
    pub const ALL: [Self; 8] = [
        Self::QuiescentDream,
        Self::DeepConsolidation,
        Self::HighChurnWaking,
        Self::StressedGating,
        Self::DivergentExploration,
        Self::AnalyticalConvergence,
        Self::ConstitutionalQuarantine,
        Self::ResonantPhaseShift,
    ];

    pub fn name(self) -> &'static str {
        match self {
            Self::QuiescentDream => "QuiescentDream",
            Self::DeepConsolidation => "DeepConsolidation",
            Self::HighChurnWaking => "HighChurnWaking",
            Self::StressedGating => "StressedGating",
            Self::DivergentExploration => "DivergentExploration",
            Self::AnalyticalConvergence => "AnalyticalConvergence",
            Self::ConstitutionalQuarantine => "ConstitutionalQuarantine",
            Self::ResonantPhaseShift => "ResonantPhaseShift",
        }
    }
}

/// Lightweight deterministic Xorshift PRNG for reproducible benchmark synthesis.
fn xorshift64(state: &mut u64) -> u64 {
    let mut x = *state;
    x ^= x << 13;
    x ^= x >> 7;
    x ^= x << 17;
    *state = x;
    x
}

fn rand_f32(state: &mut u64) -> f32 {
    (xorshift64(state) as f64 / u64::MAX as f64) as f32
}

fn rand_range(state: &mut u64, min: f32, max: f32) -> f32 {
    min + rand_f32(state) * (max - min)
}

/// Synthesizes a telemetry step pair (m_t, m_{t+1}) characteristic of the target regime.
pub fn synthesize_regime_telemetry(
    regime: CognitiveRegime,
    _step_idx: usize,
    rng: &mut u64,
) -> (RuntimeTelemetry, RuntimeTelemetry) {
    let mut t0 = RuntimeTelemetry::default();
    let mut t1: RuntimeTelemetry;

    match regime {
        CognitiveRegime::QuiescentDream => {
            t0.temperature = rand_range(rng, 0.70, 0.95);
            t0.commit_active = false;
            t0.activation_density = rand_range(rng, 0.80, 0.98);
            t0.pruned_edge_ratio = rand_range(rng, 0.25, 0.50);
            t0.random_walk_rate = rand_range(rng, 0.30, 0.60);
            t0.bytes_streamed = rand_range(rng, 0.0, 20.0);
            t0.pages_allocated = 0.0;
            t0.uncommitted_ops = 0;
            t0.candidate_variance = rand_range(rng, 0.40, 0.70);
            t0.candidate_entropy_ratio = rand_range(rng, 0.60, 0.85);

            t1 = t0.clone();
            t1.temperature = (t0.temperature - rand_range(rng, 0.01, 0.04)).max(0.60);
            t1.pruned_edge_ratio = (t0.pruned_edge_ratio + rand_range(rng, 0.02, 0.08)).min(0.60);
            t1.activation_density = (t0.activation_density + rand_range(rng, 0.01, 0.03)).min(1.0);
        }
        CognitiveRegime::DeepConsolidation => {
            t0.temperature = rand_range(rng, 0.40, 0.60);
            t0.commit_active = true;
            t0.community_modularity = rand_range(rng, 0.75, 0.95);
            t0.staging_buffer_count = (rand_range(rng, 20.0, 45.0)) as usize;
            t0.pages_allocated = rand_range(rng, 6.0, 16.0);
            t0.closures_verified = true;
            t0.closure_violation_mag = 0.0;
            t0.bytes_streamed = rand_range(rng, 30.0, 80.0);
            t0.uncommitted_ops = 0;

            t1 = t0.clone();
            t1.staging_buffer_count = (t0.staging_buffer_count.saturating_sub(10)).max(5);
            t1.pages_allocated = t0.pages_allocated + rand_range(rng, 2.0, 5.0);
            t1.community_modularity =
                (t0.community_modularity + rand_range(rng, 0.01, 0.04)).min(1.0);
        }
        CognitiveRegime::HighChurnWaking => {
            t0.temperature = rand_range(rng, 0.10, 0.25);
            t0.commit_active = true;
            t0.bytes_streamed = rand_range(rng, 1024.0, 4096.0);
            t0.pages_allocated = rand_range(rng, 20.0, 50.0);
            t0.uncommitted_ops = 0;
            t0.fan_out_factor = rand_range(rng, 1.8, 3.2);
            t0.homeostatic_friction = rand_range(rng, 0.05, 0.25);
            t0.activation_density = rand_range(rng, 0.40, 0.65);

            t1 = t0.clone();
            t1.bytes_streamed = t0.bytes_streamed + rand_range(rng, 256.0, 1024.0);
            t1.pages_allocated = t0.pages_allocated + rand_range(rng, 4.0, 12.0);
            t1.homeostatic_friction =
                (t0.homeostatic_friction + rand_range(rng, 0.02, 0.08)).min(0.50);
        }
        CognitiveRegime::StressedGating => {
            t0.temperature = rand_range(rng, 0.20, 0.40);
            t0.homeostatic_friction = rand_range(rng, 0.65, 0.95);
            t0.refusal_factor = rand_range(rng, 0.70, 1.0);
            t0.potential_tension = rand_range(rng, 0.60, 0.98);
            t0.boundary_leakage_rate = rand_range(rng, 0.0, 0.04);
            t0.working_set_bounded = true;
            t0.commit_active = false;
            t0.uncommitted_ops = (rand_range(rng, 3.0, 12.0)) as usize;

            t1 = t0.clone();
            t1.potential_tension = (t0.potential_tension - rand_range(rng, 0.02, 0.06)).max(0.40);
            t1.homeostatic_friction =
                (t0.homeostatic_friction - rand_range(rng, 0.01, 0.05)).max(0.50);
        }
        CognitiveRegime::DivergentExploration => {
            t0.candidate_variance = rand_range(rng, 0.65, 0.98);
            t0.candidate_entropy_ratio = rand_range(rng, 0.75, 1.0);
            t0.fan_out_factor = rand_range(rng, 3.5, 6.5);
            t0.random_walk_rate = rand_range(rng, 0.50, 0.85);
            t0.commit_active = false;
            t0.hypothesis_emitted = rand_f32(rng) > 0.6;
            t0.causal_chain_depth_ratio = rand_range(rng, 0.10, 0.35);

            t1 = t0.clone();
            t1.candidate_entropy_ratio =
                (t0.candidate_entropy_ratio - rand_range(rng, 0.03, 0.08)).max(0.40);
            t1.causal_chain_depth_ratio = t0.causal_chain_depth_ratio + rand_range(rng, 0.05, 0.15);
        }
        CognitiveRegime::AnalyticalConvergence => {
            t0.causal_chain_depth_ratio = rand_range(rng, 0.75, 1.0);
            t0.hypothesis_emitted = true;
            t0.candidate_entropy_ratio = rand_range(rng, 0.05, 0.25);
            t0.brier_score = rand_range(rng, 0.01, 0.08);
            t0.closures_verified = true;
            t0.closure_violation_mag = 0.0;
            t0.provenance_chain_density = rand_range(rng, 0.85, 1.0);
            t0.commit_active = false;

            t1 = t0.clone();
            t1.commit_active = true;
            t1.uncommitted_ops = 0;
            t1.brier_score = (t0.brier_score * 0.9).max(0.005);
        }
        CognitiveRegime::ConstitutionalQuarantine => {
            t0.closures_verified = false;
            t0.closure_violation_mag = rand_range(rng, 0.40, 0.88);
            t0.provenance_chain_density = rand_range(rng, 0.85, 1.0);
            t0.refusal_factor = rand_range(rng, 0.85, 1.0);
            t0.potential_tension = rand_range(rng, 0.70, 0.95);
            t0.commit_active = false;
            t0.boundary_leakage_rate = 0.0;
            t0.working_set_bounded = true;

            t1 = t0.clone();
            t1.closure_violation_mag = 0.0; // isolated to quarantine sink
            t1.potential_tension = (t0.potential_tension - 0.15).max(0.20);
        }
        CognitiveRegime::ResonantPhaseShift => {
            t0.resonance_delta = rand_range(rng, 0.70, 1.0);
            t0.phase_switch = true;
            t0.executive_coherence = rand_range(rng, 0.80, 0.98);
            t0.breath_epoch_ms = 50.0;
            t0.elapsed_cycle_ms = rand_range(rng, 35.0, 48.0);
            t0.commit_active = false;

            t1 = t0.clone();
            t1.phase_switch = false;
            t1.resonance_delta = (t0.resonance_delta - 0.30).max(0.10);
            t1.executive_coherence = rand_range(rng, 0.85, 0.99);
        }
    }

    (t0, t1)
}

/// Performs Jacobi eigenvalue decomposition on a symmetric 24x24 matrix.
pub fn jacobi_eigen_24(cov: &[[f64; 24]; 24], max_iter: usize) -> ([f64; 24], [[f64; 24]; 24]) {
    let mut a = *cov;
    let mut v = [[0.0f64; 24]; 24];
    for i in 0..24 {
        v[i][i] = 1.0;
    }

    for _ in 0..max_iter {
        let mut max_off = 0.0f64;
        let mut p = 0;
        let mut q = 1;
        for i in 0..24 {
            for j in (i + 1)..24 {
                let off = a[i][j].abs();
                if off > max_off {
                    max_off = off;
                    p = i;
                    q = j;
                }
            }
        }
        if max_off < 1e-11 {
            break;
        }

        let app = a[p][p];
        let aqq = a[q][q];
        let apq = a[p][q];
        let theta = 0.5 * (2.0 * apq).atan2(aqq - app);
        let c = theta.cos();
        let s = theta.sin();

        for i in 0..24 {
            if i != p && i != q {
                let aip = a[i][p];
                let aiq = a[i][q];
                a[i][p] = c * aip - s * aiq;
                a[p][i] = a[i][p];
                a[i][q] = s * aip + c * aiq;
                a[q][i] = a[i][q];
            }
            let vip = v[i][p];
            let viq = v[i][q];
            v[i][p] = c * vip - s * viq;
            v[i][q] = s * vip + c * viq;
        }
        a[p][p] = c * c * app - 2.0 * s * c * apq + s * s * aqq;
        a[q][q] = s * s * app + 2.0 * s * c * apq + c * c * aqq;
        a[p][q] = 0.0;
        a[q][p] = 0.0;
    }

    let mut eig_vals = [0.0f64; 24];
    for i in 0..24 {
        eig_vals[i] = a[i][i];
    }

    // Sort descending
    let mut indices: Vec<usize> = (0..24).collect();
    indices.sort_by(|&i, &j| eig_vals[j].partial_cmp(&eig_vals[i]).unwrap());

    let mut sorted_vals = [0.0f64; 24];
    let mut sorted_vecs = [[0.0f64; 24]; 24];
    for (new_idx, &old_idx) in indices.iter().enumerate() {
        sorted_vals[new_idx] = eig_vals[old_idx];
        for row in 0..24 {
            sorted_vecs[row][new_idx] = v[row][old_idx];
        }
    }

    (sorted_vals, sorted_vecs)
}

/// Inverts an N x N matrix using Gauss-Jordan elimination with partial pivoting.
pub fn invert_square_matrix(mat: &[Vec<f64>]) -> Option<Vec<Vec<f64>>> {
    let n = mat.len();
    let mut a: Vec<Vec<f64>> = mat.iter().map(|row| row.clone()).collect();
    let mut inv = vec![vec![0.0f64; n]; n];
    for i in 0..n {
        inv[i][i] = 1.0;
    }

    for col in 0..n {
        let mut max_row = col;
        let mut max_val = a[col][col].abs();
        for row in (col + 1)..n {
            if a[row][col].abs() > max_val {
                max_val = a[row][col].abs();
                max_row = row;
            }
        }
        if max_val < 1e-12 {
            return None;
        }
        a.swap(col, max_row);
        inv.swap(col, max_row);

        let pivot = a[col][col];
        for j in 0..n {
            a[col][j] /= pivot;
            inv[col][j] /= pivot;
        }

        for row in 0..n {
            if row != col {
                let factor = a[row][col];
                for j in 0..n {
                    a[row][j] -= factor * a[col][j];
                    inv[row][j] -= factor * inv[col][j];
                }
            }
        }
    }

    Some(inv)
}

/// Solves linear ridge regression W = (Z^T Z + lambda I)^(-1) Z^T Y.
pub fn solve_ridge_regression(
    z_train: &[Vec<f64>],
    y_train: &[Vec<f64>],
    lambda: f64,
) -> Option<Vec<Vec<f64>>> {
    let n = z_train.len();
    if n == 0 {
        return None;
    }
    let k = z_train[0].len();
    let d = y_train[0].len();

    // Augment with bias: [z, 1.0]
    let p = k + 1;
    let mut z_aug = vec![vec![1.0f64; p]; n];
    for i in 0..n {
        for j in 0..k {
            z_aug[i][j] = z_train[i][j];
        }
    }

    // A = Z^T Z + lambda I
    let mut a = vec![vec![0.0f64; p]; p];
    for i in 0..n {
        for r in 0..p {
            for c in 0..p {
                a[r][c] += z_aug[i][r] * z_aug[i][c];
            }
        }
    }
    for r in 0..p {
        a[r][r] += lambda;
    }

    let a_inv = invert_square_matrix(&a)?;

    // B = Z^T Y
    let mut b = vec![vec![0.0f64; d]; p];
    for i in 0..n {
        for r in 0..p {
            for c in 0..d {
                b[r][c] += z_aug[i][r] * y_train[i][c];
            }
        }
    }

    // W = A^(-1) B
    let mut w = vec![vec![0.0f64; d]; p];
    for r in 0..p {
        for c in 0..d {
            for m in 0..p {
                w[r][c] += a_inv[r][m] * b[m][c];
            }
        }
    }

    Some(w)
}

/// Evaluates linear probe prediction MSE and R^2 on test data.
pub fn evaluate_linear_probe(
    z_test: &[Vec<f64>],
    y_test: &[Vec<f64>],
    weights: &[Vec<f64>],
) -> (f64, f64) {
    let n = z_test.len();
    let k = z_test[0].len();
    let d = y_test[0].len();
    let p = k + 1;

    let mut y_pred = vec![vec![0.0f64; d]; n];
    for i in 0..n {
        for c in 0..d {
            let mut val = weights[p - 1][c]; // bias
            for j in 0..k {
                val += z_test[i][j] * weights[j][c];
            }
            y_pred[i][c] = val;
        }
    }

    let mut total_se = 0.0f64;
    let total_elements = (n * d) as f64;
    for i in 0..n {
        for c in 0..d {
            let diff = y_pred[i][c] - y_test[i][c];
            total_se += diff * diff;
        }
    }
    let mse = total_se / total_elements;

    // Compute variance of y_test
    let mut col_means = vec![0.0f64; d];
    for i in 0..n {
        for c in 0..d {
            col_means[c] += y_test[i][c];
        }
    }
    for c in 0..d {
        col_means[c] /= n as f64;
    }

    let mut total_var = 0.0f64;
    for i in 0..n {
        for c in 0..d {
            let diff = y_test[i][c] - col_means[c];
            total_var += diff * diff;
        }
    }
    let var_y = (total_var / total_elements).max(1e-9);
    let r2 = 1.0 - (mse / var_y);

    (mse, r2)
}

/// Evaluates multiclass regime classification Macro F1 score on test data.
pub fn evaluate_regime_classification_f1(
    z_train: &[Vec<f64>],
    regimes_train: &[usize],
    z_test: &[Vec<f64>],
    regimes_test: &[usize],
) -> f64 {
    let n_train = z_train.len();
    let n_test = z_test.len();
    let num_classes = 8;

    let mut y_one_hot = vec![vec![0.0f64; num_classes]; n_train];
    for i in 0..n_train {
        y_one_hot[i][regimes_train[i]] = 1.0;
    }

    let weights = match solve_ridge_regression(z_train, &y_one_hot, 1.0) {
        Some(w) => w,
        None => return 0.0,
    };

    let k = z_test[0].len();
    let p = k + 1;

    let mut preds = Vec::with_capacity(n_test);
    for i in 0..n_test {
        let mut best_class = 0;
        let mut best_score = -1e9f64;
        for c in 0..num_classes {
            let mut score = weights[p - 1][c];
            for j in 0..k {
                score += z_test[i][j] * weights[j][c];
            }
            if score > best_score {
                best_score = score;
                best_class = c;
            }
        }
        preds.push(best_class);
    }

    // Compute macro F1
    let mut f1_sum = 0.0f64;
    for c in 0..num_classes {
        let mut tp = 0;
        let mut fp = 0;
        let mut fn_count = 0;
        for i in 0..n_test {
            if preds[i] == c && regimes_test[i] == c {
                tp += 1;
            } else if preds[i] == c && regimes_test[i] != c {
                fp += 1;
            } else if preds[i] != c && regimes_test[i] == c {
                fn_count += 1;
            }
        }
        let precision = if tp + fp > 0 {
            tp as f64 / (tp + fp) as f64
        } else {
            0.0
        };
        let recall = if tp + fn_count > 0 {
            tp as f64 / (tp + fn_count) as f64
        } else {
            0.0
        };
        let f1 = if precision + recall > 1e-9 {
            2.0 * precision * recall / (precision + recall)
        } else {
            0.0
        };
        f1_sum += f1;
    }

    f1_sum / (num_classes as f64)
}

/// Computes mean pairwise absolute off-diagonal correlation (lower is more orthogonal).
pub fn compute_pairwise_redundancy(features: &[Vec<f64>]) -> f64 {
    let n = features.len();
    if n < 2 {
        return 0.0;
    }
    let k = features[0].len();
    if k < 2 {
        return 0.0;
    }

    let mut means = vec![0.0f64; k];
    for i in 0..n {
        for j in 0..k {
            means[j] += features[i][j];
        }
    }
    for j in 0..k {
        means[j] /= n as f64;
    }

    let mut stds = vec![0.0f64; k];
    for i in 0..n {
        for j in 0..k {
            let diff = features[i][j] - means[j];
            stds[j] += diff * diff;
        }
    }
    for j in 0..k {
        stds[j] = (stds[j] / (n - 1) as f64).sqrt().max(1e-9);
    }

    let mut total_corr = 0.0f64;
    let mut pairs_count = 0.0f64;
    for i in 0..k {
        for j in (i + 1)..k {
            let mut cov = 0.0f64;
            for row in 0..n {
                cov += (features[row][i] - means[i]) * (features[row][j] - means[j]);
            }
            let r = cov / ((n - 1) as f64 * stds[i] * stds[j]);
            total_corr += r.abs();
            pairs_count += 1.0;
        }
    }

    total_corr / pairs_count
}

/// Benchmark Report emitted by PEB-7 (Spectroscopy Fidelity & Multi-Baseline Representation).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Peb7BenchmarkReport {
    pub seed: u64,
    pub total_steps: usize,
    pub train_steps: usize,
    pub val_steps: usize,
    pub holdout_steps: usize,
    // Predictive Sufficiency
    pub sigma22_holdout_mse: f64,
    pub sigma22_holdout_r2: f64,
    pub raw_holdout_mse: f64,
    pub raw_holdout_r2: f64,
    pub random22_holdout_mse: f64,
    pub random22_holdout_r2: f64,
    pub pca22_holdout_mse: f64,
    pub pca22_holdout_r2: f64,
    // Discriminative Separability
    pub sigma22_regime_f1: f64,
    pub raw_regime_f1: f64,
    pub random22_regime_f1: f64,
    pub pca22_regime_f1: f64,
    // Information Bottleneck & Redundancy
    pub sigma22_redundancy: f64,
    pub pca22_redundancy: f64,
    pub random22_redundancy: f64,
    pub sigma22_bits_efficiency: f64,
    // Execution Latency
    pub mean_spectrometer_ns: f64,
    pub summary: String,
}

/// Executes the PEB-7 Multi-Baseline Spectroscopy Benchmark (N=1000 trajectory steps).
pub fn run_peb7_spectroscopy_fidelity_benchmark(seed: u64) -> Peb7BenchmarkReport {
    let mut rng = seed;
    let spec = CanonicalSpectrometer::new();

    let total_steps = 1000;
    let train_steps = 600;
    let val_steps = 200;
    let holdout_steps = 200;

    let mut raw_inputs: Vec<Vec<f64>> = Vec::with_capacity(total_steps);
    let mut raw_targets: Vec<Vec<f64>> = Vec::with_capacity(total_steps);
    let mut sigma22_features: Vec<Vec<f64>> = Vec::with_capacity(total_steps);
    let mut regimes: Vec<usize> = Vec::with_capacity(total_steps);

    let start_obs = std::time::Instant::now();
    for i in 0..total_steps {
        let reg_idx = i % 8;
        let regime = CognitiveRegime::ALL[reg_idx];
        let (t0, t1) = synthesize_regime_telemetry(regime, i, &mut rng);

        let sig = spec.observe(&t0);
        let raw0 = t0.to_raw_vector().iter().map(|&x| x as f64).collect();
        let raw1 = t1.to_raw_vector().iter().map(|&x| x as f64).collect();
        let s22 = sig.activations.iter().map(|&x| x as f64).collect();

        raw_inputs.push(raw0);
        raw_targets.push(raw1);
        sigma22_features.push(s22);
        regimes.push(reg_idx);
    }
    let obs_duration = start_obs.elapsed();
    let mean_spectrometer_ns = (obs_duration.as_nanos() as f64) / (total_steps as f64);

    // Splits
    let raw_train = &raw_inputs[0..train_steps];
    let raw_holdout = &raw_inputs[(train_steps + val_steps)..total_steps];
    let target_train = &raw_targets[0..train_steps];
    let target_holdout = &raw_targets[(train_steps + val_steps)..total_steps];
    let regimes_train = &regimes[0..train_steps];
    let regimes_holdout = &regimes[(train_steps + val_steps)..total_steps];

    let s22_train = &sigma22_features[0..train_steps];
    let s22_holdout = &sigma22_features[(train_steps + val_steps)..total_steps];

    // Compute PCA_22 on raw_train
    let mut means_24 = [0.0f64; 24];
    for row in raw_train {
        for j in 0..24 {
            means_24[j] += row[j];
        }
    }
    for j in 0..24 {
        means_24[j] /= train_steps as f64;
    }

    let mut cov_24 = [[0.0f64; 24]; 24];
    for row in raw_train {
        for r in 0..24 {
            for c in 0..24 {
                cov_24[r][c] += (row[r] - means_24[r]) * (row[c] - means_24[c]);
            }
        }
    }
    for r in 0..24 {
        for c in 0..24 {
            cov_24[r][c] /= (train_steps - 1) as f64;
        }
    }

    let (_eig_vals, eig_vecs) = jacobi_eigen_24(&cov_24, 100);

    let project_pca22 = |raw_set: &[Vec<f64>]| -> Vec<Vec<f64>> {
        raw_set
            .iter()
            .map(|row| {
                let mut proj = vec![0.0f64; 22];
                for k in 0..22 {
                    for j in 0..24 {
                        proj[k] += (row[j] - means_24[j]) * eig_vecs[j][k];
                    }
                }
                proj
            })
            .collect()
    };

    let pca22_train = project_pca22(raw_train);
    let pca22_holdout = project_pca22(raw_holdout);

    // Generate Random_22 projection matrix
    let mut rand_mat = vec![vec![0.0f64; 24]; 22];
    for r in 0..22 {
        for c in 0..24 {
            rand_mat[r][c] = (rand_f32(&mut rng) * 2.0 - 1.0) as f64;
        }
        // Normalize
        let norm: f64 = rand_mat[r]
            .iter()
            .map(|&x| x * x)
            .sum::<f64>()
            .sqrt()
            .max(1e-9);
        for c in 0..24 {
            rand_mat[r][c] /= norm;
        }
    }

    let project_random22 = |raw_set: &[Vec<f64>]| -> Vec<Vec<f64>> {
        raw_set
            .iter()
            .map(|row| {
                let mut proj = vec![0.0f64; 22];
                for k in 0..22 {
                    for j in 0..24 {
                        proj[k] += row[j] * rand_mat[k][j];
                    }
                }
                proj
            })
            .collect()
    };

    let rand22_train = project_random22(raw_train);
    let rand22_holdout = project_random22(raw_holdout);

    // 1. Predictive Sufficiency (Linear Probes on Holdout)
    let w_s22 = solve_ridge_regression(s22_train, target_train, 1.0).unwrap();
    let (s22_mse, s22_r2) = evaluate_linear_probe(s22_holdout, target_holdout, &w_s22);

    let w_raw = solve_ridge_regression(raw_train, target_train, 1.0).unwrap();
    let (raw_mse, raw_r2) = evaluate_linear_probe(raw_holdout, target_holdout, &w_raw);

    let w_rand22 = solve_ridge_regression(&rand22_train, target_train, 1.0).unwrap();
    let (rand22_mse, rand22_r2) = evaluate_linear_probe(&rand22_holdout, target_holdout, &w_rand22);

    let w_pca22 = solve_ridge_regression(&pca22_train, target_train, 1.0).unwrap();
    let (pca22_mse, pca22_r2) = evaluate_linear_probe(&pca22_holdout, target_holdout, &w_pca22);

    // 2. Discriminative Separability (Regime Classification Macro F1)
    let s22_f1 =
        evaluate_regime_classification_f1(s22_train, regimes_train, s22_holdout, regimes_holdout);
    let raw_f1 =
        evaluate_regime_classification_f1(raw_train, regimes_train, raw_holdout, regimes_holdout);
    let rand22_f1 = evaluate_regime_classification_f1(
        &rand22_train,
        regimes_train,
        &rand22_holdout,
        regimes_holdout,
    );
    let pca22_f1 = evaluate_regime_classification_f1(
        &pca22_train,
        regimes_train,
        &pca22_holdout,
        regimes_holdout,
    );

    // 3. Information Redundancy
    let s22_red = compute_pairwise_redundancy(s22_holdout);
    let pca22_red = compute_pairwise_redundancy(&pca22_holdout);
    let rand22_red = compute_pairwise_redundancy(&rand22_holdout);

    // Bits efficiency: delta log-loss / bits
    let delta_mse = (rand22_mse - s22_mse).max(0.0);
    let bits_efficiency = delta_mse / (22.0 * 0.15);

    let summary = format!(
        "PEB-7 Report => total={}, train={}, holdout={}, sigma22_mse={:.4}, sigma22_r2={:.4}, raw_mse={:.4}, raw_r2={:.4}, pca22_mse={:.4}, pca22_r2={:.4}, random22_mse={:.4}, random22_r2={:.4}, sigma22_f1={:.4}, pca22_f1={:.4}, raw_f1={:.4}, random22_f1={:.4}, sigma22_red={:.4}, pca22_red={:.4}, mean_ns={:.1}",
        total_steps,
        train_steps,
        holdout_steps,
        s22_mse,
        s22_r2,
        raw_mse,
        raw_r2,
        pca22_mse,
        pca22_r2,
        rand22_mse,
        rand22_r2,
        s22_f1,
        pca22_f1,
        raw_f1,
        rand22_f1,
        s22_red,
        pca22_red,
        mean_spectrometer_ns
    );

    Peb7BenchmarkReport {
        seed,
        total_steps,
        train_steps,
        val_steps,
        holdout_steps,
        sigma22_holdout_mse: s22_mse,
        sigma22_holdout_r2: s22_r2,
        raw_holdout_mse: raw_mse,
        raw_holdout_r2: raw_r2,
        random22_holdout_mse: rand22_mse,
        random22_holdout_r2: rand22_r2,
        pca22_holdout_mse: pca22_mse,
        pca22_holdout_r2: pca22_r2,
        sigma22_regime_f1: s22_f1,
        raw_regime_f1: raw_f1,
        random22_regime_f1: rand22_f1,
        pca22_regime_f1: pca22_f1,
        sigma22_redundancy: s22_red,
        pca22_redundancy: pca22_red,
        random22_redundancy: rand22_red,
        sigma22_bits_efficiency: bits_efficiency,
        mean_spectrometer_ns,
        summary,
    }
}

#[cfg(test)]
pub mod tests {
    use super::*;

    #[test]
    fn test_all_motifs_bounded_in_unit_interval() {
        let spec = CanonicalSpectrometer::new();
        let default_telem = RuntimeTelemetry::default();
        let sig = spec.observe(&default_telem);

        for (i, &act) in sig.activations.iter().enumerate() {
            assert!(
                act >= 0.0 && act <= 1.0,
                "Motif {} ({:?}) out of bounds: {}",
                i,
                DynamicalMotif::ALL[i],
                act
            );
        }
    }

    #[test]
    fn test_spectrometer_is_pure_and_deterministic() {
        let spec = CanonicalSpectrometer::new();
        let mut telem = RuntimeTelemetry::default();
        telem.candidate_variance = 0.88;
        telem.bytes_streamed = 1024.0;
        telem.temperature = 1.2;

        let sig1 = spec.observe(&telem);
        let sig2 = spec.observe(&telem);

        assert_eq!(sig1, sig2, "Spectrometer must be 100% deterministic");
    }

    #[test]
    fn test_extreme_and_nan_telemetry_resilience() {
        let spec = CanonicalSpectrometer::new();
        let telem_extreme = RuntimeTelemetry {
            candidate_variance: f32::NAN,
            candidate_entropy_ratio: f32::INFINITY,
            commit_active: true,
            boundary_leakage_rate: -10.0,
            working_set_bounded: false,
            elapsed_cycle_ms: f32::NEG_INFINITY,
            breath_epoch_ms: 0.0,
            provenance_chain_density: 50.0,
            hop_distance: 100.0,
            max_hop_distance: 0.0,
            homeostatic_friction: 2.0,
            edge_mutation_delta: -5.0,
            fan_out_factor: 100.0,
            community_modularity: -1.0,
            hypothesis_emitted: false,
            causal_chain_depth_ratio: 10.0,
            activation_density: -0.5,
            random_walk_rate: 10.0,
            refusal_factor: -2.0,
            potential_tension: 100.0,
            closures_verified: false,
            closure_violation_mag: 10.0,
            brier_score: 5.0,
            staging_buffer_count: 1000,
            pages_allocated: -5.0,
            bytes_streamed: -100.0,
            resonance_delta: -1.0,
            phase_switch: true,
            executive_coherence: 5.0,
            temperature: -1.0,
            pruned_edge_ratio: 2.0,
            uncommitted_ops: 100,
        };

        let sig = spec.observe(&telem_extreme);
        for &act in &sig.activations {
            assert!(!act.is_nan(), "Activation must never be NaN");
            assert!(!act.is_infinite(), "Activation must never be infinite");
            assert!(
                act >= 0.0 && act <= 1.0,
                "Activation must be clamped in [0, 1]"
            );
        }
    }

    #[test]
    fn test_distinct_cognitive_regimes_produce_distinct_spectra() {
        let spec = CanonicalSpectrometer::new();

        // 1. Quiescent Dream: high temperature, zero commit, fluid diffusion
        let dream_telem = RuntimeTelemetry {
            commit_active: false,
            temperature: 0.85,
            activation_density: 0.95, // high Mem diffusion
            pruned_edge_ratio: 0.35,  // high Shin annealing
            random_walk_rate: 0.40,   // Nun mutation
            pages_allocated: 0.0,
            bytes_streamed: 0.0,
            ..Default::default()
        };

        // 2. High Churn Waking: active commit, high I/O, storage assimilation
        let waking_telem = RuntimeTelemetry {
            commit_active: true,
            temperature: 0.15,
            pages_allocated: 25.0,  // high Kaph storage
            bytes_streamed: 2048.0, // high Pe emission
            uncommitted_ops: 0,     // high Taw seal
            ..Default::default()
        };

        let dream_sig = spec.observe(&dream_telem);
        let waking_sig = spec.observe(&waking_telem);

        assert_ne!(dream_sig, waking_sig);
        // In dream, Taw (seal) must be 0 because commit is false
        assert_eq!(dream_sig.get(DynamicalMotif::Taw400), 0.0);
        // In waking, Taw must be > 0.5 because commit is true and uncommitted is 0
        assert!(waking_sig.get(DynamicalMotif::Taw400) > 0.5);
        // In waking, Pe (emission) must be substantially higher
        assert!(waking_sig.get(DynamicalMotif::Pe80) > dream_sig.get(DynamicalMotif::Pe80));
    }

    #[test]
    fn test_peb7_spectroscopy_benchmark_execution() {
        let report = run_peb7_spectroscopy_fidelity_benchmark(42);
        println!("{}", report.summary);

        // Verification of invariant bounds:
        assert_eq!(report.total_steps, 1000);
        assert_eq!(report.holdout_steps, 200);

        // Predictive Sufficiency: Verify that Sigma22 explains significant physical variance
        assert!(
            report.sigma22_holdout_r2 > 0.85,
            "Sigma22 R^2 ({}) must exceed 0.85 on untouched holdout",
            report.sigma22_holdout_r2
        );
        assert!(
            report.pca22_holdout_r2 > 0.90,
            "PCA22 R^2 ({}) must exceed 0.90",
            report.pca22_holdout_r2
        );

        // Discriminative Separability: Sigma22 should achieve decisive regime classification
        assert!(
            report.sigma22_regime_f1 >= 0.95,
            "Sigma22 F1 ({}) must be >= 0.95 across 8 regimes",
            report.sigma22_regime_f1
        );

        // Redundancy: Sigma22 should have bounded pairwise correlation
        assert!(
            report.sigma22_redundancy < 0.60,
            "Sigma22 redundancy ({}) must be bounded (< 0.60)",
            report.sigma22_redundancy
        );

        // Sub-microsecond / low-microsecond observation latency in unoptimized debug build:
        assert!(
            report.mean_spectrometer_ns < 100_000.0,
            "Spectrometer mean latency must be under 100 µs in unoptimized debug build"
        );
    }
}
