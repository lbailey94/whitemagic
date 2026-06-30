
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
        // SAFETY: AVX2 feature was detected at runtime.
        unsafe {
            batch_normalize_avx2(vectors, dim, num_vectors)
        }
    } else {
        // Fallback to scalar
        batch_normalize_scalar(vectors, dim, num_vectors)
    }
}

/// SAFETY: Caller must ensure AVX2 is available (e.g., via `is_x86_feature_detected!("avx2")`).
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
        // SAFETY: AVX2 feature was detected at runtime.
        unsafe {
            batch_cosine_avx2(query, matrix, dim, num_vectors, results)
        }
    } else {
        batch_cosine_scalar(query, matrix, dim, num_vectors, results)
    }
}

/// SAFETY: Caller must ensure AVX2 is available (e.g., via `is_x86_feature_detected!("avx2")`).
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

/// Batch circular convolution for HRR binding operations.
///
/// Binds N query vectors with a single relation vector using circular convolution.
/// This is the batched version of `circular_convolution` for GHRR attention.
///
/// # Arguments
/// * `queries` - N query vectors concatenated (N * dim floats, row-major)
/// * `relation` - Single relation vector (dim floats)
/// * `dim` - Dimension of each vector
/// * `n_vectors` - Number of query vectors
/// * `results` - Output buffer (N * dim floats)
///
/// # Returns
/// Number of vectors processed
#[inline]
pub fn batch_circular_convolution_simd(
    queries: &[f32],
    relation: &[f32],
    dim: usize,
    n_vectors: usize,
    results: &mut [f32],
) -> usize {
    if n_vectors == 0 || dim == 0 || queries.len() < n_vectors * dim || results.len() < n_vectors * dim {
        return 0;
    }

    // Circular convolution via direct computation (O(n²) per vector)
    // For production use, FFT would be preferred, but this provides
    // a SIMD-accelerated direct path that avoids FFT overhead for small dims.
    for i in 0..n_vectors {
        let q_offset = i * dim;
        let r_offset = 0;
        let out_offset = i * dim;

        if is_x86_feature_detected!("avx2") {
            unsafe {
                circular_conv_avx2(
                    &queries[q_offset..q_offset + dim],
                    &relation[r_offset..r_offset + dim],
                    dim,
                    &mut results[out_offset..out_offset + dim],
                );
            }
        } else {
            circular_conv_scalar(
                &queries[q_offset..q_offset + dim],
                &relation[r_offset..r_offset + dim],
                dim,
                &mut results[out_offset..out_offset + dim],
            );
        }
    }

    n_vectors
}

/// AVX2-accelerated circular convolution for a single pair
#[target_feature(enable = "avx2")]
unsafe fn circular_conv_avx2(a: &[f32], b: &[f32], dim: usize, out: &mut [f32]) {
    for k in 0..dim {
        let mut sum = _mm256_setzero_ps();
        let mut j = 0;

        while j + 8 <= dim {
            // a[j] * b[(k - j) mod dim]
            let a_vec = _mm256_loadu_ps(a.as_ptr().add(j));
            // Gather b indices (modular)
            let idx = [
                ((k as i64 - j as i64 + dim as i64) % dim as i64) as usize,
                ((k as i64 - (j + 1) as i64 + dim as i64) % dim as i64) as usize,
                ((k as i64 - (j + 2) as i64 + dim as i64) % dim as i64) as usize,
                ((k as i64 - (j + 3) as i64 + dim as i64) % dim as i64) as usize,
                ((k as i64 - (j + 4) as i64 + dim as i64) % dim as i64) as usize,
                ((k as i64 - (j + 5) as i64 + dim as i64) % dim as i64) as usize,
                ((k as i64 - (j + 6) as i64 + dim as i64) % dim as i64) as usize,
                ((k as i64 - (j + 7) as i64 + dim as i64) % dim as i64) as usize,
            ];
            let b_vals = [
                *b.get_unchecked(idx[0]),
                *b.get_unchecked(idx[1]),
                *b.get_unchecked(idx[2]),
                *b.get_unchecked(idx[3]),
                *b.get_unchecked(idx[4]),
                *b.get_unchecked(idx[5]),
                *b.get_unchecked(idx[6]),
                *b.get_unchecked(idx[7]),
            ];
            let b_vec = _mm256_loadu_ps(b_vals.as_ptr());
            let prod = _mm256_mul_ps(a_vec, b_vec);
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
            let b_idx = ((k as i64 - j as i64 + dim as i64) % dim as i64) as usize;
            dot += a[j] * *b.get_unchecked(b_idx);
            j += 1;
        }

        out[k] = dot;
    }
}

