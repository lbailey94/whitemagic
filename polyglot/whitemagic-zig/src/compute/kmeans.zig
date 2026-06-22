const std = @import("std");

/// K-means assignment step — SIMD-accelerated.
/// Assigns each point to its nearest centroid by Euclidean distance.
/// `points_ptr` is n*dim contiguous f32. `centroids_ptr` is k*dim contiguous f32.
/// `assignments_out` must point to n u32 values.

const LANE_WIDTH = 8;
const VecF32 = @Vector(LANE_WIDTH, f32);

pub export fn wm_kmeans_assign(
    points_ptr: [*]const f32,
    n: usize,
    dim: usize,
    centroids_ptr: [*]const f32,
    k: usize,
    assignments_out: [*]u32,
) void {
    if (n == 0 or dim == 0 or k == 0) return;
    const points = points_ptr[0 .. n * dim];
    const centroids = centroids_ptr[0 .. k * dim];
    const assignments = assignments_out[0..n];

    for (0..n) |p_idx| {
        const p = points[p_idx * dim .. (p_idx + 1) * dim];
        var best_k: usize = 0;
        var best_dist: f32 = std.math.floatMax(f32);

        for (0..k) |c_idx| {
            const c = centroids[c_idx * dim .. (c_idx + 1) * dim];
            var dist_sq: f32 = 0.0;

            // SIMD distance computation
            const simd_len = dim - (dim % LANE_WIDTH);
            var d: usize = 0;
            var dist_acc: VecF32 = @splat(0.0);

            while (d < simd_len) : (d += LANE_WIDTH) {
                const vp: VecF32 = p[d..][0..LANE_WIDTH].*;
                const vc: VecF32 = c[d..][0..LANE_WIDTH].*;
                const diff = vp - vc;
                dist_acc += diff * diff;
            }
            dist_sq += @reduce(.Add, dist_acc);

            // Scalar remainder
            while (d < dim) : (d += 1) {
                const diff = p[d] - c[d];
                dist_sq += diff * diff;
            }

            if (dist_sq < best_dist) {
                best_dist = dist_sq;
                best_k = c_idx;
            }
        }

        assignments[p_idx] = @intCast(best_k);
    }
}

/// Weighted centroid computation — SIMD-accelerated.
/// Computes Σ vectors[i] * weights[i] / Σ weights[i]
/// `vectors_ptr` is n*dim contiguous f32. `weights_ptr` is n f32 values.
/// `out_ptr` must point to dim f32 values.
pub export fn wm_weighted_centroid(
    vectors_ptr: [*]const f32,
    weights_ptr: [*]const f32,
    n: usize,
    dim: usize,
    out_ptr: [*]f32,
) void {
    if (n == 0 or dim == 0) return;
    const vectors = vectors_ptr[0 .. n * dim];
    const weights = weights_ptr[0..n];
    const out = out_ptr[0..dim];

    var total_weight: f32 = 0.0;
    for (0..n) |i| total_weight += weights[i];

    if (total_weight == 0.0) {
        @memset(out, 0.0);
        return;
    }

    for (0..dim) |d| {
        var acc: f32 = 0.0;
        for (0..n) |i| {
            acc += vectors[i * dim + d] * weights[i];
        }
        out[d] = acc / total_weight;
    }
}
