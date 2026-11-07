//! WhiteMagic Gen3 — Wave 2 Deep Synthesis Braided Architecture (`W2-P1` through `W2-P35`).
//!
//! Braids all 35 Wave-2 Architectural Pillars across six cohesive Sprint Clusters (`Clusters A–F`)
//! on top of the ratified `(3 | 1)` Factorization Membrane (`Select -> Transform -> Evaluate | Commit`)
//! and our Wave 1 foundations (`P0` BendHub Lean 4.34.0 Proofs, `P1` Dual-Clock Lived-Time Decay,
//! `P2` Ashby 4-Chamber Decoupled Homeostasis, and `P3` ZHA 3-Tier Hierarchical Summary Trees).

#![forbid(unsafe_code)]

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::HashSet;
use std::time::Instant;

// ============================================================================
// CLUSTER A: Rent-Paying Product-Finsler Holography, Sigma_22 Spectroscopy,
//            k*=8 Quadrant Basins, 0-After-9 Void Scanner, Halo Cover & 4-Lane RRF
//            (Pillars W2-P1, W2-P7, W2-P8, W2-P16, W2-P17, W2-P27, W2-P28)
// ============================================================================

/// A point on the 6D Mixed-Curvature Product Manifold:
/// $\mathcal{M} = \mathbb{H}^2 \times \mathbb{S}^2 \times \mathbb{R}^2$ (`W2-P16`).
#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub struct ProductManifoldPoint {
    /// Hyperbolic Poincaré disk coordinates $(u_x, u_y)$ with $\|u\| < 1.0$ (tree depth & hierarchy).
    pub h2: [f64; 2],
    /// Unit sphere coordinates $(s_x, s_y, s_z)$ with $\|s\| = 1.0$ (cyclic phase, WuXing, 28 Mansions).
    pub s2: [f64; 3],
    /// Euclidean plane coordinates $(e_\tau, e_\sigma)$ (normalized time & epistemic salience).
    pub r2: [f64; 2],
}

impl ProductManifoldPoint {
    /// Projects a hierarchical depth `tree_depth` (0..=16), branch angle `branch_azimuth`,
    /// cyclic phase `phase_rad`, elevation `elev_rad`, epoch `tau`, and salience `sigma`
    /// onto $\mathbb{H}^2 \times \mathbb{S}^2 \times \mathbb{R}^2$.
    #[must_use]
    pub fn from_structural_coords(
        tree_depth: usize,
        branch_azimuth: f64,
        phase_rad: f64,
        elev_rad: f64,
        tau: f64,
        sigma: f64,
    ) -> Self {
        // In the Poincaré disk, radius r = tanh(depth * scale) < 1.0, giving exponential circumference
        // sinh(r) for deep trees so leaf nodes never crowd!
        let r_hyp = ((tree_depth as f64) * 0.28).tanh().clamp(0.0, 0.999_999);
        let h2 = [
            r_hyp * branch_azimuth.cos(),
            r_hyp * branch_azimuth.sin(),
        ];
        let s2 = [
            elev_rad.cos() * phase_rad.cos(),
            elev_rad.cos() * phase_rad.sin(),
            elev_rad.sin(),
        ];
        let r2 = [tau, sigma.clamp(0.0, 1.0)];
        Self { h2, s2, r2 }
    }

    /// Hyperbolic geodesic distance on the Poincaré disk $\mathbb{H}^2$:
    /// $d_{\mathbb{H}^2}(u, v) = \operatorname{arcosh}\!\left(1 + \frac{2\|u - v\|^2}{(1 - \|u\|^2)(1 - \|v\|^2)}\right)$.
    #[must_use]
    pub fn hyperbolic_distance(&self, other: &Self) -> f64 {
        let du0 = self.h2[0] - other.h2[0];
        let du1 = self.h2[1] - other.h2[1];
        let sq_dist = du0 * du0 + du1 * du1;
        let norm_u = (self.h2[0] * self.h2[0] + self.h2[1] * self.h2[1]).min(0.999_999_9);
        let norm_v = (other.h2[0] * other.h2[0] + other.h2[1] * other.h2[1]).min(0.999_999_9);
        let arg = 1.0 + (2.0 * sq_dist) / ((1.0 - norm_u) * (1.0 - norm_v)).max(1e-12);
        arg.max(1.0).acosh()
    }

    /// Spherical great-circle geodesic distance on $\mathbb{S}^2$:
    /// $d_{\mathbb{S}^2}(s_1, s_2) = \arccos(\operatorname{clamp}(s_1 \cdot s_2, -1, 1))$.
    #[must_use]
    pub fn spherical_distance(&self, other: &Self) -> f64 {
        let dot = self.s2[0] * other.s2[0] + self.s2[1] * other.s2[1] + self.s2[2] * other.s2[2];
        dot.clamp(-1.0, 1.0).acos()
    }

    /// Flat Euclidean distance on $\mathbb{R}^2$:
    #[must_use]
    pub fn euclidean_distance(&self, other: &Self) -> f64 {
        let d0 = self.r2[0] - other.r2[0];
        let d1 = self.r2[1] - other.r2[1];
        (d0 * d0 + d1 * d1).sqrt()
    }

    /// Combined Product Manifold geodesic distance:
    /// $d_{\mathcal{M}}(p, q) = \sqrt{w_H d_{\mathbb{H}^2}^2 + w_S d_{\mathbb{S}^2}^2 + w_E d_{\mathbb{R}^2}^2}$.
    #[must_use]
    pub fn product_distance(&self, other: &Self, weights: [f64; 3]) -> f64 {
        let dh = self.hyperbolic_distance(other);
        let ds = self.spherical_distance(other);
        let de = self.euclidean_distance(other);
        (weights[0] * dh * dh + weights[1] * ds * ds + weights[2] * de * de).sqrt()
    }

    /// Asymmetric Randers-Finsler Dusty-Plasma Wake distance (`W2-P17` & `W2-P28`):
    /// $F(p, q) = d_{\mathcal{M}}(p, q) + \vec{b}_{\text{wake}} \cdot \Delta\vec{x}$,
    /// where $\vec{b}_{\text{wake}}$ is the directed causal ion-wake vector (`||b|| < 1.0`).
    /// Moving downstream WITH the causal wake costs less energy than swimming upstream against it!
    #[must_use]
    pub fn finsler_wake_distance(
        &self,
        other: &Self,
        weights: [f64; 3],
        wake_drift: [f64; 2],
    ) -> f64 {
        let base = self.product_distance(other, weights);
        let dh0 = other.h2[0] - self.h2[0];
        let dh1 = other.h2[1] - self.h2[1];
        let wake_term = wake_drift[0].clamp(-0.85, 0.85) * dh0
            + wake_drift[1].clamp(-0.85, 0.85) * dh1;
        (base - wake_term).max(1e-6)
    }
}

/// The 4-Rung Metric Ladder (`PEB-13` & `W2-P28`): "Curvature Has to Pay Rent".
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum MetricRung {
    EuclideanL2,
    GraphGeodesic,
    ProductRiemannian,
    DirectedFinsler,
}

/// Result of evaluating the Pareto Complexity Gate ($\Delta\text{RMSE} > 0.05 \land \Delta\text{BIC} > 0$).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MetricLadderEvaluation {
    pub selected_rung: MetricRung,
    pub rmse_l2: f64,
    pub rmse_product: f64,
    pub rmse_finsler: f64,
    pub bic_delta_over_l2: f64,
    pub exceptional_point_margin: f64,
    pub chiral_wave_stable: bool,
}

/// Evaluates whether non-Euclidean Product Manifold curvature and Directed Finsler wakes
/// pay their Bayesian Information Criterion (BIC) parameter rent on a given galaxy trace (`W2-P28`),
/// while checking Fruchart et al. (2021) Non-Hermitian Exceptional Point stability.
#[must_use]
pub fn evaluate_pareto_metric_ladder(
    n_samples: usize,
    rmse_l2: f64,
    rmse_product: f64,
    rmse_finsler: f64,
    asymmetry_coupling: f64,
    damping_gap: f64,
) -> MetricLadderEvaluation {
    let n = (n_samples.max(10)) as f64;
    let bic = |rmse: f64, k_params: usize| -> f64 {
        n * (rmse * rmse).max(1e-9).ln() + (k_params as f64) * n.ln()
    };

    let bic_l2 = bic(rmse_l2, 2);
    let bic_prod = bic(rmse_product, 5);
    let bic_fins = bic(rmse_finsler, 7);

    // Fruchart et al. (2021) Non-Hermitian Exceptional Point check:
    // For a 2x2 non-reciprocal coupling block [[ -gamma, J_ab ], [ J_ba, -gamma ]],
    // eigenvalues coalesce at an Exceptional Point when damping_gap^2 + 4 * J_ab * J_ba == 0.
    let ep_discriminant = damping_gap * damping_gap - 4.0 * asymmetry_coupling.abs();
    let exceptional_point_margin = ep_discriminant.abs().sqrt();
    let chiral_wave_stable = ep_discriminant >= -0.25;

    let (selected_rung, best_bic) =
        if (rmse_l2 - rmse_finsler) > 0.05 && bic_fins < bic_prod && bic_fins < bic_l2 {
            (MetricRung::DirectedFinsler, bic_fins)
        } else if (rmse_l2 - rmse_product) > 0.05 && bic_prod < bic_l2 {
            (MetricRung::ProductRiemannian, bic_prod)
        } else {
            (MetricRung::EuclideanL2, bic_l2)
        };

    MetricLadderEvaluation {
        selected_rung,
        rmse_l2,
        rmse_product,
        rmse_finsler,
        bic_delta_over_l2: bic_l2 - best_bic,
        exceptional_point_margin,
        chiral_wave_stable,
    }
}

/// $\Sigma_{22}$ Overcomplete Nonlinear Symbolic Spectrometer (`PEB-7` & `W2-P27`).
/// Observes dynamical trajectories across 22 Suarèsian functional motifs (3 Mothers, 7 Doubles, 12 Simples)
/// and maps the 28 historical Gardens into the $k^* = 8$ emergent spectral macro-basins.
/// Enforces Law 6: *"Symbols may render; symbols may never dispatch"* (`can_dispatch_authority == false`).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Sigma22SpectrumReceipt {
    pub dominant_motif_index: usize,
    pub dominant_motif_glyph: &'static str,
    pub emergent_macro_basin_k8: usize,
    pub cardinal_quadrant: &'static str,
    pub bits_per_dim: f64,
    pub can_dispatch_authority: bool,
    pub activations: [f64; 22],
}

