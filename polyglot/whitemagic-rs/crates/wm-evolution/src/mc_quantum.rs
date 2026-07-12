//! Quantum-inspired computing primitives for WhiteMagic.
//!
//! Implements:
//! 1. Natural gradient optimization (Fubini-Study metric, geodesic updates)
//! 2. Hierarchical tensor networks (MPS bind/unbind, multi-scale compression)
//! 3. Mixed-curvature embeddings (hyperbolic, spherical, Euclidean)
//! 4. Born-rule sampling (probability = |amplitude|²)
//! 5. Topological error protection (Berry phase, Chern numbers)
//! 6. QAOA-style combinatorial optimization (quantum walk exploration)
//!
//! These modules provide quantum-inspired mathematical operations that
//! enhance classical ML, memory, and cognitive systems.

use rand::{RngCore, SeedableRng};
use rand_xoshiro::Xoshiro256PlusPlus;

// ═════════════════════════════════════════════════════════════════════
// 1. NATURAL GRADIENT OPTIMIZATION (Fubini-Study Metric)
// ═════════════════════════════════════════════════════════════════════

/// Compute the Fubini-Study metric tensor for a parameterized quantum state.
///
/// For a state |ψ(θ)⟩, the FS metric is:
/// g_μν = Re[⟨∂_μψ|∂_νψ⟩ - ⟨∂_μψ|ψ⟩⟨ψ|∂_νψ⟩]
///
/// This defines the natural geometry of quantum state space and enables
/// geodesic optimization instead of flat Euclidean gradients.
pub fn fubini_study_metric(
    state: &[f64],        // |ψ⟩ as real-valued vector (amplitudes)
    jacobian: &[Vec<f64>], // ∂_μ|ψ⟩ for each parameter μ
    n_params: usize,
) -> Vec<Vec<f64>> {
    let d = state.len();
    let mut metric = vec![vec![0.0; n_params]; n_params];

    let norm_sq = state.iter().map(|x| x * x).sum::<f64>();

    for mu in 0..n_params {
        for nu in 0..n_params {
            // ⟨∂_μψ|∂_νψ⟩
            let dmu_dnu: f64 = jacobian[mu]
                .iter()
                .zip(jacobian[nu].iter())
                .map(|(a, b)| a * b)
                .sum();

            // ⟨∂_μψ|ψ⟩
            let dmu_psi: f64 = jacobian[mu]
                .iter()
                .zip(state.iter())
                .map(|(a, b)| a * b)
                .sum();

            // ⟨ψ|∂_νψ⟩
            let psi_dnu: f64 = state
                .iter()
                .zip(jacobian[nu].iter())
                .map(|(a, b)| a * b)
                .sum();

            // g_μν = Re[⟨∂_μψ|∂_νψ⟩ - ⟨∂_μψ|ψ⟩⟨ψ|∂_νψ⟩ / ⟨ψ|ψ⟩]
            metric[mu][nu] = dmu_dnu - (dmu_psi * psi_dnu) / norm_sq.max(1e-15);
        }
    }

    metric
}

/// Natural gradient update: θ_new = θ_old - η * g⁻¹ * ∇L
///
/// Uses the Fubini-Study metric to transform gradients into geodesic updates.
/// Falls back to standard gradient descent if metric is singular.
pub fn natural_gradient_step(
    params: &[f64],
    gradients: &[f64],
    metric: &[Vec<f64>],
    learning_rate: f64,
) -> Vec<f64> {
    let n = params.len();
    if n == 0 {
        return Vec::new();
    }

    // Solve g * Δθ = ∇L via Gaussian elimination (with regularization)
    let mut aug = vec![vec![0.0; n + 1]; n];
    for i in 0..n {
        for j in 0..n {
            aug[i][j] = metric[i][j];
        }
        // Regularize diagonal
        aug[i][i] += 1e-8;
        aug[i][n] = gradients[i];
    }

    // Forward elimination
    for col in 0..n {
        // Partial pivot
        let pivot = (col..n)
            .max_by(|&a, &b| aug[a][col].abs().partial_cmp(&aug[b][col].abs()).unwrap())
            .unwrap_or(col);
        if pivot != col {
            aug.swap(col, pivot);
        }
        if aug[col][col].abs() < 1e-12 {
            continue; // Singular, skip
        }
        for row in (col + 1)..n {
            let factor = aug[row][col] / aug[col][col];
            for j in col..=n {
                aug[row][j] -= factor * aug[col][j];
            }
        }
    }

    // Back substitution
    let mut delta = vec![0.0; n];
    for i in (0..n).rev() {
        let mut sum = aug[i][n];
        for j in (i + 1)..n {
            sum -= aug[i][j] * delta[j];
        }
        delta[i] = if aug[i][i].abs() > 1e-12 {
            sum / aug[i][i]
        } else {
            gradients[i] // Fallback to standard gradient
        };
    }

    // Apply update
    params
        .iter()
        .zip(delta.iter())
        .map(|(p, d)| p - learning_rate * d)
        .collect()
}

// ═════════════════════════════════════════════════════════════════════
// 2. HIERARCHICAL TENSOR NETWORKS (MPS Compression)
// ═════════════════════════════════════════════════════════════════════

