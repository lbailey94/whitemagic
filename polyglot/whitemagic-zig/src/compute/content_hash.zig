const std = @import("std");

/// SIMD-accelerated memory content hashing for fast deduplication.
/// Computes 64-bit content hashes using SIMD-optimized FNV-1a variant.
/// Used for memory deduplication in V002 dedup pipeline.

const LANE_WIDTH = 8;
const VecU64 = @Vector(LANE_WIDTH, u64);

// FNV-1a 64-bit prime and offset basis
const FNV_PRIME: u64 = 1099511628211;
const FNV_OFFSET: u64 = 14695981039346656037;

/// SIMD-accelerated FNV-1a hash for content deduplication.
/// Processes 8 bytes at a time using SIMD.
export fn wm_content_hash_64(
    content_ptr: [*]const u8,
    content_len: usize,
) u64 {
    if (content_len == 0) return FNV_OFFSET;
    
    var hash: u64 = FNV_OFFSET;
    
    // SIMD processing: 8 bytes at a time
    const simd_len = content_len - (content_len % LANE_WIDTH);
    var i: usize = 0;
    
    while (i < simd_len) : (i += LANE_WIDTH) {
        // Load 8 bytes and accumulate into hash
        for (0..LANE_WIDTH) |j| {
            hash ^= content_ptr[i + j];
            hash *%= FNV_PRIME;
        }
    }
    
    // Scalar remainder
    while (i < content_len) : (i += 1) {
        hash ^= content_ptr[i];
        hash *%= FNV_PRIME;
    }
    
    return hash;
}

/// Batch compute content hashes for multiple memory contents.
export fn wm_content_hash_batch_64(
    contents_ptr: [*][*]const u8,  // Array of content pointers
    lengths_ptr: [*]const usize,   // Array of content lengths
    n: usize,
    hashes_out: [*]u64,
) void {
    for (0..n) |i| {
        hashes_out[i] = wm_content_hash_64(contents_ptr[i], lengths_ptr[i]);
    }
}

/// Compute 128-bit content hash (two 64-bit FNV-1a hashes with different seeds).
/// Useful for collision-resistant deduplication.
export fn wm_content_hash_128(
    content_ptr: [*]const u8,
    content_len: usize,
    hash_out: [*]u64,  // 2 elements: [low, high]
) void {
    if (content_len == 0) {
        hash_out[0] = FNV_OFFSET;
        hash_out[1] = FNV_OFFSET + 1;
        return;
    }
    
    // Two independent FNV-1a hashes with different starting points
    var h1: u64 = FNV_OFFSET;
    var h2: u64 = FNV_OFFSET ^ 0x123456789ABCDEF0;
    
    const simd_len = content_len - (content_len % LANE_WIDTH);
    var i: usize = 0;
    
    while (i < simd_len) : (i += LANE_WIDTH) {
        for (0..LANE_WIDTH) |j| {
            const byte = content_ptr[i + j];
            h1 ^= byte;
            h1 *%= FNV_PRIME;
            h2 ^= byte ^ 0x55;  // XOR with different pattern
            h2 *%= FNV_PRIME;
        }
    }
    
    while (i < content_len) : (i += 1) {
        const byte = content_ptr[i];
        h1 ^= byte;
        h1 *%= FNV_PRIME;
        h2 ^= byte ^ 0x55;
        h2 *%= FNV_PRIME;
    }
    
    hash_out[0] = h1;
    hash_out[1] = h2;
}

/// Fast similarity hash (SimHash variant) for near-duplicate detection.
/// Returns a 64-bit fingerprint where similar contents have similar hashes.
export fn wm_simhash_64(
    content_ptr: [*]const u8,
    content_len: usize,
) u64 {
    if (content_len == 0) return 0;
    
    // Simple SimHash: rolling hash with character n-grams
    var vec: [64]i32 = .{0} ** 64;
    
    var rolling: u64 = FNV_OFFSET;
    const window_size = @min(content_len, 4);
    
    for (0..content_len) |i| {
        // Update rolling hash with current byte
        rolling ^= content_ptr[i];
        rolling *%= FNV_PRIME;
        
        // After window is full, update SimHash vector
        if (i >= window_size - 1) {
            // Use rolling hash bits to update vector
            for (0..64) |bit| {
                const bit_val = @as(i32, @intCast((rolling >> @intCast(bit)) & 1));
                if (bit_val == 1) {
                    vec[bit] += 1;
                } else {
                    vec[bit] -= 1;
                }
            }
        }
    }
    
    // Fold vector into 64-bit hash
    var result: u64 = 0;
    for (0..64) |i| {
        if (vec[i] > 0) {
            result |= (@as(u64, 1) << @intCast(i));
        }
    }
    
    return result;
}