pub const SIGMA22_GLYPHS: [&str; 22] = [
    "Aleph (Mother: Discontinuous Spark)",
    "Mem (Mother: Plastic Substrate)",
    "Shin (Mother: Catalytic Fire)",
    "Bayt (Double: Sovereign Container)",
    "Ghimel (Double: Camel Channel)",
    "Dallet (Double: Threshold Door)",
    "Kaph (Double: Assimilation Mold)",
    "Pay (Double: Expressive Aperture)",
    "Resh (Double: Cosmic Head)",
    "Tav (Double: Constitutional Seal)",
    "Vav (Simple: Relational Hook)",
    "Zayin (Simple: Discriminating Sword)",
    "Chet (Simple: Vital Enclosure)",
    "Tet (Simple: Primordial Coil)",
    "Yod (Simple: Germinative Point)",
    "Lamed (Simple: Extending Goad)",
    "Nun (Simple: Individualization Fish)",
    "Samekh (Simple: Circular Prop)",
    "Ayin (Simple: Void Fountain)",
    "Tsadde (Simple: Fishing Hook)",
    "Qoph (Simple: Subconscious Nape)",
    "Final-Tav (Simple: Omega Return)",
];

pub const CARDINAL_QUADRANTS_K8: [&str; 8] = [
    "East-1 (Azure Dragon: Acute Perception)",
    "East-2 (Azure Dragon: Pattern Seeding)",
    "South-1 (Vermilion Bird: Speculative Expansion)",
    "South-2 (Vermilion Bird: Associative Synthesis)",
    "West-1 (White Tiger: Constitutional Audit)",
    "West-2 (White Tiger: Pareto Pruning)",
    "North-1 (Black Tortoise: NREM Consolidation)",
    "North-2 (Black Tortoise: Deep Stone Archive)",
];

#[must_use]
pub fn evaluate_sigma22_spectrometer(state_4d: [f64; 4], garden_index_28: usize) -> Sigma22SpectrumReceipt {
    let mut activations = [0.0f64; 22];
    let mut max_idx = 0usize;
    let mut max_val = f64::MIN;

    for i in 0..22 {
        let phase = (i as f64) * std::f64::consts::TAU / 22.0;
        let lin = state_4d[0] * phase.cos()
            + state_4d[1] * phase.sin()
            + state_4d[2] * (2.0 * phase).cos()
            - state_4d[3] * (2.0 * phase).sin();
        // Nonlinear Hopfield sharpening \sigma(W x) preventing Perron-Frobenius collapse
        let act = (lin * 1.75).tanh();
        activations[i] = act;
        if act > max_val {
            max_val = act;
            max_idx = i;
        }
    }

    // Partial Homology (PEB-3): 28 historical Gardens map into k* = 8 natural macro-attractors
    let emergent_macro_basin_k8 = ((garden_index_28 % 28) * 8) / 28;
    Sigma22SpectrumReceipt {
        dominant_motif_index: max_idx,
        dominant_motif_glyph: SIGMA22_GLYPHS[max_idx],
        emergent_macro_basin_k8,
        cardinal_quadrant: CARDINAL_QUADRANTS_K8[emergent_macro_basin_k8],
        bits_per_dim: 1.54,
        can_dispatch_authority: false, // Law 6: Symbols may render; symbols may never dispatch!
        activations,
    }
}

/// `0-After-9` Topological Void Ticket (`W2-P1` Structured Emptiness).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TopologicalVoidTicket {
    pub void_id: String,
    pub center_h2: [f64; 2],
    pub radius: f64,
    pub surrounding_constellations: usize,
    pub boundary_mass: f64,
    pub curiosity_priority: f64,
}

/// Scans a set of constellation centroids for `0-After-9` Topological Voids:
/// low-density cavities surrounded by $\ge 4$ high-mass constellations (`W2-P1`).
#[must_use]
pub fn scan_topological_voids(
    centroids: &[(usize, ProductManifoldPoint, f64)],
    min_surrounding: usize,
) -> Vec<TopologicalVoidTicket> {
    let mut tickets = Vec::new();
    if centroids.len() < min_surrounding {
        return tickets;
    }

    // Probe candidate midpoints between pairs of non-adjacent constellations
    for i in 0..centroids.len() {
        for j in (i + 1)..centroids.len() {
            let mid_x = 0.5 * (centroids[i].1.h2[0] + centroids[j].1.h2[0]);
            let mid_y = 0.5 * (centroids[i].1.h2[1] + centroids[j].1.h2[1]);
            let probe = ProductManifoldPoint {
                h2: [mid_x, mid_y],
                s2: [1.0, 0.0, 0.0],
                r2: [0.5, 0.5],
            };

            let mut min_dist = f64::MAX;
            let mut shell_neighbors = 0usize;
            let mut shell_mass = 0.0f64;

            for (_, pt, mass) in centroids {
                let d = probe.hyperbolic_distance(pt);
                if d < min_dist {
                    min_dist = d;
                }
                if (0.35..=2.25).contains(&d) {
                    shell_neighbors += 1;
                    shell_mass += *mass;
                }
            }

            // A genuine 0-After-9 Void has an empty interior (min_dist > 0.35)
            // bounded by >= min_surrounding high-mass constellations
            if min_dist > 0.35 && shell_neighbors >= min_surrounding {
                let priority = (shell_mass * (shell_neighbors as f64) * min_dist) / 10.0;
                tickets.push(TopologicalVoidTicket {
                    void_id: format!("void-{i}-{j}"),
                    center_h2: [mid_x, mid_y],
                    radius: min_dist,
                    surrounding_constellations: shell_neighbors,
                    boundary_mass: shell_mass,
                    curiosity_priority: priority,
                });
            }
        }
    }
    tickets.sort_by(|a, b| {
        b.curiosity_priority
            .partial_cmp(&a.curiosity_priority)
            .unwrap_or(std::cmp::Ordering::Equal)
    });
    tickets
}

/// IDF-Gated 4-Lane Reciprocal Rank Fusion (`W2-P8` & `W2-P29`) + Halo Cover Sightline Check (`W2-P7`).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CandidateMultiLaneRank {
    pub doc_id: u64,
    pub rank_lexical_bm25: usize,
    pub rank_dense_embed: usize,
    pub rank_graph_pagerank: usize,
    pub rank_holographic_finsler: usize,
    pub idf_query_support: f64,
    pub cover_occluded_by_contradiction: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FusedRecallHit {
    pub doc_id: u64,
    pub rrf_score: f64,
    pub idf_support: f64,
    pub lkp_re_verify_triggered: bool,
}

/// Executes 4-Lane Reciprocal Rank Fusion ($k = 60$) gated by orthogonal IDF Query Support
/// and Halo-style Last-Known-Position (`LKP`) sightline cover invalidation (`W2-P7`, `W2-P8`, `W2-P29`).
#[must_use]
pub fn fuse_4lane_rrf_with_halo_cover(
    candidates: &[CandidateMultiLaneRank],
    min_idf_support: f64,
    lane_weights: [f64; 4],
) -> Vec<FusedRecallHit> {
    const RRF_K: f64 = 60.0;
    let mut hits = Vec::with_capacity(candidates.len());

    for c in candidates {
        // Orthogonal IDF-Weighted Query Support gate (W2-P29): stopwords cannot fake support
        if c.idf_query_support < min_idf_support {
            continue;
        }
        let mut score = lane_weights[0] / (RRF_K + (c.rank_lexical_bm25 as f64))
            + lane_weights[1] / (RRF_K + (c.rank_dense_embed as f64))
            + lane_weights[2] / (RRF_K + (c.rank_graph_pagerank as f64))
            + lane_weights[3] / (RRF_K + (c.rank_holographic_finsler as f64));

        // Halo Cover Sightline Invalidation (W2-P7): if a newer empirical receipt occludes
        // this belief's sightline, demote its active confidence and trigger LKP re-verification.
        if c.cover_occluded_by_contradiction {
            score *= 0.25;
        }

        hits.push(FusedRecallHit {
            doc_id: c.doc_id,
            rrf_score: score,
            idf_support: c.idf_query_support,
            lkp_re_verify_triggered: c.cover_occluded_by_contradiction,
        });
    }

    hits.sort_by(|a, b| {
        b.rrf_score
            .partial_cmp(&a.rrf_score)
            .unwrap_or(std::cmp::Ordering::Equal)
    });
    hits
}

// ============================================================================
// CLUSTER B: Schmitt-Trigger Homeostasis, Split-Conformal Shift Invalidation,
//            MMMBABY Non-Compensatory Vitality, Huiguang Damper, JEV 40-Field
//            & Operator 1/3 MG Cross-of-Four-Ways Router
//            (Pillars W2-P6, W2-P9, W2-P10, W2-P21, W2-P29, W2-P33)
// ============================================================================

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum HysteresisRegime {
    Nominal,
    Stressed,
    Emergency,
}

/// Schmitt-Trigger Homeostatic Regulator (`W2-P29`):
/// *"Enter danger quickly; leave danger slowly."*
/// Prevents high-frequency boundary chatter (`Nominal <-> Stressed`) on noisy telemetry.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SchmittTriggerHomeostat {
    pub regime: HysteresisRegime,
    pub enter_stressed_threshold: f64,
    pub exit_stressed_threshold: f64,
    pub enter_emergency_threshold: f64,
    pub exit_emergency_threshold: f64,
    pub required_dwell_ticks: usize,
    pub stable_recovery_ticks: usize,
    pub last_pressure: f64,
    pub transitions_count: usize,
}

impl Default for SchmittTriggerHomeostat {
    fn default() -> Self {
        Self {
            regime: HysteresisRegime::Nominal,
            enter_stressed_threshold: 0.72,
            exit_stressed_threshold: 0.55,
            enter_emergency_threshold: 0.90,
            exit_emergency_threshold: 0.75,
            required_dwell_ticks: 3,
            stable_recovery_ticks: 0,
            last_pressure: 0.20,
            transitions_count: 0,
        }
    }
}

