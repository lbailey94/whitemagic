const std = @import("std");

/// SIMD-accelerated batch embedding quantization for memory storage optimization.
/// Quantizes 384-dim f32 embeddings to 384-dim u8 (4x space savings).
const LANE_WIDTH = 8;
const EMBEDDING_DIM = 384;
const VecF32 = @Vector(LANE_WIDTH, f32);

fn quantize_one(value: f32) u8 {
    const clamped = std.math.clamp(value, -1.0, 1.0);
    const normalized = (clamped + 1.0) * 127.5;
    return @intFromFloat(@round(normalized));
}

export fn wm_quantize_embeddings_f32_to_u8(
    embeddings_ptr: [*]const f32,
    n: usize,
    quantized_out: [*]u8,
) void {
    if (n == 0) return;
    const total_elements = n * EMBEDDING_DIM;
    const simd_elements = total_elements - (total_elements % LANE_WIDTH);
    var i: usize = 0;
    while (i < simd_elements) : (i += LANE_WIDTH) {
        const vals: VecF32 = embeddings_ptr[i..][0..LANE_WIDTH].*;
        const clamped = @max(@min(vals, @as(VecF32, @splat(1.0))), @as(VecF32, @splat(-1.0)));
        const normalized = (clamped + @as(VecF32, @splat(1.0))) * @as(VecF32, @splat(127.5));
        for (0..LANE_WIDTH) |j| {
            quantized_out[i + j] = @intFromFloat(@round(normalized[j]));
        }
    }
    while (i < total_elements) : (i += 1) {
        quantized_out[i] = quantize_one(embeddings_ptr[i]);
    }
}

export fn wm_dequantize_embeddings_u8_to_f32(
    quantized_ptr: [*]const u8,
    n: usize,
    embeddings_out: [*]f32,
) void {
    if (n == 0) return;
    const total_elements = n * EMBEDDING_DIM;
    const simd_elements = total_elements - (total_elements % LANE_WIDTH);
    var i: usize = 0;
    while (i < simd_elements) : (i += LANE_WIDTH) {
        var vals: VecF32 = undefined;
        for (0..LANE_WIDTH) |j| {
            vals[j] = @as(f32, @floatFromInt(quantized_ptr[i + j]));
        }
        const dequantized = vals / @as(VecF32, @splat(127.5)) - @as(VecF32, @splat(1.0));
        for (0..LANE_WIDTH) |j| {
            embeddings_out[i + j] = dequantized[j];
        }
    }
    while (i < total_elements) : (i += 1) {
        embeddings_out[i] = @as(f32, @floatFromInt(quantized_ptr[i])) / 127.5 - 1.0;
    }
}

export fn wm_quantized_cosine_similarity(
    q_ptr: [*]const u8,
    t_ptr: [*]const u8,
) f32 {
    const simd_elements = EMBEDDING_DIM - (EMBEDDING_DIM % LANE_WIDTH);
    var dot_product: f32 = 0.0;
    var q_norm_sq: f32 = 0.0;
    var t_norm_sq: f32 = 0.0;
    var i: usize = 0;
    while (i < simd_elements) : (i += LANE_WIDTH) {
        var q_vals: VecF32 = undefined;
        var t_vals: VecF32 = undefined;
        for (0..LANE_WIDTH) |j| {
            q_vals[j] = @as(f32, @floatFromInt(q_ptr[i + j])) / 127.5 - 1.0;
            t_vals[j] = @as(f32, @floatFromInt(t_ptr[i + j])) / 127.5 - 1.0;
        }
        dot_product += @reduce(.Add, q_vals * t_vals);
        q_norm_sq += @reduce(.Add, q_vals * q_vals);
        t_norm_sq += @reduce(.Add, t_vals * t_vals);
    }
    while (i < EMBEDDING_DIM) : (i += 1) {
        const q_val = @as(f32, @floatFromInt(q_ptr[i])) / 127.5 - 1.0;
        const t_val = @as(f32, @floatFromInt(t_ptr[i])) / 127.5 - 1.0;
        dot_product += q_val * t_val;
        q_norm_sq += q_val * q_val;
        t_norm_sq += t_val * t_val;
    }
    const denom = @sqrt(q_norm_sq * t_norm_sq);
    if (denom == 0.0) return 0.0;
    return dot_product / denom;
}

export fn wm_quantized_cosine_batch(
    q_ptr: [*]const u8,
    targets_ptr: [*]const u8,
    n: usize,
    scores_out: [*]f32,
) void {
    for (0..n) |i| {
        scores_out[i] = wm_quantized_cosine_similarity(q_ptr, targets_ptr + i * EMBEDDING_DIM);
    }
}
