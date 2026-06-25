//! Hexagram HRR Encoding + Interaction Matrix (Phase 5a) + Synergy Detection (Phase 5c)
//!
//! Encodes each of the 64 hexagrams as a holographic reduced representation (HRR)
//! vector. Computes an interaction matrix between hexagram pairs. Detects
//! synergistic hexagram combinations via cosine similarity in HRR space.

use crate::iching::Trigram;

/// HRR vector dimensionality (must be power of 2 for FFT-based binding).
pub const HRR_DIM: usize = 64;

/// HRR vector: real-valued, unit-norm.
pub type HrrVec = Vec<f64>;

/// Generate a deterministic random vector from a seed (hexagram number).
/// Uses a simple LCG for reproducibility.
fn seeded_vector(seed: u64, dim: usize) -> HrrVec {
    let mut state = seed;
    let mut v = Vec::with_capacity(dim);
    for _ in 0..dim {
        // LCG: x_{n+1} = (a*x_n + c) mod m
        state = state.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
        // Map to [-1, 1]
        let val = ((state >> 33) as f64) / (1u64 << 31) as f64 * 2.0 - 1.0;
        v.push(val);
    }
    // Normalize to unit length
    let norm: f64 = v.iter().map(|x| x * x).sum::<f64>().sqrt();
    if norm > 0.0 {
        for x in &mut v {
            *x /= norm;
        }
    }
    v
}

/// Encode a trigram as an HRR vector.
fn trigram_hrr(trigram: &Trigram) -> HrrVec {
    let seed = match trigram {
        Trigram::Qian => 1u64,
        Trigram::Kun  => 2,
        Trigram::Zhen => 3,
        Trigram::Xun  => 4,
        Trigram::Kan  => 5,
        Trigram::Li   => 6,
        Trigram::Gen  => 7,
        Trigram::Dui  => 8,
    };
    seeded_vector(seed, HRR_DIM)
}

/// Encode a hexagram as an HRR vector by binding lower and upper trigram vectors.
/// Uses circular convolution (binding) via FFT-domain multiplication.
pub fn hexagram_hrr(lower: &Trigram, upper: &Trigram) -> HrrVec {
    let lower_v = trigram_hrr(lower);
    let upper_v = trigram_hrr(upper);

    // Circular convolution (binding) via direct O(n²) — fine for dim=64
    let n = HRR_DIM;
    let mut result = vec![0.0; n];
    for i in 0..n {
        for j in 0..n {
            result[(i + j) % n] += lower_v[i] * upper_v[j];
        }
    }

    // Normalize
    let norm: f64 = result.iter().map(|x| x * x).sum::<f64>().sqrt();
    if norm > 0.0 {
        for x in &mut result {
            *x /= norm;
        }
    }
    result
}

/// Encode hexagram by King Wen number (uses reverse lookup).
pub fn hexagram_hrr_by_number(king_wen: u32) -> HrrVec {
    let binary = king_wen_to_binary(king_wen);
    let lower = Trigram::from_binary((binary & 0b111) as u8);
    let upper = Trigram::from_binary(((binary >> 3) & 0b111) as u8);
    hexagram_hrr(&lower, &upper)
}

/// Cosine similarity between two HRR vectors.
pub fn cosine_sim(a: &[f64], b: &[f64]) -> f64 {
    let dot: f64 = a.iter().zip(b.iter()).map(|(x, y)| x * y).sum();
    let norm_a: f64 = a.iter().map(|x| x * x).sum::<f64>().sqrt();
    let norm_b: f64 = b.iter().map(|x| x * x).sum::<f64>().sqrt();
    if norm_a > 0.0 && norm_b > 0.0 {
        dot / (norm_a * norm_b)
    } else {
        0.0
    }
}

/// Compute the 64×64 interaction matrix of cosine similarities between all hexagram pairs.
/// Returns a flat Vec<f64> of length 64*64, row-major (index = row*64 + col).
pub fn interaction_matrix() -> Vec<f64> {
    let vectors: Vec<HrrVec> = (1..=64u32).map(hexagram_hrr_by_number).collect();
    let mut matrix = Vec::with_capacity(64 * 64);
    for i in 0..64 {
        for j in 0..64 {
            matrix.push(cosine_sim(&vectors[i], &vectors[j]));
        }
    }
    matrix
}

