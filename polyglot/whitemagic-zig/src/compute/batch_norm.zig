const std = @import("std");

/// Batch normalization — SIMD-accelerated.
/// For each dimension d: mean_d = mean(x[:,d]), var_d = var(x[:,d])
/// Then: out[i,d] = (x[i,d] - mean_d) / sqrt(var_d + epsilon) * gamma + beta
/// `input_ptr` is n*dim contiguous f32. `out_ptr` must be n*dim contiguous f32.

const LANE_WIDTH = 8;
const VecF32 = @Vector(LANE_WIDTH, f32);

pub export fn wm_batch_norm(
    input_ptr: [*]const f32,
    n: usize,
    dim: usize,
    gamma: f32,
    beta: f32,
    epsilon: f32,
    out_ptr: [*]f32,
) void {
    if (n == 0 or dim == 0) return;
    const input = input_ptr[0 .. n * dim];
    const out = out_ptr[0 .. n * dim];

    // Per-dimension stats + normalization
    for (0..dim) |d| {
        // Compute mean for dimension d
        var mean: f32 = 0.0;
        const simd_n = n - (n % LANE_WIDTH);
        var i: usize = 0;
        var mean_acc: VecF32 = @splat(0.0);
        while (i < simd_n) : (i += LANE_WIDTH) {
            // Gather dim-th element from each row
            inline for (0..LANE_WIDTH) |lane| {
                mean_acc[lane] = input[(i + lane) * dim + d];
            }
            mean_acc = mean_acc; // keep
        }
        // Can't easily SIMD strided access — use scalar
        mean = 0.0;
        for (0..n) |row| {
            mean += input[row * dim + d];
        }
        mean /= @as(f32, @floatFromInt(n));

        // Compute variance for dimension d
        var variance: f32 = 0.0;
        for (0..n) |row| {
            const diff = input[row * dim + d] - mean;
            variance += diff * diff;
        }
        variance /= @as(f32, @floatFromInt(n));

        // Normalize
        const inv_std = 1.0 / @sqrt(variance + epsilon);
        for (0..n) |row| {
            out[row * dim + d] = (input[row * dim + d] - mean) * inv_std * gamma + beta;
        }
    }
}

/// Matrix multiply (GEMM) — tiled + SIMD.
/// C = A @ B where A is m×k, B is k×n, C is m×n.
/// All matrices are row-major contiguous f32.
const TILE_SIZE = 64;

pub export fn wm_matmul(
    a_ptr: [*]const f32,
    m: usize,
    k: usize,
    b_ptr: [*]const f32,
    n: usize,
    c_ptr: [*]f32,
) void {
    if (m == 0 or k == 0 or n == 0) return;
    const a = a_ptr[0 .. m * k];
    const b = b_ptr[0 .. k * n];
    const c = c_ptr[0 .. m * n];

    // Zero output
    @memset(c, 0.0);

    // Tiled matrix multiply
    var ii: usize = 0;
    while (ii < m) : (ii += TILE_SIZE) {
        const tile_m = @min(TILE_SIZE, m - ii);
        var jj: usize = 0;
        while (jj < n) : (jj += TILE_SIZE) {
            const tile_n = @min(TILE_SIZE, n - jj);
            var kk: usize = 0;
            while (kk < k) : (kk += TILE_SIZE) {
                const tile_k = @min(TILE_SIZE, k - kk);

                // Micro-kernel: for each (i,j) in tile, accumulate A[i,kk:kk+tile_k] · B[kk:kk+tile_k,j]
                for (0..tile_m) |i| {
                    const row_a = a[(ii + i) * k + kk .. (ii + i) * k + kk + tile_k];
                    for (0..tile_n) |j| {
                        var dot: f32 = 0.0;
                        // SIMD over k dimension
                        var d: usize = 0;
                        var dot_acc: VecF32 = @splat(0.0);
                        const inner_simd = tile_k - (tile_k % LANE_WIDTH);
                        while (d < inner_simd) : (d += LANE_WIDTH) {
                            const va: VecF32 = row_a[d..][0..LANE_WIDTH].*;
                            var vb: VecF32 = @splat(0.0);
                            inline for (0..LANE_WIDTH) |lane| {
                                vb[lane] = b[(kk + d + lane) * n + jj + j];
                            }
                            dot_acc += va * vb;
                        }
                        dot += @reduce(.Add, dot_acc);
                        while (d < tile_k) : (d += 1) {
                            dot += row_a[d] * b[(kk + d) * n + jj + j];
                        }
                        c[(ii + i) * n + jj + j] += dot;
                    }
                }
            }
        }
    }
}
