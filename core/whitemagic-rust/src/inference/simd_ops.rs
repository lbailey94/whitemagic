//! SIMD-accelerated vector operations with FMA + cache tiling.
//!
//! Optimized for Kaby Lake (AVX2 + FMA, 32KB L1d, 256KB L2).
//!
//! Key improvements over previous code:
//! - FMA (`_mm256_fmadd_ps`) fuses multiply+add into one instruction (~1.5-2x on dot products)
//! - Proper horizontal sum via `_mm256_extractf128_ps` + `_mm_hadd_ps` (no scalar loop)
//! - L1 cache tiling: process blocks of TILE_SIZE vectors to keep working set in L1d
//! - FFT-based circular convolution for dim > 64 (O(n log n) vs O(n²))

use std::arch::x86_64::*;
use rustfft::{FftPlanner, num_complex::Complex};

/// Number of vectors per L1 cache tile.
/// 32KB L1d / (dim * 4 bytes) = 32KB / (384 * 4) = ~20 vectors.
/// Use 16 to stay safely within L1 with query vector + tile.
const L1_TILE_SIZE: usize = 16;

/// Fast horizontal sum of a __m256 to a single f32.
/// Uses extract128 + hadd instead of scalar loop.
/// SAFETY: Caller must ensure AVX is available.
#[inline(always)]
unsafe fn hsum256_ps(v: __m256) -> f32 {
    let hi128 = _mm256_extractf128_ps(v, 1);  // [4,5,6,7]
    let lo128 = _mm256_castps256_ps128(v);     // [0,1,2,3]
    let sum128 = _mm_add_ps(hi128, lo128);     // [0+4, 1+5, 2+6, 3+7]
    let shuf = _mm_movehdup_ps(sum128);        // [1+5, 1+5, 3+7, 3+7]
    let sums = _mm_add_ps(sum128, shuf);       // [0+4+1+5, _, 2+6+3+7, _]
    let shuf2 = _mm_movehl_ps(sums, sums);     // [2+6+3+7, _, _, _]
    let result = _mm_add_ss(sums, shuf2);      // [0+4+1+5+2+6+3+7, _, _, _]
    _mm_cvtss_f32(result)
}

/// Batch cosine similarity between query and matrix using AVX2+FMA.
///
/// # Arguments
/// * `query` - Query vector (normalized, dim floats)
/// * `matrix` - Matrix of vectors (row-major, num_vectors * dim floats, normalized)
/// * `dim` - Dimension of vectors
/// * `results` - Output buffer for similarities (num_vectors floats)
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

    if is_x86_feature_detected!("avx2") && is_x86_feature_detected!("fma") {
        unsafe { batch_cosine_fma_tiled(query, matrix, dim, num_vectors, results) }
    } else if is_x86_feature_detected!("avx2") {
        unsafe { batch_cosine_avx2(query, matrix, dim, num_vectors, results) }
    } else {
        batch_cosine_scalar(query, matrix, dim, num_vectors, results)
    }
}

/// AVX2+FMA accelerated batch cosine similarity with L1 cache tiling.
#[target_feature(enable = "avx2,fma")]
unsafe fn batch_cosine_fma_tiled(
    query: &[f32],
    matrix: &[f32],
    dim: usize,
    num_vectors: usize,
    results: &mut [f32],
) -> usize {
    // Process vectors in L1-sized tiles to keep working set in cache.
    // Each tile: TILE_SIZE vectors × dim floats × 4 bytes = e.g. 16×384×4 = 24KB (fits L1d)
    let tile_size = L1_TILE_SIZE.min(num_vectors);
    let mut i = 0;

    while i < num_vectors {
        let tile_end = (i + tile_size).min(num_vectors);
        let tile_count = tile_end - i;

        // Process the tile
        for ti in 0..tile_count {
            let vec_idx = i + ti;
            let offset = vec_idx * dim;
            let vec = &matrix[offset..offset + dim];

            let mut sum = _mm256_setzero_ps();
            let mut j = 0;

            // FMA: sum += query[j] * vec[j] in a single instruction
            while j + 8 <= dim {
                let q = _mm256_loadu_ps(query.as_ptr().add(j));
                let v = _mm256_loadu_ps(vec.as_ptr().add(j));
                sum = _mm256_fmadd_ps(q, v, sum);
                j += 8;
            }

            // Horizontal sum (no scalar loop)
            let mut dot = hsum256_ps(sum);

            // Handle remaining elements
            while j < dim {
                dot += *query.get_unchecked(j) * *vec.get_unchecked(j);
                j += 1;
            }

            results[vec_idx] = dot;
        }

        i += tile_count;
    }

    num_vectors
}

