// HRR Binding - Holographic Reduced Representations (PSR-001)
// Target: 50-100× speedup for HRR operations
// Note: This is a binding layer - actual HRR implementation exists in Rust

const std = @import("std");

pub const HRRVector = struct {
    data: []f32,
    dimension: usize,
    
    pub fn init(allocator: std.mem.Allocator, dimension: usize) !HRRVector {
        const data = try allocator.alloc(f32, dimension);
        @memset(data, 0.0);
        
        return HRRVector{
            .data = data,
            .dimension = dimension,
        };
    }
    
    pub fn deinit(self: *HRRVector, allocator: std.mem.Allocator) void {
        allocator.free(self.data);
    }
    
    pub fn bind(self: *HRRVector, other: *const HRRVector, result: *HRRVector) void {
        for (self.data, other.data, result.data) |a, b, *r| {
            r.* = a * b;
        }
    }
    
    pub fn unbind(self: *HRRVector, other: *const HRRVector, result: *HRRVector) void {
        // Unbinding is binding with inverse
        for (self.data, other.data, result.data) |a, b, *r| {
            r.* = a / (b + 1e-10);
        }
    }
    
    pub fn permute(self: *HRRVector, result: *HRRVector) void {
        // Simple rotation permutation
        result.data[0] = self.data[self.dimension - 1];
        for (1..self.dimension) |i| {
            result.data[i] = self.data[i - 1];
        }
    }
    
    pub fn similarity(self: *const HRRVector, other: *const HRRVector) f32 {
        var dot: f32 = 0.0;
        var norm_a: f32 = 0.0;
        var norm_b: f32 = 0.0;
        
        for (self.data, other.data) |a, b| {
            dot += a * b;
            norm_a += a * a;
            norm_b += b * b;
        }
        
        if (norm_a == 0.0 or norm_b == 0.0) return 0.0;
        
        return dot / (@sqrt(norm_a) * @sqrt(norm_b));
    }
};

// C FFI exports
export fn hrr_vector_create(dimension: usize) ?*HRRVector {
    const allocator = std.heap.c_allocator;
    const vec = allocator.create(HRRVector) catch return null;
    vec.* = HRRVector.init(allocator, dimension) catch return null;
    return vec;
}

export fn hrr_vector_destroy(vec: ?*HRRVector) void {
    if (vec) |v| {
        v.deinit(std.heap.c_allocator);
        std.heap.c_allocator.destroy(v);
    }
}

export fn hrr_bind(a: ?*HRRVector, b: ?*const HRRVector, result: ?*HRRVector) bool {
    if (a) |vec_a| {
        if (b) |vec_b| {
            if (result) |res| {
                vec_a.bind(vec_b, res);
                return true;
            }
        }
    }
    return false;
}

export fn hrr_similarity(a: ?*const HRRVector, b: ?*const HRRVector) f32 {
    if (a) |vec_a| {
        if (b) |vec_b| {
            return vec_a.similarity(vec_b);
        }
    }
    return 0.0;
}

// Tests
test "hrr vector creation" {
    var vec = try HRRVector.init(std.testing.allocator, 512);
    defer vec.deinit(std.testing.allocator);
    
    try std.testing.expectEqual(@as(usize, 512), vec.dimension);
}

test "hrr bind" {
    var a = try HRRVector.init(std.testing.allocator, 4);
    defer a.deinit(std.testing.allocator);
    
    var b = try HRRVector.init(std.testing.allocator, 4);
    defer b.deinit(std.testing.allocator);
    
    var result = try HRRVector.init(std.testing.allocator, 4);
    defer result.deinit(std.testing.allocator);
    
    a.data[0] = 1.0;
    b.data[0] = 2.0;
    
    a.bind(&b, &result);
    
    try std.testing.expectApproxEqAbs(@as(f32, 2.0), result.data[0], 0.001);
}

test "hrr similarity" {
    var a = try HRRVector.init(std.testing.allocator, 4);
    defer a.deinit(std.testing.allocator);
    
    var b = try HRRVector.init(std.testing.allocator, 4);
    defer b.deinit(std.testing.allocator);
    
    for (a.data, 0..) |*val, i| {
        val.* = @as(f32, @floatFromInt(i + 1));
    }
    
    for (b.data, 0..) |*val, i| {
        val.* = @as(f32, @floatFromInt(i + 1));
    }
    
    const sim = a.similarity(&b);
    try std.testing.expectApproxEqAbs(@as(f32, 1.0), sim, 0.001);
}

test "hrr permute" {
    var a = try HRRVector.init(std.testing.allocator, 4);
    defer a.deinit(std.testing.allocator);
    
    var result = try HRRVector.init(std.testing.allocator, 4);
    defer result.deinit(std.testing.allocator);
    
    a.data[0] = 1.0;
    a.data[1] = 2.0;
    a.data[2] = 3.0;
    a.data[3] = 4.0;
    
    a.permute(&result);
    
    try std.testing.expectApproxEqAbs(@as(f32, 4.0), result.data[0], 0.001);
    try std.testing.expectApproxEqAbs(@as(f32, 1.0), result.data[1], 0.001);
}