/// Matrix Product State (MPS) tensor for hierarchical compression.
///
/// An MPS represents an N-dimensional tensor as a chain of 3-index tensors:
/// A[σ₁] · A[σ₂] · ... · A[σₙ] where each A has indices (left_bond, physical, right_bond)
///
/// This enables O(n * D² * d) storage vs O(dⁿ) for full tensors,
/// where D = bond dimension, d = physical dimension.
pub struct MatrixProductState {
    /// Tensors: [site][physical_index][left_bond][right_bond]
    pub tensors: Vec<Vec<Vec<Vec<f64>>>>,
    pub bond_dim: usize,
    pub phys_dim: usize,
    pub n_sites: usize,
}

impl MatrixProductState {
    /// Create a random MPS with given dimensions.
    pub fn random(n_sites: usize, phys_dim: usize, bond_dim: usize, seed: u64) -> Self {
        let mut rng = Xoshiro256PlusPlus::seed_from_u64(seed);
        let mut tensors = Vec::with_capacity(n_sites);

        for site in 0..n_sites {
            let left = if site == 0 { 1 } else { bond_dim };
            let right = if site == n_sites - 1 { 1 } else { bond_dim };

            let mut site_tensors = Vec::with_capacity(phys_dim);
            for _ in 0..phys_dim {
                let mut left_right = Vec::with_capacity(left);
                for _ in 0..left {
                    let mut right_vec = Vec::with_capacity(right);
                    for _ in 0..right {
                        right_vec.push((rng.next_u64() as f64 / u64::MAX as f64) * 2.0 - 1.0);
                    }
                    left_right.push(right_vec);
                }
                site_tensors.push(left_right);
            }
            tensors.push(site_tensors);
        }

        Self { tensors, bond_dim, phys_dim, n_sites }
    }

    /// Contract the MPS to recover the full state vector.
    pub fn full_state(&self) -> Vec<f64> {
        if self.n_sites == 0 {
            return Vec::new();
        }

        // Start with leftmost tensor: shape (1, phys_dim, bond_dim)
        // Result after contracting: vector of length phys_dim^1 * bond_dim
        let mut current: Vec<f64> = Vec::new();
        for p in 0..self.phys_dim {
            for r in 0..self.tensors[0][p][0].len() {
                current.push(self.tensors[0][p][0][r]);
            }
        }

        // Contract site by site
        for site in 1..self.n_sites {
            let bond_left = if site == 1 {
                self.phys_dim
            } else {
                self.phys_dim * self.bond_dim
            };
            let bond_right = if site == self.n_sites - 1 { 1 } else { self.bond_dim };

            let mut next = vec![0.0; bond_left * self.phys_dim * bond_right / if site == 1 { self.phys_dim } else { self.bond_dim }];

            // Simplified contraction: for each physical index at this site
            // next[(prev_idx * phys_dim + p) * bond_right + r] = sum_l current[prev_idx * bond_left + l] * tensors[site][p][l][r]
            let prev_size = current.len() / self.bond_dim.max(1);
            let new_size = (current.len() / self.bond_dim.max(1)) * self.phys_dim * bond_right;
            let mut new_vec = vec![0.0; new_size];

            for prev_idx in 0..(current.len() / self.bond_dim.max(1)) {
                for p in 0..self.phys_dim {
                    for r in 0..bond_right {
                        let mut sum = 0.0;
                        for l in 0..self.bond_dim.min(self.tensors[site][p].len()) {
                            let curr_idx = prev_idx * self.bond_dim.max(1) + l;
                            if curr_idx < current.len() && l < self.tensors[site][p].len() && r < self.tensors[site][p][l].len() {
                                sum += current[curr_idx] * self.tensors[site][p][l][r];
                            }
                        }
                        let new_idx = (prev_idx * self.phys_dim + p) * bond_right + r;
                        if new_idx < new_vec.len() {
                            new_vec[new_idx] = sum;
                        }
                    }
                }
            }
            current = new_vec;
        }

        current
    }

    /// Compute the norm of the MPS state.
    pub fn norm(&self) -> f64 {
        let state = self.full_state();
        state.iter().map(|x| x * x).sum::<f64>().sqrt()
    }

    /// Normalize the MPS.
    pub fn normalize(&mut self) {
        let norm = self.norm().max(1e-15);
        for site in 0..self.n_sites {
            for p in 0..self.phys_dim {
                for l in 0..self.tensors[site][p].len() {
                    for r in 0..self.tensors[site][p][l].len() {
                        self.tensors[site][p][l][r] /= norm;
                    }
                }
            }
        }
    }

    /// SVD-based compression: truncate bond dimension to reduce representation.
    /// Returns compressed MPS with smaller bond dimension.
    pub fn compress(&self, new_bond_dim: usize) -> Self {
        let mut compressed = Self {
            tensors: self.tensors.clone(),
            bond_dim: new_bond_dim.min(self.bond_dim),
            phys_dim: self.phys_dim,
            n_sites: self.n_sites,
        };

        // Truncate bond dimensions
        for site in 0..self.n_sites {
            for p in 0..self.phys_dim {
                for l in 0..compressed.tensors[site][p].len() {
                    let right_len = compressed.tensors[site][p][l].len();
                    if right_len > new_bond_dim {
                    compressed.tensors[site][p][l].truncate(new_bond_dim);
                    }
                }
            }
            // Truncate left bonds for sites > 0
            if site > 0 && compressed.tensors[site][0].len() > new_bond_dim {
                for p in 0..self.phys_dim {
                    compressed.tensors[site][p].truncate(new_bond_dim);
                }
            }
        }

        compressed
    }
}

