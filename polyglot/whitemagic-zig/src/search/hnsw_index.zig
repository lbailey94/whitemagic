const std = @import("std");

/// Simplified HNSW index for approximate nearest neighbor search.
/// Uses flat arrays and arena allocation for safety.

const LANE_WIDTH = 8;
const VecF32 = @Vector(LANE_WIDTH, f32);

/// Connection in the graph
pub const Connection = struct {
    node_id: u32,
    distance: f32,
};

/// Simple HNSW Index using flat storage
pub const HnswIndex = struct {
    allocator: std.mem.Allocator,
    arena: std.heap.ArenaAllocator,

    dim: usize,
    m: usize,
    m_max0: usize,
    ef_construction: usize,
    ef_search: usize,
    max_elements: usize,

    // Flat storage for vectors (node_id * dim)
    vectors: []f32,
    // Number of nodes added
    node_count: usize,
    // Entry point node
    entry_node: i32,
    // Max level in graph
    max_level: usize,

    // Adjacency: flat array [max_elements * MAX_LAYERS * m_max0]
    // Each entry: node_id (u32), distance (f32), count (usize)
    adj_node_ids: []u32,
    adj_distances: []f32,
    adj_counts: []usize,

    // Level counter for deterministic level assignment
    level_counter: u32,

    const MAX_LAYERS: usize = 16;
    const MAX_CONN: usize = 32; // m_max0 <= 32

    pub fn init(
        allocator: std.mem.Allocator,
        dim: usize,
        m: usize,
        ef_construction: usize,
        ef_search: usize,
        max_elements: usize,
    ) !HnswIndex {
        var arena = std.heap.ArenaAllocator.init(allocator);
        errdefer arena.deinit();

        const aa = arena.allocator();

        // Allocate vectors storage
        const vectors = try aa.alloc(f32, max_elements * dim);
        @memset(vectors, 0);

        // Allocate adjacency storage
        const adj_size = max_elements * MAX_LAYERS * MAX_CONN;
        const adj_node_ids = try aa.alloc(u32, adj_size);
        @memset(adj_node_ids, 0xFFFFFFFF); // Sentinel value
        const adj_distances = try aa.alloc(f32, adj_size);
        @memset(adj_distances, 0);
        const adj_counts = try aa.alloc(usize, max_elements * MAX_LAYERS);
        @memset(adj_counts, 0);

        return HnswIndex{
            .allocator = allocator,
            .arena = arena,
            .dim = dim,
            .m = m,
            .m_max0 = m * 2,
            .ef_construction = ef_construction,
            .ef_search = ef_search,
            .max_elements = max_elements,
            .vectors = vectors,
            .node_count = 0,
            .entry_node = -1,
            .max_level = 0,
            .adj_node_ids = adj_node_ids,
            .adj_distances = adj_distances,
            .adj_counts = adj_counts,
            .level_counter = 0,
        };
    }

    pub fn deinit(self: *HnswIndex) void {
        self.arena.deinit();
    }

    /// Get adjacency index for (node, layer, neighbor)
    fn adj_idx(_: *HnswIndex, node: usize, layer: usize, neighbor: usize) usize {
        return node * MAX_LAYERS * MAX_CONN + layer * MAX_CONN + neighbor;
    }

    /// Get adjacency count index for (node, layer)
    fn adj_count_idx(_: *HnswIndex, node: usize, layer: usize) usize {
        return node * MAX_LAYERS + layer;
    }

    /// Assign level using bit-counting (deterministic)
    fn select_level(self: *HnswIndex) usize {
        self.level_counter += 1;
        const c = self.level_counter;
        if (c == 0) return 0;
        var level: usize = 0;
        var tmp = c;
        while (tmp > 0 and (tmp & 1) == 0) : (level += 1) {
            tmp >>= 1;
        }
        return @min(level, MAX_LAYERS - 1);
    }

    /// Cosine similarity using SIMD
    pub fn cosine_similarity(query: []const f32, candidate: []const f32) f32 {
        const len = @min(query.len, candidate.len);
        if (len == 0) return 0.0;

        var dot: f32 = 0.0;
        var norm_q: f32 = 0.0;
        var norm_c: f32 = 0.0;

        const simd_len = len - (len % LANE_WIDTH);
        var i: usize = 0;

        var dot_acc: VecF32 = @splat(0.0);
        var nq_acc: VecF32 = @splat(0.0);
        var nc_acc: VecF32 = @splat(0.0);

        while (i < simd_len) : (i += LANE_WIDTH) {
            const vq: VecF32 = query[i..][0..LANE_WIDTH].*;
            const vc: VecF32 = candidate[i..][0..LANE_WIDTH].*;
            dot_acc += vq * vc;
            nq_acc += vq * vq;
            nc_acc += vc * vc;
        }

        dot += @reduce(.Add, dot_acc);
        norm_q += @reduce(.Add, nq_acc);
        norm_c += @reduce(.Add, nc_acc);

        while (i < len) : (i += 1) {
            dot += query[i] * candidate[i];
            norm_q += query[i] * query[i];
            norm_c += candidate[i] * candidate[i];
        }

        const denom = @sqrt(norm_q) * @sqrt(norm_c);
        if (denom == 0.0) return 0.0;
        return dot / denom;
    }

    /// Distance (1 - cosine similarity)
    fn distance(self: *HnswIndex, query: []const f32, node_id: usize) f32 {
        const node_vec = self.vectors[node_id * self.dim .. (node_id + 1) * self.dim];
        return 1.0 - cosine_similarity(query, node_vec);
    }

    /// Add a vector to the index
    pub fn add_item(self: *HnswIndex, vector: []const f32) !usize {
        if (self.node_count >= self.max_elements) {
            return error.IndexFull;
        }

        const node_id = self.node_count;
        const level = self.select_level();

        // Copy vector
        const dest = self.vectors[node_id * self.dim .. (node_id + 1) * self.dim];
        @memcpy(dest, vector);

        // If first node, set as entry point
        if (self.entry_node < 0) {
            self.entry_node = @intCast(node_id);
            self.max_level = level;
        } else {
            // Simple connection: connect to entry point at all layers
            const entry = @as(usize, @intCast(self.entry_node));
            const dist = self.distance(vector, entry);

            for (0..@min(level + 1, MAX_LAYERS)) |l| {
                const count_idx = self.adj_count_idx(node_id, l);
                const entry_count_idx = self.adj_count_idx(entry, l);

                // Connect node -> entry
                if (self.adj_counts[count_idx] < self.m_max0) {
                    const idx = self.adj_idx(node_id, l, self.adj_counts[count_idx]);
                    self.adj_node_ids[idx] = @intCast(entry);
                    self.adj_distances[idx] = dist;
                    self.adj_counts[count_idx] += 1;
                }

                // Connect entry -> node
                if (self.adj_counts[entry_count_idx] < self.m_max0) {
                    const idx = self.adj_idx(entry, l, self.adj_counts[entry_count_idx]);
                    self.adj_node_ids[idx] = @intCast(node_id);
                    self.adj_distances[idx] = dist;
                    self.adj_counts[entry_count_idx] += 1;
                }
            }

            if (level > self.max_level) {
                self.max_level = level;
                self.entry_node = @intCast(node_id);
            }
        }

        self.node_count += 1;
        return node_id;
    }

    /// Search for k nearest neighbors using HNSW graph traversal.
    /// Algorithm: greedy descent from top layer, then ef_search at layer 0.
    pub fn search(self: *HnswIndex, query: []const f32, k: usize) ![]Connection {
        const aa = self.arena.allocator();

        // If no entry point, return empty
        if (self.entry_node < 0) {
            return try aa.alloc(Connection, 0);
        }

        var current: usize = @intCast(self.entry_node);
        var current_dist = self.distance(query, current);

        // Greedy descent from top layer to layer 1
        var layer = self.max_level;
        while (layer > 0) : (layer -= 1) {
            if (layer >= MAX_LAYERS) continue;

            var improved = true;
            while (improved) {
                improved = false;
                const count_idx = self.adj_count_idx(current, layer);
                const count = self.adj_counts[count_idx];

                for (0..count) |ni| {
                    const a_idx = self.adj_idx(current, layer, ni);
                    const neighbor = self.adj_node_ids[a_idx];
                    if (neighbor == 0xFFFFFFFF) continue;

                    const neighbor_dist = self.distance(query, neighbor);
                    if (neighbor_dist < current_dist) {
                        current = neighbor;
                        current_dist = neighbor_dist;
                        improved = true;
                    }
                }
            }
        }

        // Layer 0 search with ef_search candidates
        const ef = @max(self.ef_search, k);
        var candidates = std.ArrayList(Connection){ .items = &.{}, .capacity = 0 };
        defer candidates.deinit(aa);

        var visited = std.AutoHashMap(u32, void).init(aa);
        defer visited.deinit();

        // Initialize with entry point at layer 0
        try candidates.append(aa, .{ .node_id = @intCast(current), .distance = current_dist });
        try visited.put(@intCast(current), {});

        // Expand candidates
        var i: usize = 0;
        while (i < candidates.items.len) : (i += 1) {
            const c = candidates.items[i];
            const node = c.node_id;

            // Explore neighbors at layer 0
            const count_idx = self.adj_count_idx(node, 0);
            const count = self.adj_counts[count_idx];

            for (0..count) |ni| {
                const a_idx = self.adj_idx(node, 0, ni);
                const neighbor = self.adj_node_ids[a_idx];
                if (neighbor == 0xFFFFFFFF) continue;
                if (visited.get(neighbor) != null) continue;

                try visited.put(neighbor, {});
                const neighbor_dist = self.distance(query, neighbor);

                // Add if better than worst candidate or not full
                if (candidates.items.len < ef or neighbor_dist < candidates.items[candidates.items.len - 1].distance) {
                    try candidates.append(aa, .{ .node_id = neighbor, .distance = neighbor_dist });

                    // Keep sorted
                    var j = candidates.items.len - 1;
                    while (j > 0 and candidates.items[j].distance < candidates.items[j - 1].distance) {
                        const tmp = candidates.items[j];
                        candidates.items[j] = candidates.items[j - 1];
                        candidates.items[j - 1] = tmp;
                        j -= 1;
                    }

                    if (candidates.items.len > ef) {
                        _ = candidates.pop();
                    }
                }
            }
        }

        // Return top k
        const actual_k = @min(candidates.items.len, k);
        const top_k = try aa.alloc(Connection, actual_k);
        @memcpy(top_k, candidates.items[0..actual_k]);
        return top_k;
    }
};

