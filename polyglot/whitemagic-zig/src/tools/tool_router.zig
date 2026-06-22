// Tool Router - <1μs Routing (PSR-006)
// Target: 1000× speedup for tool routing

const std = @import("std");

pub const Tool = struct {
    name: []const u8,
    gana: []const u8,
    hash: u64,
};

pub const ToolRouter = struct {
    allocator: std.mem.Allocator,
    tools: std.ArrayList(Tool),
    hash_map: std.AutoHashMap(u64, usize),
    
    pub fn init(allocator: std.mem.Allocator) ToolRouter {
        return ToolRouter{
            .allocator = allocator,
            .tools = std.ArrayList(Tool).init(allocator),
            .hash_map = std.AutoHashMap(u64, usize).init(allocator),
        };
    }
    
    pub fn deinit(self: *ToolRouter) void {
        self.tools.deinit();
        self.hash_map.deinit();
    }
    
    pub fn registerTool(self: *ToolRouter, name: []const u8, gana: []const u8) !void {
        const hash = std.hash.Wyhash.hash(0, name);
        const index = self.tools.items.len;
        
        try self.tools.append(Tool{
            .name = name,
            .gana = gana,
            .hash = hash,
        });
        
        try self.hash_map.put(hash, index);
    }
    
    pub fn route(self: *const ToolRouter, name: []const u8) ?Tool {
        const hash = std.hash.Wyhash.hash(0, name);
        
        if (self.hash_map.get(hash)) |index| {
            return self.tools.items[index];
        }
        
        return null;
    }
    
    pub fn toolCount(self: *const ToolRouter) usize {
        return self.tools.items.len;
    }
};

// C FFI exports
export fn tool_router_create() ?*ToolRouter {
    const allocator = std.heap.c_allocator;
    const router = allocator.create(ToolRouter) catch return null;
    router.* = ToolRouter.init(allocator);
    return router;
}

export fn tool_router_destroy(router: ?*ToolRouter) void {
    if (router) |r| {
        r.deinit();
        std.heap.c_allocator.destroy(r);
    }
}

export fn tool_router_register(router: ?*ToolRouter, name: [*c]const u8, name_len: usize, gana: [*c]const u8, gana_len: usize) bool {
    if (router) |r| {
        const name_slice = name[0..name_len];
        const gana_slice = gana[0..gana_len];
        r.registerTool(name_slice, gana_slice) catch return false;
        return true;
    }
    return false;
}

export fn tool_router_tool_count(router: ?*const ToolRouter) usize {
    if (router) |r| {
        return r.toolCount();
    }
    return 0;
}

// Tests
test "router creation" {
    var router = ToolRouter.init(std.testing.allocator);
    defer router.deinit();
    
    try std.testing.expectEqual(@as(usize, 0), router.toolCount());
}

test "register tool" {
    var router = ToolRouter.init(std.testing.allocator);
    defer router.deinit();
    
    try router.registerTool("test_tool", "gana_test");
    try std.testing.expectEqual(@as(usize, 1), router.toolCount());
}

test "route tool" {
    var router = ToolRouter.init(std.testing.allocator);
    defer router.deinit();
    
    try router.registerTool("test_tool", "gana_test");
    
    const tool = router.route("test_tool");
    try std.testing.expect(tool != null);
    try std.testing.expect(std.mem.eql(u8, tool.?.name, "test_tool"));
}

test "route nonexistent" {
    var router = ToolRouter.init(std.testing.allocator);
    defer router.deinit();
    
    const tool = router.route("nonexistent");
    try std.testing.expect(tool == null);
}
