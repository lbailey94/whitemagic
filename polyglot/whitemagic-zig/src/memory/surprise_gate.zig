// Surprise Gate - Novelty Detection (PSR-001)
// Target: 50-100× speedup for novelty detection

const std = @import("std");

pub const NoveltyScore = struct {
    score: f32,
    is_novel: bool,
    distance_to_nearest: f32,
};

pub const SurpriseGate = struct {
    allocator: std.mem.Allocator,
    seen_vectors: std.ArrayList([]const f32),
    novelty_threshold: f32,
    
    pub fn init(allocator: std.mem.Allocator, threshold: f32) SurpriseGate {
        return SurpriseGate{
            .allocator = allocator,
            .seen_vectors = std.ArrayList([]const f32).init(allocator),
            .novelty_threshold = threshold,
        };
    }
    
    pub fn deinit(self: *SurpriseGate) void {
        for (self.seen_vectors.items) |vec| {
            self.allocator.free(vec);
        }
        self.seen_vectors.deinit(self.allocator);
    }
    
    pub fn checkNovelty(self: *SurpriseGate, vector: []const f32) !NoveltyScore {
        if (self.seen_vectors.items.len == 0) {
            const owned = try self.allocator.dupe(f32, vector);
            try self.seen_vectors.append(self.allocator, owned);
            
            return NoveltyScore{
                .score = 1.0,
                .is_novel = true,
                .distance_to_nearest = std.math.inf(f32),
            };
        }
        
        var min_distance: f32 = std.math.inf(f32);
        
        for (self.seen_vectors.items) |seen| {
            const dist = euclideanDistance(vector, seen);
            if (dist < min_distance) {
                min_distance = dist;
            }
        }
        
        const is_novel = min_distance > self.novelty_threshold;
        
        if (is_novel) {
            const owned = try self.allocator.dupe(f32, vector);
            try self.seen_vectors.append(self.allocator, owned);
        }
        
        const score = @min(1.0, min_distance / self.novelty_threshold);
        
        return NoveltyScore{
            .score = score,
            .is_novel = is_novel,
            .distance_to_nearest = min_distance,
        };
    }
    
    pub fn reset(self: *SurpriseGate) void {
        for (self.seen_vectors.items) |vec| {
            self.allocator.free(vec);
        }
        self.seen_vectors.clearRetainingCapacity();
    }
    
    pub fn seenCount(self: *const SurpriseGate) usize {
        return self.seen_vectors.items.len;
    }
};

fn euclideanDistance(a: []const f32, b: []const f32) f32 {
    var sum: f32 = 0.0;
    
    for (a, b) |val_a, val_b| {
        const diff = val_a - val_b;
        sum += diff * diff;
    }
    
    return @sqrt(sum);
}

// C FFI exports
export fn surprise_gate_create(threshold: f32) ?*SurpriseGate {
    const allocator = std.heap.c_allocator;
    const gate = allocator.create(SurpriseGate) catch return null;
    gate.* = SurpriseGate.init(allocator, threshold);
    return gate;
}

export fn surprise_gate_destroy(gate: ?*SurpriseGate) void {
    if (gate) |g| {
        g.deinit();
        std.heap.c_allocator.destroy(g);
    }
}

export fn surprise_gate_check(
    gate: ?*SurpriseGate,
    vector: [*c]const f32,
    len: usize,
    score_out: [*c]f32,
) bool {
    if (gate) |g| {
        const vec_slice = vector[0..len];
        const result = g.checkNovelty(vec_slice) catch return false;
        score_out[0] = result.score;
        return result.is_novel;
    }
    return false;
}

export fn surprise_gate_seen_count(gate: ?*const SurpriseGate) usize {
    if (gate) |g| {
        return g.seenCount();
    }
    return 0;
}

// Tests
test "surprise gate creation" {
    var gate = SurpriseGate.init(std.testing.allocator, 0.5);
    defer gate.deinit();
    
    try std.testing.expectEqual(@as(usize, 0), gate.seenCount());
}

test "first vector is novel" {
    var gate = SurpriseGate.init(std.testing.allocator, 0.5);
    defer gate.deinit();
    
    const vec = [_]f32{ 1.0, 2.0, 3.0 };
    const result = try gate.checkNovelty(&vec);
    
    try std.testing.expect(result.is_novel);
    try std.testing.expectApproxEqAbs(@as(f32, 1.0), result.score, 0.001);
}

test "similar vector not novel" {
    var gate = SurpriseGate.init(std.testing.allocator, 0.5);
    defer gate.deinit();
    
    const vec1 = [_]f32{ 1.0, 2.0, 3.0 };
    _ = try gate.checkNovelty(&vec1);
    
    const vec2 = [_]f32{ 1.1, 2.1, 3.1 };
    const result = try gate.checkNovelty(&vec2);
    
    try std.testing.expect(!result.is_novel);
}

test "different vector is novel" {
    var gate = SurpriseGate.init(std.testing.allocator, 0.5);
    defer gate.deinit();
    
    const vec1 = [_]f32{ 1.0, 2.0, 3.0 };
    _ = try gate.checkNovelty(&vec1);
    
    const vec2 = [_]f32{ 10.0, 20.0, 30.0 };
    const result = try gate.checkNovelty(&vec2);
    
    try std.testing.expect(result.is_novel);
}

test "reset clears seen vectors" {
    var gate = SurpriseGate.init(std.testing.allocator, 0.5);
    defer gate.deinit();
    
    const vec = [_]f32{ 1.0, 2.0, 3.0 };
    _ = try gate.checkNovelty(&vec);
    
    try std.testing.expectEqual(@as(usize, 1), gate.seenCount());
    
    gate.reset();
    try std.testing.expectEqual(@as(usize, 0), gate.seenCount());
}
