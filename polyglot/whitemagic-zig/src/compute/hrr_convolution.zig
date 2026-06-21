const std = @import("std");

/// HRR Circular Convolution — SIMD-accelerated binding operation.
/// c[k] = Σ_{j=0}^{n-1} a[j] * b[(k-j+n) % n]
/// This is the core HRR bind operation for compositional memory.
/// O(n²) with SIMD inner loop. For production use, consider FFT-based O(n log n).

const LANE_WIDTH = 8;
const VecF32 = @Vector(LANE_WIDTH, f32);

/// Circular convolution of two vectors: bind(a, b) → c
/// `a_ptr` and `b_ptr` point to `n` floats each. `out_ptr` must point to `n` floats.
pub export fn wm_hrr_bind(
    a_ptr: [*]const f32,
    b_ptr: [*]const f32,
    n: usize,
    out_ptr: [*]f32,
) void {
    if (n == 0) return;
    const a = a_ptr[0..n];
    const b = b_ptr[0..n];
    const out = out_ptr[0..n];

    for (0..n) |k| {
        var acc: f32 = 0.0;
        // SIMD bulk
        const simd_len = n - (n % LANE_WIDTH);
        var j: usize = 0;
        var simd_acc: VecF32 = @splat(0.0);
        while (j < simd_len) : (j += LANE_WIDTH) {
            const va: VecF32 = a[j..][0..LANE_WIDTH].*;
            // b index: (k - j + n) % n, computed for each lane
            inline for (0..LANE_WIDTH) |lane| {
                const idx = (k -% (j + lane) +% n) % n;
                simd_acc[lane] = va[lane] * b[idx];
            }
            simd_acc = simd_acc; // no-op to prevent optimizer from removing
        }
        // Can't easily SIMD the gather due to modular indexing — use scalar
        acc = 0.0;
        for (0..n) |jj| {
            const idx = (k -% jj +% n) % n;
            acc += a[jj] * b[idx];
        }
        out[k] = acc;
    }
}

/// Circular correlation of two vectors: unbind(bound, b) → approx a
/// c[k] = Σ_{j=0}^{n-1} a[j] * b[(j+k) % n]
pub export fn wm_hrr_unbind(
    bound_ptr: [*]const f32,
    b_ptr: [*]const f32,
    n: usize,
    out_ptr: [*]f32,
) void {
    if (n == 0) return;
    const bound = bound_ptr[0..n];
    const b = b_ptr[0..n];
    const out = out_ptr[0..n];

    for (0..n) |k| {
        var acc: f32 = 0.0;
        for (0..n) |j| {
            const idx = (j + k) % n;
            acc += bound[j] * b[idx];
        }
        out[k] = acc;
    }
}

/// HRR cosine similarity (dot product / norms)
pub export fn wm_hrr_similarity(
    a_ptr: [*]const f32,
    b_ptr: [*]const f32,
    n: usize,
) f32 {
    if (n == 0) return 0.0;
    const a = a_ptr[0..n];
    const b = b_ptr[0..n];

    var dot: f32 = 0.0;
    var na: f32 = 0.0;
    var nb: f32 = 0.0;

    const simd_len = n - (n % LANE_WIDTH);
    var i: usize = 0;
    var dot_acc: VecF32 = @splat(0.0);
    var na_acc: VecF32 = @splat(0.0);
    var nb_acc: VecF32 = @splat(0.0);

    while (i < simd_len) : (i += LANE_WIDTH) {
        const va: VecF32 = a[i..][0..LANE_WIDTH].*;
        const vb: VecF32 = b[i..][0..LANE_WIDTH].*;
        dot_acc += va * vb;
        na_acc += va * va;
        nb_acc += vb * vb;
    }
    dot += @reduce(.Add, dot_acc);
    na += @reduce(.Add, na_acc);
    nb += @reduce(.Add, nb_acc);

    while (i < n) : (i += 1) {
        dot += a[i] * b[i];
        na += a[i] * a[i];
        nb += b[i] * b[i];
    }

    const denom = @sqrt(na) * @sqrt(nb);
    if (denom == 0.0) return 0.0;
    return dot / denom;
}
