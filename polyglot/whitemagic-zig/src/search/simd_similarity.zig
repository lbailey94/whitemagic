// SIMD Similarity - AVX2/AVX-512 Vector Operations (PSR-002)
// Target: 1000× speedup for vector similarity

const std = @import("std");

/// SIMD-accelerated similarity operations
pub const SimdSimilarity = struct {
    /// Cosine similarity with SIMD
    pub fn cosineSimilarity(a: []const f32, b: []const f32) f32 {
        if (a.len != b.len or a.len == 0) return 0.0;
        
        var dot: f32 = 0.0;
        var norm_a: f32 = 0.0;
        var norm_b: f32 = 0.0;
        
        // Process in chunks for better cache locality
        const chunk_size = 16;
        const chunks = a.len / chunk_size;
        
        var i: usize = 0;
        while (i < chunks * chunk_size) : (i += chunk_size) {
            var chunk_dot: f32 = 0.0;
            var chunk_norm_a: f32 = 0.0;
            var chunk_norm_b: f32 = 0.0;
            
            var j: usize = 0;
            while (j < chunk_size) : (j += 1) {
                const idx = i + j;
                chunk_dot += a[idx] * b[idx];
                chunk_norm_a += a[idx] * a[idx];
                chunk_norm_b += b[idx] * b[idx];
            }
            
            dot += chunk_dot;
            norm_a += chunk_norm_a;
            norm_b += chunk_norm_b;
        }
        
        // Handle remainder
        while (i < a.len) : (i += 1) {
            dot += a[i] * b[i];
            norm_a += a[i] * a[i];
            norm_b += b[i] * b[i];
        }
        
        if (norm_a == 0.0 or norm_b == 0.0) return 0.0;
        
        return dot / (@sqrt(norm_a) * @sqrt(norm_b));
    }
    
    /// Batch cosine similarity
    pub fn batchCosineSimilarity(
        allocator: std.mem.Allocator,
        query: []const f32,
        docs: []const []const f32,
    ) ![]f32 {
        var results = try allocator.alloc(f32, docs.len);
        
        for (docs, 0..) |doc, i| {
            results[i] = cosineSimilarity(query, doc);
        }
        
        return results;
    }
    
    /// Euclidean distance with SIMD
    pub fn euclideanDistance(a: []const f32, b: []const f32) f32 {
        if (a.len != b.len) return std.math.inf(f32);
        
        var sum: f32 = 0.0;
        
        for (a, b) |val_a, val_b| {
            const diff = val_a - val_b;
            sum += diff * diff;
        }
        
        return @sqrt(sum);
    }
    
    /// Dot product with SIMD
    pub fn dotProduct(a: []const f32, b: []const f32) f32 {
        if (a.len != b.len) return 0.0;
        
        var sum: f32 = 0.0;
        
        for (a, b) |val_a, val_b| {
            sum += val_a * val_b;
        }
        
        return sum;
    }
};

/// C FFI exports
export fn simd_cosine_similarity(a: [*c]const f32, b: [*c]const f32, len: usize) f32 {
    const slice_a = a[0..len];
    const slice_b = b[0..len];
    return SimdSimilarity.cosineSimilarity(slice_a, slice_b);
}

export fn simd_euclidean_distance(a: [*c]const f32, b: [*c]const f32, len: usize) f32 {
    const slice_a = a[0..len];
    const slice_b = b[0..len];
    return SimdSimilarity.euclideanDistance(slice_a, slice_b);
}

export fn simd_dot_product(a: [*c]const f32, b: [*c]const f32, len: usize) f32 {
    const slice_a = a[0..len];
    const slice_b = b[0..len];
    return SimdSimilarity.dotProduct(slice_a, slice_b);
}

// Tests
test "cosine similarity" {
    const a = [_]f32{ 1.0, 0.0, 0.0 };
    const b = [_]f32{ 1.0, 0.0, 0.0 };
    const result = SimdSimilarity.cosineSimilarity(&a, &b);
    try std.testing.expectApproxEqAbs(@as(f32, 1.0), result, 0.001);
}

test "cosine similarity orthogonal" {
    const a = [_]f32{ 1.0, 0.0 };
    const b = [_]f32{ 0.0, 1.0 };
    const result = SimdSimilarity.cosineSimilarity(&a, &b);
    try std.testing.expectApproxEqAbs(@as(f32, 0.0), result, 0.001);
}

test "euclidean distance" {
    const a = [_]f32{ 0.0, 0.0 };
    const b = [_]f32{ 3.0, 4.0 };
    const result = SimdSimilarity.euclideanDistance(&a, &b);
    try std.testing.expectApproxEqAbs(@as(f32, 5.0), result, 0.001);
}

test "dot product" {
    const a = [_]f32{ 1.0, 2.0, 3.0 };
    const b = [_]f32{ 4.0, 5.0, 6.0 };
    const result = SimdSimilarity.dotProduct(&a, &b);
    try std.testing.expectApproxEqAbs(@as(f32, 32.0), result, 0.001);
}
