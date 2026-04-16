// Embedding SIMD Acceleration - Phase 3
// ======================================
// Rust SIMD operations for embedding hot paths:
// - Batch vector normalization
// - Batch cosine similarity
// - Vector operations with AVX2/NEON

use std::arch::x86_64::*;

/// Normalize a batch of vectors in-place using SIMD
/// 
/// # Safety
/// Requires AVX2 support. Falls back to scalar if unavailable.
#[inline]
pub fn batch_normalize_vectors_simd(vectors: &mut [f32], dim: usize) -> usize {
    let num_vectors = vectors.len() / dim;
    
    if num_vectors == 0 || dim == 0 {
        return 0;
    }
    
    // Check for AVX2 support
    if is_x86_feature_detected!("avx2") {
        unsafe {
            batch_normalize_avx2(vectors, dim, num_vectors)
        }
    } else {
        // Fallback to scalar
        batch_normalize_scalar(vectors, dim, num_vectors)
    }
}

/// AVX2-accelerated batch normalization
#[target_feature(enable = "avx2")]
unsafe fn batch_normalize_avx2(vectors: &mut [f32], dim: usize, num_vectors: usize) -> usize {
    for i in 0..num_vectors {
        let offset = i * dim;
        let vec = &mut vectors[offset..offset + dim];
        
        // Compute norm using AVX2
        let mut sum = _mm256_setzero_ps();
        let mut j = 0;
        
        // Process 8 floats at a time
        while j + 8 <= dim {
            let v = _mm256_loadu_ps(vec.as_ptr().add(j));
            let squared = _mm256_mul_ps(v, v);
            sum = _mm256_add_ps(sum, squared);
            j += 8;
        }
        
        // Horizontal sum
        let mut norm_squared = 0.0f32;
        let sum_array: [f32; 8] = std::mem::transmute(sum);
        for &val in &sum_array {
            norm_squared += val;
        }
        
        // Handle remaining elements
        while j < dim {
            norm_squared += vec[j] * vec[j];
            j += 1;
        }
        
        // Normalize
        let norm = norm_squared.sqrt();
        if norm > 1e-8 {
            let inv_norm = 1.0 / norm;
            
            // Normalize using AVX2
            let inv_norm_vec = _mm256_set1_ps(inv_norm);
            j = 0;
            
            while j + 8 <= dim {
                let v = _mm256_loadu_ps(vec.as_ptr().add(j));
                let normalized = _mm256_mul_ps(v, inv_norm_vec);
                _mm256_storeu_ps(vec.as_mut_ptr().add(j), normalized);
                j += 8;
            }
            
            // Handle remaining
            while j < dim {
                vec[j] *= inv_norm;
                j += 1;
            }
        }
    }
    
    num_vectors
}

/// Scalar fallback for batch normalization
fn batch_normalize_scalar(vectors: &mut [f32], dim: usize, num_vectors: usize) -> usize {
    for i in 0..num_vectors {
        let offset = i * dim;
        let vec = &mut vectors[offset..offset + dim];
        
        // Compute norm
        let norm_squared: f32 = vec.iter().map(|&x| x * x).sum();
        let norm = norm_squared.sqrt();
        
        // Normalize
        if norm > 1e-8 {
            let inv_norm = 1.0 / norm;
            for val in vec.iter_mut() {
                *val *= inv_norm;
            }
        }
    }
    
    num_vectors
}

/// Batch cosine similarity between query and matrix using SIMD
/// 
/// # Arguments
/// * `query` - Query vector (normalized)
/// * `matrix` - Matrix of vectors (row-major, normalized)
/// * `dim` - Dimension of vectors
/// * `results` - Output buffer for similarities
/// 
/// # Returns
/// Number of similarities computed
#[inline]
pub fn batch_cosine_similarity_simd(
    query: &[f32],
    matrix: &[f32],
    dim: usize,
    results: &mut [f32],
) -> usize {
    let num_vectors = matrix.len() / dim;
    
    if num_vectors == 0 || dim == 0 || query.len() != dim {
        return 0;
    }
    
    if is_x86_feature_detected!("avx2") {
        unsafe {
            batch_cosine_avx2(query, matrix, dim, num_vectors, results)
        }
    } else {
        batch_cosine_scalar(query, matrix, dim, num_vectors, results)
    }
}

/// AVX2-accelerated batch cosine similarity
#[target_feature(enable = "avx2")]
unsafe fn batch_cosine_avx2(
    query: &[f32],
    matrix: &[f32],
    dim: usize,
    num_vectors: usize,
    results: &mut [f32],
) -> usize {
    for i in 0..num_vectors {
        let offset = i * dim;
        let vec = &matrix[offset..offset + dim];
        
        // Dot product using AVX2
        let mut sum = _mm256_setzero_ps();
        let mut j = 0;
        
        while j + 8 <= dim {
            let q = _mm256_loadu_ps(query.as_ptr().add(j));
            let v = _mm256_loadu_ps(vec.as_ptr().add(j));
            let prod = _mm256_mul_ps(q, v);
            sum = _mm256_add_ps(sum, prod);
            j += 8;
        }
        
        // Horizontal sum
        let mut dot = 0.0f32;
        let sum_array: [f32; 8] = std::mem::transmute(sum);
        for &val in &sum_array {
            dot += val;
        }
        
        // Handle remaining
        while j < dim {
            dot += query[j] * vec[j];
            j += 1;
        }
        
        results[i] = dot;
    }
    
    num_vectors
}

/// Scalar fallback for batch cosine similarity
fn batch_cosine_scalar(
    query: &[f32],
    matrix: &[f32],
    dim: usize,
    num_vectors: usize,
    results: &mut [f32],
) -> usize {
    for i in 0..num_vectors {
        let offset = i * dim;
        let vec = &matrix[offset..offset + dim];
        
        let dot: f32 = query.iter()
            .zip(vec.iter())
            .map(|(&q, &v)| q * v)
            .sum();
        
        results[i] = dot;
    }
    
    num_vectors
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_batch_normalize() {
        let mut vectors = vec![
            3.0, 4.0, 0.0,  // norm = 5
            1.0, 0.0, 0.0,  // norm = 1
        ];
        
        let count = batch_normalize_vectors_simd(&mut vectors, 3);
        assert_eq!(count, 2);
        
        // Check first vector normalized to unit length
        let norm1 = (vectors[0] * vectors[0] + vectors[1] * vectors[1] + vectors[2] * vectors[2]).sqrt();
        assert!((norm1 - 1.0).abs() < 1e-6);
        
        // Check second vector normalized to unit length
        let norm2 = (vectors[3] * vectors[3] + vectors[4] * vectors[4] + vectors[5] * vectors[5]).sqrt();
        assert!((norm2 - 1.0).abs() < 1e-6);
    }
    
    #[test]
    fn test_batch_cosine() {
        let query = vec![1.0, 0.0, 0.0];
        let matrix = vec![
            1.0, 0.0, 0.0,  // dot = 1.0
            0.0, 1.0, 0.0,  // dot = 0.0
            0.5, 0.5, 0.0,  // dot = 0.5
        ];
        let mut results = vec![0.0; 3];
        
        let count = batch_cosine_similarity_simd(&query, &matrix, 3, &mut results);
        assert_eq!(count, 3);
        
        assert!((results[0] - 1.0).abs() < 1e-6);
        assert!((results[1] - 0.0).abs() < 1e-6);
        assert!((results[2] - 0.5).abs() < 1e-6);
    }
}
