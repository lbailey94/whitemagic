// Zig SIMD Hot Path Translations
// Phase B: 8 vector-optimized functions

const std = @import("std");
const simd = @import("std").simd;

/// SIMD batch cosine similarity (lane_width=8)
pub export fn simd_cosine_batch(
    query: [*]const f32,
    vectors: [*]const [*]const f32,
    count: usize,
    dim: usize,
    out_scores: [*]f32,
) void {
    var i: usize = 0;
    while (i < count) : (i += 1) {
        out_scores[i] = cosine_similarity(query, vectors[i], dim);
    }
}

/// SIMD cosine similarity for single vector pair
fn cosine_similarity(a: [*]const f32, b: [*]const f32, dim: usize) f32 {
    var dot: f32 = 0;
    var norm_a: f32 = 0;
    var norm_b: f32 = 0;
    
    var i: usize = 0;
    // Process 8 elements at a time with SIMD
    while (i + 8 <= dim) : (i += 8) {
        const va = simd.load(f32, 8, a + i);
        const vb = simd.load(f32, 8, b + i);
        
        dot += simd.reduceAdd(f32, va * vb);
        norm_a += simd.reduceAdd(f32, va * va);
        norm_b += simd.reduceAdd(f32, vb * vb);
    }
    
    // Scalar tail
    while (i < dim) : (i += 1) {
        dot += a[i] * b[i];
        norm_a += a[i] * a[i];
        norm_b += b[i] * b[i];
    }
    
    const norm = @sqrt(norm_a * norm_b);
    if (norm == 0) return 0;
    return dot / norm;
}

/// SIMD batch Euclidean distance
pub export fn simd_euclidean_batch(
    query: [*]const f32,
    vectors: [*]const [*]const f32,
    count: usize,
    dim: usize,
    out_distances: [*]f32,
) void {
    var i: usize = 0;
    while (i < count) : (i += 1) {
        out_distances[i] = euclidean_distance(query, vectors[i], dim);
    }
}

fn euclidean_distance(a: [*]const f32, b: [*]const f32, dim: usize) f32 {
    var sum: f32 = 0;
    var i: usize = 0;
    
    while (i + 8 <= dim) : (i += 8) {
        const va = simd.load(f32, 8, a + i);
        const vb = simd.load(f32, 8, b + i);
        const diff = va - vb;
        sum += simd.reduceAdd(f32, diff * diff);
    }
    
    while (i < dim) : (i += 1) {
        const diff = a[i] - b[i];
        sum += diff * diff;
    }
    
    return @sqrt(sum);
}

/// SIMD centroid computation
pub export fn simd_centroid(
    vectors: [*]const [*]const f32,
    count: usize,
    dim: usize,
    out_centroid: [*]f32,
) void {
    // Initialize output
    var d: usize = 0;
    while (d < dim) : (d += 1) {
        out_centroid[d] = 0;
    }
    
    // Sum all vectors
    var i: usize = 0;
    while (i < count) : (i += 1) {
        var j: usize = 0;
        while (j + 8 <= dim) : (j += 8) {
            const v = simd.load(f32, 8, vectors[i] + j);
            const current = simd.load(f32, 8, out_centroid + j);
            simd.store(f32, 8, out_centroid + j, current + v);
        }
        while (j < dim) : (j += 1) {
            out_centroid[j] += vectors[i][j];
        }
    }
    
    // Divide by count
    const inv_count: f32 = 1.0 / @intToFloat(f32, count);
    d = 0;
    while (d < dim) : (d += 1) {
        out_centroid[d] *= inv_count;
    }
}

/// SIMD weighted centroid
pub export fn simd_weighted_centroid(
    vectors: [*]const [*]const f32,
    weights: [*]const f32,
    count: usize,
    dim: usize,
    out_centroid: [*]f32,
) void {
    // Initialize
    var d: usize = 0;
    while (d < dim) : (d += 1) {
        out_centroid[d] = 0;
    }
    
    var total_weight: f32 = 0;
    
    // Weighted sum
    var i: usize = 0;
    while (i < count) : (i += 1) {
        const w = weights[i];
        total_weight += w;
        
        var j: usize = 0;
        while (j + 8 <= dim) : (j += 8) {
            const v = simd.load(f32, 8, vectors[i] + j);
            const current = simd.load(f32, 8, out_centroid + j);
            const weighted = v * @splat(8, w);
            simd.store(f32, 8, out_centroid + j, current + weighted);
        }
        while (j < dim) : (j += 1) {
            out_centroid[j] += vectors[i][j] * w;
        }
    }
    
    // Normalize
    if (total_weight > 0) {
        const inv_weight: f32 = 1.0 / total_weight;
        d = 0;
        while (d < dim) : (d += 1) {
            out_centroid[d] *= inv_weight;
        }
    }
}

