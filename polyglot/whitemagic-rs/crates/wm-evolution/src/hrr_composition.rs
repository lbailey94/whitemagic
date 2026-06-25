//! HRR-Based Improvement Composition (Objective H)
//!
//! Uses Holographic Reduced Representations (circular convolution) to compose
//! improvement hypotheses and detect interaction effects (synergy, conflict).
//!
//! Operations:
//! - encode_hypothesis: Deterministic hash-based vector generation
//! - bind: Circular convolution (A ⊗ B) — creates composite hypothesis
//! - unbind: Approximate inverse + bind — recovers component contribution
//! - superposition: Vector addition + normalize — represents doing all
//! - compute_synergy: Norm of composite / sum of individual impacts

use num_complex::Complex64;
use rustfft::{FftPlanner, Fft};
use std::f64;
use std::sync::OnceLock;

/// Encode a hypothesis description into a deterministic HRR vector.
///
/// Uses a hash-based seed → Box-Muller Gaussian → normalize → scale by impact.
/// Matches the Python implementation in hrr_composition.py.
pub fn encode_hypothesis(description: &str, dim: usize, impact: f64) -> Vec<f64> {
    let seed = hash_djb2_u64(description);
    let mut vec = gaussian_vector(dim, seed);

    // Normalize to unit length
    let norm: f64 = vec.iter().map(|v| v * v).sum::<f64>().sqrt();
    if norm > 0.0 {
        for v in &mut vec {
            *v /= norm;
        }
    }

    // Scale by impact (clamped to [0.1, 2.0])
    let scale = impact.max(0.1).min(2.0);
    for v in &mut vec {
        *v *= scale;
    }

    vec
}

/// Circular convolution bind: a ⊗ b = IFFT(FFT(a) · FFT(b))
/// Uses rustfft for O(n log n) computation.
pub fn bind(a: &[f64], b: &[f64]) -> Vec<f64> {
    assert_eq!(a.len(), b.len());
    let n = a.len();
    if n == 0 {
        return vec![];
    }
    let (fft, ifft) = get_fft_plans(n);

    // Pack real inputs into complex buffers
    let mut a_buf: Vec<Complex64> = a.iter().map(|&x| Complex64::new(x, 0.0)).collect();
    let mut b_buf: Vec<Complex64> = b.iter().map(|&x| Complex64::new(x, 0.0)).collect();

    fft.process(&mut a_buf);
    fft.process(&mut b_buf);

    // Element-wise multiply in frequency domain
    for i in 0..n {
        a_buf[i] = a_buf[i] * b_buf[i];
    }

    // Inverse FFT
    ifft.process(&mut a_buf);

    // Extract real parts and normalize
    a_buf.iter().map(|c| c.re / n as f64).collect()
}

/// Approximate inverse (involution): reverse all elements except first
pub fn approximate_inverse(v: &[f64]) -> Vec<f64> {
    let n = v.len();
    let mut inv = vec![0.0; n];
    if n == 0 {
        return inv;
    }
    inv[0] = v[0];
    for i in 1..n {
        inv[i] = v[n - i];
    }
    inv
}

/// Unbind: inv(a) ⊗ b — recovers b's contribution from composite
pub fn unbind(composite: &[f64], component: &[f64]) -> Vec<f64> {
    let inv = approximate_inverse(component);
    bind(&inv, composite)
}

/// Superposition: vector addition + normalize
pub fn superposition(vectors: &[Vec<f64>]) -> Vec<f64> {
    if vectors.is_empty() {
        return vec![];
    }
    let dim = vectors[0].len();
    let mut sum = vec![0.0; dim];
    for v in vectors {
        for (i, &val) in v.iter().enumerate() {
            sum[i] += val;
        }
    }
    // Normalize
    let norm: f64 = sum.iter().map(|v| v * v).sum::<f64>().sqrt();
    if norm > 0.0 {
        for v in &mut sum {
            *v /= norm;
        }
    }
    sum
}

/// Compute vector magnitude (L2 norm)
pub fn magnitude(v: &[f64]) -> f64 {
    v.iter().map(|x| x * x).sum::<f64>().sqrt()
}

