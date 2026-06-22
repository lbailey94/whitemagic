const std = @import("std");

/// Newman modularity score — SIMD-accelerated community detection quality metric.
/// Q = (1 / 2m) * Σ_{i,j same community} (A[i,j] - k_i * k_j / (2m))
/// where m = total edge weight, k_i = degree of node i.
///
/// Optimization vs Mojo: precompute degree vector once (O(n²) with SIMD row-reduction)
/// instead of recomputing degrees inside the inner loop (Mojo's O(n³)).

const LANE_WIDTH = 8;
const VecF32 = @Vector(LANE_WIDTH, f32);

pub export fn wm_modularity_score(
    adj_ptr: [*]const f32,
    n: usize,
    communities_ptr: [*]const u32,
) f32 {
    if (n == 0) return 0.0;
    const adj = adj_ptr[0 .. n * n];
    const communities = communities_ptr[0..n];

    // Step 1: Compute degrees k[i] = Σ_j A[i,j] with SIMD row reduction
    var total_weight: f32 = 0.0;
    var degrees = std.heap.page_allocator.alloc(f32, n) catch return 0.0;
    defer std.heap.page_allocator.free(degrees);

    for (0..n) |i| {
        const row = adj[i * n .. (i + 1) * n];
        var deg: f32 = 0.0;
        const simd_n = n - (n % LANE_WIDTH);
        var j: usize = 0;
        var deg_acc: VecF32 = @splat(0.0);
        while (j < simd_n) : (j += LANE_WIDTH) {
            const vr: VecF32 = row[j..][0..LANE_WIDTH].*;
            deg_acc += vr;
        }
        deg += @reduce(.Add, deg_acc);
        while (j < n) : (j += 1) {
            deg += row[j];
        }
        degrees[i] = deg;
        total_weight += deg;
    }

    const two_m = total_weight; // 2m (each edge counted twice in undirected)
    if (two_m == 0.0) return 0.0;

    // Step 2: Compute Q = (1/2m) * Σ_{i,j same comm} (A[i,j] - k_i*k_j / 2m)
    var q: f32 = 0.0;
    for (0..n) |i| {
        const ki = degrees[i];
        const row = adj[i * n .. (i + 1) * n];
        for (0..n) |j| {
            if (communities[i] == communities[j]) {
                const expected = ki * degrees[j] / two_m;
                q += row[j] - expected;
            }
        }
    }

    return q / two_m;
}
