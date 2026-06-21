const std = @import("std");

/// Pearson temporal correlation — SIMD-accelerated causal mining.
/// Computes the correlation coefficient between two time series.
/// Uses single-pass Welford-style accumulation for numerical stability.

const LANE_WIDTH = 4; // f64 lanes (AVX2 has 4 f64 lanes)
const VecF64 = @Vector(LANE_WIDTH, f64);

/// Pearson correlation coefficient between two f64 time series.
/// Returns a value in [-1.0, 1.0]. Returns 0.0 for empty or zero-variance inputs.
pub export fn wm_causal_temporal_correlation(
    a_ptr: [*]const f64,
    b_ptr: [*]const f64,
    n: usize,
) f32 {
    if (n == 0) return 0.0;
    const a = a_ptr[0..n];
    const b = b_ptr[0..n];

    // Single-pass: accumulate sum_a, sum_b, sum_aa, sum_bb, sum_ab
    var sum_a: f64 = 0.0;
    var sum_b: f64 = 0.0;
    var sum_aa: f64 = 0.0;
    var sum_bb: f64 = 0.0;
    var sum_ab: f64 = 0.0;

    // SIMD bulk
    const simd_len = n - (n % LANE_WIDTH);
    var i: usize = 0;
    var sa_acc: VecF64 = @splat(0.0);
    var sb_acc: VecF64 = @splat(0.0);
    var saa_acc: VecF64 = @splat(0.0);
    var sbb_acc: VecF64 = @splat(0.0);
    var sab_acc: VecF64 = @splat(0.0);

    while (i < simd_len) : (i += LANE_WIDTH) {
        const va: VecF64 = a[i..][0..LANE_WIDTH].*;
        const vb: VecF64 = b[i..][0..LANE_WIDTH].*;
        sa_acc += va;
        sb_acc += vb;
        saa_acc += va * va;
        sbb_acc += vb * vb;
        sab_acc += va * vb;
    }

    sum_a += @reduce(.Add, sa_acc);
    sum_b += @reduce(.Add, sb_acc);
    sum_aa += @reduce(.Add, saa_acc);
    sum_bb += @reduce(.Add, sbb_acc);
    sum_ab += @reduce(.Add, sab_acc);

    // Scalar remainder
    while (i < n) : (i += 1) {
        sum_a += a[i];
        sum_b += b[i];
        sum_aa += a[i] * a[i];
        sum_bb += b[i] * b[i];
        sum_ab += a[i] * b[i];
    }

    const nf = @as(f64, @floatFromInt(n));
    const num = nf * sum_ab - sum_a * sum_b;
    const den_a = nf * sum_aa - sum_a * sum_a;
    const den_b = nf * sum_bb - sum_b * sum_b;
    const denom = @sqrt(den_a) * @sqrt(den_b);

    if (denom == 0.0) return 0.0;
    return @floatCast(num / denom);
}