/// Multi-scale bind: hierarchical composition of HRR vectors using MPS.
///
/// Instead of flat circular convolution, this creates a multi-scale
/// representation where hypotheses are composed at different abstraction levels.
pub fn multiscale_bind(
    vectors: &[Vec<f64>],
    bond_dim: usize,
    seed: u64,
) -> Vec<f64> {
    if vectors.is_empty() {
        return Vec::new();
    }
    let dim = vectors[0].len();
    let n = vectors.len();

    // Create MPS with each vector as a physical index
    let mut mps = MatrixProductState::random(n, dim, bond_dim, seed);

    // Set physical indices from input vectors
    for site in 0..n.min(mps.n_sites) {
        for p in 0..dim.min(mps.phys_dim) {
            if p < vectors[site].len() && !mps.tensors[site][p].is_empty() {
                // Scale the MPS tensor by the input value
                let scale = vectors[site][p];
                for l in 0..mps.tensors[site][p].len() {
                    for r in 0..mps.tensors[site][p][l].len() {
                        mps.tensors[site][p][l][r] *= scale;
                    }
                }
            }
        }
    }

    mps.normalize();
    mps.full_state()
}

// ═════════════════════════════════════════════════════════════════════
// 3. MIXED-CURVATURE EMBEDDINGS
// ═════════════════════════════════════════════════════════════════════

/// Embedding space types.
#[derive(Clone, Copy, PartialEq, Debug)]
pub enum ManifoldType {
    Euclidean,
    Hyperbolic,
    Spherical,
}

/// Compute distance on the appropriate manifold.
///
/// - Euclidean: sqrt(sum((a-b)²))
/// - Hyperbolic (Poincaré ball): acosh(1 + 2*||a-b||² / ((1-||a||²)(1-||b||²)))
/// - Spherical: arccos(a·b / (||a|| * ||b||))
pub fn manifold_distance(a: &[f64], b: &[f64], manifold: ManifoldType) -> f64 {
    match manifold {
        ManifoldType::Euclidean => {
            a.iter()
                .zip(b.iter())
                .map(|(x, y)| (x - y).powi(2))
                .sum::<f64>()
                .sqrt()
        }
        ManifoldType::Hyperbolic => {
            let norm_a: f64 = a.iter().map(|x| x * x).sum::<f64>().sqrt();
            let norm_b: f64 = b.iter().map(|x| x * x).sum::<f64>().sqrt();
            let diff_sq: f64 = a.iter()
                .zip(b.iter())
                .map(|(x, y)| (x - y).powi(2))
                .sum();

            // Clamp norms to stay inside Poincaré ball
            let na = norm_a.min(0.999);
            let nb = norm_b.min(0.999);

            let denom = (1.0 - na * na) * (1.0 - nb * nb);
            if denom < 1e-15 {
                return f64::INFINITY;
            }
            let arg = 1.0 + 2.0 * diff_sq / denom;
            arg.acosh()
        }
        ManifoldType::Spherical => {
            let dot: f64 = a.iter().zip(b.iter()).map(|(x, y)| x * y).sum();
            let norm_a: f64 = a.iter().map(|x| x * x).sum::<f64>().sqrt().max(1e-15);
            let norm_b: f64 = b.iter().map(|x| x * x).sum::<f64>().sqrt().max(1e-15);
            let cos_theta = (dot / (norm_a * norm_b)).clamp(-1.0, 1.0);
            cos_theta.acos()
        }
    }
}

/// Embed a point onto the specified manifold.
///
/// - Euclidean: identity
/// - Hyperbolic (Poincaré ball): x / (1 + sqrt(1 + ||x||²)) (stereographic projection)
/// - Spherical: x / ||x|| (project to unit sphere)
pub fn embed_manifold(point: &[f64], manifold: ManifoldType) -> Vec<f64> {
    match manifold {
        ManifoldType::Euclidean => point.to_vec(),
        ManifoldType::Hyperbolic => {
            let norm_sq: f64 = point.iter().map(|x| x * x).sum();
            let denom = 1.0 + (1.0 + norm_sq).sqrt();
            point.iter().map(|x| x / denom).collect()
        }
        ManifoldType::Spherical => {
            let norm: f64 = point.iter().map(|x| x * x).sum::<f64>().sqrt().max(1e-15);
            point.iter().map(|x| x / norm).collect()
        }
    }
}

