// SIMD Unified Operations (PSR-001) - Upgraded with AVX2/SSE Intrinsics
// Target: 100-1000× speedup for vector operations
// Uses true SIMD intrinsics instead of manual chunking

const std = @import("std");

const target = @import("builtin").target;

// AVX2 is available on x86_64 with AVX2 support
const has_avx2 = std.Target.x86.featureSetHas(target.cpu.features, .avx2);
const has_sse = std.Target.x86.featureSetHas(target.cpu.features, .sse2);

/// SIMD vector operations with AVX2/SSE fallback
pub const SimdOps = struct {
    /// Dot product using Zig's @Vector for true SIMD acceleration
    pub fn dotProductSimd(a: []const f32, b: []const f32) f32 {
        if (a.len != b.len) return 0.0;
        
        const len = a.len;
        var sum: f32 = 0.0;
        
        if (has_avx2) {
            // AVX2: Process 8 floats at a time using @Vector
            const vec_len = 8;
            const chunks = len / vec_len;
            var i: usize = 0;
            
            while (i < chunks * vec_len) : (i += vec_len) {
                const vec_a = @as(@Vector(vec_len, f32), a[i..i+vec_len].*);
                const vec_b = @as(@Vector(vec_len, f32), b[i..i+vec_len].*);
                const vec_product = vec_a * vec_b;
                const vec_sum = @reduce(.Add, vec_product);
                sum += vec_sum;
            }
        } else if (has_sse) {
            // SSE: Process 4 floats at a time using @Vector
            const vec_len = 4;
            const chunks = len / vec_len;
            var i: usize = 0;
            
            while (i < chunks * vec_len) : (i += vec_len) {
                const vec_a = @as(@Vector(vec_len, f32), a[i..i+vec_len].*);
                const vec_b = @as(@Vector(vec_len, f32), b[i..i+vec_len].*);
                const vec_product = vec_a * vec_b;
                const vec_sum = @reduce(.Add, vec_product);
                sum += vec_sum;
            }
        }
        
        // Handle remainder
        const vec_len = if (has_avx2) 8 else if (has_sse) 4 else 1;
        var i: usize = (len / vec_len) * vec_len;
        while (i < len) : (i += 1) {
            sum += a[i] * b[i];
        }
        
        return sum;
    }

    /// Dot product using AVX2 (8 floats at a time) or SSE (4 floats at a time)
    pub fn dotProduct(a: []const f32, b: []const f32) f32 {
        return dotProductSimd(a, b);
    }
    
    /// Euclidean norm (L2 norm)
    pub fn norm(vec: []const f32) f32 {
        var sum: f32 = 0.0;
        for (vec) |val| {
            sum += val * val;
        }
        return @sqrt(sum);
    }
    
    /// Cosine similarity
    pub fn cosineSimilarity(a: []const f32, b: []const f32) f32 {
        if (a.len != b.len or a.len == 0) return 0.0;
        
        const dot = dotProduct(a, b);
        const norm_a = norm(a);
        const norm_b = norm(b);
        
        if (norm_a == 0.0 or norm_b == 0.0) return 0.0;
        
        return dot / (norm_a * norm_b);
    }
    
    /// Euclidean distance
    pub fn euclideanDistance(a: []const f32, b: []const f32) f32 {
        if (a.len != b.len) return std.math.inf(f32);
        
        var sum: f32 = 0.0;
        for (a, b) |val_a, val_b| {
            const diff = val_a - val_b;
            sum += diff * diff;
        }
        
        return @sqrt(sum);
    }
    
    /// Manhattan distance (L1 distance)
    pub fn manhattanDistance(a: []const f32, b: []const f32) f32 {
        if (a.len != b.len) return std.math.inf(f32);
        
        var sum: f32 = 0.0;
        for (a, b) |val_a, val_b| {
            sum += @abs(val_a - val_b);
        }
        
        return sum;
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
};

/// C FFI exports
export fn simd_dot_product(a: [*c]const f32, b: [*c]const f32, len: usize) f32 {
    const slice_a = a[0..len];
    const slice_b = b[0..len];
    return SimdOps.dotProduct(slice_a, slice_b);
}

export fn simd_cosine_similarity(a: [*c]const f32, b: [*c]const f32, len: usize) f32 {
    const slice_a = a[0..len];
    const slice_b = b[0..len];
    return SimdOps.cosineSimilarity(slice_a, slice_b);
}

export fn simd_euclidean_distance(a: [*c]const f32, b: [*c]const f32, len: usize) f32 {
    const slice_a = a[0..len];
    const slice_b = b[0..len];
    return SimdOps.euclideanDistance(slice_a, slice_b);
}

export fn simd_manhattan_distance(a: [*c]const f32, b: [*c]const f32, len: usize) f32 {
    const slice_a = a[0..len];
    const slice_b = b[0..len];
    return SimdOps.manhattanDistance(slice_a, slice_b);
}

// Tests
test "dot product" {
    const a = [_]f32{ 1.0, 2.0, 3.0 };
    const b = [_]f32{ 4.0, 5.0, 6.0 };
    const result = SimdOps.dotProduct(&a, &b);
    try std.testing.expectApproxEqAbs(@as(f32, 32.0), result, 0.001);
}

test "cosine similarity" {
    const a = [_]f32{ 1.0, 0.0, 0.0 };
    const b = [_]f32{ 1.0, 0.0, 0.0 };
    const result = SimdOps.cosineSimilarity(&a, &b);
    try std.testing.expectApproxEqAbs(@as(f32, 1.0), result, 0.001);
}

test "euclidean distance" {
    const a = [_]f32{ 0.0, 0.0 };
    const b = [_]f32{ 3.0, 4.0 };
    const result = SimdOps.euclideanDistance(&a, &b);
    try std.testing.expectApproxEqAbs(@as(f32, 5.0), result, 0.001);
}

test "manhattan distance" {
    const a = [_]f32{ 0.0, 0.0 };
    const b = [_]f32{ 3.0, 4.0 };
    const result = SimdOps.manhattanDistance(&a, &b);
    try std.testing.expectApproxEqAbs(@as(f32, 7.0), result, 0.001);
}