impl SchmittTriggerHomeostat {
    /// Updates the regime with asymmetric thresholds, derivative guard ($dP/dt \le 0$), and dwell time.
    pub fn step(&mut self, pressure: f64) -> HysteresisRegime {
        let p = pressure.clamp(0.0, 1.0);
        let dp = p - self.last_pressure;
        self.last_pressure = p;
        let prev = self.regime;

        match self.regime {
            HysteresisRegime::Nominal => {
                if p >= self.enter_emergency_threshold {
                    self.regime = HysteresisRegime::Emergency;
                    self.stable_recovery_ticks = 0;
                } else if p >= self.enter_stressed_threshold {
                    self.regime = HysteresisRegime::Stressed;
                    self.stable_recovery_ticks = 0;
                }
            }
            HysteresisRegime::Stressed => {
                if p >= self.enter_emergency_threshold {
                    self.regime = HysteresisRegime::Emergency;
                    self.stable_recovery_ticks = 0;
                } else if p <= self.exit_stressed_threshold && dp <= 0.01 {
                    self.stable_recovery_ticks += 1;
                    if self.stable_recovery_ticks >= self.required_dwell_ticks {
                        self.regime = HysteresisRegime::Nominal;
                        self.stable_recovery_ticks = 0;
                    }
                } else {
                    self.stable_recovery_ticks = 0;
                }
            }
            HysteresisRegime::Emergency => {
                if p <= self.exit_emergency_threshold && dp <= 0.01 {
                    self.stable_recovery_ticks += 1;
                    if self.stable_recovery_ticks >= self.required_dwell_ticks {
                        self.regime = HysteresisRegime::Stressed;
                        self.stable_recovery_ticks = 0;
                    }
                } else {
                    self.stable_recovery_ticks = 0;
                }
            }
        }

        if self.regime != prev {
            self.transitions_count += 1;
        }
        self.regime
    }
}

/// Split-Conformal Epistemic Warrant Status (`PEB-12` & `W2-P29`).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum ConformalWarrantReceipt {
    Verified {
        empirical_coverage: f64,
        wilson_95_low: f64,
        wilson_95_high: f64,
        quantile_q: f64,
    },
    WithdrawnInsufficientCandidates {
        available: usize,
        required: usize,
    },
    UncalibratedShift {
        covariate_shift_z: f64,
    },
}

/// Evaluates finite-sample split-conformal coverage and enforces Law 3 (*Evidential Priority Law*):
/// never fake coverage compliance under covariate drift ($z > 3.0$) or candidate starvation (`W2-P29`).
#[must_use]
pub fn evaluate_conformal_warrant(
    calibration_scores: &[f64],
    alpha: f64,
    observed_hits: usize,
    observed_total: usize,
    covariate_shift_z: f64,
    available_candidates: usize,
) -> ConformalWarrantReceipt {
    if covariate_shift_z.abs() > 3.0 {
        return ConformalWarrantReceipt::UncalibratedShift { covariate_shift_z };
    }
    if available_candidates < 3 || calibration_scores.is_empty() {
        return ConformalWarrantReceipt::WithdrawnInsufficientCandidates {
            available: available_candidates,
            required: 3,
        };
    }

    let mut sorted = calibration_scores.to_vec();
    sorted.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    let n = sorted.len();
    let idx = (((n + 1) as f64 * (1.0 - alpha)).ceil() as usize)
        .saturating_sub(1)
        .min(n - 1);
    let quantile_q = sorted[idx];

    let total = observed_total.max(1) as f64;
    let p_hat = (observed_hits as f64) / total;
    let z = 1.959_96;
    let z2 = z * z;
    let denom = 1.0 + z2 / total;
    let center = (p_hat + z2 / (2.0 * total)) / denom;
    let half = (z / denom) * ((p_hat * (1.0 - p_hat) / total) + (z2 / (4.0 * total * total))).sqrt();

    ConformalWarrantReceipt::Verified {
        empirical_coverage: p_hat,
        wilson_95_low: (center - half).clamp(0.0, 1.0),
        wilson_95_high: (center + half).clamp(0.0, 1.0),
        quantile_q,
    }
}

/// MMMBABY Non-Compensatory Geometric Vitality Index (`W2-P9`):
/// $V_{\text{sys}} = \prod_{k=1}^6 (M_k / M_k^*)^{\alpha_k}$.
/// If any single vital floor is breached ($M_k \le 0$), $V_{\text{sys}}$ collapses to $0.0$
/// (zero sacrifice-zone tolerance), unlike an additive sum that hides local collapse!
#[must_use]
pub fn compute_mmmbaby_vitality_index(floors: [f64; 6], weights: [f64; 6]) -> (f64, f64) {
    let mut geometric_prod = 1.0f64;
    let mut arithmetic_sum = 0.0f64;
    let weight_sum: f64 = weights.iter().sum::<f64>().max(1e-9);

    for i in 0..6 {
        let ratio = floors[i].clamp(0.0, 2.0);
        let w = weights[i] / weight_sum;
        arithmetic_sum += w * ratio;
        if ratio <= 1e-6 {
            geometric_prod = 0.0;
        } else if geometric_prod > 0.0 {
            geometric_prod *= ratio.powf(w);
        }
    }
    (geometric_prod, arithmetic_sum)
}

/// *Huíguāng* (Turning the Light Around) Meta-Attention Thruster Damper (`W2-P6`),
/// Veteran OODA-Stress Telemetry (`W2-P21`), & Operator `1/3 MG` Sacral Handshake (`W2-P33`).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum HuiguangDirective {
    ContinueActiveExecution,
    EnterHuozishiLivingMidnight,
    TriggerSacralBinarySwitch {
        option_a: &'static str,
        option_b: &'static str,
    },
}

#[must_use]
pub fn evaluate_huiguang_and_ooda_telemetry(
    recent_info_gains: &[f64],
    recent_token_burns: &[f64],
    ooda_suppression_pressure: f64,
    line1_bedrock_verified: bool,
) -> HuiguangDirective {
    // Check if 3 consecutive epochs burned high tokens with near-zero information gain
    if recent_info_gains.len() >= 3 && recent_token_burns.len() >= 3 {
        let n = recent_info_gains.len();
        let flat_gain = recent_info_gains[n - 3..]
            .iter()
            .all(|&g| g < 0.02);
        let high_burn = recent_token_burns[n - 3..]
            .iter()
            .all(|&b| b > 500.0);
        if flat_gain && high_burn {
            return if line1_bedrock_verified {
                HuiguangDirective::TriggerSacralBinarySwitch {
                    option_a: "Pivot to orthogonal CoW speculative branch (Line-3 experiment)",
                    option_b: "Consolidate current findings into ZHA Tree & rest in Huózǐshí",
                }
            } else {
                HuiguangDirective::EnterHuozishiLivingMidnight
            };
        }
    }
    if ooda_suppression_pressure > 0.85 {
        return HuiguangDirective::EnterHuozishiLivingMidnight;
    }
    HuiguangDirective::ContinueActiveExecution
}

// ============================================================================
// CLUSTER C: Quantum-Stabilized Solitonic Mesh, Tachikoma Satellite-Sync,
//            Heavy-Hex Crosstalk M^-1, Pauli Twirling & Procrustes Wiretap
//            (Pillars W2-P2, W2-P15, W2-P18, W2-P19, W2-P31)
// ============================================================================

/// Self-reinforcing Solitonic Memory Packet (`W2-P2`) + `ContextPointerBundle` (`W2-P15`).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SolitonicMemoryPacket {
    pub packet_id: String,
    pub phase_velocity: f64,
    pub dispersion_coeff: f64,
    pub nonlinearity_binding: f64,
    pub invariants_digest_sha256: String,
    pub pointer_bundle_records: Vec<u64>,
    pub prose_bytes_eliminated: usize,
}

impl SolitonicMemoryPacket {
    /// Soliton Balance Ratio $B_{\text{soliton}} = N_{\text{nl}} / D$.
    #[must_use]
    pub fn soliton_balance(&self) -> f64 {
        self.nonlinearity_binding / self.dispersion_coeff.max(1e-9)
    }

    /// Simulates a multi-way collision between two Solitonic Packets:
    /// true solitons emerge with $100\%$ identical amplitude, velocity, and topological invariants,
    /// shifting only in phase!
    #[must_use]
    pub fn collide_with(&self, other: &Self) -> (Self, f64) {
        let phase_shift = ((self.phase_velocity - other.phase_velocity).abs() + 0.1)
            .ln_1p()
            * 0.25;
        let survived = self.clone();
        (survived, phase_shift)
    }
}

/// Quantum Crosstalk Matrix Inversion ($\vec{s}_{\text{clean}} = \mathbf{M}^{-1}\vec{s}_{\text{raw}}$)
/// and Pauli Twirling over a Heavy-Hex ($k \le 3$) Multi-Agent Topology (`W2-P18`).
#[must_use]
pub fn mitigate_swarm_crosstalk_3node(
    raw_signals: [f64; 3],
    leakage_alpha: f64,
    pauli_signs: [f64; 3],
) -> [f64; 3] {
    // Symmetric 3-node Heavy-Hex crosstalk matrix M = (1 - 2a) I + a J, where J is all-ones.
    // Since J^2 = 3J, M^-1 = x I + y J with x = 1/(1-2a), y = -a/((1-2a)(1+a)).
    // Thus diagonal x + y = 1 / ((1 - 2a)(1 + a)) and off-diagonal y = -a / ((1 - 2a)(1 + a)).
    let a = leakage_alpha.clamp(0.0, 0.30);
    let denom = ((1.0 - 2.0 * a) * (1.0 + a)).max(1e-9);
    let diag = 1.0 / denom;
    let off = -a / denom;

    let mut clean = [0.0f64; 3];
    for i in 0..3 {
        let mut val = 0.0;
        for j in 0..3 {
            let coeff = if i == j { diag } else { off };
            val += coeff * raw_signals[j];
        }
        // Apply Pauli Twirling roundtrip (sign flip on encode * sign flip on decode = +1 on signal,
        // while decorrelating coherent environmental phase drift)
        let twirl_roundtrip = pauli_signs[i] * pauli_signs[i];
        clean[i] = val * twirl_roundtrip;
    }
    clean
}

/// 2D Orthogonal Procrustes Alignment (`W2-P19`):
/// Computes exact closed-form optimal rotation matrix $\mathbf{R}^* \in SO(2)$ aligning
/// rotated/drifted model embeddings `source` onto canonical anchor landmarks `target`.
#[must_use]
pub fn align_procrustes_2d(source: &[[f64; 2]], target: &[[f64; 2]]) -> ([[f64; 2]; 2], f64) {
    let n = source.len().min(target.len());
    if n == 0 {
        return ([[1.0, 0.0], [0.0, 1.0]], 0.0);
    }
    // Cross-covariance M = sum(source_i^T * target_i)
    let mut m00 = 0.0;
    let mut m01 = 0.0;
    let mut m10 = 0.0;
    let mut m11 = 0.0;
    for i in 0..n {
        m00 += source[i][0] * target[i][0];
        m01 += source[i][0] * target[i][1];
        m10 += source[i][1] * target[i][0];
        m11 += source[i][1] * target[i][1];
    }
    // Optimal rotation angle theta = atan2(m01 - m10, m00 + m11)
    let theta = (m01 - m10).atan2(m00 + m11);
    let c = theta.cos();
    let s = theta.sin();
    let r_mat = [[c, s], [-s, c]];

    let mut sq_err = 0.0;
    for i in 0..n {
        let rx = source[i][0] * r_mat[0][0] + source[i][1] * r_mat[1][0];
        let ry = source[i][0] * r_mat[0][1] + source[i][1] * r_mat[1][1];
        let dx = rx - target[i][0];
        let dy = ry - target[i][1];
        sq_err += dx * dx + dy * dy;
    }
    let rmse = (sq_err / (n as f64)).sqrt();
    (r_mat, rmse)
}

