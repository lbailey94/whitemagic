//! Holographic Reduced Representations (HRR) - Core Engine
//!
//! WASM-compatible HRR using RustFFT for circular convolution binding.
//! No Python bindings here — those live in whitemagic-rust.
//!
//! HRR allows compositional memory retrieval:
//! - bind(A, B) = circular_convolution(A, B) - "A in the role of B"
//! - unbind(bound, B) = circular_correlation(bound, B) - recover A

#![allow(dead_code)]

use rustfft::{FftPlanner, num_complex::Complex};
use std::sync::Mutex;
use std::collections::HashMap;

/// HRR Engine with pre-computed relation vectors
pub struct HRREngine {
    pub dim: usize,
    relation_vectors: HashMap<String, Vec<f32>>,
    fft_planner: Mutex<FftPlanner<f32>>,
}

impl HRREngine {
    /// Create new HRR engine with specified dimension
    pub fn new(dim: usize) -> Self {
        let mut engine = Self {
            dim,
            relation_vectors: HashMap::new(),
            fft_planner: Mutex::new(FftPlanner::new()),
        };
        engine.init_relation_vectors();
        engine
    }

    /// Initialize canonical relation vectors (deterministic from seed)
    fn init_relation_vectors(&mut self) {
        use rand::{SeedableRng, rngs::StdRng};
        use rand_distr::{Distribution, StandardNormal};

        let relations = [
            "CAUSES", "CAUSED_BY",
            "FOLLOWS", "PRECEDED_BY",
            "PART_OF", "CONTAINS",
            "SIMILAR_TO", "OPPOSITE_OF",
            "EXTENDS", "EXTENDED_BY",
            "USES", "USED_BY",
            "CREATES", "CREATED_BY",
            "IMPLEMENTS", "IMPLEMENTED_BY",
            "AGENT", "ACTION", "OBJECT", "LOCATION", "TIME",
        ];

        let mut rng = StdRng::seed_from_u64(12345);
        let normal = StandardNormal;

        for rel in relations.iter() {
            let mut vec: Vec<f32> = Vec::with_capacity(self.dim);
            for _ in 0..self.dim {
                let val: f64 = normal.sample(&mut rng);
                vec.push(val as f32);
            }

            // Normalize to unit length
            let norm: f32 = vec.iter().map(|x| x * x).sum::<f32>().sqrt();
            if norm > 0.0 {
                for x in vec.iter_mut() {
                    *x /= norm;
                }
            }

            self.relation_vectors.insert(rel.to_string(), vec);
        }
    }

    /// Circular convolution: bind A to role B
    ///
    /// bind(A, B) = IFFT(FFT(A) * FFT(B))
    pub fn bind(&self, a: &[f32], b: &[f32]) -> Result<Vec<f32>, String> {
        if a.len() != self.dim || b.len() != self.dim {
            return Err(format!("Expected dim={}, got a={}, b={}", self.dim, a.len(), b.len()));
        }

        let mut a_complex: Vec<Complex<f32>> = a.iter().map(|&x| Complex::new(x, 0.0)).collect();
        let mut b_complex: Vec<Complex<f32>> = b.iter().map(|&x| Complex::new(x, 0.0)).collect();

        let mut planner = self.fft_planner.lock().unwrap_or_else(|e| e.into_inner());
        let fft = planner.plan_fft_forward(self.dim);

        fft.process(&mut a_complex);
        fft.process(&mut b_complex);

        let mut result_complex: Vec<Complex<f32>> = a_complex.iter()
            .zip(b_complex.iter())
            .map(|(a, b)| a * b)
            .collect();

        let ifft = planner.plan_fft_inverse(self.dim);
        ifft.process(&mut result_complex);

        let result: Vec<f32> = result_complex.iter()
            .map(|c| c.re / self.dim as f32)
            .collect();

        Ok(result)
    }

    /// Circular correlation: unbind B from bound vector
    ///
    /// unbind(bound, B) ~ A (approximate recovery)
    pub fn unbind(&self, bound: &[f32], b: &[f32]) -> Result<Vec<f32>, String> {
        if bound.len() != self.dim || b.len() != self.dim {
            return Err(format!("Expected dim={}, got bound={}, b={}", self.dim, bound.len(), b.len()));
        }

        let mut bound_complex: Vec<Complex<f32>> = bound.iter().map(|&x| Complex::new(x, 0.0)).collect();
        let mut b_complex: Vec<Complex<f32>> = b.iter().map(|&x| Complex::new(x, 0.0)).collect();

        let mut planner = self.fft_planner.lock().unwrap_or_else(|e| e.into_inner());
        let fft = planner.plan_fft_forward(self.dim);

        fft.process(&mut bound_complex);
        fft.process(&mut b_complex);

        let mut result_complex: Vec<Complex<f32>> = b_complex.iter()
            .zip(bound_complex.iter())
            .map(|(b, bound)| b.conj() * bound)
            .collect();

        let ifft = planner.plan_fft_inverse(self.dim);
        ifft.process(&mut result_complex);

        let result: Vec<f32> = result_complex.iter()
            .map(|c| c.re / self.dim as f32)
            .collect();

        Ok(result)
    }

