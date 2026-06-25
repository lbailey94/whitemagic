//! Holographic Reduced Representations (Plate 1995)
//!
//! Vector-symbolic architecture using circular convolution for binding
//! and approximate inverse for unbinding. Vectors are typically
//! high-dimensional (e.g., 256–1024 dims) with elements sampled from
//! N(0, 1/dim) for unit expected magnitude.

use rustfft::{FftPlanner, num_complex::Complex as RustComplex};

/// An HRR vector — a high-dimensional symbolic representation.
#[derive(Debug, Clone, PartialEq)]
pub struct HRR {
    pub vec: Vec<f64>,
}

impl HRR {
    /// Create an HRR vector of given dimension, initialized with
    /// Gaussian noise scaled for unit expected magnitude.
    pub fn random(dim: usize, seed: u64) -> Self {
        let mut v = vec![0.0; dim];
        let mut s = seed;
        for i in 0..dim {
            // Box-Muller transform for two normal variates
            let u1 = lcg_next_f64(&mut s);
            let u2 = lcg_next_f64(&mut s);
            let r = (-2.0 * u1.ln()).sqrt();
            let theta = 2.0 * std::f64::consts::PI * u2;
            let z = r * theta.cos();
            v[i] = z / (dim as f64).sqrt();
        }
        Self { vec: v }
    }

    /// Encode a string into an HRR vector deterministically.
    pub fn encode(text: &str, dim: usize) -> Self {
        let mut base = Self::random(dim, hash_djb2_u64(text));
        // Modulate slightly by text properties for semantic variation
        let len_norm = text.len() as f64 / 1000.0;
        for v in &mut base.vec {
            *v *= 1.0 + len_norm * 0.01;
        }
        // Renormalize
        base.normalize();
        base
    }

    pub fn dim(&self) -> usize {
        self.vec.len()
    }

    pub fn normalize(&mut self) {
        let mag = self.magnitude();
        if mag > 0.0 {
            for v in &mut self.vec {
                *v /= mag;
            }
        }
    }

    pub fn magnitude(&self) -> f64 {
        self.vec.iter().map(|v| v * v).sum::<f64>().sqrt()
    }

    /// Circular convolution: a ⊗ b = DFT⁻¹(DFT(a) · DFT(b))
    /// This is the *binding* operation in HRR.
    /// Uses rustfft for O(N log N) computation.
    pub fn bind(&self, other: &Self) -> Self {
        let n = self.dim();
        assert_eq!(n, other.dim());

        let a_fft = fft_real(&self.vec);
        let b_fft = fft_real(&other.vec);
        let c_fft: Vec<RustComplex<f64>> = a_fft.iter().zip(b_fft.iter()).map(|(a, b)| a * b).collect();
        let c = ifft_real(&c_fft);

        Self { vec: c }
    }

    /// Approximate inverse (involution) for unbinding.
    /// inv(a) reverses all elements except the first.
    pub fn approximate_inverse(&self) -> Self {
        let mut inv = self.vec.clone();
        for i in 1..inv.len() {
            inv[i] = self.vec[self.dim() - i];
        }
        Self { vec: inv }
    }

    /// Unbind: a ⊗⁻¹ b ≈ inv(a) ⊗ b
    pub fn unbind(&self, other: &Self) -> Self {
        self.approximate_inverse().bind(other)
    }

    /// Cosine similarity between two HRR vectors.
    pub fn similarity(&self, other: &Self) -> f64 {
        let dot = self.vec.iter().zip(other.vec.iter()).map(|(a, b)| a * b).sum::<f64>();
        let mag_a = self.magnitude();
        let mag_b = other.magnitude();
        if mag_a > 0.0 && mag_b > 0.0 {
            dot / (mag_a * mag_b)
        } else {
            0.0
        }
    }

    /// Superposition (vector addition) of multiple HRRs.
    pub fn superpose(hrrs: &[Self]) -> Self {
        if hrrs.is_empty() {
            return Self { vec: vec![] };
        }
        let dim = hrrs[0].dim();
        let mut sum = vec![0.0; dim];
        for h in hrrs {
            for (i, v) in h.vec.iter().enumerate() {
                sum[i] += v;
            }
        }
        let n = hrrs.len() as f64;
        for v in &mut sum {
            *v /= n;
        }
        Self { vec: sum }
    }
}

// ---- FFT/IFFT using rustfft (O(N log N)) ----

fn fft_real(signal: &[f64]) -> Vec<RustComplex<f64>> {
    let n = signal.len();
    if n == 0 {
        return vec![];
    }
    let mut planner = FftPlanner::<f64>::new();
    let fft = planner.plan_fft_forward(n);
    let mut buffer: Vec<RustComplex<f64>> = signal.iter().map(|&v| RustComplex::new(v, 0.0)).collect();
    fft.process(&mut buffer);
    buffer
}

fn ifft_real(spectrum: &[RustComplex<f64>]) -> Vec<f64> {
    let n = spectrum.len();
    if n == 0 {
        return vec![];
    }
    let mut planner = FftPlanner::<f64>::new();
    let ifft = planner.plan_fft_inverse(n);
    let mut buffer = spectrum.to_vec();
    ifft.process(&mut buffer);
    buffer.iter().map(|c| c.re / n as f64).collect()
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
    fn test_hrr_roundtrip() {
        let a = HRR::random(256, 42);
        let b = HRR::random(256, 43);
        let c = a.bind(&b);
        // c ⊗ inv(a) ≈ b
        let recovered = c.unbind(&a);
        let sim = recovered.similarity(&b);
        // HRR binding is approximate; rustfft provides exact circular convolution.
        assert!(
            sim > 0.5,
            "Expected similarity > 0.5 (good recovery with rustfft), got {}",
            sim
        );
    }

    #[test]
    fn test_hrr_superpose() {
        let a = HRR::random(128, 1);
        let b = HRR::random(128, 2);
        let s = HRR::superpose(&[a.clone(), b.clone()]);
        assert_eq!(s.dim(), 128);
        assert!((s.magnitude() - 1.0).abs() < 0.5); // roughly normalized
    }

    #[test]
    fn test_similarity_range() {
        let a = HRR::random(64, 99);
        let b = HRR::random(64, 100);
        let sim = a.similarity(&b);
        assert!(sim >= -1.0 && sim <= 1.0);
    }

    #[test]
    fn test_encode_deterministic() {
        let h1 = HRR::encode("hello world", 128);
        let h2 = HRR::encode("hello world", 128);
        assert_eq!(h1.vec, h2.vec);
    }
}