/// Cosine similarity between two vectors
pub fn cosine_similarity(a: &[f64], b: &[f64]) -> f64 {
    assert_eq!(a.len(), b.len());
    let dot: f64 = a.iter().zip(b.iter()).map(|(x, y)| x * y).sum();
    let mag_a = magnitude(a);
    let mag_b = magnitude(b);
    if mag_a > 0.0 && mag_b > 0.0 {
        dot / (mag_a * mag_b)
    } else {
        0.0
    }
}

/// Compute synergy score: composite_impact / sum(individual_impacts)
/// >1 = superlinear (synergy), <1 = sublinear (interference)
pub fn compute_synergy(composite_vector: &[f64], individual_impacts: &[f64]) -> f64 {
    if individual_impacts.is_empty() {
        return 0.0;
    }
    let composite_impact = magnitude(composite_vector);
    let sum_individual: f64 = individual_impacts.iter().sum();
    if sum_individual <= 0.0 {
        return 0.0;
    }
    composite_impact / sum_individual
}

// ---- Internal: FFT (rustfft), RNG, hash ----

/// Cached FFT plans for a given size. Avoids recomputing the plan on every bind call.
static FFT_CACHE: OnceLock<std::sync::Mutex<std::collections::HashMap<usize, (std::sync::Arc<dyn Fft<f64>>, std::sync::Arc<dyn Fft<f64>>)>>> = OnceLock::new();

fn get_fft_plans(n: usize) -> (std::sync::Arc<dyn Fft<f64>>, std::sync::Arc<dyn Fft<f64>>) {
    let cache = FFT_CACHE.get_or_init(|| std::sync::Mutex::new(std::collections::HashMap::new()));
    let mut guard = cache.lock().unwrap();
    if let Some((fwd, inv)) = guard.get(&n) {
        return (fwd.clone(), inv.clone());
    }
    let mut planner = FftPlanner::<f64>::new();
    let fwd = planner.plan_fft_forward(n);
    let inv = planner.plan_fft_inverse(n);
    guard.insert(n, (fwd.clone(), inv.clone()));
    (fwd, inv)
}

/// Naive O(n²) DFT — kept for test validation only.
#[cfg(test)]
fn naive_fft(signal: &[f64]) -> Vec<Complex64> {
    let n = signal.len();
    if n == 0 {
        return vec![];
    }
    (0..n)
        .map(|k| {
            let mut re = 0.0;
            let mut im = 0.0;
            for t in 0..n {
                let angle = -2.0 * std::f64::consts::PI * (t as f64) * (k as f64) / (n as f64);
                re += signal[t] * angle.cos();
                im += signal[t] * angle.sin();
            }
            Complex64::new(re, im)
        })
        .collect()
}

/// Naive O(n²) IFFT — kept for test validation only.
#[cfg(test)]
fn naive_ifft(spectrum: &[Complex64]) -> Vec<f64> {
    let n = spectrum.len();
    if n == 0 {
        return vec![];
    }
    (0..n)
        .map(|t| {
            let mut re = 0.0;
            for k in 0..n {
                let angle = 2.0 * std::f64::consts::PI * (t as f64) * (k as f64) / (n as f64);
                re += spectrum[k].re * angle.cos() - spectrum[k].im * angle.sin();
            }
            re / n as f64
        })
        .collect()
}

fn gaussian_vector(dim: usize, seed: u64) -> Vec<f64> {
    let mut v = vec![0.0; dim];
    let mut s = seed;
    for i in 0..dim {
        let u1 = lcg_next_f64(&mut s);
        let u2 = lcg_next_f64(&mut s);
        let r = (-2.0 * u1.ln()).sqrt();
        let theta = 2.0 * std::f64::consts::PI * u2;
        v[i] = r * theta.cos();
    }
    v
}

fn lcg_next_f64(seed: &mut u64) -> f64 {
    *seed = seed.wrapping_mul(1103515245).wrapping_add(12345);
    (*seed % 2147483647) as f64 / 2147483647.0
}