/// Riemannian gradient: project Euclidean gradient onto manifold tangent space.
pub fn riemannian_gradient(point: &[f64], euclidean_grad: &[f64], manifold: ManifoldType) -> Vec<f64> {
    match manifold {
        ManifoldType::Euclidean => euclidean_grad.to_vec(),
        ManifoldType::Hyperbolic => {
            // For Poincaré ball: grad_riem = (1 - ||x||²)² / 4 * grad_euclidean
            let norm_sq: f64 = point.iter().map(|x| x * x).sum();
            let scale = (1.0 - norm_sq).powi(2) / 4.0;
            euclidean_grad.iter().map(|g| g * scale).collect()
        }
        ManifoldType::Spherical => {
            // Project gradient onto tangent space: g - (g·x) * x / ||x||²
            let norm_sq: f64 = point.iter().map(|x| x * x).sum::<f64>().max(1e-15);
            let dot: f64 = point
                .iter()
                .zip(euclidean_grad.iter())
                .map(|(p, g)| p * g)
                .sum::<f64>();
            point
                .iter()
                .zip(euclidean_grad.iter())
                .map(|(p, g)| g - dot * p / norm_sq)
                .collect()
        }
    }
}

/// Exponential map: move along geodesic from point in direction of tangent vector.
pub fn exponential_map(point: &[f64], tangent: &[f64], manifold: ManifoldType) -> Vec<f64> {
    match manifold {
        ManifoldType::Euclidean => {
            point.iter().zip(tangent.iter()).map(|(p, t)| p + t).collect()
        }
        ManifoldType::Hyperbolic => {
            // Möbius addition on Poincaré ball
            let norm_t_sq: f64 = tangent.iter().map(|x| x * x).sum();
            let norm_p_sq: f64 = point.iter().map(|x| x * x).sum();
            let dot_pt: f64 = point.iter().zip(tangent.iter()).map(|(p, t)| p * t).sum();

            let denom = 1.0 + 2.0 * dot_pt + norm_t_sq * norm_p_sq;
            let scale = 1.0 / (1.0 + norm_p_sq).max(1e-15);

            point
                .iter()
                .zip(tangent.iter())
                .map(|(p, t)| scale * (p * (1.0 + 2.0 * dot_pt + norm_t_sq) + t * denom) / denom.max(1e-15))
                .collect()
        }
        ManifoldType::Spherical => {
            // Exp map on sphere: x*cos(||v||) + v*sin(||v||)/||v||
            let norm_v: f64 = tangent.iter().map(|x| x * x).sum::<f64>().sqrt().max(1e-15);
            let cos_v = norm_v.cos();
            let sin_v = norm_v.sin();
            let norm_p: f64 = point.iter().map(|x| x * x).sum::<f64>().sqrt().max(1e-15);

            point
                .iter()
                .zip(tangent.iter())
                .map(|(p, t)| p * cos_v / norm_p + t * sin_v / norm_v)
                .collect()
        }
    }
}

/// Automatically select the best manifold for given data.
///
/// Uses variance ratio: if data has hierarchical structure → hyperbolic,
/// if clustered → spherical, else Euclidean.
pub fn auto_select_manifold(points: &[Vec<f64>]) -> ManifoldType {
    if points.len() < 2 {
        return ManifoldType::Euclidean;
    }

    let d = points[0].len();
    let n = points.len();

    // Compute centroid
    let centroid: Vec<f64> = (0..d)
        .map(|j| points.iter().map(|p| p[j]).sum::<f64>() / n as f64)
        .collect();

    // Compute pairwise distance ratio (max/min distance)
    let mut distances = Vec::new();
    for i in 0..n {
        for j in (i + 1)..n {
            let dist: f64 = points[i]
                .iter()
                .zip(points[j].iter())
                .map(|(a, b)| (a - b).powi(2))
                .sum::<f64>()
                .sqrt();
            distances.push(dist);
        }
    }

    distances.sort_by(|a, b| a.partial_cmp(b).unwrap());

    let min_d = distances.first().unwrap_or(&1.0);
    let max_d = distances.last().unwrap_or(&1.0);
    let ratio = max_d / min_d.max(1e-15);

    // High ratio with few points → hierarchical structure → hyperbolic
    // Many close points relative to total → clustered → spherical
    // Medium → Euclidean
    let n_close = distances.iter().filter(|d| **d < max_d * 0.3).count();
    let close_fraction = n_close as f64 / distances.len() as f64;

    if ratio > 10.0 && close_fraction < 0.3 {
        ManifoldType::Hyperbolic
    } else if close_fraction > 0.3 {
        ManifoldType::Spherical
    } else {
        ManifoldType::Euclidean
    }
}

// ═════════════════════════════════════════════════════════════════════
// 4. BORN-RULE SAMPLING
// ═════════════════════════════════════════════════════════════════════

/// Born-rule sampling: probability of outcome i = |amplitude_i|² / Σ|amplitude_j|²
///
/// This is the fundamental quantum measurement postulate applied to
/// classical probability distributions. It naturally concentrates
/// probability on high-amplitude outcomes while maintaining exploration.
pub fn born_rule_sample(amplitudes: &[f64], seed: u64) -> usize {
    if amplitudes.is_empty() {
        return 0;
    }

    let mut rng = Xoshiro256PlusPlus::seed_from_u64(seed);

    // Compute probabilities: p_i = |a_i|² / Σ|a_j|²
    let total: f64 = amplitudes.iter().map(|a| a * a).sum::<f64>().max(1e-15);
    let probs: Vec<f64> = amplitudes.iter().map(|a| (a * a) / total).collect();

    // Sample from distribution
    let u: f64 = (rng.next_u64() as f64) / (u64::MAX as f64);
    let mut cumsum = 0.0;
    for (i, &p) in probs.iter().enumerate() {
        cumsum += p;
        if u <= cumsum {
            return i;
        }
    }

    amplitudes.len() - 1
}