// --------------------------------------------------------------------------
// C-ABI exports
// --------------------------------------------------------------------------

pub const HnswHandle = opaque {};

pub export fn wm_hnsw_create(
    dim: usize,
    m: usize,
    ef_construction: usize,
    ef_search: usize,
    max_elements: usize,
) ?*HnswHandle {
    const allocator = std.heap.c_allocator;
    const index = allocator.create(HnswIndex) catch return null;
    index.* = HnswIndex.init(
        allocator,
        dim,
        m,
        ef_construction,
        ef_search,
        max_elements,
    ) catch {
        allocator.destroy(index);
        return null;
    };
    return @ptrCast(index);
}

pub export fn wm_hnsw_free(handle: ?*HnswHandle) void {
    if (handle) |h| {
        const index: *HnswIndex = @alignCast(@ptrCast(h));
        index.deinit();
        std.heap.c_allocator.destroy(index);
    }
}

pub export fn wm_hnsw_add(
    handle: ?*HnswHandle,
    vector_ptr: [*]const f32,
) isize {
    if (handle) |h| {
        const index: *HnswIndex = @alignCast(@ptrCast(h));
        const vector = vector_ptr[0..index.dim];
        const node_id = index.add_item(vector) catch return -1;
        return @intCast(node_id);
    }
    return -1;
}