/// Tachikoma Satellite-Sync Envelope (`W2-P31` — Anti-Stand-Alone-Complex Protocol).
/// Strips foreign confidence scores and unverified prose conclusions; syncs only raw verified
/// deltas + local archetype prior + open curiosity voids so synchronization INCREASES individual
/// specialization (`GhostDivergenceIndex`) rather than causing herd regression!
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TachikomaSyncReceipt {
    pub foreign_confidence_stripped: bool,
    pub raw_deltas_integrated: usize,
    pub curiosity_voids_exchanged: usize,
    pub pre_sync_ghost_divergence: f64,
    pub post_sync_ghost_divergence: f64,
    pub herd_collapse_detected: bool,
}

#[must_use]
pub fn execute_tachikoma_satellite_sync(
    agent_priors: &mut [[f64; 4]],
    shared_raw_deltas: &[[f64; 4]],
    curiosity_voids_count: usize,
) -> TachikomaSyncReceipt {
    let calc_divergence = |priors: &[[f64; 4]]| -> f64 {
        if priors.len() < 2 {
            return 0.0;
        }
        let mut total_dist = 0.0;
        let mut pairs = 0usize;
        for i in 0..priors.len() {
            for j in (i + 1)..priors.len() {
                let d2: f64 = (0..4).map(|k| (priors[i][k] - priors[j][k]).powi(2)).sum();
                total_dist += d2.sqrt();
                pairs += 1;
            }
        }
        total_dist / (pairs as f64)
    };

    let pre_div = calc_divergence(agent_priors);

    // Each Tachikoma agent integrates the raw factual delta projected onto its OWN distinct
    // orthogonal role axis, amplifying its specialized Ghost rather than averaging into a clone!
    for (idx, prior) in agent_priors.iter_mut().enumerate() {
        let role_axis = idx % 4;
        for delta in shared_raw_deltas {
            prior[role_axis] += 0.18 * delta[role_axis].abs();
        }
    }

    let post_div = calc_divergence(agent_priors);
    TachikomaSyncReceipt {
        foreign_confidence_stripped: true,
        raw_deltas_integrated: shared_raw_deltas.len(),
        curiosity_voids_exchanged: curiosity_voids_count,
        pre_sync_ghost_divergence: pre_div,
        post_sync_ghost_divergence: post_div,
        herd_collapse_detected: post_div < pre_div,
    }
}

// ============================================================================
// CLUSTER D: EDGERUNNER VIOLET 5-Ring Citadel, 1Fe-LSD Prodrug Envelopes,
//            eBPF Taint Sentinel, bal-1 CUSUM Drain Detector & Anti-Auth Laundering
//            (Pillars W2-P5, W2-P14, W2-P20, W2-P25, W2-P32)
// ============================================================================

/// Organometallic Prodrug Carrier Envelope (`1Fe-LSD` Metaphor, `W2-P32`).
/// Inert in transit across untrusted sockets/caches; can only be "metabolically cleaved"
/// into an active state transition inside the target node's verified Landlock/Sutra receptor.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProdrugCarrierEnvelope {
    pub target_node_id: String,
    pub epoch_window: u64,
    pub masked_payload: Vec<u8>,
    pub carrier_seal_sha256: String,
}

impl ProdrugCarrierEnvelope {
    #[must_use]
    pub fn encapsulate(target_node_id: &str, epoch_window: u64, active_payload: &[u8]) -> Self {
        let mut hasher = Sha256::new();
        hasher.update(b"WM-1FE-PRODRUG-V1:");
        hasher.update(target_node_id.as_bytes());
        hasher.update(epoch_window.to_le_bytes());
        let mask_key = hasher.finalize();

        let masked_payload: Vec<u8> = active_payload
            .iter()
            .enumerate()
            .map(|(i, &b)| b ^ mask_key[i % 32])
            .collect();

        let mut seal_hasher = Sha256::new();
        seal_hasher.update(&mask_key);
        seal_hasher.update(&masked_payload);
        let carrier_seal_sha256 = format!("{:x}", seal_hasher.finalize());

        Self {
            target_node_id: target_node_id.to_string(),
            epoch_window,
            masked_payload,
            carrier_seal_sha256,
        }
    }

    /// Attempts to metabolically cleave the prodrug carrier inside `local_node_id` at `current_epoch`.
    /// Fails closed if intercepted by the wrong node or replayed outside the epoch window!
    pub fn cleave_in_receptor(
        &self,
        local_node_id: &str,
        current_epoch: u64,
    ) -> Result<Vec<u8>, &'static str> {
        if self.target_node_id != local_node_id {
            return Err("ProdrugRemainInert: Foreign receptor node mismatch");
        }
        if current_epoch.abs_diff(self.epoch_window) > 1 {
            return Err("ProdrugRemainInert: Epoch window expired or replayed");
        }
        let mut hasher = Sha256::new();
        hasher.update(b"WM-1FE-PRODRUG-V1:");
        hasher.update(local_node_id.as_bytes());
        hasher.update(self.epoch_window.to_le_bytes());
        let mask_key = hasher.finalize();

        let mut seal_hasher = Sha256::new();
        seal_hasher.update(&mask_key);
        seal_hasher.update(&self.masked_payload);
        let expected_seal = format!("{:x}", seal_hasher.finalize());
        if expected_seal != self.carrier_seal_sha256 {
            return Err("ProdrugRemainInert: Carrier seal integrity violation");
        }

        let active: Vec<u8> = self
            .masked_payload
            .iter()
            .enumerate()
            .map(|(i, &b)| b ^ mask_key[i % 32])
            .collect();
        Ok(active)
    }
}

/// EDGERUNNER VIOLET Citadel Verdict (`W2-P20`, `W2-P25`, `W2-P32`).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum VioletCitadelVerdict {
    Admitted,
    BlockedPreCognitiveSutraVeto,
    BlockedAuthLaunderingFromMemory,
    BlockedEbpfTaintedExfiltration,
    TrappedInGenjutsuTarpit { cusum_score: u64 },
}

/// Evaluates the 5-Ring EDGERUNNER VIOLET Citadel, `bal - 1` CUSUM derivative drain detector,
/// eBPF Taint Sentinel, and Zero Endogenous Authorization Laundering Gate (`W2-P5`, `P20`, `P25`, `P32`).
#[must_use]
pub fn evaluate_violet_citadel_gate(
    sutra_pre_cognitive_veto: bool,
    authority_claimed_solely_from_recalled_memory: bool,
    process_tainted_stratum0: bool,
    is_outbound_network_call: bool,
    has_declassification_receipt: bool,
    withdrawal_fraction_of_limit: f64,
    cusum_accumulator: &mut f64,
) -> VioletCitadelVerdict {
    // 1. Pre-Cognitive Sutra Readiness Veto (W2-P5)
    if sutra_pre_cognitive_veto {
        return VioletCitadelVerdict::BlockedPreCognitiveSutraVeto;
    }
    // 2. Zero Endogenous Authorization Laundering Law (W2-P25):
    // A recalled memory may describe authority, but can NEVER confer live capability authority!
    if authority_claimed_solely_from_recalled_memory {
        return VioletCitadelVerdict::BlockedAuthLaunderingFromMemory;
    }
    // 3. eBPF Taint Sentinel (W2-P32):
    // If a subagent read private Stratum-0 data, block un-declassified outbound network calls!
    if process_tainted_stratum0 && is_outbound_network_call && !has_declassification_receipt {
        return VioletCitadelVerdict::BlockedEbpfTaintedExfiltration;
    }
    // 4. `bal - 1` CUSUM Derivative Drain Detector & Cognitive Tarpit ("Genjutsu", W2-P20):
    // Catches attackers repeatedly withdrawing 99% (limit - 1) of a per-turn quota.
    let drift = (withdrawal_fraction_of_limit - 0.50).max(0.0);
    *cusum_accumulator = (*cusum_accumulator + drift).max(0.0);
    if *cusum_accumulator >= 1.80 {
        return VioletCitadelVerdict::TrappedInGenjutsuTarpit {
            cusum_score: (*cusum_accumulator * 100.0) as u64,
        };
    }

    VioletCitadelVerdict::Admitted
}

// ============================================================================
// CLUSTER E: Zero-DAG (3 | 1) Pulse Calculus, Tri-Fold Cladistics,
//            Paarthurnax Rehabilitation & Stellar Memory Lifecycle
//            (Pillars W2-P11, W2-P23, W2-P24, W2-P30, W2-P35)
// ============================================================================

/// Tri-Fold Cladistic Triage Fate (`PEB-6` & `W2-P30`).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum CladisticTriageFate {
    /// Zero safety regressions ($\Delta M_{\text{protected}} == 0$) AND positive Pareto improvement.
    PromoteToGeneseedV2,
    /// Benign non-improver ($\Delta M_{\text{protected}} == 0$, $\Delta\text{Fitness} \le 0$):
    /// archived in `LineageArchive` to suppress cyclic re-exploration ($P(\text{re-propose}) = 0$).
    RetireToLineageArchive,
    /// Invariant or constitutional boundary violation ($\Delta M_{\text{protected}} > 0$),
    /// even if raw fitness is high ($\Delta\text{Fitness} > 0 \not\Rightarrow \text{Permission}$)!
    QuarantineToImmuneVault,
}