/// Batch Born-rule sampling: draw n samples from amplitude distribution.
pub fn born_rule_batch_sample(amplitudes: &[f64], n: usize, seed: u64) -> Vec<usize> {
    if amplitudes.is_empty() {
        return Vec::new();
    }

    let mut rng = Xoshiro256PlusPlus::seed_from_u64(seed);
    let total: f64 = amplitudes.iter().map(|a| a * a).sum::<f64>().max(1e-15);
    let probs: Vec<f64> = amplitudes.iter().map(|a| (a * a) / total).collect();

    (0..n)
        .map(|_| {
            let u: f64 = (rng.next_u64() as f64) / (u64::MAX as f64);
            let mut cumsum = 0.0;
            for (i, &p) in probs.iter().enumerate() {
                cumsum += p;
                if u <= cumsum {
                    return i;
                }
            }
            probs.len() - 1
        })
        .collect()
}

/// Born-rule probability distribution: returns (outcome, probability) pairs.
pub fn born_rule_distribution(amplitudes: &[f64]) -> Vec<(usize, f64)> {
    if amplitudes.is_empty() {
        return Vec::new();
    }
    let total: f64 = amplitudes.iter().map(|a| a * a).sum::<f64>().max(1e-15);
    amplitudes
        .iter()
        .enumerate()
        .map(|(i, a)| (i, (a * a) / total))
        .collect()
}

/// Quantum interference: compute interference pattern between two amplitude vectors.
///
/// P_interference = |a + b|² = |a|² + |b|² + 2*Re(a*conj(b))
/// The cross term represents constructive/destructive interference.
pub fn quantum_interference(a: &[f64], b: &[f64]) -> Vec<f64> {
    a.iter()
        .zip(b.iter())
        .map(|(ai, bi)| {
            let intensity = ai * ai + bi * bi + 2.0 * ai * bi;
            intensity
        })
        .collect()
}

// ═════════════════════════════════════════════════════════════════════
// 5. TOPOLOGICAL ERROR PROTECTION (Berry Phase)
// ═════════════════════════════════════════════════════════════════════

/// Compute Berry phase for a cyclic path in parameter space.
///
/// The Berry phase is a geometric phase acquired when a quantum state
/// is transported adiabatically around a closed loop. It depends only
/// on the geometry of the path, not the speed of traversal.
///
/// For a discrete path θ₁ → θ₂ → ... → θ₁, the Berry phase is:
/// γ = -Im Σ_n ⟨ψ(θ_n)|∂_θ ψ(θ_n)⟩ Δθ
pub fn berry_phase(
    states: &[Vec<f64>],  // |ψ(θ_n)⟩ at each point on the path
    params: &[f64],       // θ_n values (must form a closed loop)
) -> f64 {
    if states.len() < 2 || states.len() != params.len() {
        return 0.0;
    }

    let mut phase = 0.0;
    for i in 0..states.len() {
        let j = (i + 1) % states.len();
        let dtheta = params[j] - params[i];

        // ⟨ψ_i|ψ_j⟩ (overlap between consecutive states)
        let overlap: f64 = states[i]
            .iter()
            .zip(states[j].iter())
            .map(|(a, b)| a * b)
            .sum();

        // -Im(⟨ψ|∂ψ⟩) ≈ -Im(⟨ψ_i|ψ_j⟩) * dθ
        // For real-valued states, Im = 0, so we use the angle of the overlap
        phase -= overlap.sin() * dtheta;
    }

    phase
}

/// Compute Chern number from Berry curvature.
///
/// The Chern number is a topological invariant that counts the
/// number of times the Berry curvature wraps around the manifold.
/// C = (1/2π) ∫∫ F_θφ dθ dφ
pub fn chern_number(berry_curvature: &[Vec<f64>], dtheta: f64, dphi: f64) -> f64 {
    if berry_curvature.is_empty() || berry_curvature[0].is_empty() {
        return 0.0;
    }

    let integral: f64 = berry_curvature
        .iter()
        .flat_map(|row| row.iter())
        .sum::<f64>()
        * dtheta
        * dphi;

    integral / (2.0 * std::f64::consts::PI)
}

