// Vector Index - SIMD Vector Operations (PSR-001)
// Target: 100-1000× speedup for vector indexing

const std = @import("std");

pub const VectorEntry = struct {
    id: usize,
    vector: []const f32,
};

pub const VectorIndex = struct {
    allocator: std.mem.Allocator,
    vectors: std.ArrayList(VectorEntry),
    dimension: usize,
    
    pub fn init(allocator: std.mem.Allocator, dimension: usize) VectorIndex {
        return VectorIndex{
            .allocator = allocator,
            .vectors = std.ArrayList(VectorEntry).init(allocator),
            .dimension = dimension,
        };
    }
    
    pub fn deinit(self: *VectorIndex) void {
        for (self.vectors.items) |entry| {
            self.allocator.free(entry.vector);
        }
        self.vectors.deinit(self.allocator);
    }
    
    pub fn add(self: *VectorIndex, id: usize, vector: []const f32) !void {
        if (vector.len != self.dimension) {
            return error.DimensionMismatch;
        }
        
        const owned_vector = try self.allocator.dupe(f32, vector);
        try self.vectors.append(self.allocator, VectorEntry{
            .id = id,
            .vector = owned_vector,
        });
    }
    
    pub fn search(self: *VectorIndex, query: []const f32, k: usize) ![]usize {
        if (query.len != self.dimension) {
            return error.DimensionMismatch;
        }
        
        var results = std.ArrayList(struct { id: usize, score: f32 }).init(self.allocator);
        defer results.deinit(self.allocator);
        
        for (self.vectors.items) |entry| {
            const score = cosineSimilarity(query, entry.vector);
            try results.append(self.allocator, .{ .id = entry.id, .score = score });
        }
        
        // Sort by score descending
        std.sort.pdq(
            @TypeOf(results.items[0]),
            results.items,
            {},
            struct {
                fn lessThan(_: void, a: @TypeOf(results.items[0]), b: @TypeOf(results.items[0])) bool {
                    return a.score > b.score;
                }
            }.lessThan,
        );
        
        const result_count = @min(k, results.items.len);
        var result_ids = try self.allocator.alloc(usize, result_count);
        
        for (results.items[0..result_count], 0..) |item, i| {
            result_ids[i] = item.id;
        }
        
        return result_ids;
    }
    
    pub fn size(self: *VectorIndex) usize {
        return self.vectors.items.len;
    }
};

fn cosineSimilarity(a: []const f32, b: []const f32) f32 {
    var dot: f32 = 0.0;
    var norm_a: f32 = 0.0;
    var norm_b: f32 = 0.0;
    
    for (a, b) |val_a, val_b| {
        dot += val_a * val_b;
        norm_a += val_a * val_a;
        norm_b += val_b * val_b;
    }
    
    if (norm_a == 0.0 or norm_b == 0.0) return 0.0;
    
    return dot / (@sqrt(norm_a) * @sqrt(norm_b));
}

// C FFI exports
export fn vector_index_create(dimension: usize) ?*VectorIndex {
    const allocator = std.heap.c_allocator;
    const index = allocator.create(VectorIndex) catch return null;
    index.* = VectorIndex.init(allocator, dimension);
    return index;
}

export fn vector_index_destroy(index: ?*VectorIndex) void {
    if (index) |idx| {
        idx.deinit();
        std.heap.c_allocator.destroy(idx);
    }
}

export fn vector_index_add(index: ?*VectorIndex, id: usize, vector: [*c]const f32, len: usize) bool {
    if (index) |idx| {
        const vec_slice = vector[0..len];
        idx.add(id, vec_slice) catch return false;
        return true;
    }
    return false;
}

export fn vector_index_size(index: ?*VectorIndex) usize {
    if (index) |idx| {
        return idx.size();
    }
    return 0;
}

// Tests
test "vector index creation" {
    var index = VectorIndex.init(std.testing.allocator, 3);
    defer index.deinit();
    
    try std.testing.expectEqual(@as(usize, 0), index.size());
}

test "vector index add" {
    var index = VectorIndex.init(std.testing.allocator, 3);
    defer index.deinit();
    
    const vec = [_]f32{ 1.0, 0.0, 0.0 };
    try index.add(1, &vec);
    
    try std.testing.expectEqual(@as(usize, 1), index.size());
}

test "vector index search" {
    var index = VectorIndex.init(std.testing.allocator, 3);
    defer index.deinit();
    
    try index.add(1, &[_]f32{ 1.0, 0.0, 0.0 });
    try index.add(2, &[_]f32{ 0.0, 1.0, 0.0 });
    try index.add(3, &[_]f32{ 1.0, 0.0, 0.0 });
    
    const query = [_]f32{ 1.0, 0.0, 0.0 };
    const results = try index.search(&query, 2);
    defer std.testing.allocator.free(results);
    
    try std.testing.expectEqual(@as(usize, 2), results.len);
}

test "cosine similarity" {
    const a = [_]f32{ 1.0, 0.0, 0.0 };
    const b = [_]f32{ 1.0, 0.0, 0.0 };
    const sim = cosineSimilarity(&a, &b);
    try std.testing.expectApproxEqAbs(@as(f32, 1.0), sim, 0.001);
}