/// SIMD batch dot product
pub export fn simd_batch_dot(
    query: [*]const f32,
    vectors: [*]const [*]const f32,
    count: usize,
    dim: usize,
    out_dots: [*]f32,
) void {
    var i: usize = 0;
    while (i < count) : (i += 1) {
        var dot: f32 = 0;
        var j: usize = 0;
        while (j + 8 <= dim) : (j += 8) {
            const va = simd.load(f32, 8, query + j);
            const vb = simd.load(f32, 8, vectors[i] + j);
            dot += simd.reduceAdd(f32, va * vb);
        }
        while (j < dim) : (j += 1) {
            dot += query[j] * vectors[i][j];
        }
        out_dots[i] = dot;
    }
}

/// SIMD vector normalization
pub export fn simd_normalize(
    vectors: [*]const [*]const f32,
    count: usize,
    dim: usize,
    out_vectors: [*]f32,
) void {
    var i: usize = 0;
    while (i < count) : (i += 1) {
        // Compute norm
        var norm_sq: f32 = 0;
        var j: usize = 0;
        while (j + 8 <= dim) : (j += 8) {
            const v = simd.load(f32, 8, vectors[i] + j);
            norm_sq += simd.reduceAdd(f32, v * v);
        }
        while (j < dim) : (j += 1) {
            norm_sq += vectors[i][j] * vectors[i][j];
        }
        
        const norm = @sqrt(norm_sq);
        const inv_norm: f32 = if (norm > 0) 1.0 / norm else 0;
        
        // Normalize
        j = 0;
        while (j + 8 <= dim) : (j += 8) {
            const v = simd.load(f32, 8, vectors[i] + j);
            simd.store(f32, 8, out_vectors + i * dim + j, v * @splat(8, inv_norm));
        }
        while (j < dim) : (j += 1) {
            out_vectors[i * dim + j] = vectors[i][j] * inv_norm;
        }
    }
}

/// SIMD circular convolution (c = a * b)
/// c[k] = sum_{i=0}^{n-1} a[i] * b[(k-i) % n]
pub export fn simd_circular_convolution(
    a: [*]const f32,
    b: [*]const f32,
    dim: usize,
    out: [*]f32,
) void {
    var k: usize = 0;
    while (k < dim) : (k += 1) {
        var sum: f32 = 0;
        var i: usize = 0;
        while (i + 8 <= dim) : (i += 8) {
            const va = simd.load(f32, 8, a + i);
            var vb_data: [8]f32 = undefined;
            var j: usize = 0;
            while (j < 8) : (j += 1) {
                const idx = (k + dim - (i + j)) % dim;
                vb_data[j] = b[idx];
            }
            const vb: @Vector(8, f32) = vb_data;
            sum += simd.reduceAdd(f32, va * vb);
        }
        while (i < dim) : (i += 1) {
            const idx = (k + dim - i) % dim;
            sum += a[i] * b[idx];
        }
        out[k] = sum;
    }
}

/// SIMD circular correlation (c = a # b)
/// c[k] = sum_{i=0}^{n-1} a[i] * b[(i+k) % n]
pub export fn simd_circular_correlation(
    a: [*]const f32,
    b: [*]const f32,
    dim: usize,
    out: [*]f32,
) void {
    var k: usize = 0;
    while (k < dim) : (k += 1) {
        var sum: f32 = 0;
        var i: usize = 0;
        while (i + 8 <= dim) : (i += 8) {
            const va = simd.load(f32, 8, a + i);
            var vb_data: [8]f32 = undefined;
            var j: usize = 0;
            while (j < 8) : (j += 1) {
                const idx = (i + j + k) % dim;
                vb_data[j] = b[idx];
            }
            const vb: @Vector(8, f32) = vb_data;
            sum += simd.reduceAdd(f32, va * vb);
        }
        while (i < dim) : (i += 1) {
            const idx = (i + k) % dim;
            sum += a[i] * b[idx];
        }
        out[k] = sum;
    }
}