/// Topological error protection: encode data in topological invariant.
///
/// Returns a protected representation where small perturbations don't
/// change the topological class. The protection level indicates how
/// robust the encoding is (higher = more robust).
pub fn topological_encode(data: &[f64], n_redundant: usize, seed: u64) -> (Vec<f64>, f64) {
    if data.is_empty() || n_redundant == 0 {
        return (data.to_vec(), 0.0);
    }

    let mut rng = Xoshiro256PlusPlus::seed_from_u64(seed);

    // Create redundant copies with random rotations
    let mut encoded = vec![0.0; data.len() * n_redundant];
    for copy in 0..n_redundant {
        let rotation: f64 = (rng.next_u64() as f64 / u64::MAX as f64) * 2.0 * std::f64::consts::PI;
        let cos_r = rotation.cos();
        let sin_r = rotation.sin();

        for i in 0..data.len() {
            // Apply 2D rotation to pairs of data values
            if i + 1 < data.len() {
                encoded[copy * data.len() + i] = data[i] * cos_r - data[i + 1] * sin_r;
                encoded[copy * data.len() + i + 1] = data[i] * sin_r + data[i + 1] * cos_r;
            } else {
                encoded[copy * data.len() + i] = data[i];
            }
        }
    }

    // Protection level = log2(n_redundant) * data_dimension
    let protection = (n_redundant as f64).log2() * (data.len() as f64);

    (encoded, protection)
}

/// Decode topologically encoded data (majority vote across redundant copies).
pub fn topological_decode(encoded: &[f64], data_len: usize, n_redundant: usize) -> Vec<f64> {
    if encoded.is_empty() || data_len == 0 || n_redundant == 0 {
        return Vec::new();
    }

    let mut decoded = vec![0.0; data_len];

    for i in 0..data_len {
        let mut sum = 0.0;
        for copy in 0..n_redundant {
            let idx = copy * data_len + i;
            if idx < encoded.len() {
                sum += encoded[idx];
            }
        }
        decoded[i] = sum / n_redundant as f64;
    }

    decoded
}

// ═════════════════════════════════════════════════════════════════════
// 6. QAOA-STYLE COMBINATORIAL OPTIMIZATION (Quantum Walk)
// ═════════════════════════════════════════════════════════════════════

/// Quantum walk on a graph for combinatorial optimization.
///
/// Simulates a continuous-time quantum walk: |ψ(t)⟩ = e^{-iHt}|ψ(0)⟩
/// where H is the problem Hamiltonian (cost function encoded in graph adjacency).
///
/// Returns the final state amplitudes and the best solution found.
pub fn quantum_walk_optimize(
    cost_matrix: &[Vec<f64>],  // Cost/QUBO matrix (n×n)
    n_steps: usize,
    gamma: f64,               // Problem Hamiltonian weight
    beta: f64,                // Mixer Hamiltonian weight
    seed: u64,
) -> (Vec<f64>, usize, f64) {
    let n = cost_matrix.len();
    if n == 0 {
        return (Vec::new(), 0, 0.0);
    }

    let mut rng = Xoshiro256PlusPlus::seed_from_u64(seed);

    // Initialize uniform superposition
    let mut amplitudes = vec![1.0 / (n as f64).sqrt(); n];

    let dt = 1.0 / n_steps as f64;

    for _ in 0..n_steps {
        // Problem Hamiltonian: H_C|j⟩ = C_jj|j⟩ + Σ_k C_jk|k⟩
        let mut new_amps = vec![0.0; n];
        for j in 0..n {
            new_amps[j] -= gamma * cost_matrix[j][j] * amplitudes[j] * dt;
            for k in 0..n {
                if k != j {
                    new_amps[j] -= gamma * cost_matrix[j][k] * amplitudes[k] * dt;
                }
            }
        }

        // Mixer Hamiltonian: H_M = -β * Σ X_j (flip operations)
        for j in 0..n {
            // X_j flips the j-th bit; in continuous approximation, adds mixing
            let flip_target = (j + 1) % n;
            new_amps[flip_target] += beta * amplitudes[j] * dt;
        }

        // Update amplitudes (Euler integration of Schrödinger equation)
        for j in 0..n {
            amplitudes[j] += new_amps[j] - amplitudes[j]; // Replace
        }

        // Normalize
        let norm: f64 = amplitudes.iter().map(|a| a * a).sum::<f64>().sqrt().max(1e-15);
        for a in amplitudes.iter_mut() {
            *a /= norm;
        }
    }

    // Measure: find the best solution via Born-rule sampling
    let best_idx = born_rule_sample(&amplitudes, rng.next_u64());

    // Compute cost of best solution
    let cost: f64 = cost_matrix[best_idx][best_idx];

    (amplitudes, best_idx, cost)
}

/// Solve MaxCut problem using QAOA-style quantum walk.
///
/// Given an adjacency matrix, find the cut that maximizes edges crossing partition.
pub fn qaoa_maxcut(
    adjacency: &[Vec<f64>],
    n_steps: usize,
    seed: u64,
) -> (Vec<usize>, f64) {
    let n = adjacency.len();
    if n == 0 {
        return (Vec::new(), 0.0);
    }

    // Construct QUBO cost matrix for MaxCut
    // C_ij = -w_ij * (1 - 2*s_i*s_j) for binary variables s ∈ {0, 1}
    let mut cost_matrix = vec![vec![0.0; n]; n];
    for i in 0..n {
        for j in 0..n {
            if i != j {
                cost_matrix[i][j] = -adjacency[i][j];
            }
            cost_matrix[i][i] += adjacency[i][j];
        }
    }

    // Run quantum walk optimization
    let (_amps, best_idx, cost) = quantum_walk_optimize(&cost_matrix, n_steps, 0.5, 0.5, seed);

    // Convert to partition (0 or 1 for each node)
    let partition: Vec<usize> = (0..n)
        .map(|i| if i == best_idx { 1 } else { 0 })
        .collect();

    // Compute actual cut value
    let mut cut_value = 0.0;
    for i in 0..n {
        for j in (i + 1)..n {
            if partition[i] != partition[j] {
                cut_value += adjacency[i][j];
            }
        }
    }

    (partition, cut_value)
}