/// AVX2-only fallback (no FMA) — still has proper horizontal sum.
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

        let mut sum = _mm256_setzero_ps();
        let mut j = 0;

        while j + 8 <= dim {
            let q = _mm256_loadu_ps(query.as_ptr().add(j));
            let v = _mm256_loadu_ps(vec.as_ptr().add(j));
            sum = _mm256_add_ps(sum, _mm256_mul_ps(q, v));
            j += 8;
        }

        let mut dot = hsum256_ps(sum);

        while j < dim {
            dot += *query.get_unchecked(j) * *vec.get_unchecked(j);
            j += 1;
        }

        results[i] = dot;
    }

    num_vectors
}

/// Scalar fallback
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
        let dot: f32 = query.iter().zip(vec.iter()).map(|(&q, &v)| q * v).sum();
        results[i] = dot;
    }
    num_vectors
}

/// Batch dot product with AVX2+FMA.
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

    if is_x86_feature_detected!("avx2") && is_x86_feature_detected!("fma") {
        unsafe { batch_dot_fma(query, matrix, dim, num_vectors, results) }
    } else {
        batch_dot_scalar(query, matrix, dim, num_vectors, results)
    }
}

#[target_feature(enable = "avx2,fma")]
unsafe fn batch_dot_fma(
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
            sum = _mm256_fmadd_ps(q, v, sum);
            j += 8;
        }

        let mut dot = hsum256_ps(sum);

        while j < dim {
            dot += *query.get_unchecked(j) * *vec.get_unchecked(j);
            j += 1;
        }

        results[i] = dot;
    }

    num_vectors
}

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
        results[i] = query.iter().zip(vec.iter()).map(|(&q, &v)| q * v).sum();
    }
    num_vectors
}

/// Batch Euclidean distance with AVX2+FMA.
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

    if is_x86_feature_detected!("avx2") && is_x86_feature_detected!("fma") {
        unsafe { batch_euclidean_fma(query, matrix, dim, num_vectors, results) }
    } else {
        batch_euclidean_scalar(query, matrix, dim, num_vectors, results)
    }
}

#[target_feature(enable = "avx2,fma")]
unsafe fn batch_euclidean_fma(
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
            sum = _mm256_fmadd_ps(diff, diff, sum);
            j += 8;
        }

        let mut dist_sq = hsum256_ps(sum);

        while j < dim {
            let d = *query.get_unchecked(j) - *vec.get_unchecked(j);
            dist_sq += d * d;
            j += 1;
        }

        results[i] = dist_sq.sqrt();
    }

    num_vectors
}

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
        let dist_sq: f32 = query
            .iter()
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

/// Batch circular convolution using FFT (O(n log n) per vector).
///
/// For dim=384: FFT = 384×9 ≈ 3,456 ops vs direct = 384² = 147,456 ops.
/// That's a 42x algorithmic reduction.
///
/// Falls back to direct SIMD for dim < 64 (FFT overhead not worth it).
#[inline]
pub fn batch_circular_convolution_fft(
    queries: &[f32],
    relation: &[f32],
    dim: usize,
    n_vectors: usize,
    results: &mut [f32],
) -> usize {
    if n_vectors == 0 || dim == 0 || queries.len() < n_vectors * dim || results.len() < n_vectors * dim {
        return 0;
    }

    if dim < 64 {
        // For small dims, direct SIMD is faster (no FFT planning overhead)
        return batch_circular_convolution_direct(queries, relation, dim, n_vectors, results);
    }

    // FFT path: O(n log n) per vector
    let mut planner = FftPlanner::<f32>::new();
    let fft = planner.plan_fft_forward(dim);
    let ifft = planner.plan_fft_inverse(dim);

    // Pre-compute FFT of relation (done once, reused for all queries)
    let mut rel_fft: Vec<Complex<f32>> = relation.iter().map(|&x| Complex::new(x, 0.0)).collect();
    fft.process(&mut rel_fft);

    let inv_dim = 1.0 / dim as f32;

    for i in 0..n_vectors {
        let q_offset = i * dim;
        let out_offset = i * dim;

        // FFT of query
        let mut q_fft: Vec<Complex<f32>> = queries[q_offset..q_offset + dim]
            .iter()
            .map(|&x| Complex::new(x, 0.0))
            .collect();
        fft.process(&mut q_fft);

        // Element-wise multiply: query_fft * relation_fft
        let mut result_fft: Vec<Complex<f32>> = q_fft
            .iter()
            .zip(rel_fft.iter())
            .map(|(q, r)| q * r)
            .collect();

        // Inverse FFT
        ifft.process(&mut result_fft);

        // Extract real part (imaginary should be ~0 for real input)
        for k in 0..dim {
            results[out_offset + k] = result_fft[k].re * inv_dim;
        }
    }

    n_vectors
}

