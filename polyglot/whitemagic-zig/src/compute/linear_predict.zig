const std = @import("std");

/// Logistic linear prediction — SIMD-accelerated.
/// score = bias + Σ(features · weights), then sigmoid(score) = 1 / (1 + e^(-score))
/// `features_ptr` is n*dim contiguous f32. `weights_ptr` is dim f32 values.
/// `scores_out` must point to n f32 values (sigmoid probabilities).

const LANE_WIDTH = 8;
const VecF32 = @Vector(LANE_WIDTH, f32);

pub export fn wm_linear_predict_sigmoid(
    features_ptr: [*]const f32,
    n: usize,
    dim: usize,
    weights_ptr: [*]const f32,
    bias: f32,
    scores_out: [*]f32,
) void {
    if (n == 0 or dim == 0) return;
    const features = features_ptr[0 .. n * dim];
    const weights = weights_ptr[0..dim];
    const scores = scores_out[0..n];

    const simd_len = dim - (dim % LANE_WIDTH);

    for (0..n) |i| {
        const feat = features[i * dim .. (i + 1) * dim];
        var dot: f32 = 0.0;

        // SIMD dot product
        var d: usize = 0;
        var dot_acc: VecF32 = @splat(0.0);
        while (d < simd_len) : (d += LANE_WIDTH) {
            const vf: VecF32 = feat[d..][0..LANE_WIDTH].*;
            const vw: VecF32 = weights[d..][0..LANE_WIDTH].*;
            dot_acc += vf * vw;
        }
        dot += @reduce(.Add, dot_acc);

        // Scalar remainder
        while (d < dim) : (d += 1) {
            dot += feat[d] * weights[d];
        }

        const score = bias + dot;
        // Sigmoid: 1 / (1 + e^(-score))
        scores[i] = 1.0 / (1.0 + @exp(-score));
    }
}

/// Raw linear prediction (no sigmoid) — just bias + dot product.
pub export fn wm_linear_predict(
    features_ptr: [*]const f32,
    n: usize,
    dim: usize,
    weights_ptr: [*]const f32,
    bias: f32,
    scores_out: [*]f32,
) void {
    if (n == 0 or dim == 0) return;
    const features = features_ptr[0 .. n * dim];
    const weights = weights_ptr[0..dim];
    const scores = scores_out[0..n];

    const simd_len = dim - (dim % LANE_WIDTH);

    for (0..n) |i| {
        const feat = features[i * dim .. (i + 1) * dim];
        var dot: f32 = 0.0;

        var d: usize = 0;
        var dot_acc: VecF32 = @splat(0.0);
        while (d < simd_len) : (d += LANE_WIDTH) {
            const vf: VecF32 = feat[d..][0..LANE_WIDTH].*;
            const vw: VecF32 = weights[d..][0..LANE_WIDTH].*;
            dot_acc += vf * vw;
        }
        dot += @reduce(.Add, dot_acc);

        while (d < dim) : (d += 1) {
            dot += feat[d] * weights[d];
        }

        scores[i] = bias + dot;
    }
}