/// Get interaction score between two hexagrams (King Wen numbers 1-64).
pub fn interaction_score(kw1: u32, kw2: u32) -> f64 {
    let v1 = hexagram_hrr_by_number(kw1);
    let v2 = hexagram_hrr_by_number(kw2);
    cosine_sim(&v1, &v2)
}

// ---------------------------------------------------------------------------
// Phase 5c: Hexagram Synergy Detection
// ---------------------------------------------------------------------------

/// A synergistic pair: two hexagrams whose HRR similarity exceeds a threshold.
#[derive(Debug, Clone)]
pub struct SynergyPair {
    pub hexagram_a: u32,
    pub hexagram_b: u32,
    pub similarity: f64,
}

/// Find all synergistic hexagram pairs above a threshold.
pub fn detect_synergies(threshold: f64) -> Vec<SynergyPair> {
    let vectors: Vec<HrrVec> = (1..=64u32).map(hexagram_hrr_by_number).collect();
    let mut pairs = Vec::new();

    for i in 0..64 {
        for j in (i + 1)..64 {
            let sim = cosine_sim(&vectors[i], &vectors[j]);
            if sim > threshold {
                pairs.push(SynergyPair {
                    hexagram_a: (i + 1) as u32,
                    hexagram_b: (j + 1) as u32,
                    similarity: sim,
                });
            }
        }
    }
    pairs.sort_by(|a, b| b.similarity.partial_cmp(&a.similarity).unwrap_or(std::cmp::Ordering::Equal));
    pairs
}

/// Find the top-K most synergistic pairs.
pub fn top_synergies(k: usize) -> Vec<SynergyPair> {
    let vectors: Vec<HrrVec> = (1..=64u32).map(hexagram_hrr_by_number).collect();
    let mut pairs = Vec::new();

    for i in 0..64 {
        for j in (i + 1)..64 {
            let sim = cosine_sim(&vectors[i], &vectors[j]);
            pairs.push(SynergyPair {
                hexagram_a: (i + 1) as u32,
                hexagram_b: (j + 1) as u32,
                similarity: sim,
            });
        }
    }
    pairs.sort_by(|a, b| b.similarity.partial_cmp(&a.similarity).unwrap_or(std::cmp::Ordering::Equal));
    pairs.truncate(k);
    pairs
}

/// Superpose two hexagram HRR vectors (addition + normalization).
/// Represents combining two hexagram influences.
pub fn superpose(a: &[f64], b: &[f64]) -> HrrVec {
    let mut result: Vec<f64> = a.iter().zip(b.iter()).map(|(x, y)| x + y).collect();
    let norm: f64 = result.iter().map(|x| x * x).sum::<f64>().sqrt();
    if norm > 0.0 {
        for x in &mut result {
            *x /= norm;
        }
    }
    result
}

/// Unbind a hexagram from a superposition (approximate inverse via reversal).
pub fn unbind(superposition: &[f64], key: &[f64]) -> HrrVec {
    // Circular correlation (unbind) via direct computation
    let n = superposition.len();
    let mut result = vec![0.0; n];
    for i in 0..n {
        for j in 0..n {
            result[i] += superposition[j] * key[(n - j + i) % n];
        }
    }
    // Normalize
    let norm: f64 = result.iter().map(|x| x * x).sum::<f64>().sqrt();
    if norm > 0.0 {
        for x in &mut result {
            *x /= norm;
        }
    }
    result
}