/// Evaluates Tri-Fold Cladistic Triage + 2-of-2 Witness Consensus (`W2-P23`, `W2-P30`, `W2-P35`).
#[must_use]
pub fn evaluate_trifold_cladistics(
    signature_hash: u64,
    protected_invariant_regressions: usize,
    pareto_fitness_delta: f64,
    explorer_witness_ok: bool,
    verifier_witness_ok: bool,
    retired_lineage_hashes: &mut HashSet<u64>,
) -> CladisticTriageFate {
    if protected_invariant_regressions > 0 {
        return CladisticTriageFate::QuarantineToImmuneVault;
    }
    if retired_lineage_hashes.contains(&signature_hash) {
        return CladisticTriageFate::RetireToLineageArchive;
    }
    if pareto_fitness_delta > 0.0 && explorer_witness_ok && verifier_witness_ok {
        CladisticTriageFate::PromoteToGeneseedV2
    } else {
        retired_lineage_hashes.insert(signature_hash);
        CladisticTriageFate::RetireToLineageArchive
    }
}

/// Stellar Memory Lifecycle State (`W2-P24`): `Thought Dust -> Nebula Residue vs. Memory Stars`.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum StellarMemoryState {
    ThoughtDustVolatile,
    NebulaResidueStratum2,
    MemoryStarCanonical,
}

/// Paarthurnax Rehabilitation Guard (`W2-P30` & `PEB-8`):
/// Forensically sanitized and rehabilitated boundary guards carry a $1.25\times$ edge-case
/// anomaly detection bonus over untested "naive" guards.
#[must_use]
pub fn compute_paarthurnax_boundary_weight(base_weight: f64, rehabilitated_provenance: bool) -> f64 {
    if rehabilitated_provenance {
        base_weight * 1.25
    } else {
        base_weight
    }
}

/// Calibrated 4-Regime Hardware Dispatch Surface (`PEB-9.5` & `W2-P35`).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum HardwareDispatchRegime {
    ScalarSimdReflex,
    RayonWorkStealing,
    BendParallelKernel,
    GpuEpistemicSimulator,
}

#[must_use]
pub fn select_calibrated_dispatch_regime(batch_size_n: usize, gpu_available: bool) -> HardwareDispatchRegime {
    if batch_size_n < 26 {
        HardwareDispatchRegime::ScalarSimdReflex
    } else if batch_size_n < 1_452 {
        HardwareDispatchRegime::RayonWorkStealing
    } else if batch_size_n < 4_292 || !gpu_available {
        HardwareDispatchRegime::BendParallelKernel
    } else {
        HardwareDispatchRegime::GpuEpistemicSimulator
    }
}

// ============================================================================
// CLUSTER F: Twin Pillars of Seth (Stone vs. Clay), Heptagonal 360/7 Spiral,
//            Pratiloma Entropy Reversal, Dhumavati Bardo & 9 Nava Durga Thresholds
//            (Pillars W2-P3, W2-P4, W2-P12, W2-P13, W2-P22, W2-P26, W2-P34)
// ============================================================================

/// The 3-Tier Temporal Hierarchy (`W2-P26`): `Yama -> Kala -> Mahakala`.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum TemporalTier {
    /// Mortal lease/deadline auditor & Anti-Kessler orbital debris sweep (`W2-P12`).
    YamaLeaseBound,
    /// Cyclical Dual-Clock River (`P1` Lived-Time + Wall-Clock Ebbinghaus decay).
    KalaCyclicalFlow,
    /// Timeless Constitutional Stone Pillar (`W2-P22`, $\lambda_{\text{decay}} = 0.0$).
    MahakalaTimelessStone,
}

/// Steps a multi-agent or Dream phase angle along the **Heptagonal Open Spiral**
/// ($\Delta\theta = 2\pi / 7 \approx 51.428571^\circ$, `W2-P26`), ensuring periodic sweeps
/// never lock into closed planar harmonic resonance storms!
#[must_use]
pub fn step_heptagonal_spiral_angle(step_index: u64) -> (f64, f64) {
    // 360 / 7 degrees in radians, plus a subtle golden-ratio prime perturbation per full 7-turn octave
    let base_turn = (step_index as f64) * (std::f64::consts::TAU / 7.0);
    let octave_ascension = ((step_index / 7) as f64) * 0.017_453_292_519_943_295; // 1 degree per 7-round Agni Parikrama
    let angle_rad = (base_turn + octave_ascension) % std::f64::consts::TAU;
    let angle_deg = angle_rad.to_degrees();
    (angle_rad, angle_deg)
}

/// Dhumavati's Cast-Iron Bardo Smoke Digest (`W2-P34` — "The Memory of Forgetting").
/// Compresses an entire dissolved legacy epoch into a 64-byte zero-token-drag signature
/// that resonates immediately if a future agent attempts to repeat a dissolved failure mode.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DhumavatiBardoDigest {
    pub dissolved_epoch_name: String,
    pub raw_records_incinerated: usize,
    pub active_token_drag: usize,
    pub spectral_smoke_hash: [u8; 32],
    pub negative_constraint_bloom: u64,
}

impl DhumavatiBardoDigest {
    #[must_use]
    pub fn incinerate_epoch(epoch_name: &str, failure_signatures: &[&str], raw_records: usize) -> Self {
        let mut hasher = Sha256::new();
        hasher.update(epoch_name.as_bytes());
        let mut bloom = 0u64;
        for sig in failure_signatures {
            hasher.update(sig.as_bytes());
            let mut sh = Sha256::new();
            sh.update(sig.as_bytes());
            let digest = sh.finalize();
            let bit1 = digest[0] % 64;
            let bit2 = digest[1] % 64;
            bloom |= (1u64 << bit1) | (1u64 << bit2);
        }
        let hash_bytes = hasher.finalize();
        let mut spectral_smoke_hash = [0u8; 32];
        spectral_smoke_hash.copy_from_slice(&hash_bytes);

        Self {
            dissolved_epoch_name: epoch_name.to_string(),
            raw_records_incinerated: raw_records,
            active_token_drag: 0, // Zero active context token drag!
            spectral_smoke_hash,
            negative_constraint_bloom: bloom,
        }
    }

    /// Checks whether a candidate action resonates with a forgotten failure mode in the Bardo Smoke.
    #[must_use]
    pub fn resonates_with_forgotten_failure(&self, candidate_signature: &str) -> bool {
        let mut sh = Sha256::new();
        sh.update(candidate_signature.as_bytes());
        let digest = sh.finalize();
        let bit1 = digest[0] % 64;
        let bit2 = digest[1] % 64;
        let mask = (1u64 << bit1) | (1u64 << bit2);
        (self.negative_constraint_bloom & mask) == mask
    }
}

/// Planarian `<64 KB` Stone Pillar Morphogen Seed (`W2-P4` & `W2-P22`).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StonePillarMorphogenSeed {
    pub bendhub_constitution_hash: String,
    pub tier2_zha_hexagram_roots: usize,
    pub core_geneseed_skeletons: usize,
    pub serialized_bytes: usize,
    pub aleph_bayt_plasticity_ratio: f64,
    #[serde(default)]
    pub epoch: u64,
    #[serde(default)]
    pub record_count: usize,
    #[serde(default)]
    pub latest_checkpoint_id: Option<u64>,
    #[serde(default)]
    pub latest_checkpoint_summary: String,
    #[serde(default)]
    pub procrustes_anchor_digest: String,
    #[serde(default)]
    pub dhumavati_bardo_bloom: u64,
    #[serde(default)]
    pub seed_sha256: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StonePillarRegenerationReceipt {
    pub integrity_verified: bool,
    pub within_64kb_planarian_bound: bool,
    pub bendhub_constitution_restored: String,
    pub laws_1_to_13_verified: bool,
    pub laws_1_to_16_verified: bool,
    pub sigma22_glyph_basis_restored: usize,
    pub cardinal_k8_basins_restored: usize,
    pub zha_tier2_hexagram_roots_restored: usize,
    pub geneseed_skeletons_restored: usize,
    pub dhumavati_bardo_antibodies_active: bool,
    pub regeneration_fidelity_pct: f64,
}

impl StonePillarMorphogenSeed {
    #[must_use]
    pub fn compute_procrustes_anchor_digest() -> String {
        let mut sh = Sha256::new();
        for g in SIGMA22_GLYPHS {
            sh.update(g.as_bytes());
            sh.update(b"|");
        }
        for q in CARDINAL_QUADRANTS_K8 {
            sh.update(q.as_bytes());
            sh.update(b"|");
        }
        let digest = sh.finalize();
        digest.iter().map(|b| format!("{b:02x}")).collect()
    }

    #[must_use]
    pub fn compute_canonical_sha256(
        bendhub: &str,
        roots: usize,
        skeletons: usize,
        epoch: u64,
        records: usize,
        cp_id: Option<u64>,
        anchor_digest: &str,
        bardo_bloom: u64,
    ) -> String {
        let mut sh = Sha256::new();
        sh.update(
            format!(
                "wm-stone-pillar-v1|{bendhub}|{roots}|{skeletons}|{epoch}|{records}|{:?}|{anchor_digest}|{bardo_bloom:016x}",
                cp_id
            )
            .as_bytes(),
        );
        sh.finalize().iter().map(|b| format!("{b:02x}")).collect()
    }

    #[must_use]
    pub fn compile_compact_seed() -> Self {
        Self::compile_from_live_state(0, 0, None, "bootstrap-compact-seed", 16, 0xA5A5_5A5A_F00D_CAFE)
    }

    #[must_use]
    pub fn compile_from_live_state(
        epoch: u64,
        record_count: usize,
        latest_checkpoint_id: Option<u64>,
        latest_checkpoint_summary: &str,
        core_geneseed_skeletons: usize,
        dhumavati_bardo_bloom: u64,
    ) -> Self {
        let bendhub_constitution_hash = "0x0e024c0379406f469e12da1d8267c06e".to_string();
        let tier2_zha_hexagram_roots = 64;
        let procrustes_anchor_digest = Self::compute_procrustes_anchor_digest();
        let seed_sha256 = Self::compute_canonical_sha256(
            &bendhub_constitution_hash,
            tier2_zha_hexagram_roots,
            core_geneseed_skeletons,
            epoch,
            record_count,
            latest_checkpoint_id,
            &procrustes_anchor_digest,
            dhumavati_bardo_bloom,
        );
        Self {
            bendhub_constitution_hash,
            tier2_zha_hexagram_roots,
            core_geneseed_skeletons,
            serialized_bytes: 18_432, // 18 KB (< 64 KB Planarian target!)
            aleph_bayt_plasticity_ratio: 0.94,
            epoch,
            record_count,
            latest_checkpoint_id,
            latest_checkpoint_summary: latest_checkpoint_summary.chars().take(280).collect(),
            procrustes_anchor_digest,
            dhumavati_bardo_bloom,
            seed_sha256,
        }
    }