/// Direct SIMD circular convolution for small dims (< 64).
#[target_feature(enable = "avx2")]
unsafe fn circular_conv_avx2_direct(a: &[f32], b: &[f32], dim: usize, out: &mut [f32]) {
    for k in 0..dim {
        let mut sum = _mm256_setzero_ps();
        let mut j = 0;

        while j + 8 <= dim {
            let a_vec = _mm256_loadu_ps(a.as_ptr().add(j));
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
            sum = _mm256_fmadd_ps(a_vec, b_vec, sum);
            j += 8;
        }

        let mut dot = hsum256_ps(sum);

        while j < dim {
            let b_idx = ((k as i64 - j as i64 + dim as i64) % dim as i64) as usize;
            dot += a[j] * *b.get_unchecked(b_idx);
            j += 1;
        }

        out[k] = dot;
    }
}

fn batch_circular_convolution_direct(
    queries: &[f32],
    relation: &[f32],
    dim: usize,
    n_vectors: usize,
    results: &mut [f32],
) -> usize {
    for i in 0..n_vectors {
        let q_offset = i * dim;
        let out_offset = i * dim;

        if is_x86_feature_detected!("avx2") && is_x86_feature_detected!("fma") {
            unsafe {
                circular_conv_avx2_direct(
                    &queries[q_offset..q_offset + dim],
                    &relation[..dim],
                    dim,
                    &mut results[out_offset..out_offset + dim],
                );
            }
        } else {
            // Scalar fallback
            for k in 0..dim {
                let mut sum = 0.0f32;
                for j in 0..dim {
                    let b_idx = (k as i64 - j as i64 + dim as i64) % dim as i64;
                    sum += queries[q_offset + j] * relation[b_idx as usize];
                }
                results[out_offset + k] = sum;
            }
        }
    }

    n_vectors
}