/// Scalar circular convolution for a single pair
fn circular_conv_scalar(a: &[f32], b: &[f32], dim: usize, out: &mut [f32]) {
    for k in 0..dim {
        let mut sum = 0.0f32;
        for j in 0..dim {
            let b_idx = (k as i64 - j as i64 + dim as i64) % dim as i64;
            sum += a[j] * b[b_idx as usize];
        }
        out[k] = sum;
    }
}

/// Batch Euclidean distance between a query vector and a matrix of vectors using SIMD.
///
/// # Arguments
/// * `query` - Query vector (dim floats)
/// * `matrix` - Matrix of vectors (row-major, num_vectors * dim floats)
/// * `dim` - Dimension of vectors
/// * `results` - Output buffer for distances (num_vectors floats)
///
/// # Returns
/// Number of distances computed
#[inline]
pub fn batch_euclidean_distance_simd(
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
            batch_euclidean_avx2(query, matrix, dim, num_vectors, results)
        }
    } else {
        batch_euclidean_scalar(query, matrix, dim, num_vectors, results)
    }
}

/// AVX2-accelerated batch Euclidean distance
#[target_feature(enable = "avx2")]
unsafe fn batch_euclidean_avx2(
    query: &[f32],
    matrix: &[f32],
    dim: usize,
    num_vectors: usize,
    results: &mut [f32],
) -> usize {
    for i in 0..num_vectors {
        let offset = i * dim;
        let vec = &matrix[offset..offset + dim];

        let mut sum = _mm256_setzero_ps();
        let mut j = 0;

        while j + 8 <= dim {
            let q = _mm256_loadu_ps(query.as_ptr().add(j));
            let v = _mm256_loadu_ps(vec.as_ptr().add(j));
            let diff = _mm256_sub_ps(q, v);
            let squared = _mm256_mul_ps(diff, diff);
            sum = _mm256_add_ps(sum, squared);
            j += 8;
        }

        let mut dist_sq = 0.0f32;
        let sum_array: [f32; 8] = std::mem::transmute(sum);
        for &val in &sum_array {
            dist_sq += val;
        }

        while j < dim {
            let d = query[j] - vec[j];
            dist_sq += d * d;
            j += 1;
        }

        results[i] = dist_sq.sqrt();
    }

    num_vectors
}

/// Scalar fallback for batch Euclidean distance
fn batch_euclidean_scalar(
    query: &[f32],
    matrix: &[f32],
    dim: usize,
    num_vectors: usize,
    results: &mut [f32],
) -> usize {
    for i in 0..num_vectors {
        let offset = i * dim;
        let vec = &matrix[offset..offset + dim];

        let dist_sq: f32 = query.iter()
            .zip(vec.iter())
            .map(|(&q, &v)| {
                let d = q - v;
                d * d
            })
            .sum();

        results[i] = dist_sq.sqrt();
    }

    num_vectors
}

/// Batch dot product between a query vector and a matrix of vectors using SIMD.
///
/// # Arguments
/// * `query` - Query vector (dim floats)
/// * `matrix` - Matrix of vectors (row-major, num_vectors * dim floats)
/// * `dim` - Dimension of vectors
/// * `results` - Output buffer for dot products (num_vectors floats)
///
/// # Returns
/// Number of dot products computed
#[inline]
pub fn batch_dot_product_simd(
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
            batch_dot_avx2(query, matrix, dim, num_vectors, results)
        }
    } else {
        batch_dot_scalar(query, matrix, dim, num_vectors, results)
    }
}