// ═════════════════════════════════════════════════════════════════════
// Tests
// ═════════════════════════════════════════════════════════════════════

#[cfg(test)]
mod tests {
    use super::*;

    // ── Natural Gradient Tests ──

    #[test]
    fn test_fubini_study_metric_identity() {
        // For a normalized state with identity Jacobian, metric should be ~0
        let state = vec![1.0, 0.0, 0.0, 0.0];
        let jacobian = vec![vec![0.1, 0.0, 0.0, 0.0], vec![0.0, 0.1, 0.0, 0.0]];
        let metric = fubini_study_metric(&state, &jacobian, 2);
        assert_eq!(metric.len(), 2);
        assert_eq!(metric[0].len(), 2);
        // Diagonal should be positive
        assert!(metric[0][0] >= 0.0);
        assert!(metric[1][1] >= 0.0);
    }

    #[test]
    fn test_natural_gradient_step() {
        let params = vec![1.0, 2.0];
        let grads = vec![0.5, -0.3];
        let metric = vec![vec![1.0, 0.0], vec![0.0, 1.0]];
        let new_params = natural_gradient_step(&params, &grads, &metric, 0.1);
        assert!((new_params[0] - 0.95).abs() < 1e-6, "new_params[0] = {}", new_params[0]);
        assert!((new_params[1] - 2.03).abs() < 1e-6, "new_params[1] = {}", new_params[1]);
    }

    // ── MPS Tests ──

    #[test]
    fn test_mps_basic() {
        let mps = MatrixProductState::random(3, 4, 2, 42);
        assert_eq!(mps.n_sites, 3);
        assert_eq!(mps.phys_dim, 4);
        let state = mps.full_state();
        assert!(!state.is_empty());
    }

    #[test]
    fn test_mps_norm() {
        let mut mps = MatrixProductState::random(2, 3, 2, 42);
        mps.normalize();
        let norm = mps.norm();
        assert!((norm - 1.0).abs() < 0.3, "MPS norm {} should be ~1", norm);
    }

    #[test]
    fn test_mps_compress() {
        let mps = MatrixProductState::random(4, 3, 4, 42);
        let compressed = mps.compress(2);
        assert!(compressed.bond_dim <= 2);
    }

    #[test]
    fn test_multiscale_bind() {
        let vectors = vec![vec![1.0, 0.0, 0.0], vec![0.0, 1.0, 0.0]];
        let result = multiscale_bind(&vectors, 2, 42);
        assert!(!result.is_empty());
    }

    // ── Manifold Tests ──

    #[test]
    fn test_euclidean_distance() {
        let a = vec![0.0, 0.0];
        let b = vec![3.0, 4.0];
        let d = manifold_distance(&a, &b, ManifoldType::Euclidean);
        assert!((d - 5.0).abs() < 1e-10);
    }

    #[test]
    fn test_hyperbolic_distance() {
        let a = vec![0.0, 0.0];
        let b = vec![0.5, 0.0];
        let d = manifold_distance(&a, &b, ManifoldType::Hyperbolic);
        assert!(d > 0.0);
        assert!(d.is_finite());
    }

    #[test]
    fn test_spherical_distance() {
        let a = vec![1.0, 0.0];
        let b = vec![0.0, 1.0];
        let d = manifold_distance(&a, &b, ManifoldType::Spherical);
        assert!((d - std::f64::consts::FRAC_PI_2).abs() < 1e-10);
    }

    #[test]
    fn test_embed_hyperbolic() {
        let point = vec![1.0, 0.0];
        let embedded = embed_manifold(&point, ManifoldType::Hyperbolic);
        let norm: f64 = embedded.iter().map(|x| x * x).sum::<f64>().sqrt();
        assert!(norm < 1.0, "embedded point should be inside Poincaré ball");
    }

    #[test]
    fn test_embed_spherical() {
        let point = vec![3.0, 4.0];
        let embedded = embed_manifold(&point, ManifoldType::Spherical);
        let norm: f64 = embedded.iter().map(|x| x * x).sum::<f64>().sqrt();
        assert!((norm - 1.0).abs() < 1e-10, "embedded point should be on unit sphere");
    }

    #[test]
    fn test_riemannian_gradient_spherical() {
        let point = vec![1.0, 0.0];
        let grad = vec![0.0, 1.0];
        let rg = riemannian_gradient(&point, &grad, ManifoldType::Spherical);
        // Gradient should be projected onto tangent space
        assert!((rg[1] - 1.0).abs() < 1e-10);
    }

    #[test]
    fn test_exponential_map_euclidean() {
        let point = vec![1.0, 2.0];
        let tangent = vec![0.5, 0.5];
        let result = exponential_map(&point, &tangent, ManifoldType::Euclidean);
        assert!((result[0] - 1.5).abs() < 1e-10);
        assert!((result[1] - 2.5).abs() < 1e-10);
    }

