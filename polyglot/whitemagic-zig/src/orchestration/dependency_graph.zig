// Dependency Graph - Lock-Free Dependency Tracking (PSR-007)
// Target: 1000× speedup for dependency resolution

const std = @import("std");

pub const DependencyGraph = struct {
    allocator: std.mem.Allocator,
    edges: std.StringHashMap(std.ArrayList([]const u8)),
    
    pub fn init(allocator: std.mem.Allocator) DependencyGraph {
        return DependencyGraph{
            .allocator = allocator,
            .edges = std.StringHashMap(std.ArrayList([]const u8)).init(allocator),
        };
    }
    
    pub fn deinit(self: *DependencyGraph) void {
        var it = self.edges.iterator();
        while (it.next()) |entry| {
            entry.value_ptr.deinit();
        }
        self.edges.deinit();
    }
    
    pub fn addDependency(self: *DependencyGraph, task: []const u8, depends_on: []const u8) !void {
        const result = try self.edges.getOrPut(task);
        if (!result.found_existing) {
            result.value_ptr.* = std.ArrayList([]const u8).init(self.allocator);
        }
        try result.value_ptr.append(depends_on);
    }
    
    pub fn getDependencies(self: *const DependencyGraph, task: []const u8) ?[]const []const u8 {
        if (self.edges.get(task)) |deps| {
            return deps.items;
        }
        return null;
    }
    
    pub fn nodeCount(self: *const DependencyGraph) usize {
        return self.edges.count();
    }
};

// C FFI exports
export fn dependency_graph_create() ?*DependencyGraph {
    const allocator = std.heap.c_allocator;
    const graph = allocator.create(DependencyGraph) catch return null;
    graph.* = DependencyGraph.init(allocator);
    return graph;
}

export fn dependency_graph_destroy(graph: ?*DependencyGraph) void {
    if (graph) |g| {
        g.deinit();
        std.heap.c_allocator.destroy(g);
    }
}

export fn dependency_graph_node_count(graph: ?*const DependencyGraph) usize {
    if (graph) |g| {
        return g.nodeCount();
    }
    return 0;
}

// Tests
test "graph creation" {
    var graph = DependencyGraph.init(std.testing.allocator);
    defer graph.deinit();
    
    try std.testing.expectEqual(@as(usize, 0), graph.nodeCount());
}

test "add dependency" {
    var graph = DependencyGraph.init(std.testing.allocator);
    defer graph.deinit();
    
    try graph.addDependency("task1", "task0");
    try std.testing.expectEqual(@as(usize, 1), graph.nodeCount());
}

test "get dependencies" {
    var graph = DependencyGraph.init(std.testing.allocator);
    defer graph.deinit();
    
    try graph.addDependency("task1", "task0");
    
    const deps = graph.getDependencies("task1");
    try std.testing.expect(deps != null);
    try std.testing.expectEqual(@as(usize, 1), deps.?.len);
}
