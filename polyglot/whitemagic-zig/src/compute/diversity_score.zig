const std = @import("std");

/// SIMD-accelerated memory diversity scoring for result deduplication.
/// Ensures returned memories cover distinct semantic topics.

const LANE_WIDTH = 8;
const VecF32 = @Vector(LANE_WIDTH, f32);

/// Compute Maximal Marginal Relevance (MMR) diversity scores
/// MMR = lambda * relevance - (1 - lambda) * max_sim_to_selected
export fn wm_mmr_diversity_scores(
    relevance_scores: [*]const f32,
    similarity_matrix: [*]const f32,  // n x n similarity matrix (flat)
    n: usize,
    lambda: f32,
    selected_mask: [*]const u8,  // 1 if already selected, 0 otherwise
    mmr_scores_out: [*]f32,
) void {
    for (0..n) |i| {
        if (selected_mask[i] == 1) {
            mmr_scores_out[i] = -1.0; // Already selected
            continue;
        }
        
        // Find max similarity to any selected item
        var max_sim: f32 = 0.0;
        for (0..n) |j| {
            if (selected_mask[j] == 1) {
                const sim = similarity_matrix[i * n + j];
                if (sim > max_sim) {
                    max_sim = sim;
                }
            }
        }
        
        // MMR formula
        mmr_scores_out[i] = lambda * relevance_scores[i] - (1.0 - lambda) * max_sim;
    }
}

/// Batch compute diversity scores using SIMD
export fn wm_diversity_score_batch(
    embeddings_ptr: [*]const f32,
    n: usize,
    dim: usize,
    centroid_ptr: [*]const f32,
    diversity_scores_out: [*]f32,
) void {
    // Compute distance from centroid for each embedding
    // Higher distance = more diverse
    
    for (0..n) |i| {
        const offset = i * dim;
        
        // Compute squared distance to centroid
        var dist_sq: f32 = 0.0;
        var j: usize = 0;
        
        // SIMD processing
        const simd_len = dim - (dim % LANE_WIDTH);
        while (j < simd_len) : (j += LANE_WIDTH) {
            var emb: VecF32 = undefined;
            var ctr: VecF32 = undefined;
            for (0..LANE_WIDTH) |k| {
                emb[k] = embeddings_ptr[offset + j + k];
                ctr[k] = centroid_ptr[j + k];
            }
            const diff = emb - ctr;
            dist_sq += @reduce(.Add, diff * diff);
        }
        
        // Scalar remainder
        while (j < dim) : (j += 1) {
            const diff = embeddings_ptr[offset + j] - centroid_ptr[j];
            dist_sq += diff * diff;
        }
        
        // Diversity = sqrt(distance) normalized
        diversity_scores_out[i] = @sqrt(dist_sq);
    }
}

/// Compute centroid of embedding cluster
export fn wm_compute_centroid(
    embeddings_ptr: [*]const f32,
    n: usize,
    dim: usize,
    centroid_out: [*]f32,
) void {
    // Initialize to zero
    for (0..dim) |d| {
        centroid_out[d] = 0.0;
    }
    
    // Sum all embeddings
    for (0..n) |i| {
        const offset = i * dim;
        for (0..dim) |d| {
            centroid_out[d] += embeddings_ptr[offset + d];
        }
    }
    
    // Divide by n
    const inv_n = 1.0 / @as(f32, @floatFromInt(n));
    for (0..dim) |d| {
        centroid_out[d] *= inv_n;
    }
}

/// Select diverse subset using greedy MMR
export fn wm_select_diverse_subset(
    relevance_scores: [*]const f32,
    similarity_matrix: [*]const f32,
    n: usize,
    k: usize,
    lambda: f32,
    selected_out: [*]usize,
) usize {
    var selected_count: usize = 0;
    var selected_mask = std.ArrayList(u8).init(std.heap.page_allocator);
    defer selected_mask.deinit();
    selected_mask.appendNTimes(0, n) catch return 0;
    
    // First select highest relevance
    var best_idx: usize = 0;
    var best_score: f32 = relevance_scores[0];
    for (1..n) |i| {
        if (relevance_scores[i] > best_score) {
            best_score = relevance_scores[i];
            best_idx = i;
        }
    }
    selected_out[selected_count] = best_idx;
    selected_count += 1;
    selected_mask.items[best_idx] = 1;
    
    // Greedily select using MMR
    var mmr_buffer = std.ArrayList(f32).init(std.heap.page_allocator);
    defer mmr_buffer.deinit();
    mmr_buffer.appendNTimes(0.0, n) catch return selected_count;
    
    while (selected_count < k and selected_count < n) {
        wm_mmr_diversity_scores(
            relevance_scores,
            similarity_matrix,
            n,
            lambda,
            selected_mask.items.ptr,
            mmr_buffer.items.ptr,
        );
        
        // Find best MMR score
        var best_mmr_idx: usize = 0;
        var best_mmr: f32 = -1.0;
        for (0..n) |i| {
            if (mmr_buffer.items[i] > best_mmr) {
                best_mmr = mmr_buffer.items[i];
                best_mmr_idx = i;
            }
        }
        
        if (best_mmr < 0.0) break; // No more valid candidates
        
        selected_out[selected_count] = best_mmr_idx;
        selected_count += 1;
        selected_mask.items[best_mmr_idx] = 1;
    }
    
    return selected_count;
}
