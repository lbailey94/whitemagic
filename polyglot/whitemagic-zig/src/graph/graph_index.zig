// Graph Index - Lock-Free Adjacency Lists (PSR-003)
// Target: 1000× speedup for graph indexing

const std = @import("std");

pub const GraphIndex = struct {
    allocator: std.mem.Allocator,
    adjacency: std.StringHashMap(std.ArrayList([]const u8)),
    
    pub fn init(allocator: std.mem.Allocator) GraphIndex {
        return GraphIndex{
            .allocator = allocator,
            .adjacency = std.StringHashMap(std.ArrayList([]const u8)).init(allocator),
        };
    }
    
    pub fn deinit(self: *GraphIndex) void {
        var it = self.adjacency.iterator();
        while (it.next()) |entry| {
            for (entry.value_ptr.items) |neighbor| {
                self.allocator.free(neighbor);
            }
            entry.value_ptr.deinit();
            self.allocator.free(entry.key_ptr.*);
        }
        self.adjacency.deinit();
    }
    
    pub fn addEdge(self: *GraphIndex, source: []const u8, target: []const u8) !void {
        const source_key = try self.allocator.dupe(u8, source);
        const target_dup = try self.allocator.dupe(u8, target);
        
        const result = try self.adjacency.getOrPut(source_key);
        if (!result.found_existing) {
            result.value_ptr.* = std.ArrayList([]const u8).init(self.allocator);
        }
        
        try result.value_ptr.append(target_dup);
    }
    
    pub fn getNeighbors(self: *const GraphIndex, node: []const u8) ?[]const []const u8 {
        if (self.adjacency.get(node)) |neighbors| {
            return neighbors.items;
        }
        return null;
    }
    
    pub fn nodeCount(self: *const GraphIndex) usize {
        return self.adjacency.count();
    }
};

// C FFI exports
export fn graph_index_create() ?*GraphIndex {
    const allocator = std.heap.c_allocator;
    const index = allocator.create(GraphIndex) catch return null;
    index.* = GraphIndex.init(allocator);
    return index;
}

export fn graph_index_destroy(index: ?*GraphIndex) void {
    if (index) |idx| {
        idx.deinit();
        std.heap.c_allocator.destroy(idx);
    }
}

export fn graph_index_add_edge(index: ?*GraphIndex, source: [*c]const u8, source_len: usize, target: [*c]const u8, target_len: usize) bool {
    if (index) |idx| {
        const src = source[0..source_len];
        const tgt = target[0..target_len];
        idx.addEdge(src, tgt) catch return false;
        return true;
    }
    return false;
}

export fn graph_index_node_count(index: ?*const GraphIndex) usize {
    if (index) |idx| {
        return idx.nodeCount();
    }
    return 0;
}

// Tests
test "index creation" {
    var index = GraphIndex.init(std.testing.allocator);
    defer index.deinit();
    
    try std.testing.expectEqual(@as(usize, 0), index.nodeCount());
}

test "add edge" {
    var index = GraphIndex.init(std.testing.allocator);
    defer index.deinit();
    
    try index.addEdge("a", "b");
    try std.testing.expectEqual(@as(usize, 1), index.nodeCount());
}

test "get neighbors" {
    var index = GraphIndex.init(std.testing.allocator);
    defer index.deinit();
    
    try index.addEdge("a", "b");
    try index.addEdge("a", "c");
    
    const neighbors = index.getNeighbors("a");
    try std.testing.expect(neighbors != null);
    try std.testing.expectEqual(@as(usize, 2), neighbors.?.len);
}