/// AVX2-accelerated batch dot product
#[target_feature(enable = "avx2")]
unsafe fn batch_dot_avx2(
    query: &[f32],
    matrix: &[f32],
    dim: usize,
    num_vectors: usize,
    results: &mut [f32],
) -> usize {
    for i in 0..num_vectors {
        let offset = i * dim;
        let vec = &matrix[offset..offset + dim];

        let mut sum = _mm256_setzero_ps();
        let mut j = 0;

        while j + 8 <= dim {
            let q = _mm256_loadu_ps(query.as_ptr().add(j));
            let v = _mm256_loadu_ps(vec.as_ptr().add(j));
            let prod = _mm256_mul_ps(q, v);
            sum = _mm256_add_ps(sum, prod);
            j += 8;
        }

        let mut dot = 0.0f32;
        let sum_array: [f32; 8] = std::mem::transmute(sum);
        for &val in &sum_array {
            dot += val;
        }

        while j < dim {
            dot += query[j] * vec[j];
            j += 1;
        }

        results[i] = dot;
    }

    num_vectors
}

/// Scalar fallback for batch dot product
fn batch_dot_scalar(
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

/// Batch top-k selection: find k vectors with highest cosine similarity to query.
///
/// Uses a simple partial selection sort approach. For large k, a heap would
/// be more efficient, but for typical k < 100 this is faster due to cache locality.
///
/// # Arguments
/// * `query` - Query vector (dim floats, should be normalized)
/// * `matrix` - Matrix of vectors (row-major, num_vectors * dim floats, should be normalized)
/// * `dim` - Dimension of vectors
/// * `num_vectors` - Number of vectors in matrix
/// * `k` - Number of top results to return
/// * `out_indices` - Output buffer for indices (k ints)
/// * `out_scores` - Output buffer for scores (k floats)
///
/// # Returns
/// Number of results written (min(k, num_vectors))
#[inline]
pub fn batch_topk_simd(
    query: &[f32],
    matrix: &[f32],
    dim: usize,
    num_vectors: usize,
    k: usize,
    out_indices: &mut [usize],
    out_scores: &mut [f32],
) -> usize {
    if num_vectors == 0 || dim == 0 || query.len() != dim || k == 0 {
        return 0;
    }

    let actual_k = k.min(num_vectors);

    // Compute all cosine similarities
    let mut scores = vec![0.0f32; num_vectors];
    batch_cosine_similarity_simd(query, matrix, dim, &mut scores);

    // Partial selection sort for top-k
    let mut indices: Vec<usize> = (0..num_vectors).collect();

    for i in 0..actual_k {
        let mut best_idx = i;
        let mut best_score = scores[indices[i]];

        for j in (i + 1)..num_vectors {
            let score = scores[indices[j]];
            if score > best_score {
                best_score = score;
                best_idx = j;
            }
        }

        indices.swap(i, best_idx);
        out_indices[i] = indices[i];
        out_scores[i] = best_score;
    }

    actual_k
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

    #[test]
    fn test_batch_circular_convolution() {
        // Test with known vectors: bind([1,0,0], [0,1,0]) = [0,1,0] (shifted)
        let queries = vec![
            1.0, 0.0, 0.0,
            0.0, 1.0, 0.0,
        ];
        let relation = vec![0.0, 1.0, 0.0];
        let mut results = vec![0.0; 6];

        let count = batch_circular_convolution_simd(&queries, &relation, 3, 2, &mut results);
        assert_eq!(count, 2);

        // bind([1,0,0], [0,1,0]) = [0,0,0] shifted → circular conv gives [0, 0, 0]
        // Actually: out[k] = sum_j a[j] * b[(k-j) mod dim]
        // out[0] = a[0]*b[0] + a[1]*b[2] + a[2]*b[1] = 1*0 + 0*0 + 0*1 = 0
        // out[1] = a[0]*b[1] + a[1]*b[0] + a[2]*b[2] = 1*1 + 0*0 + 0*0 = 1
        // out[2] = a[0]*b[2] + a[1]*b[1] + a[2]*b[0] = 1*0 + 0*1 + 0*0 = 0
        assert!((results[0] - 0.0).abs() < 1e-5);
        assert!((results[1] - 1.0).abs() < 1e-5);
        assert!((results[2] - 0.0).abs() < 1e-5);

        // bind([0,1,0], [0,1,0]) = [0,0,1] (double shift)
        // out[0] = 0*0 + 1*0 + 0*1 = 0
        // out[1] = 0*1 + 1*0 + 0*0 = 0
        // out[2] = 0*0 + 1*1 + 0*0 = 1
        assert!((results[3] - 0.0).abs() < 1e-5);
        assert!((results[4] - 0.0).abs() < 1e-5);
        assert!((results[5] - 1.0).abs() < 1e-5);
    }

    #[test]
    fn test_batch_euclidean_distance() {
        let query = vec![0.0, 0.0, 0.0];
        let matrix = vec![
            3.0, 4.0, 0.0,  // dist = 5.0
            0.0, 0.0, 0.0,  // dist = 0.0
            1.0, 0.0, 0.0,  // dist = 1.0
        ];
        let mut results = vec![0.0; 3];

        let count = batch_euclidean_distance_simd(&query, &matrix, 3, &mut results);
        assert_eq!(count, 3);

        assert!((results[0] - 5.0).abs() < 1e-5);
        assert!((results[1] - 0.0).abs() < 1e-5);
        assert!((results[2] - 1.0).abs() < 1e-5);
    }

    #[test]
    fn test_batch_dot_product() {
        let query = vec![1.0, 2.0, 3.0];
        let matrix = vec![
            1.0, 0.0, 0.0,  // dot = 1.0
            0.0, 1.0, 0.0,  // dot = 2.0
            1.0, 1.0, 1.0,  // dot = 6.0
        ];
        let mut results = vec![0.0; 3];

        let count = batch_dot_product_simd(&query, &matrix, 3, &mut results);
        assert_eq!(count, 3);

        assert!((results[0] - 1.0).abs() < 1e-5);
        assert!((results[1] - 2.0).abs() < 1e-5);
        assert!((results[2] - 6.0).abs() < 1e-5);
    }

    #[test]
    fn test_batch_topk() {
        let query = vec![1.0, 0.0, 0.0];
        let matrix = vec![
            0.0, 1.0, 0.0,  // cosine = 0.0
            1.0, 0.0, 0.0,  // cosine = 1.0
            0.5, 0.5, 0.0,  // cosine = 0.5
            0.0, 0.0, 1.0,  // cosine = 0.0
        ];
        let mut indices = vec![0usize; 2];
        let mut scores = vec![0.0f32; 2];

        let count = batch_topk_simd(&query, &matrix, 3, 4, 2, &mut indices, &mut scores);
        assert_eq!(count, 2);

        // Top result should be index 1 (cosine = 1.0)
        assert_eq!(indices[0], 1);
        assert!((scores[0] - 1.0).abs() < 1e-5);

        // Second result should be index 2 (cosine = 0.5)
        assert_eq!(indices[1], 2);
        assert!((scores[1] - 0.5).abs() < 1e-5);
    }

    #[test]
    fn test_batch_euclidean_empty() {
        let query: Vec<f32> = vec![];
        let matrix: Vec<f32> = vec![];
        let mut results: Vec<f32> = vec![];

        let count = batch_euclidean_distance_simd(&query, &matrix, 0, &mut results);
        assert_eq!(count, 0);
    }

    #[test]
    fn test_batch_dot_product_mismatched_dim() {
        let query = vec![1.0, 0.0];
        let matrix = vec![1.0, 0.0, 0.0];  // dim=3 but query is dim=2
        let mut results = vec![0.0; 1];

        let count = batch_dot_product_simd(&query, &matrix, 3, &mut results);
        assert_eq!(count, 0);
    }
}
