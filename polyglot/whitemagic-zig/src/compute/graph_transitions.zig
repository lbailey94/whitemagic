const std = @import("std");

/// SIMD-accelerated batch transition probability computation for graph walker.
/// Computes weighted probability from 4 signals: semantic, gravity, recency, staleness.
/// Used by graph_walker_hot_path.py for parallel BFS traversal scoring.

const LANE_WIDTH = 8; // AVX2-friendly
const VecF32 = @Vector(LANE_WIDTH, f32);

/// Batch compute transition probabilities for graph edges.
/// Each edge has 4 signals: semantic_sim, galactic_gravity, recency, staleness
/// Weights default: semantic=0.4, gravity=0.3, recency=0.2, staleness=0.1
/// 
/// Args:
///   semantic_ptr: [*]const f32 - semantic similarity scores (per edge)
///   gravity_ptr: [*]const f32 - galactic gravity scores (per edge)
///   recency_ptr: [*]const f32 - recency scores (per edge)
///   staleness_ptr: [*]const f32 - staleness scores (per edge)
///   weights_ptr: [*]const f32 - 4 weights [semantic, gravity, recency, staleness]
///   n: usize - number of edges
///   probs_out: [*]f32 - output probabilities (must have space for n)
pub export fn wm_graph_transition_batch(
    semantic_ptr: [*]const f32,
    gravity_ptr: [*]const f32,
    recency_ptr: [*]const f32,
    staleness_ptr: [*]const f32,
    weights_ptr: [*]const f32,
    n: usize,
    probs_out: [*]f32,
) void {
    if (n == 0) return;
    
    // Load weights
    const w_semantic: f32 = weights_ptr[0];
    const w_gravity: f32 = weights_ptr[1];
    const w_recency: f32 = weights_ptr[2];
    const w_staleness: f32 = weights_ptr[3];
    
    // Create weight vectors for SIMD
    const w_sem_vec: VecF32 = @splat(w_semantic);
    const w_grav_vec: VecF32 = @splat(w_gravity);
    const w_rec_vec: VecF32 = @splat(w_recency);
    const w_stal_vec: VecF32 = @splat(w_staleness);
    
    const simd_len = n - (n % LANE_WIDTH);
    var i: usize = 0;
    
    // SIMD bulk processing
    while (i < simd_len) : (i += LANE_WIDTH) {
        const sem: VecF32 = semantic_ptr[i..][0..LANE_WIDTH].*;
        const grav: VecF32 = gravity_ptr[i..][0..LANE_WIDTH].*;
        const rec: VecF32 = recency_ptr[i..][0..LANE_WIDTH].*;
        const stal: VecF32 = staleness_ptr[i..][0..LANE_WIDTH].*;
        
        // prob = w_s * semantic + w_g * gravity + w_r * recency + w_st * (1 - staleness)
        var prob = sem * w_sem_vec;
        prob += grav * w_grav_vec;
        prob += rec * w_rec_vec;
        prob += (@as(VecF32, @splat(1.0)) - stal) * w_stal_vec;
        
        // Clamp to [0, 1]
        prob = @max(prob, @as(VecF32, @splat(0.0)));
        prob = @min(prob, @as(VecF32, @splat(1.0)));
        
        // Store results
        for (0..LANE_WIDTH) |j| {
            probs_out[i + j] = prob[j];
        }
    }
    
    // Scalar remainder
    while (i < n) : (i += 1) {
        var prob: f32 = w_semantic * semantic_ptr[i] +
                       w_gravity * gravity_ptr[i] +
                       w_recency * recency_ptr[i] +
                       w_staleness * (1.0 - staleness_ptr[i]);
        // Clamp to [0, 1]
        if (prob < 0.0) prob = 0.0;
        if (prob > 1.0) prob = 1.0;
        probs_out[i] = prob;
    }
}

/// Single transition probability computation (for individual edge scoring).
/// Returns probability in [0.0, 1.0].
pub export fn wm_graph_transition_single(
    semantic_sim: f32,
    galactic_gravity: f32,
    recency: f32,
    staleness: f32,
    w_semantic: f32,
    w_gravity: f32,
    w_recency: f32,
    w_staleness: f32,
) f32 {
    const prob: f32 = w_semantic * semantic_sim +
                   w_gravity * galactic_gravity +
                   w_recency * recency +
                   w_staleness * (1.0 - staleness);
    if (prob < 0.0) return 0.0;
    if (prob > 1.0) return 1.0;
    return prob;
}

// --------------------------------------------------------------------------
// Tests
// --------------------------------------------------------------------------

test "wm_graph_transition_single basic" {
    // Test with default weights
    const prob = wm_graph_transition_single(
        0.8,  // semantic_sim
        0.6,  // galactic_gravity
        0.9,  // recency
        0.2,  // staleness (low = good)
        0.4,  // w_semantic
        0.3,  // w_gravity
        0.2,  // w_recency
        0.1,  // w_staleness
    );
    // Expected: 0.4*0.8 + 0.3*0.6 + 0.2*0.9 + 0.1*(1-0.2) = 0.32 + 0.18 + 0.18 + 0.08 = 0.76
    try std.testing.expectApproxEqAbs(prob, 0.76, 0.001);
}

test "wm_graph_transition_batch" {
    const n: usize = 16;
    var semantic: [n]f32 = undefined;
    var gravity: [n]f32 = undefined;
    var recency: [n]f32 = undefined;
    var staleness: [n]f32 = undefined;
    var probs: [n]f32 = undefined;
    
    // Fill with test data
    for (0..n) |i| {
        semantic[i] = @as(f32, @floatFromInt(i)) / @as(f32, @floatFromInt(n)); // 0.0 to ~0.94
        gravity[i] = 0.5;
        recency[i] = 0.7;
        staleness[i] = 0.1;
    }
    
    const weights = [4]f32{ 0.4, 0.3, 0.2, 0.1 };
    
    wm_graph_transition_batch(
        &semantic,
        &gravity,
        &recency,
        &staleness,
        &weights,
        n,
        &probs,
    );
    
    // Check first result
    // prob = 0.4*0.0 + 0.3*0.5 + 0.2*0.7 + 0.1*(1-0.1) = 0 + 0.15 + 0.14 + 0.09 = 0.38
    try std.testing.expectApproxEqAbs(probs[0], 0.38, 0.001);
    
    // Check last result (index 15: semantic = 15/16 = 0.9375)
    // prob = 0.4*0.9375 + 0.15 + 0.14 + 0.09 = 0.375 + 0.38 = 0.755
    try std.testing.expectApproxEqAbs(probs[15], 0.755, 0.001);
    
    // All results should be in [0, 1]
    for (probs) |p| {
        try std.testing.expect(p >= 0.0);
        try std.testing.expect(p <= 1.0);
    }
}

test "wm_graph_transition_clamping" {
    // Test that results are clamped to [0, 1]
    const prob_high = wm_graph_transition_single(
        1.0, 1.0, 1.0, 0.0,  // all good signals
        1.0, 0.0, 0.0, 0.0,  // all weight on semantic
    );
    try std.testing.expectApproxEqAbs(prob_high, 1.0, 0.001);
    
    const prob_low = wm_graph_transition_single(
        0.0, 0.0, 0.0, 1.0,  // all bad signals
        0.5, 0.0, 0.0, 0.5,  // weights on semantic and staleness
    );
    // prob = 0.5*0 + 0 + 0 + 0.5*(1-1) = 0
    try std.testing.expectApproxEqAbs(prob_low, 0.0, 0.001);
}
