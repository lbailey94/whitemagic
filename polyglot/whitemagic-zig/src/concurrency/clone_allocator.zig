// Clone Allocator - Custom Arena Allocator for Clone Objects (PSR-005)
// Target: 1000× speedup for clone allocation

const std = @import("std");

pub const CloneArena = struct {
    allocator: std.mem.Allocator,
    arena: std.heap.ArenaAllocator,
    allocated_count: usize,
    
    pub fn init(backing_allocator: std.mem.Allocator) CloneArena {
        return CloneArena{
            .allocator = backing_allocator,
            .arena = std.heap.ArenaAllocator.init(backing_allocator),
            .allocated_count = 0,
        };
    }
    
    pub fn deinit(self: *CloneArena) void {
        self.arena.deinit();
    }
    
    pub fn allocate(self: *CloneArena, size: usize) ![]u8 {
        const memory = try self.arena.allocator().alloc(u8, size);
        self.allocated_count += 1;
        return memory;
    }
    
    pub fn reset(self: *CloneArena) void {
        _ = self.arena.reset(.retain_capacity);
        self.allocated_count = 0;
    }
    
    pub fn getAllocatedCount(self: *const CloneArena) usize {
        return self.allocated_count;
    }
};

// C FFI exports
export fn clone_arena_create() ?*CloneArena {
    const allocator = std.heap.c_allocator;
    const arena = allocator.create(CloneArena) catch return null;
    arena.* = CloneArena.init(allocator);
    return arena;
}

export fn clone_arena_destroy(arena: ?*CloneArena) void {
    if (arena) |a| {
        a.deinit();
        std.heap.c_allocator.destroy(a);
    }
}

export fn clone_arena_allocate(arena: ?*CloneArena, size: usize) ?[*]u8 {
    if (arena) |a| {
        const memory = a.allocate(size) catch return null;
        return memory.ptr;
    }
    return null;
}

export fn clone_arena_reset(arena: ?*CloneArena) void {
    if (arena) |a| {
        a.reset();
    }
}

export fn clone_arena_allocated_count(arena: ?*const CloneArena) usize {
    if (arena) |a| {
        return a.getAllocatedCount();
    }
    return 0;
}

// Tests
test "arena creation" {
    var arena = CloneArena.init(std.testing.allocator);
    defer arena.deinit();
    
    try std.testing.expectEqual(@as(usize, 0), arena.getAllocatedCount());
}

test "arena allocate" {
    var arena = CloneArena.init(std.testing.allocator);
    defer arena.deinit();
    
    _ = try arena.allocate(1024);
    try std.testing.expectEqual(@as(usize, 1), arena.getAllocatedCount());
}

test "arena reset" {
    var arena = CloneArena.init(std.testing.allocator);
    defer arena.deinit();
    
    _ = try arena.allocate(1024);
    arena.reset();
    
    try std.testing.expectEqual(@as(usize, 0), arena.getAllocatedCount());
}

test "multiple allocations" {
    var arena = CloneArena.init(std.testing.allocator);
    defer arena.deinit();
    
    _ = try arena.allocate(100);
    _ = try arena.allocate(200);
    _ = try arena.allocate(300);
    
    try std.testing.expectEqual(@as(usize, 3), arena.getAllocatedCount());
}