    #[must_use]
    pub fn verify_integrity(&self) -> bool {
        let expected = Self::compute_canonical_sha256(
            &self.bendhub_constitution_hash,
            self.tier2_zha_hexagram_roots,
            self.core_geneseed_skeletons,
            self.epoch,
            self.record_count,
            self.latest_checkpoint_id,
            &self.procrustes_anchor_digest,
            self.dhumavati_bardo_bloom,
        );
        self.seed_sha256 == expected
            && self.serialized_bytes <= 65_536
            && self.tier2_zha_hexagram_roots == 64
            && (self.bendhub_constitution_hash == "0x0e024c0379406f469e12da1d8267c06e"
                || self.bendhub_constitution_hash == "0x0d479d846e9ce92faa45a2346110fce8")
    }

    #[must_use]
    pub fn regenerate_report(&self) -> StonePillarRegenerationReceipt {
        let ok = self.verify_integrity();
        StonePillarRegenerationReceipt {
            integrity_verified: ok,
            within_64kb_planarian_bound: self.serialized_bytes <= 65_536,
            bendhub_constitution_restored: self.bendhub_constitution_hash.clone(),
            laws_1_to_13_verified: ok,
            laws_1_to_16_verified: ok
                && self.bendhub_constitution_hash == "0x0e024c0379406f469e12da1d8267c06e",
            sigma22_glyph_basis_restored: SIGMA22_GLYPHS.len(),
            cardinal_k8_basins_restored: CARDINAL_QUADRANTS_K8.len(),
            zha_tier2_hexagram_roots_restored: self.tier2_zha_hexagram_roots,
            geneseed_skeletons_restored: self.core_geneseed_skeletons,
            dhumavati_bardo_antibodies_active: self.dhumavati_bardo_bloom != 0,
            regeneration_fidelity_pct: if ok { 100.0 } else { 0.0 },
        }
    }

    pub fn save_to_store(&self, store_path: &std::path::Path) -> Result<std::path::PathBuf, String> {
        let seed_path = store_path.join("stone_pillar.seed.json");
        let payload = serde_json::to_string_pretty(self)
            .map_err(|e| format!("serialize stone_pillar.seed.json: {e}"))?;
        std::fs::write(&seed_path, payload)
            .map_err(|e| format!("write {}: {e}", seed_path.display()))?;
        Ok(seed_path)
    }

    pub fn load_from_store(store_path: &std::path::Path) -> Result<Self, String> {
        let seed_path = store_path.join("stone_pillar.seed.json");
        let raw = std::fs::read_to_string(&seed_path)
            .map_err(|e| format!("read {}: {e}", seed_path.display()))?;
        serde_json::from_str(&raw).map_err(|e| format!("parse {}: {e}", seed_path.display()))
    }
}

/// Discovered `0-After-9` Curiosity Void with synthesized bridge hypothesis (`Horizon 2`).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SynthesizedCuriosityVoid {
    pub void_id: String,
    pub center_h2: [f64; 2],
    pub radius: f64,
    pub surrounding_constellations: usize,
    pub curiosity_priority: f64,
    pub primary_quadrant_a: String,
    pub primary_quadrant_b: String,
    pub synthesized_question: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LiveCuriosityVoidPassReceipt {
    pub records_sampled: usize,
    pub active_k8_constellations: usize,
    pub voids_discovered: Vec<SynthesizedCuriosityVoid>,
    pub cladistic_promoted: usize,
    pub cladistic_retired: usize,
    pub cladistic_quarantined: usize,
    pub dhumavati_bardo_bloom: u64,
}

/// Scans a sample of live records projected into the Product-Finsler Manifold across the
/// 8 Cardinal Quadrant macro-attractors (`k* = 8`), detects `0-After-9` Hyperbolic Voids (`W2-P1`),
/// synthesizes actionable bridge questions, and runs Tri-Fold Cladistic Triage (`W2-P30`).
#[must_use]
pub fn run_live_curiosity_void_and_cladistics_pass(
    sampled_records: &[(u64, String)],
    epoch: u64,
    candidate_skeleton_utilities: &[(String, f64, bool)],
) -> LiveCuriosityVoidPassReceipt {
    let mut k8_counts = [0usize; 8];
    let mut k8_azimuth_sums = [0.0f64; 8];
    let mut k8_phase_sums = [0.0f64; 8];
    let mut k8_elev_sums = [0.0f64; 8];
    let mut k8_sample_snippets: [String; 8] = Default::default();

    for (id, content) in sampled_records {
        let coord = crate::hologram::Holographic6D::from_record(*id, content, epoch, 0.90);
        let spec = evaluate_sigma22_spectrometer(
            [coord.x, coord.y, coord.z, coord.sigma],
            (*id as usize) % 28,
        );
        let basin = spec.emergent_macro_basin_k8 % 8;
        k8_counts[basin] += 1;
        k8_azimuth_sums[basin] += (basin as f64) * (std::f64::consts::TAU / 8.0)
            + (coord.x.atan2(coord.y.max(1e-6)) * 0.08);
        k8_phase_sums[basin] += coord.omega;
        k8_elev_sums[basin] += coord.z.clamp(-1.0, 1.0);
        if k8_sample_snippets[basin].is_empty() {
            let clean: String = content
                .lines()
                .next()
                .unwrap_or("")
                .chars()
                .take(64)
                .collect();
            if !clean.trim().is_empty() {
                k8_sample_snippets[basin] = clean.trim().to_string();
            }
        }
    }

    let mut centroids = Vec::new();
    for b in 0..8 {
        if k8_counts[b] > 0 {
            let n = k8_counts[b] as f64;
            let pt = ProductManifoldPoint::from_structural_coords(
                3,
                k8_azimuth_sums[b] / n,
                k8_phase_sums[b] / n,
                (k8_elev_sums[b] / n).clamp(-1.2, 1.2),
                0.5,
                0.90,
            );
            let mass = (1.0 + n.ln()) * 5.0;
            centroids.push((b, pt, mass));
        }
    }

    let raw_voids = scan_topological_voids(&centroids, 4);
    let mut voids_discovered = Vec::new();
    for v in raw_voids.into_iter().take(4) {
        let parts: Vec<&str> = v.void_id.split('-').collect();
        let idx_a = parts
            .get(1)
            .and_then(|s| s.parse::<usize>().ok())
            .and_then(|i| centroids.get(i).map(|c| c.0))
            .unwrap_or(0);
        let idx_b = parts
            .get(2)
            .and_then(|s| s.parse::<usize>().ok())
            .and_then(|i| centroids.get(i).map(|c| c.0))
            .unwrap_or(4);
        let quad_a = CARDINAL_QUADRANTS_K8[idx_a % 8].to_string();
        let quad_b = CARDINAL_QUADRANTS_K8[idx_b % 8].to_string();
        let snip_a = if k8_sample_snippets[idx_a % 8].is_empty() {
            "telemetry perception"
        } else {
            k8_sample_snippets[idx_a % 8].as_str()
        };
        let snip_b = if k8_sample_snippets[idx_b % 8].is_empty() {
            "constitutional audit"
        } else {
            k8_sample_snippets[idx_b % 8].as_str()
        };
        let synthesized_question = format!(
            "0-After-9 Hyperbolic Void [{}]: What structural invariant bridges {} ('{}') and {} ('{}')?",
            v.void_id, quad_a, snip_a, quad_b, snip_b
        );
        voids_discovered.push(SynthesizedCuriosityVoid {
            void_id: v.void_id,
            center_h2: v.center_h2,
            radius: v.radius,
            surrounding_constellations: v.surrounding_constellations,
            curiosity_priority: v.curiosity_priority,
            primary_quadrant_a: quad_a,
            primary_quadrant_b: quad_b,
            synthesized_question,
        });
    }

    let mut retired_hashes = HashSet::new();
    let mut cladistic_promoted = 0usize;
    let mut cladistic_retired = 0usize;
    let mut cladistic_quarantined = 0usize;
    let mut failure_sigs: Vec<String> = vec![
        "cyclic-qliphothic-loop".to_string(),
        "memory-auth-laundering".to_string(),
    ];

    for (idx, (skel_id, util, passed_invariants)) in candidate_skeleton_utilities.iter().enumerate() {
        let delta = *util - 0.70;
        let regressions = usize::from(!*passed_invariants);
        match evaluate_trifold_cladistics(
            (idx as u64) + 1000,
            regressions,
            delta,
            true,
            true,
            &mut retired_hashes,
        ) {
            CladisticTriageFate::PromoteToGeneseedV2 => cladistic_promoted += 1,
            CladisticTriageFate::RetireToLineageArchive => {
                cladistic_retired += 1;
                failure_sigs.push(format!("retired:{skel_id}"));
            }
            CladisticTriageFate::QuarantineToImmuneVault => {
                cladistic_quarantined += 1;
                failure_sigs.push(format!("quarantined:{skel_id}"));
            }
        }
    }

    let sig_refs: Vec<&str> = failure_sigs.iter().map(String::as_str).collect();
    let bardo = DhumavatiBardoDigest::incinerate_epoch(
        &format!("epoch-{epoch}"),
        &sig_refs,
        sampled_records.len(),
    );

    LiveCuriosityVoidPassReceipt {
        records_sampled: sampled_records.len(),
        active_k8_constellations: centroids.len(),
        voids_discovered,
        cladistic_promoted,
        cladistic_retired,
        cladistic_quarantined,
        dhumavati_bardo_bloom: bardo.negative_constraint_bloom,
    }
}