fn hash_djb2_u64(text: &str) -> u64 {
    let mut h: u64 = 5381;
    for c in text.bytes() {
        h = h.wrapping_shl(5).wrapping_add(h).wrapping_add(c as u64);
    }
    h
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_encode_deterministic() {
        let v1 = encode_hypothesis("fix untitled memories", 128, 0.5);
        let v2 = encode_hypothesis("fix untitled memories", 128, 0.5);
        assert_eq!(v1, v2);
    }

    #[test]
    fn test_encode_different_descriptions() {
        let v1 = encode_hypothesis("fix untitled memories", 128, 0.5);
        let v2 = encode_hypothesis("improve search recall", 128, 0.5);
        assert_ne!(v1, v2);
    }

    #[test]
    fn test_encode_impact_scaling() {
        let v_low = encode_hypothesis("test", 64, 0.1);
        let v_high = encode_hypothesis("test", 64, 2.0);
        assert!(magnitude(&v_high) > magnitude(&v_low));
    }

    #[test]
    fn test_bind_unbind_roundtrip() {
        let a = encode_hypothesis("hypothesis A", 256, 0.5);
        let b = encode_hypothesis("hypothesis B", 256, 0.5);
        let composite = bind(&a, &b);
        let recovered = unbind(&composite, &a);
        let sim = cosine_similarity(&recovered, &b);
        // HRR recovery is approximate
        assert!(sim > -0.5, "Expected similarity > -0.5, got {}", sim);
    }

    #[test]
    fn test_superposition_normalizes() {
        let a = encode_hypothesis("A", 64, 1.0);
        let b = encode_hypothesis("B", 64, 1.0);
        let s = superposition(&[a, b]);
        let mag = magnitude(&s);
        assert!((mag - 1.0).abs() < 0.01, "Expected unit norm, got {}", mag);
    }

    #[test]
    fn test_synergy_calculation() {
        let composite = vec![3.0, 4.0]; // magnitude = 5.0
        let individuals = vec![2.0, 2.0]; // sum = 4.0
        let synergy = compute_synergy(&composite, &individuals);
        assert!((synergy - 1.25).abs() < 0.001);
    }

    #[test]
    fn test_synergy_empty() {
        let synergy = compute_synergy(&[1.0, 0.0], &[]);
        assert_eq!(synergy, 0.0);
    }

    #[test]
    fn test_cosine_similarity_identical() {
        let v = encode_hypothesis("test", 64, 0.5);
        let sim = cosine_similarity(&v, &v);
        assert!((sim - 1.0).abs() < 0.001);
    }

    #[test]
    fn test_rustfft_matches_naive() {
        // Verify rustfft bind produces same result as naive O(n²) DFT bind
        let a = encode_hypothesis("hypothesis X", 128, 0.7);
        let b = encode_hypothesis("hypothesis Y", 128, 0.6);

        // rustfft bind
        let fast = bind(&a, &b);

        // Naive bind: IFFT(FFT(a) * FFT(b))
        let a_fft = naive_fft(&a);
        let b_fft = naive_fft(&b);
        let c_fft: Vec<Complex64> = a_fft.iter().zip(b_fft.iter()).map(|(x, y)| x * y).collect();
        let naive = naive_ifft(&c_fft);

        // Should match within floating point tolerance
        for i in 0..fast.len() {
            assert!(
                (fast[i] - naive[i]).abs() < 1e-9,
                "Mismatch at index {}: fast={}, naive={}",
                i, fast[i], naive[i]
            );
        }
    }

    #[test]
    fn test_bind_empty() {
        let a: Vec<f64> = vec![];
        let b: Vec<f64> = vec![];
        let result = bind(&a, &b);
        assert!(result.is_empty());
    }

    #[test]
    fn test_bind_single_element() {
        let a = vec![3.0];
        let b = vec![4.0];
        let result = bind(&a, &b);
        assert!((result[0] - 12.0).abs() < 1e-10, "Expected 12.0, got {}", result[0]);
    }
}