    /// Superposition: element-wise sum of multiple vectors, normalized.
    pub fn superpose(&self, vectors: &[Vec<f32>]) -> Result<Vec<f32>, String> {
        if vectors.is_empty() {
            return Err("Need at least one vector for superposition".to_string());
        }

        for v in vectors {
            if v.len() != self.dim {
                return Err(format!("Expected dim={}, got {}", self.dim, v.len()));
            }
        }

        let mut result = vec![0.0f32; self.dim];
        for vec in vectors {
            for (i, &val) in vec.iter().enumerate() {
                result[i] += val;
            }
        }

        let norm: f32 = result.iter().map(|x| x * x).sum::<f32>().sqrt();
        if norm > 0.0 {
            for x in result.iter_mut() {
                *x /= norm;
            }
        }

        Ok(result)
    }

    /// Cosine similarity between two vectors
    pub fn similarity(&self, a: &[f32], b: &[f32]) -> Result<f32, String> {
        if a.len() != self.dim || b.len() != self.dim {
            return Err(format!("Expected dim={}, got a={}, b={}", self.dim, a.len(), b.len()));
        }

        let dot: f32 = a.iter().zip(b.iter()).map(|(x, y)| x * y).sum();
        let norm_a: f32 = a.iter().map(|x| x * x).sum::<f32>().sqrt();
        let norm_b: f32 = b.iter().map(|x| x * x).sum::<f32>().sqrt();

        if norm_a == 0.0 || norm_b == 0.0 {
            return Ok(0.0);
        }

        Ok(dot / (norm_a * norm_b))
    }

    /// Get or generate relation vector
    pub fn get_relation_vector(&mut self, relation: &str) -> Vec<f32> {
        let rel_upper = relation.to_uppercase();

        if let Some(vec) = self.relation_vectors.get(&rel_upper) {
            return vec.clone();
        }

        use std::collections::hash_map::DefaultHasher;
        use std::hash::{Hash, Hasher};
        use rand::{SeedableRng, rngs::StdRng};
        use rand_distr::{Distribution, StandardNormal};

        let mut hasher = DefaultHasher::new();
        rel_upper.hash(&mut hasher);
        let seed = hasher.finish();

        let mut rng = StdRng::seed_from_u64(seed);
        let normal = StandardNormal;

        let mut vec: Vec<f32> = Vec::with_capacity(self.dim);
        for _ in 0..self.dim {
            let val: f64 = normal.sample(&mut rng);
            vec.push(val as f32);
        }

        let norm: f32 = vec.iter().map(|x| x * x).sum::<f32>().sqrt();
        if norm > 0.0 {
            for x in vec.iter_mut() {
                *x /= norm;
            }
        }

        self.relation_vectors.insert(rel_upper.clone(), vec.clone());
        vec
    }

    /// Project embedding through a relation
    pub fn project(&mut self, embedding: &[f32], relation: &str) -> Result<Vec<f32>, String> {
        let rel_vec = self.get_relation_vector(relation);
        self.bind(embedding, &rel_vec)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_bind_unbind() {
        let engine = HRREngine::new(64);
        let a = vec![1.0; 64];
        let b = vec![0.5; 64];

        let bound = engine.bind(&a, &b).unwrap();
        assert_eq!(bound.len(), 64);

        let recovered = engine.unbind(&bound, &b).unwrap();
        assert_eq!(recovered.len(), 64);

        let sim = engine.similarity(&a, &recovered).unwrap();
        assert!(sim > 0.5, "Similarity {} too low", sim);
    }

    #[test]
    fn test_superpose() {
        let engine = HRREngine::new(64);
        let vecs = vec![
            vec![1.0; 64],
            vec![0.5; 64],
            vec![0.25; 64],
        ];

        let result = engine.superpose(&vecs).unwrap();
        assert_eq!(result.len(), 64);

        let norm: f32 = result.iter().map(|x| x * x).sum::<f32>().sqrt();
        assert!((norm - 1.0).abs() < 0.01, "Not normalized: {}", norm);
    }

    #[test]
    fn test_similarity_identical() {
        let engine = HRREngine::new(64);
        let a = vec![1.0; 64];
        let sim = engine.similarity(&a, &a).unwrap();
        assert!((sim - 1.0).abs() < 0.01);
    }

    #[test]
    fn test_project() {
        let mut engine = HRREngine::new(64);
        let emb = vec![0.5; 64];
        let projected = engine.project(&emb, "CAUSES").unwrap();
        assert_eq!(projected.len(), 64);
    }
}