pub export fn wm_hnsw_search(
    handle: ?*HnswHandle,
    query_ptr: [*]const f32,
    k: usize,
    results_ptr: [*]Connection,
) usize {
    if (handle) |h| {
        const index: *HnswIndex = @alignCast(@ptrCast(h));
        const query = query_ptr[0..index.dim];
        const results = index.search(query, k) catch return 0;
        const actual = @min(results.len, k);
        for (0..actual) |i| {
            results_ptr[i] = results[i];
        }
        return actual;
    }
    return 0;
}

pub export fn wm_hnsw_count(handle: ?*HnswHandle) usize {
    if (handle) |h| {
        const index: *HnswIndex = @alignCast(@ptrCast(h));
        return index.node_count;
    }
    return 0;
}

pub export fn wm_hnsw_max_level(handle: ?*HnswHandle) usize {
    if (handle) |h| {
        const index: *HnswIndex = @alignCast(@ptrCast(h));
        return index.max_level;
    }
    return 0;
}

// --------------------------------------------------------------------------
// Tests
// --------------------------------------------------------------------------

test "hnsw basic" {
    var index = try HnswIndex.init(
        std.testing.allocator,
        4, 16, 200, 50, 1000,
    );
    defer index.deinit();

    const v1 = [_]f32{ 1.0, 0.0, 0.0, 0.0 };
    const v2 = [_]f32{ 0.0, 1.0, 0.0, 0.0 };
    const v3 = [_]f32{ 1.0, 0.1, 0.0, 0.0 };

    _ = try index.add_item(&v1);
    _ = try index.add_item(&v2);
    _ = try index.add_item(&v3);

    try std.testing.expectEqual(index.node_count, 3);

    const query = [_]f32{ 0.9, 0.1, 0.0, 0.0 };
    const results = try index.search(&query, 2);

    try std.testing.expect(results.len >= 1);
    try std.testing.expect(results[0].node_id == 0 or results[0].node_id == 2);
}
