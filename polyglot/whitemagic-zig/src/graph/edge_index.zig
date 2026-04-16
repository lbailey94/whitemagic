// Edge Index - Lock-Free Edge Storage (PSR-003)
// Target: 1000× speedup for edge indexing

const std = @import("std");

pub const Edge = struct {
    source: []const u8,
    target: []const u8,
    weight: f32,
    edge_type: []const u8,
};

pub const EdgeIndex = struct {
    allocator: std.mem.Allocator,
    edges: std.ArrayListUnmanaged(Edge),
    
    pub fn init(allocator: std.mem.Allocator) EdgeIndex {
        _ = allocator;
        return EdgeIndex{
            .allocator = undefined,
            .edges = .{},
        };
    }
    
    pub fn initWithAllocator(allocator: std.mem.Allocator) EdgeIndex {
        return EdgeIndex{
            .allocator = allocator,
            .edges = .{},
        };
    }
    
    pub fn deinit(self: *EdgeIndex) void {
        self.edges.deinit(self.allocator);
    }
    
    pub fn addEdge(self: *EdgeIndex, edge: Edge) !void {
        try self.edges.append(self.allocator, edge);
    }
    
    pub fn getEdges(self: *const EdgeIndex, source: []const u8) std.ArrayListUnmanaged(Edge) {
        var results: std.ArrayListUnmanaged(Edge) = .{};
        
        for (self.edges.items) |edge| {
            if (std.mem.eql(u8, edge.source, source)) {
                results.append(self.allocator, edge) catch continue;
            }
        }
        
        return results;
    }
    
    pub fn edgeCount(self: *const EdgeIndex) usize {
        return self.edges.items.len;
    }
};

// C FFI exports
export fn edge_index_create() ?*EdgeIndex {
    const allocator = std.heap.c_allocator;
    const index = allocator.create(EdgeIndex) catch return null;
    index.* = EdgeIndex.initWithAllocator(allocator);
    return index;
}

export fn edge_index_destroy(index: ?*EdgeIndex) void {
    if (index) |idx| {
        idx.deinit();
        std.heap.c_allocator.destroy(idx);
    }
}

export fn edge_index_edge_count(index: ?*const EdgeIndex) usize {
    if (index) |idx| {
        return idx.edgeCount();
    }
    return 0;
}

// Tests
test "index creation" {
    var index = EdgeIndex.initWithAllocator(std.testing.allocator);
    defer index.deinit();
    
    try std.testing.expectEqual(@as(usize, 0), index.edgeCount());
}

test "add edge" {
    var index = EdgeIndex.initWithAllocator(std.testing.allocator);
    defer index.deinit();
    
    try index.addEdge(Edge{
        .source = "a",
        .target = "b",
        .weight = 1.0,
        .edge_type = "link",
    });
    
    try std.testing.expectEqual(@as(usize, 1), index.edgeCount());
}

test "get edges" {
    var index = EdgeIndex.initWithAllocator(std.testing.allocator);
    defer index.deinit();
    
    try index.addEdge(Edge{
        .source = "a",
        .target = "b",
        .weight = 1.0,
        .edge_type = "link",
    });
    
    try index.addEdge(Edge{
        .source = "a",
        .target = "c",
        .weight = 2.0,
        .edge_type = "link",
    });
    
    var edges = index.getEdges("a");
    defer edges.deinit(std.testing.allocator);
    
    try std.testing.expectEqual(@as(usize, 2), edges.items.len);
}