// Reverse King Wen lookup (local copy)
fn king_wen_to_binary(kw: u32) -> u32 {
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
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_seeded_vector_unit_norm() {
        let v = seeded_vector(42, 64);
        let norm: f64 = v.iter().map(|x| x * x).sum::<f64>().sqrt();
        assert!((norm - 1.0).abs() < 1e-10, "Norm should be 1.0, got {}", norm);
    }

    #[test]
    fn test_seeded_vector_deterministic() {
        let v1 = seeded_vector(42, 64);
        let v2 = seeded_vector(42, 64);
        assert_eq!(v1, v2);
    }

    #[test]
    fn test_trigram_hrr_unit_norm() {
        for t in [Trigram::Qian, Trigram::Kun, Trigram::Zhen, Trigram::Xun,
                  Trigram::Kan, Trigram::Li, Trigram::Gen, Trigram::Dui] {
            let v = trigram_hrr(&t);
            let norm: f64 = v.iter().map(|x| x * x).sum::<f64>().sqrt();
            assert!((norm - 1.0).abs() < 1e-10, "Trigram {:?} norm = {}", t, norm);
        }
    }

    #[test]
    fn test_hexagram_hrr_unit_norm() {
        let v = hexagram_hrr(&Trigram::Qian, &Trigram::Kun);
        let norm: f64 = v.iter().map(|x| x * x).sum::<f64>().sqrt();
        assert!((norm - 1.0).abs() < 1e-10, "Hexagram HRR norm = {}", norm);
    }

    #[test]
    fn test_hexagram_hrr_dim() {
        let v = hexagram_hrr(&Trigram::Qian, &Trigram::Kun);
        assert_eq!(v.len(), HRR_DIM);
    }

    #[test]
    fn test_cosine_sim_self_is_one() {
        let v = hexagram_hrr(&Trigram::Qian, &Trigram::Kun);
        let sim = cosine_sim(&v, &v);
        assert!((sim - 1.0).abs() < 1e-10, "Self-similarity should be 1.0, got {}", sim);
    }

    #[test]
    fn test_cosine_sim_orthogonal_low() {
        let v1 = seeded_vector(1, 64);
        let v2 = seeded_vector(999, 64);
        let sim = cosine_sim(&v1, &v2);
        assert!(sim.abs() < 0.5, "Different seeds should have low similarity, got {}", sim);
    }

    #[test]
    fn test_interaction_matrix_size() {
        let m = interaction_matrix();
        assert_eq!(m.len(), 64 * 64);
    }

    #[test]
    fn test_interaction_matrix_diagonal_one() {
        let m = interaction_matrix();
        for i in 0..64 {
            let diag = m[i * 64 + i];
            assert!((diag - 1.0).abs() < 1e-10, "Diagonal {} = {}", i, diag);
        }
    }

    #[test]
    fn test_interaction_matrix_symmetric() {
        let m = interaction_matrix();
        for i in 0..64 {
            for j in 0..64 {
                assert!((m[i * 64 + j] - m[j * 64 + i]).abs() < 1e-10,
                    "Asymmetric at ({},{})", i, j);
            }
        }
    }

    #[test]
    fn test_interaction_score_range() {
        for a in [1u32, 10, 30, 50, 64] {
            for b in [1u32, 10, 30, 50, 64] {
                let s = interaction_score(a, b);
                assert!(s >= -1.01 && s <= 1.01, "Score ({},{}) = {} out of range", a, b, s);
            }
        }
    }

    #[test]
    fn test_detect_synergies_threshold() {
        // With high threshold, should get few or no synergies
        let high = detect_synergies(0.99);
        // Self-similarity is excluded (i < j), so high threshold may give 0
        assert!(high.iter().all(|p| p.similarity > 0.99));

        // With low threshold, should get many
        let low = detect_synergies(-1.0);
        assert!(low.len() == 64 * 63 / 2, "Expected all pairs, got {}", low.len());
    }

    #[test]
    fn test_detect_synergies_sorted() {
        let pairs = detect_synergies(0.0);
        for i in 1..pairs.len() {
            assert!(pairs[i].similarity <= pairs[i-1].similarity,
                "Not sorted descending at index {}", i);
        }
    }

    #[test]
    fn test_top_synergies_count() {
        let top = top_synergies(10);
        assert_eq!(top.len(), 10);
    }

    #[test]
    fn test_top_synergies_sorted() {
        let top = top_synergies(20);
        for i in 1..top.len() {
            assert!(top[i].similarity <= top[i-1].similarity);
        }
    }

    #[test]
    fn test_superpose_unit_norm() {
        let v1 = hexagram_hrr(&Trigram::Qian, &Trigram::Kun);
        let v2 = hexagram_hrr(&Trigram::Zhen, &Trigram::Xun);
        let s = superpose(&v1, &v2);
        let norm: f64 = s.iter().map(|x| x * x).sum::<f64>().sqrt();
        assert!((norm - 1.0).abs() < 1e-10, "Superposed norm = {}", norm);
    }

    #[test]
    fn test_hexagram_hrr_by_number() {
        let v1 = hexagram_hrr_by_number(1);
        let v2 = hexagram_hrr_by_number(2);
        assert_eq!(v1.len(), HRR_DIM);
        assert_eq!(v2.len(), HRR_DIM);
        // Different hexagrams should have different vectors
        assert!(v1 != v2);
    }

    #[test]
    fn test_same_hexagram_same_hrr() {
        let v1 = hexagram_hrr_by_number(15);
        let v2 = hexagram_hrr_by_number(15);
        assert_eq!(v1, v2, "Same hexagram should produce same HRR");
    }
}