/// Batch top-k selection with cosine similarity.
/// Uses a partial selection sort — efficient for k < 100.
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

    let mut scores = vec![0.0f32; num_vectors];
    batch_cosine_similarity_simd(query, matrix, dim, &mut scores);

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
    fn test_batch_cosine_fma() {
        let query = vec![1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0];
        let matrix = vec![
            1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, // dot = 1.0
            0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, // dot = 0.0
            0.5, 0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, // dot = 0.5
        ];
        let mut results = vec![0.0; 3];

        let count = batch_cosine_similarity_simd(&query, &matrix, 8, &mut results);
        assert_eq!(count, 3);
        assert!((results[0] - 1.0).abs() < 1e-5);
        assert!((results[1] - 0.0).abs() < 1e-5);
        assert!((results[2] - 0.5).abs() < 1e-5);
    }

    #[test]
    fn test_batch_cosine_384dim() {
        // Test with realistic embedding dimension
        let mut query = vec![0.0f32; 384];
        query[0] = 1.0;
        let mut matrix = vec![0.0f32; 384 * 3];
        // Vector 0: identical to query → dot = 1.0
        matrix[0] = 1.0;
        // Vector 1: orthogonal → dot = 0.0
        matrix[384 + 1] = 1.0;
        // Vector 2: 45 degrees → dot = 0.5
        matrix[768 + 0] = 0.5;
        matrix[768 + 1] = 0.5;

        let mut results = vec![0.0; 3];
        let count = batch_cosine_similarity_simd(&query, &matrix, 384, &mut results);
        assert_eq!(count, 3);
        assert!((results[0] - 1.0).abs() < 1e-4);
        assert!((results[1] - 0.0).abs() < 1e-4);
        assert!((results[2] - 0.5).abs() < 1e-4);
    }

    #[test]
    fn test_batch_dot_fma() {
        let query = vec![1.0, 2.0, 3.0, 0.0, 0.0, 0.0, 0.0, 0.0];
        let matrix = vec![
            1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, // dot = 1.0
            0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, // dot = 2.0
            1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, // dot = 6.0
        ];
        let mut results = vec![0.0; 3];

        let count = batch_dot_product_simd(&query, &matrix, 8, &mut results);
        assert_eq!(count, 3);
        assert!((results[0] - 1.0).abs() < 1e-5, "results[0]={} expected 1.0", results[0]);
        assert!((results[1] - 2.0).abs() < 1e-5, "results[1]={} expected 2.0", results[1]);
        assert!((results[2] - 6.0).abs() < 1e-5, "results[2]={} expected 6.0", results[2]);
    }

    #[test]
    fn test_batch_euclidean_fma() {
        let query = vec![0.0; 8];
        let matrix = vec![
            3.0, 4.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, // dist = 5.0
            0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, // dist = 0.0
            1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, // dist = 1.0
        ];
        let mut results = vec![0.0; 3];

        let count = batch_euclidean_distance_simd(&query, &matrix, 8, &mut results);
        assert_eq!(count, 3);
        assert!((results[0] - 5.0).abs() < 1e-4);
        assert!((results[1] - 0.0).abs() < 1e-4);
        assert!((results[2] - 1.0).abs() < 1e-4);
    }

    #[test]
    fn test_circular_convolution_fft() {
        // Test with dim=128 (above FFT threshold of 64)
        let dim = 128;
        let queries = vec![0.0f32; dim];
        let relation = vec![0.0f32; dim];
        let mut results = vec![0.0f32; dim];

        // Simple test: bind([1,0,0,...], [0,1,0,...]) should give [0,1,0,...] (shifted)
        let mut q = vec![0.0f32; dim];
        q[0] = 1.0;
        let mut r = vec![0.0f32; dim];
        r[1] = 1.0;
        let mut out = vec![0.0f32; dim];

        let count = batch_circular_convolution_fft(&q, &r, dim, 1, &mut out);
        assert_eq!(count, 1);

        // out[1] should be 1.0 (circular conv of delta at 0 with delta at 1)
        assert!((out[1] - 1.0).abs() < 1e-4, "Expected out[1]≈1.0, got {}", out[1]);
        // All other elements should be ~0
        for k in 0..dim {
            if k != 1 {
                assert!(out[k].abs() < 1e-4, "Expected out[{}]≈0, got {}", k, out[k]);
            }
        }
    }

    #[test]
    fn test_circular_convolution_fft_batch() {
        let dim = 256;
        let n = 4;
        let mut queries = vec![0.0f32; dim * n];
        let mut relation = vec![0.0f32; dim];

        // Set up: each query is a delta at different positions
        for i in 0..n {
            queries[i * dim + i] = 1.0;
        }
        relation[0] = 1.0; // identity relation → output should equal input

        let mut results = vec![0.0f32; dim * n];
        let count = batch_circular_convolution_fft(&queries, &relation, dim, n, &mut results);
        assert_eq!(count, n);

        // With identity relation (delta at 0), output should equal input
        for i in 0..n {
            let val = results[i * dim + i];
            assert!((val - 1.0).abs() < 1e-4, "Vector {}: expected {}=1.0, got {}", i, i, val);
        }
    }

    #[test]
    fn test_topk() {
        let query = vec![1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0];
        let matrix = vec![
            0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, // cosine = 0.0
            1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, // cosine = 1.0
            0.5, 0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, // cosine = 0.5
            0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, // cosine = 0.0
        ];
        let mut indices = vec![0usize; 2];
        let mut scores = vec![0.0f32; 2];

        let count = batch_topk_simd(&query, &matrix, 8, 4, 2, &mut indices, &mut scores);
        assert_eq!(count, 2);
        assert_eq!(indices[0], 1);
        assert!((scores[0] - 1.0).abs() < 1e-5);
        assert_eq!(indices[1], 2);
        assert!((scores[1] - 0.5).abs() < 1e-5);
    }
}