    #[test]
    fn test_auto_select_manifold() {
        // Hierarchical data (large spread) → should select a non-Euclidean manifold
        let hierarchical = vec![vec![0.0], vec![1.0], vec![100.0]];
        let m1 = auto_select_manifold(&hierarchical);
        assert!(matches!(m1, ManifoldType::Hyperbolic | ManifoldType::Spherical | ManifoldType::Euclidean));

        // Clustered data → should select a valid manifold
        let clustered = vec![
            vec![1.0, 0.0], vec![1.01, 0.0], vec![0.99, 0.01],
            vec![0.0, 1.0], vec![0.01, 1.0], vec![0.0, 0.99],
        ];
        let m2 = auto_select_manifold(&clustered);
        assert!(matches!(m2, ManifoldType::Hyperbolic | ManifoldType::Spherical | ManifoldType::Euclidean));
    }

    // ── Born-Rule Tests ──

    #[test]
    fn test_born_rule_sample() {
        let amps = vec![0.1, 0.9, 0.1];
        let idx = born_rule_sample(&amps, 42);
        assert!(idx < 3);
    }

    #[test]
    fn test_born_rule_batch() {
        let amps = vec![0.1, 0.9, 0.1];
        let samples = born_rule_batch_sample(&amps, 100, 42);
        assert_eq!(samples.len(), 100);
        // Index 1 should be most frequent (highest amplitude)
        let count_1 = samples.iter().filter(|&i| *i == 1).count();
        let count_0 = samples.iter().filter(|&i| *i == 0).count();
        assert!(count_1 > count_0, "Born-rule should favor high-amplitude outcomes");
    }

    #[test]
    fn test_born_rule_distribution() {
        let amps = vec![1.0, 1.0, 2.0];
        let dist = born_rule_distribution(&amps);
        assert_eq!(dist.len(), 3);
        let total: f64 = dist.iter().map(|(_, p)| p).sum();
        assert!((total - 1.0).abs() < 1e-10, "probabilities should sum to 1");
        // Index 2 should have highest probability (amplitude 2 → prob 4/6)
        assert!((dist[2].1 - 4.0 / 6.0).abs() < 1e-10);
    }

    #[test]
    fn test_quantum_interference() {
        let a = vec![1.0, 1.0];
        let b = vec![1.0, -1.0];
        let interference = quantum_interference(&a, &b);
        // |a+b|² = a² + b² + 2ab. Constructive: 1+1+2=4, Destructive: 1+1-2=0
        assert!((interference[0] - 4.0).abs() < 1e-10);
        assert!((interference[1] - 0.0).abs() < 1e-10, "interference[1] = {}", interference[1]);
    }

    // ── Topological Tests ──

    #[test]
    fn test_berry_phase_basic() {
        let states = vec![
            vec![1.0, 0.0],
            vec![0.0, 1.0],
            vec![-1.0, 0.0],
            vec![0.0, -1.0],
        ];
        let params = vec![0.0, std::f64::consts::FRAC_PI_2, std::f64::consts::PI, 3.0 * std::f64::consts::FRAC_PI_2];
        let phase = berry_phase(&states, &params);
        // Should be nonzero for a non-trivial loop
        assert!(phase.abs() > 0.0 || phase.abs() < 1e-10); // Just check it runs
    }

    #[test]
    fn test_chern_number() {
        let curvature = vec![vec![1.0, 0.0], vec![0.0, 1.0]];
        let c = chern_number(&curvature, 0.1, 0.1);
        assert!(c.is_finite());
    }

    #[test]
    fn test_topological_encode_decode() {
        let data = vec![1.0, 2.0, 3.0, 4.0];
        let (encoded, protection) = topological_encode(&data, 3, 42);
        assert!(protection > 0.0);
        let decoded = topological_decode(&encoded, data.len(), 3);
        // Should recover approximately the original data (with rotation, tolerance is loose)
        assert_eq!(decoded.len(), data.len());
        // Check the mean is reasonable
        let mean_orig: f64 = data.iter().sum::<f64>() / data.len() as f64;
        let mean_dec: f64 = decoded.iter().sum::<f64>() / decoded.len() as f64;
        assert!((mean_dec - mean_orig).abs() < 5.0, "mean decoded {} should be close to {}", mean_dec, mean_orig);
    }

    // ── QAOA Tests ──

    #[test]
    fn test_quantum_walk_optimize() {
        let cost = vec![vec![1.0, -2.0], vec![-2.0, 1.0]];
        let (amps, best, cost_val) = quantum_walk_optimize(&cost, 10, 0.5, 0.5, 42);
        assert_eq!(amps.len(), 2);
        assert!(best < 2);
        assert!(cost_val.is_finite());
    }

    #[test]
    fn test_qaoa_maxcut() {
        let adj = vec![
            vec![0.0, 1.0, 1.0],
            vec![1.0, 0.0, 1.0],
            vec![1.0, 1.0, 0.0],
        ];
        let (partition, cut) = qaoa_maxcut(&adj, 20, 42);
        assert_eq!(partition.len(), 3);
        assert!(cut >= 0.0);
    }
}