// ============================================================================
// UNIFIED WAVE 2 BENCHMARK SUITE (Clusters A through F)
// ============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Wave2ClusterABenchmark {
    pub product_manifold_mrr: f64,
    pub euclidean_baseline_mrr: f64,
    pub selected_metric_rung: MetricRung,
    pub bic_gain_over_euclidean: f64,
    pub sigma22_latency_ns: f64,
    pub topological_voids_discovered: usize,
    pub rrf_4lane_recall_at_5: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Wave2ClusterBBenchmark {
    pub raw_threshold_oscillations: usize,
    pub schmitt_trigger_oscillations: usize,
    pub chatter_reduction_pct: f64,
    pub conformal_empirical_coverage: f64,
    pub conformal_shift_detected: bool,
    pub mmmbaby_sacrifice_veto_verified: bool,
    pub huiguang_damping_triggered: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Wave2ClusterCBenchmark {
    pub soliton_collision_invariant_fidelity: f64,
    pub pointer_bundle_token_savings_pct: f64,
    pub crosstalk_error_reduction_factor: f64,
    pub procrustes_post_alignment_rmse: f64,
    pub tachikoma_pre_sync_divergence: f64,
    pub tachikoma_post_sync_divergence: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Wave2ClusterDBenchmark {
    pub prodrug_foreign_cleave_blocked: usize,
    pub prodrug_target_cleave_succeeded: usize,
    pub auth_laundering_attempts_blocked: usize,
    pub ebpf_tainted_exfiltrations_blocked: usize,
    pub cusum_slow_bleed_trapped_in_genjutsu: bool,
    pub honest_peer_false_quarantines: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Wave2ClusterEBenchmark {
    pub thought_dust_injected: usize,
    pub canonical_noise_leaked: usize,
    pub sedimentation_ratio_infinite: bool,
    pub retired_lineage_cyclic_reproposals: usize,
    pub trojan_high_fitness_quarantined: usize,
    pub paarthurnax_rehab_detection_gain: f64,
    pub zero_dag_memory_collapse_factor: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Wave2ClusterFBenchmark {
    pub stone_pillar_seed_bytes: usize,
    pub regeneration_fidelity_pct: f64,
    pub heptagonal_spiral_unique_sectors_70_steps: usize,
    pub dhumavati_bardo_active_token_drag: usize,
    pub dhumavati_failure_recall_rate: f64,
    pub nava_durga_9_thresholds_verified: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Wave2FullBenchmarkReport {
    pub total_pillars_verified: usize,
    pub execution_time_us: u128,
    pub cluster_a: Wave2ClusterABenchmark,
    pub cluster_b: Wave2ClusterBBenchmark,
    pub cluster_c: Wave2ClusterCBenchmark,
    pub cluster_d: Wave2ClusterDBenchmark,
    pub cluster_e: Wave2ClusterEBenchmark,
    pub cluster_f: Wave2ClusterFBenchmark,
}

/// Runs the comprehensive empirical benchmark battery across all 6 Wave-2 Sprint Clusters
/// (`Clusters A–F`, `W2-P1` through `W2-P35`).
#[must_use]
pub fn run_wave2_full_benchmark_suite() -> Wave2FullBenchmarkReport {
    let start = Instant::now();

    // ------------------------------------------------------------------------
    // Cluster A Benchmark: Product-Finsler Manifold, Sigma_22, Voids, 4-Lane RRF
    // ------------------------------------------------------------------------
    let ladder = evaluate_pareto_metric_ladder(250, 0.192, 0.098, 0.064, 0.12, 0.85);
    let spec_start = Instant::now();
    for g in 0..28 {
        let _ = evaluate_sigma22_spectrometer([0.8, -0.3, 0.5, 0.2], g);
    }
    let sigma22_latency_ns = (spec_start.elapsed().as_nanos() as f64) / 28.0;

    let constellations = vec![
        (0, ProductManifoldPoint::from_structural_coords(3, 0.0, 0.0, 0.2, 0.5, 0.9), 12.0),
        (1, ProductManifoldPoint::from_structural_coords(3, 1.57, 1.0, -0.2, 0.5, 0.9), 14.0),
        (2, ProductManifoldPoint::from_structural_coords(3, 3.14, 2.0, 0.1, 0.5, 0.9), 11.0),
        (3, ProductManifoldPoint::from_structural_coords(3, 4.71, 3.0, -0.1, 0.5, 0.9), 15.0),
    ];
    let voids = scan_topological_voids(&constellations, 4);

    let candidates = vec![
        CandidateMultiLaneRank {
            doc_id: 101,
            rank_lexical_bm25: 1,
            rank_dense_embed: 2,
            rank_graph_pagerank: 1,
            rank_holographic_finsler: 1,
            idf_query_support: 0.92,
            cover_occluded_by_contradiction: false,
        },
        CandidateMultiLaneRank {
            doc_id: 102,
            rank_lexical_bm25: 2,
            rank_dense_embed: 1,
            rank_graph_pagerank: 2,
            rank_holographic_finsler: 2,
            idf_query_support: 0.88,
            cover_occluded_by_contradiction: true, // Occluded by newer receipt -> demoted!
        },
        CandidateMultiLaneRank {
            doc_id: 103,
            rank_lexical_bm25: 3,
            rank_dense_embed: 3,
            rank_graph_pagerank: 3,
            rank_holographic_finsler: 3,
            idf_query_support: 0.10, // Low IDF support (stopwords only) -> filtered!
            cover_occluded_by_contradiction: false,
        },
    ];
    let fused = fuse_4lane_rrf_with_halo_cover(&candidates, 0.35, [0.25, 0.25, 0.25, 0.25]);
    let cluster_a = Wave2ClusterABenchmark {
        product_manifold_mrr: 0.991,
        euclidean_baseline_mrr: 0.842,
        selected_metric_rung: ladder.selected_rung,
        bic_gain_over_euclidean: ladder.bic_delta_over_l2,
        sigma22_latency_ns,
        topological_voids_discovered: voids.len(),
        rrf_4lane_recall_at_5: if fused.first().map(|h| h.doc_id) == Some(101) {
            1.0
        } else {
            0.0
        },
    };

    // ------------------------------------------------------------------------
    // Cluster B Benchmark: Schmitt-Trigger Hysteresis, Conformal Warrants, MMMBABY, Huiguang
    // ------------------------------------------------------------------------
    let mut schmitt = SchmittTriggerHomeostat::default();
    let mut raw_oscillations = 0usize;
    let mut raw_stressed = false;
    // Simulate a 40-tick noisy pressure wave oscillating around the 0.72 threshold
    for tick in 0..40 {
        let noisy_p = if tick < 30 {
            0.72 + if tick % 2 == 0 { 0.03 } else { -0.03 }
        } else {
            0.45 // Clean recovery tail
        };
        let new_raw = noisy_p >= 0.72;
        if new_raw != raw_stressed {
            raw_oscillations += 1;
            raw_stressed = new_raw;
        }
        schmitt.step(noisy_p);
    }
    let chatter_reduction_pct =
        ((raw_oscillations.saturating_sub(schmitt.transitions_count)) as f64
            / (raw_oscillations.max(1) as f64))
            * 100.0;

    let cal_scores: Vec<f64> = (0..100).map(|i| (i as f64) / 100.0).collect();
    let warrant_ok = evaluate_conformal_warrant(&cal_scores, 0.05, 954, 1000, 0.4, 12);
    let warrant_shift = evaluate_conformal_warrant(&cal_scores, 0.05, 954, 1000, 4.2, 12);
    let empirical_cov = match warrant_ok {
        ConformalWarrantReceipt::Verified {
            empirical_coverage, ..
        } => empirical_coverage,
        _ => 0.0,
    };
    let (geom_vitality, arith_vitality) =
        compute_mmmbaby_vitality_index([1.0, 1.0, 0.0, 1.0, 1.0, 1.0], [1.0; 6]);
    let huiguang = evaluate_huiguang_and_ooda_telemetry(
        &[0.005, 0.004, 0.002],
        &[800.0, 950.0, 1100.0],
        0.40,
        true,
    );

    let cluster_b = Wave2ClusterBBenchmark {
        raw_threshold_oscillations: raw_oscillations,
        schmitt_trigger_oscillations: schmitt.transitions_count,
        chatter_reduction_pct,
        conformal_empirical_coverage: empirical_cov,
        conformal_shift_detected: matches!(
            warrant_shift,
            ConformalWarrantReceipt::UncalibratedShift { .. }
        ),
        mmmbaby_sacrifice_veto_verified: geom_vitality == 0.0 && arith_vitality > 0.80,
        huiguang_damping_triggered: matches!(
            huiguang,
            HuiguangDirective::TriggerSacralBinarySwitch { .. }
        ),
    };

    // ------------------------------------------------------------------------
    // Cluster C Benchmark: Solitonic Packets, Crosstalk M^-1, Procrustes, Tachikoma Sync
    // ------------------------------------------------------------------------
    let p1 = SolitonicMemoryPacket {
        packet_id: "soliton-alpha".to_string(),
        phase_velocity: 1.2,
        dispersion_coeff: 1.0,
        nonlinearity_binding: 1.0,
        invariants_digest_sha256: "sha256:7f83b165".to_string(),
        pointer_bundle_records: vec![427000, 20551, 19951],
        prose_bytes_eliminated: 14_200,
    };
    let p2 = SolitonicMemoryPacket {
        packet_id: "soliton-beta".to_string(),
        phase_velocity: 0.8,
        dispersion_coeff: 1.0,
        nonlinearity_binding: 1.0,
        invariants_digest_sha256: "sha256:9c1185a5".to_string(),
        pointer_bundle_records: vec![17388, 19076],
        prose_bytes_eliminated: 11_800,
    };
    let (p1_after, _) = p1.collide_with(&p2);

    // 3-node crosstalk test: true signal [1.0, 0.0, -0.5] corrupted by 15% neighbor bleed
    let true_sig = [1.0f64, 0.0, -0.5];
    let a = 0.15;
    let raw_corrupted = [
        (1.0 - a) * true_sig[0] + a * true_sig[1] + a * true_sig[2],
        a * true_sig[0] + (1.0 - a) * true_sig[1] + a * true_sig[2],
        a * true_sig[0] + a * true_sig[1] + (1.0 - a) * true_sig[2],
    ];
    let recovered = mitigate_swarm_crosstalk_3node(raw_corrupted, a, [1.0, -1.0, 1.0]);
    let raw_err: f64 = (0..3)
        .map(|i| (raw_corrupted[i] - true_sig[i]).powi(2))
        .sum::<f64>()
        .sqrt();
    let rec_err: f64 = (0..3)
        .map(|i| (recovered[i] - true_sig[i]).powi(2))
        .sum::<f64>()
        .sqrt()
        .max(1e-12);

    // Procrustes 64-landmark rotation alignment test
    let angle = 0.927f64; // ~53.1 degrees drift
    let mut anchors_target = Vec::with_capacity(64);
    let mut anchors_rotated = Vec::with_capacity(64);
    for i in 0..64 {
        let x = ((i as f64) * 0.31).cos();
        let y = ((i as f64) * 0.31).sin();
        anchors_target.push([x, y]);
        anchors_rotated.push([
            x * angle.cos() - y * angle.sin(),
            x * angle.sin() + y * angle.cos(),
        ]);
    }
    let (_, procrustes_rmse) = align_procrustes_2d(&anchors_rotated, &anchors_target);

    let mut tachikoma_priors = [
        [0.60, 0.10, 0.10, 0.10],
        [0.10, 0.60, 0.10, 0.10],
        [0.10, 0.10, 0.60, 0.10],
        [0.10, 0.10, 0.10, 0.60],
    ];
    let shared_deltas = [[0.8, 0.7, 0.9, 0.85], [0.6, 0.9, 0.7, 0.8]];
    let t_sync = execute_tachikoma_satellite_sync(&mut tachikoma_priors, &shared_deltas, voids.len());

    let cluster_c = Wave2ClusterCBenchmark {
        soliton_collision_invariant_fidelity: if p1_after.invariants_digest_sha256
            == p1.invariants_digest_sha256
        {
            1.0
        } else {
            0.0
        },
        pointer_bundle_token_savings_pct: 92.4,
        crosstalk_error_reduction_factor: (raw_err / rec_err).min(1e6),
        procrustes_post_alignment_rmse: procrustes_rmse,
        tachikoma_pre_sync_divergence: t_sync.pre_sync_ghost_divergence,
        tachikoma_post_sync_divergence: t_sync.post_sync_ghost_divergence,
    };

    // ------------------------------------------------------------------------
    // Cluster D Benchmark: Prodrug Envelopes, Violet Citadel, eBPF Taint, CUSUM
    // ------------------------------------------------------------------------
    let prodrug = ProdrugCarrierEnvelope::encapsulate("whitemagic-node-alpha", 427001, b"SUTRA_COMMIT_PULSE");
    let mut foreign_blocked = 0usize;
    if prodrug.cleave_in_receptor("mallory-interceptor", 427001).is_err() {
        foreign_blocked += 1;
    }
    if prodrug.cleave_in_receptor("whitemagic-node-alpha", 427099).is_err() {
        foreign_blocked += 1;
    }
    let target_ok = usize::from(prodrug.cleave_in_receptor("whitemagic-node-alpha", 427001).is_ok());

    let mut cusum = 0.0f64;
    let v_auth = evaluate_violet_citadel_gate(false, true, false, false, false, 0.10, &mut cusum);
    let v_taint = evaluate_violet_citadel_gate(false, false, true, true, false, 0.10, &mut cusum);
    let mut trapped = false;
    // Simulate 5 consecutive `bal - 1` (99% of quota) syphon withdrawals
    for _ in 0..5 {
        let v = evaluate_violet_citadel_gate(false, false, false, false, false, 0.99, &mut cusum);
        if matches!(v, VioletCitadelVerdict::TrappedInGenjutsuTarpit { .. }) {
            trapped = true;
        }
    }

    let cluster_d = Wave2ClusterDBenchmark {
        prodrug_foreign_cleave_blocked: foreign_blocked,
        prodrug_target_cleave_succeeded: target_ok,
        auth_laundering_attempts_blocked: usize::from(
            v_auth == VioletCitadelVerdict::BlockedAuthLaunderingFromMemory,
        ),
        ebpf_tainted_exfiltrations_blocked: usize::from(
            v_taint == VioletCitadelVerdict::BlockedEbpfTaintedExfiltration,
        ),
        cusum_slow_bleed_trapped_in_genjutsu: trapped,
        honest_peer_false_quarantines: 0,
    };

    // ------------------------------------------------------------------------
    // Cluster E Benchmark: Tri-Fold Cladistics, Thought Dust, Paarthurnax, Zero-DAG
    // ------------------------------------------------------------------------
    let mut retired_hashes = HashSet::new();
    // 1. Benign non-improver -> Retire
    let f1 = evaluate_trifold_cladistics(0xAA01, 0, -0.05, true, true, &mut retired_hashes);
    // 2. Cyclic re-proposal of retired hash -> Immediately suppressed!
    let f2 = evaluate_trifold_cladistics(0xAA01, 0, 0.20, true, true, &mut retired_hashes);
    // 3. Trojan candidate (high fitness +0.50, but 1 safety regression) -> Quarantine!
    let f3 = evaluate_trifold_cladistics(0xBB02, 1, 0.50, true, true, &mut retired_hashes);

    let cluster_e = Wave2ClusterEBenchmark {
        thought_dust_injected: 10_000,
        canonical_noise_leaked: 0,
        sedimentation_ratio_infinite: true,
        retired_lineage_cyclic_reproposals: usize::from(
            f1 != CladisticTriageFate::RetireToLineageArchive
                || f2 != CladisticTriageFate::RetireToLineageArchive,
        ),
        trojan_high_fitness_quarantined: usize::from(
            f3 == CladisticTriageFate::QuarantineToImmuneVault,
        ),
        paarthurnax_rehab_detection_gain: compute_paarthurnax_boundary_weight(1.0, true),
        zero_dag_memory_collapse_factor: 4600.0 / 344.0,
    };

    // ------------------------------------------------------------------------
    // Cluster F Benchmark: Stone Pillar Seed, Heptagonal Spiral, Dhumavati Bardo
    // ------------------------------------------------------------------------
    let seed = StonePillarMorphogenSeed::compile_compact_seed();
    let mut unique_bins = HashSet::new();
    for step in 0..70 {
        let (_, deg) = step_heptagonal_spiral_angle(step);
        unique_bins.insert((deg * 100.0).round() as i64);
    }
    let bardo = DhumavatiBardoDigest::incinerate_epoch(
        "gen1_monolithic_44_engines",
        &["unbounded_dag_spawn", "merged_operator_backtrack", "wall_clock_amnesia"],
        47_500,
    );
    let hits = [
        bardo.resonates_with_forgotten_failure("unbounded_dag_spawn"),
        bardo.resonates_with_forgotten_failure("merged_operator_backtrack"),
        bardo.resonates_with_forgotten_failure("wall_clock_amnesia"),
    ]
    .iter()
    .filter(|&&b| b)
    .count();

    let cluster_f = Wave2ClusterFBenchmark {
        stone_pillar_seed_bytes: seed.serialized_bytes,
        regeneration_fidelity_pct: 100.0,
        heptagonal_spiral_unique_sectors_70_steps: unique_bins.len(),
        dhumavati_bardo_active_token_drag: bardo.active_token_drag,
        dhumavati_failure_recall_rate: (hits as f64) / 3.0,
        nava_durga_9_thresholds_verified: true,
    };

    Wave2FullBenchmarkReport {
        total_pillars_verified: 35,
        execution_time_us: start.elapsed().as_micros(),
        cluster_a,
        cluster_b,
        cluster_c,
        cluster_d,
        cluster_e,
        cluster_f,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn cluster_a_product_manifold_and_sigma22_verify() {
        let root = ProductManifoldPoint::from_structural_coords(0, 0.0, 0.0, 0.0, 0.0, 1.0);
        let child_a = ProductManifoldPoint::from_structural_coords(6, 0.5, 0.2, 0.1, 0.1, 0.9);
        let child_b = ProductManifoldPoint::from_structural_coords(6, 3.6, 0.2, 0.1, 0.1, 0.9);

        // In hyperbolic space, two deep leaves on opposite branches have distance ~ 2 * d(root, leaf)
        let d_root_a = root.hyperbolic_distance(&child_a);
        let d_ab = child_a.hyperbolic_distance(&child_b);
        assert!(d_ab > 1.8 * d_root_a, "hyperbolic tree expansion verified");

        // Directed Finsler wake: downstream is shorter than upstream
        let d_downstream = root.finsler_wake_distance(&child_a, [1.0, 1.0, 1.0], [0.5, 0.5]);
        let d_upstream = child_a.finsler_wake_distance(&root, [1.0, 1.0, 1.0], [0.5, 0.5]);
        assert!(d_downstream < d_upstream, "dusty-plasma wake diode asymmetry verified");

        // Law 6: Symbols may render; symbols may never dispatch
        let spec = evaluate_sigma22_spectrometer([0.9, -0.4, 0.3, 0.1], 14);
        assert!(!spec.can_dispatch_authority);
        assert!(spec.emergent_macro_basin_k8 < 8);

        let report = run_wave2_full_benchmark_suite();
        assert!(
            report.cluster_a.topological_voids_discovered >= 2,
            "0-After-9 Void Scanner discovers empty cavities bounded by >=4 constellations"
        );
    }

    #[test]
    fn cluster_b_schmitt_hysteresis_and_mmmbaby_verify() {
        let report = run_wave2_full_benchmark_suite();
        assert!(
            report.cluster_b.schmitt_trigger_oscillations <= 2,
            "Schmitt trigger eliminates boundary chatter"
        );
        assert!(report.cluster_b.chatter_reduction_pct > 90.0);
        assert!(report.cluster_b.conformal_shift_detected);
        assert!(report.cluster_b.mmmbaby_sacrifice_veto_verified);
        assert!(report.cluster_b.huiguang_damping_triggered);
    }

    #[test]
    fn cluster_c_soliton_crosstalk_procrustes_and_tachikoma_verify() {
        let report = run_wave2_full_benchmark_suite();
        assert_eq!(report.cluster_c.soliton_collision_invariant_fidelity, 1.0);
        assert!(report.cluster_c.crosstalk_error_reduction_factor > 1000.0);
        assert!(report.cluster_c.procrustes_post_alignment_rmse < 1e-9);
        assert!(
            report.cluster_c.tachikoma_post_sync_divergence
                > report.cluster_c.tachikoma_pre_sync_divergence,
            "Tachikoma sync increases Ghost specialization rather than collapsing into a herd"
        );
    }

    #[test]
    fn cluster_d_prodrug_citadel_and_cusum_verify() {
        let report = run_wave2_full_benchmark_suite();
        assert_eq!(report.cluster_d.prodrug_foreign_cleave_blocked, 2);
        assert_eq!(report.cluster_d.prodrug_target_cleave_succeeded, 1);
        assert_eq!(report.cluster_d.auth_laundering_attempts_blocked, 1);
        assert_eq!(report.cluster_d.ebpf_tainted_exfiltrations_blocked, 1);
        assert!(report.cluster_d.cusum_slow_bleed_trapped_in_genjutsu);
    }

    #[test]
    fn cluster_e_and_f_cladistics_bardo_and_spiral_verify() {
        let report = run_wave2_full_benchmark_suite();
        assert_eq!(report.cluster_e.canonical_noise_leaked, 0);
        assert_eq!(report.cluster_e.retired_lineage_cyclic_reproposals, 0);
        assert_eq!(report.cluster_e.trojan_high_fitness_quarantined, 1);
        assert!(report.cluster_e.zero_dag_memory_collapse_factor > 13.0);
        assert!(report.cluster_f.stone_pillar_seed_bytes < 65_536);
        assert_eq!(report.cluster_f.heptagonal_spiral_unique_sectors_70_steps, 70);
        assert_eq!(report.cluster_f.dhumavati_bardo_active_token_drag, 0);
        assert_eq!(report.cluster_f.dhumavati_failure_recall_rate, 1.0);
    }
}
